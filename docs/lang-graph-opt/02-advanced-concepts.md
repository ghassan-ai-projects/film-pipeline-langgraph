# 02 — Advanced Concepts: Persistence, Human-in-the-Loop, Multi-Agent

**Date:** 2026-06-22
**Question:** Are we using LangGraph's advanced concepts (persistence/checkpointing, human-in-the-loop, multi-agent subgraphs) optimally? Do we need them? What other concepts are useful but unused?

---

## 1. Persistence & Checkpointing

### LangGraph's Model vs Our Implementation

LangGraph provides automatic checkpointing: pass a checkpointer to `graph.compile(checkpointer=...)` and every node transition is saved. On crash or resume, the graph picks up from the last successful step. This also enables time-travel debugging and replay.

#### What We Built Instead

We built a **custom git-backed checkpoint system** (`checkpoints/` module) that operates **outside** the graph:

| Component | File | Role |
|-----------|------|------|
| `CheckpointManager` | `checkpoints/manager.py` | Creates semantic checkpoints as git commits + annotated tags |
| `GitBackend` | `checkpoints/git_backend.py` | Thin git wrapper (commit, tag, branch, restore) |
| `InvalidationEngine` | `checkpoints/invalidation.py` | Declarative dependency graph — computes what gets invalidated by a rollback |

**How checkpoints are created today:**

```python
# In StudioRuntime.approve_phase() — runtime.py:170-184
checkpoint = self.create_checkpoint(
    project_id=active["project_id"],
    phase=current_phase,
    reason=f"Approved {current_phase}",
)
# → CheckpointManager.create()
#   → git commit (project-state.json)
#   → git tag (checkpoint/intake-a1b2c3)
#   → stores CheckpointMetadata in-memory
```

The graph itself has **zero awareness** of checkpoints:
- `graph.invoke()` receives `config={"recursion_limit": 50, "configurable": {"thread_id": ...}}` but **no checkpointer**.
- No `MemorySaver`, no `SqliteSaver`, no `InMemorySaver` anywhere in the codebase.
- Checkpoints are created by the **runtime** (not the graph) at manual approval boundaries.

**Rollback works through MCP tools** — `rollback_artifact` and `rollback_to_checkpoint` call `InvalidationEngine` then restore files via `GitBackend.restore_files()`. The runtime state dict is manually replaced.

#### What We Have vs What LangGraph Provides

