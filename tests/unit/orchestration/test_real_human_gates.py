"""Tests for Phase 1 — Real Human Gates with interrupt() + checkpointer."""

from __future__ import annotations

from typing import Any, cast


class TestGraphWithCheckpointer:
    def test_graph_compiles_with_checkpointer(self) -> None:
        """Graph compiles with MemorySaver checkpointer."""
        from film_pipeline.studio.graph_factory import build_graph

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
        assert "approve_phase" in _get_actions(payload)

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
        actions = _get_actions(payload)
        assert "approve_phase" not in actions
        assert "request_revision" in actions
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
        actions = _get_actions(payload)
        assert "approve_phase" not in actions
        assert "escalate" in actions
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
        actions = _get_actions(payload)
        assert "approve_phase" in actions
        assert "request_revision" in actions
        assert payload["blocking_issue_count"] == 0


class TestAfterApproval:
    def test_approved_advances_to_next_phase(self) -> None:
        """Approved intake routes to constitution."""
        from film_pipeline.orchestration.edges import after_approval

        state: dict[str, object] = {
            "current_phase": "intake",
            "approved": True,
            "_orchestrator__convergence": {},
        }
        assert after_approval(state) == "constitution"

    def test_issues_not_stalled_routes_to_repair(self) -> None:
        """Unapproved issues route to repair (when not stalled)."""
        from film_pipeline.orchestration.edges import after_approval

        state: dict[str, object] = {
            "current_phase": "intake",
            "approved": False,
            "issues": [{"severity": "blocking"}],
            "_orchestrator__convergence": {},
        }
        assert after_approval(state) == "repair"

    def test_stalled_with_issues_stays_at_gate(self) -> None:
        """Stalled phase stays at await_approval (not repair → infinite loop)."""
        from film_pipeline.orchestration.edges import after_approval

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
        assert state["human_approval_required"] is True
        assert state["_stalled_phase"] == "shot_bible"
        issues = cast(list[dict[str, object]], state["issues"])
        stalled_issues = [
            issue
            for issue in issues
            if isinstance(issue, dict) and issue.get("code") == "ORCHESTRATOR_STALLED"
        ]
        assert len(stalled_issues) == 1
        assert after_approval(state) == "await_approval"
        issues = cast(list[dict[str, object]], state["issues"])
        stalled_issues = [
            issue
            for issue in issues
            if isinstance(issue, dict) and issue.get("code") == "ORCHESTRATOR_STALLED"
        ]
        assert len(stalled_issues) == 1


def _build_payload(state: dict[str, object]) -> dict[str, object]:
    """Replicate the payload-building logic from await_approval_node for testing."""
    from film_pipeline.orchestration.orchestrator_state import is_stalled

    phase = str(state.get("current_phase", ""))
    gate = str(state.get("human_approval_phase", ""))
    issues = state.get("issues", [])
    if isinstance(issues, list):
        blocking_count = sum(
            1 for i in issues if isinstance(i, dict) and i.get("severity") == "blocking"
        )
    else:
        blocking_count = 0
    stalled = is_stalled(state, phase)

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


def _get_actions(payload: dict[str, object]) -> list[str]:
    """Extract allowed_actions as a typed list for assertions."""
    from typing import cast

    actions: object = payload.get("allowed_actions", [])
    return cast(list[str], actions) if isinstance(actions, list) else []


class TestHumanGateMandatory:
    """Human gate cannot be bypassed by the orchestrator agent."""

    def test_await_approval_interrupts_even_when_orchestrator_approves(
        self, monkeypatch: Any
    ) -> None:
        """With human gates ON, orchestrator approve recommendation still pauses."""
        from film_pipeline.orchestration.nodes import await_approval_node

        called: dict[str, object] = {}

        def fake_interrupt(payload: dict[str, object]) -> dict[str, object]:
            called["payload"] = payload
            return {"action": "approve_phase"}

        monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)
        monkeypatch.setattr(
            "film_pipeline.orchestration.nodes.approval._run_orchestrator_agent",
            lambda _state: {"action": "approve", "feedback": "looks good", "preserve": []},
        )

        state: dict[str, Any] = {
            "project_id": "test-human-gate",
            "current_phase": "script",
            "human_approval_phase": "script",
            "artifact_refs": [],
            "issues": [],
            "resolved_config": {"studio": {"require_human_approval": True}},
        }
        result = await_approval_node(state)
        assert "payload" in called
        payload = cast(dict[str, object], called["payload"])
        assert payload.get("phase") == "script"
        recommendation = payload.get("recommendation")
        assert isinstance(recommendation, dict)
        assert recommendation.get("action") == "approve"
        assert result.get("approved") is True


