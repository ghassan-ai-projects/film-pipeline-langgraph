# Architecture Review — Maintainability, Observability, Flexibility

**Branch:** `arch-improvement-review` · **Pinned at HEAD:** `e811d1d` (post PR-#20 merge)
**Method:** five independent lens analyses (boundaries/layering, state & data flow, observability,
flexibility/extensibility, cognition/reasoning-load), each evidence-verified against source with
`file:line` citations, synthesized here. Full lens reports are archived in
[`documentation/reviews/arch-lens-*.md`](reviews/) — every finding below carries its lens ID and is
traceable to the detailed write-up. An AST import-edge scan (Tarjan SCC) supplied the dependency facts.

---

## The bar this document was held to

1. **Grounded** — every finding cites `file:line` verified at `e811d1d`; an independent verifier must be able to spot-check ≥90% of citations with zero stale references.
2. **Specific** — zero generic advice; every proposal names concrete files/symbols, a target design, migration steps, effort (S/M/L), and risk.
3. **Complete on axes** — maintainability, observability, flexibility, plus reasoning-load each get explicit coverage and a verdict table.
4. **Decision-ready roadmap** — prioritized P0/P1/P2 with sequencing that respects sub-package law; explicit guardrails ("do NOT do") included.
5. **Honest uncertainty** — anything not fully verified is marked UNCERTAIN in the lens reports rather than asserted.
6. **Independent critic pass** — a fresh reviewer scores all criteria 1–5 and spot-checks random citations; revisions continue until every dimension scores ≥4.

Critic verdict for this revision: recorded at the bottom ([Verification](#verification)).

---

## Executive summary

The codebase is **locally excellent and globally fragile**. Modules are small, docstrings honest,
naming inside files consistent, gates and tests earnest. The costs live in the connections:

> **Theme 1 — "Two of everything."** Nearly every important mechanism exists twice: two QC
> implementations (parallel subgraph vs sequential node) with material drift [DF-F4]; two generation
> lifecycles (MCP tools vs `GenerationExecutor`) that **have already drifted on a money-spending path**
> [B-F5]; two audit systems (a typed package that nothing executes + a live untyped dict log) [O-F1/F2];
> two rollback-record stores with divergent id formats [C-1.2]; three operator surfaces computing
> "what should I do next" independently [B-F6].

> **Theme 2 — Hand-maintained parallel tables with no invariant tests.** Five phase tables for one
> graph phase addition [Flx-matrix]; four agent identity tables already drifted (≥9 orphan ids) [Flx-F2];
> three provider tables in one if-chain file [Flx-F1]; validator dispatch duplicated while the real
> `ValidatorRegistry` is never populated [B-F5d, Flx-F5]; the orchestrator channel allowlist whose
> omission caused the D-009 production bug — still generically open [DF-F1].

> **Theme 3 — Dead or dormant machinery wearing load-bearing clothes.** The entire `observability`
> package has zero production callers [O-F1]; `ArtifactStore.approve()/supersede()` never run — every
> artifact stays CANDIDATE forever while approval semantics live elsewhere [DF-F3]; router safety rules
> read channels no production code writes [DF-F6]; `get_blockers` always returns empty while the
> operator guide tells users to consult it [O-F6]; budget escalation routes on a spend value that is
> structurally frozen at 0.0 [O-F9].

> **Theme 4 — Silence as the default failure mode.** A bare `except Exception` converts failed graph
> resumes into gate-bypassing manual advance [DF-F5, O-F4]; provider failures flatten to truncated
> strings at every surface with the exception class discarded [O-F5]; `_propagate_side_effects`
> silently drops unregistered channels (D-009 precedent, one live instance today [DF-F2]); profile
> knobs and env overrides no-op without warning [Flx-F6].

> **Theme 5 — The law and docs describe a smaller system.** AGENTS.md governs 12 sub-packages; the
> tree has 19; the blueprint never mentions `app/`, `tui/`, or `OperatorService` (~40% of hotspot LOC)
> [B-F8, C-6.3]. The boundary law covers data-via-artifacts but has no behavior-reuse rule — which is
> precisely why post→validation breaches and dispatch-table forks keep appearing [B-F8].

**Verdict per requested axis**

| Axis | Verdict | Highest-leverage fix |
|---|---|---|
| Maintainability | Good bones; coupling tax concentrated in parallel tables & duplicate mechanisms | Channel registry + parity test [DF-F1]; single-source phase table [Flx-F11#3] |
| Observability | Weakest axis: forensics not answerable from disk today | Typed event catalog + run_id/node lifecycle events [O-F1/F2/F3/F7] |
| Flexibility | Registries exist but are bypassed or drifted; extension cost 6–8 touches for providers/phases | Provider catalog [Flx-F1]; config-contract test [Flx-F9] |
| Reasoning load | Fast for contained changes, unsafe by default for cross-cutting ones | Ref-format chokepoint [C-3.2]; docs truth [C-6] |

---

## Ground truth

- **307 Python modules, ~41.5k LOC**, 19 sub-packages (AGENTS.md documents 12).
- **Import edges between domains** (module-level AST scan): `mcp` imports 13 packages, `app` imports
  11 (composition root — expected); domain-to-domain edges that strain the law:
  `post→validation`, `config→providers`, `agents→providers`, `generation→{artifacts,providers}`.
  Exactly **one package-level cycle**: `{app ↔ mcp}`, held together by lazy imports and the documented
  `get_runtime` binding hack. 198 lazy cross-package imports total (mcp 109, graph 42, app 24).
- **Hotspots** (LOC): `app/services/operator.py` 473 · `tui/screens/studio.py` 471 ·
  `agents/runner.py` 471 · `graph/nodes/_context.py` 470 · `mcp/tools/_profile_change.py` 467 ·
  `app/runtime.py` 464 · `graph/nodes/qc.py` 455 · `graph/orchestrator_state.py` 435.
- **Tests:** unit suite measured green at the phase-2 referee gate immediately pre-merge
  (1,802 passed / 1 skipped, serial, from scratch; UNCERTAIN whether the exact count differs at
  `e811d1d` — no full-suite re-run was performed for this review), but coverage of *behavior* is
  uneven — the brief.py
  StoryBible cross-checks have never been exercised by unit tests, the resume staleness quartet has
  zero direct tests, and qc.py's translation helpers are imported by no test [C-4.2, DF-F5].
- Prior context absorbed into this review: `.fleet/reports/COVERAGE-CLASSIFICATION.md` (0 dead-code
  findings at symbol level — note Theme 3 concerns dead *mechanisms*, which are registry-wired or
  exported and therefore "alive" by that analysis's rules), D-001..D-010 fleet reports, incident history.

---

## A. Structure & boundaries (maintainability)

Full detail: [`arch-lens-boundaries.md`](reviews/arch-lens-boundaries.md).

| ID | Finding | Severity | Effort |
|---|---|---|---|
| B-F1 | `post → validation` breach: `delivery_packaging_agent.py:190` lazily imports `DeliveryCompletenessValidator` and fabricates its input dict; completeness rules duplicated in two packages | Medium | S |
| B-F2 | `config → providers`: runtime wiring (`register_project_providers`, `missing_provider_credentials`) parked in `config/profile_resolver.py:179,204`, importing the **private** `_env_var_for` | Medium | S |
| B-F3 | `agents/model_adapter.py:31` imports `OPENROUTER_API` from concrete adapter `seedance_openrouter.py` — generic chat transport coupled to one media adapter's constant | Low-Med | S |
| B-F4 | **Production default startup imports the test-fixtures package**: `graph/services.py:72` (`for_mock_runtime`) pulls `testing/fixtures/mock_responses.py` (392 LOC of canned demo film) — mock mode is the default server mode | **High** | S |
| B-F5 | MCP thickness: generation lifecycle implemented twice **and already drifted** (MCP sends unresolved `prompt_ref` + hardcoded `duration=5.0`; executor resolves prompts + row durations; MCP polling can strand rows RUNNING); text-only policy near-verbatim ×2; validator dispatch tables ×2 while `ValidatorRegistry` is never populated | **High** | M+S |
| B-F6 | Composition root mostly clean; leakage = private reach-ins (`_persist_project_state`, `store._root`) and triplicated operator recommendation logic | Low-Med | S/M |
| B-F7 | One package cycle `{app↔mcp}` held by lazy imports + monkeypatch-binding hack; 198 lazy imports hide true fan-out | Medium | M |
| B-F8 | Boundary law misdescribes reality (12 vs 19 packages) and lacks a behavior-reuse rule — root cause of B-F1/B-F5 recurring | Medium (law debt) | S |

**Axis verdict:** layering intent is sound and mostly followed; the failures cluster where the law is
silent (behavior reuse) and where mock-mode fixtures were parked under a misleading package name.

## B. State & data-flow integrity

Full detail: [`arch-lens-dataflow.md`](reviews/arch-lens-dataflow.md).

| ID | Finding | Severity | Effort |
|---|---|---|---|
| DF-F1 | `_propagate_side_effects` copies a fixed key list covering **1 of 10** orchestrator channels; 3 more survive via hand-carrying; 5 have no production writer; no test fails when a new channel is added unpropagated (the D-009 bug class, generically open) | **High** | S |
| DF-F2 | Live instance: `_orchestrator__execution_brief` written into node-private deepcopy and dropped; masked only by a store fallback hardcoded to version 1 (`brief.py:35`) | Med-High | S |
| DF-F3 | Three disconnected notions of "approved": store `approve()/supersede()` never called (sidecars stay CANDIDATE forever), scalar refs track latest candidates regardless of gate outcome, promotion is promote-all | **High** | M |
| DF-F4 | Two live QC implementations with drift inventory (artifact resolution pinned-vs-latest, delivery validator missing from fan-out, matrix-patch/consensus side effects only on sequential path) | **High** | M |
| DF-F5 | Resume validity rests on an untested heuristic guarded by bare `except Exception → advance_to_next_phase`, silently bypassing human gates; external-state replay covers exactly one key; write-only crash artifacts accumulate unread | **High** | S-M |
| DF-F6 | Router rules 2–4 read channels production never writes — decision logic that cannot fire (dead safety logic masquerading as resilience) | Medium | M/S |
| DF-F7 | Deepcopy-everything convention: 22 sites; dual role as diff-base and mutation-masker; staged immutability path mapped (S/M/L) | Medium | staged |
| DF-F8 | Full artifact trace (`film_constitution`) with five silent-divergence points — four sources claim to answer "which version is canonical" | (analysis) | — |
| DF-F9 | Choke-point design review: right place (node boundary), wrong mechanism (allowlist). Sequence: registry → generic diff → immutable boundary | (design) | — |

**Axis verdict:** the pipeline's correctness guarantees (gates, approvals, QC reproducibility) rest on
conventions enforced nowhere. Every P0 guardrail below targets making one of these conventions
machine-checked.

## C. Observability & forensics

Full detail: [`arch-lens-observability.md`](reviews/arch-lens-observability.md).

| ID | Finding | Severity | Effort |
|---|---|---|---|
| O-F1 | The `observability` package is dead code (AuditTrail/MetricsCollector/BlockerReporter: zero src consumers); live audit is a parallel untyped dict mechanism in `StudioRuntime._record_audit` | **High** | M |
| O-F2 | No event vocabulary on the live path: 11 free-string actions across 6 files, drifting already (`create_project` vs `create_film_project`); D-007 fixed a typo in the enum nobody executes | **High** | S-M |
| O-F3 | Graph execution invisible to audit: 0/18 nodes emit events; handoff records carry no id/timestamp; auto-approve indistinguishable from human approval | **High** | M |
| O-F4 | Exceptions swallowed: resume fallback (`_graph_exec.py:181-183`) and auto-checkpoint (`:125`) fail silently, no log, no audit event | **High** | S |
| O-F5 | One failure renders three different ways (ledger truncation / MCP internal_error / TUI footer); `FailureClassifier` exists with zero callers; LLM retry ladder discards the cause entirely (`all_retries_exhausted`) | **High** | M |
| O-F6 | `get_blockers` always returns `{blockers: []}` — its writer `add_blocker` has zero callers; operator guide directs users to it | **High** | S |
| O-F7 | Run forensics NOT answerable from persisted artifacts: no run/correlation id (`thread_id==project_id`), no node durations, checkpoints filed under wrong phase (`intake` hardcoded), `explain_last_decision` ignores project scope, O(n²) audit rewrites | **High** | M |
| O-F8 | Provider health states exist but are only ever "healthy" — nothing feeds BLOCKED/DEGRADED from real errors | Med-High | S |
| O-F9 | Cost estimated everywhere, recorded nowhere: `actual_cost_usd`/`spent_usd` never written; budget-escalation gate structurally cannot fire; planner prompt advertises imagen $0.02 where ultra bills $0.10 [see also Flx-F10] | **High** | M |
| O-F10 | Logging: consistent `getLogger(__name__)` but zero handlers/config anywhere — warnings evaporate unless host captures stderr | Medium | S |
| O-F11 | Audit persistence quirks: full-file rewrite per event (no atomic rename), restart-visible event loss for unscoped events | Low-Med | S |

**Axis verdict:** weakest of the three requested axes. The building blocks exist (pricing table,
failure classifier, metrics API, typed enums) but are unwired; the live system answers almost no
forensic question from disk alone.

## D. Flexibility & extensibility

Full detail: [`arch-lens-flexibility.md`](reviews/arch-lens-flexibility.md). Extension-cost matrix
(verified steps per extension type) lives there; highlights:

| Extension | Cost today | Failure mode when a step is missed |
|---|---|---|
| New provider adapter | 6 src edits across 4 files (factory.py holds 3 tables) + yaml | Silent fallbacks: unknown model → `[]`, unknown rate → `$0.00` |
| New graph phase/node | **8+ edits across 7 files, five parallel phase tables** | Missing `_NEXT_PHASE_AFTER_APPROVAL` row silently routes to `"end"` |
| New agent | 6–7 places over four identity tables (already drifted: ≥9 orphan profile-map ids) | Routing yields `agent_not_found` at runtime only |
| New validator | 3 places; advertised registry bypassed | QC and MCP surfaces disagree |
| New MCP tool | Cheap mechanically, toll at 387-LOC ordering-sensitive registry; all 52 tools ship empty JSON schemas; boilerplate descriptions | Clients can't validate args |
| New profile knob | 1 YAML line — and zero enforcement anyone reads it | Dead-knob corpus grows silently |

Key findings: provider catalog proposal [Flx-F1]; agent-table consolidation + reverse invariant tests
[Flx-F2]; registry *policy* unification (raise-on-duplicate everywhere; `PromptTemplateRegistry`
silently overwrites today) [Flx-F3]; thresholds in three disagreeing sets with profile knobs nobody
reads [Flx-F5/F6]; mis-wired `FILM_PIPELINE_MODEL_OVERRIDE` (writes a path nothing reads — worse than
dead) [Flx-F6]; dormant-capability convention (`# DORMANT(...)` tag + zero-caller CI test)
[Flx-F8]; next enum targets ranked (severity strings #1) [Flx-F11]; imagen tier-rate relapse
[Flx-F10].

**Axis verdict:** configurability is the stated product interface but has no contract enforcement;
extension cost is highest exactly where growth is most likely (phases, providers).

## E. Reasoning load (how fast can engineers move safely)

Full detail: [`arch-lens-cognition.md`](reviews/arch-lens-cognition.md).

| ID | Finding | Severity | Effort |
|---|---|---|---|
| C-1.1 | "Shot density" walkthrough: fast to find (`scope_contract.py`) but hidden validator coupling (brief.py recomputes tolerance from the same table) and a `_flag_density_warnings` name collision mislead blast-radius reasoning | Medium | S |
| C-1.2 | "Add MCP rollback tool" walkthrough: dual rollback-record stores with divergent id formats; undeclared 4–6-touchpoint checklist; boilerplate tool descriptions (`registry.py:112`) | **High** | S/M |
| C-2.1 | `operator.py`: ≥6 reasons-to-change in one class + direct `runtime.projects[...]` mutation leak (named split proposed) | Medium | M |
| C-2.2 | `runner.py`: prompts + retry ladder + mock plumbing in one class; errors-as-status-dicts contract | Med-High | M |
| C-2.3 | `_context.py`: four unrelated jobs incl. an agent-profile config map (named split proposed) | Medium | S-M |
| C-3.1 | `server_mode`/`runtime_mode`/`workflow_mode` — one concept, three names, fallback-or chains | **High** | M |
| C-3.2 | Artifact-ref format: 6 builders, ≥8 `split(":")` parsers, `ArtifactRef` schema unused at these sites | **High** | M |
| C-3.3 | gate/blocker/blocking-issue/blocked-action synonym drift; duplicated `_is_blocking_issue` helpers | Med-Low | S |
| C-4.1 | 68 monkeypatch sites across 11 files pin the `get_runtime` binding detail, holding import layout hostage via comments alone | **High** | L |
| C-4.2 | Tests-as-spec unevenness: strong exemplars exist; monolith test files (2138-line TUI, 1301-line test_mcp) and implementation-pinning patterns (setattr → builtin `list`) | Medium | M |
| C-6 | Docs-code trust: blueprint omits app/tui (~40% of hotspot LOC); AGENTS.md table stale (12 vs 19); operator-guide catalog lags registry with no sync mechanism | **High** | S |

**Axis verdict:** locally readable, globally unsafe-to-change: the couplings that bite are invisible at
the edit site. The highest-leverage items are the ref-format chokepoint [C-3.2], the docs-truth pass
[C-6] (both P0/P1), and the seam unlock [C-4.1] (P2, behind characterization tests).

Narrative highlights:
- **Contained change ≈ 1 hour; unsafe change also ≈ 1 hour** — the couplings that bite (ref-string
  format, density numbers feeding distant validators, `get_runtime` binding layout) are invisible at
  the edit site [C-overall].
- Concept wears multiple names across layers: `server_mode`/`runtime_mode`/`workflow_mode` declared
  side-by-side with fallback-or chains [C-3.1]; `artifact:{id}:v{n}` built in 6 places, parsed by
  `split(":")` in ≥8, despite an existing `ArtifactRef` schema [C-3.2]; gate/blocker/blocking-issue/
  blocked-action near-synonyms [C-3.3].
- Hotspot anatomy with named splits: `OperatorService` (≥6 reasons-to-change; direct
  `runtime.projects[...]` mutation leak), `PromptRunner` (prompts + retry ladder + mock plumbing;
  errors-as-dicts contract), `_context.py` (four unrelated jobs incl. an agent-profile config map)
  [C-2.1/2/3].
- Test seam: **68 monkeypatch sites pin the `get_runtime` lazy-binding implementation detail**,
  holding production import layout hostage via comments alone [C-4.1]. Good exemplars exist
  (`test_checkpoints.py`: zero patches, public-API-driven) [C-4.2].
- Docs trust: blueprint omits app/tui layers; AGENTS.md table stale; operator-guide tool catalog lags
  the registry with no sync mechanism [C-6].
- Debt register DBT-1..DBT-9 consolidated there, with payoff estimates and a recommended order
  starting with characterization tests before any structural refactor.

---

## Consolidated debt register (top items, merged across lenses)

| ID | Debt | Lens | Payoff | Effort |
|---|---|---|---|---|
| D1 | Orchestrator channel allowlist (no invariant) | DF-F1 | Closes D-009 bug class | S |
| D2 | Generation lifecycle ×2, drifted on money path | B-F5 | One owner for submit/poll/cancel + honest payloads | M |
| D3 | Two QC implementations | DF-F4 | Reproducible verdicts across normal/repair paths | M |
| D4 | Typed event catalog replacing 2.5 audit systems | O-F1/F2 | D-007-class bugs unrepresentable; base for all forensics | M |
| D5 | Approval semantics split (dead store lifecycle, promote-all, candidate-tracking refs) | DF-F3 | Human-gate contract becomes enforceable | M |
| D6 | Resume bypass + untested staleness quartet | DF-F5/O-F4 | Gates cannot be silently skipped | S-M |
| D7 | Parallel hand-maintained tables (phase ×5, agent ×4, provider ×3, validators ×2) | Flx | Extension cost drops 6–8 touches → 1–2; drift caught by CI | M each |
| D8 | Artifact-ref string scatter (14 sites) | C-3.2 | Format evolution becomes a two-function change | M |
| D9 | get_runtime seam pinned by 68 test patches | C-4.1 | Unblocks tool-layer refactors forever | L |
| D10 | Dead/dormant machinery (observability pkg, ValidatorRegistry, route_agent arms, `run_agent_for_phase`, dead knobs) | multiple | Attention + false-confidence reclaimed; some deletions are free wins | S each |
| D11 | Docs/law describe 12 packages & no app/tui | B-F8/C-6 | Agents and newcomers stop over-breaching or inventing seams | S |
| D12 | Boundary breaches with duplicated rules (post→validation completeness ×2; config→providers wiring) | B-F1/F2/F3 | Single source for gate rules; phase scoping restored | S |
| D13 | Unwired safety channels (failure_decisions / provider_health_snapshot / budget_snapshot never written; router rules that cannot fire) + dual rollback-record stores with divergent ids | DF-F6, C-1.2/DBT-3 | Blueprint-promised resilience becomes real (or honestly removed); rollback listing unambiguous | M/S |

---

## Roadmap

Sequencing principles: **guardrails before refactors** (invariant tests make later moves safe);
**characterize before touching** spec-bearing helpers (DBT-9 first); **docs-as-law early** because
coding agents read AGENTS.md first; **behavior-preserving envelopes** around any change to
money/QC/gate paths.

### P0 — Guardrails & quick wins (each ≤ S-M, low risk; do in this order)

1. **Orchestrator channel registry + schema-parity test** [D1]. Frozen `ORCH_CHANNELS` table;
   parity test fails at collect time when a channel lacks a registry entry; absorb the three
   hand-carried keys. Fixes DF-F2 as its first consumer.
2. **Resume integrity** [D6]: narrow `_graph_exec.py:181-183` bare except to "no checkpoint"
   conditions; log + audit-event anything else; table-driven tests for the staleness quartet.
3. **Move mock fixtures out of `testing/` and out of `graph`** [B-F4]: `app/mock_responses.py` +
   DI parameter on `for_mock_runtime`. Removes deletion-by-cleanup hazard on the default startup path.
4. **Imagen pricing delegation** [Flx-F10]: tier map into `pricing.rate_for(provider_id, model=...)`;
   parametrized estimate-vs-pricing test. Restores cost-integrity of planner prompts.
5. **Config-contract test** [Flx-F9]: every profile leaf and env-override path must have a reader or
   a `KNOWN_DEAD` allowlist row seeded from `hardcoded-values-inventory.md`. Fails today on
   `re_anchor_every_n_clips`, `validation.thresholds`, and mis-wired `FILM_PIPELINE_MODEL_OVERRIDE`.
6. **Truthful `get_blockers`** [O-F6]: derive from `compute_actions` + issues; keep response shape.
7. **Logging bootstrap** [O-F10]: `dictConfig` at MCP/TUI entrypoints; level via env; rotating file
   under runtime root; stderr stays WARNING-safe for stdio.
8. **Amend the boundary law + CI edge scan** [B-F8]: AGENTS.md table → 19 packages, explicit
   schemas exception, behavior-reuse rule ("domain→domain behavior via owned registry/service invoked
   by graph/mcp/app"); add `scripts/check_boundaries.py` in warn mode.
9. **Docs truth pass** [C-6]: blueprint "Application Layer" section; regenerate operator-guide tool
   catalog from `register_all_tools`; "adding an MCP tool" checklist in AGENTS.md.

### P1 — Structural consolidations (M each; sequence within themes)

1. **Generation lifecycle behind `GenerationExecutor`** [D2]: MCP start/resume/cancel delegate;
   write-the-divergence-test-first (identical payloads via both surfaces); text-only policy to
   `generation/text_only.py`; shared `PHASE_VALIDATORS` dispatch table.
2. **Typed event catalog + single audit implementation** [D4]: Pydantic `AuditEvent` +
   `AuditActionKind` StrEnum owned by `observability/`; `_record_audit` constructs it; delete/absorb
   dead classes once parity proven through runtime tests (not package-isolated tests).
3. **Run correlation + node lifecycle** [O-F3/F7]: `run_id` minted at the three graph-entry points;
   `node_start/node_end` events with duration/ok/error_kind emitted executor-side; true checkpoint
   phase tags; atomic append-friendly persistence.
4. **Unify QC core** [D3]: pure `run_validator_set(services, resolver, validators)` with injected
   artifact resolution; Send-worker bodies and sequential loop become thin adapters; golden-test both.
5. **Approval semantics unification** [D5]: wire `store.approve/supersede` into `approve_phase_node`
   scoped to reviewed families; consumers resolve via `resolve_artifact(family)`; narrow promote-all.
6. **Provider catalog** [Flx-F1]: one declarative table (aliases/env/models/capabilities/pricing)
   consumed by factory/credentials/pricing; alias-agreement test.
7. **Phase single-source-of-truth** [Flx matrix worst row]: ordered `PhaseKey` StrEnum deriving the
   five tables; reverse-direction agent-table invariant tests; delete ghost rows [Flx-F2].
8. **Error taxonomy end-to-end** [O-F5/O-F8]: typed `PipelineError` hierarchy; boundary logging with
   traceback + audit error events; wire `FailureClassifier` → provider health; preserve
   `MCPErrorCode` through TUI gateway; `record_cost(project_id, run_id, usd)` seam [O-F9].
9. **Artifact-ref chokepoint** [D8]: `ArtifactRef.parse/render` sweep of 14 sites.
10. **Registry policy alignment** [Flx-F3]: raise-on-duplicate everywhere (`replace=True` opt-in);
    capability tokens validated at register time [Flx-F11#4].
11. **Boundary repairs** [D12]: invert post→validation (validator owns `check_delivery_package`;
    delete the fabricated-input + duplicated completeness rules in `delivery_packaging_agent.py`);
    move `register_project_providers`/`missing_provider_credentials` to `providers/bootstrap.py`
    (public `env_var_for`), shrinking to a loop once the provider catalog lands; repoint
    `OPENROUTER_API` through `providers/credentials.py`. All S-sized; the CI edge scan from P0 #8
    keeps the class from returning.
12. **Wire or delete the unwired safety channels** [D13/DF-F6]: with the channel registry in place,
    record `failure_decisions` + `provider_health_snapshot` where failures/health actually change
    (executor + classifier wiring from item 8); budget snapshot where spend is recorded [O-F9];
    delete `active_review_cycles` and the shadowed `_orchestrator__routing_decisions` namespace.
13. **Single rollback-record producer** [D13/C-1.2]: `RollbackManager` persists via artifact store
    only; delete the tool-side duplicate writer (`mcp/tools/checkpoints.py:67-77`) after an id-format
    compatibility check against audit-feed/e2e consumers.

### P2 — Larger bets (L; only after their P0/P1 prerequisites)

1. **ToolContext DI** [D9/C-4.1]: retire the `get_runtime` binding hack; migrate tests module-by-module
   behind characterization tests.
2. **Generic `diff_updates(original, working)`** then staged immutability [DF-F7/F9] — replaces the
   allowlist class entirely; full frozen-state only if profiling shows deepcopy matters.
3. **Hotspot splits** [C-2/B-F6]: `ProjectLifecycleService`/`WorkspaceViews`/`OperatorMutations`
   (this also retires the triplicated operator recommendation logic — `compute_actions` becomes the
   single "what next" source); `rctco.py`/`call_ladder.py`/mock-registry extraction;
   `_context.py` → `agent_profiles.py` / `prompt_context.py` / `upstream_injection.py`.
4. **Mode-name unification** [C-3.1]: `environment_mode` + `approval_policy` accessors with tolerant
   persisted-key reads.
5. **Empty-schema ratchet for MCP tools** [Flx-F4]: extend `_register(input_schema=...)`; pin count,
   grow over time; per-tool description strings replace boilerplate.
6. **Enum follow-through** per [Flx-F11] ranking (severity strings first, then artifact_type at
   boundaries), using the established parse-coercion-boundary pattern from commit `52f5c2b`.

### Guardrails — what NOT to do

- **No big-bang immutable-state rewrite.** Deepcopy is load-bearing for diffing and merge semantics;
  stage it (S→M→L) or leave it. Removing deepcopy without fixing the by-reference propagation of the
  candidate-ref map (`_agent_handoff.py:37`) would introduce shared-mutation bugs.
- **No mechanical registry unification.** Align policies (dup handling, missing lookup), not idioms —
  AGENTS.md forbids abstraction without proven need.
- **Don't wire or delete the route_agent dormant arms unilaterally** [DBT-2 / Flx-F8] — that's a
  product decision; until then, apply the `# DORMANT(...)` marker + zero-caller test so the state is
  machine-checkable.
- **Keep JSON payload shapes stable** during enum waves (StrEnum serializes identically — proven by
  the D-005 receipts); persist legacy-string tolerance at boundaries like the landed severity ripple did.
- **Don't chase deepcopy performance** without a profile; the structural argument is enough to justify
  the read-only-view stage, nothing more.
- **Preserve the MCP-first contract**: tools become thin delegates over services/executor — they must
  not grow second implementations again, nor should services start bypassing the tool registry.

---

## Verification

**Method.** All five lens reports verified their own citations against source at `e811d1d` and flagged
UNCERTAIN items inline (preserved in the archived reports above).

**Independent critic pass (round 1).** A fresh reviewer performed 28 citation spot-checks across the
lens reports and this synthesis; full report:
[`documentation/reviews/arch-review-critic.md`](reviews/arch-review-critic.md). Round-1 scores:
Grounded 3 · Specific 4 · Complete-on-axes 4 · Decision-ready roadmap 4 · Honest uncertainty 4 ·
Independent pass 3 — verdict **REVISE**, with 4 factual defects and 3 dropped-findings gaps.

**Revisions applied (rounds 2–3).** Factual: monkeypatch file count corrected 32→11 files (F-4.1 and
the DBT-7 register row); package count corrected 21→19 (cognition lens, both places); dataflow F-1
heading corrected to "9 of 10" with reconciliation note; lazy-import recount 194→198 everywhere
(ground truth + B-F7); budget-gate and threshold citations precision-fixed. Faithfulness: D12/D13
added so every exec-summary theme and tabulated finding now has a debt-register row and a roadmap
home or explicit deferral (B-F6 triple-surface unification is explicitly scheduled inside P2 hotspot
splits); §E gained a findings/verdict table mirroring A–D; the test-count bullet carries provenance +
UNCERTAIN; the previously dangling critic-report reference now points at the archived file.

**Status:** critic round-3 confirmation received — **PASS**. Final scores: Grounded 5 · Specific 5 ·
Complete-on-axes 5 · Decision-ready roadmap 4 · Honest uncertainty 5 · Independent pass 5. All 28
spot-checked citations exact, zero stale references (full three-round record:
[`reviews/arch-review-critic.md`](reviews/arch-review-critic.md), §Round-3).
