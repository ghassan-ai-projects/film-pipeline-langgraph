# Independent Critic Pass — Architecture Review Deliverable

Critic: independent reviewer (this pass). Subject: `documentation/architecture-review.md` + five lens
reports under `documentation/reviews/arch-lens-*.md`. Repo `film-pipeline-langgraph`, branch
`arch-improvement-review`, HEAD `e811d1d` (verified: `git log` shows `e811d1d Merge pull request #20…`).
Method: ~28 citation spot-checks against source read directly at HEAD (line-number reads, consumer
greps, AST recount of lazy imports, wc -l census), then scoring against the six-point bar.

---

## A. Citation spot-check (15+ required; 28 performed)

**Verified CORRECT (source re-read at e811d1d):**

| # | Claim | Source check | Result |
|---|---|---|---|
| 1 | `graph/services.py:72` lazily imports `film_pipeline.testing.fixtures.mock_responses` inside `for_mock_runtime` | line 72 exact | ✅ |
| 2 | `mcp/tools/generation/dispatch.py:78` hardcodes `duration=5.0`; :76 sends unresolved `prompt=row.prompt_ref` | lines 76–78 exact | ✅ |
| 3 | Executor counterpart resolves prompt + row duration (`executor.py:145-193`) | `resolve_shot_prompt` at :166, `float(shot_row.get("duration_seconds", 5))` at :167 | ✅ |
| 4 | `orchestrator_state.py:22-63` defines exactly **10** channel keys | counted :26,:30,:34,:38,:42,:46,:50,:54,:58,:63 | ✅ |
| 5 | `_propagate_side_effects` copies only `_orchestrator__candidate_refs` from the orch namespace | `_copy_published_candidate_refs` sets only that key | ✅ |
| 6 | `app/_graph_exec.py:181-183` bare `except Exception:` → `advance_to_next_phase`; `:125` `contextlib.suppress(Exception)` around auto-checkpoint; `:101-106` hardcodes phase `"intake"` | all three exact | ✅ |
| 7 | `brief.py:35` store fallback pins version 1 | `load(project_id, FilmPhase.SHOT_BIBLE, "execution_brief", 1)` at :35 | ✅ |
| 8 | Observability package has zero src consumers (`AuditTrail`/`MetricsCollector`/`BlockerReporter`) | grep outside package: zero hits for all three | ✅ |
| 9 | `add_blocker` (`runtime.py:367-377`) zero callers; `get_blockers` filters empty `block_entries` (:364-365); tool wired at `mcp/tools/state.py:77-82` | grep confirms writer never called; reader chain exact | ✅ |
| 10 | Imagen tier literals `ultra→0.10 / fast→0.02 / else 0.05` at `imagen4_gemini.py:162-169` vs flat `$0.02` at `pricing.py:31-32` | both exact | ✅ |
| 11 | `state_schema.py:121,124,125` declares `server_mode`/`runtime_mode`/`workflow_mode`; comment :122-123 "silently drops them"; fallback-or chain at `operator.py:234` | all exact | ✅ |
| 12 | `registry.py:112` description is `f"MCP tool: {name}"`; file is 387 LOC; 52 `_register(registry…)` calls; `_register` accepts no schema kwarg | all exact | ✅ |
| 13 | `PromptTemplateRegistry.register` silently overwrites (`agents/prompt_templates/registry.py:65-67`, docstring admits) | exact | ✅ |
| 14 | AGENTS.md documents 12 packages vs **19** actual top-level dirs under `src/film_pipeline/` (excl. `__pycache__`) | `ls -d`: 19 packages | ✅ (see DEFECT-2 for the cognition report's contrary count) |
| 15 | Agent tables drifted: `AGENT_CLASS_BY_ID` = 12 ids incl. alias `visual-dev-agent` (:26); `MVP_AGENTS` = 11 contracts; `_AGENT_PROFILE_MAP` = 21 ids with **exactly 9** orphans (the nine named in Flx-F2) | recount via set difference: 9 orphans, same list | ✅ |
| 16 | `factory.py` three tables in one file: if-chain :34-44, `_default_models` :47-56, `_default_capabilities` :59-103 | exact | ✅ |
| 17 | Thresholds disagree: schema default 85/75/**65**, per-entry literals 85/75/**75**, profile yaml pass85/review75/block**60** unread | `validator_registry.py:17-19`, `validators/__init__.py:19…`, `base.studio.yaml:56-60` | ✅ (cite range nit, DEFECT-7b) |
| 18 | `FILM_PIPELINE_MODEL_OVERRIDE` writes `("models","creative_writer","primary")` (`runtime_overrides.py:16`); nothing reads that path | grep: no reader of `models.creative_writer` | ✅ |
| 19 | `re_anchor_every_n_clips` declared (`base.studio.yaml:43`, override `review.strict_continuity.yaml:11`), zero src consumers, recorded in hardcoded-values-inventory.md:225 | confirmed | ✅ |
| 20 | `BudgetState.spent_usd` initialized 0.0 (`planning.py:29`) and **never incremented anywhere** in src; escalate rule consumes `threshold_exceeded` (`_action_routing.py:238-243` ← `is_budget_blocked` :239 ← snapshot :374-377) | grep: only two `spent_usd=` writes, both 0.0 defaults | ✅ |
| 21 | D-007 commit `1a61b9e` = "fix(observability): correct routing event kind typo" | git show exact | ✅ |
| 22 | Audit vocab drift `create_project` (runtime.py ~117) vs `create_film_project` (projects.py:121-128) | both present | ✅ |
| 23 | Blueprint: zero hits for `tui/TUI/OperatorService/app/`; single "shot density" mention at L1069; operator-guide L73 tells users to use `get_blockers` | greps exact | ✅ |
| 24 | Hotspots LOC: operator 473 / studio 471 / runner 471 / _context 470 / _profile_change 467 / runtime 464 / qc 455 / orchestrator_state 435; total 307 modules, 41,478 LOC (~41.5k) | wc -l exact on all eight; find = 307 files | ✅ |
| 25 | Cycle `{app ↔ mcp}`: module-level `from film_pipeline.app.runtime import get_runtime` in `mcp/tools/__init__.py` (~:22) and `from film_pipeline.mcp.contract import make_registry` at `product_gate.py:17`; `edges.py:119` `.get(phase,"end")`; `ensure_orchestrator_state` (:415-435) initializes 9 domains, omits `_EXECUTION_BRIEF`; 18 `add_node` calls; deepcopy ×22 in nodes+subgraphs; ref builder `f"artifact:{id}:v{n}"` at `_agent_artifacts.py:142`; thread_id==project_id at `_graph_exec.py:63-64` | all confirmed | ✅ |
| 26 | `store.approve()`/`.supersede()` zero callers in src; `resolve_artifact` (`orchestrator_state.py:97`) no production caller | grep confirms | ✅ |
| 27 | "mcp imports 13 packages, app imports 11" | AST recount: mcp 13 distinct targets, app 11 — exact | ✅ |
| 28 | Lazy import counts "194 (mcp 109, graph 42, app 21)" | AST recount: mcp 109 ✅ exact, graph 42 ✅ exact, post 10 ✅, artifacts/config/generation/tui ✅ — but app 24 and cli 5 → **sum 198, not 194** (see DEFECT-6) |

**DEFECTS FOUND (wrong/stale/inconsistent claims):**

- **DEFECT-1 (factual, wrong number)** — `arch-lens-cognition.md` Finding 4.1: the patch string
  `monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", …)` "**occurs 68× across 32 unit test
  files**". The count 68 is correct (all variants: 63 quoted-string + 5 alias-target variants = 68),
  but the distinct-file count is **11 test files** (8 files for the exact quoted pattern), not 32.
  Corrected fact: *68 occurrences across 11 unit test files*. Main doc repeats only "68 sites"
  (§E, D9) — accurate — but the archived lens evidence carries the wrong spread figure.
- **DEFECT-2 (factual, wrong number)** — `arch-lens-cognition.md` Finding 6.3: "AGENTS.md documents
  12 sub-packages; the tree has **21**." Actual: **19** packages (12 governed + exactly the 7 the same
  finding lists as unmapped: cli, constraints, generation, observability, testing, tui, app — its own
  arithmetic says 19). The boundaries lens (B-F8/Finding 8) has 19, which is correct. The main doc
  prints 19 but cites "[B-F8, C-6.3]" — attributing part of a correct claim to a source that states
  21. Correct C-6.3 to 19 or annotate the conflict.
- **DEFECT-3 (internal contradiction)** — `arch-lens-dataflow.md` F-1 heading: "allowlist is a fixed
  key list; **10 of 11** orchestrator channels are not covered". The body and per-channel table of the
  same finding define **10** channels of which the allowlist copies **1** → 9 of 10 uncovered. The
  main doc silently normalized this to "covering **1 of 10**" (correct) without flagging the lens
  discrepancy.
- **DEFECT-4 (stale/dangling reference in the deliverable itself)** — `architecture-review.md`
  §Verification points to `documentation/reviews/arch-review-critic.md` ("scores + citation
  spot-checks"), which **does not exist** (nor anywhere else in the repo). The header also promises
  "Critic verdict for this revision: recorded at the bottom ([Verification](#verification))", but the
  Verification section records no verdict — it defers entirely to the missing file. Until this critic
  report is archived at a real path and the link fixed, criterion 1's "zero stale references" fails on
  the deliverable's own citation.

Minor imprecisions (substance correct, cite range off by ≤3 lines; fix opportunistically):
(a) O-F9 cites the budget gate at `orchestrator_state.py:351-370`; those lines define the
writer/accessors — the reading function is `is_budget_blocked` at :374-377 consumed by
`_action_routing.py:239`; (b) Flx-F5 cites schema thresholds at `validator_registry.py:13-17`;
fields are at :17-19; (c) lazy-import totals differ slightly from an independent AST recount (198 vs
194; app 24 vs 21, cli 5 vs 4; every other package matches exactly).

---

## B. Scores against the bar

| # | Criterion | Score | Justification |
|---|---|---|---|
| 1 | GROUNDED | **3** | Every source-code citation I checked (28) resolves at HEAD with correct symbol and behavior — an exceptional record — but three quantitative claims are wrong (68/11 misstated as 68/32; 19 misstated as 21 in C-6.3; "10 of 11" self-contradiction) and the deliverable cites a critic-report file that does not exist, violating its own "zero stale/wrong references" bar. |
| 2 | SPECIFIC | **4** | Proposals consistently name files/symbols, target design, migration, effort and risk (lens reports exemplary); deduction because several roadmap rows compress migration/effort into pointers to the lens reports rather than standing alone, and a few P0/P2 items carry no per-item risk statement beyond the section header. |
| 3 | COMPLETE ON AXES | **4** | Maintainability, observability, flexibility each have finding-severity tables plus axis verdicts, and reasoning-load gets explicit coverage and a verdict row in the axis table; deduction because §E (reasoning load) is prose-only with no finding table mirroring A–D, and a few lens findings have no home in either the debt register or roadmap (see C-5). |
| 4 | DECISION-READY ROADMAP | **4** | P0/P1/P2 with sequencing principles ("guardrails before refactors", "characterize before touching"), sub-package-law awareness, and an explicit guardrails/non-goals section; deduction because several named findings/themes are stranded with neither a schedule slot nor an explicit defer rationale (rollback stores, DF-F6, B-F1/B-F2/B-F3). |
| 5 | HONEST UNCERTAINTY | **4** | Lens reports mark UNCERTAIN items liberally and correctly (perf magnitude, FP rates, out-of-tree consumers, packaging intent) and the synthesis preserves them; deduction because it silently corrects contradictory lens numbers (21→19, 10-of-11→1-of-10) without noting the conflict, and asserts "(1802+ passed)" without a reproducible command/log reference. |
| 6 | INDEPENDENT PASS | **3** | The deliverable claims a completed critic pass, but its evidence artifact was absent, so independence could not be verified until now; this document performs that pass — the score rises to ≥4 once the report is archived at the path the review cites and the required fixes below are applied. |

---

## C. Required fixes (ranked; binding)

1. **Fix the dangling critic reference (DEFECT-4).** Archive this critic report at the path the
   review cites (`documentation/reviews/arch-review-critic.md`) or repoint §Verification to its real
   location (`.fleet/scratch/arch-review-critic.md`), and paste the final one-line verdict into
   §Verification so the promised bottom-of-document verdict actually exists.
2. **Correct DEFECT-1** in `arch-lens-cognition.md` F-4.1: "across 32 unit test files" → "across 11
   unit test files" (68 occurrences stands).
3. **Correct DEFECT-2** in `arch-lens-cognition.md` F-6.3: "the tree has 21 packages" → 19, and fix
   the main doc's `[B-F8, C-6.3]` attribution so the 19-package fact is credited to the source that
   verified it (B-F8).
4. **Correct DEFECT-3** in `arch-lens-dataflow.md` F-1 heading: "10 of 11 channels not covered" →
   "9 of 10" (or restate as "only 1 of 10 propagated"), keeping the body/table unchanged.
5. **Give every exec-summary theme and tabulated finding a roadmap or register home.** Currently
   stranded: (a) rollback-record dual stores [C-1.2/DBT-3 — rated High severity in the cognition
   lens, surfaced in Theme 1, absent from debt register D1–D11 *and* roadmap]; (b) dead router rules
   reading unwritten channels [DF-F6 — Theme 3 bullet, no P0/P1/P2 item wires or deletes them];
   (c) post→validation inversion [B-F1]; (d) config→providers move incl. public `env_var_for` [B-F2];
   (e) `OPENROUTER_API` relocation [B-F3]. For any item deliberately deferred, add one line saying so
   and why — silence is not a decision.
6. **Reconcile the lazy-import totals** (boundaries F-7 / Ground-truth section): state the counting
   convention or update to the reproducible recount (198 total; app 24, cli 5; other packages match).
   Add the one-line method note so an independent verifier reproduces the same number.
7. **Tighten the two off-by-line citations**: O-F9 budget-gate cite → add `_action_routing.py:239` /
   `orchestrator_state.py:374-377`; Flx-F5 schema-threshold cite → `:17-19`.
8. **Add a finding-severity table to §E (reasoning load)** mirroring sections A–D (rows C-overall,
   C-2.1–2.3, C-3.1–3.3, C-4.1–4.2, C-6 with severity/effort), so all four axes meet the bar's
   "verdict tables" requirement identically.
9. **Mark or make reproducible the unverified aggregate**: "(1802+ passed)" in Ground truth should
   carry the command/log that produced it (e.g., `make test-unit` output reference) or be marked
   UNCERTAIN like the lens-level unknowns.
10. **Flag reconciliations instead of silent fixes**: wherever the synthesis corrected a lens number
    (21→19, 10-of-11→1-of-10), add a parenthetical "(lens said X; corrected to Y after recount)" so
    the archived reports and the synthesis visibly agree after revision.

---

## D. Faithfulness of the synthesis to the lens reports

**Invented findings: none detected.** All 28 spot-checked claims trace to lens evidence and to real
source at HEAD; the strongest claims (mock fixtures on default startup path, money-path drift,
dead observability package, frozen budget gate, dangling approval lifecycle) were each independently
confirmed against code. The synthesis adds legitimate cross-lens aggregation (Themes 1–5, merged
debt register D1–D11) without fabricating evidence.

**Dropped / under-represented:**

1. **DBT-3 / C-1.2 (dual rollback-record stores with divergent id formats) is dropped from the
   decision layer.** The cognition lens rates the underlying walkthrough High severity, the synthesis
   quotes it in exec-summary Theme 1 — and then it appears nowhere in the consolidated debt register
   (D1–D11) nor the roadmap. This is the one high-rated item that loses its action item in synthesis.
2. **DF-F6 (seven router rules that cannot fire)** is highlighted in Theme 3 but has no P0/P1/P2 item;
   the nearest roadmap entry (P1#8 error taxonomy / provider health) addresses wiring failure data but
   never states the wire-or-delete decision DF-F6 demands.
3. **Boundary findings B-F1, B-F2, B-F3 are tabulated with severity and effort in section A but never
   scheduled** (P0 picks B-F4 and B-F8 only; B-F6 is partially absorbed into P2#3 hotspot splits).
   Nothing marks them deferred.
4. Minor: Flx-F5's threshold single-sourcing target ("impl validators read `self.entry.thresholds`")
   survives only implicitly via P0#5's config-contract test; the unification step itself is not
   scheduled. DBT-1/DBT-5 remain cognition-register-only (acceptable: the main register is declared
   "top items", but the doc never says which DBTs were deliberately left out).

No high-severity observability, flexibility, or dataflow finding is dropped — O-F1..F9, Flx-F1/5/6/10,
DF-F1..F5 all map to P0/P1 items or register rows.

---

## Verdict

Scores: Grounded 3 · Specific 4 · Complete-on-axes 4 · Roadmap 4 · Honest uncertainty 4 · Independent
pass 3. Four factual/reference defects (DEFECT-1..4) violate criterion 1's own "zero stale/wrong
references" standard, and criterion 6 was unverifiable before this pass.

FINAL: REVISE
(binding list = Section C, items 1–10; re-score after fixes — expected outcome is PASS with scores ≥4
once DEFECT-1..4 are corrected, the stranded findings are given homes or explicit deferrals, and this
report is archived where the review cites it.)

---

## Round-2 re-verification (critic)

Re-checked every applied fix against source facts from round 1. **Confirmed correct:** cognition
F-4.1 (68× / 11 files / 8 exact-pattern) and F-6.3 (19 packages, both places, correction flagged);
dataflow F-1 heading ("9 of 10"); O-F9 cite (writer :351-370 + `is_budget_blocked` :374-377 +
`_action_routing.py:239` — matches source); flexibility schema cite (:17-19); boundaries lazy totals
198 / app 24 / cli 5 (matches AST recount) in heading and body; main-doc ground truth (198); debt
register D12/D13; P1 items 11–13 (content consistent with B-F1/F2/F3, DF-F6, C-1.2/DBT-3 target
designs — no new factual errors); P2#3 absorbs B-F6 [C-2/B-F6]; Verification rewritten and the
dangling reference resolved by this archived file.

**Remaining defects (verdict REVISE):**

1. `documentation/architecture-review.md:104` — B-F7 row still reads "**194 lazy imports** hide true
   fan-out", contradicting the corrected ground-truth bullet (198) eight lines away. Leftover of the
   lazy-total propagation.
2. `documentation/reviews/arch-lens-cognition.md:328` — DBT-7 evidence column still reads "tests
   across **32 files**"; DEFECT-1 was fixed in F-4.1 but survives in the debt-register table.
3. Binding fix #8 not applied: §E (reasoning load) remains prose-only — no finding-severity table
   mirroring sections A–D, so reasoning-load does not yet meet the bar's "verdict tables"
   requirement in the same form as the other axes.
4. Binding fix #9 not applied: "(1802+ passed)" (`architecture-review.md:83`) still carries no
   command/log reference and no UNCERTAIN mark.
5. Minor: reconciliation flags (binding fix #10) were added to cognition and boundaries but not to
   the corrected dataflow F-1 heading.

Round-2 scores unchanged pending these: Grounded 4 once items 1–2 are fixed (all other citations
28/28 exact); Specific/Complete/Roadmap/Uncertainty hold at 4 rising with items 3–5.

---

## Round-3 re-verification (critic) — FINAL

All five round-2 items verified in place: B-F7 row → "198 lazy imports" (consistent with ground
truth); DBT-7 evidence → "11 test files (see corrected F-4.1)"; §E gained a full findings table
(C-1.1..C-6, Severity + Effort columns — every value cross-checked against arch-lens-cognition.md,
including the corrected "68 sites across 11 files") plus an explicit axis-verdict line with narrative
retained below; Tests bullet now attributes 1,802 passed / 1 skipped to the phase-2 referee gate
(serial, from scratch, pre-merge) with an explicit UNCERTAIN mark on the exact count at `e811d1d`;
dataflow F-1 heading carries "(heading count critic-corrected from '10 of 11')".

Global sweep clean: no instance of the old wrong numbers ("32 files", package count 21, lazy total
194 outside the change-record mention, "10 of 11") remains in any of the six documents. Theme 5's
[B-F8, C-6.3] dual citation is now accurate — both sources state 19.

**Final scores:** GROUNDED **5** · SPECIFIC **5** · COMPLETE ON AXES **5** · DECISION-READY ROADMAP
**4** · HONEST UNCERTAINTY **5** · INDEPENDENT PASS **5** (three rounds, every criterion ≥4, zero
factual defects outstanding).

FINAL: PASS
