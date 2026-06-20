from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from app.config import get_settings
from app.logger import get_logger

logger = get_logger(__name__)


def get_vectorstore() -> PineconeVectorStore:
    settings = get_settings()
    return PineconeVectorStore(
        index_name=settings.pinecone_index_name,
        pinecone_api_key=settings.pinecone_api_key,
        embedding=OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model="text-embedding-3-small"
        )
    )


def retrieve_similar(query: str, k: int = None) -> list:
    settings = get_settings()
    if k is None:
        k = settings.rag_top_k

    logger.info("RAG retrieve | k=%d | query=%.80s", k, query)

    try:
        vs = get_vectorstore()
        results = vs.similarity_search(query, k=k)
        logger.info("RAG retrieve | found=%d chunks", len(results))
        return results
    except Exception as e:
        logger.error("RAG retrieve | FAILED | %s", str(e))
        return []


def retrieve_with_scores(query: str, k: int = None) -> list:
    """Returns (document, score) tuples with full metadata."""
    settings = get_settings()
    if k is None:
        k = settings.rag_top_k

    logger.info("RAG retrieve_with_scores | k=%d | query=%.80s", k, query)

    try:
        vs = get_vectorstore()
        results = vs.similarity_search_with_score(query, k=k)

        for doc, score in results:
            logger.info(
                "RAG result | score=%.4f | type=%s | file=%s | chunk=%s/%s",
                score,
                doc.metadata.get("document_type", "unknown"),
                doc.metadata.get("filename", "unknown"),
                doc.metadata.get("chunk_index", "?"),
                doc.metadata.get("total_chunks", "?")
            )

        return results
    except Exception as e:
        logger.error("RAG retrieve_with_scores | FAILED | %s", str(e))
        return []