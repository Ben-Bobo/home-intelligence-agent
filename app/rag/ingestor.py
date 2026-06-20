from app.rag.loader import load_and_chunk
from app.rag.vectorstore import get_vectorstore
from app.logger import get_logger
from app.errors import DocumentIngestionError

logger = get_logger(__name__)


def ingest_document(file_path: str, filename: str, doc_type: str = "general") -> int:
    logger.info("Ingestion start | file=%s | type=%s", filename, doc_type)

    chunks = load_and_chunk(file_path, filename, doc_type)

    if not chunks:
        raise DocumentIngestionError(f"No content extracted from {filename}")

    try:
        vs = get_vectorstore()
        vs.add_documents(chunks)
        logger.info("Ingestion complete | file=%s | chunks_stored=%d", filename, len(chunks))
        return len(chunks)
    except DocumentIngestionError:
        raise
    except Exception as e:
        logger.error("Ingestion failed | file=%s | %s", filename, str(e))
        raise DocumentIngestionError(f"Failed to store {filename} in Pinecone: {str(e)}")