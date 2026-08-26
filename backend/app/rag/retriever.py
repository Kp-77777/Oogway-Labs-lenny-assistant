"""Hybrid transcript retrieval with pgvector, full-text search, and provenance."""
import json
import logging
from typing import Any, Optional

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings
from app.rag.ingest import all_chunk_data as _in_memory_chunks

logger = logging.getLogger(__name__)


def _metadata(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _source_from_row(row: Any) -> dict:
    metadata = _metadata(getattr(row, "source_metadata", None))
    return {
        "episode": getattr(row, "episode_title", None) or "Lenny Episode",
        "guest": getattr(row, "guest_name", None) or "Lenny Guest",
        "url": metadata.get("timestamp_url") or getattr(row, "episode_url", None) or metadata.get("github_url", "") or "",
        "excerpt": getattr(row, "chunk_text", None) or "",
        "similarity": float(getattr(row, "similarity", 0) or 0),
        "speakers": metadata.get("speakers", []),
        "start_seconds": metadata.get("start_seconds"),
        "end_seconds": metadata.get("end_seconds"),
        "github_url": metadata.get("github_url", ""),
    }


async def _embed_query(query: str) -> Optional[list[float]]:
    if not settings.gemini_available:
        return None
    for model_id in settings.gemini_embed_model_candidates:
        try:
            embeddings = GoogleGenerativeAIEmbeddings(
                model=model_id,
                google_api_key=settings.GEMINI_API_KEY,
            )
            embedding = list(await __import__("asyncio").to_thread(embeddings.embed_query, query))
            if len(embedding) == settings.VECTOR_DIMENSIONS:
                return embedding
            logger.warning("Query embedding dimensions did not match the configured vector column")
        except Exception as exc:
            logger.warning("Query embedding failed for %s: %s", model_id, exc)
    return None


class TranscriptRetriever(BaseRetriever):
    """LangChain retriever backed by the existing Supabase pgvector contract."""

    top_k: int = settings.RAG_TOP_K

    def _get_relevant_documents(self, query: str, *, run_manager: Any = None) -> list[Document]:
        raise NotImplementedError("Use TranscriptRetriever.ainvoke in the async API")

    async def _aget_relevant_documents(self, query: str, *, run_manager: Any = None) -> list[Document]:
        results = await search_transcripts(query, self.top_k)
        return [
            Document(
                page_content=result["excerpt"],
                metadata={key: value for key, value in result.items() if key != "excerpt"},
            )
            for result in results
        ]



async def _pgvector_search(query: str, query_embedding: list[float], top_k: int) -> list[dict]:
    """Hybrid rank: cosine similarity plus a small exact-term signal."""
    try:
        from app.db.database import get_session_factory
        from sqlalchemy import text

        factory = get_session_factory()
        if factory is None:
            return []
        vector = "[" + ",".join(str(value) for value in query_embedding) + "]"
        async with factory() as session:
            result = await session.execute(
                text("""
                    SELECT episode_title, guest_name, episode_url, chunk_text, source_metadata,
                           0.90 * (1 - (embedding <=> CAST(:embedding AS vector))) +
                           0.10 * LEAST(
                               ts_rank_cd(
                                   to_tsvector('english', coalesce(episode_title, '') || ' ' || coalesce(guest_name, '') || ' ' || coalesce(chunk_text, '')),
                                   plainto_tsquery('english', :query)
                               ),
                               1.0
                           ) AS similarity
                    FROM transcript_chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY similarity DESC
                    LIMIT :top_k
                """),
                {"embedding": vector, "query": query, "top_k": top_k},
            )
            return [_source_from_row(row) for row in result.fetchall()]
    except Exception as exc:
        logger.error("Hybrid pgvector search failed: %s", exc)
        return []


async def _db_keyword_search(query: str, top_k: int) -> list[dict]:
    """Full-text fallback when embeddings are unavailable."""
    try:
        from app.db.database import get_session_factory
        from sqlalchemy import text

        factory = get_session_factory()
        if factory is None:
            return []
        async with factory() as session:
            result = await session.execute(
                text("""
                    SELECT episode_title, guest_name, episode_url, chunk_text, source_metadata,
                           ts_rank_cd(
                               to_tsvector('english', coalesce(episode_title, '') || ' ' || coalesce(guest_name, '') || ' ' || coalesce(chunk_text, '')),
                               plainto_tsquery('english', :query)
                           ) AS similarity
                    FROM transcript_chunks
                    WHERE to_tsvector('english', coalesce(episode_title, '') || ' ' || coalesce(guest_name, '') || ' ' || coalesce(chunk_text, ''))
                          @@ plainto_tsquery('english', :query)
                    ORDER BY similarity DESC
                    LIMIT :top_k
                """),
                {"query": query, "top_k": top_k},
            )
            return [_source_from_row(row) for row in result.fetchall()]
    except Exception as exc:
        logger.error("Database full-text search fallback failed: %s", exc)
        return []


def _keyword_fallback_search(query: str, top_k: int) -> list[dict]:
    """Multi-term fallback for deliberate no-database development mode."""
    words = [word for word in query.lower().split() if len(word) > 2]
    scored: list[tuple[float, dict]] = []
    for chunk in _in_memory_chunks:
        metadata = chunk.get("source_metadata", {})
        keywords = metadata.get("keywords", [])
        searchable = " ".join(
            [
                chunk.get("episode_title", ""),
                chunk.get("guest_name", ""),
                chunk.get("chunk_text", ""),
                " ".join(str(item) for item in keywords) if isinstance(keywords, list) else str(keywords),
            ]
        ).lower()
        matches = sum(1 for word in words if word in searchable)
        if matches:
            title_bonus = sum(1 for word in words if word in chunk.get("episode_title", "").lower()) * 0.5
            scored.append((matches + title_bonus, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, chunk in scored[:top_k]:
        metadata = chunk.get("source_metadata", {})
        results.append(
            {
                "episode": chunk["episode_title"],
                "guest": chunk["guest_name"],
                "url": metadata.get("timestamp_url") or chunk.get("episode_url", ""),
                "excerpt": chunk["chunk_text"],
                "similarity": score / max(len(words), 1),
                "speakers": metadata.get("speakers", []),
                "start_seconds": metadata.get("start_seconds"),
                "end_seconds": metadata.get("end_seconds"),
                "github_url": metadata.get("github_url", ""),
            }
        )
    return results


async def search_transcripts(query: str, top_k: Optional[int] = None) -> list[dict]:
    """Return grounded transcript context with citation and timestamp provenance."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return []
    k = max(1, min(top_k or settings.RAG_TOP_K, 12))
    threshold = getattr(settings, "RAG_SIMILARITY_THRESHOLD", 0.45)
    results: list[dict] = []
    if settings.db_available:
        embedding = await _embed_query(cleaned_query)
        if embedding:
            results = await _pgvector_search(cleaned_query, embedding, k)
        if not results:
            results = await _db_keyword_search(cleaned_query, k)
    elif _in_memory_chunks:
        results = _keyword_fallback_search(cleaned_query, k)

    return [r for r in results if float(r.get("similarity", 0) or 0) >= threshold]
