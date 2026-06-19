"""E2E Scenario 9: Project ambiguity — multiple projects coexist safely."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.graph.services import GraphServices


@pytest.mark.e2e
class TestProjectAmbiguity:
    def test_multiple_projects_do_not_cross_contaminate(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services

        rt.create_project("proj-a", "Dark City")
        rt.set_active("proj-a")
        proj_a = rt.get_active()
        assert proj_a is not None
        proj_a["idea"] = "A detective story."
        proj_a["current_phase"] = "constitution"
        rt.projects["proj-a"] = proj_a

        rt.create_project("proj-b", "Sunny Side")
        rt.set_active("proj-b")
        proj_b = rt.get_active()
        assert proj_b is not None
        proj_b["idea"] = "Two rival bakers fall in love."
        proj_b["current_phase"] = "development"
        rt.projects["proj-b"] = proj_b

        rt.set_active("proj-a")
        a = rt.get_active()
        assert a is not None
        assert a.get("current_phase") == "constitution"
        assert a.get("project_id") == "proj-a"

        rt.set_active("proj-b")
        b = rt.get_active()
        assert b is not None
        assert b.get("current_phase") == "development"
        assert b.get("project_id") == "proj-b"

        assert a.get("current_phase") != b.get("current_phase")

    def test_active_project_switching_preserves_state(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services

        rt.create_project("switch-a", "Switch A")
        rt.create_project("switch-b", "Switch B")

        rt.set_active("switch-a")
        proj_a = rt.get_active()
        assert proj_a is not None
        proj_a["idea"] = "Film A idea."
        proj_a["current_phase"] = "constitution"
        rt.projects["switch-a"] = proj_a

        rt.set_active("switch-b")
        proj_b = rt.get_active()
        assert proj_b is not None
        proj_b["idea"] = "Film B idea."
        proj_b["current_phase"] = "intake"
        rt.projects["switch-b"] = proj_b

        rt.set_active("switch-a")
        a_again = rt.get_active()
        assert a_again is not None
        assert a_again["current_phase"] == "constitution"
        assert a_again["idea"] == "Film A idea."
