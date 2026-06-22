# 01 — Core Building Blocks: Nodes, Edges, State

**Date:** 2026-06-22
**Question:** Are we using LangGraph's core building blocks (Nodes, Edges, State) correctly? How, why, where? How can we optimize?

---

## 1. State — The Shared Memory

### What We Have

The graph uses **`StateGraph(dict)`** — an untyped `dict[str, Any]` as the state schema.

```python
# graph.py line 32
builder = StateGraph(dict)
```

#### State structure (flat dict, no schema)

| Key | Type | Purpose |
|-----|------|---------|
| `current_phase` | `str` | Active phase (intake, constitution, …, delivery) |
| `approved` | `bool` | Whether current phase is approved |
| `human_approval_required` | `bool` | Gate flag — pauses for human review |
| `human_approval_phase` | `str` | Which gate label is active |
| `project_id` | `str` | Active project identifier |
| `issues` | `list[dict]` | Validation issues (severity, code, message) |
| `artifact_refs` | `list[str]` | Accumulated artifact references (`artifact:id:v1`) |
| `*_ref` keys | `str` | Named ref pointers (e.g. `script_ref`, `shot_matrix_ref`) |
| `_services` | `GraphServices` | Injected service bundle (agents, artifact store, prompt runner) |
| `_orchestrator__*` | various | Namespaced orchestrator state (refs, cycles, revisions, routing, convergence, provider health, budget, execution brief) |
| `_repair_feedback` | `str` | Transient repair feedback string |
| `_validation_reports` | `list[dict]` | Accumulated validator reports |
| `_routing_decisions` | `list[dict]` | Agent handoff records |
| `_approval_blocked_by_issues` | `bool` | Temporary flag set by approve_phase_node |
| `resolved_config` | `dict` | Profile/config from intake |
| `generation_requests` | `list` | Provider dispatch plan from gen_planning |
| `completed` | `bool` | Final phase flag |

#### Orchestrator state sub-domain (`orchestrator_state.py`)

Because the state is untyped, we namespaced a sub-domain with `_orchestrator:` prefixed keys:

- **Candidate/approved refs:** version tracking per artifact family
- **Review cycles:** per-phase review state (round count, strategy, status)
- **Revision requests:** durable revision tracking
- **Routing decisions:** explainable routing audit trail
- **Convergence tracking:** per-phase repair round counter, stall detection
- **Failure decisions:** failure handler output
- **Provider health snapshot:** cached provider status
- **Budget snapshot:** cap, spent, remaining, threshold exceeded
- **Execution brief:** structural contract for the film

Each domain has typed getter/setter functions (40+ helpers total).

#### How state flows

1. Every node receives the full state dict
2. Every node does `new_state = deepcopy(state)` — full deep copy on entry
3. Node mutates `new_state` and returns it
4. LangGraph merges the returned dict into the graph state (default reducer: replace keys)
5. Services are injected at graph invocation time via `state[SERVICES_KEY] = self.services` in `StudioRuntime.run_graph()`

### What We Don't Have / Gaps

| Gap | Severity | Detail |
|-----|----------|--------|
| **No typed state schema** | High | `StateGraph(dict)` gives zero compile-time or runtime type safety. Any key can be set anywhere with any type. Typos in state keys cause silent failures (e.g. `currnt_phase` instead of `current_phase`). |
| **No per-key reducers** | Medium | LangGraph supports typed state with per-key reducers (append, merge, replace). We lose this entirely — every state update is a full-key replacement. No append-only lists, no additive counters. |
| **No state channel segregation** | Medium | The flat dict is a "god object" — orchestrator state, phase artifacts, config, issues, services all live in one namespace. The `_orchestrator:` prefix is a workaround, not a solution. |
| **Deep-copy antipattern** | Medium | Every node calls `deepcopy(state)` (~15 nodes). As state grows (accumulated artifacts, routing decisions, audit trails), this gets linearly more expensive. LangGraph's native state model avoids this — nodes return partial updates, the framework handles merging. |
| **Services via magic key** | Low | `_services` is injected as a state key and must be stripped before serialization. LangGraph supports passing config/runnables through the config dict instead. |
| **No Pydantic state model** | Medium | LangGraph supports `StateGraph(BaseModel)` for full validation. We could use Pydantic v2 (already a dependency) for typed, validated state with runtime enforcement. |

### Optimization Recommendations

