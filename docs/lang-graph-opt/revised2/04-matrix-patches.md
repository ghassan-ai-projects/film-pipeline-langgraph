# Phase 4 — Living Matrix via Versioned Patches

**Goal:** Make `MasterFilmMatrix` living — downstream phases emit patch artifacts that update
individual row fields (`prompt_ref`, `asset_refs`, `validation_refs`, `status`) instead of
saving separate disconnected artifacts.

**Prerequisite:** Phase 3 (artifact versioning) — patches need auto-incremented versions.

---

## Current State

```
shot_bible_node creates shot_matrix:v1 (all rows status="planned")
                                       │
                         ┌─────────────┼─────────────┐
                         ▼             ▼             ▼
                  gen_planning    generation      qc_node
                  saves cost_     stub — no      saves consensus
                  estimate —      row updates    report — no
                  no row updates                 row updates
                         │             │             │
                         ▼             ▼             ▼
                  Matrix rows unchanged: prompt_ref="", asset_refs=[],
                  validation_refs=[], status="planned" forever
```

## Target State

```
shot_bible_node creates shot_matrix:v1 (all rows status="planned")
                                       │
                         ┌─────────────┼─────────────┐
                         ▼             ▼             ▼
                  gen_planning    generation      qc_node
                  emits patch:v1  emits patch:v1  emits patch:v1
                  sets:           sets:           sets:
                  prompt_ref      asset_refs      validation_refs
                  provider_plan   status="gen"    status="val/fail"
                  status="prompted"
                         │             │             │
                         ▼             ▼             ▼
                  Materialized matrix = base.v1 + gen_planning_patch
                  + generation_patch + qc_patch
                  → every row has complete lifecycle tracking
```

---

## Files to Create/Modify

| File | Change |
|------|--------|
| NEW: `schemas/matrix_patch.py` | `MatrixRowUpdate`, `MatrixPatch` schemas |
| NEW: `artifacts/matrix_projection.py` | `materialize_matrix()`, `apply_patch()` helpers |
| `graph/nodes.py:gen_planning_node` | Emit matrix patch after planning |
| `graph/nodes.py:generation_node` | Emit matrix patch after generation |
| `graph/nodes.py:qc_node:_run_validators` | Emit matrix patch after validation |
| `graph/nodes.py:post_node` | Emit matrix patch after assembly |
| `schemas/matrix.py` | Add `status` transition validation |
| `graph/nodes.py:_save_artifact` | Handle `MatrixPatch` artifact type |

---

## Step-by-Step

### Step 1: Create Matrix Patch Schemas

**File:** NEW `src/film_pipeline/schemas/matrix_patch.py`

```python
"""Matrix patch artifacts — row-level updates without whole-matrix replacement."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class MatrixRowUpdate(SchemaBase):
    """A single row field update within a matrix patch."""

    shot_id: str = Field(description="Target shot row identifier.")
    set: dict[str, object] = Field(
        description="Fields to set, e.g. {'prompt_ref': '...', 'status': 'prompted'}."
    )
    append: dict[str, list[object]] = Field(
        default_factory=dict,
        description="Fields to append to, e.g. {'asset_refs': ['gen/shot_0001.mp4']}."
    )
    old_values: dict[str, object] = Field(
        default_factory=dict,
        description="Previous values for rollback support."
    )


class MatrixPatch(SchemaBase):
    """A versioned patch to the Master Film Matrix.

    Applied on top of a base matrix. Multiple patches can be layered.
    """

    patch_id: str = Field(description="Unique identifier, e.g. 'gen_planning_batch_001'.")
    matrix_ref: str = Field(description="Base matrix ref this patch applies to.")
    phase: str = Field(description="Phase that produced this patch.")
    reason: str = Field(default="", description="Why this patch was created.")
    updates: list[MatrixRowUpdate] = Field(
        default_factory=list,
        description="Row-level updates to apply."
    )
    created_by_agent: str = Field(default="", description="Agent that produced this patch.")
    validator_refs: list[str] = Field(default_factory=list)
    approval_refs: list[str] = Field(default_factory=list)

    def apply_to(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        """Apply this patch to a list of row dicts. Returns modified rows."""
        row_map = {str(r.get("shot_id", "")): r for r in rows}

        for update in self.updates:
            row = row_map.get(update.shot_id)
            if row is None:
                continue

            # Record old values for rollback
            for key in update.set:
                update.old_values[key] = row.get(key)
            for key in update.append:
                update.old_values[key] = list(row.get(key, []))

            # Apply set
            for key, value in update.set.items():
                row[key] = value

            # Apply append
            for key, values in update.append.items():
                existing = row.get(key, [])
                if not isinstance(existing, list):
                    existing = []
                row[key] = existing + values

        return list(row_map.values())
```

