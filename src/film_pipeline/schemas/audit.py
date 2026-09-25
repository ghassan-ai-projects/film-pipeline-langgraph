"""Audit log entry — every explainable action in the studio."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from film_pipeline.schemas.base import SchemaBase


class AuditLogEntry(SchemaBase):
    """One auditable action."""

    entry_id: str
    project_id: str
    timestamp: datetime
    actor_type: str = Field(
        description="'orchestrator' | 'agent' | 'human' | 'mock_human' | 'system'."
    )
    actor_id: str
    action: str = Field(description="Stable action code, e.g. 'phase_approved'.")
    graph_node: str = ""
    routing_decision_ref: str = ""
    kb_context_ref: str = ""
    input_artifact_refs: list[str] = Field(default_factory=list)
    output_artifact_refs: list[str] = Field(default_factory=list)
    validation_refs: list[str] = Field(default_factory=list)
    provider_job_id: str | None = None
    cost_estimate_usd: float | None = None
    approval_ref: str | None = None
    checkpoint_ref: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
