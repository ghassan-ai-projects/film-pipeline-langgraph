"""Compatibility and consumer checks for the one phase-sequence owner."""

from __future__ import annotations

from itertools import pairwise
from typing import cast
from unittest.mock import Mock

import pytest
from langgraph.checkpoint.memory import MemorySaver

from film_pipeline.app import _graph_exec
from film_pipeline.app.graph_factory import (
    _APPROVAL_DESTINATIONS,
    _route_current_phase,
    build_graph,
)
from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.filmspec import PHASE_SEQUENCE as CANONICAL_PHASE_SEQUENCE
from film_pipeline.filmspec import FilmPhase as CanonicalFilmPhase
from film_pipeline.filmspec import next_phase as canonical_next_phase
from film_pipeline.orchestration.edges import after_approval
from film_pipeline.orchestration.nodes._repair_loop import _PHASE_NODES
from film_pipeline.orchestration.phase_sequence import (
    PHASE_NODES,
    PHASE_ORDER,
    PHASE_SEQUENCE,
    next_phase,
)
from film_pipeline.orchestration.router import PHASE_ORDER as PUBLIC_PHASE_ORDER
from film_pipeline.schemas import FilmPhase


def test_phase_order_preserves_the_serialized_workflow() -> None:
    """Reordering enum members would change resume and approval semantics."""
    expected = [
        "intake",
        "constitution",
        "development",
        "script",
        "visual_dev",
        "shot_bible",
        "gen_planning",
        "generation",
        "qc",
        "post",
        "delivery",
    ]
    assert list(PHASE_SEQUENCE) == expected
    assert expected == PHASE_ORDER
    assert [phase.value for phase in FilmPhase] == list(PHASE_SEQUENCE)
    assert PUBLIC_PHASE_ORDER is PHASE_ORDER
    assert FilmPhase is CanonicalFilmPhase
    assert PHASE_SEQUENCE is CANONICAL_PHASE_SEQUENCE
    assert next_phase is canonical_next_phase


def test_legacy_list_mutation_does_not_change_internal_sequence() -> None:
    original_order = PHASE_ORDER.copy()
    try:
        PHASE_ORDER[:] = ["invalid"]
        assert next_phase("intake") == "constitution"
        assert after_approval({"approved": True, "current_phase": "intake"}) == "constitution"
        assert _route_current_phase({"current_phase": "intake"}) == PHASE_NODES["intake"]
    finally:
        PHASE_ORDER[:] = original_order


def test_successor_and_approval_edges_agree_for_every_phase() -> None:
    for current, successor in pairwise(PHASE_SEQUENCE):
        assert next_phase(current) == successor
        assert after_approval({"approved": True, "current_phase": current}) == successor
        assert _APPROVAL_DESTINATIONS[successor] == PHASE_NODES[successor]

    assert next_phase("delivery") is None
    assert after_approval({"approved": True, "current_phase": "delivery"}) == "end"
    assert next_phase("unknown") is None
    assert after_approval({"approved": True, "current_phase": "unknown"}) == "end"


def test_every_phase_node_is_registered_and_dispatchable() -> None:
    graph = build_graph(checkpointer=MemorySaver())
    assert set(PHASE_NODES) == set(PHASE_SEQUENCE)
    assert set(_PHASE_NODES) == set(PHASE_SEQUENCE)
    assert set(PHASE_NODES.values()) <= set(graph.nodes)
    for phase, node in PHASE_NODES.items():
        assert _route_current_phase({"current_phase": phase}) == node
    assert _route_current_phase({"current_phase": "unknown"}) == PHASE_NODES["intake"]


def test_app_advance_uses_the_same_successor_and_preserves_terminal_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = Mock()
    runtime.projects = {}
    run_phase_node = Mock(
        side_effect=lambda _runtime, state, phase: {**state, "current_phase": phase}
    )
    monkeypatch.setattr(_graph_exec, "run_phase_node", run_phase_node)

    state = {"project_id": "p1", "current_phase": "script"}
    advanced = _graph_exec.advance_to_next_phase(cast(StudioRuntime, runtime), state)
    assert advanced["current_phase"] == "visual_dev"
    run_phase_node.assert_called_once_with(runtime, state, "visual_dev")

    run_phase_node.reset_mock()
    terminal = _graph_exec.advance_to_next_phase(
        cast(StudioRuntime, runtime), {"project_id": "p1", "current_phase": "delivery"}
    )
    assert terminal["completed"] is True
    assert terminal["human_approval_phase"] == ""
    run_phase_node.assert_not_called()
