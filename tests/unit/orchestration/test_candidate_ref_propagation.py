"""Regression tests for candidate-ref publication across the node boundary.

``_save_artifact`` records candidate refs into the node's deep-copied working
state only. ``_propagate_side_effects`` must copy the
``_orchestrator__candidate_refs`` map into the returned update; otherwise the
refs never reach real graph state and ``approve_phase_node`` promotes nothing.
"""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.orchestration import nodes
from film_pipeline.orchestration.nodes import approve_phase_node
from film_pipeline.orchestration.nodes._agent_handoff import _propagate_side_effects
from film_pipeline.orchestration.orchestrator_state import (
    get_approved_refs,
    get_candidate_refs,
)
from film_pipeline.orchestration.services import _SERVICES_CTX, SERVICES_KEY, GraphServices
from film_pipeline.studio.mock_responses import default_mock_responses


@pytest.fixture(autouse=True)
def _reset_services_contextvar() -> Any:
    """Reset the services ContextVar so it never leaks between tests."""
    token = _SERVICES_CTX.set(None)
    yield
    _SERVICES_CTX.reset(token)


def _mock_state(**extra: Any) -> dict[str, Any]:
    svc = GraphServices.for_mock_runtime(mock_responses=default_mock_responses())
    _SERVICES_CTX.set(svc)
    state: dict[str, Any] = {
        "project_id": "d009-regression",
        "idea": "A lighthouse keeper who mails letters to the future.",
        "current_phase": "intake",
        SERVICES_KEY: svc,
        "resolved_config": {"studio": {"require_human_approval": False}},
        "artifact_refs": [],
    }
    state.update(extra)
    return state


def test_intake_node_publishes_candidate_refs_into_updates() -> None:
    """Refs written into the node's working copy reach the returned update."""
    state = _mock_state(target_runtime_seconds=300)
    updates = nodes.intake_node(state)

    published = get_candidate_refs(updates)
    assert published, "candidate refs must be propagated into node updates"
    assert set(published) >= {"project_profile", "project_constraints", "scope_contract"}

    # Every published ref agrees with the scalar ref channel for its family.
    scalar_refs = {
        "project_profile": updates.get("profile_ref"),
        "project_constraints": updates.get("constraints_ref"),
        "scope_contract": updates.get("scope_contract_ref"),
    }
    for family, ref in scalar_refs.items():
        assert ref is not None
        assert published[family] == ref


def test_propagated_candidate_refs_promote_on_approve() -> None:
    """After LangGraph merges the updates, approval promotes those exact refs."""
    state = _mock_state(target_runtime_seconds=300)
    updates = nodes.intake_node(state)

    # LangGraph merge semantics: partial update applied over accumulated state.
    merged = {**state, **updates}
    decision = approve_phase_node(merged)

    approved = get_approved_refs(
        {**merged, "_orchestrator__approved_refs": decision["_orchestrator__approved_refs"]}
    )
    candidates = get_candidate_refs(merged)
    for family, ref in candidates.items():
        assert approved.get(family) == ref


class TestPropagateSideEffectsCandidateRefs:
    def test_carries_candidate_refs_when_present(self) -> None:
        source: dict[str, Any] = {"_orchestrator__candidate_refs": {"script": "artifact:script:v2"}}
        dest: dict[str, Any] = {}
        _propagate_side_effects(source, dest)
        assert dest["_orchestrator__candidate_refs"] == {"script": "artifact:script:v2"}

    def test_omits_key_when_no_candidates_were_published(self) -> None:
        source: dict[str, Any] = {"_routing_decisions": [{"phase": "intake"}]}
        dest: dict[str, Any] = {}
        _propagate_side_effects(source, dest)
        assert "_orchestrator__candidate_refs" not in dest
        assert dest["_routing_decisions"] == [{"phase": "intake"}]

    def test_empty_map_is_not_reemitted(self) -> None:
        source: dict[str, Any] = {"_orchestrator__candidate_refs": {}}
        dest: dict[str, Any] = {}
        _propagate_side_effects(source, dest)
        assert "_orchestrator__candidate_refs" not in dest
