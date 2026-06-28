"""Artifact/scene reader, review/validation row builders, and selection helpers."""

from __future__ import annotations

from typing import Any

from film_pipeline.app.services.models import (
    ArtifactDetail,
    OperatorComment,
    ReviewWorkspace,
    ValidationWorkspace,
)
from film_pipeline.tui.view_models.helpers import (
    _all_issues,
    _artifact_outline,
    _artifact_scenes,
    _comments_for_target,
    _dedupe_review_issues,
    _find_scene,
    _is_scene_id,
    _issue_focus_target,
    _issue_target,
    _open_command,
    _render_artifact_body,
    _render_scene,
    _scene_outline,
    _severity_rank,
    _target_from_text,
    _target_type_for_issue,
    _validation_for_target,
    _validator_action,
)
from film_pipeline.tui.view_models.models import (
    ReaderView,
    ReviewIssueTarget,
    TargetSelection,
    ValidationFixSuggestion,
    ValidationGroup,
)


def build_review_checklist_rows(
    review: ReviewWorkspace | None,
    validation: ValidationWorkspace | None,
    comments: list[OperatorComment],
) -> list[dict[str, object]]:
    """Build review readiness checklist rows."""
    if review is None:
        return []
    blocking_count = len(validation.blocking_issues) if validation else 0
    warning_count = len(validation.non_blocking_issues) if validation else 0
    candidate_count = len(review.candidate_artifacts)
    comment_count = len([comment for comment in comments if not comment.resolved])
    return [
        {
            "check": "candidate_artifacts",
            "status": "ready" if candidate_count else "missing",
            "detail": f"{candidate_count} candidate artifact(s)",
            "action": "review candidates" if candidate_count else "wait for artifacts",
        },
        {
            "check": "blocking_validation",
            "status": "blocked" if blocking_count else "ready",
            "detail": f"{blocking_count} blocking issue(s)",
            "action": "show blocked" if blocking_count else "approve eligible",
        },
        {
            "check": "warning_validation",
            "status": "warning" if warning_count else "ready",
            "detail": f"{warning_count} warning(s)",
            "action": "validation warning" if warning_count else "none",
        },
        {
            "check": "operator_comments",
            "status": "noted" if comment_count else "empty",
            "detail": f"{comment_count} open comment(s)",
            "action": "thread <target>" if comment_count else "add comment",
        },
        {
            "check": "approval_actions",
            "status": "ready" if review.available_actions else "blocked",
            "detail": ", ".join(review.available_actions) or "none",
            "action": "approve or revise" if review.available_actions else "inspect blockers",
        },
    ]


def build_review_issue_rows(
    review: ReviewWorkspace | None,
    validation: ValidationWorkspace | None,
) -> list[dict[str, object]]:
    """Build review issue rows with inferred target commands."""
    issues = build_review_issue_targets(review, validation)
    return [
        {
            "issue_id": issue.issue_id,
            "severity": issue.severity,
            "target_id": issue.target_id,
            "target_type": issue.target_type,
            "message": issue.message,
            "command": issue.command,
        }
        for issue in issues
    ]


def build_review_issue_targets(
    review: ReviewWorkspace | None,
    validation: ValidationWorkspace | None,
) -> list[ReviewIssueTarget]:
    """Merge review issue text and validation issues into navigable targets."""
    rows: list[ReviewIssueTarget] = []
    for index, message in enumerate(review.open_issues if review else [], start=1):
        target_id = _target_from_text(message)
        target_type = "scene" if _is_scene_id(target_id) else "review_issue"
        rows.append(
            ReviewIssueTarget(
                issue_id=f"review:{index}",
                severity="review",
                target_id=target_id or f"review:{index}",
                target_type=target_type,
                message=message,
                command=_open_command(target_type, target_id),
            )
        )
    for index, issue in enumerate(_all_issues(validation), start=1):
        target_id = _issue_focus_target(issue) or _issue_target(issue) or f"validation:{index}"
        target_type = _target_type_for_issue(issue, target_id)
        rows.append(
            ReviewIssueTarget(
                issue_id=f"validation:{index}",
                severity=str(issue.get("severity", "warning")),
                target_id=target_id,
                target_type=target_type,
                message=str(issue.get("message", "")),
                command=_open_command(target_type, target_id),
            )
        )
    return _dedupe_review_issues(rows)


