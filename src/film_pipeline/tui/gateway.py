"""Gateway contracts for the terminal operator console."""

from __future__ import annotations

from typing import Protocol

from film_pipeline.app.services.models import (
    ArtifactDetail,
    AuditEvent,
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


class StudioGateway(Protocol):
    """Typed boundary between the TUI and backend use cases."""

    def list_projects(self) -> list[ProjectListItem]:
        """List project rail entries."""

    def create_project(self, request: ProjectCreateRequest) -> MutationResult:
        """Create a project and optionally run intake from an idea."""

    def set_active_project(self, project_id: str) -> DashboardSummary:
        """Set the active project."""

    def set_runtime_mode(self, mode: str) -> str:
        """Switch the session runtime mode (``mock``/``real``); return active mode."""

    def submit_idea(self, project_id: str, idea: str) -> MutationResult:
        """Submit or replace the active project idea."""

    def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
        """Return dashboard state."""

    def get_review_workspace(self, project_id: str | None = None) -> ReviewWorkspace:
        """Return the current phase review workspace."""

    def get_validation_workspace(self, project_id: str | None = None) -> ValidationWorkspace:
        """Return validation reports and issues."""

    def run_validation(self, project_id: str | None = None) -> ValidationWorkspace:
        """Run validators on demand and return the refreshed validation workspace."""

    def approve_phase(self, project_id: str | None = None) -> MutationResult:
        """Approve the active phase."""

    def get_generation_workspace(self, project_id: str | None = None) -> GenerationWorkspace:
        """Return generation ledger status for the project."""

    def plan_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        """Plan a generation batch for every shot in the approved shot matrix."""

    def approve_generation_spend(
        self, project_id: str | None = None, max_cost_usd: float = -1.0
    ) -> GenerationWorkspace:
        """Approve spend for planned generation rows."""

    def start_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        """Submit approved generation rows to providers."""

    def poll_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        """Poll running generations once, delivering completed outputs."""

    def request_revision(self, note: str, project_id: str | None = None) -> MutationResult:
        """Request a revision with notes."""

    def add_operator_comment(
        self,
        request: OperatorCommentRequest,
        project_id: str | None = None,
    ) -> OperatorComment:
        """Persist a target-scoped operator comment."""

    def list_operator_comments(
        self,
        project_id: str | None = None,
        *,
        include_resolved: bool = False,
    ) -> list[OperatorComment]:
        """List target-scoped operator comments."""

    def list_artifacts(
        self, project_id: str | None = None, phase: str | None = None
    ) -> list[dict[str, object]]:
        """List artifacts."""

    def list_assets(self, project_id: str | None = None) -> list[dict[str, object]]:
        """List generated/reference assets."""

    def inspect_artifact(
        self,
        artifact_id: str,
        phase: str,
        version: int = 1,
        project_id: str | None = None,
    ) -> ArtifactDetail:
        """Inspect one artifact."""

    def list_checkpoints(self, project_id: str | None = None) -> list[dict[str, str]]:
        """List checkpoints."""

    def list_provider_status(self) -> list[dict[str, object]]:
        """List provider status."""

    def get_audit_feed(self, project_id: str | None = None, limit: int = 20) -> list[AuditEvent]:
        """Return audit events."""
