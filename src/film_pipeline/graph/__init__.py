"""Compatibility shims for the orchestration layer.

The graph package became `orchestration` once the gate law, validators, scope
contracts, and consistency checks moved to `governance`. This package keeps the
historical `film_pipeline.graph.*` import paths resolving while consumers
migrate; every module here re-exports its orchestration owner.
"""

from __future__ import annotations

import importlib
from typing import Any

#: Orchestration submodules that had a `graph` counterpart.
_SHIMS = (
    "_agent_routing",
    "_gate_facts",
    "context_packets",
    "edges",
    "orchestrator_state",
    "phase_sequence",
    "router",
    "services",
    "state_schema",
)


def __getattr__(name: str) -> Any:
    """Resolve a legacy submodule name against its orchestration owner."""
    if name in _SHIMS:
        return importlib.import_module(f"film_pipeline.orchestration.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_SHIMS))


__all__ = list(_SHIMS)
