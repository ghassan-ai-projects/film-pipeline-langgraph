"""Assembly agent — orders clips per manifest, produces review cut plan."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

# Placeholder duration assigned to every clip until real media probing exists.
_SECONDS_PER_CLIP = 5.0


def _match_clip(shot_id: str, clip_paths: list[str]) -> str | None:
    """Return the first clip whose path contains the shot id, if any."""
    return next((c for c in clip_paths if shot_id in c), None)


def _consecutive_cuts(clips: list[str]) -> list[dict[str, str]]:
    """Build a hard-cut transition between each pair of consecutive clips."""
    return [{"from": clips[i], "to": clips[i + 1], "type": "cut"} for i in range(len(clips) - 1)]


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
    produces an AssemblyPlan. Persists the plan as an artifact.
    """

    def build_plan(
        self,
        project_id: str,
        shot_ids: list[str],
        clip_paths: list[str],
        scene_order: list[str] | None = None,
    ) -> AssemblyPlan:
        """Build an assembly plan from available clips and scene order."""
        plan = AssemblyPlan(
            plan_id=f"assembly-plan:{project_id}:{uuid4().hex[:8]}",
            project_id=project_id,
        )

        if scene_order is None:
            scene_order = sorted(shot_ids)

        seen: set[str] = set()
        for shot_id in scene_order:
            if shot_id in seen:
                plan.notes.append(f"Duplicate shot {shot_id} skipped.")
                continue
            seen.add(shot_id)

            clip = _match_clip(shot_id, clip_paths)
            if clip:
                plan.clips.append(clip)
                plan.clip_count += 1
                plan.total_duration_seconds += _SECONDS_PER_CLIP
            else:
                plan.missing_assets.append(shot_id)

        plan.transition_points = _consecutive_cuts(plan.clips)

        if plan.missing_assets:
            plan.notes.append(
                f"Missing {len(plan.missing_assets)} assets: {', '.join(plan.missing_assets)}"
            )

        return plan

    def persist(
        self,
        plan: AssemblyPlan,
        artifact_store: Any,
    ) -> str:
        """Persist the assembly plan as a versioned artifact.

        Returns the artifact reference string.
        """
        from datetime import UTC, datetime

        from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef
        from film_pipeline.schemas.assembly import AssemblyPlanArtifact
        from film_pipeline.schemas.base import ArtifactStatus, ArtifactType, FilmPhase

        artifact_id = "assembly_manifest"
        model = AssemblyPlanArtifact(
            plan_id=plan.plan_id,
            project_id=plan.project_id,
            clip_order=[
                {
                    "shot_id": path.split("/")[-1].rsplit(".", 1)[0],
                    "source_asset_ref": path,
                    "in_seconds": i * _SECONDS_PER_CLIP,
                    "out_seconds": (i + 1) * _SECONDS_PER_CLIP,
                }
                for i, path in enumerate(plan.clips)
            ],
            clips=plan.clips,
            total_duration_seconds=plan.total_duration_seconds,
            clip_count=plan.clip_count,
            missing_assets=plan.missing_assets,
            transitions=[
                {"from_shot_id": t["from"], "to_shot_id": t["to"], "transition_type": t["type"]}
                for t in plan.transition_points
            ],
            notes=plan.notes,
        )
        meta = ArtifactMetadata(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.ASSEMBLY_MANIFEST,
            project_id=plan.project_id,
            phase=FilmPhase("post"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="assembly-agent",
            created_at=datetime.now(UTC),
        )
        ref: ArtifactRef = artifact_store.save(model, meta)
        return ref.to_string()

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
