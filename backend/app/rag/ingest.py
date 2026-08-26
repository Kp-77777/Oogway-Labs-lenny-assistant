"""Canonical GitHub ingestion for Lenny's Podcast transcript knowledge base.

The source repository stores one episode at ``episodes/<episode-slug>/transcript.md``.
This module discovers those files, preserves source metadata and speaker timestamps,
then writes retrieval-ready chunks to Supabase/pgvector.
"""
import asyncio
import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

try:
    import yaml
except ImportError:  # Keeps the app usable until dependencies are installed.
    yaml = None


logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_WEB_BASE = "https://github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"
INGESTION_SCHEMA_VERSION = "lenny-transcript-rag-v3-index-topics"
FRONTMATTER_PATTERN = re.compile(r"\A---\s*\r?\n(?P<meta>.*?)\r?\n---\s*\r?\n?(?P<body>.*)\Z", re.DOTALL)
SPEAKER_TURN_PATTERN = re.compile(
    r"(?P<speaker>[A-Z][A-Za-z .,'’\-]{0,80}?)\s*\((?P<timestamp>\d{1,2}:\d{2}:\d{2})\):"
)
PROMOTIONAL_MARKERS = (
    "this episode is brought to you by",
    "after a short word from our sponsors",
    "brought to you by",
    "sponsored by",
    "use code ",
)

_sync_state = {
    "initialized": False,
    "episode_count": 0,
    "chunk_count": 0,
    "last_sync_at": None,
    "syncing": False,
    "last_sync_stats": {},
    "processed_episodes": 0,
    "total_episodes": 0,
}

# Used only when the database is deliberately not configured.
all_chunk_data: list[dict] = []


def get_kb_status() -> dict:
    return {
        "initialized": _sync_state["initialized"],
        "episode_count": _sync_state["episode_count"],
        "chunk_count": _sync_state["chunk_count"],
        "last_sync_at": _sync_state["last_sync_at"],
        "syncing": _sync_state["syncing"],
        "last_sync_stats": _sync_state["last_sync_stats"],
        "processed_episodes": _sync_state["processed_episodes"],
        "total_episodes": _sync_state["total_episodes"],
        "db_available": settings.db_available,
        "gemini_available": settings.gemini_available,
    }


async def get_kb_status_async() -> dict:
    """Return process status enriched with persistent Supabase counts."""
    status = get_kb_status()
    if not settings.db_available:
        return status
    try:
        from sqlalchemy import text
        from app.db.database import get_session_factory

        factory = get_session_factory()
        if factory is None:
            return status
        async with factory() as session:
            counts = await session.execute(text("""
                SELECT
                    (SELECT COUNT(*) FROM knowledge_documents WHERE is_active = true) AS episode_count,
                    (SELECT COUNT(*) FROM transcript_chunks) AS chunk_count
            """))
            row = counts.fetchone()
            if row:
                status["episode_count"] = max(status["episode_count"], int(row.episode_count or 0))
                status["chunk_count"] = max(status["chunk_count"], int(row.chunk_count or 0))
                status["initialized"] = status["initialized"] or status["chunk_count"] > 0
    except Exception as exc:
        logger.warning("Could not enrich knowledge status from Supabase: %s", exc)
    return status


def _compute_hash(content: str, index_topics: Optional[list[str]] = None) -> str:
    # Versioned hashes trigger one safe re-index when parsing/chunking changes.
    topics = ",".join(sorted(index_topics or []))
    return hashlib.sha256(f"{INGESTION_SCHEMA_VERSION}\n{topics}\n{content}".encode("utf-8")).hexdigest()


def _fallback_frontmatter_parse(frontmatter: str) -> dict[str, Any]:
    """Small fallback for common scalar YAML when PyYAML is unavailable."""
    result: dict[str, Any] = {}
    current_list: Optional[str] = None
    for line in frontmatter.splitlines():
        if line.startswith("  - ") or line.startswith("- "):
            if current_list:
                result.setdefault(current_list, []).append(line.split("- ", 1)[1].strip())
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_list = key.strip()
        value = value.strip().strip("\"'")
        result[current_list] = value if value else []
    return result


