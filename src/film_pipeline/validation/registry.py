"""Validator registry — register, lookup by scope, modality, or id.

Distinct from the Pydantic ``ValidatorRegistry`` schema (which is
serializable). This is the runtime registry backed by a dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from film_pipeline.schemas.base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)


@dataclass
class ValidatorRegistry:
    """Runtime registry of validators, keyed by validator_id."""

    entries: dict[str, ValidatorRegistryEntry] = field(default_factory=dict)

    def register(self, entry: ValidatorRegistryEntry) -> None:
        if entry.validator_id in self.entries:
            raise ValueError(f"Validator '{entry.validator_id}' already registered.")
        self.entries[entry.validator_id] = entry

    def register_many(self, entries: list[ValidatorRegistryEntry]) -> None:
        for e in entries:
            self.register(e)

    def lookup_by_id(self, validator_id: str) -> ValidatorRegistryEntry | None:
        return self.entries.get(validator_id)

    def lookup_by_scope(self, scope: ValidationScope) -> list[ValidatorRegistryEntry]:
        return [e for e in self.entries.values() if e.scope == scope]

    def lookup_by_modality(self, modality: ValidationModality) -> list[ValidatorRegistryEntry]:
        return [e for e in self.entries.values() if modality in e.modalities]

    def enabled_only(self) -> list[ValidatorRegistryEntry]:
        return [e for e in self.entries.values() if e.enabled]

    def __len__(self) -> int:
        return len(self.entries)

    def __contains__(self, validator_id: str) -> bool:
        return validator_id in self.entries


# ── The MVP validator set ────────────────────────────────────────────────────
# Moved here from `validation/validators/__init__.py` (doc 06 slice 6.6), a package
# whose only content was this list. The registry it feeds is this module, so the data
# and its consumer now sit together, and `validation` no longer has two things a
# reader might expect to be the same thing as `governance/gates`.

MVP_VALIDATORS: list[ValidatorRegistryEntry] = [
    # --- Text validators (artifact scope) ---
    ValidatorRegistryEntry(
        validator_id="logline-validator",
        scope=ValidationScope.ARTIFACT,
        modalities=[ValidationModality.TEXT],
        input_schema="logline",
        model_profile="text_validator",
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
        blocking_conditions=["unclear_premise", "missing_emotional_hook"],
        warning_conditions=["too_long", "generic_language"],
    ),
    ValidatorRegistryEntry(
        validator_id="treatment-validator",
        scope=ValidationScope.ARTIFACT,
        modalities=[ValidationModality.TEXT],
        input_schema="treatment",
        model_profile="text_validator",
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
        blocking_conditions=["missing_acts", "no_theme"],
        warning_conditions=["overlong", "weak_act_breaks"],
    ),
    ValidatorRegistryEntry(
        validator_id="scene-writing-validator",
        scope=ValidationScope.SCENE,
        modalities=[ValidationModality.TEXT],
        input_schema="scene_script",
        model_profile="text_validator",
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
        blocking_conditions=["missing_scene_intent", "no_conflict"],
        warning_conditions=["dialogue_dense", "scene_too_long"],
    ),
    ValidatorRegistryEntry(
        validator_id="dialogue-voice-validator",
        scope=ValidationScope.SCENE,
        modalities=[ValidationModality.TEXT],
        input_schema="scene_script",
        model_profile="text_validator",
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
        blocking_conditions=["voice_inconsistency", "character_truth_broken"],
        warning_conditions=["generic_dialogue", "exposition_heavy"],
    ),
    ValidatorRegistryEntry(
        validator_id="character-dossier-validator",
        scope=ValidationScope.ARTIFACT,
        modalities=[ValidationModality.TEXT, ValidationModality.IMAGE],
        input_schema="character_bible",
        model_profile="multimodal_reviewer",
        thresholds=ValidatorThresholds(pass_at=80, review_at=70, block_below=70),
        blocking_conditions=["missing_visual_identity", "no_must_not_change"],
        warning_conditions=["generic_appearance", "incomplete_wardrobe"],
    ),
    ValidatorRegistryEntry(
        validator_id="environment-bible-validator",
        scope=ValidationScope.ARTIFACT,
        modalities=[ValidationModality.TEXT, ValidationModality.IMAGE],
        input_schema="environment_bible",
        model_profile="multimodal_reviewer",
        thresholds=ValidatorThresholds(pass_at=80, review_at=70, block_below=70),
        blocking_conditions=["missing_locked_prompt_block", "no_lighting_profiles"],
        warning_conditions=["inconsistent_time_of_day", "missing_props"],
    ),
    ValidatorRegistryEntry(
        validator_id="reference-usability-validator",
        scope=ValidationScope.ARTIFACT,
        modalities=[ValidationModality.IMAGE],
        input_schema="reference_strategy",
        model_profile="multimodal_reviewer",
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
        blocking_conditions=["low_resolution", "moderation_risk", "wrong_subject"],
        warning_conditions=["poor_lighting", "non_matching_style"],
    ),
    # --- Camera + design validators ---
    ValidatorRegistryEntry(
        validator_id="shot-design-validator",
        scope=ValidationScope.ARTIFACT,
        modalities=[ValidationModality.TEXT, ValidationModality.CAMERA],
        input_schema="master_film_matrix",
        model_profile="multimodal_reviewer",
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
        blocking_conditions=["missing_coverage", "no_camera_profile"],
        warning_conditions=["repetitive_framing", "missing_transitions"],
    ),
    ValidatorRegistryEntry(
        validator_id="prompt-readiness-validator",
        scope=ValidationScope.ARTIFACT,
        modalities=[ValidationModality.TEXT],
        input_schema="prompt_package",
        model_profile="text_validator",
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
        blocking_conditions=["malformed_rctco", "missing_refs", "prompt_too_long"],
        warning_conditions=["ambiguous_constraints", "missing_examples"],
    ),
    # --- Video validators (clip scope) ---
    ValidatorRegistryEntry(
        validator_id="clip-quality-validator",
        scope=ValidationScope.CLIP,
        modalities=[ValidationModality.VIDEO],
        input_schema="generated_clip",
        model_profile="multimodal_reviewer",
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
        blocking_conditions=["corrupt_asset", "wrong_duration", "black_frame"],
        warning_conditions=["compression_artifacts", "motion_blur", "lighting_issue"],
    ),
    ValidatorRegistryEntry(
        validator_id="prompt-adherence-validator",
        scope=ValidationScope.CLIP,
        modalities=[ValidationModality.VIDEO],
        input_schema="generated_clip",
        model_profile="multimodal_reviewer",
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
        blocking_conditions=["wrong_character", "wrong_environment", "missing_action"],
        warning_conditions=["partial_adherence", "extra_elements"],
    ),
    # --- Continuity + flow validators ---
    ValidatorRegistryEntry(
        validator_id="scene-continuity-validator",
        scope=ValidationScope.SCENE,
        modalities=[ValidationModality.CONTINUITY],
        input_schema="scene_clips",
        model_profile="multimodal_reviewer",
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
        blocking_conditions=["character_state_mismatch", "prop_disappeared"],
        warning_conditions=["lighting_shift", "wardrobe_minor_drift"],
    ),
    ValidatorRegistryEntry(
        validator_id="act-structure-validator",
        scope=ValidationScope.ACT,
        modalities=[ValidationModality.TEXT, ValidationModality.FLOW],
        input_schema="act_clips",
        model_profile="text_validator",
        thresholds=ValidatorThresholds(pass_at=80, review_at=70, block_below=70),
        blocking_conditions=["broken_narrative_arc", "missing_climax"],
        warning_conditions=["pacing_issue", "weak_transitions"],
    ),
    ValidatorRegistryEntry(
        validator_id="full-movie-flow-validator",
        scope=ValidationScope.FULL_MOVIE,
        modalities=[ValidationModality.FLOW, ValidationModality.CONTINUITY],
        input_schema="full_movie",
        model_profile="multimodal_reviewer",
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
        blocking_conditions=["emotional_arc_broken", "major_continuity_gap"],
        warning_conditions=["pacing_drift", "minor_continuity_note"],
    ),
    # --- Assembly validator ---
    ValidatorRegistryEntry(
        validator_id="assembly-validator",
        scope=ValidationScope.DELIVERY,
        modalities=[ValidationModality.ASSEMBLY],
        input_schema="assembly_manifest",
        model_profile="text_validator",
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
        blocking_conditions=["missing_clips", "broken_transitions", "wrong_order"],
        warning_conditions=["audio_sync_minor", "color_grade_inconsistent"],
    ),
]
