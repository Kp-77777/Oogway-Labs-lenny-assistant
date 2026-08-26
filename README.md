# The Lenny Growth Assistant (`oogwayylabs`)

**A production-ready, grounded AI assistant that answers product management and growth questions using Lenny's Podcast transcripts.**

The system combines a hybrid multi-LLM runtime (Cloud Gemini 3.6 Flash + Local Ollama `llama3.1:8b`), a persistent PostgreSQL `pgvector` knowledge base (Supabase Cloud or local Docker container), and a persistent Node.js Pi Agent orchestrator.

---

## 📚 Documentation Sitemap

Detailed specifications and architectural guides are available in the repository:

- 📄 [**Product Requirement Document (PRD)**](docs/prd.md): User personas, problem statement, success metrics, product scope, and acceptance criteria.
- 🎨 [**Design Specification**](docs/design.md): UI/UX design principles, information architecture, interaction states, responsive layouts, and accessibility.
- 🏗️ [**Architecture Specification**](docs/architecture.md): Complete database schema, API endpoints, component boundaries, RAG retrieval pipeline, model toggle, and deployment topology.
- 🤖 [**Agent Specification (AGENT.md)**](agent-transcripts/AGENT.md): Detailed description of Pi Agent runtime, tool RPC interfaces, single 3072-dimension vector embedding contracts, and active model state switching.

---

## ⚡ Quick Start — One-Command Docker Setup

The entire system is containerized for seamless evaluation with **one command**:

### 1. Clone & Set Environment

```bash
git clone https://github.com/your-org/oogwayylabs.git
cd oogwayylabs

# Copy environment template
cp .env.example .env
```

Ensure `.env` contains your Gemini API key:
```env
GEMINI_API_KEY="your-gemini-api-key-here"
```

### 2. Launch Container Environment

```bash
docker compose up --build
```

Access the application in your browser once startup completes:
- 🌐 **Frontend Application**: [http://localhost:3000](http://localhost:3000)
- ⚙️ **FastAPI Backend Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🤖 **Pi Agent Service**: Port 8001 (internal container service)
- 🦙 **Ollama Service**: Port 11434 (`llama3.1:8b` auto-downloaded on launch)

---

## 🏗️ Architecture Overview

```
User's Browser (http://localhost:3000)
    │
    ▼
[Frontend] Nginx (React UI / HTML5 / CSS3)
    │
    ▼
[Backend] FastAPI (Python 3.12, Port 8000)
    ├─► [Pi Agent] Persistent Node.js service (Port 8001 internal)
    ├─► [Database] PostgreSQL + pgvector (Supabase Cloud OR Local Docker)
    └─► [LLM Runtime] Cloud Gemini 3.6 Flash OR Local Ollama (llama3.1:8b)
```

### Core Services Summary

| Service | Type | Purpose | Setup |
|---------|------|---------|-------|
| **Gemini 3.6 Flash** | Cloud LLM | Primary chat & 3072-dim embeddings | Free API key from Google AI Studio |
| **Ollama (llama3.1:8b)** | Local LLM | Privacy-first local LLM alternative | Auto-downloaded and run inside Docker container |
| **PostgreSQL + pgvector** | Vector Database | Stores transcript chunks, chat sessions & artifacts | Connects to Cloud Supabase (default in `.env`) or local Docker pgvector |
| **Pi Agent** | Orchestrator | Handles turn-taking, prompt grounding, and tool execution | Built-in Node.js runtime inside backend container |

---

## 🔑 Key Features & Technical Decisions

### 1. Strict 3072-Dimension Embedding Contract
- The system uses Google Gemini Embeddings (`gemini-embedding-001`) with exactly **3072 dimensions**.
- Mismatched 768-dim fallback models (`GEMINI_EMBED_FALLBACK_MODELS=""`) are disabled in `.env` and `config.py` to prevent vector dimension mismatch errors against the PostgreSQL `vector(3072)` column schema.

### 2. Active Model Switching
- Users can switch between **Cloud Gemini** and **Local Ollama** seamlessly using the UI model switcher.
- Switching updates the active provider state via `PUT /api/v1/models/current`, and all subsequent chat requests inherit the active provider selection automatically.

### 3. Grounded RAG Retrieval
- Ingests canonical markdown files from GitHub (`ChatPRD/lennys-podcast-transcripts`).
- Computes hybrid similarity scores combining cosine vector distance and PostgreSQL GIN full-text keyword ranking.
- All factual claims include source citations formatted as `[Episode: Guest Name - Episode Title]` with direct links to transcript lines.

### 4. Interactive Artifact Builder
- Complex frameworks, HTML calculators, matrix cards, and 1,250-word Ship 30 essays open in a dedicated side-by-side **Artifact Panel** for rich inspection.

---

## ⚙️ Environment Variables Reference

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `PROJECT_NAME` | `The Lenny Growth Assistant` | Application display name |
| `PORT` | `8000` | FastAPI server port |
| `DATABASE_URL` | Supabase URI | PostgreSQL connection string (Supabase Cloud or local Docker) |
| `GEMINI_API_KEY` | *(Required)* | Google Gemini API key |
| `GEMINI_CHAT_MODEL` | `gemini-3.6-flash` | Primary cloud chat LLM |
| `GEMINI_EMBED_MODEL` | `gemini-embedding-001` | Primary vector embedding model (3072 dimensions) |
| `GEMINI_EMBED_FALLBACK_MODELS` | `""` | Disabled to maintain 3072-dim vector contract |
| `VECTOR_DIMENSIONS` | `3072` | Embedding vector column dimensions |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama service URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | Local Ollama model name |

---

## 🧪 Testing & System Diagnostics

To run system health checks and configuration verification:

```bash
# Verify Gemini configuration (no hardcoded fallbacks, 3072-dim setup)
python test_gemini_config.py

# Run system integration test suite
venv/Scripts/python.exe backend/test_system.py
```
