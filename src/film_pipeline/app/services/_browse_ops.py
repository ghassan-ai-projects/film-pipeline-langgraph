"""Read-side operator views: comments, artifacts, assets, checkpoints, audit feed."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

from film_pipeline.app._persistence import artifact_root
from film_pipeline.artifacts.manifest import read_manifest
from film_pipeline.operations.errors import BackendOperationError
from film_pipeline.operations.models import (
    ArtifactDetail,
    AuditEvent,
    OperatorComment,
    OperatorCommentRequest,
)
from film_pipeline.schemas.base import FilmPhase

if TYPE_CHECKING:
    from film_pipeline.app.services.operator import OperatorService


def add_operator_comment(
    svc: OperatorService,
    request: OperatorCommentRequest,
    project_id: str | None = None,
) -> OperatorComment:
    """Persist a target-scoped operator comment."""
    body = _required_text(request.body, "comment body")
    target_type = _required_text(request.target_type, "comment target_type")
    target_id = _required_text(request.target_id, "comment target_id")
    state = svc._state_for_project(project_id)
    raw = svc.runtime.add_operator_comment(
        str(state["project_id"]),
        target_type=target_type,
        target_id=target_id,
        body=body,
        phase=request.phase.strip(),
        source=request.source.strip() or "operator",
    )
    return _comment_from_raw(raw)


def list_operator_comments(
    svc: OperatorService,
    project_id: str | None = None,
    *,
    include_resolved: bool = False,
) -> list[OperatorComment]:
    """List target-scoped operator comments."""
    state = svc._state_for_project(project_id)
    comments = svc.runtime.list_operator_comments(
        str(state["project_id"]),
        include_resolved=include_resolved,
    )
    return [_comment_from_raw(comment) for comment in comments]


def list_artifacts(
    svc: OperatorService, project_id: str | None = None, phase: str | None = None
) -> list[dict[str, Any]]:
    """List artifacts for a project, optionally filtered to one phase."""
    state = svc._state_for_project(project_id)
    store = svc.runtime.services.artifact_store if svc.runtime.services else None
    if store is None:
        return []
    phase_filter: FilmPhase | None = FilmPhase(phase) if phase else None
    artifacts = store.list_artifacts(str(state["project_id"]), phase_filter)
    rows: list[dict[str, Any]] = []
    for artifact in artifacts:
        rows.append(
            {
                "artifact_id": artifact.artifact_id,
                "artifact_type": str(artifact.artifact_type.value),
                "phase": str(artifact.phase.value),
                "version": artifact.version,
                "status": str(artifact.status.value),
            }
        )
    return rows


def list_assets(svc: OperatorService, project_id: str | None = None) -> list[dict[str, Any]]:
    """List generated/reference assets from the project asset manifest."""
    state = svc._state_for_project(project_id)
    root = artifact_root(svc.runtime)
    if root is None:
        return []
    manifest = read_manifest(str(state["project_id"]), root=root)
    if manifest is None:
        return []
    return [
        {
            "asset_id": entry.asset_id,
            "kind": entry.kind,
            "scene_id": entry.scene_id,
            "shot_id": entry.shot_id,
            "take": entry.take,
            "active": entry.active,
            "path": entry.path,
        }
        for entry in manifest.entries
    ]


def inspect_artifact(
    svc: OperatorService,
    artifact_id: str,
    phase: str,
    version: int = 1,
    project_id: str | None = None,
) -> ArtifactDetail:
    """Load one artifact body."""
    if not artifact_id:
        raise BackendOperationError("artifact_id is required.")
    state = svc._state_for_project(project_id)
    if svc.runtime.services is None:
        raise BackendOperationError("artifact store is not configured.")
    body = svc.runtime.services.artifact_store.load(
        str(state["project_id"]), FilmPhase(phase), artifact_id, version
    )
    return ArtifactDetail(
        artifact_id=artifact_id,
        artifact_type=str(body.get("artifact_type", artifact_id)),
        phase=phase,
        version=version,
        status=str(body.get("status", "candidate")),
        body=body,
    )


def list_checkpoints(svc: OperatorService, project_id: str | None = None) -> list[dict[str, str]]:
    """List checkpoints for a project."""
    state = svc._state_for_project(project_id)
    checkpoints = svc.runtime.list_checkpoints(str(state["project_id"]))
    return [
        {
            "checkpoint_id": checkpoint.checkpoint_id,
            "project_id": checkpoint.project_id,
            "phase": str(checkpoint.phase.value),
            "reason": checkpoint.reason,
            "created_at": checkpoint.created_at.isoformat(),
        }
        for checkpoint in checkpoints
    ]


def list_provider_status(svc: OperatorService) -> list[dict[str, Any]]:
    """Return provider health rows."""
    return [
        {"provider_id": provider_id, **health}
        for provider_id, health in sorted(svc.runtime.get_all_health().items())
    ]


def get_audit_feed(
    svc: OperatorService, project_id: str | None = None, limit: int = 20
) -> list[AuditEvent]:
    """Return recent audit events."""
    state = svc._state_for_project(project_id) if project_id else None
    events = svc.runtime.get_audit_log(
        str(state["project_id"]) if state is not None else None,
        limit=limit,
    )
    feed: list[AuditEvent] = []
    for event in events:
        details = cast(dict[str, Any], event.get("details", {}))
        target = str(details.get("project_id", details.get("phase", "")))
        feed.append(
            AuditEvent(
                timestamp=str(event.get("timestamp", "")),
                actor=str(event.get("actor", "")),
                action=str(event.get("action", "")),
                target=target,
                summary=f"{event.get('action', '')} {target}".strip(),
            )
        )
    return feed


def _required_text(value: str, field_label: str) -> str:
    """Return the stripped value, failing when the field is blank."""
    text = value.strip()
    if not text:
        raise BackendOperationError(f"{field_label} is required.")
    return text


def _comment_from_raw(raw: Mapping[str, Any]) -> OperatorComment:
    return OperatorComment(
        comment_id=str(raw.get("comment_id", "")),
        project_id=str(raw.get("project_id", "")),
        target_type=str(raw.get("target_type", "")),
        target_id=str(raw.get("target_id", "")),
        body=str(raw.get("body", "")),
        phase=str(raw.get("phase", "")),
        source=str(raw.get("source", "")),
        created_at=str(raw.get("created_at", "")),
        resolved=bool(raw.get("resolved", False)),
    )
