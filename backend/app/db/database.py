"""Async SQLAlchemy database engine and session factory.

Falls back gracefully when DATABASE_URL is not configured — the app
runs in no-DB mode (in-memory sessions, no RAG persistence).
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


# Module-level engine/session — initialized at startup
_engine = None
_async_session_factory = None
DB_AVAILABLE = False


def init_db(database_url: str) -> bool:
    """Initialize the async engine. Returns True if successful."""
    global _engine, _async_session_factory, DB_AVAILABLE

    if not database_url or "YOUR" in database_url:
        logger.warning(
            "DATABASE_URL not configured — running in no-DB mode. "
            "Sessions will be in-memory only and reset on restart."
        )
        DB_AVAILABLE = False
        return False

    try:
        # Convert postgresql:// → postgresql+asyncpg://
        async_url = database_url.replace(
            "postgresql://", "postgresql+asyncpg://"
        ).replace(
            "postgres://", "postgresql+asyncpg://"
        )

        _engine = create_async_engine(
            async_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        _async_session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        DB_AVAILABLE = True
        logger.info("Database engine initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        DB_AVAILABLE = False
        return False


def get_session_factory():
    """Returns the async sessionmaker, auto-initializing if needed."""
    global _async_session_factory
    if _async_session_factory is None and settings.db_available:
        init_db(settings.DATABASE_URL)
    return _async_session_factory


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    if not DB_AVAILABLE or _async_session_factory is None:
        yield None
        return

    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables():
    """Create all tables (called at startup if DB is available)."""
    if not DB_AVAILABLE or _engine is None:
        return

    # Import models to register them with Base metadata
    from app.db import models  # noqa: F401

    async with _engine.begin() as conn:
        # Enable pgvector extension first
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        from app.db.database import Base
        await conn.run_sync(Base.metadata.create_all)
        # ``create_all`` does not alter existing Supabase tables. These additions are
        # backward-compatible and preserve rich transcript provenance for retrieval.
        await conn.execute(__import__("sqlalchemy").text("""
            ALTER TABLE knowledge_documents
            ADD COLUMN IF NOT EXISTS source_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        """))
        await conn.execute(__import__("sqlalchemy").text("""
            ALTER TABLE transcript_chunks
            ADD COLUMN IF NOT EXISTS source_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        """))
        await conn.execute(__import__("sqlalchemy").text("""
            CREATE INDEX IF NOT EXISTS transcript_chunks_full_text_idx
            ON transcript_chunks
            USING GIN (to_tsvector(
                'english',
                coalesce(episode_title, '') || ' ' || coalesce(guest_name, '') || ' ' || coalesce(chunk_text, '')
            ))
        """))

    logger.info("Database tables created/verified.")
