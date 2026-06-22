# 03 — The Living State: The Master Matrix as the Central Nervous System

**Date:** 2026-06-22
**Question:** How can we improve the "Living State" — making the Master Film Matrix a genuine central nervous system that evolves across phases rather than a static artifact?

---

## 1. The Vision vs. The Reality

### What the Architecture Blueprint Promises

> "The master film matrix is not a spreadsheet afterthought. It is the shared contract between agents. The orchestrator should treat the matrix as the production backbone." — `architecture-blueprint.md:431`

> "Master Film Matrix — central production table connecting story, characters, environments, prompts, references, validation." — `analysis-status-plan.md:87`

The Master Film Matrix is designed to be the **single source of truth** that every phase reads from, enriches, and passes forward. It should:

| Phase | What it reads from the matrix | What it writes back |
|-------|------------------------------|---------------------|
| Shot Bible (5) | Scene intents, script, visual refs | Creates all rows (planned status) |
| Gen Planning (6) | All rows (planned) | `prompt_ref`, `provider_plan_ref` per row |
| Generation (7) | Rows with prompts + plans | `asset_refs`, `generation_order` status |
| QC (8) | All rows with assets | `validation_refs` per row |
| Post (9) | All rows with validated assets | `post_refs`, `status="assembled"` |
| Delivery (10) | All completed rows | Final status checks |

Every row transitions through: `planned` → `prompted` → `generated` → `validated` → `assembled` → `delivered`.

### What Actually Happens

The MasterFilmMatrix is a **static JSON artifact** created once and never mutated in place:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Shot Bible   │────▶│ ArtifactStore │     │ Gen Planning │
│ (creates it) │     │ (JSON on disk)│◀────│ (loads full  │
└─────────────┘     └──────────────┘     │  JSON, uses  │
                                         │  in prompt)  │
                                         └─────────────┘
```

**Here's the critical trace — how the matrix flows through the system:**

#### Step 1: Creation (shot_bible_node, `nodes.py:581-640`)

```python
# Agent produces the matrix as a Python object
shot_matrix = result.get("shot_matrix")  # MasterFilmMatrix instance

# Saved as opaque JSON artifact
ref = _save_artifact(new_state, shot_matrix, "shot_matrix", "shot_bible")
new_state["shot_matrix_ref"] = ref  # → "artifact:shot_matrix:v1"
```

The Python object is gone. Only a pointer string remains in state.

#### Step 2: Loading for Gen Planning (gen_planning_node, `nodes.py:641-700`)

```python
shot_matrix_ref = str(new_state.get("shot_matrix_ref", ""))
if shot_matrix_ref:
    parsed = _parse_ref(shot_matrix_ref)
    # Loads ENTIRE JSON from disk, parses back to dict
    matrix_data = services.artifact_store.load(
        project_id, FilmPhase("shot_bible"), parsed.artifact_id, parsed.version
    )
    # Cross-validate, then discard
```

#### Step 3: Prompt Context Injection (`_inject_artifact_context`, `nodes.py:339-367`)

```python
# Loads full matrix JSON from disk AGAIN
data = services.artifact_store.load(
    project_id, FilmPhase("shot_bible"), parsed.artifact_id, parsed.version
)
# Serializes to string, truncates to 6000 chars
context_vars["shot_matrix_content"] = _compact_json_context(data)
# Injected into LLM prompt as a giant string blob
```

Every downstream phase repeats this pattern: **load entire JSON → serialize to string → inject into prompt → discard**.

#### Step 4: After Gen Planning — Matrix Is Never Updated

```python
# gen_planning_node saves a SEPARATE artifact (cost_estimate)
# It does NOT write prompt_ref or provider_plan_ref back to the matrix rows
cost_estimate = result.get("cost_estimate")
ref = _save_artifact(new_state, cost_estimate, "cost_estimate", "gen_planning")
```

The `MasterFilmMatrixRow` fields that downstream phases should populate — `prompt_ref`, `provider_plan_ref`, `asset_refs`, `validation_refs`, `post_refs` — **remain empty forever**. They exist in the schema but nothing writes to them.

### The Result: A Dead Matrix

The matrix is created in phase 5 and **never changes** after that. Phases 6-10 produce separate artifacts (cost_estimate, consensus_report, assembly_manifest) but never cross-reference them back into the matrix rows. The matrix is a snapshot of the plan, not a living record of execution.

---

## 2. Root Causes: Why the Matrix Doesn't Live

### 2.1 Artifact-Only Storage Model

```python
# The ONLY way to persist anything:
def _save_artifact(state, artifact, artifact_id, phase) -> str:
    services.artifact_store.save(artifact, meta)    # writes JSON to disk
    return f"artifact:{artifact_id}:v1"              # returns pointer string
