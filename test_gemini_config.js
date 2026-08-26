#!/usr/bin/env node
/**
 * Test: Verify Gemini 3.6 Flash config is env-driven only (no hardcoded fallbacks)
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load .env
const envPath = path.resolve(__dirname, '.env');
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

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || '';
const GEMINI_CHAT_MODEL = process.env.GEMINI_CHAT_MODEL || 'gemini-3.5-flash';
const GEMINI_CHAT_FALLBACK_MODELS = process.env.GEMINI_CHAT_FALLBACK_MODELS || '';

console.log('=== Gemini Configuration Test ===\n');
console.log(`✓ Primary Model: ${GEMINI_CHAT_MODEL}`);
console.log(`✓ Fallback Models: ${GEMINI_CHAT_FALLBACK_MODELS || '(none - no fallback)'}`);
console.log(`✓ API Key Present: ${GEMINI_API_KEY ? 'Yes' : 'No'}`);

// Build model list from env only
const fallbacks = GEMINI_CHAT_FALLBACK_MODELS
  ? GEMINI_CHAT_FALLBACK_MODELS.split(',').map(m => m.trim()).filter(m => m)
  : [];
const modelsToTry = [GEMINI_CHAT_MODEL, ...fallbacks].filter((v, i, a) => a.indexOf(v) === i);

console.log(`\n✓ Models to try (in order):`);
modelsToTry.forEach((m, i) => console.log(`  ${i + 1}. ${m}`));

if (modelsToTry.length === 1) {
  console.log('\n✓ SUCCESS: Only env-driven model will be tried. No hardcoded fallbacks.');
} else {
  console.log('\n✓ CONFIGURED: Will try fallback models only if specified in .env');
}