### Step 2: Create Matrix Projection Helper

**File:** NEW `src/film_pipeline/artifacts/matrix_projection.py`

```python
"""Materialize the current matrix from base artifact + patches."""

from __future__ import annotations

from typing import Any


def load_base_matrix(store: Any, project_id: str, matrix_ref: str) -> dict[str, Any]:
    """Load the base matrix artifact."""
    parts = matrix_ref.split(":")
    artifact_id = parts[1] if len(parts) > 1 else matrix_ref
    version_str = parts[2] if len(parts) > 2 else "1"
    version = int(version_str.lstrip("v"))

    from film_pipeline.schemas._base import FilmPhase
    return store.load(project_id, FilmPhase.SHOT_BIBLE, artifact_id, version)


def load_patch(store: Any, project_id: str, patch_ref: str) -> Any:
    """Load a matrix patch artifact."""
    from film_pipeline.schemas.matrix_patch import MatrixPatch

    parts = patch_ref.split(":")
    artifact_id = parts[1] if len(parts) > 1 else patch_ref
    version_str = parts[2] if len(parts) > 2 else "1"
    version = int(version_str.lstrip("v"))

    # Patches are stored in the phase that created them
    # For now, try common phases
    from film_pipeline.schemas._base import FilmPhase
    for phase in [FilmPhase.GEN_PLANNING, FilmPhase.GENERATION, FilmPhase.QC, FilmPhase.POST]:
        try:
            data = store.load(project_id, phase, artifact_id, version)
            return MatrixPatch(**data)
        except (FileNotFoundError, ValueError):
            continue

    raise FileNotFoundError(f"Patch {patch_ref} not found in any phase")


def materialize_matrix(
    store: Any,
    project_id: str,
    base_ref: str,
    patch_refs: list[str],
) -> dict[str, Any]:
    """Build the current matrix by applying patches to the base.

    Args:
        store: ArtifactStore instance.
        project_id: Project identifier.
        base_ref: Base matrix artifact ref (e.g. "artifact:shot_matrix:v1").
        patch_refs: Ordered list of patch refs to apply.

    Returns:
        Matrix dict with all patches applied.
    """
    matrix = load_base_matrix(store, project_id, base_ref)
    rows = matrix.get("rows", [])
    if not isinstance(rows, list):
        rows = []

    for patch_ref in patch_refs:
        patch = load_patch(store, project_id, patch_ref)
        rows = patch.apply_to(rows)

    matrix["rows"] = rows
    return matrix


def get_rows_by_status(matrix: dict[str, Any], status: str) -> list[dict[str, Any]]:
    """Filter matrix rows by status field."""
    rows = matrix.get("rows", [])
    return [r for r in rows if r.get("status") == status]
```

### Step 3: Wire `gen_planning_node` to Emit Matrix Patch

**File:** `src/film_pipeline/graph/nodes.py:gen_planning_node` (~line 641)

After saving `cost_estimate`, add patch emission:

```python
def gen_planning_node(state):
    # ... existing code to run agent, save cost_estimate ...

    # NEW: Emit matrix patch updating prompt_ref and provider_plan_ref per row
    result = _run_agent(state, agent_id="provider-planning-agent", ...)
    shot_groups = result.get("shot_groups", [])

    if shot_groups:
        from film_pipeline.schemas.matrix_patch import MatrixPatch, MatrixRowUpdate

        updates = []
        for group in shot_groups:
            shot_id = group.get("shot_id", "")
            if not shot_id:
                continue
            updates.append(MatrixRowUpdate(
                shot_id=shot_id,
                set={
                    "prompt_ref": group.get("prompt_ref", ""),
                    "provider_plan_ref": group.get("provider_plan_ref", ""),
                    "status": "prompted",
                },
            ))

        patch = MatrixPatch(
            patch_id=f"gen_planning_{project_id}",
            matrix_ref=state.get("shot_matrix_ref", ""),
            phase="gen_planning",
            reason="Generation plan assigned prompts and provider plans.",
            updates=updates,
            created_by_agent="provider-planning-agent",
        )

        # Save patch as artifact
        patch_ref = _save_artifact(state, patch, "matrix_patch_gen_planning", "gen_planning")
        if patch_ref:
            updates_dict["gen_planning_patch_ref"] = patch_ref

    return updates_dict
```

