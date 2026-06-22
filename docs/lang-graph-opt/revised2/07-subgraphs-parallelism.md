# Phase 7 — Subgraphs & Parallelism

**Goal:** Replace flat nodes with compiled subgraphs where they reduce complexity or improve throughput. Use LangGraph `Send` API for parallel validator and generation batch execution.

**Prerequisite:** Phase 1-4 (interrupts, typed state, versioning, matrix patches). The graph must be correct before we make it parallel.

---

## Current State

```
Parent graph:
  qc_node (flat function, 168 lines):
    - Loads artifacts from 7 phases
    - Runs 6 validators sequentially (script_structure → dialogue_voice → reference →
      prompt → continuity → assembly)
    - Builds consensus
    - Saves report

  generation_node (stub, 12 lines):
    - Only runs Gate C validation
    - No real generation
```

All 13 `subgraphs/` modules are stubs re-exporting from `nodes.py`.

---

## Target State

```
Parent graph:
  qc_node = qc_subgraph.compile()
    internal:
      load_artifacts → Send(6 validators in parallel) → reduce → consensus → interrupt

  generation_node = generation_subgraph.compile()
    internal:
      load_batch → Send(N generation workers in parallel) → reduce ledger → emit matrix patch

  review_gate_node = review_gate_subgraph.compile()
    internal:
      build_package → interrupt → normalize_decision → route(approve/revise/rollback)
```

---

## Files to Create/Modify

| File | Change |
|------|--------|
| `graph/subgraphs/qc.py` | Replace stub with compiled QC subgraph |
| `graph/subgraphs/generation.py` | Replace stub with compiled generation subgraph |
| `graph/subgraphs/review_gate.py` | New — approval gate as compiled subgraph |
| `graph/graph.py` | Wire subgraphs instead of flat nodes |
| `graph/nodes.py:qc_node` | Deprecate — logic moves into QC subgraph |
| `graph/nodes.py:generation_node` | Deprecate — logic moves into generation subgraph |

---

## Step-by-Step

### Step 1: QC Validator Fan-Out Subgraph

**File:** `src/film_pipeline/graph/subgraphs/qc.py` (replace stub)

```python
"""QC subgraph — fan-out validators, reduce reports, build consensus."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from film_pipeline.graph.state_schema import StudioGraphState


# ── Validator worker nodes ─────────────────────────────────────────────

def script_structure_worker(state: StudioGraphState) -> dict[str, object]:
    """Run ScriptStructureValidator on loaded script data."""
    script_data = state.get("_qc_script_data", {})
    if not script_data:
        return {"_qc_reports": [{"validator": "script_structure", "status": "skipped"}]}

    from film_pipeline.validation.impl.script_structure import ScriptStructureValidator
    validator = ScriptStructureValidator()
    report = validator.run({"script": script_data})

    return {
        "_qc_reports": [{
            "validator_id": "script-structure",
            "score": report.score,
            "status": report.status,
            "blocking_count": len(report.blocking_issues),
            "warning_count": len(report.warnings),
        }],
        "_qc_raw_reports": [report.model_dump()],
    }

def dialogue_voice_worker(state: StudioGraphState) -> dict[str, object]:
    """Run DialogueVoiceValidator on loaded script data."""
    # Same pattern as script_structure_worker
    ...

# ... repeat for reference_usability_worker, prompt_readiness_worker,
#     scene_continuity_worker, assembly_worker


# ── Fan-out router ─────────────────────────────────────────────────────

def fan_out_validators(state: StudioGraphState) -> list[Send]:
    """Create one Send per validator, each gets the same state."""
    workers = [
        "script_structure_worker",
        "dialogue_voice_worker",
        "reference_usability_worker",
        "prompt_readiness_worker",
        "scene_continuity_worker",
        "assembly_worker",
    ]
    return [Send(worker, state) for worker in workers]


# ── Reduce node ────────────────────────────────────────────────────────

def reduce_reports(state: StudioGraphState) -> dict[str, object]:
    """Collect all validator reports, build consensus."""
    from film_pipeline.validation.consensus import ConsensusBuilder

    reports = state.get("_qc_raw_reports", [])
    if len(reports) >= 2:
        consensus = ConsensusBuilder().build(reports, state.get("artifact_refs", []))
        # Save consensus report as artifact
        ...

    return {}


# ── Build subgraph ─────────────────────────────────────────────────────

def build_qc_subgraph() -> CompiledStateGraph:
    """Build the QC subgraph with parallel validator fan-out."""
    builder = StateGraph(StudioGraphState)

    builder.add_node("load_artifacts", load_qc_artifacts)
    builder.add_node("script_structure_worker", script_structure_worker)
    builder.add_node("dialogue_voice_worker", dialogue_voice_worker)
    builder.add_node("reference_usability_worker", reference_usability_worker)
    builder.add_node("prompt_readiness_worker", prompt_readiness_worker)
    builder.add_node("scene_continuity_worker", scene_continuity_worker)
    builder.add_node("assembly_worker", assembly_worker)
    builder.add_node("reduce_reports", reduce_reports)

    builder.set_entry_point("load_artifacts")
    builder.add_conditional_edges("load_artifacts", fan_out_validators, [
        "script_structure_worker",
        "dialogue_voice_worker",
        "reference_usability_worker",
        "prompt_readiness_worker",
        "scene_continuity_worker",
        "assembly_worker",
    ])

    # All workers → reduce
    for worker in ["script_structure_worker", "dialogue_voice_worker",
                   "reference_usability_worker", "prompt_readiness_worker",
                   "scene_continuity_worker", "assembly_worker"]:
        builder.add_edge(worker, "reduce_reports")

    builder.add_edge("reduce_reports", END)

    return builder.compile()
```

