"""Delivery packaging agent — assembles the delivery package manifest."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

# What makes a delivery package complete, stated once:
# (inclusion-flag attribute on DeliveryPackage, missing-item label).
_COMPLETION_REQUIREMENTS: tuple[tuple[str, str], ...] = (
    ("subtitles_included", "subtitles"),
    ("audio_stems_included", "audio_stems"),
    ("validation_report_included", "validation_report"),
    ("cost_report_included", "cost_report"),
    ("credits_included", "credits"),
)


@dataclass
class DeliveryPackage:
    """A delivery package manifest with all required files."""

    package_id: str
    project_id: str
    files: list[dict[str, str]] = field(default_factory=list)
    format_version: str = "1.0"
    subtitles_included: bool = False
    audio_stems_included: bool = False
    stills_included: bool = False
    prompt_archive_included: bool = False
    validation_report_included: bool = False
    cost_report_included: bool = False
    credits_included: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return all(getattr(self, attribute) for attribute, _label in _COMPLETION_REQUIREMENTS)

    @property
    def missing_items(self) -> list[str]:
        return [
            label for attribute, label in _COMPLETION_REQUIREMENTS if not getattr(self, attribute)
        ]


def _completeness_check_artifact(package: DeliveryPackage) -> dict[str, Any]:
    """Shape a package as the artifact dict DeliveryCompletenessValidator reads.

    Canonical basenames stand in for real paths because the validator only
    checks that each manifest slot is present and non-empty.
    """
    artifact_dict: dict[str, Any] = {
        "manifest": {
            "files": package.files,
            "subtitles": [],
            "stills": [],
            "validation_report_ref": "",
            "cost_report_ref": "",
            "credits_ref": "",
        }
    }

    # Populate from package state
    if package.subtitles_included:
        artifact_dict["manifest"]["subtitles"] = ["subtitles.srt"]
    if package.stills_included:
        artifact_dict["manifest"]["stills"] = ["still_01.png"]
    if package.validation_report_included:
        artifact_dict["manifest"]["validation_report_ref"] = "validation_report.json"
    if package.cost_report_included:
        artifact_dict["manifest"]["cost_report_ref"] = "cost_report.json"
    if package.credits_included:
        artifact_dict["manifest"]["credits_ref"] = "credits.txt"

    return artifact_dict


@dataclass
class DeliveryPackagingAgent:
    """Assembles a delivery package manifest and persists it as an artifact.

    Also runs the DeliveryCompletenessValidator on the persisted package.
    """

    def build_package(
        self,
        project_id: str,
        video_path: str = "",
        subtitle_path: str = "",
        audio_stems_dir: str = "",
        stills_dir: str = "",
        prompt_archive_dir: str = "",
        validation_report_path: str = "",
        cost_report_path: str = "",
        credits_path: str = "",
    ) -> DeliveryPackage:
        """Build a delivery package manifest."""
        package = DeliveryPackage(
            package_id=f"delivery:{project_id}:{uuid4().hex[:8]}",
            project_id=project_id,
        )

        if video_path:
            package.files.append({"path": video_path, "type": "video"})
        if subtitle_path:
            package.files.append({"path": subtitle_path, "type": "subtitles"})
            package.subtitles_included = True
        if audio_stems_dir:
            package.files.append({"path": audio_stems_dir, "type": "audio_stems"})
            package.audio_stems_included = True
        if stills_dir:
            package.files.append({"path": stills_dir, "type": "stills"})
            package.stills_included = True
        if prompt_archive_dir:
            package.files.append({"path": prompt_archive_dir, "type": "prompt_archive"})
            package.prompt_archive_included = True
        if validation_report_path:
            package.files.append({"path": validation_report_path, "type": "validation_report"})
            package.validation_report_included = True
        if cost_report_path:
            package.files.append({"path": cost_report_path, "type": "cost_report"})
            package.cost_report_included = True
        if credits_path:
            package.files.append({"path": credits_path, "type": "credits"})
            package.credits_included = True

        if not package.is_complete:
            package.notes.append(f"Missing items: {', '.join(package.missing_items)}")

        return package

    def persist(
        self,
        package: DeliveryPackage,
        artifact_store: Any,
    ) -> str:
        """Persist the delivery package manifest as a versioned artifact.

        Returns the artifact reference string.
        """
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
        from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef
        from film_pipeline.schemas.delivery import DeliveryPackage as DeliveryPackageModel

        artifact_id = "delivery_package"
        model = DeliveryPackageModel(
            package_id=package.package_id,
            project_id=package.project_id,
            files=package.files,
            format_version=package.format_version,
            subtitles_included=package.subtitles_included,
            audio_stems_included=package.audio_stems_included,
            stills_included=package.stills_included,
            prompt_archive_included=package.prompt_archive_included,
            validation_report_included=package.validation_report_included,
            cost_report_included=package.cost_report_included,
            credits_included=package.credits_included,
            is_complete=package.is_complete,
            missing_items=package.missing_items,
            notes=package.notes,
        )
        meta = ArtifactMetadata(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.DELIVERY_PACKAGE,
            project_id=package.project_id,
            phase=FilmPhase("delivery"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="delivery-packaging-agent",
            created_at=datetime.now(UTC),
        )
        ref: ArtifactRef = artifact_store.save(model, meta)
        return ref.to_string()

    def validate(
        self,
        package: DeliveryPackage,
        artifact_store: Any = None,
    ) -> dict[str, Any]:
        """Run the DeliveryCompletenessValidator on the persisted package.

        Returns a dict with validation results.
        """
        _ = artifact_store
        from film_pipeline.validation.impl.delivery_completeness import (
            DeliveryCompletenessValidator,
        )

        artifact_dict = _completeness_check_artifact(package)

        validator = DeliveryCompletenessValidator()
        report = validator.run(artifact_dict)

        return {
            "validator_id": report.validator_id,
            "score": report.score,
            "status": str(report.status.value),
            "is_complete": package.is_complete,
            "missing_items": package.missing_items,
            "blocking_issues": [
                {"code": i.code, "message": i.message} for i in report.blocking_issues
            ],
            "warnings": [{"code": i.code, "message": i.message} for i in report.warnings],
        }
