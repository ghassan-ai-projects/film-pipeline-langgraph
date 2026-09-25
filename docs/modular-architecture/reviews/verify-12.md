# Verify 12 — adversarial verification of `audit/12-post-delivery-constraints-budget.md`

- Verifier: independent agent (A6), did not write the audit.
- Verified at: `modular-app` = `fb85baa0e6b769b709791a96a89980089304bf13`, clean tree
  (`git status --porcelain` empty). All anchors read with `git show HEAD:<path>`.
- Method: line-by-line anchor/quote resolution; every `Reproduce` command re-run; every
  in-scope claim re-executed with `.venv/bin/python` and throwaway `/tmp` scripts; writer/reader
  sets re-derived by `grep -rn` over `src/` and `tests/`; prior-art lines re-read in
  `documentation/` and in the sibling audits `06`, `07`, `08`, `14`.

## 1. Verdict table

| Finding | Verdict | One-line reason |
|---|---|---|
| F-POST-01 | CONFIRMED | Two `AssemblyAgent` classes and both invocation paths reproduce exactly; only the "share no field" sentence is overstated. |
| F-POST-02 | CONFIRMED | The mismap and the never-produced `failure_decision` reproduce; the `AGENT_CLASS_BY_ID` grep evidence and the "five registries" count are wrong. |
| F-POST-03 | CONFIRMED | The dataclass/schema twin pairs all resolve and the zero-shared-field diff reproduces. |
| F-POST-04 | CONFIRMED | `is_complete=True` vs validator `blocked/0.0` with 5 blocking issues reproduced verbatim. |
| F-POST-05 | CONFIRMED | One artifact id, two schemas, one live writer + one test-only writer; the field split reproduces. |
| F-POST-06 | **DOWNGRADED** | Divergence reproduces, but owner B has **zero** production callers → recomputed Medium (2×4=8), not High (12). |
| F-POST-07 | CONFIRMED | Orphan `delivery_manifest` probe, writerless `DeliveryManifest`, and non-writing `delivery_node` all reproduce. |
| F-BUD-01 | CONFIRMED | Four divergent caps reproduce; counts are wrong (8 representations / 5 caps, ≥7 writer modules). |
| F-BUD-02 | CONFIRMED | G1-only refusal, inert G5, and the G2-vs-G3/G4 default divergence all reproduce. |
| F-BUD-03 | CONFIRMED | Zero non-init writers for `spent_usd`/`per_phase_spent_usd`/`SpendRecord`/`actual_cost_usd`; `remaining_usd == cap_usd`. |
| F-BUD-04 | CONFIRMED | `state["budget_cap"]` has no writer and the planner branch is dead (`base.py:56` discards `prepare`); O-class arguable. |
| F-BUD-05 | CONFIRMED | Tables are byte-identical today, grammars duplicate, no test binds them; parity/equality repro passes. |

Counts: **11 CONFIRMED, 1 DOWNGRADED, 0 REJECTED.** No finding cites a non-resolving anchor.

## 2. Expanded non-CONFIRMED row

