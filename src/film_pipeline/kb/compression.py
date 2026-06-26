"""Deterministic context compression for artifact prompt payloads."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

DEFAULT_MAX_CONTEXT_CHARS = 6000
MIN_COMPRESSED_CONTEXT_CHARS = 256
_CLIP_MARKER = "\n\n... [compressed artifact body clipped] ...\n\n"
_ID_KEY_SUFFIXES = ("_id", "_ref")
_ID_KEYS = {"id", "shot_id", "scene_id", "character_id", "location_id", "environment_id"}


class ArtifactContextDigest(BaseModel):
    """Metadata prepended to a compressed artifact context block."""

    original_chars: int = Field(ge=0)
    emitted_chars: int = Field(ge=0)
    preserved_identifiers: dict[str, list[str]] = Field(default_factory=dict)


def compact_json_context(
    data: dict[str, Any],
    *,
    max_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> str:
    """Serialize artifact content while preserving bounded prompt size.

    The compressor is intentionally deterministic and provider-free. It keeps
    JSON shape from the beginning and end of a large artifact, and promotes
    discovered identifiers into a header so downstream agents can still anchor
    references after the body is clipped.
    """
    limit = _normalize_limit(max_chars)
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)
    if len(text) <= limit:
        return text

    identifiers = _collect_identifiers(data)
    header = _format_header(
        ArtifactContextDigest(
            original_chars=len(text),
            emitted_chars=limit,
            preserved_identifiers=identifiers,
        )
    )
    if len(header) >= limit:
        return header[:limit]

    body_budget = limit - len(header)
    if body_budget <= len(_CLIP_MARKER) + 2:
        return (header + text[:body_budget])[:limit]

    available = body_budget - len(_CLIP_MARKER)
    head_chars = max(1, available * 2 // 3)
    tail_chars = max(1, available - head_chars)
    clipped = f"{text[:head_chars]}{_CLIP_MARKER}{text[-tail_chars:]}"
    return (header + clipped)[:limit]


def _normalize_limit(max_chars: int) -> int:
    return max(MIN_COMPRESSED_CONTEXT_CHARS, int(max_chars))


def _format_header(digest: ArtifactContextDigest) -> str:
    lines = [
        "[COMPRESSED ARTIFACT CONTEXT]",
        f"Original characters: {digest.original_chars}",
        f"Emitted character budget: {digest.emitted_chars}",
    ]
    if digest.preserved_identifiers:
        lines.append("Preserved identifiers:")
        for key, values in sorted(digest.preserved_identifiers.items()):
            lines.append(f"- {key}: {', '.join(values)}")
    return "\n".join(lines) + "\n\n"


def _collect_identifiers(data: Any) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}

    def visit(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, str(child_key))
            return
        if isinstance(value, list):
            for item in value:
                visit(item, key)
            return
        if not _is_identifier_key(key) or not isinstance(value, str | int):
            return
        bucket = found.setdefault(key, [])
        identifier = str(value)
        if identifier and identifier not in bucket and len(bucket) < 20:
            bucket.append(identifier)

    visit(data)
    return found


def _is_identifier_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in _ID_KEYS or lowered.endswith(_ID_KEY_SUFFIXES)
