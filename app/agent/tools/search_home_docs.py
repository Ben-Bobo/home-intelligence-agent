from langchain_core.tools import tool
from app.rag.vectorstore import retrieve_hybrid
from app.logger import get_logger

logger = get_logger(__name__)


@tool
def search_home_docs(query: str) -> str:
    """Search the homeowner's personal documents including inspection reports,
    mortgage documents, appliance manuals, warranties, contractor quotes,
    and HOA rules. Use this when the user asks about something specific
    to their home or their documents."""

    logger.info("Tool: search_home_docs | query=%.80s", query)

    results = retrieve_hybrid(query)

    if not results:
        return "No relevant documents found in the home knowledge base."

    output_parts = []
    for i, result in enumerate(results):
        meta = result["metadata"]
        doc_type = meta.get("document_type", "document")
        filename = meta.get("filename", "unknown")
        chunk_index = meta.get("chunk_index", "?")
        total_chunks = meta.get("total_chunks", "?")
        reranked = " | reranked" if result.get("reranked") else ""

        output_parts.append(
            f"[Source {i+1} | relevance: {result['score']:.4f} | {doc_type} | {filename} | chunk {chunk_index}/{total_chunks}{reranked}]:\n{result['content']}"
        )

    return "\n\n".join(output_parts)