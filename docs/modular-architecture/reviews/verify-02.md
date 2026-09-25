# verify-02 — adversarial verification of `audit/02-orchestration-state-and-routing.md`

- **Target:** `docs/modular-architecture/audit/02-orchestration-state-and-routing.md` (16 findings, F-OST-01…16).
- **Repo / commit:** `${REPO_ROOT}`, branch `modular-app` @
  `fb85baa0e6b769b709791a96a89980089304bf13` (`git rev-parse HEAD`). Working tree: docs only.
- **Verifier:** independent pass (bar A6); did not write the audit. Bar read in full:
  `docs/modular-architecture/00-methodology-and-quality-bar.md` §1.4–§1.7, §2.
- **Method:** every anchor opened at HEAD; every `Reproduce` command re-run (`grep`, `.venv/bin/python`,
  `/tmp` probe scripts); drift proofs reproduced. Repo not modified.
- **Cross-checked against:** `docs/modular-architecture/enola-out/insights.json` +
  `enola-architecture-facts.md`, `audit/01-phase-model-and-transitions.md`.

---

## Verdict table

| id | verdict | one-line reason |
|---|---|---|
| F-OST-01 | CONFIRMED-WITH-FIX | drift proof valid (LangGraph silently drops the un-declared key); "eleven keys" is 10. |
| F-OST-02 | **DOWNGRADED** | divergence real, but the stated drift proof ("grep … returns nothing", "no test executes ORCHESTRATOR_STALLED") is false. |
| F-OST-03 | CONFIRMED | predicate count reproduces (18), `IssueRecord` unused, `issues` channel raw dict. |
| F-OST-04 | CONFIRMED | anchors + mutation scenario valid; severity/owner disputed vs audit 01 F-PHASE-03. |
| F-OST-05 | CONFIRMED | four veto sites, two scopes, anchors exact. |
| F-OST-06 | CONFIRMED | `consensus_report` has **no** writer anywhere in `src/`; confirmed mechanically + schema absent. |
| F-OST-07 | CONFIRMED-WITH-FIX | substance real; two anchors do not resolve (`_repair_loop.py:46`, `nodes/qc.py:386-404`). |
| F-OST-08 | CONFIRMED-WITH-FIX | reducer duplication real; the stale-report asymmetry in the drift proof is overstated and one clause is vacuous. |
| F-OST-09 | CONFIRMED | both renderers present; `operator._recommendation` has no test. |
| F-OST-10 | CONFIRMED | two readers of `require_human_approval`, anchors exact; severity disputed vs audit 01 F-PHASE-07. |
| F-OST-11 | CONFIRMED-WITH-FIX | mutation valid; "grep convergence_round tests/ finds none" is false. |
| F-OST-12 | CONFIRMED | reproduce command prints exactly `['_orchestrator__budget_snapshot']` / `'Budget cap: $0'`. |
| F-OST-13 | CONFIRMED | three representations; `update_provider_health` production-caller-free. |
| F-OST-14 | CONFIRMED | typed producer unused; only invocation is `wrapup.py:26`. |
| F-OST-15 | CONFIRMED | reproduce prints exactly the claimed output; owner overlaps audit 01 `phase-model`. |
| F-OST-16 | CONFIRMED-WITH-FIX | channel split + `None []` reproduce; `state_schema.py:115-118` cites the wrong file. |

Counts: **9 CONFIRMED, 6 CONFIRMED-WITH-FIX, 1 DOWNGRADED, 0 REJECTED.**

---

## Expanded non-CONFIRMED / corrected rows

### F-OST-01 — CONFIRMED, count corrected
- Verified: `orchestrator_state.py:23,27-64` defines **10** `_orchestrator__*` constants; `state_schema.py:188-197`
  declares the **same 10** fields. The audit's "the same eleven keys" is wrong (§1.6.4 count).
  `grep -c "_orchestrator__" src/film_pipeline/graph/state_schema.py` → `10`.
- Drift proof independently validated, including the LangGraph mechanism. Probe at HEAD
  (`StateGraph(S)` with `S(TypedDict)`; node returns `{"a":1,"totally_unknown_key":2}`):
  `result: {'a': 1}` — langgraph 0.2.76 **silently drops** the un-declared key, so the described
  "pass a constant+registry row, no schema field" mutation really is silent. `graph.py:170`
  confirms `builder = StateGraph(StudioGraphState)`.
- Both guard directions confirmed one-sided: `test_channel_registry.py:70-76` compares
  constants↔registry (both ways) and `:79-85` only `schema_keys - registered ⊆ ∅`; no test performs
  `constants == schema_keys` (grep for `== schema_keys`/`constants ==` → 0 hits).
