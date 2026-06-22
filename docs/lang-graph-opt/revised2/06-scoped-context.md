# Phase 6 — Scoped Context Packets

**Goal:** Replace full-artifact JSON injection with phase-specific structured context.
Each phase's agent receives only the data it actually needs — not truncated 6000-char JSON blobs.

**Prerequisite:** Phase 4 (matrix patches) — matrix projection provides row-level querying needed for scoped context.

---

## Current State

```python
# nodes.py:117-135 — ALL 8 artifact slots injected for EVERY agent
context_vars = {
    "constitution_content": "",    # loaded from disk, serialized to string
    "treatment_content": "",       # loaded from disk, serialized to string
    "scene_list_content": "",      # loaded from disk, serialized to string
    "script_content": "",          # loaded from disk, serialized to string
    "story_bible_content": "",     # loaded from disk, serialized to string
    "shot_matrix_content": "",     # loaded from disk, serialized to string → TRUNCATED at 6000 chars
    "visual_refs_content": "",     # loaded from disk, serialized to string
    "execution_brief_content": "", # loaded from disk, serialized to string
}
_inject_artifact_context(state, services, context_vars)
# Each artifact: file I/O → JSON parse → JSON dump → truncate at 6000 chars → inject
```

**Token cost:** ~33K tokens per pipeline run. 88% of matrix data truncated for real films.

---

## Target State

```python
# Per-phase context builders — only what the phase needs
def build_constitution_context(state):   # idea + classification
def build_development_context(state):    # constitution summary + target runtime
def build_script_context(state):         # treatment + scene_list + constitution
def build_visual_dev_context(state):     # script scenes + constitution style
def build_shot_bible_context(state):     # execution brief + script scene map + visual ref ids
def build_gen_planning_context(state):   # planned rows only + budget/provider policy
def build_generation_context(state):     # batch of ready rows only
def build_qc_context(state):            # artifact refs + targeted excerpts per validator
```

**Token savings:** ~80% reduction per agent call.

---

## Files to Modify

| File | Change |
|------|--------|
| NEW: `graph/context_packets.py` | Per-phase context builders |
| `graph/nodes.py:117-180` | Replace `_inject_artifact_context` with phase-specific builders |
| `agents/prompt_templates/defaults.py` | Update context templates to use structured data |

---

## Step-by-Step

### Step 1: Create Context Packet Builders

**File:** NEW `src/film_pipeline/graph/context_packets.py`

```python
"""Phase-specific context packets — scoped data for agent prompts."""

from __future__ import annotations

from typing import Any


def build_constitution_context(state: dict[str, Any]) -> str:
    """Constitution phase: just the idea."""
    idea = str(state.get("idea", ""))
    film_type = str(state.get("film_type", ""))
    target = state.get("target_runtime_seconds", 0)

    return (
        f"Film idea: {idea}\n"
        f"Film type: {film_type}\n"
        f"Target runtime: {target}s\n"
        f"Project ID: {state.get('project_id', '')}"
    )


def build_script_context(
    state: dict[str, Any],
    services: Any,
) -> str:
    """Script phase: treatment summary + scene list + constitution summary."""
    parts = []

    # Treatment summary (load from store, extract key fields)
    treatment_ref = state.get("treatment_ref", "")
    if treatment_ref:
        data = _load_artifact(state, services, treatment_ref, "development")
        if data:
            themes = data.get("themes", [])
            act_map = data.get("act_map", {})
            parts.append(f"Treatment themes: {', '.join(themes) if themes else 'none'}")
            for act, desc in act_map.items():
                parts.append(f"  {act}: {desc}")

    # Scene list summary
    scene_list_ref = state.get("scene_list_ref", "")
    if scene_list_ref:
        data = _load_artifact(state, services, scene_list_ref, "development")
        if data:
            scenes = data.get("scenes", [])
            parts.append(f"Scene count: {len(scenes)}")
            for s in scenes[:50]:  # cap at 50 scenes
                parts.append(
                    f"  {s.get('scene_id', '?')}: {s.get('dramatic_function', '')}"
                )

    return "\n".join(parts)


def build_shot_bible_context(
    state: dict[str, Any],
    services: Any,
) -> str:
    """Shot bible phase: execution brief + script scene map + visual ref summary."""
    parts = []

    # Execution brief (short, critical)
    brief_ref = state.get("execution_brief_ref", "")
    if brief_ref:
        data = _load_artifact(state, services, brief_ref, "shot_bible")
        if data:
            parts.append("EXECUTION BRIEF (structural contract):")
            parts.append(f"  Target runtime: {data.get('target_runtime_seconds', 0)}s")
            parts.append(f"  Pacing: {data.get('pacing_style', 'standard')}")
            for m in data.get("movements", []):
                parts.append(
                    f"  Movement '{m.get('movement_id', '?')}': "
                    f"{m.get('shot_count', 0)} shots, "
                    f"duration range {m.get('duration_range_seconds', [0,0])}"
                )

    # Script scene summary
    script_ref = state.get("script_ref", "")
    if script_ref:
        data = _load_artifact(state, services, script_ref, "script")
        if data:
            scenes = data.get("scenes", [])
            parts.append(f"\nSCRIPT: {len(scenes)} scenes")
            for s in scenes[:50]:
                parts.append(
                    f"  {s.get('scene_id', '?')}: {s.get('scene_heading', '')} "
                    f"[{len(s.get('dialogue', []))} dialogue lines]"
                )

    return "\n".join(parts)


def build_gen_planning_context(
    state: dict[str, Any],
    services: Any,
) -> str:
    """Gen planning: only planned rows + budget/provider policy."""
    parts = []

    # Only show rows that still need planning (status="planned")
    from film_pipeline.artifacts.matrix_projection import materialize_matrix, get_rows_by_status

    matrix_ref = state.get("shot_matrix_ref", "")
    patch_refs = state.get("active_matrix_patch_refs", [])

    if matrix_ref:
        matrix = materialize_matrix(services.artifact_store, state["project_id"], matrix_ref, patch_refs)
        planned_rows = get_rows_by_status(matrix, "planned")

        parts.append(f"SHOTS TO PLAN: {len(planned_rows)}")
        for row in planned_rows[:100]:  # cap at 100 rows
            parts.append(
                f"  {row.get('shot_id', '?')}: "
                f"act={row.get('act_id', '?')}, "
                f"scene={row.get('scene_id', '?')}, "
                f"duration={row.get('duration_seconds', 0)}s, "
                f"camera={row.get('camera_profile', '?')}"
            )

    # Budget info
    budget = state.get("budget_snapshot", {})
    if budget:
        parts.append(f"\nBudget: ${budget.get('remaining_usd', 0)} remaining of ${budget.get('cap_usd', 0)}")

    return "\n".join(parts)


def _load_artifact(
    state: dict[str, Any],
    services: Any,
    ref: str,
    phase: str,
) -> dict[str, Any] | None:
    """Load an artifact by ref string. Returns None on failure."""
    parts = ref.split(":")
    if len(parts) < 3:
        return None
    artifact_id = parts[1]
    version = int(parts[2].lstrip("v"))

    from film_pipeline.schemas._base import FilmPhase
    try:
        return services.artifact_store.load(
            str(state.get("project_id", "")),
            FilmPhase(phase),
            artifact_id,
            version,
        )
    except (FileNotFoundError, ValueError):
        return None
```

