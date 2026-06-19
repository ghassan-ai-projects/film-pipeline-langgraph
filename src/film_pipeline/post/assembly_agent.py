"""Assembly agent — orders clips per manifest, produces review cut plan."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class AssemblyPlan:
    """A structured plan for assembling clips into a review cut."""

    plan_id: str
    project_id: str
    clips: list[str] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    clip_count: int = 0
    missing_assets: list[str] = field(default_factory=list)
    transition_points: list[dict[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class AssemblyAgent:
    """Reads the master film matrix and assembly manifest, orders clips,
    produces an AssemblyPlan. Does not execute ffmpeg — that's for the
    real production pipeline.
    """

    def build_plan(
        self,
        project_id: str,
        shot_ids: list[str],
        clip_paths: list[str],
        scene_order: list[str] | None = None,
    ) -> AssemblyPlan:
        """Build an assembly plan from available clips and scene order.

        Args:
            project_id: The film project identifier.
            shot_ids: Shot identifiers in scene order (e.g. S001-01, S001-02).
            clip_paths: Paths to generated clip files.
            scene_order: Optional scene ordering override.
        """
        plan = AssemblyPlan(
            plan_id=f"assembly-plan:{project_id}:{uuid4().hex[:8]}",
            project_id=project_id,
        )

        if scene_order is None:
            # Default: alphabetical shot order
            scene_order = sorted(shot_ids)

        seen: set[str] = set()
        for shot_id in scene_order:
            if shot_id in seen:
                plan.notes.append(f"Duplicate shot {shot_id} skipped.")
                continue
            seen.add(shot_id)

            clip = next(
                (c for c in clip_paths if shot_id in c),
                None,
            )
            if clip:
                plan.clips.append(clip)
                plan.clip_count += 1
                plan.total_duration_seconds += 5.0  # Default clip duration
            else:
                plan.missing_assets.append(shot_id)

        # Plan transition points between consecutive clips
        for i in range(len(plan.clips) - 1):
            plan.transition_points.append(
                {
                    "from": plan.clips[i],
                    "to": plan.clips[i + 1],
                    "type": "cut",
                }
            )

        if plan.missing_assets:
            plan.notes.append(
                f"Missing {len(plan.missing_assets)} assets: {', '.join(plan.missing_assets)}"
            )

        return plan

    def validate_plan(self, plan: AssemblyPlan) -> list[str]:
        """Validate an assembly plan. Returns list of issues (empty = valid)."""
        issues: list[str] = []
        if not plan.clips:
            issues.append("No clips in assembly plan.")
        if plan.missing_assets:
            issues.append(f"Missing assets: {', '.join(plan.missing_assets)}")
        if plan.clip_count != len(plan.clips):
            issues.append("Clip count mismatch.")
        return issues
