"""View models for the Textual operator cockpit."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from film_pipeline.app.services.models import (
    ArtifactDetail,
    AuditEvent,
    DashboardSummary,
    OperatorComment,
    ProjectListItem,
    ReviewWorkspace,
    ValidationWorkspace,
)

GRAPH_PHASES: tuple[str, ...] = (
    "intake",
    "constitution",
    "development",
    "script",
    "visual_dev",
    "shot_bible",
    "gen_planning",
    "generation",
    "qc",
    "post",
    "delivery",
)


@dataclass(frozen=True)
class CockpitSnapshot:
    """Single refresh payload for the operator cockpit."""

    projects: list[ProjectListItem]
    dashboard: DashboardSummary | None
    review: ReviewWorkspace | None
    validation: ValidationWorkspace | None
    artifacts: list[dict[str, object]]
    checkpoints: list[dict[str, str]]
    providers: list[dict[str, object]]
    audit_events: list[AuditEvent]
    comments: list[OperatorComment]
    matrix_rows: list[dict[str, object]]
    graph_rows: list[dict[str, object]]
    command_suggestions: list[dict[str, object]]
    command_options: CommandOptions


@dataclass(frozen=True)
class CommandOptions:
    """Selectable IDs used by command palette and contextual forms."""

    project_ids: list[str] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)
    artifact_ids: list[str] = field(default_factory=list)
    scene_ids: list[str] = field(default_factory=list)
    validator_ids: list[str] = field(default_factory=list)
    provider_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CommandValidation:
    """Live validation result for one command palette value."""

    status: str
    message: str
    completion: str = ""


@dataclass(frozen=True)
class TargetSelection:
    """Selected cockpit object used for contextual inspection and comments."""

    target_type: str
    target_id: str
    phase: str = ""
    source: str = ""
    detail: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReaderView:
    """Readable artifact or scene view for the cockpit."""

    title: str
    subtitle: str
    outline: list[str]
    body: str
    metadata: dict[str, object]
    linked_comments: list[OperatorComment]
    linked_validation: list[dict[str, Any]]


@dataclass(frozen=True)
class MatrixImpact:
    """Impact summary for a selected smart-matrix row."""

    target_id: str
    target_type: str
    phase: str
    summary: str
    linked_comments: list[OperatorComment]
    linked_validation: list[dict[str, Any]]
    suggested_actions: list[str]


@dataclass(frozen=True)
class ValidationGroup:
    """Grouped validator failures for operator triage."""

    validator_id: str
    severity: str
    count: int
    targets: list[str]
    message: str
    suggested_action: str


@dataclass(frozen=True)
class ValidationFixSuggestion:
    """Actionable fix row derived from one validation issue."""

    target_id: str
    target_type: str
    severity: str
    validator_id: str
    message: str
    command: str
    rationale: str


@dataclass(frozen=True)
class PhaseDetail:
    """Drill-down view for one pipeline graph phase."""

    phase: str
    status: str
    summary: str
    artifacts: list[dict[str, object]]
    blockers: list[str]
    suggested_commands: list[str]


@dataclass(frozen=True)
class ReviewIssueTarget:
    """Review issue with inferred navigation target."""

    issue_id: str
    severity: str
    target_id: str
    target_type: str
    message: str
    command: str


def build_dashboard_kpi_rows(
    dashboard: DashboardSummary | None,
    validation: ValidationWorkspace | None,
    providers: list[dict[str, object]],
    comments: list[OperatorComment],
) -> list[dict[str, object]]:
    """Build compact dashboard KPI rows for cockpit scanning."""
    if dashboard is None:
        return []
    degraded = [
        provider
        for provider in providers
        if str(provider.get("status", "")).lower() not in {"healthy", "ok", ""}
    ]
    blocking = len(validation.blocking_issues) if validation else 0
    warnings = len(validation.non_blocking_issues) if validation else 0
    open_comments = len([comment for comment in comments if not comment.resolved])
    return [
        {
            "metric": "phase",
            "value": dashboard.current_phase or "none",
            "state": dashboard.status,
            "command": f"phase {dashboard.current_phase}"
            if dashboard.current_phase
            else "open graph",
        },
        {
            "metric": "blockers",
            "value": blocking,
            "state": "blocked" if blocking else "clear",
            "command": "show blocked" if blocking else "open review",
        },
        {
            "metric": "warnings",
            "value": warnings,
            "state": "warning" if warnings else "clear",
            "command": "validation warning" if warnings else "open validation",
        },
        {
            "metric": "providers",
            "value": f"{len(providers) - len(degraded)}/{len(providers)}",
            "state": "degraded" if degraded else "healthy",
            "command": "providers",
        },
        {
            "metric": "comments",
            "value": open_comments,
            "state": "open" if open_comments else "empty",
            "command": "open review",
        },
    ]


def build_dashboard_action_rows(
    dashboard: DashboardSummary | None,
    review: ReviewWorkspace | None,
    validation: ValidationWorkspace | None,
) -> list[dict[str, object]]:
    """Build dashboard action ladder rows with concrete commands."""
    if dashboard is None:
        return []
    rows: list[dict[str, object]] = [
        {
            "priority": 1,
            "action": dashboard.next_action or "inspect",
            "status": dashboard.status,
            "reason": dashboard.route_reason or "No route reason recorded.",
            "command": "next",
        }
    ]
    if validation and validation.blocking_issues:
        first = validation.blocking_issues[0]
        target = _issue_focus_target(first) or _issue_target(first)
        rows.append(
            {
                "priority": 2,
                "action": "resolve validation blocker",
                "status": "blocked",
                "reason": str(first.get("message", "")),
                "command": f"fix {target}" if target else "show blocked",
            }
        )
    if review and "request_revision" in review.available_actions:
        rows.append(
            {
                "priority": 3,
                "action": "request revision",
                "status": "available",
                "reason": review.recommendation,
                "command": "open review",
            }
        )
    if "approve_phase" in dashboard.eligible_actions:
        rows.append(
            {
                "priority": 4,
                "action": "approve phase",
                "status": "available",
                "reason": "Current phase is eligible for approval.",
                "command": "approve",
            }
        )
    return rows


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
        if phase == current:
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
        if "request_revision" in dashboard.eligible_actions:
            commands.append("revise <note>")
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


def build_command_suggestions(
    *,
    dashboard: DashboardSummary | None,
    validation: ValidationWorkspace | None,
    artifacts: list[dict[str, object]],
    matrix_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Generate command rows that are valid for the current cockpit snapshot."""
    rows: list[dict[str, object]] = [
        {
            "command": "open graph",
            "scope": "navigation",
            "reason": "show pipeline position",
        },
        {
            "command": "open review",
            "scope": "navigation",
            "reason": "inspect approval workspace",
        },
        {
            "command": "matrix blocking",
            "scope": "matrix",
            "reason": "filter production matrix to blockers",
        },
    ]
    if dashboard is not None:
        rows.append(
            {
                "command": f"phase {dashboard.current_phase}",
                "scope": "graph",
                "reason": "inspect current phase",
            }
        )
        if "approve_phase" in dashboard.eligible_actions:
            rows.append(
                {
                    "command": "approve",
                    "scope": "review",
                    "reason": "approve the current phase",
                }
            )
        if "request_revision" in dashboard.eligible_actions:
            rows.append(
                {
                    "command": "revise <note>",
                    "scope": "review",
                    "reason": "request changes for the selected target",
                }
            )
    for suggestion in build_validation_fix_suggestions(validation)[:5]:
        rows.append(
            {
                "command": suggestion.command,
                "scope": "validation",
                "reason": suggestion.rationale,
            }
        )
    for artifact in artifacts[:5]:
        artifact_id = str(artifact.get("artifact_id", ""))
        if artifact_id:
            rows.append(
                {
                    "command": f"artifact {artifact_id}",
                    "scope": "reader",
                    "reason": f"open {artifact_id}",
                }
            )
    for row in matrix_rows:
        target = str(row.get("target", ""))
        if _is_scene_id(target):
            rows.append(
                {
                    "command": f"scene {target}",
                    "scope": "reader",
                    "reason": str(row.get("validation", "open scene")),
                }
            )
    return _dedupe_command_rows(rows)


