"""Tests for the deterministic Story Scope Contract derivation."""

from __future__ import annotations

from film_pipeline.governance.scope_contract import (
    avg_shot_duration_for,
    derive_scope_contract,
    normalize_pacing,
    pacing_from_config,
)


class TestNormalizePacing:
    def test_canonical_values_pass_through(self) -> None:
        assert normalize_pacing("slow_cinema", "narrative") == "slow_cinema"
        assert normalize_pacing("standard", "narrative") == "standard"
        assert normalize_pacing("dynamic", "narrative") == "dynamic"

    def test_profile_vocabulary_is_mapped(self) -> None:
        assert normalize_pacing("meditative", "visual_poetry") == "slow_cinema"
        assert normalize_pacing("character_driven", "narrative") == "standard"
        assert normalize_pacing("action", "commercial") == "dynamic"

    def test_falls_back_to_film_type_default(self) -> None:
        assert normalize_pacing(None, "visual_poetry") == "slow_cinema"
        assert normalize_pacing("", "commercial") == "dynamic"
        assert normalize_pacing(None, "narrative") == "standard"

    def test_unknown_pacing_and_film_type_default_to_standard(self) -> None:
        assert normalize_pacing("nonsense", "also_nonsense") == "standard"
        assert normalize_pacing(None, None) == "standard"


class TestAvgShotDuration:
    def test_returns_canonical_durations(self) -> None:
        assert avg_shot_duration_for("slow_cinema") == 9.0
        assert avg_shot_duration_for("standard") == 6.5
        assert avg_shot_duration_for("dynamic") == 4.0

    def test_aliases_and_unknown(self) -> None:
        assert avg_shot_duration_for("meditative") == 9.0
        assert avg_shot_duration_for("unknown") == 6.5


class TestDeriveScopeContract:
    def test_narrative_300s(self) -> None:
        c = derive_scope_contract("p", 300, "narrative", None)
        assert c.pacing_style == "standard"
        assert c.target_scene_count == 14
        assert c.min_scene_count == 12
        assert c.target_shot_count == 46
        assert c.shots_per_scene_low >= 1
        assert c.shots_per_scene_high >= c.shots_per_scene_low

    def test_film_type_changes_scope(self) -> None:
        poetry = derive_scope_contract("p", 300, "visual_poetry", "meditative")
        commercial = derive_scope_contract("p", 300, "commercial", "dynamic")
        # Same runtime, different style → different scope (proves profiles matter).
        assert poetry.target_scene_count != commercial.target_scene_count
        assert poetry.pacing_style == "slow_cinema"
        assert commercial.pacing_style == "dynamic"
        assert commercial.target_shot_count > poetry.target_shot_count

    def test_is_deterministic(self) -> None:
        a = derive_scope_contract("p", 240, "narrative", "character_driven")
        b = derive_scope_contract("p", 240, "narrative", "character_driven")
        assert a.model_dump() == b.model_dump()

    def test_never_fewer_shots_than_scenes(self) -> None:
        c = derive_scope_contract("p", 1000, "visual_poetry", "meditative")
        assert c.target_shot_count >= c.target_scene_count

    def test_tiny_runtime_stays_valid(self) -> None:
        c = derive_scope_contract("p", 1, "narrative", None)
        assert c.target_scene_count >= 1
        assert c.min_scene_count >= 1
        assert c.target_shot_count >= 1

    def test_runtime_consistency_with_validator_avg(self) -> None:
        # The shot total x the shared avg-duration must land near the runtime,
        # so the downstream ExecutionBrief validator does not flag a mismatch.
        for runtime in (120, 300, 600):
            for ft, pacing in (("narrative", None), ("commercial", "dynamic")):
                c = derive_scope_contract("p", runtime, ft, pacing)
                est = c.target_shot_count * avg_shot_duration_for(c.pacing_style)
                assert abs(est - runtime) <= runtime * 0.20


class TestPacingFromConfig:
    def test_reads_pacing(self) -> None:
        assert pacing_from_config({"pacing": "meditative"}) == "meditative"

    def test_missing_or_bad_config(self) -> None:
        assert pacing_from_config({}) is None
        assert pacing_from_config(None) is None
        assert pacing_from_config({"pacing": ""}) is None


class TestUserSceneCountOverride:
    def test_user_scene_count_overrides_runtime_derivation(self) -> None:
        c = derive_scope_contract("p", 180, "narrative", "standard", user_scene_count=12)
        assert c.target_scene_count == 12
        assert c.min_scene_count == 12
        assert c.target_shot_count >= 12

    def test_user_scene_count_increases_shot_count_to_match(self) -> None:
        c = derive_scope_contract("p", 60, "narrative", "standard", user_scene_count=20)
        assert c.target_scene_count == 20
        assert c.target_shot_count >= 20

    def test_none_user_scene_count_uses_runtime_derivation(self) -> None:
        c_with = derive_scope_contract("p", 180, "narrative", "standard", user_scene_count=12)
        c_without = derive_scope_contract("p", 180, "narrative", "standard")
        assert c_with.target_scene_count == 12
        assert c_without.target_scene_count == 8
