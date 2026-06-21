# Data Storage Implementation Plan — README

> **Goal:** Close every gap in the artifact map so the pipeline produces all
> documented artifacts through the correct storage methods.
>
> **Source:** `docs/data-storage/artifact-map.md` (verified against code 2026-06-21)
>
> **Status legend per phase:**
> - ✅ Complete
> - 🟢 Ready to start (dependencies met)
> - 🟡 Blocked (waiting on dependency)
> - ⬜ Not started

---

## Dependency Graph

```
00-character-bible ─────┐
01-environment-bible ───┼──→ 05-additional-composites
02-camera-style-bibles ─┘

00 + 01 ──→ 03-frame-sidecars ──→ 04-sheet-manifests

(independent)
06-shot-bible-writers ──→ 07-generation-plan-budget ──→ 08-qc-validation
                                                             │
09-post-delivery ←───────────────────────────────────────────┘

10-cross-cutting (independent, can start anytime)
```

---

## Phase Summary

| # | Phase | File | Depends On | Status |
|---|-------|------|-----------|--------|
| 00 | CharacterBible Writer | `00-character-bible-writer.md` | — | 🟢 |
| 01 | EnvironmentBible Writer | `01-environment-bible-writer.md` | — | 🟢 |
| 02 | Camera + Style Bible Writers | `02-camera-and-style-bibles.md` | — | 🟢 |
| 03 | Frame Metadata Sidecars | `03-frame-metadata-sidecars.md` | 00, 01 | 🟡 |
| 04 | Sheet Manifests | `04-sheet-manifests.md` | 03 | 🟡 |
| 05 | Additional Composite Templates | `05-additional-composite-templates.md` | 00, 01, 02 | 🟡 |
| 06 | Shot Bible Writers | `06-shot-bible-writers.md` | — | 🟢 |
| 07 | Generation Plan + Budget | `07-generation-plan-and-budget.md` | 06 | 🟡 |
| 08 | QC Node + Validation Writers | `08-qc-node-and-validation.md` | 07 | 🟡 |
| 09 | Post + Delivery Writers | `09-post-and-delivery.md` | 08 | 🟡 |
| 10 | Cross-Cutting Artifacts | `10-cross-cutting-artifacts.md` | — | 🟢 |

---

## What's at Stake

| If we skip… | Impact |
|------------|--------|
| 00-02 (Bibles) | Reference image prompts fall back to LLM-generated text instead of locked CharacterBible/EnvironmentBible data. Identity consistency degrades. |
| 03-04 (Sidecars, Manifests) | No per-frame audit trail. Cannot prove which provider/model/seed produced each frame. Composite layouts not machine-readable. |
| 05 (Composite Templates) | Only Character Identity Sheet and Environment Board exist. No costume, expression, prop, style, camera, or scale boards. |
| 06 (Shot Bible) | No shot matrix, continuity ledger, or prompt registry. Generation planning has nothing to plan from. |
| 07 (Generation Plan) | No ordered shot execution plan with provider routing. Cannot estimate cost before generation. |
| 08 (QC) | No structured validation reports. Blocking issues not tracked. |
| 09 (Post + Delivery) | Cannot assemble or deliver a final film. |
| 10 (Cross-cutting) | No checkpoints, rollbacks, or invalidation tracking. Asset manifest written but never consumed. |

---

## Related Docs

- `docs/data-storage/artifact-map.md` — Current state vs target state
- `docs/data-storage/analysis.md` — Review of original document
- `docs/openclaw-mcp-operator-guide.md` — Operator workflow
- `docs/reference-image/implementation-review.md` — Reference image pipeline status
