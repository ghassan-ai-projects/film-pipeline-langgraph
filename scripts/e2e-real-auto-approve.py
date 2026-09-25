"""E2E test: full pipeline via MCP tools in real mode with auto-approve.

Requires OPENROUTER_API_KEY and GOOGLE_API_KEY in .env.
Run: uv run python scripts/e2e-real-auto-approve.py
"""

import asyncio
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

os.chdir("/Users/ghassan/my-projects/film-pipeline-langgraph")
sys.path.insert(0, str(Path.cwd() / "src"))

# Load API keys
env_file = Path(".env")
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

os.environ["FILM_PIPELINE_MCP_MODE"] = "real"

from _scratch_bootstrap import use_scratch_roots

SCRATCH_ARTIFACTS = use_scratch_roots()

from film_pipeline.app.runtime import StudioRuntime, get_runtime


def invoke_tool(rt: StudioRuntime, tool_name: str, **args: Any) -> dict[str, Any]:
    """Synchronously invoke an MCP tool by name against the runtime."""
    import film_pipeline.app.runtime as rt_mod

    rt_mod._RUNTIME = rt

    async def _invoke() -> dict[str, Any]:
        mod = importlib.import_module("film_pipeline.mcp.tools")
        handler = getattr(mod, tool_name, None)
        if handler is None:
            raise ValueError(f"Unknown MCP tool: {tool_name}")
        result = await handler(dict(args))
        return result  # type: ignore[no-any-return]

    return asyncio.run(_invoke())


rt = get_runtime()
rt.server_mode = "real"

PROJECT_ID = "e2e-auto-001"
IDEA = (
    "A four-minute short film about an old clockmaker who discovers that "
    "one of his clocks can stop time for exactly sixty seconds. He uses "
    "this gift to complete the masterpiece his late wife always believed he could make."
)

print("=" * 70)
print("🎬 E2E: Real pipeline with auto-approve profile")
print(f"   Project: {PROJECT_ID}")
print(f"   OPENROUTER: {'✅' if os.environ.get('OPENROUTER_API_KEY') else '❌'}")
print(f"   GOOGLE:     {'✅' if os.environ.get('GOOGLE_API_KEY') else '❌'}")
print("=" * 70)

# Clean previous
import shutil

proj_dir = SCRATCH_ARTIFACTS / PROJECT_ID
if proj_dir.exists():
    shutil.rmtree(proj_dir)
for pid in list(rt.projects.keys()):
    if pid == PROJECT_ID:
        del rt.projects[pid]

# ── Create project with auto-approve ──────────────────────────────────────
print("\n📦 Creating project...")
r = invoke_tool(
    rt,
    "create_film_project",
    project_id=PROJECT_ID,
    title="The Clockmaker's Minute",
    slug="the-clockmakers-minute",
    runtime_mode="real",
    provider_profile="provider.seedance_primary",
    quality_profile="quality.studio",
    film_type_profile="film-type.narrative",
    auto_approve_profile="auto-approve",
)
print(f"   create: {r.get('ok')} | {r.get('project_id', r.get('error', ''))}")

r = invoke_tool(rt, "set_active_project", project_ref=PROJECT_ID)
print(f"   set_active: {r.get('ok')}")

r = invoke_tool(rt, "get_runtime_mode")
print(
    f"   mode: aligned={r.get('aligned')}, server={r.get('server_mode')}, runtime={r.get('runtime_mode')}"
)
if r.get("profile_stack"):
    print(f"   profile stack: {json.dumps(r['profile_stack'], indent=2)}")

# ── Submit idea ───────────────────────────────────────────────────────────
print(f"\n💡 Submitting idea ({len(IDEA)} chars)...")
r = invoke_tool(rt, "submit_idea", idea=IDEA)
print(f"   submit_idea: ok={r.get('ok')}, phase={r.get('current_phase', r.get('error', 'N/A'))}")

# ── Run through all phases ────────────────────────────────────────────────
PHASES = [
    "intake",
    "constitution",
    "development",
    "script",
    "visual_dev",
    "shot_bible",
    "gen_planning",
]

