"""Checkpoint / version / rollback tools."""

from __future__ import annotations

from typing import Any

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.checkpoints.rollback import RollbackManager

from .helpers import _active_project_id, _error, _ok, _services


def _save_rollback_artifacts(
    rt: Any,
    project_id: str,
    rollback_target: str,
    artifact_types: list[str],
    performed_by: str,
) -> tuple[str, str]:
    """Persist an InvalidationReport and RollbackRecord to the artifact store."""
    from datetime import UTC, datetime
    from uuid import uuid4

    from film_pipeline.checkpoints.invalidation import InvalidationEngine
    from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata
    from film_pipeline.schemas.checkpoint import RollbackRecord

    engine = InvalidationEngine()
    invalidation_report = engine.report(
        rollback_target=rollback_target,
        artifact_types=artifact_types,
    )

    store = _services(rt).artifact_store
    inv_id = f"invalidation_report_{uuid4().hex[:8]}"
    inv_version = store.next_version(project_id, "intake", inv_id)
    inv_meta = ArtifactMetadata(
        artifact_id=inv_id,
        artifact_type=ArtifactType.INVALIDATION_REPORT,
        project_id=project_id,
        phase=FilmPhase("intake"),
        version=inv_version,
        status=ArtifactStatus.CANDIDATE,
        created_by="rollback_tool",
        created_at=datetime.now(UTC),
    )
    store.save(invalidation_report, inv_meta)
    inv_ref = f"artifact:{inv_id}:v{inv_version}"

    rollback_id = f"rollback:{project_id}:{uuid4().hex[:8]}"
    record = RollbackRecord(
        rollback_id=rollback_id,
        project_id=project_id,
        target_checkpoint_id=rollback_target,
        invalidation_report_ref=inv_ref,
        performed_by=performed_by,
        created_at=datetime.now(UTC),
        outcome="success",
    )
    rec_id = f"rollback_record_{uuid4().hex[:8]}"
    rec_version = store.next_version(project_id, "intake", rec_id)
    rec_meta = ArtifactMetadata(
        artifact_id=rec_id,
        artifact_type=ArtifactType.ROLLBACK_RECORD,
        project_id=project_id,
        phase=FilmPhase("intake"),
        version=rec_version,
        status=ArtifactStatus.CANDIDATE,
        created_by="rollback_tool",
        created_at=datetime.now(UTC),
    )
    store.save(record, rec_meta)
    rec_ref = f"artifact:{rec_id}:v{rec_version}"
    return inv_ref, rec_ref


