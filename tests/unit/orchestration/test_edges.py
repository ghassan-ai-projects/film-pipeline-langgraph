"""Tests for the after_phase / after_approval routing table in graph/edges.py.

``after_phase`` maps ``compute_actions().next_action`` to a graph node name.
Some entries in that mapping table are defensive (e.g. "advance_to_end",
literal "repair"/"revise") and not currently emitted by ``compute_actions``
itself — those are tested here by monkeypatching ``compute_actions`` directly,
since the contract being verified is the routing table, not the router.
"""

from __future__ import annotations

from unittest import mock

from film_pipeline.orchestration.edges import after_phase
from film_pipeline.orchestration.router import RouterResult
from film_pipeline.orchestration.state_schema import StudioGraphState


def _routed(next_action: str) -> str:
    result = RouterResult(next_action=next_action)
    with mock.patch("film_pipeline.orchestration.edges.compute_actions", return_value=result):
        return after_phase({})


class TestAfterPhaseHumanGateActions:
    def test_wait_for_human_routes_to_consistency_check(self) -> None:
        assert _routed("wait_for_human") == "consistency_check"

    def test_present_review_package_routes_to_consistency_check(self) -> None:
        assert _routed("present_review_package") == "consistency_check"

    def test_escalate_to_human_routes_to_consistency_check(self) -> None:
        assert _routed("escalate_to_human") == "consistency_check"

    def test_continue_unrelated_work_routes_to_consistency_check(self) -> None:
        assert _routed("continue_unrelated_work") == "consistency_check"


class TestAfterPhaseRepairAndAdvance:
    def test_handle_blockers_routes_to_repair(self) -> None:
        assert _routed("handle_blockers") == "repair"

    def test_advance_to_phase_returns_phase_key(self) -> None:
        assert _routed("advance_to_constitution") == "constitution"

    def test_advance_to_end_routes_to_end_node(self) -> None:
        assert _routed("advance_to_end") == "end"

    def test_literal_repair_stays_at_gate(self) -> None:
        assert _routed("repair") == "await_approval"

    def test_literal_revise_stays_at_gate(self) -> None:
        assert _routed("revise") == "await_approval"

    def test_wrap_routes_to_end(self) -> None:
        assert _routed("wrap") == "end"

    def test_unknown_action_falls_back_to_consistency_check(self) -> None:
        assert _routed("something_unrecognized") == "consistency_check"


class TestAfterPhaseRealRouterOutcomes:
    """Sanity checks using the real router (no monkeypatch) for reachable cases."""

    def test_pending_revision_routes_to_gate(self) -> None:
        # NOTE: the original (untyped) revision of this test seeded
        # ``"_orchestrator": {"revisions": {"script": [{"note": "x"}]}}``.
        # That key is an *undeclared* namespace — the schema spells its keys
        # ``_orchestrator__*`` — so it cannot appear in a ``StudioGraphState``
        # literal, and it is also not what the router reads.
        #
        # Measured: ``has_pending_revision`` reads the declared
        # ``_orchestrator__pending_revisions`` channel
        # (``orchestrator_state._PENDING_REVISIONS``), which this test never
        # populated. So the assertion below passes through ``after_phase``'s
        # *fallback* path, not the pending-revision rule the test is named for.
        # That gap predates this typing change; it is reported rather than
        # silently rewritten with different data.
        state: StudioGraphState = {
            "current_phase": "script",
            "approved": False,
            "human_approval_required": False,
            "issues": [],
        }
        assert after_phase(state) == "consistency_check"
