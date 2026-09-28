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
| 8 | CLI through `MCPServer.call`; public runtime installer | `30575ec` | Step 7's two tests pass; no `_RUNTIME` writes outside `studio` | 0 |
| 9 | Delete the orphaned operator surface | `f717013` | coverage ≥ 90% **without new tests**; `mcp -> studio._operator_runtime` stays 1 | 0 |
| 10a | `ToolContext` mechanism + first group (`audit`); slice 3 (one active project) | `2ae1db7` | `call_tool` fixture; `MCPServer.active_project_id` deleted | 0 |
| 10b | **All 25 tool modules** on `ToolContext`; `require_project_*` deleted | `e34c3e0` | `get_runtime()` in `mcp` **61 → 3**, all in `server.py` | 0 |
| 11a | `ToolSpec`/`ToolArgs` mechanism + `audit` declarations + catalog guard | `8f182f1` | `input_schema`: 0 → 4; generic descriptions 75 → 71 | 0 |
| 11b | `checkpoints` (8) + `projects` (6) declared | `ec1c323` | `input_schema`: 4 → 18; generic descriptions 71 → 57 | 0 |
| 11c | `generation` (9) + `bibles` (5) declared; args-coverage guard | `cc83fcd` | `input_schema`: 18 → 31; generic descriptions 57 → 44 | 0 |
| 11d | `artifact` (7), `state` (5), `kb` (4), `validation` (3) declared | `9446b27` | `input_schema`: 31 → 50; generic descriptions 44 → 25 | 0 |
| 11e | **remaining 25 tools + dead `_register` path + derived facade** | `e7cbb95` | `input_schema`: 50 → **75/75**; generic descriptions 25 → **0** | 0 |
| 13 | Graph execution moved into `orchestration` | `88d773a` | cross-package private reach-ins: **8 → 2** | 0 |
| 14a | Profile-change resolve/diff into `config`; graph-builder regression fixed | `0ca9313` | 7 pure helpers out of `mcp`; new registration guard | 0 |
| 14b | Reference generation use case into `generation` | `001ad57` | `mcp -> generation` imports: **23 → 14** | 0 |
| 15a | Lazy-import guard added; `storage` and `governance` hoisted to 0 | `c8e7a58` | unexplained lazy imports: **277 → 266**; guard ratchets | 0 |
| 15b | `post`, `cli` hoisted; `# lazy:` handling for real blockers | `ac4b505` | unexplained lazy imports: **266 → 242**; `post` 20 → 5, `cli` 7 → 1 | 0 |
| 15c | `generation.reference` hoisted where safe; patched call targets kept lazy | `637ceac` | unexplained lazy imports: **242 → 222**; `generation` 25 → 5 | 0 |
| 15d | `studio` hoisted to 0 | `b7ca469` | unexplained lazy imports: **222 → 207**; `studio` 15 → 0 | 0 |
| 15e | `generation` hoisted to 0 | `485a7cc` | unexplained lazy imports: **207 → 202**; `generation` 25 → 0 | 0 |
| 15f | `post` to 0; the guard's per-line reason rule made explicit | `9a99fcb` | unexplained lazy imports: **202 → 197**; `post` 5 → 0 | 0 |
| 15g | `orchestration`: `visual` (13), `subgraphs/qc` (11), `nodes/qc` (11) hoisted | `5cc0170` | unexplained lazy imports: **197 → 164**; `orchestration` 89 → 56 | 0 |
| 15h | `orchestration`: `_repair_loop`, `approval`, `execution` hoisted | `e829c1d` | unexplained lazy imports: **164 → 144**; `orchestration` 56 → 36 | 0 |
| 15i | **`orchestration` to 0**; AST-based hoister replaces the regex | `51bba6a` | unexplained lazy imports: **144 → 108**; `orchestration` 36 → **0** | 0 |
| 15j | **`mcp` to 0 — Step 15 complete** | `_pending_` | unexplained lazy imports: **108 → 0**; 39 remain, all explained | 0 |
| 16 | `StudioRuntime` re-measured and the split decided against | `_pending_` | **393 lines, 29 methods, 9 concerns**, 13 delegators | 0 |

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

## Step 9 — the orphaned operator surface is gone (2026-09-28)

**The decision doc 03 says to ask about was asked.** The user chose deletion; the
question and the measured options are in this session's record. Doc 03's own
caveat stands: if an HTTP or web operator surface is later built, it should be
written against MCP (the product boundary), not against a resurrected in-process
service — which is exactly the divergence `audit-findings.md` #8 recorded.

**Measured before deleting** (this is what made the slice safe):

| Surface | Consumers outside `operations/` in `src` |
|---|---:|
| `DashboardSummary`, `ReviewWorkspace`, `ValidationWorkspace`, `GenerationWorkspace`, `AuditEvent`, `ProjectListItem`, `MutationResult`, … | **0** each |
| `OperatorService` public methods | **6 of 31** |

The six survivors, each moved to the package that owns its concern:

| Use case | New home |
|---|---|
| `get_checkpoint`, `rollback_artifact`, `rollback_to_checkpoint` | `operations/_checkpoint_ops.py` (already there; now plain functions over a `RuntimePort`) |
| `register_profile_providers` | `studio/_operator_runtime.py` (composition policy — needs the concrete adapter factory) |
| `missing_profile_credentials` | `mcp/tools/helpers.py` |
| `preview_generation_prompts` | `generation/prompt_preview.py` (new) |

Deleted: `operator.py`, `_browse_ops.py`, `_generation_ops.py`,
`project_discovery.py`, the 7 view models and 4 more unused models, the
`RuntimeProvider` and `ProviderComposition` protocols, `OperatorService`, and
`tests/unit/operations/test_operator_service.py` (698 lines) plus
`tests/integration/test_operator_path_divergence.py` (660 lines) — tests that
existed because there were two operator paths.

**Three things the deletion taught, each caught by a guard rather than by review:**

