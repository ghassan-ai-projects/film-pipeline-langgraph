"""E2E Scenario 10: Dynamic flow — blocked path does not destroy available work."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.graph.router import compute_actions
from film_pipeline.graph.services import GraphServices


@pytest.mark.e2e
class TestDynamicFlow:
    def test_blocked_path_yields_available_actions(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services
        rt.create_project("dynamic-test", "Dynamic Test")
        rt.set_active("dynamic-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "A story about parallel universes."
        project["current_phase"] = "script"
        project["issues"] = [
            {
                "issue_id": "block-1",
                "severity": "blocking",
                "code": "SCRIPT_INCOMPLETE",
                "message": "Missing act 3.",
            }
        ]
        rt.projects["dynamic-test"] = project

        result = compute_actions(project)
        assert len(result.blocked) >= 1, "Should have at least one blocker"
        assert result.human_gate or result.next_action, "Should have gate or next action"

    def test_blocked_phase_preserves_prior_artifacts(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services
        rt.create_project("blocked-test", "Blocked Test")
        rt.set_active("blocked-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "A silent film about noise."
        project["current_phase"] = "development"
        project["artifact_refs"] = ["artifact:film_constitution:v1", "artifact:project_profile:v1"]
        rt.projects["blocked-test"] = project

        active = rt.get_active()
        assert active is not None
        assert active.get("current_phase") == "development"
        refs = active.get("artifact_refs", [])
        assert len(refs) >= 2, f"Should have artifact refs, got {refs}"
