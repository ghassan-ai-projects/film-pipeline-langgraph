# Phase 5 — Structured Repair Feedback

**Goal:** Replace the flat string `_repair_feedback` with typed per-row repair instructions.
Agents receive structured data telling them exactly which rows to fix, which to preserve,
and what each fix should be.

**Prerequisite:** Phase 4 (matrix patches) — validators must emit row-level findings before repair can target rows.

---

## Current State

```python
# repair_phase_node builds a flat string:
state["_repair_feedback"] = (
    f"REPAIR ROUND {round_num}: Your previous output was REJECTED. "
    f"Issues to fix:\n[shot_count_mismatch] Expected 20 shots, got 12."
)

# _run_agent reads it:
feedback = state.pop("_repair_feedback", "")
if feedback:
    task = f"{feedback}\n\n{task}"  # prepended as string
```

The agent gets a text blob and guesses:
- Which rows need fixing? (the validator only said "got 12, need 20")
- Which rows are good and should be preserved? (no information)
- What exactly is wrong with each bad row? (vague)

---

## Target State

```python
# Structured feedback saved as artifact, reference passed through state:
state["repair_feedback_ref"] = "artifact:repair_feedback:v1"

# Agent receives structured data:
{
  "phase": "shot_bible",
  "round": 1,
  "failed_rows": [
    {
      "shot_id": "shot_0003",
      "issues": [{"code": "missing_prompt_ref", "field": "prompt_ref", "action": "set prompt_ref"}],
      "preserve_other_fields": true
    }
  ],
  "global_issues": [
    {"code": "shot_count_mismatch", "message": "act_1 needs 4 more shots"}
  ],
  "passed_row_ids": ["shot_0001", "shot_0002", "shot_0004", ...]
}
```

---

## Files to Modify

| File | Change |
|------|--------|
| NEW: `schemas/repair.py` | `RepairFeedback`, `RowRepairInstruction` schemas |
| `validation/base.py` | Add optional `shot_id`, `field`, `recommended_action` to findings |
| `graph/nodes.py:repair_phase_node` | Build structured `RepairFeedback`, persist as artifact |
| `graph/nodes.py:_run_agent()` | Read `repair_feedback_ref`, load structured feedback |
| Agent prompt templates | Update context to use structured repair data |

---

## Step-by-Step

### Step 1: Create Repair Feedback Schema

**File:** NEW `src/film_pipeline/schemas/repair.py`

```python
"""Structured repair feedback — tells agents exactly what to fix."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class RowRepairInstruction(SchemaBase):
    """Instruction for fixing a single matrix row."""

    shot_id: str
    issues: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {code, field, message, recommended_action} dicts."
    )
    preserve_other_fields: bool = Field(
        default=True,
        description="If True, only fix the listed issues. Other fields should be left as-is."
    )


class GlobalRepairIssue(SchemaBase):
    """A repair issue that spans multiple rows or is not row-specific."""

    code: str
    message: str
    recommended_action: str = ""


class RepairFeedback(SchemaBase):
    """Complete repair instructions for a phase re-run."""

    repair_id: str = Field(description="Unique identifier, e.g. 'repair:shot_bible:r1'.")
    phase: str
    round: int = Field(ge=1)
    project_id: str

    # Row-level instructions
    failed_rows: list[RowRepairInstruction] = Field(default_factory=list)
    passed_row_ids: list[str] = Field(
        default_factory=list,
        description="Rows that passed validation and should be preserved verbatim."
    )

    # Global issues
    global_issues: list[GlobalRepairIssue] = Field(default_factory=list)

    # Metadata
    validation_report_refs: list[str] = Field(default_factory=list)
    previous_artifact_ref: str = Field(default="")
    convergence_round: int = Field(default=1, ge=1, le=5)

    def to_agent_context(self) -> str:
        """Render as structured text for agent prompt injection."""
        lines = [
            f"REPAIR ROUND {self.round}: Your previous output was REJECTED.",
            "",
        ]

        if self.passed_row_ids:
            lines.append(
                f"PRESERVE these {len(self.passed_row_ids)} rows verbatim "
                f"(they passed validation): {', '.join(self.passed_row_ids[:20])}"
                + ("..." if len(self.passed_row_ids) > 20 else "")
            )
            lines.append("")

        if self.failed_rows:
            lines.append(f"FIX these {len(self.failed_rows)} rows:")
            for fr in self.failed_rows:
                issue_descs = []
                for issue in fr.issues:
                    desc = f"[{issue.get('code', '?')}] {issue.get('message', '')}"
                    if issue.get("field"):
                        desc += f" (field: {issue.get('field')})"
                    if issue.get("recommended_action"):
                        desc += f" → {issue.get('recommended_action')}"
                    issue_descs.append(desc)

                preserve = " (preserve all other fields)" if fr.preserve_other_fields else ""
                lines.append(f"  {fr.shot_id}: {'; '.join(issue_descs)}{preserve}")
            lines.append("")

        if self.global_issues:
            lines.append("GLOBAL FIXES:")
            for gi in self.global_issues:
                lines.append(f"  [{gi.code}] {gi.message}")
                if gi.recommended_action:
                    lines.append(f"    → {gi.recommended_action}")

        return "\n".join(lines)
```

