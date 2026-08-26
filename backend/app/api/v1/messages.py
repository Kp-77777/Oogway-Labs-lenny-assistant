"""v1 Messages API Router: GET & POST /api/v1/sessions/{session_id}/messages"""
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db import database
from app.db.database import get_db
from app.core.sessions import session_store
from app.agent.engine import agent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["messages"])


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    provider: Optional[str] = Field(default="cloud")


class SourceCitationSchema(BaseModel):
    episode: str
    guest: str
    url: str
    excerpt: str


class MessageResponseSchema(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    response_type: str
    sources: list[SourceCitationSchema]
    artifact_id: Optional[str] = None
    artifact_title: Optional[str] = None
    artifact_html: Optional[str] = None
    provider: str
    model: str
    created_at: str


class HistoryMessageSchema(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    sources: list
    response_type: str
    created_at: str


async def _save_artifact_to_db(title: str, artifact_type: str, content: str, db) -> str:
    """Save generated artifact to DB or memory and return artifact_id."""
    art_id = str(uuid.uuid4())
    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            await db.execute(
                text("""
                    INSERT INTO generated_artifacts (id, title, artifact_type, content, created_at)
                    VALUES (:id, :title, :type, :content, NOW())
                """),
                {"id": art_id, "title": title, "type": artifact_type, "content": content}
            )
        except Exception as e:
            logger.error(f"Failed to save artifact to DB: {e}")
    return art_id


@router.get("/{session_id}/messages", response_model=list[HistoryMessageSchema])
async def get_session_messages(session_id: str, db=Depends(get_db)):
    """Loads stored conversation history from Supabase or memory."""
    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            res = await db.execute(
                text("SELECT id, session_id, role, content, sources, response_type, created_at FROM chat_messages WHERE session_id = :sid ORDER BY created_at ASC"),
                {"sid": session_id}
            )
            rows = res.fetchall()
            return [
                HistoryMessageSchema(
                    id=str(r.id),
                    session_id=str(r.session_id),
                    role=r.role,
                    content=r.content,
                    sources=r.sources or [],
                    response_type=r.response_type or "answer",
                    created_at=r.created_at.isoformat()
                )
                for r in rows
            ]
        except Exception as e:
            logger.error(f"DB messages fetch failed: {e}")

    msgs = session_store.get_history(session_id)
    return [
        HistoryMessageSchema(
            id=m.id,
            session_id=session_id,
            role=m.role,
            content=m.content,
            sources=m.sources,
            response_type=m.response_type,
            created_at=m.created_at
        )
        for m in msgs
    ]


@router.post("/{session_id}/messages", response_model=MessageResponseSchema)
async def post_session_message(session_id: str, body: SendMessageRequest, db=Depends(get_db)):
    """Sends a user message → Agent → RAG/tools/model → stores the response → returns the response."""
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()

    # Never run an expensive agent request for a session that does not exist.
    if database.DB_AVAILABLE and db is not None:
        from sqlalchemy import text
        exists = await db.execute(text("SELECT 1 FROM chat_sessions WHERE id = :sid"), {"sid": session_id})
        if exists.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Session not found")
    elif session_store.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Fetch history
    history = []
    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            res = await db.execute(
                text("SELECT role, content FROM chat_messages WHERE session_id = :sid ORDER BY created_at ASC"),
                {"sid": session_id}
            )
            history = [{"role": r.role, "content": r.content} for r in res.fetchall()]
        except Exception:
            pass
    if not history:
        msgs = session_store.get_history(session_id)
        history = [{"role": m.role, "content": m.content} for m in msgs]

    # 2. Persist user message
    user_msg_id = str(uuid.uuid4())
    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            await db.execute(
                text("""
                    INSERT INTO chat_messages (id, session_id, role, content, sources, response_type, created_at)
                    VALUES (:id, :sid, 'user', :content, '[]'::jsonb, 'answer', NOW())
                """),
                {"id": user_msg_id, "sid": session_id, "content": body.message}
            )
            title = body.message[:60] + ("..." if len(body.message) > 60 else "")
            await db.execute(
                text("UPDATE chat_sessions SET title = COALESCE(title, :title), updated_at = NOW() WHERE id = :sid"),
                {"title": title, "sid": session_id}
            )
        except Exception as e:
            logger.error(f"DB user message persist failed: {e}")
    else:
        session_store.add_message(session_id, "user", body.message, [], "answer")

    from app.api.v1.models import _active_model_state

    # 3. Run Agent Pipeline (RAG search -> Tool execution -> LLM call)
    active_provider = body.provider if body.provider else _active_model_state.get("provider", "cloud")
    result = await agent.run(
        user_message=body.message,
        provider=active_provider,
        history=history
    )

    # 4. Save artifact if generated
    artifact_id = None
    if result.get("artifact_html"):
        artifact_id = await _save_artifact_to_db(
            title=result.get("artifact_title") or "Generated Artifact",
            artifact_type=result.get("artifact_type") or "html",
            content=result["artifact_html"],
            db=db
        )

    # 5. Persist assistant message
    asst_msg_id = str(uuid.uuid4())
    if database.DB_AVAILABLE and db is not None:
        try:
            from sqlalchemy import text
            await db.execute(
                text("""
                    INSERT INTO chat_messages (id, session_id, role, content, sources, response_type, created_at)
                    VALUES (:id, :sid, 'assistant', :content, CAST(:sources AS jsonb), :rtype, NOW())
                """),
                {
                    "id": asst_msg_id,
                    "sid": session_id,
                    "content": result["response"],
                    "sources": __import__("json").dumps(result["sources"]),
                    "rtype": result["response_type"]
                }
            )
        except Exception as e:
            logger.error(f"DB assistant message persist failed: {e}")
    else:
        session_store.add_message(
            session_id,
            "assistant",
            result["response"],
            result["sources"],
            result["response_type"]
        )

    return MessageResponseSchema(
        id=asst_msg_id,
        session_id=session_id,
        role="assistant",
        content=result["response"],
        response_type=result["response_type"],
        sources=[SourceCitationSchema(**s) for s in result["sources"]],
        artifact_id=artifact_id,
        artifact_title=result.get("artifact_title"),
        artifact_html=result.get("artifact_html"),
        provider=result["provider"],
        model=result["model"],
        created_at=now
    )
