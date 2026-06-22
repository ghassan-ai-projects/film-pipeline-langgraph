# 05 — Why Repair Loops Don't Actually Fix Matrix Rows

**Date:** 2026-06-22
**Context:** Builds on `04-question-enricchtment.md` — the "LangGraph trap" where state doesn't update across repair loops. This document verifies that analysis against our actual code and identifies our specific variant of the problem.

---

## 1. Does Our Code Have the "Validator-in-Edge" Trap?

**No.** The user's `04-` file describes the classic LangGraph bug where validation logic lives in a conditional edge (which can't write to state). We do NOT have this bug.

### Our validator placement is correct

Validators run inside **nodes**, not edges:

```python
# nodes.py:633-640 — Gate A runs INSIDE shot_bible_node (a node)
if shot_matrix is not None:
    brief = load_execution_brief(new_state)
    if brief is not None:
        struct_issues = validate_shot_structure(new_state, brief, shot_matrix)
        new_state.setdefault("issues", []).extend(struct_issues)
```

```python
# nodes.py:690-700 — Gate B runs INSIDE gen_planning_node (a node)
plan_issues = validate_planning_completeness(new_state, matrix_data, cost_estimate)
new_state.setdefault("issues", []).extend(plan_issues)
```

```python
# nodes.py:710-714 — Gate C runs INSIDE generation_node (a node)
dispatch_issues = validate_dispatch_readiness(new_state, gen_requests)
new_state.setdefault("issues", []).extend(dispatch_issues)
```

**Our conditional edges ARE "dumb traffic cops":**

```python
# edges.py:130-150 — after_phase() just reads issues and routes
def after_phase(state):
    result = compute_actions(state)
    if action in ("handle_blockers",):
        return "repair"    # ← routes to repair, doesn't try to validate
    # ...
```

So the fundamental architecture from `04-question-enricchtment.md` is already in place:
- ✅ Validator is a node (writes issues to `state["issues"]`)
- ✅ Conditional edge is a dumb router (reads issues, routes)
- ✅ Repair node injects feedback into state

### Our repair loop actually does work at the artifact level

Tracing a `shot_bible` → repair → retry:

```
1. shot_bible_node runs:
   - Agent produces MasterFilmMatrix with 12 rows
   - Gate A: "expected 20, got 12" → blocking issue added to state["issues"]
   - Returns state with issues

2. after_phase():
   - compute_actions() sees blocking issues → next_action = "handle_blockers"
   - edges.py maps "handle_blockers" → "repair"

3. repair_phase_node (nodes.py:1148-1198):
   - Gets phase = "shot_bible", phase_fn = shot_bible_node
   - Builds _repair_feedback:
     "REPAIR ROUND 1: Your previous output was REJECTED.
      Issues to fix:
      [shot_count_mismatch] Movement 'act_1': expected 20 shots, got 12."
   - Calls shot_bible_node(state) with feedback in state

4. shot_bible_node re-runs:
   - _run_agent() reads state.pop("_repair_feedback")
   - Prepends to task: "REPAIR ROUND 1: ... \n\n Produce the master film matrix..."
   - Agent produces NEW matrix with 20 rows
   - Saves as artifact (overwrites v1)
   - Gate A re-validates → passes! (if agent fixed it correctly)
```

**The loop works.** Agents get feedback and produce corrected output. The repair path is functional.

### But it works at the WRONG GRANULARITY

The entire matrix is replaced as a blob. Individual rows are never updated. Let me prove this.

---

## 2. Our Specific Variant: Three Hidden Problems

### Problem 1: Text-Based Feedback, Not Structural Feedback

The repair feedback is a **flat string** injected into the agent's prompt:

```python
# repair_phase_node:1191-1194
state["_repair_feedback"] = (
    f"REPAIR ROUND {round_num}: Your previous output was REJECTED. "
    f"Issues to fix:\n" + "\n".join(feedback_parts)
)
```

This becomes:
```
REPAIR ROUND 1: Your previous output was REJECTED. Issues to fix:
[shot_count_mismatch] Movement 'act_1': expected 20 shots, got 12.
[incomplete_shot_rows] shot_0003: missing prompt_ref; shot_0007: missing camera_profile
```