def _split_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Return parsed YAML metadata and transcript body without frontmatter."""
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content.strip()

    raw_metadata = match.group("meta")
    try:
        parsed = yaml.safe_load(raw_metadata) if yaml else _fallback_frontmatter_parse(raw_metadata)
    except Exception as exc:
        logger.warning("Could not parse transcript frontmatter: %s", exc)
        parsed = _fallback_frontmatter_parse(raw_metadata)
    return (parsed if isinstance(parsed, dict) else {}), match.group("body").strip()


def _metadata_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _timestamp_to_seconds(timestamp: str) -> int:
    hours, minutes, seconds = (int(part) for part in timestamp.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def _timestamp_url(url: str, start_seconds: Optional[int]) -> str:
    if not url or start_seconds is None:
        return url
    return f"{url}{'&' if '?' in url else '?'}t={start_seconds}s"


def _is_promotional_turn(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in PROMOTIONAL_MARKERS)


def _episode_metadata(file_meta: dict, frontmatter: dict[str, Any]) -> dict[str, Any]:
    """Normalize repository frontmatter and retain it as source provenance."""
    title = _metadata_text(frontmatter.get("title") or frontmatter.get("episode_title")) or "Unknown Episode"
    guest = _metadata_text(frontmatter.get("guest") or frontmatter.get("guest_name")) or "Unknown Guest"
    youtube_url = _metadata_text(frontmatter.get("youtube_url"))
    episode_url = youtube_url or _metadata_text(
        frontmatter.get("url") or frontmatter.get("episode_url") or frontmatter.get("link")
    )
    source_metadata = json.loads(json.dumps(frontmatter, default=str))
    source_metadata.update(
        {
            "github_url": file_meta.get("github_url", ""),
            "raw_url": file_meta.get("download_url", ""),
            "git_sha": file_meta.get("sha", ""),
            "file_path": file_meta.get("path", ""),
            "episode_slug": file_meta.get("path", "").split("/")[-2] if "/" in file_meta.get("path", "") else "",
        }
    )
    return {
        "episode_title": title,
        "guest_name": guest,
        "episode_url": episode_url,
        "source_metadata": source_metadata,
    }


def _chunk_transcript(body: str, episode: dict[str, Any]) -> list[dict[str, Any]]:
    """Chunk on speaker turns, retaining timestamps and avoiding sponsor copy."""
    matches = list(SPEAKER_TURN_PATTERN.finditer(body))
    fallback_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )

    def make_chunk(parts: list[dict[str, Any]], text: str) -> dict[str, Any]:
        start_seconds = parts[0]["start_seconds"] if parts else None
        end_seconds = parts[-1]["start_seconds"] if parts else None
        speakers = list(dict.fromkeys(part["speaker"] for part in parts))
        source_metadata = dict(episode["source_metadata"])
        source_metadata.update(
            {
                "speakers": speakers,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "timestamp_url": _timestamp_url(episode["episode_url"], start_seconds),
            }
        )
        keywords = source_metadata.get("keywords", [])
        keyword_text = ", ".join(str(item) for item in keywords) if isinstance(keywords, list) else str(keywords)
        index_topics = source_metadata.get("index_topics", [])
        index_topic_text = ", ".join(str(item) for item in index_topics) if isinstance(index_topics, list) else str(index_topics)
        document = Document(
            page_content=text.strip(),
            metadata={
                "episode": episode["episode_title"],
                "guest": episode["guest_name"],
                "source": episode["episode_url"],
                **source_metadata,
            },
        )
        return {
            "episode_title": episode["episode_title"],
            "guest_name": episode["guest_name"],
            "episode_url": episode["episode_url"],
            "chunk_text": document.page_content,
            # Titles/topics help semantic matching without polluting the cited excerpt.
            "embedding_text": (
                f"Episode: {episode['episode_title']}\nGuest: {episode['guest_name']}\n"
                f"Topics: {keyword_text}\nIndex topics: {index_topic_text}\nTranscript:\n{text.strip()}"
            ),
            "source_metadata": source_metadata,
        }

    if not matches:
        cleaned = re.sub(r"^#.*?\n", "", body, count=1).strip()
        cleaned = re.sub(r"^##\s+Transcript\s*", "", cleaned, flags=re.IGNORECASE).strip()
        return [make_chunk([], part) for part in fallback_splitter.split_text(cleaned) if len(part.strip()) >= 50]

    turns: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        text = body[match.end():next_start].strip()
        if not text or _is_promotional_turn(text):
            continue
        turns.append(
            {
                "speaker": match.group("speaker").strip(),
                "start_seconds": _timestamp_to_seconds(match.group("timestamp")),
                "text": f"{match.group('speaker').strip()} ({match.group('timestamp')}): {text}",
            }
        )

    chunks: list[dict[str, Any]] = []
    current_turns: list[dict[str, Any]] = []
    current_texts: list[str] = []
    current_length = 0

    def flush() -> None:
        nonlocal current_turns, current_texts, current_length
        if current_texts:
            chunks.append(make_chunk(current_turns, "\n\n".join(current_texts)))
        current_turns, current_texts, current_length = [], [], 0

    for turn in turns:
        turn_text = turn["text"]
        if len(turn_text) > settings.CHUNK_SIZE:
            flush()
            for part in fallback_splitter.split_text(turn_text):
                if len(part.strip()) >= 50:
                    chunks.append(make_chunk([turn], part))
            continue
        if current_texts and current_length + len(turn_text) + 2 > settings.CHUNK_SIZE:
            flush()
        current_turns.append(turn)
        current_texts.append(turn_text)
        current_length += len(turn_text) + 2
    flush()
    return chunks


async def _fetch_transcript_list(client: httpx.AsyncClient) -> list[dict]:
    """Discover only canonical transcript files with one GitHub tree request."""
    base_path = settings.TRANSCRIPTS_GITHUB_PATH.strip("/")
    ref = settings.TRANSCRIPTS_GITHUB_BRANCH
    tree_url = f"{GITHUB_API_BASE}/repos/{settings.TRANSCRIPTS_GITHUB_REPO}/git/trees/{ref}?recursive=1"
    pattern = re.compile(rf"^{re.escape(base_path)}/[^/]+/transcript\.(?:md|txt)$", re.IGNORECASE)
    try:
        response = await client.get(tree_url, timeout=30)
        response.raise_for_status()
        files = []
        for item in response.json().get("tree", []):
            path = item.get("path", "")
            if item.get("type") != "blob" or not pattern.match(path):
                continue
            files.append(
                {
                    "path": path,
                    "name": path.rsplit("/", 1)[-1],
                    "sha": item.get("sha", ""),
                    "download_url": f"{GITHUB_RAW_BASE}/{settings.TRANSCRIPTS_GITHUB_REPO}/{ref}/{path}",
                    "github_url": f"{GITHUB_WEB_BASE}/{settings.TRANSCRIPTS_GITHUB_REPO}/blob/{ref}/{path}",
                }
            )
        if files:
            return sorted(files, key=lambda item: item["path"])
        logger.warning("GitHub tree returned no transcript files below %s", base_path)
    except Exception as exc:
        logger.warning("Could not fetch transcript tree from GitHub: %s", exc)
    return []


async def _fetch_index_topics(client: httpx.AsyncClient) -> dict[str, list[str]]:
    """Build episode-slug topic metadata from the repository's index files."""
    tree_url = f"{GITHUB_API_BASE}/repos/{settings.TRANSCRIPTS_GITHUB_REPO}/git/trees/{settings.TRANSCRIPTS_GITHUB_BRANCH}?recursive=1"
    try:
        response = await client.get(tree_url, timeout=30)
        response.raise_for_status()
        index_files = [
            item for item in response.json().get("tree", [])
            if item.get("type") == "blob"
            and re.match(r"^index/[^/]+\.md$", item.get("path", ""), re.IGNORECASE)
            and item.get("path", "").lower() != "index/readme.md"
        ]
        topics_by_slug: dict[str, list[str]] = {}
        for item in index_files:
            raw_url = f"{GITHUB_RAW_BASE}/{settings.TRANSCRIPTS_GITHUB_REPO}/{settings.TRANSCRIPTS_GITHUB_BRANCH}/{item['path']}"
            try:
                index_response = await client.get(raw_url, timeout=60)
                index_response.raise_for_status()
            except Exception as exc:
                logger.warning("Failed to download index file %s: %s", item["path"], exc)
                continue
            topic = item["path"].rsplit("/", 1)[-1][:-3]
            for slug in re.findall(r"\.\./episodes/([^/]+)/transcript\.md", index_response.text):
                topics_by_slug.setdefault(slug, []).append(topic)
        return {slug: sorted(set(topics)) for slug, topics in topics_by_slug.items()}
    except Exception as exc:
        logger.warning("Could not fetch topic index from GitHub: %s", exc)
        return {}