1. **`config` may not import `providers`.** Putting `missing_profile_credentials`
   beside `config.profile_resolver` (doc 03's suggestion) violated
   `test_profile_resolver_does_not_import_app_or_provider_modules` — `config` is
   the *neutral* resolver. It moved to `mcp/tools/helpers.py`, which composes
   `provider_specs` + `providers.credentials` directly and keeps `mcp`'s single
   composition-root reach-in at **one** site (adding it to
   `studio._operator_runtime` would have made that reach-in count 1 → 2, which
   `test_known_private_reach_ins_have_not_grown` reported).
2. **`RuntimePort`'s docstring was false.** It claimed "every member below is
   called by at least one operator use case"; after the deletion that held for 7
   of ~30. The protocol is now the measured surface, which is what doc 03 asked
   for (`ArtifactStorePort`/`ServicesPort` remain aliases, not protocols).
3. **A surface guard reported shrinkage as growth.** `test_surface_ratchet`'s
   three count guards compared with `!=`, so deleting four modules failed with
   *"public module count grew"*. Fixed to compare direction, with a new
   `_assert_shrunk_rows_are_recorded` requiring the baseline to be lowered —
   otherwise slack would let that much growth return silently, the same defect
   `test_recorded_reach_ins_are_not_stale` guards for reach-ins. Verified
   adversarially: raising a baseline row above reality now fails with the exact
   edit named.

**Falsifiable check from doc 03, satisfied:** `make ci-check` and the 90% gate stay
green *without adding tests* — 2334 passed, **91.55%** coverage (was 91.86% with
~1,400 lines of operator tests). The small drop is the evidence that a little of
the deleted code was load-bearing and is now covered by its owners' own tests;
the gate itself never moved. `enola check` exits 0.

## Step 10a — the `ToolContext` mechanism, the `audit` group, and slice 3 (2026-09-28)

Doc 01 splits into three slices and says to do one tool group per commit. This is
the **mechanism** plus the first group, because the mechanism is what every later
group depends on. The remaining 24 modules follow the same pattern.

### The mechanism

`ToolContext` (`mcp/tools/context.py`) carries `runtime`, `project_id`, and
`envelope`. Dispatch builds it in `MCPServer._build_context`, once per call,
instead of each handler resolving the process singleton for itself.

Handlers now come in two shapes, and `MCPServer._accepts_context` picks between
them **from the first parameter's name** — so a module is migrated by changing its
signature, with no registry flag to keep in step:

- `handler(ctx, args)` — the target shape.
- `handler(args)` — legacy, still handed `"_envelope"` inside `args`.

`ToolHandler` admits both; when the last legacy handler moves, the second member
and the `"_envelope"` key are deleted together. `measure.py` still reports 61
`get_runtime()` calls at this point **by design** — only one group has moved.

### Group 1: `audit`

Four handlers migrated. Their tests now use a shared `call_tool` fixture that
builds the real `ToolContext` from a runtime the test owns, replacing direct
`handler(args)` calls. Doc 01's slice 2 predicts this deletes the 73
`get_runtime` monkeypatches as groups move; the fixture also handles the legacy
shape so a half-migrated tree stays testable.

### Slice 3 came forward, because the E2E path forced it

Routing the E2E `invoke_tool` fixture through `MCPServer.call` (doc 01's
"what this does not establish" predicted this) immediately failed five scenarios
with `NO_ACTIVE_PROJECT`. The cause is finding 01's second half: **"active project"
had two owners** — `MCPServer.active_project_id` and
`StudioRuntime.active_project_id` — reconciled after the fact by
`_auto_register_from_runtime`, whose own comment conceded the gap.

`MCPServer.active_project_id` is now **deleted**, and the server reads the
runtime's active project through `_active_project_from_runtime()`. The runtime
owns project state, so it owns "active". Two tests asserted the second copy's
behaviour and were rewritten to assert the stronger property that resolution never
has a side effect on the active project.

**`invoke_tool` now goes through dispatch**, so the E2E scenarios exercise the
confirmation gate and the active-project precondition for the first time. That is
the single biggest evidence improvement in this slice: the suite's strongest
end-to-end test was previously evidence about the path that skips the checks.

### A cycle this slice created, and the three placements it took to remove it

`ToolContext` was written inside `envelope.py`, then in its own `mcp/context.py`,
then in `contract.py`. Each closed an `mcp -> tools -> mcp` cycle Enola reports
(cycle count went 1 → 2). The mechanism, measured rather than guessed:

- `mcp/contract.py` declares `ToolHandler` as a **runtime** type alias mentioning
  `ToolContext`, so it must import the name at runtime — `TYPE_CHECKING` raises
  `NameError` when the alias is evaluated.
- `mcp/__init__` imported `contract` eagerly, and the tool modules do
  `import film_pipeline.mcp.tools as tools_pkg`, which executes `mcp/__init__`.
- Enola collapses every module directly under `mcp/` into the `mcp` node, so an
  import from `contract` (root) to a module the tools also reach *is* the cycle.

Fixes, both kept because both are improvements:

1. **`mcp/__init__`'s re-exports are now lazy** (PEP 562 `__getattr__`, the pattern
   the facade already used for `MCPServer`). Nothing in `src/` imports the facade —
   only tests do — so this costs nothing and removed a real
   `mcp.__init__ -> mcp.server` edge too.
2. **`ToolContext` lives in `mcp/tools/context.py`**, under the subpackage Enola
   treats as its own node, so `contract -> tools.context` is no longer a root
   self-edge.

`ToolContext.project_state()` was also dropped: `helpers.require_project_state`
already owns "the project's state, or a raise", and a second method for one rule is
the duplication this program keeps removing.

### Evidence

- Step 7's and Step 8's tests still pass; the full E2E and smoke suites pass
  through dispatch.
- `make ci-check`: **2334 passed, 91.56% coverage**, product gate PASS.
- `mypy src tests` clean.
- `enola check` exit 0, cycle count **back to 1** (only the known `orchestration`
  root-collapse artifact).
- Recorded surface growth, re-measured not asserted: `mcp` 14→15 declared names and
  37→38 public modules, `mcp.tools` 31→32 modules.

## Step 10b — every tool module on `ToolContext` (2026-09-28)

**Doc 01 slice 2's falsifiable check is met.** `measure.py`:

```text
get_runtime() calls in mcp:  61  ->  3
```

All three survivors are in `mcp/server.py` and they are dispatch itself:
`_resolve_project_ref`'s active-project read, `_build_context`, and
`_active_project_from_runtime`. That is the target — one place resolves the
runtime, instead of 61 handlers doing it for themselves.

### What moved

All 25 handler modules migrated, each by changing its signature to
`handler(ctx, args)` — `MCPServer._accepts_context` picks the shape from the first
parameter's name, so no registry flag had to be kept in step. Groups, in the order
they landed: `audit`, `providers`, `intake`, `config`, `assembly`, `review`,
`validation`, `operator`, `planning`, `bibles` (5 modules), `generation` (4),
`artifacts`, `checkpoints`, `state`, `kb`, `projects`, `_profile_change`,
`reference_generation`.

**Deleted with the migration**, because the context made them dead:

- `helpers.require_project_id` and `helpers.require_project_state` — 44 handlers
  called one of them to re-derive a project dispatch had already resolved. They
  now call `ctx.project_state()`, whose rule lives once, on the context.
- `helpers._active_project_id` — the two-source fallback (envelope, then runtime)
  that existed only because the handler had to reconstruct the resolution.
- `mcp/tools/context.py` gained `project_state()`. It was removed in Step 10a
  because `require_project_state` still owned the rule; once the migrated callers
  needed it, the context became the owner — and, from `mcp/tools/`, it no longer
  closes the `mcp -> tools -> mcp` cycle that forced it out in Step 10a.

### The test seam

`call_tool` moved from `tests/unit/mcp/tools/conftest.py` to the **root**
`tests/conftest.py`, so `tests/unit/`, `tests/integration/` and the smoke suite can
all use it. It builds the real `ToolContext` for a runtime the test owns, and it
still handles the legacy `handler(args)` shape — which is why a half-migrated tree
stayed runnable throughout, and why the remaining legacy handlers in the tree today
are only those with no `get_runtime` call to remove.

It reads `tools_pkg.get_runtime()` on purpose: a test that patched that accessor
gets its own runtime, and a test that patched nothing gets the process runtime,
exactly as dispatch would.

### Four defects the migration surfaced, all caught by tools rather than review

1. **`project_state()` was needed after all.** Removing it in 10a was premature —
   see above. The cycle that justified its removal was a *placement* problem, not a
   reason to lose the rule.
2. **A nested helper was given the fixture parameter.** My codemod added
   `call_tool: CallTool` to `_fake_poll`, `is_configured` and a `_explode` stub
   because they were in functions that used the fixture. Every one was a
   `TypeError` at runtime, and mypy and ruff were both silent.
3. **A `return` was dropped** from `asyncio.run`-wrapped closures when they became
   sync, which mypy caught as `Missing return statement`.
4. **`ctx.project_id` is `str | None`** where a handler needed `str`. The fix was
   not a cast: `project_state()` already proves the guarantee by returning, so the
   id is read from the resolved state.

### Evidence

- `measure.py`: `get_runtime()` in `mcp` **61 → 3**; `rt: Any` parameters **37 → 35**.
- `make ci-check`: **2335 passed, 91.63% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean across 212 test files.
- `enola check` exit 0, **cycle count still 1** (only the known `orchestration`
  root-collapse artifact).
- No `git stash`-style experiments left behind: the tree is the committed state.

## Step 11a — the tool declaration becomes real (2026-09-28)

Doc 04's mechanism plus the first group, same shape as Step 10a: the mechanism is
what every later group depends on.

### What was measured before

```text
tools: 75
with input_schema: 0
with output_schema: 0
with generic 'MCP tool: <name>' description: 75
args.get( in mcp: 86
```

The stdio transport forwards `input_schema` as `inputSchema`, so every MCP client
saw 75 tools that accept `{}` and are described only by their names — while
handlers compensated with 86 `args.get(...)` calls and ad-hoc coercion. AGENTS.md
states the rule that breaks: *"Pydantic v2 for all schemas (never raw dicts across
boundaries)"*, and this is the boundary the blueprint calls the product surface.

### The mechanism

- `ToolArgs` — a Pydantic base with `extra="forbid"`. Deliberate, and the same
  experiment that produced the schemas round's 96-failure work list: an unknown
  argument becomes a typed error instead of a silent no-op, so the first failing
  run enumerates every caller sending something no handler reads.
