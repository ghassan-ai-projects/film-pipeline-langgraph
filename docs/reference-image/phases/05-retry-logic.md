# Phase 5 — Retry Logic

**Status:** Not started  
**Depends on:** Phase 3 (Gemini review) + Phase 4 (identity/geometry consistency state)  
**Blocks:** Phase 7 (compositor needs finalized frames)  

---

## Goal

On validation failure, retry up to 2 times with specific fixes, then use best attempt. Never block the pipeline.

## Why

The legacy spec rule: "max 2 retries per frame, best attempt used after that, flagged for human review. Never block the pipeline."

## Retry Loop

```
for attempt in 1..3:
    generate frame
    run heuristics (Phase 1)
    if heuristics fail → retry with same prompt (provider glitch)
    run Gemini review (Phase 3)
    if score >= 28 → accept, break
    if attempt < 3 → regenerate with actionable_feedback injected into prompt
    if attempt == 3 → accept best attempt across all attempts, mark human_review_required
```

## Identity-Aware Retry

When retrying subsequent frames (not the anchor):
- Retry 1: same seed, same prompt (provider jitter)
- Retry 2: same seed + I2I from anchor with strength 0.5
- Retry 3: same seed + I2I from anchor with strength 0.3 (strong lock)

## Data Tracked Per Entry

```python
entry["retry_count"] = int       # number of attempts
entry["best_score"] = float      # best Gemini score across attempts
entry["best_attempt"] = int      # which attempt had the best score
```

## Fail-Safe

- After 3 attempts, accept the attempt with the highest Gemini score
- Flag `human_review_required` in validation status
- Never block — the pipeline continues with whatever we have

## Files

| File | Action |
|------|--------|
| `schemas/reference.py` | Add `retry_count`, `best_score`, `best_attempt` to `ReferenceIndexEntry` |
| `mcp/tools/__init__.py` | Wrap generation in retry loop |

## Effort

~50 lines. Schema change + loop in tools.

## Tests

| Type | What |
|------|------|
| Unit | Retry loop terminates after max 2 retries |
| Unit | Best score selected from all attempts |
| Unit | Identity-aware retry: subsequent frame retries use same seed + I2I from anchor |
| Unit | After 3 failures, best attempt accepted with human_review_required flag |