- Severity 3×3=9 holds. Required fix: change "eleven" → "ten".

### F-OST-02 — DOWNGRADED (High 15 → High 12)
- Anchors all resolve: `orchestrator_state.py:362-367` (`max_rounds: int = 5` at `:362`),
  `mark_stalled :370-376`, `edges.py:90-93` (`state["_stalled_phase"] = phase` at `:93`),
  `_repair_loop.py:72-80` (`max_rounds=3` at `:72`), readers `_action_routing.py:156`,
  `approval.py:216`, `app/services/operator.py:465`, prompt literal
  `agents/prompt_templates/defaults/production.py:386`. Two representations + three thresholds: real.
- **Counter-evidence to the drift proof.** The audit states: *"No test executes `_start_round`,
  `max_rounds=3`, or `ORCHESTRATOR_STALLED` at all — `grep -rn "max_rounds=3\|_start_round\|ORCHESTRATOR_STALLED" tests/`
  returns nothing"*. Re-run at HEAD:
  ```
  tests/unit/graph/test_real_human_gates.py:140: ... issue.get("code") == "ORCHESTRATOR_STALLED"
  tests/unit/graph/test_real_human_gates.py:148: ... issue.get("code") == "ORCHESTRATOR_STALLED"
  ```
  The command returns 2 hit lines (plus `.pyc` binary matches). `test_real_human_gates.py:117-150`
  executes `after_approval`, asserts `state["_stalled_phase"] == "shot_bible"` (`:135`) and the
  `ORCHESTRATOR_STALLED` issue (`:142`); `tests/unit/test_graph.py:54-67` and
  `tests/e2e/test_orchestrator_decision_loop.py:148-154` also exercise `is_stalled`. So the
  "absence of any test" claim is false for the *representation* half of the seam.
- What still holds: the **cap** divergence is untested — every test passes `max_rounds=` explicitly
  (`test_orchestrator_state.py:157,164`, `test_orchestrator_decision_loop.py:64,154`) or sets
  `stalled=True`, and no test calls `_start_round` (grep: 0 hits). Mutating `:362` `5→2` therefore
  still fails nothing. Recompute drift 5 → **4** because one of the two representations is pinned;
  score **3×4 = 12, High**. Required fix: delete the false sentence and the quoted grep command.

### F-OST-07 — CONFIRMED-WITH-FIX (anchors)
- Substance verified: `graph.py:115` binds `qc_node` to `build_qc_subgraph()`;
  `_repair_loop.py:38-50` `_PHASE_NODES` binds `"qc": qc_node` and is re-exported through
  `nodes/approval.py:10,21` and consumed by `app/_graph_exec.py:449-452`; translation #1 at
  `subgraphs/qc.py:228-246` (quote at `:239`), translation #2 at `nodes/qc.py:406-415`; only the node
  path synthesises a consensus (`nodes/qc.py:40,95-112,170-183`; `ConsensusBuilder` appears nowhere
  in `subgraphs/qc.py`). Existing channel divergence (`subgraphs/qc.py:68-73` vs `nodes/qc.py:30,91,111,182`)
  is real.
- **Two anchors do not resolve:**
  - `_repair_loop.py:46` quoted as `'"qc": qc_node,'` — line 46 is `"generation": generation_node,`;
    the quote is at **`:47`** (`grep -n '"qc": qc_node'`). Repeated in the §3 ownership-map row for
    "QC lifecycle".
  - `nodes/qc.py:386-404` quoted as `'"issue_id": f"val:{report.validator_id}:{finding.code}",'` —
    that line is **`:409`**; `:386-404` is `_append_validator_report` up to `_track_matrix_row_updates`.
- Drift proof (mark `blocking_issues` as `"warning"` in `subgraphs/qc.py:233`) is valid. Severity
  3×4=12 holds once anchors are corrected.

### F-OST-08 — CONFIRMED-WITH-FIX (drift proof overstated)
- Code claims verified: `state_schema.py:171-174` reducers, `:208` `_validation_reports` un-reduced,
  `:210-211` `_qc_reports`/`_qc_raw_reports` with `add`; `app/_graph_exec.py:467-472` registry omits
  the QC channels and `:481` union-merges `_routing_decisions`/`_validation_reports`. No test compares
  the two merge paths (`run_phase_node` is exercised only through `rt._run_phase_node`, e.g.
  `tests/unit/mcp/tools/test_bibles.py:54-57`).
