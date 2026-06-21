# Phase 8 — Composite Validation (Sheet-Level Rubrics)

**Status:** Not started
**Depends on:** Phase 7 (composite sheets exist) + Phase 7b (environment boards exist)
**Blocks:** Phase 9 (delta regeneration needs failing tiles), Phase 10 (entry update needs final status)

---

## Goal

After building a composite sheet, run a Gemini review of the *complete sheet* against domain-specific rubrics. This is distinct from per-frame validation (Phase 3) — it evaluates the assembled product, not individual frames.

## Why

Per-frame validation catches bad frames. Composite validation catches bad *sheets* — identity drift across tiles, composition problems, contradictory features. Sheets passing per-frame checks can still fail as a unit.

## Rubrics

### Character Identity Sheet (50 pts, threshold ≥40/80%)

| Domain | Max | Checks |
|--------|-----|--------|
| Identity Accuracy | 15 | Same person across all tiles? Age matches? Features consistent? |
| Expression Fidelity | 10 | Each expression matches its label? No ambiguity? Range useful for story? |
| Composition Quality | 10 | Visual hierarchy clear? Largest tile = most important anchor? Labels in margins? |
| Technical Quality | 10 | No artifacts? Consistent lighting across tiles? Color-matched? Clean edges? |
| Usability as Reference | 5 | Would this stabilize generation across 60+ shots? |

### Environment Board (50 pts, threshold ≥40/80%)

| Domain | Max | Checks |
|--------|-----|--------|
| Spatial Consistency | 15 | Same geometry across angles? No new walls/furniture? Layout coherent? |
| Lighting Accuracy | 10 | Lighting matches target? Consistent direction? Shadows believable? |
| Mood Encoding | 10 | Mood matches scene description? Palette consistent? |
| Technical Quality | 10 | No artifacts? Clean composites? Consistent exposure? |
| Usability as Reference | 5 | Would this stabilize environment across shots? |

### Scale Sheet (20 pts, threshold ≥16/80%)

| Domain | Max | Checks |
|--------|-----|--------|
| Relative Proportion | 10 | Characters correctly scaled relative to each other? |
| Context Clarity | 5 | Scale reference bar clear and usable? Increments legible? |
| Technical Quality | 5 | Consistent perspective across all characters? |

### Style & Color Board (30 pts, threshold ≥24/80%)

| Domain | Max | Checks |
|--------|-----|--------|
| Palette Clarity | 10 | Palette swatches clear? Hex codes included? |
| Mood Encoding | 10 | Visual mood matches film constitution? |
| Technical Quality | 5 | Clean layout? No artifacts? |
| Usability | 5 | Usable as prompt anchor? Not over-constraining? |

### Prop Sheet (30 pts, threshold ≥24/80%)

| Domain | Max | Checks |
|--------|-----|--------|
| Object Clarity | 10 | Silhouette clear? Material readable? |
| Scale Reference | 10 | In-hand view gives scale? Isolated view shows detail? |
| State Coverage | 5 | Changed states covered if story-relevant? |
| Technical Quality | 5 | Clean renders? No artifacts? |

### Camera Reference Board (30 pts, threshold ≥24/80%)

| Domain | Max | Checks |
|--------|-----|--------|
| Composition Clarity | 10 | Close-up style readable? Wide-shot composition clear? |
| Movement Mood | 10 | Camera movement intent visible? Lens feeling conveyed? |
| Usability | 10 | Would this stabilize camera grammar? Not over-constraining? |

## Gemini Prompt Template

```
You are validating an AI-generated reference sheet for film production.
Sheet type: {sheet_type}
Subject: {subject_id}
Prompt used: {prompt_text}

Score against this rubric:
{rubric_domains}

Threshold: {threshold}

Return JSON:
{
  "sheet_id": "",
  "sheet_type": "",
  "scores": {
    "{domain}": {"score": 0, "max": N, "notes": ""}
  },
  "total": 0,
  "passed": false,
  "actionable_feedback": "",
  "failing_tiles": [],
  "bad_reference_tags": []
}
```

## Validation Statuses

| Status | Meaning | Action |
|--------|---------|--------|
| `approved` | ≥ threshold, no concerns | Lock sheet, register in index |
| `approved_with_notes` | ≥ threshold, minor concerns | Lock sheet, include notes in prompt assembly |
| `needs_delta_fix` | Failed, specific tiles identified | Regenerate only failing tiles (Phase 9) |
| `needs_regeneration` | Failed, no clear tile-level fix | Regenerate entire sheet |
| `human_review_required` | Model uncertain, creative tradeoff | Flag for operator review |
| `rejected` | Harmful or unusable | Do not use |

## Bad Reference Tags

| Tag | Meaning |
|-----|---------|
| `too_noisy` | Too many competing subjects |
| `identity_unclear` | Inconsistent face across tiles |
| `geometry_unclear` | Cluttered environment, confused layout |
| `style_conflict` | Strong mismatch with desired output style |
| `moderation_risk` | Contains elements likely to trigger provider filter |
| `low_resolution` | Too small for generation model to read |
| `text_bleed_risk` | Labels encroach on tile content |
| `contradictory` | Conflicting signals (e.g., two different palettes) |

## Selective Composite Validation (Save Cost)

| Sheet Type | Validate |
|-----------|----------|
| Character identity sheets | ✅ Always |
| Environment boards | ✅ Always (recurring) / Skip (one-off) |
| Scale sheets | ✅ Once |
| Style boards | ✅ Once |
| Prop sheets | ✅ Spot-check 50% |
| Camera boards | ✅ Once |

## Multi-Model Review (Critical Anchors Only — Future Enhancement)

- Main character identity sheets → 2+ different models review
- Consensus report preserves disagreements

## Files

| File | Action |
|------|--------|
| **NEW** `generation/sheet_reviewer.py` | `review_composite_sheet(sheet_path, sheet_type, subject_id, prompt_text) -> SheetReviewResult` |
| `generation/compositor.py` | Trigger composite validation after build |
| `mcp/tools/__init__.py` | Wire composite validation into generation flow |

## Effort

~180 lines. One new file + ~30 lines across 2 files.

## Tests

| Type | What |
|------|------|
| Unit | `review_composite_sheet()` parses Gemini composite response for each sheet type |
| Unit | Each rubric scores correctly at threshold boundaries |
| Unit | Validation status assigned correctly from score vs threshold |
| Unit | Bad reference tags parsed from Gemini response |