def build_command_help_rows(options: CommandOptions) -> list[dict[str, object]]:
    """Build operator-facing command reference rows with live selectable values."""
    return [
        {
            "command": "open <page>",
            "values": "dashboard, graph, matrix, review, scenes, assets, validation",
            "purpose": "jump between cockpit workspaces",
        },
        {
            "command": "artifact <artifact_id>",
            "values": _preview_values(options.artifact_ids),
            "purpose": "open a readable artifact with linked issues and comments",
        },
        {
            "command": "scene <scene_id>",
            "values": _preview_values(options.scene_ids),
            "purpose": "open a scene reader and make it the active comment target",
        },
        {
            "command": "phase <phase>",
            "values": _preview_values(options.phases),
            "purpose": "drill into graph position and phase blockers",
        },
        {
            "command": "validator <validator_id>",
            "values": _preview_values(options.validator_ids),
            "purpose": "filter validation issues by validator",
        },
        {
            "command": "matrix <query>",
            "values": "blocking, warning, candidate, status:<value>, phase:<value>",
            "purpose": "filter the smart matrix across scenes, artifacts, and issues",
        },
        {
            "command": "matrix pivot <field>",
            "values": "status, phase, kind, validation",
            "purpose": "regroup the matrix by the selected operating dimension",
        },
        {
            "command": "fix <target>",
            "values": _preview_values([*options.scene_ids, *options.artifact_ids]),
            "purpose": "prefill a targeted revision note from validation intelligence",
        },
        {
            "command": "comment <target> | <note>",
            "values": "target plus note",
            "purpose": "store a durable operator annotation on a scene, artifact, or phase",
        },
        {
            "command": "draft <target> | <note>",
            "values": "target plus note",
            "purpose": "prefill a targeted revision note without submitting it",
        },
        {
            "command": "create <project_id> | <title> | <idea>",
            "values": "three required fields",
            "purpose": "create a new film project with default runtime settings",
        },
    ]


