#!/usr/bin/env python3
"""Real-mode MCP operator guide walkthrough test.

Follows docs/openclaw-mcp-operator-guide.md step-by-step with real providers.
Uses the "After the Fall" story from the operator guide examples.

Usage:
    FILM_PIPELINE_MCP_MODE=real uv run python scripts/test_real_mcp_operator.py
"""

import json
import os
import sys
from typing import Any

# Force real mode before any imports that read the env var
os.environ["FILM_PIPELINE_MCP_MODE"] = "real"

from film_pipeline.app.runtime import StudioRuntime, create_runtime

# Colors for output
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RESET = "\033[0m"
BOLD = "\033[1m"


def invoke_tool(rt: StudioRuntime, tool_name: str, **args: Any) -> dict[str, Any]:
    """Synchronously invoke an MCP tool by name against the runtime."""
    import asyncio
    import importlib

    import film_pipeline.app.runtime as rt_mod

    rt_mod._RUNTIME = rt

    async def _invoke() -> dict[str, Any]:
        mod = importlib.import_module("film_pipeline.mcp.tools")
        handler = getattr(mod, tool_name, None)
        if handler is None:
            return {"ok": False, "error": f"Unknown tool: {tool_name}"}
        try:
            return await handler(dict(args))
        except Exception as exc:
            return {"ok": False, "error": str(exc), "tool": tool_name}

    return asyncio.run(_invoke())


def step(name: str) -> None:
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}  STEP: {name}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}")


def show(r: dict[str, Any], label: str = "Result") -> None:
    """Pretty-print a tool result."""
    ok = r.get("ok", False)
    color = GREEN if ok else RED
    icon = "✓" if ok else "✗"
    print(f"\n{color}{icon} {label}{RESET}: ok={ok}")

    # Show key fields
    for key in [
        "server_mode",
        "runtime_mode",
        "project_runtime_mode",
        "aligned",
        "project_id",
        "current_phase",
        "next_action",
        "route_reason",
        "issue_count",
        "profile_count",
        "provider_count",
        "approved",
    ]:
        if key in r:
            print(f"  {key}: {r[key]}")

    # Show error if present
    if not ok and "error" in r:
        print(f"  {RED}error: {r['error']}{RESET}")

    # For deeper inspection, show profile_stack
    if "profile_stack" in r:
        print(f"  profile_stack: {json.dumps(r['profile_stack'], indent=4)}")

    # Full output for debugging
    if os.getenv("VERBOSE"):
        print(json.dumps(r, indent=2, default=str))


