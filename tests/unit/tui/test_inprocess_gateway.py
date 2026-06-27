"""Tests for the in-process TUI gateway delegation layer."""

from __future__ import annotations

from typing import Any

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
from film_pipeline.tui.gateways.inprocess import InProcessStudioGateway


class RecordingService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def _record(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append((name, args, kwargs))

    def list_projects(self) -> list[ProjectListItem]:
        self._record("list_projects")
        return [
            ProjectListItem(
                project_id="p1",
                title="Project",
                slug="project",
                current_phase="script",
                status="awaiting_review",
                has_blockers=False,
                awaiting_review=True,
            )
        ]

    def create_project(self, request: ProjectCreateRequest) -> MutationResult:
        self._record("create_project", request)
        return MutationResult(ok=True, project_id=request.project_id, current_phase="")

    def set_active_project(self, project_id: str) -> DashboardSummary:
        self._record("set_active_project", project_id)
        return self.get_dashboard(project_id)

    def submit_idea(self, project_id: str, idea: str) -> MutationResult:
        self._record("submit_idea", project_id, idea)
        return MutationResult(ok=True, project_id=project_id, current_phase="intake")

    def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
        self._record("get_dashboard", project_id)
        return DashboardSummary(
            project_id=project_id or "p1",
            title="Project",
            slug="project",
            current_phase="script",
            runtime_mode="mock",
            workflow_mode="manual",
            status="awaiting_review",
            next_action="present_review_package",
            route_reason="review",
        )

    def get_review_workspace(self, project_id: str | None = None) -> ReviewWorkspace:
        self._record("get_review_workspace", project_id)
        return ReviewWorkspace(
            project_id=project_id or "p1", phase="script", recommendation="Review"
        )

    def get_validation_workspace(self, project_id: str | None = None) -> ValidationWorkspace:
        self._record("get_validation_workspace", project_id)
        return ValidationWorkspace(project_id=project_id or "p1", phase="script", source="none")

    def approve_phase(self, project_id: str | None = None) -> MutationResult:
        self._record("approve_phase", project_id)
        return MutationResult(ok=True, project_id=project_id or "p1", current_phase="next")

    def request_revision(self, note: str, project_id: str | None = None) -> MutationResult:
        self._record("request_revision", note, project_id)
        return MutationResult(ok=True, project_id=project_id or "p1", current_phase="script")

    def add_operator_comment(
        self,
        request: OperatorCommentRequest,
        project_id: str | None = None,
    ) -> OperatorComment:
        self._record("add_operator_comment", request, project_id)
        return OperatorComment(
            comment_id="comment:1",
            project_id=project_id or "p1",
            target_type=request.target_type,
            target_id=request.target_id,
            body=request.body,
            phase=request.phase,
            source=request.source,
            created_at="now",
        )

    def list_operator_comments(
        self,
        project_id: str | None = None,
        *,
        include_resolved: bool = False,
    ) -> list[OperatorComment]:
        self._record("list_operator_comments", project_id, include_resolved=include_resolved)
        return []

    def list_artifacts(
        self, project_id: str | None = None, phase: str | None = None
    ) -> list[dict[str, object]]:
        self._record("list_artifacts", project_id, phase)
        return [{"artifact_id": "script"}]

    def list_assets(self, project_id: str | None = None) -> list[dict[str, object]]:
        self._record("list_assets", project_id)
        return [{"asset_id": "clip_1"}]

    def inspect_artifact(
        self,
        artifact_id: str,
        phase: str,
        version: int = 1,
        project_id: str | None = None,
    ) -> ArtifactDetail:
        self._record("inspect_artifact", artifact_id, phase, version, project_id)
        return ArtifactDetail(
            artifact_id=artifact_id,
            artifact_type=artifact_id,
            phase=phase,
            version=version,
            status="candidate",
            body={"ok": True},
        )

    def list_checkpoints(self, project_id: str | None = None) -> list[dict[str, str]]:
        self._record("list_checkpoints", project_id)
        return [{"checkpoint_id": "cp1"}]

    def list_provider_status(self) -> list[dict[str, object]]:
        self._record("list_provider_status")
        return [{"provider_id": "mock"}]

    def get_audit_feed(self, project_id: str | None = None, limit: int = 20) -> list[AuditEvent]:
        self._record("get_audit_feed", project_id, limit)
        return [
            AuditEvent(timestamp="now", actor="system", action="x", target="p1", summary="x p1")
        ]


def test_inprocess_gateway_delegates_operator_methods() -> None:
    service = RecordingService()
    gateway = InProcessStudioGateway(service)  # type: ignore[arg-type]
    create_request = ProjectCreateRequest(project_id="p1", title="Project")
    comment_request = OperatorCommentRequest(target_type="scene", target_id="s1", body="Fix")

    assert gateway.list_projects()[0].project_id == "p1"
    assert gateway.create_project(create_request).project_id == "p1"
    assert gateway.set_active_project("p1").project_id == "p1"
    assert gateway.submit_idea("p1", "Idea").current_phase == "intake"
    assert gateway.get_dashboard("p1").current_phase == "script"
    assert gateway.get_review_workspace("p1").phase == "script"
    assert gateway.get_validation_workspace("p1").source == "none"
    assert gateway.approve_phase("p1").current_phase == "next"
    assert gateway.request_revision("Note", "p1").project_id == "p1"
    assert gateway.add_operator_comment(comment_request, "p1").comment_id == "comment:1"
    assert gateway.list_operator_comments("p1", include_resolved=True) == []
    assert gateway.list_artifacts("p1", "script") == [{"artifact_id": "script"}]
    assert gateway.list_assets("p1") == [{"asset_id": "clip_1"}]
    assert gateway.inspect_artifact("script", "script", 2, "p1").version == 2
    assert gateway.list_checkpoints("p1") == [{"checkpoint_id": "cp1"}]
    assert gateway.list_provider_status() == [{"provider_id": "mock"}]
    assert gateway.get_audit_feed("p1", 7)[0].summary == "x p1"

    assert [name for name, _args, _kwargs in service.calls] == [
        "list_projects",
        "create_project",
        "set_active_project",
        "get_dashboard",
        "submit_idea",
        "get_dashboard",
        "get_review_workspace",
        "get_validation_workspace",
        "approve_phase",
        "request_revision",
        "add_operator_comment",
        "list_operator_comments",
        "list_artifacts",
        "list_assets",
        "inspect_artifact",
        "list_checkpoints",
        "list_provider_status",
        "get_audit_feed",
    ]
    assert service.calls[11][2] == {"include_resolved": True}