1. **Migrate to `TypedDict` state** — Define an `OrchestratorState(TypedDict)` with per-key reducers:
   ```python
   class OrchestratorState(TypedDict):
       current_phase: str
       approved: bool
       issues: Annotated[list[dict], add]       # append-only
       artifact_refs: Annotated[list[str], add]  # append-only
       # ... all keys typed
   ```
   This gives IDE autocomplete, mypy type checking, and correct reducer behavior.

2. **Remove `deepcopy(state)`** — With typed reducers, nodes return only the keys they changed. LangGraph handles merging. No manual deep copies.

3. **Split state into domains** — Use separate TypedDicts for orchestrator state, phase state, and execution state, combined via composition.

4. **Move services to config** — Pass `GraphServices` through `config["configurable"]` instead of the state dict.

---

## 2. Nodes — The Actions

### What We Have

17 registered nodes in a linear pipeline:

```
phase_router → [phase_node] → await_approval → end
                                  ↕ (approve/revision/repair)
```

**Control nodes** (passthrough — just return state):
- `phase_router` — routes to the correct phase node based on `current_phase`
- `await_approval` — pause point (state flag only)
- `end` — terminal node → `END`

**Gate nodes** (mutate state):
- `approve_phase_node` — promotes candidate refs → approved refs, guards against blocking issues
- `request_revision_node` — adds REVISION_REQUESTED issue, creates durable revision request
- `repair_phase_node` — generic repair: looks up phase node, injects feedback, re-runs, tracks convergence (max 3 rounds)

**Phase nodes** (11 nodes — one per film production phase):

| Node | File Location | Implements |
|------|--------------|------------|
| `intake_node` | `nodes.py:422` | Full: runs IntakeAgent, saves profile |
| `constitution_node` | `nodes.py:445` | Full: runs ConstitutionAgent, saves constitution |
| `development_node` | `nodes.py:472` | Full: runs DevelopmentAgent, saves treatment + scene list |
| `script_node` | `nodes.py:516` | Full: runs ScreenwriterAgent, saves story bible + script |
| `visual_dev_node` | `nodes.py:555` | Full: runs VisualDevAgent, saves reference index |
| `shot_bible_node` | `nodes.py:581` | Full: runs StructureExtractorAgent → ShotBibleAgent, Gate A validation |
| `gen_planning_node` | `nodes.py:641` | Full: runs GenPlannerAgent, Gate B validation |
| `generation_node` | `nodes.py:703` | Partial: Gate C validation only, no real generation |
| `qc_node` | `nodes.py:720` | Full: runs all validators + QCSynthesisAgent |
| `post_node` | `nodes.py:1087` | Full: runs AssemblyAgent, saves assembly manifest |
| `delivery_node` | `nodes.py:1119` | Stub: sets flags only |

**Node implementation pattern:**

Every node follows the same structure:
```python
def X_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "X"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "gate_label"
    # ... agent execution, artifact saving, validation ...
    return new_state
```

**Agent execution** (`_run_agent()`, lines 24-218 in `nodes.py`):
- 195-line mega-function handling: repair feedback injection, dynamic agent routing, model selection, prompt template lookup, context injection (8 artifact types), KB context building, model output routing, agent class dispatch (11 agents), handoff recording
- Critical-path agents get dedicated prompt templates; non-critical agents get generic RCTCO assembly
- Artifact context injection loads up to 8 upstream artifacts into prompt context

**Validator execution** (`_run_validators()`, lines 756-868):
- Dispatches 6 validator families based on current phase
- QC phase scans all 7 upstream phases for artifacts
- Builds consensus reports when ≥2 validators produce reports

### What We Don't Have / Gaps

| Gap | Severity | Detail |
|-----|----------|--------|
| **No node-level error handling** | High | If any node raises an unhandled exception, the graph fails. No try/except around `_run_agent()` or `_save_artifact()`. The validator dispatch has per-validator try/except but the agent execution path doesn't. |
| **Monolithic `_run_agent()`** | High | 195-line function with 11 imports inside the function body (lazy to avoid circular imports). Mixes routing, prompting, model calling, parsing, artifact injection, and audit recording. Hard to test in isolation. |
| **Subgraphs are stubs** | Medium | `subgraphs/` directory exists with per-phase modules but they just re-export from `nodes.py`. The docstring says "will eventually contain internal router → creator agent → reviewer → validator → orchestrator synthesis flow" — not implemented. |
| **No node composition** | Medium | Nodes are flat functions. No way to compose a node from reusable pieces (e.g. `agent_step + validate + save_artifact`). The pattern is copy-pasted 11 times. |
| **generation_node is a stub** | Medium | Only runs Gate C validation. Real generation (provider dispatch, polling, download, ledger) lives elsewhere or is pending. |
| **`_passthrough` nodes** | Low | `phase_router`, `await_approval`, and `end` are pure identity functions. LangGraph could handle this routing without explicit passthrough nodes. |
| **No node timeouts** | Low | No timeout or cancellation mechanism for long-running agent calls. |

