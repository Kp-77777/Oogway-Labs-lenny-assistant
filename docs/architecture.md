# System Architecture Specification — The Lenny Growth Assistant (`architecture.md`)

## 1. Overview & Deployment Topology

**The Lenny Growth Assistant** is built as a containerized, 3-tier hybrid LLM architecture combining FastAPI, Node.js, PostgreSQL with `pgvector`, and dual LLM providers (Cloud Gemini + Local Ollama).

```
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 │                           DOCKER HOST (OOGWAYYLABS)                             │
 │                                                                                 │
 │   ┌───────────────────────┐                    ┌────────────────────────────┐   │
 │   │ Frontend (Nginx:80)   │                    │ Backend (FastAPI:8000)     │   │
 │   │ Port 3000 -> 80       │                    │ Port 8000 -> 8000          │   │
 │   └───────────┬───────────┘                    └─────────────┬──────────────┘   │
 │               │                                              │                  │
 │               └──────────────────────┬───────────────────────┘                  │
 │                                      │                                          │
 │               ┌──────────────────────┴──────────────────────┐                   │
 │               ▼                                             ▼                   │
 │   ┌───────────────────────┐                    ┌────────────────────────────┐   │
 │   │ Pi Agent Runtime      │                    │ Database Layer             │   │
 │   │ (Node.js:8001 Internal)│                    │ (Supabase Cloud OR         │   │
 │   └───────────┬───────────┘                    │ Local Postgres pgvector)   │   │
 │               │                                └────────────────────────────┘   │
 │        ┌──────┴──────┐                                                          │
 │        ▼             ▼                                                          │
 │  ┌───────────┐ ┌───────────┐                                                    │
 │  │ Cloud     │ │ Ollama    │                                                    │
 │  │ Gemini API│ │ (11434)   │                                                    │
 │  └───────────┘ └───────────┘                                                    │
 └─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Boundaries & Responsibilities

1. **Frontend (`frontend/`)**: Nginx web server hosting HTML5/CSS3/JavaScript static assets. Provides chat interface, provider controls, citation popovers, and artifact rendering.
2. **FastAPI Backend (`backend/app/`)**: Python 3.12 REST API providing session lifecycle management, transcript ingestion endpoints, database management, and HTTP client bridges.
3. **Pi Agent Orchestrator (`pi_agent/agent_service.js`)**: Persistent Node.js HTTP service running on port 8001. Manages LLM message formatting, prompt grounding policies, system instructions, and tool RPC.
4. **Vector Database**: PostgreSQL with `pgvector` extension storing chunked transcripts and embeddings. Supports local Docker (`pgvector/pgvector:pg16-latest`) or remote **Supabase PostgreSQL Cloud**.
5. **LLM Runtime Engine**:
   - **Cloud LLM**: Google Gemini API (`gemini-3.6-flash` / `gemini-2.0-flash`).
   - **Local LLM**: Ollama service (`llama3.1:8b` via `http://ollama:11434` or `http://localhost:11434`).

---

## 3. Database Schema (`postgresql+pgvector`)

### `knowledge_documents`
Tracks canonical ingested transcript files from GitHub.

```sql
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path VARCHAR(500) UNIQUE NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    episode_title VARCHAR(500) NOT NULL,
    guest_name VARCHAR(200) NOT NULL,
    source_url VARCHAR(1000),
    source_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### `transcript_chunks`
Stores paragraph-level chunks with 3072-dimensional vector embeddings and GIN full-text index.

```sql
CREATE TABLE transcript_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    file_path VARCHAR(500),
    episode_title VARCHAR(500) NOT NULL,
    guest_name VARCHAR(200) NOT NULL,
    episode_url VARCHAR(1000),
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    source_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(3072), -- Fixed 3072-dim vector for gemini-embedding-001
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- GIN Full-Text Index for Hybrid Keyword Search
CREATE INDEX transcript_chunks_full_text_idx ON transcript_chunks
USING GIN (to_tsvector('english', coalesce(episode_title, '') || ' ' || coalesce(guest_name, '') || ' ' || coalesce(chunk_text, '')));
```

### `chat_sessions`, `chat_messages`, `generated_artifacts`

```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(300),
    provider VARCHAR(50) NOT NULL DEFAULT 'cloud',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]'::jsonb,
    response_type VARCHAR(30) DEFAULT 'answer',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE generated_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    artifact_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. Ingestion & RAG Retrieval Flow

### A. Ingestion Pipeline (`backend/app/rag/ingest.py`)
1. **GitHub Discovery**: Discovers transcript files (`episodes/<slug>/transcript.md`) from `ChatPRD/lennys-podcast-transcripts`.
2. **Parsing & Chunking**: Extracts YAML frontmatter, timestamps, and speaker turns. Chunks body text into ~1500 character blocks (`CHUNK_SIZE=1500`, `CHUNK_OVERLAP=150`).
3. **Embedding Generation**: Batch embeds chunk texts via Google Gemini Embeddings (`gemini-embedding-001`, **3072 dimensions**).
4. **Database Upsert**: Performs atomic transactions writing documents to `knowledge_documents` and chunk vectors to `transcript_chunks`.

### B. Hybrid Retrieval Flow (`backend/app/rag/retriever.py`)
1. **Query Embedding**: Embeds user query using `gemini-embedding-001` (3072-dim).
2. **Hybrid Scoring**: Executes SQL hybrid rank combining vector distance and full-text keyword ranking:
   $$\text{Score} = 0.90 \times (1 - (\text{embedding} \Leftrightarrow \text{query\_vec})) + 0.10 \times \text{ts\_rank\_cd}(\dots)$$
3. **Fallback**: If embeddings are temporarily unavailable, falls back to GIN full-text search (`_db_keyword_search`).

---

## 5. Agent Routing & Model Toggle

```
[User Prompts]
      │
      ▼
[FastAPI /messages POST] ──► Reads active provider state (_active_model_state)
                                       │
                                       ▼
                       [HTTP POST to Pi Agent :8001/chat]
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
     provider == "cloud"                           provider == "ollama"
                │                                             │
      Call Google Gemini API                       Call Local Ollama API
   (gemini-3.6-flash / 2.0-flash)                    (llama3.1:8b)
```

---

## 6. Internal API & External Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/health` | `GET` | Health check & system status |
| `/api/v1/models` | `GET` | Catalog of available LLM providers |
| `/api/v1/models/current` | `GET/PUT` | Read or update active LLM provider selection |
| `/api/v1/sessions` | `GET/POST` | List or create conversation sessions |
| `/api/v1/sessions/{id}/messages` | `GET/POST` | Fetch history or post new grounded prompt |
| `/api/v1/artifacts` | `GET` | Retrieve saved HTML/Markdown artifacts |
| `/api/v1/internal/tools/search_knowledge` | `POST` | Internal tool: search RAG vector store |
| `/api/v1/internal/tools/ship30_skill` | `POST` | Internal tool: generate Ship 30 essay framework |
| `/api/v1/internal/tools/create_artifact` | `POST` | Internal tool: format HTML/Markdown artifacts |

---

## 7. Security & Network Isolation Notes

- **Docker Bridge Network**: All container-to-container communication (`backend` <-> `ollama`, `backend` <-> `postgres`, `backend` <-> `pi_agent`) occurs isolated on the internal `oogwayylabs-net` bridge network.
- **API CORS**: Configured in [`main.py`](file:///d:/projects/oogwayylabs/backend/app/main.py) to enable local browser communication while serving frontend static files via Nginx.
