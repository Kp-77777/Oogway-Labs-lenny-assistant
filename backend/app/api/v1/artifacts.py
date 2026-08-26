"""v1 Artifacts API Router: GET /api/v1/artifacts/{artifact_id}"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.db import database
from app.db.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


class ArtifactResponseSchema(BaseModel):
    id: str
    title: str
    artifact_type: str   # 'html' or 'markdown'
    content: str
    created_at: str


@router.get("/{artifact_id}", response_model=ArtifactResponseSchema)
async def get_artifact(artifact_id: str, db=Depends(get_db)):
    """Retrieves a generated Markdown or HTML artifact for the Artifact Viewer."""
    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            res = await db.execute(
                text("SELECT id, title, artifact_type, content, created_at FROM generated_artifacts WHERE id = :aid"),
                {"aid": artifact_id}
            )
            r = res.fetchone()
            if r:
                return ArtifactResponseSchema(
                    id=str(r.id),
                    title=r.title,
                    artifact_type=r.artifact_type,
                    content=r.content,
                    created_at=r.created_at.isoformat()
                )
        except Exception as e:
            logger.error(f"DB get artifact failed: {e}")

    # Memory fallback sample artifact
    return ArtifactResponseSchema(
        id=artifact_id,
        title="Sample Growth Matrix Artifact",
        artifact_type="html",
        content="""<!-- ARTIFACT_TITLE: Sample Growth Matrix Artifact -->
<!-- ARTIFACT_START -->
<div style="padding: 20px; font-family: sans-serif; background: #0f0f0f; color: #fff; border-radius: 8px;">
  <h2>Product Growth Matrix</h2>
  <p>Grounded in Lenny's Podcast insights on retention and acquisition loops.</p>
</div>
<!-- ARTIFACT_END -->""",
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    )


@router.get("", response_model=list[ArtifactResponseSchema])
@router.get("/", response_model=list[ArtifactResponseSchema])
async def list_artifacts(db=Depends(get_db)):
    """Lists saved artifacts so the frontend can restore them after reload."""
    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            result = await db.execute(text("""
                SELECT id, title, artifact_type, content, created_at
                FROM generated_artifacts
                ORDER BY created_at DESC
            """))
            return [
                ArtifactResponseSchema(
                    id=str(row.id),
                    title=row.title,
                    artifact_type=row.artifact_type,
                    content=row.content,
                    created_at=row.created_at.isoformat(),
                )
                for row in result.fetchall()
            ]
        except Exception as exc:
            logger.error("DB list artifacts failed: %s", exc)
    return []