### Step 2: Extend Validator Findings

**File:** `src/film_pipeline/validation/base.py`

Add optional fields to the base finding/report:

```python
class ValidationFinding(SchemaBase):
    code: str
    message: str
    severity: str  # "blocking" | "warning"

    # NEW: row-level targeting
    shot_id: str | None = None       # which matrix row
    field: str | None = None         # which field on the row
    recommended_action: str = ""     # what the agent should do
```

Update all 6 validator implementations to set `shot_id` and `field` where possible.

### Step 3: Rewrite `repair_phase_node`

**File:** `src/film_pipeline/graph/nodes.py:repair_phase_node`

```python
def repair_phase_node(state):
    from film_pipeline.graph.orchestrator_state import (
        increment_convergence_round, is_stalled, mark_stalled,
    )

    _init_phase_nodes()
    phase = str(state.get("current_phase", ""))

    # Convergence check
    round_num = increment_convergence_round(state, phase)
    if is_stalled(state, phase, max_rounds=3):
        mark_stalled(state, phase, f"Repair failed after {round_num} rounds.")
        return state

    # Build structured feedback from issues
    blocking = [i for i in state.get("issues", []) if i.get("severity") == "blocking"]
    all_issues = state.get("issues", [])

    from film_pipeline.schemas.repair import (
        RepairFeedback, RowRepairInstruction, GlobalRepairIssue,
    )

    # Separate row-level from global issues
    row_issues: dict[str, list[dict]] = {}
    global_list: list[GlobalRepairIssue] = []

    for issue in all_issues:
        shot_id = issue.get("shot_id")
        if shot_id:
            row_issues.setdefault(str(shot_id), []).append({
                "code": str(issue.get("code", "?")),
                "field": str(issue.get("field", "")),
                "message": str(issue.get("message", "")),
                "recommended_action": str(issue.get("recommended_action", "")),
            })
        else:
            global_list.append(GlobalRepairIssue(
                code=str(issue.get("code", "?")),
                message=str(issue.get("message", "")),
            ))

    # Determine passed rows (present in matrix, not in failed_rows)
    matrix = state.get("matrix")  # from Phase 3
    all_row_ids = []
    if matrix:
        all_row_ids = [r.shot_id for r in matrix.rows] if hasattr(matrix, "rows") else []
    passed_ids = [sid for sid in all_row_ids if sid not in row_issues]

    feedback = RepairFeedback(
        repair_id=f"repair:{phase}:r{round_num}",
        phase=phase,
        round=round_num,
        project_id=str(state.get("project_id", "")),
        failed_rows=[
            RowRepairInstruction(shot_id=sid, issues=issues)
            for sid, issues in row_issues.items()
        ],
        passed_row_ids=passed_ids,
        global_issues=global_list,
        convergence_round=round_num,
    )

    # Save as artifact
    services = _get_services(state)
    if services:
        ref = _save_artifact(state, feedback, f"repair_feedback_{phase}", phase)
        if ref:
            state["repair_feedback_ref"] = ref

    # Re-run the phase node
    phase_fn = _PHASE_NODES.get(phase)
    if phase_fn:
        return phase_fn(state)

    return state
```

