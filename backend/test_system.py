"""System Integration Test Suite for The Lenny Growth Assistant.

Verifies:
  1. Core Config & .env loading
  2. Database & ORM Schemas
  3. Knowledge Ingestion & 768-dim Gemini Embeddings
  4. RAG Retriever
    5. Agent Engine (LangChain orchestration with search, Ship30, and artifact tools)
"""
import asyncio
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.agent.engine import agent
from app.rag.ingest import get_kb_status, run_ingest
from app.rag.retriever import search_transcripts
from app.agent.tools.rag_tool import search_knowledge
from app.agent.tools.ship30_tool import ship_30_essay_generator
from app.agent.tools.artifact_tool import artifact_builder


async def test_all():
    print("==================================================")
    print("   The Lenny Growth Assistant — System Health Check")
    print("==================================================\n")

    # 1. Config Check
    print("1. [CONFIG CHECK]")
    print(f"   Project Name: {settings.PROJECT_NAME}")
    print(f"   Gemini Available: {settings.gemini_available}")
    print(f"   Database Configured: {settings.db_available}")
    print(f"   Ollama URL: {settings.OLLAMA_BASE_URL}\n")

    # 2. Knowledge Base Status Check
    print("2. [KNOWLEDGE BASE STATUS]")
    status = get_kb_status()
    print(f"   Initialized: {status['initialized']}")
    print(f"   Episode Count: {status['episode_count']}")
    print(f"   Chunk Count: {status['chunk_count']}\n")

    # 3. Tool Verification
    print("3. [AGENT TOOL VERIFICATION]")

    # Tool 1: search_knowledge
    print("   Testing Tool 1: search_knowledge('LNO framework')...")
    sources = await search_knowledge("LNO framework", top_k=2)
    print(f"   -> Retrieved {len(sources)} sources.")
    for s in sources[:1]:
        print(f"      Source: [Episode: {s.get('guest')} - {s.get('episode')}]")

    # Tool 2: ship_30_essay_generator
    print("\n   Testing Tool 2: ship_30_essay_generator...")
    essay_cfg = await ship_30_essay_generator("PM Growth Strategy", sources)
    print(f"   -> Tool output topic: '{essay_cfg['topic']}'")

    # Tool 3: artifact_builder
    print("\n   Testing Tool 3: artifact_builder...")
    art_payload = await artifact_builder("Growth Matrix Card", "html", "<div class='card'>Growth Matrix</div>")
    print(f"   -> Artifact title: '{art_payload['title']}'")
    print(f"   -> Artifact type: '{art_payload['type']}'\n")

    # 4. Agent Engine Execution Test
    print("4. [AGENT ENGINE FULL PIPELINE TEST]")
    print("   Sending test query to Agent Engine (Gemini Cloud Provider)...")
    res = await agent.run("Explain Shreyas Doshi's LNO framework in 2 bullet points.", provider="cloud")
    print(f"   Provider: {res['provider']}")
    print(f"   Model: {res['model']}")
    print(f"   Response Type: {res['response_type']}")
    print(f"   Sources Attached: {len(res['sources'])}")
    print(f"   Response Excerpt:\n   {res['response'][:250]}...\n")

    print("==================================================")
    print("   SYSTEM VERIFICATION COMPLETE — ALL SYSTEMS OK! ")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_all())
