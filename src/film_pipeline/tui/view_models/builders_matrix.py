"""Matrix, graph timeline, and scene row builders for the operator cockpit."""

from __future__ import annotations

from film_pipeline.app.services.models import DashboardSummary, OperatorComment, ValidationWorkspace
from film_pipeline.tui.view_models.helpers import (
    _comments_for_target,
    _int_value,
    _is_scene_id,
    _issue_label,
    _issue_target,
    _issues_by_target,
    _phase_blockers,
    _row_matches_token,
    _scene_ids_from_summary,
    _validation_bucket,
    _validation_for_target,
)
from film_pipeline.tui.view_models.models import GRAPH_PHASES, MatrixImpact, PhaseDetail


def build_matrix_pivot_rows(
    rows: list[dict[str, object]],
    field: str,
) -> list[dict[str, object]]:
    """Group smart-matrix rows by a supported field."""
    pivot_field = {
        "status": "status",
        "phase": "phase",
        "kind": "kind",
        "type": "kind",
        "validation": "validation",
    }.get(field.strip().lower(), "status")
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        value = str(row.get(pivot_field, "")) or "unknown"
        if pivot_field == "validation":
            value = _validation_bucket(value)
        grouped.setdefault(value, []).append(row)
    result: list[dict[str, object]] = []
    for value, bucket in sorted(
        grouped.items(),
        key=lambda item: (-sum(_int_value(row.get("issue_count", 0)) for row in item[1]), item[0]),
    ):
        issue_count = sum(_int_value(row.get("issue_count", 0)) for row in bucket)
        sample = str(bucket[0].get("target", ""))
        result.append(
            {
                "field": pivot_field,
                "value": value,
                "rows": len(bucket),
                "issues": issue_count,
                "sample": sample,
                "command": f"matrix {pivot_field}:{value}" if value != "unknown" else "matrix all",
            }
        )
    return result


def build_graph_rows(dashboard: DashboardSummary | None) -> list[dict[str, object]]:
    """Build a graph timeline with completed/current/future status."""
    current = dashboard.current_phase if dashboard else ""
    rows: list[dict[str, object]] = []
    reached_current = False
    for index, phase in enumerate(GRAPH_PHASES, start=1):
        if dashboard and dashboard.stalled_phase == phase:
            status = "stalled"
            reached_current = True
        elif phase == current:
            status = "current"
            reached_current = True
        elif current and not reached_current:
            status = "complete"
        elif not current and index == 1:
            status = "next"
        else:
            status = "future"
        rows.append(
            {
                "step": index,
                "phase": phase,
                "status": status,
                "next_action": dashboard.next_action if dashboard and phase == current else "",
            }
        )
    return rows


def build_phase_detail(
    phase: str,
    *,
    dashboard: DashboardSummary | None,
    artifacts: list[dict[str, object]],
    validation: ValidationWorkspace | None,
) -> PhaseDetail:
    """Build graph drill-down context for one phase."""
    graph_row = next(
        (row for row in build_graph_rows(dashboard) if str(row.get("phase", "")) == phase),
        {"phase": phase, "status": "unknown", "next_action": ""},
    )
    phase_artifacts = [
        artifact for artifact in artifacts if str(artifact.get("phase", "")) == phase
    ]
    blockers = _phase_blockers(phase, dashboard, validation)
    commands = [f"phase {phase}", f"matrix phase:{phase}"]
    if phase_artifacts:
        first = str(phase_artifacts[0].get("artifact_id", ""))
        if first:
            commands.append(f"artifact {first}")
    if dashboard and phase == dashboard.current_phase:
        if "approve_phase" in dashboard.eligible_actions:
            commands.append("approve")
            commands.append("confirm approve")
        if "request_revision" in dashboard.eligible_actions:
            commands.append("revise <note>")
        if dashboard.stalled_phase == phase:
            commands.append("show blocked")
    summary = (
        f"{phase} is {graph_row.get('status', 'unknown')}. "
        f"{len(phase_artifacts)} artifact(s), {len(blockers)} blocker(s)."
    )
    return PhaseDetail(
        phase=phase,
        status=str(graph_row.get("status", "")),
        summary=summary,
        artifacts=phase_artifacts,
        blockers=blockers,
        suggested_commands=commands,
    )


