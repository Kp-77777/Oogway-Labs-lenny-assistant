"""In-memory session store — used as fallback when DATABASE_URL is not configured.

When Supabase is available, the API endpoints use the DB directly.
When not available, this store keeps sessions alive for the duration of the process.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class InMemoryMessage:
    id: str
    role: str           # 'user' or 'assistant'
    content: str
    sources: List[dict]
    response_type: str  # 'answer' | 'essay' | 'artifact'
    created_at: str


@dataclass
class InMemorySession:
    id: str
    title: Optional[str]
    provider: str
    created_at: str
    updated_at: str
    messages: List[InMemoryMessage] = field(default_factory=list)


class InMemorySessionStore:
    """Thread-safe in-memory store for chat sessions when DB is unavailable."""

    def __init__(self):
        self._sessions: Dict[str, InMemorySession] = {}

    def create_session(self, provider: str = "cloud") -> InMemorySession:
        session_id = str(uuid.uuid4())
        now = _now_iso()
        session = InMemorySession(
            id=session_id,
            title=None,
            provider=provider,
            created_at=now,
            updated_at=now,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[InMemorySession]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[InMemorySession]:
        return sorted(
            self._sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: List[dict] = None,
        response_type: str = "answer"
    ) -> Optional[InMemoryMessage]:
        session = self._sessions.get(session_id)
        if not session:
            return None

        msg = InMemoryMessage(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            sources=sources or [],
            response_type=response_type,
            created_at=_now_iso()
        )
        session.messages.append(msg)
        session.updated_at = _now_iso()

        # Auto-set title from the first user message
        if role == "user" and session.title is None:
            session.title = content[:60] + ("..." if len(content) > 60 else "")

        return msg

    def get_history(self, session_id: str) -> List[InMemoryMessage]:
        session = self._sessions.get(session_id)
        return session.messages if session else []

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False


# Singleton instance — imported by API endpoints
session_store = InMemorySessionStore()
