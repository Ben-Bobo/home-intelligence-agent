import uuid
import json
from fastapi import APIRouter, HTTPException, Depends
from langchain_core.messages import HumanMessage
from app.agent.graph import agent
from app.agent.state import create_initial_state
from app.queue import action_queue
from app.auth import verify_api_key
from app.models.requests import AskRequest
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