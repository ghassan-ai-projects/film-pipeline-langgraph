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

    llm_enabled = True

    def __init__(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="scene-writing-validator",
            scope=ValidationScope.SCENE,
            modalities=[ValidationModality.TEXT],
            input_schema="scene_script",
            model_profile="text_validator",
            thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
            blocking_conditions=["missing_scene_intent", "no_conflict", "scene_count_under_min"],
            warning_conditions=["dialogue_dense", "scene_too_long"],
        )
        super().__init__(entry)

    def validate(
        self,
        artifact: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run rule-based checks, then augment with LLM findings if available."""
        rule_result = self._validate_rules(artifact, context)
        if self.llm_enabled and self._has_llm_services():
            try:
                llm_result = self._validate_llm(artifact, context)
            except Exception:
                return rule_result
            # Merge LLM issues on top of rule-based issues.
            rule_result.setdefault("issues", []).extend(llm_result.get("issues", []))
            # Carry over top-level LLM fields (score, passed, summary, etc.).
            for key in ("score", "passed", "summary"):
                if key in llm_result:
                    rule_result[key] = llm_result[key]
        return rule_result

    def _validate_rules(
        self,
        artifact: dict[str, Any],
        context: object = None,
    ) -> dict[str, Any]:
        """Inspect the script artifact for structural issues."""
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

        # Scene-count compliance against the Story Scope Contract.
        ctx = context if isinstance(context, dict) else {}
        target_scene_count = ctx.get("target_scene_count")
        min_scene_count = ctx.get("min_scene_count")
        if isinstance(min_scene_count, int) and len(scenes) < min_scene_count:
            issues.append(
                {
                    "code": "scene_count_under_min",
                    "severity": "blocking",
                    "message": (
                        f"Script has {len(scenes)} scenes, below the minimum "
                        f"{min_scene_count}. Target was {target_scene_count}."
                    ),
                }
            )

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
        # LLM path: score is directly in the response
        if "score" in raw:
            return float(raw.get("score", 0))
        # Stub path: compute from issue counts
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
                suggestion=str(i.get("suggestion", "")),
                affected_entity=str(i.get("affected_entity", "")),
                affected_field=str(i.get("affected_field", "")),
                affected_shot=str(i.get("affected_shot", "")),
            )
            for i in raw.get("issues", [])
        ]
