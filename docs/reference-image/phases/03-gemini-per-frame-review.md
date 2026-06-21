# Phase 3 — Gemini Per-Frame AI Review (Per-Frame Validation Stage 2)

**Status:** Not started  
**Depends on:** Phase 1 (heuristics) + Phase 2 (structured prompts)  
**Blocks:** Phase 4 (drift detection needs Gemini scores), Phase 5 (retry needs review results)  

---

## Goal

For frames that pass heuristics, run a Gemini Flash review against the legacy rubric.

## Why

Heuristics catch technical failures. Gemini catches semantic failures — wrong expression, missing subject, artifacts the human eye would see. ~$0.001/frame.

## Rubric (40 pts, threshold ≥28/70%)

| Domain | Max | Checks |
|--------|-----|--------|
| Subject Present | 10 | Expected subject visible? Face/character clear? |
| Prompt Match | 10 | Expression, position, lighting match prompt? |
| Artifact Freedom | 10 | No deformities, merges, extra anatomy? |
| Technical Quality | 10 | Sharp focus, proper exposure, clean quality? |

## Selective Validation (Save Cost)

| Frame Type | Gemini Review |
|-----------|---------------|
| Environment wide shots | ❌ Skip |
| Environment lighting variants | ❌ Skip |
| Character front face | ✅ Always |
| Character alt angles | ✅ Spot-check 30% |
| Character expressions | ✅ First 3, then spot-check |
| Detail insets | ❌ Skip |
| Scale reference | ✅ Once |
| Prop views | ✅ Once |

## Gemini Prompt Template

```
You are validating an AI-generated reference image for film production.
The image should show: {prompt_text}.

Score against this rubric (40 pts):
1. SUBJECT (10 pts): Is the expected subject visible? Face/character clear?
2. PROMPT MATCH (10 pts): Does expression/position/lighting match prompt?
3. ARTIFACTS (10 pts): Any deformities, merges, extra anatomy, corruption?
4. TECHNICAL (10 pts): Sharp focus, proper exposure, clean quality?

Threshold: 28/40 (70%).

Return JSON:
{
  "frame_id": "",
  "scores": {
    "subject": {"score": 0, "max": 10, "notes": ""},
    "prompt_match": {"score": 0, "max": 10, "notes": ""},
    "artifacts": {"score": 0, "max": 10, "notes": ""},
    "technical": {"score": 0, "max": 10, "notes": ""}
  },
  "total": 0,
  "passed": false,
  "actionable_feedback": ""
}
```

## Decision Flow

- Pass (≥28) → `generation_status = "validated"`, record scores
- Fail → `generation_status = "needs_regeneration"`, store `actionable_feedback`, retry (Phase 5)

## Files

| File | Action |
|------|--------|
| **NEW** `generation/frame_reviewer.py` | `review_frame(image_path, prompt_text, subject_type) -> FrameReviewResult` |
| `mcp/tools/__init__.py` | Call `review_frame()` after heuristics pass |

## Effort

~120 lines. One new file + ~20 lines in tools.

## Tests

| Type | What |
|------|------|
| Unit | `review_frame()` parses Gemini JSON response correctly |
| Unit | Handles Gemini error responses gracefully |
| Unit | Selective validation: correct skip/always/spot-check decisions |
