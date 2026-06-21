# Phase 04 — Sheet Manifests

> **Status:** 🟡 Blocked by 03 | **Depends on:** Frame Metadata Sidecars (03)

## Problem

Composite sheets (Character Identity Sheet, Environment Board) are built from
master frames, but the tile layout and frame provenance are not persisted.
There is no machine-readable record of which frame went into which tile position,
making delta regeneration and composite validation harder to audit.

## What to Build

### 1. `CompositeSheetManifest` Schema

New Pydantic model in `src/film_pipeline/schemas/reference.py`:

```python
class TileEntry(SchemaBase):
    tile_name: str           # "front-face", "profile-right", etc.
    frame_reference_id: str  # which ReferenceIndexEntry produced this tile
    frame_path: str          # relative path to the PNG used
    position: tuple[int, int, int, int]  # x, y, w, h in sheet coordinates

class CompositeSheetManifest(SchemaBase):
    sheet_id: str            # subject_id: "leo", "studio"
    sheet_type: str          # "character_identity_sheet", "environment_board"
    sheet_path: str          # relative path to the composite PNG
    dimensions: tuple[int, int]  # e.g. (2048, 2048)
    template_version: str    # "1.0" — increment when layout changes
    tiles: list[TileEntry]
    placeholder_tiles: list[str]  # tile names that rendered as placeholders
    created_at: str
    validation_status: str   # from composite validation
    validation_score: float  # from composite validation
```

### 2. Manifest Writer

Modify `build_character_identity_sheet()` and `build_environment_board()` in
`src/film_pipeline/generation/compositor.py` to build and write the manifest.

Write path: `{sheet_path}.sheet.json` (e.g., `identity-sheet.png.sheet.json`)

### 3. Manifest Reader

Function `read_sheet_manifest(sheet_path: Path) -> CompositeSheetManifest` for
delta regeneration and validation consumers.

### 4. Wire Into Delta Regeneration

Update `regenerate_failing_tiles()` in `delta_regenerator.py` to read the manifest
to find which frame produced a failing tile, instead of doing a linear scan of
all entries.

## Files to Create

- `tests/unit/generation/test_sheet_manifest.py`

## Files to Modify

- `src/film_pipeline/schemas/reference.py` — Add `CompositeSheetManifest`, `TileEntry`
- `src/film_pipeline/generation/compositor.py` — Build and write manifest during sheet construction
- `src/film_pipeline/generation/delta_regenerator.py` — Read manifest for targeted tile replacement
- `src/film_pipeline/generation/__init__.py` — Export new symbols

## Acceptance Criteria

1. `CompositeSheetManifest` schema passes mypy strict + round-trip JSON test
2. Every composite sheet build writes a `.sheet.json` manifest next to the PNG
3. Manifest correctly lists all tiles with their frame reference IDs and positions
4. `placeholder_tiles` lists any tiles that rendered as gray placeholders
5. `regenerate_failing_tiles()` reads the manifest to find tile sources
6. Unit tests for manifest round-trip, placeholder detection, and delta regen integration

## Risks

- **Template drift**: If tile positions change in the compositor but the manifest
  is not updated, manifests become stale. Mitigation: `template_version` field
  and assertion in compositor that layout matches manifest.
- **Delta regen dependency**: Phase 09 (delta regeneration) is already implemented.
  This phase improves it but must not break existing behavior.
