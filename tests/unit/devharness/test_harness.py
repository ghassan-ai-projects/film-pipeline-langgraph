"""Tests for the development harness mock actors and scenario scripts.

This file is the single behaviour suite for ``film_pipeline.devharness``. It
replaces ``tests/unit/test_testing_utils.py`` and
``tests/unit/testing/test_mock_actors.py``, which covered the same behaviour
twice after the harness moved out of the legacy ``testing`` package.
"""

from __future__ import annotations

import pytest

from film_pipeline.devharness.mock_human import DecisionProfile, MockHumanActor
from film_pipeline.devharness.mock_model import MockModelAdapter
from film_pipeline.devharness.scenarios import HAPPY_PATH_SEQUENTIAL_CHAIN


class TestMockHumanActor:
    def test_approve_all_decides_approve(self) -> None:
        actor = MockHumanActor(profile=DecisionProfile.APPROVE_ALL)
        assert actor.decide("script", "approve") == "approve"

    def test_revise_script_once_decides_revision_first(self) -> None:
        actor = MockHumanActor(profile=DecisionProfile.REVISE_SCRIPT_ONCE)
        assert actor.decide("script", "approve") == "request_revision"

    def test_revise_script_once_approves_second(self) -> None:
        actor = MockHumanActor(profile=DecisionProfile.REVISE_SCRIPT_ONCE)
        actor.decide("script", "approve")  # first: revision
        assert actor.decide("script", "approve") == "approve"

    def test_reject_bad_reference(self) -> None:
        actor = MockHumanActor(profile=DecisionProfile.REJECT_BAD_REFERENCE)
        assert actor.decide("visual_dev", "visual_bible_review") == "request_revision"

    def test_reject_bad_reference_approves_other(self) -> None:
        actor = MockHumanActor(profile=DecisionProfile.REJECT_BAD_REFERENCE)
        assert actor.decide("script", "approve") == "approve"

    def test_approve_spend_always_approves(self) -> None:
        actor = MockHumanActor(profile=DecisionProfile.APPROVE_SPEND_UNDER_LIMIT)
        assert actor.decide("gen_planning", "approve_spend") == "approve"

    def test_stop_on_provider_block_approves(self) -> None:
        actor = MockHumanActor(profile=DecisionProfile.STOP_ON_PROVIDER_BLOCK)
        assert actor.decide("generation", "resolve_block") == "approve"

    def test_confirm_rollback_approves(self) -> None:
        actor = MockHumanActor(profile=DecisionProfile.CONFIRM_ROLLBACK)
        assert actor.decide("script", "confirm_rollback") == "approve"

    def test_reject_final_cut(self) -> None:
        actor = MockHumanActor(profile=DecisionProfile.REJECT_FINAL_CUT)
        assert actor.decide("post", "final_cut_review") == "request_revision"

    def test_reject_final_cut_approves_other(self) -> None:
        actor = MockHumanActor(profile=DecisionProfile.REJECT_FINAL_CUT)
        assert actor.decide("script", "approve") == "approve"

    def test_disabled_in_production(self) -> None:
        actor = MockHumanActor(test_mode=False)
        with pytest.raises(RuntimeError, match="production"):
            actor.decide("script", "approve")

    def test_approval_record_metadata(self) -> None:
        actor = MockHumanActor()
        meta = actor.approval_record_metadata()
        assert meta["actor_type"] == "mock_human"
        assert meta["profile"] == "approve_all"


class TestMockModelAdapter:
    def test_register_and_call(self) -> None:
        model = MockModelAdapter()
        model.register("agent-1", {"result": "ok"})
        assert model.call("agent-1") == {"result": "ok"}

    def test_unregistered_returns_default(self) -> None:
        model = MockModelAdapter()
        output = model.call("unknown")
        assert output["agent"] == "unknown"
        assert output["mock_model"] is True

    def test_agent_response_uses_call(self) -> None:
        model = MockModelAdapter()
        model.register("agent-a", {"data": 42})
        assert model.agent_response("agent-a") == {"data": 42}

    def test_validator_response_default(self) -> None:
        model = MockModelAdapter()
        output = model.validator_response("val-1")
        assert output["score"] == 90
        assert output["status"] == "pass"

    def test_validator_response_registered(self) -> None:
        model = MockModelAdapter()
        model.register("val-x", {"score": 75, "status": "review", "issues": ["bad"]})
        output = model.validator_response("val-x")
        assert output["score"] == 75
        assert output["status"] == "review"

    def test_registered_response_is_not_mutated_by_callers(self) -> None:
        """``call`` must return a copy so a caller cannot corrupt the registry."""
        model = MockModelAdapter()
        model.register("a", {"x": 1})
        first = model.call("a")
        first["x"] = 99
        assert model.call("a")["x"] == 1


class TestScenarios:
    def test_happy_path_steps(self) -> None:
        assert len(HAPPY_PATH_SEQUENTIAL_CHAIN) == 3
        assert HAPPY_PATH_SEQUENTIAL_CHAIN[0].shot_id == "S001-01"
        assert HAPPY_PATH_SEQUENTIAL_CHAIN[0].submit == "success"
