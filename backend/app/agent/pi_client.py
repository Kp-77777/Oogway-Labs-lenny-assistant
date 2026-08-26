"""HTTP client for the persistent Pi Agent service."""
import logging
import os

import httpx

logger = logging.getLogger(__name__)


async def run_pi_agent(user_message: str, provider: str, history: list[dict]) -> dict:
    """Send one request to the persistent Pi service and return structured JSON."""
    base_url = os.getenv("PI_AGENT_URL", "http://127.0.0.1:8001").rstrip("/")
    payload = {"message": user_message, "provider": provider, "history": history[-12:]}
    try:
        async with httpx.AsyncClient(timeout=float(os.getenv("PI_AGENT_TIMEOUT_SECONDS", "180"))) as client:
            response = await client.post(f"{base_url}/chat", json=payload)
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"Pi Agent service unavailable: {exc}") from exc
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "Pi Agent returned an error"))
    return result
