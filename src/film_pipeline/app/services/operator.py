"""Operator-facing application service.

This service is intentionally thin. It owns use-case sequencing and view-model
mapping while keeping durable state changes inside ``StudioRuntime`` and graph
helpers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from film_pipeline.app.runtime import StudioRuntime, get_runtime
from film_pipeline.app.services.errors import BackendOperationError, ProjectNotFoundError
from film_pipeline.app.services.models import (
    ArtifactDetail,
    AuditEvent,
    DashboardSummary,
    MutationResult,
    OperatorComment,
    OperatorCommentRequest,
    ProjectCreateRequest,
    ProjectListItem,
    ReviewWorkspace,
    ValidationWorkspace,
)
from film_pipeline.graph import orchestrator_state as ostate
from film_pipeline.graph.router import compute_actions
from film_pipeline.schemas._base import FilmPhase


class OperatorService:
    """Shared service for TUI and future thin MCP adapters."""

    def __init__(self, runtime: StudioRuntime | None = None) -> None:
        self._runtime = runtime

    @property
    def runtime(self) -> StudioRuntime:
        """Return the configured runtime, resolving the singleton lazily."""
        return self._runtime if self._runtime is not None else get_runtime()

    def list_projects(self) -> list[ProjectListItem]:
        """List all known projects with operator status fields."""
        items: list[ProjectListItem] = []
        for project_id, state in sorted(self.runtime.projects.items()):
            phase = str(state.get("current_phase", ""))
            has_blockers = self._has_blockers(state)
            items.append(
                ProjectListItem(
                    project_id=project_id,
                    title=str(state.get("title") or project_id),
                    slug=str(state.get("slug", project_id)),
                    current_phase=phase,
                    status=self._status_for_state(state),
                    has_blockers=has_blockers,
                    awaiting_review=bool(state.get("human_approval_required")),
                )
            )
        return items

    def create_project(self, request: ProjectCreateRequest) -> MutationResult:
        """Create a project, set it active, and optionally submit the idea."""
        if not request.project_id.strip():
            raise BackendOperationError("project_id is required.")
        if not request.title.strip():
            raise BackendOperationError("title is required.")

        state = self.runtime.create_project(
            project_id=request.project_id.strip(),
            title=request.title.strip(),
            slug=request.slug.strip() or request.project_id.strip(),
        )
        state["runtime_mode"] = request.runtime_mode
        state["workflow_mode"] = request.workflow_mode
        self.runtime.set_active(request.project_id.strip())

        if request.idea.strip():
            state["idea"] = request.idea.strip()
            state = self.runtime.run_graph(state)
            self.runtime.projects[request.project_id.strip()] = state

        return MutationResult(
            ok=True,
            project_id=str(state["project_id"]),
            current_phase=str(state.get("current_phase", "")),
            message="Project created.",
        )

    def set_active_project(self, project_id: str) -> DashboardSummary:
        """Select an active project and return its dashboard."""
        self._require_project(project_id)
        self.runtime.set_active(project_id)
        return self.get_dashboard(project_id)

    def submit_idea(self, project_id: str, idea: str) -> MutationResult:
        """Attach an idea to a project and run intake."""
        if not idea.strip():
            raise BackendOperationError("idea is required.")
        state = self._require_project(project_id)
        self.runtime.set_active(project_id)
        state["idea"] = idea.strip()
        next_state = self.runtime.run_graph(state)
        self.runtime.projects[project_id] = next_state
        return MutationResult(
            ok=True,
            project_id=project_id,
            current_phase=str(next_state.get("current_phase", "")),
            message="Idea submitted.",
        )

    def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
        """Return the current dashboard summary."""
        state = self._state_for_project(project_id)
        ostate.ensure_orchestrator_state(state)
        router_result = compute_actions(state)
        latest_decision = ostate.get_latest_routing_decision(state)
        project_id_value = str(state["project_id"])
        checkpoint_count = len(self.runtime.list_checkpoints(project_id_value))
        return DashboardSummary(
            project_id=project_id_value,
            title=str(state.get("title") or project_id_value),
            slug=str(state.get("slug", project_id_value)),
            current_phase=str(state.get("current_phase", "")),
            runtime_mode=str(state.get("runtime_mode", state.get("server_mode", ""))),
            workflow_mode=str(state.get("workflow_mode", "manual")),
            status=self._status_for_state(state),
            next_action=router_result.next_action,
            route_reason=str(latest_decision.get("reason", "")) if latest_decision else "",
            eligible_actions=list(router_result.eligible),
            blocked_actions=list(router_result.blocked),
            pending_revisions=list(ostate.get_pending_revisions(state)),
            candidate_refs=dict(ostate.get_candidate_refs(state)),
            approved_refs=dict(ostate.get_approved_refs(state)),
            budget_snapshot=dict(ostate.get_budget_snapshot(state)),
            provider_blocked=list(ostate.get_blocked_providers(state)),
            issue_count=len(cast(list[Any], state.get("issues", []))),
            artifact_count=len(self.list_artifacts(project_id_value)),
            checkpoint_count=checkpoint_count,
            has_blockers=self._has_blockers(state),
        )

    def get_review_workspace(self, project_id: str | None = None) -> ReviewWorkspace:
        """Return review context for the active phase."""
        state = self._state_for_project(project_id)
        phase = str(state.get("current_phase", ""))
        if not phase:
            return ReviewWorkspace(
                project_id=str(state["project_id"]),
                phase="",
                recommendation="Submit an idea to start intake.",
            )

        router_result = compute_actions(state)
        artifacts = self.list_artifacts(str(state["project_id"]), phase=phase)
        blocking_issues = [
            str(issue.get("message", issue))
            for issue in cast(list[Mapping[str, Any]], state.get("issues", []))
            if issue.get("severity") == "blocking"
        ]
        recommendation = self._recommendation(router_result.next_action, phase)
        return ReviewWorkspace(
            project_id=str(state["project_id"]),
            phase=phase,
            recommendation=recommendation,
            candidate_artifacts=list(artifacts),
            open_issues=blocking_issues,
            available_actions=list(router_result.eligible),
            blocked_actions=list(router_result.blocked),
        )

    def get_validation_workspace(self, project_id: str | None = None) -> ValidationWorkspace:
        """Return stored validation reports and current validation issues."""
        state = self._state_for_project(project_id)
        reports = state.get("_validation_reports", [])
        report_list = list(reports) if isinstance(reports, list) else []
        issue_list = [
            issue
            for issue in cast(list[Mapping[str, Any]], state.get("issues", []))
            if isinstance(issue, dict)
        ]
        blocking = [dict(issue) for issue in issue_list if issue.get("severity") == "blocking"]
        non_blocking = [dict(issue) for issue in issue_list if issue.get("severity") != "blocking"]
        return ValidationWorkspace(
            project_id=str(state["project_id"]),
            phase=str(state.get("current_phase", "")),
            source="stored_state" if report_list else "none",
            reports=[cast(dict[str, Any], report) for report in report_list],
            blocking_issues=blocking,
            non_blocking_issues=non_blocking,
        )

    def approve_phase(self, project_id: str | None = None) -> MutationResult:
        """Approve the active phase through the runtime approval gate."""
        state = self._state_for_project(project_id)
        self.runtime.set_active(str(state["project_id"]))
        next_state = self.runtime.approve_phase()
        return MutationResult(
            ok=True,
            project_id=str(next_state["project_id"]),
            current_phase=str(next_state.get("current_phase", "")),
            message="Phase approved.",
        )

    def request_revision(self, note: str, project_id: str | None = None) -> MutationResult:
        """Request revision for the active phase."""
        if not note.strip():
            raise BackendOperationError("revision note is required.")
        state = self._state_for_project(project_id)
        self.runtime.set_active(str(state["project_id"]))
        next_state = self.runtime.request_revision(note=note.strip())
        return MutationResult(
            ok=True,
            project_id=str(next_state["project_id"]),
            current_phase=str(next_state.get("current_phase", "")),
            message="Revision requested.",
        )

    def add_operator_comment(
        self,
        request: OperatorCommentRequest,
        project_id: str | None = None,
    ) -> OperatorComment:
        """Persist a target-scoped operator comment."""
        if not request.body.strip():
            raise BackendOperationError("comment body is required.")
        if not request.target_type.strip():
            raise BackendOperationError("comment target_type is required.")
        if not request.target_id.strip():
            raise BackendOperationError("comment target_id is required.")
        state = self._state_for_project(project_id)
        raw = self.runtime.add_operator_comment(
            str(state["project_id"]),
            target_type=request.target_type.strip(),
            target_id=request.target_id.strip(),
            body=request.body.strip(),
            phase=request.phase.strip(),
            source=request.source.strip() or "tui",
        )
        return self._comment_from_raw(raw)

    def list_operator_comments(
        self,
        project_id: str | None = None,
        *,
        include_resolved: bool = False,
    ) -> list[OperatorComment]:
        """List target-scoped operator comments."""
        state = self._state_for_project(project_id)
        comments = self.runtime.list_operator_comments(
            str(state["project_id"]),
            include_resolved=include_resolved,
        )
        return [self._comment_from_raw(comment) for comment in comments]

    def list_artifacts(
        self, project_id: str | None = None, phase: str | None = None
    ) -> list[dict[str, Any]]:
        """List artifacts for a project, optionally filtered to one phase."""
        state = self._state_for_project(project_id)
        store = self.runtime.services.artifact_store if self.runtime.services else None
        if store is None:
            return []
        phase_filter: FilmPhase | None = FilmPhase(phase) if phase else None
        artifacts = store.list_artifacts(str(state["project_id"]), phase_filter)
        return [
            {
                "artifact_id": artifact.artifact_id,
                "artifact_type": str(artifact.artifact_type.value),
                "phase": str(artifact.phase.value),
                "version": artifact.version,
                "status": str(artifact.status.value),
            }
            for artifact in artifacts
        ]

    def inspect_artifact(
        self,
        artifact_id: str,
        phase: str,
        version: int = 1,
        project_id: str | None = None,
    ) -> ArtifactDetail:
        """Load one artifact body."""
        if not artifact_id:
            raise BackendOperationError("artifact_id is required.")
        state = self._state_for_project(project_id)
        if self.runtime.services is None:
            raise BackendOperationError("artifact store is not configured.")
        body = self.runtime.services.artifact_store.load(
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

    def list_checkpoints(self, project_id: str | None = None) -> list[dict[str, str]]:
        """List checkpoints for a project."""
        state = self._state_for_project(project_id)
        checkpoints = self.runtime.list_checkpoints(str(state["project_id"]))
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

    def list_provider_status(self) -> list[dict[str, Any]]:
        """Return provider health rows."""
        return [
            {"provider_id": provider_id, **health}
            for provider_id, health in sorted(self.runtime.get_all_health().items())
        ]

    def get_audit_feed(self, project_id: str | None = None, limit: int = 20) -> list[AuditEvent]:
        """Return recent audit events."""
        state = self._state_for_project(project_id) if project_id else None
        events = self.runtime.get_audit_log(
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

    @staticmethod
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

    def _state_for_project(self, project_id: str | None) -> dict[str, Any]:
        if project_id:
            return self._require_project(project_id)
        active = self.runtime.get_active()
        if active is None:
            raise ProjectNotFoundError("No active project.")
        return active

    def _require_project(self, project_id: str) -> dict[str, Any]:
        project = self.runtime.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")
        return project

    def _has_blockers(self, state: dict[str, Any]) -> bool:
        project_id = str(state.get("project_id", ""))
        runtime_blockers = self.runtime.get_blockers(project_id) if project_id else []
        issue_blockers = [
            issue
            for issue in cast(list[Mapping[str, Any]], state.get("issues", []))
            if issue.get("severity") == "blocking"
        ]
        return bool(runtime_blockers or issue_blockers)

    @staticmethod
    def _status_for_state(state: dict[str, Any]) -> str:
        if state.get("completed"):
            return "complete"
        if state.get("human_approval_required"):
            return "awaiting_review"
        if state.get("current_phase"):
            return "in_progress"
        return "created"

    @staticmethod
    def _recommendation(next_action: str, phase: str) -> str:
        if next_action in {"wait_for_human", "present_review_package"}:
            return f"Review the {phase} outputs and approve or request revision."
        if next_action == "handle_blockers":
            return "Resolve blocking issues before advancing."
        if next_action.startswith("advance_to_"):
            return f"Ready to advance to {next_action.removeprefix('advance_to_')}."
        if not next_action:
            return "No next action is currently available."
        return f"Current action: {next_action}."
