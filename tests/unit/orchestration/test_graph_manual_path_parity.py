"""One lifecycle: the graph's nodes and the manual path's nodes must be the same.

## What these guards exist for

``docs/modularity-improvements/02`` found two divergent duplicates of the core
lifecycle, and a green suite said nothing about either:

**A — a second graph executor.** ``studio/_graph_exec.run_phase_node`` runs a
phase node *outside* the compiled graph and merges its result with a **hand-written
reducer table**. LangGraph instead applies the reducers declared on
``StudioGraphState``'s ``Annotated`` channels. The two tables disagreed on 4 of 8
accumulating channels, so any consumer of the manual path — ``approve_phase``
without a checkpoint, and every ``resume_stalled_manual_advance`` — merged node
results by different rules than the graph does.

**B — two QC implementations.** ``build_graph`` wires ``qc_node`` to the parallel
subgraph (``build_qc_subgraph``); ``_PHASE_NODES["qc"]`` pointed at the sequential
``nodes.qc.qc_node``, which is what ``repair_phase_node`` re-runs on a revision
round. A film's first QC pass and its repair QC pass therefore ran different code.

The hand-maintained reducer copy is the defect class: a newly annotated channel is
*invisible* to it. That is why the parity test does not enumerate a fixed channel
list — it walks ``typing.get_type_hints(..., include_extras=True)``, so a channel
added tomorrow is graded the day it is added.

## How to read a failure here

Both tests are written to fail on the pre-fix tree. ``test_phase_nodes_match_graph``
fails on ``qc`` only; ``test_manual_merge_matches_graph_reducer`` fails on the four
channels listed in 02's table.
"""

from __future__ import annotations

import tempfile
import typing
from pathlib import Path
from typing import Any

import pytest

from film_pipeline.orchestration.nodes._repair_loop import _PHASE_NODES
from film_pipeline.orchestration.state_schema import StudioGraphState, apply_node_update
from film_pipeline.studio.graph_factory import build_graph


def _graph_node_callable(phase: str) -> Any:
    """The callable ``build_graph`` actually registered for ``phase``.

    Two layers are unwrapped: ``builder.nodes`` holds a ``StateNodeSpec`` whose
    ``runnable`` is the callable as registered, and a plain function is wrapped in
    a ``RunnableCallable`` whose ``func`` is the original. A compiled subgraph has
    neither, which is exactly what makes the qc divergence visible.
    """
    graph = build_graph(runtime_root=Path(tempfile.mkdtemp()))
    spec = graph.builder.nodes[f"{phase}_node"]
    runnable = getattr(spec, "runnable", spec)
    return getattr(runnable, "func", runnable)


# --- B: one callable per phase ------------------------------------------------


def test_phase_nodes_match_graph() -> None:
    """Every phase's repair/manual node is the object the graph wires.

    A phase with two implementations is a phase whose first pass and repair pass
    run different code. Ten of eleven phases already agree; this pins all eleven so
    the eleventh cannot drift back.
    """
    divergent = {
        phase: (node, _graph_node_callable(phase))
        for phase, node in _PHASE_NODES.items()
        if _graph_node_callable(phase) is not node
    }
    shape = {
        phase: (getattr(node, "__name__", node), type(wired).__name__)
        for phase, (node, wired) in divergent.items()
    }
    assert not divergent, (
        "these phases have two implementations: `_PHASE_NODES[phase]` is not the "
        "callable `build_graph` registers for `<phase>_node`. Measured "
        f"{shape}. Point `_PHASE_NODES` at the graph's own object, or the phase is "
        "running one code path on its first pass and another on repair."
    )


def test_phase_nodes_covers_the_whole_sequence() -> None:
    """Guard the guard: the identity test is vacuous if the table is empty/short."""
    from film_pipeline.filmspec import PHASE_SEQUENCE

    assert set(_PHASE_NODES) == set(PHASE_SEQUENCE), (
        "`_PHASE_NODES` must name exactly the film's phases, or the identity test "
        "above silently grades a subset."
    )


# --- A: one reducer source ----------------------------------------------------


def _annotated_channels() -> dict[str, Any]:
    """Map every ``Annotated[T, reducer]`` channel of ``StudioGraphState``.

    Resolved from the live type hints rather than a hand-kept list, so a channel
    added to the schema without teaching the manual path about it fails here
    instead of mis-merging in production.
    """
    hints = typing.get_type_hints(StudioGraphState, include_extras=True)
    return {
        name: hint.__metadata__[0]
        for name, hint in hints.items()
        if typing.get_origin(hint) is typing.Annotated and hint.__metadata__
    }


def test_the_schema_still_declares_annotated_channels() -> None:
    """Guard the guard: with no annotated channels, parity is vacuously true."""
    channels = _annotated_channels()
    assert len(channels) >= 6, (
        f"expected at least the six known accumulating channels, found {sorted(channels)}. "
        "If the schema really dropped them, update this floor deliberately."
    )


@pytest.mark.parametrize("channel", sorted(_annotated_channels()), ids=str)
def test_manual_merge_matches_graph_reducer(channel: str) -> None:
    """``run_phase_node``'s merge must equal LangGraph's rule for every channel.

    LangGraph's rule is exact and small: an ``Annotated[T, reducer]`` field merges
    through its reducer; every other key is a last write. The manual executor used
    to carry its own table, which disagreed with this rule on ``_routing_decisions``,
    ``_validation_reports``, ``_qc_reports`` and ``_qc_raw_reports``.

    The sample values are shaped to the channel's declared element type:
    ``merge_unique`` is a **string**-ref reducer and raises on a dict, so feeding
    it dicts would test the sample rather than the merge rule.
    """
    reducer = _annotated_channels()[channel]
    element: Any = "artifact:script:v1" if channel.endswith("_refs") else {"marker": channel}
    existing: Any = []
    incoming = [element]

    merged = apply_node_update({channel: existing}, {channel: incoming})

    expected = reducer(existing, incoming)
    assert merged[channel] == expected, (
        f"channel '{channel}' merged as {merged[channel]!r}, but its declared "
        f"reducer {getattr(reducer, '__name__', reducer)!r} gives {expected!r}. "
        "The manual path is not applying the graph's own merge rule."
    )


def test_non_annotated_keys_are_last_write() -> None:
    """A key with no ``Annotated`` reducer is replaced, not accumulated."""
    merged = apply_node_update(
        {"current_phase": "intake", "_stalled_phase": "old"},
        {"current_phase": "script"},
    )
    assert merged["current_phase"] == "script"
    assert merged["_stalled_phase"] == "old", "keys absent from the update must survive"


def test_update_channels_are_not_hard_coded() -> None:
    """The four channels 02 measured as divergent are merged by the schema's rule.

    A named regression for the exact disagreement in 02's table, so that reverting
    to a hand-written table fails with a message naming the channel rather than
    only the parametrized case.
    """
    divergent = ("_routing_decisions", "_validation_reports", "_qc_reports", "_qc_raw_reports")
    channels = _annotated_channels()
    for channel in divergent:
        if channel not in channels:
            continue
        reducer = channels[channel]
        incoming = [{"marker": channel}]
        merged = apply_node_update({channel: []}, {channel: incoming})
        assert merged[channel] == reducer([], incoming), (
            f"'{channel}' was one of the four channels the manual reducer table "
            f"disagreed on; it must merge through {getattr(reducer, '__name__', reducer)!r}."
        )
