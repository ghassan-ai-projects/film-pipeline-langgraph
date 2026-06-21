# Implementation Plan Review — Gaps & Risks

> **Date:** 2026-06-21
> **Plan reviewed:** `docs/reference-image/implementation-plan.md` (12 phases, 0–11)

---

## Summary

The plan covers the core character pipeline well (structured prompts → heuristics → Gemini review → identity consistency → retry → compositor → composite validation → delta regeneration). But it has seven gaps — three are pre-requisites (no CharacterBible producer, no environment compositor, no environment identity locking), two are integration gaps (graph wiring, cost tracking), and two are scope gaps (multi-model review, prompt block locking).

---

## Gap 1 — No CharacterBible Agent (Pre-requisite)

**Severity:** Blocker for Phase 2

Phase 2 depends on `CharacterBible.identity_block` — the locked descriptive block used in prompts. But nothing in the pipeline creates CharacterBibles.

**Current flow:** intake → constitution → development → script → visual_dev → shot_bible → gen_planning → generation → qc → post → delivery

There is no `character_bible` phase. The `CharacterBible` schema exists (`schemas/character.py`) but no agent produces it.

**Fix:** Either:
- Add a character bible agent that runs between constitution and visual_dev, OR
- Have the VisualDevAgent produce CharacterBible entries alongside the ReferenceIndex (since it already has script + constitution context), OR
- Make Phase 2's fallback chain robust enough to work without CharacterBible (use constitution.character_truths + script prose)

The last option is the pragmatic short-term fix. The structured prompt builder should work with or without CharacterBible.

---

## Gap 2 — No Environment Compositor Template

**Severity:** Major scope gap

Phase 7 only builds the Character Identity Sheet template. The legacy spec defines 7 reference types:

| Type | In Plan? |
|------|----------|
| Character Identity Sheet | ✅ Phase 7 |
| Costume & State Sheet | ❌ |
| Environment Board | ❌ |
| Prop & Object Sheet | ❌ |
| Scale Sheet | ❌ |
| Style & Color Board | ❌ |
| Camera Reference Board | ❌ |

Environment Board is the second most important reference type after Character Identity Sheet. Without it, environment consistency across shots has no anchor.

**Fix:** Add Phase 7b — Environment Board compositor (same architecture as Character Identity Sheet, different template). Can follow Phase 7 implementation pattern.

---

## Gap 3 — No Environment Identity/Geometry Locking

**Severity:** Major scope gap

Phase 4 solves character identity consistency (seed lock + I2I from anchor frame). Environments have the same problem — if you generate "wide establishing" and "alt angle desk" independently, you get different rooms.

The legacy spec handles this the same way: seed locking for same-geometry frames, but the plan doesn't mention environments in Phase 4.

**Fix:** Extend Phase 4 to cover environment geometry consistency. Same mechanism (seed + I2I from wide establishing anchor), same drift detection (Gemini review scoring low on "Spatial Consistency"), but the `ENV_REINFORCE` block drives it instead of `ID_REINFORCE`.

---

## Gap 4 — No Prompt Block Version Locking

**Severity:** Medium (deferrable)

The legacy spec Phase 1 requires prompt blocks to be version-locked before generation starts.
If `CHAR_DESC` changes mid-phase, ALL previously generated frames are invalidated.

The plan builds structured prompts (Phase 2) but doesn't version-lock the blocks. A change to `CharacterBible.identity_block` or `FilmConstitution.visual_language` would silently invalidate all generated frames with no detection.

**Fix:** Add a hash of each block source to the `ReferenceIndexEntry` (e.g., `prompt_block_hash: str`). On re-generation with `force=False`, compare hashes — if changed, invalidate and regenerate. This is a small addition (~20 lines) that can be deferred to post-MVP.

---

## Gap 5 — Graph generation_node Is Still a No-Op

**Severity:** Medium (integration gap)

```python
def generation_node(state):
    new_state = deepcopy(state)
    new_state["current_phase"] = "generation"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    return new_state
```

The entire reference image pipeline runs through the `generate_reference_images` MCP tool, bypassing the LangGraph state machine. This means:
- No checkpointing during reference generation
- No graph-based retry or recovery
- Human approval gates don't apply
- The `generation_node` flag-only design means the graph thinks "generation" is a video phase

