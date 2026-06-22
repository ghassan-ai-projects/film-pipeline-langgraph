# Revised2 — Scenario Stress Test: Does the Plan Actually Work?

**Date:** 2026-06-22
**Purpose:** Walk through 8 real-world scenarios and trace whether the 8-phase plan handles them correctly. Find gaps the plan doesn't cover.

---

## Scenario 1: Crash Mid-Phase Recovery

**Situation:** Process dies during `script_node` execution. Agent has called the model, received a response, but hasn't saved the artifact yet. The node is mid-execution.

### Today
```
run_graph() → script_node executing → PROCESS DIES
                                        │
                                   State is lost. No checkpointer.
                                   Project stuck at "script" phase.
                                   Must restart from last git checkpoint.
```

### After Phase 1
```
run_graph() → script_node executing → PROCESS DIES
                                        │
                                   MemorySaver had last checkpoint BEFORE script_node.
                                   On restart: graph.invoke(None, config)
                                   ... MemorySaver is in-memory. Process died = memory wiped.
                                   STATE IS STILL LOST.
```

**Verdict: ❌ Phase 1 does NOT solve crash recovery.**

Phase 1 adds `MemorySaver` which survives interrupts (intentional pauses) but not process death. The plan says "SqliteSaver in Phase 7+" but Phase 7 only mentions it in passing. Crash recovery requires a **durable** checkpointer.

**Fix needed:** Add `SqliteSaver` as a prerequisite in Phase 1 itself, OR add an explicit Phase 1b: "Durable Checkpointer" that ships immediately after Phase 1. `MemorySaver` is a proof-of-concept — it shouldn't ship as the Phase 1 deliverable if crash recovery is the goal.

Alternatively: keep the git-backed checkpoint system for crash recovery. Before every phase node, create a git checkpoint of the current state. On restart, load the last git checkpoint and resume. This works today but is slow (git commit per phase).

---

## Scenario 2: Repair Loop — 2 Fixes, 1 Regression

**Situation:** Shot bible agent produces 20 rows. Gate A finds rows 3 and 7 have issues. Repair round 1: agent fixes rows 3 and 7, but accidentally breaks row 12 (was previously passing). Gate A now finds 1 issue (row 12). This is net progress (2→1) but not convergence.

### Today
```
Repair round 1: agent gets "REPAIR ROUND 1: [shot_count_mismatch] act_1 expected 5, got 3"
                Agent guesses which rows to fix. Regenerates entire matrix.
                Fixes rows 3 and 7 ✓. Accidentally breaks row 12 ✗.
                Gate A: 1 new issue on row 12. Total issues: 1.

Repair round 2: agent gets "REPAIR ROUND 2: [missing_camera_profile] shot_0012"
                Agent fixes row 12. Preserves other rows (by luck, not design).
                Gate A: 0 issues. Phase passes.

Convergence: 3 rounds total (initial + 2 repairs). Under max_rounds=3. Works.
```

But: if round 1 produces MORE issues than the initial run (regression), the agent doesn't know. It keeps trying. The convergence counter doesn't track score degradation.

### After Phase 5
```
Repair round 1: agent gets structured feedback:
                "PRESERVE rows: 1,2,4,5,6,8-20"
                "FIX row 3: [missing_prompt_ref] → set prompt_ref"
                "FIX row 7: [duration_out_of_range] → set to 5-15s"

                Agent fixes ONLY rows 3 and 7. Rows 1-20 are preserved.
                Row 12 is untouched (preserved). No regression possible.

Gate A: 0 issues. Phase passes.
```

**Verdict: ✅ Phase 5 solves this — IF validators can identify specific rows.**

**Critical dependency:** Validators must set `shot_id` on findings. The `Gate A` validator (`validate_shot_structure`) produces global issues (`shot_count_mismatch`, `runtime_mismatch`) that don't name specific rows. If the shot count is wrong, the validator can't say "row X is missing" — it only says "expected 20, got 18." The repair feedback has only `global_issues`, not per-row instructions. The agent still guesses.

**Gap:** Phase 5 needs validator enhancement for row-level targeting. Gate A must identify WHICH act is short and suggest WHERE to add rows, not just "you're 2 rows short."

---

## Scenario 3: Upstream Change Cascades — Constitution Wrong After Delivery

**Situation:** Full pipeline completed. Constitution → Treatment → Script → Matrix → Gen Plan → Generation → QC → Post → Delivery. Then someone realizes `constitution.theme` was "dark noir" but should be "hopeful sci-fi." Constitution is re-run with corrected theme.

