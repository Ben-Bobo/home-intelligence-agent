import uuid
import json
from fastapi import APIRouter, HTTPException, Depends
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from app.agent.graph import agent
from app.agent.state import create_initial_state
from app.queue import action_queue
from app.auth import verify_api_key
from app.models.requests import AskRequest, ResumeRequest
from app.models.responses import AskResponse, ActionOut
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    logger.info("Ask request | question=%.80s", request.question)

    thread_id = request.thread_id or str(uuid.uuid4())

    content = []
    if request.image:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{request.image}"}
        })
    content.append({"type": "text", "text": request.question})

    human_message = HumanMessage(content=content)

    initial_state = create_initial_state([human_message])

    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = agent.invoke(initial_state, config=config)

        # Check if graph paused for HITL approval
        graph_state = agent.get_state(config)
        if graph_state.tasks:
            for task in graph_state.tasks:
                if task.interrupts:
                    interrupt_value = task.interrupts[0].value
                    logger.info("Ask paused for HITL approval | thread=%s | action_type=%s",
                                thread_id, interrupt_value.get("action", {}).get("type"))
                    return AskResponse(
                        question=request.question,
                        answer="An action requires your approval before it can be submitted.",
                        thread_id=thread_id,
                        actions=[],
                        pending_approval=interrupt_value
                    )

        last_message = result["messages"][-1]
        answer_text = last_message.content if last_message.content else ""

        # Actions are already validated and in state
        actions = result.get("actions", [])

        # Store in queue for n8n
        for action in actions:
            action_queue.add(action)

        action_outputs = [
            ActionOut(type=a["type"], data={k: v for k, v in a.items() if k != "type"})
            for a in actions
        ]

        logger.info(
            "Ask complete | thread=%s | actions=%d | answer_length=%d",
            thread_id, len(actions), len(answer_text)
        )

        return AskResponse(
            question=request.question,
            answer=answer_text,
            thread_id=thread_id,
            actions=action_outputs
        )

    except Exception as e:
        logger.error("Ask failed | %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Agent failed to process the question.")


@router.post("/resume", response_model=AskResponse)
async def resume(request: ResumeRequest):
    logger.info("Resume request | thread=%s | approved=%s", request.thread_id, request.approved)

    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        result = agent.invoke(Command(resume=request.approved), config=config)

        last_message = result["messages"][-1]
        answer_text = last_message.content if last_message.content else ""

        actions = result.get("actions", [])

        for action in actions:
            action_queue.add(action)

        action_outputs = [
            ActionOut(type=a["type"], data={k: v for k, v in a.items() if k != "type"})
            for a in actions
        ]

        logger.info(
            "Resume complete | thread=%s | approved=%s | actions=%d",
            request.thread_id, request.approved, len(actions)
        )

        return AskResponse(
            question="",
            answer=answer_text,
            thread_id=request.thread_id,
            actions=action_outputs
        )

    except Exception as e:
        logger.error("Resume failed | %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Agent failed to resume.")