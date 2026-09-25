"""Unit tests for orchestrator structural validators (Gates A/B/C)."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

import pytest
from pydantic import ValidationError

from film_pipeline.governance.validators import (
    validate_dispatch_readiness,
    validate_execution_brief,
    validate_planning_completeness,
    validate_shot_scene_references,
    validate_shot_structure,
)
from film_pipeline.schemas.execution_brief import ExecutionBrief, MovementSpec

# ── Test helpers ───────────────────────────────────────────────────────────


def _brief(
    runtime: int = 240,
    movements: list[MovementSpec] | None = None,
) -> ExecutionBrief:
    if movements is None:
        movements = [
            MovementSpec(
                movement_id="act_1",
                shot_count=5,
                duration_range_seconds=(10, 15),
                description="Opening",
            ),
            MovementSpec(
                movement_id="act_2",
                shot_count=5,
                duration_range_seconds=(10, 15),
                description="Middle",
            ),
        ]
    return ExecutionBrief(
        project_id="test-proj",
        target_runtime_seconds=runtime,
        movements=movements,
        mandatory_anchors=["hero", "eagle"],
        environment_progression=["barren", "green"],
        pacing_style="slow_cinema",
    )


@dataclass
class FakeRow:
    shot_id: str = "s_001"
    act_id: str = "act_1"
    duration_seconds: int = 12
    prompt_ref: str = "p_001"
    characters: list[str] = dc_field(default_factory=lambda: ["hero"])
    environment: str = "barren"
    camera_profile: str = "static_wide"
    generation_order: int = 1


@dataclass
class FakeMatrix:
    rows: list[FakeRow] = dc_field(default_factory=list)


# ── Gate A: Shot structure ─────────────────────────────────────────────────


class TestGateAShotStructure:
    def test_passes_when_shot_counts_match(self) -> None:
        brief = _brief(
            runtime=25,  # match total duration to avoid runtime check
            movements=[
                MovementSpec(movement_id="act_1", shot_count=2, duration_range_seconds=(10, 15)),
            ],
        )
        matrix = FakeMatrix(
            rows=[
                FakeRow(shot_id="s_001", act_id="act_1", duration_seconds=12),
                FakeRow(shot_id="s_002", act_id="act_1", duration_seconds=13),
            ]
        )
        issues = validate_shot_structure({}, brief, matrix)
        assert issues == []

    def test_blocks_on_shot_count_mismatch(self) -> None:
        brief = _brief(
            runtime=12,  # match single-shot duration to avoid runtime issue
            movements=[
                MovementSpec(movement_id="act_1", shot_count=5, duration_range_seconds=(10, 15)),
            ],
        )
        matrix = FakeMatrix(
            rows=[
                FakeRow(shot_id="s_001", act_id="act_1", duration_seconds=12),
            ]
        )
        issues = validate_shot_structure({}, brief, matrix)
        assert len(issues) == 1
        assert issues[0]["severity"] == "blocking"
        assert "shot_count_mismatch" in issues[0]["code"]

    def test_blocks_on_act_ids_outside_execution_brief(self) -> None:
        brief = _brief(
            runtime=48,
            movements=[
                MovementSpec(movement_id="act_1", shot_count=1, duration_range_seconds=(10, 15)),
                MovementSpec(movement_id="act_2", shot_count=1, duration_range_seconds=(10, 15)),
                MovementSpec(movement_id="act_3", shot_count=1, duration_range_seconds=(10, 15)),
            ],
        )
        matrix = FakeMatrix(
            rows=[
                FakeRow(shot_id="s_001", act_id="act_1", duration_seconds=12),
                FakeRow(shot_id="s_002", act_id="act_2", duration_seconds=12),
                FakeRow(shot_id="s_003", act_id="act_3", duration_seconds=12),
                FakeRow(shot_id="s_004", act_id="act_4", duration_seconds=12),
            ]
        )
        issues = validate_shot_structure({}, brief, matrix)
        assert [issue["code"] for issue in issues] == ["unexpected_act_ids"]

    def test_blocks_on_runtime_mismatch(self) -> None:
        brief = _brief(
            runtime=240,
            movements=[
                MovementSpec(movement_id="act_1", shot_count=2, duration_range_seconds=(10, 15)),
            ],
        )
        matrix = FakeMatrix(
            rows=[
                FakeRow(shot_id="s_001", act_id="act_1", duration_seconds=5),
                FakeRow(shot_id="s_002", act_id="act_1", duration_seconds=5),
            ]
        )  # total = 10, target = 240 → 10% tolerance = 24, so 10 vs 240 fails
        issues = validate_shot_structure({}, brief, matrix)
        assert len(issues) >= 1
        runtime_issues = [i for i in issues if i["code"] == "runtime_mismatch"]
        assert len(runtime_issues) == 1

    def test_blocks_on_empty_matrix(self) -> None:
        brief = _brief()
        matrix = FakeMatrix(rows=[])
        issues = validate_shot_structure({}, brief, matrix)
        assert len(issues) == 1
        assert "empty" in issues[0]["code"]


# ── Gate B: Planning completeness ──────────────────────────────────────────


class TestGateBPlanningCompleteness:
    def test_passes_when_all_fields_present_and_cost_nonzero(self) -> None:
        matrix = FakeMatrix(
            rows=[
                FakeRow(
                    shot_id="s_001",
                    act_id="act_1",
                    duration_seconds=12,
                    prompt_ref="p_001",
                    characters=["hero"],
                    environment="barren",
                    camera_profile="static",
                    generation_order=1,
                ),
            ]
        )
        cost: dict[str, Any] = {"clip_count": 1, "total_cost_usd": 5.0}
        issues = validate_planning_completeness({}, matrix, cost)
        assert issues == []

    def test_blocks_on_missing_fields(self) -> None:
        matrix = FakeMatrix(
            rows=[
                FakeRow(
                    shot_id="s_001",
                    act_id="act_1",
                    prompt_ref="",
                    characters=[],
                    environment="",
                    camera_profile="",
                    generation_order=0,
                ),
            ]
        )
        issues = validate_planning_completeness({}, matrix, {})
        assert len(issues) >= 1
        field_issues = [i for i in issues if "incomplete_shot_rows" in i["code"]]
        assert len(field_issues) == 1

    def test_passes_for_environment_only_shot(self) -> None:
        """Environment establishing shots may have empty characters."""
        matrix = FakeMatrix(
            rows=[
                FakeRow(
                    shot_id="s_001",
                    act_id="act_1",
                    prompt_ref="p_001",
                    characters=[],
                    environment="barren void",
                    camera_profile="static wide",
                    generation_order=1,
                ),
            ]
        )
        cost: dict[str, Any] = {"clip_count": 1, "total_cost_usd": 5.0}
        issues = validate_planning_completeness({}, matrix, cost)
        assert all(i["code"] != "incomplete_shot_rows" for i in issues)

    def test_blocks_on_zero_clip_count(self) -> None:
        matrix = FakeMatrix(rows=[FakeRow()])
        cost: dict[str, Any] = {"clip_count": 0, "total_cost_usd": 0.0}
        issues = validate_planning_completeness({}, matrix, cost)
        assert len(issues) >= 1
        assert any("zero_clip_count" in i["code"] for i in issues)

    def test_blocks_on_placeholder_cost_with_clips(self) -> None:
        matrix = FakeMatrix(rows=[FakeRow()])
        cost: dict[str, Any] = {"clip_count": 5, "total_cost_usd": 0.0}
        issues = validate_planning_completeness({}, matrix, cost)
        assert len(issues) >= 1
        assert any("placeholder_cost" in i["code"] for i in issues)

    def test_blocks_on_missing_cost_estimate(self) -> None:
        matrix = FakeMatrix(rows=[FakeRow()])
        issues = validate_planning_completeness({}, matrix, None)
        assert len(issues) >= 1
        assert any("missing_cost_estimate" in i["code"] for i in issues)

    def test_blocks_shots_referencing_missing_script_scenes(self) -> None:
        script = {"scenes": [{"scene_id": "SC_001"}]}
        matrix = {
            "rows": [
                {"shot_id": "shot_001", "scene_id": "SC_001"},
                {"shot_id": "shot_002", "scene_id": "SC_999"},
            ]
        }
        issues = validate_shot_scene_references(script, matrix)
        assert len(issues) == 1
        assert issues[0]["code"] == "shot_scene_reference_mismatch"
        assert "shot_002->SC_999" in issues[0]["message"]


# ── Gate C: Dispatch readiness ─────────────────────────────────────────────


class TestGateCDispatchReadiness:
    def test_passes_when_requests_are_dispatchable(self) -> None:
        requests = [
            {
                "shot_id": "s_001",
                "provider": "seedance",
                "model": "v2",
                "prompt_payload": {"resolved_prompt": "A cinematic test prompt."},
            },
        ]
        issues = validate_dispatch_readiness({}, requests)
        assert issues == []

    def test_blocks_on_none_requests(self) -> None:
        issues = validate_dispatch_readiness({}, None)
        assert len(issues) == 1
        assert "no_generation_requests" in issues[0]["code"]

    def test_blocks_on_empty_requests(self) -> None:
        issues = validate_dispatch_readiness({}, [])
        assert len(issues) == 1
        assert "empty" in issues[0]["code"]

    def test_blocks_on_undispatchable_request(self) -> None:
        requests = [
            {"shot_id": "s_001", "provider": "", "model": "", "prompt": ""},
        ]
        issues = validate_dispatch_readiness({}, requests)
        assert len(issues) == 1
        assert "undispatchable" in issues[0]["code"]

    def test_blocks_when_resolved_prompt_missing(self) -> None:
        requests = [
            {"shot_id": "s_001", "provider": "s", "model": "m", "prompt_payload": {}},
        ]
        issues = validate_dispatch_readiness({}, requests)
        assert len(issues) == 1
        assert "undispatchable" in issues[0]["code"]

    def test_passes_when_dict_requests_have_prompt_payload(self) -> None:
        requests = [
            {
                "shot_id": "s_001",
                "provider": "s",
                "model": "m",
                "prompt_payload": {"resolved_prompt": "prompt text"},
            },
        ]
        issues = validate_dispatch_readiness({}, requests)
        assert issues == []


# ── ExecutionBrief round-trip ──────────────────────────────────────────────


class TestExecutionBriefSchema:
    def test_round_trip_json(self) -> None:
        brief = _brief()
        data = brief.model_dump(mode="json")
        reloaded = ExecutionBrief(**data)
        assert reloaded.target_runtime_seconds == 240
        assert len(reloaded.movements) == 2
        assert reloaded.movements[0].shot_count == 5

    def test_minimal_validation_rejects_empty(self) -> None:
        with pytest.raises(ValidationError):
            ExecutionBrief(project_id="", target_runtime_seconds=0, movements=[])

    def test_movement_spec_requires_positive_shot_count(self) -> None:
        with pytest.raises(ValidationError):
            MovementSpec(movement_id="a", shot_count=0, duration_range_seconds=(1, 2))


# ── Enforcement: approve_phase blocked by structural issues ─────────────


class TestApprovalEnforcement:
    """Verify that the approval path rejects phases with blocking issues."""

    def test_approve_phase_node_blocks_with_issues(self) -> None:
        from film_pipeline.graph.nodes import approve_phase_node

        state: dict[str, Any] = {
            "current_phase": "shot_bible",
            "approved": False,
            "issues": [
                {"severity": "blocking", "code": "runtime_mismatch", "message": "Bad runtime"}
            ],
        }
        result = approve_phase_node(state)
        assert result.get("approved") is False
        assert result.get("_approval_blocked_by_issues") is True

    def test_approve_phase_node_passes_without_blocking_issues(self) -> None:
        from film_pipeline.graph.nodes import approve_phase_node

        state: dict[str, Any] = {
            "current_phase": "shot_bible",
            "approved": False,
            "issues": [],
        }
        result = approve_phase_node(state)
        assert result.get("approved") is True


# ── Cross-validation of ExecutionBrief ───────────────────────────────────


class TestValidateExecutionBrief:
    def test_passes_valid_brief(self) -> None:
        # 33 shots at slow_cinema (avg 9.0s) ~= 297s, within tolerance of 300s.
        # Counts come from the single-source density model (graph.scope_contract).
        brief = _brief(
            runtime=300,
            movements=[
                MovementSpec(movement_id="act_1", shot_count=11, duration_range_seconds=(8, 10)),
                MovementSpec(movement_id="act_2", shot_count=11, duration_range_seconds=(8, 10)),
                MovementSpec(movement_id="act_3", shot_count=11, duration_range_seconds=(8, 10)),
            ],
        )
        state: dict[str, Any] = {}
        issues = validate_execution_brief(state, brief)
        assert issues == []

    def test_blocks_too_few_movements(self) -> None:
        brief = _brief(
            movements=[
                MovementSpec(movement_id="act_1", shot_count=5, duration_range_seconds=(10, 15)),
            ]
        )
        issues = validate_execution_brief({}, brief)
        assert any("too_few_movements" in i["code"] for i in issues)

    def test_blocks_too_many_movements(self) -> None:
        brief = _brief(
            movements=[
                MovementSpec(movement_id=f"act_{n}", shot_count=2, duration_range_seconds=(10, 15))
                for n in range(1, 7)
            ]
        )
        issues = validate_execution_brief({}, brief)
        assert any("too_many_movements" in i["code"] for i in issues)

    def test_blocks_zero_shots(self) -> None:
        # When no movements exist, total_shots = 0 → zero_shots fires.
        # Pydantic validates shot_count >= 1, so this only catches
        # the empty-movements case (also caught by too_few_movements).
        brief = ExecutionBrief(
            project_id="test",
            target_runtime_seconds=240,
            movements=[],
            mandatory_anchors=["hero"],
            environment_progression=[],
            pacing_style="standard",
        )
        issues = validate_execution_brief({}, brief)
        assert any("zero_shots" in i["code"] for i in issues)

    def test_blocks_runtime_inconsistency(self) -> None:
        brief = _brief(
            runtime=300,
            movements=[
                MovementSpec(movement_id="act_1", shot_count=1, duration_range_seconds=(2, 5)),
            ],
        )
        issues = validate_execution_brief({}, brief)
        assert any("runtime_inconsistent" in i["code"] for i in issues)

    def test_blocks_no_anchors(self) -> None:
        brief = _brief(
            runtime=240,
            movements=[
                MovementSpec(movement_id="act_1", shot_count=5, duration_range_seconds=(10, 15)),
                MovementSpec(movement_id="act_2", shot_count=5, duration_range_seconds=(10, 15)),
            ],
        )
        brief = ExecutionBrief(
            project_id="test",
            target_runtime_seconds=240,
            movements=[
                MovementSpec(movement_id="act_1", shot_count=5, duration_range_seconds=(10, 15)),
                MovementSpec(movement_id="act_2", shot_count=5, duration_range_seconds=(10, 15)),
            ],
            mandatory_anchors=[],
            environment_progression=[],
            pacing_style="slow_cinema",
        )
        issues = validate_execution_brief({}, brief)
        assert any("no_anchors" in i["code"] for i in issues)


# ── Dict-row coverage for all three gates ─────────────────────────────────


class TestGateDictRows:
    """Verify gates handle dict rows correctly (not just dataclass rows)."""

    def test_gate_a_dict_rows_shot_count(self) -> None:
        brief = _brief(
            runtime=25,
            movements=[
                MovementSpec(movement_id="act_1", shot_count=2, duration_range_seconds=(10, 15)),
            ],
        )
        matrix = {
            "rows": [
                {"shot_id": "s1", "act_id": "act_1", "duration_seconds": 12},
                {"shot_id": "s2", "act_id": "act_1", "duration_seconds": 13},
            ]
        }
        issues = validate_shot_structure({}, brief, matrix)
        assert issues == []

    def test_gate_a_dict_rows_mismatch(self) -> None:
        brief = _brief(
            runtime=12,
            movements=[
                MovementSpec(movement_id="act_1", shot_count=5, duration_range_seconds=(10, 15)),
            ],
        )
        matrix = {
            "rows": [
                {"shot_id": "s1", "act_id": "act_1", "duration_seconds": 12},
            ]
        }
        issues = validate_shot_structure({}, brief, matrix)
        assert len(issues) == 1
        assert "shot_count_mismatch" in issues[0]["code"]

    def test_gate_b_dict_rows_missing_fields(self) -> None:
        matrix = {
            "rows": [
                {
                    "shot_id": "s1",
                    "prompt_ref": "",
                    "characters": [],
                    "environment": "",
                    "camera_profile": "",
                },
            ]
        }
        cost: dict[str, Any] = {"clip_count": 1, "total_cost_usd": 5.0}
        issues = validate_planning_completeness({}, matrix, cost)
        assert any("incomplete_shot_rows" in i["code"] for i in issues)
