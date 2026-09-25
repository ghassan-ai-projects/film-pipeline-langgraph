"""ScriptStructureValidator — validates scene writing and act structure."""

from __future__ import annotations

from typing import Any

from film_pipeline.schemas.base import IssueSeverity, ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.schemas.validation import ValidationIssue
from film_pipeline.validation.base import BaseValidator

_CONFLICT_KEYWORDS = frozenset({"conflict", "tension", "argue", "fight", "disagree", "struggle"})


def _no_scenes_result() -> dict[str, Any]:
    """Result payload for a script without scenes."""
    return {
        "scenes_count": 0,
        "issues": [
            {
                "code": "missing_scene_intent",
                "severity": "blocking",
                "message": "Script contains no scenes.",
            }
        ],
    }


def _flag_scene_shortfall(
    scenes: list[dict[str, Any]],
    context: object,
    issues: list[dict[str, str]],
) -> None:
    """Blocking: scene count below the Story Scope Contract minimum."""
    ctx = context if isinstance(context, dict) else {}
    target_scene_count = ctx.get("target_scene_count")
    min_scene_count = ctx.get("min_scene_count")
    if not (isinstance(min_scene_count, int) and len(scenes) < min_scene_count):
        return
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


def _classify_scenes(
    scenes: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    """Bucket scenes as intent-less, dialogue-dense, and action-heavy."""
    scenes_without_intent: list[str] = []
    dense_dialogue_scenes: list[str] = []
    many_action_line_scenes: list[str] = []

    for s in scenes:
        sid = str(s.get("scene_id", "?"))
        if not str(s.get("intent_ref", "")):
            scenes_without_intent.append(sid)
        if len(s.get("dialogue", [])) > 15:
            dense_dialogue_scenes.append(sid)
        if len(s.get("action_lines", [])) > 10:
            many_action_line_scenes.append(sid)

    return scenes_without_intent, dense_dialogue_scenes, many_action_line_scenes


def _conflict_candidate_lines(scene: dict[str, Any]) -> list[str]:
    """Lowercased dialogue lines and action lines of one scene."""
    lines = [str(d.get("line", "")).lower() for d in scene.get("dialogue", [])]
    lines.extend(str(al).lower() for al in scene.get("action_lines", []))
    return lines


def _scene_lacks_conflict(scene: dict[str, Any]) -> bool:
    """True when neither dialogue nor action lines mention a conflict keyword."""
    return not any(
        kw in line for line in _conflict_candidate_lines(scene) for kw in _CONFLICT_KEYWORDS
    )


def _scenes_lacking_conflict(scenes: list[dict[str, Any]]) -> list[str]:
    """Scene ids whose dialogue and action lines show no conflict indicators."""
    return [str(s.get("scene_id", "?")) for s in scenes if _scene_lacks_conflict(s)]


def _flag_density_warnings(
    dense_dialogue_scenes: list[str],
    many_action_line_scenes: list[str],
    issues: list[dict[str, str]],
) -> None:
    """Warnings for dialogue-dense and overly long scenes."""
    if dense_dialogue_scenes:
        issues.append(
            {
                "code": "dialogue_dense",
                "severity": "warning",
                "message": (
                    f"Scenes with >15 dialogue lines: {', '.join(dense_dialogue_scenes[:5])}"
                ),
            }
        )
    if many_action_line_scenes:
        issues.append(
            {
                "code": "scene_too_long",
                "severity": "warning",
                "message": (
                    f"Scenes with >10 action lines: {', '.join(many_action_line_scenes[:5])}"
                ),
            }
        )


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
            return _no_scenes_result()

        # Scene-count compliance against the Story Scope Contract.
        _flag_scene_shortfall(scenes, context, issues)

        without_intent, dense_dialogue, oversized = _classify_scenes(scenes)

        # Blocking: scenes without intent refs
        if without_intent:
            issues.append(
                {
                    "code": "missing_scene_intent",
                    "severity": "blocking",
                    "message": f"Scenes missing intent_ref: {', '.join(without_intent[:5])}",
                }
            )

        # Blocking: scenes without conflict (check dialogue for conflict indicators)
        lacking_conflict = _scenes_lacking_conflict(scenes)
        if len(lacking_conflict) > len(scenes) * 0.5:
            issues.append(
                {
                    "code": "no_conflict",
                    "severity": "blocking",
                    "message": (
                        f"Over half of scenes ({len(lacking_conflict)}/{len(scenes)}) "
                        "lack clear conflict indicators."
                    ),
                }
            )

        # Warnings
        _flag_density_warnings(dense_dialogue, oversized, issues)

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
                severity=IssueSeverity(i.get("severity", "info")),
                suggestion=str(i.get("suggestion", "")),
                affected_entity=str(i.get("affected_entity", "")),
                affected_field=str(i.get("affected_field", "")),
                affected_shot=str(i.get("affected_shot", "")),
            )
            for i in raw.get("issues", [])
        ]
