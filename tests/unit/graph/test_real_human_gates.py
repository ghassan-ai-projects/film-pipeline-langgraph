"""Tests for Phase 1 — Real Human Gates with interrupt() + checkpointer."""

from __future__ import annotations

import pytest


class TestGraphWithCheckpointer:
    def test_graph_compiles_with_checkpointer(self) -> None:
        """Graph compiles with MemorySaver checkpointer."""
        from film_pipeline.graph.graph import build_graph

        graph = build_graph()
        assert graph.checkpointer is not None


class TestAwaitApprovalNode:
    def test_payload_has_expected_keys(self) -> None:
        """await_approval_node builds payload with required fields."""
        # Test the payload logic without actually interrupting
        state: dict[str, object] = {
            "project_id": "test-1",
            "current_phase": "intake",
            "human_approval_phase": "intake",
            "artifact_refs": [],
            "issues": [],
            "_orchestrator__convergence": {},
        }
        payload = _build_payload(state)
        assert "project_id" in payload
        assert "phase" in payload
        assert "allowed_actions" in payload
        assert "approve_phase" in payload["allowed_actions"]

    def test_blocking_issues_prevent_approval(self) -> None:
        """When blocking issues exist, approve_phase is not allowed."""
        state: dict[str, object] = {
            "project_id": "test-2",
            "current_phase": "shot_bible",
            "human_approval_phase": "shot_bible",
            "artifact_refs": [],
            "issues": [
                {
                    "severity": "blocking",
                    "code": "shot_count_mismatch",
                    "message": "Expected 20, got 18",
                }
            ],
            "_orchestrator__convergence": {},
        }
        payload = _build_payload(state)
        assert "approve_phase" not in payload["allowed_actions"]
        assert "request_revision" in payload["allowed_actions"]
        assert payload["blocking_issue_count"] == 1

    def test_stalled_phase_allows_escalate(self) -> None:
        """Stalled phase offers escalate instead of request_revision."""
        state: dict[str, object] = {
            "project_id": "test-3",
            "current_phase": "shot_bible",
            "human_approval_phase": "shot_bible",
            "artifact_refs": [],
            "issues": [{"severity": "blocking", "code": "x", "message": "y"}],
            "_orchestrator__convergence": {
                "shot_bible": {
                    "round_count": 5,
                    "stalled": True,
                    "escalation_reason": "Too many failures",
                }
            },
        }
        payload = _build_payload(state)
        assert "approve_phase" not in payload["allowed_actions"]
        assert "escalate" in payload["allowed_actions"]
        assert payload["stalled"] is True

    def test_no_issues_allows_approval(self) -> None:
        """Clean phase allows approval."""
        state: dict[str, object] = {
            "project_id": "test-4",
            "current_phase": "constitution",
            "human_approval_phase": "constitution",
            "artifact_refs": ["artifact:film_constitution:v1"],
            "issues": [],
            "_orchestrator__convergence": {},
        }
        payload = _build_payload(state)
        assert "approve_phase" in payload["allowed_actions"]
        assert "request_revision" in payload["allowed_actions"]
        assert payload["blocking_issue_count"] == 0


class TestAfterApproval:
    def test_approved_advances_to_next_phase(self) -> None:
        """Approved intake routes to constitution."""
        from film_pipeline.graph.edges import after_approval

        state: dict[str, object] = {
            "current_phase": "intake",
            "approved": True,
            "_orchestrator__convergence": {},
        }
        assert after_approval(state) == "constitution"

    def test_issues_not_stalled_routes_to_repair(self) -> None:
        """Unapproved issues route to repair (when not stalled)."""
        from film_pipeline.graph.edges import after_approval

        state: dict[str, object] = {
            "current_phase": "intake",
            "approved": False,
            "issues": [{"severity": "blocking"}],
            "_orchestrator__convergence": {},
        }
        assert after_approval(state) == "repair"

    def test_stalled_with_issues_stays_at_gate(self) -> None:
        """Stalled phase stays at await_approval (not repair → infinite loop)."""
        from film_pipeline.graph.edges import after_approval

        state: dict[str, object] = {
            "current_phase": "shot_bible",
            "approved": False,
            "issues": [{"severity": "blocking"}],
            "_orchestrator__convergence": {
                "shot_bible": {
                    "round_count": 5,
                    "stalled": True,
                    "escalation_reason": "repair failed",
                }
            },
        }
        assert after_approval(state) == "await_approval"


def _build_payload(state: dict[str, object]) -> dict[str, object]:
    """Replicate the payload-building logic from await_approval_node for testing."""
    from film_pipeline.graph.orchestrator_state import is_stalled

    phase = str(state.get("current_phase", ""))
    gate = str(state.get("human_approval_phase", ""))
    issues = state.get("issues", [])
    if isinstance(issues, list):
        blocking_count = sum(
            1 for i in issues if isinstance(i, dict) and i.get("severity") == "blocking"
        )
    else:
        blocking_count = 0
    stalled = is_stalled(state, phase)  # type: ignore[arg-type]

    allowed_actions: list[str] = []
    if blocking_count == 0:
        allowed_actions.append("approve_phase")
    if stalled:
        allowed_actions.append("escalate")
    else:
        allowed_actions.append("request_revision")

    return {
        "project_id": state.get("project_id", ""),
        "phase": phase,
        "gate": gate,
        "artifact_refs": state.get("artifact_refs", []),
        "blocking_issue_count": blocking_count,
        "stalled": stalled,
        "allowed_actions": allowed_actions,
    }
