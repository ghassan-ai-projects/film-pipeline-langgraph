# Phase 1 — Auto-Heuristic Checks (Per-Frame Validation Stage 1)

**Status:** Not started  
**Depends on:** Nothing  
**Blocks:** Phase 3 (Gemini review runs after heuristics pass)  

---

## Goal

Before accepting a generated image, run 5 free checks that catch ~80% of obvious failures.

## Why

The legacy spec catches broken/corrupt/blank images at $0 cost before any Gemini review. Without this, we accept garbage from the provider and call it "validated."

## Checks

| # | Check | Method | Fail If |
|---|-------|--------|---------|
| 1 | File exists | `Path.stat().st_size` | 0 bytes |
| 2 | Min resolution | `PIL.Image.open().size` | < 512×512 |
| 3 | Not corrupt | `PIL.Image.open()` + `.verify()` | Can't open / corrupt |
| 4 | Has content | Color variance (std dev across pixels) | Solid color / all black / all white |
| 5 | Face present | `PIL.Image.open()` — face width >10% of frame | No detectable face (character frames only) |

## Implementation

- Check 5 (face detection) is optional for non-character frames — gated on `subject_type == "character"`
- Failed heuristics → mark entry `generation_status = "failed"`, add issue to `entry["issues"]`, skip Gemini review
- Passed heuristics → proceed to Gemini review (Phase 3)

## Files

| File | Action |
|------|--------|
| **NEW** `generation/frame_heuristics.py` | `run_heuristic_checks(image_path: Path, subject_type: str) -> HeuristicResult` |
| `mcp/tools/__init__.py` | Call `run_heuristic_checks()` after download, before accepting |

## Dependencies

`Pillow` — verify in `pyproject.toml`.

## Effort

~60 lines. One new file + ~15 lines in tools.

## Tests

| Type | What |
|------|------|
| Unit | Each heuristic check with valid + invalid images (test fixtures — use 128×128 synthetic PNGs) |
