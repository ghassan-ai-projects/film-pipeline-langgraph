"""Build the complete LangGraph supervisor graph."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from film_pipeline.graph.edges import after_approval, after_phase
from film_pipeline.graph.nodes import (
    approve_phase_node,
    constitution_node,
    delivery_node,
    development_node,
    gen_planning_node,
    generation_node,
    intake_node,
    post_node,
    qc_node,
    request_revision_node,
    script_node,
    shot_bible_node,
    visual_dev_node,
)


def build_graph() -> CompiledStateGraph:
    """Construct the supervisor graph with all phases and approval gates."""
    builder = StateGraph(dict)

    # Phase nodes
    builder.add_node("intake_node", intake_node)
    builder.add_node("constitution_node", constitution_node)
    builder.add_node("development_node", development_node)
    builder.add_node("script_node", script_node)
    builder.add_node("visual_dev_node", visual_dev_node)
    builder.add_node("shot_bible_node", shot_bible_node)
    builder.add_node("gen_planning_node", gen_planning_node)
    builder.add_node("generation_node", generation_node)
    builder.add_node("qc_node", qc_node)
    builder.add_node("post_node", post_node)
    builder.add_node("delivery_node", delivery_node)

    # Human gate nodes
    builder.add_node("await_approval", _passthrough)
    builder.add_node("approve_phase", approve_phase_node)
    builder.add_node("request_revision", request_revision_node)
    builder.add_node("repair", _passthrough)
    builder.add_node("end", _passthrough)

    # Entry
    builder.set_entry_point("intake_node")

    # Phase → await_approval or next phase
    builder.add_conditional_edges("intake_node", after_phase, {"await_approval": "await_approval"})
    builder.add_conditional_edges(
        "constitution_node", after_phase, {"await_approval": "await_approval"}
    )
    builder.add_conditional_edges(
        "development_node", after_phase, {"await_approval": "await_approval"}
    )
    builder.add_conditional_edges("script_node", after_phase, {"await_approval": "await_approval"})
    builder.add_conditional_edges(
        "visual_dev_node", after_phase, {"await_approval": "await_approval"}
    )
    builder.add_conditional_edges(
        "shot_bible_node", after_phase, {"await_approval": "await_approval"}
    )
    builder.add_conditional_edges(
        "gen_planning_node", after_phase, {"await_approval": "await_approval"}
    )
    builder.add_conditional_edges(
        "generation_node", after_phase, {"await_approval": "await_approval"}
    )
    builder.add_conditional_edges("qc_node", after_phase, {"await_approval": "await_approval"})
    builder.add_conditional_edges("post_node", after_phase, {"await_approval": "await_approval"})
    builder.add_conditional_edges(
        "delivery_node", after_phase, {"await_approval": "await_approval"}
    )

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

    return builder.compile()


def _passthrough(state: dict[str, Any]) -> dict[str, Any]:
    return state
