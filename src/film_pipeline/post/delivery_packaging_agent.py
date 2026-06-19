"""Delivery packaging agent — assembles the delivery package manifest."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    """Assembles a delivery package manifest.

    Does not execute ffmpeg — produces a DeliveryPackage for the real pipeline.
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
        """Build a delivery package manifest.

        Args:
            project_id: The film project identifier.
            video_path: Path to final video file.
            subtitle_path: Path to SRT subtitle file.
            audio_stems_dir: Path to audio stems directory.
            stills_dir: Path to stills/keyframes directory.
            prompt_archive_dir: Path to prompt archive.
            validation_report_path: Path to validation report JSON.
            cost_report_path: Path to cost report JSON.
            credits_path: Path to credits/metadata JSON.
        """
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
