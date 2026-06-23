"""Tests for the terminal operator console."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from film_pipeline.app.services.models import (
    ArtifactDetail,
    AuditEvent,
    DashboardSummary,
    MutationResult,
    ProjectCreateRequest,
    ProjectListItem,
    ReviewWorkspace,
    ValidationWorkspace,
)
from film_pipeline.tui.app import OperatorConsole
from film_pipeline.tui.formatting import table


@dataclass
class RecordingGateway:
    """Small gateway fake for console interaction tests."""

    created_request: ProjectCreateRequest | None = None
    approved_count: int = 0
    revision_count: int = 0

    def list_projects(self) -> list[ProjectListItem]:
        return []

    def create_project(self, request: ProjectCreateRequest) -> MutationResult:
        self.created_request = request
        return MutationResult(
            ok=True,
            project_id=request.project_id,
            current_phase="intake" if request.idea else "",
            message="Project created.",
        )

    def set_active_project(self, project_id: str) -> DashboardSummary:
        return self.get_dashboard(project_id)

    def submit_idea(self, project_id: str, idea: str) -> MutationResult:
        return MutationResult(ok=True, project_id=project_id, current_phase="intake")

    def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
        return DashboardSummary(
            project_id=project_id or "field-message",
            title="The Field Message",
            slug="the-field-message",
            current_phase="intake",
            runtime_mode="mock",
            workflow_mode="manual",
            status="awaiting_review",
            next_action="wait_for_human",
            route_reason="",
        )

    def get_review_workspace(self, project_id: str | None = None) -> ReviewWorkspace:
        return ReviewWorkspace(
            project_id=project_id or "field-message",
            phase="intake",
            recommendation="Review the intake outputs.",
        )

    def get_validation_workspace(self, project_id: str | None = None) -> ValidationWorkspace:
        return ValidationWorkspace(
            project_id=project_id or "field-message",
            phase="intake",
            source="stored_state",
            reports=[{"validator_id": "script-structure", "score": 91}],
            blocking_issues=[{"severity": "blocking", "message": "Missing shot prompt."}],
        )

    def approve_phase(self, project_id: str | None = None) -> MutationResult:
        self.approved_count += 1
        return MutationResult(
            ok=True,
            project_id=project_id or "field-message",
            current_phase="constitution",
        )

    def request_revision(self, note: str, project_id: str | None = None) -> MutationResult:
        self.revision_count += 1
        return MutationResult(
            ok=True,
            project_id=project_id or "field-message",
            current_phase="intake",
        )

    def list_artifacts(
        self, project_id: str | None = None, phase: str | None = None
    ) -> list[dict[str, object]]:
        return []

    def inspect_artifact(
        self,
        artifact_id: str,
        phase: str,
        version: int = 1,
        project_id: str | None = None,
    ) -> ArtifactDetail:
        return ArtifactDetail(artifact_id, artifact_id, phase, version, "candidate", {})

    def list_checkpoints(self, project_id: str | None = None) -> list[dict[str, str]]:
        return []

    def list_provider_status(self) -> list[dict[str, object]]:
        return []

    def get_audit_feed(self, project_id: str | None = None, limit: int = 20) -> list[AuditEvent]:
        return []


class TestOperatorConsole:
    def test_create_project_from_values_uses_gateway(self) -> None:
        gateway = RecordingGateway()
        output: list[str] = []
        console = OperatorConsole(gateway=gateway, output_func=output.append)

        console.create_project_from_values(
            project_id="field-message",
            title_text="The Field Message",
            slug="the-field-message",
            idea="A walker crosses five changing fields.",
        )

        assert gateway.created_request is not None
        assert gateway.created_request.project_id == "field-message"
        assert gateway.created_request.idea == "A walker crosses five changing fields."
        assert any("Created project field-message" in line for line in output)

    def test_table_renders_empty_body_with_headers(self) -> None:
        rendered = table([], ["project_id", "status"])

        assert "project_id" in rendered
        assert "status" in rendered

    def test_approve_phase_requires_confirmation(self) -> None:
        gateway = RecordingGateway()
        inputs = iter(["n"])
        output: list[str] = []
        console = OperatorConsole(
            gateway=gateway,
            input_func=lambda _prompt: next(inputs),
            output_func=output.append,
        )
        console._active_project_id = "field-message"

        console._approve_phase()

        assert gateway.approved_count == 0
        assert "Approval cancelled." in output

    def test_approve_phase_runs_after_confirmation(self) -> None:
        gateway = RecordingGateway()
        inputs = iter(["yes"])
        output: list[str] = []
        console = OperatorConsole(
            gateway=gateway,
            input_func=lambda _prompt: next(inputs),
            output_func=output.append,
        )
        console._active_project_id = "field-message"

        console._approve_phase()

        assert gateway.approved_count == 1
        assert any("Current phase: constitution" in line for line in output)

    def test_validation_view_renders_reports_and_issues(self) -> None:
        gateway = RecordingGateway()
        output: list[str] = []
        console = OperatorConsole(gateway=gateway, output_func=output.append)
        console._active_project_id = "field-message"

        console._show_validation()

        rendered = "\n".join(output)
        assert "Validation" in rendered
        assert "script-structure" in rendered
        assert "Missing shot prompt" in rendered


def test_gateway_protocol_shape_accepts_recording_gateway() -> None:
    gateway = RecordingGateway()
    rows: list[dict[str, Any]] = gateway.list_artifacts()

    assert rows == []
