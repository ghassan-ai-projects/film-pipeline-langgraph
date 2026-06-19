"""Validator registry entry schema."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import (
    SchemaBase,
    ValidationModality,
    ValidationScope,
)


class ValidatorThresholds(SchemaBase):
    """Score thresholds that determine pass / review / block."""

    pass_at: float = Field(default=85.0, ge=0, le=100)
    review_at: float = Field(default=75.0, ge=0, le=100)
    block_below: float = Field(default=75.0, ge=0, le=100)


class ValidatorRegistryEntry(SchemaBase):
    """Discoverable record for a validator."""

    validator_id: str
    scope: ValidationScope
    modalities: list[ValidationModality] = Field(default_factory=list)
    input_schema: str = ""
    output_schema: str = "validation-report:v1"
    models: list[str] = Field(default_factory=list)
    thresholds: ValidatorThresholds = Field(default_factory=ValidatorThresholds)
    blocking_conditions: list[str] = Field(default_factory=list)
    warning_conditions: list[str] = Field(default_factory=list)
    enabled: bool = True


class ValidatorRegistry(SchemaBase):
    """Aggregate validator registry."""

    validators: list[ValidatorRegistryEntry] = Field(default_factory=list)
