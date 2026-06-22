# Challenge Analysis: Is the Original Issue Actually Fixed?

## Verdict

**No.** The implementation is a detection system, not an enforcement system. The gates detect structural problems and write them to `state["issues"]`, but the approval path never reads that field. It's a smoke detector with no sprinkler system.

## The Critical Gap

### What we built

Gate A/B/C validators run at phase boundaries and append blocking issues to `state["issues"]`. This works — the issues are correctly detected and stored.

### What doesn't work

The MCP `approve_phase` tool bypasses LangGraph entirely. It goes through `runtime.approve_phase()` → `_advance_to_next_phase()` directly, which never checks `state["issues"]` for blocking issues.

### The execution trace

```
User calls MCP approve_phase tool
  → mcp/tools/__init__.py:502  approve_phase()
    → runtime.py:144  rt.approve_phase()
      → runtime.py:296  self._approve_current_phase(active)
        → nodes.py:957  approve_phase_node(state)
          → new_state["approved"] = True          ← approval granted
          → new_state["human_approval_required"] = False
          → return new_state
      → runtime.py:309  self._advance_to_next_phase(approved_state)
        → runs next phase node immediately         ← phase advanced
      → return result                               ← user sees success
```

At no point in this path does anyone check `state["issues"]` for blocking issues.

### Where the check IS

The `compute_actions()` function in `router.py` (tier 5) does check blocking issues and routes to `handle_blockers`. But that function is only called by `after_phase()` in `edges.py` — the **LangGraph edge function**. The MCP approval path doesn't go through LangGraph edges.

The `review/actions.py` `compute_available_actions()` function also blocks `approve_phase` when blocking issues exist — but that's only used for **display** in the review package. The actual MCP tool never calls it.

## Acceptance Criteria Status

| Criterion | Status | Why |
|-----------|--------|-----|
| "A failing shot-count mismatch blocks advancement out of shot-bible" | NOT FIXED | Gate A adds a blocking issue, but `approve_phase` ignores it and advances |
| "A failing runtime mismatch blocks advancement" | NOT FIXED | Same — issue is added but not enforced |
| "A missing prompt or reference package blocks provider dispatch" | NOT FIXED | Gate B adds issue, but approval still works |
| "Provider dispatch only starts from executable requests" | NOT FIXED | Gate C adds issue, but nothing checks it before dispatch |
| "The orchestrator stores the approved film execution brief" | PARTIAL | Brief is stored, but at shot_bible phase start, not "after script approval" |
| "Shot-bible output includes enough shot rows" | NOT FIXED | Validated but not enforced |
| "Every shot row contains non-empty generation-critical fields" | NOT FIXED | Validated but not enforced |
| "Generation planning produces real clip counts and non-placeholder cost estimates" | NOT FIXED | Validated but not enforced |

## The Fix

`runtime.approve_phase()` must check for blocking issues before advancing:

```python
def approve_phase(self) -> dict[str, Any]:
    active = self.get_active()
    if not active:
        raise ValueError("No active project.")

    issues = active.get("issues", [])
    blocking = [i for i in issues if i.get("severity") == "blocking"]
    if blocking:
        codes = ", ".join(i.get("code", "?") for i in blocking)
        raise ValueError(
            f"Cannot approve phase: {len(blocking)} blocking issue(s) "
            f"must be resolved first. Codes: {codes}"
        )

    # ... proceed with approval
```

Additionally, `approve_phase_node` in `nodes.py` should have the same guard, since it's the LangGraph-path entry point for approval.

## What We Actually Have

| Layer | Status |
|-------|--------|
| ExecutionBrief extraction | Works — auto-extracts from raw story |
| Cross-validation of brief | Works — checks act count, runtime consistency, anchors |
| Gate A (shot count + runtime) | Detects correctly, doesn't enforce |
| Gate B (field completeness + cost) | Detects correctly, doesn't enforce |
| Gate C (dispatch readiness) | Detects correctly, doesn't enforce |
| Approval path checks issues | **MISSING — this is the sprinkler** |
| Repair routing on blocking issues | Works in LangGraph path, but MCP bypasses it |
| Retry with feedback injection | Not implemented |
