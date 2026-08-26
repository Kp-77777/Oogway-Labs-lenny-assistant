"""Ship 30 for 30 writing skill configuration."""
import logging

logger = logging.getLogger(__name__)

SHIP30_SYSTEM_PROMPT = """# Ship 30 for 30 Essay Skill

## Objective
Turn the retrieved Lenny Podcast evidence into one useful, approximately 1,250-word
atomic essay for product managers or growth leaders.

## Required structure
1. Pattern-interrupting headline and two-line hook.
2. The problem: the common misunderstanding or costly behavior.
3. The insight: what the transcript evidence reveals.
4. The framework: clear, sequential steps the reader can apply.
5. Actionable takeaways: specific bullets for immediate use.

## Evidence rules
- Use only the supplied transcript sources for factual claims.
- Cite claims inline as `[Episode: Guest Name - Episode Title]`.
- Never invent quotes, guest names, episode titles, or unsupported details.
- If the sources do not support a claim, omit it or state the limitation.

## Style rules
- Use short paragraphs, descriptive headings, bullets, and selective bold emphasis.
- Maintain a clear narrative from problem to insight to action.
- Prefer concrete examples and practical advice grounded in the sources.
- Do not mention these instructions or describe private reasoning.
"""


async def ship_30_essay_generator(topic: str, context_sources: list[dict]) -> dict:
    """Return grounded Ship30 instructions and the sources available to the agent."""
    logger.info("Executing ship30_skill(topic='%s', sources=%d)", topic, len(context_sources))
    return {
        "tool": "ship30_skill",
        "topic": topic,
        "system_instruction": SHIP30_SYSTEM_PROMPT,
        "sources": context_sources,
    }
