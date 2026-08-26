"""Skill 1 Tool: search_knowledge — queries Supabase PostgreSQL pgvector for grounded transcript chunks."""
import logging
from app.rag.retriever import TranscriptRetriever

logger = logging.getLogger(__name__)

async def search_knowledge(query: str, top_k: int = 6) -> list[dict]:
    """Retrieves top K transcript chunks from the Supabase pgvector runtime knowledge base.
    
    Includes episode title, guest name, source URL, and verified excerpt for citation.
    """
    logger.info(f"Executing Tool: search_knowledge(query='{query}', top_k={top_k})")
    documents = await TranscriptRetriever(top_k=top_k).ainvoke(query)
    return [
        {
            **document.metadata,
            "excerpt": document.page_content,
        }
        for document in documents
    ]

# Alias for backwards compatibility
transcript_rag_search = search_knowledge