**Fix:** Either wire `generate_reference_images` into `generation_node` (so the graph orchestrates reference generation), or create a separate `reference_generation_node` that the graph routes to for image-only generation. This is not urgent — the MCP path works — but should be addressed before claiming operator-readiness.

---

## Gap 6 — No Cost Tracking Integration

**Severity:** Low (nice-to-have)

The plan generates images through Imagen 4 ($0.02–0.10/image) and runs Gemini reviews (~$0.001/frame) but never tracks or reports actual cost. The `GenerationLedger` exists but is video-centric (shot_id, duration). The legacy spec has a $10 budget ceiling.

**Fix:** Add a lightweight cost counter in `generate_reference_images` that:
- Tracks images generated × provider tier cost
- Tracks Gemini review calls × $0.001
- Logs total at end: `"Reference generation complete: 15 images, $0.85 total"`
- Optionally updates a reference-specific ledger row

Deferrable. The cost is low enough ($2–5 per full reference set) that manual tracking is fine for now.

---

## Gap 7 — Multi-Model Review Not Detailed

**Severity:** Low (scope gap)

Phase 8 mentions multi-model review for critical anchors but doesn't specify:
- Which models (Gemini Flash + ?)
- How consensus is computed
- How disagreements are preserved vs squashed
- What "critical anchor" means (main character only? recurring environments?)

**Fix:** Defer to post-MVP. Single-model Gemini Flash review (Phase 3 + Phase 8) is sufficient for 90% of cases. Multi-model review is a quality enhancement, not a launch requirement.

---

## Gap Summary

| # | Gap | Severity | Action |
|---|-----|----------|--------|
| 1 | No CharacterBible producer | Blocker | Make Phase 2 fallback work without it |
| 2 | No Environment compositor | Major | Add Phase 7b after Phase 7 |
| 3 | No environment geometry locking | Major | Extend Phase 4 to environments |
| 4 | No prompt block version locking | Medium | Add hash field, defer implementation |
| 5 | Graph generation_node no-op | Medium | Defer, MCP path works |
| 6 | No cost tracking | Low | Defer, add counter later |
| 7 | Multi-model review not detailed | Low | Defer to post-MVP |

---

## Revised Phase Order (After Gap Fixes)

| Phase | Name | Changes from current plan |
|-------|------|--------------------------|
| 0 | Organize Output Directories | No change |
| 1 | Auto-Heuristic Checks | No change |
| 2 | Structured Prompt Construction | Make CharacterBible fallback robust (Gap 1 fix) |
| 3 | Per-Frame Gemini Review | No change |
| 4 | Identity & Geometry Consistency | Extend to environments (Gap 3 fix) |
| 5 | Retry Logic | No change |
| 6 | Provider Tier Routing | No change |
| 7 | Character Identity Sheet Compositor | No change |
| 7b | Environment Board Compositor | **NEW** (Gap 2 fix) |
| 8 | Composite Validation | No change |
| 9 | Delta Regeneration | No change |
| 10 | Post-Generation Entry Update | No change |
| 11 | Reference Index Persistence | No change |

---

## What The Plan Gets Right

1. **Structured prompts from domain data** — Phase 2 fixes the root cause of bad reference images (vague prompts). Using `CharacterBible.identity_block` + block assembly is the correct architecture.

2. **Two-tier validation** — Free heuristics catch 80% of failures at $0, Gemini catches the semantic 20% at ~$0.001/frame. Correct cost/quality tradeoff.

3. **Identity consistency before compositing** — Seed lock + I2I fallback (Phase 4) before building sheets (Phase 7) is the correct ordering. You can't composite inconsistent frames into a useful sheet.

4. **Delta regeneration** — Tile-level fixes instead of full batch regeneration saves 30–40% cost. Correct optimization.

5. **80% thresholds everywhere** — Character sheets, environment boards, scale sheets all use ≥80% pass. Prevents infinite iteration loops.

6. **Never block the pipeline** — Best attempt after max retries, human review flag. Correct failure mode.

7. **Image-only** — No video generation, no duration, no clips. The plan stays in its lane.
