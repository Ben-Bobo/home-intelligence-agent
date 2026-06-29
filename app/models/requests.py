from pydantic import BaseModel
from typing import Optional


class AskRequest(BaseModel):
    question: str
    thread_id: Optional[str] = None
    image: Optional[str] = None


class IngestRequest(BaseModel):
    doc_type: str = "general"
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None


class ResumeRequest(BaseModel):
    thread_id: str
    approved: bool