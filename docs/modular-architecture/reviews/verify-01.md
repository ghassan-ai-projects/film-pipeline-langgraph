# Verify 01 — adversarial verification of `audit/01-phase-model-and-transitions.md`

Verifier: independent agent (did not write the audit). Repo
`${REPO_ROOT}`, branch `modular-app`,
HEAD `fb85baa`, clean tree (`git status --porcelain` empty). All anchors opened
at HEAD; all drift proofs re-executed with `.venv/bin/python` (3.12.13) or
reproduced greps; throwaway scripts only under `/tmp`. No `src/`, `tests/`, or
audit file was modified. Cross-checked against
`docs/modular-architecture/enola-architecture-facts.md` and
`enola-out/insights.json` for the coupling/lifecycle findings.

Headline equality script (audit lines 18–35) reproduced exactly: `True / True /
True`. All 11 inventory definitions resolve and are keyed identically at HEAD;
the defect is duplication-without-agreement, not divergence.

| Finding | Verdict | One-line reason |
|---|---|---|
| F-PHASE-01 | CONFIRMED | Divergence reproduced (`GRAPH continue_unrelated_work` / `APP generation`); anchors resolve; Critical ≥16 holds after recompute. |
| F-PHASE-02 | CONFIRMED | 11 definitions in 8 files re-verified; mutation → `wrap` reproduced; no agreement test. Count wording disputed. |
| F-PHASE-03 | CONFIRMED | `APPROVAL_GATES` vs 11 node `gate=` literals vs QC inline all resolve; all 11 values agree but no test compares them. |
| F-PHASE-04 | CONFIRMED | `_NEXT_PHASE_AFTER_APPROVAL` and `PHASE_ORDER`-index successor both resolve; qc/post swap is unguarded by any cited test. |
| F-PHASE-05 | CONFIRMED | Second order authority at `store.py:501` / `project_storage.py:136` real; but the stated mutation outcome is inverted (see Disputes). |
| F-PHASE-06 | CONFIRMED | Existing gap reproduced (`after_phase` → `consistency_check`); mutation clause is false (see Disputes). |
| F-PHASE-07 | CONFIRMED | Both predicates and their config-key reads verified; no test asserts agreement. Stated stall consequence imprecise. |
| F-PHASE-08 | CONFIRMED | 9/11 and 7/11 partial maps verified; silent `orchestrator-agent` / empty-context fallback reproduced. |
| F-PHASE-09 | CONFIRMED | All five policy literals resolve; `requires_regeneration` has *zero* test references (stronger than claimed). |
| F-PHASE-10 | DOWNGRADED | Core O4 holds for **two** phase→validator tables, not three; `_VALIDATOR_MAP`/`_WORKER_NODES` are not phase-keyed; prior art exists. Severity unchanged (Medium 6). |

---

## Non-CONFIRMED — expanded

### F-PHASE-10 — DOWNGRADED (claim scope; severity unchanged, Medium 2×3=6)

The headline "Three phase→validator registries" is not supported by the cited
anchors:

- `src/film_pipeline/graph/subgraphs/qc.py:45` — `"_VALIDATOR_MAP: dict[str, str] = {"`
  keys are validator **ids** (`"script-structure"`, `"assembly"`, …), not phases;
  consumed as `cls = _VALIDATOR_MAP.get(validator_id, "")` (`:133`).
- `src/film_pipeline/graph/subgraphs/qc.py:210-217` — `_WORKER_NODES` is a tuple of
  graph node names, not a phase map.
- `src/film_pipeline/graph/subgraphs/qc.py:154` — `_VALIDATOR_ARTIFACTS: dict[str, tuple[str, ...]]`
  is a third validator-id registry the audit omits entirely
  (`"assembly": ("assembly_manifest", "review_cut", "final_cut")`).

Only two of the cited tables are genuinely phase-keyed: `_VALIDATOR_RUNNERS`
(`graph/nodes/qc.py:361`, `({"post", "assembly", "qc"}, _run_assembly_validators)`)
and `_live_validator_specs` (`mcp/tools/validation.py:123`, `phases=("post", "assembly")`).
The surviving O4 claim (these two must agree, nothing enforces it) is real, and
the dead `"assembly"` alias is reproduced:

```
$ .venv/bin/python -c "... print([p for p in ('post','assembly') if p not in [x.value for x in FilmPhase]])"
['assembly']
```
`_parse_phase` (`mcp/tools/validation.py:28-33`) raises-returns `None` via
`FilmPhase(phase_str)`, and `run_validation` rejects before `_run_live_validators`
(`:290-292`), so `phases=("post", "assembly")` is unreachable — the audit's
"dead branch" claim is correct.

