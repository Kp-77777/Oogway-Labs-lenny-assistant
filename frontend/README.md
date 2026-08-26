# Lenny Growth Assistant — Frontend

Vanilla HTML/CSS/JavaScript frontend for the Lenny Growth Assistant. It uses the
canonical FastAPI v1 REST API and does not require a frontend build step.

---

## 📁 Directory Structure

```
frontend/
├── index.html        # Main single-page application structure & modals
├── styles.css        # Clean CSS design system & modern layout
├── app.js            # Vanilla JS UI controller, state & stream rendering
├── api.js            # Modular API client (SSE & REST ready for FastAPI/Ollama)
└── README.md         # Integration guide & architecture documentation
```

---

## 🚀 Key Features

1. **Chat Interface with Streaming & Citations**
   - New Chat & organized conversation history by date
   - Token-by-token message streaming via Server-Sent Events (SSE) or client simulation
   - Grounded source references showing episode guest, timestamp, excerpt, and link

2. **Side-by-Side Artifact Viewer**
   - Live interactive sandboxed iframe rendering for HTML/CSS prototypes
   - Formatted Markdown rendering
   - Code inspection tab with syntax highlighting, copy, and file download

3. **Single Unified Knowledge Base (Manual Trigger Sync)**
   - Displays real-time status of the single unified podcast knowledge store
   - Manual sync trigger simulating 4-stage pipeline (Scanning → Chunking → Vector Embeddings → Index Building)
   - Searchable Transcripts Explorer with quote filtering

4. **Model Switching & Error Handling**
- Seamless toggle between **Ollama Local** and **Cloud**; model IDs come from FastAPI configuration.
   - Interactive settings modal for API base URLs
   - Graceful offline / error fallback modal

---

## 🔌 How to Integrate with Backend Modules

To connect this frontend to a Python FastAPI backend or Ollama server:

1. Open `api.js` and configure `API_CONFIG`:
   ```javascript
   export const API_CONFIG = {
     useMockBackend: false,                         // Switch to true live backend
     fastApiBaseUrl: 'http://localhost:8000',      // Your FastAPI server URL
     ollamaBaseUrl: 'http://localhost:11434',      // Ollama endpoint
     defaultProvider: 'ollama',
   };
   ```

2. **Expected Backend Endpoints**:
   - `GET/PUT /api/v1/models/current` — Reads or changes the active provider/model.
   - `POST /api/v1/sessions` — Creates an independent chat session.
   - `GET /api/v1/sessions` — Lists persisted sessions.
   - `GET/POST /api/v1/sessions/{session_id}/messages` — Loads history or sends a message.
   - `GET /api/v1/knowledge/status` — Returns knowledge-base status.
   - `POST /api/v1/knowledge/sync` — Starts transcript synchronization.
   - `GET /api/v1/knowledge/documents` — Lists indexed transcripts.