### Today
```
Re-run constitution_node → saves film_constitution:v2
Nothing detects that treatment, script, matrix, gen_plan, assets are stale.
Operator must manually re-run every phase from treatment onward.
No tool shows what's affected.
```

### After Phase 3
```
Re-run constitution_node → saves film_constitution:v2 with built_from={profile:v1}

consistency_check_node (runs after constitution):
  check_staleness("film_constitution:v2") → no deps (constitution has no upstream)
  No warnings. Constitution passes its own gate.

  But treatment:v1 still has built_from={constitution:v1}.
  Script:v1 has built_from={treatment:v1, constitution:v1}.
  Matrix:v1 has built_from={script:v1, ...}.
  Assets built from matrix:v1.

  NOTHING PROACTIVELY CHECKS THESE. Staleness is only checked when a phase runs.

Operator sees constitution approved. No indication that everything downstream is stale.
```

**Verdict: ❌ Phase 3 detects staleness at phase boundaries, not proactively.**

The `consistency_check_node` runs AFTER a phase completes. When constitution is re-run, it checks if constitution's own dependencies are stale (they're not — constitution depends on nothing). It doesn't check if DOWNSTREAM artifacts are now stale because constitution changed.

**Fix needed:** Add a `check_downstream_staleness()` function that, given an artifact, finds all artifacts whose `built_from` references it and flags them as stale. Run this in `consistency_check_node` OR as a standalone MCP tool. Example: after constitution changes, the operator runs `check_impact(artifact:film_constitution:v2)` → returns list of 12 downstream artifacts that are now stale.

**Phase 3 plan gap:** The plan says `check_staleness(artifact_ref)` checks "if an artifact's upstream dependencies have newer versions." This is the WRONG direction. We need the reverse: "which downstream artifacts depend on this one?"

---

## Scenario 4: Triple Rejection → Stall → Escalation

**Situation:** Operator rejects shot_bible 3 times. Convergence tracker marks phase as stalled.

### Today (Current Code Trace)
```
Repair round 1: rejected. convergence[shot_bible].round_count = 1
Repair round 2: rejected. convergence[shot_bible].round_count = 2
Repair round 3: rejected. convergence[shot_bible].round_count = 3
  is_stalled(state, "shot_bible", max_rounds=3) → True
  mark_stalled(state, "shot_bible", "Repair failed after 3 rounds.")
  return state  (does NOT re-run phase)

Graph returns to await_approval (edge: repair → await_approval)
after_approval sees: approved=False, issues exist → return "repair"
  → repair_phase_node:
    is_stalled → True → return state immediately
  → await_approval → after_approval → "repair" → repair → ...

INFINITE LOOP. Graph never escapes.
```

### After Phase 1 (with interrupt)
```
Repair round 3: stalled. Returns state without repair.
Graph: repair → await_approval → interrupt(payload)
  Payload includes: stalled=True, reason="Repair failed after 3 rounds"
  Allowed actions: currently ["approve_phase"] or ["request_revision"] —
  NEITHER makes sense when stalled.

Human sees interrupt. Options are wrong:
  - "Approve" — but blocking issues exist, should be blocked
  - "Revise" — but repair already failed 3 times

Human has no good option. Must manually rollback or accept with known issues.
```

**Verdict: ❌ The plan doesn't handle stall escalation as a first-class action.**

Current code has an infinite loop. Phase 1 replaces it with an interrupt that offers wrong options. Neither works.

**Fix needed:**
1. Add `"escalate"` as a third action in the interrupt payload when `stalled=True`.
2. Escalate means: "present this to a human with note that automated repair failed; human must decide: rollback, accept_with_known_issues, or manually edit."
3. Fix the infinite loop in current code: `after_approval` must check `is_stalled` and route to escalation, not repair.

---

## Scenario 5: Large Matrix — 200 Shots, 50 Scenes

**Situation:** A 10-minute film with 200 planned shots across 50 scenes. The matrix is ~250KB JSON. Every downstream agent needs matrix data but gets only truncated context.

### Today
```
_compact_json_context(matrix, max_chars=6000)
→ First ~5% of rows visible. Rest: "... [truncated]"

Gen planner sees ~10 rows out of 200. Plans 10. 190 unplanned.
QC sees ~10 rows. Validates 10. 190 unchecked.
Post sees ~10 rows. Assembles 10. 190 missing from assembly.
```

### After Phase 6
```
build_gen_planning_context():
  get_rows_by_status(matrix, "planned") → 200 rows
  for row in planned_rows[:100]:  ← CAP at 100
      parts.append(f"{shot_id}: act={act_id}, scene={scene_id}, ...")

  Result: 100 rows shown. 100 rows invisible.
  Context: ~3000 chars. Under limit. Good.

But: 100 rows are STILL invisible to the agent.
The agent plans 100 shots, 100 are unplanned.
```

