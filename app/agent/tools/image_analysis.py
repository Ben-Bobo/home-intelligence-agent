from langchain_core.tools import tool
from app.logger import get_logger

logger = get_logger(__name__)


@tool
def analyze_image(question_about_image: str) -> str:
    """Analyze an image the user has uploaded. Use this when the user asks
    'what is this?', wants to identify something in their home, or asks
    about something visible in a photo they provided. The image is already
    available to you in the conversation — describe what you see and answer
    the user's question about it."""

    logger.info("Tool: analyze_image | question=%.80s", question_about_image)

    return f"Analyze the image provided in the conversation and answer: {question_about_image}"