### Step 2: Replace `_inject_artifact_context` in `_run_agent()`

**File:** `src/film_pipeline/graph/nodes.py:_run_agent()`

```python
# Current:
_inject_artifact_context(state, services, context_vars)

# Target — per-phase context builders:
phase_context_builders = {
    "intake": build_constitution_context,
    "constitution": build_constitution_context,
    "development": build_development_context,
    "script": build_script_context,
    "visual_dev": build_visual_dev_context,
    "shot_bible": build_shot_bible_context,
    "gen_planning": build_gen_planning_context,
    "generation": build_generation_context,
    "qc": build_qc_context,
}

builder = phase_context_builders.get(phase)
if builder:
    context_vars["scoped_context"] = builder(state, services)
else:
    # Fallback to legacy full-artifact injection
    _inject_artifact_context(state, services, context_vars)
```

### Step 3: Update Prompt Templates

Templates currently use `{constitution_content}`, `{script_content}`, etc.
After Phase 6, they use `{scoped_context}` instead:

```python
# Current (shot_bible template):
context_template=(
    "=== EXECUTION BRIEF ===\n{execution_brief_content}\n"
    "Script content:\n{script_content}\n"
    "Visual refs:\n{visual_refs_content}\n"
)

# Target:
context_template=(
    "{scoped_context}\n"
    "Project ID: {project_id}\n"
    "KB refs: {kb_refs}"
)
```

**Migrate incrementally:** Start with shot_bible (biggest savings), then gen_planning, then script. Keep legacy `{X_content}` vars as fallback until all templates are migrated.

---

## Test Cases

```python
def test_shot_bible_context_includes_execution_brief():
    """Shot bible context contains execution brief structural data."""
    # Setup mock state + services
    context = build_shot_bible_context(state, services)
    assert "EXECUTION BRIEF" in context
    assert "target_runtime" in context.lower()

def test_gen_planning_context_only_includes_planned_rows():
    """Gen planning context excludes rows already planned."""
    # Setup matrix with mixed statuses
    context = build_gen_planning_context(state, services)
    assert "SHOTS TO PLAN" in context
    # Should not include rows with status != "planned"

def test_context_under_3000_chars_for_large_matrix():
    """100-row matrix context stays under 3000 chars."""
    # Setup 100-row matrix
    context = build_shot_bible_context(state, services)
    assert len(context) < 3000  # vs 6000+ for full JSON

def test_fallback_to_legacy_injection_when_no_builder():
    """Phases without a context builder fall back to _inject_artifact_context."""
    # Phase without builder → old behavior preserved
```

---

## Acceptance Criteria

- [ ] `build_shot_bible_context()` produces structured context under 3000 chars
- [ ] `build_gen_planning_context()` only includes rows with `status="planned"`
- [ ] `build_script_context()` includes treatment summary, not full JSON
- [ ] Shot bible template migrated to use `{scoped_context}`
- [ ] Gen planning template migrated to use `{scoped_context}`
- [ ] Legacy `_inject_artifact_context` preserved as fallback
- [ ] Context token cost reduced by ~80% for migrated phases
- [ ] `make ci-check` green

**Estimated implementation time:** 3-4 hours
**Prerequisite:** Phase 4 (matrix patches) — `materialize_matrix()` and `get_rows_by_status()`
