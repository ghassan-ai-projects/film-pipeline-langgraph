"""In-process TUI gateway backed by application services."""

from __future__ import annotations

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
from film_pipeline.app.services.operator import OperatorService


class InProcessStudioGateway:
    """Gateway that calls application services directly."""

    def __init__(self, service: OperatorService | None = None) -> None:
        self._service = service or OperatorService()

    def list_projects(self) -> list[ProjectListItem]:
        return self._service.list_projects()

    def create_project(self, request: ProjectCreateRequest) -> MutationResult:
        return self._service.create_project(request)

    def set_active_project(self, project_id: str) -> DashboardSummary:
        return self._service.set_active_project(project_id)

    def submit_idea(self, project_id: str, idea: str) -> MutationResult:
        return self._service.submit_idea(project_id, idea)

    def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
        return self._service.get_dashboard(project_id)

    def get_review_workspace(self, project_id: str | None = None) -> ReviewWorkspace:
        return self._service.get_review_workspace(project_id)

    def get_validation_workspace(self, project_id: str | None = None) -> ValidationWorkspace:
        return self._service.get_validation_workspace(project_id)

    def approve_phase(self, project_id: str | None = None) -> MutationResult:
        return self._service.approve_phase(project_id)

    def request_revision(self, note: str, project_id: str | None = None) -> MutationResult:
        return self._service.request_revision(note, project_id)

    def add_operator_comment(
        self,
        request: OperatorCommentRequest,
        project_id: str | None = None,
    ) -> OperatorComment:
        return self._service.add_operator_comment(request, project_id)

    def list_operator_comments(
        self,
        project_id: str | None = None,
        *,
        include_resolved: bool = False,
    ) -> list[OperatorComment]:
        return self._service.list_operator_comments(project_id, include_resolved=include_resolved)

    def list_artifacts(
        self, project_id: str | None = None, phase: str | None = None
    ) -> list[dict[str, object]]:
        return self._service.list_artifacts(project_id, phase)

    def list_assets(self, project_id: str | None = None) -> list[dict[str, object]]:
        return self._service.list_assets(project_id)

    def inspect_artifact(
        self,
        artifact_id: str,
        phase: str,
        version: int = 1,
        project_id: str | None = None,
    ) -> ArtifactDetail:
        return self._service.inspect_artifact(artifact_id, phase, version, project_id)

    def list_checkpoints(self, project_id: str | None = None) -> list[dict[str, str]]:
        return self._service.list_checkpoints(project_id)

    def list_provider_status(self) -> list[dict[str, object]]:
        return self._service.list_provider_status()

    def get_audit_feed(self, project_id: str | None = None, limit: int = 20) -> list[AuditEvent]:
        return self._service.get_audit_feed(project_id, limit)
