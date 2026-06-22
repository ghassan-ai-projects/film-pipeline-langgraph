# Phase 1 — Real Human Gates: Interrupts + Checkpointer

**Goal:** Replace recursion-limit approval gates with LangGraph `interrupt()` + checkpointer.
Make `approve_phase` and `request_revision` MCP tools resume the graph instead of manually
mutating runtime state.

**Product risk:** Human gates are the mandatory review system. Currently they work because
`GraphRecursionError` is caught and treated as "gate reached" — fragile and incorrect.

---

## Current State (What We're Replacing)

```
graph.invoke() → intake_node → await_approval(passthrough) → after_approval → await_approval → ...
   │                                                                                              │
   └── loops until recursion_limit=50 ────────────────────────────────────────────────────────────┘
                                          │
                                    GraphRecursionError caught
                                          │
                                    runtime extracts state
                                          │
                                    MCP approve_phase calls runtime.approve_phase()
                                    → manually calls approve_phase_node()
                                    → manually calls intake_node()
                                          │
                                    next MCP submit_idea calls graph.invoke() again
```

## Target State (What We're Building)

```
graph.invoke() → intake_node → await_approval → interrupt(payload)  ← graph PAUSES here
                                                      │
                                              MCP returns payload to operator
                                                      │
                                              operator calls approve_phase
                                                      │
                                    graph.invoke(Command(resume="approve"), config)
                                                      │
                                    await_approval resumes → approve_phase_node
                                                      │
                                    graph continues to next phase
```

---

## Files to Modify

| File | Current State | Target State |
|------|--------------|--------------|
| `graph/graph.py:32` | `StateGraph(dict)` | `StateGraph(dict)` — no change yet (typed state is Phase 2) |
| `graph/graph.py:32` | `return builder.compile()` | `return builder.compile(checkpointer=MemorySaver())` |
| `graph/graph.py:50` | `builder.add_node("await_approval", _passthrough)` | `builder.add_node("await_approval", await_approval_node)` — new node |
| `graph/nodes.py` | No `await_approval_node` | New node with `interrupt()` call |
| `graph/nodes.py` | `approve_phase_node`, `request_revision_node` | Keep as-is (called inside gate node) |
| `graph/nodes.py` | `repair_phase_node` | Keep — called transitively when gate routes to repair |
| `graph/edges.py` | `after_phase()` routes to `"await_approval"` | Keep routing, but gate now pauses |
| `app/runtime.py:130` | `graph.invoke(state, config={recursion_limit: 50})` | `graph.invoke(state, config)` — no recursion_limit needed |
| `app/runtime.py:131-139` | Try/except `GraphRecursionError` | **Remove entirely** |
| `app/runtime.py:139-182` | `approve_phase()` manually calls nodes | `approve_phase()` calls `graph.invoke(Command(resume="approve"))` |
| `app/runtime.py:188-203` | `request_revision()` manually calls nodes | `request_revision()` calls `graph.invoke(Command(resume="revise"))` |
| `mcp/tools/__init__.py:502` | `rt.approve_phase()` | Keep — delegates to runtime which now uses graph resume |
| `mcp/tools/__init__.py:511` | `rt.request_revision()` | Keep — same pattern |
| `graph/interrupts.py` | Flag-setting only | Keep as helper (builds interrupt payload) |

---

## Step-by-Step

### Step 1: Add Checkpointer to Graph Compilation

**File:** `src/film_pipeline/graph/graph.py:130`

```python
# Current:
return builder.compile()

# Target:
from langgraph.checkpoint.memory import MemorySaver
return builder.compile(checkpointer=MemorySaver())
```

For Phase 1, in-memory is sufficient. Phase 7+ would add `SqliteSaver` for durability across restarts.

### Step 2: Create `await_approval_node` with `interrupt()`

**File:** `src/film_pipeline/graph/nodes.py` — new function, ~40 lines

```python
def await_approval_node(state: dict[str, Any]) -> dict[str, Any]:
    """Pause the graph for human review. Resumes via Command(resume=decision)."""
    from langgraph.types import interrupt

    # Build the review package payload (refs, not bodies)
    blocking_count = sum(
        1 for i in state.get("issues", [])
        if i.get("severity") == "blocking"
    )

    payload = {
        "project_id": state.get("project_id", ""),
        "phase": state.get("current_phase", ""),
        "gate": state.get("human_approval_phase", ""),
        "artifact_refs": state.get("artifact_refs", []),
        "blocking_issue_count": blocking_count,
        "allowed_actions": (
            ["approve_phase"] if blocking_count == 0
            else ["request_revision"]
        ),
    }

    # This PAUSES the graph. Resumes when graph.invoke(Command(resume=...), config) is called.
    decision = interrupt(payload)

    # Normalize and route
    if isinstance(decision, dict):
        action = decision.get("action", "")
        note = decision.get("note", "")
    elif isinstance(decision, str):
        action = decision
        note = ""
    else:
        action = "await"  # stay paused

    if action in ("approve", "approve_phase"):
        return approve_phase_node(state)
    elif action in ("revise", "request_revision"):
        return request_revision_node(state, note=note)
    else:
        # Re-interrupt — stay paused
        return state
```