```

The artifact store is file-based: save = write JSON file, load = read JSON file. There's no:
- In-place mutation of existing artifacts
- Row-level read/write
- Transactional updates
- Cross-reference tracking

### 2.2 State as a String-Based Pointer System

The graph state holds artifact refs as strings:

```python
state["shot_matrix_ref"] = "artifact:shot_matrix:v1"
state["constitution_ref"] = "artifact:film_constitution:v1"
state["treatment_ref"] = "artifact:treatment:v1"
state["script_ref"] = "artifact:script:v1"
# ... etc
```

These are **opaque pointers** — the graph has no idea what they contain. To access the data, every consumer must:
1. Parse the ref string (`"artifact:shot_matrix:v1"` → `("shot_matrix", 1)`)
2. Load from ArtifactStore (file I/O)
3. Deserialize from JSON
4. Use the data
5. Discard

### 2.3 Prompt Context as the Primary Data Sharing Mechanism

Artifact content flows between phases primarily through **LLM prompt injection**, not through structured state:

```python
# _inject_artifact_context() serializes artifacts to strings and stuffs them into prompts
context_vars["shot_matrix_content"] = json.dumps(matrix_data, indent=2)  # string blob
context_vars["script_content"] = json.dumps(script_data, indent=2)        # string blob
# ... injected into prompt templates like:
# "Shot matrix content:\n{shot_matrix_content}\n"
```

The LLM reads a serialized string, produces new JSON, and that JSON becomes the next artifact. There is **no machine-readable cross-referencing** between artifacts.

### 2.4 The Deep-Copy State Model Prevents Mutation

```python
def gen_planning_node(state):
    new_state = deepcopy(state)  # full copy, disconnected from original
    # ... work with new_state ...
    return new_state              # replaces old state entirely
```

If `gen_planning_node` modified `state["matrix_rows"][0].prompt_ref`, that change would be lost because:
1. The original is deep-copied on entry
2. The matrix rows aren't in state — they're on disk
3. Even if they were in state, the next phase would deep-copy again

### 2.5 No Cross-Phase Mutation Contract

The schema says `MasterFilmMatrixRow.prompt_ref: str` should be populated by gen planning. But:

```python
# gen_planning_node saves a cost_estimate artifact — NOT matrix rows
cost_estimate = result.get("cost_estimate")
_save_artifact(new_state, cost_estimate, "cost_estimate", "gen_planning")

# No code that does:
# for row in matrix.rows:
#     row.prompt_ref = generated_prompts[row.shot_id]
#     row.provider_plan_ref = generated_plans[row.shot_id]
# _save_artifact(new_state, matrix, "shot_matrix", "gen_planning")  # update version
```

There's no code path that mutates individual matrix rows and saves the updated matrix back.

---

## 3. What "Living State" Should Look Like

### 3.1 The Matrix as a State-Held Entity

Instead of `state["shot_matrix_ref"] = "artifact:shot_matrix:v1"`, the matrix lives in state:

```python
# After shot_bible_node creates it:
state["matrix"] = MasterFilmMatrix(
    project_id="demo",
    rows=[row1, row2, ...],
    coverage_groups=[...],
)

