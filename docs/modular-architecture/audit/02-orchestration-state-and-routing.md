# 02 — Audit: Orchestration State and Routing

- **Repo:** `${REPO_ROOT}`
- **Branch / commit audited:** `modular-app` @ `fb85baa0e6b769b709791a96a89980089304bf13` (`git rev-parse HEAD`
  → `fb85baa0e6b769b709791a96a89980089304bf13`, clean working tree at start of audit).
- **Methodology:** `docs/modular-architecture/00-methodology-and-quality-bar.md` (read in full; conforms to §1.6,
  §1.7, §2). Every anchor below was read at this commit. Line numbers drift; verify at HEAD.
- **Cluster:** "Orchestration state and routing" — state fields, blocker lists, failure decisions, budget
  decisions, repair loops, routing rules, and every module that independently defines, mutates, or interprets
  them.
- **Independent verification (A6):** verified by a second agent in
  `docs/modular-architecture/reviews/verify-02.md` @ HEAD `fb85baa`: **9 CONFIRMED, 6 CONFIRMED-WITH-FIX,
  1 DOWNGRADED, 0 REJECTED** (F-OST-01, -07, -08, -11, -16 = CONFIRMED-WITH-FIX; F-OST-02 = DOWNGRADED;
  F-OST-03 clause "18 comparisons, 14 over `state[\"issues\"]`" = verifier count error, corrected in the file
  to the verified 11/7 split; all other findings CONFIRMED). All seven disputes in that file's "Disputes
  requiring the author to fix"
  section are resolved in this revision (fix log below). The verifier's missed seam
  (`_orchestrator__active_review_cycles`, a dead channel with a live operator reader) is added as
  F-OST-17; its two further corrections (the §4 "one projection" overstatement and the missing
  `_resume_to_repair` ownership row) are applied in §3/§4, and its phase-catalog ownership conflict is
  resolved in §7.
