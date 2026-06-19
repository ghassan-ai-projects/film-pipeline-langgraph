"""Delivery package and manifest."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class DeliveryManifest(SchemaBase):
    """List of files in the delivery package."""

    package_id: str
    project_id: str
    files: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {'path': str, 'kind': str} entries.",
    )
    subtitles: list[str] = Field(default_factory=list)
    audio_stems: list[str] = Field(default_factory=list)
    stills: list[str] = Field(default_factory=list)
    validation_report_ref: str = ""
    cost_report_ref: str = ""
    credits_ref: str = ""


class DeliveryPackage(SchemaBase):
    """Top-level delivery package for a finished film."""

    package_id: str
    project_id: str
    final_video_ref: str
    review_cut_ref: str = ""
    manifest: DeliveryManifest
    archive_refs: list[str] = Field(
        default_factory=list,
        description="Archive artifacts (prompt archive, reference archive, etc).",
    )
    notes: str = ""
