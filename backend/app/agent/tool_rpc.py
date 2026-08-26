"""Legacy JSON tool runner retained for direct diagnostics.

The production Pi service calls the FastAPI internal tool routes over HTTP.
"""
import asyncio
import json
import sys

from app.agent.tools.artifact_tool import artifact_builder
from app.agent.tools.rag_tool import search_knowledge
from app.agent.tools.ship30_tool import ship_30_essay_generator


async def execute(request: dict) -> dict:
    tool = request.get("tool")
    arguments = request.get("arguments") or {}

    if tool == "search_knowledge":
        results = await search_knowledge(
            query=arguments.get("query", ""),
            top_k=int(arguments.get("top_k", 6)),
        )
        return {"results": results}

    if tool == "ship30_skill":
        return await ship_30_essay_generator(
            topic=arguments.get("topic", ""),
            context_sources=arguments.get("context_sources", []),
        )

    if tool == "create_artifact":
        return await artifact_builder(
            title=arguments.get("title", "Generated Artifact"),
            artifact_type=arguments.get("type", "html"),
            content=arguments.get("content", ""),
        )

    raise ValueError(f"Unknown Pi tool: {tool}")


async def main() -> None:
    request = json.loads(sys.stdin.read())
    try:
        result = await execute(request)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise


if __name__ == "__main__":
    asyncio.run(main())
