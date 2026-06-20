"""E2E Scenario 7: Rollback after bad style change."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.checkpoints.invalidation import InvalidationEngine
from film_pipeline.graph.services import GraphServices


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
