# Phase 9 — Delta Regeneration

**Status:** Not started  
**Depends on:** Phase 8 (composite validation returns failing_tiles)  
**Blocks:** Phase 10 (entry update needs final state after delta fix)  

---

## Goal

When composite validation fails with specific tile-level issues, regenerate only the failing tiles instead of the entire sheet.

## Why

The legacy spec found 30–40% cost reduction by replacing specific tiles instead of regenerating entire batches. If the front face is good but the profile angle shows a different person, you regenerate the profile — not all 12 frames.

## Trigger

Composite validation (Phase 8) returns `status = "needs_delta_fix"` with `failing_tiles`:

```json
{
  "status": "needs_delta_fix",
  "failing_tiles": ["profile-right", "expression-tired"],
  "actionable_feedback": "Profile angle shows different jaw structure. Tired expression reads as angry."
}
```

## Logic

```
1. Parse composite validation report for failing_tiles list
2. For each failing tile:
   a. Look up the source frame in master-frames/
   b. Regenerate that frame with corrected prompt (actionable_feedback injected)
   c. Use same seed + I2I from anchor (identity consistency, Phase 4)
   d. Run per-frame heuristics + Gemini review on regenerated frame
   e. Retry up to 2 times (Phase 5)
3. Rebuild composite sheet with new tiles (Phase 7/7b)
4. Re-run composite validation (Phase 8)
5. Max 3 delta iterations per sheet
6. After 3 iterations, best composite score wins — no blocking
7. Log: "{sheet_name}: best={score}/{max} after {n} delta iterations"
```

## Delta State (Per Sheet)

```python
delta_state = {
    "delta_iteration": int,              # 1–3
    "best_composite_score": float,
    "best_iteration": int,
    "failing_tiles_history": list[list[str]],  # per-iteration
}
```

## Partial Rebuild

`compositor.replace_tile(sheet_path, tile_name, new_frame_path)` swaps a single tile in the composite without rebuilding all tiles. The composite sheet is reloaded from disk, the specified tile region is replaced, and the sheet is re-saved.

## Files

| File | Action |
|------|--------|
| **NEW** `generation/delta_regenerator.py` | `regenerate_failing_tiles(sheet_review, entry_index, project_root) -> list[Path]` |
| `generation/compositor.py` | Expose `replace_tile()` for partial rebuild |
| `mcp/tools/__init__.py` | Wire delta loop after composite validation |

## Effort

~120 lines. One new file + ~30 lines across 2 files.

## Tests

| Type | What |
|------|------|
| Unit | Delta regenerator parses failing_tiles from composite review |
| Unit | Only listed tiles regenerated (others untouched) |
| Unit | Max 3 delta iterations enforced |
| Unit | Best score tracked and selected across iterations |
| Unit | `replace_tile()` swaps a single tile in composite sheet |
