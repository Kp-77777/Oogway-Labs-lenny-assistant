# Product Requirement Document (PRD) — The Lenny Growth Assistant

## 1. Executive Summary & Problem Statement

### Problem Statement
Product Managers, Founders, and Growth Leaders frequently seek actionable frameworks, tactics, and case study advice from industry experts featured on *Lenny's Podcast*. However, finding specific insights, exact guest quotes, timestamps, or proven frameworks across hundreds of hours of raw audio and multi-thousand-word transcript markdown files is time-consuming and unreliable. General-purpose LLMs hallucinate guest quotes, attribute frameworks to the wrong speakers, or give generic advice.

### Solution Overview
**The Lenny Growth Assistant** is a full-stack, grounded AI assistant that indexes the canonical *Lenny's Podcast* transcript repository (`ChatPRD/lennys-podcast-transcripts`). It delivers factual, source-attributed answers, atomic 1,250-word Ship 30 essays, and interactive HTML growth artifacts (dashboards, calculators, matrix cards). It seamlessly supports both Cloud LLMs (Google Gemini 3.6 Flash) and Local privacy-first LLMs (Ollama `llama3.1:8b`).

---

## 2. Target Users & User Personas

| Persona | Role | Primary Need | Key Use Case |
|---------|------|--------------|--------------|
| **Product Manager (PM)** | Senior / Lead PM | Practical execution frameworks (e.g., Shreyas Doshi's LNO framework, pricing, activation loops) | Asks specific growth questions, generates reference artifacts, and reviews cited excerpts with exact timestamp URLs. |
| **Growth Marketer / Founder** | Startup Founder / Growth Lead | Long-form, structured strategy essays to share with teams | Triggers the Ship 30 for 30 essay skill to generate grounded 1,250-word action plans from expert transcript insights. |
| **Evaluator / Technical Reviewer** | System Evaluator | One-command deployment, robust multi-model toggle, zero hallucination | Deploys containerized environment via `docker compose up --build` to test RAG grounding, cloud/local model switching, and artifact rendering. |

---

## 3. Success Metrics

1. **Grounding & Citation Accuracy**: 100% of factual claims regarding guest advice cite verified transcript sources formatted as `[Episode: Guest Name - Episode Title]` with working GitHub/timestamp URLs.
2. **Zero Hallucination Rate**: If transcript context is empty or missing relevant evidence, the agent explicitly states that available transcripts do not contain the answer, avoiding ungrounded speculation.
3. **Model Switching Reliability**: 100% smooth toggling between Cloud Gemini (`gemini-3.6-flash`) and Local Ollama (`llama3.1:8b`) without server crashes or state loss.
4. **Deployment Simplicity**: Complete environment startup in one command (`docker compose up --build`).

---

## 4. System Assumptions & Constraints

### Key Assumptions
1. **Single Embedding Model (3072 Dimensions)**: The vector database schema uses `vector(3072)` matching `gemini-embedding-001`. Fallback models with mismatched dimensions (e.g., 768-dim `text-embedding-004`) are disabled to guarantee vector consistency.
2. **Database Flexibility**: Supports both cloud Supabase PostgreSQL (via URI in `.env`) and local Docker PostgreSQL (`pgvector/pgvector:pg16-latest`).
3. **Environment Setup**: Evaluators execute the app via Docker Compose or local Python 3.12 / Node.js 22 runtime with `.env` containing a valid `GEMINI_API_KEY`.
4. **No Security Auth Overhead Needed for Demo**: The system is designed for local/evaluator demonstration; internal RPC endpoints (`/api/v1/internal/tools/*`) are unauthenticated to eliminate setup complexity.

---

## 5. Product Scope & Functional Requirements

### In-Scope
- **Canonical Transcript Ingestion**: Discovers and ingests transcript files (`episodes/<slug>/transcript.md`) from GitHub, extracting speaker turns, timestamps, frontmatter, and topic indices.
- **Hybrid Retrieval Engine**: Cosine vector similarity (using `gemini-embedding-001`) + PostgreSQL full-text keyword search (`ts_rank_cd`).
- **Persistent Node.js Pi Agent Service**: Runs persistent agent loop on port 8001 to process messages, call internal FastAPI tools over HTTP, and format grounded responses.
- **Dual Model Provider Support**: Instant model switching between Cloud Gemini and Local Ollama.
- **Artifact Generation**: Built-in HTML/Markdown artifact builder rendering interactive growth cards, calculators, and matrix views in a side-by-side UI panel.

### Out-of-Scope (Future Enhancements)
- Multi-user authentication & user account management (currently session-based UUID).
- Live audio processing or direct YouTube video streaming.

---

## 6. Core User Flows

```
[User Query] ──► [Frontend UI] ──► [FastAPI /messages Endpoint]
                                              │
                                              ▼
                                 [Pi Agent Service (Port 8001)]
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
       [search_knowledge Tool]                             [Check Active LLM Provider]
                    │                                                   │
        (RAG Retrieval from pgvector)                         (Cloud Gemini OR Local Ollama)
                    │                                                   │
                    └─────────────────────────┬─────────────────────────┘
                                              ▼
                                   [Augmented Grounded Prompt]
                                              │
                                              ▼
                              [LLM Completion + Citation Check]
                                              │
                                              ▼
                              [Render Artifact Panel / Response]
```

---

## 7. Acceptance Criteria

- [x] **Single 3072-Dim Vector Standard**: System operates on a strict 3072-dimension vector embedding contract (`gemini-embedding-001`).
- [x] **Model Provider Toggle**: Switching provider in the UI updates active selection state via `PUT /api/v1/models/current` and routes subsequent prompts correctly.
- [x] **Defined Tool Payloads**: `search_knowledge`, `ship30_skill`, and `create_artifact` return non-null, fully defined JSON objects.
- [x] **One-Command Docker Setup**: `docker compose up --build` builds and starts Nginx, FastAPI, Pi Agent, Ollama, and PostgreSQL containers.

---

## 8. Risk Assessment & Mitigation

| Risk | Impact | Mitigation Strategy |
|------|--------|---------------------|
| **Embedding Dimension Mismatch** | High | Disabled mismatched fallback embedding models (`GEMINI_EMBED_FALLBACK_MODELS=""`) to enforce `vector(3072)` contract. |
| **Ollama Model Download Delay** | Medium | Ollama container pulls `llama3.1:8b` on first startup and caches model in `ollama_data` Docker volume. Cloud Gemini remains available immediately. |
| **Hallucination on Niche Queries** | Medium | Enforced strict system prompt grounding policy; agent must state lack of transcript evidence if vector search score is low. |

---

## 9. Implementation & Verification Plan

1. **Config & Environment Verification**: Verified single 3072-dim embedding configuration via `test_gemini_config.py`.
2. **Backend API Testing**: Verified session message routing and active model state switching.
3. **Documentation**: Created `AGENT.md`, `PRD.md`, `DESIGN.md`, `ARCHITECTURE.md`, and updated `README.md`.
