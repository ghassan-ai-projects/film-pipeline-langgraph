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
| G-01 | Reference extraction: immutable phase sequence, graph destinations, app/CLI/resume consumers, and callable-registry parity | Three independent lenses complete; all findings addressed | Graph/app/CLI/dynamic-routing subset passed | PASS — `make ci-check`; 2,008 passed / 8 skipped; 91.62% coverage | PASS — comparable baseline; 0 cycle findings added or removed | Pending | Ready to commit |
| O-01 | Freeze operator-path behavior at MCP call and stdio boundaries; compare graph/MCP validation and blocked-generation behavior | Not started | Not started | Pending | Pending | Pending | Queued |
| R-01 | Repair proven runtime, validation handoff, and persistence defects from O-01 evidence | Not started | Not started | Pending | Pending | Pending | Queued |
| V-01 | Consolidate other high-value vocabularies and provider registration ownership where tests prove a seam | Not started | Not started | Pending | Pending | Pending | Queued |
| B-01 | Tighten only measured import boundaries after behavior fixes | Not started | Not started | Pending | Pending | Pending | Queued |
| D-01 | Align product documentation with exercised operator behavior | Not started | Not started | Pending | Pending | Pending | Queued |

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
