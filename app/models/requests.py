from pydantic import BaseModel
from typing import Optional


class AskRequest(BaseModel):
    question: str
    thread_id: Optional[str] = None
    image: Optional[str] = None  # base64 encoded image