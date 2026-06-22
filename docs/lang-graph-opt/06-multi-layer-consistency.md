# 06 — Multi-Layer Data Consistency: Keeping Constitution → Assembly in Sync

**Date:** 2026-06-22
**Question:** We have multi levels of data — scripts, master matrix, shots, etc. How do we update them and keep them in sync after changes? Think from big picture to details, including context length and cost saving.

---

## 1. The Data Layers — A Living Dependency Tree

The pipeline has **8 layers** of data, each building on the previous:

```
Layer 1: Constitution     (theme, tone, visual language, taboos)
   │
   ▼
Layer 2: Treatment        (act structure, scene breakdown, dramatic functions)
   │
   ▼
Layer 3: Script           (dialogue, action lines, story bible, setup-payoff)
   │
   ▼
Layer 4: Visual Refs      (character bibles, environment bibles, reference index)
   │
   ▼
Layer 5: Master Matrix    (shot-by-shot: camera, duration, characters, env per shot)
   │
   ▼
Layer 6: Generation Plan  (provider, model, prompt, cost per shot)
   │
   ▼
Layer 7: Generated Assets (actual video clips)
   │
   ▼
Layer 8: Assembly         (clip ordering, transitions, audio, color, delivery)
```

**The dependency rule:** If layer N changes, layers N+1 through 8 are potentially stale. The deeper the change, the more downstream artifacts are affected.

### How Stale Can Data Get? A Concrete Example

```
Change: constitution_node re-runs → theme changes from "dark noir" to "hopeful sci-fi"

Immediate impact:
  ✗ treatment — built from constitution:v1, now constitution:v2 exists
  ✗ script — built from treatment:v1 (which was built from constitution:v1)
  ✗ visual_refs — reference entries designed for "dark noir" aesthetic
  ✗ shot_matrix — rows describe noir lighting, noir camera profiles
  ✗ gen_plan — cost estimates for noir-style shots
  ✗ generated_assets — actual clips in noir visual style
  ✗ assembly — assembled from noir clips

Current behavior: NOTHING detects this. The graph doesn't know these are stale.
```

The `InvalidationEngine` has a dependency graph (`checkpoints/invalidation.py:8-24`) that models this exactly — but it's **only used for rollback**, not for change propagation.

---

## 2. Current State: What We Have and What's Broken

### 2.1 The InvalidationEngine — Correct Map, Wrong Use Case

```python
# checkpoints/invalidation.py:8-24
DEPENDENCY_GRAPH = {
    "film_constitution": ["treatment", "script", "character_bible", "environment_bible"],
    "treatment":         ["script", "scene_intents", "shot_bible"],
    "script":            ["scene_intents", "shot_bible", "prompt_registry", "continuity_ledger"],
    "shot_bible":        ["prompt_registry", "continuity_ledger", "generation_schedule"],
    "prompt_registry":   ["provider_plan", "generation_schedule"],
    "provider_plan":     ["generation_schedule"],
    "generation_schedule": ["generated_clips"],
    # ...
}
```

This graph is **correct** — it accurately models the dependency chain. But it's only invoked by `rollback_artifact` and `rollback_to_checkpoint` MCP tools, not by the normal graph flow.

**What's missing:** After every phase completes, compare the artifact versions that the current phase was "built from" against the latest versions. If any upstream artifact has been updated since, flag this phase's output as stale.

### 2.2 No Version Tracking on Dependencies

Artifacts don't record which versions of upstream artifacts they depend on:

```json
// Current: shot_matrix.v1.json
{
  "project_id": "demo",
  "rows": [...]
  // NOWHERE does it say: "I was built from script:v2, constitution:v1, visual_refs:v1"
}
```

Without this, you can't answer: "Is this shot matrix still consistent with the current script?"

### 2.3 6 of 18 Artifact Types Are Never Saved

From the dependency map (Section 1), these declared artifacts are **never persisted by their phase nodes**:

| Artifact | Phase | Status |
|----------|-------|--------|
| `character_bible` | visual_dev | Agent contract exists, node doesn't save it |
| `environment_bible` | visual_dev | Same — `visual_dev_node` only saves `reference_index` |
| `continuity_ledger` | shot_bible | Agent contract exists, node doesn't save it |
| `prompt_registry` | gen_planning | Agent contract exists, node only saves `cost_estimate` |
| `generation_plan` | generation | Entire phase is a stub |
| `delivery_package` | delivery | Entire phase is a stub |

