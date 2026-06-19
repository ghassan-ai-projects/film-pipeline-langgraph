"""LangGraph global state model — every state domain as a typed field."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any

from langgraph.graph.message import add_messages


@dataclass
class FilmStudioState:
    """Typed global state for the LangGraph film studio.

    Each domain maps to one canonical artifact set. The orchestrator reads
    and writes these fields; agents produce artifacts that update them.
    """

    project_id: str = ""
    current_phase: str = "intake"
    config: dict[str, Any] = field(default_factory=dict)
    film_constitution: dict[str, Any] = field(default_factory=dict)
    narrative: dict[str, Any] = field(default_factory=dict)
    characters: dict[str, Any] = field(default_factory=dict)
    environments: dict[str, Any] = field(default_factory=dict)
    camera_language: dict[str, Any] = field(default_factory=dict)
    scene_intents: dict[str, Any] = field(default_factory=dict)
    shot_bible: dict[str, Any] = field(default_factory=dict)
    continuity_ledger: dict[str, Any] = field(default_factory=dict)
    reference_strategy: dict[str, Any] = field(default_factory=dict)
    generation_plan: dict[str, Any] = field(default_factory=dict)
    assets: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    approvals: dict[str, Any] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)
    budget: dict[str, Any] = field(default_factory=dict)
    provider_health: dict[str, Any] = field(default_factory=dict)
    runtime_errors: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    delivery: dict[str, Any] = field(default_factory=dict)
    messages: Annotated[list[Any], add_messages] = field(default_factory=list)
    eligible_actions: list[str] = field(default_factory=list)
    blocked_actions: list[dict[str, str]] = field(default_factory=list)
    routing_decision: dict[str, Any] = field(default_factory=dict)
    human_approval_required: bool = False
    human_approval_phase: str = ""
    approved: bool = False
    error: str = ""
