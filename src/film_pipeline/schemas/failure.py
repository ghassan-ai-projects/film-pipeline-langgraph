"""Failure decisions from the failure-handling agent.

Produced by ``failure-handling-agent`` to classify errors and recommend
graph routing decisions. Persisted as durable state so the orchestrator
can route without re-running the agent on every action.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from film_pipeline.schemas.base import FailureClass, MutableSchemaBase, SchemaBase


class FailureDecision(SchemaBase):
    """A structured failure decision produced by the failure-handling agent.

    Mirrors the architecture blueprint's FailureDecision shape and is used
    by the orchestrator to route the graph after provider, runtime, budget,
    or continuity errors.
    """

    decision_id: str
    project_id: str
    phase: str
    error_class: FailureClass
    severity: str = Field(
        default="blocking",
        description="'blocking' | 'non_blocking'. Blocking errors pause the affected chain.",
    )
    safe_to_retry: bool = Field(
        default=False,
        description="Whether the same request can be safely retried without duplication risk.",
    )
    safe_to_continue_other_work: bool = Field(
        default=True,
        description=(
            "Whether unrelated phases (planning, writing, validation) can continue "
            "while this failure is unresolved."
        ),
    )
    next_graph_action: str = Field(
        default="stop_until_resolved",
        description="Recommended next action: 'retry', 're_anchor', 'provider_switch', "
        "'human_escalation', 'stop_until_resolved', 'continue_unaffected'.",
    )
    human_message: str = Field(
        default="",
        description="Human-readable explanation of the failure and recommended next step.",
    )
    affected_generation_ids: list[str] = Field(default_factory=list)
    recommended_provider_switch: str | None = Field(
        default=None,
        description="Alternative provider ID if a provider switch is recommended.",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now().replace(microsecond=0))


class FailureRecoveryRecord(MutableSchemaBase):
    """Tracks recovery actions taken after a failure decision.

    Updated as recovery progresses (retry attempt, provider switch, re-anchor).
    """

    recovery_id: str
    failure_decision_id: str
    project_id: str
    phase: str
    attempt_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    last_action: str = ""
    last_action_at: datetime | None = None
    resolved: bool = False
    resolution_note: str = ""
