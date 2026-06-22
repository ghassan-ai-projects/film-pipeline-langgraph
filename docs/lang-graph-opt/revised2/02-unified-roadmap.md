# Revised2 — Unified Implementation Roadmap

**Date:** 2026-06-22
**Source:** Merged from Qwen `docs/lang-graph-opt/01-07` (code-level findings) + Codex `docs/lang-graph-opt/revised/` (architectural direction)

---

## Guiding Rule

Make the graph and runtime correct before making them clever. Each phase builds on the previous.

---

## Phase 0 — Quick Wins (Zero Architectural Risk)

Do these immediately. They require no graph changes and have zero impact on existing tests.

### 0.1 Route Creative Agents to Creative Profiles

**Why:** Every agent currently runs at temperature 0.2 via `operations_triage`. The `creative_writer` profile (temp 0.7, max_tokens 8192) exists but is unreachable.

**Where:** `src/film_pipeline/graph/nodes.py:180`

**What:**
```python
_AGENT_PROFILE_MAP = {
    "film-constitution-agent": "creative_writer",
    "treatment-agent": "creative_writer",
    "screenwriter-agent": "creative_writer",
    "shot-design-agent": "creative_writer",
    "visual-dev-agent": "creative_writer",
    "reference-strategy-planner": "visual_reasoner",
    "structure-extractor-agent": "strict_validator",
    "clip-validator": "strict_validator",
    "provider-planning-agent": "operations_triage",
    "intake-classifier-agent": "operations_triage",
}

model_profile = _AGENT_PROFILE_MAP.get(resolved_agent_id, "operations_triage")
model_output, template_id, _ = services.prompt_runner.run_from_template(
    template, kb, task, context_vars=context_vars, model_profile=model_profile
)
```

**Test:** Verify `run_from_template` receives `model_profile="creative_writer"` for screenwriter agent. No behavior change at mock level.

### 0.2 Add Quality Instructions to Creative Template Roles

**Why:** Role fields are identity-only (15 tokens). Chat interfaces add 200+ tokens of quality instructions.

**Where:** `src/film_pipeline/agents/prompt_templates/defaults.py`

**What:** Add a `quality_instructions` field to `PromptTemplate` and render it in creative templates:
```
QUALITY REQUIREMENTS:
- Be thorough and detailed. Never summarize unless explicitly asked.
- Use vivid, sensory language appropriate for creative writing.
- Make specific, defensible creative choices. Never be vague or generic.
- Review your output for internal consistency before finalizing.
```

**Test:** Verify rendered template includes quality instructions for creative agents.

---

## Phase 1 — Real Human Gates (P0)

**Goal:** Replace recursion-limit approval with LangGraph `interrupt()` + checkpointer.

**Product risk:** Human gates are the mandatory review system. Currently broken — works via `GraphRecursionError` catch.

### 1.1 Compile with Checkpointer

**Where:** `src/film_pipeline/graph/graph.py:130`
```python
# Current:
return builder.compile()

# Target:
from langgraph.checkpoint.memory import MemorySaver
return builder.compile(checkpointer=MemorySaver())
```

### 1.2 Replace `await_approval` Passthrough with Interrupt Node

**Where:** `src/film_pipeline/graph/nodes.py` (new node), `src/film_pipeline/graph/graph.py:50`

```python
def await_approval_node(state: dict[str, Any]) -> dict[str, Any]:
    from langgraph.types import interrupt

    payload = {
        "project_id": state["project_id"],
        "phase": state["current_phase"],
        "artifact_refs": state.get("artifact_refs", []),
        "blocking_issue_count": sum(1 for i in state.get("issues", []) if i.get("severity") == "blocking"),
        "allowed_actions": ["approve", "request_revision"],
    }
    decision = interrupt(payload)

    if decision == "approve":
        return approve_phase_node(state)
    return request_revision_node(state)
```

### 1.3 MCP Tools Resume Graph Instead of Mutating Runtime

**Where:** `src/film_pipeline/mcp/tools/__init__.py:502` (`approve_phase`), `src/film_pipeline/app/runtime.py:139-182`

```python
async def approve_phase(args):
    from langgraph.types import Command
    rt = get_runtime()
    graph = rt.ensure_graph()
    config = {"configurable": {"thread_id": rt.active_project_id}}
    state = graph.invoke(Command(resume="approve"), config)
    rt.projects[rt.active_project_id] = state
    return _ok(...)
```

### 1.4 Remove `GraphRecursionError` as Control Flow

**Where:** `src/film_pipeline/app/runtime.py:108-139`

