"""E2E Scenario 1: Happy path — idea → review cut with real artifacts via MCP."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.studio.runtime import StudioRuntime


@pytest.mark.e2e
class TestHappyPath:
    """End-to-end: a mini-film goes from idea through all phases producing real artifacts."""

    def test_full_mcp_driven_happy_path(
        self,
        studio_runtime: StudioRuntime,
        tmp_path: Path,
    ) -> None:
        """Drive idea → script approval entirely through MCP tools.

        Verifies artifacts are persisted at each phase and approvals create checkpoints.
        """
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        # ── 1. Create project ──────────────────────────────────────────
        result = invoke_tool(
            rt,
            "create_film_project",
            project_id="e2e-happy",
            title="The Last Launch",
            slug="last-launch",
        )
        assert result["ok"] is True, f"create_film_project failed: {result}"
        assert result["project_id"] == "e2e-happy"

        # ── 2. Set active project ──────────────────────────────────────
        result = invoke_tool(rt, "set_active_project", project_ref="e2e-happy")
        assert result["ok"] is True, f"set_active_project failed: {result}"

        # ── 3. Submit idea ─────────────────────────────────────────────
        result = invoke_tool(
            rt, "submit_idea", idea="A dying astronaut sends one last message home."
        )
        assert result["ok"] is True, f"submit_idea failed: {result}"
        assert result.get("current_phase") is not None

        # ── 4. Get intake analysis ─────────────────────────────────────
        result = invoke_tool(rt, "get_intake_analysis")
        assert result.get("ok") is True, f"get_intake_analysis failed: {result}"
        analysis = result.get("analysis", {})
        assert analysis, "Intake analysis should not be empty"

        # ── 5. Approve intake → creates checkpoint, advances ──────────
        checkpoints_before = len(rt.checkpoints)
        result = invoke_tool(rt, "approve_intake", confirmed=True)
        assert result["ok"] is True, f"approve_intake failed: {result}"
        new_phase = result.get("current_phase", "")
        assert new_phase != "intake", "Should advance past intake"
        # Verify checkpoint was created
        assert len(rt.checkpoints) > checkpoints_before, "Approve should create checkpoint"

        # ── 6. Approve remaining phases to reach script ────────────────
        for expected_phase in ("constitution", "development"):
            result = invoke_tool(rt, "approve_phase", confirmed=True)
            assert result["ok"] is True, f"approve_phase failed at {expected_phase}: {result}"

        # ── 7. Verify artifacts exist ──────────────────────────────────
        artifacts_result = invoke_tool(rt, "list_artifacts")
        assert artifacts_result["ok"] is True
        artifacts = artifacts_result.get("artifacts", [])
        assert len(artifacts) > 0, "At least one artifact should exist"

        # ── 8. Get orchestrator summary ────────────────────────────────
        result = invoke_tool(rt, "get_orchestrator_summary")
        assert result["ok"] is True
        assert result.get("current_phase") == "script"

        # ── 9. Verify checkpoints accumulated ─────────────────────────
        result = invoke_tool(rt, "list_checkpoints")
        assert result["ok"] is True
        cps = result.get("checkpoints", [])
        assert len(cps) >= 3, f"Expected ≥3 checkpoints, got {len(cps)}"

        # ── 10. Verify audit trail ─────────────────────────────────────
        result = invoke_tool(rt, "get_audit_log", limit=50)
        assert result["ok"] is True
        events = result.get("events", [])
        assert len(events) > 0, "Audit log should have events"

    def test_approval_creates_persisted_state(self, studio_runtime: StudioRuntime) -> None:
        """After approving a phase, the state change is durable (survives re-get)."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        invoke_tool(rt, "create_film_project", project_id="e2e-persist", title="Persist Test")
        invoke_tool(rt, "set_active_project", project_ref="e2e-persist")
        invoke_tool(rt, "submit_idea", idea="A story about memory.")

        # Approve intake
        invoke_tool(rt, "approve_intake", confirmed=True)

        # Re-get active project and verify phase advanced
        result = invoke_tool(rt, "get_active_project")
        assert result["ok"] is True
        phase = result.get("current_phase", "")
        assert phase != "intake", f"Phase should have advanced beyond intake, got: {phase}"
        assert phase != "", "Phase should not be empty after approval"

    def test_artifact_inspectability(self, studio_runtime: StudioRuntime) -> None:
        """After artifacts are created, they can be inspected."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        invoke_tool(rt, "create_film_project", project_id="e2e-inspect", title="Inspect Test")
        invoke_tool(rt, "set_active_project", project_ref="e2e-inspect")
        invoke_tool(rt, "submit_idea", idea="A silent film about movement.")

        # List artifacts early (should be empty or have intake analysis)
        result = invoke_tool(rt, "list_artifacts")
        assert result["ok"] is True
        artifacts = result.get("artifacts", [])
        # At minimum, the list should return without error
        assert isinstance(artifacts, list)

    def test_validation_report_available(self, studio_runtime: StudioRuntime) -> None:
        """Validation reports can be fetched for the current phase."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        invoke_tool(rt, "create_film_project", project_id="e2e-validate", title="Validate Test")
        invoke_tool(rt, "set_active_project", project_ref="e2e-validate")
        invoke_tool(rt, "submit_idea", idea="An action film.")

        # Advance to script phase (approve_intake then 2 approve_phase)
        result = invoke_tool(rt, "approve_intake", confirmed=True)
        assert result["ok"] is True
        for _ in range(2):
            result = invoke_tool(rt, "approve_phase", confirmed=True)
            assert result["ok"] is True

        # Get validation report (script phase has validators)
        result = invoke_tool(rt, "get_validation_report")
        assert result["ok"] is True
        # May return empty reports if none stored, but should return without error
        assert "phase" in result