### Step 4: Update `_run_agent()` to Read Structured Feedback

**File:** `src/film_pipeline/graph/nodes.py:_run_agent()`

```python
def _run_agent(state, agent_id, phase, task, *, task_type="create"):
    # Load structured repair feedback if available
    repair_ref = state.pop("repair_feedback_ref", "")
    if repair_ref:
        services = _get_services(state)
        if services:
            try:
                from film_pipeline.schemas.repair import RepairFeedback
                parts = repair_ref.split(":")
                aid = parts[1] if len(parts) > 1 else repair_ref
                ver_str = parts[2] if len(parts) > 2 else "1"
                ver = int(ver_str.lstrip("v"))
                data = services.artifact_store.load(
                    str(state.get("project_id", "")),
                    FilmPhase(phase), aid, ver,
                )
                feedback = RepairFeedback(**data)
                task = f"{feedback.to_agent_context()}\n\n{task}"
            except (FileNotFoundError, ValueError, KeyError):
                pass
    else:
        # Fallback to legacy string feedback
        feedback = state.pop("_repair_feedback", "")
        if feedback:
            task = f"{feedback}\n\n{task}"

    # ... rest of _run_agent ...
```

---

## Test Cases

```python
def test_repair_feedback_includes_passed_rows():
    """Feedback lists which rows to preserve."""
    feedback = RepairFeedback(
        repair_id="test", phase="shot_bible", round=1, project_id="test",
        failed_rows=[RowRepairInstruction(shot_id="s_003", issues=[...])],
        passed_row_ids=["s_001", "s_002", "s_004"],
    )
    rendered = feedback.to_agent_context()
    assert "PRESERVE" in rendered
    assert "s_001" in rendered
    assert "s_003" in rendered  # failed row

def test_repair_feedback_global_issues_no_rows():
    """Global issues don't require row-level targeting."""
    feedback = RepairFeedback(
        repair_id="test", phase="shot_bible", round=1, project_id="test",
        global_issues=[GlobalRepairIssue(code="runtime_mismatch", message="...")],
    )
    rendered = feedback.to_agent_context()
    assert "GLOBAL FIXES" in rendered

def test_validator_finding_with_shot_id():
    """Validator can tag findings with shot_id for row-level repair."""
    finding = ValidationFinding(
        code="missing_prompt_ref", message="...", severity="blocking",
        shot_id="shot_0003", field="prompt_ref",
        recommended_action="Set prompt_ref to a valid prompt artifact ref.",
    )
    assert finding.shot_id == "shot_0003"
```

---

## Acceptance Criteria

- [ ] `RepairFeedback` schema with `failed_rows`, `passed_row_ids`, `global_issues`
- [ ] `ValidationFinding` has optional `shot_id`, `field`, `recommended_action`
- [ ] `repair_phase_node` builds structured `RepairFeedback` and saves as artifact
- [ ] `_run_agent()` loads `repair_feedback_ref` artifact and formats as structured context
- [ ] Legacy `_repair_feedback` string path still works as fallback
- [ ] At least 2 validators set `shot_id` on findings
- [ ] `make ci-check` green

**Estimated implementation time:** 2-3 hours
**Prerequisite:** Phase 4 (matrix patches) — validators need row-targeted findings
