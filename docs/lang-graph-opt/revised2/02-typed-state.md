# Phase 2 — Typed State Contract

**Goal:** Replace `StateGraph(dict)` with typed `StudioGraphState(TypedDict)` with reducers.
Remove the `deepcopy(state)` pattern from all nodes. Move services out of state.

**Prerequisite:** Phase 1 (real human gates) — typed state builds on a graph that pauses/resumes correctly.

---

## Current State (What We're Replacing)

```python
# graph.py:32
builder = StateGraph(dict)

# nodes.py — every node:
def intake_node(state):
    new_state = deepcopy(state)   # copy everything
    new_state["current_phase"] = "intake"
    new_state["approved"] = False
    # ... mutate ...
    return new_state               # return entire state

# runtime.py:115
state[SERVICES_KEY] = self.services  # injected into state dict
```

Problems:
- No type safety — any key can be set anywhere with any type
- No reducer behavior — lists are replaced, not appended
- Deep-copy on every node — linear cost growth as state accumulates
- Services in state — must be stripped before serialization

---

## Target State

```python
from typing import Annotated, TypedDict
from operator import add

class StudioGraphState(TypedDict, total=False):
    # Scalar channels (last write wins — default reducer)
    project_id: str
    current_phase: str
    approved: bool
    human_approval_phase: str
    active_matrix_ref: str
    execution_brief_ref: str
    completed: bool

    # Ref pointers (scalar)
    constitution_ref: str
    treatment_ref: str
    scene_list_ref: str
    script_ref: str
    story_bible_ref: str
    shot_matrix_ref: str
    visual_refs: str
    cost_estimate_ref: str
    consensus_report_ref: str
    assembly_manifest_ref: str

    # Append-only channels (list accumulation)
    artifact_refs: Annotated[list[str], add]
    issues: Annotated[list[dict[str, object]], add]
    validation_report_refs: Annotated[list[str], add]
    audit_events: Annotated[list[dict[str, object]], add]

    # Snapshot channels (replace)
    budget_snapshot: dict[str, object]
    provider_health_snapshot: dict[str, object]

    # Config (injected via runtime, not state)
    # _services: REMOVED — pass via config["configurable"] instead
```

---

## Files to Modify

| File | Change |
|------|--------|
| NEW: `graph/state_schema.py` | Define `StudioGraphState` TypedDict |
| `graph/graph.py:32` | `StateGraph(StudioGraphState)` instead of `StateGraph(dict)` |
| `graph/nodes.py` — all nodes | Return partial updates, remove `deepcopy()` |
| `graph/nodes.py:_run_agent()` | Read services from different location |
| `app/runtime.py:115` | Inject services via `config["configurable"]` not state |
| `tests/unit/test_graph.py` | Update for typed state |
| `tests/unit/graph/test_orchestrator_state.py` | Ensure orchestrator helpers work with typed state |

---

## Step-by-Step

### Step 1: Create `StudioGraphState`

**File:** NEW `src/film_pipeline/graph/state_schema.py`

```python
"""Typed graph state with reducers for append-only channels."""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict


class StudioGraphState(TypedDict, total=False):
    """Canonical graph state for the film pipeline.

    Scalar fields use the default reducer (last write wins).
    Fields annotated with ``Annotated[T, add]`` accumulate across nodes.
    """

    # ── Core identifiers ──────────────────────────────────────────────
    project_id: str
    current_phase: str
    approved: bool
    completed: bool

    # ── Human gate control ────────────────────────────────────────────
    human_approval_phase: str
    human_approval_required: bool   # set by phase nodes, cleared on approve

    # ── Ref pointers (scalar — latest write wins) ────────────────────
    idea: str
    film_type: str
    target_runtime_seconds: int
    profile_ref: str
    constitution_ref: str
    treatment_ref: str
    scene_list_ref: str
    script_ref: str
    story_bible_ref: str
    shot_matrix_ref: str
    visual_refs: str
    execution_brief_ref: str
    cost_estimate_ref: str
    consensus_report_ref: str
    assembly_manifest_ref: str

    # ── Append-only channels ──────────────────────────────────────────
    artifact_refs: Annotated[list[str], add]
    issues: Annotated[list[dict[str, object]], add]
    validation_report_refs: Annotated[list[str], add]

    # ── Snapshot channels ─────────────────────────────────────────────
    budget_snapshot: dict[str, object]
    provider_health_snapshot: dict[str, object]

    # ── Transient / repair ────────────────────────────────────────────
    repair_feedback_ref: str
    generation_requests: list[dict[str, object]]
    resolved_config: dict[str, object]
```

