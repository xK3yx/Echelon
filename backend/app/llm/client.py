"""
Async httpx wrapper for the Groq chat-completions API.

All calls log: model, message count, temperature, max_tokens, latency,
prompt/completion token counts, and validation outcome (set by callers).
Never fabricates output — raises GroqError when the key is missing or the
API returns a non-200 status.
"""

import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.groq.com/openai/v1"


# Reasoning models spend completion tokens on hidden reasoning before they
# answer. Without headroom, a small max_tokens budget can be used up entirely
# by reasoning and return an empty answer, so keep reasoning short and add room.
_REASONING_HEADROOM = 1024


def _model_options(model: str, max_tokens: int) -> dict:
    if model.startswith("openai/gpt-oss"):
        return {"max_tokens": max_tokens + _REASONING_HEADROOM, "reasoning_effort": "low"}
    if model.startswith("qwen/qwen3"):
        return {"max_tokens": max_tokens + _REASONING_HEADROOM, "reasoning_effort": "none"}
    return {"max_tokens": max_tokens}


class GroqError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


async def chat_completion(
    *,
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    response_format: dict | None = None,
) -> dict:
    """
    Sends a single chat-completion request to Groq and returns the raw
    parsed response dict (the full API envelope, not just the content string).

    Raises:
        GroqError(400, ...) — GROQ_API_KEY not configured
        GroqError(status, ...) — non-200 HTTP response from Groq
        httpx.TimeoutException — request timed out (caller decides retry)
    """
    if not settings.groq_api_key:
        raise GroqError(
            400,
            "GROQ_API_KEY is not configured. Set it in your .env file.",
        )

    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        **_model_options(model, max_tokens),
    }
    if response_format:
        payload["response_format"] = response_format

    logger.info(
        "groq_request | model=%s | messages=%d | temperature=%.2f | max_tokens=%d",
        model,
        len(messages),
        temperature,
        payload["max_tokens"],
    )

    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    elapsed = time.monotonic() - t0

    if resp.status_code != 200:
        logger.error(
            "groq_error | status=%d | body=%.500s",
            resp.status_code,
            resp.text,
        )
        raise GroqError(resp.status_code, f"Groq API returned {resp.status_code}")

    data = resp.json()
    # Callers index choices[0].message.content directly; normalise a null
    # content (possible when a reasoning model runs out of tokens) to "".
    for choice in data.get("choices", []):
        message = choice.get("message") or {}
        if message.get("content") is None:
            message["content"] = ""
    usage = data.get("usage", {})
    logger.info(
        "groq_response | latency=%.2fs | prompt_tokens=%s | completion_tokens=%s",
        elapsed,
        usage.get("prompt_tokens", "?"),
        usage.get("completion_tokens", "?"),
    )

    return data
