# Phase 3 — Artifact Versioning & Dependency Metadata

**Goal:** Fix `_save_artifact()` to auto-increment versions. Add `built_from` dependency tracking.
Add staleness detection so the graph can warn when downstream artifacts are based on stale upstream versions.

**Prerequisite:** Phase 2 (typed state) — nodes must return partial updates for version counting to work correctly.

---

## Current State

```python
# nodes.py:253-268 — _save_artifact ALWAYS uses version=1
meta = ArtifactMetadata(
    artifact_id=artifact_id,
    version=1,                    # ← Hardcoded. Repair overwrites v1.
    status=ArtifactStatus.CANDIDATE,
    parents=parents,
    created_by="graph_node",
    created_at=datetime.now(UTC),
)
services.artifact_store.save(artifact, meta)
ref = f"artifact:{artifact_id}:v1"  # ← Always v1
```

Result: `shot_matrix` repair round 3 still writes to `05-shot-bible/shot_matrix.v1.json`.
No version history. No rollback to v1 after v2 was bad. No way to know what each version was built from.

---

## Target State

```python
# First save:  artifact:shot_matrix:v1
# Repair:      artifact:shot_matrix:v2  (does NOT overwrite v1)
# Repair #2:   artifact:shot_matrix:v3
# Downstream can diff v1→v2→v3. Rollback can restore v1.
```

Each artifact metadata records:
```json
{
  "artifact_id": "shot_matrix",
  "version": 2,
  "built_from": {
    "script": "artifact:script:v1",
    "execution_brief": "artifact:execution_brief:v1",
    "visual_refs": "artifact:reference_index:v1"
  },
  "parents": [{"artifact_id": "shot_matrix", "version": 1}],
  "change_summary": "Repair round 1: fixed shot count mismatch"
}
```

---

## Files to Modify

| File | Change |
|------|--------|
| `graph/nodes.py:253-268` | `_save_artifact()` — auto-increment version, accept `change_summary` |
| `graph/nodes.py:225` | `_record_handoff()` — record version in handoff |
| `schemas/artifact.py` | Add `built_from: dict[str,str]` and `change_summary: str` to `ArtifactMetadata` |
| `artifacts/store.py` | Add `next_version()` method, `load_metadata()` if missing |
| NEW: `graph/consistency.py` | `check_staleness()` function |
| NEW: `graph/nodes.py` | `consistency_check_node` (post-phase staleness check) |
| `graph/graph.py` | Add `consistency_check` node between phases and gate |

---

## Step-by-Step

### Step 1: Add `built_from` and `change_summary` to ArtifactMetadata

**File:** `src/film_pipeline/schemas/artifact.py`

Check current schema, add fields:

```python
class ArtifactMetadata(SchemaBase):
    artifact_id: str
    artifact_type: ArtifactType
    project_id: str
    phase: FilmPhase
    version: int
    status: str  # ArtifactStatus
    parents: list[ArtifactRef] = Field(default_factory=list)
    created_by: str = "graph_node"
    created_at: datetime

    # NEW fields
    built_from: dict[str, str] = Field(
        default_factory=dict,
        description="Map of artifact_id → version_ref at creation time."
    )
    change_summary: str = Field(
        default="",
        description="Human-readable summary of what changed in this version."
    )
```

### Step 2: Add `next_version()` to ArtifactStore

**File:** `src/film_pipeline/artifacts/store.py`

```python
def next_version(self, project_id: str, phase: str, artifact_id: str) -> int:
    """Determine the next version number for an artifact.

    Scans existing artifact files in the phase directory and returns
    max(existing_versions) + 1, or 1 if no prior versions exist.
    """
    phase_dir = self._artifact_path(project_id, phase, artifact_id, 1).parent
    if not phase_dir.exists():
        return 1

    existing = list(phase_dir.glob(f"{artifact_id}.v*.json"))
    if not existing:
        return 1

    versions = []
    for p in existing:
        # Extract version from filename: artifact_id.v3.json → 3
        stem = p.stem  # artifact_id.v3
        if ".v" in stem:
            try:
                v = int(stem.split(".v")[-1])
                versions.append(v)
            except ValueError:
                continue

    return max(versions) + 1 if versions else 1
```

### Step 3: Rewrite `_save_artifact()` to Auto-Increment

**File:** `src/film_pipeline/graph/nodes.py:253-268`

