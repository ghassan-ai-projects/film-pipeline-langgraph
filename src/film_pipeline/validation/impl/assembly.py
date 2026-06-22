"""AssemblyValidator — validates assembly manifest completeness and structure."""

from __future__ import annotations

from typing import Any

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.schemas.validation import ValidationIssue
from film_pipeline.validation.base import BaseValidator


class AssemblyValidator(BaseValidator):
    """Validates assembly manifest: clip order, transitions, missing assets.

    Matches the ``assembly-validator`` contract.
    """

    def __init__(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="assembly-validator",
            scope=ValidationScope.DELIVERY,
            modalities=[ValidationModality.ASSEMBLY],
            input_schema="assembly_manifest",
            model_profile="text_validator",
            thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
            blocking_conditions=["missing_clips", "broken_transitions", "wrong_order"],
            warning_conditions=["audio_sync_minor", "color_grade_inconsistent"],
        )
        super().__init__(entry)

    def _validate_rules(
        self,
        artifact: dict[str, Any],
        context: object = None,
    ) -> dict[str, Any]:
        """Inspect assembly manifest for structural issues."""
        _ = context
        clip_order: list[dict[str, Any]] = artifact.get("clip_order", [])
        transitions: list[dict[str, Any]] = artifact.get("transitions", [])
        missing_assets: list[str] = artifact.get("missing_assets", [])
        audio_plan: dict[str, Any] = artifact.get("audio_plan", {})
        cut_id = str(artifact.get("cut_id", "?"))

        issues: list[dict[str, str]] = []

        # Blocking: no clips
        if not clip_order:
            issues.append(
                {
                    "code": "missing_clips",
                    "severity": "blocking",
                    "message": f"Assembly '{cut_id}' has no clips in clip_order.",
                }
            )
            return {
                "clip_count": 0,
                "transition_count": 0,
                "missing_asset_count": len(missing_assets),
                "issues": issues,
                "broken_transitions": 0,
                "wrong_order": 0,
                "audio_sync_minor": 0,
                "color_inconsistent": 0,
            }

        # Collect shot IDs in order for validation
        shot_ids = [str(c.get("shot_id", "")) for c in clip_order]

        # Blocking: broken transitions (transition references shots not in clip_order)
        broken_transitions = 0
        for t in transitions:
            from_id = str(t.get("from_shot_id", ""))
            to_id = str(t.get("to_shot_id", ""))
            transition_type = str(t.get("transition_type", ""))

            if from_id not in shot_ids:
                broken_transitions += 1
                issues.append(
                    {
                        "code": "broken_transitions",
                        "severity": "blocking",
                        "message": f"Transition references unknown from_shot_id '{from_id}'.",
                    }
                )
            if to_id not in shot_ids:
                broken_transitions += 1
                issues.append(
                    {
                        "code": "broken_transitions",
                        "severity": "blocking",
                        "message": f"Transition references unknown to_shot_id '{to_id}'.",
                    }
                )
            valid_types = {"cut", "dissolve", "fade", "wipe", "crossfade"}
            if transition_type and transition_type not in valid_types:
                issues.append(
                    {
                        "code": "broken_transitions",
                        "severity": "blocking",
                        "message": f"Transition has unknown type '{transition_type}'.",
                    }
                )

        # Blocking: wrong order — check for duplicate shot_ids or in_seconds out of sequence
        wrong_order = 0
        seen_ids: set[str] = set()
        prev_out: float = 0.0
        for c in clip_order:
            sid = str(c.get("shot_id", ""))
            in_sec = float(c.get("in_seconds", 0))
            out_sec = float(c.get("out_seconds", 0))

            if sid in seen_ids:
                wrong_order += 1
                issues.append(
                    {
                        "code": "wrong_order",
                        "severity": "blocking",
                        "message": f"Duplicate shot_id '{sid}' in clip order.",
                    }
                )
            seen_ids.add(sid)

            if out_sec < in_sec:
                wrong_order += 1
                issues.append(
                    {
                        "code": "wrong_order",
                        "severity": "blocking",
                        "message": (
                            f"Shot '{sid}' has out_seconds ({out_sec}) < in_seconds ({in_sec})."
                        ),
                    }
                )

            # Check sequential ordering
            if prev_out > 0 and in_sec < prev_out - 0.01:
                issues.append(
                    {
                        "code": "wrong_order",
                        "severity": "blocking",
                        "message": (
                            f"Shot '{sid}' starts at {in_sec}s but previous ends at {prev_out}s."
                        ),
                    }
                )
            prev_out = out_sec

        # Blocking: missing assets
        if missing_assets:
            for ma in missing_assets[:5]:
                issues.append(
                    {
                        "code": "missing_clips",
                        "severity": "blocking",
                        "message": f"Missing asset: {ma}",
                    }
                )

        # Warning: audio sync minor (if audio plan has cue points but no dialogue tracks)
        audio_sync_issues = 0
        cue_points: list[dict[str, Any]] = audio_plan.get("cue_points", [])
        dialogue_tracks: list[str] = audio_plan.get("dialogue_track_refs", [])
        if cue_points and not dialogue_tracks:
            audio_sync_issues += 1
            issues.append(
                {
                    "code": "audio_sync_minor",
                    "severity": "warning",
                    "message": "Audio plan has cue points but no dialogue track references.",
                }
            )

        # Warning: color grade inconsistent
        color_plan: dict[str, Any] = artifact.get("color_plan", {})
        look = str(color_plan.get("look", ""))
        per_scene: dict[str, str] = color_plan.get("per_scene", {})
        color_inconsistent = 0
        if not look and not per_scene:
            color_inconsistent += 1
            issues.append(
                {
                    "code": "color_grade_inconsistent",
                    "severity": "warning",
                    "message": "No color plan specified (no overall look or per-scene grades).",
                }
            )

        return {
            "clip_count": len(clip_order),
            "transition_count": len(transitions),
            "missing_asset_count": len(missing_assets),
            "issues": issues,
            "broken_transitions": broken_transitions,
            "wrong_order": wrong_order,
            "audio_sync_minor": audio_sync_issues,
            "color_inconsistent": color_inconsistent,
        }

    def extract_score(self, raw: dict[str, Any]) -> float:
        clip_count: int = raw.get("clip_count", 0)
        if clip_count == 0:
            return 0.0

        missing: int = raw.get("missing_asset_count", 0)
        broken: int = raw.get("broken_transitions", 0)
        wrong: int = raw.get("wrong_order", 0)
        audio: int = raw.get("audio_sync_minor", 0)
        color: int = raw.get("color_inconsistent", 0)

        score = 100.0
        score -= missing * 25.0
        score -= broken * 15.0
        score -= wrong * 15.0
        score -= audio * 10.0
        score -= color * 8.0
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
