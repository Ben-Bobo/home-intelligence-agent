from langchain_core.tools import tool
from ddgs import DDGS
from app.logger import get_logger

logger = get_logger(__name__)


@tool
def web_search(query: str) -> str:
    """Search the web for current information. Use this for finding contractors,
    repair cost estimates, general home improvement advice, product information,
    or anything not found in the homeowner's personal documents.
    Always use the current year 2026 if a year is relevant to the search."""

    logger.info("Tool: web_search | query=%.80s", query)

    try:
        results = DDGS().text(query, max_results=5)

        if not results:
            return "No web results found for this query."

        output_parts = []
        for r in results:
            output_parts.append(f"**{r['title']}**\n{r['body']}\nSource: {r['href']}")

        return "\n\n".join(output_parts)

    except Exception as e:
        logger.error("Tool: web_search | FAILED | %s", str(e))
        return f"Web search failed: {str(e)}"