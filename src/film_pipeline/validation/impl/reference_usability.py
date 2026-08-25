"""ReferenceUsabilityValidator — validates reference image usability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.schemas.validation import ValidationIssue
from film_pipeline.validation.base import BaseValidator

_VALID_SUBJECT_TYPES = frozenset({"character", "environment", "prop", "style", "camera"})
_POOR_LIGHTING_KEYWORDS = ("dark", "overexposed", "underexposed", "blown out")
_STYLE_MISMATCH_KEYWORDS = ("style mismatch", "inconsistent", "doesn't match")


@dataclass(frozen=True)
class _ReferenceFacts:
    """Usability-relevant facts extracted from one reference entry."""

    reference_id: str
    asset_path: str
    generation_status: str
    quality_score: float
    moderation_risk: str
    subject_type: str
    notes: str


def _empty_reference_result() -> dict[str, Any]:
    """Result payload for a strategy that declares no references."""
    return {
        "total_entries": 0,
        "low_res": 0,
        "high_moderation_risk": 0,
        "wrong_subject_count": 0,
        "poor_lighting_count": 0,
        "non_matching_style_count": 0,
        "issues": [],
    }


def _reference_facts(entry: dict[str, Any]) -> _ReferenceFacts:
    """Extract the usability-relevant facts of a single reference entry."""
    return _ReferenceFacts(
        reference_id=str(entry.get("reference_id", "?")),
        asset_path=str(entry.get("asset_path", "")),
        generation_status=str(entry.get("generation_status", "planned")),
        quality_score=float(entry.get("quality_score", 100)),
        moderation_risk=str(entry.get("moderation_risk", "low")),
        subject_type=str(entry.get("subject_type", "")),
        notes=str(entry.get("notes", "")).lower(),
    )


def _flag_low_resolution(
    facts: _ReferenceFacts,
    issues: list[dict[str, str]],
) -> int:
    """Blocking: low resolution inferred from a quality_score below 60."""
    if facts.quality_score >= 60:
        return 0
    issues.append(
        {
            "code": "low_resolution",
            "severity": "blocking",
            "message": (
                f"Reference '{facts.reference_id}' has quality_score {facts.quality_score} (< 60)."
            ),
        }
    )
    return 1


def _flag_high_moderation_risk(
    facts: _ReferenceFacts,
    issues: list[dict[str, str]],
) -> int:
    """Blocking: the reference carries a high moderation risk."""
    if facts.moderation_risk != "high":
        return 0
    issues.append(
        {
            "code": "moderation_risk",
            "severity": "blocking",
            "message": f"Reference '{facts.reference_id}' has high moderation risk.",
        }
    )
    return 1


def _flag_unknown_subject_type(
    facts: _ReferenceFacts,
    issues: list[dict[str, str]],
) -> int:
    """Blocking: subject_type outside the known vocabulary."""
    if not facts.subject_type or facts.subject_type in _VALID_SUBJECT_TYPES:
        return 0
    issues.append(
        {
            "code": "wrong_subject",
            "severity": "blocking",
            "message": (
                f"Reference '{facts.reference_id}' has unknown subject_type '{facts.subject_type}'."
            ),
        }
    )
    return 1


def _flag_failed_generation(
    facts: _ReferenceFacts,
    issues: list[dict[str, str]],
) -> int:
    """Blocking: image generation failed for this reference."""
    if facts.generation_status not in {"failed"}:
        return 0
    issues.append(
        {
            "code": "generation_failed",
            "severity": "blocking",
            "message": f"Reference '{facts.reference_id}' failed during image generation.",
        }
    )
    return 1


def _flag_generated_without_asset(
    facts: _ReferenceFacts,
    issues: list[dict[str, str]],
) -> int:
    """Blocking: a generated reference must carry an asset_path."""
    if facts.generation_status not in {"generated", "validated"} or facts.asset_path:
        return 0
    issues.append(
        {
            "code": "missing_asset",
            "severity": "blocking",
            "message": (
                f"Reference '{facts.reference_id}' is marked generated but has no asset_path."
            ),
        }
    )
    return 1


def _flag_poor_lighting_notes(
    facts: _ReferenceFacts,
    issues: list[dict[str, str]],
) -> int:
    """Warning: notes suggest lighting problems."""
    if not any(kw in facts.notes for kw in _POOR_LIGHTING_KEYWORDS):
        return 0
    issues.append(
        {
            "code": "poor_lighting",
            "severity": "warning",
            "message": f"Reference '{facts.reference_id}' notes suggest lighting issues.",
        }
    )
    return 1


def _flag_style_mismatch_notes(
    facts: _ReferenceFacts,
    issues: list[dict[str, str]],
) -> int:
    """Warning: notes suggest a style mismatch."""
    if not any(kw in facts.notes for kw in _STYLE_MISMATCH_KEYWORDS):
        return 0
    issues.append(
        {
            "code": "non_matching_style",
            "severity": "warning",
            "message": f"Reference '{facts.reference_id}' notes suggest style mismatch.",
        }
    )
    return 1


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
            model_profile="multimodal_reviewer",
            thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
            blocking_conditions=["low_resolution", "moderation_risk", "wrong_subject"],
            warning_conditions=["poor_lighting", "non_matching_style"],
        )
        super().__init__(entry)

    def _validate_rules(
        self,
        artifact: dict[str, Any],
        context: object = None,
    ) -> dict[str, Any]:
        """Inspect reference entries for usability issues."""
        _ = context
        entries: list[dict[str, Any]] = artifact.get("entries", [])
        if not entries:
            return _empty_reference_result()

        issues: list[dict[str, str]] = []
        low_res_count = 0
        high_mod_risk = 0
        wrong_subject = 0
        poor_lighting = 0
        non_matching_style = 0

        for entry in entries:
            facts = _reference_facts(entry)
            low_res_count += _flag_low_resolution(facts, issues)
            high_mod_risk += _flag_high_moderation_risk(facts, issues)
            wrong_subject += _flag_unknown_subject_type(facts, issues)
            wrong_subject += _flag_failed_generation(facts, issues)
            low_res_count += _flag_generated_without_asset(facts, issues)
            poor_lighting += _flag_poor_lighting_notes(facts, issues)
            non_matching_style += _flag_style_mismatch_notes(facts, issues)

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
                suggestion=str(i.get("suggestion", "")),
                affected_entity=str(i.get("affected_entity", "")),
                affected_field=str(i.get("affected_field", "")),
                affected_shot=str(i.get("affected_shot", "")),
            )
            for i in raw.get("issues", [])
        ]
