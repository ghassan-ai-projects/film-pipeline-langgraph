"""Delivery package and manifest."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas.base import SchemaBase


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
    """Top-level delivery package artifact persisted by the delivery agent."""

    package_id: str
    project_id: str
    files: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {'path': str, 'type': str} entries.",
    )
    format_version: str = "1.0"
    subtitles_included: bool = False
    audio_stems_included: bool = False
    stills_included: bool = False
    prompt_archive_included: bool = False
    validation_report_included: bool = False
    cost_report_included: bool = False
    credits_included: bool = False
    is_complete: bool = False
    missing_items: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
