"""Run full pipeline in REAL mode for a neon-noir Tokyo ramen bar story.
Tests the MCP surface + runtime both, with a visually distinct premise.
"""

import json
import os
import sys

os.chdir("/Users/ghassan/my-projects/film-pipeline-langgraph")

with open(".env") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

os.environ["FILM_PIPELINE_MCP_MODE"] = "real"

from _scratch_bootstrap import use_scratch_roots

SCRATCH_ARTIFACTS = use_scratch_roots()

from film_pipeline.app.runtime import get_runtime

from film_pipeline.schemas.base import FilmPhase

rt = get_runtime()
rt.server_mode = "real"

PROJECT_ID = "neon-ramen-001"
print(f"🎬 Creating project: {PROJECT_ID}")

for pid in list(rt.projects.keys()):
    if pid == PROJECT_ID:
        del rt.projects[pid]

import shutil

proj_dir = SCRATCH_ARTIFACTS / PROJECT_ID
if proj_dir.exists():
    shutil.rmtree(proj_dir)

rt.create_project(project_id=PROJECT_ID, title="Last Bowl at 3AM", slug="neon-ramen")
rt.set_active(PROJECT_ID)

active = rt.get_active()
active["runtime_mode"] = "real"
active["server_mode"] = "real"
active["profile_stack"] = {
    "film_type_profile": "film-type.narrative",
    "quality_profile": "quality.studio",
    "provider_profile": "provider.seedance_primary",
    "review_profile": "review.strict_continuity",
}

story = """A one-minute neon-noir short set in a tiny Tokyo ramen bar at 3AM.
Two strangers — an elderly woman who has been ordering the same bowl every night for 40 years
and a young man who just got fired — sit one seat apart, not speaking. The entire story is told
through: the steam rising from the broth, the old woman's chopstick technique (she eats in a
specific ritual sequence: nori first, then egg, then noodles), the young man's trembling hands
spilling his soup, and a single glance they exchange when the fluorescent bulb above them
flickers. No dialogue. The neon sign outside hums in and out. The cook (visible only as hands
and apron) knows both their orders by heart. The film ends with the old woman leaving a
500-yen coin on the counter — exactly enough for one bowl — and the young man discovering
she paid for his too. The color palette is deep blues, neon red, warm amber from the broth,
with one single cold white flicker at the midpoint."""

active["idea"] = story
print("⏳ Submitting idea + running intake...")
sys.stdout.flush()
state = rt.run_graph(active)
rt.projects[PROJECT_ID] = state
print(f"✅ Idea submitted. Phase: {state.get('current_phase')}")

# Approve through all phases
for phase, label in [
    ("intake", "INTAKE"),
    ("constitution", "CONSTITUTION"),
    ("development", "DEVELOPMENT"),
    ("script", "SCRIPT"),
    ("visual_dev", "VISUAL DEV"),
    ("shot_bible", "SHOT BIBLE"),
    ("gen_planning", "GEN PLANNING"),
    ("generation", "GENERATION"),
]:
    ap = rt.get_active().get("current_phase", "")
    if not ap or ap == "completed":
        print("⏹️  Pipeline completed")
        break
    print(f"\n⏳ {label} (phase={ap})...")
    sys.stdout.flush()
    try:
        state = rt.approve_phase()
        rt.projects[PROJECT_ID] = state
        print(f"✅ {label}: → {state.get('current_phase', '<done>')}")
    except ValueError as e:
        print(f"❌ {label}: {e}")
        break
    except Exception as e:
        print(f"❌ {label}: {type(e).__name__}: {e}")
        break

# Show everything
print(f"\n{'=' * 70}")
print("📦 ALL ARTIFACTS")
print(f"{'=' * 70}")
store = rt.services.artifact_store
for phase in list(FilmPhase):
    try:
        artifacts = store.list_artifacts(PROJECT_ID, phase)
        for a in artifacts:
            print(
                f"   {a.phase.value!s:15s} / {a.artifact_id:30s} v{a.version} [{a.artifact_type.value!s:20s}] {a.status.value!s}"
            )
    except Exception:
        pass

# Show contents of key artifacts
for aid in ["project_profile", "film_constitution", "treatment", "scene_list", "script"]:
    for phase in list(FilmPhase):
        try:
            data = store.load(PROJECT_ID, phase, aid, 1)
            if data:
                cls_name = type(data).__name__
                text = json.dumps(data, indent=2, default=str, ensure_ascii=False)[:1200]
                print(f"\n{'-' * 60}")
                print(f"📄 {aid} ({cls_name}):")
                print(text)
                break
        except (FileNotFoundError, ValueError):
            pass

active = rt.get_active()
if active:
    print(f"\n{'=' * 60}")
    print(f"🏁 Phase: {active.get('current_phase')}")
    print(f"   Approval: {active.get('approved')}")
    print(f"   Issues: {len(active.get('issues', []))}")
    print(f"   Artifact refs: {len(active.get('artifact_refs', []))}")
    print(f"{'=' * 60}")
