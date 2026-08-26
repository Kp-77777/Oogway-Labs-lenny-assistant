# Lenny Growth Assistant

A grounded assistant for product-management and growth questions. It retrieves
evidence from Lenny's Podcast transcripts using the Python/LangChain RAG layer,
then sends that evidence to a project-local Node Pi Agent for response
orchestration. It supports Gemini and a local Ollama model.

## Evaluator quick start (Docker)

This is the supported evaluation path. You need Docker Desktop, Docker Compose,
an internet connection for the first Ollama-model download, and a Gemini API key
for the default cloud chat provider and semantic embeddings.

1. Clone the repository and create your environment file.

   ```bash
   git clone <repository-url>
   cd oogwayylabs
   cp .env.example .env
   ```

   On Windows PowerShell, use:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Edit `.env` and set at least:

   ```env
   GEMINI_API_KEY="your-real-key"
   ```

   Leave `DATABASE_URL=""` to use the included PostgreSQL + pgvector
   container. Keep `OLLAMA_MODEL="llama3.1:8b"` unless you intentionally want
   another locally supported model.

3. Build and start everything.

   ```bash
   docker compose up --build
   ```

4. Open the application at <http://localhost:3000>.

   Useful checks:

   ```bash
   curl http://localhost:8000/api/v1/health
   curl http://localhost:8000/api/v1/health/ready
   ```

The first startup is slow because Docker downloads the Ollama image/model and
the backend starts transcript ingestion. The app can open before ingestion
finishes, but transcript-grounded answers are available only after the knowledge
base has indexed relevant content. Monitor it with:

```bash
docker compose logs -f backend
curl http://localhost:8000/api/v1/knowledge/status
```

To stop the stack while preserving the database and model cache:

```bash
docker compose down
```

Do not use `docker compose down -v` unless you deliberately want to delete the
local PostgreSQL data and downloaded Ollama models.

## Local development (without Docker)

This is the intended workflow for the project owner. Ollama must be installed
and running on the computer; Pi dependencies remain inside `pi_agent/` and are
never installed globally.

Prerequisites:

- Python 3.12 and a virtual environment at `venv/`
- Node.js 22.19 or later (the repository includes a Windows Node binary fallback)
- Ollama running at `http://localhost:11434`
- A PostgreSQL/pgvector database configured in `.env` if persistent RAG and
  sessions are required

Initial setup:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
Set-Location pi_agent
npm ci
Set-Location ..
```

Copy `.env.example` to `.env`, then configure `DATABASE_URL`, `GEMINI_API_KEY`,
and any desired models. Start Ollama separately, for example:

```powershell
ollama serve
```

In another PowerShell window, start the application:

```powershell
.\scripts\start-dev.ps1
```

The launcher starts the project-local Pi service, waits for its health endpoint,
then starts FastAPI at <http://127.0.0.1:8000>. Serve the static `frontend/`
directory with any static web server, or open it through the Docker frontend
when evaluating the complete stack.

## Configuration

All runtime settings are in `.env`; `.env.example` is the complete template.

| Setting | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Required for Gemini chat and Gemini embeddings. |
| `GEMINI_CHAT_MODEL` | Cloud model used when the UI selects Cloud. |
| `GEMINI_EMBED_MODEL` / `VECTOR_DIMENSIONS` | Must remain compatible; default is `gemini-embedding-001` and `3072`. |
| `OLLAMA_MODEL` | Local model used when the UI selects Ollama. |
| `DATABASE_URL` | Leave blank for Docker PostgreSQL; set it for a local/Supabase database. |
| `INGEST_MAX_EPISODES` | `0` indexes all source transcripts; use a small number only for development. |
| `RAG_SIMILARITY_THRESHOLD` | Minimum retrieval score; raise for stricter evidence, lower for broader recall. |
| `PI_AGENT_PORT` / `PI_AGENT_URL` | Local Pi Agent service address. |

## Architecture and behavior

```text
Browser → Frontend → FastAPI → Pi Agent → Gemini or Ollama
                         │
                         └→ LangChain RAG → PostgreSQL + pgvector
```

- RAG retrieval is performed before grounded product/growth answers, Ship30
  essays, and factual artifacts.
- When no relevant transcript evidence is found, the assistant states that the
  available transcripts do not directly support the answer.
- The Pi Agent dependencies are locked in `pi_agent/package-lock.json` and are
  installed locally with `npm ci` or inside the evaluator Docker image.
- Chat sessions and generated artifacts are persisted only when `DATABASE_URL`
  points to a reachable database.

## Verification

Run the included unit tests from the repository root:

```powershell
Set-Location backend
..\venv\Scripts\python.exe -m pytest tests -q
```

These tests cover API basics and transcript parsing. They do not replace a live
end-to-end check with your selected database, LLM provider, and transcript sync.
