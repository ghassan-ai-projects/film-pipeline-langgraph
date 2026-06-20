"""E2E Scenario 3: Reference validation failure — blocks are detectable."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.graph.router import compute_actions
from film_pipeline.graph.services import GraphServices
from film_pipeline.validation.impl.reference_usability import ReferenceUsabilityValidator


@pytest.mark.e2e
class TestReferenceFailure:
    def test_validation_issues_are_stored_in_state(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services

        rt.create_project("ref-fail-test", "Ref Fail Test")
        rt.set_active("ref-fail-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "A film with impossible visual references."
        project["current_phase"] = "visual_dev"
        project["issues"] = [
            {
                "issue_id": "ref-1",
                "severity": "blocking",
                "code": "REFERENCE_UNUSABLE",
                "message": "Reference below minimum resolution.",
            }
        ]
        rt.projects["ref-fail-test"] = project

        result = compute_actions(project)
        assert len(result.blocked) > 0, "Project with blocking issues should report blockers"

    def test_blocking_issue_preserves_prior_artifacts(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services

        rt.create_project("preserve-test", "Preserve Test")
        rt.set_active("preserve-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "Test preservation."
        project["current_phase"] = "development"
        project["artifact_refs"] = ["artifact:film_constitution:v1", "artifact:project_profile:v1"]
        rt.projects["preserve-test"] = project

        refs_before = list(project.get("artifact_refs", []))
        project["issues"] = [
            {"issue_id": "b1", "severity": "blocking", "code": "REF_BLOCK", "message": "Blocked."}
        ]
        rt.projects["preserve-test"] = project

        active = rt.get_active()
        assert active is not None
        refs_after = list(active.get("artifact_refs", []))
        assert refs_after == refs_before, "Artifact refs unchanged after blocking issue"

    def test_real_validator_detects_low_quality(self) -> None:
        """Reference with quality_score < 60 triggers low_resolution blocking issue."""
        validator = ReferenceUsabilityValidator()
        report = validator.run(
            {
                "entries": [
                    {
                        "reference_id": "ref-001",
                        "quality_score": 45,
                        "moderation_risk": "low",
                        "subject_type": "character",
                        "notes": "",
                    }
                ]
            }
        )
        assert any(i.code == "low_resolution" for i in report.blocking_issues)
        assert report.score < 85

    def test_real_validator_clean_ref_passes(self) -> None:
        """A reference with good quality passes validation."""
        validator = ReferenceUsabilityValidator()
        report = validator.run(
            {
                "entries": [
                    {
                        "reference_id": "ref-001",
                        "quality_score": 95,
                        "moderation_risk": "low",
                        "subject_type": "character",
                        "notes": "",
                    }
                ]
            }
        )
        assert report.status.value == "pass"
        assert report.score == 100.0
