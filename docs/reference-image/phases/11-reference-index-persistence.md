# Phase 11 — Reference Index Persistence

**Status:** Not started  
**Depends on:** Phase 10 (entry data must be finalized)  
**Blocks:** Nothing (final phase)  

---

## Goal

Save the updated reference index after generation and make it queryable.

## Why

Already partially done (`_save_reference_index_artifact` exists in the artifact store), but also needs human-readable files on disk and richer query responses.

## Deliverables

### 1. Artifact Store Save

Save updated ReferenceIndex to artifact store (existing `_save_reference_index_artifact` function). This is the canonical machine-readable source.

### 2. Human-Readable Index Files

Write two files to `references/index/`:

**`reference-index.json`** — full reference index with all entries and their final state:
```json
{
  "project_id": "...",
  "generated_at": "2026-06-21T12:00:00Z",
  "entries": [
    {
      "reference_id": "ref:char:leo:identity:v1",
      "asset_type": "character_identity_sheet",
      "subject_id": "leo",
      "asset_path": "references/characters/leo/identity-sheet.png",
      "provider": "gemini-imagen-4",
      "validation": {"status": "approved", "score": 85},
      "locked": true
    }
  ]
}
```

**`reference-validation-summary.json`** — aggregate summary:
```json
{
  "project_id": "...",
  "total_entries": 15,
  "generated": 12,
  "validated": 10,
  "failed": 2,
  "average_score": 82.3,
  "by_type": {
    "character_identity_sheet": {"count": 3, "average_score": 84.0},
    "environment_board": {"count": 2, "average_score": 80.5}
  }
}
```

### 3. Enriched `inspect_reference` Response

Update the MCP tool to return frame paths, validation scores, issues, and bad reference tags:

```json
{
  "reference_id": "ref:char:leo:identity:v1",
  "asset_path": "references/characters/leo/identity-sheet.png",
  "frames": ["master-frames/ref-001-front.png", "master-frames/ref-001-3-4-l.png"],
  "validation": {"status": "approved", "score": 85},
  "ai_usability": {"score": 86, "risks": []},
  "issues": [],
  "locked": true
}
```

## Files

| File | Action |
|------|--------|
| `mcp/tools/__init__.py` | Write index JSON files to `project_root/references/index/` after generation |
| `mcp/tools/__init__.py` | Enrich `inspect_reference()` response with frame details |

## Effort

~30 lines. Two functions in tools.

## Tests

| Type | What |
|------|------|
| Integration | After `generate_reference_images`, `references/index/reference-index.json` exists and is valid |
| Integration | `inspect_reference` returns frame paths and validation scores |
