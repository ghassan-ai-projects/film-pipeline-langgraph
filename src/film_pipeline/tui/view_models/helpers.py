"""Scene and artifact rendering helpers shared by the studio view models."""

from __future__ import annotations

from typing import Any

from film_pipeline.app.services.models import (
    OperatorComment,
    ValidationWorkspace,
)


def all_issues(validation: ValidationWorkspace | None) -> list[dict[str, Any]]:
    """Return blocking and non-blocking validation issues as one list."""
    if validation is None:
        return []
    return [*validation.blocking_issues, *validation.non_blocking_issues]


def issue_target(issue: dict[str, Any]) -> str:
    """Best-effort identifier of the object a validation issue points at."""
    for key in ("artifact_id", "target", "affected_entity", "scene_id", "asset_id"):
        value = str(issue.get(key, ""))
        if value:
            return value
    return ""


def artifact_outline(body: dict[str, Any]) -> list[str]:
    """One line per scene/section, used as the reader outline."""
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


def render_artifact_body(body: dict[str, Any]) -> str:
    """Render an artifact body as readable text (screenplay-style for scenes)."""
    if isinstance(body.get("text"), str):
        return str(body["text"])
    if isinstance(body.get("treatment"), dict) and isinstance(body["treatment"].get("text"), str):
        return str(body["treatment"]["text"])
    if isinstance(body.get("scenes"), list):
        scenes = [scene for scene in body["scenes"] if isinstance(scene, dict)]
        return "\n\n".join(render_scene(scene) for scene in scenes)
    if isinstance(body.get("rows"), list):
        rows = [row for row in body["rows"] if isinstance(row, dict)]
        return "\n\n".join(render_scene(row) for row in rows)
    return compact_dict(body)


def find_scene(body: dict[str, Any], scene_id: str) -> dict[str, Any] | None:
    """Locate one scene dict inside an artifact body."""
    for scene in artifact_scenes(body):
        if str(scene.get("scene_id", "")) == scene_id:
            return scene
    return None


def artifact_scenes(body: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect scene dicts from the containers artifacts use for scenes."""
    scene_list = body.get("scene_list", {})
    nested_scenes = scene_list.get("scenes", []) if isinstance(scene_list, dict) else []
    scenes: list[dict[str, Any]] = []
    for container in (body.get("scenes"), nested_scenes, body.get("rows")):
        if isinstance(container, list):
            scenes.extend(scene for scene in container if isinstance(scene, dict))
    return scenes


def scene_outline(scene: dict[str, Any]) -> list[str]:
    """Key facts about a scene, used as the reader outline."""
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


def render_scene(scene: dict[str, Any]) -> str:
    """Render one scene as screenplay-style readable text."""
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
    extras: list[str] = []
    _append_scene_collection(extras, "characters", scene.get("characters"))
    _append_scene_collection(extras, "assets", scene.get("asset_refs", scene.get("assets")))
    _append_scene_collection(extras, "references", scene.get("reference_refs"))
    _append_scene_collection(extras, "validation", scene.get("validation_refs"))
    if extras:
        lines.append("")
        lines.extend(extras)
    if len(lines) <= 1:
        return compact_dict(scene)
    return "\n".join(lines).strip("\n")


def _append_scene_collection(lines: list[str], label: str, value: object) -> None:
    if isinstance(value, list) and value:
        lines.append(f"{label}: {', '.join(str(item) for item in value)}")
    elif isinstance(value, str) and value:
        lines.append(f"{label}: {value}")


def comments_for_target(
    comments: list[OperatorComment],
    target_id: str,
    artifact_id: str,
) -> list[OperatorComment]:
    """Operator comments attached to a scene/artifact target."""
    return [
        comment
        for comment in comments
        if comment.target_id in {target_id, artifact_id}
        or (comment.target_type == "artifact" and comment.target_id == artifact_id)
    ]


def validation_for_target(
    validation: ValidationWorkspace | None,
    target_id: str,
    artifact_id: str,
) -> list[dict[str, Any]]:
    """Validation issues attached to a scene/artifact target."""
    issues = all_issues(validation)
    return [
        issue
        for issue in issues
        if issue_target(issue) in {target_id, artifact_id}
        or str(issue.get("scene_id", "")) == target_id
    ]


def compact_dict(value: dict[str, Any]) -> str:
    """Render a dict one key per line, summarizing nested containers."""
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
