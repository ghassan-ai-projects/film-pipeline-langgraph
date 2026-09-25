"""Camino del Genesis — fresh run with latest fixes."""

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
from film_pipeline.schemas._base import FilmPhase

rt = get_runtime()
rt.server_mode = "real"

PROJECT_ID = "camino-del-genesis-008"
for pid in list(rt.projects.keys()):
    if pid == PROJECT_ID:
        del rt.projects[pid]
d = SCRATCH_ARTIFACTS / PROJECT_ID
if d.exists():
    import shutil

    shutil.rmtree(d)

rt.create_project(project_id=PROJECT_ID, title="Camino del Genesis", slug="camino-del-genesis")
rt.set_active(PROJECT_ID)
active = rt.get_active()
active["runtime_mode"] = "real"
active["server_mode"] = "real"
active["profile_stack"] = {
    "film_type_profile": "film-type.visual_poetry",
    "quality_profile": "quality.studio",
    "provider_profile": "provider.seedance_primary",
    "review_profile": "review.strict_continuity",
}

story = """Camino del Genesis is a 4-minute dialogue-free visual poem in 4 movements with exactly 20 shots (10-15s each).

Movement 1: The Canvas and the Catalyst (5 shots, 0:00-1:00)
Shot 1 The Infinite Stillness: Static ultra-wide shot of barren Dali-esque earth. Immense sky. Nothing moves. 15s.
Shot 2 The Descent: Extreme slow motion. Eagle glides on thermal winds. Raindrop falls, strikes eagle's back, absorbs its essence. 15s.
Shot 3 The Ripple: Raindrop hits barren dust. Ripple travels through image fabric, warping horizon. 10s.
Shot 4 The First Sound: First birdsong. Translucent wave of light rolls across landscape. 10s.
Shot 5 The Wave Spreads: Wave continues across empty canvas. 10s.

Movement 2: The Awakening (5 shots, 1:00-2:00)
Shot 6 The Breath: Birdsong wave washes over earth. Green plants swell like a deep breath. 15s.
Shot 7 The Tree: Kazantzakis almond tree pushes upward — earth stretching into tree shape, roots indistinguishable from soil. 15s.
Shot 8 The Blossom: Almond blossom detaches and falls. Camera follows. 10s.
Shot 9 The Emergence: Young Man emerges where blossom lands, silhouette peeling from green background. 15s.
Shot 10 The Cycle: Young Man steps, crushing an insect. Boundaryless ants emerge like earth ripples, absorb it. 5s.

Movement 3: The Bleeding Boundaries (5 shots, 2:00-3:00)
Shot 11 The Paint: Camera tracks Young Man walking. With each step, green earth transforms into yellow roses. 15s.
Shot 12 The Trail: Arm trails color of roses. Body and earth boundaries fail. 15s.
Shot 13 The Rose: Push in to yellow rose. Thick impasto texture, heavy paint ridges. 10s.
Shot 14 The Bee: Bee separates from yellow paint, emerges from center of rose petals. 10s.
Shot 15 The Flight: Bee zips through frame leaving trail of painted light and pollen. 10s.

Movement 4: The Symphony of Form (5 shots, 3:00-4:00)
Shot 16 The Convergence: Sweeping wide. Sky is Van Gogh clouds, earth is yellow roses. Eagle soars, wings dragging clouds. 15s.
Shot 17 The Melting: Young Man by tree, form melting into brushstrokes. Bee leaves painted light. 15s.
Shot 18 The Wave: Birdsong wave washes over everything. All textures vibrate in unison. 15s.
Shot 19 The Lift: Camera tilts up into swirling impasto sky. 10s.
Shot 20 The End: Fade to black. Final piano chord held 5 seconds, then silence. 5s.

This film has exactly 20 shots. Each 10-15s. 4 movements × 5 shots = 20 shots = 240s = 4 minutes."""

active["idea"] = story
print("⏳ Running...")
sys.stdout.flush()
state = rt.run_graph(active)
rt.projects[PROJECT_ID] = state

for phase, label in [
    ("intake", "INTAKE"),
    ("constitution", "CONSTITUTION"),
    ("development", "DEVELOPMENT"),
    ("script", "SCRIPT"),
    ("visual_dev", "VISUAL DEV"),
    ("shot_bible", "SHOT BIBLE"),
    ("gen_planning", "GEN PLANNING"),
]:
    ap = rt.get_active().get("current_phase", "")
    if not ap or ap == "completed":
        break
    print(f"⏳ {label} (phase={ap})...")
    sys.stdout.flush()
    try:
        state = rt.approve_phase()
        rt.projects[PROJECT_ID] = state
        print(f"✅ {label}: → {state.get('current_phase', '<done>')}")
    except Exception as e:
        print(f"❌ {label}: {type(e).__name__}: {str(e)[:200]}")
        break

store = rt.services.artifact_store
print("\n📦 ARTIFACTS:")
for phase in list(FilmPhase):
    try:
        for a in store.list_artifacts(PROJECT_ID, phase):
            print(f"   {a.phase.value!s:15s} / {a.artifact_id:30s} v{a.version}")
    except:
        pass

sm_path = SCRATCH_ARTIFACTS / PROJECT_ID / "05-shot-bible" / "shot_matrix.v1.json"
if sm_path.exists():
    sm = json.load(open(sm_path))
    rows = sm.get("rows", [])
    t = sum(r.get("duration_seconds", 0) for r in rows)
    print(f"\n🎬 SHOT MATRIX: {len(rows)} shots, {t}s ({t // 60}m{t % 60}s)")
    for r in rows:
        print(
            f"   {r['shot_id']:20s} {r.get('duration_seconds', '?'):>3}s  scene={r.get('scene_id', '?')}"
        )
else:
    print("\n⚠️ No shot matrix found")

for aid in ["project_profile", "film_constitution", "treatment", "scene_list", "script"]:
    for phase in list(FilmPhase):
        try:
            data = store.load(PROJECT_ID, phase, aid, 1)
            if data:
                t = json.dumps(data, indent=2, default=str, ensure_ascii=False)[:800]
                print(f"\n📄 {aid}:")
                print(t)
                break
        except:
            pass