Prior art is misstated: `documentation/reviews/arch-lens-flexibility.md:17`
already records both dispatch tables ("wire into dispatch:
`graph/subgraphs/qc.py` name→class map (:46-51) **or**
`mcp/tools/validation.py` per-phase tuple fns (:73-115)"), contradicting
"Prior art: … searched; none" (A7 violation). Also, `tests/unit/graph/test_qc_validator_dispatch.py`
does guard `_VALIDATOR_RUNNERS` membership (the audit says "no test compares
them" — true only for *cross*-registry comparison; the file should be named).

Recomputed: impact 2 (recoverable internal divergence) × drift 3 (no cross-registry
test) = **6 Medium** — same score, reduced scope.

---

## Missed in scope

### M1 — `_APPROVAL_DESTINATIONS` is a hand-copied restatement of `_PHASE_TO_NODE`; the ownership map wrongly calls phase→node "single definition"

`src/film_pipeline/graph/graph.py:55-67` defines the 11 phase→node names;
`src/film_pipeline/graph/graph.py:85-99` defines the same mapping again for 10
phases plus `end`/`repair`/`await_approval`. Reproduced:

```
shared keys: ['constitution','delivery','development','gen_planning','generation','post','qc','script','shot_bible','visual_dev']
values identical: True
phase keys in _PHASE_TO_NODE not in _APPROVAL_DESTINATIONS: {'intake'}
_APPROVAL_DESTINATIONS extra: {'repair','await_approval','end'}
```
`_AFTER_PHASE_DESTINATIONS` (`:70-76`) is correctly derived via `**_PHASE_TO_NODE`;
`_APPROVAL_DESTINATIONS` is not. No test references it
(`grep -rn "_APPROVAL_DESTINATIONS\|_PHASE_TO_NODE\|_ROUTER_DESTINATIONS" tests/ --include='*.py'`
→ no matches), and deleting an entry still compiles —
`.venv/bin/python` with `del _APPROVAL_DESTINATIONS["post"]; build_graph()` → `build_graph: OK`.
The ownership map row "Phase → node name | `graph/graph.py:55` | single definition" is
therefore false under §1.4 O1. The audit's own candidate-owner table would derive
both, so this is an internal inconsistency rather than a wholly new concern.

### M2 — `_UPSTREAM_CONTENT_SOURCES`: 8 phase-name literals the sweep cannot see

`src/film_pipeline/graph/nodes/_context.py:329` — `_UPSTREAM_CONTENT_SOURCES: dict[str, tuple[str, str]]`
holds `("constitution", …)`, `("development", …)` ×2, `("script", …)` ×2,
`("shot_bible", …)` ×2, `("visual_dev", …)` as tuple **values**, so the audit's
line-initial regex `^\s*"<phase>"` (audit:81) never matches them. The phase
element is unpacked as `_phase_name` and never used
(`:351 for ref_key, (_phase_name, content_key) in _UPSTREAM_CONTENT_SOURCES.items()`);
no test references the map (`grep -rn _UPSTREAM_CONTENT_SOURCES tests/` → none).
This is not cosmetic as a sweep result: any-position phase-string occurrences in
`src/` total **359**, versus the audit's **129** line-initial entries, so the
"11 definitions / 8 modules" set is a lower bound, and the audit's
"# 129 line-initial entries across 8 modules" comment is wrong on both counts
(the grep spans **16** files; see D2).

### M3 — KB phase applicability is an unvalidated free-string phase registry, absent from Coverage

`src/film_pipeline/schemas/kb.py:25` — `applies_to_phases: list[str] = Field(default_factory=list)`;
`src/film_pipeline/kb/manifest.py:44` — `if "all" in i.applies_to_phases or phase in i.applies_to_phases`.
Data at `film-knowledge-base/index/kb-manifest.yaml` carries phase lists
(`applies_to_phases: [generation, post]`, `[qc, post]`, `[visual_dev, gen_planning]`, …).
Nothing validates tokens against `FilmPhase`, and the only test
(`tests/unit/kb/test_manifest.py:48-53`) asserts a loose `len(items) >= 8`, so a
typo'd or renamed phase silently stops applying with no failing test (O8/O4).
`kb/` appears nowhere in the audit's Coverage table although §A1 lists it.

---

## Disputes requiring the author to fix

- **D1 (F-PHASE-02 count).** "ten the full 11-name set" is false. Inventory item 6
  `_APPROVAL_DESTINATIONS` (`graph.py:85`) has **10** phase keys (omits `intake`,
  confirmed programmatically), and item 11 `_PHASE_DEFAULT_AGENTS` has 9. Nine
  definitions carry the full set; the count is 9 full + 1 10-of-11 + 1 9-of-11.
  The same error is repeated in the Ownership map ("10 full 11-name definitions +
  1 9-of-11").
- **D2 (F-PHASE-02 reproduce).** `grep -rcE '^\s*"…"' -r src/film_pipeline …`
  returns **129** entries spread over **16** files (per-file output:
  `artifacts/registry.py`, `checkpoints/invalidation.py`, `app/mock_responses.py`,
  `mcp/tools/planning.py`, `graph/nodes/generation.py`, `graph/nodes/qc.py`,
  `graph/nodes/visual.py`, `graph/nodes/_shared.py`, …), not "across 8 modules".
  The 8-module figure belongs to the full-vocabulary definitions, not the grep;
  the comment conflates them.
- **D3 (F-PHASE-05 drift proof inverted).** Reproduced with a real
  `ProjectStorage.latest_artifact_phase` over a project holding both `08-validation`
  and `09-post` artifacts:
  ```
  current map order tail: ['qc', 'post', 'delivery']   -> latest: post
  mutated order tail:     ['post', 'qc', 'delivery']   -> latest: qc
  ```
  The audit says moving `post` above `qc` makes it "report `post`"; it reports
  `qc`. Correct statement: reordering the map makes the storage layer return an
  *earlier* phase as "latest" (resume point moves backwards). The seam is real
  and the absence of any order test is verified; only the mechanism is wrong.
- **D4 (F-PHASE-06 mutation clause false).** Changing the literal at
  `graph/_action_routing.py:221` to `"escalate_failure"` fails
  `tests/unit/test_graph.py:138`, `tests/integration/test_dynamic_routing.py:48`,
  and `tests/e2e/test_orchestrator_decision_loop.py:134` (all assert
  `next_action == "escalate_to_failure_handler"`), so "no routing test fails" is
  wrong. The *valid* drift proof is the existing gap, which I reproduced:
  `after_phase` with a mocked `compute_actions` returns `consistency_check`
  (`edges.py:86-87`), and no graph/edges test asserts that destination.
- **D5 (F-PHASE-10).** See expanded row: three-registry headline false,
  `_VALIDATOR_ARTIFACTS` omitted, prior art exists at `arch-lens-flexibility.md:17`.
- **D6 (prior-art anchors, §1.6.1).** F-PHASE-03 and F-PHASE-05 cite
  `documentation/reviews/arch-lens-flexibility.md:120`; line 120 is the
  "Agent capability tokens" row. The phase-vocabulary row is line **119**, and
  neither line mentions gate tables or `PHASE_DIR_MAP`. Only line **19** supports
  the quoted "five hand-maintained parallel phase tables with no single source".
- **D7 (candidate owner incoherence).** `phase-model` is proposed at
  `schemas/phase.py` with `advance_decision(state) -> RouterResult` in its public
  contract (audit:400-402). `RouterResult` lives in `graph/_action_routing.py:64`
  and the decision needs `graph.orchestrator_state.get_blocked_providers`
  (`_action_routing.py:334`). `graph` already imports `schemas`, so that placement
  creates a new `schemas ↔ graph` cycle. The enola snapshot at HEAD has exactly
  five cycles and none is `schemas ↔ graph` (`enola-architecture-facts.md` §2;
  insight source `cycles` lists schemas only with `schemas/registries`), and
  `schemas` is the shared kernel (fan-in 509, §3). The transition invariant
  (`successor`, `advance_decision`, provider refusal) belongs in `graph`; only
  `FilmPhase`/`PHASE_ORDER`/`PHASE_GATES` and the vocabulary-derived policy sets
  belong in the shared kernel. This does not duplicate `artifacts.PHASE_DIR_MAP`
  (kept in `artifacts`, only re-keyed) — that part of the design is coherent.
- **D8 (F-PHASE-01 impact wording).** "can start the paid generation phase" is
  overstated: `generation_node` runs `_plan_generation_ledger` and
  `_gate_dispatch_readiness` and then parks at `generation_batch`
  (`graph/nodes/generation.py:108`); no provider spend occurs on entry.
  Recompute impact 4 (gate-policy bypass, spend only on subsequent approval) ×
  drift 4 = **16, still Critical** — score survives.
- **D9 (F-PHASE-09 class/scope).** The five cited literals are distinct policies
  that each re-encode phase names as raw strings (regeneration set, extractor
  keywords, budget caps, critical context, intake guard); they are not "the same
  map defined in 2+ modules". O1 is defensible for the vocabulary leak, but the
  block mixes five concerns against §1.1/§1.7, and the regeneration/budget/context
  policies should stay with their modules — `phase-model` should own only the
  `FilmPhase` keys, not the policies.
- **D10 (F-PHASE-07 consequence).** With `_require_human_approval` returning
  `False`, `_phase_gate_updates` sets `approved = not _require_human_approval`
  → `True` (`_shared.py:153-157`), so `after_approval` advances rather than
  "loops `await_approval` on stall". The asymmetry is real in the opposite
  direction; the stated failure mode should be corrected. Minor: F-PHASE-01 says
  `test_resume_integrity.py:91-100` is "the only test on this path", but
  `test_stalled_resume_advances_and_audits` (`:224`) exercises the second call
  site too (also without asserting target phase/provider health).

---

## Overall verdict

All ten findings are real and independently reproduced (no REJECTED; one
DOWNGRADED in scope, none in severity); the audit's core claims survive, but
D1–D7 and D9–D10 must be corrected before the file can be called verified under
§A2/§A6, and M1–M3 extend its inventory.
