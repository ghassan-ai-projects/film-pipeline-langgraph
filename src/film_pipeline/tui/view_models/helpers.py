"""Shared private utilities used across the cockpit view-model builders."""

from __future__ import annotations

import re
from typing import Any

from film_pipeline.app.services.models import (
    DashboardSummary,
    OperatorComment,
    ValidationWorkspace,
)
from film_pipeline.tui.view_models.models import CommandValidation, ReviewIssueTarget


def _all_issues(validation: ValidationWorkspace | None) -> list[dict[str, Any]]:
    if validation is None:
        return []
    return [*validation.blocking_issues, *validation.non_blocking_issues]


def _scene_ids_from_summary(artifact: dict[str, object]) -> list[str]:
    raw_values: list[object] = [
        artifact.get("scene_id", ""),
        artifact.get("scene_ids", []),
        artifact.get("scenes", []),
    ]
    body = artifact.get("body")
    if isinstance(body, dict):
        raw_values.extend(
            [
                body.get("scene_id", ""),
                body.get("scene_ids", []),
                body.get("scenes", []),
            ]
        )
        scene_list = body.get("scene_list")
        if isinstance(scene_list, dict):
            raw_values.append(scene_list.get("scenes", []))

    scene_ids: list[str] = []
    for raw in raw_values:
        if isinstance(raw, str) and _is_scene_id(raw):
            scene_ids.append(raw)
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, str) and _is_scene_id(item):
                    scene_ids.append(item)
                elif isinstance(item, dict):
                    value = str(item.get("scene_id", ""))
                    if _is_scene_id(value):
                        scene_ids.append(value)
    return sorted(set(scene_ids))


