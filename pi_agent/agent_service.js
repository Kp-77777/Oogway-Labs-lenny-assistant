/**
 * Persistent Pi Agent Service for Lenny Growth Assistant.
 * Built using Node.js standard HTTP and the Pi Agent architecture.
 * Calls FastAPI internal tools directly over persistent HTTP (zero subprocess overhead).
 */
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Load .env automatically if present
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const envPaths = [path.resolve(__dirname, '../.env'), path.resolve(__dirname, '.env')];

for (const envPath of envPaths) {
  if (fs.existsSync(envPath)) {
    const envContent = fs.readFileSync(envPath, 'utf-8');
    for (const line of envContent.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const idx = trimmed.indexOf('=');
      if (idx > 0) {
        const key = trimmed.slice(0, idx).trim();
        let val = trimmed.slice(idx + 1).trim();
        if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
          val = val.slice(1, -1);
        }
        if (!process.env[key]) {
          process.env[key] = val;
        }
      }
    }
  }
}

const PORT = parseInt(process.env.PI_AGENT_PORT || '8001', 10);
const FASTAPI_INTERNAL_URL = process.env.FASTAPI_INTERNAL_URL || 'http://127.0.0.1:8000';
const OLLAMA_BASE_URL = process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434';
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || 'llama3.1:8b';
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || '';
const GEMINI_CHAT_MODEL = process.env.GEMINI_CHAT_MODEL || 'gemini-2.0-flash';
const GEMINI_CHAT_FALLBACK_MODELS = process.env.GEMINI_CHAT_FALLBACK_MODELS || 'gemini-1.5-flash,gemini-1.5-pro';

const SYSTEM_PROMPT = `# Lenny Growth Assistant — System Instructions

## ROLE
You are the conversational assistant for product managers and growth leaders.
You answer the user's complex product and growth questions using grounded knowledge.
Use prior conversation messages to resolve follow-up references.

## GROUNDING POLICY
The only approved source for factual product, growth, guest, episode, quote,
framework, or statistic claims is the output of \`search_knowledge\`.

## STRICT RULES
- Never invent quotes, guests, episode titles, URLs, statistics, or attributions.
- Cite every transcript-grounded claim exactly as:
  [Episode: Guest Name - Episode Title]
- If retrieval returns no relevant evidence, state that "The available Lenny transcripts do not directly support the answer". NEVER answer from ungrounded general knowledge.

## AVAILABLE TOOLS
1. search_knowledge(query, top_k): Search Lenny's Podcast transcripts.
2. ship30_skill(topic): Write a 1,250-word Ship 30 for 30 essay using retrieved knowledge.
3. create_artifact(title, type, content): Generate HTML or Markdown artifacts.
`;

/**
 * Execute FastAPI internal tool over HTTP
 */
async function callInternalTool(endpoint, payload) {
  const url = `${FASTAPI_INTERNAL_URL}/api/v1/internal/tools/${endpoint}`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Tool call failed (${res.status}): ${errText}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`[Pi Agent] Tool call to ${endpoint} failed:`, err.message);
    throw err;
  }
}

/**
 * Call Ollama chat API
 */
async function callOllama(messages, tools = []) {
  const url = `${OLLAMA_BASE_URL}/api/chat`;
  const body = {
    model: OLLAMA_MODEL,
    messages,
    stream: false,
    options: { temperature: 0.2 },
  };
  if (tools.length > 0) {
    body.tools = tools;
  }

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(`Ollama request failed with status ${res.status}`);
  }
  const data = await res.json();
  return data.message;
}

/**
 * Call Gemini Chat API with automatic model fallbacks
 */
