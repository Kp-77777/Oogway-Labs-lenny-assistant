"""Quick Supabase connection check script.

Usage:
    python backend/check_db.py

Tests:
  1. DATABASE_URL loaded from .env
  2. PostgreSQL TCP connection reachable
  3. pgvector extension available
  4. All app tables exist
"""
import asyncio
import sys
from pathlib import Path

# Ensure backend is in path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings


async def check_db():
    print("=" * 52)
    print("   Supabase / PostgreSQL Connection Check")
    print("=" * 52)

    # 1. Check env loaded
    db_url = settings.DATABASE_URL
    if not db_url:
        print("\n[FAIL] DATABASE_URL is not set in .env")
        return

    # Mask password for safe display
    try:
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        safe_url = db_url.replace(parsed.password or "", "****") if parsed.password else db_url
    except Exception:
        safe_url = db_url[:40] + "..."

    print(f"\n  URL     : {safe_url}")
    print(f"  DB OK   : {settings.db_available}")

    if not settings.db_available:
        print("\n[FAIL] DATABASE_URL still contains placeholder text.")
        print("  Replace [YOUR-PASSWORD] and [YOUR-PROJECT-REF] with real values in .env")
        return

    # 2. Attempt TCP connection
    print("\n[1] Testing TCP connection to Supabase...")
    try:
        import asyncpg
        conn = await asyncpg.connect(db_url, timeout=10)
        version = await conn.fetchval("SELECT version()")
        print(f"[OK]  Connected!")
        print(f"      {version[:80]}")
        await conn.close()
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        print("\nCommon causes:")
        print("  - Wrong password in DATABASE_URL")
        print("  - Supabase project is paused (check dashboard)")
        print("  - Firewall blocking port 5432")
        return

    # 3. Check pgvector extension
    print("\n[2] Checking pgvector extension...")
    try:
        conn = await asyncpg.connect(db_url, timeout=10)
        ext = await conn.fetchval(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        )
        if ext:
            print("[OK]  pgvector extension is ENABLED")
        else:
            print("[WARN] pgvector NOT found - will be created on first app startup")
        await conn.close()
    except Exception as e:
        print(f"[WARN] Could not check pgvector: {e}")

    # 4. Check app tables
    print("\n[3] Checking app tables...")
    tables = [
        "knowledge_documents",
        "transcript_chunks",
        "chat_sessions",
        "chat_messages",
        "generated_artifacts"
    ]
    try:
        conn = await asyncpg.connect(db_url, timeout=10)
        for table in tables:
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                table
            )
            status = "EXISTS" if exists else "NOT YET (auto-created on startup)"
            print(f"  {table:<30} {status}")

        # Check transcript chunk count if table exists
        tc_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'transcript_chunks')"
        )
        if tc_exists:
            chunk_count = await conn.fetchval("SELECT COUNT(*) FROM transcript_chunks")
            print(f"\n  Transcript chunks in DB : {chunk_count}")

        await conn.close()
    except Exception as e:
        print(f"[FAIL] Table check failed: {e}")
        return

    print("\n" + "=" * 52)
    print("   DATABASE CONNECTION OK -- ALL SYSTEMS READY!")
    print("=" * 52)


if __name__ == "__main__":
    asyncio.run(check_db())
