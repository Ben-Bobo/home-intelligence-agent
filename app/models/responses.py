from pydantic import BaseModel


class IngestResponse(BaseModel):
    success: bool
    filename: str
    chunks_stored: int
    message: str


class ActionOut(BaseModel):
    type: str
    data: dict


class AskResponse(BaseModel):
    question: str
    answer: str
    thread_id: str
    actions: list[ActionOut]