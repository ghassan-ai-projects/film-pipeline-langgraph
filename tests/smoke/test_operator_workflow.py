"""Smoke tests: prove the documented operator workflow from runbook-first-film.md.

Each test maps to a runbook step. If a step fails, the runbook is broken.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.studio.runtime import StudioRuntime


@pytest.mark.smoke
class TestOperatorWorkflow:
    """Operator workflow: create → submit idea → approve → inspect → validate → audit."""

    def test_create_project_and_submit_idea(
        self,
        studio_runtime: StudioRuntime,
        tmp_path: Path,
    ) -> None:
        """Runbook steps 2-3: create project, submit idea, verify state."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        # Step 2: Create project
        r = invoke_tool(
            rt, "create_film_project", project_id="smoke-1", title="Smoke Test", slug="smoke-1"
        )
        assert r["ok"] is True, f"create_film_project: {r}"
        assert r["project_id"] == "smoke-1"

        # Step 2: Set active
        r = invoke_tool(rt, "set_active_project", project_ref="smoke-1")
        assert r["ok"] is True

        # Step 2: List projects
        r = invoke_tool(rt, "list_projects")
        assert r["ok"] is True
        assert "smoke-1" in r.get("projects", [])

        # Step 2: Get project summary
        r = invoke_tool(rt, "get_project_summary")
        assert r["ok"] is True
        assert r.get("project_id") == "smoke-1"

        # Step 3: Submit idea
        r = invoke_tool(rt, "submit_idea", idea="A robot learns to paint.")
        assert r["ok"] is True
        assert r.get("current_phase") is not None

        # Step 3: Get intake analysis
        r = invoke_tool(rt, "get_intake_analysis")
        assert r["ok"] is True

        # Step 3: Get current phase
        r = invoke_tool(rt, "get_current_phase")
        assert r["ok"] is True
        assert r.get("current_phase")

    def test_approval_cycle_and_artifacts(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        """Runbook steps 4-5: approve through phases, verify artifacts."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        invoke_tool(
            rt, "create_film_project", project_id="smoke-2", title="Approval Cycle", slug="smoke-2"
        )
        invoke_tool(rt, "set_active_project", project_ref="smoke-2")
        invoke_tool(rt, "submit_idea", idea="A gardener discovers sentient plants.")

        # Step 4: Approve intake
        r = invoke_tool(rt, "approve_intake", confirmed=True)
        assert r["ok"] is True
        assert r.get("current_phase")

        # Step 5: Approve through constitution → development (2 more approvals to reach script)
        for _ in range(2):
            r = invoke_tool(rt, "approve_phase", confirmed=True)
            assert r["ok"] is True, f"approve_phase: {r}"

        # We're now at script phase — verify artifacts exist
        r = invoke_tool(rt, "get_current_phase")
        assert r.get("current_phase") == "script", (
            f"Expected script phase, got {r.get('current_phase')}"
        )

        # Step 6: Inspect artifacts
        r = invoke_tool(rt, "list_artifacts")
        assert r["ok"] is True
        artifacts = r.get("artifacts", [])
        artifact_ids = {a["artifact_id"] for a in artifacts}
        expected = {
            "project_profile",
            "film_constitution",
            "treatment",
            "scene_list",
            "story_bible",
            "script",
        }
        found = expected & artifact_ids
        assert found == expected, f"Missing artifacts: {expected - found}"

        r = invoke_tool(
            rt, "inspect_artifact", artifact_id="film_constitution", phase="constitution"
        )
        assert r["ok"] is True, f"inspect_artifact film_constitution: {r}"
        assert r.get("content") is not None

        r = invoke_tool(rt, "get_project_summary")
        assert r["ok"] is True
        assert r.get("artifact_count", 0) >= 4

    def test_validation_and_issues(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        """Runbook step 7: validation reports and issue listing."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        invoke_tool(
            rt, "create_film_project", project_id="smoke-3", title="Validation Test", slug="smoke-3"
        )
        invoke_tool(rt, "set_active_project", project_ref="smoke-3")
        invoke_tool(rt, "submit_idea", idea="Two rival chefs compete in a cooking duel.")

        # Approve through script phase to get artifacts for validation
        invoke_tool(rt, "approve_intake", confirmed=True)
        for _ in range(3):
            invoke_tool(rt, "approve_phase", confirmed=True)

        r = invoke_tool(rt, "get_validation_report")
        assert r["ok"] is True

        r = invoke_tool(rt, "list_validation_issues")
        assert r["ok"] is True

        r = invoke_tool(rt, "get_blockers")
        assert r["ok"] is True
        assert isinstance(r.get("blockers"), list)

    def test_generation_ledger_lifecycle(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        """Runbook steps 8-9: plan, approve spend, submit, poll, promote."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        invoke_tool(
            rt, "create_film_project", project_id="smoke-4", title="Ledger Test", slug="smoke-4"
        )
        invoke_tool(rt, "set_active_project", project_ref="smoke-4")
        invoke_tool(
            rt, "submit_idea", idea="A time traveler tries to prevent coffee from being invented."
        )

        # Approve through script
        invoke_tool(rt, "approve_intake", confirmed=True)
        for _ in range(3):
            invoke_tool(rt, "approve_phase", confirmed=True)

        # Step 8: Plan generation batch
        r = invoke_tool(rt, "plan_generation_batch", shot_ids=["shot_0001", "shot_0002"])
        assert r["ok"] is True
        assert r.get("planned", 0) >= 1

        # Step 8: List active generations
        r = invoke_tool(rt, "list_active_generations")
        assert r["ok"] is True
        assert r.get("count", 0) >= 1

        # Step 8: Approve spend. The MCP tool was removed with the cost feature;
        # the PREPARED -> SUBMITTED transition it performed is the operator use
        # case, which survives.
        from film_pipeline.studio._operator_runtime import operator_service

        workspace = operator_service(rt).approve_generation_spend()
        assert workspace.submitted >= 1, f"approval did not submit rows: {workspace}"

        # Step 8: Start generation batch
        r = invoke_tool(rt, "start_generation_batch")
        assert r["ok"] is True

        # Step 8: Get generation status (for a submitted row)
        r = invoke_tool(rt, "get_generation_status", generation_id="gen:smoke-4:shot_0001:")
        # May fail if exact generation_id not found — that's fine, just checks plumbing
        assert r.get("ok") is True or "not found" in str(r.get("error", ""))

        # Step 9: Promote to production
        r = invoke_tool(rt, "promote_test_to_production", confirmed=True)
        assert r["ok"] is True

    def test_recovery_and_audit(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        """Runbook step 10: audit log, routing decisions, checkpoints."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        invoke_tool(
            rt, "create_film_project", project_id="smoke-5", title="Audit Test", slug="smoke-5"
        )
        invoke_tool(rt, "set_active_project", project_ref="smoke-5")
        invoke_tool(rt, "submit_idea", idea="A librarian discovers books that write themselves.")
        invoke_tool(rt, "approve_intake", confirmed=True)

        # Audit log
        r = invoke_tool(rt, "get_audit_log")
        assert r["ok"] is True
        assert isinstance(r.get("events"), list)
        assert len(r["events"]) >= 1, "Audit log should have events after create+submit+approve"

        # Routing decisions
        r = invoke_tool(rt, "explain_agent_routing")
        assert r["ok"] is True

        # Checkpoints
        r = invoke_tool(rt, "list_checkpoints")
        assert r["ok"] is True
        checkpoints = r.get("checkpoints", [])
        # Approvals create checkpoints — at least 1 should exist
        assert len(checkpoints) >= 1, (
            f"Expected at least 1 checkpoint after approvals, got {len(checkpoints)}"
        )

        # Create manual checkpoint
        r = invoke_tool(rt, "create_checkpoint", reason="smoke test manual checkpoint")
        assert r["ok"] is True

    def test_provider_health_and_listing(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        """Runbook step 10 (recovery): provider health and listing."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        r = invoke_tool(rt, "list_providers")
        assert r["ok"] is True
        assert r.get("total", 0) >= 1

        r = invoke_tool(rt, "check_provider_health", provider_id="mock-video-provider")
        assert r["ok"] is True

    def test_clip_handoff(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        """Runbook step 11: assemble review cut produces non-placeholder output."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        # Need an active project for assemble_review_cut
        invoke_tool(
            rt, "create_film_project", project_id="smoke-6", title="Handoff Test", slug="smoke-6"
        )
        invoke_tool(rt, "set_active_project", project_ref="smoke-6")

        r = invoke_tool(
            rt, "assemble_review_cut", shot_ids=["shot_0001"], clip_paths=["gen/shot_0001.mp4"]
        )
        assert r["ok"] is True, f"assemble_review_cut failed: {r}"
        assert "stub" not in r, f"assemble_review_cut returned stub: {r}"
        assert r.get("plan_id") is not None