def main() -> int:
    print(f"{BOLD}{YELLOW}Real-Mode MCP Operator Guide Walkthrough{RESET}")
    print(f"API keys: OPENROUTER={os.getenv('OPENROUTER_API_KEY', 'MISSING')[:15]}...")
    print(f"           GOOGLE={os.getenv('GOOGLE_API_KEY', 'MISSING')[:15]}...")
    print(f"Mode: FILM_PIPELINE_MCP_MODE={os.getenv('FILM_PIPELINE_MCP_MODE')}")

    # ── Create runtime ──────────────────────────────────────────────
    step("Create real-mode runtime")
    rt = create_runtime("real")
    print(f"Runtime created: server_mode={rt.server_mode}")
    print(f"Services: {type(rt.services).__name__}")

    failures: list[str] = []

    # ── Step 2: Discover & Inspect Profiles ─────────────────────────
    step("Step 2: list_profiles")
    r = invoke_tool(rt, "list_profiles")
    show(r, "list_profiles")
    if not r.get("ok"):
        failures.append("list_profiles failed")
        print(f"{RED}  Profile list failed — cannot continue profile inspection{RESET}")
    else:
        profile_count = r.get("profile_count", 0)
        r.get("profiles", [])
        print(f"  Found {profile_count} profiles")

    # Inspect key profiles
    for pid in [
        "provider.seedance_primary",
        "quality.studio",
        "film-type.narrative",
        "review.strict_continuity",
        "local-real-provider",
    ]:
        step(f"Step 2: inspect_profile({pid})")
        r = inspect(rt, pid)
        show(r, f"inspect_profile({pid})")
        if not r.get("ok"):
            print(f"{YELLOW}  ⚠ Profile '{pid}' inspection returned issues{RESET}")

    # ── Step 3: Create Project ──────────────────────────────────────
    step("Step 3: create_film_project (real mode)")
    r = invoke_tool(
        rt,
        "create_film_project",
        project_id="after-the-fall-001",
        title="After the Fall",
        slug="after-the-fall",
        runtime_mode="real",
        provider_profile="provider.seedance_primary",
        quality_profile="quality.studio",
        film_type_profile="film-type.narrative",
        review_profile="review.strict_continuity",
    )
    show(r, "create_film_project")
    if not r.get("ok"):
        failures.append(f"create_film_project: {r.get('error', 'unknown')}")
        print(f"{RED}  CRITICAL: Project creation failed{RESET}")
        # Continue to test remaining tools that don't require a project
    else:
        # Set active project
        step("set_active_project")
        r2 = invoke_tool(rt, "set_active_project", project_ref="after-the-fall-001")
        show(r2, "set_active_project")
        if not r2.get("ok"):
            failures.append("set_active_project failed")

    # ── Step 4: Verify Alignment ────────────────────────────────────
    step("Step 4: get_runtime_mode")
    r = invoke_tool(rt, "get_runtime_mode")
    show(r, "get_runtime_mode")
    if not r.get("ok"):
        failures.append(f"get_runtime_mode: {r.get('error', 'unknown')}")
    else:
        aligned = r.get("aligned")
        if aligned:
            print(f"{GREEN}  ✓ Server and project modes are aligned{RESET}")
        else:
            print(f"{RED}  ✗ Server and project modes are MISALIGNED{RESET}")
            failures.append("Mode misalignment detected")

    # ── Step 4.5: List Providers ────────────────────────────────────
    step("Step 4.5: list_providers")
    r = invoke_tool(rt, "list_providers")
    show(r, "list_providers")
    if r.get("ok"):
        providers = r.get("providers", [])
        print(f"  Registered providers: {providers}")

    # ── Submit Idea ─────────────────────────────────────────────────
    step("submit_idea")
    r = invoke_tool(
        rt,
        "submit_idea",
        idea="A lone survivor emerges from underground after a global collapse, discovering that the real threat is not the ruined world but the remnants of human ambition.",
    )
    show(r, "submit_idea")
    if not r.get("ok"):
        failures.append(f"submit_idea: {r.get('error', 'unknown')}")

    # ── Intake Analysis ─────────────────────────────────────────────
    step("get_intake_analysis")
    r = invoke_tool(rt, "get_intake_analysis")
    show(r, "get_intake_analysis")
    if not r.get("ok"):
        failures.append(f"get_intake_analysis: {r.get('error', 'unknown')}")

    # ── Approve Intake ──────────────────────────────────────────────
    step("approve_intake")
    r = invoke_tool(rt, "approve_intake")
    show(r, "approve_intake")
    if r.get("ok"):
        print(f"  current_phase: {r.get('current_phase')}")
    else:
        failures.append(f"approve_intake: {r.get('error', 'unknown')}")

    # ── Approve through phases ──────────────────────────────────────
    for phase_name in ["constitution", "development", "script"]:
        step(f"approve_phase → {phase_name}")
        r = invoke_tool(rt, "approve_phase")
        show(r, f"approve_phase → {phase_name}")
        if not r.get("ok"):
            failures.append(f"approve_phase ({phase_name}): {r.get('error', 'unknown')}")
            break
        print(f"  Now at phase: {r.get('current_phase')}")

    # ── Orchestrator Summary ────────────────────────────────────────
    step("get_orchestrator_summary")
    r = invoke_tool(rt, "get_orchestrator_summary")
    show(r, "get_orchestrator_summary")
    if r.get("ok"):
        print(f"  next_action: {r.get('next_action')}")
        print(f"  route_reason: {r.get('route_reason')}")
        print(f"  eligible_actions: {r.get('eligible_actions')}")
        print(f"  blocked_actions: {r.get('blocked_actions')}")
        print(f"  candidate_refs: {r.get('candidate_refs')}")
        print(f"  approved_refs: {r.get('approved_refs')}")
        print(f"  pending_revisions: {r.get('pending_revisions')}")
        print(f"  budget_snapshot: {r.get('budget_snapshot')}")
    else:
        failures.append(f"get_orchestrator_summary: {r.get('error', 'unknown')}")

    # ── Review Phase Artifacts ──────────────────────────────────────
    step("review_phase_artifacts")
    r = invoke_tool(rt, "review_phase_artifacts")
    show(r, "review_phase_artifacts")
    if r.get("ok"):
        rp = r.get("review_package", {})
        print(f"  review_package_id: {rp.get('review_package_id')}")
        print(f"  phase: {rp.get('phase')}")
        print(f"  orchestrator_recommendation: {rp.get('orchestrator_recommendation')}")
        print(f"  available_actions: {rp.get('available_actions')}")
        print(f"  blocked_actions: {rp.get('blocked_actions')}")
    else:
        failures.append(f"review_phase_artifacts: {r.get('error', 'unknown')}")

    # ── Get Blockers ────────────────────────────────────────────────
    step("get_blockers")
    r = invoke_tool(rt, "get_blockers")
    show(r, "get_blockers")
    if r.get("ok"):
        blockers = r.get("blockers", [])
        print(f"  Blockers: {len(blockers)}")
        for b in blockers:
            print(f"    - {b.get('phase', '?')}: {b.get('reason', '?')} [{b.get('severity', '?')}]")

    # ── Get Next Actions ────────────────────────────────────────────
    step("get_next_actions")
    r = invoke_tool(rt, "get_next_actions")
    show(r, "get_next_actions")
    if r.get("ok"):
        print(f"  next_action: {r.get('next_action')}")
        print(f"  eligible_actions: {r.get('eligible_actions')}")

    # ── List Artifacts ──────────────────────────────────────────────
    step("list_artifacts")
    r = invoke_tool(rt, "list_artifacts")
    show(r, "list_artifacts")
    if r.get("ok"):
        artifacts = r.get("artifacts", [])
        print(f"  Artifacts: {len(artifacts)}")
        for a in artifacts[:10]:
            print(
                f"    - {a.get('artifact_id', '?')} (type={a.get('artifact_type', '?')}, v{a.get('version', '?')}, {a.get('status', '?')})"
            )

    # ── Get Current Phase ───────────────────────────────────────────
    step("get_current_phase")
    r = invoke_tool(rt, "get_current_phase")
    show(r, "get_current_phase")
    if r.get("ok"):
        print(f"  current_phase: {r.get('current_phase')}")

    # ── Get Project Summary ─────────────────────────────────────────
    step("get_project_summary")
    r = invoke_tool(rt, "get_project_summary")
    show(r, "get_project_summary")

    # ── List Checkpoints ────────────────────────────────────────────
    step("list_checkpoints")
    r = invoke_tool(rt, "list_checkpoints")
    show(r, "list_checkpoints")
    if r.get("ok"):
        checkpoints = r.get("checkpoints", [])
        print(f"  Checkpoints: {len(checkpoints)}")

    # ── Get Audit Log ───────────────────────────────────────────────
    step("get_audit_log")
    r = invoke_tool(rt, "get_audit_log", limit=20)
    show(r, "get_audit_log")
    if r.get("ok"):
        events = r.get("events", [])
        print(f"  Audit events: {len(events)}")

    # ── Report ──────────────────────────────────────────────────────
    print(f"\n{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}RESULTS SUMMARY{RESET}")
    print(f"{'=' * 70}")
    if failures:
        print(f"{RED}FAILURES ({len(failures)}):{RESET}")
        for f in failures:
            print(f"  {RED}✗{RESET} {f}")
    else:
        print(f"{GREEN}✓ All operator guide steps passed{RESET}")

    print(f"\n{BOLD}Next steps from operator guide:{RESET}")
    print("  4.5a generate_character_bible")
    print("  4.5b generate_environment_bible")
    print("  4.5c generate_camera_bible")
    print("  4.5d generate_style_bible")
    print("  5. generate_reference_images")
    print("  6a. generate_shot_bible")
    print("  6b. initialize_budget + generate_plan")
    print("  6c. run_validation")
    print("  6d. plan_generation_batch → approve_generation_spend → start_generation_batch")
    print("  6e. assemble_review_cut")
    print("  6f. create_checkpoint")

    return 1 if failures else 0


def inspect(rt: StudioRuntime, profile_id: str) -> dict[str, Any]:
    """Wrapper that calls inspect_profile, handling any errors."""
    return invoke_tool(rt, "inspect_profile", profile_id=profile_id)


if __name__ == "__main__":
    sys.exit(main())
