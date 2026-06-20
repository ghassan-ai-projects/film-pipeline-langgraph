"""ReferenceUsabilityValidator — validates reference image usability."""

from __future__ import annotations

from typing import Any

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.schemas.validation import ValidationIssue
from film_pipeline.validation.base import BaseValidator


class ReferenceUsabilityValidator(BaseValidator):
    """Validates reference images for resolution, subject correctness, and moderation flags.

    Matches the ``reference-usability-validator`` contract.
    """

    def __init__(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="reference-usability-validator",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.IMAGE],
            input_schema="reference_strategy",
            models=["gemini-flash"],
            thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
            blocking_conditions=["low_resolution", "moderation_risk", "wrong_subject"],
            warning_conditions=["poor_lighting", "non_matching_style"],
        )
        super().__init__(entry)

    def validate(
        self,
        artifact: dict[str, Any],
        context: object = None,
    ) -> dict[str, Any]:
        """Inspect reference entries for usability issues."""
        _ = context
        entries: list[dict[str, Any]] = artifact.get("entries", [])
        if not entries:
            return {
                "total_entries": 0,
                "low_res": 0,
                "high_moderation_risk": 0,
                "wrong_subject_count": 0,
                "poor_lighting_count": 0,
                "non_matching_style_count": 0,
                "issues": [],
            }

        issues: list[dict[str, str]] = []
        low_res_count = 0
        high_mod_risk = 0
        wrong_subject = 0
        poor_lighting = 0
        non_matching_style = 0

        for entry in entries:
            ref_id = str(entry.get("reference_id", "?"))

            # Blocking: low resolution (inferred from quality_score)
            quality: float = float(entry.get("quality_score", 100))
            if quality < 60:
                low_res_count += 1
                issues.append(
                    {
                        "code": "low_resolution",
                        "severity": "blocking",
                        "message": f"Reference '{ref_id}' has quality_score {quality} (< 60).",
                    }
                )

            # Blocking: moderation risk
            mod_risk = str(entry.get("moderation_risk", "low"))
            if mod_risk == "high":
                high_mod_risk += 1
                issues.append(
                    {
                        "code": "moderation_risk",
                        "severity": "blocking",
                        "message": f"Reference '{ref_id}' has high moderation risk.",
                    }
                )

            # Blocking: wrong subject type (unexpected subject_type)
            subject_type = str(entry.get("subject_type", ""))
            valid_subjects = {"character", "environment", "prop", "style", "camera"}
            if subject_type and subject_type not in valid_subjects:
                wrong_subject += 1
                issues.append(
                    {
                        "code": "wrong_subject",
                        "severity": "blocking",
                        "message": (
                            f"Reference '{ref_id}' has unknown subject_type '{subject_type}'."
                        ),
                    }
                )

            # Warning: poor lighting (from notes)
            notes = str(entry.get("notes", "")).lower()
            if any(kw in notes for kw in ("dark", "overexposed", "underexposed", "blown out")):
                poor_lighting += 1
                issues.append(
                    {
                        "code": "poor_lighting",
                        "severity": "warning",
                        "message": f"Reference '{ref_id}' notes suggest lighting issues.",
                    }
                )

            # Warning: non-matching style (from notes)
            if any(kw in notes for kw in ("style mismatch", "inconsistent", "doesn't match")):
                non_matching_style += 1
                issues.append(
                    {
                        "code": "non_matching_style",
                        "severity": "warning",
                        "message": f"Reference '{ref_id}' notes suggest style mismatch.",
                    }
                )

        return {
            "total_entries": len(entries),
            "low_res": low_res_count,
            "high_moderation_risk": high_mod_risk,
            "wrong_subject_count": wrong_subject,
            "poor_lighting_count": poor_lighting,
            "non_matching_style_count": non_matching_style,
            "issues": issues,
        }

    def extract_score(self, raw: dict[str, Any]) -> float:
        total: int = raw.get("total_entries", 0)
        if total == 0:
            return 100.0

        low_res: int = raw.get("low_res", 0)
        high_risk: int = raw.get("high_moderation_risk", 0)
        wrong_subj: int = raw.get("wrong_subject_count", 0)
        poor_light: int = raw.get("poor_lighting_count", 0)
        style_issues: int = raw.get("non_matching_style_count", 0)

        score = 100.0
        score -= (low_res / total) * 40.0
        score -= (high_risk / total) * 50.0
        score -= (wrong_subj / total) * 30.0
        score -= (poor_light / total) * 15.0
        score -= (style_issues / total) * 10.0
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
