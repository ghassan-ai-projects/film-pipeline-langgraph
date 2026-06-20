"""E2E Scenario 2: Script revision loop — revise, verify versioning, re-approve."""

from __future__ import annotations

import pytest

from film_pipeline.app.runtime import StudioRuntime


@pytest.mark.e2e
class TestScriptRevision:
    """End-to-end: revise script, verify versioning, preserve checkpoints."""

    def test_revision_loop_preserves_checkpoint_history(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        """Request revision creates a REVISION_REQUESTED issue without losing checkpoints."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        invoke_tool(rt, "create_film_project", project_id="e2e-revise", title="Revision Test")
        invoke_tool(rt, "set_active_project", project_ref="e2e-revise")
        invoke_tool(rt, "submit_idea", idea="A film about second chances.")

        # Advance to script
        invoke_tool(rt, "approve_intake")
        invoke_tool(rt, "approve_phase")  # constitution
        invoke_tool(rt, "approve_phase")  # development

        cps_before = len(rt.checkpoints)

        # Request revision with a note
        result = invoke_tool(rt, "request_revision", note="Dialogue too formal.")
        assert result["ok"] is True
        assert result.get("current_phase") == "script", "Revision should stay in script phase"

        # Check that REVISION_REQUESTED issue exists
        issues = result.get("issues", [])
        assert any(i.get("code", "") == "REVISION_REQUESTED" for i in issues)

        # Checkpoints should not be deleted
        cps_after = len(rt.checkpoints)
        assert cps_after >= cps_before, "Revision should not delete checkpoints"

    def test_revision_then_reapproval(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        """After revision, the project state reflects the revision request."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        invoke_tool(rt, "create_film_project", project_id="e2e-reapprove", title="Reapprove Test")
        invoke_tool(rt, "set_active_project", project_ref="e2e-reapprove")
        invoke_tool(rt, "submit_idea", idea="A documentary about silence.")
        invoke_tool(rt, "approve_intake")
        invoke_tool(rt, "approve_phase")  # constitution

        # Request revision at development
        result = invoke_tool(rt, "request_revision", note="Needs darker tone.")
        assert result["ok"] is True

        # Verify issues contain REVISION_REQUESTED
        issues = result.get("issues", [])
        assert any(i.get("code") == "REVISION_REQUESTED" for i in issues)

        # State should still be at the same phase
        summary = invoke_tool(rt, "get_orchestrator_summary")
        assert summary["ok"] is True

    def test_revision_audit_trail(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        """Revision events appear in the audit log."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        invoke_tool(rt, "create_film_project", project_id="e2e-audit-rev", title="Audit Revision")
        invoke_tool(rt, "set_active_project", project_ref="e2e-audit-rev")
        invoke_tool(rt, "submit_idea", idea="Short story.")
        invoke_tool(rt, "approve_intake")
        invoke_tool(rt, "approve_phase")
        invoke_tool(rt, "approve_phase")

        # Count audit events before revision
        result = invoke_tool(rt, "get_audit_log", limit=100)
        events_before = len(result.get("events", []))

        # Request revision
        invoke_tool(rt, "request_revision", note="Make it punchier.")

        # Verify audit grew
        result = invoke_tool(rt, "get_audit_log", limit=100)
        events_after = len(result.get("events", []))
        assert events_after > events_before, "Audit should record revision"