# gen_planning_node reads specific rows, updates them:
for row in state["matrix"].rows:
    row.prompt_ref = prompt_map[row.shot_id]
    row.provider_plan_ref = plan_map[row.shot_id]

# generation_node updates asset refs:
for row in state["matrix"].rows:
    if row.shot_id in generated_assets:
        row.asset_refs.append(generated_assets[row.shot_id])
        row.status = "generated"
```

The matrix **is** the state, not a pointer to a file.

### 3.2 Row-Level Diffing and Provenance

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class RowChange:
    shot_id: str
    field: str          # e.g. "asset_refs"
    old_value: Any
    new_value: Any
    phase: str          # e.g. "generation"
    timestamp: datetime

# State accumulates changes:
class MatrixState(TypedDict):
    matrix: MasterFilmMatrix
    matrix_changes: Annotated[list[RowChange], add]  # append-only changelog
```

Now you can answer: "What changed on shot S001-01 during generation?" — consult `matrix_changes`.

### 3.3 Phase-Specific Views (Row Filtering)

Not every phase needs every row. State should support querying:

```python
# Gen planning only needs rows that are "planned" and have prompts ready
rows = [r for r in state["matrix"].rows if r.status == "planned"]

# QC only needs rows with assets
rows = [r for r in state["matrix"].rows if r.asset_refs]

# Post only needs validated rows
rows = [r for r in state["matrix"].rows if r.status == "validated"]
```

Currently, the full matrix is serialized to a 6000-char string and injected into prompts regardless of what the phase actually needs.

### 3.4 Cross-Artifact References as First-Class State

Instead of opaque string pointers, references should be typed links:

```python
@dataclass(frozen=True)
class ArtifactLink:
    artifact_id: str
    artifact_type: ArtifactType
    version: int
    phase: FilmPhase

# In state:
state["matrix"].rows[0].prompt_ref = ArtifactLink(
    artifact_id="prompt_S001_01",
    artifact_type=ArtifactType.PROMPT,
    version=1,
    phase=FilmPhase.GEN_PLANNING,
)
```

Now the graph can traverse references without loading files — it knows what exists and where.

### 3.5 Event-Sourced State Evolution

Each phase appends events, rather than overwriting:

```python
# Instead of:
state["matrix"] = new_matrix  # full replacement

# Do:
state["matrix_events"].append({
    "event": "rows_updated",
    "phase": "gen_planning",
    "shot_ids": ["S001-01", "S001-02"],
    "fields_changed": ["prompt_ref", "provider_plan_ref"],
    "timestamp": datetime.now(UTC),
})
```

This enables:
- Auditing: "Who set the prompt_ref on S001-01?"
- Rollback: Undo all changes from gen_planning
- Replay: Re-run gen_planning and compare results

---

## 4. The Optimization Plan

### Phase 1: Bring the Matrix Into State (Foundation)

**Goal:** The matrix lives in `state["matrix"]`, not just as a disk pointer.

**Changes:**

1. **After `shot_bible_node`**, store the `MasterFilmMatrix` instance directly in state:

   ```python
   # In shot_bible_node:
   shot_matrix = result.get("shot_matrix")
   if shot_matrix is not None:
       # Keep disk artifact for durability
       ref = _save_artifact(new_state, shot_matrix, "shot_matrix", "shot_bible")
       new_state["shot_matrix_ref"] = ref
       # ALSO store in state for downstream phases
       new_state["matrix"] = shot_matrix  # ← NEW
   ```

2. **Typed state with matrix key:**

   ```python
   from film_pipeline.schemas.matrix import MasterFilmMatrix

   class OrchestratorState(TypedDict):
       matrix: MasterFilmMatrix | None  # ← the living matrix
       # ... other keys
   ```