**Important LangGraph constraint:** Code before `interrupt()` runs AGAIN on resume. The payload must be idempotent. Since we only read state (no writes), it is naturally idempotent.

### Step 3: Register the New Node in Graph

**File:** `src/film_pipeline/graph/graph.py:50`

```python
# Current:
builder.add_node("await_approval", _passthrough)

# Target:
builder.add_node("await_approval", await_approval_node)
```

Also update the import at top of `graph.py`:
```python
from film_pipeline.graph.nodes import (
    # ... existing imports ...
    await_approval_node,  # NEW
)
```

### Step 4: Update Runtime to Resume Graph

**File:** `src/film_pipeline/app/runtime.py`

**4a. Remove recursion_limit dependency:**

```python
# Current (lines 108-139):
def run_graph(self, state):
    graph = self.ensure_graph()
    from langgraph.errors import GraphRecursionError
    state = dict(state)
    state[SERVICES_KEY] = self.services
    try:
        return graph.invoke(
            state,
            config={
                "recursion_limit": 50,
                "configurable": {"thread_id": state.get("project_id", "default")},
            },
        )
    except GraphRecursionError:
        latest = dict(state)
        try:
            for event in graph.stream(
                state,
                config={
                    "recursion_limit": 50,
                    "configurable": {"thread_id": state.get("project_id", "default")},
                },
                stream_mode="values",
            ):
                latest = dict(event)
        except GraphRecursionError:
            pass
        return latest

# Target:
def run_graph(self, state):
    graph = self.ensure_graph()
    state = dict(state)
    state[SERVICES_KEY] = self.services
    config = {"configurable": {"thread_id": state.get("project_id", "default")}}
    return graph.invoke(state, config)
```

**4b. Rewrite `approve_phase()` to use graph resume:**

```python
# Current implementation manually calls approve_phase_node() then advance_to_next_phase()
# Target:
def approve_phase(self) -> dict[str, Any]:
    from langgraph.types import Command

    active = self.get_active()
    if not active:
        raise ValueError("No active project.")

    graph = self.ensure_graph()
    config = {"configurable": {"thread_id": active["project_id"]}}

    # Resume the graph with the approve decision
    state = graph.invoke(
        Command(resume={"action": "approve"}),
        config,
    )

    # Update stored state
    self.projects[active["project_id"]] = state
    self._persist_project_state(active["project_id"])

    # Create git checkpoint after approval
    checkpoint = self.create_checkpoint(
        project_id=active["project_id"],
        phase=str(state.get("current_phase", "")),
        reason=f"Approved at {state.get('human_approval_phase', '')} gate",
    )
    self._record_audit("human", "approve_phase", ...)

    return state
```

**4c. Rewrite `request_revision()` similarly:**

```python
def request_revision(self, note: str = "") -> dict[str, Any]:
    from langgraph.types import Command

    active = self.get_active()
    if not active:
        raise ValueError("No active project.")

    graph = self.ensure_graph()
    config = {"configurable": {"thread_id": active["project_id"]}}

    state = graph.invoke(
        Command(resume={"action": "revise", "note": note}),
        config,
    )

    self.projects[active["project_id"]] = state
    self._persist_project_state(active["project_id"])
    self._record_audit("human", "request_revision", note=note)

    return state
```

### Step 5: Remove `_advance_to_next_phase` and Manual Phase Running

**File:** `src/film_pipeline/app/runtime.py`

The `_advance_to_next_phase()` method (which manually calls phase nodes outside the graph) is no longer needed. The graph handles phase transitions via its edges.

**Remove or deprecate:**
- `_advance_to_next_phase()` — graph handles this now
- `_run_phase_node()` — graph handles this now
- `_approve_current_phase()` — graph handles this now

**Keep:**
- `create_project()` — unchanged
- `set_active()` — unchanged
- `create_checkpoint()` — still needed for git checkpoints
- `ensure_graph()` — still needed to lazy-load graph

### Step 6: Keep Git Checkpoints

The `CheckpointManager` system (git-backed, semantic milestones) runs AFTER graph-level approval. Do not remove it. It complements the LangGraph checkpointer:

| Checkpointer | Purpose | When |
|-------------|---------|------|
| LangGraph `MemorySaver` | Operational — resume after pause/crash | Every node transition |
| Git `CheckpointManager` | Semantic — audit, rollback, compliance | After approved phase gates |

---

## Test Cases

### Unit Tests (`tests/unit/test_graph.py`)