### Optimization Recommendations

1. **Extract `_run_agent()` into a composable pipeline:**
   ```
   prepare_context → select_agent → build_prompt → call_model → parse_output → record_handoff
   ```
   Each step is independently testable.

2. **Add per-node error boundaries** — wrap `_run_agent()` calls in try/except that capture errors as state issues rather than crashing the graph.

3. **Implement subgraphs** — Each phase subgraph should be a compiled `StateGraph` with internal router → agent → reviewer → validator flow. The parent graph treats each subgraph as a single node.

4. **Deduplicate node boilerplate** — The 5-line preamble (`deepcopy`, `current_phase`, `approved`, `human_approval_required`, `human_approval_phase`) repeats identically in all 11 phase nodes. Extract a decorator or context manager.

5. **Replace passthrough nodes** — Use LangGraph's conditional entry points or `Command` for phase routing without explicit passthrough nodes.

---

## 3. Edges — The Pathways

### What We Have

**Entry point:**
```python
builder.set_entry_point("phase_router")
```

**Phase router → phase nodes** (1 conditional edge):
```python
builder.add_conditional_edges(
    "phase_router", _route_current_phase,
    {phase: f"{phase}_node" for phase in PHASE_ORDER}
)
```

**Phase nodes → await_approval** (11 conditional edges, all identical):
```python
# Every phase node has this exact pattern:
builder.add_conditional_edges("X_node", after_phase, {"await_approval": "await_approval"})
```
Despite being `add_conditional_edges`, the mapping only has ONE target — functionally a normal edge. The condition function (`after_phase()`) computes orchestrator actions (8-tier priority) but the edge map ignores everything except `"await_approval"`.

**await_approval → next phase / repair / end** (1 conditional edge, 12 targets):
```python
builder.add_conditional_edges(
    "await_approval", after_approval,
    {
        phase: f"{phase}_node" for phase in PHASE_ORDER
    } | {"end": "end", "repair": "repair", "await_approval": "await_approval"}
)
```
This is the real decision point. `after_approval()` routes:
- Approved → next phase node (constitution, development, …, end)
- Issues exist → repair node
- Neither → await_approval (stay)

**Gate → await_approval** (3 normal edges):
```python
builder.add_edge("approve_phase", "await_approval")
builder.add_edge("request_revision", "await_approval")
builder.add_edge("repair", "await_approval")
```

**Terminal:**
```python
builder.add_edge("end", END)
```

### Graph topology (simplified):

```
                    ┌─────────────┐
                    │ phase_router │
                    └──────┬──────┘
                           │ (conditional: which phase?)
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        intake_node  constitution_node  ... delivery_node
              │            │                  │
              └────────────┼──────────────────┘
                           │ (all → after_phase → "await_approval")
                           ▼
                    ┌──────────────┐
                    │await_approval│◄──────────────────┐
                    └──────┬───────┘                   │
                           │ (conditional: approved?   │
                           │  issues? next phase?)     │
               ┌───────────┼───────────┬──────────────┐│
               ▼           ▼           ▼              ││
         next_phase    repair       end              ││
         (e.g.         │                             ││
         constitution) │                             ││
               │       ▼                             ││
               │   [repair re-runs                    ││
               │    current phase]                    ││
               │       │                             ││
               └───────┴─────────────────────────────┘│
                                                      │
         approve_phase ───────────────────────────────┘
         request_revision ────────────────────────────┘
```

### What We Don't Have / Gaps