**Verdict: ⚠️ Phase 6 reduces but doesn't eliminate the truncation problem.**

The 100-row cap is arbitrary. For a 200-shot film, half the rows are invisible. The agent can't produce a complete plan.

**Fix needed:**
1. Make the cap configurable: `max_rows_in_context = 500` for planning phases.
2. Use pagination or batching: instead of one agent call for 200 rows, do 4 calls of 50 rows each.
3. Alternatively: don't send individual row data for PLANNING. Send aggregate stats: "200 rows: 50 act_1, 80 act_2, 70 act_3. Providers available: [seedance, veo]. Budget: $36." The agent plans at the aggregate level, not per-row.

**Phase 6 plan gap:** Context builders need pagination awareness. For phases that need per-row data (generation, QC), batch the work. For phases that need aggregate data (gen_planning), send aggregates.

---

## Scenario 6: Model Returns Invalid JSON 3 Times in a Row

**Situation:** The model is having a bad day. Three consecutive calls return unparseable output.

### Today
```
_run_agent() → PromptRunner.run_from_template() → ModelAdapter.chat_json()
  → chat() returns text → 4 extraction strategies fail → ValueError("not valid JSON")

ValueError propagates up through _run_agent(), crashes the phase node.
Graph node crashes. No try/except. Graph fails.
No retry. No fallback model. No escalation.
```

### After Plan (Any Phase)
```
Same flow. The plan doesn't add JSON retry logic to any phase.
Phase 8 adds chain-of-thought (might improve JSON quality) but no retry loop.
```

**Verdict: ❌ The plan doesn't address model failure recovery at all.**

**Fix needed:** Add a retry wrapper around `chat_json()`:
1. Attempt 1: normal call with assigned profile
2. Attempt 2: retry with lower temperature (0.1) + explicit instruction "You MUST output valid JSON"
3. Attempt 3: retry with fallback model (cheaper, more reliable)
4. After 3 failures: save raw model output as an artifact, add blocking issue with the raw output attached, escalate to human.

This is a pre-requisite for ANY phase that calls a real model. It should be in Phase 0 alongside profile routing.

---

## Scenario 7: Rollback After Delivery — Trace Full Cascade

**Situation:** Delivery complete. Someone realizes constitution was wrong. Must determine everything that needs regeneration.

### Today
```
InvalidationEngine.report("constitution", ["film_constitution"])
→ will_revert: ["film_constitution"]
→ will_invalidate: ["treatment", "script", "character_bible", "environment_bible"]
→ Only ONE level deep! Doesn't show:
  - shot_bible (depends on script)
  - prompt_registry (depends on shot_bible)
  - provider_plan (depends on prompt_registry)
  - generation_schedule (depends on provider_plan)
  - generated_clips (depends on generation_schedule)
  - validation_reports (depends on continuity_ledger + generated_clips)
  - assembly_manifest (depends on matrix + generated_clips)
```

### After Phase 3 + Phase 4
```
Phase 3 adds built_from to every artifact:
  treatment:  built_from={constitution:v1}
  script:     built_from={constitution:v1, treatment:v1}
  matrix:     built_from={script:v1, constitution:v1, execution_brief:v1}
  gen_plan:   built_from={matrix:v1}
  gen_assets: built_from={gen_plan:v1, matrix:v1}
  ...

Transitive stale check:
  constitution:v2 exists → check all artifacts with built_from.constitution
  → treatment:v1 is stale (built_from constitution:v1, current:v2)
  → script:v1 is stale
  → matrix:v1 is stale (via script, via constitution)
  → gen_plan:v1 is stale (via matrix, via script, via constitution)
  → ... etc

Full cascade: 12 artifacts need regeneration.
Estimated cost: sum of all provider_plan entries for all affected shots.
```

**Verdict: ✅ Phase 3 enables this — but no tool exposes it.**

The data is there (`built_from` on every artifact). The algorithm is simple (transitive graph traversal). But there's no MCP tool to run it.

**Fix needed:** Add `estimate_rollback_impact` MCP tool that:
1. Takes an artifact ref
2. Transitively finds all downstream artifacts via `built_from` chains
3. Returns list of affected artifacts with estimated regeneration cost
4. Offers two paths: "cascade regenerate all" or "only regenerate what's visibly different"

---

## Scenario 8: Budget Exceeded Mid-Generation