async def _fetch_raw_content(client: httpx.AsyncClient, file_meta: dict) -> Optional[str]:
    try:
        response = await client.get(file_meta["download_url"], timeout=60)
        response.raise_for_status()
        return response.text
    except Exception as exc:
        logger.warning("Failed to download %s: %s", file_meta.get("path"), exc)
        return None


async def _generate_embeddings(texts: list[str]) -> list[Optional[list[float]]]:
    if not settings.gemini_available:
        return [None] * len(texts)
    for model_id in settings.gemini_embed_model_candidates:
        try:
            embeddings = GoogleGenerativeAIEmbeddings(
                model=model_id,
                google_api_key=settings.GEMINI_API_KEY,
            )
            values = await asyncio.to_thread(embeddings.embed_documents, texts)
            if all(len(value) == settings.VECTOR_DIMENSIONS for value in values):
                return [list(value) for value in values]
            logger.warning("Embedding model %s returned an unexpected vector dimension", model_id)
        except Exception as exc:
            logger.warning("Embedding request failed for %s: %s", model_id, exc)
    return [None] * len(texts)


async def _get_existing_docs_from_db() -> dict[str, str]:
    if not settings.db_available:
        return {}
    try:
        from app.db.database import get_session_factory
        from sqlalchemy import text

        factory = get_session_factory()
        if factory is None:
            return {}
        async with factory() as session:
            result = await session.execute(text("SELECT file_path, content_hash FROM knowledge_documents WHERE is_active = true"))
            return {row.file_path: row.content_hash for row in result.fetchall()}
    except Exception as exc:
        logger.warning("Could not fetch existing knowledge documents: %s", exc)
        return {}


