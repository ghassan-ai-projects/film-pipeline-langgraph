# 08 — MCP Tools for OpenClaw Orchestration (Implementation Plan)

## Summary

Replace internal hard validators with MCP tools that let OpenClaw inspect,
reason about, and direct the pipeline. OpenClaw is the orchestrator; the
pipeline is the execution engine.

## Tools

### 1. `get_phase_context` (NEW)

**Purpose:** One-call context packet for OpenClaw to assess phase output quality.

**Input:** None (uses active project + current phase)

**Output:**
```json
{
  "ok": true,
  "project_id": "primordial-v4",
  "current_phase": "development",
  "target": {
    "runtime_seconds": 600,
    "film_type": "narrative",
    "pacing_style": "standard",
    "expected_scene_count": "~13 (at ~45s/scene)",
    "expected_shot_count": "~80 (at ~7.5s/shot)"
  },
  "constitution": {
    "theme": "rediscovery through collision of artistic paralysis and primal creativity",
    "tone": "introspective, surreal, transformative",
    "visual_language": "painterly textures..."
  },
  "artifacts": {
    "treatment": {
      "scenes": 6,
      "acts": 3,
      "themes": ["collision of modern and primal", "timeless expression"],
      "preview": "first 300 chars of treatment text..."
    },
    "scene_list": {
      "count": 6,
      "scenes": [
        {"id": "s_001", "function": "Establish creative paralysis..."},
        ...
      ]
    }
  },
  "metrics": {
    "scene_count": 6,
    "expected_scenes_for_runtime": 13,
    "estimated_content_duration": "~150s",
    "runtime_gap": "~450s short of 600s target"
  },
  "consistency_warnings": []
}
```

### 2. `review_phase_artifacts` (ENHANCE)

**Changes:**
- Add `metrics` section (same as `get_phase_context`)
- Add `consistency_warnings` from staleness check
- Add `target_comparison`: "6 scenes vs expected ~13 for 600s"

### 3. `request_revision` (ENHANCE)

**Changes:**
- Add optional `preserve` field: list of things to keep
- Add optional `target_artifact` field: which artifact to focus on
- The feedback string goes to the repair phase node as `_repair_feedback`

**Input:**
```json
{
  "feedback": "Expand scene 3 into 2-3 discovery moments...",
  "preserve": ["opening studio scenes", "crack transition"],
  "target_artifact": "treatment"
}
```

### 4. Validators → Informational (MODIFY)

**File:** `src/film_pipeline/graph/orchestrator_validators.py`

Change issue severity from `"blocking"` to `"warning"` in:
- `validate_shot_structure`
- `validate_planning_completeness`

Keep the validators running — they provide useful data. But they don't block
approval. OpenClaw reads their output through `get_phase_context` and decides.

## Implementation Steps

### Step 1: `get_phase_context` MCP tool
- File: `src/film_pipeline/mcp/tools/__init__.py`
- Assembles context packet from state + artifact store
- ~150 lines

### Step 2: Enhance `review_phase_artifacts`
- File: `src/film_pipeline/mcp/tools/__init__.py`
- Add metrics + consistency_warnings to output
- ~30 lines

### Step 3: Enhance `request_revision`
- File: `src/film_pipeline/mcp/tools/__init__.py`
- Parse `preserve` and `target_artifact` from args
- Store in state for repair node to read
- ~20 lines

### Step 4: Validators → warning severity
- File: `src/film_pipeline/graph/orchestrator_validators.py`
- Change `_blocking()` to `_warning()` for Gate A and Gate B
- ~10 lines

### Step 5: OpenClaw operator prompt
- File: `docs/openclaw-mcp-operator-guide.md` (update)
- Add "Orchestrator Role" section with decision loop
- ~50 lines

### Step 6: Tests
- Unit test: `get_phase_context` returns expected shape
- Unit test: `request_revision` stores preserve/target
- Smoke test: OpenClaw flow (manual, with `scripts/e2e-real-auto-approve.py`)

## Files Changed

| File | Change |
|------|--------|
| `src/film_pipeline/mcp/tools/__init__.py` | New `get_phase_context` tool + enhance 2 existing |
| `src/film_pipeline/graph/orchestrator_validators.py` | Severity: blocking → warning |
| `docs/openclaw-mcp-operator-guide.md` | OpenClaw orchestrator role section |

## What Stays The Same

- Phase nodes — unchanged
- Graph structure — unchanged
- Auto-approve profile — unchanged (OpenClaw replaces human, not auto-approve)
- Repair node — unchanged (already accepts `_repair_feedback`)
- Convergence tracking — unchanged (3 rounds → escalate to OpenClaw)