def build_comment_thread_rows(comments: list[OperatorComment]) -> list[dict[str, object]]:
    """Group operator comments by target for review triage."""
    grouped: dict[tuple[str, str], list[OperatorComment]] = {}
    for comment in comments:
        grouped.setdefault((comment.target_type, comment.target_id), []).append(comment)
    rows: list[dict[str, object]] = []
    for (target_type, target_id), thread in sorted(grouped.items(), key=lambda item: item[0]):
        latest = max(thread, key=lambda comment: comment.created_at)
        open_count = len([comment for comment in thread if not comment.resolved])
        rows.append(
            {
                "target_id": target_id,
                "target_type": target_type,
                "open": open_count,
                "latest": latest.body,
                "updated": latest.created_at,
                "command": f"thread {target_id}",
            }
        )
    return rows


def build_validation_groups(
    validation: ValidationWorkspace | None,
) -> list[ValidationGroup]:
    """Group validation issues by validator and severity."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for issue in _all_issues(validation):
        validator_id = str(issue.get("validator_id", "unknown-validator"))
        severity = str(issue.get("severity", "warning"))
        grouped.setdefault((validator_id, severity), []).append(issue)

    groups: list[ValidationGroup] = []
    for (validator_id, severity), issues in sorted(
        grouped.items(),
        key=lambda item: (_severity_rank(item[0][1]), item[0][0]),
    ):
        targets = sorted({target for issue in issues if (target := _issue_focus_target(issue))})
        groups.append(
            ValidationGroup(
                validator_id=validator_id,
                severity=severity,
                count=len(issues),
                targets=targets,
                message=str(issues[0].get("message", "")),
                suggested_action=_validator_action(severity, targets),
            )
        )
    return groups


def build_validation_fix_suggestions(
    validation: ValidationWorkspace | None,
) -> list[ValidationFixSuggestion]:
    """Turn validation issues into direct operator actions."""
    suggestions: list[ValidationFixSuggestion] = []
    for issue in sorted(
        _all_issues(validation),
        key=lambda item: (_severity_rank(str(item.get("severity", ""))), _issue_target(item)),
    ):
        target_id = _issue_target(issue) or str(issue.get("validator_id", "validation"))
        target_type = _target_type_for_issue(issue, target_id)
        message = str(issue.get("message", "Validation issue needs review."))
        validator_id = str(issue.get("validator_id", "unknown-validator"))
        command_target = str(issue.get("scene_id", "")) or target_id
        suggestions.append(
            ValidationFixSuggestion(
                target_id=command_target,
                target_type=target_type,
                severity=str(issue.get("severity", "warning")),
                validator_id=validator_id,
                message=message,
                command=f"fix {command_target}",
                rationale=f"{validator_id}: {message}",
            )
        )
    return suggestions


def validation_issue_rows(
    validation: ValidationWorkspace | None,
    *,
    validator_id: str = "",
    severity: str = "",
) -> list[dict[str, object]]:
    """Build rendered validation issue rows with optional filters."""
    rows: list[dict[str, object]] = []
    for issue in _all_issues(validation):
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
                "target": _issue_target(issue),
                "scene": str(issue.get("scene_id", "")),
                "message": issue.get("message", ""),
            }
        )
    return rows


def format_fix_draft(suggestion: ValidationFixSuggestion) -> str:
    """Build a concise review note draft for a suggested fix."""
    return f"{suggestion.validator_id}: {suggestion.message}"


def selection_from_row(source: str, row: dict[str, object]) -> TargetSelection:
    """Infer a typed selection from a rendered table row."""
    if source == "asset_table" and row.get("asset_id"):
        return TargetSelection(
            target_type="asset",
            target_id=str(row.get("asset_id", "")),
            phase=str(row.get("scene_id", "")),
            source=source,
            detail=row,
        )
    if source in {"asset_table", "review_artifacts", "dashboard_artifacts"}:
        target_id = str(row.get("artifact_id", row.get("artifact", "")))
        return TargetSelection(
            target_type="artifact",
            target_id=target_id,
            phase=str(row.get("phase", "")),
            source=source,
            detail=row,
        )
    if source == "dashboard_kpi_table":
        return TargetSelection(
            target_type="dashboard_metric",
            target_id=str(row.get("metric", "")),
            source=source,
            detail=row,
        )
    if source == "dashboard_action_table":
        return TargetSelection(
            target_type="dashboard_action",
            target_id=str(row.get("action", "")),
            source=source,
            detail=row,
        )
    if source == "project_table":
        return TargetSelection(
            target_type="project",
            target_id=str(row.get("project", "")),
            source=source,
            detail=row,
        )
    if source == "guide_table":
        return TargetSelection(
            target_type="guide_step",
            target_id=str(row.get("step", "")),
            source=source,
            detail=row,
        )
    if source == "review_checklist_table":
        return TargetSelection(
            target_type="review_check",
            target_id=str(row.get("check", "")),
            source=source,
            detail=row,
        )
    if source == "review_issue_table":
        return TargetSelection(
            target_type=str(row.get("target_type", "review_issue")),
            target_id=str(row.get("target_id", "")),
            source=source,
            detail=row,
        )
    if source == "comment_thread_table":
        return TargetSelection(
            target_type=str(row.get("target_type", "comment_thread")),
            target_id=str(row.get("target_id", "")),
            source=source,
            detail=row,
        )
    if source == "scene_table":
        return TargetSelection(
            target_type="scene",
            target_id=str(row.get("scene", "")),
            phase=str(row.get("phase", "")),
            source=source,
            detail=row,
        )
    if source == "validation_table":
        target_id = str(row.get("target", "")) or str(row.get("validator", ""))
        return TargetSelection(
            target_type="validation_issue",
            target_id=target_id,
            phase=str(row.get("phase", "")),
            source=source,
            detail=row,
        )
    if source == "validation_group_table":
        return TargetSelection(
            target_type="validator",
            target_id=str(row.get("validator_id", "")),
            source=source,
            detail=row,
        )
    if source == "validation_fix_table":
        return TargetSelection(
            target_type=str(row.get("target_type", "validation_fix")),
            target_id=str(row.get("target_id", "")),
            source=source,
            detail=row,
        )
    if source == "matrix_table":
        kind = str(row.get("kind", "matrix_row"))
        return TargetSelection(
            target_type=kind,
            target_id=str(row.get("target", "")),
            phase=str(row.get("phase", "")),
            source=source,
            detail=row,
        )
    if source == "matrix_pivot_table":
        return TargetSelection(
            target_type="matrix_pivot",
            target_id=str(row.get("value", "")),
            source=source,
            detail=row,
        )
    if source == "graph_table":
        return TargetSelection(
            target_type="graph_phase",
            target_id=str(row.get("phase", "")),
            phase=str(row.get("phase", "")),
            source=source,
            detail=row,
        )
    if source == "graph_artifact_table":
        return TargetSelection(
            target_type="artifact",
            target_id=str(row.get("artifact_id", "")),
            phase=str(row.get("phase", "")),
            source=source,
            detail=row,
        )
    if source == "command_suggestion_table":
        return TargetSelection(
            target_type="command",
            target_id=str(row.get("command", "")),
            source=source,
            detail=row,
        )
    if source == "reader_index_table":
        return TargetSelection(
            target_type=str(row.get("target_type", "reader_index")),
            target_id=str(row.get("target_id", "")),
            source=source,
            detail=row,
        )
    if source == "reader_link_table":
        return TargetSelection(
            target_type=str(row.get("kind", "reader_link")),
            target_id=str(row.get("target_id", "")),
            source=source,
            detail=row,
        )
    if source == "asset_action_table":
        return TargetSelection(
            target_type="asset_action",
            target_id=str(row.get("artifact_id", "")),
            phase=str(row.get("phase", "")),
            source=source,
            detail=row,
        )
    if source == "provider_table":
        return TargetSelection(
            target_type="provider",
            target_id=str(row.get("provider_id", "")),
            source=source,
            detail=row,
        )
    if source == "checkpoint_table":
        return TargetSelection(
            target_type="checkpoint",
            target_id=str(row.get("checkpoint_id", "")),
            phase=str(row.get("phase", "")),
            source=source,
            detail=row,
        )
    return TargetSelection(
        target_type=source,
        target_id=str(next(iter(row.values()), "")),
        source=source,
        detail=row,
    )


def format_selection_detail(selection: TargetSelection) -> str:
    """Render a selected object in the context drawer."""
    lines = [
        "Selected Target",
        "",
        f"type: {selection.target_type}",
        f"id: {selection.target_id or 'unknown'}",
    ]
    if selection.phase:
        lines.append(f"phase: {selection.phase}")
    lines.extend(["", "Detail"])
    for key, value in selection.detail.items():
        lines.append(f"{key}: {value}")
    lines.extend(
        [
            "",
            "Comment format",
            f"comment {selection.target_id} | <what you want changed>",
        ]
    )
    return "\n".join(lines)


def format_targeted_revision_note(selection: TargetSelection | None, note: str) -> str:
    """Attach a free-form operator note to the selected target."""
    clean_note = note.strip()
    if selection is None:
        return clean_note
    parts = [
        f"target_type={selection.target_type}",
        f"target_id={selection.target_id or 'unknown'}",
    ]
    if selection.phase:
        parts.append(f"phase={selection.phase}")
    return f"[{' '.join(parts)}] {clean_note}"


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
    scene = _find_scene(body, scene_id) if scene_id else None
    if scene is not None:
        title = str(scene.get("scene_heading", scene_id))
        subtitle = f"scene {scene_id} from {artifact.artifact_id}:v{artifact.version}"
        outline = _scene_outline(scene)
        readable_body = _render_scene(scene)
        metadata = {
            "scene_id": scene_id,
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "phase": artifact.phase,
            "version": artifact.version,
            "status": artifact.status,
        }
    else:
        title = f"{artifact.artifact_id}:v{artifact.version}"
        subtitle = f"{artifact.artifact_type} | {artifact.phase} | {artifact.status}"
        outline = _artifact_outline(body)
        readable_body = _render_artifact_body(body)
        metadata = {
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "phase": artifact.phase,
            "version": artifact.version,
            "status": artifact.status,
        }
        for key in ("created_by", "reviewed_by", "validation_refs", "approval_ref", "built_from"):
            if key in body:
                metadata[key] = body[key]
    return ReaderView(
        title=title,
        subtitle=subtitle,
        outline=outline,
        body=readable_body,
        metadata=metadata,
        linked_comments=_comments_for_target(comments, target_id, artifact.artifact_id),
        linked_validation=_validation_for_target(validation, target_id, artifact.artifact_id),
    )


def build_reader_index_rows(artifact: ArtifactDetail | None) -> list[dict[str, object]]:
    """Build navigable scene/section index rows for the current artifact."""
    if artifact is None:
        return []
    scenes = _artifact_scenes(artifact.body)
    if scenes:
        return [
            {
                "order": index,
                "target_id": str(scene.get("scene_id", f"scene_{index}")),
                "target_type": "scene",
                "heading": str(
                    scene.get(
                        "scene_heading",
                        scene.get("dramatic_function", scene.get("scene_id", "")),
                    )
                ),
                "command": f"scene {scene.get('scene_id', f'scene_{index}')}",
            }
            for index, scene in enumerate(scenes, start=1)
        ]
    return [
        {
            "order": index,
            "target_id": str(key),
            "target_type": "section",
            "heading": str(key),
            "command": f"link {key}",
        }
        for index, key in enumerate(artifact.body, start=1)
    ]


def build_reader_link_rows(reader: ReaderView | None) -> list[dict[str, object]]:
    """Build linked validation/comment rows for the current reader."""
    if reader is None:
        return []
    rows: list[dict[str, object]] = []
    for issue in reader.linked_validation:
        target_id = _issue_focus_target(issue) or _issue_target(issue)
        rows.append(
            {
                "kind": "validation",
                "target_id": target_id,
                "status": str(issue.get("severity", "")),
                "detail": str(issue.get("message", "")),
                "command": f"fix {target_id}" if target_id else "show blocked",
            }
        )
    for comment in reader.linked_comments:
        rows.append(
            {
                "kind": "comment",
                "target_id": comment.target_id,
                "status": "resolved" if comment.resolved else "open",
                "detail": comment.body,
                "command": f"thread {comment.target_id}",
            }
        )
    return rows


def build_asset_action_rows(artifacts: list[dict[str, object]]) -> list[dict[str, object]]:
    """Build direct action rows for artifact review and revision work."""
    rows: list[dict[str, object]] = []
    for artifact in artifacts:
        artifact_id = str(artifact.get("artifact_id", ""))
        artifact_type = str(artifact.get("artifact_type", "artifact"))
        phase = str(artifact.get("phase", ""))
        if not artifact_id:
            continue
        rows.extend(
            [
                {
                    "artifact_id": artifact_id,
                    "action": "review",
                    "phase": phase,
                    "purpose": f"ask for focused review of {artifact_type}",
                    "command": f"asset review {artifact_id}",
                },
                {
                    "artifact_id": artifact_id,
                    "action": "change",
                    "phase": phase,
                    "purpose": "request a targeted change",
                    "command": f"asset change {artifact_id} | <note>",
                },
                {
                    "artifact_id": artifact_id,
                    "action": "extend",
                    "phase": phase,
                    "purpose": "request more detail, coverage, or variants",
                    "command": f"asset extend {artifact_id} | <note>",
                },
            ]
        )
    return rows