def build_scene_rows(
    matrix_rows: list[dict[str, object]],
    *,
    artifacts: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    """Extract scene-oriented rows from the smart matrix."""
    scene_rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for artifact in artifacts or []:
        for scene_id in _scene_ids_from_summary(artifact):
            if scene_id in seen:
                continue
            seen.add(scene_id)
            scene_rows.append(
                {
                    "scene": scene_id,
                    "phase": artifact.get("phase", ""),
                    "status": artifact.get("status", ""),
                    "validation": "passing/unknown",
                    "action": "open scene",
                }
            )
    for row in matrix_rows:
        target = str(row.get("target", ""))
        kind = str(row.get("kind", ""))
        if _is_scene_id(target) or kind in {"scene", "scene_script", "scene_issue"}:
            if target in seen:
                continue
            seen.add(target)
            scene_rows.append(
                {
                    "scene": target,
                    "phase": row.get("phase", ""),
                    "status": row.get("status", ""),
                    "validation": row.get("validation", ""),
                    "action": row.get("action", ""),
                }
            )
    return scene_rows


def build_matrix_rows(
    artifacts: list[dict[str, object]],
    validation: ValidationWorkspace | None,
) -> list[dict[str, object]]:
    """Build a smart production matrix from artifacts and validation issues."""
    rows: list[dict[str, object]] = []
    issues = list(validation.blocking_issues if validation else [])
    issues.extend(validation.non_blocking_issues if validation else [])
    issues_by_target = _issues_by_target(issues)

    for artifact in artifacts:
        artifact_id = str(artifact.get("artifact_id", ""))
        phase = str(artifact.get("phase", ""))
        row_issues = issues_by_target.get(artifact_id, [])
        rows.append(
            {
                "target": artifact_id,
                "kind": str(artifact.get("artifact_type", "artifact")),
                "phase": phase,
                "version": artifact.get("version", ""),
                "status": artifact.get("status", ""),
                "validation": _issue_label(row_issues),
                "issue_count": len(row_issues),
                "action": "open artifact" if not row_issues else "review issues",
            }
        )

    for issue in issues:
        target = _issue_target(issue)
        if target and any(row["target"] == target for row in rows):
            continue
        rows.append(
            {
                "target": target or str(issue.get("validator_id", "issue")),
                "kind": "validation_issue",
                "phase": validation.phase if validation else "",
                "version": "",
                "status": str(issue.get("severity", "warning")),
                "validation": str(issue.get("message", "")),
                "issue_count": 1,
                "action": "request fix",
            }
        )
    return rows


def filter_matrix_rows(
    rows: list[dict[str, object]],
    query: str,
) -> list[dict[str, object]]:
    """Filter smart-matrix rows with small operator-friendly query terms."""
    normalized = query.strip().lower()
    if not normalized or normalized in {"all", "clear", "*"}:
        return list(rows)
    result = rows
    for token in normalized.split():
        result = [row for row in result if _row_matches_token(row, token)]
    return result


def build_matrix_impact(
    row: dict[str, object],
    *,
    comments: list[OperatorComment],
    validation: ValidationWorkspace | None,
) -> MatrixImpact:
    """Build impact context for one smart-matrix row."""
    target = str(row.get("target", ""))
    kind = str(row.get("kind", "matrix_row"))
    phase = str(row.get("phase", ""))
    linked_comments = _comments_for_target(comments, target, target)
    linked_validation = _validation_for_target(validation, target, target)
    suggested = ["open linked object", "add comment"]
    if linked_validation:
        suggested.append("request targeted revision")
    if str(row.get("status", "")).lower() in {"candidate", "warning", "blocking"}:
        suggested.append("review before approval")
    summary = (
        f"{kind} {target or 'unknown'} in phase {phase or 'unknown'} has "
        f"{len(linked_validation)} linked validation issue(s) and "
        f"{len(linked_comments)} operator comment(s)."
    )
    return MatrixImpact(
        target_id=target,
        target_type=kind,
        phase=phase,
        summary=summary,
        linked_comments=linked_comments,
        linked_validation=linked_validation,
        suggested_actions=suggested,
    )