- **Revision log (this file):** (1) F-OST-01 count 11→10; (2) F-OST-02 downgraded High 15→12 and its
  drift proof rewritten to the cap-only divergence; (3) F-OST-07 anchors `src/film_pipeline/graph/nodes/_repair_loop.py:46`→`:47`,
  `src/film_pipeline/graph/nodes/qc.py:386-404`→`:406-415` (quote `:409`); (4) F-OST-16 anchor `src/film_pipeline/graph/state_schema.py:115-118`→
  `src/film_pipeline/graph/orchestrator_state.py:114-118` (quote `:117`); (5) F-OST-08 drift proof restated, High 12→9; (6) F-OST-03
  count caveat added; (7) cross-cluster severity/owner conflicts with audit 01 resolved in §5; (8) F-OST-04
  raised Medium 6 → High 12 (class O4 → O1+O2) and re-owned to `phase-model`, matching F-PHASE-03; (9) F-OST-10
  reconciled Medium 9 → 6, matching F-PHASE-07, owner → `phase-model`; (10) F-OST-15 reconciled Medium 8 → 6,
  matching F-PHASE-08, owner → the `phase-model` phase-catalog projection (F-PHASE-02 cited for the umbrella
  defect); (11) F-OST-17 added (the verifier's missed seam); (12) F-OST-18 blast-radius reachability corrected —
  `OperatorService.run_validation` has zero non-test callers, there is no operator dashboard/TUI in this repository,
  and no shipped entry point reaches the dropped patch; (13) F-OST-18 prior-art grep corrected to exclude this file
  (the old command counted this file's own text): the key is named in **no other** `audit/` file (exit 1).
  (Note: the verifier's F-OST-02 and F-OST-11 quotes of a "grep returns nothing" claim describe the
  pre-revision draft; F-OST-11's false grep was already replaced before verification closed, and the
  replacement is retained here with its command anchored to the quoted key. The verifier's suggested F-OST-03
  split — "18 comparisons, 14 over `state[\"issues\"]`" — does not reproduce against the file's own command:
  the 18 hits divide 11 over the graph `state[\"issues\"]` channel and 7 over other severity domains
  (config conflicts ×2, failure decisions, and four validator-internal lists); the file states the verified 11/7
  split and enumerates the 7.)
- **Findings after this revision: 18** — **0 Critical, 13 High, 5 Medium, 0 Low**. The 17 findings verified at
  `fb85baa` keep the verdicts recorded in the A6 bullet above (12 High / 5 Medium, revision log items 1–11); the one
  added after that verification (F-OST-18) is now verified as well — `reviews/verify-16.md` §1 returns
  **CONFIRMED-WITH-FIX**, the 3 × 5 = 15 score stands, and its two printed defects are fixed in revision-log
  items 12–13.
- **Added post-verification (verified by `reviews/verify-16.md` §1: CONFIRMED-WITH-FIX, High 3 × 5 = 15; the two
  printed defects it names are fixed in this revision):** F-OST-18 — the QC validator→matrix-patch handoff is an
  undeclared, untyped key on the state dict (`_pending_row_updates`), and the app's on-demand `run_validation` fills
  it with no consumer, so the per-row matrix patch is silently dropped on that path (High, impact 3 × drift 5 = 15;
  uncovered by the adversarial coverage pass — `reviews/adversarial-coverage.md` §H9, confirmed by
  `reviews/orchestrator-verification-notes.md` §V15).

---

## 1. Coverage

Scope files, read in full (line counts from `wc -l` at HEAD). Verdict = "clean, no distributed ownership
found" or "has findings".

| File | Lines | Verdict |
|---|---|---|
| `src/film_pipeline/graph/orchestrator_state.py` | 537 | read fully — owner of the key model; **has findings** (F-OST-01, -02, -11, -12, -13, -14, -16, **-17**) |
| `src/film_pipeline/graph/_action_routing.py` | 394 | **has findings** (F-OST-03, -04, -05, -06, -15) |
| `src/film_pipeline/graph/_agent_routing.py` | 211 | **has findings** (F-OST-15) |
| `src/film_pipeline/graph/consistency.py` | 84 | clean — read-only consumer of `get_approved_refs` (`:65-69`); writes nothing |
| `src/film_pipeline/graph/context_packets.py` | 186 | **has findings** (F-OST-12) |
| `src/film_pipeline/graph/services.py` | 137 | clean for this cluster — it is a service-locator object (`GraphServices`, `SERVICES_KEY` `:137`); it owns no orchestration state. Nodes reach it only through `_get_services` (`src/film_pipeline/graph/nodes/_shared.py:16-26`) |
| `src/film_pipeline/graph/nodes/_agent.py` | 238 | clean for this cluster — writes only `_last_kb_context_ref` (`:120`); no orchestrator key |
| `src/film_pipeline/graph/nodes/_agent_artifacts.py` | 150 | clean — single writer path for candidate refs (`:43-48`), guard-tested |
| `src/film_pipeline/graph/nodes/_agent_handoff.py` | 143 | **has findings** (F-OST-16); otherwise clean — registry-driven propagation, no local key list (`:45-73`), guard-tested |
| `src/film_pipeline/graph/nodes/_agent_prompt_context.py` | 149 | clean — read-only prompt context; no state writes |
| `src/film_pipeline/graph/nodes/_context.py` | 465 | **has findings** (F-OST-11) |
| `src/film_pipeline/graph/nodes/_generation_batch_planning.py` | 165 | clean for this cluster — writes only `generation_requests`/`issues`; no orchestrator key |
| `src/film_pipeline/graph/nodes/_generation_prompts.py` | 178 | clean — read-only (`state.get` only) |
| `src/film_pipeline/graph/nodes/_repair_loop.py` | 243 | **has findings** (F-OST-02, -05, -11) |
| `src/film_pipeline/graph/nodes/_shared.py` | 210 | **has findings** (F-OST-04, -05, -10) |
| `src/film_pipeline/graph/nodes/_visual_matrix_coverage.py` | 149 | clean — read-only (`script_ref`, `project_id`) |
| `src/film_pipeline/graph/nodes/approval.py` | 294 | **has findings** (F-OST-05, -11) |
| `src/film_pipeline/graph/nodes/generation.py` | 132 | clean for this cluster — uses `_phase_gate_updates` (`:108`) |
| `src/film_pipeline/graph/nodes/prep.py` | 382 | **has findings** (F-OST-05) |
| `src/film_pipeline/graph/nodes/qc.py` | 435 | **has findings** (F-OST-07, -08) |
| `src/film_pipeline/graph/nodes/visual.py` | 632 | clean for this cluster — only `set_execution_brief` (`:92-97`) and gate updates |
| `src/film_pipeline/graph/nodes/wrapup.py` | 60 | **has findings** (F-OST-14) |
| `src/film_pipeline/graph/nodes/__init__.py` | 114 | clean — pure re-export surface |
| `src/film_pipeline/graph/subgraphs/qc.py` | 311 | **has findings** (F-OST-07, -10) |
| `src/film_pipeline/graph/orchestrator_validators/__init__.py` | 40 | clean — no state writes |
| `src/film_pipeline/graph/orchestrator_validators/_shared.py` | 66 | clean — pure issue constructors |
| `src/film_pipeline/graph/orchestrator_validators/brief.py` | 238 | clean — reads the brief through the owner accessor (`:21-23`) |
| `src/film_pipeline/graph/orchestrator_validators/planning_gates.py` | 268 | clean — pure predicates over loaded artifacts |
| `src/film_pipeline/graph/orchestrator_validators/prep_gates.py` | 155 | clean — pure predicates |

Read beyond the scope list because the grep sweep named them as writers/readers of the same state:
`graph/state_schema.py`, `graph/router.py`, `graph/edges.py`, `graph/graph.py`, `app/services/operator.py`,
`app/_graph_exec.py`, `app/_resume.py`, `app/runtime.py`, `app/_provider_seeds.py`, `app/health.py`,
`mcp/tools/state.py`, `mcp/tools/review.py`, `mcp/tools/projects.py`, `cli/driver.py`,
`schemas/runtime_state.py`, `schemas/issue.py`, `schemas/failure.py`, `agents/mvp/__init__.py`,
`agents/impl/qc_synthesis_agent.py`, plus the guard tests in `tests/unit/graph/*`, `tests/unit/mcp/tools/*`,
`tests/integration/test_dynamic_routing.py`, `tests/e2e/test_orchestrator_decision_loop.py`.

Scope-file sweep commands (re-runnable):

```bash
# who imports the orchestrator-state owner
grep -rn "orchestrator_state" src/ --include=*.py
# who writes an orchestrator key outside the owner
grep -rn '"_orchestrator__' src/ --include=*.py | grep -v orchestrator_state.py
# who writes any state key directly
grep -rn 'state\[[^]]*\] *=' src/film_pipeline/ --include=*.py | grep -v '=='
```

---

## 2. Findings

### F-OST-01 — The orchestrator channel-key set is defined twice (constants vs TypedDict) and parity is one-directional

- **Class:** O1 (duplicated normative model) + O4 (parallel registries)
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** Which state keys belong to the orchestrator domain, and therefore which survive the LangGraph
  node boundary.
- **De-facto owners:**
  - `src/film_pipeline/graph/orchestrator_state.py:23` — builds every key from one namespace constant —
    `"_ORCH_NS = \"_orchestrator\""` / `:27` `"_CANDIDATE_REFS = f\"{_ORCH_NS}__candidate_refs\""`
  - `src/film_pipeline/graph/state_schema.py:188` — re-spells the same ten keys as typed fields —
    `"_orchestrator__candidate_refs: dict[str, str]"` (through `:197`; `grep -c "_orchestrator__"
    src/film_pipeline/graph/state_schema.py` → `10`, matching the ten owner constants at
    `src/film_pipeline/graph/orchestrator_state.py:27-64`)
  - `tests/unit/graph/test_channel_registry.py:79-85` — the parity guard only proves `schema ⊆ registry` —
    `"missing = schema_keys - registered"` … `"assert not missing"`
- **Drift proof:** mutation scenario. Add a new domain to the owner, e.g.
  `_BUDGET_ALERTS = f"{_ORCH_NS}__budget_alerts"` at `src/film_pipeline/graph/orchestrator_state.py:59` plus an `ORCH_CHANNELS` row.
  `test_every_orchestrator_constant_has_a_registry_row` (`:70-76`) passes (constant has a row) and
  `test_every_schema_declared_orchestrator_key_has_a_registry_row` (`:79-85`) passes (no *schema* key is
  unregistered), yet `StudioGraphState` has no such field, so LangGraph drops every write to it — the owner's
  keys and the graph's persisted schema silently disagree. No existing test compares the two sets for equality
  (`assert not missing` only, never `constants == schema_keys`).
  The dropping mechanism is **independently verified** (verify-02): a probe building
  `StateGraph(StudioGraphState)` and returning `{"totally_unknown_key": 2}` from a node yields
  `result: {'a': 1}` on langgraph 0.2.76 — the un-declared key is silently discarded.
- **Reproduce:**
  ```bash
  grep -n "_candidate_refs\|_execution_brief" src/film_pipeline/graph/orchestrator_state.py src/film_pipeline/graph/state_schema.py
  grep -c "_orchestrator__" src/film_pipeline/graph/state_schema.py   # 10
  grep -n "missing = \|unknown = " tests/unit/graph/test_channel_registry.py
  ```
- **Blast radius:** every orchestrator state domain (`src/film_pipeline/graph/orchestrator_state.py:27-64`); a key that exists in one
  model and not the other is either un-persistable or unreadable. User-visible: orchestrator decisions vanish
  across checkpoints.
- **Candidate owner module:** `graph/orchestrator_state.py` — sole definer of the orchestrator state grammar.
- **Extraction sketch:** make `state_schema.py` derive its orchestrator fields from a single exported tuple
  (e.g. `ORCH_CHANNELS`) or add **both** directions to the parity test (`constants == schema_keys`); expose a
  guard test `test_orchestrator_key_sets_are_identical`.
- **Prior art:** `documentation/reviews/arch-lens-dataflow.md:34` claims the parity test "assert every
  `_orchestrator__*` appears in `ORCH_CHANNELS`"; at HEAD the test runs one direction only. Still present,
  narrowed.

### F-OST-02 — "Stalled phase" has two representations and three thresholds

- **Class:** O3 (split state authority) + O5 (policy-by-branch)
- **Severity:** High (impact 3 × drift 4 = 12) — downgraded from 3 × 5 = 15 by verify-02 because one of the
  two representations *is* pinned by tests (see drift proof), leaving only the cap/threshold divergence silent.
- **Concern:** What makes a phase "stalled" and which state records it.
- **De-facto owners:**
  - `src/film_pipeline/graph/orchestrator_state.py:362-367` — canonical predicate over `_CONVERGENCE` —
    `"return bool(conv.get(\"stalled\", False)) or conv.get(\"round_count\", 0) >= max_rounds"` (default
    `max_rounds: int = 5`, `:362`); writer `mark_stalled` `:370-376`
  - `src/film_pipeline/graph/edges.py:90-93` — a second representation written directly by a *routing function* —
    `"state[\"human_approval_required\"] = True"` / `"state[\"_stalled_phase\"] = phase"`
  - `src/film_pipeline/graph/nodes/_repair_loop.py:72-80` — a third threshold and a second writer —
    `"if is_stalled(state, phase, max_rounds=3):"` … `"\"_stalled_phase\": phase,"`
  - Readers split across both representations: `src/film_pipeline/graph/_action_routing.py:156` `'if state.get("_stalled_phase"):'` vs
    `src/film_pipeline/graph/nodes/approval.py:216` `"stalled = is_stalled(state, phase)"` vs `src/film_pipeline/app/services/operator.py:465`
    `'if state.get("_stalled_phase"):'`
- **Drift proof:** mutation scenario, scoped to the half the tests do **not** pin. The `_stalled_phase`
  representation is pinned: `tests/unit/graph/test_real_human_gates.py:117-150` calls `after_approval`, asserts
  `state["_stalled_phase"] == "shot_bible"` (`:135`) and the `ORCHESTRATOR_STALLED` issue (`:140,148`);
  `tests/unit/test_graph.py:54-67` and `tests/e2e/test_orchestrator_decision_loop.py:148-154` exercise
  `is_stalled` through the same representation. The **cap** is not pinned: change the default at
  `src/film_pipeline/graph/orchestrator_state.py:362` from `5` to `2` and every existing test still passes, because each either
  pre-sets `stalled: True` / an explicit `round_count` (`tests/unit/graph/test_real_human_gates.py:125-130`, `tests/unit/test_graph.py:60`,
  `tests/unit/graph/test_prep_gates.py:123`, `tests/integration/test_dynamic_routing.py:194-195`) or passes `max_rounds` explicitly
  (`tests/unit/graph/test_orchestrator_state.py:157,164`, `tests/e2e/test_orchestrator_decision_loop.py:64`). With that edit
  `edges.after_approval` (`src/film_pipeline/graph/edges.py:123`) declares a stall at two rounds while `_start_round` keeps
  `max_rounds=3` (`src/film_pipeline/graph/nodes/_repair_loop.py:72`) and keeps re-running the phase; `_action_routing._human_approval_result`
  then offers `escalate_to_human` (`:156-157`) from a flag the repair loop never set. The repair loop's own
  threshold is untested end to end: `grep -rn "max_rounds=3\|_start_round" tests/ --include=*.py` returns
  nothing (verified at HEAD), so no test
  connects the two caps.
- **Reproduce:**
  ```bash
  grep -rn "max_rounds" src/ tests/ --include=*.py
  grep -rn "max_rounds=3\|_start_round" tests/ --include=*.py   # no hits
  grep -rn "ORCHESTRATOR_STALLED" tests/ --include=*.py         # tests/unit/graph/test_real_human_gates.py:140,148
  grep -rn "_stalled_phase" src/ tests/ --include=*.py
  ```
- **Blast radius:** `edges.py`, `nodes/approval.py`, `nodes/_repair_loop.py`, `_action_routing.py`,
  `app/services/operator.py`, and the orchestrator prompt
  `src/film_pipeline/agents/prompt_templates/defaults/production.py:386` (`"CONVERGENCE ROUND: {convergence_round} of 3"` hard-codes
  the repair loop's `3` as a third literal). User-visible: an unbounded repair loop or a premature human
  escalation, depending on which site was edited.
- **Candidate owner module:** `graph/orchestrator_state.py` — sole owner of convergence/stall state and the cap.
- **Extraction sketch:** export one `STALL_MAX_ROUNDS` constant; make `_start_round` and `is_stalled` share it;
  delete `_stalled_phase` in favour of a single `ostate.mark_stalled` call from the repair loop; guard test
  asserting `after_approval`/`await_approval_node`/`repair_phase_node` agree on the stall verdict for the same
  state.
- **Prior art:** `documentation/reviews/hardcoded-values-inventory.md:117` ("Stall `max_rounds` = 5 default but
  called with 3 … Inconsistent convergence cap") and its 2026-08 re-check `:140` ("**still true**:
  `src/film_pipeline/graph/orchestrator_state.py:260` … vs `src/film_pipeline/graph/nodes/_repair_loop.py:72`" — the
  review's paths are re-spelled repo-relative here; its `:260` is a stale line number (at HEAD `is_stalled` is
  at `:362` and the `max_rounds=3` call is at `src/film_pipeline/graph/nodes/_repair_loop.py:72`). **Still present at HEAD,
  unchanged**; new in this audit: the third representation (`_stalled_phase`) and the untested default cap
  (the representation itself is guarded — see drift proof).

### F-OST-03 — The `issues` channel has no typed contract; the blocking predicate is re-derived at 18 comparison sites (11 over `state["issues"]`), including both canonical blocker views

- **Class:** O8 (missing contract) + O1 (duplicated normative model)
- **Severity:** High (impact 4 × drift 3 = 12)
- **Concern:** What an issue is, and what "blocking" means — the input to every approval and routing veto.
- **De-facto owners:**
  - `src/film_pipeline/schemas/issue.py:12-22` — the typed model exists but is unused —
    `"class IssueRecord(SchemaBase):"` … `"severity: IssueSeverity"`; only import is the package re-export
    `src/film_pipeline/schemas/__init__.py:94`
  - `src/film_pipeline/graph/state_schema.py:172` — the state channel is raw dicts —
    `"issues: Annotated[list[dict[str, object]], merge_issues]"`
  - `src/film_pipeline/graph/_action_routing.py:90-92` — the one named predicate, private and unexported —
    `"return isinstance(issue, dict) and issue.get(\"severity\") == \"blocking\""`; `router.py` does not re-export it
  - `src/film_pipeline/graph/router.py:59-68` — the *canonical* blocker projection re-derives it inline —
    `"if isinstance(issue, dict) and issue.get(\"severity\") == \"blocking\""`
  - `src/film_pipeline/graph/nodes/approval.py:52-55` — the approval veto re-derives it a third time —
    `"return sum(1 for i in issues if i.get(\"severity\") == \"blocking\")"`
- **Drift proof:** existing divergence in rule coverage. `router.get_blockers_for_state` and
  `approval._count_blocking_issues` implement the identical predicate twice, so a partial edit is silent:
  change `_action_routing._is_blocking_issue` (`:92`) to also accept `severity == "fail"` while
  `src/film_pipeline/graph/router.py:64` and `src/film_pipeline/graph/nodes/approval.py:55` keep the old test — `compute_actions` stops blocking
  (`_blocking_issues_result` `:256`) while `get_blockers_for_state` still reports blockers and `approve_phase_node`
  still refuses; no test compares the three predicates, and `tests/unit/graph/test_router_blockers.py` pins only
  the projection's own output.
- **Reproduce:** (count caveat from verify-02: of the 18 comparisons, 11 read the graph's `state["issues"]`
  channel and 7 read other severity domains — config conflicts at `src/film_pipeline/config/resolver.py:25` and
  `src/film_pipeline/mcp/tools/projects.py:78`, the failure-decision channel at `src/film_pipeline/graph/orchestrator_state.py:400`, and
  validator-internal issue lists at `src/film_pipeline/validation/base.py:261`,
  `src/film_pipeline/validation/impl/script_structure.py:220`,
  `src/film_pipeline/validation/impl/delivery_completeness.py:177`, and
  `src/film_pipeline/validation/impl/dialogue_voice.py:221`)
  ```bash
  grep -rn 'severity") == "blocking"\|severity\] == "blocking"\|severity == "blocking"' src/film_pipeline --include=*.py | wc -l   # 18
  grep -rn 'severity") == "blocking"\|severity\] == "blocking"\|severity == "blocking"' src/film_pipeline --include=*.py
  grep -rn "IssueRecord" src/ tests/ --include=*.py
  ```
- **Blast radius:** `graph/_action_routing.py`, `graph/router.py`, `graph/nodes/{approval,prep,_repair_loop,qc}.py`,
  `app/_resume.py`, `app/services/operator.py`, `mcp/tools/review.py`, `cli/run.py`, `cli/driver.py`,
  `validation/*`. User-visible: a phase can be approved on one surface and reported blocked on another — the
  exact disagreement `router.get_blockers_for_state`'s docstring claims to prevent (`src/film_pipeline/graph/router.py:48-51`).
- **Candidate owner module:** `graph/issue_state.py` (or `schemas/issue.py` promoted) — the issue model, the
  blocking predicate, and the append/remove reducer.
- **Extraction sketch:** make the state channel hold `IssueRecord` (or a dict validated through it); export
  `is_blocking(issue)` from the owner and delete all 18 inline comparisons (11 of them over `state["issues"]`);
  guard test parametrised over `compute_actions`, `get_blockers_for_state`, and `approve_phase_node` with one
  blocking issue.
- **Prior art:** `documentation/reviews/arch-lens-cognition.md:236-238` notes `src/film_pipeline/graph/_action_routing.py:90` "has yet
  another `_is_blocking_issue`"; still present at HEAD, and the typed `IssueRecord` remains unused.

### F-OST-04 — The human-gate label is produced by two independent maps (node literals vs `APPROVAL_GATES`)

- **Class:** O1 (duplicated normative model) + O2 (duplicated invariant enforcement) — raised from O4 by
  `verify-02.md` cross-check; the map is a normative phase table, not merely a lookup registry.
- **Severity:** High (impact 3 × drift 4 = 12) — **raised from Medium 6 by `verify-02.md`** to match
  `docs/modular-architecture/audit/01-phase-model-and-transitions.md` §F-PHASE-03 (High, 3 × 4 = 12);
  the same defect must not carry two severities across sibling audits.
- **Concern:** Which named gate a phase parks at (`human_approval_phase` / `RouterResult.human_gate`).
- **De-facto owners:**
  - `src/film_pipeline/graph/_action_routing.py:49-61` — the phase→gate map —
    `"APPROVAL_GATES = {"` … `"\"gen_planning\": \"generation_spend\","`
  - `src/film_pipeline/graph/nodes/_shared.py:154-159` — the same mapping re-supplied as a call-site literal —
    `"\"human_approval_phase\": gate,"`, fed by e.g. `src/film_pipeline/graph/nodes/prep.py:108` `'gate="config"'` and `src/film_pipeline/graph/nodes/visual.py:34-36`
    `'phase="visual_dev", gate="visual_bible"'`
  - `src/film_pipeline/graph/subgraphs/qc.py:270` — a third, hard-coded instance for the QC path —
    `"\"human_approval_phase\": \"qc\","`
- **Drift proof:** mutation scenario. Change `APPROVAL_GATES["visual_dev"]` to `"visual_design"`
  (`src/film_pipeline/graph/_action_routing.py:54`); `visual_dev_node` still parks at `human_approval_phase == "visual_bible"`
  (`src/film_pipeline/graph/nodes/_shared.py:158` via `src/film_pipeline/graph/nodes/visual.py:35`), so the review-package tool reports gate `visual_design`
  (`src/film_pipeline/mcp/tools/review.py:115`) while the interrupt payload shows `visual_bible` (`src/film_pipeline/graph/nodes/approval.py:110`). No test
  relates the two maps: `tests/integration/test_dynamic_routing.py:211-212` asserts only
  `phase in APPROVAL_GATES`, and the node-side assertions (`tests/unit/graph/test_wrapup_nodes.py:126,138,256`,
  `tests/unit/graph/test_qc_subgraph.py:85`) pin literals, not agreement.
- **Reproduce:**
  ```bash
  grep -rn "APPROVAL_GATES" src/ tests/ --include=*.py
  grep -rn "_phase_gate_updates(" src/film_pipeline/graph --include=*.py
  ```
- **Blast radius:** `graph/nodes/*`, `graph/subgraphs/qc.py`, `graph/_action_routing.py`,
  `mcp/tools/review.py`, operator dashboards. User-visible: the operator is told to review the wrong gate name.
- **Candidate owner module:** `phase-model` — owns `PHASE_GATES` (from `APPROVAL_GATES`);
  `_phase_gate_updates` becomes the only writer of `human_approval_phase` and takes the gate from that map.
  See §5 "Cross-cluster ownership reconciliation": this nomimation was previously left split between
  `graph/orchestrator_state.py` and the phase model; `verify-02.md` flagged the double ownership and it is
  resolved in favour of `phase-model` (audit 01).
- **Extraction sketch:** delete the per-node `gate=` argument; `_phase_gate_updates(state, phase=...)` looks up
  `PHASE_GATES[phase]`; replace `src/film_pipeline/graph/subgraphs/qc.py:263-271` with a call to `_phase_gate_updates`. Guard test: for
  every `PHASE_ORDER` entry, `_phase_gate_updates(...)["human_approval_phase"] == APPROVAL_GATES[phase]`
  (audit 01 guard #4 already asserts this direction).
- **Prior art:** `docs/modular-architecture/audit/01-phase-model-and-transitions.md` §F-PHASE-03 —
  "The phase→approval-gate map is written twice, and the QC subgraph writes the gate update inline"
  (High, 3 × 4 = 12), whose candidate owner is `phase-model`. What is new *here* is the orchestrator-state
  angle: the read side (`RouterResult.human_gate` → `src/film_pipeline/mcp/tools/review.py:115`, operator dashboards) consumes
  the same label without sharing the map, and the independent evidence that no test relates the two writers
  (`tests/integration/test_dynamic_routing.py:211-212` asserts only `phase in APPROVAL_GATES`).

### F-OST-05 — The "cannot approve with blocking issues" veto is implemented four times with two different scopes

- **Class:** O2 (duplicated invariant enforcement)
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** Under what conditions a phase may be approved.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/approval.py:250-251` — veto over **all** state issues —
    `"if _count_blocking_issues(state):"` / `"return {\"approved\": False, \"_approval_blocked_by_issues\": True}"`
  - `src/film_pipeline/graph/nodes/prep.py:339-356` — veto over **fresh** issues only —
    `"if any(i.get(\"severity\") == \"blocking\" for i in issues):"` / `"updates[\"approved\"] = False"`, reached
    from `:333-336` with `"fresh_issues = [i for i in node_issues if _is_new_issue(i, state)]"`
  - `src/film_pipeline/graph/nodes/approval.py:221-224` — headless fallback re-checks —
    `"approve_phase_node(state)"` / `"if _count_blocking_issues(state) == 0"`
  - `src/film_pipeline/graph/_action_routing.py:151-169` — the router offers `approve_phase` only when
    `"blocking_count == 0"` (`:154-155`), with a fifth count helper `_blocking_issue_count` (`:95-97`)
- **Drift proof:** the scopes already differ. A blocking issue that is *already in state* (not freshly emitted
  by this node) is invisible to `prep._withhold_auto_approval_on_blockers` (`src/film_pipeline/graph/nodes/prep.py:333` filters by
  `_is_new_issue`) but vetoes `approve_phase_node` (`src/film_pipeline/graph/nodes/approval.py:55` counts the whole list) and fires the
  router's `handle_blockers` (`src/film_pipeline/graph/_action_routing.py:256`). Today `after_phase` routes to repair before the gate
  (`src/film_pipeline/graph/edges.py:69-70`), masking the outcome; the guard inputs nevertheless disagree, and no test asserts that all
  four sites use the same scope — `tests/unit/test_graph.py:54-70` and `tests/unit/graph/test_real_human_gates.py:117-150` pin the
  node and edge behaviour separately.
- **Reproduce:**
  ```bash
  grep -rn "blocking_count\|_count_blocking_issues\|_withhold_auto_approval_on_blockers\|_blocking_issue_count" src/film_pipeline/graph --include=*.py
  ```
- **Blast radius:** `nodes/prep.py` (development/script in headless mode), `nodes/approval.py`, `graph/edges.py`,
  `_action_routing.py`. User-visible: headless auto-approval can accept a phase that the interactive gate would
  refuse.
- **Candidate owner module:** `graph/orchestrator_state.py` — one `may_approve(state) -> (bool, reason)` predicate.
- **Extraction sketch:** collapse the four sites into one owned predicate; guard test running the same state
  (fresh vs pre-existing blocking issue) through `approve_phase_node`, `await_approval_node`, and
  `compute_actions`.
- **Prior art:** new

### F-OST-06 — Routing reads `state["consensus_report"]`, a key no production writer produces and the schema does not declare

- **Class:** O5 (policy-by-branch on a never-written input) + O7 (leaked internals)
- **Severity:** High (impact 3 × drift 5 = 15)
- **Concern:** The documented priority "explicit consensus wins over validation reports" in the
  validation-status routing rule.
- **De-facto owners:**
  - `src/film_pipeline/graph/_action_routing.py:108-115` — reads the dict key —
    `"consensus = state.get(\"consensus_report\")"` … `"return _status_from_value(str(raw))"`
  - `src/film_pipeline/graph/_action_routing.py:134-140` — makes it the highest-priority signal —
    `"consensus = _consensus_status(state)"` / `"if consensus is not None:"` / `"return consensus"`
  - `src/film_pipeline/graph/state_schema.py:157` — only the ref is a state field —
    `"consensus_report_ref: str"` (no `consensus_report`)
  - `src/film_pipeline/agents/impl/qc_synthesis_agent.py:71` — the only producer returns it to the *caller*,
    never into state — `"return {\"consensus_report\": report}"`; the consumer stores an artifact instead
    (`src/film_pipeline/graph/nodes/qc.py:107-111`)
- **Drift proof:** the branch is unreachable in production. `grep -rn '"consensus_report"' src/` finds only the
  agent's local return dict; nothing assigns `state["consensus_report"]`, and the key is absent from
  `StudioGraphState`, so LangGraph would drop it even if a node returned it. The only writer in the repo is
  `tests/unit/graph/test_router_validation_status.py:77`, which is why the rule looks tested while routing in
  production always falls through to `state["_validation_reports"]` (`:139`). No test fails.
- **Reproduce:**
  ```bash
  grep -rn 'consensus_report' src/film_pipeline --include=*.py
  grep -rn '"consensus_report"' src/ tests/ --include=*.py
  ```
- **Blast radius:** `_action_routing.py` (rule 6), `graph/nodes/qc.py`, `graph/subgraphs/qc.py`,
  `src/film_pipeline/app/_graph_exec.py:342`. User-visible: the strongest available validation signal is ignored; routing acts on
  the weaker per-validator reports.
- **Candidate owner module:** `graph/orchestrator_state.py` — one declared validation-signal channel with typed
  writers.
- **Extraction sketch:** delete `_consensus_status` or give the QC path a declared state field
  (`consensus_report_ref` → load through the store, mirroring `orchestrator_validators.brief.load_execution_brief`);
  guard test that a BLOCKED consensus artifact makes `compute_actions` return `handle_blockers`.
- **Prior art:** `docs/clean-code-refactor/review-findings.md:42` already flags the rule-6 mutate-vs-replace
  fragility; new here: the rule's input is never populated.

### F-OST-07 — Two QC lifecycles (Send subgraph vs sequential node) with the findings→issues translation written twice

- **Class:** O6 (parallel lifecycle) + O2 (duplicated invariant enforcement)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** What running the QC phase means, and how validator findings become blocking issues.
- **De-facto owners:**
  - `src/film_pipeline/graph/graph.py:115` — the compiled graph binds the subgraph as `qc_node` —
    `'builder.add_node("qc_node", build_qc_subgraph())  # Phase 7: parallel subgraph'`
  - `src/film_pipeline/graph/nodes/_repair_loop.py:47` — repair and manual advance bind the *other*
    implementation — `'"qc": qc_node,'` (from `nodes/qc.py`), the same table used by
    `src/film_pipeline/app/_graph_exec.py:449-456`
  - `src/film_pipeline/graph/subgraphs/qc.py:228-246` — translation #1 —
    `'"issue_id": f"val:{validator_id}:{finding.get(\'code\', \'?\')}",'`
  - `src/film_pipeline/graph/nodes/qc.py:406-415` — translation #2, the `_issue_entry` helper whose key
    literal is at `:409` —
    `'"issue_id": f"val:{report.validator_id}:{finding.code}",'`
  - Only the node path produces the consensus artifact: `src/film_pipeline/graph/nodes/qc.py:40` `"_synthesize_consensus_report(new_state)"`
    vs the subgraph reduce (`src/film_pipeline/graph/subgraphs/qc.py:249-277`), which never synthesises one
- **Drift proof:** existing divergence in what the QC phase produces. The graph path writes
  `_qc_reports`/`_qc_raw_reports` (`src/film_pipeline/graph/subgraphs/qc.py:68-73`) and never writes `consensus_report_ref`; the repair
  path (`_PHASE_NODES["qc"]`) writes `consensus_report_ref`/`qc_patch_ref` (`src/film_pipeline/graph/nodes/qc.py:91,111,182`) and never
  writes `_qc_reports`. Change the severity mapping in one translation — e.g. mark
  `blocking_issues` as `"warning"` in `src/film_pipeline/graph/subgraphs/qc.py:233` — and the graph QC path silently stops blocking
  while the repair path still blocks; `tests/unit/graph/test_qc_subgraph.py:90-113` asserts the subgraph's own
  output and `tests/unit/graph/test_qc_validator_dispatch.py` asserts only runner dispatch, so neither notices.
- **Reproduce:**
  ```bash
  grep -n "qc_node" src/film_pipeline/graph/graph.py src/film_pipeline/graph/nodes/_repair_loop.py
  grep -rn '"val:' src/film_pipeline/graph --include=*.py
  grep -rn "_qc_reports\|consensus_report_ref" src/film_pipeline/graph/subgraphs/qc.py src/film_pipeline/graph/nodes/qc.py
  ```
- **Blast radius:** QC evidence and the issues the human gate sees; `src/film_pipeline/graph/state_schema.py:210-211` (`add` reducers)
  vs the node path's plain list. User-visible: the same project blocks or passes depending on whether QC ran
  through the graph or through a repair/manual advance.
- **Candidate owner module:** `graph/qc_lifecycle.py` (or keep the subgraph as the single QC implementation and
  delete `nodes/qc.qc_node`'s duplicate translation).
- **Extraction sketch:** one `findings_to_issues()` owned with the issue model; `_PHASE_NODES["qc"]` must invoke
  the subgraph; guard test asserting both entry points produce the same issues for the same reports.
- **Prior art:** new

### F-OST-08 — `app._graph_exec.run_phase_node` re-implements the graph's channel reducers and diverges from the declared schema

- **Class:** O4 (parallel registries) + O6 (parallel lifecycle)
- **Severity:** High (impact 3 × drift 3 = 9) — **drift reduced 4 → 3 by `verify-02.md`**: the policy
  duplication is real and mechanical, but the originally claimed user-visible consequence was not exclusive
  to the manual path (see drift proof).
- **Concern:** How a node's partial update merges into accumulated state on each execution path.
- **De-facto owners:**
  - `src/film_pipeline/graph/state_schema.py:171-174, :208-211` — the declared reducers —
    `"artifact_refs: Annotated[list[str], merge_unique]"`, `"issues: Annotated[list[dict[str, object]], merge_issues]"`,
    `"_qc_reports: Annotated[list[dict[str, Any]], add]"`, while `"_validation_reports: list[dict[str, Any]]"`
    (`:208`) has **no** reducer (last write wins)
  - `src/film_pipeline/app/_graph_exec.py:467-481` — a hand-maintained parallel registry —
    `'"artifact_refs": merge_unique,'` … `'_qc_reports'/'_qc_raw_reports' omitted`, then
    `"merged[key] = list(prev) + [item for item in new if item not in prev]"` for `_routing_decisions` and
    `_validation_reports`
- **Drift proof:** policy duplication, not an existing user-visible divergence. The same channel is merged by
  two independently editable rules: `_validation_reports` is unreduced in `src/film_pipeline/graph/state_schema.py:208` (the compiled
  graph replaces the channel with the node's returned list) but is union-merged by hand at
  `src/film_pipeline/app/_graph_exec.py:481`; `_qc_reports`/`_qc_raw_reports` (`src/film_pipeline/graph/state_schema.py:210-211`, `add`) are simply absent
  from the manual map (`:467-472`). Mutation scenario: add or change a reducer in `state_schema.py` (e.g. give
  `_validation_reports` a union reducer, or point `issues` at a new function) — the compiled graph honours it,
  `run_phase_node` keeps its hand-written list and diverges silently, and no test compares the two paths
  (`run_phase_node` is exercised only indirectly through `rt._run_phase_node`, e.g.
  `tests/unit/mcp/tools/test_bibles.py:54-57`). The concrete *existing* difference is the merge-policy pair
  itself (`_validation_reports`: replace vs union; the two QC channels: `add` vs absent); it is a latent
  divergence, so drift is 3, not 4, and the finding rests on the duplicated policy rather than on a
  demonstrated wrong output today. (An earlier draft claimed the manual path uniquely preserved stale BLOCKED
  reports; `verify-02.md` showed that is wrong — `_qc_raw_reports` is never cleared, so
  `src/film_pipeline/graph/subgraphs/qc.py:259,266` re-publishes earlier reports into `_validation_reports` on the compiled-graph path
  too. That claim is withdrawn.)
- **Reproduce:**
  ```bash
  sed -n '455,484p' src/film_pipeline/app/_graph_exec.py
  sed -n '170,175p;199,211p' src/film_pipeline/graph/state_schema.py
  ```
- **Blast radius:** the manual advance fallback (`src/film_pipeline/app/_graph_exec.py:442`, entered when no checkpoint exists —
  `:209-210`) and the repair path share this merge. User-visible today: none demonstrated; the exposure is
  latent — a future edit to `state_schema`'s reducers silently fails to reach the manual path, so the two
  execution paths can accumulate `_validation_reports` and the QC channels under different policies.
- **Candidate owner module:** `graph/state_schema.py` — export the reducer map (`REDUCERS`) and have
  `run_phase_node` consume it.
- **Extraction sketch:** derive `REDUCERS` from the `Annotated` metadata once; delete the literal dict in
  `_graph_exec.py`; guard test applying the same node update through `run_phase_node` and a compiled graph step
  and asserting equal channel values.
- **Prior art:** new

### F-OST-09 — `next_action` → operator prose is re-derived in two modules

- **Class:** O5 (policy-by-branch at N call sites)
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** The public rendering of the router's action vocabulary.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/review.py:120-143` — MCP rendering, 8 branches plus a default —
    `'if action == "wait_for_human":'` … `'return f"Current action: {action}."'`
  - `src/film_pipeline/app/services/operator.py:473-483` — dashboard rendering, 4 branches —
    `'if next_action in {"wait_for_human", "present_review_package"}:'`
- **Drift proof:** existing divergence. `operator._recommendation` collapses `wait_for_human` and
  `present_review_package` into one string and has no branch for `revise`; the MCP renderer distinguishes them
  and adds `escalate_to_failure_handler`/`continue_unrelated_work`. A new `next_action` added in
  `_action_routing.py` produces "Current action: X." on the dashboard and the MCP default — both tests stay
  green because each pins only its own module (`tests/unit/mcp/tools/test_review.py:151-158`;
  `operator._recommendation` has no test at all).
- **Reproduce:**
  ```bash
  grep -rn "_recommendation\|_build_orchestrator_recommendation" src/ --include=*.py
  grep -rn "def test.*recommendation" tests/ --include=*.py
  ```
- **Blast radius:** `mcp/tools/review.py`, `app/services/operator.py`, TUI/dashboard consumers.
- **Candidate owner module:** `graph/router.py` — publish `describe_action(next_action) -> str`.
- **Extraction sketch:** move both mappings behind one router function; guard test iterating the action
  vocabulary produced by `compute_actions` over a state matrix and asserting every value has a description.
- **Prior art:** `documentation/reviews/arch-lens-boundaries.md:196,203,208` already recommends funnelling
  "next action" through `compute_actions`; still present at HEAD.

### F-OST-10 — The auto/headless approval policy is derived twice from `resolved_config`

- **Class:** O1 (duplicated normative model) + O5 (policy-by-branch)
- **Severity:** Medium (impact 3 × drift 2 = 6) — **reconciled with the sibling audit by `verify-02.md`**:
  this finding is the same defect as `docs/modular-architecture/audit/01-phase-model-and-transitions.md`
  §F-PHASE-07 (rated Medium 3 × 2 = 6). An earlier draft rated it High 3 × 3 = 9; the same finding must not
  carry two severities across sibling audits, and audit 01 is the owning cluster for the gate-mode predicate,
  so its drift rating (2: divergence requires a specific edit with no test relating the two readers) is adopted
  here. This audit contributes the routing consequence, not an independent severity.
- **Concern:** Whether human approval is required, and what "auto mode" implies for edge routing.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/_shared.py:132-144` — the canonical reader —
    `"return bool(studio.get(\"require_human_approval\", True))"`
  - `src/film_pipeline/graph/edges.py:18-25` — an independent reader used by the edge —
    `"return not bool(studio.get(\"require_human_approval\", True))"`
  - Both consume the same config, and a third call site reaches the helper for the QC path
    (`src/film_pipeline/graph/subgraphs/qc.py:257-262`), so the policy has three call sites and two implementations
- **Drift proof:** mutation scenario. Rename the config key to `approval_required` in `src/film_pipeline/graph/nodes/_shared.py:143` only;
  `edges._is_auto_mode` (`:24`) keeps reading `require_human_approval` and therefore returns `False` for every
  project, so `after_approval` never takes the headless terminal branch (`src/film_pipeline/graph/edges.py:127-129`) and a stalled
  headless run loops at the gate. The two guards do not cross-check: `tests/unit/graph/test_prep_gates.py:106-113` pins
  `_is_auto_mode`'s literal-input behaviour and `tests/unit/graph/test_real_human_gates.py:237-245` pins
  `_require_human_approval`'s defaults; neither asserts the two agree.
- **Reproduce:**
  ```bash
  grep -rn "require_human_approval" src/ --include=*.py
  grep -rn "_is_auto_mode\|_require_human_approval" tests/ --include=*.py
  ```
- **Blast radius:** `graph/edges.py`, `graph/nodes/_shared.py`, `graph/nodes/approval.py`,
  `graph/subgraphs/qc.py`; `src/film_pipeline/config/runtime_overrides.py:21` maps `FILM_PIPELINE_APPROVAL_MODE` into the same key.
  User-visible: a gate bypassed or a headless run wedged.
- **Candidate owner module:** `phase-model` (audit 01 §F-PHASE-07) — owns the gate-mode predicate
  (`_require_human_approval`); `edges._is_auto_mode` delegates to it. The orchestrator-state owner keeps only
  the *state field* (`human_approval_required`) it publishes.
- **Extraction sketch:** make `edges._is_auto_mode` call `_require_human_approval`; guard test asserting
  `_is_auto_mode(state) == (not _require_human_approval(state))` for the config matrix.
- **Prior art:** `docs/modular-architecture/audit/01-phase-model-and-transitions.md` §F-PHASE-07 —
  "Gate mode (human vs auto) is re-derived in two modules from the same config key" (Medium, 3 × 2 = 6), with
  the identical two owners, mutation scenario and extraction sketch. What is new *here* is the routing framing:
  the duplicated predicate gates the `after_approval` terminal branch against the orchestrator's published
  `human_approval_required` flag, so a divergence shows up as a routing loop (`src/film_pipeline/graph/edges.py:127-130`) rather than
  only as a wrong approval prompt.

### F-OST-11 — Orchestrator key literals and the `_orchestrator__` prefix grammar are re-derived by three consumer modules

- **Class:** O7 (leaked internals)
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** How consumers name and address orchestrator state.
- **De-facto owners:**
  - `src/film_pipeline/graph/orchestrator_state.py:23` — the only declared grammar —
    `"_ORCH_NS = \"_orchestrator\""` plus the `f"{_ORCH_NS}__…"` convention (`:27-64`)
  - `src/film_pipeline/graph/nodes/approval.py:62-66` — re-implements the namespace filter —
    `'key: deepcopy(value) for key, value in state.items() if key.startswith("_orchestrator__")'`
  - `src/film_pipeline/graph/nodes/approval.py:267,293` — re-spells key names —
    `'"\"_orchestrator__approved_refs\": working.get(\"_orchestrator__approved_refs\", {}),"` and
    `'"\"_orchestrator__pending_revisions\"…'`
  - `src/film_pipeline/graph/nodes/_repair_loop.py:70,78,235,238-240` — re-spells the convergence and
    revision keys —
    `'convergence_update = deepcopy(state.get("_orchestrator__convergence", {}))'` (`:70`),
    `'result.setdefault("_orchestrator__convergence", convergence_update)'` (`:235`) and
    `'result["_orchestrator__pending_revisions"] = revision_update['` (`:239`)
  - `src/film_pipeline/graph/nodes/_context.py:81` — reads the convergence key for prompt context —
    `'conv = state.get("_orchestrator__convergence", {})'`
- **Drift proof:** the leak is already visible in the tests: `tests/unit/graph/test_real_human_gates.py:125`
  and `tests/integration/test_dynamic_routing.py:194` must spell `"_orchestrator__convergence"` themselves
  (the key appears at `tests/unit/graph/test_real_human_gates.py:27,46,62,84,101,113,125` and
  `tests/integration/test_dynamic_routing.py:121,194`), because the owner publishes no accessor for the whole slice — the
  private key spelling has become the public contract. Mutation scenario that passes every test: add
  `_ORCH_ALERTS = f"{_ORCH_NS}_alerts"` (single underscore) at `src/film_pipeline/graph/orchestrator_state.py:64` plus an
  `ORCH_CHANNELS` row. `_ast_orchestrator_keys` collects it as `_orchestrator` + `_alerts`
  (`tests/unit/graph/test_channel_registry.py:62-66`), so both parity tests pass, but
  `approval._orchestrator_working_state`'s filter (`src/film_pipeline/graph/nodes/approval.py:63`) drops it from the approval working copy, so
  `approve_phase_node` never promotes or re-emits it. No test asserts the `_orchestrator__` prefix invariant.
  The verifier's `verify-02.md` row is correct that the *quoted inner key* is what must be grepped: the
  quoted key `"convergence_round"` genuinely has 0 test hits (`grep -rn '"convergence_round"' tests/` →
  exit 1), whereas the bare identifier `convergence_round` has 5 hits, all the unrelated function
  `increment_convergence_round` (`tests/unit/graph/test_orchestrator_state.py:156,163`,
  `tests/e2e/test_orchestrator_decision_loop.py:62,63,153`). The absence claim is therefore about the quoted key only.
- **Reproduce:**
  ```bash
  grep -rn '"_orchestrator__' src/ --include=*.py | grep -v orchestrator_state.py
  grep -rn '"_orchestrator__convergence"' tests/ --include=*.py      # 9 hits, all hand-spelled
  grep -rn '"convergence_round"' tests/ --include=*.py; echo "exit=$?"  # exit=1: no test reads the inner key
  grep -n 'startswith("_orchestrator__")' src/film_pipeline/graph/nodes/approval.py
  ```
- **Blast radius:** `nodes/approval.py`, `nodes/_repair_loop.py`, `nodes/_context.py`; any future rename of an
  orchestrator key. User-visible: repair convergence silently stops working.
- **Candidate owner module:** `graph/orchestrator_state.py` — publish key accessors, keep the literals private.
- **Extraction sketch:** add `orchestrator_slice(state)` and `set_*`/`get_*`-only writes; forbid
  `key.startswith("_orchestrator")` outside the owner via an import/AST test (the sweep in
  `tests/unit/graph/test_channel_registry.py:247-305` already parses `graph/nodes/**` and can be extended to reads).
- **Prior art:** new

### F-OST-12 — Budget state exists under two keys, and the prompt reader uses the one nothing writes

- **Class:** O1 (duplicated normative model) + O3 (split state authority)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** The budget snapshot and the budget-blocked routing rule.
- **De-facto owners:**
  - `src/film_pipeline/graph/orchestrator_state.py:59` + `:449-463` — the real channel and its only writer —
    `'_BUDGET_SNAPSHOT = f"{_ORCH_NS}__budget_snapshot"'` … `'state[_BUDGET_SNAPSHOT] = {' followed by
    `'"cap_usd": cap_usd,'`
  - `src/film_pipeline/graph/context_packets.py:121-123` — the prompt path reads the *other* key —
    `'budget = state.get("budget_snapshot", {})'` / `'cap = budget.get("cap_usd", 0) if isinstance(budget, dict) else 0'`
  - `src/film_pipeline/graph/state_schema.py:177-178` declares both —
    `"budget_snapshot: dict[str, object]"` and `:196` `"_orchestrator__budget_snapshot: dict[str, Any]"`
  - Routing reads the namespaced one: `src/film_pipeline/graph/_action_routing.py:238-241` → `ostate.is_budget_blocked` (`:477-479`)
- **Drift proof:** existing divergence, provable end to end. `ostate.update_budget_snapshot(state, cap_usd=50.0)`
  sets `_orchestrator__budget_snapshot`; `build_gen_planning_context(state)` then renders
  `"Budget cap: $0"` because `src/film_pipeline/graph/context_packets.py:121` reads the un-namespaced key. Both sides are pinned
  separately — `tests/unit/graph/test_context_packets.py:175` injects `"budget_snapshot": {"cap_usd": 42}` and
  `tests/unit/graph/test_router_blockers.py:43` / `tests/unit/test_graph.py:114` use
  `ostate.update_budget_snapshot` — so no test crosses the two keys. Separately, `update_budget_snapshot` has
  **zero production callers** (`grep` returns only `orchestrator_state.py` and tests), so the routing rule is
  dormant; the duplication is what makes the drift invisible.
- **Reproduce:** (verified at HEAD — prints `['_orchestrator__budget_snapshot']` then `'Budget cap: $0'`)
  ```bash
  .venv/bin/python -c "
  from types import SimpleNamespace
  from film_pipeline.graph import orchestrator_state as o
  from film_pipeline.graph.context_packets import build_gen_planning_context as b
  s = {}; o.update_budget_snapshot(s, cap_usd=50.0, spent_usd=10.0)
  print(sorted(s.keys())); print(repr(b(s, SimpleNamespace(artifact_store=None))))"
  grep -rn "budget_snapshot" src/film_pipeline --include=*.py
  ```
- **Blast radius:** `context_packets.py` (gen-planning prompt), `_action_routing.py` rule 4,
  `src/film_pipeline/mcp/tools/state.py:57`, `src/film_pipeline/app/services/operator.py:251`. User-visible: prompts state a $0 cap while the router
  sees the real cap.
- **Candidate owner module:** `graph/orchestrator_state.py` — one budget channel, one reader.
- **Extraction sketch:** delete the un-namespaced `budget_snapshot` field or make
  `context_packets` call `ostate.get_budget_snapshot`; guard test asserting the prompt block and
  `is_budget_blocked` read the same value after one `update_budget_snapshot` call.
- **Prior art:** `documentation/reviews/arch-lens-observability.md:161` records that the budget gate reads a
  value that is never incremented; new here: the two-key split and the concrete $50 vs $0 divergence.

### F-OST-13 — Provider health has three representations; routing reads the one with no production writer

- **Class:** O3 (split state authority) + O4 (parallel registries)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** Which providers are blocked, for the generation-dependent routing rules.
- **De-facto owners:**
  - `src/film_pipeline/graph/orchestrator_state.py:55` + `:427-435` — the routing source —
    `'_PROVIDER_HEALTH_SNAPSHOT = f"{_ORCH_NS}__provider_health_snapshot"'` …
    `'if health.get("status", "").startswith("blocked_")'`
  - `src/film_pipeline/app/runtime.py:51,386-393` — the live operator source —
    `"provider_health: dict[str, Any] = field(default_factory=dict)"` / `'self.provider_health[provider_id] = {"status": status, "reason": reason}'`,
    seeded by `src/film_pipeline/app/_provider_seeds.py:28` `'rt.set_provider_health(provider_id, "healthy")'` and read by
    `src/film_pipeline/app/health.py:47` `"h = rt.get_provider_health(pid)"`
  - `src/film_pipeline/graph/state_schema.py:178` — a third, plain key with no reader in this cluster —
    `"provider_health_snapshot: dict[str, object]"`
  - Routing consumers: `src/film_pipeline/graph/_action_routing.py:228` (`_blocked_providers_result`) and `:334`
    (`_advance_result`) both call `ostate.get_blocked_providers`
- **Drift proof:** existing divergence. Operator surfaces report provider health from
  `rt.provider_health` (runtime dict), while `compute_actions` reads `_orchestrator__provider_health_snapshot`,
  whose only writer `update_provider_health` (`:406-410`) has **zero production callers** (grep finds only
  `orchestrator_state.py` and tests). Freeze a provider via `rt.set_provider_health("p", "blocked_quota")` and
  the dashboard shows it blocked while `compute_actions` returns `advance_to_generation` — rule 3
  (`src/film_pipeline/graph/_action_routing.py:226-235`) can never fire. No test crosses the two sources:
  `tests/unit/graph/test_router_blockers.py:50-59` seeds the orchestrator key directly and app-level tests seed
  the runtime dict.
- **Reproduce:**
  ```bash
  grep -rn "provider_health\|ProviderHealth" src/film_pipeline --include=*.py | grep -v "^src/film_pipeline/graph/orchestrator_state.py"
  grep -rn "update_provider_health\|set_provider_health" src/ tests/ --include=*.py
  ```
- **Blast radius:** `_action_routing.py` rules 3 and 8 (`_advance_result`), `src/film_pipeline/mcp/tools/state.py:56`,
  `src/film_pipeline/app/services/operator.py:252`, `app/health.py`, `app/_browse_ops`. User-visible: generation is dispatched to
  a provider the operator dashboard shows as blocked.
- **Candidate owner module:** `graph/orchestrator_state.py` + a provider-health port; the runtime dict should be
  the single source and the orchestrator snapshot a projection of it.
- **Extraction sketch:** make the graph runtime push `rt.provider_health` into the owner's channel at invoke
  time (single writer), delete the plain `provider_health_snapshot` field; guard test asserting
  `compute_actions` blocks a generation-phase advance whenever the runtime marks a generation provider blocked.
- **Prior art:** `documentation/reviews/arch-lens-dataflow.md:155-158` records the test-only writers and the
  "blocked-provider work continues" failure scenario; still present at HEAD (verified by grep). New here: the
  third representation and the runtime-vs-snapshot split.

### F-OST-14 — Failure decisions: typed producer, untyped dict channel, no bridge

- **Class:** O8 (missing contract) + incomplete wiring
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** How a failure decision reaches the router's blocking-failure rule.
- **De-facto owners:**
  - `src/film_pipeline/graph/orchestrator_state.py:382-384` — the channel's only writer takes a raw dict —
    `'def add_failure_decision(state: dict[str, Any], decision: dict[str, Any]) -> None:'`
  - `src/film_pipeline/graph/orchestrator_state.py:398-400` — the predicate reads a string field —
    `'return any(d.get("severity") == "blocking" for d in get_failure_decisions(state))'`
  - `src/film_pipeline/schemas/failure.py:17-37` — the typed contract exists with a *different* id field —
    `"class FailureDecision(SchemaBase):"` … `"decision_id: str"` … `"severity: str = Field(default=\"blocking\")"`;
    zero users in `src/` outside the package re-export (`src/film_pipeline/schemas/__init__.py:79`)
  - `src/film_pipeline/agents/mvp/__init__.py:162` — the agent that produces it — `'output_artifacts=["failure_decision"]'`;
    its sole invocation (`src/film_pipeline/graph/nodes/wrapup.py:24-35`) reads only `"assembly_manifest"`
  - Consumer: `src/film_pipeline/graph/_action_routing.py:211-223` (rule 2) via `ostate.has_blocking_failure` / `get_latest_failure_decision`
- **Drift proof:** mutation scenario plus a live gap. `add_failure_decision` has **zero production callers**, so
  `_orchestrator__failure_decisions` is always empty and rule 2 (`escalate_to_failure_handler`) is unreachable —
  while the failure-handling agent's declared `failure_decision` output is dropped at `src/film_pipeline/graph/nodes/wrapup.py:30-35`. Even
  when wired, the seam is untyped: the owner stores whatever dict the caller passes and interprets
  `d["severity"]`, while the producer model exposes `decision_id` — a rename of `FailureDecision` fields
  (e.g. `severity` → `blocking`) passes every schema test and silently turns every decision non-blocking.
- **Reproduce:**
  ```bash
  grep -rn "add_failure_decision" src/ tests/ --include=*.py
  grep -rn "FailureDecision" src/ --include=*.py
  grep -n "assembly_manifest" src/film_pipeline/graph/nodes/wrapup.py
  ```
- **Blast radius:** `_action_routing.py` rule 2, `agents/mvp/__init__.py`, `nodes/wrapup.py`,
  `schemas/failure.py`. User-visible: provider failures never trigger `escalate_to_failure_handler`.
- **Candidate owner module:** `graph/orchestrator_state.py` — the channel takes `FailureDecision`, not
  `dict[str, Any]`.
- **Extraction sketch:** type `add_failure_decision(state, decision: FailureDecision)`; bridge the
  failure-handling agent's output in the failure path; guard test asserting a
  `FailureDecision(severity="blocking")` makes `compute_actions` return `escalate_to_failure_handler`.
- **Prior art:** `documentation/reviews/arch-lens-dataflow.md:155` (the failure-decision, provider-health, and
  budget-snapshot writers are called only from tests); still present at HEAD.

### F-OST-15 — Seven phase-keyed registries with no agreement check; one already disagrees with `PHASE_ORDER`

- **Class:** O4 (parallel registries) + O1 (duplicated normative model)
- **Severity:** Medium (impact 2 × drift 3 = 6) — **reconciled with the sibling audit by `verify-02.md`**:
  the shared evidence (`_PHASE_DEFAULT_AGENTS` covering 9/11 phases) is `docs/modular-architecture/audit/01-phase-model-and-transitions.md`
  §F-PHASE-08 (Medium, 3 × 2 = 6). An earlier draft rated this High-impact-adjacent at Medium 8; the drift axis
  is aligned to the sibling (3) so the same evidence carries one severity. The umbrella "eleven parallel phase
  tables" defect is rated once, at audit 01 §F-PHASE-02 (Critical 4 × 4 = 16); this finding does **not** re-rate it.
- **Concern:** The phase vocabulary and the per-phase facts keyed by it.
- **De-facto owners:**
  - `src/film_pipeline/graph/_action_routing.py:18-30` — the ordering —
    `"PHASE_ORDER = ["` … `"\"delivery\","`
  - `src/film_pipeline/graph/_action_routing.py:33-47` — the same 11 phases re-listed as two sets —
    `'_PHASE_AGNOSTIC_PHASES = {' … `'_GENERATION_DEPENDENT_PHASES = {"generation"}'`
  - `src/film_pipeline/graph/_agent_routing.py:35-47` — 9 phases only —
    `'_PHASE_DEFAULT_AGENTS: Mapping[str, str] = MappingProxyType(' … missing `generation` and `delivery`
  - plus `APPROVAL_GATES` (`src/film_pipeline/graph/_action_routing.py:49`), `_NEXT_PHASE_AFTER_APPROVAL` (`src/film_pipeline/graph/edges.py:40`),
    `_PHASE_TO_NODE` (`src/film_pipeline/graph/graph.py:55`), `_PHASE_NODES` (`src/film_pipeline/graph/nodes/_repair_loop.py:38`), each listing all 11 independently
- **Drift proof:** existing divergence. `_PHASE_DEFAULT_AGENTS` covers 9 of the 11 `PHASE_ORDER` entries, so
  `_default_agent_for("generation")` and `_default_agent_for("delivery")` fall through to
  `"orchestrator-agent"` (`src/film_pipeline/graph/_agent_routing.py:50-52`) — an unintended fallback that no test pins:
  `tests/unit/graph/test_create_path_routing.py:43-53` covers `shot_bible` only. Separately,
  `_PHASE_AGNOSTIC_PHASES` must stay the exact complement of `_GENERATION_DEPENDENT_PHASES`, but adding a phase
  to `PHASE_ORDER` requires three coordinated edits (`src/film_pipeline/graph/_action_routing.py:18`, `:33`, `:47`) with nothing
  enforcing agreement.
- **Reproduce:** (verified at HEAD — prints `['delivery', 'generation']` then `True`)
  ```bash
  .venv/bin/python -c "
  from film_pipeline.graph.router import PHASE_ORDER
  from film_pipeline.graph._agent_routing import _PHASE_DEFAULT_AGENTS
  from film_pipeline.graph._action_routing import _PHASE_AGNOSTIC_PHASES, _GENERATION_DEPENDENT_PHASES
  print('missing default agents:', sorted(set(PHASE_ORDER) - set(_PHASE_DEFAULT_AGENTS)))
  print('agnostic+gen-dependent == order:',
        set(_PHASE_AGNOSTIC_PHASES) | set(_GENERATION_DEPENDENT_PHASES) == set(PHASE_ORDER))"
  ```
- **Blast radius:** `_agent_routing.py`, `_action_routing.py`, `edges.py`, `graph.py`, `_repair_loop.py`,
  `src/film_pipeline/app/_graph_exec.py:427-441`, `src/film_pipeline/cli/driver.py:139-214`. User-visible: a create-path task in generation/delivery
  is routed to the orchestrator agent, which cannot produce the phase output.
- **Candidate owner module:** `phase-model` (audit 01, proposed home `schemas/phase.py`) — owns `FilmPhase`,
  `PHASE_ORDER`, the phase-class sets and the gate label; the orchestrator/routing registries listed here become
  **derived projections** of that catalog, not a second catalog. No new `phases.py` is proposed by this audit.
- **Extraction sketch:** re-key every registry in the owner list above by `FilmPhase` and derive
  `_PHASE_TO_NODE`/`_PHASE_NODES`/`_NEXT_PHASE_AFTER_APPROVAL`/`_PHASE_DEFAULT_AGENTS` from the catalog; guard
  test asserting each registry's key set is `⊆ PHASE_ORDER` (with intentional omissions declared, per F-PHASE-08)
  and that `set(_PHASE_AGNOSTIC_PHASES) | set(_GENERATION_DEPENDENT_PHASES) == set(PHASE_ORDER)`.
- **Prior art:** `docs/modular-architecture/audit/01-phase-model-and-transitions.md` §F-PHASE-02 — "The phase
  vocabulary and order are defined independently in eleven places across eight modules, and nothing pins
  agreement" (Critical, 4 × 4 = 16) — and §F-PHASE-08 — "Partial phase registries fall back silently for the
  phases they omit" (Medium, 3 × 2 = 6). What is new *here* is the routing-safety consequence of the
  `_PHASE_AGNOSTIC_PHASES`/`_GENERATION_DEPENDENT_PHASES` complement: `_advance_result` uses that complement to
  decide whether blocked providers gate the advance (`src/film_pipeline/graph/_action_routing.py:334-339`), so a phase omitted from both
  sets silently loses its provider gate — a consequence neither sibling finding records.

### F-OST-16 — Routing decisions are recorded in two channels; the operator-facing readers use the empty one

- **Class:** O1 (duplicated normative model) + O3 (split state authority)
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** Where the explainable routing record lives and which channel the operator/MCP surfaces read.
- **De-facto owners:**
  - `src/film_pipeline/graph/orchestrator_state.py:43` + `:307-327` — the declared channel and its explainable
    record shape — `'_ROUTING_DECISIONS = f"{_ORCH_NS}__routing_decisions"'` /
    `'"\"routing_decision_id\": f\"route:{datetime.now().strftime(\'%Y%m%d%H%M%S\')}:{selected_agent}\","'`;
    **zero production callers**
  - `src/film_pipeline/graph/nodes/_agent_handoff.py:125-142` — the channel that is actually written —
    `'routes: list[dict[str, Any]] = state.setdefault("_routing_decisions", [])'` … `'"routing_reason": route_result.routing_reason,'`
  - `src/film_pipeline/graph/orchestrator_state.py:114-118` — the `ORCH_CHANNELS` registry row that
    acknowledges the split, whose note literal is at `:117` —
    `'"shadow namespace; deletion scheduled with D13/P1 wire-or-delete"'`
  - Readers of the empty channel: `src/film_pipeline/mcp/tools/state.py:39` `"latest_decision = ostate.get_latest_routing_decision(state)"`
    (reported at `:49` as `route_reason=...`) and `src/film_pipeline/app/services/operator.py:232` (reported at `:244`)
- **Drift proof:** existing divergence, visible without a test. Put a handoff record in state
  (`{"_routing_decisions": [{"routing_reason": "why"}]}`) and `ostate.get_latest_routing_decision` returns
  `None` because it reads `_orchestrator__routing_decisions` (`src/film_pipeline/graph/orchestrator_state.py:330-338`); the MCP
  `get_orchestrator_summary` and the dashboard therefore always show `route_reason == ""` while
  `_routing_decisions` holds the reasons. Each side is pinned separately
  (`tests/unit/graph/test_orchestrator_state.py` for the owner's channel,
  `tests/unit/graph/test_channel_registry.py` for propagation) and no test crosses them.
- **Reproduce:** (verified at HEAD — prints `None []`)
  ```bash
  grep -rn "record_routing_decision\|_routing_decisions" src/film_pipeline --include=*.py
  .venv/bin/python -c "
  from film_pipeline.graph import orchestrator_state as o
  s = {'_routing_decisions': [{'routing_reason': 'why'}]}
  print(o.get_latest_routing_decision(s), o.get_routing_decisions(s))"
  ```
- **Blast radius:** `mcp/tools/state.py` (`get_orchestrator_summary`), `app/services/operator.py`
  (`get_dashboard.route_reason`), `nodes/_agent_handoff.py`. User-visible: the "why was this agent chosen"
  explanation is always blank on every operator surface.
- **Candidate owner module:** `graph/orchestrator_state.py` — one routing-decision channel with one typed write
  (`record_routing_decision`) that `_record_handoff` calls.
- **Extraction sketch:** have `_record_handoff` call `ostate.record_routing_decision` and delete
  `_routing_decisions`, or point `get_latest_routing_decision` at `_routing_decisions` and drop the shadow row;
  guard test asserting a handoff makes `get_orchestrator_summary()["route_reason"]` non-empty.
- **Prior art:** `documentation/reviews/arch-lens-observability.md:54` notes `record_routing_decision` "has
  **zero production callers** (tests only)"; still present at HEAD. New here: the second channel that *is*
  written, and the readers that point at the empty one.

### F-OST-17 — The review-cycle channel is declared, initialised and read on an operator surface, but has no production writer

- **Class:** O3 (split state authority) + O8 (missing contract) — a third dead channel alongside
  `_orchestrator__routing_decisions` (F-OST-16) and the failure/budget/provider writers (F-OST-12/13/14).
  Added by this revision after `verify-02.md` §"Missed in scope" 1.
- **Severity:** Medium (impact 2 × drift 3 = 6) — the surface field is always `None` (impact 2), and no test
  crosses the owner API with the MCP reader (drift 3).
- **Concern:** Whether a review cycle is active for the current phase, and who is allowed to open one.
- **De-facto owners:**
  - `src/film_pipeline/graph/orchestrator_state.py:35` + `:105-109` — the channel and its propagation spec —
    `'_ACTIVE_REVIEW_CYCLES = f"{_ORCH_NS}__active_review_cycles"'`, registered as
    `'OrchChannelSpec(\n        _ACTIVE_REVIEW_CYCLES,\n        "explicit",\n        "review-cycle writers return cycles in updates",\n    ),'`
  - `src/film_pipeline/graph/orchestrator_state.py:228-243` — the only writer, test-only —
    `'state.setdefault(_ACTIVE_REVIEW_CYCLES, []).append(cycle)'`, returning the `cycle` dict (not an update)
  - `src/film_pipeline/graph/orchestrator_state.py:246-252` / `:255-260` — `advance_review_round` /
    `close_review_cycle`, also test-only, which mutate the found cycle in place
  - `src/film_pipeline/graph/orchestrator_state.py:523` — `ensure_orchestrator_state` initialises the channel —
    `'state.setdefault(_ACTIVE_REVIEW_CYCLES, [])'`; declared in the schema at `src/film_pipeline/graph/state_schema.py:190`
    (`'_orchestrator__active_review_cycles: list[dict[str, Any]]'`)
  - `src/film_pipeline/mcp/tools/state.py:40` — the live reader —
    `'review_cycle = ostate.get_active_review_cycle(state, str(state.get("current_phase", "")))'`,
    published at `:55` as `'active_review_cycle=review_cycle,'`
- **Drift proof:** existing divergence, visible without a test. `grep -rn
  "start_review_cycle\|advance_review_round\|close_review_cycle" src/` returns only the three definitions —
  every other hit is `tests/unit/graph/test_orchestrator_state.py:62-91` — so nothing in `src/` ever appends to
  `_orchestrator__active_review_cycles` (the only `src/` initialisation is the empty list at `:523`). Yet the
  MCP orchestrator summary exposes `active_review_cycle` as a first-class field, so it is `None` for every
  project on every call. The surface is pinned by neither side: `test_orchestrator_state.py` exercises the owner
  API against a hand-built dict and never calls `get_orchestrator_summary`, so wiring a writer (or deleting the
  channel) cannot fail a test today. Secondary contract break: the registered propagation is `"explicit"`
  ("writers return cycles in updates"), but `start_review_cycle` returns the bare `cycle` dict after an
  in-place `append`; a caller that returned that dict as the channel update would put a `dict` into a
  `list[dict[str, Any]]` field instead of the list.
- **Reproduce:** (the second command prints `None`; the first shows no production caller)
  ```bash
  grep -rn "start_review_cycle\|advance_review_round\|close_review_cycle" src/ --include=*.py
  .venv/bin/python -c "
  from film_pipeline.graph import orchestrator_state as o
  s = {'current_phase': 'script'}
  o.ensure_orchestrator_state(s)
  print(o.get_active_review_cycle(s, 'script'))"
  ```
- **Blast radius:** `src/film_pipeline/graph/orchestrator_state.py:105-109,228-260`, `src/film_pipeline/graph/state_schema.py:190`, `src/film_pipeline/mcp/tools/state.py:40,55`.
  User-visible: the operator/MCP summary reports no active review cycle even during a review, and the
  `"explicit"` propagation contract for this channel is never exercised.
- **Candidate owner module:** `graph/orchestrator_state.py` — either wire `start_review_cycle`/
  `advance_review_round`/`close_review_cycle` into the review/repair nodes and return the full list per the
  `"explicit"` spec, or delete the channel, the three functions and the MCP field under the same
  D13/P1 wire-or-delete decision that governs `_orchestrator__routing_decisions`.
- **Extraction sketch:** the owner publishes the channel plus one `open_review_cycle(state, phase, ...) -> dict`
  update helper used by the QC/approval nodes; guard test asserting a started cycle makes
  `get_orchestrator_summary()["active_review_cycle"]` non-null (or, if deleted, that the summary key is gone).
- **Prior art:** new — this channel is not covered by any prior review (`documentation/reviews/*` records the
  routing-decision, failure, budget and provider writers, but not the review-cycle API).

### F-OST-18 — The QC validator→matrix-patch handoff is an undeclared, untyped key on the state dict, and the app's `run_validation` fills it with no consumer

- **Class:** O8 (missing contract) + O3 (split state authority)
- **Severity:** High (impact 3 × drift 5 = 15) — H9 proposed no numeric score, so §1.5 is applied directly. Impact
  is 3 (wrong internal state, recoverable) rather than F-VR-03's 4: the app path still copies the validator `issues`
  back (`src/film_pipeline/app/_graph_exec.py:340`), so the blocking gate still fires and only the durable per-row matrix patch is
  lost. Drift is 5 because no test can fail when either site changes (§1.5) — see the drift proof.
- **Concern:** How the per-row `MatrixRowUpdate`s the QC validators collect reach the `MatrixPatch` emitter, and
  which module owns that handoff.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/qc.py:421` — the only writer, an untyped string key stashed on the shared state
    dict — `pending: list[Any] = state.setdefault("_pending_row_updates", [])`
  - `src/film_pipeline/graph/nodes/qc.py:70` — the only consumer, which re-parses the list and pops the key —
    `pending_updates = state.pop("_pending_row_updates", [])`
  - `src/film_pipeline/graph/nodes/qc.py:39` — the only call site of that consumer, inside `qc_node` —
    `_emit_matrix_patch_from_findings(new_state)`
  - `src/film_pipeline/app/_graph_exec.py:336-337` — a second authority over the same key: `run_validation`
    (`:310`) clears it and then runs the *same* dispatch, never calling the consumer —
    `working.pop("_pending_row_updates", None)` / `_run_validators(working)`
  - `src/film_pipeline/graph/state_schema.py:102` — the graph state schema declares no such field —
    `class StudioGraphState(TypedDict, total=False):`
  - `src/film_pipeline/graph/orchestrator_state.py:93-165` — `ORCH_CHANNELS`, the declared list of keys that cross a
    node boundary, has no row for it — `ORCH_CHANNELS: tuple[OrchChannelSpec, ...] = (`
  - `tests/unit/graph/test_channel_registry.py:292-293` — the program's own writer-disposition sweep scopes itself
    to the registry keys plus four named extras, so the key is out of scope —
    `return frozenset(spec.key for spec in ORCH_CHANNELS) | _EXTRA_SWEEP_KEYS`
- **Drift proof:** existing divergence between two callers of one dispatch. `_run_validators` (`:115`) buffers one
  `MatrixRowUpdate` per per-shot finding through `_append_validator_report` (`:403`) → `_track_matrix_row_updates`
  (`:417-421`); `qc_node` consumes the buffer at `:39` and persists a `matrix_patch_qc` artifact plus `qc_patch_ref`
  (`:83-91`). `run_validation` calls the identical dispatch at `src/film_pipeline/app/_graph_exec.py:337` but writes back only `issues`,
  `_validation_reports` and `consensus_report_ref` (`:340-344`), so the buffer dies with the local `working` copy and
  no patch is written. The failure is silent and unpinnable today: `grep -rn
  "_pending_row_updates\|_emit_matrix_patch_from_findings\|qc_patch_ref" tests/` exits 1 — no test names the key, its
  consumer, or the ref — and the writer sweep is structurally blind to it, because the write is a `setdefault` call
  (a form the AST sweep does not inspect: `tests/unit/graph/test_channel_registry.py:254-272` handles only `state.update({...})`,
  `:280-288` only string-subscript assignments) *and* the key is outside `_sweep_scope()` (`:293`). The same silence
  covers the mutation: rename the literal at `src/film_pipeline/graph/nodes/qc.py:421` (or delete the `:39` call) and the pop at `:70` finds
  nothing, no patch is emitted on either path, and no test fails.
- **Reproduce:** (verified at `fb85baa`; the second command prints `tests exit=1`, the third prints
  `audit-docs exit=1` with no hits, and the probe prints the asymmetric call sets and the two `False` declarations)
  ```bash
  cd ${REPO_ROOT}
  grep -rn "_pending_row_updates" src/ tests/ --include=*.py
  grep -rn "_pending_row_updates\|qc_patch_ref\|_emit_matrix_patch_from_findings" tests/ --include=*.py; echo "tests exit=$?"
  grep -rn "_pending_row_updates" docs/modular-architecture/audit/ --exclude=02-orchestration-state-and-routing.md; echo "audit-docs exit=$?"
  UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
  import ast, pathlib
  src = pathlib.Path('src/film_pipeline')
  def calls(path, func):
      tree = ast.parse(path.read_text())
      for n in ast.walk(tree):
          if isinstance(n, ast.FunctionDef) and n.name == func:
              return sorted(c.func.id if isinstance(c.func, ast.Name) else c.func.attr
                            for c in ast.walk(n) if isinstance(c, ast.Call))
      return []
  qc, app = src/'graph/nodes/qc.py', src/'app/_graph_exec.py'
  print('qc_node      :', [c for c in calls(qc, 'qc_node') if 'validator' in c or 'matrix' in c])
  print('run_validation:', [c for c in calls(app, 'run_validation') if 'validator' in c or 'matrix' in c])
  print('declared in schema/registry:',
        '_pending_row_updates' in (src/'graph/state_schema.py').read_text(),
        '_pending_row_updates' in (src/'graph/orchestrator_state.py').read_text())
  "
  # src/film_pipeline/app/_graph_exec.py:336, src/film_pipeline/graph/nodes/qc.py:70, :421  (exactly three sites)
  # tests exit=1
  # audit-docs exit=1   (no other file under docs/modular-architecture/audit/ names the key)
  # qc_node      : ['_emit_matrix_patch_from_findings', '_run_validators']
  # run_validation: ['_run_validators']
  # declared in schema/registry: False False
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/qc.py` (the sequential QC node and its validator helpers) and
  `src/film_pipeline/app/_graph_exec.py` (`run_validation`, defined `:310`, reached from `StudioRuntime.run_validation`
  (`src/film_pipeline/app/runtime.py:234-236`) ← `OperatorService.run_validation`
  (`src/film_pipeline/app/services/operator.py:310-315`)); downstream, every consumer of `matrix_patch_qc` /
  `qc_patch_ref` (`src/film_pipeline/artifacts/matrix_projection.py`) and the shot-matrix row statuses it patches.
  User-visible: running validation on demand leaves the shot matrix unpatched — rows keep their pre-QC status and
  gain no `validation_refs` — while the identical dispatch through `qc_node` patches them, with no error and no
  audit signal.
  The MCP `run_validation` tool (`src/film_pipeline/mcp/tools/validation.py:280`) is a third implementation that never calls
  `_run_validators`; it neither fills nor drops this key, so H9's "app/MCP path" label holds only for the app path.
  **Reachability (corrected at the verify-16 re-check):** `OperatorService.run_validation` has **zero non-test
  callers** — the only calls in the tree are its own delegation at `src/film_pipeline/app/services/operator.py:315` and
  the tests at `tests/unit/app/services/test_operator_service.py:505,517` — and the CLI driver reaches runtime
  capability only through MCP tools (`src/film_pipeline/cli/driver.py:199-204` resolves `film_pipeline.mcp.tools`
  attributes, never `OperatorService` methods; its only runtime calls are `self.rt.get_project` at `:109,188`).
  There is no operator dashboard or TUI in this repository (`get_dashboard`,
  `src/film_pipeline/app/services/operator.py:226`, returns a `DashboardSummary` view model and is called only from
  `select_project` (`:200`) and tests). So the drop is reachable through the app validation path **as the tests
  invoke it**, and from any future caller of `OperatorService.run_validation`; **no shipped entry point currently
  reaches it**, because the one registered validation tool is the separate MCP implementation above. The defect is
  an O8 missing-contract defect in present-tense code, not a live user-facing regression.
- **Candidate owner module:** `graph/orchestrator_state.py` (this audit's proposed orchestrator-state & routing
  owner) — the handoff becomes a declared, typed channel, so no caller can half-participate; if audit 08 §F-VR-03's
  shared QC core (`validation/runtime.py`) is extracted first, that core owns the returned buffer and this key
  disappears.
- **Extraction sketch:** stop stashing the buffer on the shared state dict — have `_run_validators` return (or
  publish through a typed owner accessor) the `list[MatrixRowUpdate]` it collects, and make
  `_emit_matrix_patch_from_findings` take it as an argument. If the key must stay in state, declare it on
  `StudioGraphState`, give `ORCH_CHANNELS` a row (or add it to `_EXTRA_SWEEP_KEYS`), and extend
  `test_writer_sweep_matches_recorded_dispositions` to recognise `setdefault`/`pop`. Guard test: run the same
  per-shot blocking finding through `qc_node` and `app._graph_exec.run_validation` and assert both produce a
  `matrix_patch_qc` artifact / `qc_patch_ref` (the "equal side-effect keys" guard F-VR-03 already asks for).
- **Prior art:** `documentation/reviews/arch-lens-dataflow.md:202` already traces the shot-level path
  "… → `_pending_row_updates` → MatrixPatch artifact (`src/film_pipeline/graph/nodes/qc.py:71-95`) — patch exists only on the sequential
  path (F-4)", and its `:110` table records the sequential-vs-subgraph side-effect asymmetry;
  `docs/modular-architecture/audit/08-validation-and-review.md` §F-VR-03 (`:437,447-449,471`) owns the two-lifecycle
  equivalence and lists `src/film_pipeline/app/_graph_exec.py:337` as a call site; audit 09 §F-KBCTX-05 (`:292-304`) uses the same
  "declared in neither `ORCH_CHANNELS` nor `StudioGraphState`" argument for another undeclared node-local sidecar
  (`_last_kb_context_ref`). **Distinct from F-VR-03:** F-VR-03's invariant is behavioural equivalence of the QC
  entry paths; this finding's invariant is the handoff *contract* — the buffer has no declared type, no declared
  owner and no guard, which is why a third caller (`run_validation`) can implement half the protocol unnoticed.
  **What is new here:** the handoff key itself is the defect — its single consumer, its invisibility to the
  writer-disposition sweep, and the app path that fills it and silently drops it. No **other** file under
  `docs/modular-architecture/audit/` names the key:
  `grep -rn "_pending_row_updates" docs/modular-architecture/audit/ --exclude=02-orchestration-state-and-routing.md`
  prints nothing and exits 1 (the `--exclude` is required because this finding is itself the only `audit/` file
  that names the key, and counting that text was the earlier command's defect). Outside `audit/`, every mention is
  downstream of this finding: its source (`docs/modular-architecture/reviews/adversarial-coverage.md:405`), its
  mechanical confirmation (`docs/modular-architecture/reviews/orchestrator-verification-notes.md:431`), the verifier's
  re-check (`docs/modular-architecture/reviews/verify-16.md:81`), and the one
  ownership-map row that records it by id (`docs/modular-architecture/01-ownership-map.md:106`).

  *(Fix note, verify-16 §1.3: the previous sentence read "The key is named in **zero** audit files
  (`grep -rn _pending_row_updates docs/modular-architecture/audit/` → 0)"; that command in fact printed 11 hits,
  all inside this file.)*
- **Provenance:** uncovered by the adversarial coverage pass (`reviews/adversarial-coverage.md` §H9); added post-verification.

---

## 3. Ownership map

Writer(s) found by the sweep commands in §1. "Single" means exactly one production write path exists at HEAD.

| State field / policy | Writer(s) | Single or distributed |
|---|---|---|
| `_orchestrator__candidate_refs` | `src/film_pipeline/graph/nodes/_agent_artifacts.py:43-48` (`_publish_candidate_ref`, called from `_save_artifact:148`) | **Single** (guard: `test_candidate_ref_propagation.py`, `tests/unit/graph/test_channel_registry.py:296`) |
| `_orchestrator__approved_refs` | `src/film_pipeline/graph/nodes/approval.py:259-267` (`approve_phase_node`, via `ostate.set_approved_ref`) | **Single** (literal key spelling re-derived — F-OST-11) |
| `_orchestrator__pending_revisions` | `src/film_pipeline/graph/nodes/approval.py:277-293` (`request_revision_node` → `add_revision_request`) | **Single** |
| `_orchestrator__convergence` (rounds, `stalled`, `escalation_reason`) | `src/film_pipeline/graph/nodes/_repair_loop.py:69-78` (`increment_convergence_round`/`mark_stalled` + literal write) | **Distributed** — F-OST-02, F-OST-11 |
| `_stalled_phase` (second stall representation) | `src/film_pipeline/graph/edges.py:93`; also `src/film_pipeline/graph/nodes/_repair_loop.py:79` | **Distributed** — F-OST-02 |
| `human_approval_required` | `src/film_pipeline/graph/nodes/_shared.py:157` (per-phase gate), `src/film_pipeline/graph/nodes/prep.py:356` (withhold), `src/film_pipeline/graph/edges.py:92` (`_record_stall`), `src/film_pipeline/graph/subgraphs/qc.py:269`, `src/film_pipeline/graph/nodes/approval.py:224,265,283`, `src/film_pipeline/app/services/_project_discovery.py:56`, `src/film_pipeline/cli/driver.py:184` | **Distributed** (≥8 sites) — F-OST-02, F-OST-05 |
| `approved` | `src/film_pipeline/graph/nodes/_shared.py:156` + `src/film_pipeline/graph/nodes/prep.py:355` + `src/film_pipeline/graph/nodes/approval.py:251,264,282` + `src/film_pipeline/graph/subgraphs/qc.py:268` + `src/film_pipeline/cli/driver.py:183` | **Distributed** — F-OST-05 |
| `human_approval_phase` (gate label) | `src/film_pipeline/graph/nodes/_shared.py:158` (call-site literals), `src/film_pipeline/graph/subgraphs/qc.py:270`, `src/film_pipeline/app/_graph_exec.py:436`, `src/film_pipeline/app/_persistence.py:168`, `src/film_pipeline/app/runtime.py:120` | **Distributed** — F-OST-04 |
| `issues` (blocker list) | every phase node's `updates["issues"]`; `src/film_pipeline/graph/edges.py:95-107` (direct append); `src/film_pipeline/graph/nodes/_repair_loop.py:206` (`merge_issues`); `src/film_pipeline/app/_resume.py:74` (replace); `src/film_pipeline/app/_graph_exec.py:340` (replace); `src/film_pipeline/app/services/_generation_ops.py:173` (replace) | **Distributed** — F-OST-03 |
| Blocking-issue predicate | `src/film_pipeline/graph/_action_routing.py:90-92`, `src/film_pipeline/graph/router.py:64`, `src/film_pipeline/graph/nodes/approval.py:55`, +15 more | **Distributed** (18 sites) — F-OST-03 |
| `RouterResult` (`eligible`/`blocked`/`next_action`/`human_gate`) | `_action_routing.py` only (10 constructors/in-place annotators) | **Single** owner; the *vocabulary* is re-branched in `src/film_pipeline/mcp/tools/review.py:120-143` and `src/film_pipeline/app/services/operator.py:473-483` — F-OST-09 |
| Canonical blocker projection (`has_blockers`) | `router.get_blockers_for_state:43-87` | **Single** (guard: `test_router_blockers.py`); its predicate input is not — F-OST-03 |
| `_orchestrator__failure_decisions` | none in production (`add_failure_decision` test-only) | **No writer** — F-OST-14 |
| `_orchestrator__provider_health_snapshot` | none in production (`update_provider_health` test-only); live health lives in `src/film_pipeline/app/runtime.py:386-393` | **Split / no writer** — F-OST-13 |
| `_orchestrator__budget_snapshot` | none in production (`update_budget_snapshot` test-only); prompt reads `budget_snapshot` instead | **Split / no writer** — F-OST-12 |
| `_orchestrator__active_review_cycles` | none in production (`start_review_cycle`/`advance_review_round`/`close_review_cycle` test-only; `ensure_orchestrator_state` only initialises the empty list at `src/film_pipeline/graph/orchestrator_state.py:523`) | **No writer** (owner API dormant; read by `src/film_pipeline/mcp/tools/state.py:40` and published at `:55`) — F-OST-17 |
| `_orchestrator__routing_decisions` | none in production (`record_routing_decision` test-only); the live channel `_routing_decisions` is written by `src/film_pipeline/graph/nodes/_agent_handoff.py:125-142` | **Two parallel channels** (the namespaced one is permanently empty, yet read by `src/film_pipeline/mcp/tools/state.py:39` and `src/film_pipeline/app/services/operator.py:232`) — F-OST-16 |
| `_orchestrator__execution_brief` | `src/film_pipeline/graph/nodes/visual.py:92-97` (`set_execution_brief`) only | **Single** (guard: `tests/unit/graph/test_channel_registry.py:311-371`) |
| Auto-approval policy (`require_human_approval`) | read by `src/film_pipeline/graph/nodes/_shared.py:132-144` and `src/film_pipeline/graph/edges.py:18-25`; written to `resolved_config` by `src/film_pipeline/app/services/operator.py:144`, `src/film_pipeline/mcp/tools/projects.py:117`, `src/film_pipeline/mcp/tools/_profile_change.py:281`, `src/film_pipeline/config/runtime_overrides.py:21` | **Distributed** — F-OST-10 |
| Channel merge policy | `src/film_pipeline/graph/state_schema.py:171-174,210-211` (compiled graph) and `src/film_pipeline/app/_graph_exec.py:467-481` (manual/repair) | **Distributed** — F-OST-08 |
| Phase vocabulary | 7 registries — see F-OST-15 | **Distributed** — F-OST-15 |
| QC lifecycle | `src/film_pipeline/graph/graph.py:115` (subgraph) vs `src/film_pipeline/graph/nodes/_repair_loop.py:47` + `src/film_pipeline/app/_graph_exec.py:452` (node) | **Distributed** — F-OST-07 |
| `_resume_to_repair` (declared at `src/film_pipeline/graph/state_schema.py:204`) | written only by `src/film_pipeline/app/_graph_exec.py:392` (`_resume_to_repair(True)`); read by `src/film_pipeline/graph/graph.py:193` (`_route_current_phase`) and `src/film_pipeline/graph/nodes/_repair_loop.py:198,242` (reset to `False`) | **Cross-boundary single writer** — one writer in `app`, three readers in `graph`; the flag is not part of the `_orchestrator__*` namespace and is not in `ORCH_CHANNELS`, so the graph cannot observe its own repair trigger without the app setting it (C1-class; no dedicated finding — recorded here after `verify-02.md` noted the omission) |
| `_orchestrator__*` write by MCP tools | **none** — `mcp/tools/*` only call `ensure_orchestrator_state` on a shallow copy (`src/film_pipeline/mcp/tools/state.py:36-38`, `src/film_pipeline/mcp/tools/review.py:97-100`) and read via `ostate` accessors | **Clean** (see §4) |
| `_orchestrator__*` write by `app/` | **none** — `src/film_pipeline/app/services/operator.py:229-231` is the only site and it mutates a copy | **Clean** |

---

## 4. Clean concerns

1. **Candidate→approved ref promotion is single-writer.** `set_approved_ref` has exactly one call site
   (`src/film_pipeline/graph/nodes/approval.py:261`, inside `approve_phase_node`), and `set_candidate_ref` exactly one
   (`src/film_pipeline/graph/nodes/_agent_artifacts.py:48`). Guard tests: `tests/unit/graph/test_candidate_ref_propagation.py`,
   `tests/unit/graph/test_wrapup_nodes.py:21`, and the writer sweep
   `tests/unit/graph/test_channel_registry.py:296-305`.
2. **Node-boundary propagation is registry-driven with no local key lists.**
   `src/film_pipeline/graph/nodes/_agent_handoff.py:60-73` iterates `ORCH_CHANNELS`; `src/film_pipeline/graph/orchestrator_state.py:93-165` is the only place a
   channel is declared. Guard tests: `tests/unit/graph/test_channel_registry.py:113-205` (policy parity) and `:200-205`
   (`_services`/unknown keys are never copied).
3. **Action selection itself is single-owner.** `grep -rn "compute_actions(" src/` shows the definition in
   `src/film_pipeline/graph/_action_routing.py:348` and consumers only (`src/film_pipeline/graph/edges.py:64`, `src/film_pipeline/graph/router.py:55`, `src/film_pipeline/app/services/operator.py:231,273`,
   `src/film_pipeline/mcp/tools/state.py:38,68`, `src/film_pipeline/mcp/tools/review.py:100`). No module computes eligible actions independently.
4. **The canonical blocker *projection* is single-owner — but it is not the only issue-list projection.**
   `router.get_blockers_for_state` (`src/film_pipeline/graph/router.py:43-87`) is defined once and consumed by
   `src/film_pipeline/mcp/tools/state.py:89`, `src/film_pipeline/mcp/tools/projects.py:293`, and `src/film_pipeline/app/services/operator.py:450` (`_has_blockers`); the old
   `runtime.get_blockers`/`add_blocker`/`BlockerReporter` path flagged in
   `documentation/reviews/arch-lens-observability.md:121` is **gone from `src/` at HEAD** (grep finds no
   `block_entries`, `add_blocker`, or `BlockerReporter`). Guard tests: `tests/unit/graph/test_router_blockers.py`.
   Narrowed by `verify-02.md`: the same `state["issues"]` channel is *also* projected into blocker/message lists
   independently — `operator._blocking_state_issues` (`src/film_pipeline/app/services/operator.py:453-459`, used at `:276` for the review
   workspace), the inline blocking/non-blocking split in `operator.get_validation_workspace`
   (`:299-300`), and `mcp/tools/review.py:_blocking_issues` (`:63-65`, used at `:56,101`). Those three are the
   F-OST-03 predicate-duplication surface, so "one projection" would be too strong; the accurate statement is
   that the *router* projection has one definition and three callers.
5. **MCP tools and `app/services` do not write orchestrator state.** `grep -rn "_orchestrator" src/film_pipeline/mcp src/film_pipeline/app`
   finds only imports, `ensure_orchestrator_state(...)` calls on `dict(state)` copies, and reads
   (`src/film_pipeline/mcp/tools/state.py:36-38`, `src/film_pipeline/mcp/tools/review.py:97-100`, `src/film_pipeline/app/services/operator.py:229-231`). The
   no-mutation property is guarded for the router path only:
   `tests/unit/graph/test_router_blockers.py:21-25`
   (`test_blocker_projection_does_not_initialize_live_state`). **Guard gap:** the equivalent MCP
   `get_orchestrator_summary`/`get_next_actions` copies (`src/film_pipeline/mcp/tools/state.py:36,68`) have no such test.
6. **`_orchestrator__execution_brief` has a single writer and an end-to-end regression guard** —
   `src/film_pipeline/graph/nodes/visual.py:92-97` writes it, `src/film_pipeline/graph/orchestrator_validators/brief.py:21-33` reads it through the owner
   accessor, and `tests/unit/graph/test_channel_registry.py:311-371` pins both the boundary crossing and replay idempotency.
7. **Explicit absence: no guard test exists** for `merge_issues` / the `__remove_codes__` sentinel
   (`grep -rln "merge_issues" tests/` → nothing; `grep -rn "__remove_codes__" tests/` → nothing), for the
   repair loop's `_start_round`/`max_rounds=3` (`grep -rn "max_rounds=3\|_start_round" tests/` → nothing), or
   for `add_failure_decision`/`update_provider_health`/`update_budget_snapshot` in production (F-OST-12, -13,
   -14). Corrected by `verify-02.md`: the `ORCHESTRATOR_STALLED` *issue* **is** guarded
   (`tests/unit/graph/test_real_human_gates.py:140,148`) — only the stall *cap* is unguarded (F-OST-02), and
   the earlier draft wrongly listed the issue code here.

---

## 5. Candidate module boundary

A single **orchestrator-state & routing owner** should hold, and nothing else should be able to:

- **Owns (N):** the orchestrator state grammar — the key set, the per-key shape, the
  `OrchestratorKey`/`ORCH_CHANNELS` registry, the channel-merge policy (`REDUCERS`), the action vocabulary, the
  issue/blocking model, the stall policy, and the validation-status severity order. It **consumes** the phase
  catalog (order, gate label, phase node, default agent, successor) from audit 01's `phase-model`; it does not
  define it — see "Cross-cluster ownership reconciliation" below.
- **Enforces (I):** `is_stalled`/stall cap, `may_approve(state)`, `is_blocking(issue)`,
  budget/provider/failure input admission, and the single channel-merge policy. The gate-mode predicate
  (`require_human_approval`) is owned by `phase-model` (audit 01 §F-PHASE-07); this owner consumes it.
- **Writes (R):** every `_orchestrator__*` key and the orchestrator-owned gate flags
  (`human_approval_required`; the `human_approval_phase` label is supplied by the `phase-model` gate map);
  the canonical blocker projection.

**Public contract (proposed):**

```
# state grammar
ORCH_CHANNELS: tuple[ChannelSpec, ...]        # single source for keys + propagation + shape
REDUCERS: Mapping[str, Reducer]               # derived from StudioGraphState annotations, one source
# phase catalog: imported from phase-model (audit 01); NOT re-declared here
# policy
may_approve(state) -> ApprovalDecision
is_stalled(state, phase) -> bool              # one cap, one representation
is_blocking(issue) -> bool
require_human_approval(state) -> bool         # re-exported from phase-model
resolve_action(state) -> RouterResult         # single producer of the action vocabulary
describe_action(action) -> str
# typed writes only
set_candidate_ref / set_approved_ref / add_revision_request / resolve_revision
open_review_cycle(state, phase, ...) -> dict  # or the channel is deleted (F-OST-17)
record_failure_decision(FailureDecision) / update_budget(BudgetSnapshot) / update_provider_health(...)
findings_to_issues(reports) -> list[IssueRecord]
```

**Writers that must become read-only consumers:**

| Current writer | Becomes |
|---|---|
| `src/film_pipeline/graph/edges.py:92-93,128` (state mutation inside routing functions) | returns a routing key; `await_approval_node`/`repair_phase_node` apply the stall through the owner |
| `src/film_pipeline/graph/nodes/_shared.py:154-159` + every `gate=` literal | reads the `phase-model` gate map (`PHASE_GATES[phase]`) |
| `src/film_pipeline/graph/nodes/prep.py:339-356`, `src/film_pipeline/graph/nodes/approval.py:220-225` | calls `may_approve(state)` |
| `src/film_pipeline/graph/subgraphs/qc.py:262-271` | returns reports/refs; the owner sets gate flags |
| `src/film_pipeline/graph/nodes/approval.py:58-66,267,293`; `src/film_pipeline/graph/nodes/_repair_loop.py:70-78,235,238-240`; `src/film_pipeline/graph/nodes/_context.py:81` | uses owner accessors (`get_approved_refs`, `get_pending_revisions`, `get_convergence`, …); no `_orchestrator__` literal outside the owner |
| `src/film_pipeline/app/_graph_exec.py:467-481` | consumes `REDUCERS` |
| `src/film_pipeline/app/_resume.py:74`, `src/film_pipeline/app/services/_generation_ops.py:173`, `src/film_pipeline/app/_graph_exec.py:340` | emits the `__remove_codes__` sentinel through the owner's issue API instead of replacing `issues` |
| `src/film_pipeline/app/services/operator.py:473-483`, `src/film_pipeline/mcp/tools/review.py:120-143` | call `describe_action` |
| `src/film_pipeline/app/runtime.py:386-393` (provider health) | projects into the owner channel at invoke time (single writer) |
| `src/film_pipeline/cli/driver.py:182-184` | presentation only; must not be the source of `approved`/`human_approval_required` |

**Guard tests that would fail if the seam regresses:** key-set equality between owner constants and the TypedDict
(F-OST-01); single-representation stall at one cap (F-OST-02); one `is_blocking` used by `compute_actions`,
`get_blockers_for_state`, and `approve_phase_node` (F-OST-03); the `phase-model` gate map value == the gate
written by the phase node (F-OST-04; audit 01 guard #4); one `may_approve` predicate (F-OST-05); every
`next_action` value returned by `compute_actions` over a state matrix has a `describe_action` entry (F-OST-09);
`run_phase_node` and a compiled graph step produce identical channels (F-OST-08); routing blocks a build whose
runtime provider is blocked (F-OST-13); a typed `FailureDecision(severity="blocking")` routes to
`escalate_to_failure_handler` (F-OST-14); every phase-model catalog entry has gate/node/default-agent/successor
(F-OST-15); a recorded handoff makes `get_orchestrator_summary()["route_reason"]` non-empty (F-OST-16); a started
review cycle makes `get_orchestrator_summary()["active_review_cycle"]` non-null, or the channel and its MCP
field are deleted (F-OST-17); no `_orchestrator` key literal and no orchestrator-prefix filter exists outside
the owner module (F-OST-11); **the owner's exported surface stays bounded** — `docs/modular-architecture/enola-out/insights.json:4946`
records "Large public surface: src/film_pipeline/graph/orchestrator_state exports 38 of 38 symbols (100%)", so
a guard should assert a declared `__all__` (or an explicit "public accessors + registry" subset) rather than
letting every new helper join the public API.

**Structural constraint (enola):** `docs/modular-architecture/enola-out/llm_context.md:410` records the cycle
`graph -> graph/nodes -> graph/orchestrator_validators -> graph/subgraphs -> graph`. The orchestrator-state
owner sits inside that cycle at its centre; the extraction in §5 must not add a fifth leg (in particular,
`graph/nodes/*` and `graph/subgraphs/qc.py` may import the owner, and the owner must import neither).

**Non-goals:** the owner does not run agents, does not load artifacts, does not own artifact storage or
validation adapters (it consumes their reports through `findings_to_issues`), and does not persist services
(`_services` stays runtime-only, `src/film_pipeline/graph/services.py:137`).

---

## 6. Unverified hypotheses (explicitly not findings)

Per §1.6.6 these are recorded but excluded from the finding list:

- **Framework semantics of edge-time mutation.** F-OST-02 cites `src/film_pipeline/graph/edges.py:92-93` writing `state[...]`
  inside `after_approval`. Whether LangGraph persists mutations made by a conditional-edge function
  (as opposed to channel updates returned by nodes) was **not verified** in this audit; the finding rests on the
  duplicated representation and the reader split, not on that behaviour.
- **Real-runtime provider-health propagation.** It was not verified whether any runtime path outside `src/`
  (scripts, CI fixtures, operator tooling) writes `_orchestrator__provider_health_snapshot` or
  `_orchestrator__budget_snapshot`; the grep in F-OST-12/-13 covers `src/` only.
- **Whether `_PHASE_DEFAULT_AGENTS`' missing `generation`/`delivery` entries are deliberate.** No comment,
  test, or doc states an intent; recorded as an unenforced gap, not as an intentional design.

---

## 7. Cross-cluster ownership reconciliation

`verify-02.md` dispute 5 found that this audit (§5, F-OST-04, F-OST-10, F-OST-15) and
`docs/modular-architecture/audit/01-phase-model-and-transitions.md` nominated two owners for the same phase
facts. The resolution applied in this revision:

| Fact / policy | Owner after reconciliation | This audit's role | Sibling finding |
|---|---|---|---|
| `FilmPhase`, `PHASE_ORDER`, phase-class sets | `phase-model` (audit 01, proposed home `schemas/phase.py`) | derived projections only | `01 §F-PHASE-02` (Critical 4×4=16) |
| Gate label map (`APPROVAL_GATES` → `PHASE_GATES`) | `phase-model` | consumes the label for `RouterResult.human_gate` / operator surfaces | `01 §F-PHASE-03` (High 3×4=12) — F-OST-04 re-rated to match |
| Successor / advance transition law | `phase-model` | consumes `advance_decision()` in `_advance_result` | `01 §F-PHASE-04` |
| Gate-mode predicate (`require_human_approval`) | `phase-model` | consumes it; owns only the published `human_approval_required` field | `01 §F-PHASE-07` (Medium 3×2=6) — F-OST-10 re-rated to match |
| Partial per-phase registries (`_PHASE_DEFAULT_AGENTS`, `PHASE_BUILDERS`) | `phase-model` owns the key discipline (`⊆ PHASE_ORDER`, omissions declared) | consumes `_PHASE_DEFAULT_AGENTS` in `_agent_routing` | `01 §F-PHASE-08` (Medium 3×2=6) — F-OST-15 re-rated to match |
| Orchestrator key set, `ORCH_CHANNELS`, `REDUCERS`, action vocabulary, stall cap, issue/blocking model, budget/provider/failure admission, review-cycle channel | **this audit's orchestrator-state owner** | sole owner | not claimed by audit 01 |
| `_PHASE_TO_NODE` / `_PHASE_NODES` / `_NEXT_PHASE_AFTER_APPROVAL` | `phase-model` (derived views) | read-only consumers | `01 §F-PHASE-02`, `§F-PHASE-04` |

**Open reconciliation items for `03-target-architecture.md`** (recorded, not resolved here):

1. **Where the orchestrator-state owner lives.** This audit's `graph/orchestrator_state.py` owner and audit 01's
   `schemas/phase.py` `phase-model` must have a declared import direction: the phase model must not import
   orchestration state, and the orchestrator owner must import the phase model (never the reverse). Neither
   audit fixes the module path of the orchestrator owner (`graph/` vs a new package).
2. **Who owns the phase *gate flag* write.** F-OST-04 gives the gate *value* to `phase-model`;
   `_phase_gate_updates` (`src/film_pipeline/graph/nodes/_shared.py:154-159`) currently writes both `human_approval_phase` and
   `human_approval_required`/`approved`. The target architecture must say whether the gate writer lives with the
   phase model (which would make `nodes/_shared.py` a phase-model consumer) or with the orchestrator owner
   (which would make it read the gate map). This audit assumes the former.
3. **Single severity per shared defect.** F-OST-04, F-OST-10 and F-OST-15 are now aligned to their siblings'
   severities; `03-target-architecture.md` should confirm that rule (one severity per shared defect, taken from
   the owning cluster) rather than re-rating the same evidence per cluster.