async def _upsert_document_and_chunks_to_db(doc_data: dict, chunks: list[dict]) -> None:
    if not settings.db_available:
        return
    try:
        from app.db.database import get_session_factory
        from sqlalchemy import text

        factory = get_session_factory()
        if factory is None:
            return
        async with factory() as session:
            await session.execute(
                text("""
                    INSERT INTO knowledge_documents
                        (id, file_path, content_hash, episode_title, guest_name, source_url, source_metadata, is_active, created_at, updated_at)
                    VALUES
                        (:id, :file_path, :content_hash, :episode_title, :guest_name, :source_url, CAST(:source_metadata AS jsonb), true, NOW(), NOW())
                    ON CONFLICT (file_path) DO UPDATE SET
                        content_hash = EXCLUDED.content_hash,
                        episode_title = EXCLUDED.episode_title,
                        guest_name = EXCLUDED.guest_name,
                        source_url = EXCLUDED.source_url,
                        source_metadata = EXCLUDED.source_metadata,
                        is_active = true,
                        updated_at = NOW()
                """),
                {**doc_data, "id": str(uuid.uuid4()), "source_metadata": json.dumps(doc_data["source_metadata"])},
            )
            result = await session.execute(text("SELECT id FROM knowledge_documents WHERE file_path = :path"), {"path": doc_data["file_path"]})
            row = result.fetchone()
            if not row:
                raise RuntimeError("Document upsert did not return an id")
            document_id = str(row[0])
            await session.execute(text("DELETE FROM transcript_chunks WHERE file_path = :path"), {"path": doc_data["file_path"]})
            for chunk in chunks:
                embedding = chunk.get("embedding")
                vector = "[" + ",".join(str(value) for value in embedding) + "]" if embedding else None
                await session.execute(
                    text("""
                        INSERT INTO transcript_chunks
                            (id, document_id, file_path, episode_title, guest_name, episode_url, chunk_text, chunk_index, source_metadata, embedding, created_at)
                        VALUES
                            (:id, :document_id, :file_path, :episode_title, :guest_name, :episode_url, :chunk_text, :chunk_index,
                             CAST(:source_metadata AS jsonb), CAST(:embedding AS vector), NOW())
                    """),
                    {
                        "id": str(uuid.uuid4()), "document_id": document_id, "file_path": doc_data["file_path"],
                        "episode_title": chunk["episode_title"], "guest_name": chunk["guest_name"],
                        "episode_url": chunk["episode_url"], "chunk_text": chunk["chunk_text"],
                        "chunk_index": chunk["chunk_index"], "source_metadata": json.dumps(chunk["source_metadata"]), "embedding": vector,
                    },
                )
            await session.commit()
    except Exception as exc:
        logger.error("Document/chunk upsert failed for %s: %s", doc_data["file_path"], exc)