Remove the try/except `GraphRecursionError` block. With real interrupts, the graph pauses cleanly — no recursion limit needed for gates.

### 1.5 Keep Git Checkpoints at Approved Gates

**Where:** `src/film_pipeline/app/runtime.py:170-184`

After graph-level approval (inside `await_approval_node` or in a `consistency_check` node), create a git checkpoint. Don't remove this — it's the semantic milestone system.

**Tests:**
- `submit_idea` reaches interrupt payload, does not hit recursion limit
- `approve_phase` MCP tool resumes graph, advances to next phase
- `request_revision` MCP tool resumes graph with revision path
- Runtime restart + `graph.invoke(None, config)` resumes pending gate (with durable checkpointer)
- Git checkpoint still created at approved gates

**Risk:** Code before `interrupt()` re-runs on resume. Review package generation must be idempotent (check by key before creating).

---

## Phase 2 — Typed State Contract (P0)

**Goal:** Replace `StateGraph(dict)` with typed `TypedDict` state + reducers. Remove `deepcopy` pattern. Remove services from state.

### 2.1 Define `StudioGraphState`

**Where:** New file `src/film_pipeline/graph/state_schema.py`

```python
from operator import add
from typing import Annotated, TypedDict

class StudioGraphState(TypedDict, total=False):
    project_id: str
    current_phase: str
    approved: bool
    completed: bool

    # Append-only channels
    artifact_refs: Annotated[list[str], add]
    issues: Annotated[list[dict[str, object]], add]
    validation_report_refs: Annotated[list[str], add]
    audit_events: Annotated[list[dict[str, object]], add]

    # Scalar channels (replace on write)
    human_approval_phase: str
    active_matrix_ref: str
    budget_snapshot: dict[str, object]
    provider_health_snapshot: dict[str, object]
```

### 2.2 Port Graph to Typed State

**Where:** `src/film_pipeline/graph/graph.py:32`
```python
# Current:
builder = StateGraph(dict)

# Target:
from film_pipeline.graph.state_schema import StudioGraphState
builder = StateGraph(StudioGraphState)
```

### 2.3 Remove `deepcopy` from Nodes

Nodes return partial updates. LangGraph handles merging.

**Where:** All phase nodes in `src/film_pipeline/graph/nodes.py`

```python
# Current:
def intake_node(state):
    new_state = deepcopy(state)
    new_state["current_phase"] = "intake"
    # ...
    return new_state

# Target:
def intake_node(state):
    return {
        "current_phase": "intake",
        "approved": False,
        "artifact_refs": [ref],  # appended by reducer
    }
```

### 2.4 Move Services Out of State

**Where:** `src/film_pipeline/graph/services.py:217` (`SERVICES_KEY`), `src/film_pipeline/app/runtime.py:115`

Pass services through `config["configurable"]` or inject into node closures:
```python
config = {
    "configurable": {
        "thread_id": project_id,
        "services": services,   # available in node via config
    }
}
```

