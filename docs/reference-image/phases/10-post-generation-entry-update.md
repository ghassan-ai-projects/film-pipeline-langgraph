# Phase 10 — Post-Generation Entry Update

**Status:** Not started  
**Depends on:** Phase 1–9 (all previous phases must have run)  
**Blocks:** Phase 11 (index persistence needs final entry data)  

---

## Goal

Ensure every generated entry has correct metadata after generation completes — no fake values.

## Why

Currently `generate_reference_images` sets fields inline with hardcoded values (`quality_score=85`, `locked=True`, `validation status=approved`) even when no validation ran. After Phases 1–9, these must reflect actual results.

## Fields Updated

```python
entry["asset_path"] = relative path to generated file
entry["provider"] = provider_id
entry["source_frames"] = [relative paths to all generated frames for this entry]
entry["generation_status"] = "validated" | "needs_regeneration" | "failed"
entry["quality_score"] = gemini_score                  # or heuristic fallback
entry["locked"] = (generation_status == "validated")
entry["validation"] = {"status": ..., "score": ..., "reports": [...]}
entry["ai_usability"] = {"score": ..., "risks": [...], "notes": ""}
entry["issues"] = list of issue dicts from heuristics + Gemini
entry["retry_count"] = number of attempts
entry["best_score"] = best Gemini score across attempts
entry["delta_iterations"] = number of delta regeneration attempts (if applicable)
```

## Non-Generated Entries

If the VisualDevAgent created entries that never got generated (e.g., `generation_status = "planned"`), leave them as-is. Only update entries that went through the generation pipeline.

## Files

| File | Action |
|------|--------|
| `mcp/tools/__init__.py` | Update entry dict with real values after generation completes |

## Effort

~20 lines. One file.

## Tests

| Type | What |
|------|------|
| Unit | Entry fields reflect actual validation results, not hardcoded defaults |
