from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    # App
    app_name: str = "Home Intelligence Agent"
    environment: str = "development"
    debug: bool = False
    
    # Auth
    api_secret_key: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_timeout: int = 30

    # RAG
    pinecone_api_key: str = ""
    pinecone_index_name: str = "home-intelligence"
    rag_top_k: int = 15
    rag_alpha: float = 0.7  # 1.0 = pure semantic, 0.0 = pure keyword

    # Chunking
    chunk_size: int = 800
    chunk_overlap: int = 100

    # LangSmith
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = True
    langchain_project: str = "home-intelligence-agent"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def log_level(self) -> str:
        return "INFO" if self.is_production else "DEBUG"


@lru_cache()
def get_settings() -> Settings:
    return Settings()