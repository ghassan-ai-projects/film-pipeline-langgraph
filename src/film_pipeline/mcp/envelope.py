"""Request envelopes and project resolution for the MCP layer.

Every mutation request must resolve into a :class:`RequestEnvelope` before
the orchestrator changes state. This prevents agents from acting on the
wrong film.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True)
class RequestEnvelope:
    """Structured MCP request envelope.

    ``resolved_project_id`` is set by project resolution middleware before
    the tool handler is invoked.
    """

    request_id: str
    project_ref: str | None = None
    resolved_project_id: str | None = None
    active_phase: str | None = None
    user_intent: str | None = None
    requires_confirmation: bool = False
    actor_id: str | None = None
    actor_type: str = "human"
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def new_envelope(
    project_ref: str | None = None,
    *,
    user_intent: str | None = None,
    actor_id: str | None = None,
    actor_type: str = "human",
) -> RequestEnvelope:
    """Construct a new request envelope with a unique id."""
    return RequestEnvelope(
        request_id=f"req_{uuid4().hex[:12]}",
        project_ref=project_ref,
        user_intent=user_intent,
        actor_id=actor_id,
        actor_type=actor_type,
    )