3. **Loading prioritizes state over disk:**

   ```python
   def get_matrix(state):
       if "matrix" in state and state["matrix"] is not None:
           return state["matrix"]         # fast path: in memory
       # Fallback: load from artifact store
       return load_from_artifact_store(state["shot_matrix_ref"])
   ```

4. **Eliminate `_inject_artifact_context` for the matrix** — instead of loading JSON → serializing to string → injecting into prompt, pass the matrix directly to the agent as structured context.

### Phase 2: Enable Row-Level Mutations (Living Matrix)

**Goal:** Downstream phases update individual rows, not the whole matrix.

**Changes:**

1. **gen_planning_node writes back to matrix rows:**

   ```python
   def gen_planning_node(state):
       matrix = state["matrix"]
       prompts = result.get("prompts", {})
       plans = result.get("provider_plans", {})

       for row in matrix.rows:
           if row.shot_id in prompts:
               row.prompt_ref = prompts[row.shot_id]
           if row.shot_id in plans:
               row.provider_plan_ref = plans[row.shot_id]

       # Persist updated matrix
       _save_matrix(state, matrix, phase="gen_planning")
       return state
   ```

2. **generation_node writes asset_refs:**

   ```python
   def generation_node(state):
       matrix = state["matrix"]
       for row in matrix.rows:
           asset = generated_assets.get(row.shot_id)
           if asset:
               row.asset_refs.append(asset)
               row.status = "generated"
       return state
   ```

3. **qc_node writes validation_refs:**

   ```python
   def qc_node(state):
       matrix = state["matrix"]
       for validation in validation_results:
           row = find_row(matrix, validation.shot_id)
           if row:
               row.validation_refs.append(validation.ref)
               row.status = "validated" if validation.passed else "failed"
       return state
   ```

### Phase 3: Row-Level Diffing and Provenance (Observability)

**Goal:** Track what changed, when, and by which phase.

**Changes:**

1. **Add a changelog to state:**

   ```python
   class MatrixState(TypedDict):
       matrix: MasterFilmMatrix
       matrix_changelog: Annotated[list[MatrixRowChange], add]  # append-only
   ```

2. **Track changes on mutation:**

   ```python
   def update_row(row, field, new_value, phase):
       old = getattr(row, field)
       setattr(row, field, new_value)
       return MatrixRowChange(
           shot_id=row.shot_id,
           field=field,
           old_value=old,
           new_value=new_value,
           phase=phase,
           timestamp=datetime.now(UTC),
       )

   # In gen_planning_node:
   changelog = []
   for row in matrix.rows:
       changelog.append(update_row(row, "prompt_ref", prompts[row.shot_id], "gen_planning"))
   state["matrix_changelog"].extend(changelog)
   ```

### Phase 4: Phase-Specific Views (Performance)

**Goal:** Phases only see the rows they need, reducing prompt token costs.

**Changes:**

1. **View functions on matrix state:**

   ```python
   def rows_for_phase(matrix: MasterFilmMatrix, phase: str) -> list[MasterFilmMatrixRow]:
       """Filter matrix rows relevant to a phase."""
       status_map = {
           "gen_planning": "planned",
           "generation": "prompted",
           "qc": "generated",
           "post": "validated",
       }
       target = status_map.get(phase, "planned")
       return [r for r in matrix.rows if r.status == target]
   ```

2. **Use views in agent tasks instead of full matrix dumps:**

   ```python
   # Before: inject 6000-char JSON string into prompt
   context_vars["shot_matrix_content"] = json.dumps(matrix_data)

   # After: inject structured summary
   relevant = rows_for_phase(matrix, "generation")
   context_vars["shots_to_generate"] = json.dumps([
       {"shot_id": r.shot_id, "prompt_ref": r.prompt_ref, "duration": r.duration_seconds}
       for r in relevant
   ])
   ```

