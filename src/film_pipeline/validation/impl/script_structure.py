"""ScriptStructureValidator — validates scene writing and act structure."""

from __future__ import annotations

from typing import Any

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.schemas.validation import ValidationIssue
from film_pipeline.validation.base import BaseValidator


class ScriptStructureValidator(BaseValidator):
    """Validates script scene structure: scene count, dramatic function coverage,
    conflict presence, and intent mapping.

    Matches the ``scene-writing-validator`` contract.
    """

    def __init__(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="scene-writing-validator",
            scope=ValidationScope.SCENE,
            modalities=[ValidationModality.TEXT],
            input_schema="scene_script",
            models=["gemini-flash"],
            thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
            blocking_conditions=["missing_scene_intent", "no_conflict"],
            warning_conditions=["dialogue_dense", "scene_too_long"],
        )
        super().__init__(entry)

    def validate(
        self,
        artifact: dict[str, Any],
        context: object = None,
    ) -> dict[str, Any]:
        """Inspect the script artifact for structural issues."""
        _ = context
        scenes: list[dict[str, Any]] = artifact.get("scenes", [])
        issues: list[dict[str, str]] = []

        if not scenes:
            issues.append(
                {
                    "code": "missing_scene_intent",
                    "severity": "blocking",
                    "message": "Script contains no scenes.",
                }
            )
            return {"scenes_count": 0, "issues": issues}

        scenes_without_intent: list[str] = []
        scenes_without_conflict: list[str] = []
        scenes_with_dense_dialogue: list[str] = []
        scenes_with_many_action_lines: list[str] = []

        for s in scenes:
            sid = str(s.get("scene_id", "?"))
            intent = str(s.get("intent_ref", ""))
            dialogue = s.get("dialogue", [])
            action_lines = s.get("action_lines", [])

            if not intent:
                scenes_without_intent.append(sid)
            if not any(
                d.get("conflict") or s.get("conflict") for d in ([s, *dialogue])
            ):  # pragma: no cover
                pass  # conflict is on SceneIntent, not ScriptScene
            dialogue_count = len(dialogue)
            if dialogue_count > 15:
                scenes_with_dense_dialogue.append(sid)
            if len(action_lines) > 10:
                scenes_with_many_action_lines.append(sid)

        # Blocking: scenes without intent refs
        if scenes_without_intent:
            issues.append(
                {
                    "code": "missing_scene_intent",
                    "severity": "blocking",
                    "message": f"Scenes missing intent_ref: {', '.join(scenes_without_intent[:5])}",
                }
            )

        # Blocking: scenes without conflict (check dialogue for conflict indicators)
        conflict_keywords = {"conflict", "tension", "argue", "fight", "disagree", "struggle"}
        scenes_without_conflict = [
            str(s.get("scene_id", "?"))
            for s in scenes
            if not any(
                kw in str(d.get("line", "")).lower()
                for d in s.get("dialogue", [])
                for kw in conflict_keywords
            )
            and not any(
                kw in str(al).lower()
                for al in s.get("action_lines", [])
                for kw in conflict_keywords
            )
        ]
        if len(scenes_without_conflict) > len(scenes) * 0.5:
            issues.append(
                {
                    "code": "no_conflict",
                    "severity": "blocking",
                    "message": (
                        f"Over half of scenes ({len(scenes_without_conflict)}/{len(scenes)}) "
                        "lack clear conflict indicators."
                    ),
                }
            )

        # Warnings
        if scenes_with_dense_dialogue:
            dense_list = ", ".join(scenes_with_dense_dialogue[:5])
            issues.append(
                {
                    "code": "dialogue_dense",
                    "severity": "warning",
                    "message": f"Scenes with >15 dialogue lines: {dense_list}",
                }
            )
        if scenes_with_many_action_lines:
            long_list = ", ".join(scenes_with_many_action_lines[:5])
            issues.append(
                {
                    "code": "scene_too_long",
                    "severity": "warning",
                    "message": f"Scenes with >10 action lines: {long_list}",
                }
            )

        return {"scenes_count": len(scenes), "issues": issues}

    def extract_score(self, raw: dict[str, Any]) -> float:
        issues: list[dict[str, str]] = raw.get("issues", [])
        scenes_count: int = raw.get("scenes_count", 0)
        if scenes_count == 0:
            return 0.0

        blocking_count = sum(1 for i in issues if i.get("severity") == "blocking")
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")

        score = 100.0
        score -= blocking_count * 25.0
        score -= warning_count * 10.0
        return max(0.0, min(100.0, score))

    def extract_issues(self, raw: dict[str, Any]) -> list[ValidationIssue]:
        return [
            ValidationIssue(
                code=str(i.get("code", "unknown")),
                message=str(i.get("message", "")),
                severity=str(i.get("severity", "info")),
            )
            for i in raw.get("issues", [])
        ]
