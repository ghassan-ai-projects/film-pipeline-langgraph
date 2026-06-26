"""Build the complete LangGraph supervisor graph."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from film_pipeline.graph.edges import after_approval
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


def build_graph() -> CompiledStateGraph:
    """Construct the supervisor graph with all phases and approval gates."""
    builder = StateGraph(StudioGraphState)

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

    # Entry
    builder.set_entry_point("phase_router")
    builder.add_conditional_edges(
        "phase_router",
        _route_current_phase,
        {
            "intake_node": "intake_node",
            "constitution_node": "constitution_node",
            "development_node": "development_node",
            "script_node": "script_node",
            "visual_dev_node": "visual_dev_node",
            "shot_bible_node": "shot_bible_node",
            "gen_planning_node": "gen_planning_node",
            "generation_node": "generation_node",
            "qc_node": "qc_node",
            "post_node": "post_node",
            "delivery_node": "delivery_node",
        },
    )

    # Phase → consistency_check (non-blocking staleness detection)
    for phase_node in [
        "intake_node",
        "constitution_node",
        "development_node",
        "script_node",
        "visual_dev_node",
        "shot_bible_node",
        "gen_planning_node",
        "generation_node",
        "qc_node",
        "post_node",
        "delivery_node",
    ]:
        builder.add_edge(phase_node, "consistency_check")

    # Consistency → await_approval (always passes through)
    builder.add_edge("consistency_check", "await_approval")

    # Approval gate → next phase or repair
    builder.add_conditional_edges(
        "await_approval",
        after_approval,
        {
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
        },
    )

    # Approve/revision → await_approval
    builder.add_edge("approve_phase", "await_approval")
    builder.add_edge("request_revision", "await_approval")
    builder.add_edge("repair", "await_approval")
    builder.add_edge("end", END)

    return builder.compile(checkpointer=MemorySaver())


def _passthrough(state: dict[str, Any]) -> dict[str, Any]:
    return state


def _route_current_phase(state: dict[str, Any]) -> str:
    phase = str(state.get("current_phase", ""))
    if phase in PHASE_ORDER:
        return f"{phase}_node"
    return "intake_node"


graph: CompiledStateGraph = build_graph()