### F-POST-06 — three independent validators of the assembly plan (DOWNGRADED)
- **Verdict: DOWNGRADED — High (12) → Medium (impact 2 × drift 4 = 8).**
- Drift proof **confirmed as written**: for
  `AssemblyPlan(plan_id='i', project_id='p', clips=['a','b'], clip_count=1)` owner A returns
  `['Clip count mismatch.']` and owner B returns `[]` (re-run; identical to the audit's output).
  Anchors `post/assembly_agent.py:135-144` (`validate_plan`, `:142-143` clip-count rule) and
  `post/validators.py:16-25` (`if plan.clip_count == 0:` / `"Clip count is zero."`) both resolve.
- **Counter-evidence to the severity:** the audit's own §2 table (line 98) records `PostValidator`
  as having **no invocation path** ("used only by `tests/unit/post/test_post.py`"); the production
  consumer on this seam is owner A via `mcp/tools/assembly.py:45`. `grep -rn "PostValidator" src/`
  returns only `post/validators.py` and the `post/__init__.py` façade. A divergence in a rule that
  no production path can reach cannot produce "wrong internal behavior" (impact 3) — it is a latent
  maintenance seam. Impact **2** is the defensible value; drift **4** stands (no test binds the two
  owners; `test_post.py:47-65` vs `:171-251`). Section 1.3's exclusion of *incompleteness* does not
  apply to a duplicated rule, so this stays a finding, at Medium.

## 3. Confirmed findings — additional corrections (do not change the verdict)

- **F-POST-01:** the sentence "The two classes do not share a single output field beyond the
  artifact name" is false. The finding's own reproduce command prints
  `shared = ['clip_order', 'missing_assets', 'project_id', 'schema_version', 'transitions']`
  (5 names; 4 domain fields + inherited `schema_version`). F-POST-05 line 416 already says
  "share only five field names", contradicting F-POST-01. The *semantic* payload split
  (manifest-only `audio_plan, color_plan, cut_id, delivery_mode, duration_total_seconds`;
  plan-only `clip_count, clips, notes, plan_id, total_duration_seconds`) reproduces exactly, so
  the drift proof survives.
- **F-POST-02:** (a) the title says "five registries" but six de-facto-owner sites are enumerated
  (`mvp/__init__.py:157`, `impl/registry.py:29`, `production.py:303`, `_context.py:49`,
  `_agent_routing.py:45`, `mock_responses.py:398`). (b) The parenthetical
  ``grep -rn "AGENT_CLASS_BY_ID" src/ tests/` → the registry and `graph/nodes/_agent.py:100` only``
  is wrong twice: the grep also matches `tests/unit/agents/test_impl_registry.py:7,22`, and
  `graph/nodes/_agent.py:100` matches `get_agent_class`, not `AGENT_CLASS_BY_ID` (which appears
  only in `impl/registry.py:18,36`). The substantive claim — no test compares the registry keys
  against contracts' `output_artifacts` — still holds (`test_impl_registry.py:22` is the tautology
  `len(d) == len(set(d))`).
- **F-POST-03:** the stated "schema-only" sets omit the inherited `schema_version`
  (`schemas/_base.SchemaBase`), so the reproduce output is
  `schema-only = ['cue_points','dialogue_track_refs','music_track_refs','schema_version','sfx_track_refs']`
  and likewise for `TransitionPlan`. The "zero fields shared" conclusion is unchanged.
- **F-POST-05:** the finding frames the split as two live writers, but its source table
  (F-POST-01, line 93) already proves `post/assembly_agent.persist` has **no `src/` caller**
  (`grep -rn "\.persist(" src/` → empty). Writer 2 is exercised only by
  `tests/unit/post/test_post.py:298`. The "existing divergence" is therefore live-writer vs
  test-only-writer; the drift proof remains valid under §1.6.3 but the blast-radius sentence
  should say so.
- **F-BUD-01:** three numeric defects. (1) "Distinct … representations: **7**" omits
  `ProjectProfile.budget_cap_usd` (`schemas/project.py:43`, written at
  `agents/impl/intake_agent.py:49`) which the audit's own scope row (line 77) and writer-table row
  (line 125) list — the count is **8**. (2) "four independent budget caps" likewise omits that
  fifth cap/value. (3) "Modules that write budget/cost state or derive a ceiling: **6**" groups
  `intake_agent.py`+`extractor.py` as one entry and omits `graph/nodes/_context.py`, which the same
  finding calls cap C (`:422-427`) — the honest count is **7** listed modules, **8** with
  `_context.py`, **9** if the defined-but-uncalled `orchestrator_state.update_budget_snapshot` is
  counted. The central claim (no single authoritative cap) is unaffected and reproduces.
- **F-BUD-04:** the O5 classification is arguable; the operative defect is a writerless state key
  `state["budget_cap"]` consumed by `gen_planner_agent.py:53,58` — O8 (missing contract) fits at
  least as well as O5. Severity 12 is defensible either way.

## 4. Missed in scope (post / delivery / constraints / budget seams)

1. **A fourth budget-cap vocabulary and an omitted reader: `graph/context_packets.py:121-123`.**
   `budget = state.get("budget_snapshot", {})` / `cap = budget.get("cap_usd", 0) …` /
   `parts.append(f"Budget cap: ${cap}")`. The real channel is namespaced —
   `orchestrator_state.py:59` `_BUDGET_SNAPSHOT = f"{_ORCH_NS}__budget_snapshot"` — so the plain
   key is never written by any module (`grep -rn "budget_snapshot" src/` → only this read, the
   `get_budget_snapshot` accessor, and typed model fields); the only writer of the plain key is a
   test, `tests/unit/graph/test_context_packets.py:175` `"budget_snapshot": {"cap_usd": 42}`.
   Reachable via `_agent_prompt_context.py:109-116` (`PHASE_BUILDERS.get("gen_planning")`).
   Caveat lowering impact: no template contains `{scoped_context}` (`grep -rn "scoped_context" src/`
   → only the assignment at `_agent_prompt_context.py:116`), so today the string is computed and
   dropped — impact 1–2. Still a budget reader/key the audit's "4 readers" row (line 124) omits and
   a fourth place a cap string is derived. Candidate: `budget` owns the key, or delete the read.
2. **`ProjectProfile.budget_cap_usd` is a distinct cap representation.** `schemas/project.py:43`
   `budget_cap_usd: float | None = Field(default=None, ge=0, description="Hard spend cap.")`,
   written from model output at `agents/impl/intake_agent.py:49` and read by nothing
   (`grep -rn "budget_cap_usd" src/` → writers only). It belongs in F-BUD-01's cap inventory and in
   the §3 writer map as its own row, not merged into the `ProjectConstraints` row.
3. **A third name in the delivery seam: `graph/state_schema.py:162` `delivery_manifest_ref: str`.**
   The state ref name matches the *writerless* artifact id, while the only writer emits
   `delivery_package` (`post/delivery_packaging_agent.py:149`) and `qc.py:356` probes
   `("delivery_manifest", "delivery_package")`. F-POST-07 cites the qc probe, the schema, and
   `wrapup.delivery_node` but not this state-key, which strengthens its O8 case.
4. **`post/validators.py:38-46` `validate_delivery` consumes owner A's verdict**
   (`if not package.is_complete: … missing = package.missing_items`), a third place where the
   completeness policy is observable; F-POST-04's blast radius lists only the packaging agent, the
   validation impl, `qc.py`, and the MCP tool. Minor, same owner as F-POST-04.

## 5. Disputes requiring the author to fix

- **D1 (F-POST-01).** Replace "do not share a single output field" with the executed result —
  they share four domain fields plus inherited `schema_version`; make it consistent with F-POST-05.
- **D2 (F-POST-02).** Fix the title count (five → six) and the `AGENT_CLASS_BY_ID` grep evidence —
  the audit's own command contradicts the stated result.
- **D3 (F-POST-03 / F-POST-07).** Add `schema_version` to the schema-side field lists so the quoted
  results match the reproduce commands (§1.6.2/§1.6.4).
- **D4 (F-BUD-01).** Recompute the representation/cap/module counts per §3 above, or state the
  counting rule that excludes `ProjectProfile.budget_cap_usd` and `_context.py`.
- **D5 (prior art, A7).** Line drift in sibling citations: `06-generation-runtime-and-ledger.md`
  F-GEN-10 is at **:467**, not `:463`; the `estimated_cost_usd` writer-table row is at **:663**,
  not `:651`; the "third plan/cost builder" note is at **:44**, not `:43`. `08-validation-and-review.md`
  F-VR-07 does **not** say the delivery validator is absent from the QC dispatch paths — it says it
  is absent from `_WORKER_NODES` and the `qc`-phase runner sets while present at `nodes/qc.py:367`
  for phase `delivery`; reword F-POST-07's prior-art sentence.
- **D6 (F-BUD table row 122).** The third cost-estimate producer is cited as
  `mcp/tools/generation/planning.py:64-71`, but that range is an `_error` return and an import; the
  producer is `:93-100` (`estimated_costs = {shot_id: estimate_cost_for_duration(…)`).
- **D7 (F-POST-05).** State explicitly that writer 2 is test-only (`post` `persist` has no `src/`
  caller) so the severity's impact 4 is read against a latent, not live, production divergence.
- **D8 (F-BUD-04).** Re-state the O-class as O8 (writerless contract key) or justify O5.

## 6. Candidate-owner collisions for reconciliation

- **`constraints` vs `budget` — real collision.** §6.3 gives `constraints` the extraction grammar
  and `ProjectConstraints` (including `budget_cap_usd`, `constraints/extractor.py:154`), while §6.4
  gives `budget` "the cap value (F-BUD-01)" and a `cap_for` that falls back to
  `ProjectConstraints.budget_cap_usd`. Both modules cannot own the user-stated cap. Needed rule:
  `constraints` produces the value; `budget` owns resolution/precedence and is the only writer of
  `BudgetState`.
- **`budget` vs `generation` — boundary is drawn but not scheduled.** §6.4's non-goals correctly
  leave `estimated_cost_usd` and ledger rows to `generation`/`06`, and F-BUD-01 explicitly defers
  F-GEN-10. But F-BUD-02's sketch requires editing `generation/ledger.py:108` (deleting the `-1.0`
  default) and F-BUD-03's `record_spend` is called from `generation/executor.py:257,293,399`; the
  roadmap must sequence that as `generation`-consumer edits, or ownership will read as shared.
- **`delivery` vs `validation` — no collision.** F-POST-04/07 put the required-artifact table and
  the writer in `delivery`, and the validator consumes the table; §6.2 states the non-goal
  explicitly. Consistent.
- **`post-production` vs `schemas` — no collision.** F-POST-03 nominates `schemas` for the models
  and §6.1 has `post-production` own behavior with "contract types live in `schemas/assembly.py`
  only". Consistent.

## 7. Overall verdict

The cluster's factual core is sound — both `AssemblyAgent` implementations, the registry mismap,
the delivery-completeness divergence, the orphan delivery id, and the split budget authority all
reproduce independently — but one severity (F-POST-06) is overstated for a dead second owner, three
counts in the budget inventory are wrong, F-POST-02's grep evidence contradicts its own command,
and the audit misses a fourth budget-cap read (`context_packets.py:121-123`) plus the fifth cap
(`ProjectProfile.budget_cap_usd`); with the listed corrections it is **not blocking**.
