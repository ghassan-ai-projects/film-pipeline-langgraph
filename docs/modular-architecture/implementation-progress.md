# Implementation progress

Updated: 2026-09-25

This log tracks implementation slices from the reviewed direction in
[06 — independent review and architecture decision](06-independent-review-and-decision.md).
It does not turn the superseded 20-module proposal into an execution plan.

## Per-slice quality gates

Each slice records its owner, consumers, three independent review lenses,
behavior tests, full `make ci-check` result (including coverage of at least 90%),
Enola result against a comparable baseline, self-review, and commit. Reviewers
must return actionable findings or an explicit no-findings verdict. Focused
test runs use `--no-cov`; only the full suite establishes the coverage gate.

Enola checks use the docs-local snapshot at `enola-out/` with
`enola-config.yaml`. The default `.enola` baseline is stale and incomparable;
it is not a passing result. Enola currently checks cycle deltas only because no
layer intent is declared. Package ownership is reviewed against the approved
direction and tested at consumer boundaries.

## Progress ledger

| Slice | Scope | Review | Focused proof | Full gate / coverage | Enola | Commit | Status |
|---|---|---|---|---|---|---|---|
| G-01 | Reference extraction: immutable phase sequence, graph destinations, app/CLI/resume consumers, and callable-registry parity | Three independent lenses complete; all findings addressed | Graph/app/CLI/dynamic-routing subset passed | PASS — `make ci-check`; 2,008 passed / 8 skipped; 91.62% coverage | PASS — comparable baseline; 0 cycle findings added or removed | `62b3eea` | Complete |
| O-01 | Freeze operator-path behavior at MCP call and stdio boundaries; compare graph/MCP validation and blocked-generation behavior | Three independent lenses complete; all findings resolved | PASS — 14 passed / 11 strict xfailed; `--runxfail` confirms all 11 fail at their intended divergences | PASS — `make ci-check`; 2,022 passed / 8 skipped / 11 xfailed; 91.69% coverage | PASS — clean against comparable baseline; no cycle findings changed | `8900416` | Complete |
| R-01a | Migration only: move checkpoint rollback manager orchestration and bookkeeping from MCP tools into `OperatorService` / app services while preserving active-project selection, confirmation, errors, and response projection | Three independent final reviews pass; first-round findings addressed | PASS — 63 passed / 10 strict xfailed across checkpoint service, MCP checkpoint, and O-01 divergence suites | PASS — `make ci-check`; 2,023 passed / 8 skipped / 11 xfailed; 91.69% coverage | PASS — docs-local snapshot baseline; clean, no cycle delta | Pending | In progress |
| R-01b | Keep provider-blocked generation paused after approval in compiled graph and app fallback | Queued | Pending | Pending | Pending | Pending | Queued |
| R-01c | Share validation result handoff, issue identity, and QC row-patch persistence across graph, app, and MCP | Queued | Pending | Pending | Pending | Pending | Queued |
| R-01d | Read and write MCP stdio as newline-delimited JSON at the process boundary | Queued | Pending | Pending | Pending | Pending | Queued |
| R-01e | Make graph/checkpointer bootstrap explicit and unify persistence root/mode selection while preserving `langgraph.json` loading | Queued | Pending | Pending | Pending | Pending | Queued |
| V-01 | Consolidate other high-value vocabularies and provider registration ownership where tests prove a seam | Not started | Not started | Pending | Pending | Pending | Queued |
| B-01 | Tighten only measured import boundaries after behavior fixes | Not started | Not started | Pending | Pending | Pending | Queued |
| D-01 | Align product documentation with exercised operator behavior | Not started | Not started | Pending | Pending | Pending | Queued |

## R-01a plan

- **Owner and consumers:** MCP keeps confirmation, existing runtime-active (or
  checkpoint-owner fallback) project selection, error mapping, and response
  projection. `OperatorService` owns rollback use-case orchestration;
  `app.services._checkpoint_ops` owns manager selection, rollback execution,
  and invalidation/rollback artifact persistence. The runtime remains the
  owner of checkpoint metadata and manager registries.
- **Planned code and tests:** extract the MCP-local rollback helpers into the
  app service without changing project-ref routing or any other operator
  behavior. Keep checkpoint lookup global, as before. Retain the committed
  O-01 strict xfails for deferred approval, revision, validation, and
  project-targeting divergences. Add a service-level proof that a checkpoint
  rollback returns its typed result and persists both bookkeeping artifacts;
  retain the MCP contract tests for confirmation and response shape.
- **Validation:** focused R-01a tests with `--no-cov -n 0`, full
  `UV_CACHE_DIR=.uv-cache make ci-check` (coverage at least 90%), Enola against
  `docs/modular-architecture/enola-out`, and `git diff --check` before commit.
- **Migration exit bar:** rollback manager construction/calls and bookkeeping
  persistence exist only in the app service; MCP contains confirmation and DTO
  projection only; success/confirmation response projections remain unchanged;
  all three independent reviewers approve the migration scope; full CI remains
  above 90% coverage; Enola reports no structural regression or cycle delta.