- `ToolSpec` — pairs `name`, `group`, `description`, `args` model, handler and the
  four flags. `spec.contract()` publishes `args.model_json_schema()` as the real
  `input_schema`, so the contract is *delivered*, not just declared.
- `ToolRegistry.register_spec` is the target register path; `ToolRegistration`
  carries the spec so dispatch can validate.
- **Dispatch validates arguments through the spec** and answers a typed
  `VALIDATION_ERROR`, so a malformed call is a refusal rather than a `KeyError`
  deep inside a handler. Tools registered the older way have no spec and pass
  through unchanged — the same both-shapes-during-migration pattern as Step 10.

### Group 1: `audit`

Four tools declared next to their handlers. The tool list was previously declared
in three places (registry calls, the `_TOOL_MODULES` lazy facade, the `.pyi` stub);
a spec is one edit.

### The guard doc 04 requires

`tests/unit/mcp/test_tool_contract_catalog.py` ratchets:

- the count of tools publishing an `input_schema` may only **rise** (a fall means a
  tool lost its spec, and it names the count rather than passing);
- a tool with a schema must not still carry the generic `"MCP tool: <name>"` text —
  the two travel together in a `ToolSpec`, so publishing one and not the other
  means the spec was bypassed;
- every published schema must set `additionalProperties: false`;
- a guard-the-guard asserting the catalog is not empty, so the sweep cannot be
  vacuous.

Verified adversarially: raising `TOOLS_WITH_DECLARED_ARGS` above the real count
fails with the tool-count message.

### The cycle this slice re-opened, and the restructure that closed it

Declaring specs made tool modules import `contract`, which is at the `mcp` package
root that `mcp/__init__` imports — so `mcp -> tools -> mcp` came back (Enola cycle
count 1 → 2). Four placements were tried; the first three each moved the edge
rather than removing it. The one that worked:

**The declaration vocabulary moved to `mcp/tools/spec.py`** — `ToolArgs`,
`ToolSpec`, `ToolContract`, `ToolGroup`, `ToolHandler` — beside the tools that use
them. `contract.py` keeps only the registry and imports none of them at runtime
(`TYPE_CHECKING` for the annotations, which are strings via
`from __future__ import annotations`). `mcp/__init__` resolves all of them lazily.

That is the honest shape: the *registry* is infrastructure and lives at the root;
the *declaration* is what a tool owns and lives with the tools. Verified:
`measure.py` is unaffected, every import order of `contract`, `registry`, `spec`,
`context` and `tools.audit` succeeds in a fresh interpreter, and the Enola cycle
count is **back to 1**.

### Evidence

- `measure.py`: `input_schema` **0 → 4**; generic descriptions **75 → 71**.
- `make ci-check`: **2339 passed, 91.64% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean.
- `enola check` exit 0, cycle count 1.
- Recorded surface growth, re-measured: `mcp` 38 → 39 modules, `mcp.tools` 32 → 33.

## Step 11b — `checkpoints` and `projects` declared (2026-09-28)

The two largest `args.get` groups (11 and 10 calls). 14 tools, taking the catalog
from 4 tools with a real `input_schema` to 18, and generic descriptions from 71 to
57. `measure.py` confirms both.

### The flag-parity check, which caught a real slip

Moving a tool from `_register(...)` to a `ToolSpec` **re-states its four flags**,
and nothing about a green suite notices a wrong one: a flag changes *when* dispatch
refuses a call, not whether the handler works.

So the migration was verified against the contract as published **before** the move:
capture every tool's `(group, mutates_state, requires_confirmation,
creates_checkpoint)` from the registry at the previous commit, then diff after the
swap. It reported exactly one difference — `rollback_artifact` had gained
`creates_checkpoint: True`, which the registry had never set. Without the check this
would have shipped as a silent semantic change: the tool would have started creating
checkpoints.

That comparison is now a guard,
`test_declared_specs_preserve_the_registered_flags`, with the pre-move flags recorded
explicitly. It is deliberately *not* derived from the specs — a guard that reads the
thing it grades cannot catch a restatement.

### Evidence

- `measure.py`: `input_schema` **4 → 18**; generic descriptions **71 → 57**.
- Flag diff against HEAD: **NONE**, after fixing the one above.
- `make ci-check`: **2340 passed, 91.66% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count 1.

## Step 11c — `generation` and `bibles` declared, and the guard that grades the rest (2026-09-28)

14 more tools: the four `generation` modules (9 tools) and the five `bibles`
documented as `generation`-group tools. Catalog: **31 tools with a real input
schema** (from 18), generic descriptions **44** (from 57).

### `extra="forbid"` found a real argument immediately

The smoke suite failed with:

```text
1 validation error for PlanGenerationBatchArgs
mode   Extra inputs are not permitted
```

`plan_generation_batch` reads `args.get("mode", "test")` and my model omitted
`mode`. The AST sweep that produced the models had missed it because the call is
`args.get("mode", "test")` in a *module-level helper* (`_resolve_generation_mode`),
not in the handler body. That is the experiment doc 04 predicted working as
intended: the failing call named the gap instead of the gap shipping as a silently
ignored argument.

### So the sweep became a guard, not a one-off

`tests/unit/mcp/test_tool_args_coverage.py` walks every `ToolSpec`, follows the
handler **and every module-level helper it calls**, and asserts the args model
declares every key any of them reads. Run across all 31 specs it reported exactly
one offender — the `mode` above — then zero.

Adversarially verified: deleting `mode` from the model fails the guard with
`{'plan_generation_batch': ['mode']}`.

### Two more real defects, both caught only by the smoke suite

1. **`confirmed` is a protocol field, not a tool argument.** `MCPServer._check_confirmation`
   reads `arguments["confirmed"]` for every `confirm=True` tool and never passes it
   to the handler. With `extra="forbid"` this meant every confirming tool rejected
   the field the gate requires. Fixed by declaring `confirmed` once on `ToolArgs`,
   with the reasoning in its docstring, plus
   `test_the_protocol_confirmed_field_is_really_declared`.
2. **An edit that silently did not apply.** The first attempt to add that field
   matched a docstring string that had already changed, so the field was never
   defined — and *every gate stayed green*: mypy, ruff, the catalog ratchet and the
   args-coverage sweep were all satisfied, because the field was absent rather than
   wrong and no unit test called a confirming tool. Only
   `promote_test_to_production` in the smoke suite failed. The regression guard
   above exists specifically because of this.

### A deletion I caused, and the check that caught it

Replacing the `# generation` block in `registry.py` removed **8 registrations that
lived in that range but were not `generation` tools** as such — the five bibles,
`generate_plan`, `generate_reference_images` and `run_validation`. They were
restored as specs with their original groups and flags.

Caught by the same flag-parity diff from Step 11b, extended to compare the full
catalog: it reported those 8 tools as `None` (absent) rather than merely different.
Registration **order** was also verified identical to HEAD, because a
`# Registered in its historical slot` comment in the original recorded that the
order was deliberate.

### Evidence

- `measure.py`: `input_schema` **18 → 31**; generic descriptions **57 → 44**.
- Flag diff against HEAD: **NONE**; registration order: **IDENTICAL**.
- Args-coverage sweep: **31 specs, 0 with undeclared keys**.
- `make ci-check`: **2342 passed, 91.68% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count 1.
- Recorded surface growth: `mcp.tools.bibles` 6 → 12, `mcp.tools.generation` 11 → 15.

## Step 11d — `artifact`, `state`, `kb`, `validation` declared (2026-09-28)

19 tools. `input_schema` **31 → 50**; generic descriptions **44 → 25**. Two thirds
of the catalogue now delivers its contract.

### A second protocol field

`list_artifacts` rejected a per-call project selection:

```text
project_ref   Extra inputs are not permitted
```

Like `confirmed`, `project_ref` is **not a tool argument**. `MCPServer.call` lifts
it out of `arguments` into the request envelope (`new_envelope(project_ref=...)`)
before dispatch, so it never reaches a handler. Declared once on `ToolArgs`
alongside `confirmed`, with the reason for each in the docstring, and the regression
guard extended to cover both.

That is now **two** protocol fields found this way. Both were found by a failing
call, not by reading `server.py` — which is the argument for making the boundary
strict rather than documenting it.

### The section swap that deleted 18 tools, and the check that caught it

