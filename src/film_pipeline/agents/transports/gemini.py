"""Gemini ``generateContent`` transport.

Gemini does not speak the OpenAI chat-completions wire format, so this module
owns its own request value object, payload builder, URL construction (the API
key travels in the query string), and response unwrapping.

The API key rides in the URL, so the transport error prefix must never echo the
request URL — ``post_json`` is called with ``redact_body=False`` and the key is
resolved only inside ``gemini_url``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from film_pipeline.providers.credentials import lookup
from film_pipeline.providers.http_transport import post_json

GEMINI_MODEL_PREFIX = "google/"
GEMINI_API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_ERROR_PREFIX = "Gemini generateContent failed"


@dataclass(frozen=True)
class GeminiRequest:
    """Parameters for a single Gemini generateContent call."""

    prompt: str
    model: str
    images_b64: list[str]
    mime_type: str
    max_tokens: int
    temperature: float


def gemini_api_key(configured_api_key: str | None) -> str:
    """Resolve the Gemini key, preferring the constructor-supplied value."""
    key = configured_api_key or lookup("gemini-imagen-4")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is not set. Set it in the environment or .env file.")
    return key


def gemini_url(model: str, api_key: str) -> str:
    """Build the generateContent endpoint URL for ``model``."""
    gemini_model = model.removeprefix(GEMINI_MODEL_PREFIX)
    return f"{GEMINI_API_ROOT}/{gemini_model}:generateContent?key={api_key}"


def build_gemini_payload(request: GeminiRequest) -> dict[str, Any]:
    """Build the generateContent body with text plus inline image data."""
    parts: list[dict[str, Any]] = [{"text": request.prompt}]
    for img in request.images_b64:
        parts.append({"inline_data": {"mime_type": request.mime_type, "data": img}})
    return {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_tokens,
        },
    }


def first_candidate_text(response: dict[str, Any]) -> str:
    """Return the first candidate's first text part, or raise."""
    candidates: list[dict[str, Any]] = response.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")
    parts_out: list[dict[str, Any]] = candidates[0].get("content", {}).get("parts", [])
    if not parts_out:
        raise RuntimeError("Gemini returned no content parts.")
    return str(parts_out[0].get("text", ""))


def send_generate_content(
    request: GeminiRequest,
    *,
    http_opener: Any,
    timeout_seconds: float | None,
    api_key: str,
) -> str:
    """Call Gemini's generateContent API with text + inline images."""
    response = post_json(
        gemini_url(request.model, api_key),
        json.dumps(build_gemini_payload(request)).encode("utf-8"),
        http_opener=http_opener,
        timeout_seconds=timeout_seconds,
        headers={"Content-Type": "application/json"},
        error_prefix=GEMINI_ERROR_PREFIX,
        redact_body=False,
    )
    return first_candidate_text(response)
