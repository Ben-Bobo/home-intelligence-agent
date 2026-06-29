from pydantic import BaseModel
from typing import Optional


class IngestResponse(BaseModel):
    success: bool
    filename: str
    chunks_stored: int
    chunk_size: int
    chunk_overlap: int
    message: str


class ActionOut(BaseModel):
    type: str
    data: dict


class AskResponse(BaseModel):
    question: str
    answer: str
    thread_id: str
    actions: list[ActionOut]
    pending_approval: Optional[dict] = None