```python
def _save_artifact(
    state: dict[str, Any],
    artifact: Any,
    artifact_id: str,
    phase: str,
    artifact_type: str | None = None,
    *,
    change_summary: str = "",
    built_from: dict[str, str] | None = None,
) -> str | None:
    """Persist an artifact with auto-incremented version and dependency metadata."""
    services = _get_services(state)
    if services is None:
        return None

    # Determine next version
    project_id = str(state.get("project_id", ""))
    version = services.artifact_store.next_version(project_id, phase, artifact_id)

    # Build dependency map from current state refs
    if built_from is None:
        built_from = _build_dependency_map(state)

    from datetime import UTC, datetime
    from film_pipeline.schemas._base import ArtifactStatus, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef

    if artifact_type is not None:
        try:
            atype = _ArtifactType(artifact_type)
        except ValueError:
            atype = _ArtifactType.SCRIPT
    else:
        atype = _infer_artifact_type(artifact)

    # Parent refs (previous versions of this artifact)
    parent_refs = [
        r for r in state.get("artifact_refs", [])
        if artifact_id in str(r)
    ]
    parents = [_parse_ref(r) for r in parent_refs]

    meta = ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=atype,
        project_id=project_id,
        phase=FilmPhase(phase),
        version=version,               # ← NOW AUTO-INCREMENTED
        status=ArtifactStatus.CANDIDATE,
        parents=parents,
        created_by="graph_node",
        created_at=datetime.now(UTC),
        built_from=built_from,          # ← NEW
        change_summary=change_summary,  # ← NEW
    )
    services.artifact_store.save(artifact, meta)
    ref = f"artifact:{artifact_id}:v{version}"

    # Record candidate ref for orchestrator state
    from film_pipeline.graph.orchestrator_state import ensure_orchestrator_state, set_candidate_ref
    ensure_orchestrator_state(state)
    set_candidate_ref(state, artifact_id, ref)

    return ref


def _build_dependency_map(state: dict[str, Any]) -> dict[str, str]:
    """Build built_from map from current state artifact refs."""
    ref_keys = [
        "profile_ref", "constitution_ref", "treatment_ref", "scene_list_ref",
        "script_ref", "story_bible_ref", "shot_matrix_ref", "visual_refs",
        "execution_brief_ref", "cost_estimate_ref",
    ]
    built_from: dict[str, str] = {}
    for key in ref_keys:
        ref = state.get(key)
        if ref and isinstance(ref, str) and ":" in ref:
            # Extract artifact_id from ref string "artifact:script:v2"
            parts = ref.split(":")
            if len(parts) >= 3:
                built_from[parts[1]] = ref
    return built_from
```

### Step 4: Update Repair Node to Pass `change_summary`

**File:** `src/film_pipeline/graph/nodes.py:repair_phase_node`

```python
# After re-running the phase node, the _save_artifact inside it
# will auto-increment. We can augment with change_summary:
# (This happens naturally — the phase node calls _save_artifact
#  which now auto-increments. No explicit change needed in repair node.)
```

### Step 5: Create `check_staleness()` Function

**File:** NEW `src/film_pipeline/graph/consistency.py`

```python
"""Artifact consistency checks — staleness detection, dependency validation."""

from __future__ import annotations

from typing import Any


def check_staleness(
    artifact_ref: str,
    state: dict[str, Any],
    services: Any,
) -> list[dict[str, Any]]:
    """Check if an artifact's upstream dependencies have newer versions.

    Returns a list of staleness warnings. Empty list = all deps are current.
    """
    warnings: list[dict[str, Any]] = []

    # Parse the artifact ref
    parts = artifact_ref.split(":")
    if len(parts) < 3:
        return warnings
    artifact_id = parts[1]

    # Load metadata for this artifact
    try:
        metadata = services.artifact_store.load_metadata(
            str(state.get("project_id", "")),
            artifact_id,
        )
    except (FileNotFoundError, ValueError):
        return warnings

    built_from = getattr(metadata, "built_from", {}) or {}

    # Compare each dependency version against current approved ref
    from film_pipeline.graph.orchestrator_state import get_approved_refs
    approved = get_approved_refs(state)

    for dep_id, dep_version_ref in built_from.items():
        current_ref = approved.get(dep_id)
        if current_ref and current_ref != dep_version_ref:
            warnings.append({
                "artifact_id": artifact_id,
                "artifact_ref": artifact_ref,
                "dependency_id": dep_id,
                "built_with_version": dep_version_ref,
                "current_version": current_ref,
                "severity": "stale",
                "message": (
                    f"Artifact '{artifact_id}' was built from {dep_version_ref} "
                    f"but {dep_id} is now at {current_ref}. This artifact may be stale."
                ),
            })

    return warnings


def check_phase_consistency(
    state: dict[str, Any],
    services: Any,
) -> dict[str, Any]:
    """Run staleness checks on all artifacts created in the current phase.

    Returns updates dict to merge into state (adds consistency_warnings).
    """
    phase = str(state.get("current_phase", ""))
    artifact_refs = state.get("artifact_refs", [])

    all_warnings: list[dict[str, Any]] = []
    for ref in artifact_refs:
        all_warnings.extend(check_staleness(ref, state, services))

    return {"consistency_warnings": all_warnings}
```