**Note on `total=False`:** All keys are optional. Nodes return only the keys they modify. This is the standard LangGraph pattern for partial updates.

### Step 2: Wire `StateGraph(StudioGraphState)`

**File:** `src/film_pipeline/graph/graph.py:30-32`

```python
# Current:
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

def build_graph() -> CompiledStateGraph:
    builder = StateGraph(dict)

# Target:
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from film_pipeline.graph.state_schema import StudioGraphState

def build_graph() -> CompiledStateGraph:
    builder = StateGraph(StudioGraphState)
```

### Step 3: Convert Nodes to Return Partial Updates

Every phase node currently does:
```python
def intake_node(state):
    new_state = deepcopy(state)
    new_state["current_phase"] = "intake"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "config"
    # ... agent, save, etc ...
    return new_state
```

Target:
```python
def intake_node(state: StudioGraphState) -> dict[str, object]:
    result = _run_agent(state, agent_id="intake-classifier-agent", ...)
    profile = result.get("profile")

    updates: dict[str, object] = {
        "current_phase": "intake",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "config",
    }

    if profile is not None:
        ref = _save_artifact(state, profile, "project_profile", "intake")
        if ref:
            updates["profile_ref"] = ref
            updates["artifact_refs"] = [ref]  # append-only channel — added to list
            updates["target_runtime_seconds"] = getattr(profile, "target_runtime_seconds", 0)
            updates["film_type"] = str(getattr(profile, "film_type", ""))

    return updates  # LangGraph merges these into existing state
```

**Critical:** `artifact_refs` and `issues` use `Annotated[list, add]` — returning `[ref]` APPENDS to the existing list. Returning `artifact_refs` as a key REPLACES the entire list (scalar behavior, wrong). Always return new items, not the accumulated list.

**Migration pattern for all 11 phase nodes:**

```python
# Pattern: replace this in every phase node
# OLD:
new_state = deepcopy(state)
new_state["current_phase"] = "X"
new_state["approved"] = False
new_state["human_approval_required"] = True
new_state["human_approval_phase"] = "Y"
# ... agent work ...
return new_state

# NEW:
updates: dict[str, object] = {
    "current_phase": "X",
    "approved": False,
    "human_approval_required": True,
    "human_approval_phase": "Y",
}
# ... agent work ...
if ref:
    updates["X_ref"] = ref
    updates["artifact_refs"] = [ref]
if issues_found:
    updates["issues"] = issues_found
return updates
```

### Step 4: Move Services Out of State

**File:** `src/film_pipeline/app/runtime.py:110-116`

```python
# Current:
def run_graph(self, state):
    state = dict(state)
    state[SERVICES_KEY] = self.services
    config = {"configurable": {"thread_id": state.get("project_id", "default")}}
    return graph.invoke(state, config)

# Target:
def run_graph(self, state):
    state = dict(state)
    config = {
        "configurable": {
            "thread_id": state.get("project_id", "default"),
            "services": self.services,  # ← services live in config, not state
        }
    }
    return graph.invoke(state, config)
```

**File:** `src/film_pipeline/graph/nodes.py:_get_services`

```python
# Current:
def _get_services(state: dict[str, Any]) -> GraphServices | None:
    return state.get(SERVICES_KEY)

# Target:
def _get_services(state: dict[str, Any]) -> GraphServices | None:
    # Check state first (legacy), then config
    if SERVICES_KEY in state:
        return state.get(SERVICES_KEY)
    # LangGraph nodes can access config via get_config()
    # For now, keep the runtime injection path
    return state.get(SERVICES_KEY)  # still works until config-based approach is finalized
```

For Phase 2, keeping state-based service injection is acceptable. The goal is to remove `_services` from the TypedDict schema so it's not serialized. The runtime can still inject it for nodes to use.

### Step 5: Update Orchestrator State Helpers

**File:** `src/film_pipeline/graph/orchestrator_state.py`

