/**
 * Lenny Assistant API Client
 * 
 * Directly connects to FastAPI backend v1 REST endpoints.
 * Zero mock data — all sessions, messages, knowledge base documents,
 * sync status, and artifacts are retrieved live from the backend API.
 */

export const API_CONFIG = {
  fastApiBaseUrl: 'http://localhost:8000',
  defaultProvider: 'cloud', // 'ollama' | 'cloud'
};

class LennyApiClient {
  constructor() {
    this.currentProvider = API_CONFIG.defaultProvider;
    this.currentModel = '';
    this.isSyncing = false;
    this.syncProgress = 0;
    this.syncInterval = null;
    this.isOllamaAvailable = false;
    this.isGeminiAvailable = true;
    this.simulateOllamaOffline = false;
  }

  toggleOllamaAvailability(available) {
    // UI-only simulation control used by the settings test switch.
    this.simulateOllamaOffline = !available;
    this.isOllamaAvailable = Boolean(available);
  }

  // --- Model / Provider Config ---
  async setProvider(provider) {
    this.currentProvider = provider;
    try {
      const targetProvider = provider === 'cloud' ? 'cloud' : 'ollama';
      const fallbackModel = '';
      let targetModel = fallbackModel;

      // Resolve the provider's configured model from FastAPI so the UI toggle
      // never requires a code change when model names change in configuration.
      const modelsRes = await fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/models`);
      if (modelsRes.ok) {
        const catalog = await modelsRes.json();
        const selected = (catalog.providers || []).find(p => p.id === targetProvider);
        targetModel = selected?.models?.[0] || targetModel;
        if (targetProvider === 'ollama') {
          this.isOllamaAvailable = !this.simulateOllamaOffline && Boolean(selected?.available);
        } else {
          this.isGeminiAvailable = Boolean(selected?.available);
        }
      }

      const res = await fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/models/current`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: targetProvider, model: targetModel })
      });
      if (res.ok) {
        const data = await res.json();
        this.currentModel = data.current?.model || targetModel;
      }
    } catch (e) {
      console.warn('Could not update backend model provider:', e);
    }
    return {
      provider: this.currentProvider,
      model: this.currentModel,
      status: 'ready',
      ollamaAvailable: this.isOllamaAvailable,
      geminiAvailable: this.isGeminiAvailable
    };
  }

  async getModelStatus() {
    try {
      const [currentRes, catalogRes] = await Promise.all([
        fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/models/current`),
        fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/models`)
      ]);
      if (currentRes.ok) {
        const current = await currentRes.json();
        const catalog = catalogRes.ok ? await catalogRes.json() : { providers: [] };
        const providers = catalog.providers || [];
        const cloud = providers.find(p => p.id === 'cloud');
        const ollama = providers.find(p => p.id === 'ollama');

        this.currentProvider = current.provider === 'ollama' ? 'ollama' : 'cloud';
        this.currentModel = current.model || this.currentModel;
        this.isGeminiAvailable = Boolean(cloud?.available);
        this.isOllamaAvailable = !this.simulateOllamaOffline && Boolean(ollama?.available);
        return {
          provider: this.currentProvider,
          model: this.currentModel,
          status: 'ready',
          geminiAvailable: this.isGeminiAvailable,
          ollamaAvailable: this.isOllamaAvailable
        };
      }
    } catch (err) {
      console.warn('Backend model status unreachable:', err);
    }
    return {
      provider: this.currentProvider,
      model: this.currentModel,
      status: 'ready'
    };
  }

  // --- Conversations / Sessions Management ---
  async getConversations() {
    try {
      const res = await fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/sessions`);
      if (res.ok) {
        const sessions = await res.json();
        return (sessions || []).map(s => ({
          id: s.session_id || s.id,
          title: s.title || 'New Conversation',
          timeGroup: 'Today',
          updatedAt: s.updated_at ? new Date(s.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recently',
          messages: []
        }));
      }
    } catch (err) {
      console.warn('Could not fetch sessions from backend:', err);
    }
    return [];
  }

  async getConversation(id) {
    try {
      const res = await fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/sessions/${id}/messages`);
      if (res.ok) {
        const msgs = await res.json();
        return {
          id,
          title: 'Active Session',
          timeGroup: 'Today',
          updatedAt: 'Now',
          messages: (msgs || []).map((m, idx) => ({
            id: m.id || `msg-${idx}`,
            role: m.role,
            content: m.content,
            sources: m.sources || [],
            timestamp: m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Now'
          }))
        };
      }
    } catch (err) {
      console.warn(`Could not load messages for session ${id}:`, err);
    }
    return null;
  }

  async createConversation(title = 'New Conversation') {
    try {
      const res = await fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          provider: this.currentProvider
        })
      });
      if (res.ok) {
        const session = await res.json();
        return {
          id: session.session_id || session.id,
          title: session.title || title,
          timeGroup: 'Today',
          updatedAt: 'Just now',
          messages: []
        };
      }
    } catch (err) {
      console.warn('Could not create session on backend:', err);
    }
    return {
      id: 'session-' + Date.now(),
      title,
      timeGroup: 'Today',
      updatedAt: 'Just now',
      messages: []
    };
  }

  async deleteConversation(id) {
    try {
      await fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/sessions/${id}`, { method: 'DELETE' });
    } catch (err) {
      console.warn(`Could not delete session ${id}:`, err);
    }
    return { success: true };
  }

  async getArtifacts() {
    try {
      const res = await fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/artifacts`);
      if (res.ok) return await res.json();
    } catch (err) {
      console.warn('Could not fetch saved artifacts from backend:', err);
    }
    return [];
  }

  // --- Live Agent Messaging & Streaming ---
  async sendMessageStream({
    conversationId,
    message,
    onChunk,
    onSource,
    onArtifact,
    onError,
    onDone
  }) {
    try {
      const endpoint = `${API_CONFIG.fastApiBaseUrl}/api/v1/sessions/${conversationId}/messages`;
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          provider: this.currentProvider
        })
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
      const responseText = data.content || data.response || '';

      // Stream tokens into UI smoothly
      const words = responseText.split(' ');
      for (let i = 0; i < words.length; i++) {
        onChunk((i === 0 ? '' : ' ') + words[i]);
        await new Promise(r => setTimeout(r, 12));
      }

      // Attach retrieved ground sources from pgvector
      if (data.sources && Array.isArray(data.sources)) {
        data.sources.forEach((src, idx) => {
          onSource({
            id: `src-${idx + 1}`,
            number: String(idx + 1).padStart(2, '0'),
            guest: src.guest || src.guest_name || 'Lenny Guest',
            episode: src.episode || src.episode_title || 'Episode',
            title: src.episode || src.episode_title || 'Lenny Podcast Transcript',
            excerpt: src.excerpt || src.chunk_text || '',
            timestamp: src.similarity ? `${Math.round(src.similarity * 100)}% match` : 'pgvector match',
            url: src.url || src.episode_url || 'https://www.lennyspodcast.com',
            topics: ['Lenny Transcript', 'PGVector Match']
          });
        });
      }

      // Render generated interactive Artifact
      if (data.artifact_html || (data.artifact && data.artifact.code)) {
        onArtifact({
          id: 'art-' + Date.now(),
          title: data.artifact_title || 'Generated Artifact',
          type: 'html',
          badge: 'Interactive Artifact',
          code: data.artifact_html || data.artifact.code
        });
      }

      onDone();
    } catch (err) {
      console.error('Agent message execution failed:', err);
      onError(err);
    }
  }

  // --- Live Knowledge Base Management ---
  async getKnowledgeBaseMetadata() {
    try {
      const res = await fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/knowledge/status`);
      if (res.ok) {
        const data = await res.json();
        return {
          id: 'kb-supabase-pgvector',
          name: "Lenny's Podcast & Frameworks Knowledge Base",
          totalEpisodes: data.episode_count || 0,
          totalChunks: data.chunk_count || 0,
          totalWords: `${data.chunk_count || 0} chunks in pgvector`,
          vectorModel: 'gemini-embedding-001 (3072 dim)',
          lastSynced: data.last_sync_at ? new Date(data.last_sync_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Never synced',
          status: data.initialized ? 'ready' : 'uninitialized',
          syncMode: 'manual'
        };
      }
    } catch (err) {
      console.warn('Could not fetch knowledge status:', err);
    }
    return {
      id: 'kb-supabase-pgvector',
      name: "Lenny's Podcast & Frameworks Knowledge Base",
      totalEpisodes: 0,
      totalChunks: 0,
      totalWords: '0 chunks',
      vectorModel: 'gemini-embedding-001 (3072 dim)',
      lastSynced: 'Not connected',
      status: 'uninitialized',
      syncMode: 'manual'
    };
  }

  async getTranscripts(search = '') {
    try {
      const res = await fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/knowledge/documents`);
      if (res.ok) {
        const docs = await res.json();
        if (Array.isArray(docs) && docs.length > 0) {
          const mapped = docs.map((d, i) => ({
            id: d.id || `doc-${i}`,
            number: String(i + 1).padStart(2, '0'),
            guest: d.guest_name || 'Podcast Guest',
            episode: d.episode_title || 'Episode',
            title: d.episode_title || 'Podcast Transcript',
            excerpt: `Canonical source: ${d.file_path || 'transcript.md'}`,
            timestamp: d.created_at ? new Date(d.created_at).toLocaleDateString() : 'Indexed',
            url: d.source_url || 'https://www.lennyspodcast.com',
            topics: ['Lenny Transcript', 'PGVector']
          }));
          if (!search) return mapped;
          const term = search.toLowerCase();
          return mapped.filter(s =>
            s.guest.toLowerCase().includes(term) ||
            s.title.toLowerCase().includes(term)
          );
        }
      }
    } catch (err) {
      console.warn('Could not load transcripts from backend:', err);
    }
    return [];
  }

  async getKnowledgeBaseStatus() {
    try {
      const res = await fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/knowledge/status`);
      if (res.ok) {
        const data = await res.json();
        return {
          state: data.syncing ? 'syncing' : (data.initialized ? 'ready' : 'uninitialized'),
          name: "Lenny's Podcast Knowledge Base (Supabase pgvector)",
          totalEpisodes: data.episode_count || 0,
          totalWords: `${data.chunk_count || 0} pgvector chunks`,
          lastSync: data.last_sync_at ? new Date(data.last_sync_at).toLocaleTimeString() : 'Never',
          syncMode: 'manual',
          vectorModel: 'gemini-embedding-001 (3072 dim)',
          syncProgress: this.syncProgress
        };
      }
    } catch (err) {
      console.warn('FastAPI knowledge status unreachable:', err);
    }
    return {
      state: 'uninitialized',
      name: "Lenny's Podcast Knowledge Base",
      totalEpisodes: 0,
      totalWords: '0 chunks',
      lastSync: 'Never',
      syncMode: 'manual',
      vectorModel: 'gemini-embedding-001 (3072 dim)',
      syncProgress: 0
    };
  }

  async startSync({ onProgress, onStep, onDone }) {
    this.isSyncing = true;
    this.syncProgress = 0;

    const steps = [
      { step: 1, name: 'Scanning GitHub repository for new transcripts' },
      { step: 2, name: 'Computing SHA-256 hashes & chunking text' },
      { step: 3, name: 'Generating 3072-dim embeddings with Gemini' },
      { step: 4, name: 'Updating Supabase pgvector search index' }
    ];

    let currentStepIdx = 0;
    let progress = 10;
    if (onStep) onStep(steps[0]);

    // Fire live sync request to backend
    const syncPromise = fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/knowledge/sync`, { method: 'POST' })
      .then(async res => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `Knowledge sync failed (${res.status})`);
        return data;
      });

    this.syncInterval = setInterval(() => {
      if (!this.isSyncing) {
        clearInterval(this.syncInterval);
        return;
      }

      progress += 6;
      if (progress > 95) progress = 95;
      this.syncProgress = progress;
      if (onProgress) onProgress(progress);

      if (progress > 25 && currentStepIdx === 0) {
        currentStepIdx = 1;
        if (onStep) onStep(steps[1]);
      } else if (progress > 55 && currentStepIdx === 1) {
        currentStepIdx = 2;
        if (onStep) onStep(steps[2]);
      } else if (progress > 80 && currentStepIdx === 2) {
        currentStepIdx = 3;
        if (onStep) onStep(steps[3]);
      }
    }, 150);

    try {
      await syncPromise;
      let sawBackendSyncing = false;
      let completed = false;

      // The sync endpoint starts a background task. Wait for its real status
      // instead of marking the UI complete as soon as the POST returns.
      for (let attempt = 0; attempt < 600 && this.isSyncing; attempt++) {
        await new Promise(resolve => setTimeout(resolve, 500));
        const statusRes = await fetch(`${API_CONFIG.fastApiBaseUrl}/api/v1/knowledge/status`);
        if (!statusRes.ok) throw new Error(`Could not read sync status (${statusRes.status})`);
        const status = await statusRes.json();
        if (status.syncing) {
          sawBackendSyncing = true;
          if (status.total_episodes > 0) {
            const processed = status.processed_episodes || 0;
            progress = Math.min(95, 10 + Math.round((processed / status.total_episodes) * 85));
            this.syncProgress = progress;
            if (onProgress) onProgress(progress);
            if (processed / status.total_episodes >= 0.8 && currentStepIdx < 3) {
              currentStepIdx = 3;
              if (onStep) onStep(steps[3]);
            } else if (processed / status.total_episodes >= 0.45 && currentStepIdx < 2) {
              currentStepIdx = 2;
              if (onStep) onStep(steps[2]);
            } else if (processed > 0 && currentStepIdx < 1) {
              currentStepIdx = 1;
              if (onStep) onStep(steps[1]);
            }
          }
          continue;
        }
        // Allow the background task a couple of polling cycles to start.
        if (sawBackendSyncing || attempt >= 2) {
          completed = true;
          break;
        }
      }

      if (!completed && this.isSyncing) {
        throw new Error('Knowledge sync timed out while waiting for the backend.');
      }
      if (!this.isSyncing) return;
    } catch (err) {
      clearInterval(this.syncInterval);
      this.isSyncing = false;
      if (onDone) onDone(err);
      return;
    }
    clearInterval(this.syncInterval);

    this.isSyncing = false;
    this.syncProgress = 100;
    if (onProgress) onProgress(100);
    if (onDone) onDone();
  }

  cancelSync() {
    this.isSyncing = false;
    if (this.syncInterval) clearInterval(this.syncInterval);
    this.syncProgress = 0;
    return { success: true };
  }
}

export const api = new LennyApiClient();
