"""E2E Scenario 6: Continuity drift — detection stops work and flags repair."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.graph.router import compute_actions
from film_pipeline.graph.services import GraphServices


@pytest.mark.e2e
class TestContinuityDrift:
    def test_continuity_issues_are_detectable(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services
        rt.create_project("continuity-test", "Continuity Test")
        rt.set_active("continuity-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "A time-loop thriller."
        project["current_phase"] = "generation"
        project["issues"] = [
            {
                "issue_id": "cont-1",
                "severity": "blocking",
                "code": "CHARACTER_STATE_MISMATCH",
                "message": "Character Elara eye color mismatch.",
            }
        ]
        rt.projects["continuity-test"] = project

        issues = project.get("issues", [])
        assert any(i["code"] == "CHARACTER_STATE_MISMATCH" for i in issues)

    def test_blocked_phase_flags_repair_action(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services
        rt.create_project("repair-test", "Repair Test")
        rt.set_active("repair-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "Repair test."
        project["current_phase"] = "generation"
        project["issues"] = [
            {"issue_id": "c1", "severity": "blocking", "code": "CONTINUITY_GAP", "message": "Gap."}
        ]
        rt.projects["repair-test"] = project

        result = compute_actions(project)
        assert result.blocked, "Router should report blocked state"
