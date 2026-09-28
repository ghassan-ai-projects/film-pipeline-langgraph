# Progress ledger — modularity improvements

One row per committed slice from [07 — sequencing and guards](07-sequencing-and-guards.md).
The "check" column is a command whose output is the evidence, not an argument.

Tooling note: `enola` 0.4.25 is the installed build. A `DECLINED` (exit 3) means the
pinned baseline is not comparable — regenerating is the fix, never a filter change.

| Step | Slice | Commit | Check | Enola |
|---:|---|---|---|---|
| 0 | Regenerate baseline; ignore `.pre-commit-cache/**`; `make enola` | `ba193d0` | `enola check` exits 0; 0 facts for `app`/`graph`/`artifacts`/`review`/`testing` | 0 |
| 1 | Delete the `nodes.approval` re-export shim | `f83e496` | module-level SCCs 2 → 1 (`measure.py`) | 0 |
| 2 | Delete dead functions, `generation/gemini_client.py`, cost residue | `fc80b18` | each deleted name greps to 0 in `src`/`tests`/`scripts` | 0 |
| 3 | One `ORCH_NS`; one vendor-endpoint module | `2bd8eff` | duplicated literals all → 1 (`measure.py`) | 0 |
| 4 | **Test first:** `_PHASE_NODES` identity + reducer parity | `4112a9e` | 9 cases fail, by design | n/a |
| 5 | Derive the manual merge from `StudioGraphState` | `2cc1bdb` | 8 of 9 cases flip to pass | 0 |
| 6 | One QC implementation: the parallel subgraph | `a0b016e` | identity test passes; SCCs back to 1 | 0 |
| 7 | **Test first:** CLI driver gets `NO_ACTIVE_PROJECT` / `CONFIRMATION_REQUIRED` | `fb14d31` | both fail, by design | n/a |
| 8 | CLI through `MCPServer.call`; public runtime installer | `_pending_` | Step 7's two tests pass; no `_RUNTIME` writes outside `studio` | 0 |

## Step 0 — Enola gate restored (2026-09-28)

Before: `enola check` exited **3 (DECLINED)** — baseline pinned by
`0.2.7-51-g72cd079` at `df97c47`; installed `0.4.25`; ignore globs differed.

What changed:

- `.pre-commit-cache/**` added to `ignore` in `enola-config.yaml`. This is a scope
  correction of the same kind as `.uv-cache/**`, not a threshold change: the dir is
  gitignored vendored hook code, and it contributed 963 facts that surfaced as
  "new coupling" on every run.
- Baseline cleared and re-pinned with `0.4.25` from the tree at `74490e2`.
- `make enola` added: runs the check **without a pipe** and propagates the exit code,
  so a later run cannot read `tail`'s status as the gate's.

After: `enola check` exits **0 (PASS — no architectural change)**; snapshot
`sha256:8783d71d…`, 8497 facts, 0 facts for the five removed packages
(`app`, `graph`, `artifacts`, `review`, `testing`).

Note, per AGENTS.md: a freshly pinned baseline grades against a snapshot, so it
cannot catch a *new* cycle. That check stays in
`tests/unit/architecture/test_package_acyclicity.py`.

The baseline artifacts are gitignored (`/docs/modular-architecture/enola-out/`), so
this slice's committed content is the config ignore entry and the `make enola` target.

## Step 1 — one fewer module cycle (2026-09-28)

`orchestration/nodes/approval.py` re-exported `_PHASE_NODES` and `repair_phase_node`
from `_repair_loop` "to keep the historical `graph.nodes.approval` import paths
working" — but the `graph` package no longer exists. That eager back-import was one
half of the `approval <-> _repair_loop` module cycle.

Pointed the two consumers (`studio/_graph_exec.run_phase_node` and
`orchestration/nodes/__init__`) at the owner, `nodes._repair_loop`, and deleted the
re-export plus its now-empty `__all__`.

The re-export goes through the public `orchestration.nodes` facade rather than the
private `_repair_loop` module, so `studio` adds **no** new private-module reach-in:
`test_boundary_law` keeps `studio -> orchestration._PHASE_NODES` at its recorded 1
(the facade uses the explicit `X as X` re-export form and does not widen `__all__`).

Evidence: `measure.py` module-level SCCs **2 → 1** (only `mcp.contract <-> registry`
remains). `enola check` exit 0. Full `make ci-check` green on the committed tree
(`f83e496`).

## Step 2 — dead code and cost residue (2026-09-28)

Deleted, each verified by `grep` to have no reference outside its own definition:

- `generation/gemini_client.py` — a "compatibility alias" re-exporting
  `providers.gemini_review_client`, with 0 importers in `src`, `tests`, `scripts`.
