"""Assembly agent — orders clips per manifest, produces review cut plan."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
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

            clip = next((c for c in clip_paths if shot_id in c), None)
            if clip:
                plan.clips.append(clip)
                plan.clip_count += 1
                plan.total_duration_seconds += 5.0
            else:
                plan.missing_assets.append(shot_id)

        for i in range(len(plan.clips) - 1):
            plan.transition_points.append(
                {"from": plan.clips[i], "to": plan.clips[i + 1], "type": "cut"}
            )

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

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
        from film_pipeline.schemas.artifact import ArtifactMetadata

        artifact_id = "assembly_manifest"
        data = {
            "plan_id": plan.plan_id,
            "project_id": plan.project_id,
            "clip_order": [
                {
                    "shot_id": path.split("/")[-1].rsplit(".", 1)[0],
                    "source_asset_ref": path,
                    "in_seconds": i * 5.0,
                    "out_seconds": (i + 1) * 5.0,
                }
                for i, path in enumerate(plan.clips)
            ],
            "clips": plan.clips,
            "total_duration_seconds": plan.total_duration_seconds,
            "clip_count": plan.clip_count,
            "missing_assets": plan.missing_assets,
            "transitions": [
                {"from_shot_id": t["from"], "to_shot_id": t["to"], "transition_type": t["type"]}
                for t in plan.transition_points
            ],
            "notes": plan.notes,
        }
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
        artifact_store.save_dict(data, meta)
        return f"artifact:{artifact_id}:v1"

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