### Step 6: Add Consistency Check Node

**File:** `src/film_pipeline/graph/nodes.py` — new node

```python
def consistency_check_node(state: dict[str, Any]) -> dict[str, Any]:
    """Post-phase consistency check: are our outputs still valid?"""
    services = _get_services(state)
    if services is None:
        return {}
    return check_phase_consistency(state, services)
```

**File:** `src/film_pipeline/graph/graph.py` — wire into graph

```python
# After each phase node, before await_approval:
builder.add_node("consistency_check", consistency_check_node)
builder.add_edge("intake_node", "consistency_check")
builder.add_edge("consistency_check", "await_approval")
# ... repeat for all phase nodes
```

For Phase 3, add the node but keep it non-blocking — staleness warnings are informational.

---

## Test Cases

### Unit Tests (`tests/unit/test_artifacts.py` — update)

```python
def test_auto_increment_version(tmp_path):
    """Saving same artifact_id twice creates v1 then v2."""
    store = ArtifactStore(root=tmp_path)
    project_id = "test"

    meta1 = ArtifactMetadata(artifact_id="test_artifact", version=1, project_id=project_id, ...)
    store.save(artifact1, meta1)

    # Next version should be 2
    v = store.next_version(project_id, "intake", "test_artifact")
    assert v == 2

def test_first_version_is_1(tmp_path):
    """No prior versions → next_version returns 1."""
    store = ArtifactStore(root=tmp_path)
    v = store.next_version("new_project", "intake", "new_artifact")
    assert v == 1

def test_built_from_populated_on_save():
    """_save_artifact records upstream dependency versions."""
    state = {
        "project_id": "test",
        "artifact_refs": [],
        "script_ref": "artifact:script:v2",
        "constitution_ref": "artifact:film_constitution:v1",
    }
    # Call _save_artifact — verify metadata.built_from contains script and constitution refs
```

def test_check_staleness_detects_newer_upstream():
    """When upstream dep is newer, staleness warning is generated."""
    # Setup: artifact built from script:v1, but script is now at v3
    # check_staleness should return a warning
```

def test_check_staleness_clean_when_all_current():
    """When all deps match, no warnings."""
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `next_version()` scans filesystem — slow with many artifacts | Acceptable. Artifact counts per project are low (<50). Can add in-memory cache in Phase 6. |
| `total=False` TypedDict doesn't have `built_from` typed | Acceptable. `ArtifactMetadata` has the field typed — state just passes through. |
| Existing tests assert `v1` in ref strings | Update tests to use `_save_artifact` return value instead of hardcoded `v1`. |
| `consistency_check_node` adds latency | Non-blocking, informational only in Phase 3. Upgrade to blocking in Phase 6. |

---

## Acceptance Criteria

- [ ] `_save_artifact()` auto-increments version — first save = v1, repair = v2, second repair = v3
- [ ] `ArtifactMetadata.built_from` populated on every save with current upstream refs
- [ ] `ArtifactMetadata.change_summary` field exists (can be empty for initial implementation)
- [ ] `ArtifactStore.next_version()` returns correct next version
- [ ] `check_staleness()` detects when dependencies have newer versions
- [ ] `consistency_check_node` exists (non-blocking, informational)
- [ ] New tests: version increment, built_from population, staleness detection
- [ ] `make ci-check` green

**Estimated implementation time:** 2-3 hours
**Prerequisite:** Phase 2 (typed state) — version counting depends on `artifact_refs` append-only channel
