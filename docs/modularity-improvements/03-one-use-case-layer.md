# 03 — One use-case layer: retire the orphaned half of `operations`, move workflows out of `mcp`

**Priority: 2 (simplicity; prerequisite for any `StudioRuntime` split).** Size: L, in
independent slices.

## Finding A — `operations` lost its client when the TUI was removed

`operations` was built as the operator surface for the TUI
(`documentation/audit-findings.md` #8: "TUI bypasses the MCP contract through an
internal `OperatorService`"). The TUI is gone (`docs/plans/remove-tui-support.md`). The
layer it served mostly is not:

| Surface | Consumers outside `operations/` in `src` |
|---|---:|
| `DashboardSummary`, `ReviewWorkspace`, `ValidationWorkspace`, `GenerationWorkspace`, `AuditEvent`, `ProjectListItem`, `MutationResult` | **0** each |
| `OperatorService` public methods | **6 of 31** used, all by `mcp` |

The six in use: `register_profile_providers`, `missing_profile_credentials`,
`get_checkpoint`, `rollback_artifact`, `rollback_to_checkpoint`,
`preview_generation_prompts`. The other 25 — `get_dashboard`, `get_review_workspace`,
`approve_generation_spend`, `list_projects`, … — have no caller in `src` outside
`operations`; their consumers are `tests/unit/operations/test_operator_service.py`
(698 lines) and
`tests/integration/test_operator_path_divergence.py` (660 lines), a test that exists
because there *were* two operator paths.

The cost is not only dead code. This orphaned layer is what keeps two structural
debts alive:

- **The last irreducible reach-in** `mcp -> studio._operator_runtime` exists to build a
  wired `OperatorService` (AGENT-27). With 6 methods left, the wiring question shrinks
  to "which runtime/provider objects do these 6 need", which `ToolContext` (doc 01)
  already carries.
- **`RuntimePort`** declares "every member below is called by at least one operator use
  case" ([ports.py:39](../../src/film_pipeline/operations/ports.py)) — true, but most of
  those use cases have no production caller. `ArtifactStorePort = ArtifactStore` and
  `ServicesPort = GraphServices` are aliases, not ports.

## Finding B — the real use cases live in the transport package

`mcp` is the largest package (7,144 lines) and the one with the widest fan-out
(**16 packages** once function-level imports are counted; 8 visible at module level).
Most of that is not transport. Three workflows, ~2,650 lines, are domain orchestration
written as MCP handlers:

| Workflow | Lines | What it does | Natural owner |
|---|---:|---|---|
| `mcp/tools/reference_generation/` | 1,324 | bounded retry loop, provider submit, frame/sheet review, composite sheets, reference index | `generation` (already owns compositor, reviewers, `delta_regenerator`, ledger) |
| `mcp/tools/bibles/` | 857 | run a roster agent, validate, save a visual-dev candidate, publish its ref | an `agents`-level `run_agent` shared with the graph (see below) |
| `mcp/tools/_profile_change.py` | 469 | validate stack, resolve & diff config, persist proposal/approval, invalidate downstream | `config` + `checkpoints` (invalidation) |

`bibles/_shared._run_bible_agent` describes itself as *"the MCP counterpart of
`orchestration.nodes._agent`"* and records that its predecessor was "a second agent
lifecycle" that could never have produced a bible on the real-model path. The fix
routed both through `PromptRunner`, but the two entry points remain.

Consequence: a use case reachable only as an MCP handler can only be tested through
the MCP calling convention (the 30 test files in doc 01), and cannot be reused by the
graph or the CLI without going through `mcp.tools`.

## Recommendation

The target is one sentence: **MCP handlers parse arguments, call one use case, and shape
the response; use cases live with the concern they change.** No new package is needed.

### Slice 1 — delete the orphaned operator surface

Delete the 7 view models and the 25 `OperatorService` methods with no `src` caller, with
their tests (re-check each with `grep` first — some may be called by the six survivors).
Keep the six used operations as plain functions in the modules that already hold them
(`_checkpoint_ops.py`, `_generation_ops.py`, a profile-credentials function next to
`config.profile_resolver`). `OperatorService` and `studio._operator_runtime` go away
when their last method moves — which retires the irreducible reach-in instead of
freezing it.

Decide `test_operator_path_divergence.py` explicitly: keep the graph-vs-MCP cases, drop
the operator-service cases.

**Falsifiable check:** after deletion, `make ci-check` and the 90% gate stay green
without adding tests — evidence the deleted code was covered only by its own tests.
If coverage drops below 90%, that is the measurement that some of it was load-bearing.

### Slice 2 — move reference generation into `generation`

Move the retry loop, outcome recording, and composite assembly into
`generation/reference/` (or similar), taking `GraphServices` and `ArtifactStore`
explicitly. The MCP handler keeps argument parsing and response shaping.

**Falsifiable check:** `mcp -> generation` import count (20 today) falls to the one
entry function per tool; `tests/unit/mcp/tools/test_reference_generation.py` (682 lines)
splits into a use-case test that constructs no MCP context and a thin handler test.

### Slice 3 — one agent-run entry point

Compare `orchestration.nodes._agent._run_agent` and `mcp.tools.bibles._shared._run_bible_agent`
line by line. The shared part (roster contract -> template -> `PromptRunner` -> mock ->
`execute()` parse) belongs in `agents` as a public function over `GraphServices`; the
graph node keeps state bookkeeping, the bible tool keeps subject-id stamping.

**Measure first:** this slice is only worth doing if the shared part is more than the
two already-shared calls. Record the diff before deciding.

### Slice 4 — profile change into `config`

The resolve-and-diff half is pure and belongs beside `config.profile_resolver`. The
invalidation half already has an owner (`checkpoints` invalidation reports). The
handler keeps the proposal/approval artifact persistence only if nothing else writes
those artifacts.

## Ordering

Slice 1 first: it is pure deletion, shrinks `RuntimePort`, and removes the reason for
the `mcp -> studio._operator_runtime` reach-in. Slices 2–4 are independent of each other
and should follow doc 01's `ToolContext`, so the moved use cases take explicit
dependencies instead of learning `tools_pkg.get_runtime()`.

## What this does not establish

That the 25 unused methods have no *intended* future client. If an HTTP or web operator
surface is planned, it should be written against MCP (the product boundary), not
against a resurrected in-process service — which is the exact divergence
`audit-findings.md` #8 recorded.