| Gap | Severity | Detail |
|-----|----------|--------|
| **Fake conditional edges on phase nodes** | Medium | 11 edges declared as conditional but mapping to a single target. Should be normal edges, or the condition should actually route to different nodes (e.g. phase → repair if issues, phase → next if auto-advance). |
| **Single bottleneck at `await_approval`** | Medium | Every decision (advance, repair, stall, end) funnels through one node. This works but makes the routing function (`after_approval`) a 20-line switch statement that must know about every possible transition. |
| **No LangGraph `interrupt()` usage** | High | The `interrupts.py` module only sets `human_approval_required = True` as a state flag. It does NOT call `interrupt()` — LangGraph never actually pauses. The "human gate" is emulated through state + routing. This means the graph runs to completion on every `invoke()`, and the runtime manually advances phases. |
| **No dynamic parallel edges (Send API)** | Medium | LangGraph's `Send` API allows fan-out to N nodes in parallel. Not used. Validators are run sequentially in `_run_validators()` even though they're independent. |
| **No Command objects** | Low | LangGraph v0.2+ `Command(goto=..., update=...)` combines state update + routing. Not used; nodes return state dicts and routing is separate. |
| **No cycle detection / infinite loop protection** | Low | The repair → await_approval → repair cycle has convergence tracking (max 3 rounds in `repair_phase_node`), but the general graph has no built-in cycle guard beyond the `recursion_limit=50` config. |

### Optimization Recommendations

1. **Use real LangGraph interrupts for human gates:**
   ```python
   from langgraph.types import interrupt

   def await_approval_node(state):
       decision = interrupt({"phase": state["current_phase"], "artifacts": state["artifact_refs"]})
       if decision == "approve":
           return approve_phase_node(state)
       else:
           return request_revision_node(state)
   ```
   This makes the graph genuinely pause, supports resume via `Command(resume=...)`, and is the canonical LangGraph pattern for human-in-the-loop.

2. **Replace pseudo-conditional edges with normal edges:**
   ```python
   builder.add_edge("intake_node", "await_approval")
   builder.add_edge("constitution_node", "await_approval")
   # ... etc
   ```
   Unless we want phase nodes to auto-route to different targets based on state.

3. **Use Send for parallel validator execution:**
   ```python
   from langgraph.types import Send

   def fanout_validators(state):
       return [Send("script_structure_validator", state),
               Send("dialogue_voice_validator", state)]
   ```
   This would run validators in parallel instead of sequentially.

4. **Add a cycle guard node** — a node that checks `recursion_limit` state and forces `END` if the graph has looped too many times, independent of the per-phase convergence tracking.

---

## Summary: Maturity Assessment

| Concept | Status | Maturity |
|---------|--------|----------|
| **State** | `StateGraph(dict)` — untyped, no reducers, deep-copy pattern | 🔶 Functional but fragile |
| **Nodes** | 17 nodes, 11 full, 1 partial, 1 stub, 4 gate nodes | 🟢 Mostly implemented |
| **Edges** | Conditional + normal edges, single bottleneck pattern | 🟢 Working |
| **Interrupts** | Simulated via state flags, not real LangGraph interrupts | 🔴 Missing |
| **Subgraphs** | Directory exists, all stubs | 🔴 Not implemented |
| **Parallelism** | No Send API, sequential validators | 🔴 Not leveraged |
| **State typing** | No TypedDict or Pydantic schema | 🔴 Missing |
| **Checkpointer** | Custom git-backed, not LangGraph's checkpointer API | 🟡 Custom works but misses native resume |

### Priority Optimization Order

1. **P0:** Real LangGraph interrupts for human gates — currently simulated, fragile
2. **P0:** Typed state (TypedDict with reducers) — eliminates entire class of bugs
3. **P1:** Remove `deepcopy(state)` antipattern — performance as state grows
4. **P1:** Extract `_run_agent()` into composable pipeline
5. **P2:** Implement subgraphs for phases with internal agent→validator flow
6. **P2:** Use Send API for parallel validator execution
7. **P3:** Node error boundaries, deduplicate boilerplate, cycle guards

### Files Referenced

| File | Lines | Role |
|------|-------|------|
| `src/film_pipeline/graph/graph.py` | 132 | Graph construction |
| `src/film_pipeline/graph/nodes.py` | 1198 | Node definitions |
| `src/film_pipeline/graph/edges.py` | 80 | Conditional edge functions |
| `src/film_pipeline/graph/router.py` | 285 | Action + agent routing |
| `src/film_pipeline/graph/orchestrator_state.py` | 428 | Namespaced state helpers |
| `src/film_pipeline/graph/interrupts.py` | 58 | Human gate flags (not real interrupts) |
| `src/film_pipeline/graph/services.py` | 210 | Service injection |
| `src/film_pipeline/graph/subgraphs/` | 13 files | Phase subgraphs (all stubs) |
| `src/film_pipeline/app/runtime.py` | 316 | Graph invocation, checkpoint, audit |
