"""Fix transcript_chunks embedding column: change vector(768) -> vector(3072)
for gemini-embedding-001 which outputs 3072 dimensions.

Usage:
    python backend/fix_vector_dim.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.core.config import settings


async def main():
    import asyncpg

    print("=" * 52)
    print("  Fixing transcript_chunks vector dimension")
    print(f"  New dimension: {settings.VECTOR_DIMENSIONS}")
    print("=" * 52)

    conn = await asyncpg.connect(settings.DATABASE_URL, timeout=10)

    # Drop and recreate transcript_chunks with correct vector dim
    print("\n[1] Dropping old transcript_chunks table...")
    await conn.execute("DROP TABLE IF EXISTS transcript_chunks CASCADE")
    print("[OK]  Dropped")

    print(f"\n[2] Creating transcript_chunks with vector({settings.VECTOR_DIMENSIONS})...")
    await conn.execute(f"""
        CREATE TABLE transcript_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID REFERENCES knowledge_documents(id) ON DELETE CASCADE,
            file_path VARCHAR(500),
            episode_title VARCHAR(500) NOT NULL,
            guest_name VARCHAR(200) NOT NULL,
            episode_url VARCHAR(1000),
            chunk_text TEXT NOT NULL,
            chunk_index INTEGER NOT NULL DEFAULT 0,
            embedding vector({settings.VECTOR_DIMENSIONS}),
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    print("[OK]  Created")

    # Verify
    exists = await conn.fetchval(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'transcript_chunks')"
    )
    col = await conn.fetchrow("""
        SELECT data_type, udt_name
        FROM information_schema.columns
        WHERE table_name = 'transcript_chunks' AND column_name = 'embedding'
    """)
    print(f"\n[OK]  Table exists: {exists}")
    print(f"[OK]  Embedding column type: {col['udt_name']}")

    await conn.close()
    print("\n  Done! transcript_chunks is ready for 3072-dim vectors.")
    print("=" * 52)


if __name__ == "__main__":
    asyncio.run(main())
