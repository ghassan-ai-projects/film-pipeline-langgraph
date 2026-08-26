"""Build the complete LangGraph supervisor graph."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Hashable
from pathlib import Path
from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from film_pipeline.graph.edges import after_approval, after_phase
from film_pipeline.graph.nodes import (
    approve_phase_node,
    await_approval_node,
    consistency_check_node,
    constitution_node,
    delivery_node,
    development_node,
    gen_planning_node,
    generation_node,
    intake_node,
    post_node,
    repair_phase_node,
    request_revision_node,
    script_node,
    shot_bible_node,
    visual_dev_node,
)
from film_pipeline.graph.router import PHASE_ORDER
from film_pipeline.graph.state_schema import StudioGraphState
from film_pipeline.graph.subgraphs.qc import build_qc_subgraph


def _checkpoint_dir() -> Path:
    """Return the checkpoint directory honoring FILM_PIPELINE_PERSIST_ROOT."""
    root = Path(os.getenv("FILM_PIPELINE_PERSIST_ROOT", Path.home() / ".film-pipeline"))
    return root / "checkpoints"


_CHECKPOINT_DIR: Path = _checkpoint_dir()
_CHECKPOINT_DB: Path = _CHECKPOINT_DIR / "checkpoints.sqlite"


def _default_checkpointer(runtime_root: Path | None = None) -> BaseCheckpointSaver[Any]:
    """Return SQLite only when persistence is explicitly enabled."""
    if os.getenv("FILM_PIPELINE_NO_PERSIST") or not os.getenv("FILM_PIPELINE_PERSIST_STATE"):
        return MemorySaver()
    checkpoint_dir = runtime_root / "checkpoints" if runtime_root is not None else _CHECKPOINT_DIR
    checkpoint_db = checkpoint_dir / "checkpoints.sqlite"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(checkpoint_db), check_same_thread=False)
    return SqliteSaver(conn=conn)


# Phase key → phase node name, in pipeline order.
_PHASE_TO_NODE: dict[str, str] = {
    "intake": "intake_node",
    "constitution": "constitution_node",
    "development": "development_node",
    "script": "script_node",
    "visual_dev": "visual_dev_node",
    "shot_bible": "shot_bible_node",
    "gen_planning": "gen_planning_node",
    "generation": "generation_node",
    "qc": "qc_node",
    "post": "post_node",
    "delivery": "delivery_node",
}

# Destinations reachable from any phase node via after_phase().
_AFTER_PHASE_DESTINATIONS: dict[str, str] = {
    "consistency_check": "consistency_check",
    "await_approval": "await_approval",
    "repair": "repair",
    "end": "end",
    **_PHASE_TO_NODE,
}

# phase_router dispatches straight into the current phase's node.
_ROUTER_DESTINATIONS: dict[Hashable, str] = {
    node_name: node_name for node_name in _PHASE_TO_NODE.values()
}

# Approval gate outcomes.
_APPROVAL_DESTINATIONS: dict[Hashable, str] = {
    "constitution": "constitution_node",
    "development": "development_node",
    "script": "script_node",
    "visual_dev": "visual_dev_node",
    "shot_bible": "shot_bible_node",
    "gen_planning": "gen_planning_node",
    "generation": "generation_node",
    "qc": "qc_node",
    "post": "post_node",
    "delivery": "delivery_node",
    "end": "end",
    "repair": "repair",
    "await_approval": "await_approval",
}


def _register_nodes(builder: StateGraph) -> None:
    """Register the router passthrough, all phase nodes, and gate nodes."""
    builder.add_node("phase_router", _passthrough)

    # Phase nodes
    builder.add_node("intake_node", intake_node)
    builder.add_node("constitution_node", constitution_node)
    builder.add_node("development_node", development_node)
    builder.add_node("script_node", script_node)
    builder.add_node("visual_dev_node", visual_dev_node)
    builder.add_node("shot_bible_node", shot_bible_node)
    builder.add_node("gen_planning_node", gen_planning_node)
    builder.add_node("generation_node", generation_node)
    builder.add_node("qc_node", build_qc_subgraph())  # Phase 7: parallel subgraph
    builder.add_node("post_node", post_node)
    builder.add_node("delivery_node", delivery_node)

    # Human gate nodes
    builder.add_node("consistency_check", consistency_check_node)
    builder.add_node("await_approval", await_approval_node)
    builder.add_node("approve_phase", approve_phase_node)
    builder.add_node("request_revision", request_revision_node)
    builder.add_node("repair", repair_phase_node)
    builder.add_node("end", _passthrough)


def _wire_entry_router(builder: StateGraph) -> None:
    """Set the entry point and its per-phase conditional dispatch."""
    builder.set_entry_point("phase_router")
    builder.add_conditional_edges(
        "phase_router",
        _route_current_phase,
        _ROUTER_DESTINATIONS,
    )


def _wire_phase_transitions(builder: StateGraph) -> None:
    """Route every phase node through after_phase() for dynamic next-step routing."""
    after_phase_destinations = cast(dict[Hashable, str], _AFTER_PHASE_DESTINATIONS)
    for phase_node in _PHASE_TO_NODE.values():
        builder.add_conditional_edges(
            phase_node,
            after_phase,
            after_phase_destinations,
        )


def _wire_gate_edges(builder: StateGraph) -> None:
    """Wire the human-gate cycle: consistency → approval → next/repair."""
    # Consistency → await_approval (always passes through)
    builder.add_edge("consistency_check", "await_approval")

    # Approval gate → next phase or repair
    builder.add_conditional_edges("await_approval", after_approval, _APPROVAL_DESTINATIONS)

    # Approve/revision → await_approval
    builder.add_edge("approve_phase", "await_approval")
    builder.add_edge("request_revision", "await_approval")
    builder.add_edge("repair", "await_approval")
    builder.add_edge("end", END)


def build_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    *,
    runtime_root: Path | None = None,
) -> CompiledStateGraph:
    """Construct the supervisor graph with all phases and approval gates."""
    builder = StateGraph(StudioGraphState)

    _register_nodes(builder)

    _wire_entry_router(builder)

    _wire_phase_transitions(builder)

    _wire_gate_edges(builder)

    return builder.compile(
        checkpointer=checkpointer or _default_checkpointer(runtime_root=runtime_root)
    )


def _passthrough(state: dict[str, Any]) -> dict[str, Any]:
    # Routing-only node: returning the full state would re-append every
    # reducer-channel entry, so return an empty update.
    _ = state
    return {}


def _route_current_phase(state: dict[str, Any]) -> str:
    phase = str(state.get("current_phase", ""))
    if phase in PHASE_ORDER:
        return f"{phase}_node"
    return "intake_node"


graph: CompiledStateGraph = build_graph()
