from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from app.agent.state import AgentState
from app.agent.prompts import get_system_prompt
from app.agent.tools import ALL_TOOLS
from app.config import get_settings
from app.logger import get_logger

logger = get_logger(__name__)


def get_reasoning_node():
    settings = get_settings()

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout
    )

    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    system_message = SystemMessage(content=get_system_prompt())

    def reasoning_node(state: AgentState) -> dict:
        logger.info("Node: reasoning | messages=%d", len(state["messages"]))

        messages = [system_message] + state["messages"]

        try:
            response = llm_with_tools.invoke(messages)
            logger.info(
                "Node: reasoning | tool_calls=%d | content_length=%d",
                len(response.tool_calls) if response.tool_calls else 0,
                len(response.content) if response.content else 0
            )
            return {"messages": [response]}

        except Exception as e:
            logger.error("Node: reasoning | FAILED | %s", str(e))
            from langchain_core.messages import AIMessage
            error_msg = AIMessage(content="I encountered an error while processing your question. Please try again.")
            return {"messages": [error_msg]}

    return reasoning_node