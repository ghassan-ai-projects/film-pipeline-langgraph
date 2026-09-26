"""Typed markdown renderers for artifact views (storage upgrade plan D9).

Each major artifact kind renders a human-readable ``current.md`` through a
registered renderer instead of the generic key-value dump. Renderers are
pure functions from the payload dict to markdown; the store calls the
registry's renderer when one is registered and falls back to the generic
render otherwise.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Renderer = Callable[[dict[str, Any]], str]


def _section(title: str, lines: list[str]) -> str:
    body = "\n".join(line for line in lines if line)
    return f"## {title}\n\n{body}\n" if body else ""


def _bullets(values: list[Any]) -> list[str]:
    return [f"- {value}" for value in values]


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    rule = "|" + "|".join("---" for _ in headers) + "|"
    body = "\n".join("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return f"{head}\n{rule}\n{body}"


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    container = payload.get(key)
    return (
        [row for row in container if isinstance(row, dict)] if isinstance(container, list) else []
    )


# --- Per-kind renderers -------------------------------------------------------


def render_script(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    title = payload.get("title")
    if title:
        parts.append(f"**Title:** {title}\n")
    scenes = payload.get("scenes", []) if isinstance(payload.get("scenes"), list) else []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        heading = scene.get("scene_heading") or scene.get("scene_id") or "Scene"
        lines = [f"### {heading}"]
        for action in scene.get("action_lines", []) or []:
            lines.append(str(action))
        for dialogue in scene.get("dialogue", []) or []:
            if isinstance(dialogue, dict):
                character = str(dialogue.get("character_id", "")).upper()
                direction = str(dialogue.get("direction", ""))
                line = str(dialogue.get("line", ""))
                lines.append(f"**{character}**{f' ({direction})' if direction else ''}: {line}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def render_prose(payload: dict[str, Any]) -> str:
    """Treatment/constitution/logline-style payloads: render text fields as prose."""
    parts: list[str] = []
    for key, value in payload.items():
        if key in {"project_id", "schema_version"}:
            continue
        if isinstance(value, str) and value:
            parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
        elif isinstance(value, list) and value and all(isinstance(item, str) for item in value):
            parts.append(_section(key.replace("_", " ").title(), _bullets(value)))
    return "\n\n".join(parts)


def render_scene_list(payload: dict[str, Any]) -> str:
    scenes = payload.get("scene_list")
    rows = _rows(scenes if isinstance(scenes, dict) else payload, "scenes") or _rows(
        payload, "scenes"
    )
    if not rows:
        return ""
    table = _table(
        ["Scene", "Dramatic Function", "Story Function", "Outcome"],
        [
            [
                scene.get("scene_id", "?"),
                scene.get("dramatic_function", ""),
                scene.get("story_function", ""),
                scene.get("outcome", ""),
            ]
            for scene in rows
        ],
    )
    return _section("Scenes", table.split("\n"))


def render_shot_matrix(payload: dict[str, Any]) -> str:
    rows = _rows(payload, "rows")
    if not rows:
        return ""
    table = _table(
        ["Shot", "Scene", "Act", "Duration", "Camera", "Status"],
        [
            [
                row.get("shot_id", "?"),
                row.get("scene_id", ""),
                row.get("act_id", ""),
                row.get("duration_seconds", ""),
                row.get("camera_profile", row.get("camera_movement", "")),
                row.get("status", ""),
            ]
            for row in rows
        ],
    )
    functions = [
        f"- **{row.get('shot_id', '?')}**: {row.get('story_function')}"
        for row in rows
        if row.get("story_function")
    ]
    body = table if not functions else f"{table}\n\n{chr(10).join(functions)}"
    return _section("Shot Matrix", body.split("\n"))


def _finding_lines(findings: list[Any]) -> list[str]:
    lines: list[str] = []
    for finding in findings:
        if isinstance(finding, dict):
            severity = finding.get("severity", finding.get("severity_level", ""))
            message = finding.get("message", finding.get("description", ""))
            lines.append(f"- [{severity}] {message}" if severity else f"- {message}")
        elif isinstance(finding, str):
            lines.append(f"- {finding}")
        else:
            lines.append(f"- {finding}")
    return lines


def render_validation_report(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    summary_bits = [
        f"{key}: {payload[key]}"
        for key in ("validator_id", "score", "status")
        if payload.get(key) is not None
    ]
    if summary_bits:
        parts.append(_section("Summary", ["- " + bit for bit in summary_bits]))
    blocking = payload.get("blocking_issues") or []
    if isinstance(blocking, list) and blocking:
        parts.append(_section("Blocking Issues", _finding_lines(blocking)))
    warnings = payload.get("warnings") or []
    if isinstance(warnings, list) and warnings:
        parts.append(_section("Warnings", _finding_lines(warnings)))
    actions = payload.get("recommended_actions") or []
    if isinstance(actions, list) and actions:
        parts.append(_section("Recommended Actions", _bullets(actions)))
    return "\n\n".join(parts)


def render_consensus_report(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    summary_bits = [
        f"{key}: {payload[key]}"
        for key in ("consensus_status", "agreement_level", "orchestrator_recommendation")
        if payload.get(key) is not None
    ]
    if summary_bits:
        parts.append(_section("Summary", ["- " + bit for bit in summary_bits]))
    reviewers = payload.get("reviewers") or []
    if isinstance(reviewers, list) and reviewers:
        parts.append(_section("Reviewers", _bullets(reviewers)))
    shared = payload.get("shared_findings") or []
    if isinstance(shared, list) and shared:
        parts.append(_section("Shared Findings", _finding_lines(shared)))
    disagreements = payload.get("disagreements") or []
    if isinstance(disagreements, list) and disagreements:
        parts.append(_section("Disagreements", _finding_lines(disagreements)))
    return "\n\n".join(parts)


def render_review_package(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("phase", "orchestrator_recommendation"):
        if payload.get(key):
            parts.append(f"**{key.replace('_', ' ').title()}:** {payload[key]}")
    actions = payload.get("available_actions") or []
    if isinstance(actions, list) and actions:
        parts.append(_section("Available Actions", _bullets(actions)))
    artifacts = payload.get("artifacts") or []
    if isinstance(artifacts, list) and artifacts:
        parts.append(_section("Artifacts in Review", _bullets(artifacts)))
    return "\n\n".join(parts)


def render_bible(payload: dict[str, Any]) -> str:
    """Character/environment/camera/style bibles: sections for dict values."""
    parts: list[str] = []
    for key, value in payload.items():
        if key in {"project_id", "schema_version"}:
            continue
        title = key.replace("_", " ").title()
        if isinstance(value, dict):
            lines = [f"- {k}: {v}" for k, v in value.items() if v]
            if lines:
                parts.append(_section(title, lines))
        elif isinstance(value, list) and value:
            parts.append(_section(title, _bullets(value)))
        elif isinstance(value, str) and value:
            parts.append(f"**{title}:** {value}")
    return "\n\n".join(parts)
