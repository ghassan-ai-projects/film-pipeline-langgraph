# Phase 01 — State-Safety Guardrails

**Roadmap items:** P0 #1 (D1 channel registry + parity test; consumes DF-F2), P0 #2 (D6 resume
integrity incl. O-F4), P0 #3 (B-F4 mock fixtures relocation).
**Source review:** [`../architecture-review.md`](../architecture-review.md) §Roadmap P0 1–3;
lens detail in `../reviews/arch-lens-dataflow.md` (F-1, F-2, F-5), `arch-lens-boundaries.md` (F-4),
`arch-lens-observability.md` (F-4).
**Baseline at plan time:** `make ci-check` green (1945 passed / 6 skipped, coverage 91.95%, mypy
strict clean, product gate PASS). Branch `arch-improvement-review`.

Theme: make the three silent-failure classes machine-checked — unpropagated orchestrator channels
(the D-009 bug class), gate-bypassing resume fallbacks, and fixture data on the production default
startup path.

---

## Item A — Orchestrator channel registry + parity test [D1 / DF-F1 / DF-F2]

### Ground truth (verified at HEAD)

- `graph/orchestrator_state.py:22-63` defines exactly ten `_orchestrator__*` channel constants:
  candidate_refs, approved_refs, active_review_cycles, pending_revisions, routing_decisions,
  convergence, failure_decisions, provider_health_snapshot, budget_snapshot, execution_brief.
- `graph/nodes/_agent_handoff.py` propagates across the node boundary via four hand-maintained
  lists: `_copy_decision_channels` (:18-22 → `_routing_decisions`, `_repair_feedback`,
  `_validation_reports`), `_copy_published_candidate_refs` (:25-38 → `_orchestrator__candidate_refs`
  only), `_append_new_reducer_entries` (:40-59 → `issues`, `validation_report_refs`, sliced against
  input). `_capture_run_outcome` (:90-102) separately hand-carries `_routing_decisions` and clears
  consumed `_repair_feedback`.