for phase in PHASES:
    # Check current phase
    r = invoke_tool(rt, "get_current_phase")
    current = r.get("current_phase", "unknown")
    print(f"\n⏳ Phase: {current}")

    if current == "completed":
        print("   Pipeline already completed.")
        break

    # Auto-approve should already be set, but call approve_phase to advance
    r = invoke_tool(rt, "approve_phase")
    ok = r.get("ok")
    new_phase = r.get("current_phase", r.get("error", "?"))
    artifacts = r.get("new_artifacts", [])

    if ok:
        arts = ", ".join(artifacts) if artifacts else "none"
        print(f"   ✅ approve_phase → next={new_phase} | artifacts=[{arts}]")
    else:
        error = r.get("error", str(r)[:200])
        # Check if it's blocking issues
        r2 = invoke_tool(rt, "get_blockers")
        blockers = r2.get("blocking_issues", [])
        print(f"   ⚠️  approve_phase FAILED: {error}")
        if blockers:
            for b in blockers[:5]:
                print(f"      - [{b.get('code', '?')}] {b.get('message', '')[:120]}")
        # Try request_revision + approve
        print("   🔄 Trying request_revision → approve_phase...")
        invoke_tool(rt, "request_revision")
        r = invoke_tool(rt, "approve_phase")
        print(f"   after revision: ok={r.get('ok')}, next={r.get('current_phase', '?')}")

# ── Check artifacts ───────────────────────────────────────────────────────
print(f"\n{'=' * 70}")
print("📦 Artifacts")
print("=" * 70)

r = invoke_tool(rt, "list_artifacts")
if r.get("ok"):
    artifacts = r.get("artifacts", [])
    print(f"   Count: {len(artifacts)}")
    for a in artifacts:
        aid = a.get("artifact_id", "?")
        phase = a.get("phase", "?")
        version = a.get("version", "?")
        status = a.get("status", "?")
        print(f"   v{version} [{status:12s}] {phase:15s} {aid}")
else:
    print(f"   ❌ list_artifacts failed: {r}")

# ── Inspect key artifacts ─────────────────────────────────────────────────
EXPECTED = {
    "project_profile": "intake",
    "film_constitution": "constitution",
    "treatment": "development",
    "scene_list": "development",
    "story_bible": "script",
    "script": "script",
}

print(f"\n{'=' * 70}")
print("🔍 Key artifact inspection")
print("=" * 70)

missing = []
for artifact_id, phase in EXPECTED.items():
    r = invoke_tool(rt, "inspect_artifact", artifact_id=artifact_id, phase=phase)
    if r.get("ok"):
        content = r.get("content", {})
        if isinstance(content, dict):
            preview = json.dumps(content, default=str)[:200]
        else:
            preview = str(content)[:200]
        print(f"   ✅ {artifact_id:25s} ({phase:15s}): {preview}")
    else:
        print(f"   ❌ {artifact_id:25s} ({phase:15s}): {r.get('error', 'not found')}")
        missing.append(artifact_id)

# ── Summary ────────────────────────────────────────────────────────────────
print(f"\n{'=' * 70}")
print("🏁 Summary")
print("=" * 70)

r = invoke_tool(rt, "get_orchestrator_summary")
if r.get("ok"):
    s = r
    print(f"   Phase: {s.get('current_phase', '?')}")
    print(f"   Approved: {s.get('approved')}")
    print(f"   Issues: {len(s.get('issues', []))}")
    print(f"   Decisions: {len(s.get('routing_decisions', []))}")

if missing:
    print(f"\n❌ MISSING ARTIFACTS ({len(missing)}): {', '.join(missing)}")
else:
    print(f"\n✅ All {len(EXPECTED)} expected artifacts present.")

# File listing
if proj_dir.exists():
    files = list(proj_dir.rglob("*.json"))
    print(f"\n📁 Files on disk: {len(files)}")
    for p in sorted(files):
        print(f"   {p.relative_to(proj_dir)}")
