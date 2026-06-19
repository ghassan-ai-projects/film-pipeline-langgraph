"""E2E Scenario 2: Script revision loop — revise script, verify persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.graph.services import GraphServices


@pytest.mark.e2e
class TestScriptRevision:
    def test_revision_creates_new_issue_and_preserves_state(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services

        rt.create_project("revision-test", "Revision Test")
        rt.set_active("revision-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "A film about second chances."
        project["current_phase"] = "script"
        rt.projects["revision-test"] = project

        # Request revision
        result = rt.request_revision("The dialogue feels too formal.")
        assert result.get("current_phase") == "script"
        issues = result.get("issues", [])
        assert any(i.get("code") == "REVISION_REQUESTED" for i in issues), (
            "Revision should add REVISION_REQUESTED issue"
        )
        assert result.get("project_id") == "revision-test"

    def test_revision_preserves_checkpoint_history(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services

        rt.create_project("cp-revision-test", "CP Test")
        rt.set_active("cp-revision-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "A documentary about silence."
        project["current_phase"] = "intake"
        rt.projects["cp-revision-test"] = project

        # Run a phase and approve to generate a checkpoint
        rt.approve_phase()
        checkpoints_before = len(rt.checkpoints)
        assert checkpoints_before >= 1, f"Should have ≥1 checkpoint, got {checkpoints_before}"

        # Advance to script manually
        active = rt.get_active()
        assert active is not None
        active["current_phase"] = "script"
        rt.projects["cp-revision-test"] = active

        rt.request_revision("Needs darker tone.")
        checkpoints_after = len(rt.checkpoints)
        assert checkpoints_after >= checkpoints_before, "Revision should not delete checkpoints"