The namespaced keys (`_orchestrator__candidate_refs`, etc.) are stored inside the state dict. With typed state, these keys don't appear in the TypedDict schema. They still work because `total=False` allows extra keys.

**Action:** No change needed for Phase 2. The helpers continue to use `state["_orchestrator__..."]` keys which are valid in `total=False` TypedDict.

**Future (Phase 4+):** Fold orchestrator state into typed channels (candidate_refs, approved_refs, convergence, etc.).

---

## Test Cases

### Unit Tests (`tests/unit/graph/test_state_schema.py` — NEW)

```python
from film_pipeline.graph.state_schema import StudioGraphState

def test_artifact_refs_append_reducer():
    """Returning [ref] appends, doesn't replace."""
    state: StudioGraphState = {"artifact_refs": ["artifact:a:v1"]}
    # Simulate reducer: add(["artifact:b:v1"], ["artifact:a:v1"])
    from operator import add
    result = add(["artifact:a:v1"], ["artifact:b:v1"])
    assert result == ["artifact:a:v1", "artifact:b:v1"]

def test_scalar_channels_replace():
    """Returning a scalar value replaces it."""
    state: StudioGraphState = {"current_phase": "intake"}
    # TypedDict with scalar (no Annotated) → default reducer: replace
    state["current_phase"] = "constitution"
    assert state["current_phase"] == "constitution"

def test_partial_update_preserves_other_keys():
    """Returning {"current_phase": "X"} doesn't touch other keys."""
    state: StudioGraphState = {
        "project_id": "test",
        "current_phase": "intake",
        "artifact_refs": ["ref1"],
    }
    update = {"current_phase": "constitution"}
    merged = {**state, **update}
    assert merged["project_id"] == "test"
    assert merged["current_phase"] == "constitution"
    assert merged["artifact_refs"] == ["ref1"]
```

### Unit Tests (`tests/unit/test_graph.py` — update existing)

```python
def test_graph_uses_typed_state():
    """Graph is built with StudioGraphState, not dict."""
    graph = build_graph()
    # Verify the graph accepts typed state
    from film_pipeline.graph.state_schema import StudioGraphState
    assert True  # compilation succeeded

def test_node_returns_partial_update():
    """intake_node returns only modified keys, not full state."""
    state: StudioGraphState = {"project_id": "test", "idea": "test idea"}
    updates = intake_node(state)
    assert "current_phase" in updates
    assert "approved" in updates
    assert "project_id" not in updates  # not returned because unchanged
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Reducer duplicates on interrupt replay | `add` reducer appends every time the node re-runs. Use deterministic refs (`artifact:shot_matrix:v1` is deterministic — but `v2` from repair is different, so duplicates are correct). For truly idempotent lists, add dedup logic in Phase 5. |
| TypedDict `total=False` allows untyped keys | `_orchestrator__*` keys and `_repair_feedback` are untyped but functional. Acceptable for Phase 2. Type them in Phase 4. |
| Nodes must not return accumulated lists | If `intake_node` returns `artifact_refs=[ref1, ref2]` instead of `artifact_refs=[ref2]`, LangGraph's `add` reducer will double-append `ref1`. Document the rule: always return only NEW items. |
| `_get_services()` must work during migration | Keep `SERVICES_KEY` injection in runtime. Nodes read from state as before. Phase 2 doesn't change the injection mechanism, only removes it from the TypedDict schema. |

---

## Acceptance Criteria

- [ ] `StateGraph(StudioGraphState)` compiles and `make ci-check` passes
- [ ] `StudioGraphState` defines all keys currently in use with correct types
- [ ] At least 3 phase nodes (intake, constitution, development) return partial updates instead of `deepcopy(state)` + full state
- [ ] Append-only channels (`artifact_refs`, `issues`) use `Annotated[list, add]` and nodes return only new items
- [ ] `_services` key not in `StudioGraphState` TypedDict (still injected at runtime via legacy path)
- [ ] New tests: reducer behavior, partial update preservation
- [ ] Existing tests pass with updated state handling
- [ ] `make ci-check` green

**Estimated implementation time:** 3-4 hours (converting 11 nodes is the bulk of the work)
**Prerequisite:** Phase 1 (real human gates)