This means the dependency chain breaks at visual_dev (missing character/environment bibles), shot_bible (missing continuity ledger), and generation (entirely missing).

### 2.4 Context Injection: Paying for Data the Agent Doesn't Need

Every critical-path agent call injects **all available upstream artifacts** as full JSON strings:

```python
# nodes.py:117-133 — context_vars ALWAYS includes all 8 artifact slots
context_vars = {
    "constitution_content": "",    # 0-6000 chars
    "treatment_content": "",       # 0-6000 chars
    "scene_list_content": "",      # 0-6000 chars
    "script_content": "",          # 0-6000 chars
    "story_bible_content": "",     # 0-6000 chars
    "shot_matrix_content": "",     # 0-6000 chars  ← massive for real films
    "visual_refs_content": "",     # 0-6000 chars
    "execution_brief_content": "", # 0-6000 chars
}
# Then _inject_artifact_context() loads them ALL from disk
```

**Token cost per agent call (actual):**

| Agent | Artifacts Injected | Est. Context Tokens | Notes |
|-------|-------------------|---------------------|-------|
| Screenwriter | treatment + scene_list + constitution | ~4,500 | 3 × 1500 tokens |
| Visual Dev | script + story_bible + constitution | ~4,500 | 3 × 1500 tokens |
| Shot Bible | execution_brief + script + visual_refs | ~4,500 | 3 × 1500 tokens |
| Gen Planner | execution_brief + shot_matrix + budget | ~4,500 | 2 × 1500 + budget |
| QC Synthesis | ALL 7 upstream phases | ~10,500 | 7 × 1500 tokens |
| **Total per pipeline run** | | **~33,000 tokens** | Across 10 critical-path agents |

At $2.00/M tokens (GPT-4o): ~$0.066 per full run. At $0.15/M (Gemini Flash): ~$0.005.

The cost isn't the main issue — it's **context dilution**. A 100-shot matrix is ~50KB of JSON. Truncated to 6000 chars, the agent sees only ~12% of the data. It's flying blind on 88% of the shot rows.

### 2.5 The Truncation Problem — Hidden Data Loss

```python
# nodes.py:394-399
def _compact_json_context(data: dict[str, Any], max_chars: int = 6000) -> str:
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n... [truncated]"
```

For a real film (~100 shots × 25 fields per row × ~50 chars per field = ~125KB), the agent receives only the first ~5% of rows. The rest is `...[truncated]`. Every downstream agent works with partial data.

---

## 3. The Consistency Model — How It Should Work

### 3.1 Versioned Dependencies on Every Artifact

Every artifact must record what it was built from:

```python
class ArtifactMetadata(SchemaBase):
    artifact_id: str
    version: int
    # ... existing fields ...

    # NEW: upstream dependency versions at build time
    built_from: dict[str, str] = Field(
        default_factory=dict,
        description="Map of artifact_id → version_ref at time of creation. "
                    "e.g. {'script': 'artifact:script:v2', 'constitution': 'artifact:film_constitution:v1'}"
    )
```

When `constitution_node` saves `film_constitution:v2`, the metadata records:
```json
{
  "artifact_id": "film_constitution",
  "version": 2,
  "built_from": {
    "project_profile": "artifact:project_profile:v1"
  }
}
```

When `shot_bible_node` saves `shot_matrix:v1`:
```json
{
  "artifact_id": "shot_matrix",
  "version": 1,
  "built_from": {
    "script": "artifact:script:v1",
    "constitution": "artifact:film_constitution:v1",
    "visual_refs": "artifact:reference_index:v1",
    "execution_brief": "artifact:execution_brief:v1"
  }
}
```

### 3.2 Staleness Detection — The Consistency Gate

After every phase saves an artifact, run a consistency check:

