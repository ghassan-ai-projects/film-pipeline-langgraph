"""SceneContinuityValidator — validates continuity across shot sequences."""

from __future__ import annotations

from typing import Any

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.schemas.validation import ValidationIssue
from film_pipeline.validation.base import BaseValidator


class SceneContinuityValidator(BaseValidator):
    """Validates continuity across shots: character state, prop presence,
    lighting consistency, and wardrobe drift.

    Matches the ``scene-continuity-validator`` contract.
    """

    def __init__(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="scene-continuity-validator",
            scope=ValidationScope.SCENE,
            modalities=[ValidationModality.CONTINUITY],
            input_schema="scene_clips",
            models=["gemini-flash"],
            thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
            blocking_conditions=["character_state_mismatch", "prop_disappeared"],
            warning_conditions=["lighting_shift", "wardrobe_minor_drift"],
        )
        super().__init__(entry)

    def validate(
        self,
        artifact: dict[str, Any],
        context: object = None,
    ) -> dict[str, Any]:
        """Inspect shots for continuity issues across the sequence."""
        _ = context
        shots: list[dict[str, Any]] = artifact.get("shots", artifact.get("scenes", []))
        if not shots:
            return {
                "total_shots": 0,
                "issues": [],
                "character_state_mismatches": 0,
                "prop_disappearances": 0,
                "lighting_shifts": 0,
                "wardrobe_drifts": 0,
            }

        issues: list[dict[str, str]] = []
        char_state_mismatches = 0
        prop_disappearances = 0
        lighting_shifts = 0
        wardrobe_drifts = 0

        # Track character state across shots
        prev_character_states: dict[str, dict[str, str]] = {}
        prev_lighting: dict[str, str] = {}
        prev_props: set[str] = set()
        prev_wardrobe: dict[str, str] = {}

        for idx, shot in enumerate(shots):
            shot_id = str(shot.get("shot_id", shot.get("scene_id", f"shot-{idx}")))
            characters: list[dict[str, Any]] = shot.get("characters", [])
            lighting = str(shot.get("lighting", ""))
            props: list[str] = shot.get("props", [])
            wardrobe: dict[str, str] = shot.get("wardrobe", {})

            # Character state tracking
            current_states: dict[str, dict[str, str]] = {}
            for char in characters:
                cid = str(char.get("character_id", "?"))
                state = str(char.get("state", ""))
                position = str(char.get("position", ""))
                current_states[cid] = {"state": state, "position": position}

                if cid in prev_character_states:
                    prev = prev_character_states[cid]
                    # Blocking: character state changes without explanation
                    if prev["state"] and state and prev["state"] != state:
                        transition = shot.get("state_transition_reason", "")
                        if not transition:
                            char_state_mismatches += 1
                            issues.append(
                                {
                                    "code": "character_state_mismatch",
                                    "severity": "blocking",
                                    "message": (
                                        f"Character '{cid}' state changed from "
                                        f"'{prev['state']}' to '{state}' in shot '{shot_id}' "
                                        "without documented transition reason."
                                    ),
                                }
                            )

            # Prop tracking across consecutive shots
            current_props = set(props)
            if idx > 0 and prev_props:
                disappeared = prev_props - current_props
                if disappeared:
                    prop_disappearances += 1
                    issues.append(
                        {
                            "code": "prop_disappeared",
                            "severity": "blocking",
                            "message": (
                                f"Props {sorted(disappeared)} present in previous shot "
                                f"but missing from shot '{shot_id}'."
                            ),
                        }
                    )

            # Lighting shift detection (warning level)
            if idx > 0 and lighting and prev_lighting.get("_prev"):
                prev_light = prev_lighting["_prev"]
                if prev_light != lighting:
                    lighting_shifts += 1
                    issues.append(
                        {
                            "code": "lighting_shift",
                            "severity": "warning",
                            "message": (
                                f"Lighting changed from '{prev_light}' to '{lighting}' "
                                f"in shot '{shot_id}'."
                            ),
                        }
                    )

            # Wardrobe drift (warning level)
            if idx > 0 and wardrobe and prev_wardrobe:
                for cid, outfit in wardrobe.items():
                    prev_outfit = prev_wardrobe.get(cid)
                    if prev_outfit and prev_outfit != outfit:
                        wardrobe_drifts += 1
                        issues.append(
                            {
                                "code": "wardrobe_minor_drift",
                                "severity": "warning",
                                "message": (
                                    f"Character '{cid}' outfit changed from "
                                    f"'{prev_outfit}' to '{outfit}' in shot '{shot_id}'."
                                ),
                            }
                        )

            # Store for next iteration
            prev_character_states = current_states
            prev_lighting = {"_prev": lighting}
            prev_props = current_props
            prev_wardrobe = wardrobe

        return {
            "total_shots": len(shots),
            "issues": issues,
            "character_state_mismatches": char_state_mismatches,
            "prop_disappearances": prop_disappearances,
            "lighting_shifts": lighting_shifts,
            "wardrobe_drifts": wardrobe_drifts,
        }

    def extract_score(self, raw: dict[str, Any]) -> float:
        total: int = raw.get("total_shots", 0)
        if total == 0:
            return 100.0

        char_mismatch: int = raw.get("character_state_mismatches", 0)
        prop_dis: int = raw.get("prop_disappearances", 0)
        light_shift: int = raw.get("lighting_shifts", 0)
        wd: int = raw.get("wardrobe_drifts", 0)

        score = 100.0
        # Blocking items cost more
        score -= char_mismatch * 20.0
        score -= prop_dis * 20.0
        # Warning items cost less
        score -= light_shift * 8.0
        score -= wd * 5.0
        return max(0.0, min(100.0, max(score, 0.0)))

    def extract_issues(self, raw: dict[str, Any]) -> list[ValidationIssue]:
        return [
            ValidationIssue(
                code=str(i.get("code", "unknown")),
                message=str(i.get("message", "")),
                severity=str(i.get("severity", "info")),
            )
            for i in raw.get("issues", [])
        ]