async def list_checkpoints(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    project_id = str(args.get("project_id", "") or "")
    if not project_id and args.get("project_ref"):
        project_id = _active_project_id(args, rt) or ""
    cps = rt.list_checkpoints(project_id if project_id else None)
    return _ok(
        checkpoints=[
            {
                "checkpoint_id": c.checkpoint_id,
                "project_id": c.project_id,
                "phase": c.phase.value,
                "created_at": c.created_at.isoformat(),
                "reason": c.reason,
            }
            for c in cps
        ]
    )


async def create_checkpoint(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
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
    return _ok(
        checkpoint_id=cp.checkpoint_id,
        project_id=cp.project_id,
        phase=cp.phase.value,
        created_at=cp.created_at.isoformat(),
        reason=cp.reason,
    )


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
    for c in cps[-20:]:
        for art_type, ver in c.artifact_versions.items():
            versions.append(
                {"checkpoint_id": c.checkpoint_id, "artifact_type": art_type, "version": ver}
            )
    return _ok(versions=versions)


async def rollback_artifact(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    artifact_id = str(args.get("artifact_id", ""))
    if not artifact_id:
        return _error("artifact_id is required.")
    checkpoint_id = str(args.get("checkpoint_id", ""))
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    project_id = str(active["project_id"])

    confirmed = bool(args.get("confirmed"))
    if not confirmed:
        preview_cp = rt.get_checkpoint(checkpoint_id) if checkpoint_id else None
        artifact_types = [artifact_id]
        if preview_cp is not None:
            artifact_types = list(preview_cp.artifact_versions.keys()) or artifact_types
        return _error(
            "Rollback requires confirmation. Set confirmed=True to proceed.",
            invalidation_preview={
                "rollback_target": checkpoint_id or f"latest:{artifact_id}",
                "artifact_types": artifact_types,
            },
        )

    # If a specific checkpoint is given, use it as the restore target
    if checkpoint_id:
        cp = rt.get_checkpoint(checkpoint_id)
        if cp is None:
            return _error(f"Checkpoint '{checkpoint_id}' not found.")
        if not cp.git_commit:
            return _error(f"Checkpoint '{checkpoint_id}' has no git commit ref.")
        try:
            manager = rt.checkpoint_managers.get(project_id)
            if manager is None:
                return _error("No checkpoint manager for project.")
            rm = RollbackManager(checkpoint_manager=manager, git=manager.git)
            rm.rollback_artifact(artifact_id, cp.git_commit, performed_by="operator")
            inv_ref, rec_ref = _save_rollback_artifacts(
                rt,
                project_id,
                checkpoint_id,
                list(cp.artifact_versions.keys()) or [artifact_id],
                performed_by="operator",
            )
            return _ok(
                artifact_id=artifact_id,
                restored_from=checkpoint_id,
                git_commit=cp.git_commit[:8],
                invalidation_report_ref=inv_ref,
                rollback_record_ref=rec_ref,
            )
        except Exception as e:
            return _error(str(e))

    # Fallback: find latest checkpoint that contains this artifact
    cps = rt.list_checkpoints(project_id)
    for cp in sorted(cps, key=lambda c: c.created_at, reverse=True):
        if cp.git_commit and artifact_id in cp.artifact_versions:
            try:
                manager = rt.checkpoint_managers.get(project_id)
                if manager is None:
                    continue
                rm = RollbackManager(checkpoint_manager=manager, git=manager.git)
                rm.rollback_artifact(artifact_id, cp.git_commit, performed_by="operator")
                inv_ref, rec_ref = _save_rollback_artifacts(
                    rt,
                    project_id,
                    cp.checkpoint_id,
                    list(cp.artifact_versions.keys()),
                    performed_by="operator",
                )
                return _ok(
                    artifact_id=artifact_id,
                    restored_from=cp.checkpoint_id,
                    git_commit=cp.git_commit[:8],
                    invalidation_report_ref=inv_ref,
                    rollback_record_ref=rec_ref,
                )
            except Exception:
                continue

    return _error(f"No checkpoint found containing artifact '{artifact_id}'.")


async def rollback_to_checkpoint(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    checkpoint_id = str(args.get("checkpoint_id", ""))
    cp = rt.get_checkpoint(checkpoint_id)
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

    active = rt.get_active()
    project_id = str(active["project_id"]) if active else cp.project_id
    manager = rt.checkpoint_managers.get(project_id)
    if manager is None:
        return _error("No checkpoint manager for project.")

    try:
        rm = RollbackManager(checkpoint_manager=manager, git=manager.git)
        _record, _report = rm.rollback_to_checkpoint(checkpoint_id, performed_by="operator")
        inv_ref, rec_ref = _save_rollback_artifacts(
            rt,
            project_id,
            checkpoint_id,
            list(cp.artifact_versions.keys()),
            performed_by="operator",
        )
        return _ok(
            rollback_target=checkpoint_id,
            phase=cp.phase.value,
            reason=cp.reason,
            invalidation_report_ref=inv_ref,
            rollback_record_ref=rec_ref,
            message="Rollback completed. Invalidation report and rollback record saved.",
        )
    except Exception as e:
        return _error(str(e))


async def get_invalidation_report(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    checkpoint_id = str(args.get("checkpoint_id", ""))
    cp = rt.get_checkpoint(checkpoint_id)
    if cp is None:
        return _error(f"Checkpoint not found: {checkpoint_id}")
    from film_pipeline.checkpoints.invalidation import InvalidationEngine

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