```python
def check_consistency(state, artifact_id: str) -> list[StalenessWarning]:
    """Check if any upstream dependencies have newer versions."""
    metadata = load_metadata(artifact_id)
    warnings = []

    for dep_id, dep_version_ref in metadata.built_from.items():
        current_ref = get_latest_approved_ref(state, dep_id)
        if current_ref and current_ref != dep_version_ref:
            warnings.append(StalenessWarning(
                artifact_id=artifact_id,
                dependency=dep_id,
                built_with=dep_version_ref,
                current=current_ref,
                severity="stale" if is_major_change(dep_id, dep_version_ref, current_ref) else "review_needed",
            ))

    return warnings
```

This runs as a **post-phase validation node** — a new node added after every phase node that checks consistency before the human gate.

### 3.3 Selective Re-Derivation — Not Everything Must Regenerate

When `constitution.theme` changes from "dark noir" to "hopeful sci-fi", not everything downstream needs regeneration:

| Artifact | Must Regenerate? | Why |
|----------|-----------------|-----|
| treatment | **Maybe not** | The act structure (3 acts, scene count) might still be valid even if the tone changed |
| script | **Likely yes** | Dialogue and action lines reflect tone |
| visual_refs | **Yes** | Reference images for noir vs sci-fi are completely different |
| shot_matrix | **Partially** | Camera profiles change, but shot count might not |
| gen_plan | **Yes** | Prompts change, providers might change |
| generated_assets | **Yes** | Clips must match new visual style |

The key insight: **only re-derive what actually depends on the changed field.**

This requires:
1. **Field-level dependency tracking:** Not just "script depends on constitution" but "script.dialogue depends on constitution.tone" vs "script.scene_count depends on treatment.act_map"
2. **Change detection:** When constitution:v2 is saved, diff it against constitution:v1. Only `theme` and `visual_language` changed — `character_truths` and `taboo_mistakes` are unchanged.
3. **Impact analysis:** `theme` change affects → treatment.themes, script.dialogue, visual_refs, shot_matrix rows. `character_truths` (unchanged) affects nothing.

### 3.4 The Matrix as the Consistency Anchor

Since the Master Film Matrix is the central production backbone, each **row** should track its own dependency versions:

```python
class MasterFilmMatrixRow(SchemaBase):
    shot_id: str
    # ... existing fields ...

    # NEW: per-row dependency tracking
    built_from_script_version: str = ""       # "artifact:script:v2"
    built_from_constitution_version: str = "" # "artifact:film_constitution:v1"
    built_from_visual_refs_version: str = ""  # "artifact:reference_index:v1"
    built_from_execution_brief_version: str = ""  # "artifact:execution_brief:v1"
```

Now you can answer at row granularity: "Shot S001-05 was built from script:v2. Script is now at v3. Is S001-05 still valid?"

The answer depends on whether the script change affected scene `sc_001` (which S001-05 belongs to). If `sc_001` was unchanged between script:v2 and script:v3, then S001-05 is still valid — **no need to regenerate**.

### 3.5 Diff-Aware Context Injection — Only Send What Changed

Instead of injecting full artifact content into every prompt, inject a **change summary**:

```python
# CURRENT: inject full constitution JSON
context_vars["constitution_content"] = json.dumps(constitution_data)  # up to 6000 chars

# PROPOSED: inject only what's relevant and what changed
if is_repair_or_revision(state):
    context_vars["upstream_changes"] = build_change_summary(state, phase)
    # "Since your last run:
    #  - constitution.theme changed: 'dark noir' → 'hopeful sci-fi'
    #  - constitution.visual_language changed: 'desaturated' → 'vibrant neon'
    #  - script: NO CHANGES
    #  - treatment: NO CHANGES"
else:
    # First run: inject structured summaries, not full JSON
    context_vars["constitution_summary"] = summarize_constitution(constitution_data)
    # "Theme: hopeful sci-fi. Tone: grounded with wonder.
    #  Visual language: vibrant neon palette. Camera: handheld intimacy.
    #  Character truths: Mara fears abandonment, Elias protects loved ones."
```

**Token savings:**

| Approach | Constitution Context | Savings |
|----------|---------------------|---------|
| Full JSON (current) | ~1500 tokens | — |
| Structured summary | ~200 tokens | 87% less |
| Change diff (repair) | ~50 tokens | 97% less |

Applied across 8 artifacts × 10 agents = **~100K → ~20K tokens per full run** — 80% reduction without losing relevance.