def _issues_by_target(issues: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        target = _issue_target(issue)
        if target:
            grouped.setdefault(target, []).append(issue)
    return grouped


def _phase_blockers(
    phase: str,
    dashboard: DashboardSummary | None,
    validation: ValidationWorkspace | None,
) -> list[str]:
    blockers: list[str] = []
    if dashboard and phase == dashboard.current_phase:
        blockers.extend(
            f"{item.get('action', 'action')}: {item.get('reason', 'blocked')}"
            for item in dashboard.blocked_actions
        )
    if validation and validation.phase == phase:
        blockers.extend(str(issue.get("message", "")) for issue in validation.blocking_issues)
    return [blocker for blocker in blockers if blocker]


def _dedupe_command_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    unique: list[dict[str, object]] = []
    for row in rows:
        command = str(row.get("command", ""))
        if not command or command in seen:
            continue
        seen.add(command)
        unique.append(row)
    return unique


def _dedupe_review_issues(rows: list[ReviewIssueTarget]) -> list[ReviewIssueTarget]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[ReviewIssueTarget] = []
    for row in rows:
        key = (row.target_id, row.severity, row.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _issue_target(issue: dict[str, Any]) -> str:
    for key in ("artifact_id", "target", "affected_entity", "scene_id", "asset_id"):
        value = str(issue.get(key, ""))
        if value:
            return value
    return ""


def _issue_focus_target(issue: dict[str, Any]) -> str:
    scene_id = str(issue.get("scene_id", ""))
    if scene_id:
        return scene_id
    return _issue_target(issue)


def _target_from_text(text: str) -> str:
    match = re.search(r"\b(?:SC_[A-Za-z0-9_-]+|s_[A-Za-z0-9_-]+|scene_[0-9]+)\b", text)
    if match:
        return match.group(0)
    return ""


def _open_command(target_type: str, target_id: str) -> str:
    if not target_id:
        return "open review"
    if target_type == "scene":
        return f"scene {target_id}"
    if target_type == "artifact":
        return f"artifact {target_id}"
    return f"open {target_id}"


def _target_type_for_issue(issue: dict[str, Any], target_id: str) -> str:
    if str(issue.get("scene_id", "")) or _is_scene_id(target_id):
        return "scene"
    if str(issue.get("artifact_id", "")) or str(issue.get("target", "")):
        return "artifact"
    if str(issue.get("asset_id", "")):
        return "asset"
    return "validation_issue"


def _severity_rank(severity: str) -> int:
    return {"blocking": 0, "error": 1, "warning": 2, "info": 3}.get(severity.lower(), 4)


def _validator_action(severity: str, targets: list[str]) -> str:
    if not targets:
        return "inspect validator report"
    first = targets[0]
    if severity.lower() == "blocking":
        return f"fix {first}"
    return f"review {first}"


def _issue_label(issues: list[dict[str, Any]]) -> str:
    if not issues:
        return "passing/unknown"
    blocking = [issue for issue in issues if issue.get("severity") == "blocking"]
    if blocking:
        return f"blocking: {blocking[0].get('message', '')}"
    return f"warning: {issues[0].get('message', '')}"


def _validation_bucket(value: str) -> str:
    normalized = value.lower()
    if "blocking" in normalized or "failed" in normalized:
        return "blocking"
    if "warning" in normalized or "warn" in normalized:
        return "warning"
    if "passing" in normalized:
        return "passing"
    return "unknown"


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _row_matches_token(row: dict[str, object], token: str) -> bool:
    if token in {"failed", "fail", "blocked", "blocking"}:
        haystack = _row_text(row)
        return "blocking" in haystack or "failed" in haystack or "block" in haystack
    if token in {"warn", "warning", "warnings"}:
        return "warning" in _row_text(row)
    if token in {"candidate", "approved"}:
        return str(row.get("status", "")).lower() == token
    if ":" in token:
        key, expected = token.split(":", maxsplit=1)
        field = {
            "scene": "target",
            "target": "target",
            "kind": "kind",
            "type": "kind",
            "phase": "phase",
            "status": "status",
            "validator": "validation",
        }.get(key)
        if field is None:
            return expected in _row_text(row)
        return expected in str(row.get(field, "")).lower()
    return token in _row_text(row)


def _row_text(row: dict[str, object]) -> str:
    return " ".join(str(value).lower() for value in row.values())


def _is_scene_id(value: str) -> bool:
    return bool(re.match(r"^(SC_|s_)[A-Za-z0-9_-]+$", value) or re.match(r"^scene_[0-9]+$", value))


def _artifact_outline(body: dict[str, Any]) -> list[str]:
    if isinstance(body.get("scenes"), list):
        return [
            f"{scene.get('scene_id', '?')}: "
            f"{scene.get('scene_heading', scene.get('dramatic_function', ''))}"
            for scene in body["scenes"]
            if isinstance(scene, dict)
        ]
    if isinstance(body.get("scene_list"), dict) and isinstance(
        body["scene_list"].get("scenes"), list
    ):
        return [
            f"{scene.get('scene_id', '?')}: {scene.get('dramatic_function', '')}"
            for scene in body["scene_list"]["scenes"]
            if isinstance(scene, dict)
        ]
    if isinstance(body.get("rows"), list):
        return [
            f"{row.get('scene_id', '?')}: {row.get('shot_id', row.get('story_function', ''))}"
            for row in body["rows"]
            if isinstance(row, dict)
        ]
    return [str(key) for key in body]


def _render_artifact_body(body: dict[str, Any]) -> str:
    if isinstance(body.get("text"), str):
        return str(body["text"])
    if isinstance(body.get("treatment"), dict) and isinstance(body["treatment"].get("text"), str):
        return str(body["treatment"]["text"])
    if isinstance(body.get("scenes"), list):
        scenes = [scene for scene in body["scenes"] if isinstance(scene, dict)]
        return "\n\n".join(_render_scene(scene) for scene in scenes)
    if isinstance(body.get("rows"), list):
        rows = [row for row in body["rows"] if isinstance(row, dict)]
        return "\n\n".join(_render_scene(row) for row in rows)
    return _compact_dict(body)


def _find_scene(body: dict[str, Any], scene_id: str) -> dict[str, Any] | None:
    for scene in _artifact_scenes(body):
        if str(scene.get("scene_id", "")) == scene_id:
            return scene
    return None


def _artifact_scenes(body: dict[str, Any]) -> list[dict[str, Any]]:
    scene_list = body.get("scene_list", {})
    nested_scenes = scene_list.get("scenes", []) if isinstance(scene_list, dict) else []
    scenes: list[dict[str, Any]] = []
    for container in (body.get("scenes"), nested_scenes, body.get("rows")):
        if isinstance(container, list):
            scenes.extend(scene for scene in container if isinstance(scene, dict))
    return scenes


def _scene_outline(scene: dict[str, Any]) -> list[str]:
    outline = [str(scene.get("scene_id", "scene"))]
    for key in (
        "scene_heading",
        "dramatic_function",
        "story_function",
        "emotional_shift",
        "conflict",
        "outcome",
        "environment",
        "camera_profile",
        "movement",
        "camera_movement",
    ):
        if scene.get(key):
            outline.append(f"{key}: {scene[key]}")
    return outline


def _render_scene(scene: dict[str, Any]) -> str:
    lines: list[str] = []
    heading = str(scene.get("scene_heading", scene.get("scene_id", "Scene")))
    if heading:
        lines.append(heading)
    for key in (
        "dramatic_function",
        "story_function",
        "conflict",
        "emotional_shift",
        "outcome",
        "environment",
        "environment_zone",
        "environment_state",
        "lighting_state",
        "viewpoint",
        "camera_profile",
        "camera_movement",
        "movement",
        "coverage_role",
        "story_moment",
        "continuity_event",
    ):
        if scene.get(key):
            lines.append(f"{key}: {scene[key]}")
    for action in scene.get("action_lines", []):
        lines.append(str(action))
    for dialogue in scene.get("dialogue", []):
        if not isinstance(dialogue, dict):
            continue
        character = str(dialogue.get("character_id", "")).upper()
        direction = str(dialogue.get("direction", ""))
        line = str(dialogue.get("line", ""))
        lines.append("")
        lines.append(character)
        if direction:
            lines.append(f"({direction})")
        lines.append(line)
    _append_scene_collection(lines, "characters", scene.get("characters"))
    _append_scene_collection(lines, "assets", scene.get("asset_refs", scene.get("assets")))
    _append_scene_collection(lines, "references", scene.get("reference_refs"))
    _append_scene_collection(lines, "validation", scene.get("validation_refs"))
    if len(lines) <= 1:
        return _compact_dict(scene)
    return "\n".join(line for line in lines if line != "")


def _append_scene_collection(lines: list[str], label: str, value: object) -> None:
    if isinstance(value, list) and value:
        lines.append(f"{label}: {', '.join(str(item) for item in value)}")
    elif isinstance(value, str) and value:
        lines.append(f"{label}: {value}")


def _comments_for_target(
    comments: list[OperatorComment],
    target_id: str,
    artifact_id: str,
) -> list[OperatorComment]:
    return [
        comment
        for comment in comments
        if comment.target_id in {target_id, artifact_id}
        or (comment.target_type == "artifact" and comment.target_id == artifact_id)
    ]


def _validation_for_target(
    validation: ValidationWorkspace | None,
    target_id: str,
    artifact_id: str,
) -> list[dict[str, Any]]:
    issues = _all_issues(validation)
    return [
        issue
        for issue in issues
        if _issue_target(issue) in {target_id, artifact_id}
        or str(issue.get("scene_id", "")) == target_id
    ]


def _compact_dict(value: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, item in value.items():
        if isinstance(item, (str, int, float, bool)):
            lines.append(f"{key}: {item}")
        elif isinstance(item, list):
            lines.append(f"{key}: {len(item)} item(s)")
        elif isinstance(item, dict):
            lines.append(f"{key}: {len(item)} field(s)")
        else:
            lines.append(f"{key}: {item}")
    return "\n".join(lines)


def _preview_values(values: list[str], limit: int = 6) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return "none available"
    visible = cleaned[:limit]
    suffix = f" +{len(cleaned) - limit} more" if len(cleaned) > limit else ""
    return ", ".join(visible) + suffix


def _first_command(rows: list[dict[str, object]]) -> str:
    for row in rows:
        command = str(row.get("command", ""))
        if command:
            return command
    return ""


def _matching_suggestion(command: str, rows: list[dict[str, object]]) -> str | None:
    normalized = command.strip().lower()
    for row in rows:
        candidate = str(row.get("command", ""))
        if candidate.lower() == normalized:
            return candidate
    return None


def _first_prefix_match(prefix: str, rows: list[dict[str, object]]) -> str:
    normalized = prefix.strip().lower()
    if not normalized:
        return _first_command(rows)
    for row in rows:
        candidate = str(row.get("command", ""))
        if candidate.lower().startswith(normalized) and "<" not in candidate:
            return candidate
    return ""


def _validate_known_value(
    label: str,
    value: str,
    valid_values: list[str],
) -> CommandValidation:
    if value in valid_values:
        return CommandValidation(status="ready", message=f"Ready: {label} {value}")
    prefix_match = next(
        (candidate for candidate in valid_values if candidate.lower().startswith(value.lower())),
        "",
    )
    if prefix_match:
        return CommandValidation(
            status="incomplete",
            message=f"Partial {label}. Complete to: {prefix_match}",
            completion=f"{label} {prefix_match}",
        )
    return CommandValidation(
        status="unknown",
        message=f"Unknown {label} '{value}'. Try: {_preview_values(valid_values)}.",
    )


def _is_placeholder(value: str) -> bool:
    stripped = value.strip()
    return stripped.startswith("<") and stripped.endswith(">")
