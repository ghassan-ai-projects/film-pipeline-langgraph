"""Checkpoint / version / rollback tools."""

from __future__ import annotations

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.checkpoints.invalidation import InvalidationEngine
from film_pipeline.schemas.checkpoint import CheckpointMetadata

from .helpers import (
    _active_project_id,
    _error,
    _ok,
    operator_service,
    require_project_state,
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


async def list_checkpoints(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    project_id = str(args.get("project_id", "") or "")
    if not project_id and args.get("project_ref"):
        project_id = _active_project_id(args, rt) or ""
    cps = rt.list_checkpoints(project_id if project_id else None)
    return _ok(checkpoints=[_checkpoint_summary(c) for c in cps])


async def create_checkpoint(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    active = require_project_state(args)
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


async def get_checkpoint(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    checkpoint_id = str(args.get("checkpoint_id", ""))
    cp = rt.get_checkpoint(checkpoint_id)
    if cp is None:
        return _error(f"Checkpoint not found: {checkpoint_id}")
    return _ok(**_checkpoint_summary(cp))


async def compare_versions(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
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


async def list_artifact_versions(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
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


async def rollback_artifact(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    artifact_id = str(args.get("artifact_id", ""))
    if not artifact_id:
        return _error("artifact_id is required.")
    checkpoint_id = str(args.get("checkpoint_id", ""))
    confirmed = bool(args.get("confirmed"))
    active = require_project_state(args)
    project_id = str(active["project_id"])
    service = operator_service(rt)
    checkpoint = service.get_checkpoint(checkpoint_id) if checkpoint_id and not confirmed else None

    if not confirmed:
        return _error(
            "Rollback requires confirmation. Set confirmed=True to proceed.",
            invalidation_preview=_unconfirmed_preview(checkpoint, checkpoint_id, artifact_id),
        )
    try:
        result = service.rollback_artifact(
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


async def rollback_to_checkpoint(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    checkpoint_id = str(args.get("checkpoint_id", ""))
    service = operator_service(rt)
    cp = service.get_checkpoint(checkpoint_id)
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
        result = service.rollback_to_checkpoint(cp, project_id)
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


async def get_invalidation_report(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
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