### 3.6 The Per-Phase Context Budget

Each phase doesn't need all 8 artifacts. It needs specific ones:

| Phase | Needs | Doesn't Need |
|-------|-------|-------------|
| Constitution | idea only | — |
| Development | constitution + idea | — |
| Script | treatment + scene_list + constitution | visual_refs, shot_matrix, execution_brief |
| Visual Dev | script + constitution | treatment, shot_matrix |
| Shot Bible | execution_brief + script + visual_refs | treatment, constitution (already embedded in script) |
| Gen Planning | shot_matrix + execution_brief + budget | script, visual_refs, constitution |
| Generation | gen_plan per row + shot_matrix (relevant rows only) | full script, full visual_refs |
| QC | generated assets + relevant matrix rows + validator reports | full constitution, full treatment |

**Current code already injects the right artifacts per agent** (each template specifies which context vars to include). The issue is **how much** — full JSON instead of structured summaries.

---

## 4. The Implementation Plan

### Phase 1: Dependency Version Tracking (Foundation)

**Goal:** Every artifact records what upstream versions it was built from.

**Changes:**

1. **Add `built_from: dict[str, str]` to `ArtifactMetadata`** — a map of `artifact_id → version_ref`

2. **Populate `built_from` when saving artifacts** — `_save_artifact()` reads `state["artifact_refs"]` and records current approved versions:

   ```python
   def _save_artifact(state, artifact, artifact_id, phase):
       # Build dependency map from current state
       built_from = {}
       for ref_str in state.get("artifact_refs", []):
           if ":" in ref_str:
               parts = ref_str.split(":")
               dep_id = parts[1]
               built_from[dep_id] = ref_str

       meta = ArtifactMetadata(
           artifact_id=artifact_id,
           version=version,
           built_from=built_from,  # ← NEW
           # ...
       )
   ```

3. **Write a `check_staleness(artifact_id, state) → list[StalenessWarning]` function** that compares `built_from` against current approved refs.

### Phase 2: Consistency Gate Node

**Goal:** After every phase, the graph checks for staleness before the human gate.

**Changes:**

1. **Add `consistency_check_node`** between phase nodes and `await_approval`:

   ```python
   def consistency_check_node(state):
       """Check if this phase's output is consistent with upstream artifacts."""
       current_phase = state["current_phase"]
       artifact_refs = state.get("artifact_refs", [])

       warnings = []
       for ref in artifact_refs:
           artifact_id = parse_ref(ref).artifact_id
           warnings.extend(check_staleness(artifact_id, state))

       if warnings:
           state.setdefault("consistency_warnings", []).extend(warnings)

       return state
   ```

2. **Wire into graph:**
   ```python
   builder.add_edge("intake_node", "consistency_check")
   builder.add_edge("consistency_check", "await_approval")
   ```

3. **Review package includes staleness warnings** — human sees "Script was built from constitution:v1 but constitution is now at v2. Script may be stale."

### Phase 3: Smart Context Injection (Cost Savings)

**Goal:** Inject structured summaries instead of full JSON. On repair, inject diffs.

**Changes:**

1. **Build artifact summarizers per schema:**

   ```python
   def summarize_constitution(data: dict) -> str:
       return (
           f"Theme: {data.get('theme', '')}. "
           f"Tone: {data.get('tone', '')}. "
           f"Visual language: {data.get('visual_language', '')}. "
           f"Camera philosophy: {data.get('camera_philosophy', '')}. "
           f"Taboos: {', '.join(data.get('taboo_mistakes', []))}."
       )

   def summarize_script(data: dict) -> str:
       scenes = data.get("scenes", [])
       return (
           f"Total scenes: {len(scenes)}. "
           f"Scene IDs: {', '.join(s.get('scene_id', '') for s in scenes[:20])}"
           + ("..." if len(scenes) > 20 else "")
       )

   def summarize_shot_matrix(data: dict) -> str:
       rows = data.get("rows", [])
       acts = {}
       for r in rows:
           act = r.get("act_id", "?")
           acts[act] = acts.get(act, 0) + 1
       return (
           f"Total shots: {len(rows)}. "
           f"By act: {acts}. "
           f"Status: {sum(1 for r in rows if r.get('status') != 'planned')} processed."
       )
   ```

