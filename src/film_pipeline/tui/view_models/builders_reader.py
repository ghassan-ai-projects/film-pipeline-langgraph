"""Builders that turn service payloads into readable reader views and rows."""

from __future__ import annotations

from film_pipeline.app.services.models import (
    ArtifactDetail,
    DashboardSummary,
    OperatorComment,
    ValidationWorkspace,
)
from film_pipeline.tui.view_models.helpers import (
    all_issues,
    artifact_outline,
    comments_for_target,
    find_scene,
    issue_target,
    render_artifact_body,
    render_scene,
    scene_outline,
    validation_for_target,
)
from film_pipeline.tui.view_models.models import ReaderView


def validation_issue_rows(
    validation: ValidationWorkspace | None,
    *,
    validator_id: str = "",
    severity: str = "",
) -> list[dict[str, object]]:
    """Build rendered validation issue rows with optional filters."""
    rows: list[dict[str, object]] = []
    for issue in all_issues(validation):
        issue_validator = str(issue.get("validator_id", ""))
        issue_severity = str(issue.get("severity", ""))
        if validator_id and issue_validator != validator_id:
            continue
        if severity and issue_severity != severity:
            continue
        rows.append(
            {
                "severity": issue_severity,
                "validator": issue_validator,
                "target": issue_target(issue),
                "scene": str(issue.get("scene_id", "")),
                "message": issue.get("message", ""),
            }
        )
    return rows


def _artifact_identity(artifact: ArtifactDetail) -> dict[str, object]:
    """Fields identifying the artifact a reader view describes, plus its state."""
    return {
        "artifact_id": artifact.artifact_id,
        "artifact_type": artifact.artifact_type,
        "phase": artifact.phase,
        "version": artifact.version,
        "status": artifact.status,
    }


def build_artifact_reader(
    artifact: ArtifactDetail,
    *,
    comments: list[OperatorComment],
    validation: ValidationWorkspace | None,
    scene_id: str = "",
) -> ReaderView:
    """Build a readable view for an artifact or one scene inside it."""
    body = artifact.body
    target_id = scene_id or artifact.artifact_id
    scene = find_scene(body, scene_id) if scene_id else None
    if scene is not None:
        title = str(scene.get("scene_heading", scene_id))
        subtitle = f"scene {scene_id} from {artifact.artifact_id}:v{artifact.version}"
        outline = scene_outline(scene)
        readable_body = render_scene(scene)
        metadata = {"scene_id": scene_id, **_artifact_identity(artifact)}
    else:
        title = f"{artifact.artifact_id}:v{artifact.version}"
        subtitle = f"{artifact.artifact_type} | {artifact.phase} | {artifact.status}"
        outline = artifact_outline(body)
        readable_body = render_artifact_body(body)
        metadata = _artifact_identity(artifact)
        for key in ("created_by", "reviewed_by", "validation_refs", "approval_ref", "built_from"):
            if key in body:
                metadata[key] = body[key]
    return ReaderView(
        title=title,
        subtitle=subtitle,
        outline=outline,
        body=readable_body,
        metadata=metadata,
        linked_comments=comments_for_target(comments, target_id, artifact.artifact_id),
        linked_validation=validation_for_target(validation, target_id, artifact.artifact_id),
    )


def build_overview_reader(
    dashboard: DashboardSummary,
    *,
    blocking_issues: int = 0,
    stage_explanation: str = "",
) -> ReaderView:
    """Build the default reader content: where the film is and what to do next.

    Shown when nothing is selected, so the studio is never blank.
    """
    lines: list[str] = []
    if dashboard.idea:
        lines.append(dashboard.idea)
        lines.append("")
    lines.append(f"Now:  {dashboard.current_phase or 'not started'} — {dashboard.status}")
    if stage_explanation:
        lines.append(f"      {stage_explanation}")
    if dashboard.next_action:
        lines.append(f"Next: {dashboard.next_action}")
    if dashboard.route_reason:
        lines.append(f"Why:  {dashboard.route_reason}")
    if blocking_issues:
        lines.append(f"Blocked by {blocking_issues} validation issue(s) — see the Issues tab.")

    metadata: dict[str, object] = {
        "mode": f"{dashboard.workflow_mode}/{dashboard.runtime_mode}",
    }
    if dashboard.generation_policy == "text_only":
        metadata["policy"] = "text only (no generated media)"
    return ReaderView(
        title=dashboard.title,
        subtitle=f"project {dashboard.project_id}",
        outline=[],
        body="\n".join(lines),
        metadata=metadata,
        linked_comments=[],
        linked_validation=[],
    )
