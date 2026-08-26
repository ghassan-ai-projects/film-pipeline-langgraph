"""Tests for ShotBibleAgent — produces MasterFilmMatrix from model output."""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.agents.impl.registry import get_agent_class
from film_pipeline.agents.impl.shot_bible_agent import ShotBibleAgent
from film_pipeline.schemas._base import AgentFamily, AgentRole
from film_pipeline.schemas.handoff import AgentRegistration
from film_pipeline.schemas.kb import KBContextPacket
from film_pipeline.schemas.matrix import MasterFilmMatrix


def _make_contract() -> AgentRegistration:
    return AgentRegistration(
        agent_id="shot-design-agent",
        family=AgentFamily.DIRECTING,
        role=AgentRole.CREATOR,
        capabilities=["shot_design", "matrix_assembly", "coverage_planning"],
        input_artifacts=["script", "scene_intents", "character_bible", "environment_bible"],
        output_artifacts=["shot_bible", "master_film_matrix"],
    )


def _make_kb() -> KBContextPacket:
    return KBContextPacket(
        kb_context_id="kbctx:shots:v1",
        project_id="test-project",
        phase="visual_dev",
        agent_id="shot-design-agent",
        task="Assemble the master film matrix.",
    )


def _make_agent() -> ShotBibleAgent:
    return ShotBibleAgent(_make_contract())


_SHOT_ROW: dict[str, Any] = {
    "shot_id": "shot_0001",
    "act_id": "act1",
    "sequence_id": "seq_001",
    "scene_id": "sc_010",
    "scene_intent_ref": "scene_intent:sc_010:v1",
    "duration_seconds": 8,
    "story_function": "inciting image",
    "characters": ["leo"],
    "environment": "studio",
    "camera_profile": "anamorphic_wide",
    "prompt_ref": "prompt:shot_0001:v1",
    "generation_order": 1,
    "chaining": {"input_frame_ref": "asset:frame_0009", "re_anchor": True},
    "priority": "hero",
    "risk_level": "low",
}

_COVERAGE_GROUP: dict[str, Any] = {
    "coverage_group_id": "cg_001",
    "scene_id": "sc_010",
    "story_moment": "the reveal",
    "continuity_event": "the glass shatters",
    "coverage_type": "emotional_reveal",
    "required_angles": ["vp_wide", "vp_insert_hands"],
    "editorial_intent": "cut on the reveal, hold two beats wide.",
}

_VALID_OUTPUT: dict[str, Any] = {
    "project_id": "test-project",
    "rows": [_SHOT_ROW],
    "coverage_groups": [_COVERAGE_GROUP],
}


class TestShotBibleAgent:
    def test_registry_resolves_shot_design_agent_to_class(self) -> None:
        assert get_agent_class("shot-design-agent") is ShotBibleAgent

    def test_execute_produces_valid_matrix(self) -> None:
        agent = _make_agent()
        result = agent.execute(_VALID_OUTPUT)
        matrix = result["shot_matrix"]
        assert isinstance(matrix, MasterFilmMatrix)
        assert matrix.project_id == "test-project"
        assert len(matrix.rows) == 1
        row = matrix.rows[0]
        assert row.shot_id == "shot_0001"
        assert row.scene_id == "sc_010"
        assert row.duration_seconds == 8
        assert row.priority == "hero"
        assert row.risk_level == "low"
        assert row.characters == ["leo"]
        assert row.chaining.input_frame_ref == "asset:frame_0009"
        assert row.chaining.re_anchor is True

    def test_execute_builds_coverage_group(self) -> None:
        agent = _make_agent()
        group = agent.execute(_VALID_OUTPUT)["shot_matrix"].coverage_groups[0]
        assert group.coverage_group_id == "cg_001"
        assert group.scene_id == "sc_010"
        assert group.coverage_type == "emotional_reveal"
        assert group.required_angles == ["vp_wide", "vp_insert_hands"]

    def test_execute_handles_nested_output(self) -> None:
        agent = _make_agent()
        result = agent.execute({"shot_matrix": _VALID_OUTPUT})
        matrix = result["shot_matrix"]
        assert matrix.project_id == "test-project"
        assert matrix.rows[0].shot_id == "shot_0001"

    def test_execute_handles_raw_list_of_shots(self) -> None:
        agent = _make_agent()
        result = agent.execute({"shot_matrix": [_SHOT_ROW]})
        matrix = result["shot_matrix"]
        # The bare-list form carries no project id section.
        assert matrix.project_id == ""
        assert [r.shot_id for r in matrix.rows] == ["shot_0001"]
        assert matrix.coverage_groups == []

    def test_execute_fills_defaults_for_minimal_row(self) -> None:
        agent = _make_agent()
        row = agent.execute({"rows": [{}]})["shot_matrix"].rows[0]
        assert row.shot_id == "shot_0000"
        assert row.act_id == "act1"
        assert row.sequence_id == "seq_000"
        assert row.duration_seconds == 5
        assert row.generation_order == 0
        assert row.priority == "standard"
        assert row.risk_level == "medium"
        assert row.chaining.input_frame_ref is None
        assert row.chaining.re_anchor is False

    def test_execute_handles_empty_input(self) -> None:
        agent = _make_agent()
        matrix = agent.execute({})["shot_matrix"]
        assert isinstance(matrix, MasterFilmMatrix)
        assert matrix.rows == []
        assert matrix.coverage_groups == []

    def test_validate_passes_for_valid_matrix(self) -> None:
        agent = _make_agent()
        result = agent.execute(_VALID_OUTPUT)
        assert agent.validate(result) is True

    def test_validate_fails_for_matrix_without_rows(self) -> None:
        agent = _make_agent()
        result = agent.execute({})
        assert agent.validate(result) is False

    def test_validate_fails_for_wrong_artifact_type(self) -> None:
        agent = _make_agent()
        assert agent.validate({"shot_matrix": object()}) is False

    def test_run_lifecycle_round_trips_valid_output(self) -> None:
        agent = _make_agent()
        prepared = agent.prepare(
            {
                "project_id": "test-project",
                "script_ref": "script:v1",
                "visual_refs": "reference_strategy:v1",
            },
            _make_kb(),
            "Assemble the master film matrix.",
        )
        assert prepared == {
            "project_id": "test-project",
            "script_ref": "script:v1",
            "visual_refs": "reference_strategy:v1",
            "task": "Assemble the master film matrix.",
        }
        result = agent.run({}, _make_kb(), "Assemble the master film matrix.", _VALID_OUTPUT)
        assert isinstance(result["shot_matrix"], MasterFilmMatrix)

    def test_run_lifecycle_rejects_invalid_output(self) -> None:
        agent = _make_agent()
        with pytest.raises(ValueError, match="produced invalid output"):
            agent.run({}, _make_kb(), "Assemble the master film matrix.", {})
