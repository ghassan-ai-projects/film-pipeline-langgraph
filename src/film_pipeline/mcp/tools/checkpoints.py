"""Checkpoint / version / rollback tools."""

from __future__ import annotations

import film_pipeline.mcp.tools as tools_pkg

from .helpers import _error, _ok


async def list_checkpoints(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    project_id = str(args.get("project_id", "") or "")
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
            manager.git.restore_files(cp.git_commit, [artifact_id])
            manager.git.commit(f"rollback: artifact {artifact_id} to {cp.git_commit[:8]}")
            return _ok(
                artifact_id=artifact_id,
                restored_from=checkpoint_id,
                git_commit=cp.git_commit[:8],
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
                manager.git.restore_files(cp.git_commit, [artifact_id])
                manager.git.commit(f"rollback: artifact {artifact_id} to {cp.git_commit[:8]}")
                return _ok(
                    artifact_id=artifact_id,
                    restored_from=cp.checkpoint_id,
                    git_commit=cp.git_commit[:8],
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
    return _ok(
        rollback_target=checkpoint_id,
        phase=cp.phase.value,
        reason=cp.reason,
        message="Rollback requires human confirmation. State restored to checkpoint.",
    )


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
