"""FastAPI facade for the persistent Pi Agent service."""
import logging
import re
from typing import Optional

from app.agent.pi_client import run_pi_agent
from app.agent.tools.artifact_tool import artifact_builder
from app.core.config import settings

logger = logging.getLogger(__name__)


def _response_type(content: str, artifact_html: Optional[str]) -> str:
    if artifact_html or "```html" in content or "```markdown" in content:
        return "artifact"
    return "essay" if len(content.split()) > 600 else "answer"


def _extract_artifact(content: str) -> tuple[str, str, str]:
    title = (re.search(r"<!-- ARTIFACT_TITLE:\s*(.+?)\s*-->", content) or [None, "Generated Artifact"])[1]
    match = re.search(r"<!-- ARTIFACT_START -->(.*?)<!-- ARTIFACT_END -->", content, re.DOTALL)
    if match:
        return title, match.group(1).strip(), "html"
    match = re.search(r"```html\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
    if match:
        return title, match.group(1).strip(), "html"
    match = re.search(r"```markdown\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
    if match:
        return title, match.group(1).strip(), "markdown"
    return title, content, "html"


class AgentEngine:
    """Single Pi Agent orchestration boundary used by FastAPI."""

    async def run(self, user_message: str, provider: str = "cloud", history: Optional[list[dict]] = None) -> dict:
        provider = provider.lower() if provider else "cloud"
        if provider not in {"cloud", "ollama"}:
            provider = "cloud"
        try:
            result = await run_pi_agent(user_message, provider, history or [])
        except Exception as exc:
            logger.exception("Pi Agent failed")
            return {
                "response": f"Agent error: {exc}", "response_type": "answer", "sources": [],
                "artifact_title": None, "artifact_html": None, "provider": provider,
                "model": settings.OLLAMA_MODEL if provider == "ollama" else settings.GEMINI_CHAT_MODEL,
                "tools_executed": [],
            }
        response = result.get("response", "")
        artifact_html = result.get("artifact_html")
        artifact_title = result.get("artifact_title")
        if not artifact_html and _response_type(response, None) == "artifact":
            artifact_title, content, artifact_type = _extract_artifact(response)
            artifact_html = (await artifact_builder(artifact_title, artifact_type, content))["html"]
        return {
            **result,
            "response_type": _response_type(response, artifact_html),
            "artifact_title": artifact_title,
            "artifact_html": artifact_html,
        }


agent = AgentEngine()
