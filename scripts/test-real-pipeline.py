"""Run full pipeline in REAL mode through the runtime API (bypasses MCP envelope routing bug).

The MCP server's create_film_project registers with the runtime but not with the
MCPServer's ProjectRegistry, causing set_active_project and all subsequent MCP calls
to fail with "No active project."  This test calls the runtime directly.

REAL MODE: uses actual LLM via OpenRouter
"""

import json
import os
import sys
from pathlib import Path

os.chdir("/Users/ghassan/my-projects/film-pipeline-langgraph")

# Load API keys from .env
with open(".env") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

# Force real mode
os.environ["FILM_PIPELINE_MCP_MODE"] = "real"

print("🚀 Running pipeline in REAL mode")
print(f"   OPENROUTER_API_KEY: set={bool(os.environ.get('OPENROUTER_API_KEY'))}")
print(f"   GOOGLE_API_KEY: set={bool(os.environ.get('GOOGLE_API_KEY'))}")

from film_pipeline.app.runtime import get_runtime
from film_pipeline.schemas._base import FilmPhase

rt = get_runtime()
rt.server_mode = "real"  # Force real mode on the runtime

PROJECT_ID = "the-last-dragon-vein-003"
print(f"\n🎬 Creating project: {PROJECT_ID}")

# Clean previous runs
for pid in list(rt.projects.keys()):
    if pid == PROJECT_ID:
        del rt.projects[pid]

import shutil

proj_dir = Path("projects") / PROJECT_ID
if proj_dir.exists():
    shutil.rmtree(proj_dir)

# ===== STEP 1: Create + submit idea =====
rt.create_project(project_id=PROJECT_ID, title="The Last Dragon Vein", slug="the-last-dragon-vein")
rt.set_active(PROJECT_ID)

active = rt.get_active()
# Set real config
active["runtime_mode"] = "real"
active["server_mode"] = "real"
active["profile_stack"] = {
    "film_type_profile": "film-type.narrative",
    "quality_profile": "quality.studio",
    "provider_profile": "provider.seedance_primary",
    "review_profile": "review.strict_continuity",
}

story = """A short film about an old Chinese ink wash painter living alone in a remote mountain village.
He has spent 70 years perfecting a single brushstroke — the 'dragon vein' stroke that brings
his paintings to life. When a young city photographer arrives documenting vanishing traditions,
the painter reluctantly teaches her his technique over one transformative autumn. Their unlikely
friendship bridges two worlds: analog vs digital, ancient vs modern, stillness vs speed.
The climax comes when the painter, facing his final stroke, must decide whether to complete
his masterpiece or leave it unfinished — a choice that will define whether his art lives
beyond him."""

active["idea"] = story
print("⏳ Running intake node (calling model via OpenRouter)...")
sys.stdout.flush()
state = rt.run_graph(active)
rt.projects[PROJECT_ID] = state
print(f"✅ Idea submitted. Phase: {state.get('current_phase')}")

# ===== STEP 2-8: Approve through all phases =====
for phase, label in [
    ("intake", "APPROVE INTAKE"),
    ("constitution", "APPROVE CONSTITUTION"),
    ("development", "APPROVE DEVELOPMENT"),
    ("script", "APPROVE SCRIPT"),
    ("visual_dev", "APPROVE VISUAL DEV"),
    ("shot_bible", "APPROVE SHOT BIBLE"),
    ("gen_planning", "APPROVE GEN PLANNING"),
    ("generation", "APPROVE GENERATION"),
]:
    active_phase = rt.get_active().get("current_phase", "")
    if not active_phase or active_phase == "completed":
        print("⏹️  Pipeline completed")
        break

    try:
        print(f"\n⏳ {label} (phase={active_phase})...")
        sys.stdout.flush()
        state = rt.approve_phase()
        rt.projects[PROJECT_ID] = state
        print(f"✅ {label}: → next={state.get('current_phase', '<done>')}")
    except ValueError as e:
        print(f"❌ {label}: {e}")
        break

# ===== Check artifacts =====
store = rt.services.artifact_store


def list_artifacts():
    results = {}
    for phase in list(FilmPhase):
        try:
            artifacts = store.list_artifacts(PROJECT_ID, phase)
            for a in artifacts:
                key = f"{a.phase.value!s:25s} / {a.artifact_id:30s}"
                results[key] = {
                    "v": a.version,
                    "t": str(a.artifact_type.value)[:20],
                    "s": str(a.status.value)[:15],
                }
        except Exception:
            pass
    return results


artifacts = list_artifacts()
print(f"\n📦 Artifacts stored ({len(artifacts)} total):")
for key, meta in sorted(artifacts.items()):
    print(f"   v{meta['v']:3d} {meta['t']:20s} {meta['s']:15s} | {key}")

# ===== Print key artifact contents =====
print("\n📄 Key artifact previews:")
store = rt.services.artifact_store
for aid_name in [
    "project_profile",
    "film_constitution",
    "treatment",
    "scene_list",
    "story_bible",
    "script",
]:
    for phase in list(FilmPhase):
        try:
            data = store.load(PROJECT_ID, phase, aid_name, 1)
            if data:
                cls_name = type(data).__name__
                text = json.dumps(data, indent=2, default=str, ensure_ascii=False)[:800]
                print(f"\n{'-' * 60}")
                print(f"📄 {aid_name} (v1, {cls_name}):")
                print(text)
                break
        except (FileNotFoundError, ValueError):
            pass

# Final state
active = rt.get_active()
if active:
    print(f"\n{'=' * 60}")
    print("🏁 FINAL STATE")
    print(f"{'=' * 60}")
    print(f"   Phase: {active.get('current_phase')}")
    print(f"   Approved: {active.get('approved')}")
    print(f"   Issues: {len(active.get('issues', []))}")
    print(f"   Routing decisions: {len(active.get('_routing_decisions', []))}")
    print(f"   Artifact refs: {len(active.get('artifact_refs', []))}")

# File listing
if proj_dir.exists():
    print("\n📁 Files on disk:")
    for p in sorted(proj_dir.rglob("*.json")):
        print(f"   {p.relative_to(proj_dir)}")