async function callGemini(contents, systemInstruction = '') {
  if (!GEMINI_API_KEY) {
    throw new Error('GEMINI_API_KEY is not configured');
  }

  // Build model list from env: primary + comma-separated fallbacks
  const fallbacks = GEMINI_CHAT_FALLBACK_MODELS
    ? GEMINI_CHAT_FALLBACK_MODELS.split(',').map(m => m.trim()).filter(m => m)
    : [];
  const modelsToTry = [GEMINI_CHAT_MODEL, ...fallbacks].filter((v, i, a) => a.indexOf(v) === i);

  let lastError = null;

  for (const model of modelsToTry) {
    try {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${GEMINI_API_KEY}`;
      const payload = {
        contents,
        systemInstruction: systemInstruction ? { parts: [{ text: systemInstruction }] } : undefined,
        generationConfig: { temperature: 0.2 },
      };

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        const text = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
        if (!text) {
          console.warn(`[Pi Agent] Gemini ${model} returned empty text. Full response:`, JSON.stringify(data, null, 2));
        }
        return text;
      }

      const errText = await res.text();
      lastError = new Error(`Gemini API error for model ${model} (${res.status}): ${errText}`);
      console.warn(`[Pi Agent] Model ${model} failed (${res.status}), trying next fallback...`);
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error('All Gemini models failed');
}

/**
 * Run agent orchestration loop
 */
async function runAgent(userMessage, provider = 'cloud', history = []) {
  const sourcesCollected = [];
  const toolsExecuted = [];
  let artifactTitle = null;
  let artifactHtml = null;

  // Step 1: Check intent and search knowledge if substantive
  let ragContext = '';
  try {
    const searchRes = await callInternalTool('search_knowledge', { query: userMessage, top_k: 6 });
    if (searchRes.ok && Array.isArray(searchRes.results)) {
      for (const item of searchRes.results) {
        if (!item) continue;
        sourcesCollected.push({
          episode: String(item.episode || item.episode_title || 'Lenny Episode'),
          guest: String(item.guest || item.guest_name || 'Lenny Guest'),
          url: String(item.url || item.episode_url || item.source_url || ''),
          excerpt: String(item.excerpt || item.chunk_text || item.text || ''),
        });
      }
      toolsExecuted.push('search_knowledge');

      if (sourcesCollected.length > 0) {
        const blocks = sourcesCollected.map((s, i) =>
          `Source ${i + 1} [Episode: ${s.guest ? s.guest + ' - ' : ''}${s.episode}]\nURL: ${s.url}\nExcerpt: ${s.excerpt}`
        );
        ragContext = `\n\n## Relevant Transcript Context:\n${blocks.join('\n\n')}`;
      }
    }
  } catch (err) {
    console.warn('[Pi Agent] Search knowledge step error:', err.message);
  }

  // Step 2: Check for Ship 30 essay skill trigger
  const lowerMsg = userMessage.toLowerCase();
  const isShip30 = lowerMsg.includes('ship 30') || lowerMsg.includes('1250') || lowerMsg.includes('1,250') || lowerMsg.includes('essay');
  if (isShip30) {
    try {
      const shipRes = await callInternalTool('ship30_skill', {
        topic: userMessage,
        context_sources: sourcesCollected,
      });
      if (shipRes.ok) {
        toolsExecuted.push('ship30_skill');

        const essaySources = (shipRes.sources || sourcesCollected).map((source, index) =>
          `Source ${index + 1} [Episode: ${source.guest ? source.guest + ' - ' : ''}${source.episode || 'Lenny Episode'}]\nURL: ${source.url || ''}\nExcerpt: ${source.excerpt || source.text || ''}`
        ).join('\n\n');
        const essayPrompt = `${userMessage}\n\nRetrieved transcript evidence:\n${essaySources || 'No relevant transcript evidence was found.'}`;
        let essay;

        if (provider === 'ollama') {
          const reply = await callOllama([
            { role: 'system', content: shipRes.system_instruction || SYSTEM_PROMPT },
            { role: 'user', content: essayPrompt },
          ]);
          essay = reply.content || '';
        } else {
          essay = await callGemini([
            { role: 'user', parts: [{ text: essayPrompt }] },
          ], shipRes.system_instruction || SYSTEM_PROMPT);
        }

        if (!essay) {
          throw new Error('Essay model returned an empty response');
        }

        return {
          response: essay,
          response_type: 'essay',
          sources: sourcesCollected,
          artifact_title: null,
          artifact_html: null,
          provider,
          model: provider === 'ollama' ? OLLAMA_MODEL : GEMINI_CHAT_MODEL,
          tools_executed: toolsExecuted,
        };
      }
    } catch (err) {
      console.warn('[Pi Agent] Ship 30 skill step error:', err.message);
    }
  }

  // Step 3: Run LLM completion with transcript grounding
  let finalResponse = '';
  const augmentedPrompt = `${userMessage}${ragContext ? '\n' + ragContext : ''}`;

  if (provider === 'ollama') {
    const messages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...history.map(h => ({ role: h.role, content: h.content })),
      { role: 'user', content: augmentedPrompt }
    ];
    const reply = await callOllama(messages);
    finalResponse = reply.content || '';
  } else {
    // Cloud / Gemini
    const contents = [
      ...history.map(h => ({
        role: h.role === 'assistant' ? 'model' : 'user',
        parts: [{ text: h.content }]
      })),
      {
        role: 'user',
        parts: [{ text: augmentedPrompt }]
      }
    ];
    finalResponse = await callGemini(contents, SYSTEM_PROMPT);
  }

  // Step 4: Detect and build artifact if requested
  const isArtifact = lowerMsg.includes('artifact') || lowerMsg.includes('html') || lowerMsg.includes('dashboard') || lowerMsg.includes('calculator') || finalResponse.includes('```html') || finalResponse.includes('<!-- ARTIFACT_START -->');
  if (isArtifact) {
    try {
      const artRes = await callInternalTool('create_artifact', {
        title: 'Generated Growth Artifact',
        type: 'html',
        content: finalResponse,
      });
      if (artRes.ok && artRes.html) {
        artifactTitle = artRes.title || 'Generated Growth Artifact';
        artifactHtml = artRes.html;
        toolsExecuted.push('create_artifact');
      }
    } catch (err) {
      console.warn('[Pi Agent] Artifact generation error:', err.message);
    }
  }

  return {
    response: finalResponse,
    response_type: artifactHtml ? 'artifact' : (finalResponse.split(/\s+/).length > 600 ? 'essay' : 'answer'),
    sources: sourcesCollected,
    artifact_title: artifactTitle,
    artifact_html: artifactHtml,
    provider,
    model: provider === 'ollama' ? OLLAMA_MODEL : GEMINI_CHAT_MODEL,
    tools_executed: toolsExecuted,
  };
}

// HTTP Server
const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (req.method === 'GET' && url.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ready', agent: 'pi-agent-core', port: PORT }));
    return;
  }

  if (req.method === 'POST' && url.pathname === '/chat') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      try {
        const payload = JSON.parse(body || '{}');
        const userMessage = payload.message || '';
        const provider = (payload.provider || 'cloud').toLowerCase();
        const history = payload.history || [];

        const result = await runAgent(userMessage, provider, history);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, ...result }));
      } catch (err) {
        console.error('[Pi Agent Server Error]:', err);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: false, error: err.message }));
      }
    });
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[Pi Agent Service] Persistent agent runtime listening on port ${PORT}`);
});
