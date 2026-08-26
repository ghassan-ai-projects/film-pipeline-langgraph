"""Post-production validators — assembly, transitions, audio, delivery."""

from __future__ import annotations

from dataclasses import dataclass

from film_pipeline.post.assembly_agent import AssemblyPlan
from film_pipeline.post.delivery_packaging_agent import DeliveryPackage
from film_pipeline.post.transition_agent import TRANSITION_TYPES, TransitionPlan


@dataclass
class PostValidator:
    """Base validator for post-production artifacts."""

    def validate_assembly(self, plan: AssemblyPlan) -> list[str]:
        """Validate an assembly plan."""
        issues: list[str] = []
        if not plan.clips:
            issues.append("No clips in assembly plan.")
        if plan.missing_assets:
            issues.append(f"Missing assets: {', '.join(plan.missing_assets)}")
        if plan.clip_count == 0:
            issues.append("Clip count is zero.")
        return issues

    def validate_transitions(self, plan: TransitionPlan, clip_count: int) -> list[str]:
        """Validate a transition plan."""
        issues: list[str] = []
        expected = max(0, clip_count - 1)
        if plan.total_count != expected:
            issues.append(f"Expected {expected} transitions, got {plan.total_count}.")
        for t in plan.transitions:
            if t["type"] not in TRANSITION_TYPES:
                issues.append(f"Unknown transition type: {t['type']}")
        return issues

    def validate_delivery(self, package: DeliveryPackage) -> list[str]:
        """Validate a delivery package."""
        issues: list[str] = []
        if not package.is_complete:
            missing = package.missing_items
            issues.append(f"Delivery incomplete. Missing: {', '.join(missing)}")
        if not package.files:
            issues.append("No files in delivery package.")
        return issues

    def validate_subtitles(self, cue_count: int, dialogue_count: int) -> list[str]:
        """Validate subtitle cue count matches dialogue."""
        issues: list[str] = []
        if cue_count == 0:
            issues.append("No subtitle cues generated.")
        if cue_count != dialogue_count and dialogue_count > 0:
            issues.append(f"Subtitle cue count ({cue_count}) != dialogue count ({dialogue_count}).")
        return issues
