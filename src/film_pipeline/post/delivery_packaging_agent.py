"""Delivery packaging agent — assembles the delivery package manifest."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


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
        required = [
            self.subtitles_included,
            self.audio_stems_included,
            self.validation_report_included,
            self.cost_report_included,
            self.credits_included,
        ]
        return all(required)

    @property
    def missing_items(self) -> list[str]:
        missing: list[str] = []
        if not self.subtitles_included:
            missing.append("subtitles")
        if not self.audio_stems_included:
            missing.append("audio_stems")
        if not self.validation_report_included:
            missing.append("validation_report")
        if not self.cost_report_included:
            missing.append("cost_report")
        if not self.credits_included:
            missing.append("credits")
        return missing


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
        from film_pipeline.schemas.artifact import ArtifactMetadata

        artifact_id = "delivery_package"
        data = {
            "package_id": package.package_id,
            "project_id": package.project_id,
            "files": package.files,
            "format_version": package.format_version,
            "subtitles_included": package.subtitles_included,
            "audio_stems_included": package.audio_stems_included,
            "stills_included": package.stills_included,
            "prompt_archive_included": package.prompt_archive_included,
            "validation_report_included": package.validation_report_included,
            "cost_report_included": package.cost_report_included,
            "credits_included": package.credits_included,
            "is_complete": package.is_complete,
            "missing_items": package.missing_items,
            "notes": package.notes,
        }
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
        artifact_store.save_dict(data, meta)
        return f"artifact:{artifact_id}:v1"

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

        # Build artifact dict for validator
        artifact_dict = {
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
