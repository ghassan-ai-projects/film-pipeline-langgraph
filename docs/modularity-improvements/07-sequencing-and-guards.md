# 07 — Sequencing, guards, and what not to do

Each row is one commit with green `make ci-check`, `uv run mypy src tests`, and an
Enola exit code read **without a pipe**. The "check" column is the measurement that
proves the slice did what it says; record it in the progress ledger.

## Order

| Step | Slice | Doc | Check |
|---:|---|---|---|
| 0 | Regenerate the Enola baseline with the installed version; ignore `.pre-commit-cache/**` | 06 §6.9 | `enola check` exits 0 on the committed tree |
| 1 | Delete the `nodes.approval` re-export shim; point its 2 consumers at `_repair_loop` | 05 B | module-level SCCs: 2 -> 1 |
| 2 | Delete verified-dead functions, `generation/gemini_client.py`, cost residue | 06 §6.4, 6.5, 6.10 | suite green with no test edits beyond deleted-code tests |
| 3 | One `_ORCH_NS`; one vendor-endpoint module | 06 §6.1, 6.2 | `measure.py` duplicate-literal counts -> 1 |
| 4 | Test first: `_PHASE_NODES[p]` is the graph's node for every phase; reducer parity test | 02 | both fail on `qc` / 4 channels, before any fix |
| 5 | Derive `run_phase_node`'s reducers from `StudioGraphState`; move to `orchestration` as `apply_node_update` | 02 slice 1 | reducer parity test passes |
| 6 | Decide the canonical QC; make `_PHASE_NODES["qc"]` that object | 02 slice 2 | identity test passes; decision recorded in `documentation/` |
| 7 | Test first: CLI driver gets `NO_ACTIVE_PROJECT` / `CONFIRMATION_REQUIRED` | 01 | both fail today (see `probe_dispatch_paths.py`) |
| 8 | CLI through `MCPServer.call`; public runtime installer | 01 slice 1 | step 7 tests pass; no `_RUNTIME` writes outside `studio` |
| 9 | Delete the orphaned operator surface | 03 slice 1 | coverage ≥ 90% without new tests |
| 10 | `ToolContext` handler signature, one tool group per commit | 01 slice 2 | `get_runtime()` in `mcp`: 61 -> 1 at the end |
| 11 | Typed args + description per tool, same groups | 04 slice 1 | tools with `input_schema`: 0 -> 75 |
| 12 | One owner for the active project | 01 slice 3 | `MCPServer.active_project_id` deleted |
| 13 | Move graph execution into `orchestration` | 02 slice 3 | cross-package private-symbol imports: 5 -> 2 |
| 14 | Reference generation into `generation`; profile change into `config` | 03 slices 2, 4 | `mcp -> generation` imports: 20 -> one per tool |
| 15 | Hoist lazy imports, package by package; add the lazy-import guard | 05 | hoistable count per package -> 0; import time unchanged |
| 16 | **Re-measure `StudioRuntime`**, then decide whether to split it | `08` | public methods and concerns, per `AGENTS.md`'s table |

Why this order:

- **0 first** because every later "Enola passed" line is otherwise unverifiable.
- **1–3 are deletions** with no design decision; they shrink the surface the later
  slices have to move.
- **4–6 before 7–14** because they are correctness defects in the core lifecycle and
  independent of the MCP work.
- **7 before 8, 4 before 5**: write the failing test on the old tree, so the fix is
  proven by the test flipping rather than by the absence of failures.
- **9 before 10–14**: deleting 25 unused methods first means the `ToolContext` and
  use-case moves never have to carry them.
- **15 late**: hoisting is mechanical, but it touches the same files as 10–14. Doing it
  after avoids rebasing every slice.
- **16 last**, as `08` and `11` both concluded: the consumer set moves before the
  structure. Steps 8–14 *are* that consumer move.

## Guards each slice should leave behind

| Guard | Protects against | Where |
|---|---|---|
| `_PHASE_NODES` identity with the graph builder | a phase with two implementations | `tests/unit/orchestration/` |
| Reducer parity over every `Annotated` channel | the manual path mis-merging a new channel | `tests/unit/orchestration/` |
| No handler imports outside `mcp/server.py` + `mcp/registry.py` in `src` | a new direct-call path | `tests/unit/architecture/test_boundary_law.py` |
| No writes to another package's `_`-attributes | `rt_mod._RUNTIME = …` from outside `studio` | same file (it counts private *imports* today, not private *writes*) |
| Every tool has `input_schema` + real description (ratcheted) | the contract regressing to names only | `tests/unit/test_mcp.py` or a new catalog test |
| Lazy-import totals are ratcheted, not annotated | coupling hidden in function bodies | `tests/unit/architecture/test_lazy_imports.py` |
| `make enola` runs without a pipe | reading `tail`'s exit code as the gate's | `Makefile` |

Audit each guard as AGENTS.md requires: *what change would make this pass while being
wrong?* Then inject it. For example, the reducer parity test must fail when a new
`Annotated` channel is added to `StudioGraphState` and not to the stub node's
update — otherwise it only checks the channels that existed when it was written.

## What not to do

- **Do not add a new layer or package** to hold use cases. `operations`, `generation`,
  `config`, `agents` already own the concerns; doc 03 moves code *into* them.
- **Do not wrap the global runtime** in an accessor to "reduce fan-in". 61 call sites
  of one getter are the symptom; passing a context at dispatch is the fix (AGENTS.md:
  "the repair is to move the concern up … not to add a wrapper that keeps every call
  site").
- **Do not model output schemas speculatively.** Only where a program parses the output.
- **Do not sweep the underscore-name convention or the enum import spelling.** Apply
  them when touching a file for another reason.
- **Do not grade imports against `03`'s layer law.** `06` §4 still governs.
- **Do not narrate a slice.** Every check in the table above is a command; run it in
  the same turn you describe it.

## What this plan does not establish

- That the QC divergence (02 B) has produced a wrong artifact in a real run.
- That hoisting 275 imports is behaviour-neutral where modules have import-time side
  effects (registries populated at import).
- That the 25 unused `OperatorService` methods have no planned consumer — ask before
  deleting if a web or HTTP operator surface is on the roadmap.
- Anything about runtime performance beyond MCP-server import time.
