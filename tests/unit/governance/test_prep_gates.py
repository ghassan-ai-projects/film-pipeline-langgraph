"""Tests for prep gates (Gate S), auto-mode enforcement, and routing helpers."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.model_routing import ModelRouter
from film_pipeline.governance.validators import (
    validate_scene_count,
    validate_script_scene_preservation,
)
from film_pipeline.graph import nodes
from film_pipeline.graph.edges import _is_auto_mode, after_approval


class TestGateSValidators:
    def test_scene_count_below_floor_blocks(self) -> None:
        state = {"min_scene_count": 12, "target_scene_count": 14, "target_runtime_seconds": 300}
        issues = validate_scene_count(state, 8)
        assert issues and issues[0]["code"] == "scene_count_below_floor"
        assert issues[0]["severity"] == "blocking"

    def test_scene_count_at_floor_passes(self) -> None:
        state = {"min_scene_count": 12}
        assert validate_scene_count(state, 12) == []

    def test_scene_count_noop_without_contract(self) -> None:
        assert validate_scene_count({}, 1) == []

    def test_script_dropped_scenes_blocks(self) -> None:
        issues = validate_script_scene_preservation({"min_scene_count": 0}, 8, 14)
        assert issues and issues[0]["code"] == "script_dropped_scenes"

    def test_script_below_floor_blocks(self) -> None:
        issues = validate_script_scene_preservation({"min_scene_count": 12}, 10, 10)
        assert any(i["code"] == "script_below_floor" for i in issues)

    def test_script_preserved_passes(self) -> None:
        assert validate_script_scene_preservation({"min_scene_count": 12}, 14, 14) == []


class TestRuntimeAndOverrideHelpers:
    def test_coerce_user_runtime(self) -> None:
        assert nodes._coerce_user_runtime({"target_runtime_seconds": 300}) == 300
        assert nodes._coerce_user_runtime({"target_runtime_seconds": 0}) == 0
        assert nodes._coerce_user_runtime({"target_runtime_seconds": True}) == 0
        assert nodes._coerce_user_runtime({}) == 0
        assert nodes._coerce_user_runtime({"target_runtime_seconds": "bad"}) == 0

    def test_model_overrides_for(self) -> None:
        state = {"resolved_config": {"model_profiles": {"creative_writer": {"max_tokens": 16384}}}}
        assert nodes._model_overrides_for(state, "creative_writer") == {"max_tokens": 16384}
        assert nodes._model_overrides_for(state, "strict_validator") is None
        assert nodes._model_overrides_for({}, "creative_writer") is None

    def test_model_router_applies_overrides(self) -> None:
        router = ModelRouter()
        model, max_tokens, temp, _, _ = router.resolve_model_params(
            "creative_writer", {"primary": "x/y", "max_tokens": 16384, "temperature": 0.75}
        )
        assert model == "x/y" and max_tokens == 16384 and temp == 0.75


class TestCriticalContextGate:
    def test_blocks_when_required_ref_failed_to_load(self) -> None:
        state = {
            "constitution_ref": "artifact:c:v1",
            "treatment_ref": "artifact:t:v1",
            "scene_list_ref": "artifact:s:v1",
            "_context_load_failures": ["treatment_ref"],
        }
        issues = nodes._critical_context_issues(state, "script")
        assert len(issues) == 1
        assert issues[0]["code"] == "critical_context_unavailable"
        assert "treatment_ref" in issues[0]["message"]

    def test_no_block_when_no_failures(self) -> None:
        assert (
            nodes._critical_context_issues({"constitution_ref": "artifact:c:v1"}, "development")
            == []
        )

    def test_no_block_for_unguarded_phase(self) -> None:
        assert nodes._critical_context_issues({"_context_load_failures": ["x"]}, "qc") == []


class TestAutoApprovalWithholding:
    def test_withholds_on_blocking_in_auto_mode(self) -> None:
        updates: dict[str, Any] = {"approved": True, "human_approval_required": False}
        nodes._withhold_auto_approval_on_blockers(updates, issues=[{"severity": "blocking"}])
        assert updates["approved"] is False

    def test_keeps_approval_when_only_warnings(self) -> None:
        updates: dict[str, Any] = {"approved": True}
        nodes._withhold_auto_approval_on_blockers(updates, issues=[{"severity": "warning"}])
        assert updates["approved"] is True

    def test_noop_in_human_mode(self) -> None:
        updates: dict[str, Any] = {"approved": False}
        nodes._withhold_auto_approval_on_blockers(updates, issues=[{"severity": "blocking"}])
        assert updates["approved"] is False
        assert "human_approval_required" not in updates


class TestEdgesAutoMode:
    def test_is_auto_mode(self) -> None:
        assert _is_auto_mode({"resolved_config": {"studio": {"require_human_approval": False}}})
        assert not _is_auto_mode({"resolved_config": {"studio": {"require_human_approval": True}}})
        assert not _is_auto_mode({})

    def test_is_auto_mode_handles_non_dict_shapes(self) -> None:
        assert not _is_auto_mode({"resolved_config": "not-a-dict"})
        assert not _is_auto_mode({"resolved_config": {"studio": "not-a-dict"}})

    def test_after_approval_terminates_on_stall_in_auto_mode(self) -> None:
        from film_pipeline.graph import orchestrator_state as ostate

        state: dict[str, Any] = {
            "current_phase": "development",
            "approved": False,
            "resolved_config": {"studio": {"require_human_approval": False}},
        }
        ostate.mark_stalled(state, "development", "stuck")
        assert after_approval(state) == "end"
        assert state.get("completed") is True

    def test_after_approval_routes_blockers_to_repair(self) -> None:
        state: dict[str, Any] = {
            "current_phase": "development",
            "approved": False,
            "issues": [{"severity": "blocking", "code": "x"}],
            "resolved_config": {"studio": {"require_human_approval": False}},
        }
        assert after_approval(state) == "repair"
