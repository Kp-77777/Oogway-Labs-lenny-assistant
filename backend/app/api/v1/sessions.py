"""v1 Sessions API Router: POST /api/v1/sessions, GET /api/v1/sessions, GET/DELETE /api/v1/sessions/{session_id}"""
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db import database
from app.db.database import get_db
from app.core.sessions import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    provider: str = Field(default="cloud", pattern="^(cloud|ollama)$")
    title: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    title: Optional[str]
    provider: str
    created_at: str
    updated_at: str
    message_count: int = 0


@router.post("", response_model=SessionResponse)
@router.post("/", response_model=SessionResponse)
async def create_session(body: CreateSessionRequest, db=Depends(get_db)):
    """Creates a new independent chat session."""
    session_id = str(uuid.uuid4())
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()

    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            await db.execute(
                text("INSERT INTO chat_sessions (id, title, provider, created_at, updated_at) VALUES (:id, :title, :provider, NOW(), NOW())"),
                {"id": session_id, "title": body.title, "provider": body.provider}
            )
            return SessionResponse(
                session_id=session_id,
                title=body.title,
                provider=body.provider,
                created_at=now,
                updated_at=now,
                message_count=0
            )
        except Exception as e:
            logger.warning(f"DB session create failed, using memory fallback: {e}")

    s = session_store.create_session(body.provider)
    if body.title:
        s.title = body.title

    return SessionResponse(
        session_id=s.id,
        title=s.title,
        provider=s.provider,
        created_at=s.created_at,
        updated_at=s.updated_at,
        message_count=len(s.messages)
    )


@router.get("", response_model=list[SessionResponse])
@router.get("/", response_model=list[SessionResponse])
async def list_sessions(db=Depends(get_db)):
    """Returns previous sessions for the sidebar."""
    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            res = await db.execute(text("""
                SELECT s.id, s.title, s.provider, s.created_at, s.updated_at,
                       COUNT(m.id) as msg_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON m.session_id = s.id
                GROUP BY s.id
                ORDER BY s.updated_at DESC
            """))
            rows = res.fetchall()
            return [
                SessionResponse(
                    session_id=str(r.id),
                    title=r.title,
                    provider=r.provider,
                    created_at=r.created_at.isoformat(),
                    updated_at=r.updated_at.isoformat(),
                    message_count=r.msg_count
                )
                for r in rows
            ]
        except Exception as e:
            logger.error(f"DB session list failed: {e}")

    sessions = session_store.list_sessions()
    return [
        SessionResponse(
            session_id=s.id,
            title=s.title,
            provider=s.provider,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=len(s.messages)
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_details(session_id: str, db=Depends(get_db)):
    """Returns information about a specific session."""
    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            res = await db.execute(
                text("""
                    SELECT s.id, s.title, s.provider, s.created_at, s.updated_at,
                           COUNT(m.id) as msg_count
                    FROM chat_sessions s
                    LEFT JOIN chat_messages m ON m.session_id = s.id
                    WHERE s.id = :sid
                    GROUP BY s.id
                """),
                {"sid": session_id}
            )
            r = res.fetchone()
            if r:
                return SessionResponse(
                    session_id=str(r.id),
                    title=r.title,
                    provider=r.provider,
                    created_at=r.created_at.isoformat(),
                    updated_at=r.updated_at.isoformat(),
                    message_count=r.msg_count
                )
        except Exception as e:
            logger.error(f"DB session get failed: {e}")

    s = session_store.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=s.id,
        title=s.title,
        provider=s.provider,
        created_at=s.created_at,
        updated_at=s.updated_at,
        message_count=len(s.messages)
    )


@router.delete("/{session_id}")
async def delete_session(session_id: str, db=Depends(get_db)):
    """Deletes a chat session and its associated data."""
    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            await db.execute(text("DELETE FROM chat_sessions WHERE id = :sid"), {"sid": session_id})
            return {"deleted": True, "session_id": session_id}
        except Exception as e:
            logger.error(f"DB session delete failed: {e}")

    deleted = session_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True, "session_id": session_id}
