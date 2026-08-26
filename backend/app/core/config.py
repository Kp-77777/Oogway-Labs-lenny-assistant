"""Application configuration with environment overrides and safe defaults."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Locate project root and load .env into os.environ
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE, override=True)
else:
    load_dotenv(dotenv_path=".env", override=True)


class Settings:
    """Configuration values may be overridden through environment variables."""

    # --- Application ---
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "The Lenny Growth Assistant")
    PORT: int = int(os.getenv("PORT", "8000"))

    # --- Database (Supabase PostgreSQL + pgvector) ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

    # --- Gemini LLM ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_CHAT_MODEL: str = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
    GEMINI_CHAT_FALLBACK_MODELS: str = os.getenv("GEMINI_CHAT_FALLBACK_MODELS", "")
    GEMINI_EMBED_MODEL: str = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    # Comma-separated fallback embedding models tried in order if primary returns 404
    GEMINI_EMBED_FALLBACK_MODELS: str = os.getenv("GEMINI_EMBED_FALLBACK_MODELS", "")

    # --- Ollama LLM ---
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    # --- RAG / Knowledge Base ---
    TRANSCRIPTS_GITHUB_REPO: str = os.getenv("TRANSCRIPTS_GITHUB_REPO", "ChatPRD/lennys-podcast-transcripts")
    TRANSCRIPTS_GITHUB_PATH: str = os.getenv("TRANSCRIPTS_GITHUB_PATH", "episodes")
    TRANSCRIPTS_GITHUB_BRANCH: str = os.getenv("TRANSCRIPTS_GITHUB_BRANCH", "main")
    # 0 means sync the full repository. Use a positive value only for local development.
    INGEST_MAX_EPISODES: int = int(os.getenv("INGEST_MAX_EPISODES", "0"))
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "6"))
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.55"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    # Embedding vector dimensions — must match the model output:
    #   gemini-embedding-001 = 3072, text-embedding-004 = 768
    VECTOR_DIMENSIONS: int = int(os.getenv("VECTOR_DIMENSIONS", "3072"))

    @property
    def gemini_embed_model_candidates(self) -> list[str]:
        """Ordered list of Gemini embedding models: primary first, then fallbacks.
        All model names come from .env — no hardcoding here.
        """
        primary = [self.GEMINI_EMBED_MODEL] if self.GEMINI_EMBED_MODEL else []
        fallbacks = (
            [m.strip() for m in self.GEMINI_EMBED_FALLBACK_MODELS.split(",") if m.strip()]
            if self.GEMINI_EMBED_FALLBACK_MODELS
            else []
        )
        candidates = primary + fallbacks
        seen: set = set()
        return [m for m in candidates if not (m in seen or seen.add(m))]

    @property
    def db_available(self) -> bool:
        return bool(
            self.DATABASE_URL
            and "YOUR" not in self.DATABASE_URL
            and "[PASSWORD]" not in self.DATABASE_URL
            and "[REF]" not in self.DATABASE_URL
            and "[YOUR-PROJECT-REF]" not in self.DATABASE_URL
        )

    @property
    def gemini_available(self) -> bool:
        return bool(
            self.GEMINI_API_KEY
            and "YOUR" not in self.GEMINI_API_KEY
            and "your-gemini-api-key" not in self.GEMINI_API_KEY
        )

    @property
    def ollama_available(self) -> bool:
        return bool(self.OLLAMA_BASE_URL)


settings = Settings()