Replacing the `# state` … `# artifact` … `# validation` … `# kb` blocks assumed each
marker's next marker bounded that block. It does not: `# state` is followed by
`# review`, not `# artifact`, so the swap swallowed the whole `# review` section, and
one boundary also cut into `# generation`. Eighteen tools vanished from the registry.

The flag-parity diff reported them as `None` (absent, not different), which is how
it was caught immediately rather than at the next gate. The redo counted
registrations per block *before* replacing — `removed 4 (expected 4)` — and that
check caught a second, subtler error: `# validation` holds only **2** registrations,
because `run_validation` is registered in the `# generation` block at a slot the
original marked "so per-group registration order is unchanged". It is now
`RUN_VALIDATION`, a named spec registered from that block, so both paths share one
declaration.

Final state, all re-measured against HEAD:

- tools: **75**, tool set **IDENTICAL**
- flag diff: **NONE**
- registration order: **IDENTICAL**
- args-coverage sweep: **50 specs, 0 with undeclared keys**

### Evidence

- `measure.py`: `input_schema` **31 → 50**; generic descriptions **44 → 25**.
- `make ci-check`: **2342 passed, 91.70% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count 1.

### Remaining for slice 1

25 tools in 8 groups: `assembly` (7 incl. coverage), `config` (5), `intake` (3),
`operator` (2), `provider` (3), `review` (3), plus `generate_plan` and
`generate_reference_images`.

## Step 11e — slice 1 complete: every tool delivers its contract (2026-09-28)

```text
tools: 75
with input_schema: 75        (was 0)
with output_schema: 0
with generic 'MCP tool: <name>' description: 0    (was 75)
```

**Doc 04 slice 1's falsifiable check is met.** Every tool now publishes a real JSON
Schema for its arguments and a real description, and `extra="forbid"` means an
unknown argument is a typed `VALIDATION_ERROR` rather than a silent no-op.

### What this slice removed, beyond the declarations

Two of the three places the tool list was written are now gone:

1. **`registry._register(...)` and `_tool_contract(...)` deleted** — 46 lines. Every
   tool registers through `registry.register_spec(spec)`, so the older path had no
   callers. The contract, the args model and the handler are one declaration.
2. **`tools/__init__._TOOL_MODULES` is derived, not written.** The mapping used to
   be a hand-maintained `name -> module` dict, and it was the second copy of the
   list. It is now parsed from the `ToolSpec` declarations at first use — parsed
   rather than imported, because importing every tool module would defeat the
   laziness this facade exists to provide. Verified: the derived set equals the
   registered set exactly, plus one explicit non-tool export (`register_all_tools`)
   that the previous mapping also served.

The third copy, the `.pyi` stub, is unchanged; `measure.py`'s
`registered tools missing from the .pyi stub: []` shows it is already in step.

### Three real callers sending arguments no handler reads

`extra="forbid"` found them, exactly as doc 04 predicted:

| Argument | Tool | Verdict |
|---|---|---|
| `phase` | `approve_phase` | The handler is `_ = args` — it approves the *current* phase. Two tests were sending a vestigial `phase`; corrected. |
| `confirmed` | any `confirm=True` tool | Protocol field; now declared once on `ToolArgs`. |
| `project_ref` | any tool | Protocol field consumed by `MCPServer.call` into the envelope; declared once. |

The first is the interesting one: the strict boundary turned an ignored argument
into a refused one, and the fix was in the caller.

### Verification, re-measured at the end against HEAD

- tools: **75**, tool set **IDENTICAL**
- flag diff: **NONE**
- registration order: **IDENTICAL**
- args-coverage sweep: **75 specs, 0 with undeclared keys**
- `get_runtime()` in `mcp`: **3** (all dispatch, from Step 10b)
- cycle count: **1** (only the known `orchestration` root-collapse artifact)

### What this slice does not establish

`output_schema` remains **0**. Doc 04 lists it, and this slice only did
`input_schema`; a tool's *result* shape is still undocumented at the boundary.
That is the remaining half of the doc-04 finding and is deliberately not claimed
here.

### Evidence

- `measure.py`: `input_schema` **50 → 75** (of 75); generic descriptions **25 → 0**.
- `make ci-check`: **2342 passed, 91.74% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count 1.
- Recorded surface growth: `mcp.tools.reference_generation` 14 → 15.

## Step 13 — graph execution lives with the graph (2026-09-28)

Doc 02 slice 3. `studio/_graph_exec.py` (542 lines) and `studio/_resume.py` (99)
became `orchestration/execution.py` and `orchestration/resume.py`.

### The check

```text
cross-package private reach-ins:  8  ->  2
  mcp -> studio._operator_runtime      (1, provably irreducible; see the guard)
  mcp -> studio._persistence           (1, one call site at process start)
```

Doc 02's target was 5 → 2. The measured start was 8, because earlier steps in this
program had already added reach-ins of their own; the three named in the finding
(`services._SERVICES_CTX`, `nodes._run_validators`, `nodes.approval._PHASE_NODES`)
are gone, and the remaining two are the same two the finding did *not* claim.

The finding's own reasoning is what the measurement confirms: *a module that needs
three of another package's private names is not a consumer of that package, it is
part of it.* No port was invented — moving the module removed all three.

### Two cycles the move created, and the inversions that removed them

The move was not mechanical. Putting execution in `orchestration` gave it two
back-edges, both caught by `test_package_acyclicity` (which reads `ast`, so a
function-level import would not have hidden either):

1. **`orchestration.execution -> studio.graph_factory`** — `ensure_graph` built the
   graph, and `graph_factory` imports `orchestration` to wire the nodes. Fixed by
   **injecting the builder**: `execution.register_graph_builder(build_graph)`, called
   once by the composition root at import. `studio` knows about `orchestration`;
   `execution` now knows only that a builder exists. A runtime used without the
   registration raises a message naming the missing call rather than an
   `AttributeError`.
2. **`orchestration.execution -> operations.ports`** — the obvious way to type the
   runtime argument, since `RuntimePort` already declares persist/audit. But
   `operations.ports` imports `orchestration.services`, so extending it closed
   `operations <-> orchestration`. Fixed by making **`GraphHost` self-contained**:
   it declares `services` plus the persist/audit pair itself. The two protocols
   overlap on exactly those three members, which is not enough to justify a cycle.

`GraphHost` also states `create_checkpoint`'s full keyword-only signature rather
than `**kwargs: Any`. A looser protocol would have been satisfied by a method the
module cannot actually call — a protocol that lies about its requirement is worse
than none.

### `studio` keeps what it owns

`graph_factory` still wires services and the checkpointer; `StudioRuntime` still
exposes `run_graph`, `approve_phase`, `run_validation` and `request_revision` as its
public interface. What moved is the execution *policy*, not the composition.

### Re-measured `StudioRuntime` (feeds Step 16)

**393 lines, 29 public methods.** Doc 02 predicted "the 27-method count should drop
by the graph-execution delegates". It did not: the method count went **27 → 29**, and
the six graph-execution methods survive as one-line delegators to
`orchestration.execution`. The line count dropped (516 → 393 for the file).

That is worth stating plainly rather than rounding toward the prediction: this slice
moved *bodies and knowledge*, not *surface*. `StudioRuntime` is still the composition
root's facade over execution, and whether those six delegators belong on it is a real
question — but it is Step 16's, and the honest measurement is that slice 3 did not
shrink the public method count.

### Evidence

- cross-package private reach-ins: **8 → 2**, both pre-existing and both recorded.
- `make ci-check`: **2341 passed, 91.84% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count **1**.
- Recorded surface growth: `orchestration` 15 → 17 public modules (both deliberate).
- Three boundary-law rows deleted because they reached zero — the guard requires
  tightening rather than allowing a stale row.

## Step 14a — profile-change resolution into `config`, and a Step 13 regression (2026-09-28)

Doc 03 slice 4, plus a defect Step 13 introduced that the unit suite could not see.

### Slice 4: the resolve-and-diff half moved to its owner

Seven pure helpers left `mcp/tools/_profile_change.py` for
`config/profile_resolver.py`, beside the resolver they call:

`requested_profile_changes`, `load_profile_stack`, `merge_profile_changes`,
`config_diff`, `resolve_config_pair`, `resolve_config_or_error`, `resolved_raw`
(plus `PROFILE_STACK_KEYS`).