### Phase 5: Event-Sourced State with Rollback (Durability)

**Goal:** Every state change is an append-only event. Rollback is cheap.

**Changes:**

1. **Event log as append-only state channel:**

   ```python
   class OrchestratorState(TypedDict):
       matrix: MasterFilmMatrix
       events: Annotated[list[MatrixEvent], add]

   @dataclass
   class MatrixEvent:
       event_id: str
       event_type: str          # "rows_created", "rows_updated", "validation_added"
       phase: str
       shot_ids: list[str]
       payload: dict
       timestamp: datetime
   ```

2. **Rebuild matrix from events (for rollback):**

   ```python
   def rebuild_matrix(events: list[MatrixEvent], up_to_phase: str | None = None):
       matrix = empty_matrix()
       for event in events:
           if up_to_phase and event.phase == up_to_phase:
               break
           apply_event(matrix, event)
       return matrix
   ```

3. **LangGraph checkpointer stores events automatically** — no manual persistence needed.

---

## 5. Concrete Before/After Comparison

### Current Flow (Phase 5 → 6 transition)

```
shot_bible_node:
  1. Agent creates MasterFilmMatrix (Python object)
  2. Save to ArtifactStore → disk JSON
  3. State gets "shot_matrix_ref" = "artifact:shot_matrix:v1"
  4. Python object discarded

gen_planning_node:
  1. Read state["shot_matrix_ref"] → "artifact:shot_matrix:v1"
  2. Parse ref → ("shot_matrix", 1)
  3. ArtifactStore.load() → file I/O → JSON parse → dict
  4. Serialize dict to string (json.dumps)
  5. Inject string into prompt context
  6. Agent reads string, produces cost_estimate
  7. Save cost_estimate → separate artifact
  8. Matrix on disk is UNCHANGED
  9. State discards loaded matrix data
```

**Problems:** 2 disk I/O operations, 2 JSON serialize/deserialize cycles, matrix not updated, prompt gets 6000-char blob.

### Proposed Flow

```
shot_bible_node:
  1. Agent creates MasterFilmMatrix (Python object)
  2. Save to ArtifactStore → disk JSON (durability)
  3. State["matrix"] = matrix (lives in state)
  4. State["events"].append(RowsCreated(...))

gen_planning_node:
  1. Read state["matrix"] → Python object (no I/O)
  2. Filter: state["matrix"].rows where status == "planned"
  3. Pass structured rows to agent (not string blob)
  4. Agent returns prompts + plans
  5. For each row: row.prompt_ref = prompt, row.provider_plan_ref = plan
  6. State["events"].append(RowsUpdated(shot_ids=[...], fields=["prompt_ref", ...]))
  7. Persist updated matrix to disk (optional, on phase gate)
```

**Benefits:** 0 disk I/O, 0 JSON serialize/deserialize, matrix IS updated, prompt gets structured data, full provenance.

---

## 6. What We'd Need to Change

### Files to Modify

| File | Change |
|------|--------|
| `graph/graph.py` | Add typed state with `matrix: MasterFilmMatrix` and `events: list` keys |
| `graph/nodes.py` | shot_bible_node: store matrix in state. gen_planning/generation/qc/post: read from state, write back to matrix rows |
| `graph/orchestrator_state.py` | Add `get_matrix()`, `update_matrix_row()`, `get_matrix_changelog()` helpers |
| `graph/services.py` | Remove matrix from mock responses (mock responses become unnecessary when matrix is in state) |
| `agents/prompt_templates/defaults.py` | Replace `{shot_matrix_content}` string injection with structured row data |
| `agents/impl/shot_bible_agent.py` | No changes (already produces MasterFilmMatrix) |
| `agents/impl/gen_planner_agent.py` | Change input from `shot_matrix_ref` string to structured row list |
| `agents/impl/assembly_agent.py` | Same — use structured rows instead of loading from ref |
| `schemas/matrix.py` | Add `MatrixRowChange`, `MatrixEvent` schemas |
| `mcp/tools/__init__.py` | Expose `get_matrix_state` tool for inspection |

