"""Tests for validator registry."""

from __future__ import annotations

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
)
from film_pipeline.validation.registry import ValidatorRegistry
from film_pipeline.validation.validators import MVP_VALIDATORS


class TestValidatorRegistry:
    def test_register(self) -> None:
        reg = ValidatorRegistry()
        entry = ValidatorRegistryEntry(
            validator_id="test-validator",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
        )
        reg.register(entry)
        assert len(reg) == 1
        assert "test-validator" in reg

    def test_register_duplicate_raises(self) -> None:
        reg = ValidatorRegistry()
        entry = ValidatorRegistryEntry(
            validator_id="dup",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
        )
        reg.register(entry)
        try:
            reg.register(entry)
            raise AssertionError("Expected ValueError")
        except ValueError:
            pass

    def test_register_many(self) -> None:
        reg = ValidatorRegistry()
        reg.register_many(MVP_VALIDATORS)
        assert len(reg) == 15

    def test_lookup_by_id(self) -> None:
        reg = ValidatorRegistry()
        reg.register_many(MVP_VALIDATORS)
        entry = reg.lookup_by_id("clip-quality-validator")
        assert entry is not None
        assert entry.scope == ValidationScope.CLIP

    def test_lookup_by_scope_clip(self) -> None:
        reg = ValidatorRegistry()
        reg.register_many(MVP_VALIDATORS)
        clips = reg.lookup_by_scope(ValidationScope.CLIP)
        assert len(clips) == 2  # clip-quality + prompt-adherence

    def test_lookup_by_modality_video(self) -> None:
        reg = ValidatorRegistry()
        reg.register_many(MVP_VALIDATORS)
        video = reg.lookup_by_modality(ValidationModality.VIDEO)
        assert len(video) == 2

    def test_lookup_by_modality_text(self) -> None:
        reg = ValidatorRegistry()
        reg.register_many(MVP_VALIDATORS)
        text = reg.lookup_by_modality(ValidationModality.TEXT)
        assert len(text) >= 6  # multiple text validators

    def test_enabled_only(self) -> None:
        reg = ValidatorRegistry()
        reg.register_many(MVP_VALIDATORS)
        assert len(reg.enabled_only()) == 15  # all enabled by default

    def test_all_validators_have_thresholds(self) -> None:
        reg = ValidatorRegistry()
        reg.register_many(MVP_VALIDATORS)
        for entry in reg.entries.values():
            assert entry.thresholds.pass_at > 0
            assert entry.thresholds.block_below > 0