### Step 2: Wire QC Subgraph into Parent Graph

**File:** `src/film_pipeline/graph/graph.py`

```python
from film_pipeline.graph.subgraphs.qc import build_qc_subgraph

def build_graph():
    builder = StateGraph(StudioGraphState)

    # ... existing nodes ...

    # Replace flat qc_node with compiled subgraph
    qc_subgraph = build_qc_subgraph()
    builder.add_node("qc_node", qc_subgraph)

    # ... edges unchanged ...
```

### Step 3: Approval Gate Subgraph

**File:** NEW `src/film_pipeline/graph/subgraphs/review_gate.py`

```python
"""Review gate subgraph — build package, interrupt, route decision."""

from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

def build_review_package(state):
    """Build a review package artifact. Returns its ref."""
    from film_pipeline.review.generator import ReviewPackageGenerator
    generator = ReviewPackageGenerator()
    package = generator.build(...)
    ref = _save_artifact(state, package, "review_package", state["current_phase"])
    return {"review_package_ref": ref}

def human_interrupt(state):
    """Pause for human review."""
    payload = {
        "project_id": state["project_id"],
        "phase": state["current_phase"],
        "review_package_ref": state.get("review_package_ref"),
        "allowed_actions": ["approve", "request_revision"],
    }
    decision = interrupt(payload)
    return {"_review_decision": decision}

def route_decision(state):
    """Route based on human decision."""
    decision = state.get("_review_decision", {})
    action = decision.get("action", "") if isinstance(decision, dict) else str(decision)

    if action == "approve":
        return "approve"
    elif action in ("revise", "request_revision"):
        return "revise"
    return "stay"

def build_review_gate_subgraph():
    builder = StateGraph(StudioGraphState)
    builder.add_node("build_package", build_review_package)
    builder.add_node("interrupt", human_interrupt)
    builder.add_node("approve", approve_handler)
    builder.add_node("revise", revise_handler)

    builder.set_entry_point("build_package")
    builder.add_edge("build_package", "interrupt")
    builder.add_conditional_edges("interrupt", route_decision, {
        "approve": "approve",
        "revise": "revise",
        "stay": END,
    })

    builder.add_edge("approve", END)
    builder.add_edge("revise", END)

    return builder.compile()
```

---

## Important: Defer Generation Subgraph

The `generation_node` is currently a stub. Building a parallel generation subgraph requires:
- Real provider adapters (currently mock-only)
- Idempotent job submission
- Polling and failure recovery
- Cost tracking

**DO NOT implement the generation subgraph in Phase 7.** The QC subgraph (validators only, no paid calls) and review gate subgraph are safe to parallelize immediately.

---

## Test Cases

```python
def test_qc_subgraph_compiles():
    """QC subgraph compiles without errors."""
    subgraph = build_qc_subgraph()
    assert subgraph is not None  # compilation succeeded

def test_qc_subgraph_runs_all_validators(studio_runtime):
    """All 6 validator workers produce reports."""
    state = {"project_id": "test", "current_phase": "qc", ...}
    subgraph = build_qc_subgraph()
    result = subgraph.invoke(state)
    reports = result.get("_qc_reports", [])
    assert len(reports) == 6

def test_review_gate_subgraph_pauses_at_interrupt():
    """Review gate subgraph emits interrupt payload."""
    ...

def test_sequential_and_parallel_produce_same_consensus():
    """Sequential validators (old code) and parallel (new) produce same result."""
    ...
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `Send` API creates N copies of state — memory | Validator workers receive lightweight state (refs only, not artifact bodies). |
| Parallel validator results arrive in any order | `reduce_reports` node collects all reports — order independent. |
| Subgraph checkpointer conflicts with parent checkpointer | Subgraphs inherit parent checkpointer. No special config needed. |
| Generation subgraph premature — no real providers | Defer. Only QC and review gate subgraphs in Phase 7. |

---

## Acceptance Criteria

- [ ] QC subgraph compiles and runs all 6 validators
- [ ] Validators run via `Send` (verify via tracing/order independence)
- [ ] Consensus report built from parallel validator results
- [ ] Review gate subgraph compiles — build package → interrupt → route
- [ ] Parent graph wires QC subgraph instead of flat `qc_node`
- [ ] Old sequential behavior preserved as fallback (config toggle)
- [ ] `make ci-check` green
- [ ] No regression in E2E test scenarios

**Estimated implementation time:** 4-5 hours
**Prerequisite:** Phase 1 (interrupts) + Phase 2 (typed state) + Phase 4 (matrix patches for QC row updates)
