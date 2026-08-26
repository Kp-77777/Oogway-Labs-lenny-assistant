"""v1 Models API Router: GET /api/v1/models, GET /api/v1/models/current, PUT /api/v1/models/current"""
import logging
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/models", tags=["models"])

# In-memory global state for active model selection
_active_model_state = {
    "provider": "cloud",
    "model": settings.GEMINI_CHAT_MODEL
}


class UpdateModelRequest(BaseModel):
    provider: str = Field(pattern="^(cloud|ollama)$")
    model: str = Field(min_length=1)


@router.get("")
@router.get("/")
async def list_available_models():
    """Returns available providers/models and their availability."""
    ollama_ready = False
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                ollama_ready = True
                data = resp.json()
                ollama_models = [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        ollama_ready = False

    return {
        "providers": [
            {
                "id": "cloud",
                "name": "Cloud provider",
                "available": settings.gemini_available,
                "models": [settings.GEMINI_CHAT_MODEL],
                "description": "Fast cloud LLM with 1M token context window"
            },
            {
                "id": "ollama",
                "name": "Ollama (Local LLM)",
                "available": ollama_ready,
                "models": ollama_models or [settings.OLLAMA_MODEL],
                "description": "Local privacy-first LLM running on your computer"
            }
        ]
    }


@router.get("/current")
async def get_current_model():
    """Returns the currently selected provider and model."""
    return _active_model_state


@router.put("/current")
async def set_current_model(body: UpdateModelRequest):
    """Changes the active model/provider, e.g. Ollama to Cloud."""
    _active_model_state["provider"] = body.provider.lower()
    _active_model_state["model"] = body.model
    logger.info(f"Active model switched to: {body.provider} / {body.model}")
    return {
        "message": "Active model updated successfully.",
        "current": _active_model_state
    }