2. **Replace `_inject_artifact_context` with `_inject_artifact_summaries`:**

   ```python
   def _inject_artifact_summaries(state, services, context_vars):
       """Inject structured summaries instead of full JSON blobs."""
       summarizers = {
           "constitution_content": (summarize_constitution, "constitution_ref", "constitution"),
           "script_content": (summarize_script, "script_ref", "script"),
           "shot_matrix_content": (summarize_shot_matrix, "shot_matrix_ref", "shot_bible"),
           # ...
       }
       for context_key, (summarizer, ref_key, phase) in summarizers.items():
           ref = state.get(ref_key)
           if not ref:
               continue
           data = services.artifact_store.load(project_id, FilmPhase(phase), ...)
           context_vars[context_key] = summarizer(data)
   ```

3. **On repair, inject only diffs:**

   ```python
   if state.get("_repair_feedback"):
       # Already have feedback — don't re-inject full context
       context_vars["upstream_changes"] = compute_diff_since_last_run(state)
   ```

### Phase 4: Row-Level Dependency Tracking (Precision)

**Goal:** Matrix rows track their individual upstream versions so we can answer "is this specific row stale?"

**Changes:**

1. **Add dependency fields to `MasterFilmMatrixRow`:**

   ```python
   class MasterFilmMatrixRow(SchemaBase):
       # ... existing fields ...
       built_from_script_version: str = ""
       built_from_constitution_version: str = ""
       built_from_visual_refs_version: str = ""
   ```

2. **Populate at creation time** — `shot_bible_node` records current versions:

   ```python
   for row in matrix.rows:
       row.built_from_script_version = state["script_ref"]
       row.built_from_constitution_version = state["constitution_ref"]
       row.built_from_visual_refs_version = state["visual_refs"]
   ```

3. **Staleness check at row level:**

   ```python
   def get_stale_rows(matrix, state) -> list[str]:
       """Return shot_ids whose upstream dependencies have changed."""
       stale = []
       for row in matrix.rows:
           if row.built_from_script_version != state.get("script_ref"):
               # Check if this row's scene was affected
               if scene_changed(row.scene_id, row.built_from_script_version, state["script_ref"]):
                   stale.append(row.shot_id)
       return stale
   ```

### Phase 5: Incremental Context (Advanced)

**Goal:** On re-run of a phase, only send context for the rows/scenes that actually changed.

This requires the matrix to be in state (from doc `03-living-state-master-matrix.md`). Once it is:

```python
def gen_planning_node(state):
    matrix = state["matrix"]

    # Only plan for rows that don't have a plan yet, or whose
    # upstream deps changed
    rows_to_plan = [
        r for r in matrix.rows
        if not r.provider_plan_ref or is_row_stale(r, state)
    ]

    if not rows_to_plan:
        return state  # nothing to do

    result = _run_agent(
        state,
        agent_id="provider-planning-agent",
        phase="gen_planning",
        task=(
            f"Plan generation for {len(rows_to_plan)} shots. "
            f"{len(matrix.rows) - len(rows_to_plan)} shots already have plans "
            f"and have not changed — preserve them."
        ),
        # Only inject the rows_to_plan, not the full matrix
        context_override={"shots": rows_to_plan},
    )
```

**Cost impact:** A 100-shot film where only 3 shots' scenes changed → agent plans 3 shots instead of 100. 97% context reduction for this phase.

---

## 5. The Architecture Diagram — What Consistency Looks Like

```
┌──────────────────────────────────────────────────────┐
│                   GRAPH EXECUTION                     │
│                                                       │
│  phase_node ──→ save_artifact(built_from={deps})      │
│       │                                               │
│       ▼                                               │
│  consistency_check_node                               │
│       │  ┌──────────────────────────────────┐         │
│       │  │ check_staleness(artifact_id):     │         │
│       │  │   for dep_id, dep_version in      │         │
│       │  │     metadata.built_from:          │         │
│       │  │       if current[dep_id] !=       │         │
│       │  │          dep_version:             │         │
│       │  │         → StalenessWarning        │         │
│       │  └──────────────────────────────────┘         │
│       │                                               │
│       ├── no warnings → await_approval                │
│       │                                               │
│       └── warnings → await_approval                   │
│              (review package shows stale deps)         │
│                                                       │
│  await_approval                                       │
│       │                                               │
│       ├── human approves → next phase                 │
│       │   (next phase gets SMART CONTEXT:              │
│       │    summaries, not full JSON.                   │
│       │    On repair: diff of what changed.)           │
│       │                                               │
│       └── human requests revision → repair            │
│           (repair feedback includes:                   │
│            "Only scene sc_003 changed.                  │
│             Fix rows shot_0007-shot_0009 only.")       │
└──────────────────────────────────────────────────────┘
```

