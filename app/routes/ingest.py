import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from app.rag.ingestor import ingest_document
from app.models.responses import IngestResponse
from app.errors import DocumentIngestionError
from app.auth import verify_api_key
from app.logger import get_logger
from typing import Optional

logger = get_logger(__name__)
router = APIRouter(dependencies=[Depends(verify_api_key)])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(...),
    doc_type: str = Form(default="general"),
    chunk_size: Optional[int] = Form(default=None),
    chunk_overlap: Optional[int] = Form(default=None)
):
    logger.info("Ingest request | file=%s | type=%s | chunk_size=%s | overlap=%s",
                file.filename, doc_type, chunk_size, chunk_overlap)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}"
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        result = ingest_document(tmp_path, file.filename, doc_type, chunk_size, chunk_overlap)

        return IngestResponse(
            success=True,
            filename=file.filename,
            chunks_stored=result["chunks_stored"],
            chunk_size=result["chunk_size"],
            chunk_overlap=result["chunk_overlap"],
            message=f"Ingested {file.filename} into {result['chunks_stored']} chunks (size={result['chunk_size']}, overlap={result['chunk_overlap']})."
        )

    except DocumentIngestionError as e:
        logger.error("Ingest failed | %s", str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Ingest unexpected error | %s", str(e))
        raise HTTPException(status_code=500, detail="Unexpected ingestion error.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)