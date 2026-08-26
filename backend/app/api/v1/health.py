"""v1 Health API Router: GET /api/v1/health and GET /api/v1/health/ready"""
import logging
import httpx
from fastapi import APIRouter
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("")
@router.get("/")
async def health_check():
    """Basic API health check."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0"
    }


@router.get("/ready")
async def health_readiness():
    """Checks whether FastAPI, Supabase/PostgreSQL, and Ollama are available."""
    # Check Ollama status (non-blocking fast timeout)
    ollama_ready = False
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            res = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if res.status_code == 200:
                ollama_ready = True
    except Exception:
        ollama_ready = False

    db_ready = settings.db_available

    is_ready = db_ready or settings.gemini_available or ollama_ready

    return {
        "status": "ready" if is_ready else "degraded",
        "fastapi": True,
        "supabase_postgresql": db_ready,
        "ollama": ollama_ready,
        "cloud": settings.gemini_available,
    }
