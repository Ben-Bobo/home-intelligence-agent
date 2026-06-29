from app.rag.loader import load_and_chunk
from app.rag.vectorstore import upsert_documents
from app.logger import get_logger
from app.errors import DocumentIngestionError

logger = get_logger(__name__)


def ingest_document(
    file_path: str,
    filename: str,
    doc_type: str = "general",
    chunk_size: int = None,
    chunk_overlap: int = None
) -> dict:
    logger.info("Ingestion start | file=%s | type=%s", filename, doc_type)

    chunks, config = load_and_chunk(file_path, filename, doc_type, chunk_size, chunk_overlap)

    if not chunks:
        raise DocumentIngestionError(f"No content extracted from {filename}")

    try:
        count = upsert_documents(chunks)
        logger.info("Ingestion complete | file=%s | chunks_stored=%d", filename, count)
        return {
            "chunks_stored": count,
            "chunk_size": config["chunk_size"],
            "chunk_overlap": config["chunk_overlap"]
        }
    except DocumentIngestionError:
        raise
    except Exception as e:
        logger.error("Ingestion failed | file=%s | %s", filename, str(e))
        raise DocumentIngestionError(f"Failed to store {filename}: {str(e)}")