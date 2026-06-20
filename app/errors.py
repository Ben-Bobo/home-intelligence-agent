class HomeAgentError(Exception):
    """Base exception for the home intelligence agent."""
    pass


class RAGRetrievalError(HomeAgentError):
    """Pinecone query failed."""
    pass


class DocumentIngestionError(HomeAgentError):
    """Document could not be loaded, chunked, or embedded."""
    pass


class LLMError(HomeAgentError):
    """OpenAI call failed."""
    pass


class ClassificationError(HomeAgentError):
    """Agent could not classify the query type."""
    pass