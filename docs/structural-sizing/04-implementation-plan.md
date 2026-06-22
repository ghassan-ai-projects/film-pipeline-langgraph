# 04 — Implementation Plan

## TL;DR

The structure extractor must run BEFORE development (not at shot_bible), derive its
numbers FROM the target runtime (not the story text), and produce a structural
contract that development and script MUST meet.

## Implementation Steps

### Step 1: Move Structure Extractor to `development_node` (P0)

Currently in `shot_bible_node` as a pre-step. Move to `development_node` as a
pre-step, BEFORE the development agent runs.

**File:** `src/film_pipeline/graph/nodes.py` → `development_node`

**Before (current):**
```python
def development_node(state):
    result = _run_agent(new_state, agent_id="treatment-agent", ...)
```

**After:**
```python
def development_node(state):
    # ── Pre-step: extract structural contract ──
    if not has_execution_brief(new_state):
        brief = _extract_structure(new_state)  # calls structure-extractor-agent
        # uses target_runtime_seconds from project_profile, NOT from story text
    # ── Run development agent with contract ──
    result = _run_agent(new_state, agent_id="treatment-agent", ...)
    # ── Gate 0: validate scene count ──
    validate_scene_count(new_state, brief)
```

### Step 2: Add `scene_count` to ExecutionBrief (P0)

**File:** `src/film_pipeline/schemas/execution_brief.py`

Add field:
```python
scene_count: int = Field(ge=1, description="Required number of scenes.")
```

The structure extractor computes this from the formula:
```python
scene_count = target_runtime_seconds // avg_scene_duration_by_pacing[pacing_style]
```

### Step 3: Structure Extractor Uses Target Runtime (P0)

**File:** `src/film_pipeline/agents/prompt_templates/defaults.py` → `_structure_extractor`

Template change: inject `{target_runtime_seconds}` into context, instruct
the agent to use it as THE number (not derive from text).

### Step 4: Gate 0 — Scene Count Validator (P0)

**File:** `src/film_pipeline/graph/orchestrator_validators.py`

New function:
```python
def validate_scene_count(state, scene_list, execution_brief):
    """Check that scene count matches the structural contract."""
    required = execution_brief.scene_count
    actual = len(scene_list.scenes)
    if actual < required:
        return [_blocking("insufficient_scenes",
            f"Expected {required} scenes, got {actual}.")]
    return []
```

### Step 5: Development Template — Hard Scene Count (P0)

**File:** `src/film_pipeline/agents/prompt_templates/defaults.py` → `_development_creator`

Change from ranges to hard numbers:
```
Current:  "1-4 min film → 4-8 scenes"
Ideal:    "The structural contract requires EXACTLY {required_scenes} scenes.
           You MUST produce exactly this many. {scene_distribution}"
```

### Step 6: Script Template — Duration Guidance (P1)

**File:** `src/film_pipeline/agents/prompt_templates/defaults.py` → `_screenwriter`

Add per-scene duration guidance:
```
"Each of the {scene_count} scenes should contribute approximately
 {avg_scene_duration}s to the total {target_runtime}s runtime."
```

### Step 7: MCP Runtime Override (P1)

**File:** `src/film_pipeline/mcp/tools/__init__.py` → `create_film_project`

Add optional parameter `target_runtime_seconds` that overrides intake's estimate.

## What Does NOT Change

- Shot Bible template and Gate A validator — already correct
- Gen Planning template and Gate B validator — fixed in `acf73e4`
- Intake template — already improved in `bad0de2`
- Graph structure — edges unchanged
- Auto-approve profile — unchanged

## Files Affected

| File | Change |
|------|--------|
| `src/film_pipeline/graph/nodes.py` | Move structure extractor to `development_node` |
| `src/film_pipeline/schemas/execution_brief.py` | Add `scene_count` field |
| `src/film_pipeline/graph/orchestrator_validators.py` | Add `validate_scene_count` |
| `src/film_pipeline/agents/prompt_templates/defaults.py` | Update structure extractor, development, screenwriter templates |
| `src/film_pipeline/mcp/tools/__init__.py` | Optional `target_runtime_seconds` parameter |

## Risk: Moving The Extractor Breaks Shot Bible

The structure extractor currently runs in `shot_bible_node` and the shot bible
depends on its output. If we move it earlier, shot_bible must receive the brief
via state (it's already persisted as an artifact, and `_inject_artifact_context`
loads upstream content into prompts). The brief is already loaded:

```python
# In nodes.py _inject_artifact_context:
"execution_brief_ref": ("shot_bible", "execution_brief_content"),
```

This loads from `shot_bible` phase — if we save the brief in `development` phase
instead, this mapping needs updating. **But** the injector tries multiple phases
via `load_phases` in `consistency_check_node`, so it should find it regardless.
Verify during implementation.