---

## 6. What We Already Have That Helps

| Component | File | What It Does | Gap |
|-----------|------|-------------|-----|
| `DEPENDENCY_GRAPH` | `checkpoints/invalidation.py:8` | Maps artifact → downstream dependents | Only used for rollback, not consistency |
| `InvalidationEngine.report()` | `checkpoints/invalidation.py:30` | Computes what rollback invalidates | Not called during normal graph flow |
| `_inject_artifact_context()` | `graph/nodes.py:339` | Loads upstream artifacts into prompt | Loads full JSON, no summaries |
| `built_from` pattern | — | Does not exist | Needs to be added to `ArtifactMetadata` |
| `_compact_json_context()` | `graph/nodes.py:394` | Truncates at 6000 chars | Loses 88% of data for real films |
| `compute_artifact_diff()` | `review/diff.py` | Diffs artifact ref lists for review | Only does ref-level diff, not content diff |

---

## 7. Priority Roadmap

| Priority | What | Token Savings | Consistency Gain |
|----------|------|--------------|-----------------|
| **P0** | Add `built_from` to ArtifactMetadata + populate on save | — | Foundation for everything below |
| **P0** | `check_staleness()` function using `built_from` vs current refs | — | Detects stale artifacts |
| **P1** | Structured summaries instead of full JSON in context injection | 80% reduction per agent call | Less context dilution = better agent output |
| **P1** | Consistency check node after every phase | — | Human sees staleness warnings at every gate |
| **P1** | Diff-based context on repair (only show what changed) | 97% reduction on repair calls | Agent focuses on fixing, not re-reading |
| **P2** | Row-level dependency tracking on matrix rows | — | Targeted re-derivation instead of full regeneration |
| **P2** | Per-phase context budgets (only inject what that phase needs) | 50% reduction for early phases | Less noise in prompts |
| **P3** | Incremental re-derivation (only re-plan/re-generate changed rows) | Up to 97% for large films | Enables cost-effective film iteration |

---

## 8. Summary

The pipeline has 8 layers of data with well-understood dependencies. The `InvalidationEngine` already models them correctly — it just needs to be used for consistency, not just rollback.

**Three things to do now:**

1. **Version the dependencies** — every artifact records `built_from: {dep → version_ref}`. This is a one-field schema change with zero breaking impact.

2. **Summarize, don't serialize** — replace the `_compact_json_context(data, max_chars=6000)` pattern with per-schema structured summaries. The agent doesn't need the full JSON; it needs the key facts.

3. **Check staleness at every gate** — a 20-line `check_staleness()` function that compares `built_from` versions against current approved refs. Add a `consistency_check_node` after every phase.

These three changes together give you: **detection of stale data, 80% token reduction, and a foundation for incremental re-derivation.**

### Files Referenced

| File | Lines | Role |
|------|-------|------|
| `checkpoints/invalidation.py` | 73 | Dependency graph — correct map, wrong use case |
| `graph/nodes.py:117-200` | ~85 | Context variable assembly + artifact injection |
| `graph/nodes.py:339-399` | ~60 | _inject_artifact_context + _compact_json_context |
| `graph/nodes.py:24-218` | ~195 | _run_agent with context injection |
| `agents/prompt_templates/defaults.py` | 1079 | Agent prompt templates with context slots |
| `schemas/matrix.py` | 85 | MasterFilmMatrixRow — needs dependency fields |
| `schemas/artifact.py` | — | ArtifactMetadata — needs built_from field |
| `artifacts/store.py` | 105 | Artifact persistence — needs built_from in metadata |
| `review/diff.py` | — | Artifact diffing — currently ref-level only |
