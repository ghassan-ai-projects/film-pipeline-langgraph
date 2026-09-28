"""Checkpoint / version / rollback tools."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.checkpoints.invalidation import InvalidationEngine
from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec
from film_pipeline.operations import (
    get_checkpoint as get_checkpoint_use_case,
)
from film_pipeline.operations import (
    rollback_artifact as rollback_artifact_use_case,
)
from film_pipeline.operations import (
    rollback_to_checkpoint as rollback_to_checkpoint_use_case,
)
from film_pipeline.schemas.checkpoint import CheckpointMetadata

from .helpers import (
    _error,
    _ok,
)

_RECENT_CHECKPOINT_LIMIT = 20


def _recent_checkpoints(cps: list[CheckpointMetadata]) -> list[CheckpointMetadata]:
    """Return only the most recent checkpoints for version listing."""
    return cps[-_RECENT_CHECKPOINT_LIMIT:]


def _checkpoint_summary(cp: CheckpointMetadata) -> dict[str, object]:
    """Serialize one checkpoint into the summary shape exposed by the tools."""
    return {
        "checkpoint_id": cp.checkpoint_id,
        "project_id": cp.project_id,
        "phase": cp.phase.value,
        "created_at": cp.created_at.isoformat(),
        "reason": cp.reason,
    }


async def list_checkpoints(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    rt = ctx.runtime
    # An explicit `project_id` wins; otherwise the context's resolved project is
    # the active-project fallback that used to be re-derived here.
    project_id = str(args.get("project_id", "") or "") or (ctx.project_id or "")
    cps = rt.list_checkpoints(project_id if project_id else None)
    return _ok(checkpoints=[_checkpoint_summary(c) for c in cps])


async def create_checkpoint(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    rt = ctx.runtime
    active = ctx.project_state()
    reason = str(args.get("reason", "manual checkpoint"))
    try:
        cp = rt.create_checkpoint(
            project_id=active["project_id"],
            phase=active.get("current_phase", "intake"),
            reason=reason,
        )
        return _ok(
            checkpoint_id=cp.checkpoint_id,
            project_id=cp.project_id,
            phase=cp.phase.value,
        )
    except ValueError as e:
        return _error(str(e))


async def get_checkpoint(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    rt = ctx.runtime
    checkpoint_id = str(args.get("checkpoint_id", ""))
    cp = rt.get_checkpoint(checkpoint_id)
    if cp is None:
        return _error(f"Checkpoint not found: {checkpoint_id}")
    return _ok(**_checkpoint_summary(cp))


async def compare_versions(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    rt = ctx.runtime
    cp_a = rt.get_checkpoint(str(args.get("checkpoint_id_a", "")))
    cp_b = rt.get_checkpoint(str(args.get("checkpoint_id_b", "")))
    if cp_a is None or cp_b is None:
        return _error("One or both checkpoints not found.")
    return _ok(
        older_phase=cp_a.phase.value,
        newer_phase=cp_b.phase.value,
        older_reason=cp_a.reason,
        newer_reason=cp_b.reason,
    )


async def list_artifact_versions(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    rt = ctx.runtime
    cps = rt.list_checkpoints()
    versions: list[dict[str, str]] = []
    for c in _recent_checkpoints(cps):
        for art_type, ver in c.artifact_versions.items():
            versions.append(
                {"checkpoint_id": c.checkpoint_id, "artifact_type": art_type, "version": ver}
            )
    return _ok(versions=versions)


def _unconfirmed_preview(
    checkpoint: CheckpointMetadata | None,
    checkpoint_id: str,
    artifact_id: str,
) -> dict[str, object]:
    """Describe the rollback an unconfirmed call would have performed."""
    artifact_types = [artifact_id]
    if checkpoint is not None:
        artifact_types = list(checkpoint.artifact_versions.keys()) or artifact_types
    return {
        "rollback_target": checkpoint_id or f"latest:{artifact_id}",
        "artifact_types": artifact_types,
    }


async def rollback_artifact(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    rt = ctx.runtime
    artifact_id = str(args.get("artifact_id", ""))
    if not artifact_id:
        return _error("artifact_id is required.")
    checkpoint_id = str(args.get("checkpoint_id", ""))
    confirmed = bool(args.get("confirmed"))
    active = ctx.project_state()
    project_id = str(active["project_id"])
    checkpoint = (
        get_checkpoint_use_case(rt, checkpoint_id) if checkpoint_id and not confirmed else None
    )

    if not confirmed:
        return _error(
            "Rollback requires confirmation. Set confirmed=True to proceed.",
            invalidation_preview=_unconfirmed_preview(checkpoint, checkpoint_id, artifact_id),
        )
    try:
        result = rollback_artifact_use_case(
            rt,
            project_id=project_id,
            artifact_id=artifact_id,
            checkpoint_id=checkpoint_id,
        )
    except Exception as e:
        return _error(str(e))
    return _ok(
        artifact_id=result.artifact_id,
        restored_from=result.restored_from,
        git_commit=result.git_commit,
        invalidation_report_ref=result.invalidation_report_ref,
        rollback_record_ref=result.rollback_record_ref,
    )


async def rollback_to_checkpoint(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    rt = ctx.runtime
    checkpoint_id = str(args.get("checkpoint_id", ""))
    cp = get_checkpoint_use_case(rt, checkpoint_id)
    if cp is None:
        return _error(f"Checkpoint not found: {checkpoint_id}")

    confirmed = bool(args.get("confirmed"))
    if not confirmed:
        return _error(
            "Rollback requires confirmation. Set confirmed=True to proceed.",
            rollback_target=checkpoint_id,
            phase=cp.phase.value,
            reason=cp.reason,
        )

    try:
        active = rt.get_active()
        project_id = str(active["project_id"]) if active is not None else cp.project_id
        result = rollback_to_checkpoint_use_case(rt, cp, project_id)
    except Exception as e:
        return _error(str(e))
    return _ok(
        rollback_target=result.rollback_target,
        phase=result.phase,
        reason=result.reason,
        invalidation_report_ref=result.invalidation_report_ref,
        rollback_record_ref=result.rollback_record_ref,
        message="Rollback completed. Invalidation report and rollback record saved.",
    )


async def get_invalidation_report(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    rt = ctx.runtime
    checkpoint_id = str(args.get("checkpoint_id", ""))
    cp = rt.get_checkpoint(checkpoint_id)
    if cp is None:
        return _error(f"Checkpoint not found: {checkpoint_id}")
    engine = InvalidationEngine()
    report = engine.report(
        rollback_target=checkpoint_id,
        artifact_types=list(cp.artifact_versions.keys()),
    )
    return _ok(
        rollback_target=report.rollback_target,
        will_revert=report.will_revert,
        will_invalidate=report.will_invalidate,
        requires_regeneration=report.requires_regeneration,
    )


# ── Tool declarations ────────────────────────────────────────────────────────
# Declared next to the handlers they describe (doc 04 slice 1).


class ListCheckpointsArgs(ToolArgs):
    """Arguments for `list_checkpoints`."""

    project_id: str = Field(
        default="", description="Project to list; empty uses the active project."
    )


class CreateCheckpointArgs(ToolArgs):
    """Arguments for `create_checkpoint`."""

    reason: str = Field(default="manual checkpoint", description="Why the checkpoint was taken.")


class GetCheckpointArgs(ToolArgs):
    """Arguments for `get_checkpoint`."""

    checkpoint_id: str = Field(description="Checkpoint to fetch.")


class CompareVersionsArgs(ToolArgs):
    """Arguments for `compare_versions`."""

    checkpoint_id_a: str = Field(description="Left-hand checkpoint.")
    checkpoint_id_b: str = Field(description="Right-hand checkpoint.")


class ListArtifactVersionsArgs(ToolArgs):
    """Arguments for `list_artifact_versions` (none)."""


class RollbackArtifactArgs(ToolArgs):
    """Arguments for `rollback_artifact`."""

    artifact_id: str = Field(description="Artifact to restore.")
    checkpoint_id: str = Field(
        default="", description="Checkpoint to restore from; empty uses the latest."
    )
    confirmed: bool | None = Field(
        default=None, description="Must be true to perform the rollback."
    )


class RollbackToCheckpointArgs(ToolArgs):
    """Arguments for `rollback_to_checkpoint`."""

    checkpoint_id: str = Field(description="Checkpoint to roll the project back to.")
    confirmed: bool | None = Field(
        default=None, description="Must be true to perform the rollback."
    )


class GetInvalidationReportArgs(ToolArgs):
    """Arguments for `get_invalidation_report`."""

    checkpoint_id: str = Field(description="Checkpoint whose invalidation report to read.")


CHECKPOINT_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="list_checkpoints",
        group=ToolGroup.CHECKPOINT,
        description="List recent checkpoints for a project.",
        args=ListCheckpointsArgs,
        handler=list_checkpoints,
    ),
    ToolSpec(
        name="create_checkpoint",
        group=ToolGroup.CHECKPOINT,
        description="Take a checkpoint of the active project so it can be rolled back to.",
        args=CreateCheckpointArgs,
        handler=create_checkpoint,
        mutates=True,
        active_project=True,
    ),
    ToolSpec(
        name="get_checkpoint",
        group=ToolGroup.CHECKPOINT,
        description="Fetch one checkpoint's metadata by id.",
        args=GetCheckpointArgs,
        handler=get_checkpoint,
    ),
    ToolSpec(
        name="compare_versions",
        group=ToolGroup.CHECKPOINT,
        description="Compare two checkpoints and report what changed between them.",
        args=CompareVersionsArgs,
        handler=compare_versions,
    ),
    ToolSpec(
        name="list_artifact_versions",
        group=ToolGroup.CHECKPOINT,
        description="List the recorded versions of every artifact across checkpoints.",
        args=ListArtifactVersionsArgs,
        handler=list_artifact_versions,
    ),
    ToolSpec(
        name="rollback_artifact",
        group=ToolGroup.CHECKPOINT,
        description=(
            "Roll one artifact back to an earlier checkpoint's version, reporting invalidations."
        ),
        args=RollbackArtifactArgs,
        handler=rollback_artifact,
        mutates=True,
        confirm=True,
        active_project=True,
    ),
    ToolSpec(
        name="rollback_to_checkpoint",
        group=ToolGroup.CHECKPOINT,
        description=(
            "Roll the whole project back to a checkpoint, invalidating downstream artifacts."
        ),
        args=RollbackToCheckpointArgs,
        handler=rollback_to_checkpoint,
        mutates=True,
        confirm=True,
    ),
    ToolSpec(
        name="get_invalidation_report",
        group=ToolGroup.CHECKPOINT,
        description="Read the invalidation report produced by a checkpoint's rollback.",
        args=GetInvalidationReportArgs,
        handler=get_invalidation_report,
    ),
)
