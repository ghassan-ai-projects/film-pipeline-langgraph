# Why `StudioRuntime` looks impossible to shrink

Date: 2026-09-26. Revision: `74f36cd`. This is a diagnosis, not a plan. It exists
because an earlier attempt to split `StudioRuntime` made it *larger* (370 → 381
lines, 39 → 41 methods), and the reason that happened turns out to be the actual
finding.

## 1. The failed attempt, honestly recorded

I extracted the provider cluster into a `ProviderRegistry` collaborator and kept
all ten public methods on `StudioRuntime` as delegations. Measured result:

| | Lines | Methods | Public |
|---|---:|---:|---:|
| Before | 370 | 39 | 27 |
| After (facade) | 381 | 41 | 29 |

The state moved; the surface did not. A facade that retains every method adds
indirection without removing anything. That change was reverted.

The lesson is not "extract differently" — it is that **the method count is not
where the size comes from.**

## 2. Why the surface is so large: two paths to the same state

There are 77 MCP tool handlers. Of the 24 files that call `get_runtime()`, only
**4** also use `OperatorService`, the intended operator boundary:

- `mcp/tools/_profile_change.py`
- `mcp/tools/checkpoints.py`
- `mcp/tools/generation/planning.py`
- `mcp/tools/projects.py`

The other ~20 reach into `StudioRuntime` directly. `OperatorService` exposes
methods for some of what they need; for the rest, the tool bypasses the service
layer entirely and calls the runtime.

## 3. The measured capability gap

MCP tools use 27 distinct `rt.*` attributes. **20 of them are not available on
`OperatorService`**:

**Pure reads (14):** `get_active` (×25 call sites), `projects` (×10),
`get_project` (×7), `server_mode` (×7), `get_provider` (×5),
`provider_adapters` (×4), `list_providers` (×3), `default_video_provider` (×3),
`get_provider_health` (×2), `services` (×2), `audit_events`, `get_audit_log`,
`get_all_health`, `project_roots`

**Mutations (6):** `_persist_project_state` (×7), `_record_audit` (×3),
`run_graph` (×2), `set_active` (×2), `create_checkpoint`, `set_provider_health`

So the runtime is not a god object because it *chose* to be one. It is one
because it is the only thing that answers "what is the current project, what is
its state, and let me change it" for two thirds of the operator surface.

## 4. The specific smell

`get_active()` alone accounts for 25 call sites, and the pattern is the same
every time:

```python
rt = tools_pkg.get_runtime()
active = rt.get_active()
if active is None:
    return _error("No active project. ...")
```

A helper for exactly this already exists — `helpers._active_project_state(args)`
and `helpers._active_project_id(args, rt)` — and some tools use it while others
re-derive it inline. So the duplication is not only "reach past the service
layer"; it is also "re-implement one policy in N places."

## 5. What this implies

Decomposing `StudioRuntime` by moving state into collaborators does not reduce
the surface, because the surface is driven by *consumers*, not by the class's
internal structure. Any split that keeps the 21 missing capabilities reachable
through the runtime reproduces the same 27-method facade.

Three directions are available, and they are genuinely different in cost and
risk:

**A. Close the capability gap in `OperatorService`.** Add the 14 pure reads and
6 mutations to the service, then retarget the ~20 bypassing tool files to it.
`StudioRuntime`'s surface can then shrink because nothing outside `studio`
calls it. Highest value; touches ~20 source files and the tests that patch
`mcp.tools.get_runtime` (see §6).

**B. Extract only what has no external readers.** The provider cluster is the
only group whose *state* is not read directly by many callers
(`provider_adapters` is read in 6 places, `provider_health` rarely). A split
here shrinks the class slightly and is low risk, but it is a small win and was
the change that failed above when done as a facade.

**C. Leave `StudioRuntime` alone.** Defensible: its size is a consequence of
being the session's shared state, and `03` §3.8 already records the intended
fix (project state moves to `projects`, F-RUNTIME-01). Doing nothing is not
obviously worse than a facade.

I do not think B is worth doing. It has the cost of a split and the benefit of
a rename.

## 6. The constraint that makes A expensive

250 test references and 156 source references touch `get_runtime`. The MCP tool
facade deliberately re-exports it (`mcp/tools/__init__.py`) and at least 71 test
sites monkeypatch `film_pipeline.mcp.tools.get_runtime`. Any change to *how*
tools obtain a runtime has to respect that seam or retarget all of it.

This is why direction A is a real project rather than a round: it is not one
refactor, it is a boundary change with a test-suite migration attached.

## 7. What I have not established

- Whether `OperatorService` is the right target for all 20 capabilities. Some
  (notably `run_graph`) may belong to `orchestration` rather than the operator
  service. I have not analysed that.
- Whether the 24 `get_runtime()` files are genuinely bypassing an intended
  boundary or whether the service layer was simply never extended to cover
  them. The commit history that introduced `OperatorService` was not examined.
- Whether direction A's ~20-file retarget actually removes the runtime from
  their imports, or merely adds a hop. That needs a prototype before committing
  to it.
