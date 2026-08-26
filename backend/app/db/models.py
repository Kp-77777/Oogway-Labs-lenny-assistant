"""SQLAlchemy ORM Models for the Lenny Growth Assistant.

Tables:
  - knowledge_documents: Ingested transcript files tracking content_hash, file_path & provenance
  - transcript_chunks:   RAG knowledge base (pgvector embeddings, linked to document provenance)
  - chat_sessions:       Conversation sessions
  - chat_messages:       Individual messages within a session
  - generated_artifacts: Renderable HTML/Markdown artifacts
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, JSON, Boolean
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.core.config import settings

try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None


def _now():
    return datetime.now(timezone.utc)


class KnowledgeDocument(Base):
    """Tracks canonical ingested transcript files from GitHub for incremental sync & provenance."""
    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String(500), unique=True, nullable=False, index=True)
    content_hash = Column(String(64), nullable=False)
    episode_title = Column(String(500), nullable=False)
    guest_name = Column(String(200), nullable=False)
    source_url = Column(String(1000), nullable=True)
    source_metadata = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    chunks = relationship("TranscriptChunk", back_populates="document", cascade="all, delete-orphan")


class TranscriptChunk(Base):
    """One paragraph-level chunk from a Lenny's Podcast transcript episode."""
    __tablename__ = "transcript_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    file_path = Column(String(500), nullable=True, index=True)
    episode_title = Column(String(500), nullable=False, index=True)
    guest_name = Column(String(200), nullable=False, index=True)
    episode_url = Column(String(1000), nullable=True)
    source_metadata = Column(JSONB, nullable=False, default=dict)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)

    if PGVECTOR_AVAILABLE:
        embedding = Column(Vector(settings.VECTOR_DIMENSIONS), nullable=True)

    document = relationship("KnowledgeDocument", back_populates="chunks")


class ChatSession(Base):
    """A single user conversation session."""
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=True)
    provider = Column(String(50), nullable=False, default="cloud")
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        order_by="ChatMessage.created_at",
        cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    """A single message (user or assistant) within a chat session."""
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True, default=list)
    response_type = Column(String(30), nullable=True, default="answer")
    created_at = Column(DateTime(timezone=True), default=_now)

    session = relationship("ChatSession", back_populates="messages")


class GeneratedArtifact(Base):
    """Stores generated Markdown or HTML artifacts for the Artifact Viewer."""
    __tablename__ = "generated_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    artifact_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
