"""v1 Knowledge API Router: GET status, POST sync, GET documents & GET documents/{document_id}"""
import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.db import database
from app.db.database import get_db
from app.rag.ingest import run_ingest, get_kb_status, get_kb_status_async

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


class DocumentMetadataSchema(BaseModel):
    id: str
    file_path: str
    content_hash: str
    episode_title: str
    guest_name: str
    source_url: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str
    chunk_count: int = 0


@router.get("/status")
async def get_knowledge_status():
    """Shows whether the knowledge base is initialized/ready and information such as document count and last sync."""
    return await get_kb_status_async()


@router.post("/sync")
async def start_knowledge_sync(background_tasks: BackgroundTasks):
    """Starts synchronization from the Lenny GitHub repository. Detects new, modified, unchanged, and deleted transcripts."""
    status = get_kb_status()
    if status.get("syncing"):
        raise HTTPException(status_code=409, detail="Knowledge base synchronization is already in progress.")

    background_tasks.add_task(run_ingest)
    return {
        "message": "Knowledge synchronization started.",
        "status_url": "/api/v1/knowledge/status"
    }


@router.get("/documents", response_model=list[DocumentMetadataSchema])
async def list_knowledge_documents(db=Depends(get_db)):
    """Lists indexed transcript documents."""
    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            res = await db.execute(text("""
                SELECT d.id, d.file_path, d.content_hash, d.episode_title, d.guest_name,
                       d.source_url, d.is_active, d.created_at, d.updated_at,
                       COUNT(c.id) AS chunk_count
                FROM knowledge_documents d
                LEFT JOIN transcript_chunks c ON c.document_id = d.id
                WHERE d.is_active = true
                GROUP BY d.id
                ORDER BY d.episode_title ASC
            """))
            rows = res.fetchall()
            return [
                DocumentMetadataSchema(
                    id=str(r.id),
                    file_path=r.file_path,
                    content_hash=r.content_hash,
                    episode_title=r.episode_title,
                    guest_name=r.guest_name,
                    source_url=r.source_url,
                    is_active=r.is_active,
                    created_at=r.created_at.isoformat(),
                    updated_at=r.updated_at.isoformat(),
                    chunk_count=r.chunk_count
                )
                for r in rows
            ]
        except Exception as e:
            logger.error(f"DB list documents failed: {e}")

    # Never show synthetic documents as Lenny Podcast sources.
    return []


@router.get("/documents/{document_id}", response_model=DocumentMetadataSchema)
async def get_knowledge_document_details(document_id: str, db=Depends(get_db)):
    """Returns metadata/details for a specific indexed transcript."""
    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            res = await db.execute(
                text("""
                    SELECT d.id, d.file_path, d.content_hash, d.episode_title, d.guest_name,
                           d.source_url, d.is_active, d.created_at, d.updated_at,
                           COUNT(c.id) AS chunk_count
                    FROM knowledge_documents d
                    LEFT JOIN transcript_chunks c ON c.document_id = d.id
                    WHERE d.id = :did OR d.file_path = :did
                    GROUP BY d.id
                """),
                {"did": document_id}
            )
            r = res.fetchone()
            if r:
                return DocumentMetadataSchema(
                    id=str(r.id),
                    file_path=r.file_path,
                    content_hash=r.content_hash,
                    episode_title=r.episode_title,
                    guest_name=r.guest_name,
                    source_url=r.source_url,
                    is_active=r.is_active,
                    created_at=r.created_at.isoformat(),
                    updated_at=r.updated_at.isoformat(),
                    chunk_count=r.chunk_count
                )
        except Exception as e:
            logger.error(f"DB get document failed: {e}")

    raise HTTPException(status_code=404, detail="Document not found")