- **Deferred behavior:** request-scoped project targeting for approval,
  revision, validation, and rollback; checkpoint cross-project mismatch
  semantics; revision-note normalization at MCP; and the read-only
  `get_invalidation_report` scope finding. These remain explicit follow-ups.

## R-01a review record

The previous draft bundled request-scoped behavior repairs with the extraction.
At user direction, those edits were removed so this slice measures the
migration alone. The three independent review lenses were app/MCP ownership,
behavior preservation at the existing MCP contract, and implementation/test
quality. Behavior findings outside the extraction are recorded as deferred
rather than fixed in this slice.

The first review round found: a new import from private `schemas._base`,
redundant checkpoint reads on confirmed paths, and formatting/output-coverage
gaps. These were addressed by importing from `film_pipeline.schemas`, passing
the already-read typed checkpoint into rollback execution, skipping artifact
preview reads on confirmed calls, and strengthening the existing artifact
rollback success test to load both returned bookkeeping refs. The final
boundary review found no ownership blocker; the behavior review confirmed
normal-path parity; the quality review found no remaining actionable issue.
Ruff, strict mypy, the full test suite, package build, product gate, and Enola
all pass. Enola policy status is clean against the docs-local snapshot, with
the same five cycle findings and no cycle delta.

One invalid-runtime-state edge is explicit: if `runtime.services` is missing,
the app service now returns an actionable initialization error rather than
MCP's former empty assertion message. Normal initialized runtime paths and
their MCP output remain covered and unchanged. The read-only
`get_invalidation_report` path and request-scoped routing divergences remain
deferred as listed above.

## G-01 review record

- **Boundary lens:** identified missing parity coverage for
  `graph.nodes._repair_loop._PHASE_NODES`; keep callable ownership there and
  assert its keys match `PHASE_SEQUENCE`.
- **Behavior lens:** found no regression. Reconfirmed the provider-blocked
  generation mismatch in the app fallback as a separate follow-up for O-01.
- **Quality lens:** identified that the public mutable `PHASE_ORDER` could
  diverge from maps built once, and that the test name overstated graph
  reachability. Internal consumers now use the immutable sequence; the test name
  and proof description are narrowed.

The reviewed change set is the phase-sequence extraction already present in the
working tree at baseline commit `fb85baa`. The initial default Enola check was
declined because the root `.enola` baseline is stale; the docs-local baseline
and matching config provide the passing comparable result recorded above.
The first sandboxed `make ci-check` run passed format, lint, typing, and tests
but could not fetch the isolated `hatchling` build backend because DNS access was
blocked. The required full command was rerun with network access and passed,
including source/wheel builds and the product gate.

## O-01 review record

- **Behavior lens:** confirmed approval can enter `generation` after a human
  gate even when the provider is blocked; the graph edge and app fallback both
  advance directly. Also flagged revision-note preservation, approval-result
  reporting, and rollback state/report behavior for the next evidence pass; O-01
  freezes their response surfaces but does not yet claim those secondary leads
  are reproduced defects.
- **Boundary lens:** identified that all four mutating operator handlers can
  ignore the resolved request project and use active runtime state. Final
  two-project probes cover `approve_phase`, `request_revision`, `run_validation`,
  and checkpoint rollback. The action contract tests freeze `MCPResponse` and
  the JSON-RPC distinction between handler results and pre-dispatch errors.
- **Quality lens:** found existing tests mostly call handlers directly or use
  self-framed stdio fixtures; recommended real registry dispatch, mutation-
  relevant parity assertions, isolated roots, and no duplicate framing tests.
  Final review confirmed strict typing, a real compiled graph QC subgraph, a
  real persisted matrix fixture, and precise expected-failure boundaries.
- **Protocol check:** the in-repo stdio uses `Content-Length`; the current MCP
  transport spec requires newline-delimited JSON. The process probe sends only
  the valid initialization request, so it records the framing divergence without
  sending an operation before the initialize response.
- **Final review loop:** the behavior lens found that the earlier batched probe
  sent follow-up messages before receiving the initialize response. The probe
  was narrowed to one initialization request; the final behavior, boundary, and
  quality passes reported no remaining findings.

O-01 is characterization-only until its test commit. Known-divergence probes
must be strict expected failures so the suite stays green and the repair step
cannot accidentally leave a probe failing silently after it is fixed. No
production behavior changes are included in this slice.

The QC parity target follows §4 of the approved decision: graph and MCP
validation expose equivalent report findings, issues, and row-patch references.
The current MCP QC branch returns only `ok` plus a no-validator message, while
the existing script branch returns concise report summaries and saved refs.
O-01 therefore records an additive QC result projection (`reports`, `issues`,
and `qc_patch_ref`) as an explicit R-01 API target; the established script
response remains separately frozen. The project-resolution probes cover all
four mutating operator actions, and the stdio expected failure is isolated from
process-startup and malformed-response failures.