- **Counter-evidence.** (a) The drift proof says stale BLOCKED reports "survive forever on the
  manual/repair path" as the distinguishing effect, but `_qc_raw_reports` is an `add` channel that is
  never cleared — `subgraphs/qc.py:264-273` clears only `_qc_reports` — and
  `reduce_qc_reports` publishes `"_validation_reports": raw` built from the whole accumulated
  `state.get("_qc_raw_reports", [])` (`:259,266`). On the compiled-graph path a second QC run
  therefore re-publishes the earlier run's reports into `_validation_reports` too. The asymmetry is
  not "graph clears / manual keeps".
  (b) The clause "`_qc_reports`/`_qc_raw_reports` are absent from the manual registry, so they would be
  overwritten rather than accumulated" is vacuous: the manual path runs `_PHASE_NODES["qc"]`
  (`nodes/qc.qc_node`), and no node reachable from `run_phase_node` ever writes `_qc_reports`
  (`grep _qc_reports src/` → only `subgraphs/qc.py` and `state_schema.py`).
- Severity: keep High, drift 4 → **3** (impact 3 × 3 = **9**) because the demonstrated consequence is
  not exclusive to the manual path. Required fix: restate the divergence as "the manual merge policy
  is a hand-maintained duplicate of `state_schema`" and drop the stale-report asymmetry claim, or
  supply a run showing the graph path clears while the manual path does not.

### F-OST-11 — CONFIRMED-WITH-FIX (false negative grep)
- Anchors verified: `orchestrator_state.py:23,27-64`; `approval.py:62-64` (`startswith("_orchestrator__")`),
  `:267,293`; `_repair_loop.py:70,78,238-240`; `_context.py:81`. The rename mutation is valid: the
  two hard-coded literals at `_repair_loop.py:70,78` would be dropped by LangGraph (probe in F-OST-01)
  while `is_stalled` reads the renamed channel — no test reads the context key
  (`grep -rn '"convergence_round"' tests/` → 0 hits).
- **Counter-evidence:** the audit says *"`grep -rn convergence_round tests/` finds none"*. Re-run:
  5 hits (`test_orchestrator_state.py:156,163`, `test_orchestrator_decision_loop.py:62,63,153`) —
  all `increment_convergence_round`, a different identifier. The intended command must anchor the
  quoted key. Severity 4×3=12 holds; fix the command text.

### F-OST-16 — CONFIRMED-WITH-FIX (wrong file anchor)
- Substance fully verified: `orchestrator_state.py:43,307-327` (`record_routing_decision`, zero
  production callers); `_agent_handoff.py:125-142` writes `_routing_decisions`
  (`"routing_reason"` at `:135`); readers `mcp/tools/state.py:39` (reported `:49`) and
  `app/services/operator.py:232` (reported `:244`). Reproduce command prints exactly `None []`.
- **Anchor error:** the "shadow namespace; deletion scheduled with D13/P1 wire-or-delete" quote is at
  **`orchestrator_state.py:117`** (the `_ROUTING_DECISIONS` `OrchChannelSpec` note). The cited
  `state_schema.py:115-118` is `project_id / current_phase / approved / completed`. `state_schema.py`
  contains no such string.
- Severity 2×4=8 holds.

---

## Missed in scope (my own evidence)

1. **`_orchestrator__active_review_cycles` is a third dead channel with a live operator reader —
   no finding block.** `start_review_cycle`/`advance_review_round`/`close_review_cycle`
   (`orchestrator_state.py:228,246,255`) have **zero** production callers
   (`grep -rn "start_review_cycle\|advance_review_round\|close_review_cycle" src/` → only the
   definitions; all other hits are `tests/unit/graph/test_orchestrator_state.py`), yet
   `mcp/tools/state.py:40` reads `ostate.get_active_review_cycle(...)` and publishes it at `:55` as
   `active_review_cycle`. `ensure_orchestrator_state` initialises it to `[]` (`:523`), so the MCP
   surface always reports `None`/empty while the review-cycle lifecycle is dead. This is the exact
   F-OST-16 pattern (O3 split/no-writer state authority) but it is only a row in the §3 ownership map
   and is absent from §5's public contract. **Recomputed severity: Medium (impact 2 × drift 3 = 6)**
   — no test crosses the owner API and the MCP reader, so a partial wire would be silent.
2. **§4 clean-concern #4 overstates "one projection".** The action/reason projection is single
   (`router.get_blockers_for_state`), but operator-facing *blocking-issue lists* are re-derived again
   at `app/services/operator.py:453-459` (used at `:276` for `review_package.open_issues` and at
   `:299` for `ValidationWorkspace.blocking_issues`) and `mcp/tools/review.py:63-65`. These are inside
   F-OST-03's 18-site grep, but §4's "the operator-facing blocker list has one projection" contradicts
   F-OST-03 and should be narrowed to the action/reason projection.