### Step 4: Wire `generation_node` to Emit Matrix Patch

**File:** `src/film_pipeline/graph/nodes.py:generation_node` (~line 703)

Currently a stub (runs Gate C only). After Phase 4, also emit asset patch:

```python
def generation_node(state):
    updates: dict[str, object] = {
        "current_phase": "generation",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "generation_batch",
    }

    # Gate C validation (existing)
    gen_requests = state.get("generation_requests")
    if gen_requests is not None:
        dispatch_issues = validate_dispatch_readiness(state, gen_requests)
        if dispatch_issues:
            updates["issues"] = dispatch_issues

    # NEW: For each generated clip, emit a matrix patch row
    generated_assets = _run_generation(state)  # new function
    if generated_assets:
        from film_pipeline.schemas.matrix_patch import MatrixPatch, MatrixRowUpdate

        updates_list = []
        for asset in generated_assets:
            updates_list.append(MatrixRowUpdate(
                shot_id=asset["shot_id"],
                append={"asset_refs": [asset["ref"]]},
                set={"status": "generated"},
            ))

        patch = MatrixPatch(
            patch_id=f"generation_{state.get('project_id')}",
            matrix_ref=state.get("shot_matrix_ref", ""),
            phase="generation",
            reason="Clips generated.",
            updates=updates_list,
            created_by_agent="generation-scheduler-agent",
        )
        patch_ref = _save_artifact(state, patch, "matrix_patch_generation", "generation")
        if patch_ref:
            updates["generation_patch_ref"] = patch_ref

    return updates
```

### Step 5: Wire `qc_node` to Emit Matrix Patch

**File:** `src/film_pipeline/graph/nodes.py:_run_validators` → after validation

After validators produce findings, emit a patch that sets `validation_refs` and status:

```python
def _append_validator_report(report, issues, state):
    # ... existing code to append issues ...

    # NEW: Build matrix patch entries for per-row findings
    row_updates = []
    for finding in report.findings:
        shot_id = getattr(finding, "shot_id", None)
        if not shot_id:
            continue

        row_updates.append(MatrixRowUpdate(
            shot_id=shot_id,
            append={"validation_refs": [report.validator_id]},
            set={
                "status": "failed" if finding.severity == "blocking" else "validated",
            },
        ))

    if row_updates:
        state.setdefault("_pending_row_updates", []).extend(row_updates)
```

Then in `qc_node`, after all validators run, save the patch:

```python
def qc_node(state):
    # ... existing agent and validator code ...

    pending = state.pop("_pending_row_updates", [])
    if pending:
        patch = MatrixPatch(
            patch_id=f"qc_{state.get('project_id')}",
            matrix_ref=state.get("shot_matrix_ref", ""),
            phase="qc",
            reason="Validation results applied to matrix rows.",
            updates=pending,
            created_by_agent="clip-validator",
        )
        patch_ref = _save_artifact(state, patch, "matrix_patch_qc", "qc")
        if patch_ref:
            updates["qc_patch_ref"] = patch_ref

    return updates
```

### Step 6: Wire `post_node` to Emit Matrix Patch

**File:** `src/film_pipeline/graph/nodes.py:post_node`

After assembly manifest is saved, emit patch for assembled rows:

```python
def post_node(state):
    # ... existing code ...

    # Mark rows as assembled
    matrix_ref = state.get("shot_matrix_ref", "")
    if matrix_ref:
        # Materialize current matrix to get all row IDs
        matrix = materialize_matrix(services.artifact_store, project_id, matrix_ref, patch_refs)
        updates = [
            MatrixRowUpdate(
                shot_id=row["shot_id"],
                set={"status": "assembled", "post_refs": [assembly_manifest_ref]},
            )
            for row in matrix.get("rows", [])
            if row.get("status") == "validated"
        ]

        if updates:
            patch = MatrixPatch(...)
            patch_ref = _save_artifact(state, patch, "matrix_patch_post", "post")

    return updates
```

