"""Dashboard KPI and action row builders for the operator cockpit."""

from __future__ import annotations

from film_pipeline.app.services.models import (
    DashboardSummary,
    OperatorComment,
    ReviewWorkspace,
    ValidationWorkspace,
)
from film_pipeline.tui.view_models.helpers import _issue_focus_target, _issue_target


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
    if dashboard.stalled_phase:
        rows.append(
            {
                "priority": 1,
                "action": "escalate stalled phase",
                "status": "stalled",
                "reason": f"{dashboard.stalled_phase} needs human intervention.",
                "command": f"phase {dashboard.stalled_phase}",
            }
        )
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
    if dashboard.stalled_phase:
        lines.append(f"STALLED: {dashboard.stalled_phase} requires human intervention.")
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
