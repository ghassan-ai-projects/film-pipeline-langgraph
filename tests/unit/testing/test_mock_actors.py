"""Tests for mock human actor and mock model adapter."""

from __future__ import annotations

import pytest

from film_pipeline.testing.mock_human import DecisionProfile, MockHumanActor
from film_pipeline.testing.mock_model import MockModelAdapter


class TestMockHuman:
    def test_approve_all(self) -> None:
        human = MockHumanActor(profile=DecisionProfile.APPROVE_ALL)
        assert human.decide("script", "script_review") == "approve"
        assert human.decide("generation", "clip_batch_review") == "approve"

    def test_revise_script_once(self) -> None:
        human = MockHumanActor(profile=DecisionProfile.REVISE_SCRIPT_ONCE)
        # First script review → revise
        assert human.decide("script", "script_review") == "request_revision"
        # Second script review → approve
        assert human.decide("script", "script_review") == "approve"

    def test_reject_bad_reference(self) -> None:
        human = MockHumanActor(profile=DecisionProfile.REJECT_BAD_REFERENCE)
        assert human.decide("visual_dev", "visual_bible_review") == "request_revision"
        assert human.decide("script", "script_review") == "approve"

    def test_approve_spend_under_limit(self) -> None:
        human = MockHumanActor(profile=DecisionProfile.APPROVE_SPEND_UNDER_LIMIT)
        assert human.decide("gen_planning", "generation_spend") == "approve"

    def test_stop_on_provider_block(self) -> None:
        human = MockHumanActor(profile=DecisionProfile.STOP_ON_PROVIDER_BLOCK)
        assert human.decide("generation", "clip_batch_review") == "approve"

    def test_confirm_rollback(self) -> None:
        human = MockHumanActor(profile=DecisionProfile.CONFIRM_ROLLBACK)
        assert human.decide("script", "script_review") == "approve"

    def test_reject_final_cut(self) -> None:
        human = MockHumanActor(profile=DecisionProfile.REJECT_FINAL_CUT)
        assert human.decide("delivery", "final_cut_review") == "request_revision"
        assert human.decide("script", "script_review") == "approve"

    def test_production_mode_rejects(self) -> None:
        human = MockHumanActor(test_mode=False)
        with pytest.raises(RuntimeError, match="production mode"):
            human.decide("script", "script_review")

    def test_approval_record_metadata(self) -> None:
        human = MockHumanActor(profile=DecisionProfile.APPROVE_ALL)
        meta = human.approval_record_metadata()
        assert meta["actor_type"] == "mock_human"
        assert meta["profile"] == "approve_all"


class TestMockModel:
    def test_default_response(self) -> None:
        model = MockModelAdapter()
        resp = model.call("unknown-agent")
        assert resp["status"] == "ok"
        assert resp["mock_model"] is True

    def test_registered_response(self) -> None:
        model = MockModelAdapter()
        model.register("test-agent", {"result": "custom", "score": 95})
        resp = model.call("test-agent")
        assert resp["result"] == "custom"
        assert resp["score"] == 95

    def test_agent_response(self) -> None:
        model = MockModelAdapter()
        model.register("script-agent", {"script": "ACT 1..."})
        resp = model.agent_response("script-agent")
        assert resp["script"] == "ACT 1..."

    def test_validator_response_default(self) -> None:
        model = MockModelAdapter()
        resp = model.validator_response("v1")
        assert resp["score"] == 90
        assert resp["status"] == "pass"

    def test_validator_response_registered(self) -> None:
        model = MockModelAdapter()
        model.register("clip-quality-validator", {"score": 65, "status": "blocked"})
        resp = model.validator_response("clip-quality-validator")
        assert resp["score"] == 65
        assert resp["status"] == "blocked"

    def test_response_is_copy(self) -> None:
        model = MockModelAdapter()
        model.register("a", {"x": 1})
        r1 = model.call("a")
        r1["x"] = 99
        r2 = model.call("a")
        assert r2["x"] == 1  # Not mutated
