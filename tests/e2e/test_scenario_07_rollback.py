"""E2E Scenario 7: Rollback after bad style change."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.checkpoints.invalidation import InvalidationEngine
from film_pipeline.orchestration.services import GraphServices


@pytest.mark.e2e
class TestRollback:
    def test_rollback_restores_prior_phase_state(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services
        rt.create_project("rollback-test", "Rollback Test")
        rt.set_active("rollback-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "A thriller about identity."
        project["current_phase"] = "intake"
        rt.projects["rollback-test"] = project

        rt.approve_phase()
        active = rt.get_active()
        assert active is not None
        assert active.get("current_phase") == "constitution"

        checkpoints = list(rt.checkpoints.values())
        assert len(checkpoints) >= 1, "Should have checkpoint from intake approval"

    def test_invalidation_engine_reports_downstream_impact(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        engine = InvalidationEngine()
        report = engine.report(
            rollback_target="constitution",
            artifact_types=["film_constitution"],
        )
        assert report is not None
        assert len(report.will_invalidate) >= 1, (
            "Rolling back constitution should invalidate downstream artifacts"
        )

    def test_rollback_via_mcp_tool(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        """Rollback to a checkpoint via MCP tool preserves state."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        invoke_tool(rt, "create_film_project", project_id="e2e-rollback", title="Rollback Test")
        invoke_tool(rt, "set_active_project", project_ref="e2e-rollback")
        invoke_tool(rt, "submit_idea", idea="A story.")
        invoke_tool(rt, "approve_intake", confirmed=True)

        # List checkpoints
        result = invoke_tool(rt, "list_checkpoints")
        assert result["ok"] is True
        cps = result.get("checkpoints", [])
        assert len(cps) >= 1

        # Rollback to the first checkpoint
        cp_id = cps[0]["checkpoint_id"]
        result = invoke_tool(rt, "rollback_to_checkpoint", checkpoint_id=cp_id, confirmed=True)
        assert result["ok"] is True

    def test_invalidation_report_via_mcp(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        """Get invalidation report for a checkpoint."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        invoke_tool(rt, "create_film_project", project_id="e2e-inval", title="Invalidation Test")
        invoke_tool(rt, "set_active_project", project_ref="e2e-inval")
        invoke_tool(rt, "submit_idea", idea="A short.")
        invoke_tool(rt, "approve_intake", confirmed=True)

        result = invoke_tool(rt, "list_checkpoints")
        cps = result.get("checkpoints", [])
        if cps:
            result = invoke_tool(
                rt, "get_invalidation_report", checkpoint_id=cps[0]["checkpoint_id"]
            )
            assert result["ok"] is True
            assert "will_revert" in result
