# The Lenny Growth Assistant — Agent & System Architecture (`AGENT.md`)

This document provides a verified, technical description of **The Lenny Growth Assistant** system, architecture, multi-LLM orchestration, RAG retrieval engine, and tool contracts.

---

## 1. System Architecture Overview

The system operates as a containerized, 3-tier hybrid LLM platform:

```
                  ┌─────────────────────────────────────┐
                  │ User Browser (http://localhost:3000) │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                   ┌──────────────────────────────────┐
                   │   Frontend (Nginx / Static Web)  │
                   └─────────────────┬────────────────┘
                                     │
                                     ▼
                   ┌──────────────────────────────────┐
                   │    Backend API (FastAPI:8000)    │
                   └──────┬────────────────────┬──────┘
                          │                    │
                          ▼                    ▼
   ┌──────────────────────────────┐    ┌──────────────────────────────┐
   │ Persistent Pi Agent (Node.js)│    │ PostgreSQL + pgvector (5432) │
   │ Port 8001 (Internal RPC)     │    │ Transcripts & Chat Storage   │
   └──────────────┬───────────────┘    └──────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│ Google Gemini │   │ Local Ollama  │
│ (Cloud LLM)   │   │ (Port 11434)  │
└───────────────┘   └───────────────┘
```

---

## 2. Verified Technical Specifications

### A. Embedding & Vector Database Contract
- **Embedding Model**: Fixed to Google Gemini Embeddings (`gemini-embedding-001`).
- **Vector Dimension**: Exactly **3072 dimensions**.
- **Dimension Consistency**: Fallback models (`GEMINI_EMBED_FALLBACK_MODELS=""`) are disabled to prevent dimension mismatch errors against the PostgreSQL `vector(3072)` column schema.
- **Retrieval Strategy**: Hybrid retrieval using cosine similarity (`1 - (embedding <=> query_vec)`) combined with PostgreSQL full-text search (`ts_rank_cd`).

### B. Multi-LLM Provider Switching
- **Supported Providers**:
  1. `cloud`: Primary model `gemini-3.6-flash` (or `gemini-2.0-flash` with fallbacks).
  2. `ollama`: Local model (e.g. `llama3.1:8b` via `http://localhost:11434` or `http://ollama:11434`).
- **Active State Switching**: Updating the active model selection via `PUT /api/v1/models/current` updates the global system provider state (`_active_model_state`). The backend messages endpoint (`/api/v1/sessions/{session_id}/messages`) automatically respects the active provider selection for all subsequent agent requests.

### C. Agent Tools & Return Payload Guarantees
All internal tools invoked by the persistent Pi Agent (`/api/v1/internal/tools/*`) are verified to return non-null, structured payloads:

1. **`search_knowledge(query, top_k)`**:
   - Performs vector + text search over `transcript_chunks`.
   - Returns array of objects with guaranteed non-null fields: `episode`, `guest`, `url`, and `excerpt`.
2. **`ship30_skill(topic, context_sources)`**:
   - Generates structured writing instructions for 1,250-word atomic essays.
   - Returns `{ ok: true, tool: "ship30_skill", topic, system_instruction, sources }`.
3. **`create_artifact(title, type, content)`**:
   - Encapsulates HTML/Markdown components inside artifact tags (`<!-- ARTIFACT_START -->`).
   - Returns `{ ok: true, tool: "artifact_builder", title, type, html }`.

---

## 3. Evaluator One-Command Docker Deployment

To evaluate the complete system end-to-end:

```bash
# 1. Clone repository and set .env
cp .env.example .env

# 2. Launch container environment
docker compose up --build
```

- **Frontend Application**: `http://localhost:3000`
- **Backend API & OpenAPI Docs**: `http://localhost:8000/docs`
- **Pi Agent Internal Service**: `http://localhost:8001`
- **Ollama Local Instance**: `http://localhost:11434`
