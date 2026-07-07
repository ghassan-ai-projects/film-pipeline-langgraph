"""Shared helpers for bible generation tools."""

from __future__ import annotations

from typing import Any, cast


def _extract_script_text(script_data: dict[str, object] | None) -> str:
    """Extract readable text from the Script artifact."""
    if script_data is None:
        return ""
    if isinstance(script_data, dict):
        scenes = script_data.get("scenes", script_data.get("content", []))
        if isinstance(scenes, list):
            lines: list[str] = []
            for scene in scenes:
                if isinstance(scene, dict):
                    heading = scene.get("heading", scene.get("scene_heading", ""))
                    if heading:
                        lines.append(str(heading))
                    if scene is not None:
                        for action in cast(
                            list[Any], scene.get("action_lines", scene.get("actions", []))
                        ):
                            lines.append(str(action))
                        for dialogue in cast(
                            list[Any], scene.get("dialogue_lines", scene.get("dialogue", []))
                        ):
                            if isinstance(dialogue, dict):
                                char = dialogue.get("character_id", dialogue.get("character", ""))
                                line = dialogue.get("line", dialogue.get("text", ""))
                                lines.append(f"{char}: {line}")
            return "\n".join(lines)
    return str(script_data)
