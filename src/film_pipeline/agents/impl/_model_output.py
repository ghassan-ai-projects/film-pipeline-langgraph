"""Shared model-output parsing for the bible agents.

Bible agents receive free-form LLM output that may arrive as a raw JSON
string or an already-parsed dict, optionally wrapped under the agent's own
artifact key or the generic ``data``/``output`` keys. Section fields inside
that payload are coerced to their container type so malformed sections
collapse to empty instead of raising.
"""

from __future__ import annotations

import json
from typing import Any


def normalize_model_output(model_output: dict[str, Any] | str, artifact_key: str) -> dict[str, Any]:
    """Parse raw JSON strings and unwrap the payload nested under ``artifact_key``."""
    if isinstance(model_output, str):
        try:
            model_output = json.loads(model_output)
        except (json.JSONDecodeError, TypeError):
            return {}
    if not isinstance(model_output, dict):
        return {}
    for key in (artifact_key, "data", "output"):
        candidate = model_output.get(key)
        if isinstance(candidate, dict):
            return candidate
    return model_output


def as_dict(value: Any) -> dict[str, Any]:
    """Coerce an optional or mistyped section to an empty dict."""
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    """Coerce an optional or mistyped section to an empty list."""
    if not isinstance(value, list):
        return []
    return value