They were pure functions over a profile stack and a resolved configuration — no
runtime, no artifact store, no MCP context — that happened to live in the tool layer
because that is where they were first needed. The handler keeps argument parsing,
proposal persistence and the invalidation call, which already has an owner in
`checkpoints.invalidation`.

### A Step 13 regression that `make ci-check` passed

Step 13 made `orchestration.execution` take its graph builder by injection, and
registered it from `studio/graph_factory.py` at import. **That only fires if
`graph_factory` is imported.**

The unit suite imports it; the integration suite does not. So a runtime whose graph
had never been built raised:

```text
RuntimeError: No graph builder is registered.
```

`make ci-check` was green through it. I found it only because the profile-change
commit's integration run failed — and then confirmed the cause by checking whether
the failure predated my edit, which it did not.

**Fix:** register on a path no caller can avoid — `studio/runtime.py` at import, which
every runtime construction goes through. `graph_factory` is imported lazily, so
hanging a required side effect on it was the error; `runtime` is not.

**Guard:** `tests/unit/orchestration/test_graph_builder_registration.py` asserts in a
*fresh interpreter* that importing `studio.runtime` alone leaves a builder installed.
It deliberately does not import `graph_factory` first — doing so would re-register
the builder and pass even with the runtime-side install removed, which is exactly how
the defect hid. Verified adversarially: deleting the install line fails the guard with
the message naming what did not happen.

A second test is the guard-the-guard: `ensure_graph` must still raise a message
naming `register_graph_builder` when nothing is registered, rather than returning
`None` for every graph run to fail later.

### Evidence

- `make ci-check`: **2343 passed, 91.84% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count 1.
- The regression guard fails when the fix is removed (measured, then restored).

### Remaining for doc 03

Slice 2 (reference generation into `generation`, ~1350 lines across 8 modules) is not
done. `mcp -> generation` is the measurement it moves.

## Step 14b — reference generation moves to its owner (2026-09-28)

Doc 03 slice 2. The seven use-case modules left
`mcp/tools/reference_generation/` (1353 lines) for `generation/reference/`, and the
MCP handler stayed behind.

### The check

```text
mcp -> generation imports:  23  ->  14
```

Doc 03 predicted 20 → "one entry function per tool". The measured start was 23, and
the 14 that remain are the five `generation` *tool* modules (13) plus one registry
import — i.e. the tool surface, which is where they belong. The
`reference_generation` half went from 10 to 0.

### Where the split had to fall

Moving the whole package into `generation` closed `generation <-> mcp`, because
`tool.py` imports `ToolContext`, `ToolArgs` and `_ok`/`_error`. That is a real
boundary, not a technicality: **a package that owns a use case must not depend on the
surface that exposes it.** So:

- `generation/reference/` — retry loop, outcome recording, composite assembly, index
  persistence, entry loading. No MCP context, no response shaping, no tool arguments.
- `mcp/tools/reference_generation/tool.py` — argument validation, response shaping,
  and the `ToolSpec`.

### Two things the move forced, both improvements

1. **`_services` and `_latest_artifact_version` had to leave `mcp`.** The use case
   called `mcp.tools.helpers` for a three-line assertion and a store query. They are
   now `reference_services` and `latest_artifact_version` in the use case's own
   `context.py`. Reaching into the tool layer for them was the use case depending on
   the surface above it.
2. **14 helpers became public.** They were `_`-prefixed while they were `mcp`-internal;
   crossing a package boundary makes them the use case's API, and the boundary-law
   guard correctly refused to let them cross as private symbols. That guard is what
   forced the rename, and it is the right outcome: `mcp` now consumes a *published*
   interface rather than another package's internals.

### Evidence

- `measure.py`: no `mcp -> generation` count is printed directly, so it was measured
  from the AST: **23 → 14**, with the `reference_generation` share going 10 → 0.
- `make ci-check`: **2344 passed, 91.85% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count **1**.
- Surface rows recorded: `generation.reference` (24, 6) added,
  `mcp.tools.reference_generation` lowered to (2, 1), `generation` 15 → 21 modules,
  and the shrunken `mcp`/`mcp.tools` rows lowered to match (39 → 33, 33 → 27).

### What this does not establish

The test split doc 03 also predicted — "a use-case test that constructs no MCP context
and a thin handler test" — is **not** done. `tests/unit/mcp/tools/test_reference_generation.py`
(719 lines) still drives the use case through `call_tool`, and its helper tests import
the use-case package directly. The production split is real; the test split is not
claimed.

## Step 15a — the lazy-import guard, and the two smallest packages hoisted (2026-09-28)

Doc 05's finding is that **96% of function-level imports protect no cycle** — 275 of
287. The number alone was not actionable, because nothing could distinguish a
load-bearing lazy import from a habitual one. So this slice builds the discriminator
first, then uses it.

### `tests/unit/architecture/test_lazy_imports.py`

A function-level `film_pipeline` import is allowed only if:

1. **It is cycle-required** — the target can already reach the source through eager
   edges, so hoisting would close a cycle. Computed by **importing `measure.py`'s own
   `collect_imports`/`reaches`** rather than reimplementing the walk: a guard that
   disagrees with the measurement it grades is worse than no guard, and the drift
   would be invisible.
2. **It carries `# lazy: <reason>`** on the import's line or the line above (the
   latter for multi-line `from x import (...)`).

`HOISTABLE_CEILING` counts the imports that are *neither* — the unexplained ones. It
may only fall. Counting the unexplained rather than all lazy imports is deliberate: a
guard that failed on all 275 could not be committed until the migration finished, so
it would not exist during the migration, which is exactly when it is needed.

Adversarially verified: raising the ceiling above the real count fails with the count
and a per-package breakdown.

A second test requires the reason to be a *reason* — `# lazy: defers langgraph`, not a
bare `# lazy:`. It is cheap to satisfy badly and the guard's job is to make the
sentence exist. A third is the guard-the-guard: a broken collector reporting zero
would otherwise pass silently.

### `storage` 3 → 0, `governance` 7 → 0

Both hoists were the same shape: a function-level import of `schemas.base`,
`schemas.artifact` or `schemas.matrix_patch` where the module already imported sibling
`schemas` names at module level, so no cycle was ever at risk.

One real cleanup fell out: `storage/matrix_projection.py` had a `TYPE_CHECKING` block
importing `MatrixPatch` **and** a function-level import of the same name. The
`TYPE_CHECKING` block proved the annotation position was safe; the runtime use at
`MatrixPatch(**data)` was equally safe, so both collapsed into one module-level
import and the now-empty `if TYPE_CHECKING:` was deleted with its `TYPE_CHECKING`
import.

### Evidence

- Guard: **277 unexplained → 266**; `storage` and `governance` at **0**.
- `make ci-check`: **2347 passed, 91.85% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count 1.

### Remaining for doc 05

`mcp` (108), `orchestration` (91), `generation` (25), `post` (20), `studio` (15),
`cli` (7). These are larger and several will need genuine `# lazy:` reasons rather
than hoists — the guard is what will force those reasons to be written down.

## Step 15b — `post` and `cli`, and the two hoists that had to be refused (2026-09-28)

`post` 20 → 5, `cli` 7 → 1, total unexplained **266 → 242**.

### Two hoists that were wrong, and how each was caught

Doc 05 says hoisting is not behaviour-preserving in general — "module import order can
matter where a module has [side effects]". Both cases here were real, and neither was
the side-effect kind:

**1. `post/subtitle_agent.py` — hoisting shadowed a name.**
The function imported `schemas.SubtitleCue`, but the module defines its *own*
`SubtitleCue` dataclass, which is what the cue conversion actually builds. Hoisting
put the schema's class in module scope and silently changed the type. Caught by
`ruff` (`F811 Redefinition of unused SubtitleCue`) and then by `mypy`
(`List[SubtitleCue]` vs `List[schemas.subtitle.SubtitleCue]`). Reverted, and the
import now carries a three-line `# lazy:` reason explaining the hazard.

Worth noting: the original lazy import was **already wrong** — it imported
`SubtitleCue` and never used it, while building the local class instead. The lazy
import was hiding an unused import and a latent type mismatch. The hoist did not
create the problem; it revealed it.

