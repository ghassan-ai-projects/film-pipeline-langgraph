"""z.ai (GLM) OpenAI-compatible chat-completions transport.

z.ai speaks the same wire format as OpenRouter, so this module reuses
``ChatRequest`` and ``chat_completions_payload`` from
``transports.chat_completions`` and adds only what is z.ai-specific: the
``zai/`` model prefix, the two-endpoint base-URL allowlist, and key resolution.

The allowlist is a security boundary: an unvetted ``ZAI_BASE_URL`` would send
the bearer token to an arbitrary host, so the override is rejected unless it is
one of the two known endpoints over ``https``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from urllib.parse import urlsplit

from film_pipeline.agents.transports.chat_completions import (
    ChatRequest,
    chat_completions_payload,
)
from film_pipeline.providers.credentials import env_or_dotenv, lookup
from film_pipeline.providers.http_transport import post_json

ZAI_MODEL_PREFIX = "zai/"
ZAI_API_BASE = "https://api.z.ai/api/paas/v4"
ZAI_CODING_API_BASE = "https://api.z.ai/api/coding/paas/v4"
ZAI_ERROR_PREFIX = "z.ai chat completions failed"
_ALLOWED_ZAI_BASE_URLS = frozenset({ZAI_API_BASE, ZAI_CODING_API_BASE})


def zai_api_key(configured_api_key: str | None) -> str:
    """Resolve the z.ai key, preferring the constructor-supplied value."""
    key = configured_api_key or lookup("zai")
    if not key:
        raise RuntimeError(
            "ZAI_API_KEY is not set. Set it in the environment or in a local .env file."
        )
    return key


def zai_base_url() -> str:
    """Resolve the z.ai API base URL.

    ``ZAI_BASE_URL`` (environment or local ``.env``) overrides the default.
    Coding-plan keys only work against the coding endpoint:
    ``https://api.z.ai/api/coding/paas/v4`` — against the standard endpoint
    they fail with error 1113 (insufficient balance).
    """
    override = env_or_dotenv("ZAI_BASE_URL")
    base_url = (override or ZAI_API_BASE).rstrip("/")
    parsed = urlsplit(base_url)
    if base_url not in _ALLOWED_ZAI_BASE_URLS or parsed.scheme != "https":
        allowed = " or ".join(sorted(_ALLOWED_ZAI_BASE_URLS))
        raise RuntimeError(f"ZAI_BASE_URL must be {allowed}.")
    return base_url


def send_zai_chat_completion(
    request: ChatRequest,
    *,
    http_opener: Any,
    timeout_seconds: float | None,
    api_key: str,
) -> dict[str, Any]:
    """POST a chat-completion request to z.ai, stripping the ``zai/`` prefix."""
    wire_request = replace(request, model=request.model.removeprefix(ZAI_MODEL_PREFIX))
    return post_json(
        f"{zai_base_url()}/chat/completions",
        chat_completions_payload(wire_request, include_frequency_penalty=False),
        http_opener=http_opener,
        timeout_seconds=timeout_seconds,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        error_prefix=ZAI_ERROR_PREFIX,
        redact_body=True,
    )
