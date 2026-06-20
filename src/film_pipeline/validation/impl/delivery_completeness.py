"""DeliveryCompletenessValidator — validates delivery package completeness."""

from __future__ import annotations

from typing import Any

from film_pipeline.schemas._base import ValidationModality, ValidationScope
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
            models=["gemini-flash"],
            thresholds=ValidatorThresholds(pass_at=90, review_at=80, block_below=80),
            blocking_conditions=["missing_required_asset", "empty_package"],
            warning_conditions=["missing_subtitles", "missing_stills"],
        )
        super().__init__(entry)

    def validate(
        self,
        artifact: dict[str, Any],
        context: object = None,
    ) -> dict[str, Any]:
        """Inspect delivery package for required files."""
        _ = context
        manifest: dict[str, Any] = artifact.get("manifest", artifact)
        files: list[dict[str, str]] = manifest.get("files", [])

        if not files:
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

        present_paths = {str(f.get("path", "")) for f in files}
        present_basenames = {p.split("/")[-1] for p in present_paths}

        missing_required = REQUIRED_DELIVERY_FILES - present_basenames
        issues: list[dict[str, str]] = []

        # Blocking: missing required assets
        if missing_required:
            for mf in sorted(missing_required):
                issues.append(
                    {
                        "code": "missing_required_asset",
                        "severity": "blocking",
                        "message": f"Missing required delivery file: {mf}",
                    }
                )

        # Warning: missing subtitles (SRT)
        subtitles: list[str] = manifest.get("subtitles", [])
        has_subtitles = bool(subtitles) or any("srt" in p.lower() for p in present_basenames)
        if not has_subtitles:
            issues.append(
                {
                    "code": "missing_subtitles",
                    "severity": "warning",
                    "message": "No subtitle file found in delivery package.",
                }
            )

        # Warning: missing stills
        stills: list[str] = manifest.get("stills", [])
        has_stills = bool(stills) or any(
            ext in p.lower() for p in present_basenames for ext in (".png", ".jpg", ".jpeg")
        )
        if not has_stills:
            issues.append(
                {
                    "code": "missing_stills",
                    "severity": "warning",
                    "message": "No still images found in delivery package.",
                }
            )

        # Check validation report and cost report
        val_ref = str(manifest.get("validation_report_ref", ""))
        if not val_ref:
            issues.append(
                {
                    "code": "missing_required_asset",
                    "severity": "blocking",
                    "message": "No validation report reference in delivery manifest.",
                }
            )

        cost_ref = str(manifest.get("cost_report_ref", ""))
        if not cost_ref:
            issues.append(
                {
                    "code": "missing_required_asset",
                    "severity": "blocking",
                    "message": "No cost report reference in delivery manifest.",
                }
            )

        credits_ref = str(manifest.get("credits_ref", ""))
        if not credits_ref:
            issues.append(
                {
                    "code": "missing_required_asset",
                    "severity": "blocking",
                    "message": "No credits reference in delivery manifest.",
                }
            )

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
                severity=str(i.get("severity", "info")),
            )
            for i in raw.get("issues", [])
        ]