**Situation:** Generation phase is running. After 15 of 20 clips generated, the total cost crosses the $50 budget cap. The system should pause and alert the operator.

### Today
```
Budget check happens in compute_actions() → tier 4.
compute_actions() runs at phase BOUNDARIES, not mid-phase.
Generation_node is a stub — doesn't generate anything.

If it did: 15 clips generated, $52 spent. Cap is $50.
No check occurs until generation_node returns.
After generation_node returns → after_phase() → compute_actions()
  → is_budget_blocked → True
  → next_action = "escalate_to_human"
  → routes to await_approval → loops to recursion limit.

But: $2 over budget already spent. Can't undo the spend.
```

### After Phase 1 + Phase 4 (generation_node real)
```
Same flow. Budget check at phase boundaries only.
15 clips generated, $52 spent. Cap exceeded.
Generation node returns. after_phase → escalate_to_human → interrupt.
Operator sees "budget exceeded" but can't un-spend the $2.
```

**Verdict: ❌ Phase-boundary budget checks are too late for generation.**

By the time the check fires, money is already spent. The check needs to be PER-CLIP, not per-phase.

**Fix needed:**
1. The generation subgraph (Phase 7) must check budget BEFORE each clip submission.
2. At the start of each worker: `if remaining_budget < clip_estimated_cost: return budget_blocked`.
3. Budget-blocked workers create blocker issues. The subgraph pauses via `interrupt()` mid-batch.
4. Also: WHO updates `budget_snapshot`? The plan doesn't say. The `ProviderAdapter.submit()` or `GenerationLedger` must update `spent_usd` after each successful generation. This wiring doesn't exist.

**Phase 4 + 7 plan gap:** Budget tracking is a state field that nobody writes to. It needs a writer: the generation ledger or provider adapter.

---

## Summary: What the Plan Gets Right vs. What It Misses

| Scenario | Plan Handles? | Gap |
|----------|--------------|-----|
| 1. Crash mid-phase | ❌ No | MemorySaver not durable. Need SqliteSaver or git fallback in Phase 1. |
| 2. Repair with regression | ✅ Yes | But depends on validators identifying specific rows (Phase 5 dependency). |
| 3. Upstream change cascade | ⚠️ Partial | Detects staleness in wrong direction. Need downstream impact check. |
| 4. Triple rejection → stall | ❌ No | Infinite loop in current code. Interrupt offers wrong options. Need "escalate" action. |
| 5. Large 200-shot matrix | ⚠️ Partial | Context still truncated at arbitrary caps. Need pagination or aggregation. |
| 6. Invalid JSON × 3 | ❌ No | No retry logic anywhere. Need retry wrapper in Phase 0. |
| 7. Rollback after delivery | ✅ Yes | built_from enables cascade trace. Missing MCP tool to expose it. |
| 8. Budget exceeded mid-gen | ❌ No | Budget check at phase boundaries only. Need per-clip check. No budget writer. |

## New Pre-Requisites Before Implementation

These must be added to the plan or done before Phase 1:

1. **P0: Add model retry wrapper** — `chat_json()` with fallback model + temperature reduction. 3 attempts → escalate. (30 min, add to Phase 0)

2. **P0: Fix stall infinite loop** — `after_approval` must check `is_stalled` and route to escalation, not repair. Add "escalate" action to interrupt payload. (30 min, add to Phase 1)

3. **P0: Durable checkpointer** — Replace `MemorySaver` with file-backed persistence before shipping Phase 1. Options: `SqliteSaver` (preferred) or git-based state snapshots. (1 hour, add to Phase 1)

4. **P1: Downstream staleness check** — `check_downstream_impact(artifact_ref)` for cascade tracing. MCP tool: `estimate_rollback_impact`. (1 hour, add to Phase 3)

5. **P1: Budget writer** — Wire `GenerationLedger` to update `budget_snapshot.spent_usd` on successful generation. Per-clip budget check in generation worker. (2 hours, add to Phase 4/7)

6. **P2: Context pagination** — For matrices >100 rows, batch agent calls or use aggregate statistics. (2 hours, add to Phase 6)

7. **P2: Validator row targeting** — Gate A/B/C validators must identify specific rows in findings, not just global issues. (2 hours, add to Phase 5)

## Revised Ready-to-Start Assessment

**Phase 0 can start immediately** — it has no dependencies and fixes profile routing + quality instructions. Add the model retry wrapper (new P0 #1).

**Phase 1 needs 3 additions** before starting: durable checkpointer, stall fix, retry wrapper. Total added: ~2 hours.

**Phase 2-8** are good with the gap fixes above. No architectural rework needed — just additions to existing phases.
