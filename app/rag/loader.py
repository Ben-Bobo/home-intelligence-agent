import uuid
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from app.config import get_settings
from app.logger import get_logger
from app.errors import DocumentIngestionError

logger = get_logger(__name__)


def load_and_chunk(file_path: str, filename: str, doc_type: str = "general") -> list[Document]:
    path = Path(file_path)
    settings = get_settings()

    if not path.exists():
        raise DocumentIngestionError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    try:
        if suffix == ".pdf":
            loader = PyPDFLoader(str(path))
            raw_docs = loader.load()
        elif suffix in [".txt", ".md"]:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            raw_docs = [Document(page_content=content)]
        else:
            raise DocumentIngestionError(f"Unsupported file type: {suffix}")
    except DocumentIngestionError:
        raise
    except Exception as e:
        raise DocumentIngestionError(f"Failed to load {filename}: {str(e)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap
    )
    chunks = splitter.split_documents(raw_docs)

    doc_id = str(uuid.uuid4())

    for i, chunk in enumerate(chunks):
        chunk.metadata.update({
            "document_id": doc_id,
            "filename": filename,
            "document_type": doc_type,
            "chunk_index": i,
            "total_chunks": len(chunks)
        })

    logger.info("Loaded %s | type=%s | chunks=%d", filename, doc_type, len(chunks))
    return chunks