class TestAutoApprove:
    """Phase nodes and await_approval_node behavior when require_human_approval is off."""

    def test_require_human_approval_defaults_true(self) -> None:
        """Missing config → gates stay ON (safe default)."""
        from film_pipeline.orchestration.orchestrator_state import _require_human_approval

        assert _require_human_approval({}) is True
        assert _require_human_approval({"resolved_config": {}}) is True

    def test_require_human_approval_reads_config_false(self) -> None:
        """require_human_approval: false → gates OFF."""
        from film_pipeline.orchestration.orchestrator_state import _require_human_approval

        state: dict[str, Any] = {
            "resolved_config": {
                "studio": {"require_human_approval": False},
            }
        }
        assert _require_human_approval(state) is False

    def test_require_human_approval_reads_config_true(self) -> None:
        """require_human_approval: true → gates ON."""
        from film_pipeline.orchestration.orchestrator_state import _require_human_approval

        state: dict[str, Any] = {
            "resolved_config": {
                "studio": {"require_human_approval": True},
            }
        }
        assert _require_human_approval(state) is True

    def test_await_approval_passes_through_when_approved(self) -> None:
        """await_approval_node returns no updates when already approved."""
        from film_pipeline.orchestration.nodes import await_approval_node

        state: dict[str, Any] = {
            "approved": True,
            "current_phase": "script",
            "human_approval_phase": "script",
            "project_id": "test",
            "artifact_refs": [],
            "issues": [],
        }
        result = await_approval_node(state)
        assert result == {}
        assert state.get("approved") is True

    def test_phase_node_auto_approves_when_config_false(self) -> None:
        """Phase node sets approved=True when require_human_approval is off."""
        from film_pipeline.orchestration.nodes import intake_node
        from film_pipeline.orchestration.orchestrator_state import _require_human_approval

        state: dict[str, Any] = {
            "project_id": "test-auto",
            "idea": "A test idea.",
            "resolved_config": {
                "studio": {"require_human_approval": False},
            },
            "artifact_refs": [],
        }
        assert _require_human_approval(state) is False
        updates = intake_node(state)
        assert updates.get("approved") is True
        assert updates.get("human_approval_required") is False

    def test_phase_node_requires_approval_when_config_true(self) -> None:
        """Phase node sets approved=False when require_human_approval is on."""
        from film_pipeline.orchestration.nodes import intake_node

        state: dict[str, Any] = {
            "project_id": "test-manual",
            "idea": "A test idea.",
            "resolved_config": {
                "studio": {"require_human_approval": True},
            },
            "artifact_refs": [],
        }
        updates = intake_node(state)
        assert updates.get("approved") is False
        assert updates.get("human_approval_required") is True


class TestExternalStateReplay:
    """External MCP mutations must be replayed into resumed checkpoints."""

    def test_apply_external_state_adds_new_generation_requests(self) -> None:
        from film_pipeline.orchestration.nodes import _apply_external_state

        state: dict[str, Any] = {
            "generation_requests": [{"generation_request_id": "r1", "shot_id": "s1"}],
        }
        external: dict[str, Any] = {
            "generation_requests": [{"generation_request_id": "r2", "shot_id": "s2"}],
        }
        updates = _apply_external_state(state, external)
        assert len(updates["generation_requests"]) == 1
        assert updates["generation_requests"][0]["generation_request_id"] == "r2"

    def test_apply_external_state_skips_existing_requests(self) -> None:
        from film_pipeline.orchestration.nodes import _apply_external_state

        state: dict[str, Any] = {
            "generation_requests": [{"generation_request_id": "r1", "shot_id": "s1"}],
        }
        external: dict[str, Any] = {
            "generation_requests": [
                {"generation_request_id": "r1", "shot_id": "s1"},
                {"generation_request_id": "r2", "shot_id": "s2"},
            ],
        }
        updates = _apply_external_state(state, external)
        assert len(updates["generation_requests"]) == 1
        assert updates["generation_requests"][0]["generation_request_id"] == "r2"

    def test_apply_external_state_empty_when_no_new_requests(self) -> None:
        from film_pipeline.orchestration.nodes import _apply_external_state

        state: dict[str, Any] = {"generation_requests": [{"generation_request_id": "r1"}]}
        external: dict[str, Any] = {"generation_requests": [{"generation_request_id": "r1"}]}
        updates = _apply_external_state(state, external)
        assert updates == {}

    def test_build_resume_payload_carries_generation_requests(self) -> None:
        from film_pipeline.studio._resume import _build_resume_payload

        active: dict[str, Any] = {"generation_requests": [{"generation_request_id": "r1"}]}
        payload = _build_resume_payload("approve", active)
        assert payload["action"] == "approve"
        assert payload["_external_state"]["generation_requests"] == active["generation_requests"]

    def test_build_resume_payload_omits_external_state_when_empty(self) -> None:
        from film_pipeline.studio._resume import _build_resume_payload

        active: dict[str, Any] = {}
        payload = _build_resume_payload("approve", active)
        assert payload == {"action": "approve"}

    def test_await_approval_applies_external_state_on_resume(self, monkeypatch: Any) -> None:
        from film_pipeline.orchestration.nodes import await_approval_node

        def fake_interrupt(payload: dict[str, object]) -> dict[str, object]:
            return {
                "action": "approve_phase",
                "_external_state": {
                    "generation_requests": [
                        {"generation_request_id": "r2", "shot_id": "s2"},
                    ],
                },
            }

        monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)
        monkeypatch.setattr(
            "film_pipeline.orchestration.nodes.approval._run_orchestrator_agent",
            lambda _state: None,
        )

        state: dict[str, Any] = {
            "project_id": "test-external",
            "current_phase": "generation",
            "human_approval_phase": "generation_batch",
            "artifact_refs": [],
            "issues": [],
            "generation_requests": [{"generation_request_id": "r1", "shot_id": "s1"}],
        }
        result = await_approval_node(state)
        assert result.get("approved") is True
        # The node returns only the *new* requests as a partial update;
        # LangGraph's ``add`` reducer appends them to the existing channel.
        request_ids = {r["generation_request_id"] for r in result.get("generation_requests", [])}
        assert request_ids == {"r2"}