3. **Cross-boundary flag not in the ownership map:** `_resume_to_repair` is written by
   `app/_graph_exec.py:392` and read/cleared inside `graph` (`graph.py:193`, `_repair_loop.py:198`,
   reset `:242`). It is an app→graph state write the §3 table does not list (weak single-writer, but
   it is the same class of seam the audit is cataloguing).

**Enola cross-check.** `enola` squares with the coupling the audit describes: cycle **C3**
(`graph ↔ graph/nodes ↔ graph/orchestrator_validators ↔ graph/subgraphs`) is exactly the edge set that
F-OST-07/F-OST-11 keep re-using, and enola measures `graph/orchestrator_state` at **38/38 exported
surface (100%)** — i.e. the module the audit nominates as sole owner currently has *no* encapsulation
boundary. Audit 02 never cites C3 or the 100%-export fact; §5 should adopt both (a boundary test is
already hinted at in F-OST-11's extraction sketch). No enola cycle contradicts any audit-02 claim.

---

## Disputes requiring the author to fix

1. **False mechanical-absence evidence in two drift proofs** — F-OST-02 (`grep … returns nothing`;
   `ORCHESTRATOR_STALLED` is asserted at `test_real_human_gates.py:140,148`) and F-OST-11
   (`grep convergence_round tests/ finds none`; 5 hits). These are §1.6.3/§1.6.4 failures, not typos:
   both sentences are load-bearing for "no test fails because Z".
2. **Two anchors do not resolve** — F-OST-07 `_repair_loop.py:46`→`:47` and `nodes/qc.py:386-404`→`:409`;
   F-OST-16 `state_schema.py:115-118`→`orchestrator_state.py:117`. §1.6.1 requires the line to point at
   the defining line.
3. **Count error** — F-OST-01 "eleven keys" → ten (`state_schema.py:188-197`).
4. **F-OST-08 drift proof overstated / one clause vacuous** (see above).
5. **Candidate-owner conflict with audit 01.** Audit 01 §"Candidate module boundary" establishes a
   single `phase-model` that owns `PHASE_ORDER`, `PHASE_GATES` (from `APPROVAL_GATES`),
   `successor`, the phase-class sets and the gate-mode predicate, and explicitly says `graph` keeps
   `_PHASE_DEFAULT_AGENTS` and derives `_PHASE_TO_NODE`/`_PHASE_NODES`. Audit 02 §5 claims the
   orchestrator-state owner "Owns (N) … the phase catalog (order, gate label, phase node, default
   agent, successor)", and F-OST-15 nominates "a single `phases.py` phase catalog". Those conflict:
   §5 must defer the phase catalog to audit 01's `phase-model` (F-OST-04 already does this in its
   candidate-owner line — make §5 consistent) and F-OST-15's owner must be `phase-model`'s
   phase-catalog projection, not a second catalog.
6. **Cross-cluster duplicate findings with conflicting severities.** F-OST-04 ≡ audit 01 F-PHASE-03
   (High 3×4=12) but rated Medium 6; F-OST-10 ≡ audit 01 F-PHASE-07 (Medium 3×2=6) but rated High 9;
   F-OST-15 ≈ audit 01 F-PHASE-02 (Critical 4×4=16) and F-PHASE-08 (Medium 6) but rated Medium 8. At
   least F-OST-04 understates impact: telling the operator a gate name the router invented is wrong
   internal behavior (impact 3), and its own evidence ("no test relates the two maps") implies drift
   4–5, i.e. **≥12, High**, matching F-PHASE-03. Each of these three should either cite the sibling
   audit as prior art (A7) and state what is new, or be folded into it.
7. **`issues`/18-sites count caveat.** `grep … \| wc -l` reproduces 18, but 4 hits are a different
   severity domain (`config/resolver.py:25`, `mcp/tools/projects.py:78`, and the two
   `validation/impl/*` internal `i.severity` checks). The finding should say "18 `severity ==
   "blocking"` comparisons, 14 of them over `state["issues"]`" so the count is not misread.

---

## Overall verdict

**No finding is rejected outright — the substance of all 16 holds — but the file does not yet meet
bar A2/A6 as written: two drift proofs cite a mechanically false "grep returns nothing" absence, two
findings cite line/file anchors that do not resolve, one count and one drift-proof consequence are
wrong, and the §5/F-OST-15 phase-catalog ownership conflicts with audit 01's `phase-model`.**
`consensus_report` truly has no production writer (and langgraph 0.2.76 silently drops that key), so
F-OST-06 — the highest-value claim — is confirmed. Fix the seven disputes above and this audit ships.
