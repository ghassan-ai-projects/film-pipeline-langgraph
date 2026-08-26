"""Translations between MCP tool payloads and TUI view models.

Pure mapping helpers: no RPC, no subprocess state. The stdio gateway
composes these with transport calls, so each translation can be exercised
without a running MCP server.
"""

from __future__ import annotations

from typing import Any

from film_pipeline.app.services.models import (
    ArtifactDetail,
    AuditEvent,
    DashboardSummary,
    GenerationWorkspace,
    MutationResult,
    OperatorComment,
    ProjectCreateRequest,
    ProjectListItem,
    ReviewWorkspace,
    ValidationWorkspace,
)


def project_create_arguments(request: ProjectCreateRequest) -> dict[str, object]:
    """Encode a create request as ``create_film_project`` tool arguments."""
    args: dict[str, object] = {
        "project_id": request.project_id,
        "title": request.title,
    }
    if request.slug:
        args["slug"] = request.slug
    if request.idea:
        args["idea"] = request.idea
    if request.runtime_mode:
        args["runtime_mode"] = request.runtime_mode
    if request.target_runtime_seconds:
        args["target_runtime_seconds"] = request.target_runtime_seconds
    if request.film_type_profile:
        args["film_type_profile"] = request.film_type_profile
    if request.quality_profile:
        args["quality_profile"] = request.quality_profile
    if request.provider_profile:
        args["provider_profile"] = request.provider_profile
    if request.review_profile:
        args["review_profile"] = request.review_profile
    if request.auto_approve_profile:
        args["auto_approve_profile"] = request.auto_approve_profile
    if request.generation_policy:
        args["generation_policy"] = request.generation_policy
    return args


def project_list_item_from_summary(project_id: str, summary: dict[str, Any]) -> ProjectListItem:
    """Translate one project summary response into a project rail entry."""
    current_phase = str(summary.get("current_phase", ""))
    status = str(summary.get("status", ""))
    if not status:
        status = "in_progress" if current_phase else "created"
    return ProjectListItem(
        project_id=project_id,
        title=str(summary.get("title", project_id)),
        slug=str(summary.get("slug", project_id)),
        current_phase=current_phase,
        status=status,
        has_blockers=bool(summary.get("has_blockers")),
        awaiting_review=status == "awaiting_review",
    )


def mutation_result_from_response(
    response: dict[str, Any],
    *,
    fallback_project_id: str,
    success_message: str,
) -> MutationResult:
    """Translate an ok/error tool response into a mutation result."""
    return MutationResult(
        ok=bool(response.get("ok")),
        project_id=str(response.get("project_id", fallback_project_id)),
        current_phase=str(response.get("current_phase", "")),
        message=success_message if response.get("ok") else str(response.get("error", "")),
    )


def dashboard_summary_from_response(response: dict[str, Any]) -> DashboardSummary:
    """Translate a project summary response into the dashboard view model."""
    return DashboardSummary(
        project_id=str(response.get("project_id", "")),
        title=str(response.get("title", "")),
        slug=str(response.get("slug", "")),
        current_phase=str(response.get("current_phase", "")),
        runtime_mode=str(response.get("runtime_mode", "mock")),
        workflow_mode="manual",
        status=str(response.get("status", "")),
        next_action="",
        route_reason="",
        issue_count=int(response.get("issue_count", 0)),
        artifact_count=int(response.get("artifact_count", 0)),
        checkpoint_count=int(response.get("checkpoint_count", 0)),
        has_blockers=bool(response.get("has_blockers")),
        generation_policy=str(response.get("generation_policy", "generate")),
    )


def review_workspace_from_response(response: dict[str, Any]) -> ReviewWorkspace:
    """Translate a review-phase-artifacts response into the review workspace."""
    artifacts = response.get("artifacts", [])
    return ReviewWorkspace(
        project_id=str(response.get("project_id", "")),
        phase=str(response.get("phase", "")),
        recommendation="Review the phase outputs and approve or request revision.",
        candidate_artifacts=list(artifacts) if isinstance(artifacts, list) else [],
    )


def validation_workspace_from_response(response: dict[str, Any]) -> ValidationWorkspace:
    """Translate a validation-report response into the validation workspace."""
    reports = response.get("reports", [])
    return ValidationWorkspace(
        project_id=str(response.get("project_id", "")),
        phase=str(response.get("phase", "")),
        source=str(response.get("source", "")),
        reports=list(reports) if isinstance(reports, list) else [],
    )


def text_only_generation_workspace(
    project_id: str | None,
    assets: list[dict[str, object]],
) -> GenerationWorkspace:
    """Build the generation workspace for a text-only policy project.

    Text-only projects have no provider rows; the batch is complete once the
    text-only delivery asset is recorded in the manifest.
    """
    completed = any(str(asset.get("kind", "")).lower() == "text_only_delivery" for asset in assets)
    return GenerationWorkspace(
        project_id=project_id or "",
        phase="generation",
        provider="",
        model="",
        estimated_cost_usd=0.0,
        rows=[],
        planned=0,
        submitted=0,
        running=0,
        completed=1 if completed else 0,
        failed=0,
        next_step="approve_phase" if completed else "plan",
    )


def generation_workspace_from_rows(
    project_id: str | None,
    rows_raw: object,
) -> GenerationWorkspace:
    """Build the generation workspace from raw active-generation rows."""
    rows = [dict(row) for row in rows_raw] if isinstance(rows_raw, list) else []
    running = sum(1 for row in rows if row.get("status") == "running")
    return GenerationWorkspace(
        project_id=project_id or "",
        phase="generation",
        provider="",
        model="",
        estimated_cost_usd=0.0,
        rows=rows,
        running=running,
        next_step="poll" if running else "plan",
    )


def artifact_detail_from_response(
    artifact_id: str,
    phase: str,
    version: int,
    response: dict[str, Any],
) -> ArtifactDetail:
    """Translate an inspect-artifact response into the detail view model."""
    content = response.get("content", {})
    return ArtifactDetail(
        artifact_id=artifact_id,
        artifact_type=str(response.get("artifact_type", artifact_id)),
        phase=phase,
        version=version,
        status=str(response.get("status", "candidate")),
        body=dict(content) if isinstance(content, dict) else {},
    )


def operator_comment_from_entry(
    comment: dict[str, Any],
    fallback_project_id: str | None,
) -> OperatorComment:
    """Translate one stored-comment entry into the comment view model."""
    return OperatorComment(
        comment_id=str(comment.get("comment_id", "")),
        project_id=str(comment.get("project_id", fallback_project_id or "")),
        target_type=str(comment.get("target_type", "")),
        target_id=str(comment.get("target_id", "")),
        body=str(comment.get("body", "")),
        phase=str(comment.get("phase", "")),
        source=str(comment.get("source", "")),
        created_at=str(comment.get("created_at", "")),
    )


def audit_event_from_entry(entry: dict[str, Any]) -> AuditEvent:
    """Translate one audit-log entry into the audit feed view model."""
    details = entry.get("details", {})
    if not isinstance(details, dict):  # pragma: no cover
        details = {}
    return AuditEvent(
        timestamp=str(entry.get("timestamp", "")),
        actor=str(entry.get("actor", "")),
        action=str(entry.get("action", "")),
        target=str(details.get("project_id", "")),
        summary=(f"{entry.get('action', '')} {details.get('project_id', '')}").strip(),
    )