The agent gets this text and must **guess**:
- Which specific scenes need more shots? (the validator only said "act_1 has 12, needs 20")
- Which rows are complete and should be preserved? (the agent doesn't know — it regenerates everything)
- What did the previous attempt get RIGHT? (no positive feedback — only blockings)

**Contrast with structural feedback:**

```python
# What should happen:
state["matrix"].rows[3].validation_issues = [
    {"code": "missing_prompt_ref", "message": "prompt_ref is empty"}
]
state["matrix"].rows[7].validation_issues = [
    {"code": "missing_camera_profile", "message": "camera_profile is empty"}
]
# All OTHER rows are clean — the agent only fixes rows 3 and 7
```

The agent would receive: "Row shot_0003 needs prompt_ref. Row shot_0007 needs camera_profile. All other rows are fine — preserve them."

### Problem 2: Full-Artifact Overwrite, Not Row-Level Update

Every repair round saves a **completely new** `MasterFilmMatrix`:

```python
# nodes.py:625-631 — shot_bible_node on repair
shot_matrix = result.get("shot_matrix")     # new MasterFilmMatrix object
if shot_matrix is not None:
    ref = _save_artifact(new_state, shot_matrix, "shot_matrix", "shot_bible")
    new_state["shot_matrix_ref"] = ref
```

And `_save_artifact` **always uses version=1**:

```python
# nodes.py:253-268
meta = ArtifactMetadata(
    artifact_id=artifact_id,
    version=1,           # ← ALWAYS 1 — never increments
    status=ArtifactStatus.CANDIDATE,
    ...
)
```

**Result:** Each repair round overwrites `05-shot-bible/shot_matrix.v1.json`. There is no v2, v3. The previous matrix is lost.

**Evidence from `_save_artifact`:**
```python
# nodes.py:267
services.artifact_store.save(artifact, meta)
# → ArtifactStore.save() writes to:
#   projects/<id>/05-shot-bible/shot_matrix.v1.json   (every time!)
```

### Problem 3: `validation_refs` on Matrix Rows Are Dead Fields

`MasterFilmMatrixRow` has a `validation_refs: list[str]` field:

```python
# schemas/matrix.py:39-76
class MasterFilmMatrixRow(SchemaBase):
    shot_id: str
    # ... 25+ fields ...
    validation_refs: list[str] = Field(default_factory=list)  # ← NEVER WRITTEN TO
    asset_refs: list[str] = Field(default_factory=list)       # ← NEVER WRITTEN TO
    post_refs: list[str] = Field(default_factory=list)        # ← NEVER WRITTEN TO
    status: str = "planned"                                   # ← NEVER UPDATED
```

**Grep confirmation — zero writes to these fields outside the agent itself:**

```
$ rg "validation_refs" src/film_pipeline/
schemas/matrix.py:72:    validation_refs: list[str] = Field(default_factory=list)
# That's the ONLY occurrence in production code (the schema definition).
# Nothing ever assigns to this field.
```

The validators produce issues in `state["issues"]` — a flat list of dicts unrelated to matrix rows. The `_append_validator_report` function:

```python
# nodes.py:1032-1064
def _append_validator_report(report, issues, state):
    for bi in report.blocking_issues:
        issues.append({
            "issue_id": f"val:{report.validator_id}:{bi.code}",
            "severity": "blocking",
            "code": bi.code,
            "message": bi.message,
        })
    # ← No code that finds the corresponding matrix row and appends to row.validation_refs
```

---

## 3. The Concrete Impact: What Breaks

### Scenario: Shot Bible with Partial Repair

1. Agent produces 20-shot matrix. Gate A finds: 1 row has missing `prompt_ref`, 1 row has 0 duration.
2. Repair round 1: agent fixes the 2 bad rows but accidentally breaks 3 previously-good rows.
3. Gate A now finds 3 issues (worse than before!).
4. Repair round 2: agent fixes 2 of 3 new issues.
5. Gate A finds 1 remaining issue.
6. Repair round 3: agent finally fixes it.

**Without row-level tracking, the agent regenerates the ENTIRE matrix every time** — it can't preserve good rows and only fix bad ones. It's like rebuilding a house because one window is cracked.

### Scenario: Multi-Phase Accumulation

1. Shot bible produces matrix. 20 rows, all `status="planned"`.
2. Gen planning adds `prompt_ref` and `provider_plan_ref` to each row. But since it writes to a SEPARATE `cost_estimate` artifact (not the matrix), these refs are lost.
3. Generation produces assets. They're saved with `shot_id` in the filename, but `matrix.rows[i].asset_refs` stays empty.
4. QC validates. Issues go to `state["issues"]`. `matrix.rows[i].validation_refs` stays empty.
5. Post tries to assemble. Loads matrix from disk. `asset_refs = []` on every row. **Can't find any clips to assemble.**

This is the silent data-loss scenario. Every downstream phase's updates to the matrix are discarded because nothing writes back to the matrix.

---

## 4. The Fix: Row-Level Feedback + In-Place Mutation

### Step 1: Write Validation Results Back to Matrix Rows

Change `_append_validator_report` (or its callers) to annotate rows:

```python
def _append_validator_report(report, issues, state):
    # Append to flat issues list (existing behavior, for router compatibility)
    for bi in report.blocking_issues:
        issues.append({...})

    # NEW: Annotate the specific rows that failed
    matrix = state.get("matrix")
    if matrix is None:
        return

    for finding in report.findings:
        shot_id = finding.shot_id  # validators must include which shot_id
        for row in matrix.rows:
            if row.shot_id == shot_id:
                row.validation_refs.append(report.validator_id)
                row.validation_issues = getattr(row, "validation_issues", [])
                row.validation_issues.append({
                    "validator": report.validator_id,
                    "code": finding.code,
                    "message": finding.message,
                    "severity": finding.severity,
                })
```

### Step 2: Structural Feedback Instead of Text Blob

Instead of a flat string injected into the prompt:

```python
# CURRENT: text blob
state["_repair_feedback"] = (
    "REPAIR ROUND 1: Your previous output was REJECTED. "
    "Issues to fix:\n[shot_count_mismatch] ..."
)
```

Use structured feedback that the agent can act on precisely:

```python
# PROPOSED: structured feedback
state["_repair_feedback"] = {
    "round": round_num,
    "failed_rows": [
        {
            "shot_id": "shot_0003",
            "issues": [
                {"code": "missing_prompt_ref", "field": "prompt_ref", "action": "add a prompt reference"},
            ],
            "preserve": True,  # everything else about this row is fine
        },
        {
            "shot_id": "shot_0007",
            "issues": [
                {"code": "invalid_duration", "field": "duration_seconds", "action": "set to 5-15 seconds"},
                {"code": "missing_camera_profile", "field": "camera_profile", "action": "add camera profile"},
            ],
            "preserve": False,  # regenerate this row completely
        },
    ],
    "passed_rows": ["shot_0001", "shot_0002", "shot_0004", ...],  # 17 rows are fine
    "global_issues": [
        {"code": "shot_count_mismatch", "message": "act_1 needs 8 more shots"},
    ],
}
```

The agent receives this as JSON context (not a string blob) and knows exactly:
- Which 17 rows to preserve verbatim
- Which 2 rows need specific field fixes
- What each fix should be
- That act_1 needs 8 additional rows (from `global_issues`)

### Step 3: Row-Level Preserve-on-Repair

In the phase node's repair path, preserve rows that passed validation:

```python
def shot_bible_node(state):
    repair_feedback = state.pop("_repair_feedback", None)

    if repair_feedback and isinstance(repair_feedback, dict):
        # Repair mode: fix only failed rows
        passed_ids = set(repair_feedback.get("passed_rows", []))
        old_matrix = state.get("matrix")

        # Preserve rows that passed
        preserved_rows = [r for r in old_matrix.rows if r.shot_id in passed_ids]

        # Ask agent to fix only failed rows (with structural context)
        result = _run_agent(
            new_state,
            agent_id="shot-design-agent",
            phase="shot_bible",
            task=(
                f"Fix {len(repair_feedback['failed_rows'])} specific shot rows. "
                f"{len(preserved_rows)} rows are already correct and must be preserved. "
                f"Failed rows: {json.dumps(repair_feedback['failed_rows'])}"
            ),
        )

        # Merge: preserved rows + fixed rows
        fixed_rows = result.get("shot_matrix").rows
        merged_rows = preserved_rows + fixed_rows
        shot_matrix = MasterFilmMatrix(
            project_id=state["project_id"],
            rows=merged_rows,
        )
    else:
        # Create mode: produce full matrix
        result = _run_agent(...)
        shot_matrix = result.get("shot_matrix")

    # Store matrix in state (NOT just a disk pointer)
    state["matrix"] = shot_matrix
    _save_artifact(state, shot_matrix, "shot_matrix", "shot_bible")
```

### Step 4: Increment Version on Repair

```python
def _save_artifact(state, artifact, artifact_id, phase, artifact_type=None):
    # Check if this artifact already exists and auto-increment version
    existing_refs = [r for r in state.get("artifact_refs", []) if artifact_id in str(r)]
    version = len(existing_refs) + 1  # v1, v2, v3...

    meta = ArtifactMetadata(
        artifact_id=artifact_id,
        version=version,     # ← NOW INCREMENTS
        status=ArtifactStatus.CANDIDATE,
        ...
    )
    services.artifact_store.save(artifact, meta)
    ref = f"artifact:{artifact_id}:v{version}"
```

---

## 5. What Already Works (Don't Break This)

The existing architecture got the big things right:

| Component | Status | Notes |
|-----------|--------|-------|
| Validators run inside nodes | ✅ | `validate_shot_structure`, `validate_planning_completeness`, `validate_dispatch_readiness` all run in phase nodes |
| Conditional edges are dumb routers | ✅ | `after_phase()` reads `state["issues"]` — doesn't try to validate |
| Repair node injects feedback | ✅ | `repair_phase_node` sets `_repair_feedback` as a string |
| Agent reads feedback | ✅ | `_run_agent()` pops `_repair_feedback` and prepends to task |
| Convergence tracking | ✅ | Max 3 repair rounds, stall detection via `orchestrator_state` |
| Human escalation on stall | ✅ | `is_stalled()` → mark → routes back to `await_approval` |

**What needs to change is the FEEDBACK FORMAT and the WRITE-BACK PATH**, not the architecture.

---

## 6. The Command Pattern (Future Optimization)

The user's `04-` file mentions LangGraph's `Command` object for combined state-update + routing. This is relevant for a future optimization:

```python
from langgraph.types import Command

def repair_phase_node(state):
    if is_stalled(state, phase, max_rounds=3):
        return Command(
            update={"issues": [...stall issue...]},
            goto="await_approval"      # combined update + routing
        )

    state["_repair_feedback"] = structured_feedback
    return Command(
        update=state,
        goto=phase_node_name           # re-run phase node directly
    )
```

This eliminates the separate `after_phase()` routing step for repair — the repair node itself says where to go next. But this is P2 — the P0 fix is structural feedback + row-level write-back.

---

## 7. Summary

The user's `04-question-enricchtment.md` correctly identifies the LangGraph pattern (validator-as-node, dumb-edges). Our code **already follows this pattern correctly**. The repair loop works.

**Our specific problem is at a different layer:**

| Problem | Root Cause | Fix |
|---------|-----------|-----|
| Agent regenerates entire matrix instead of fixing individual rows | Text-blob feedback, no row-level structural context | Structured `_repair_feedback` dict with per-row issues and `passed_rows` list |
| `validation_refs` on rows never populated | `_append_validator_report` writes to flat `state["issues"]` only | Write findings back to `matrix.rows[i].validation_refs` |
| Matrix never updated by downstream phases | `gen_planning`, `generation`, `qc`, `post` write to separate artifacts | Write `prompt_ref`, `asset_refs`, etc. back to matrix rows |
| No version history across repairs | `_save_artifact` always uses `version=1` | Auto-increment version from existing artifact refs |
| Matrix lives only on disk, not in state | `state["shot_matrix_ref"]` is a pointer string | Store `state["matrix"] = MasterFilmMatrix(...)` in memory |

**Priority order:**
1. **P0:** Write `validation_refs` back to matrix rows (fixes the silent data loss)
2. **P0:** Structured `_repair_feedback` instead of text blob (makes repairs precise)
3. **P1:** Row-level preserve-on-repair (eliminates regenerating good rows)
4. **P1:** Auto-increment version on repair (keeps history)
5. **P2:** Downstream phases write back to matrix (gen_planning → `prompt_ref`, etc.)
6. **P2:** `Command` pattern for combined update+routing
