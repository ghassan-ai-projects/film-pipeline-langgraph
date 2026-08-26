"""Runtime environment overrides for resolved profile configs."""

from __future__ import annotations

import os
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

OverridePath = tuple[str, ...]

ENV_OVERRIDE_MAP: Mapping[str, OverridePath] = {
    "FILM_PIPELINE_QUALITY": ("quality_profile",),
    "FILM_PIPELINE_MAX_SCENES": ("limits", "max_scenes"),
    "FILM_PIPELINE_SKIP_VISUAL_DEV": ("studio", "skip_visual_dev"),
    # Lands in resolved_config["model_profiles"]["creative_writer"]["primary"],
    # which _model_overrides_for() feeds to ModelRouter.resolve_model_params().
    "FILM_PIPELINE_MODEL_OVERRIDE": ("model_profiles", "creative_writer", "primary"),
    "FILM_PIPELINE_MAX_CONTEXT_CHARS": ("context", "max_chars_per_artifact"),
    "FILM_PIPELINE_SEARCH_API": ("generation", "search_api"),
    "FILM_PIPELINE_APPROVAL_MODE": ("studio", "require_human_approval"),
}


def apply_runtime_overrides(
    config: dict[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Apply supported environment overrides after profile merging.

    The input config is not mutated. Overrides are intentionally allowlisted so
    environment state cannot silently create arbitrary config paths.
    """
    env = os.environ if environ is None else environ
    resolved = deepcopy(config)
    for env_var, path in ENV_OVERRIDE_MAP.items():
        raw_value = env.get(env_var)
        if raw_value is None:
            continue
        value = _coerce_value(raw_value)
        if path == ("quality_profile",) and isinstance(value, str):
            value = value.removeprefix("quality.")
        _set_nested(resolved, path, value)
    return resolved


def _set_nested(config: dict[str, Any], path: OverridePath, value: Any) -> None:
    current = config
    for key in path[:-1]:
        nested = current.get(key)
        if not isinstance(nested, dict):
            nested = {}
            current[key] = nested
        current = nested
    current[path[-1]] = value


def _coerce_value(value: str) -> Any:
    normalized = value.strip()
    lower = normalized.lower()
    if lower in {"true", "yes", "1", "on"}:
        return True
    if lower in {"false", "no", "0", "off"}:
        return False
    try:
        return int(normalized)
    except ValueError:
        pass
    try:
        return float(normalized)
    except ValueError:
        return value
