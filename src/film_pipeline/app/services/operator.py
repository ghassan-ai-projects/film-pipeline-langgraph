"""Operator-facing application service.

This service is intentionally thin. It owns use-case sequencing and view-model
mapping while keeping durable state changes inside ``StudioRuntime`` and graph
helpers.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast

from film_pipeline.app.runtime import StudioRuntime, get_runtime, reset_runtime
from film_pipeline.app.services import _browse_ops, _checkpoint_ops, _generation_ops
from film_pipeline.app.services._project_discovery import (
    discover_project_folders,
    load_discovered_project,
    normalize_project_kind,
    project_kind_for_state,
)
from film_pipeline.app.services.errors import BackendOperationError, ProjectNotFoundError
from film_pipeline.app.services.models import (
    ArtifactDetail,
    ArtifactRollbackResult,
    AuditEvent,
    CheckpointRollbackResult,
    DashboardSummary,
    GenerationWorkspace,
    MutationResult,
    OperatorComment,
    OperatorCommentRequest,
    ProjectCreateRequest,
    ProjectListItem,
    ReviewWorkspace,
    ValidationWorkspace,
)
from film_pipeline.config import profile_resolver as _profiles
from film_pipeline.graph import orchestrator_state as ostate
from film_pipeline.graph.router import (
    RouterResult,
    compute_actions,
    get_blockers_for_state,
    public_blocked_actions,
)
from film_pipeline.schemas.checkpoint import CheckpointMetadata


class OperatorService:
    """Shared service backing the MCP operator tools."""

    def __init__(self, runtime: StudioRuntime | None = None) -> None:
        self._runtime = runtime

    @property
    def runtime(self) -> StudioRuntime:
        """Return the configured runtime, resolving the singleton lazily."""
        return self._runtime if self._runtime is not None else get_runtime()

    def list_projects(self) -> list[ProjectListItem]:
        """List all known projects with operator status fields."""
        items = [
            self._project_list_item(project_id, state)
            for project_id, state in sorted(self.runtime.projects.items())
        ]
        known_ids = {item.project_id for item in items}
        items.extend(discover_project_folders(self, known_ids))
        return items

    def _project_list_item(self, project_id: str, state: dict[str, Any]) -> ProjectListItem:
        """Map one persisted project state to its operator-facing row."""
        return ProjectListItem(
            project_id=project_id,
            title=str(state.get("title") or project_id),
            slug=str(state.get("slug", project_id)),
            current_phase=str(state.get("current_phase", "")),
            status=self._status_for_state(state),
            has_blockers=self._has_blockers(state),
            awaiting_review=bool(state.get("human_approval_required")),
            last_updated_at=self._last_updated_at(project_id),
            project_kind=project_kind_for_state(state, project_id),
            project_root=str(self.runtime.project_roots.get(project_id, "")),
        )

    def _last_updated_at(self, project_id: str) -> str:
        """ISO timestamp of the project's last persisted state change."""
        root = self.runtime.project_roots.get(project_id)
        if root is None:
            return ""
        try:
            mtime = (root / "project.json").stat().st_mtime
        except OSError:
            return ""
        return datetime.fromtimestamp(mtime, tz=UTC).isoformat()

    def create_project(self, request: ProjectCreateRequest) -> MutationResult:
        """Create a project, set it active, and optionally submit the idea."""
        project_id = request.project_id.strip()
        title = request.title.strip()
        if not project_id:
            raise BackendOperationError("project_id is required.")
        if not title:
            raise BackendOperationError("title is required.")

        state = self.runtime.create_project(
            project_id=project_id,
            title=title,
            slug=request.slug.strip() or project_id,
        )
        self._apply_requested_settings(state, request)
        self._activate_new_project(project_id, state, request)
        current_phase = self._run_intake_when_idea_supplied(project_id, state, request)

        return MutationResult(
            ok=True,
            project_id=str(state["project_id"]),
            current_phase=current_phase,
            message="Project created.",
        )

    def _apply_requested_settings(
        self, state: dict[str, Any], request: ProjectCreateRequest
    ) -> None:
        """Copy the operator-chosen modes, kind, and policy into the fresh state."""
        state["runtime_mode"] = request.runtime_mode
        state["workflow_mode"] = request.workflow_mode
        state["project_kind"] = normalize_project_kind(request.project_kind)
        state["generation_policy"] = request.generation_policy
        self._resolve_and_store_profiles(state, request)

    def _resolve_and_store_profiles(
        self, state: dict[str, Any], request: ProjectCreateRequest
    ) -> None:
        """Canonicalize the request's profile stack, store its resolution, register providers."""
        profile_stack = _profiles.canonicalize_profile_stack(
            {
                "film_type_profile": request.film_type_profile,
                "quality_profile": request.quality_profile,
                "provider_profile": request.provider_profile,
                "review_profile": request.review_profile,
                "auto_approve_profile": request.auto_approve_profile,
            }
        )
        resolved_config = _profiles.resolve_project_config(profile_stack)
        state["profile_stack"] = profile_stack
        state["resolved_config"] = cast(dict[str, object], resolved_config.get("raw", {}))
        state["resolved_config_sources"] = resolved_config["sources"]
        state["config_conflicts"] = list(cast(list[Any], resolved_config.get("conflicts", [])))
        _profiles.register_project_providers(
            self.runtime, profile_stack, cast(dict[str, object], resolved_config.get("raw", {}))
        )

    def _activate_new_project(
        self, project_id: str, state: dict[str, Any], request: ProjectCreateRequest
    ) -> None:
        """Make the new project active and seed its user-supplied target runtime."""
        self.runtime.set_active(project_id)
        if request.target_runtime_seconds > 0:
            # User-supplied runtime is authoritative — seed it before intake runs
            # so the classifier adopts it instead of guessing.
            state["target_runtime_seconds"] = request.target_runtime_seconds

    def _run_intake_when_idea_supplied(
        self, project_id: str, state: dict[str, Any], request: ProjectCreateRequest
    ) -> str:
        """Run intake immediately when an idea was supplied; return the phase reached.

        When no idea is supplied we stay aligned with MCP ``create_film_project``
        and only set up state; ``submit_idea`` is then responsible for advancing.
        """
        if not (request.idea and request.idea.strip()):
            return ""
        state["idea"] = request.idea.strip()
        next_state = self.runtime.run_graph(state)
        next_state["generation_policy"] = request.generation_policy
        self.runtime.projects[project_id] = next_state
        return str(next_state.get("current_phase", ""))

    def set_runtime_mode(self, mode: str) -> str:
        """Switch the session runtime mode, rebuilding the runtime when it changes.

        Returns the active mode after the switch. A no-op when the requested
        mode already matches, so it is safe to call before every create.
        """
        if self._runtime is not None:
            if self._runtime.server_mode != mode:
                raise BackendOperationError(
                    "Runtime mode is fixed for an explicitly injected runtime."
                )
            return self._runtime.server_mode
        if get_runtime().server_mode == mode:
            return mode
        os.environ["FILM_PIPELINE_MCP_MODE"] = mode
        runtime = reset_runtime(mode)
        runtime.seed_default_provider_health()
        return runtime.server_mode

    def set_active_project(self, project_id: str) -> DashboardSummary:
        """Select an active project and return its dashboard."""
        self._require_project(project_id)
        self.runtime.set_active(project_id)
        return self.get_dashboard(project_id)

    def submit_idea(
        self, project_id: str, idea: str, target_runtime_seconds: int = 0
    ) -> MutationResult:
        """Attach an idea to a project and run intake.

        ``target_runtime_seconds`` (> 0) is the user-supplied expected length and
        is authoritative — seeded before intake so the classifier adopts it.
        """
        if not idea.strip():
            raise BackendOperationError("idea is required.")
        state = self._require_project(project_id)
        self.runtime.set_active(project_id)
        state["idea"] = idea.strip()
        if target_runtime_seconds > 0:
            state["target_runtime_seconds"] = target_runtime_seconds
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
        routing_state = dict(state)
        ostate.ensure_orchestrator_state(routing_state)
        router_result = compute_actions(routing_state)
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
            idea=str(state.get("idea", "")),
            eligible_actions=list(router_result.eligible),
            blocked_actions=public_blocked_actions(router_result),
            pending_revisions=list(ostate.get_pending_revisions(state)),
            candidate_refs=dict(ostate.get_candidate_refs(state)),
            approved_refs=dict(ostate.get_approved_refs(state)),
            budget_snapshot=dict(ostate.get_budget_snapshot(state)),
            provider_blocked=list(ostate.get_blocked_providers(state)),
            issue_count=len(cast(list[Any], state.get("issues", []))),
            artifact_count=len(self.list_artifacts(project_id_value)),
            checkpoint_count=checkpoint_count,
            has_blockers=self._has_blockers(state, routing=router_result),
            stalled_phase=str(state.get("_stalled_phase", "")),
            profile_stack=dict(cast(Mapping[str, str], state.get("profile_stack", {}))),
            generation_policy=str(state.get("generation_policy", "generate")),
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

        router_result = compute_actions(dict(state))
        artifacts = self.list_artifacts(str(state["project_id"]), phase=phase)
        blocking_issues = [
            str(issue.get("message", issue)) for issue in self._blocking_state_issues(state)
        ]
        recommendation = self._recommendation(router_result.next_action, phase)
        return ReviewWorkspace(
            project_id=str(state["project_id"]),
            phase=phase,
            recommendation=recommendation,
            candidate_artifacts=list(artifacts),
            open_issues=blocking_issues,
            available_actions=list(router_result.eligible),
            blocked_actions=public_blocked_actions(router_result),
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

    def run_validation(self, project_id: str | None = None) -> ValidationWorkspace:
        """Run validators on demand against the current phase and return results."""
        state = self._state_for_project(project_id)
        if not str(state.get("current_phase", "")):
            raise BackendOperationError("Submit an idea before running validation.")
        self.runtime.run_validation(str(state["project_id"]))
        return self.get_validation_workspace(str(state["project_id"]))

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

    # --- Generation batch operations (see _generation_ops) ---

    def get_generation_workspace(self, project_id: str | None = None) -> GenerationWorkspace:
        """Summarize the generation ledger for the operator."""
        return _generation_ops.get_generation_workspace(self, project_id)

    def plan_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        """Plan a generation batch for every shot in the approved shot matrix."""
        return _generation_ops.plan_generation(self, project_id)

    def approve_generation_spend(
        self,
        project_id: str | None = None,
        max_cost_usd: float = -1.0,
    ) -> GenerationWorkspace:
        """Approve spend for planned generation rows."""
        return _generation_ops.approve_generation_spend(self, project_id, max_cost_usd)

    def start_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        """Submit approved generation rows to their providers."""
        return _generation_ops.start_generation(self, project_id)

    def poll_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        """Poll running generations once, delivering completed outputs."""
        return _generation_ops.poll_generation(self, project_id)

    def preview_generation_prompts(self, project_id: str | None = None) -> list[dict[str, Any]]:
        """Resolve the exact prompt each shot will send to its provider."""
        return _generation_ops.preview_generation_prompts(self, project_id)

    # --- Comments, artifacts, and audit views (see _browse_ops) ---

    def add_operator_comment(
        self,
        request: OperatorCommentRequest,
        project_id: str | None = None,
    ) -> OperatorComment:
        """Persist a target-scoped operator comment."""
        return _browse_ops.add_operator_comment(self, request, project_id)

    def list_operator_comments(
        self,
        project_id: str | None = None,
        *,
        include_resolved: bool = False,
    ) -> list[OperatorComment]:
        """List target-scoped operator comments."""
        return _browse_ops.list_operator_comments(
            self, project_id, include_resolved=include_resolved
        )

    def list_artifacts(
        self, project_id: str | None = None, phase: str | None = None
    ) -> list[dict[str, Any]]:
        """List artifacts for a project, optionally filtered to one phase."""
        return _browse_ops.list_artifacts(self, project_id, phase)

    def list_assets(self, project_id: str | None = None) -> list[dict[str, Any]]:
        """List generated/reference assets from the project asset manifest."""
        return _browse_ops.list_assets(self, project_id)

    def inspect_artifact(
        self,
        artifact_id: str,
        phase: str,
        version: int = 1,
        project_id: str | None = None,
    ) -> ArtifactDetail:
        """Load one artifact body."""
        return _browse_ops.inspect_artifact(self, artifact_id, phase, version, project_id)

    def list_checkpoints(self, project_id: str | None = None) -> list[dict[str, str]]:
        """List checkpoints for a project."""
        return _browse_ops.list_checkpoints(self, project_id)

    def get_checkpoint(
        self,
        checkpoint_id: str,
    ) -> CheckpointMetadata | None:
        """Get checkpoint metadata by its globally unique identifier."""
        return _checkpoint_ops.get_checkpoint(self, checkpoint_id)

    def rollback_to_checkpoint(
        self,
        checkpoint: CheckpointMetadata,
        project_id: str,
    ) -> CheckpointRollbackResult:
        """Restore one project's checkpoint and persist its rollback records."""
        return _checkpoint_ops.rollback_to_checkpoint(self, checkpoint, project_id)

    def rollback_artifact(
        self,
        artifact_id: str,
        checkpoint_id: str = "",
        *,
        project_id: str,
    ) -> ArtifactRollbackResult:
        """Restore one artifact from a project checkpoint."""
        return _checkpoint_ops.rollback_artifact(self, project_id, artifact_id, checkpoint_id)

    def list_provider_status(self) -> list[dict[str, Any]]:
        """Return provider health rows."""
        return _browse_ops.list_provider_status(self)

    def get_audit_feed(self, project_id: str | None = None, limit: int = 20) -> list[AuditEvent]:
        """Return recent audit events."""
        return _browse_ops.get_audit_feed(self, project_id, limit)

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
            project = load_discovered_project(self, project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")
        return project

    def _has_blockers(self, state: dict[str, Any], routing: RouterResult | None = None) -> bool:
        """True when live project state carries anything blocking.

        The MCP ``get_blockers`` tool derives the same signal from
        ``compute_actions`` plus blocking issues; this predicate stays a cheap
        boolean over the state already in hand.
        """
        return bool(get_blockers_for_state(state, routing=routing))

    @staticmethod
    def _blocking_state_issues(state: dict[str, Any]) -> list[Mapping[str, Any]]:
        """Issues stored on the project whose severity blocks advancement."""
        return [
            issue
            for issue in cast(list[Mapping[str, Any]], state.get("issues", []))
            if issue.get("severity") == "blocking"
        ]

    @staticmethod
    def _status_for_state(state: dict[str, Any]) -> str:
        if state.get("completed"):
            return "complete"
        if state.get("_stalled_phase"):
            return "stalled"
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