async def _deactivate_deleted_docs_in_db(current_file_paths: set[str]) -> int:
    if not settings.db_available:
        return 0
    try:
        from app.db.database import get_session_factory
        from sqlalchemy import text

        factory = get_session_factory()
        if factory is None:
            return 0
        async with factory() as session:
            result = await session.execute(text("SELECT file_path FROM knowledge_documents WHERE is_active = true"))
            removed = [row[0] for row in result.fetchall() if row[0] not in current_file_paths]
            for path in removed:
                await session.execute(text("DELETE FROM transcript_chunks WHERE file_path = :path"), {"path": path})
                await session.execute(text("UPDATE knowledge_documents SET is_active = false WHERE file_path = :path"), {"path": path})
            await session.commit()
            return len(removed)
    except Exception as exc:
        logger.error("Database cleanup for deleted documents failed: %s", exc)
        return 0


async def run_ingest() -> dict:
    """Synchronize canonical episode transcripts into the retrieval store."""
    if _sync_state["syncing"]:
        return {"error": "Sync already in progress"}
    _sync_state["syncing"] = True
    _sync_state["processed_episodes"] = 0
    _sync_state["total_episodes"] = 0
    stats = {"added": 0, "updated": 0, "unchanged": 0, "deleted": 0, "total_chunks": 0, "errors": 0}
    current_paths: set[str] = set()
    refreshed_chunks: list[dict] = []
    try:
        existing_docs = await _get_existing_docs_from_db()
        async with httpx.AsyncClient(headers={"User-Agent": "LennyGrowthAssistant/1.0"}, follow_redirects=True) as client:
            files = await _fetch_transcript_list(client)
            topics_by_slug = await _fetch_index_topics(client)
            if settings.INGEST_MAX_EPISODES > 0:
                files = files[:settings.INGEST_MAX_EPISODES]
            _sync_state["total_episodes"] = len(files)
            for file_meta in files:
                file_path = file_meta["path"]
                current_paths.add(file_path)
                raw = await _fetch_raw_content(client, file_meta)
                if not raw:
                    stats["errors"] += 1
                    continue
                episode_slug = file_path.split("/")[-2] if "/" in file_path else ""
                index_topics = topics_by_slug.get(episode_slug, [])
                content_hash = _compute_hash(raw, index_topics)
                if file_path in existing_docs and existing_docs[file_path] == content_hash:
                    stats["unchanged"] += 1
                    continue
                frontmatter, body = _split_frontmatter(raw)
                episode = _episode_metadata(file_meta, frontmatter)
                episode_slug = episode["source_metadata"].get("episode_slug", "")
                index_topics = topics_by_slug.get(episode_slug, [])
                episode["source_metadata"].update(
                    {
                        "index_topics": index_topics,
                        "index_topic_count": len(index_topics),
                        "index_url": f"{GITHUB_WEB_BASE}/{settings.TRANSCRIPTS_GITHUB_REPO}/tree/{settings.TRANSCRIPTS_GITHUB_BRANCH}/index",
                    }
                )
                chunks = _chunk_transcript(body, episode)
                embedding_texts = []
                for index, chunk in enumerate(chunks):
                    chunk["file_path"] = file_path
                    chunk["chunk_index"] = index
                    embedding_texts.append(chunk.pop("embedding_text"))
                # One provider request per episode is substantially faster and
                # avoids constructing a new embedding client for every chunk.
                embeddings = await _generate_embeddings(embedding_texts) if settings.db_available else [None] * len(chunks)
                for chunk, embedding in zip(chunks, embeddings):
                    chunk["embedding"] = embedding
                refreshed_chunks.extend(chunks)
                stats["total_chunks"] += len(chunks)
                await _upsert_document_and_chunks_to_db(
                    {
                        "file_path": file_path, "content_hash": content_hash, "episode_title": episode["episode_title"],
                        "guest_name": episode["guest_name"], "source_url": episode["episode_url"],
                        "source_metadata": episode["source_metadata"],
                    }, chunks,
                )
                stats["updated" if file_path in existing_docs else "added"] += 1
                _sync_state["processed_episodes"] += 1
        stats["deleted"] = await _deactivate_deleted_docs_in_db(current_paths)
        if not settings.db_available:
            all_chunk_data.clear()
            all_chunk_data.extend(refreshed_chunks)
        _sync_state.update(
            {
                "initialized": bool(current_paths), "episode_count": len(current_paths), "chunk_count": len(refreshed_chunks),
                "last_sync_at": datetime.now(timezone.utc).isoformat(), "last_sync_stats": stats,
                "processed_episodes": len(current_paths), "total_episodes": len(files),
            }
        )
        return {"status": "completed", "episodes_processed": len(current_paths), "stats": stats, "last_sync_at": _sync_state["last_sync_at"]}
    except Exception as exc:
        logger.exception("Knowledge ingestion failed")
        stats["errors"] += 1
        _sync_state["last_sync_stats"] = stats
        return {"status": "failed", "error": str(exc), "stats": stats}
    finally:
        _sync_state["syncing"] = False


async def check_and_auto_ingest() -> None:
    """Trigger a first sync only when the persistent knowledge base is empty."""
    count = 0
    if settings.db_available:
        try:
            from app.db.database import get_session_factory
            from sqlalchemy import text

            factory = get_session_factory()
            if factory:
                async with factory() as session:
                    count = (await session.execute(text("SELECT count(*) FROM transcript_chunks"))).scalar() or 0
        except Exception as exc:
            logger.warning("Could not check transcript chunk count: %s", exc)
    if count == 0 and not all_chunk_data:
        asyncio.create_task(run_ingest())
