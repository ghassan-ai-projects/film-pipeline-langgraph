"""DeliveryCompletenessValidator — validates delivery package completeness."""

from __future__ import annotations

from typing import Any

from film_pipeline.schemas._base import IssueSeverity, ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.schemas.validation import ValidationIssue
from film_pipeline.validation.base import BaseValidator

REQUIRED_DELIVERY_FILES = {
    "final_video.mp4",
    "review_cut.mp4",
    "subtitles.srt",
    "credits.txt",
    "validation_report.json",
    "cost_report.json",
}

_REQUIRED_MANIFEST_REFS: tuple[tuple[str, str], ...] = (
    ("validation_report_ref", "validation report"),
    ("cost_report_ref", "cost report"),
    ("credits_ref", "credits"),
)


def _empty_delivery_result() -> dict[str, Any]:
    """Result payload for a package that lists no files."""
    return {
        "total_files": 0,
        "missing_required": sorted(REQUIRED_DELIVERY_FILES),
        "missing_subtitles": True,
        "missing_stills": True,
        "issues": [
            {
                "code": "empty_package",
                "severity": "blocking",
                "message": "Delivery package has no files.",
            }
        ],
    }


def _present_basenames(files: list[dict[str, str]]) -> set[str]:
    """Basename of every file path listed in the manifest."""
    present_paths = {str(f.get("path", "")) for f in files}
    return {p.split("/")[-1] for p in present_paths}


def _flag_missing_required_files(
    missing_required: set[str],
    issues: list[dict[str, str]],
) -> None:
    """Flag each missing required delivery file by name."""
    for mf in sorted(missing_required):
        issues.append(
            {
                "code": "missing_required_asset",
                "severity": "blocking",
                "message": f"Missing required delivery file: {mf}",
            }
        )


def _has_subtitles(manifest: dict[str, Any], basenames: set[str]) -> bool:
    """True when the manifest declares subtitles or an SRT file is present."""
    subtitles: list[str] = manifest.get("subtitles", [])
    return bool(subtitles) or any("srt" in p.lower() for p in basenames)


def _has_stills(manifest: dict[str, Any], basenames: set[str]) -> bool:
    """True when the manifest declares stills or an image file is present."""
    stills: list[str] = manifest.get("stills", [])
    return bool(stills) or any(
        ext in p.lower() for p in basenames for ext in (".png", ".jpg", ".jpeg")
    )


def _flag_missing_manifest_refs(
    manifest: dict[str, Any],
    issues: list[dict[str, str]],
) -> None:
    """Flag required manifest reference fields left empty."""
    for key, label in _REQUIRED_MANIFEST_REFS:
        if not str(manifest.get(key, "")):
            issues.append(
                {
                    "code": "missing_required_asset",
                    "severity": "blocking",
                    "message": f"No {label} reference in delivery manifest.",
                }
            )


class DeliveryCompletenessValidator(BaseValidator):
    """Validates that a delivery package contains all required assets.

    Note: this validator is not explicitly in the 15-MVP validator matrix
    but fulfills the product-completion requirement for a
    ``delivery completeness validator``.
    """

    def __init__(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="delivery-completeness-validator",
            scope=ValidationScope.DELIVERY,
            modalities=[ValidationModality.ASSEMBLY],
            input_schema="delivery_package",
            model_profile="text_validator",
            thresholds=ValidatorThresholds(pass_at=90, review_at=80, block_below=80),
            blocking_conditions=["missing_required_asset", "empty_package"],
            warning_conditions=["missing_subtitles", "missing_stills"],
        )
        super().__init__(entry)

    def _validate_rules(
        self,
        artifact: dict[str, Any],
        context: object = None,
    ) -> dict[str, Any]:
        """Inspect delivery package for required files."""
        _ = context
        manifest: dict[str, Any] = artifact.get("manifest", artifact)
        files: list[dict[str, str]] = manifest.get("files", [])

        if not files:
            return _empty_delivery_result()

        basenames = _present_basenames(files)
        missing_required = REQUIRED_DELIVERY_FILES - basenames

        issues: list[dict[str, str]] = []
        _flag_missing_required_files(missing_required, issues)

        has_subtitles = _has_subtitles(manifest, basenames)
        if not has_subtitles:
            issues.append(
                {
                    "code": "missing_subtitles",
                    "severity": "warning",
                    "message": "No subtitle file found in delivery package.",
                }
            )

        has_stills = _has_stills(manifest, basenames)
        if not has_stills:
            issues.append(
                {
                    "code": "missing_stills",
                    "severity": "warning",
                    "message": "No still images found in delivery package.",
                }
            )

        _flag_missing_manifest_refs(manifest, issues)

        return {
            "total_files": len(files),
            "missing_required": sorted(missing_required),
            "missing_subtitles": not has_subtitles,
            "missing_stills": not has_stills,
            "issues": issues,
        }

    def extract_score(self, raw: dict[str, Any]) -> float:
        total: int = raw.get("total_files", 0)
        if total == 0:
            return 0.0

        missing = raw.get("missing_required", [])
        missing_count = len(missing) if isinstance(missing, list) else 0
        issues: list[dict[str, str]] = raw.get("issues", [])
        blocking_count = sum(1 for i in issues if i.get("severity") == "blocking")
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")

        score = 100.0
        score -= missing_count * 20.0
        score -= blocking_count * 10.0
        score -= warning_count * 5.0
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
