# 02 — Ideal Flow: Structural Contract From Day One

## Principle: The Target Runtime Is THE Contract

The `target_runtime_seconds` from intake is not a suggestion. It's the primary
structural invariant. Every phase must produce output that scales to this number.

## Ideal Phase Order

```
intake ──→ constitution ──→ structure_extractor ──→ development ──→ script ──→ ...
  │                          │                        │               │
  │ target_runtime           │ reads target_runtime   │ MUST produce  │ MUST fill N
  │ (the contract)           │ + story type           │ N scenes      │ scenes to
  │                          │ → produces             │               │ target duration
  │                          │   scene_count = f(runtime, pacing)
  │                          │   shot_count = runtime / avg_duration
  │                          │   act_distribution = proportional to runtime
```

## What Changes

### 1. Structure Extractor runs BEFORE development (not at shot_bible)

Currently runs as a pre-step in `shot_bible_node`. Should run as a pre-step in
`development_node` — or even as its own phase between constitution and development.

**Input:** constitution (theme, tone, film_type) + target_runtime_seconds
**Output:** ExecutionBrief with:
- `target_runtime_seconds` (from project_profile, not from story text)
- `scene_count` (derived: runtime / avg_scene_duration_by_pacing)
- `shot_count` (derived: runtime / avg_shot_duration_by_pacing)
- `act_distribution` (proportional to scene distribution)
- `pacing_style` (from film_type)

### 2. Development MUST produce the contract scene count

Template change:
```
Current:  "1-4 min film → 4-8 scenes"
Ideal:    "You MUST produce exactly {scene_count} scenes. This is non-negotiable."
```

Structural validator (Gate 0 — new): checks `len(scene_list.scenes) == required_scene_count`.
If mismatch → blocking issue → repair with feedback: "Expected 15 scenes, got 6."

### 3. Script gets per-scene duration guidance

Template change:
```
Current:  No duration guidance
Ideal:    "Each scene should contribute approximately {avg_scene_duration}s to the
          total {target_runtime}s runtime. With {scene_count} scenes, that's
          ~{target_runtime/scene_count}s per scene. Write enough action and
          dialogue to fill that duration."
```

### 4. Structure extractor reads FROM target, not TO target

Template change:
```
Current:  "Use the EXACT runtime stated in the story."
Ideal:    "The target runtime is {target_runtime_seconds}s. This is fixed. Derive
          all other numbers from it: scene_count = runtime / avg_scene_duration,
          shot_count = runtime / avg_shot_duration."
```

### 5. Shot Bible is already correct

Gate A validator (`validate_shot_structure`) already checks shot count and runtime.
This works because the shot bible template says "produce EXACTLY N shots" and the
validator enforces it. This pattern should be replicated upstream.

## Sizing Formulas

| Pacing | avg_scene_duration | avg_shot_duration | 600s → scenes | 600s → shots |
|--------|-------------------|-------------------|---------------|--------------|
| slow_cinema | 60s | 12.5s | 10 | 48 |
| standard | 45s | 7.5s | 13 | 80 |
| dynamic | 25s | 3.5s | 24 | 171 |

These formulas give the structural contract. Development and shot bible must hit
these numbers. Script must write enough content per scene to justify the duration.

## Validation Gates (proposed)

| Gate | Phase | Checks | Severity |
|------|-------|--------|----------|
| Gate 0 | Development | `scene_count >= required_scene_count` | Blocking |
| Gate 0b | Development | `treatment covers all acts proportionally` | Warning |
| — | Script | `scene content sufficient for duration` | Warning |
| Gate A | Shot Bible | `shot_count matches brief` | Blocking (exists) |
| Gate A | Shot Bible | `sum(durations) ≈ target_runtime` | Blocking (exists) |
| Gate B | Gen Planning | `clip_count > 0, cost > 0` | Blocking (fixed) |

## What About The Runtime Contract Itself?

If intake says 180s but the user wanted 600s, that's still a problem. Fixes:
1. Better intake template (done — concrete sizing ranges)
2. Allow runtime override at project creation time (MCP tool parameter)
3. The structure extractor should emit a warning if target_runtime seems wrong for
   the story complexity (e.g., "Story describes 5 locations and character arc but
   target runtime is only 180s")
