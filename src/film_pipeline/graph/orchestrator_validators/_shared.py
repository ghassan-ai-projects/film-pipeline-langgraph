"""Shared issue constructors and row/scene extraction helpers."""

from __future__ import annotations

from typing import Any

from film_pipeline.schemas._base import IssueSeverity


def _blocking(code: str, message: str) -> dict[str, Any]:
    return {"severity": IssueSeverity.BLOCKING.value, "code": code, "message": message}


def _row_attr(row: Any, key: str, default: Any = None) -> Any:
    """Read a field from a row, handling both dict and object rows.

    Gate validators receive rows that may be Pydantic models (from mock
    executions) or plain dicts (from artifact store deserialization).
    ``getattr`` only works on objects; dicts need ``.get()``.
    """
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _blocking_with_id(issue_id: str, code: str, message: str) -> dict[str, Any]:
    return {"issue_id": issue_id, **_blocking(code, message)}


def _extract_rows(value: Any) -> list[Any]:
    """Return row-like values from a matrix object or dict."""
    if hasattr(value, "rows"):
        rows = value.rows
        return list(rows) if isinstance(rows, list) else []
    if isinstance(value, dict):
        rows = value.get("rows", [])
        return rows if isinstance(rows, list) else []
    return []


def _extract_scene_ids(script: Any) -> set[str]:
    """Extract scene IDs from Script/StoryBible-like objects and dicts."""
    if hasattr(script, "scenes"):
        scenes = script.scenes
        return {
            str(_row_attr(scene, "scene_id", ""))
            for scene in scenes
            if str(_row_attr(scene, "scene_id", ""))
        }
    if not isinstance(script, dict):
        return set()

    candidates: list[Any] = []
    raw_scenes = script.get("scenes", [])
    if isinstance(raw_scenes, list):
        candidates.extend(raw_scenes)
    scene_list = script.get("scene_list", {})
    if isinstance(scene_list, dict):
        nested = scene_list.get("scenes", [])
        if isinstance(nested, list):
            candidates.extend(nested)
    return {
        str(_row_attr(scene, "scene_id", ""))
        for scene in candidates
        if str(_row_attr(scene, "scene_id", ""))
    }
