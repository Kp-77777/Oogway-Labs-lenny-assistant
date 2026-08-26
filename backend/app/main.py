"""Lenny Growth Assistant — FastAPI Application Entry Point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    # --- STARTUP ---
    logger.info(f"Starting {settings.PROJECT_NAME}")
    logger.info(f"Gemini available: {settings.gemini_available}")
    logger.info(f"Ollama URL: {settings.OLLAMA_BASE_URL}")
    logger.info(f"DB available: {settings.db_available}")

    # Initialize database engine (no-op if DATABASE_URL not configured)
    from app.db.database import init_db, create_tables
    db_ok = init_db(settings.DATABASE_URL)
    if db_ok:
        await create_tables()
        logger.info("Database tables ready.")
    else:
        logger.warning("Running in no-DB mode — sessions are in-memory only.")

    # Check vector DB and auto-ingest transcripts if empty on first run
    from app.rag.ingest import check_and_auto_ingest
    await check_and_auto_ingest()

    yield

    # --- SHUTDOWN ---
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered growth assistant grounded in Lenny's Podcast transcripts.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend (localhost:3000) and any origin for Docker
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API v1 Routers ---
from app.api.v1 import health as v1_health
from app.api.v1 import sessions as v1_sessions
from app.api.v1 import messages as v1_messages
from app.api.v1 import knowledge as v1_knowledge
from app.api.v1 import models as v1_models
from app.api.v1 import artifacts as v1_artifacts
from app.api.v1 import internal_tools as v1_internal_tools

app.include_router(v1_health.router)
app.include_router(v1_sessions.router)
app.include_router(v1_messages.router)
app.include_router(v1_knowledge.router)
app.include_router(v1_models.router)
app.include_router(v1_artifacts.router)
app.include_router(v1_internal_tools.router)


from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

if FRONTEND_DIR.exists():
    css_dir = FRONTEND_DIR / "css"
    js_dir = FRONTEND_DIR / "js"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/app", response_class=FileResponse)
    def serve_frontend_app():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/")
def root():
    if FRONTEND_DIR.exists():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    return {
        "service": settings.PROJECT_NAME,
        "status": "running",
        "docs": "/docs",
        "v1_health": "/api/v1/health",
        "v1_models": "/api/v1/models",
    }
