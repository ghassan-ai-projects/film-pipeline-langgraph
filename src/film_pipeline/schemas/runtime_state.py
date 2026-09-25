"""Typed runtime-state files (storage upgrade plan P4 / D3).

The runtime persists one typed project record and one machine state
snapshot per project instead of raw dict dumps:

- ``project.json``      — :class:`ProjectRecord`, the human- and MCP-readable
                          project entry point (known fields typed, unknown
                          runtime fields preserved via ``extra="allow"``).
- ``state/graph-state.json`` — :class:`GraphStateSnapshot`, the machine-only
                          LangGraph state snapshot written once per mutating
                          operation (replaces ``project-state.json`` plus
                          ``.graph_state.json``).

Both carry a ``schema_version`` so future changes are detectable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectRecord(BaseModel):
    """Typed project entry point persisted as ``project.json``.

    Frozen: a change produces a new record rather than mutating this one, so a
    caller cannot silently alter persisted state through a shared reference.
    """

    model_config = ConfigDict(extra="allow", frozen=True)

    schema_version: int = 1
    project_id: str = ""
    title: str = ""
    slug: str = ""
    server_mode: str = ""
    current_phase: str = ""
    approved: bool = False
    human_approval_required: bool = False
    human_approval_phase: str = ""
    project_kind: str = ""
    discovered: bool = False


class GraphStateSnapshot(BaseModel):
    """Machine state snapshot persisted as ``state/graph-state.json``."""

    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    saved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    state: dict[str, Any] = Field(default_factory=dict)