**2. `cli/run.py` — hoisting broke a patch point.**
`configure_logging` was imported inside `main`, so tests patching
`film_pipeline.studio.logging_setup.configure_logging` still intercepted the call. A
module-level binding is resolved at import time, *before* the patch, so the mock was
never called: `Expected 'mock' to be called once. Called 0 times.` Reverted with a
`# lazy:` reason naming the patch point.

This one is a genuine constraint on the hoist, not a test that needs updating: moving
a call target to module scope makes it unpatchable at its source, and that is a
property of the code, not of the test.

### The guard learned to read a written reason

The first `# lazy:` reason in `subtitle_agent.py` spans three comment lines. The
guard's fixed two-line lookback rejected it — a guard that fails a reason for being
*too well explained* is the wrong shape. It now walks the contiguous comment block
directly above the import and stops at the first non-comment line, verified both ways:
a reason separated from the import by code is not accepted, and a multi-line block is.

### Evidence

- Guard: **266 unexplained → 242**; `post` **20 → 5**, `cli` **7 → 1**.
- `make ci-check`: **2347 passed, 91.85% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count 1.
- `post`'s remaining 5 are one annotated import block (3 entries) and two others; the
  count is 5 rather than 0 because the annotated lines are still lazy, which is the
  intent.

### Remaining for doc 05

`mcp` (108), `orchestration` (89), `generation` (25), `studio` (15), `post` (5).
`mcp` and `orchestration` are the bulk and will need per-module work.

## Step 15c — `generation.reference`, and the patchability constraint (2026-09-28)

`generation` 25 → 5; total unexplained **242 → 222**.

### The finding: a hoist can make a call target unpatchable

This is the third instance of the same constraint, and after three it is a rule rather
than an incident. **Moving a call target to module scope binds it before any test can
patch it at its source.** A test that patches
`generation.frame_reviewer.should_review_frame` intercepts the call only while the
caller looks the name up at call time. Hoist the import and the caller holds a direct
reference, so the mock is bypassed:

```text
AssertionError: Expected 'should_review_frame' to have been called once. Called 0 times.
```

Five imports in `generation.reference` are load-bearing for this reason and now carry
`# lazy:` reasons naming the patch target:

| Import | Patched at |
|---|---|
| `should_review_frame`, `review_frame` | `generation.frame_reviewer.*` |
| `run_heuristic_checks` | `generation.frame_heuristics.*` |
| `write_frame_sidecar` | `generation.frame_sidecar.*` |
| `build_character_identity_sheet` and four siblings | `generation.compositor.build_*` |
| `review_composite_sheet` | `generation.sheet_reviewer.*` |

Doc 05 predicted that hoisting "does not establish that hoisting changes no
behaviour". It is worth recording *which* behaviour: not import-order side effects in
this tree, but the loss of a seam the test suite depends on. Where that seam is
deliberate — a test that exists to prove the call happens — the lazy import is correct
and the reason belongs in the code, which is what the guard now requires.

### Bisecting six files to find one

Six files were hoisted together and the reference-generation suite went red. Reverting
them one at a time identified `retry_loop.py` immediately, and the same method found
`outcomes.py`'s sidecar import after that. The lesson is about batch size, not about
the technique: six files in one pass meant six reverts to localise a failure that one
file at a time would have named directly. Later hoists in this step should be
smaller.

One placement error also surfaced: the sidecar import was first inserted into
`_register_generated_entry` instead of `_write_frame_sidecar_safely`, where the call
actually is. `mypy`'s `Name "write_frame_sidecar" is not defined` found it — a
name-defined error is what a mis-placed import looks like, and it is why running mypy
after every hoist rather than at the end of the batch matters.

### Evidence

- Guard: **242 unexplained → 222**; `generation` **25 → 5** (all five annotated).
- `make ci-check`: **2347 passed, 91.85% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count 1.

### Remaining for doc 05

`mcp` (108), `orchestration` (89), `studio` (15), `post` (5), `generation` (5). `mcp`
and `orchestration` are 89% of what is left and will need per-module commits rather
than package-level batches.

## Step 15d — `studio` to zero (2026-09-28)

`studio` 15 → 0; total unexplained **222 → 207**.

Ten of the fifteen hoisted without incident. Five are load-bearing and now carry
reasons, all for the same two causes:

**Patch points (4).** `studio/health.py` is the densest case in the tree — three of
its four checks call a function the test suite patches at its source:

| Import | Patched at | Symptom if hoisted |
|---|---|---|
| `get_runtime` | `studio.health.get_runtime` | readiness reports `True` when the fake has no providers |
| `validate_environment` | `studio.bootstrap.validate_environment` | bootstrap check passes against a missing profiles dir |
| `kb_manifest_path` | `kb.paths.kb_manifest_path` | KB check passes with no manifest |

**Real cycles (2, in `studio/runtime.py` and `studio/_operator_runtime.py`).**
`graph_factory` imports `orchestration`, which is the cycle Step 13 broke; and
`_provider_factory` imports this package. Both are stated rather than silently lazy.

`smoke.py`'s five imports were the one judgement call. They sat inside `try/except`
blocks, which can *look* like deliberate failure isolation, but each check already
catches its own exceptions — the `try` supplies that, not the import's position. And
no test patches them. Hoisted.

### The pattern, now measured four times

Across Steps 15b–15d the same rule held every time: **a hoist is safe unless the name
is looked up by a test's patch target.** That is a mechanical test — `grep` the dotted
name across `tests/` before hoisting — and it would have saved the bisect in 15c. It
is recorded here as the procedure for the remaining work rather than rediscovered per
package.

### Evidence

- Guard: **222 unexplained → 207**; `studio` **15 → 0**.
- `make ci-check`: **2347 passed, 91.86% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count 1.

### Remaining for doc 05

`mcp` (108), `orchestration` (89), `post` (5), `generation` (5). `mcp` and
`orchestration` are 95% of what is left; both need per-module commits at the batch
size Step 15c's bisect recommended.

## Step 15e — `generation` to zero (2026-09-28)

`generation` 25 → 0; total unexplained **207 → 202**. Five packages are now fully
hoisted or explained: `storage`, `governance`, `cli`, `studio`, `generation`.

### The grep-first procedure, which this slice should have used from the start

Step 15d concluded that a hoist is safe unless a test patches the dotted name. This
slice applied it — `grep` for `patch.*<name>` and `setattr.*<name>` across `tests/`
before touching anything — and no test broke. The five patch points that remain lazy
in `generation.reference` were identified that way rather than by bisect.

### A tooling failure worth recording

Three separate edits were lost or misapplied in this slice, all from scripted
string replacement rather than from the change itself:

- An insert landed *inside* a function body instead of at module level, twice.
- `git checkout HEAD -- <file>` reverted a hoist that had already succeeded, because
  the file was committed in a previous step and the checkout looked like a no-op fix.

The recovery was the same each time and is the durable lesson: after every scripted
edit, run `grep -n "^from film_pipeline"` on the file and `mypy` on the package, and
confirm `git status` shows the file as modified. A hoist that is not visible in
`git status` did not happen. Two of the three were caught by exactly that check
rather than by a later gate.

### Evidence

- Guard: **207 unexplained → 202**; `generation` **25 → 0**.
- `make ci-check`: **2347 passed, 91.87% coverage**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count 1.

### Remaining for doc 05

`mcp` (108), `orchestration` (89), `post` (5). `post`'s five are one annotated import
block. `mcp` and `orchestration` are 97% of what is left, and both need per-module
commits — Step 15c's bisect and Step 15e's lost-edit failures both argue for smaller
batches, and these two packages are where the remaining risk is.

## Step 16 — `StudioRuntime` re-measured, and the split decided against (2026-09-28)

The measurement and the decision are in
[`08-studioruntime-remeasured.md`](08-studioruntime-remeasured.md). Summary:

| | Before this program | Now |
|---|---:|---:|
| Lines | 516 | **393** |
| Public methods | 27 | **29** |
| Concerns | 5 | **9** |
| Pure delegators | not measured | **13 of 29** |

**The method count went the wrong way, and that is the finding.** Doc 02 predicted
Step 13's graph-execution move would drop it by the delegates; the delegates survived
as one-line forwarders, so lines fell 24% while the surface *grew* by two. Reporting
only the line count would have made this look like a clean win.

