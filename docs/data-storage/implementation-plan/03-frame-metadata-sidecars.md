# Phase 03 — Frame Metadata Sidecars

> **Status:** 🟡 Blocked by 00, 01 | **Depends on:** CharacterBible writer (00), EnvironmentBible writer (01)

## Problem

Individual generated frames (PNGs in `master-frames/`) have no metadata sidecar.
There is no record of which provider, model, seed, prompt, tier, validation score,
or retry count produced each frame. This data lives only in the in-memory entry
dict and the reference index artifact — not next to the binary file.

## What to Build

### 1. `ReferenceFrame` Schema

New Pydantic model in `src/film_pipeline/schemas/reference.py`:

```python
class ReferenceFrame(SchemaBase):
    frame_path: str          # relative to project root
    reference_id: str        # e.g. "char-leo-front-face"
    subject_type: str
    subject_id: str
    provider_id: str
    model_id: str
    tier: str                # fast / standard / ultra
    seed: int | None
    prompt_text: str
    frame_role: str
    expression: str | None
    lighting: str | None
    aspect_ratio: str
    generation_status: str   # validated / generated / failed / needs_regeneration
    quality_score: float     # 0-100
    retry_count: int
    best_score: float        # raw Gemini score (0-40)
    heuristic_checks_passed: bool
    mime_type: str
    created_at: str          # ISO-8601
```

### 2. Sidecar Writer

Function `write_frame_sidecar(frame_path: Path, metadata: ReferenceFrame) -> Path`
that writes `{frame_path}.meta.json` next to each PNG.

Called at the end of the per-frame generation loop in `generate_reference_images`,
after all metadata fields are populated.

### 3. Sidecar Reader

Function `read_frame_sidecar(frame_path: Path) -> ReferenceFrame` for downstream
consumers (compositor, validation, delivery).

### 4. Wire Into Generation Loop

In `src/film_pipeline/mcp/tools/__init__.py`, after the per-frame loop sets
`raw["asset_path"]`, `raw["quality_score"]`, `raw["validation"]`, etc., call
`write_frame_sidecar()`.

## Files to Create

- `tests/unit/generation/test_frame_sidecar.py`

## Files to Modify

- `src/film_pipeline/schemas/reference.py` — Add `ReferenceFrame` schema
- `src/film_pipeline/generation/__init__.py` — Export `write_frame_sidecar`, `read_frame_sidecar`
- `src/film_pipeline/generation/frame_sidecar.py` — New module for sidecar I/O
- `src/film_pipeline/mcp/tools/__init__.py` — Call `write_frame_sidecar()` after frame generation

## Acceptance Criteria

1. `ReferenceFrame` schema passes mypy strict + round-trip JSON test
2. After `generate_reference_images`, every `{frame}.png` has a `{frame}.png.meta.json` sidecar
3. Sidecar contains all fields populated from the generation loop
4. `read_frame_sidecar()` correctly reconstructs `ReferenceFrame` from disk
5. Missing/corrupt sidecar raises a specific exception (not silent None)
6. Unit tests for write → round-trip → read

## Risks

- **Sidecar drift**: If the generation loop mutates the entry dict after writing
  the sidecar, the sidecar will have stale data. Mitigation: write sidecar last
  in the per-frame block, after all mutations.
- **Storage overhead**: ~500 bytes per frame. Negligible for 50-100 frames.
- **Schema evolution**: Adding fields to `ReferenceFrame` later means old sidecars
  lack new fields. Mitigation: make all fields optional with defaults so old
  sidecars remain readable.
