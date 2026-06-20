from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from app.agent.state import AgentState
from app.agent.tools.search_home_docs import search_home_docs
from app.agent.tools.web_search import web_search
from app.agent.tools.image_analysis import analyze_image
from app.agent.tools.request_action import request_action
from app.config import get_settings
from app.logger import get_logger
from datetime import datetime

current_date = datetime.now().strftime("%B %d, %Y")

logger = get_logger(__name__)

TOOLS = [search_home_docs, web_search, analyze_image, request_action]

from datetime import datetime

current_date = datetime.now().strftime("%B %d, %Y")

SYSTEM_PROMPT = f"""You are a knowledgeable home intelligence assistant. Today's date is {current_date}.
You help homeowners understand their home documents, find contractors, estimate costs,
identify things around the house, and manage home maintenance.

You have access to tools. Use them when needed:
- search_home_docs: Search the homeowner's personal documents (inspection reports,
  mortgage docs, manuals, warranties, etc). Use this when they ask about THEIR home.
- web_search: Search the web for current info like contractor listings, repair costs,
  product details, or general home improvement advice.
- analyze_image: When the user uploads a photo and asks about it.
- request_action: When the user wants you to add something to their calendar, create
  a maintenance task, or send a notification. You MUST call this tool to queue the
  action. Do NOT just say you will do it — actually call the tool.

When the user asks you to add, create, schedule, or set up anything (calendar events,
tasks, reminders), you MUST call request_action. Never respond with "I'll do that"
without making the actual tool call.

When you give your final answer, be thorough and practical. Cite which documents
or sources informed your answer when relevant."""


def get_reasoning_node():
    settings = get_settings()

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout
    )

    llm_with_tools = llm.bind_tools(TOOLS)

    system_message = SystemMessage(content=SYSTEM_PROMPT)

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