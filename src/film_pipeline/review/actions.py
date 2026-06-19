"""Available actions calculator for review packages.

Computes which actions are available and which are blocked at each
approval gate, based on state, issues, and checkpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AvailableActions:
    """Available and blocked actions for a review package."""

    available: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    blocked_reasons: dict[str, str] = field(default_factory=dict)

    def has_action(self, action: str) -> bool:
        return action in self.available

    def is_blocked(self, action: str) -> bool:
        return action in self.blocked

    def block_reason(self, action: str) -> str:
        return self.blocked_reasons.get(action, "Unknown reason.")


def compute_available_actions(
    has_blocking_issues: bool = False,
    has_previous_version: bool = False,
    has_checkpoint: bool = False,
) -> AvailableActions:
    """Compute available actions for a review gate.

    Rules:
    - `approve_phase` — available only when no blocking issues exist
    - `request_revision` — always available
    - `compare_versions` — available when a previous version exists
    - `rollback_to_checkpoint` — available when a checkpoint exists
    """
    result = AvailableActions()

    # request_revision is always available
    result.available.append("request_revision")

    # approve_phase only if no blocking issues
    if has_blocking_issues:
        result.blocked.append("approve_phase")
        result.blocked_reasons["approve_phase"] = (
            "Blocking issues must be resolved before approval."
        )
    else:
        result.available.append("approve_phase")

    # compare_versions only if a previous version exists
    if has_previous_version:
        result.available.append("compare_versions")
    else:
        result.blocked.append("compare_versions")
        result.blocked_reasons["compare_versions"] = (
            "No previous approved version to compare against."
        )

    # rollback only if a checkpoint exists
    if has_checkpoint:
        result.available.append("rollback_to_checkpoint")
    else:
        result.blocked.append("rollback_to_checkpoint")
        result.blocked_reasons["rollback_to_checkpoint"] = "No checkpoint exists for rollback."

    return result
