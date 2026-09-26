"""OpenRouter OpenAI-compatible chat-completions transport.

Owns the request-shaping value object and payload builder shared by every
OpenAI-compatible provider, plus the OpenRouter send path itself. The z.ai
transport reuses ``ChatRequest`` and ``chat_completions_payload`` because it
speaks the same wire format; it differs only in base URL and key resolution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from film_pipeline.providers.adapters.seedance_openrouter import OPENROUTER_API
from film_pipeline.providers.credentials import lookup
from film_pipeline.providers.http_transport import post_json

OPENROUTER_ERROR_PREFIX = "OpenRouter chat completions failed"


@dataclass(frozen=True)
class ChatRequest:
    """Request-shaping parameters for an OpenAI-compatible chat completion.

    Shared by the OpenRouter and z.ai transports — both accept this body.
    """

    messages: list[dict[str, Any]]
    model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.95
    frequency_penalty: float = 0.0


def chat_completions_payload(
    request: ChatRequest, *, include_frequency_penalty: bool = True
) -> bytes:
    """Build an OpenAI-compatible chat body for OpenRouter or z.ai."""
    body: dict[str, Any] = {
        "model": request.model,
        "messages": request.messages,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "top_p": request.top_p,
    }
    if include_frequency_penalty:
        body["frequency_penalty"] = request.frequency_penalty
    return json.dumps(body).encode()


def openrouter_api_key(configured_api_key: str | None) -> str:
    """Resolve the OpenRouter key, preferring the constructor-supplied value."""
    key = configured_api_key or lookup("seedance-openrouter")
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Set it in the environment or in a local .env file."
        )
    return key


def send_chat_completion(
    request: ChatRequest,
    *,
    http_opener: Any,
    timeout_seconds: float | None,
    api_key: str,
) -> dict[str, Any]:
    """POST a chat-completion request to OpenRouter."""
    return post_json(
        f"{OPENROUTER_API}/chat/completions",
        chat_completions_payload(request),
        http_opener=http_opener,
        timeout_seconds=timeout_seconds,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        error_prefix=OPENROUTER_ERROR_PREFIX,
        redact_body=True,
    )
