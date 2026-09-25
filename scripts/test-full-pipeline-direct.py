"""Run the full film pipeline for an old Chinese story via runtime API.

This calls the runtime.approve_phase() method properly, which handles
phase transitions via _approve_current_phase + _advance_to_next_phase.
"""

import json
import os

os.chdir("/Users/ghassan/my-projects/film-pipeline-langgraph")


from _scratch_bootstrap import use_scratch_roots

SCRATCH_ARTIFACTS = use_scratch_roots()
from film_pipeline.app.runtime import get_runtime

from film_pipeline.schemas.base import FilmPhase

rt = get_runtime()

PROJECT_ID = "old-chinese-story-v2"
print(f"🎬 Creating project: {PROJECT_ID}")

# Clean previous run
for pid in list(rt.projects.keys()):
    if pid == PROJECT_ID:
        del rt.projects[pid]

# Clean artifact store files from previous run
import shutil

projects_dir = SCRATCH_ARTIFACTS
for d in projects_dir.iterdir():
    if d.is_dir() and d.name.startswith("old-chinese-story"):
        shutil.rmtree(d)
        print(f"   Cleaned artifacts dir: {d}")

# ===== STEP 1: Create Project + Submit Idea =====
rt.create_project(project_id=PROJECT_ID, title="The Last Dragon Vein", slug="old-chinese-story")
rt.set_active(PROJECT_ID)

active = rt.get_active()
story = """A short film about an old Chinese ink wash painter living alone in a remote mountain village.
He has spent 70 years perfecting a single brushstroke — the 'dragon vein' stroke that brings
his paintings to life. When a young city photographer arrives documenting vanishing traditions,
the painter reluctantly teaches her his technique over one transformative autumn. Their unlikely
friendship bridges two worlds: analog vs digital, ancient vs modern, stillness vs speed.
The climax comes when the painter, facing his final stroke, must decide whether to complete
his masterpiece or leave it unfinished — a choice that will define whether his art lives
beyond him."""

active["idea"] = story
state = rt.run_graph(active)
rt.projects[PROJECT_ID] = state
print(f"✅ Idea submitted. Phase: {state.get('current_phase')}")

# ===== STEP 2-5: Approve phases properly =====
phase_labels = {
    "intake": "INTAKE",
    "constitution": "CONSTITUTION",
    "development": "DEVELOPMENT (treatment)",
    "script": "SCRIPT",
    "visual_dev": "VISUAL DEV",
    "shot_bible": "SHOT BIBLE",
    "gen_planning": "GENERATION PLAN",
}

for phase, label in phase_labels.items():
    active_phase = rt.get_active().get("current_phase", "")
    if not active_phase or active_phase == "completed":
        print("⏹️  Pipeline completed or no active phase.")
        break
    expected = phase
    if active_phase != expected:
        print(f"⚠️  Expected phase '{expected}', got '{active_phase}' — skipping...")
        continue
    try:
        state = rt.approve_phase()
        rt.projects[PROJECT_ID] = state
        print(f"✅ {label}: approved → next={state.get('current_phase', '<done>')}")
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
                    "type": str(a.artifact_type.value)[:20],
                    "status": str(a.status.value)[:15],
                }
        except Exception:
            pass
    return results


artifacts = list_artifacts()
print(f"\n📦 Artifacts stored ({len(artifacts)} total):")
for key, meta in sorted(artifacts.items()):
    print(f"   v{meta['v']:3d} {meta['type']:20s} {meta['status']:15s} | {key}")

# ===== Print final state =====
active = rt.get_active()
if active:
    print("\n🏁 Final state:")
    print(f"   Phase: {active.get('current_phase')}")
    print(f"   Approved: {active.get('approved')}")
    print(f"   Issues: {len(active.get('issues', []))}")
    print(f"   Routing decisions: {len(active.get('_routing_decisions', []))}")
    print(f"   Artifact refs: {len(active.get('artifact_refs', []))}")

    # Check key artifact contents
    print("\n📄 Key artifact contents:")
    for ref in active.get("artifact_refs", [])[:5]:
        parts = ref.split(":")
        if len(parts) >= 2:
            aid = parts[1]
            ver = int(parts[2].lstrip("v")) if len(parts) > 2 else 1
            # Find the phase for this artifact
            for phase in list(FilmPhase):
                try:
                    data = store.load(PROJECT_ID, phase, aid, ver)
                    if data:
                        cls_name = type(data).__name__
                        snippet = json.dumps(data, indent=2, default=str)[:500]
                        print(f"\n   📄 {aid} (v{ver}, {cls_name}):")
                        print(f"      {snippet}")
                        break
                except (FileNotFoundError, ValueError):
                    pass
else:
    print("\n⚠️  No active project at end")

print("\n🎬 Done!")
