"""Gemini generateContent client for image-review calls.

Used by `generation.frame_reviewer` (per-frame validation) and
`generation.sheet_reviewer` (composite validation): both send a prompt plus an
inline PNG and parse a JSON verdict.

This is provider-adapter work — it talks to a concrete provider API and resolves
that provider's credentials — so it lives in `providers` rather than
`generation`, which owns orchestrating generation rather than calling providers.
It shares the API surface with `providers.adapters.imagen4_gemini`.

Transport goes through `providers.http_transport`, so a failed review call is
normalized into a prefixed `RuntimeError` with the key redacted instead of
leaking a raw `urllib` error whose message may carry the API key in the URL.
"""

from __future__ import annotations

import json
from typing import Any

from film_pipeline.providers.credentials import lookup
from film_pipeline.providers.http_transport import post_json

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

#: Provider id whose credential unlocks the review model.
_REVIEW_PROVIDER_ID = "gemini-imagen-4"

DEFAULT_REVIEW_TIMEOUT_SECONDS = 120.0


def call_gemini(
    prompt: str,
    image_b64: str,
    model: str,
    http_opener: Any = None,
    api_key: str | None = None,
    timeout_seconds: float | None = DEFAULT_REVIEW_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """POST a prompt plus an inline PNG to Gemini ``generateContent``.

    Returns the parsed JSON response. Raises ``RuntimeError`` with a
    ``Gemini review call`` prefix on transport or HTTP failure, with the
    credential redacted from the message.
    """
    key = api_key or lookup(_REVIEW_PROVIDER_ID)
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is not set.")

    url = f"{GEMINI_API_BASE}/{model}:generateContent?key={key}"
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": image_b64}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
    }
    try:
        return post_json(
            url,
            json.dumps(body).encode("utf-8"),
            http_opener=http_opener,
            timeout_seconds=timeout_seconds,
            headers={"Content-Type": "application/json"},
            error_prefix="Gemini review call failed",
            redact_body=True,
        )
    except RuntimeError as exc:
        # `credentials.redact` matches known key *formats*, which does not cover
        # a key the caller supplied explicitly. This key is known exactly, so
        # scrub it by value: the request URL carries it as a query parameter and
        # a provider error body often echoes it back.
        raise RuntimeError(str(exc).replace(key, "[REDACTED]")) from exc
