"""Structured audit trail — records every action with full context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class AuditEventType(StrEnum):
    MCP_REQUEST = "mcp_request"
    GRAPH_NODE = "graph_node"
    AGENT_CALL = "agent_call"
    MODEL_CALL = "model_call"
    KB_CONTEXT = "kb_context"
    PROVIDER_ACTION = "provider_action"
    VALIDATION = "validation"
    APPROVAL = "approval"
    ROUTING = "routing_decision"
    CHECKPOINT = "checkpoint"
    ROLLBACK = "rollback"
    ERROR = "error"


@dataclass
class AuditEvent:
    """A single auditable event with full context."""

    event_id: str
    event_type: AuditEventType
    project_id: str
    timestamp: datetime
    actor: str  # agent_id, validator_id, provider_id, or "system"
    action: str
    details: dict[str, str] = field(default_factory=dict)
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    success: bool = True
    error_message: str = ""


@dataclass
class AuditTrail:
    """In-memory audit trail aggregator.

    In production, this would write to a database or structured log.
    """

    events: list[AuditEvent] = field(default_factory=list)

    def record(
        self,
        event_type: AuditEventType,
        project_id: str,
        actor: str,
        action: str,
        details: dict[str, str] | None = None,
        cost_usd: float = 0.0,
        duration_ms: float = 0.0,
        success: bool = True,
        error_message: str = "",
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=f"audit:{event_type.value}:{uuid4().hex[:8]}",
            event_type=event_type,
            project_id=project_id,
            timestamp=datetime.now(UTC),
            actor=actor,
            action=action,
            details=details or {},
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
        )
        self.events.append(event)
        return event

    def by_project(self, project_id: str) -> list[AuditEvent]:
        return [e for e in self.events if e.project_id == project_id]

    def by_type(self, event_type: AuditEventType) -> list[AuditEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def failures(self) -> list[AuditEvent]:
        return [e for e in self.events if not e.success]

    def total_cost_usd(self) -> float:
        return sum(e.cost_usd for e in self.events)

    def __len__(self) -> int:
        return len(self.events)
