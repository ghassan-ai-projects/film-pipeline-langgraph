"""Manual reference smoke test for a 4-minute mock short film.

It drives the real MCP workflow through the supported pre-generation path and
stops before actual clip execution.
"""

from __future__ import annotations

import pytest

from film_pipeline.studio.runtime import StudioRuntime


@pytest.mark.smoke
class TestManualFourMinuteMockShort:
    def test_full_pre_generation_pipeline_for_four_minute_short(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        project_id = "manual-4min-short"
        idea = (
            "A silent four-minute pilgrimage short follows a young walker crossing five "
            "changing fields while birds, rain, blossoms, and insects pass a single "
            "message between sky and earth."
        )

        result = invoke_tool(
            rt,
            "create_film_project",
            project_id=project_id,
            title="The Field Message",
            slug="the-field-message",
        )
        assert result["ok"] is True, f"create_film_project failed: {result}"

        result = invoke_tool(rt, "set_active_project", project_ref=project_id)
        assert result["ok"] is True, f"set_active_project failed: {result}"

        result = invoke_tool(rt, "submit_idea", idea=idea)
        assert result["ok"] is True, f"submit_idea failed: {result}"

        result = invoke_tool(rt, "approve_intake", confirmed=True)
        assert result["ok"] is True, f"approve_intake failed: {result}"

        expected_phase_progression = [
            "development",
            "script",
            "visual_dev",
            "shot_bible",
            "gen_planning",
        ]
        for expected_phase in expected_phase_progression:
            result = invoke_tool(rt, "approve_phase", confirmed=True)
            assert result["ok"] is True, f"approve_phase failed before {expected_phase}: {result}"
            phase_result = invoke_tool(rt, "get_current_phase")
            assert phase_result["ok"] is True
            assert phase_result["current_phase"] == expected_phase

        # The cost_estimate artifact was removed with the cost feature. The
        # planning gate now sources its clip count from the shot matrix, so the
        # proof that gen_planning produced something is the matrix it consumed.
        result = invoke_tool(rt, "inspect_artifact", artifact_id="shot_matrix", phase="shot_bible")
        assert result["ok"] is True, f"inspect_artifact shot_matrix failed: {result}"

        result = invoke_tool(
            rt,
            "plan_generation_batch",
            shot_ids=["shot_0001"],
            provider="mock-video-provider",
            model="mock-fast",
            mode="test",
        )
        assert result["ok"] is True, f"plan_generation_batch failed: {result}"
        assert result.get("planned", 0) >= 1

        from film_pipeline.studio._operator_runtime import operator_service

        workspace = operator_service(rt).approve_generation_spend()
        assert workspace.submitted >= 1, f"approval did not submit rows: {workspace}"

        result = invoke_tool(rt, "approve_phase", confirmed=True)
        assert result["ok"] is True, f"approve_phase gen_planning->generation failed: {result}"
        phase_result = invoke_tool(rt, "get_current_phase")
        assert phase_result["current_phase"] == "generation"

        # Stop before actual clip execution, but still advance into QC-ready state.
        result = invoke_tool(rt, "approve_phase", confirmed=True)
        assert result["ok"] is True, f"approve_phase generation->qc failed: {result}"
        phase_result = invoke_tool(rt, "get_current_phase")
        assert phase_result["current_phase"] == "qc"

        summary = invoke_tool(rt, "get_project_summary")
        assert summary["ok"] is True
        assert summary.get("artifact_count", 0) >= 9

        report = invoke_tool(rt, "get_validation_report")
        assert report["ok"] is True

        routing = invoke_tool(rt, "explain_agent_routing")
        assert routing["ok"] is True
        assert routing.get("decisions"), "Expected routing decisions after phase execution"

        audit = invoke_tool(rt, "get_audit_log")
        assert audit["ok"] is True
        assert len(audit.get("events", [])) >= 1

        checkpoints = invoke_tool(rt, "list_checkpoints")
        assert checkpoints["ok"] is True
        assert len(checkpoints.get("checkpoints", [])) >= 1
