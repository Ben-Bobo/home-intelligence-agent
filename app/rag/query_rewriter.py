from langchain_openai import ChatOpenAI
from app.config import get_settings
from app.logger import get_logger

logger = get_logger(__name__)

def _make_llm() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        timeout=10
    )

_llm = _make_llm()


def rewrite_query(query: str) -> str:
    """Rewrite a user query to improve retrieval quality."""

    prompt = f"""Rewrite this search query to improve document retrieval. 
    Expand abbreviations, add relevant synonyms, and make implicit meaning explicit.
    Keep it concise — this is a search query, not a sentence.

    Original query: {query}

    If the query references a section number, paragraph, or clause, keep that reference 
    and add likely topic keywords.

    Respond with ONLY the rewritten query, nothing else."""

    try:
        response = _llm.invoke(prompt)
        rewritten = response.content.strip()
        logger.info("Query rewrite | original='%.60s' | rewritten='%.60s'", query, rewritten)
        return rewritten
    except Exception as e:
        logger.warning("Query rewrite failed, using original | %s", str(e))
        return query