- Consequence [DF-F1]: no test fails when a new channel is added unpropagated (D-009 precedent).
- Live DF-F2 instance: `visual.py:79-108` `_ensure_execution_brief` calls
  `set_execution_brief(new_state, brief)` → writes `_orchestrator__execution_brief` into the node
  working copy; **`shot_bible_node`'s propagation block at `visual.py:160-168`** then merges
  side effects **without** that key, so it is dropped. (Plan-review correction: the earlier draft
  cited `visual.py:310`, which is `gen_planning_node`'s propagation — wrong site.)
  `orchestrator_validators/brief.py:17-35` therefore never finds the brief in live state and always
  falls back to `store.load(..., "execution_brief", 1)` — version pinned to 1 forever.
  `state_schema.py:197` already declares the channel.
- Related same-class instance (architecture review finding): `visual.py:292-294`
  (`gen_planning_node`) writes `new_state["generation_requests"]`, which neither `_collect_updates`
  nor `_propagate_side_effects` carries — the state-key write dies at the boundary
  (`generation.py:127-130` shows the correct explicit-return pattern). This phase does NOT change
  that behavior (generation/money path); it registers the disposition explicitly (see sweep test).

### Target design

1. In `graph/orchestrator_state.py` add a frozen spec type and one ordered table:

   ```python
   @dataclass(frozen=True)
   class OrchChannelSpec:
       key: str                      # literal state key, e.g. "_orchestrator__candidate_refs"
       propagation: str              # "full" | "append_only" | "explicit"
       note: str                     # writer/reader summary; "explicit" rows name their writers

   ORCH_CHANNELS: tuple[OrchChannelSpec, ...] = ( ... )  # 15 rows
   ```

   Rows cover all ten `_orchestrator__*` channels plus the five non-namespaced boundary keys
   (`_routing_decisions`, `_repair_feedback`, `_validation_reports`, `issues`,
   `validation_report_refs`). Policies encode **today's behavior exactly** (behavior-preserving),
   including each key's exact copy predicate:
   - `full`: copied when present — `_routing_decisions`, `_repair_feedback`, `_validation_reports`,
     `_orchestrator__execution_brief` (the one deliberate behavior fix, per DF-F2 below). Note
     copy-on-present is load-bearing for `_repair_feedback`: `_capture_run_outcome` clears it to
     `""` and that empty string must survive propagation.
   - `full_truthy`: copied only when truthy (preserves today's `_copy_published_candidate_refs`
     semantics) — `_orchestrator__candidate_refs`. (Empty-map replace is provably a no-op: the
     working copy is a deepcopy of input.)
   - `append_only`: sliced vs input — `issues`, `validation_report_refs`.
   - `explicit`: writers return them from their own update dicts; auto-propagation must NOT copy
     them — approved_refs (promoted by `approve_phase_node`), active_review_cycles,
     pending_revisions, convergence, routing_decisions-shadow (`_orchestrator__routing_decisions`,
     noted as shadow namespace whose deletion is scheduled in P1 #12/D13), failure_decisions,
     provider_health_snapshot, budget_snapshot.
2. Rewrite `_propagate_side_effects` to be registry-driven: iterate `ORCH_CHANNELS`; `full` → copy
   when present; `append_only` → existing slice logic. The four helper functions collapse into this
   single loop plus the existing slice helper. `_prepend_repair_feedback` / `_capture_run_outcome`
   keep their consume-and-clear semantics (out of scope for the table).
3. DF-F2 consumer fix: `_orchestrator__execution_brief` becomes `full`. After any node call, a brief
   present on the working copy survives into updates and merges into real graph state; the
   `brief.py` store fallback remains as crash-recovery path but is no longer the only route. No
   change to `brief.py` itself in this phase (canonical-version unification belongs to D5/P1#5).

### Tests (`tests/unit/graph/test_channel_registry.py`)

1. Collect-time completeness, closed triangle: AST-scan `orchestrator_state.py` — every f-string
   constant built from `_ORCH_NS` must have exactly one `ORCH_CHANNELS` row and vice versa; **plus**
   reflect over live `GraphState` annotations asserting every `_orchestrator__*` name declared in
   `state_schema.py:188-197` also has a row (constants ↔ schema ↔ registry).
2. Propagation parity (table-driven): for each `full` row, present → copied (**including
   `_repair_feedback` present-but-empty**); for each `full_truthy` row, copied only when truthy;
   for each `explicit` row never copied even when present; `append_only` rows contribute only
   post-input entries.
3. Writer sweep over all declared channels (widened per plan review): AST-scan `graph/nodes/**`
   for working-copy writes to any state-schema-declared key (`issues`, `generation_requests`,
   `_qc_reports`, `_orchestrator__*`, …). Each hit must map to a disposition in a test-local
   allowlist: `propagated` (registry covers it), `explicit-writer` (returned in updates at that
   site), or `known-dropped:<reason>` for deliberate deferrals. Seeded dispositions include
   `visual.py:292 generation_requests → known-dropped:deferred to D13/P1#12`. New unregistered
   writes fail the suite — this closes the D-009 class for namespaced AND non-namespaced keys.
4. DF-F2 regression, aimed correctly: unit-level — brief on working copy survives
   `_propagate_side_effects`; end-to-end — run **`shot_bible_node`** (the causal writer via
   `_ensure_execution_brief`, propagation at `visual.py:160-168`) against a shot-bible-shaped input
   and assert the update dict carries `_orchestrator__execution_brief` alongside
   `execution_brief_ref`.

## Item B — Resume integrity [D6 / O-F4]

### Ground truth

- `app/_graph_exec.py:181-183`: bare `except Exception:` around `graph.invoke(Command(resume=…))`
  → `advance_to_next_phase` — any failure (bug, bad checkpoint, reducer error) silently bypasses
  the human gate.
- `app/_graph_exec.py:125`: `contextlib.suppress(Exception)` around `rt.create_checkpoint` — silent.
- The staleness quartet in `app/_resume.py` (77.91% coverage, zero direct tests):
  `_approval_made_progress` (:17-33), `_has_stale_generation_request_blocker` (:36-52),
  `_preserve_external_generation_requests` (:55-64), `_strip_stale_generation_request_blockers`
  (:67-78), plus payload builder `_build_resume_payload` (:81-107).

### Target design

0. **Empirical pin (probed at HEAD, langgraph MemorySaver + `build_graph()`):**
   - `graph.invoke(Command(resume=…))` on a thread with no checkpoint raises
     `langgraph.errors.InvalidUpdateError` ("Must write to at least one of …").
   - **Cleaner discriminator:** `graph.get_state(config)` on an unknown thread returns a snapshot
     with `values == {}` and `next == ()` — no exception, unambiguous.
   Because `InvalidUpdateError` can equally signal genuine mid-graph state bugs, we do NOT sniff it;
   the implementation uses the pre-invocation discriminator instead.
1. Replace the bare except with: call `graph.get_state(config)` before resuming; if the snapshot is
   empty (`not snap.values and not snap.next`), no checkpoint exists → manual advance (legitimate
   pre-checkpoint projects). Otherwise invoke the resume with **no** catch-all: any failure
   propagates after `_logger.exception(...)` + audit event via `rt._record_audit` with action
   `resume_failed` (actor `"system"`, details include project_id/phase/error class name string).
   Gates can no longer be silently skipped. If `get_state` itself raises, same fail-loudly path.
   **Try-span discipline (plan review):** the guarded region wraps ONLY the `graph.invoke(...)` call;
   `_preserve_external_generation_requests` / `_strip_stale_generation_request_blockers` /
   `_approval_stalled` + manual advance run outside it, so a failure in the stalled branch cannot be
   misclassified as a resume failure.
2. Stalled-resume visibility: when `_approval_stalled` triggers the manual advance, record audit
   event `resume_stalled_manual_advance` with phase + reason flags. Behavior unchanged, visible.
3. `auto_checkpoint`: replace `contextlib.suppress(Exception)` with try/except that logs
   (`_logger.warning`, exc_info) and records audit event `auto_checkpoint_failed`; still does not
   crash the run.

Audit action strings added by this phase (recorded verbatim for the future typed catalog D4/P1#2 to
absorb): `resume_failed`, `resume_stalled_manual_advance`, `auto_checkpoint_failed`. All use actor
`"system"` and string-valued details per `_record_audit(self, actor: str, action: str,
**details: str)` (`runtime.py:284`).

### Tests

- Table-driven unit tests for the quartet + payload builder covering every branch listed in the
  source walk above (~14 cases, parametrized).
- Resume classification tests (monkeypatched `graph.invoke` / `graph.get_state`): empty snapshot →
  advance; generic `RuntimeError` from invoke → raises out, audit event recorded, phase unchanged;
  stalled → advance + audit event.
- `auto_checkpoint` failure path → warning logged, audit event recorded, no raise.

## Item C — Mock fixtures relocation [B-F4]

### Ground truth

- `graph/services.py:72` lazily imports
  `film_pipeline.testing.fixtures.mock_responses.default_mock_responses` inside
  `for_mock_runtime`; mock mode is the production default (`app/runtime.py:446`), so the default
  startup path imports the 392-LOC canned-demo-film fixtures package. Cleanup deletion of
  `testing/` would break production startup (deletion-by-cleanup hazard).
- Other `testing.fixtures` consumers: `tests/e2e/conftest.py:130`,
  `tests/unit/agents/test_mvp_invariants.py:20`. `for_mock_runtime` callers: `app/runtime.py:446`,
  `cli/driver.py:73`, and 12 bare call sites across 7 unit-test files.

### Target design

1. `git mv src/film_pipeline/testing/fixtures/mock_responses.py` →
   `src/film_pipeline/app/mock_responses.py` (history-preserving). Delete the
   `testing/fixtures/__init__.py` re-export once importers are repointed.
2. DI parameter, required keyword with **structural annotation** (no graph→app nominal edge under
   mypy strict): `for_mock_runtime(cls, artifacts_root: str | Path | None = None, *,
   mock_responses: Mapping[str, dict[str, Any]])` — same shape as `PromptRunner.mock_responses`
   (`agents/runner.py:82`). Composition roots (`app/runtime.py`, `cli/driver.py`) and tests pass
   `app.mock_responses.default_mock_responses()`. `graph/` ends up with **zero** references to
   fixture data or the `testing` package.
3. Repoint all importers/callers listed above (mechanical, compiler-verified). Corrected inventory
   (plan review recount): production call sites 2 (`runtime.py:446`, `driver.py:73`);
   `testing.fixtures` importers 2 test files + the services import being removed; bare
   `for_mock_runtime()` calls needing signature updates: 12 sites across 7 unit-test files.

### Tests

- Boundary guard: AST test asserting no module under `src/film_pipeline/graph/` imports
  `film_pipeline.testing` or `film_pipeline.app` (locks the repair in).
- Startup-path test (probe-verified trigger): constructing mock-mode services —
  `StudioRuntime.__init__` → `_build_services_for_mode("mock")` (`runtime.py:59`) — must leave zero
  `film_pipeline.testing*` modules in `sys.modules`. (Pre-fix probe: 6 testing modules load;
  bare module import alone was already clean because the fixture import is lazy.)
- Existing service/e2e behavior tests stay green unchanged except import-path edits.

## Files touched (planned)

| File | Change |
|---|---|
| `src/film_pipeline/graph/orchestrator_state.py` | Add `OrchChannelSpec`, `ORCH_CHANNELS` |
| `src/film_pipeline/graph/nodes/_agent_handoff.py` | Registry-driven `_propagate_side_effects` |
| `src/film_pipeline/app/_graph_exec.py` | Narrowed resume except, checkpoint/resume audit events |
| `src/film_pipeline/app/mock_responses.py` | New home for canned responses (moved file) |
| `src/film_pipeline/testing/fixtures/*` | Re-export removed |
| `src/film_pipeline/graph/services.py` | Required `mock_responses` param; drop testing import |
| `src/film_pipeline/app/runtime.py`, `cli/driver.py` | Pass mock responses explicitly |
| `tests/unit/graph/test_channel_registry.py` | New: parity + DF-F2 tests |
| `tests/unit/app/test_resume_integrity.py` | New: quartet table tests + fallback classification |
| `tests/unit/graph/test_startup_boundaries.py` | New: graph→testing/app import guards |
| ~7 unit-test files | Signature updates (`mock_responses=…`) + import-path updates |

## Non-goals

No QC changes (D3/P1#4); no event catalog (D4/P1#2); no wiring or deletion of dormant channels or
writers (D13/P1#12); no `brief.py` canonical-version work (D5/P1#5); no MCP payload shape changes;
no AGENTS.md/blueprint law edits (Phase 03).

## Risks & mitigations

- ~~LangGraph no-checkpoint exception identity varies~~ **Resolved by probe at plan time**: the
  implementation uses the `get_state()` empty-snapshot discriminator and no longer depends on
  exception identity; the probe transcript is recorded in the Target design section.
- Registry-driven propagation must be byte-for-byte equivalent to today except the declared DF-F2
  fix → characterization via existing suite (`test_candidate_ref_propagation.py` et al.) must pass
  unmodified apart from import paths; any needed edit is a flagged finding, not a silent change.
- `for_mock_runtime` signature break is wide but mechanical → mypy strict enumerates every caller.

## Validation

```bash
export UV_CACHE_DIR="$PWD/.uv-cache" UV_NO_SYNC=1
make ci-check          # full gate: format, lint, strict mypy, pytest ≥90%, build, product gate
```

Targeted: `uv run --no-sync pytest tests/unit/graph/test_channel_registry.py
tests/unit/app/test_resume_integrity.py tests/unit/graph/test_startup_boundaries.py -q`

## Acceptance criteria (phase bar)

1. All three items implemented; behavior preserved except the declared DF-F2 propagation fix.
2. Every new behavior has proving tests (listed above); full suite green; coverage ≥90%.
3. `make ci-check` passes.
4. Two plan reviews (architecture; completeness & correctness) approved before implementation.
5. Three post-implementation reviews from distinct lenses return PASS with scores ≥4/5.

---

## Review record

### Plan review round 1 — architecture lens (independent reviewer): APPROVE

Scores: design-coherence 5 · boundary-compliance 4 · minimality 4 · risk-coverage 4 ·
citation-accuracy 4. Findings 1–8 folded into the plan above: (1) DF-F2 drop site corrected to
`shot_bible_node` / `visual.py:160-168`; (2) writer sweep widened to all state-schema-declared
channels with disposition allowlist, seeding the live `visual.py:292 generation_requests`
known-dropped instance for D13/P1#12; (3) per-key copy predicates preserved (`full` vs
`full_truthy`), `_repair_feedback` empty-string propagation pinned; (4) structural `Mapping`
annotation for `mock_responses`; (5) guarded region restricted to the invoke call; (6) parity test
closed over constants ↔ schema ↔ registry; (7) caller inventory corrected (12 sites / 7 files);
(8) audit action strings recorded verbatim.

### Sequencing decision (round 10)

Two cold-start completeness-lens reviewers and one context-inheriting fork each exceeded reasonable
runtime without delivering (environment latency, not task size). Decision: implementation proceeds
now under the architecture lens' APPROVE (which spot-checked 19 citations and re-derived the
registry arithmetic against source) plus the author's documented independent verification (caller
inventories, probes, drift census — all in-repo evidence). **The commit gate is unchanged:** the
completeness verdict must land and pass, alongside the three post-implementation reviews and a
green `make ci-check`, before this phase is committed. If it reports blockers after implementation,
they are fixed before any commit.

### Plan review round 1 — completeness & correctness lens (independent reviewer): APPROVE

Coverage: P0#1 covered · P0#2 covered-faithful (`get_state()` discriminator judged intent-faithful
and superior to exception-narrowing) · P0#3 covered; missed consumers: none. Findings folded as
test-section amendments BEFORE implementation: (1) replay-idempotency case for the propagated brief
(run `shot_bible_node`, merge updates, run again on merged state → identical brief payload, no
second extraction invocation); (2) combined-keys parity cases (brief + non-empty refs both land;
empty brief + refs → brief key absent); (3) audit-event assertions pinned to exact action strings,
actor `"system"`, project_id detail, error class on `resume_failed`; (4) writer-sweep allowlist
keyed by `(file, key)` with per-entry uniqueness — never line numbers.

**Sequencing note resolved:** the completeness verdict arrived before implementation began, so the
round-10 contingency was not exercised; both mandated plan approvals are on record prior to code.

## Implementation record

### Amendments applied at implementation start

- Test A.2 gains two combined-keys cases (finding 2).
- Test A.4 gains the replay-idempotency case (finding 1).
- Sweep allowlist keyed `(file, key)` with uniqueness assertion (finding 4).
- Resume/checkpoint tests assert exact audit action strings, actor, and detail keys (finding 3).

### Implementation notes — Item A discoveries (in scope via "DF-F2 first consumer")

1. **DF-F2 root cause was one layer deeper than the review recorded.** `route_agent`'s create path
   (`_agent_routing.py:178-181`) returned the phase default for every create task and ignored the
   caller-supplied `agent_id`, contradicting `_run_agent`'s own docstring. `shot_bible_node`'s
   extraction call therefore ran the shot-design agent; no ExecutionBrief was ever produced, which
   is why the state channel stayed empty AND the version-1 store fallback never had an artifact to
   find either. Fix: `route_agent(..., preferred_agent_id=…)` honored on create paths when
   registered (review/repair keep dynamic routing); `_resolve_routing` passes the call-site id for
   `task_type == "create"` only. Blast radius verified: of 11 create-path call sites, all matched
   their phase default except this one. Tests: `tests/unit/graph/test_create_path_routing.py`.
2. **Brief loader type lie became load-bearing.** `_load_brief_from_state` annotated
   `ExecutionBrief | None` but returned the raw stored dict (`set_execution_brief` persists
   `model_dump()`); unreachable until briefs actually appear in state, then an AttributeError bomb.
   Fixed by coercing dict → `ExecutionBrief(**data)` mirroring the store branch.

### Implementation record — Items A/B/C landed (pre-review)

- **Item A:** `OrchChannelSpec`/`ORCH_CHANNELS` (15 rows) in orchestrator_state; registry-driven
  `_propagate_side_effects` with per-key policies (`full` / `full_truthy` / `append_only` /
  `explicit`); three hand-carried key lists deleted; DF-F2 propagation live. Plus the two recorded
  discoveries (route_agent explicit-id fix; brief loader coercion).
  Tests: test_channel_registry.py (triangle, parity table, combined-keys, replay idempotency,
  writer sweep with 18 dispositioned pairs incl. 2 known-dropped), test_create_path_routing.py.
- **Item B:** get_state empty-snapshot discriminator gates the manual advance; guarded region wraps
  only the invoke; failures log + audit `resume_failed` + re-raise; stalled advance audits
  `resume_stalled_manual_advance`; auto_checkpoint failure logs + audits `auto_checkpoint_failed`.
  Tests: test_resume_integrity.py (classification ×4, checkpoint visibility, quartet branches ×20).
- **Item C:** mock_responses moved to app/ (git mv); `for_mock_runtime(..., *, mock_responses)`
  required kwarg with structural Mapping annotation; composition roots inject
  default_mock_responses(); testing/fixtures package removed; all callers repointed (2 prod,
  14 test files). Tests: test_startup_boundaries.py (graph-import AST guard, fresh-interpreter
  startup cleanliness, composition-root wiring).

### Implementation note — Item C consequence: demo film made self-consistent

Making extraction actually run surfaced that the canned demo film was internally inconsistent
(three-way): brief promised 14 shots / 240s across act_1..act_3; the canned matrix had 2 rows
(20s) under `act1`; pacing self-consistency wants runtime ≈ shots × 6.5s. With DF-F2 fixed the
structural validators fired for real and the mock happy path failed its own gates. Reconciled on a
single authority (`_DEMO_MOVEMENT_DURATIONS` in app/mock_responses.py): 16 rows / 104s /
5+5+6 shots — exactly 16 × 6.5s standard pacing; provider plan regenerated per row at the
Seedance $0.18/s rate ($18.72). The four affected pipeline tests (integration QC, 4-min smoke,
2 TUI e2e flows) pass against the consistent film.

## Post-implementation review verdicts (bar: all PASS, every score ≥ 4)

| Reviewer | Lens | Verdict | Scores |
|---|---|---|---|
| #1 | Correctness & test evidence | **PASS** | correctness 5 · evidence 4 · edge-cases 4 · fidelity 5 |
| #2 | Architecture, boundaries & clean code | **PASS** | boundaries 5 · minimality 4 · patterns 5 · docstrings 5 |
| #3 | Behavior preservation & regression risk | **PASS** | deltas 5 · consumers 5 · downstream 5 · payloads 5 |

Folded before commit:
- R1#1: `get_state` discriminator wrapped in the same log-audit-reraise pattern as the invoke
  guard (`resume_failed` audit now covers probe failures too).
- R1#3: three missing quartet guard branches pinned by direct tests (empty active requests,
  non-list resumed issues, non-list issues at strip time).
- R1#2: writer-sweep AST scan extended to `state.update({...})` dict-literal merges, closing the
  one identified evasion path.

Deferred with owner:
- R1#4: pre-existing persist-guard log without audit event — align with D4's audit vocabulary work.
- R2#2 (`_EXTRA_SWEEP_KEYS` could derive from state annotations) and R3#1/R3#2 informational notes
  (insertion-order delta proven non-semantic; shallow-copy of injected mappings benign): recorded
  for future maintainers, no action this phase.