- `mcp.tools.helpers._active_project_state` — the helper `11` §5b recommended routing
  handlers through; the dispatch-level precondition made it unnecessary.
- `orchestration.orchestrator_state.has_execution_brief` — and its `__all__` entry.
- `storage._layout.project_relpaths` — its docstring claimed "used by boundary
  guards"; no guard imported it.
- `studio._operator_runtime.runtime_for` — and its `__all__` entry.

Cost residue from the cost-removal round, all defined and never read:
`studio/mock_responses._SEEDANCE_RATE_USD_PER_SECOND`,
`devharness/mock_human.MockHumanActor.spend_limit_usd`,
`providers/health.ProviderHealth.credit_remaining_usd`.

`credit_remaining_usd` was checked before deletion, per 06 §6.5: `ProviderHealth` is
a plain `@dataclass` with no serialiser, and `schemas/provider_health.ProviderHealthState`
— the persisted shape — never carried the field. `quota_remaining` is live (read by
`is_blocked`'s taxonomy) and stays.

Stale wording: `governance/validators/__init__.py` claimed Gate B checks
"non-placeholder cost estimates"; that half was removed with the cost feature
(`planning_gates.py` already records it).

Two recorded counts were re-measured rather than edited to match, per AGENTS.md:
`_surface_baseline.py` `generation` modules 15 → **14** (the deleted module), and
`test_orchestrator_state_surface`'s docstring 39 → **38** public symbols.

Evidence: every deleted name greps to 0; `enola check` exit 0; full `make ci-check`
green on the committed tree with no test edits beyond the recorded-code tests above.

## Step 3 — one `ORCH_NS`, one vendor-endpoint module (2026-09-28)

**`ORCH_NS`.** The `_orchestrator` namespace prefix was defined twice — in
`governance/orchestrator_reads.py` and in `orchestration/orchestrator_state.py`.
Two copies of one literal is the "one policy, N sites" shape: had they drifted,
`get_execution_brief` would have returned `None` and the brief gate
(`governance/validators/brief.py`) would have seen no brief, with no test tying the
two. `orchestration -> governance` is already an edge, so
`orchestrator_state` imports `ORCH_NS` from `orchestrator_reads` with no new edge
and no cycle. The owner is `governance` (it is the reader that must not import
upward); `orchestration` binds it as `_ORCH_NS` to keep the ten f-string key
constants, and the parity test that reads them, unchanged.

**Vendor endpoints.** New `providers/vendor_endpoints.py` owns the two base URLs,
beside `providers/credentials.py`, which already owns the other half of "talking to
a vendor" — which env var holds its key. Four sites now import from it:

| Was | Now |
|---|---|
| `agents.transports.gemini.GEMINI_API_ROOT` | `GEMINI_API_BASE` |
| `providers.adapters.imagen4_gemini.GEMINI_API` | `GEMINI_API_BASE` |
| `providers.gemini_review_client.GEMINI_API_BASE` | `GEMINI_API_BASE` |
| `providers.adapters.seedance_openrouter.OPENROUTER_API` | `OPENROUTER_API_BASE` |

The fourth fixes a worse defect than a duplicate: `agents.transports.chat_completions`
— a *text*-LLM transport — imported the OpenRouter base from a *video* adapter module
for a string. It now imports `providers.vendor_endpoints` directly, so the
`agents -> providers.adapters` edge for that constant is gone. The z.ai bases stay in
`agents.transports.zai`: they are defined once each, two distinct hosts, and that
module owns its own allowlisted-base-URL rule.

Evidence — `measure.py` reports **1 / 1 / 1** for the Gemini, OpenRouter and
`_orchestrator` literals (was 3 / 1 / 2). `measure.py`'s `_ORCH_NS` pattern was
also corrected: it matched only the private spelling, so renaming the survivor
reported **0** definitions rather than 1 — a measurement that would have read as a
pass while checking nothing. Two recorded counts moved with the change and were
re-measured, not edited to match: `providers` public modules 13 → **14** (the new
module) and `agents.transports` declared names 20 → **19** (`GEMINI_API_ROOT` is
gone from the facade).

CLI/MCP import time is unchanged (`import film_pipeline.mcp.server` ≈ 0.17 s),
so no hoist here pulled in LangGraph.

## Step 4 — the two correctness defects, as failing tests (2026-09-28)

New `tests/unit/orchestration/test_graph_manual_path_parity.py`. **This commit is
deliberately red**: 07 asks for the failing test on the old tree first, so Step 5
and Step 6 are proven by the test flipping rather than by the absence of failures.

Reproduced on this tree:

```text
test_phase_nodes_match_graph                        FAILED
  divergent: {'qc': ('qc_node', 'CompiledStateGraph')}

test_manual_merge_matches_graph_reducer[artifact_refs]           FAILED
test_manual_merge_matches_graph_reducer[issues]                  FAILED
test_manual_merge_matches_graph_reducer[validation_report_refs]  FAILED
test_manual_merge_matches_graph_reducer[generation_requests]     FAILED
test_manual_merge_matches_graph_reducer[_qc_reports]             FAILED
test_manual_merge_matches_graph_reducer[_qc_raw_reports]         FAILED
test_non_annotated_keys_are_last_write                           FAILED
test_update_channels_are_not_hard_coded                          FAILED
```

All eight reducer cases currently fail at the same line — `studio._graph_exec`
has no `apply_node_update` — because this test names the seam Step 5 introduces.
The divergence 02 documented by reading is encoded as the named regression
`test_update_channels_are_not_hard_coded` over `_routing_decisions`,
`_validation_reports`, `_qc_reports`, `_qc_raw_reports`.

**The parity test does not enumerate a fixed channel list.** It walks
`typing.get_type_hints(StudioGraphState, include_extras=True)`, so a channel added
to the schema tomorrow is graded the day it is added — which is the whole defect
class: the hand-maintained table is invisible to new channels. Two
guard-the-guard tests (`test_the_schema_still_declares_annotated_channels`,
`test_phase_nodes_covers_the_whole_sequence`) fail if the parametrization ever
becomes vacuous, since an empty channel set or a short `_PHASE_NODES` would make
both tests pass while checking nothing.

Both `qc` and the six-channel walk were confirmed against the live tree before the
tests were written, not inferred from the document.

## Step 5 — one reducer source (2026-09-28)

`studio/_graph_exec.run_phase_node` carried its own literal reducer table. It is
gone; the merge rule is now derived from the declaration that LangGraph itself
reads.

New in `orchestration/state_schema.py` — the module that already owns the
reducers, so the rule has one owner rather than two:

- `channel_reducers()` — walks
  `get_type_hints(StudioGraphState, include_extras=True)` and returns
  `{channel: reducer}` for every `Annotated[T, reducer]` field. Cached, and the
  hints are read **with** `include_extras=True`: the default strips `Annotated`
  metadata, which would have returned an empty mapping and silently turned every
  caller into a last-write merge.
- `apply_node_update(state, update)` — LangGraph's rule and the whole of it:
  annotated channels merge through their reducer, every other key is a last write.

`run_phase_node` now calls `apply_node_update`. One behaviour change follows from
the rule, and it is the correct direction: a channel **present** in the update
merges even when the incoming value is empty, because an explicit clear is a
merge, not an omission. The old table skipped falsy incoming values.

Evidence — the Step 4 tests flipped. Before: 9 failing cases with 4 channels
divergent. After:

```text
test_manual_merge_matches_graph_reducer[all 6 channels]   PASSED
test_non_annotated_keys_are_last_write                    PASSED
test_update_channels_are_not_hard_coded                   PASSED
test_phase_nodes_match_graph                              FAILED   <- Step 6
```

The only remaining failure is `qc`, which is Step 6's slice, not this one. Full
`make ci-check`: 2381 passed, 1 failed (that test). `mypy src tests` clean.

## Step 6 — one QC implementation (2026-09-28)

Decision recorded in [`documentation/qc-single-implementation.md`](../../documentation/qc-single-implementation.md)
**before** any code changed, as 02 requires.

**Canonical: the parallel subgraph.** `_PHASE_NODES["qc"]` is now the same object
`build_graph` wires for `qc_node`. The sequential `nodes.qc.qc_node` was a second
implementation that did different work, so a film's first QC pass and its repair
QC pass ran different code.

What the decision did with the sequential node's three extra capabilities:

| Capability | Disposition |
|---|---|
| Matrix patch from per-row findings | **Kept** — `subgraphs.qc.emit_matrix_patch_from_findings`, wired into `reduce_qc_reports` (a no-op today; a test asserts the wiring) |
| Consensus report | **Kept, defect fixed** — the subgraph now builds the *deterministic* `ConsensusBuilder` consensus over the reports the workers returned, replacing the agent-based free-text synthesis that could disagree with them |
| Registry-driven validator dispatch | **Dropped for `qc`** — the subgraph's six workers are QC's validator set; `"qc"` removed from `nodes.qc._VALIDATOR_RUNNERS` |

Evidence — the Step 4 test flipped:

```text
test_phase_nodes_match_graph   FAILED  ->  PASSED   (was the only failure left by Step 5)
```

`test_qc_validator_dispatch.py`'s `qc` case moved from "covers upstream but not
delivery" to "runs no sequential runner", which is the new law.

**Three defects surfaced during implementation, two of them invisible to the suite:**

1. **`operator.add` on a missing channel** — `apply_node_update` passed `None` as
   the left-hand value, and `operator.add(None, [...])` raises. LangGraph always
   supplies an accumulator; the manual path does not, because a node reached
   through it can be the channel's *first* writer. Now treated as an empty
   accumulator. Caught by `tests/integration/test_validation_runtime.py`.
2. **A real `ImportError`** — building `_PHASE_NODES` at import time compiled the
   subgraph, so importing `subgraphs.qc` first raised `cannot import name
   'qc_phase_node' from partially initialized module`. The whole suite was green;
   only a direct import (and Enola) showed it. Fixed with a deferred
   `_LazyQcPhaseNode` row and a `resolved_phase_node(phase)` accessor.
3. **A two-module package cycle** — `measure.py` SCC count went 1 → 2 during the
   work. Final shape: `orchestration/qc_steps.py` (root, leaf-only) owns the
   shared consensus builder, `subgraphs.qc` owns the matrix-patch emitter, and every
   cross-module import among them is function-level with a `# lazy:` reason.

Final measured state: `measure.py` module-level SCCs **1** (only
`mcp.contract <-> mcp.registry`), `test_package_acyclicity` passes, and every
import order of the four modules involved succeeds in a fresh interpreter. Enola
still reports an `orchestration -> nodes -> subgraphs` cycle because it collapses
all root-level modules into the `orchestration` node; the reasoning and the three
measurements above are recorded in the decision doc as evidence it is a modelling
artifact. `enola check` exits 0.

Full `make ci-check`: 2387 passed, 91.82% coverage, product gate PASS.

## Step 7 — the CLI's dispatch bypass, as failing tests (2026-09-28)

New `tests/unit/cli/test_driver_dispatch.py`. **Deliberately red**, same rationale
as Step 4: 07 puts the failing test on the old tree so Step 8's fix is proven by
the test flipping.

Reproduced on this tree:

```text
test_driver_enforces_the_active_project_precondition  FAILED
  film_pipeline.operations.errors.ProjectNotFoundError: No active project.
  (raised out of the handler, not returned as a typed MCP error)

test_driver_enforces_confirmation_on_a_human_gate     FAILED
  approve_phase without `confirmed` returned
  {'ok': True, 'project_id': 'dispatch-test', 'current_phase': 'constitution'}
  — a human gate advanced with no confirmation.
```

Both are the *public* surface (`HeadlessDriver._call_tool`), because that is the
seam Step 8 replaces. The second is the finding's sharpest form: not a wrong error
code, an applied gate.

## Step 8 — the CLI goes through dispatch (2026-09-28)

`HeadlessDriver._call_tool` imported the handler callable and awaited it. It now
builds an `MCPServer` and calls `await server.call(name, args)`, unwrapping the
`MCPResponse` back into the `{"ok": ...}` dict the driver's callers already read.
All three dispatch checks therefore run on the headless path: `project_ref`
resolution, the confirmation gate, and the active-project precondition.

**The runtime installer.** `setup_runtime` installed its runtime by assigning
`rt_mod._RUNTIME` and `rt_mod._RUNTIME_MODE_OVERRIDE` — a write to another
package's private globals. `studio.runtime.install_runtime(runtime, mode=...)` is
the public owner-side form, and it is where the mode pin now lives so
`get_runtime` cannot discard the installed runtime for disagreeing with the
environment.

**The guard 01 asked for, built and adversarially tested.** `test_boundary_law.py`
counted private *imports*; it could not see this shape at all, because the module
(`studio.runtime`) is public and the attribute is spelled literally. New section 4
counts assignments to `<module_handle>._<name>` where the handle is another
package, with `KNOWN_PRIVATE_ATTRIBUTE_WRITES` **empty on purpose**. Two guards
keep it honest: a self-test asserting the detector still sees
`alias._private = value`, and an injection run that reintroduced
`rt_mod._RUNTIME = rt` and confirmed the guard reports
`[('cli', 'studio._RUNTIME')]` rather than passing silently.

**One existing test changed contract, deliberately.** `test_call_tool_unknown_tool`
asserted `HeadlessDriverError("Unknown MCP tool")`. Dispatch already owns "there is
no such tool" and answers `MCPErrorCode.UNKNOWN_TOOL`, so the driver now renders a
failed response instead of raising. Two owners for one condition is the defect
class this program keeps finding, so the test moved to the typed error.

Evidence: Step 7's two failing tests pass; `make ci-check` 2392 passed, 91.86%
coverage, product gate PASS; `mypy src tests` clean; the full e2e suite passes,
including the `invoke_tool` fixture that itself drives the direct path (unchanged
here — doc 01 step 10's `ToolContext` is what removes it). `enola check` exits 0.
