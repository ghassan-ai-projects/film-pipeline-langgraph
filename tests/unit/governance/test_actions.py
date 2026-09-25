"""Tests for available actions calculator."""

from __future__ import annotations

from film_pipeline.governance.actions import AvailableActions, compute_available_actions


class TestAvailableActions:
    def test_has_action(self) -> None:
        a = AvailableActions(available=["approve_phase"])
        assert a.has_action("approve_phase") is True
        assert a.has_action("request_revision") is False

    def test_is_blocked(self) -> None:
        a = AvailableActions(blocked=["approve_phase"])
        assert a.is_blocked("approve_phase") is True

    def test_block_reason(self) -> None:
        a = AvailableActions(
            blocked=["approve_phase"],
            blocked_reasons={"approve_phase": "Blocking issues exist."},
        )
        assert a.block_reason("approve_phase") == "Blocking issues exist."

    def test_block_reason_default(self) -> None:
        a = AvailableActions()
        assert a.block_reason("nonexistent") == "Unknown reason."


class TestComputeAvailableActions:
    def test_clean_state(self) -> None:
        actions = compute_available_actions()
        assert "approve_phase" in actions.available
        assert "request_revision" in actions.available
        assert "compare_versions" in actions.blocked
        assert "rollback_to_checkpoint" in actions.blocked

    def test_blocking_issues(self) -> None:
        actions = compute_available_actions(has_blocking_issues=True)
        assert "approve_phase" in actions.blocked
        assert "request_revision" in actions.available

    def test_with_previous_version(self) -> None:
        actions = compute_available_actions(has_previous_version=True)
        assert "compare_versions" in actions.available

    def test_with_checkpoint(self) -> None:
        actions = compute_available_actions(has_checkpoint=True)
        assert "rollback_to_checkpoint" in actions.available

    def test_all_available(self) -> None:
        actions = compute_available_actions(
            has_previous_version=True,
            has_checkpoint=True,
        )
        assert "approve_phase" in actions.available
        assert "request_revision" in actions.available
        assert "compare_versions" in actions.available
        assert "rollback_to_checkpoint" in actions.available
        assert len(actions.blocked) == 0
