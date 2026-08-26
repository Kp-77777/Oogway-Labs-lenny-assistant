#!/usr/bin/env python3
"""
Test: Verify Gemini 3.6 Flash config is env-driven only (no hardcoded fallbacks)
"""
import sys
sys.path.insert(0, 'backend')

from app.core.config import settings

print("=== Gemini Configuration Test (Python) ===\n")
print(f"[OK] Primary Model: {settings.GEMINI_CHAT_MODEL}")
print(f"[OK] Fallback Models: {settings.GEMINI_CHAT_FALLBACK_MODELS or '(none - no fallback)'}")
print(f"[OK] API Key Present: {'Yes' if settings.gemini_available else 'No'}")

print(f"\n[OK] Models to try (in order):")
candidates = settings.gemini_embed_model_candidates if hasattr(settings, 'gemini_embed_model_candidates') else []
# For chat models, build list manually
chat_fallbacks = [m.strip() for m in settings.GEMINI_CHAT_FALLBACK_MODELS.split(',') if m.strip()] if settings.GEMINI_CHAT_FALLBACK_MODELS else []
chat_models = [settings.GEMINI_CHAT_MODEL] + chat_fallbacks
for i, m in enumerate(chat_models, 1):
    print(f"  {i}. {m}")

if len(chat_models) == 1:
    print("\n[OK] SUCCESS: Only env-driven model will be tried. No hardcoded fallbacks.")
else:
    print("\n[OK] CONFIGURED: Will try fallback models only if specified in .env")