def filter_command_suggestions(
    rows: list[dict[str, object]],
    prefix: str,
) -> list[dict[str, object]]:
    """Filter command suggestions using a forgiving prefix/search query."""
    query = prefix.strip().lower()
    if not query:
        return rows
    matches = [
        row
        for row in rows
        if query
        in " ".join(str(row.get(key, "")).lower() for key in ("command", "scope", "reason"))
    ]
    if matches or " " not in query:
        return matches
    head = query.split(maxsplit=1)[0]
    return [
        row
        for row in rows
        if str(row.get("command", "")).lower().startswith(head)
        or str(row.get("scope", "")).lower() == head
    ]


def build_command_validation(
    command: str,
    options: CommandOptions,
    suggestions: list[dict[str, object]],
) -> CommandValidation:
    """Validate a command palette value against live selectable IDs."""
    value = command.strip()
    normalized = value.lower()
    if not value:
        return CommandValidation(
            status="incomplete",
            message="Start typing a command or select a row from suggestions.",
            completion=_first_command(suggestions),
        )

    suggestion_match = _matching_suggestion(value, suggestions)
    if suggestion_match is not None and "<" not in suggestion_match:
        return CommandValidation(status="ready", message=f"Ready: {suggestion_match}")

    tab_aliases = {
        "dashboard",
        "open dashboard",
        "review",
        "open review",
        "graph",
        "open graph",
        "matrix",
        "open matrix",
        "validation",
        "providers",
        "assets",
        "artifacts",
        "scenes",
        "checkpoints",
        "audit",
        "next",
        "approve",
        "show blocked",
    }
    if normalized in tab_aliases:
        return CommandValidation(status="ready", message=f"Ready: {value}")
    if any(candidate.startswith(normalized) for candidate in tab_aliases):
        completion = next(
            candidate for candidate in sorted(tab_aliases) if candidate.startswith(normalized)
        )
        return CommandValidation(
            status="incomplete",
            message=f"Partial command. Complete to: {completion}",
            completion=completion,
        )

    if normalized == "create":
        template = "create <project_id> | <title> | <idea>"
        return CommandValidation(
            status="incomplete",
            message="Create requires project_id, title, and idea separated by |.",
            completion=template,
        )
    if normalized.startswith("create "):
        parts = [part.strip() for part in value.removeprefix("create ").split("|")]
        if len(parts) == 3 and all(parts) and not any(_is_placeholder(part) for part in parts):
            return CommandValidation(status="ready", message="Ready: create project")
        return CommandValidation(
            status="incomplete",
            message="Create needs exactly three non-empty fields separated by |.",
            completion="create <project_id> | <title> | <idea>",
        )

    target_commands = {
        "artifact": options.artifact_ids,
        "scene": options.scene_ids,
        "phase": options.phases,
        "validator": options.validator_ids,
    }
    for verb, valid_values in target_commands.items():
        if normalized == verb:
            return CommandValidation(
                status="incomplete",
                message=f"{verb} requires one of: {_preview_values(valid_values)}.",
                completion=f"{verb} {valid_values[0]}" if valid_values else "",
            )
        if normalized.startswith(f"{verb} "):
            target = value.split(maxsplit=1)[1].strip()
            return _validate_known_value(verb, target, valid_values)

    if normalized == "matrix":
        return CommandValidation(
            status="incomplete",
            message="Matrix requires a query or pivot field.",
            completion="matrix blocking",
        )
    if normalized.startswith("matrix pivot"):
        field_value = value.removeprefix("matrix pivot").strip()
        valid_pivots = ["status", "phase", "kind", "validation"]
        if not field_value:
            return CommandValidation(
                status="incomplete",
                message=f"matrix pivot requires one of: {_preview_values(valid_pivots)}.",
                completion="matrix pivot status",
            )
        return _validate_known_value("matrix pivot", field_value, valid_pivots)
    if normalized.startswith("matrix "):
        return CommandValidation(status="ready", message=f"Ready: filter {value}")

    pipe_commands = {"comment", "draft"}
    for verb in pipe_commands:
        if normalized == verb:
            return CommandValidation(
                status="incomplete",
                message=f"{verb} requires '<target> | <note>'.",
                completion=f"{verb} <target> | <note>",
            )
        if normalized.startswith(f"{verb} "):
            payload = value.split(maxsplit=1)[1]
            parts = [part.strip() for part in payload.split("|")]
            if len(parts) == 2 and all(parts) and not any(_is_placeholder(part) for part in parts):
                return CommandValidation(status="ready", message=f"Ready: {verb}")
            return CommandValidation(
                status="incomplete",
                message=f"{verb} needs a target and note separated by |.",
                completion=f"{verb} <target> | <note>",
            )

    argument_commands = (
        "review issue",
        "thread",
        "reader",
        "link",
        "fix",
        "open",
        "dashboard",
        "validation",
        "revise",
    )
    for verb in argument_commands:
        if normalized == verb:
            return CommandValidation(
                status="incomplete",
                message=f"{verb} needs an argument.",
            )
        if normalized.startswith(f"{verb} "):
            return CommandValidation(status="ready", message=f"Ready: {verb}")

    completion = _first_prefix_match(value, suggestions)
    if completion:
        return CommandValidation(
            status="incomplete",
            message=f"Unknown partial command. Closest match: {completion}",
            completion=completion,
        )
    return CommandValidation(
        status="unknown",
        message=f"Unknown command '{value}'. Select a suggestion or type 'commands'.",
    )


