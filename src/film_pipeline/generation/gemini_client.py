"""Shared Gemini REST client for image-review calls.

Used by frame_reviewer (per-frame validation) and sheet_reviewer (composite
validation): both send a prompt plus an inline PNG and parse a JSON verdict.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, cast

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def call_gemini(
    prompt: str,
    image_b64: str,
    model: str,
    http_opener: Any = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """POST a prompt + inline PNG to Gemini generateContent, return parsed JSON."""
    from film_pipeline.providers.credentials import lookup

    key = api_key or lookup("gemini-imagen-4")
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
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    opener = http_opener if http_opener is not None else urllib.request.build_opener()
    with opener.open(req) as resp:
        return cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))