```python
def test_graph_compiles_with_checkpointer():
    """Graph compiles with MemorySaver checkpointer."""
    graph = build_graph()
    assert graph.checkpointer is not None

def test_await_approval_node_emits_interrupt():
    """await_approval_node calls interrupt() with expected payload keys."""
    # Use graph with checkpointer + config with thread_id
    state = {"project_id": "test", "current_phase": "intake", "artifact_refs": [], "issues": []}
    graph = build_graph()
    config = {"configurable": {"thread_id": "test"}}

    # First invoke should run intake_node then pause at await_approval
    # The graph will stop — we check the interrupt was raised
    result = graph.invoke(state, config)
    # After interrupt, state should have human_approval_required set
    assert result.get("current_phase") == "intake"

def test_blocking_issues_prevent_approval_in_payload():
    """Payload restricts allowed_actions when blocking issues exist."""
    state = {
        "project_id": "test", "current_phase": "shot_bible",
        "artifact_refs": [], "human_approval_phase": "shot_bible",
        "issues": [{"severity": "blocking", "code": "shot_count_mismatch", "message": "..."}],
    }
    # Build payload manually (test the logic without graph execution)
    payload = _build_approval_payload(state)
    assert "approve_phase" not in payload["allowed_actions"]
    assert "request_revision" in payload["allowed_actions"]
```

### Integration Tests (`tests/integration/test_mcp_flow.py`)

```python
def test_submit_idea_reaches_interrupt():
    """submit_idea runs graph which pauses at intake gate."""
    rt = create_runtime("mock")
    rt.create_project("test-interrupt")
    rt.set_active("test-interrupt")

    state = rt.run_graph({"project_id": "test-interrupt", "idea": "A short film"})

    assert state["human_approval_required"] is True
    assert state["current_phase"] == "intake"

def test_approve_phase_resumes_graph():
    """approve_phase resumes graph past intake gate to constitution."""
    rt = create_runtime("mock")
    rt.create_project("test-approve")
    rt.set_active("test-approve")

    # Submit idea → pauses at intake gate
    rt.run_graph({"project_id": "test-approve", "idea": "A short film"})

    # Approve → graph resumes and advances
    state = rt.approve_phase()

    assert state["current_phase"] == "constitution"

def test_request_revision_adds_issue():
    """request_revision resumes graph with revision decision."""
    rt = create_runtime("mock")
    rt.create_project("test-revise")
    rt.set_active("test-revise")

    rt.run_graph({"project_id": "test-revise", "idea": "A short film"})

    state = rt.request_revision(note="Please adjust the tone to be darker.")

    issues = state.get("issues", [])
    assert any("REVISION_REQUESTED" in str(i.get("code", "")) for i in issues)
```

### E2E Test (`tests/e2e/test_graph_execution.py`)

```python
def test_full_happy_path_no_recursion_error():
    """Full pipeline runs without GraphRecursionError."""
    rt = create_runtime("mock")
    rt.create_project("test-e2e")
    rt.set_active("test-e2e")

    # Should NOT raise GraphRecursionError
    rt.run_graph({"project_id": "test-e2e", "idea": "A short film"})

    # Approve through intake
    rt.approve_phase()
    # Should now be at constitution
    assert rt.get_active()["current_phase"] == "constitution"
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `interrupt()` code re-executes on resume → side effects doubled | Payload construction reads state only (no writes). Review package generation is idempotent by key. |
| MCP tools must coordinate `thread_id` with graph | `thread_id = project_id` — already deterministic. |
| MemorySaver loses state on process restart | Acceptable for Phase 1. Phase 7+ swaps to `SqliteSaver`. |
| `Command` object compatibility with pinned LangGraph version | Check installed LangGraph version supports `Command(resume=...)`. If not, use `None` as resume value + `config` pattern. |
| Existing tests break because `await_approval` is no longer a passthrough | Update tests that assert on passthrough behavior. |

---

## Acceptance Criteria

- [ ] `build_graph()` returns graph compiled with `MemorySaver()`
- [ ] `await_approval_node` calls `interrupt()` with structured payload
- [ ] `submit_idea` graph.invoke() reaches interrupt, does NOT hit `GraphRecursionError`
- [ ] `approve_phase` MCP tool calls `graph.invoke(Command(resume={"action": "approve"}), config)`
- [ ] `request_revision` MCP tool calls `graph.invoke(Command(resume={"action": "revise"}), config)`
- [ ] `run_graph()` does not catch `GraphRecursionError` (no try/except block)
- [ ] Git checkpoints still created at approved phase boundaries
- [ ] MCP remains the only operator-facing control path
- [ ] All existing tests pass (updated where `await_approval` behavior changed)
- [ ] New tests: interrupt payload structure, approve resume, revision resume, blocking issues prevent approval
- [ ] `make ci-check` green

**Estimated implementation time:** 2-3 hours
**Prerequisite:** None (Phase 0 optional, can be done before or after)
