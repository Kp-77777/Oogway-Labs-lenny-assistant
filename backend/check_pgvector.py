"""Interactive pgvector test — type a sentence, embed it, store it, inspect it.

Usage:
    python backend/check_pgvector.py
"""
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.core.config import settings


async def generate_embedding(text: str) -> list[float] | None:
    """Generate embedding using Gemini (model from .env)."""
    if not settings.gemini_available:
        print("[FAIL] GEMINI_API_KEY not configured in .env")
        return None
    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        for model_id in settings.gemini_embed_model_candidates:
            try:
                result = client.models.embed_content(model=model_id, contents=text)
                if hasattr(result, "embeddings") and result.embeddings:
                    return list(result.embeddings[0].values)
            except Exception:
                continue
    except Exception as e:
        print(f"[FAIL] Embedding error: {e}")
    return None


async def main():
    print("=" * 56)
    print("  pgvector Live Test — Type a sentence to embed & store")
    print("=" * 56)

    if not settings.db_available:
        print("[FAIL] DATABASE_URL not configured.")
        return

    import asyncpg
    conn = await asyncpg.connect(settings.DATABASE_URL, timeout=10)
    print("[OK]  Connected to Supabase PostgreSQL")
    print(f"[OK]  Embedding model: {settings.GEMINI_EMBED_MODEL}")
    print()

    # Get input from user
    text = input("  Enter a sentence to embed and store:\n  > ").strip()
    if not text:
        print("[FAIL] Empty input. Exiting.")
        await conn.close()
        return

    print(f"\n  Chunk text   : {text!r}")
    print(f"  Chunk length : {len(text)} characters / {len(text.split())} words")

    # Generate embedding
    print(f"\n  Generating embedding via {settings.GEMINI_EMBED_MODEL}...")
    vec = await generate_embedding(text)
    if not vec:
        print("[FAIL] Could not generate embedding.")
        await conn.close()
        return

    print(f"  Vector dims  : {len(vec)}")
    print(f"  First 5 vals : {[round(v, 6) for v in vec[:5]]}")
    print(f"  Last  5 vals : {[round(v, 6) for v in vec[-5:]]}")

    # Store to transcript_chunks table
    print("\n  Storing to Supabase transcript_chunks...")
    try:
        chunk_id = str(uuid.uuid4())
        vec_str = "[" + ",".join(str(v) for v in vec) + "]"

        await conn.execute("""
            INSERT INTO transcript_chunks
                (id, document_id, file_path, episode_title, guest_name,
                 episode_url, chunk_text, chunk_index, embedding, created_at)
            VALUES
                ($1, $2, $3, $4, $5, $6, $7, $8, $9::vector, NOW())
        """,
            chunk_id,
            None,                           # document_id nullable — no FK needed for test
            "test/manual-input.md",
            "Manual Test Entry",
            "Test User",
            "",
            text,
            0,
            vec_str
        )
        print(f"[OK]  Stored! chunk id: {chunk_id}")

        # Verify by reading back
        row = await conn.fetchrow(
            "SELECT chunk_text, array_length(embedding::real[], 1) AS dims FROM transcript_chunks WHERE id = $1",
            chunk_id
        )
        print(f"\n  -- Readback from DB --")
        print(f"  chunk_text : {row['chunk_text']!r}")
        print(f"  vector dim : {row['dims']}")

        # Show total chunks in DB
        total = await conn.fetchval("SELECT COUNT(*) FROM transcript_chunks")
        print(f"\n  Total chunks in DB now: {total}")

    except Exception as e:
        print(f"[FAIL] Could not store to DB: {e}")

    await conn.close()
    print("\n  Done!")
    print("=" * 56)


if __name__ == "__main__":
    asyncio.run(main())