| Capability | Our Custom System | LangGraph Built-in |
|-----------|-------------------|-------------------|
| **Auto-save every step** | ❌ Manual at approval gates only | ✅ Every node transition |
| **Crash recovery** | ❌ No — if `run_graph()` dies mid-phase, state is lost | ✅ Resume from last checkpoint |
| **Time travel / replay** | ⚠️ Manual via git tags — git-based restore of JSON state | ✅ Native `get_state(config)` with step index |
| **Thread isolation** | ✅ Per-project git repos | ✅ Thread ID in config |
| **Serialization** | ✅ JSON project-state.json | ✅ Built-in (pickle, json, msgpack) |
| **Human-readable history** | ✅ git log is natively browsable | ⚠️ Requires LangGraph Studio or custom tooling |
| **Branching** | ✅ Git branches for exploration | ⚠️ Possible via forked thread IDs |
| **Dependency-aware rollback** | ✅ `InvalidationEngine` with dependency graph | ❌ Not built-in (you'd build it on top of state) |
| **Streaming restores** | ❌ Full state file replacement | ✅ Incremental state replay |

### Verdict: Custom System Is Valuable but Should Augment, Not Replace

**What's good about our system:**
- Git gives us an immutable, auditable, human-browsable history — better than LangGraph's opaque binary checkpoints for compliance/audit.
- The `InvalidationEngine` dependency graph is genuinely useful and has no LangGraph equivalent.
- Tag-based semantic checkpoints are more meaningful than step-index-based ones.

**What's missing:**
- **No auto-checkpoint on every node transition.** If the process crashes mid-`script_node`, we lose everything since the last manual checkpoint.
- **No true resume.** The `run_graph()` fallback to `graph.stream()` on `GraphRecursionError` (runtime.py:131-139) is a workaround, not checkpoint-based resume.
- **No step-level debugging.** Can't say "show me state after node 7."

### Recommendation: Hybrid Approach

Keep our git-backed checkpoint system for **semantic, human-facing checkpoints** (approval gates, major milestones). Add LangGraph's checkpointer for **operational resilience**:

```python
from langgraph.checkpoint.memory import MemorySaver  # or SqliteSaver for persistence

graph = builder.compile(checkpointer=MemorySaver())

# Resume from thread_id if it already has state
config = {"configurable": {"thread_id": project_id}}
state = graph.invoke(initial_state, config)
```

Benefits:
- Crash recovery: graph picks up from last successful node.
- Time travel: `graph.get_state(config)` to inspect any step.
- Replay: re-run from any checkpoint with modified state.
- Dual-commit: save LangGraph checkpoints to disk + our semantic git tags at approval gates.

---

## 2. Human-in-the-Loop (Interrupts)

### LangGraph's Model

LangGraph provides `interrupt()` — a function that pauses graph execution, serializes state, and waits for external input:

```python
from langgraph.types import interrupt

def approval_node(state):
    decision = interrupt({"review_package": build_package(state)})
    if decision == "approve":
        return {"approved": True}
    return {"issues": [{"code": "REVISION_REQUESTED"}]}
```

The graph stops. An external caller calls `graph.invoke(Command(resume="approve"), config)` to resume. This is the **canonical LangGraph human-in-the-loop pattern**.

Additional mechanisms:
- `interrupt_before=["await_approval"]` — auto-pause before a node.
- `interrupt_after=["intake_node"]` — auto-pause after a node.
- `Command(resume=...)` — resume with human input.

### What We Built Instead

We **simulate** interrupts through **state flags + routing loops**:

```python
# Every phase node sets these flags:
new_state["human_approval_required"] = True
new_state["human_approval_phase"] = "config"
new_state["approved"] = False

# routing: after_phase() returns "await_approval" when human_approval_required
# after_approval() returns next phase only when approved == True
```

The `interrupts.py` module **never calls `interrupt()`**:

```python
# interrupts.py:27-42 — docstring says "LangGraph interrupt() call"
# but the actual code just sets dict keys:
def interrupt_for_gate(state, phase, gate):
    state["human_approval_required"] = True  # <-- not interrupt()
    state["human_approval_phase"] = gate
    state["current_phase"] = phase
    state["approved"] = False
    return state
```

The graph **never actually pauses**. Instead, `StudioRuntime.run_graph()` calls `graph.invoke()` which runs until it hits `END` or `recursion_limit=50`. The "gate" is:

1. Graph runs `intake_node` → sets `human_approval_required=True` → returns to `await_approval` (passthrough) → `after_approval` sees no approval → returns `"await_approval"` → loops until `recursion_limit=50`.
2. `run_graph()` catches `GraphRecursionError`, falls back to `graph.stream()` to extract the last stable state.
3. Human calls `approve_phase` MCP tool → `runtime.approve_phase()` manually calls `approve_phase_node()` and `intake_node()` directly (NOT through the graph).
4. The graph is only invoked again at `submit_idea` time.

**The graph itself is used as a single-phase runner**, not a continuous execution engine.

#### Gap Analysis

| Aspect | Current (State-Flag Simulation) | Proper LangGraph Interrupts |
|--------|--------------------------------|----------------------------|
| **Graph pauses mid-execution** | ❌ Runs to recursion limit, then crashes | ✅ Pauses cleanly at the interrupt point |
| **Resume with human input** | ❌ Human calls separate MCP tool; state manually merged | ✅ `Command(resume=decision)` |
| **State integrity across pause** | ⚠️ Extracted from recursion error fallback | ✅ Serialized by LangGraph checkpointer |
| **Multi-turn conversation** | ❌ Each phase is a separate graph invoke | ✅ Graph stays alive across interrupts |
| **Approval rejection path** | ⚠️ Manual `request_revision_node()` call | ✅ `Command(resume="reject")` → graph routes naturally |
| **Timeout handling** | ❌ None | ✅ Can set timeouts on interrupts |
| **Parallel approvals** | ❌ Single-project-only | ✅ Multi-thread with thread IDs |

### Verdict: This Is the Biggest Architectural Gap

The current approach:
- Burns `recursion_limit=50` unnecessarily — the graph loops `await_approval → await_approval` until the limit triggers.
- Relies on catching `GraphRecursionError` as a control flow mechanism.
- Requires the runtime to manually advance phases outside the graph.
- Cannot support a true human-in-the-loop workflow where a human reviews, rejects, and the graph naturally re-runs the phase with feedback.

### Recommendation: Adopt Real LangGraph Interrupts

```python
# Replace await_approval passthrough with:
def await_approval_node(state):
    from langgraph.types import interrupt

    package = ReviewPackageGenerator().build(
        project_id=state["project_id"],
        phase=FilmPhase(state["current_phase"]),
        summary=f"Review {state['current_phase']} output",
        current_artifacts=state.get("artifact_refs", []),
        has_blocking_issues=any(i.get("severity") == "blocking" for i in state.get("issues", [])),
        has_checkpoint=True,
    )
    decision = interrupt(package.model_dump())

    if decision == "approve":
        return approve_phase_node(state)
    return request_revision_node(state, note=decision.get("note", ""))
```

Then the MCP tool becomes:

```python
async def approve_phase(args):
    from langgraph.types import Command
    graph = rt.ensure_graph()
    state = graph.invoke(
        Command(resume="approve"),
        config={"configurable": {"thread_id": active["project_id"]}}
    )
    return _ok(project_id=state["project_id"])
```

This eliminates the `GraphRecursionError` hack, the manual phase advancement, and the complex recursion-limit workaround.

---

## 3. Multi-Agent Systems (Subgraphs)

### LangGraph's Model

Subgraphs allow composing graphs from other graphs. A node can be an entire compiled `StateGraph` with its own internal nodes, edges, and routing:

```python
# Parent graph
builder.add_node("intake", intake_subgraph.compile())
builder.add_node("script", script_subgraph.compile())

# Each subgraph has internal structure:
# intake_subgraph: router → classifier → config_inference → validator → synthesizer
```

LangGraph also provides:
- **Send API** for dynamic parallel fan-out: `Send("worker", {"task": task_i})` to N nodes.
- **Command** for combined state update + routing in a single return.
- **ToolNode** for wrapping tools as graph nodes.

### What We Have

The `subgraphs/` directory exists with **13 per-phase modules** but **all are stubs**:

```
subgraphs/
├── __init__.py       # "Each subgraph wraps a phase node and will eventually contain..."
├── intake.py         # from film_pipeline.graph.nodes import intake_node
├── constitution.py   # from film_pipeline.graph.nodes import constitution_node
├── development.py    # from film_pipeline.graph.nodes import development_node
├── screenwriting.py  # from film_pipeline.graph.nodes import script_node
├── visual_dev.py     # from film_pipeline.graph.nodes import visual_dev_node
├── shot_bible.py     # from film_pipeline.graph.nodes import shot_bible_node
├── gen_planning.py   # from film_pipeline.graph.nodes import gen_planning_node
├── generation.py     # from film_pipeline.graph.nodes import generation_node
├── qc.py             # from film_pipeline.graph.nodes import qc_node
├── post.py           # from film_pipeline.graph.nodes import post_node
└── delivery.py       # from film_pipeline.graph.nodes import delivery_node
```

**Every single one** is just `from film_pipeline.graph.nodes import X_node; __all__ = ["X_node"]`.

The parent graph in `graph.py` directly references the flat node functions:

```python
builder.add_node("intake_node", intake_node)        # flat function
builder.add_node("script_node", script_node)        # flat function
# NOT:
# builder.add_node("intake", intake_subgraph)         # compiled subgraph
```

### What the Architecture Blueprint Intended

From `docs/architecture-blueprint.md`:

> Use a layered graph: top-level project graph, phase subgraphs, action nodes, validation nodes, human interrupt nodes, repair nodes, rollback nodes, provider-block nodes, wrap/lesson nodes.

The blueprint envisioned each phase as a subgraph with internal structure:
```
shot_bible_subgraph:
  router → creator_agent → reviewer → validator → orchestrator_synthesis → human_gate
```

Instead, all of this logic is in a single 1198-line `nodes.py` where `shot_bible_node()` directly does: agent execution, validation, artifact saving — all in one function.

### What We'd Gain from Real Subgraphs

| Benefit | Detail |
|---------|--------|
| **Isolation** | A bug in the script subgraph can't corrupt state used by the visual_dev subgraph. |
| **Independent state** | Subgraphs can have their own state schemas, clean internal state, separate from parent state. |
| **Reusability** | The "router → agent → validate → save" pattern could be a generic subgraph factory parameterized by agent contract. |
| **Parallelism** | Subgraphs are natural parallelism boundaries — visual_dev and shot_bible could run concurrently if their inputs are ready. |
| **Testing** | Each subgraph can be compiled and tested independently before integration. |
| **Observability** | LangGraph's tracing shows subgraph boundaries clearly. Currently, the flat graph makes it hard to see phase transitions. |
| **Error boundaries** | Subgraph failures are scoped — a crash in one subgraph doesn't kill the parent. |

### Other LangGraph Concepts We Don't Use Yet

| Concept | What It Does | Relevant? |
|---------|-------------|-----------|
| **Send API** | Dynamic fan-out to N parallel nodes | ✅ **Highly relevant** — validators (6 types), coverage generation (N shots per scene), multi-model consensus all benefit from parallel execution |
| **Command** | Combined state update + routing in one return | ✅ **Relevant** — would simplify nodes that currently compute routing separately via `after_phase()` |
| **ToolNode** | Wraps tools as graph nodes | ⚠️ **Maybe** — our validators and agents are already function-based; ToolNode would add overhead without clear benefit |
| **Pregel-style map-reduce** | Map N subgraphs over a list, reduce results | ✅ **Highly relevant** — shot generation: map each shot group to a generation worker, reduce into a ledger |
| **Dynamic breakpoints** | Programmatic `interrupt()` calls at arbitrary points | ✅ **Relevant** — for mid-generation cost checks, quota exhaustion gates |
| **Streaming modes** | `stream_mode="updates"`, `"values"`, `"debug"` | ✅ **Relevant** — MCP tools could stream phase progress to the UI |
| **Config schema** | Typed `RunnableConfig` for passing services/metadata | ✅ **Relevant** — services currently piggyback on state via `_services` key |

### Verdict: Subgraphs Are a Design Win, Not Just a Nicety

The 13 stub files prove subgraphs were planned. The architecture blueprint explicitly calls for them. The current flat-graph approach:
- Forces all logic into `nodes.py` (1198 lines, single responsibility violation).
- Makes parallel execution impossible (validators, coverage generation).
- Prevents independent testing of phase internals.

### Recommendation: Phase 1 Subgraph — Start with QC as a Model

QC is the most internally complex phase (runs 6 validator families from 7 upstream phases, synthesizes consensus, builds reports). It's the best candidate for a real subgraph:

```
QC Subgraph:
  ┌─────────────┐
  │ load_artifacts│ ← loads from all 7 upstream phases
  └──────┬──────┘
         │ Send API: fan out to 6 validators in parallel
    ┌────┼────┬────┬────┬────┐
    ▼    ▼    ▼    ▼    ▼    ▼
  [Script] [Dialogue] [Ref] [Prompt] [Continuity] [Assembly]
  Struct   Voice      Usab   Readin   SceneCont   Validator
    │     │     │     │     │     │
    └────┴────┴────┴────┴────┘
         │ (reduce: collect all reports)
         ▼
  ┌──────────────┐
  │ consensus_build│ ← ConsensusBuilder (already exists)
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ human_gate    │ ← interrupt()
  └──────────────┘
```

Proven: this would replace ~150 lines of `_run_validators()` + `_build_consensus_if_needed()` with a compiled subgraph that runs validators in parallel via `Send`.

---

## 4. Concepts We Don't Need (Yet)

Some LangGraph features are tempting but would be premature optimization:

| Concept | Why Not Yet |
|---------|------------|
| **Custom channels / BinaryOperatorAggregate** | Only needed for complex state merge logic. Our state needs are simple: append lists, replace strings. Type reducers (`add`, `operator.add`) suffice. |
| **Dynamic Pregel channels** | For graphs that reconfigure themselves mid-run. Our graph structure is static per project. |
| **ToolNode with tool calling** | Our agents call LLMs and parse JSON — not OpenAI function-calling format. ToolNode would require refactoring all prompt contracts. |
| **LangGraph Cloud / LangGraph Platform** | Only relevant for deployed production. We're in local/SaaS operation mode. |
| **Store (durable KV)** | We already have `ArtifactStore` with file-backed persistence. Redundant. |
| **Langgrapqh checkpointer with PostgresSaver** | Overkill for single-user local operation. MemorySaver or file-backed SqliteSaver is sufficient. |

---

## 5. Priority Optimization Roadmap

### P0 — Must Have (Correctness & Safety)

1. **Real LangGraph interrupts for human gates**
   - Replace `GraphRecursionError` hack with `interrupt()` + `Command(resume=...)`
   - Eliminates recursion-limit-based workaround
   - Enables true pause/resume without separate MCP-manual phase advancement

2. **Add LangGraph checkpointer (MemorySaver or SqliteSaver)**
   - Auto-saves every node transition
   - Enables crash recovery and step-level time travel
   - Keep our git-backed checkpoints for semantic milestones, but add LangGraph checkpointer for operational resilience

### P1 — High Value (Architecture & Performance)

3. **Implement QC subgraph with Send API parallel validators**
   - Replaces ~150 lines of `_run_validators()` + `_build_consensus_if_needed()`
   - Runs 6 validator families in parallel instead of sequentially
   - Models the subgraph pattern for other phases

4. **Adopt typed state (TypedDict with reducers)**
   - Prerequisite for subgraphs (independent state schemas)
   - Eliminates deep-copy pattern
   - Enables append-only lists, additive counters

### P2 — Nice to Have

5. **Extract generic subgraph factory**
   - Pattern: `router → agent → validate → save_artifact → human_gate`
   - Parameterized by agent contract + validator list
   - Reduces 11 × 5 lines of boilerplate

6. **Send API for coverage/multi-shot generation**
   - Fan out N generation requests from gen_planning ledger
   - Reduce results into generation ledger

7. **Streaming progress to MCP tools**
   - `stream_mode="updates"` for phase-by-phase progress
   - MCP tools return incremental results instead of waiting for full invoke


---

## Summary Table

| Concept | Current State | Optimal? | Priority |
|---------|--------------|----------|----------|
| **Persistence/Checkpointing** | Custom git-backed, manual at gates | No — missing auto-save and crash recovery | P0 |
| **Human-in-the-Loop** | Simulated via state flags + recursion limit hack | No — biggest architectural gap | P0 |
| **Multi-Agent Subgraphs** | 13 stubs, all re-export flat functions | No — planned but not implemented | P1 |
| **Send API (parallelism)** | Not used, validators run sequentially | No — direct performance win | P1 |
| **Command (combined update+routing)** | Not used, routing is separate | No — would simplify nodes | P2 |
| **Interrupt (real)** | Not used, docstring lies | No — critical for human gates | P0 |
| **Streaming** | Only used as recursion error fallback | No — UI needs streaming progress | P2 |

### Files Referenced

| File | Lines | Role |
|------|-------|------|
| `src/film_pipeline/checkpoints/manager.py` | 68 | Custom git-backed checkpoint creation |
| `src/film_pipeline/checkpoints/invalidation.py` | 73 | Dependency-aware rollback engine |
| `src/film_pipeline/checkpoints/git_backend.py` | 78 | Git wrapper for checkpoint operations |
| `src/film_pipeline/graph/interrupts.py` | 58 | Human gate flags (not real interrupts) |
| `src/film_pipeline/graph/subgraphs/` | 13 files | Phase subgraphs (all stubs) |
| `src/film_pipeline/app/runtime.py` | 316 | Graph invocation with recursion-limit workaround |
| `src/film_pipeline/review/actions.py` | 72 | Available actions calculator for review gates |
| `src/film_pipeline/review/generator.py` | 114 | Review package builder |
| `src/film_pipeline/mcp/tools/__init__.py` | 4088 | MCP tool surface (approve_phase, rollback, etc.) |
| `docs/architecture-blueprint.md` | 2421 | Architectural vision (subgraphs, layered graph) |
| `docs/comprehensive-review-2026-06-19.md` | 394 | Prior review noting subgraph stubs and recursion hack |
