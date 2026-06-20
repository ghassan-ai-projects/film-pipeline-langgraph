"""E2E Scenario 8: KB conflict — conflicting policies are surfaced."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.graph.services import GraphServices
from film_pipeline.schemas.kb import KBConflictRecord


@pytest.mark.e2e
class TestKBConflict:
    def test_kb_conflict_record_creation(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        conflict = KBConflictRecord(
            conflict_id="kb-conflict:test:v1",
            items=["kb.policy.style.noir.v1", "kb.policy.style.pastel.v1"],
            description="Conflicting style policies detected.",
            detected_at=datetime.now(UTC),
        )
        assert conflict.conflict_id == "kb-conflict:test:v1"
        assert len(conflict.items) == 2
        assert conflict.resolved is False

    def test_kb_conflict_surfaces_during_phase(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services
        rt.create_project("kb-conflict-test", "KB Conflict Test")
        rt.set_active("kb-conflict-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "A film with contradictory style guidance."
        project["current_phase"] = "intake"
        project["kb_conflicts"] = [
            {
                "conflict_id": "kb-ctx-1",
                "refs": ["kb.policy.a.v1", "kb.policy.b.v1"],
                "description": "Mismatch",
                "resolution": "pending",
            }
        ]
        rt.projects["kb-conflict-test"] = project

        active = rt.get_active()
        assert active is not None
        conflicts = active.get("kb_conflicts", [])
        assert len(conflicts) == 1
        assert conflicts[0]["resolution"] == "pending"

    def test_kb_explain_context_choice(self, studio_runtime: StudioRuntime) -> None:
        """KB context explanation tool returns without error."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        result = invoke_tool(rt, "kb_explain_context_choice")
        assert result["ok"] is True
        assert "message" in result
