"""Tests for operator application services."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.app.runtime import create_runtime
from film_pipeline.app.services.errors import BackendOperationError, ProjectNotFoundError
from film_pipeline.app.services.models import ProjectCreateRequest
from film_pipeline.app.services.operator import OperatorService


def _service(tmp_path: Path) -> OperatorService:
    runtime = create_runtime("mock")
    runtime.runtime_root = tmp_path
    return OperatorService(runtime)


class TestOperatorService:
    def test_create_project_from_idea_runs_intake(self, tmp_path: Path) -> None:
        service = _service(tmp_path)

        result = service.create_project(
            ProjectCreateRequest(
                project_id="field-message",
                title="The Field Message",
                slug="the-field-message",
                idea="A walker crosses five changing fields while nature carries a message.",
            )
        )

        assert result.ok is True
        assert result.project_id == "field-message"
        assert result.current_phase == "intake"

        dashboard = service.get_dashboard("field-message")
        assert dashboard.project_id == "field-message"
        assert dashboard.title == "The Field Message"
        assert dashboard.current_phase == "intake"
        assert dashboard.workflow_mode == "manual"
        assert dashboard.artifact_count >= 1

        review = service.get_review_workspace("field-message")
        assert review.phase == "intake"
        assert review.candidate_artifacts
        assert "Review" in review.recommendation

    def test_list_projects_exposes_review_status(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(
            ProjectCreateRequest(
                project_id="quiet-city",
                title="Quiet City",
                idea="A composer hears a city become silent overnight.",
            )
        )

        projects = service.list_projects()

        assert len(projects) == 1
        assert projects[0].project_id == "quiet-city"
        assert projects[0].current_phase == "intake"
        assert projects[0].status == "awaiting_review"
        assert projects[0].awaiting_review is True

    def test_approve_phase_advances_and_creates_checkpoint(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(
            ProjectCreateRequest(
                project_id="gate-test",
                title="Gate Test",
                idea="A projectionist restores a lost frame.",
            )
        )

        result = service.approve_phase("gate-test")

        assert result.ok is True
        assert result.current_phase == "constitution"
        checkpoints = service.list_checkpoints("gate-test")
        assert len(checkpoints) == 1
        assert checkpoints[0]["phase"] == "constitution"

    def test_validation_workspace_splits_blocking_and_non_blocking_issues(
        self, tmp_path: Path
    ) -> None:
        service = _service(tmp_path)
        service.create_project(
            ProjectCreateRequest(
                project_id="validation-test",
                title="Validation Test",
                idea="A projectionist restores a lost frame.",
            )
        )
        state = service.runtime.projects["validation-test"]
        state["_validation_reports"] = [{"validator_id": "script-structure", "score": 91}]
        state["issues"] = [
            {"severity": "blocking", "message": "Missing shot prompt."},
            {"severity": "warning", "message": "Weak scene transition."},
        ]

        workspace = service.get_validation_workspace("validation-test")

        assert workspace.source == "stored_state"
        assert len(workspace.reports) == 1
        assert len(workspace.blocking_issues) == 1
        assert len(workspace.non_blocking_issues) == 1

    def test_submit_idea_requires_text(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="empty", title="Empty"))

        with pytest.raises(BackendOperationError, match="idea is required"):
            service.submit_idea("empty", "")

    def test_unknown_project_raises_actionable_error(self, tmp_path: Path) -> None:
        service = _service(tmp_path)

        with pytest.raises(ProjectNotFoundError, match="not found"):
            service.get_dashboard("missing")