---

## Test Cases

### Unit Tests (`tests/unit/schemas/test_matrix_patch.py` — NEW)

```python
from film_pipeline.schemas.matrix_patch import MatrixPatch, MatrixRowUpdate

def test_patch_sets_field_on_target_row():
    """Patch updates only the specified row, not others."""
    rows = [
        {"shot_id": "s_001", "status": "planned", "prompt_ref": ""},
        {"shot_id": "s_002", "status": "planned", "prompt_ref": ""},
    ]
    patch = MatrixPatch(
        patch_id="test",
        matrix_ref="artifact:shot_matrix:v1",
        phase="gen_planning",
        updates=[MatrixRowUpdate(shot_id="s_001", set={"prompt_ref": "ref1", "status": "prompted"})],
    )
    result = patch.apply_to(rows)
    assert result[0]["prompt_ref"] == "ref1"
    assert result[0]["status"] == "prompted"
    assert result[1]["prompt_ref"] == ""  # unchanged

def test_patch_appends_to_list_field():
    """Append adds items without removing existing."""
    rows = [{"shot_id": "s_001", "asset_refs": ["old.mp4"]}]
    patch = MatrixPatch(
        patch_id="test", matrix_ref="...", phase="generation",
        updates=[MatrixRowUpdate(shot_id="s_001", append={"asset_refs": ["new.mp4"]})],
    )
    result = patch.apply_to(rows)
    assert result[0]["asset_refs"] == ["old.mp4", "new.mp4"]

def test_patch_preserves_old_values_for_rollback():
    """old_values captures previous values for rollback support."""
    update = MatrixRowUpdate(shot_id="s_001", set={"status": "generated"})
    rows = [{"shot_id": "s_001", "status": "planned"}]
    patch = MatrixPatch(patch_id="test", matrix_ref="...", phase="generation", updates=[update])
    patch.apply_to(rows)
    assert update.old_values["status"] == "planned"

def test_materialize_matrix_applies_patches_in_order():
    """Patches are applied sequentially — later patches override earlier."""
    # Base: status=planned
    # Patch1: status=prompted
    # Patch2: status=generated
    # Result: status=generated (patch2 wins)
```

### Integration Tests (`tests/integration/test_matrix_patches.py` — NEW)

```python
def test_gen_planning_emits_patch(tmp_path):
    """gen_planning_node saves a MatrixPatch artifact."""
    # Setup runtime with mock services
    # Run gen_planning_node
    # Verify matrix_patch_gen_planning artifact exists
    # Verify patch sets prompt_ref on rows

def test_materialized_matrix_has_correct_row_statuses():
    """After all phases, rows have correct lifecycle statuses."""
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Patch application order matters | Store patch refs in order. Always apply from oldest to newest. |
| Patch references missing base matrix | Validate `matrix_ref` exists before saving patch. |
| Concurrent patches to same row | Patches are sequential per phase (graph is linear). No concurrency. |
| Row not found in base matrix | `apply_to()` silently skips unknown `shot_id`s. Log warning. |

---

## Acceptance Criteria

- [ ] `MatrixPatch` and `MatrixRowUpdate` schemas defined and importable
- [ ] `materialize_matrix()` loads base + applies patches in order
- [ ] `gen_planning_node` emits patch with `prompt_ref`, `provider_plan_ref`, `status="prompted"`
- [ ] `generation_node` emits patch with `asset_refs`, `status="generated"`
- [ ] `qc_node` emits patch with `validation_refs`, `status="validated"` or `"failed"`
- [ ] `post_node` emits patch with `post_refs`, `status="assembled"`
- [ ] Patches are saved as versioned artifacts (v1, v2, ...)
- [ ] `old_values` captured for rollback support
- [ ] New tests: patch application, materialization, per-phase patch emission
- [ ] `make ci-check` green

**Estimated implementation time:** 4-5 hours
**Prerequisite:** Phase 3 (artifact versioning) — patches need auto-incremented versions