The measurement also corrected a claim I had been repeating from memory: the concern
count is **9**, not 5, and **13 of 29 methods are single-`return` delegators** — five
to `orchestration.execution`, one to `_persistence`, and seven to the runtime's own
attributes. I stated 11 and then 13 in the same draft, and 6 rather than 5 for the
`orchestration.execution` figure; both were wrong until the AST pass re-measured them.
That is the same failure `AGENTS.md` records twice, and it is why the document's every
number comes from a re-runnable command rather than from the prose above it.

### The decision: do not split it in this program

Three reasons, recorded in full in the document: it is the composition root and
`03-target-architecture.md` §4.6 gives it that role (a split would move the wiring, not
remove it); the delegators — not the size — are the actual symptom, and `AGENTS.md`
already names the repair as moving the concern to its owner *per caller*, which is a
different and smaller job; and the small concerns (audit, operator comments: 2 methods
each) would each need a collaborator and a wiring line to remove two forwarders.

The document names what a future split would look like and ranks it — provider
registry + health (10 methods) first, taking 29 → 19 methods and 9 → 7 concerns — and
is explicit that **this is not done**.

### Evidence

- `StudioRuntime`: **393 lines, 29 public methods, 9 concerns, 13 delegators**, measured
  at `485a7cc` from the class's own section comments plus an AST pass.
- This step changes documentation only; `make ci-check`, `mypy src tests` and
  `enola check` are unchanged and green at that commit.

---

# Final state at `af50e07` (2026-09-28, goal round 40 of 40)

## The 16-slice sequence, step by step

| Step | Status | Evidence |
|---:|---|---|
| 0 | **done** | `enola check` exits 0 on the committed tree |
| 1 | **done** | module-level SCCs 2 → 1 |
| 2 | **done** | dead functions, `gemini_client.py`, cost residue deleted |
| 3 | **done** | one `_ORCH_NS`; `providers/vendor_endpoints.py` is the single definition site |
| 4 | **done** | step 4 committed red: the two defect-pinning tests failed first |
| 5 | **done** | `apply_node_update` + `channel_reducers()` derive the merge from the state |
| 6 | **done** | one QC implementation; `documentation/qc-single-implementation.md` records the decision |
| 7 | **done** | committed red, as required |
| 8 | **done** | CLI routes through `MCPServer.call`; no `_RUNTIME` writes outside `studio` |
| 9 | **done** | coverage ≥ 90% with no new tests |
| 10 | **done** | `get_runtime()` in `mcp`: **61 → 3** (all three are dispatch itself) |
| 11 | **done** | `input_schema`: **0 → 75 of 75**; generic descriptions **75 → 0** |
| 12 | **done** | `MCPServer.active_project_id` deleted |
| 13 | **done** | cross-package private reach-ins: **8 → 2** (both pre-existing, both recorded) |
| 14 | **done** | `mcp → generation` imports: **23 → 14**; profile change into `config` |
| 15 | **partial** | unexplained lazy imports **277 → 202**; `storage`, `governance`, `cli`, `studio`, `generation` at 0 |
| 16 | **done** | re-measured in `08-studioruntime-remeasured.md`; split decided against, with reasons |

## What is not done

**Step 15 (partial).** 202 function-level imports are still neither cycle-required nor
annotated:

| Package | Remaining |
|---|---:|
| `mcp` | 108 |
| `orchestration` | 89 |
| `post` | 5 |

`post`'s five are a single annotated import block already carrying a reason; the
guard's counts them as lazy, which is the intent, so the actionable remainder is
**197 across `mcp` and `orchestration`**. The guard
(`tests/unit/architecture/test_lazy_imports.py`) ratchets, so this cannot silently grow.

The procedure that works, established over Steps 15b–15e: **grep the dotted name across
`tests/` for a `patch`/`setattr` target before hoisting.** If a test patches it, the
lazy import is load-bearing and needs a `# lazy:` reason; otherwise hoist. Batch by
module, not by package — Step 15c hoisted six files at once and needed six reverts to
localise one failure.

**The five docs-only slices from doc 06** are untouched: **6.3** (where text transports
live), **6.6** (`governance.validators` → `governance/gates`; fold `MVP_VALIDATORS`
into `validation/registry.py`), **6.7** (`NO_ACTIVE_PROJECT` and text-only builders out
of `filmspec`), **6.8** (AGENTS.md package table missing `generation`, `constraints`,
`cli`), **6.11** (two import spellings for the core enums — recorded as low priority,
no sweep).

**Doc 03 slice 2's test split.** The production split landed in Step 14b, but
`tests/unit/mcp/tools/test_reference_generation.py` (719 lines) still drives the use
case through `call_tool`. Doc 03 also predicted "a use-case test that constructs no MCP
context and a thin handler test"; that half is not done and is not claimed.

## Gates at `af50e07`

- `make ci-check`: **2347 passed, 8 skipped, 1 xfailed**, 91.87% coverage, product gate PASS
- `mypy src tests`: clean (514 files)
- `ruff check` / `ruff format --check`: clean
- `enola check`: **exit 0**, cycle count **1** (only the known `orchestration` root-collapse artifact)
- 28 commits on `improve-modular` since `2450616`

## Step 15f — `post` to zero, and a guard rule made explicit (2026-09-28)

`post` 5 → 0; total unexplained **202 → 197**. Six packages are now fully hoisted or
explained: `storage`, `governance`, `cli`, `studio`, `generation`, `post`.

### The one substantive finding: the reason must be on the import's own line

`post/subtitle_agent.py` has three imports kept together on purpose — the first
imports the schema's `SubtitleCue`, which this module shadows with its own dataclass,
and the other two were left beside it. I first annotated the block once, above the
group. The guard rejected the second and third, and the reason is worth stating
because it is a design decision rather than a bug:

**`_has_reason` scans the contiguous comment block directly above each import, so a
comment placed above import A does not cover imports B and C below it.** That is
deliberate — it stops a reason being inherited from an unrelated comment higher up the
function — but it means a shared reason must be repeated or carried inline.

The fix was to put the marker on each import's own line:

```python
from film_pipeline.schemas import SubtitleArtifact, SubtitleCue  # lazy: shadows
from film_pipeline.schemas.artifact import (  # lazy: stays with the above
    ArtifactMetadata,
    ArtifactRef,
)
```

Multi-line `from x import (...)` forms are handled because the marker sits on the
opening line and the guard reads `lineno`, not the statement's last line.

This is the first case in the migration where the guard's rule had to be *worked with*
rather than satisfied by moving an import, and it is the right trade: the alternative —
letting one comment excuse an arbitrary run of imports — would make the reasons
decorative.

### Evidence

- Guard: **202 unexplained → 197**; `post` **5 → 0**.
- `make ci-check`: **2347 passed**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count **1**.

### Remaining for doc 05

`mcp` (108), `orchestration` (89) — 197 of 197. Both are now the whole remainder and
need per-module commits.

## Step 15g — `orchestration`, first four modules (2026-09-28)

`orchestration` 89 → 56; total unexplained **197 → 164**.

The grep-first rule from Step 15d paid off directly here: of the 35 imports across
`nodes/visual.py`, `subgraphs/qc.py` and `nodes/qc.py`, exactly two matched a patch
target, and **both turned out to be false positives**:

- `ScriptStructureValidator` — `tests/unit/mcp/tools/test_validation.py` patches
  `ScriptStructureValidator.run`, i.e. a *method on the class*. Hoisting the import
  changes nothing about that; the class object is the same one either way.
- `_save_artifact` — patched as `wrapup_module._save_artifact`, which resolves to
  `orchestration/nodes/wrapup.py`. The name also appears in `subgraphs/qc.py`, but
  that is a different module object with its own binding; patching one does not affect
  the other.

So all 35 hoisted. 13 of the 35 were validator imports in the two QC modules, which is
the shape doc 02 described: the QC subgraph and the sequential QC node each pulled
their validators in at call time.

### A guard threshold that had to move, honestly

`test_the_guard_has_something_to_check` asserted `len(lazy) > 200`. Total
function-level imports fell to exactly 200 as the migration proceeded, so the *sanity
check* started failing — the guard's own "is the collector reading anything" probe had
become a work target.

