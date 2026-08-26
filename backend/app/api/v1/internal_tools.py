"""Internal HTTP tools exposed only to the persistent Pi Agent service."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agent.tools.artifact_tool import artifact_builder
from app.agent.tools.rag_tool import search_knowledge
from app.agent.tools.ship30_tool import ship_30_essay_generator

router = APIRouter(prefix="/api/v1/internal/tools", tags=["internal-tools"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=6, ge=1, le=12)


class Ship30Request(BaseModel):
    topic: str = Field(min_length=1)
    context_sources: list[dict] = Field(default_factory=list)


class ArtifactRequest(BaseModel):
    title: str = "Generated Artifact"
    type: str = Field(default="html", pattern="^(html|markdown)$")
    content: str = ""


@router.post("/search_knowledge")
async def search_knowledge_internal(body: SearchRequest):
    results = await search_knowledge(body.query, body.top_k)
    return {"ok": True, "results": results}


@router.post("/ship30_skill")
async def ship30_internal(body: Ship30Request):
    result = await ship_30_essay_generator(body.topic, body.context_sources)
    return {"ok": True, **result}


@router.post("/create_artifact")
async def artifact_internal(body: ArtifactRequest):
    result = await artifact_builder(body.title, body.type, content=body.content)
    return {"ok": True, **result}