**Tests:**
- Append-only channels accumulate (don't replace) across multiple nodes
- Scalar channels replace correctly
- Node returning partial update doesn't lose other state keys
- `_services` not in serialized state

**Risk:** Reducers can duplicate refs on replay after interrupt. Add idempotent append or deterministic refs.

---

## Phase 3 — Artifact Versioning & Lineage (P1)

**Goal:** Fix artifact versioning so repair creates v2, v3 — not overwrites v1.

### 3.1 Auto-Increment Version in `_save_artifact`

**Where:** `src/film_pipeline/graph/nodes.py:253-268`, `src/film_pipeline/artifacts/store.py`

```python
def _save_artifact(state, artifact, artifact_id, phase):
    # Count existing versions
    existing = [r for r in state.get("artifact_refs", []) if artifact_id in str(r)]
    version = len(existing) + 1

    meta = ArtifactMetadata(
        artifact_id=artifact_id,
        version=version,  # was: version=1
        # ...
    )
```

### 3.2 Add `built_from` to Artifact Metadata

**Where:** `src/film_pipeline/schemas/artifact.py`

```python
class ArtifactMetadata(SchemaBase):
    # ... existing fields ...
    built_from: dict[str, str] = Field(default_factory=dict)
    # e.g. {"script": "artifact:script:v2", "constitution": "artifact:film_constitution:v1"}
```

### 3.3 Populate `built_from` on Save

**Where:** `src/film_pipeline/graph/nodes.py:_save_artifact`

Record which versions of upstream artifacts were current when this artifact was created.

### 3.4 Add Staleness Detection

**Where:** New function in `src/film_pipeline/graph/consistency.py`

```python
def check_staleness(artifact_ref: str, state) -> list[dict]:
    """Compare artifact's built_from against current approved refs."""
    metadata = load_metadata(artifact_ref)
    warnings = []
    for dep_id, dep_version in metadata.built_from.items():
        current = get_current_approved_ref(state, dep_id)
        if current and current != dep_version:
            warnings.append({
                "artifact": artifact_ref,
                "dependency": dep_id,
                "built_with": dep_version,
                "current": current,
                "severity": "stale",
            })
    return warnings
```

**Tests:**
- Saving same artifact_id twice creates v1 then v2 (not overwrite)
- built_from records correct upstream versions
- Staleness check detects when constitution changed after script was created
- Staleness check returns empty when all deps match

**Risk:** Existing tests may assert `v1` hardcoded. Update to assert current ref.

---

## Phase 4 — Living Matrix via Versioned Patches (P1)

**Goal:** Downstream phases update matrix rows through patch artifacts, not by replacing the whole matrix.

### 4.1 Add Matrix Patch Schema

**Where:** New file `src/film_pipeline/schemas/matrix_patch.py`

```python
class MatrixRowUpdate(SchemaBase):
    shot_id: str
    set: dict[str, Any]   # fields to set e.g. {"prompt_ref": "...", "status": "prompted"}
    old_values: dict[str, Any] = Field(default_factory=dict)  # for rollback

class MatrixPatch(SchemaBase):
    matrix_ref: str       # base matrix this patch applies to
    phase: str
    reason: str
    updates: list[MatrixRowUpdate]
    validator_refs: list[str] = Field(default_factory=list)
```

### 4.2 Add Matrix Projection Helper

**Where:** New file `src/film_pipeline/artifacts/matrix_projection.py`

```python
def materialize_matrix(store, project_id, base_ref, patch_refs):
    """Load base matrix + apply all approved patches, return current matrix."""
    matrix = load_matrix(base_ref)
    for patch_ref in patch_refs:
        patch = load_patch(patch_ref)
        apply_patch(matrix, patch)
    return matrix
```

### 4.3 Wire gen_planning → Matrix Patch

**Where:** `src/film_pipeline/graph/nodes.py:gen_planning_node`

After creating prompts and provider plans, emit a `MatrixPatch` that sets `prompt_ref`, `provider_plan_ref`, and `status="prompted"` on each planned row.

### 4.4 Wire generation → Matrix Patch

**Where:** `src/film_pipeline/graph/nodes.py:generation_node`

After generating assets, emit a `MatrixPatch` that appends to `asset_refs` and sets `status="generated"`.

### 4.5 Wire QC → Matrix Patch

**Where:** `src/film_pipeline/graph/nodes.py:qc_node`

After validation, emit a `MatrixPatch` that appends to `validation_refs` and sets `status="validated"` or `"failed"`.

### 4.6 Wire Post → Matrix Patch

**Where:** `src/film_pipeline/graph/nodes.py:post_node`

After assembly, emit a `MatrixPatch` that appends to `post_refs` and sets `status="assembled"`.

**Tests:**
- gen_planning patch sets prompt_ref on specific rows without touching other fields
- QC patch sets validation_refs and status on failed rows
- Materialized matrix preserves rows not touched by any patch
- Rollback of a patch restores previous values (via old_values)
- Applying patches in creation order produces the correct matrix

**Risk:** Whole-matrix saves are simpler. Do patches for new downstream updates first, decide later whether to also save a convenience full-matrix artifact.

---

## Phase 5 — Structured Repair Feedback (P1)

**Goal:** Replace flat string repair feedback with typed per-row repair instructions.

### 5.1 Add Repair Feedback Schema

**Where:** New file `src/film_pipeline/schemas/repair.py`

```python
class RowRepairInstruction(SchemaBase):
    shot_id: str
    issues: list[dict[str, str]]  # {code, field, message, recommended_action}
    preserve_other_fields: bool = True

class RepairFeedback(SchemaBase):
    phase: str
    round: int
    failed_rows: list[RowRepairInstruction]
    global_issues: list[dict[str, str]]
    passed_row_ids: list[str]
```

### 5.2 Extend Validators to Name Rows and Fields

**Where:** `src/film_pipeline/validation/base.py`, `src/film_pipeline/schemas/validation.py`

Add optional `shot_id`, `field`, `recommended_action` to validator findings.

### 5.3 Update Repair Node to Build Structured Feedback

**Where:** `src/film_pipeline/graph/nodes.py:repair_phase_node`

Instead of `state["_repair_feedback"] = "REPAIR ROUND 1: ..."`, build a `RepairFeedback` object and persist as artifact. Pass `repair_feedback_ref` through state.

### 5.4 Update Agents to Read Structured Feedback

**Where:** All agent `prepare()` methods

Agents receive repair feedback as structured data, not a prepended string. They know: "fix rows 3 and 7, preserve rows 1-2 and 4-6."

**Tests:**
- Validator finding with `shot_id` becomes per-row repair instruction
- Repair feedback includes `passed_row_ids` listing rows to preserve
- Agent receives structured feedback, not string blob
- Second repair round clears resolved issues and focuses on remaining

---

## Phase 6 — Scoped Context Packets (P2)

**Goal:** Replace full-artifact JSON injection with phase-specific structured context.

### 6.1 Build Context Packet Builders per Phase

**Where:** New file `src/film_pipeline/graph/context_packets.py`

For each phase, define what context the agent actually needs:

| Phase | Context Packet |
|-------|---------------|
| Constitution | idea text + classification |
| Development | constitution summary + target runtime + film type |
| Script | treatment + scene list + constitution |
| Visual Dev | script scene/environment list + constitution style |
| Shot Bible | execution brief + script scene map + visual ref ids |
| Gen Planning | planned rows only + budget/provider policy |
| Generation | batch of ready rows + prompt refs + continuity anchors |
| QC | artifact refs + targeted excerpts per validator |

### 6.2 Replace `_inject_artifact_context` with Scoped Packets

**Where:** `src/film_pipeline/graph/nodes.py:339-367`

**Tests:**
- 100-row matrix context includes all active row ids (no truncation)
- Screenwriter doesn't receive provider internals
- Provider planner receives budget info and planned rows only
- QC validators receive only relevant artifact slices

---

## Phase 7 — Subgraphs & Parallelism (P2)

**Goal:** Use subgraphs and `Send` where they reduce complexity or improve throughput.

### 7.1 Approval Gate Subgraph

**Where:** New `src/film_pipeline/graph/subgraphs/review_gate.py`

Internal flow: `build_review_package → interrupt → normalize_decision → approve/revise/rollback`

### 7.2 QC Validator Fan-Out Subgraph

**Where:** `src/film_pipeline/graph/subgraphs/qc.py` (replace stub)

Fan out 6 validators via `Send`, reduce reports, build consensus.

### 7.3 Generation Batch Subgraph

**Where:** `src/film_pipeline/graph/subgraphs/generation.py` (replace stub)

Fan out generation requests, poll/resume, ingest outputs, write matrix patch.

**Test:** QC subgraph runs validators in parallel and produces deterministic consensus.

**Risk:** Parallelism requires idempotency. Don't fan out paid provider calls until duplicate prevention is tested.

---

## Phase 8 — Agent Output Quality (P2)

**Goal:** Improve creative output completeness beyond Phase 0 quick wins.

### 8.1 Per-Agent Temperature Calibration

Already done in Phase 0.1.

### 8.2 Add `frequency_penalty` to ModelAdapter

**Where:** `src/film_pipeline/agents/model_adapter.py:55-68`

### 8.3 Add Chain-of-Thought to Complex Templates

**Where:** `src/film_pipeline/agents/prompt_templates/defaults.py`

Restructure core_task for screenwriter, shot designer, constitution to include step-by-step reasoning before JSON output.

---

## Dependency Graph

```
Phase 0 (Quick Wins)  ← Independent, do immediately
     │
Phase 1 (Interrupts)  ← Prerequisite for all below
     │
Phase 2 (Typed State) ← Prerequisite for all below
     │
Phase 3 (Versioning)  ← Prerequisite for Phase 4
     │
Phase 4 (Matrix Patches) ← Prerequisite for Phase 5
     │
Phase 5 (Structured Repair)
     │
Phase 6 (Scoped Context)
     │
Phase 7 (Subgraphs)   ← Can start after Phase 4 (parallel to 5 & 6)
     │
Phase 8 (Quality)     ← Mostly complete in Phase 0, remainder after Phase 6
```

## First PR: Phase 1 Only

**Acceptance criteria:**
- `submit_idea` graph.invoke() reaches interrupt payload, does not hit recursion limit
- `approve_phase` MCP tool calls `graph.invoke(Command(resume="approve"), config)`
- `request_revision` MCP tool calls `graph.invoke(Command(resume="revise"), config)`
- No test relies on `GraphRecursionError`
- Git checkpoint still created on approval
- MCP remains the only operator-facing control path
- `make ci-check` passes
