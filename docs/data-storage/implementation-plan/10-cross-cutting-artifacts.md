# Phase 10 — Cross-Cutting Artifacts

> **Status:** 🟢 Ready to start | **Depends on:** —

## Problem

Cross-cutting infrastructure artifacts are schema-only or never consumed:

- `AssetManifest` is written but never read
- `CheckpointMetadata` schema exists, no writer
- `RollbackRecord` schema exists, no writer
- `InvalidationReport` schema exists, no writer

These are not phase-specific — they support the entire pipeline lifecycle.

## What to Build

### Part A: Asset Manifest Consumer

The `AssetManifest` (`projects/{slug}/asset-manifest.json`) is a flat file
listing all binary assets. It's written but nothing reads it.

Add a consumer:
- `get_asset_manifest` MCP tool → returns the manifest
- `validate_asset_integrity` MCP tool → checks all referenced files exist
- Integration with delivery package: `archive_refs` populated from manifest

### Part B: Checkpoint Writer

When a phase gate is approved, write a checkpoint snapshot:

**Content:** Current artifact versions, graph state summary, budget state,
provider health state.

**Storage:** `projects/{slug}/versions/checkpoints/checkpoint_{phase}.v1.json`

**MCP tool:** `create_checkpoint` — called after phase approval

### Part C: Rollback Record Writer

When a rollback is requested, write a record of what changed:

**Content:** From checkpoint → to checkpoint, artifacts invalidated,
reason for rollback.

**Storage:** `projects/{slug}/versions/rollbacks/rollback_{date}.v1.json`

**MCP tool:** `rollback_to_checkpoint` — already exists as stub, wire it

### Part D: Invalidation Report Writer

When an upstream artifact changes (e.g., CharacterBible is re-generated),
compute which downstream artifacts are invalidated:

**Content:** Changed artifact, affected artifacts, severity, required actions.

**Storage:** `projects/{slug}/versions/invalidations/invalidation_{reason}.v1.json`

**Trigger:** Called automatically when a bible or constitution is re-generated.

### Part E: Handoff Record Persistence

Currently handoff records exist only in-memory (graph state). Persist them
to `projects/{slug}/handoff-log.jsonl` for audit trail.

## Files to Create

- `tests/unit/checkpoints/test_checkpoint_writer.py`
- `tests/unit/checkpoints/test_rollback.py`
- `tests/unit/checkpoints/test_invalidation.py`

## Files to Modify

- `src/film_pipeline/checkpoints/manager.py` — Implement checkpoint write
- `src/film_pipeline/checkpoints/rollback.py` — Implement rollback record
- `src/film_pipeline/checkpoints/invalidation.py` — Implement invalidation report
- `src/film_pipeline/mcp/tools/__init__.py` — Add `get_asset_manifest`, `validate_asset_integrity`, `create_checkpoint`
- `src/film_pipeline/mcp/contract.py` — Register new tools

## Acceptance Criteria

1. `get_asset_manifest` returns all binary assets with paths and metadata
2. `validate_asset_integrity` checks all referenced files exist on disk
3. `create_checkpoint` snapshots artifact versions + graph state
4. `rollback_to_checkpoint` writes rollback record and restores state
5. Invalidation report computed when upstream artifact changes
6. Handoff records persisted to JSONL file
7. Unit + integration tests

## Risks

- **Checkpoint size**: Full graph state may be large. Mitigation: store
  artifact version refs (compact) rather than full state dumps.
- **Rollback safety**: Rolling back after generation may leave orphaned
  binary files. Mitigation: soft rollback (keep files, just change refs)
  rather than hard deletion.
- **Invalidation chain**: One change can cascade. Mitigation: compute
  invalidation depth and warn if >3 levels deep.
