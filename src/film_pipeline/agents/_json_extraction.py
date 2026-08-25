"""JSON recovery for model responses — parse objects out of noisy LLM text.

Models wrap JSON in markdown fences, prepend analysis prose, or append
trailing commentary. ``extract_json_object`` applies the four recovery
strategies in order and returns the first successful mapping, or ``None``
when none of them yield one.
"""

from __future__ import annotations

import json
from typing import Any


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Return the first mapping recovered from ``text``, or ``None``."""
    for extract in (
        _parse_direct_json,
        _parse_fenced_json,
        _parse_braced_json,
        _parse_bracketed_json,
    ):
        extracted = extract(text)
        if extracted is not None:
            return extracted
    return None


def _parse_direct_json(text: str) -> dict[str, Any] | None:
    """Strategy 1: direct JSON parse."""
    try:
        return dict(json.loads(text))
    except json.JSONDecodeError:
        return None


def _parse_fenced_json(text: str) -> dict[str, Any] | None:
    """Strategy 2: extract from markdown fences (most common with Gemini)."""
    for fence_start in ("```json", "```JSON", "```"):
        if fence_start not in text:
            continue
        # Find the LAST opening fence and FIRST closing fence after it
        # (Gemini sometimes has multiple code blocks)
        last_open = text.rfind(fence_start)
        block = text[last_open + len(fence_start) :]
        close_idx = block.find("```")
        if close_idx != -1:
            block = block[:close_idx]
        candidate = block.strip()
        if not candidate:
            continue
        # Handle Gemini injecting trailing content right after closing ````
        try:
            result: Any = json.loads(candidate)
            return dict(result)
        except json.JSONDecodeError:
            pass
    return None


def _parse_braced_json(text: str) -> dict[str, Any] | None:
    """Strategy 3: find the outermost brace pair anywhere in text."""
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        candidate = text[brace_start : brace_end + 1]
        try:
            result = json.loads(candidate)
            return dict(result)
        except json.JSONDecodeError:
            pass
    return None


def _parse_bracketed_json(text: str) -> dict[str, Any] | None:
    """Strategy 4: find outermost bracket pair (for array responses)."""
    bracket_start = text.find("[")
    bracket_end = text.rfind("]")
    if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
        candidate = text[bracket_start : bracket_end + 1]
        try:
            result = json.loads(candidate)
            return dict(result)
        except (json.JSONDecodeError, TypeError):
            pass
    return None