### New Files

| File | Purpose |
|------|---------|
| `graph/matrix_state.py` | Matrix-as-state helpers: `get_matrix()`, `rows_for_phase()`, `update_row()`, `apply_event()` |
| `schemas/matrix_events.py` | Event schemas: `MatrixEvent`, `RowCreated`, `RowUpdated`, `ValidationAdded` |

### Migration Path

1. **Add `matrix` key to state** (non-breaking — existing code ignores unknown keys)
2. **Store matrix in state alongside existing ref** in `shot_bible_node`
3. **Add `get_matrix()` helper** that prefers state over disk
4. **Migrate gen_planning first** — it already loads the matrix from disk; change to use state
5. **Migrate generation, qc, post** — one phase per PR
6. **Remove `_inject_artifact_context` for matrix** once all consumers use state
7. **Add event sourcing** once matrix is in state

### Risks

- **Memory:** A 100-shot matrix with 30 fields per row is ~50KB — negligible. No risk.
- **Checkpoint serialization:** LangGraph's checkpointer must serialize `MasterFilmMatrix` (Pydantic → `.model_dump()` works natively). Already handled.
- **Backward compatibility:** Existing artifact store loaders continue to work. The matrix is stored on disk AND in state during the transition. No breaking change.
- **Durability:** State in memory is lost on crash. Persist to disk at each phase gate (already done via `_save_artifact`). Event sourcing provides replay.

---

## 7. Related Concepts Worth Adopting

| Concept | Description | Priority |
|---------|-------------|----------|
| **Row-level status machine** | Each row has `status: planned → prompted → generated → validated → assembled → delivered` with explicit transitions | P1 |
| **Matrix diff on review packages** | When presenting a review package, show which rows changed since the last approval | P2 |
| **Partial matrix saves** | Only save rows that changed, not the entire matrix | P2 |
| **Matrix as LangGraph state channel** | Use `Annotated[MasterFilmMatrix, matrix_reducer]` where the reducer applies row-level merges | P1 |
| **Generation ledger linked to rows** | Each generated asset links back to `matrix_row.shot_id` — already in schema, just needs wiring | P1 |

---

## Summary

The Master Film Matrix is the most important data structure in the pipeline — it connects every phase and every agent. Right now it's a static artifact created once and never updated. Making it a "living state" — held in state, mutated in place, tracked with provenance — transforms it from a snapshot into a nervous system.

**Core principle:** The matrix IS the state. Not a pointer to a file. Not a JSON blob in a prompt. A structured, queryable, mutable entity that evolves with every phase.

### Files Referenced

| File | Lines | Role |
|------|-------|------|
| `src/film_pipeline/schemas/matrix.py` | 85 | MasterFilmMatrix + MasterFilmMatrixRow schema |
| `src/film_pipeline/schemas/execution_brief.py` | 43 | Structural contract for matrix validation |
| `src/film_pipeline/graph/nodes.py:581-700` | ~120 | shot_bible_node (creation) + gen_planning_node (first consumer) |
| `src/film_pipeline/graph/nodes.py:339-367` | ~30 | _inject_artifact_context (matrix → prompt string) |
| `src/film_pipeline/graph/nodes.py:24-218` | ~195 | _run_agent flow (how matrix data reaches agents) |
| `src/film_pipeline/agents/impl/shot_bible_agent.py` | 107 | Agent that creates the matrix |
| `src/film_pipeline/agents/impl/gen_planner_agent.py` | 48 | Agent that should update the matrix |
| `src/film_pipeline/graph/orchestrator_validators.py:206-300` | ~95 | Gate A/C validation against matrix |
| `docs/architecture-blueprint.md:269-485` | ~216 | Vision for master film matrix as production backbone |
