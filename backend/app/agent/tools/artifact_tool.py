"""Artifact tool for HTML/CSS and Markdown outputs."""
import logging

logger = logging.getLogger(__name__)


async def artifact_builder(
    title: str,
    artifact_type: str,
    html_code: str = "",
    content: str | None = None,
) -> dict:
    """Build a structured artifact payload for the frontend viewer.

    ``html_code`` remains supported for existing callers; ``content`` is the
    public create_artifact tool argument and works for both HTML and Markdown.
    """
    logger.info(
        "Executing artifact_builder(title='%s', type='%s')",
        title,
        artifact_type,
    )
    artifact_content = content if content is not None else html_code
    return {
        "tool": "artifact_builder",
        "title": title,
        "type": artifact_type,
        "html": (
            f"<!-- ARTIFACT_TITLE: {title} -->\n"
            f"<!-- ARTIFACT_START -->\n{artifact_content}\n"
            "<!-- ARTIFACT_END -->"
        ),
    }


async def create_artifact(
    artifact_type: str,
    content: str,
    title: str = "Generated Artifact",
) -> dict:
    """Public agent tool name for creating an HTML or Markdown artifact."""
    return await artifact_builder(
        title=title,
        artifact_type=artifact_type,
        content=content,
    )
