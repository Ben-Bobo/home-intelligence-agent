from pinecone import Pinecone as PineconeClient
from langchain_openai import OpenAIEmbeddings
from pinecone_text.sparse import BM25Encoder
from langsmith import traceable
from app.config import get_settings
from app.logger import get_logger

logger = get_logger(__name__)

_bm25_encoder = None


def get_bm25_encoder() -> BM25Encoder:
    global _bm25_encoder
    if _bm25_encoder is None:
        try:
            _bm25_encoder = BM25Encoder().load("bm25_params.json")
            logger.info("BM25 encoder loaded from bm25_params.json")
        except Exception:
            _bm25_encoder = BM25Encoder().default()
            logger.info("BM25 encoder initialized with defaults")
    return _bm25_encoder


def get_pinecone_client():
    settings = get_settings()
    return PineconeClient(api_key=settings.pinecone_api_key)


def get_pinecone_index():
    pc = get_pinecone_client()
    settings = get_settings()
    return pc.Index(settings.pinecone_index_name)


def get_embeddings():
    settings = get_settings()
    return OpenAIEmbeddings(
        api_key=settings.openai_api_key,
        model="text-embedding-3-small"
    )


def upsert_documents(chunks: list) -> int:
    """Upsert documents with both dense and sparse vectors."""
    index = get_pinecone_index()
    embeddings = get_embeddings()
    bm25 = get_bm25_encoder()

    texts = [chunk.page_content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    dense_vectors = embeddings.embed_documents(texts)
    sparse_vectors = bm25.encode_documents(texts)

    vectors = []
    for i, chunk in enumerate(chunks):
        doc_id = f"{metadatas[i].get('document_id', 'unknown')}_{metadatas[i].get('chunk_index', i)}"

        meta = {}
        for k, v in metadatas[i].items():
            if isinstance(v, (str, int, float, bool)):
                meta[k] = v
        meta["text"] = texts[i]

        vectors.append({
            "id": doc_id,
            "values": dense_vectors[i],
            "sparse_values": sparse_vectors[i],
            "metadata": meta
        })

    batch_size = 50
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch)

    logger.info("Upserted %d vectors with dense + sparse embeddings", len(vectors))
    return len(vectors)

@traceable(name="hybrid_search")
def retrieve_hybrid(query: str, k: int = None, alpha: float = None, rerank: bool = True) -> list:
    """
    Hybrid search with optional reranking.
    1. Rewrite query for better retrieval
    2. Hybrid search (dense + sparse)
    3. Rerank results with Pinecone's reranker
    """
    from app.rag.query_rewriter import rewrite_query

    settings = get_settings()
    if k is None:
        k = settings.rag_top_k
    if alpha is None:
        alpha = settings.rag_alpha

    # Step 1: Rewrite the query
    search_query = rewrite_query(query)

    logger.info("RAG hybrid retrieve | k=%d | alpha=%.2f | original='%.60s' | search='%.60s'",
                k, alpha, query, search_query)

    try:
        index = get_pinecone_index()
        embeddings = get_embeddings()
        bm25 = get_bm25_encoder()

        # Step 2: Generate both vector types
        dense_vector = embeddings.embed_query(search_query)
        sparse_vector = bm25.encode_queries([search_query])[0]

        scaled_dense = [v * alpha for v in dense_vector]
        scaled_sparse = {
            "indices": sparse_vector["indices"],
            "values": [v * (1 - alpha) for v in sparse_vector["values"]]
        }

        # Retrieve more candidates if reranking (reranker will narrow down)
        retrieve_k = k * 3 if rerank else k

        results = index.query(
            vector=scaled_dense,
            sparse_vector=scaled_sparse,
            top_k=retrieve_k,
            include_metadata=True
        )

        if not results.matches:
            logger.info("RAG hybrid retrieve | no matches found")
            return []

        # Step 3: Rerank if enabled
        if rerank and len(results.matches) > 1:
            formatted = _rerank_results(query, results.matches, k)
        else:
            formatted = _format_results(results.matches)

        return formatted

    except Exception as e:
        logger.error("RAG hybrid retrieve | FAILED | %s", str(e))
        return []

@traceable(name="rerank_results")
def _rerank_results(query: str, matches: list, top_n: int) -> list:
    """Rerank search results using Pinecone's reranker."""
    pc = get_pinecone_client()

    documents = []
    match_map = {}
    for i, match in enumerate(matches):
        text = match.metadata.get("text", "")
        documents.append({"id": str(i), "text": text})
        match_map[str(i)] = match

    try:
        reranked = pc.inference.rerank(
            model="bge-reranker-v2-m3",
            query=query,
            documents=documents,
            top_n=top_n,
            rank_fields=["text"],
            return_documents=True
        )

        formatted = []
        for item in reranked.data:
            original_match = match_map[str(item.index)]
            meta = {k: v for k, v in original_match.metadata.items() if k != "text"}

            formatted.append({
                "content": item.document["text"],
                "metadata": meta,
                "score": item.score,
                "reranked": True
            })

            logger.info(
                "RAG reranked | score=%.4f | type=%s | file=%s | chunk=%s/%s",
                item.score,
                meta.get("document_type", "unknown"),
                meta.get("filename", "unknown"),
                meta.get("chunk_index", "?"),
                meta.get("total_chunks", "?")
            )

        return formatted

    except Exception as e:
        logger.warning("Reranking failed, returning unranked results | %s", str(e))
        return _format_results(matches[:top_n])


def _format_results(matches: list) -> list:
    """Format raw Pinecone matches without reranking."""
    formatted = []
    for match in matches:
        meta = {k: v for k, v in match.metadata.items() if k != "text"}
        formatted.append({
            "content": match.metadata.get("text", ""),
            "metadata": meta,
            "score": match.score,
            "reranked": False
        })

        logger.info(
            "RAG result | score=%.4f | type=%s | file=%s | chunk=%s/%s",
            match.score,
            meta.get("document_type", "unknown"),
            meta.get("filename", "unknown"),
            meta.get("chunk_index", "?"),
            meta.get("total_chunks", "?")
        )

    return formatted


def fit_bm25(texts: list[str]):
    """Fit BM25 encoder to a corpus and save parameters."""
    bm25 = BM25Encoder()
    bm25.fit(texts)
    bm25.dump("bm25_params.json")
    global _bm25_encoder
    _bm25_encoder = bm25
    logger.info("BM25 encoder fitted to %d documents and saved", len(texts))