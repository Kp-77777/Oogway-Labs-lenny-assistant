import pytest

from app.rag.ingest import _chunk_transcript, _episode_metadata, _fetch_transcript_list, _split_frontmatter


SAMPLE_TRANSCRIPT = """---
guest: Ada Chen Rekhi
title: A better product decision
youtube_url: https://www.youtube.com/watch?v=abc123
publish_date: 2023-04-21
keywords:
  - growth
  - user research
---
# A better product decision

## Transcript

Lenny (00:00:00): How do you make a better product decision with a small team?
Sponsor (00:00:12): This episode is brought to you by a company that sells software.
Ada Chen Rekhi (00:00:20): Start with a specific question, gather contextual input, and look for surprises.
Lenny (00:00:35): That makes user research more useful for a team.
"""


def test_frontmatter_and_speaker_chunks_preserve_provenance():
    frontmatter, body = _split_frontmatter(SAMPLE_TRANSCRIPT)
    episode = _episode_metadata(
        {
            "path": "episodes/ada-chen-rekhi/transcript.md",
            "sha": "abc",
            "download_url": "https://raw.example/transcript.md",
            "github_url": "https://github.example/transcript.md",
        },
        frontmatter,
    )

    chunks = _chunk_transcript(body, episode)

    assert episode["episode_title"] == "A better product decision"
    assert episode["guest_name"] == "Ada Chen Rekhi"
    assert episode["source_metadata"]["publish_date"] == "2023-04-21"
    assert chunks
    assert "This episode is brought to you" not in " ".join(chunk["chunk_text"] for chunk in chunks)
    assert chunks[0]["source_metadata"]["speakers"] == ["Lenny", "Ada Chen Rekhi"]
    assert chunks[0]["source_metadata"]["timestamp_url"].endswith("&t=0s")
    assert "Topics: growth, user research" in chunks[0]["embedding_text"]


class _MockResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "tree": [
                {"type": "blob", "path": "README.md", "sha": "readme"},
                {"type": "blob", "path": "episodes/ada-chen-rekhi/transcript.md", "sha": "ada"},
                {"type": "blob", "path": "episodes/ada-chen-rekhi/notes.md", "sha": "notes"},
                {"type": "blob", "path": "episodes/other/transcript.txt", "sha": "other"},
            ]
        }


class _MockClient:
    async def get(self, url, timeout):
        self.url = url
        return _MockResponse()


@pytest.mark.asyncio
async def test_discovery_selects_only_episode_transcripts():
    client = _MockClient()
    files = await _fetch_transcript_list(client)

    assert [item["path"] for item in files] == [
        "episodes/ada-chen-rekhi/transcript.md",
        "episodes/other/transcript.txt",
    ]
    assert "/git/trees/main?recursive=1" in client.url
