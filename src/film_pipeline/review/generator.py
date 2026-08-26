"""Review package generator — builds structured review packages per phase."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from film_pipeline.review.actions import compute_available_actions
from film_pipeline.review.diff import compute_artifact_diff
from film_pipeline.schemas._base import FilmPhase
from film_pipeline.schemas.approval import ReviewPackage

REVIEW_TYPE_MAP: dict[FilmPhase, str] = {
    FilmPhase.INTAKE: "config_review",
    FilmPhase.CONSTITUTION: "constitution_review",
    FilmPhase.DEVELOPMENT: "treatment_review",
    FilmPhase.SCRIPT: "script_review",
    FilmPhase.VISUAL_DEV: "visual_bible_review",
    FilmPhase.SHOT_BIBLE: "shot_bible_review",
    FilmPhase.GEN_PLANNING: "generation_plan_review",
    FilmPhase.GENERATION: "clip_batch_review",
    FilmPhase.QC: "qc_review",
    FilmPhase.POST: "assembly_review",
    FilmPhase.DELIVERY: "final_cut_review",
}


@dataclass
class ReviewPackageGenerator:
    """Builds a ReviewPackage for a human approval gate.

    Inputs:
    - project_id, phase, current_artifacts, previous_approved_artifacts
    - validation_results, open_issues, risks, cost_impact
    - whether blocking issues exist, whether a checkpoint exists
    """

    def build(
        self,
        *,
        project_id: str,
        phase: FilmPhase,
        summary: str,
        current_artifacts: list[str] | None = None,
        previous_approved_artifacts: list[str] | None = None,
        validation_results: list[str] | None = None,
        open_issues: list[str] | None = None,
        risks: list[str] | None = None,
        cost_impact: dict[str, str] | None = None,
        orchestrator_recommendation: str = "review",
        has_blocking_issues: bool = False,
        has_checkpoint: bool = False,
    ) -> ReviewPackage:
        """Build a complete review package for one phase."""
        current = current_artifacts or []
        previous = previous_approved_artifacts or []

        # Compute available actions
        actions = compute_available_actions(
            has_blocking_issues=has_blocking_issues,
            has_previous_version=bool(previous),
            has_checkpoint=has_checkpoint,
        )

        return ReviewPackage(
            review_package_id=f"review:{phase.value}:{uuid4().hex[:8]}",
            project_id=project_id,
            phase=phase,
            type=REVIEW_TYPE_MAP.get(phase, "generic_review"),
            summary=summary,
            artifacts=current,
            diff_from_approved=_artifact_diff(current, previous),
            validation_results=validation_results or [],
            open_issues=open_issues or [],
            risks=risks or [],
            cost_impact=cost_impact or {},
            orchestrator_recommendation=orchestrator_recommendation,
            available_actions=actions.available,
            blocked_actions=actions.blocked,
        )


def _artifact_diff(
    current_artifacts: list[str], previous_approved_artifacts: list[str]
) -> dict[str, list[str]]:
    """Compute the added/changed/removed diff against the last approved version."""
    diff_result = compute_artifact_diff(current_artifacts, previous_approved_artifacts)
    return {
        "added": diff_result.added,
        "changed": diff_result.changed,
        "removed": diff_result.removed,
    }
