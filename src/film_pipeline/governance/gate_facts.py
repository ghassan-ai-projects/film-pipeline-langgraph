"""The orchestrator reads the human-gate law depends on.

The gate law (`governance.actions`) decides which actions are eligible for a
phase. That decision legitimately depends on orchestrator facts — whether a
blocking failure exists, which providers are blocked, whether a revision is
pending, whether the budget threshold tripped.

Those facts live in orchestrator state, which is `orchestration` (L9), while
`governance` sits below it (L8) and must not import it. This module declares the
reads structurally, so the law can consume them and `orchestration` can supply
them, with no upward edge in either direction.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GateFacts(Protocol):
    """The orchestrator facts a gate decision reads.

    Every member is a pure read over already-computed state. A gate must never
    mutate here: the law decides, the orchestrator acts.
    """

    def ensure_state(self, state: dict[str, Any]) -> None:
        """Populate any missing orchestrator state domains."""
        ...

    def has_blocking_failure(self, state: dict[str, Any]) -> bool:
        """Return whether an unresolved blocking failure decision exists."""
        ...

    def latest_failure_decision(self, state: dict[str, Any]) -> dict[str, Any] | None:
        """Return the most recent unresolved failure decision."""
        ...

    def blocked_providers(self, state: dict[str, Any]) -> list[str]:
        """Return the ids of providers currently blocked."""
        ...

    def is_budget_blocked(self, state: dict[str, Any]) -> bool:
        """Return whether the budget threshold has been exceeded."""
        ...

    def has_pending_revision(self, state: dict[str, Any]) -> bool:
        """Return whether an unresolved revision request exists."""
        ...

    def approved_refs(self, state: dict[str, Any]) -> dict[str, str]:
        """Return the approved artifact ref for each artifact id."""
        ...
