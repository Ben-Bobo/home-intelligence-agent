from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.config import get_settings
from app.logger import get_logger
from app.routes import ingest, ask, actions

logger = get_logger(__name__)

app = FastAPI(title="Home Intelligence Agent")

app.include_router(ingest.router, prefix="/api")
app.include_router(ask.router, prefix="/api")
app.include_router(actions.router, prefix="/api")


@app.on_event("startup")
async def startup():
    settings = get_settings()
    logger.info(
        "Home Intelligence Agent starting | env=%s | model=%s | index=%s",
        settings.environment,
        settings.openai_model,
        settings.pinecone_index_name
    )


@app.get("/")
async def root():
    return {"status": "running", "app": "Home Intelligence Agent"}


@app.get("/health")
async def health():
    return {"status": "healthy"}