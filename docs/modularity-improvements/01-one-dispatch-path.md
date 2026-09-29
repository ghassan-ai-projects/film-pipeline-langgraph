# 01 — One dispatch path for MCP tools

**Priority: 1 (correctness of the human-gate boundary).** Size: M, in three slices.

## Finding

There are two ways to run an MCP tool handler, and only one of them applies the
tool contract.

**Path A — `MCPServer.call`** ([server.py:48](../../src/film_pipeline/mcp/server.py)):
resolves `project_ref`, then runs, in order,

1. `_check_confirmation` — the 9 `confirm=True` tools (`approve_phase`,
   `approve_intake`, `approve_profile_change`, `approve_coverage_generation`,
   `request_revision`, `export_delivery_package`, `promote_test_to_production`,
   `rollback_artifact`, `rollback_to_checkpoint`);
2. `_check_active_project` — the 44 `active_project=True` tools, the check that
   replaced 48 per-handler guards;
3. `_dispatch_handler` — maps `MCPError` / `ProjectNotFoundError` to typed responses.

**Path B — call the handler function directly.** Used by:

- **The CLI.** `HeadlessDriver._call_tool` does
  `getattr(importlib.import_module("film_pipeline.mcp.tools"), tool_name)` and awaits it
  ([cli/driver.py:200](../../src/film_pipeline/cli/driver.py)). None of the three
  checks runs. The driver installs its runtime by writing another module's private
  globals: `rt_mod._RUNTIME = rt` and `rt_mod._RUNTIME_MODE_OVERRIDE = mode`
  ([cli/driver.py:81](../../src/film_pipeline/cli/driver.py)).
- **The E2E scenarios.** The `invoke_tool` fixture
  ([tests/e2e/conftest.py:170](../../tests/e2e/conftest.py)) does the same
  `import_module("film_pipeline.mcp.tools")` + `getattr` as the CLI.
- **30 test files** import handlers from `film_pipeline.mcp.tools` and call them;
  6 go through `MCPServer`. 73 test sites monkeypatch `get_runtime`.

Handlers locate the runtime through a process-global singleton — **61
`tools_pkg.get_runtime()` calls** in `mcp`, resolved by package attribute so the
monkeypatch sees it (the docstring at
[helpers.py:62](../../src/film_pipeline/mcp/tools/helpers.py) explains the constraint).
The runtime then flows through **37 `rt: Any` parameters**. The resolved project
reaches handlers by being smuggled into the argument dict as `"_envelope"`
([server.py:251](../../src/film_pipeline/mcp/server.py)) and read back with
`getattr(envelope, "resolved_project_id", None)`.

### Reproduced

[`probe_dispatch_paths.py`](probe_dispatch_paths.py), run on `2450616`:

```text
A  get_blockers, no project   -> no_active_project
B  get_blockers, no project   -> raised ProjectNotFoundError
A  approve_phase, unconfirmed -> confirmation_required
B  approve_phase, unconfirmed -> ok=True phase intake -> constitution
```

The last line is the finding: through Path B, a human gate is approved with no
`confirmed` flag. The CLI always passes `confirmed=True`, so this is not a live bypass
in the shipped driver today — it is a gate whose enforcement depends on every caller
remembering to use the other path.

### Why it matters

- **The policy moved to dispatch, but not every caller goes through dispatch.** The
  active-project consolidation (48 guards -> 1 check) was the right move; it is only
  complete for Path A. The CLI is the headless product path, and the E2E
  scenarios drive the same direct path, so the suite's strongest end-to-end evidence
  is about the path that skips the gate checks. This is the exact shape of the AGENT-27 lesson: *a green
  suite is silence about the path it does not cover.*
- **Confirmation is enforced in two layers for some tools and one for others.** The
  rollback handlers re-check `confirmed` themselves
  ([checkpoints.py:120, 156](../../src/film_pipeline/mcp/tools/checkpoints.py));
  `approve_phase` relies on dispatch alone. That split is itself the "one policy at N
  sites" defect in miniature.
- **"Active project" has two owners.** `MCPServer.active_project_id` +
  `ProjectRegistry` and `StudioRuntime.active_project_id` + `StudioRuntime.projects`.
  They are reconciled after the fact by `_auto_register_from_runtime`, whose comment
  says it "fixes the gap where … the server's ProjectRegistry is a separate in-memory
  structure" ([server.py:125](../../src/film_pipeline/mcp/server.py)). A mutating call
  sets the *server's* active project; `set_active_project` sets the *runtime's*.

## Recommendation

Make `MCPServer.call` the only way to execute a tool, and pass handlers what they need
instead of letting them fetch it.

### Slice 1 — route the CLI through dispatch (smallest, highest value)

- `HeadlessDriver` builds an `MCPServer` bound to its runtime and calls
  `await server.call(name, args)`, unwrapping `MCPResponse` into the dict it already
  returns.
- Replace the two private-global writes with a public installer on `studio.runtime`
  (one already half-exists: `reset_runtime`). `cli` must not assign `_`-names on
  another package's module; add that shape to `test_boundary_law.py` (it currently
  counts private *imports*, not private *attribute writes*).

**Falsifiable check:** the probe's two `B` lines become the `A` results. As tests:
a driver call to a `requires_active_project` tool with no active project yields
`NO_ACTIVE_PROJECT` (today: raises `ProjectNotFoundError`), and a driver call to
`approve_phase` without `confirmed` yields `CONFIRMATION_REQUIRED` (today: advances the
phase). Write both first; both fail on `2450616`.

### Slice 2 — a request context instead of a global and a smuggled envelope

Change the handler shape from `handler(args) -> dict` to
`handler(ctx: ToolContext, args) -> dict`, where

```python
@dataclass(frozen=True)
class ToolContext:
    runtime: StudioRuntime       # or RuntimePort, if 03 lands first
    project_id: str | None       # resolved by dispatch; None only for tools that don't need one
    envelope: RequestEnvelope
```

This deletes, rather than wraps: `_active_project_id`'s two-source fallback, the
`"_envelope"` key, the `import film_pipeline.mcp.tools as tools_pkg` late-binding idiom
in every tool module, the 37 `rt: Any` parameters, and the 73 `get_runtime`
monkeypatches (tests construct a context with a real `StudioRuntime(runtime_root=tmp)`,
which they already build). It is mechanical per tool group; do one group per commit.

**Falsifiable check:** `grep -c "get_runtime()" src/film_pipeline/mcp` goes 61 -> 1
(server `main`), and mypy strict passes with `rt: Any` gone.

### Slice 3 — one owner for the active project

The runtime owns project state, so it owns "active". `MCPServer` keeps the
`ProjectRegistry` only for `project_ref` -> id resolution, reads `runtime.active_project_id`
instead of storing its own, and `_auto_register_from_runtime` is deleted because the
registry is built from `runtime.projects`.

**Falsifiable check:** remove `MCPServer.active_project_id`; the failures enumerate
every site that depended on the second copy.

## Guards to leave behind

- `src` guard: nothing outside `mcp/server.py` and `mcp/registry.py` imports handler
  callables from `film_pipeline.mcp.tools.*`.
- Tests: ratchet the "tests calling handlers directly" count (30 files) down, with a
  shared `call_tool` fixture that goes through `MCPServer.call`.

## What this does not establish

Whether any currently-passing CLI or E2E scenario would fail under dispatch. That is the
point of Slice 1's test-first step: the failures, if any, are the list of places where
the headless path relied on skipping a check.
