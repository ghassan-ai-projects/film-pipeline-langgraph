# Phase 4 — Identity & Geometry Consistency (Seed Lock + I2I)

**Status:** Not started
**Depends on:** Phase 3 (Gemini review needed for drift detection)
**Blocks:** Phase 5 (retry needs consistency state), Phase 7 (compositor needs consistent frames)

---

## Goal

When generating multiple frames for the same character or environment, enforce visual consistency so all frames show the same person or the same location.

## Why

Independent generation of each frame produces a different face/room every time. The composite sheet shows 5 different people in 5 different rooms — useless as a production reference.

## Mechanism 1 — Seed Locking (Primary, $0)

- Imagen 4 supports a `seed` parameter. Same seed + same prompt prefix = same identity.
- Generate the anchor frame first with a fixed seed.
- All subsequent frames for the same subject use the same seed.

## Mechanism 2 — Image-to-Image Fallback (When Seed Drifts)

- Triggered when Gemini review (Phase 3) detects drift: `scores.subject < 7/10`
- I2I uses the anchor frame as reference image with strength 0.3–0.5
- Strength 0.5: looser identity, allows more variation — default starting point
- Strength 0.3: strong identity lock, limits angle/expression freedom
- Each subsequent frame passes the anchor as `reference_images=[anchor_path]`

## Generation Order

### Per Character

```
1. Generate front face (anchor) — no reference, seed=X
2. Validate anchor (heuristics + Gemini)
3. If anchor fails → retry (max 2, Phase 5)
4. If anchor passes → lock seed=X and anchor_path
5. Generate 3/4 left  — same seed=X, I2I from anchor if drift detected
6. Generate profile   — same seed=X, I2I from anchor if drift detected
7. Generate full body — same seed=X, I2I from anchor if drift detected
8. Generate expressions — same seed=X, I2I from anchor if drift detected
9. Validate each subsequent frame (heuristics + Gemini)
10. Retry any failing frames (Phase 5)
```

### Per Environment

```
1. Generate wide establishing (anchor) — no reference, seed=Y
2. Validate anchor (heuristics)
3. If anchor fails → retry (max 2)
4. If anchor passes → lock seed=Y and anchor_path
5. Generate alt angles     — same seed=Y, I2I from anchor if geometry drift detected
6. Generate lighting variants — same seed=Y, I2I from anchor
7. Generate detail insets  — same seed=Y (less critical for identity)
```

## Seed Drift Detection

### Character Drift

- After generating a subsequent frame, run Gemini per-frame review (Phase 3)
- If `scores.subject < 7/10` with feedback like "different face" or "identity inconsistent" → drift
- On first drift: retry with same seed (provider jitter)
- On second drift: switch to I2I with strength 0.5
- On third drift with I2I: switch to I2I with strength 0.3 (strong lock)
- If still drifting: accept best attempt, tag `identity_unclear`, flag human review

### Environment Drift

- After generating an alternate angle, run Gemini review (Phase 3)
- If `scores.subject < 7/10` or feedback mentions "different room", "geometry changed", "new furniture" → drift
- Same retry escalation as character drift
- If still drifting: accept best attempt, tag `geometry_unclear`, flag human review

## Identity State (Per Subject Group)

```python
identity_state = {
    "anchor_frame_path": Path,
    "anchor_seed": int,
    "i2i_active": bool,
    "i2i_strength": float,       # 0.3–0.5
}
```

## Files

| File | Action |
|------|--------|
| `mcp/tools/__init__.py` | Group entries by subject_id, generate anchor first, pass seed + reference_images to provider |
| `providers/adapters/imagen4_gemini.py` | Verify `build_payload()` accepts `seed` and `reference_images` params |
| `providers/base.py` | Verify `build_payload()` signature supports seed + reference_images |
| `generation/frame_reviewer.py` | Detect seed drift from Gemini review scores |

## Effort

~100 lines. Mostly in `generate_reference_images` loop restructuring.

## Tests

| Type | What |
|------|------|
| Unit | Character entries grouped by subject_id, anchor generated first |
| Unit | Seed passed to provider for subsequent frames |
| Unit | I2I fallback activated when drift detected |
| Unit | Drift detection: subject score < 7 → flag, retry with same seed → switch to I2I |
| Unit | Environment entries: anchor (wide establishing) generated first, same seed for alt angles |