This is the distinction the goal's constraint is about: the rule is **never lower a
count to make a finding disappear**, and this is the opposite case. The threshold exists
to catch a collector that parses nothing, not to assert the migration is unfinished, so
it moves down alongside `HOISTABLE_CEILING` and is now 150. The comment on it says so,
because the next reader will otherwise see a threshold that has been lowered and
suspect the worst. `HOISTABLE_CEILING` itself **fell** (197 → 164), which is the real
measurement.

### Evidence

- Guard: **197 unexplained → 164**; `orchestration` **89 → 56**, `visual` and both QC
  modules at 0.
- `make ci-check`: **2347 passed**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count **1**.

### Remaining for doc 05

`mcp` (108), `orchestration` (56): `_repair_loop` 9, `approval` 8, `execution` 7,
`_agent_artifacts` 5, `prep` 5, `_generation_batch_planning` 4, and ten modules with
1–3 each.

## Step 15h — `_repair_loop`, `approval`, `execution` (2026-09-28)

`orchestration` 56 → 36; total unexplained **164 → 144**.

19 imports across three modules, all hoisted; the grep-first pass found no patch
targets at all in this batch. One import stayed lazy for a **cycle** reason rather
than a patch reason, and it is worth naming because it is the module that documents
this exact hazard:

```python
# _repair_loop.py, inside _LazyQcPhaseNode.resolve
# lazy: importing subgraphs.qc at module level is the partially
# initialized module this `_LazyQcPhaseNode` exists to avoid.
from film_pipeline.orchestration.subgraphs.qc import qc_phase_node
```

Step 6 built `_LazyQcPhaseNode` precisely because `_PHASE_NODES` is constructed at
module import, and resolving the QC row there imported `subgraphs.qc` while `nodes`
was still initialising — a real `ImportError: partially initialized module`. That
import therefore *cannot* hoist, and the reason now sits on it.

### A scripted-edit flaw that recurred, and the fix

My bulk hoist script mishandled a **two-space-indented** `if TYPE_CHECKING:` block: it
treated the guarded imports as function-level ones, stripped them, and re-emitted them
at column zero. `mypy` reported `Expected an indented block`, and the diff showed the
`TYPE_CHECKING` body emptied — the guard would have been left with no contents.

`_repair_loop.py` was reverted and redone by hand. This is the third scripted-edit
failure in Step 15 and the same root cause each time: **a regex that keys on
indentation cannot tell a function body from a `TYPE_CHECKING` block.** The durable
rule, now applied for the remaining files: hoist by naming the exact import statements,
not by matching leading whitespace.

For this module the right end state was better than a lift-and-shift anyway — the
`TYPE_CHECKING` block already proved those three names were import-safe, so promoting
them to real module-level imports and deleting the now-redundant guard is the honest
change.

### Evidence

- Guard: **164 unexplained → 144**; `orchestration` **56 → 36**.
- `make ci-check`: **2347 passed**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count **1**.

### Remaining for doc 05

`mcp` (108), `orchestration` (36): `_agent_artifacts` 5, `prep` 5,
`_generation_batch_planning` 4, `_generation_prompts` 3, and eleven modules with 1–2
each.

## Step 15i — `orchestration` to zero, and a better tool for the job (2026-09-28)

`orchestration` 36 → **0**; total unexplained **144 → 108**. Seven packages are now
clean: `storage`, `governance`, `cli`, `studio`, `generation`, `post`, `orchestration`.
Only `mcp` is left.

### The regex hoister was replaced, not patched

Step 15h recorded the third scripted-edit failure with the same root cause: *a regex
keyed on indentation cannot tell a function body from a `TYPE_CHECKING` block.* Three
attempts on `_repair_loop.py` failed that way.

This slice wrote a replacement that cannot make that mistake. It walks the AST for
`ImportFrom` nodes **inside `FunctionDef` bodies** instead of matching leading
whitespace. A `TYPE_CHECKING` guard is an `if` statement at module level, so its
children are never candidates and are never touched. It also dedupes multi-name
imports, drops the blank lines left behind, and re-emits each unique statement once.

Twelve files hoisted in one pass with no misplacement — the failure mode that had cost
three attempts disappeared with the regex. That is the actual lesson of Steps 15c/15h:
the *technique* was wrong, and each retry of a bad technique read as bad luck.

### The last `orchestration` import

`resume.py` kept `remove_issues_by_code` lazy. Unlike the others it was not a patch
point or a cycle; `state_schema` simply does not import `resume`, so it hoisted. It was
found only after the first pass because `measure.py` counts it under `resume`, not under
the `nodes/` files that dominated the inventory.

### The sanity threshold moved again, with its history recorded

`len(lazy) > 150` began failing at 143 real imports. It is now 100, and its docstring
records that it has moved **200 → 150 → 100** as packages were hoisted, with the reason
each time. The distinction the goal requires is explicit in the code:
`HOISTABLE_CEILING` measures the work and only falls when imports are actually hoisted
(**144 → 108** here); the sanity threshold measures that the collector parses anything
at all, and tracks the tree's shrinking size so it does not become a work target.

### Evidence

- Guard: **144 unexplained → 108**; `orchestration` **36 → 0**.
- `make ci-check`: **2347 passed**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count **1**.

### Remaining for doc 05

`mcp` (108) — the whole remainder, and the largest single package.

## Step 15j — `mcp` to zero, and Step 15 complete (2026-09-28)

```text
unexplained lazy imports:  277  ->  0
```

**Doc 05's falsifiable check is met, tree-wide.** `HOISTABLE_CEILING` is now **0**.

### What remains, and why

39 function-level imports survive, every one either cycle-required or carrying a
written `# lazy:` reason. The reasons fall into three groups:

| Reason | Count | Example |
|---|---:|---|
| A test patches the name at its source | 9 | `kb_manifest_path`, `configure_logging`, `get_runtime`, `write_frame_sidecar` |
| Hoisting would close a cycle | most of the rest | `qc_phase_node` in `_LazyQcPhaseNode`, `graph_factory` in `runtime` |
| Hoisting would shadow a same-named class | 1 | `schemas.SubtitleCue` in `post/subtitle_agent.py` |

The **patch-point** group is the one this step discovered rather than inherited. It is
9 imports across `mcp` and `studio`, and every one was found by a *failing test*, not by
reading code — including two (`kb_manifest_path` for `kb_search`/`kb_get_item`, and
`configure_logging` for `mcp.main`) that the grep-first pass itself missed and only the
suite caught. That is worth recording plainly: **the grep is a good filter and not a
proof.** It found the obvious `patch("module.name")` forms; it missed patches whose
string is built differently or whose target is reached through a second module.

### The scale of what Step 15 actually moved

| Package | Start | End |
|---|---:|---:|
| `mcp` | 108 | **0** |
| `orchestration` | 89 | **0** |
| `generation` | 25 | **0** |
| `post` | 20 | **0** |
| `studio` | 15 | **0** |
| `governance` | 7 | **0** |
| `cli` | 7 | **0** |
| `storage` | 3 | **0** |
| **total unexplained** | **277** | **0** |

### The durable lessons

1. **Grep for the patch target before hoisting.** If a test patches the dotted name,
   the lazy import is load-bearing. It is a filter, not a proof — the suite is the proof.
2. **Batch by module, not by package.** Step 15c hoisted six files at once and needed
   six reverts to localise one failure.
3. **Never hoist with a regex keyed on indentation.** It cannot distinguish a function
   body from a `TYPE_CHECKING` block; that cost three attempts on one file. The
   AST-based hoister replaced it and hoisted twelve files in one pass.
4. **Confirm the edit landed.** `grep` the file and check `git status` after every
   scripted edit — several were silently lost, including one reverted by my own
   `git checkout` on an already-committed hoist.

### Evidence

- Guard: **277 unexplained → 0**; `HOISTABLE_CEILING` = **0**.
- `make ci-check`: **2347 passed**, product gate PASS.
- `mypy src tests` clean; `ruff` clean; `enola check` exit 0, cycle count **1**.

### Remaining in the program

The five docs-only slices from doc 06 (6.3, 6.6, 6.7, 6.8, 6.11) and doc 03 slice 2's
test split. Step 16 is done
([`08-studioruntime-remeasured.md`](08-studioruntime-remeasured.md)).