def complete_command_prefix(
    command: str,
    suggestions: list[dict[str, object]],
) -> str:
    """Return the first concrete suggestion matching a command prefix."""
    return _first_prefix_match(command, suggestions)


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


def build_scene_rows(matrix_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Extract scene-oriented rows from the smart matrix."""
    scene_rows: list[dict[str, object]] = []
    for row in matrix_rows:
        target = str(row.get("target", ""))
        kind = str(row.get("kind", ""))
        if _is_scene_id(target) or kind in {"scene", "scene_script", "scene_issue"}:
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


def build_command_options(
    *,
    projects: list[ProjectListItem],
    dashboard: DashboardSummary | None,
    validation: ValidationWorkspace | None,
    artifacts: list[dict[str, object]],
    providers: list[dict[str, object]],
) -> CommandOptions:
    """Collect selectable IDs from the current project state."""
    project_ids = sorted({project.project_id for project in projects})
    phases = sorted(
        {
            phase
            for phase in [
                *(str(artifact.get("phase", "")) for artifact in artifacts),
                dashboard.current_phase if dashboard else "",
                validation.phase if validation else "",
            ]
            if phase
        }
    )
    artifact_ids = sorted(
        {
            str(artifact.get("artifact_id", ""))
            for artifact in artifacts
            if str(artifact.get("artifact_id", ""))
        }
    )
    validator_ids = sorted(
        {
            str(report.get("validator_id", issue.get("validator_id", "")))
            for report in (validation.reports if validation else [])
            for issue in [report]
            if str(report.get("validator_id", issue.get("validator_id", "")))
        }
        | {
            str(issue.get("validator_id", ""))
            for issue in _all_issues(validation)
            if str(issue.get("validator_id", ""))
        }
    )
    scene_ids = sorted(
        {
            value
            for issue in _all_issues(validation)
            for value in [
                str(issue.get("scene_id", "")),
                str(issue.get("affected_entity", "")),
                str(issue.get("target", "")),
            ]
            if _is_scene_id(value)
        }
    )
    provider_ids = sorted(
        {
            str(provider.get("provider_id", ""))
            for provider in providers
            if str(provider.get("provider_id", ""))
        }
    )
    return CommandOptions(
        project_ids=project_ids,
        phases=phases,
        artifact_ids=artifact_ids,
        scene_ids=scene_ids,
        validator_ids=validator_ids,
        provider_ids=provider_ids,
    )


def summarize_attention(
    dashboard: DashboardSummary | None,
    validation: ValidationWorkspace | None,
    providers: list[dict[str, object]],
) -> list[str]:
    """Return dense attention lines for the dashboard."""
    lines: list[str] = []
    if dashboard is None:
        return ["No active project. Create or select a project."]
    if dashboard.has_blockers:
        lines.append(f"BLOCKED: {dashboard.issue_count} issue(s) need operator attention.")
    if dashboard.status == "awaiting_review":
        lines.append(f"REVIEW: {dashboard.current_phase} is waiting for approval or revision.")
    if validation and validation.blocking_issues:
        first = validation.blocking_issues[0]
        lines.append(f"VALIDATION: {first.get('message', 'blocking issue')}")
    degraded = [
        str(provider.get("provider_id", "provider"))
        for provider in providers
        if str(provider.get("status", "")).lower() not in {"", "healthy", "ok"}
    ]
    if degraded:
        lines.append(f"PROVIDERS: {len(degraded)} degraded ({', '.join(degraded[:3])}).")
    if not lines:
        lines.append("No blocking attention items.")
    return lines


def _all_issues(validation: ValidationWorkspace | None) -> list[dict[str, Any]]:
    if validation is None:
        return []
    return [*validation.blocking_issues, *validation.non_blocking_issues]


def _issues_by_target(issues: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        target = _issue_target(issue)
        if target:
            grouped.setdefault(target, []).append(issue)
    return grouped


def _phase_blockers(
    phase: str,
    dashboard: DashboardSummary | None,
    validation: ValidationWorkspace | None,
) -> list[str]:
    blockers: list[str] = []
    if dashboard and phase == dashboard.current_phase:
        blockers.extend(
            f"{item.get('action', 'action')}: {item.get('reason', 'blocked')}"
            for item in dashboard.blocked_actions
        )
    if validation and validation.phase == phase:
        blockers.extend(str(issue.get("message", "")) for issue in validation.blocking_issues)
    return [blocker for blocker in blockers if blocker]


def _dedupe_command_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    unique: list[dict[str, object]] = []
    for row in rows:
        command = str(row.get("command", ""))
        if not command or command in seen:
            continue
        seen.add(command)
        unique.append(row)
    return unique


def _dedupe_review_issues(rows: list[ReviewIssueTarget]) -> list[ReviewIssueTarget]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[ReviewIssueTarget] = []
    for row in rows:
        key = (row.target_id, row.severity, row.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _issue_target(issue: dict[str, Any]) -> str:
    for key in ("artifact_id", "target", "affected_entity", "scene_id", "asset_id"):
        value = str(issue.get(key, ""))
        if value:
            return value
    return ""


def _issue_focus_target(issue: dict[str, Any]) -> str:
    scene_id = str(issue.get("scene_id", ""))
    if scene_id:
        return scene_id
    return _issue_target(issue)


def _target_from_text(text: str) -> str:
    match = re.search(r"\b(?:SC_[A-Za-z0-9_-]+|s_[A-Za-z0-9_-]+|scene_[0-9]+)\b", text)
    if match:
        return match.group(0)
    return ""


def _open_command(target_type: str, target_id: str) -> str:
    if not target_id:
        return "open review"
    if target_type == "scene":
        return f"scene {target_id}"
    if target_type == "artifact":
        return f"artifact {target_id}"
    return f"open {target_id}"


def _target_type_for_issue(issue: dict[str, Any], target_id: str) -> str:
    if str(issue.get("scene_id", "")) or _is_scene_id(target_id):
        return "scene"
    if str(issue.get("artifact_id", "")) or str(issue.get("target", "")):
        return "artifact"
    if str(issue.get("asset_id", "")):
        return "asset"
    return "validation_issue"


def _severity_rank(severity: str) -> int:
    return {"blocking": 0, "error": 1, "warning": 2, "info": 3}.get(severity.lower(), 4)


def _validator_action(severity: str, targets: list[str]) -> str:
    if not targets:
        return "inspect validator report"
    first = targets[0]
    if severity.lower() == "blocking":
        return f"fix {first}"
    return f"review {first}"


def _issue_label(issues: list[dict[str, Any]]) -> str:
    if not issues:
        return "passing/unknown"
    blocking = [issue for issue in issues if issue.get("severity") == "blocking"]
    if blocking:
        return f"blocking: {blocking[0].get('message', '')}"
    return f"warning: {issues[0].get('message', '')}"


def _validation_bucket(value: str) -> str:
    normalized = value.lower()
    if "blocking" in normalized or "failed" in normalized:
        return "blocking"
    if "warning" in normalized or "warn" in normalized:
        return "warning"
    if "passing" in normalized:
        return "passing"
    return "unknown"


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _row_matches_token(row: dict[str, object], token: str) -> bool:
    if token in {"failed", "fail", "blocked", "blocking"}:
        haystack = _row_text(row)
        return "blocking" in haystack or "failed" in haystack or "block" in haystack
    if token in {"warn", "warning", "warnings"}:
        return "warning" in _row_text(row)
    if token in {"candidate", "approved"}:
        return str(row.get("status", "")).lower() == token
    if ":" in token:
        key, expected = token.split(":", maxsplit=1)
        field = {
            "scene": "target",
            "target": "target",
            "kind": "kind",
            "type": "kind",
            "phase": "phase",
            "status": "status",
            "validator": "validation",
        }.get(key)
        if field is None:
            return expected in _row_text(row)
        return expected in str(row.get(field, "")).lower()
    return token in _row_text(row)


def _row_text(row: dict[str, object]) -> str:
    return " ".join(str(value).lower() for value in row.values())


def _is_scene_id(value: str) -> bool:
    return bool(re.match(r"^(SC_|s_)[A-Za-z0-9_-]+$", value) or re.match(r"^scene_[0-9]+$", value))


def _artifact_outline(body: dict[str, Any]) -> list[str]:
    if isinstance(body.get("scenes"), list):
        return [
            f"{scene.get('scene_id', '?')}: "
            f"{scene.get('scene_heading', scene.get('dramatic_function', ''))}"
            for scene in body["scenes"]
            if isinstance(scene, dict)
        ]
    if isinstance(body.get("scene_list"), dict) and isinstance(
        body["scene_list"].get("scenes"), list
    ):
        return [
            f"{scene.get('scene_id', '?')}: {scene.get('dramatic_function', '')}"
            for scene in body["scene_list"]["scenes"]
            if isinstance(scene, dict)
        ]
    return [str(key) for key in body]


def _render_artifact_body(body: dict[str, Any]) -> str:
    if isinstance(body.get("text"), str):
        return str(body["text"])
    if isinstance(body.get("treatment"), dict) and isinstance(body["treatment"].get("text"), str):
        return str(body["treatment"]["text"])
    if isinstance(body.get("scenes"), list):
        scenes = [scene for scene in body["scenes"] if isinstance(scene, dict)]
        return "\n\n".join(_render_scene(scene) for scene in scenes)
    return _compact_dict(body)


def _find_scene(body: dict[str, Any], scene_id: str) -> dict[str, Any] | None:
    for scene in _artifact_scenes(body):
        if str(scene.get("scene_id", "")) == scene_id:
            return scene
    return None


def _artifact_scenes(body: dict[str, Any]) -> list[dict[str, Any]]:
    scene_list = body.get("scene_list", {})
    nested_scenes = scene_list.get("scenes", []) if isinstance(scene_list, dict) else []
    scenes: list[dict[str, Any]] = []
    for container in (body.get("scenes"), nested_scenes):
        if isinstance(container, list):
            scenes.extend(scene for scene in container if isinstance(scene, dict))
    return scenes


def _scene_outline(scene: dict[str, Any]) -> list[str]:
    outline = [str(scene.get("scene_id", "scene"))]
    for key in ("scene_heading", "dramatic_function", "emotional_shift", "conflict", "outcome"):
        if scene.get(key):
            outline.append(f"{key}: {scene[key]}")
    return outline


def _render_scene(scene: dict[str, Any]) -> str:
    if "scene_heading" not in scene:
        return _compact_dict(scene)
    lines = [str(scene.get("scene_heading", ""))]
    for action in scene.get("action_lines", []):
        lines.append(str(action))
    for dialogue in scene.get("dialogue", []):
        if not isinstance(dialogue, dict):
            continue
        character = str(dialogue.get("character_id", "")).upper()
        direction = str(dialogue.get("direction", ""))
        line = str(dialogue.get("line", ""))
        lines.append("")
        lines.append(character)
        if direction:
            lines.append(f"({direction})")
        lines.append(line)
    return "\n".join(line for line in lines if line != "")


def _comments_for_target(
    comments: list[OperatorComment],
    target_id: str,
    artifact_id: str,
) -> list[OperatorComment]:
    return [
        comment
        for comment in comments
        if comment.target_id in {target_id, artifact_id}
        or (comment.target_type == "artifact" and comment.target_id == artifact_id)
    ]


def _validation_for_target(
    validation: ValidationWorkspace | None,
    target_id: str,
    artifact_id: str,
) -> list[dict[str, Any]]:
    issues = _all_issues(validation)
    return [
        issue
        for issue in issues
        if _issue_target(issue) in {target_id, artifact_id}
        or str(issue.get("scene_id", "")) == target_id
    ]


def _compact_dict(value: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, item in value.items():
        if isinstance(item, (str, int, float, bool)):
            lines.append(f"{key}: {item}")
        elif isinstance(item, list):
            lines.append(f"{key}: {len(item)} item(s)")
        elif isinstance(item, dict):
            lines.append(f"{key}: {len(item)} field(s)")
        else:
            lines.append(f"{key}: {item}")
    return "\n".join(lines)


def _preview_values(values: list[str], limit: int = 6) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return "none available"
    visible = cleaned[:limit]
    suffix = f" +{len(cleaned) - limit} more" if len(cleaned) > limit else ""
    return ", ".join(visible) + suffix


def _first_command(rows: list[dict[str, object]]) -> str:
    for row in rows:
        command = str(row.get("command", ""))
        if command:
            return command
    return ""


def _matching_suggestion(command: str, rows: list[dict[str, object]]) -> str | None:
    normalized = command.strip().lower()
    for row in rows:
        candidate = str(row.get("command", ""))
        if candidate.lower() == normalized:
            return candidate
    return None


def _first_prefix_match(prefix: str, rows: list[dict[str, object]]) -> str:
    normalized = prefix.strip().lower()
    if not normalized:
        return _first_command(rows)
    for row in rows:
        candidate = str(row.get("command", ""))
        if candidate.lower().startswith(normalized) and "<" not in candidate:
            return candidate
    return ""


def _validate_known_value(
    label: str,
    value: str,
    valid_values: list[str],
) -> CommandValidation:
    if value in valid_values:
        return CommandValidation(status="ready", message=f"Ready: {label} {value}")
    prefix_match = next(
        (candidate for candidate in valid_values if candidate.lower().startswith(value.lower())),
        "",
    )
    if prefix_match:
        return CommandValidation(
            status="incomplete",
            message=f"Partial {label}. Complete to: {prefix_match}",
            completion=f"{label} {prefix_match}",
        )
    return CommandValidation(
        status="unknown",
        message=f"Unknown {label} '{value}'. Try: {_preview_values(valid_values)}.",
    )


def _is_placeholder(value: str) -> bool:
    stripped = value.strip()
    return stripped.startswith("<") and stripped.endswith(">")
