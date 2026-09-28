# 05 — Import hygiene: make the dependency graph visible

**Priority: 3 (legibility; mechanical).** Size: M, one package per commit.

## Finding A — 96% of function-level imports protect no cycle

There are **287** function-level imports of `film_pipeline` modules. For each `A -> B`,
the measurement asks: does `B` already reach `A` through module-level imports
(including the package `__init__` files that importing `B` executes)? If not, hoisting
the import to module level cannot create a cycle.

| | count |
|---|---:|
| function-level internal imports | 287 |
| **hoistable without creating a cycle** | **275** |
| cycle-required | 12 |

Hoistable, by package: `mcp` 125, `orchestration` 79, `studio` 25, `post` 20, `cli` 7,
`governance` 7, `operations` 6, `storage` 3, `generation` 3.

A keyword search for a stated reason (`circular|import cycle|lazy import|avoid.*import`)
finds one, in [contract.py:122](../../src/film_pipeline/mcp/contract.py) (plus the
`_LAZY_NAMES` comment in `operations/__init__.py`).

### Why it matters

Lazy imports hide coupling from every tool that reads module headers — people, `grep
'^from'`, and module-level graph views:

| Package | fan-out visible at module level | fan-out including function-level |
|---|---:|---:|
| `mcp` | 8 | **16** |
| `studio` | 9 | 11 |
| `orchestration` | 7 | 9 |
| `post` | 1 | 3 |

Half of `mcp`'s package dependencies are invisible from its import blocks. A reviewer
reading `mcp/tools/generation/dispatch.py` (16 function-level imports) cannot tell what
it depends on without reading every function body.

### The legitimate exception: LangGraph start-up cost

Measured with `python -X importtime` and wall clock:

| Import | Cost |
|---|---:|
| `film_pipeline.mcp.server` | ~150–170 ms |
| + all 75 tool modules | +25 ms |
| + graph factory, nodes, `generation` (pulls `langgraph`) | **+339 ms** |

Deferring LangGraph until the first graph call is a reasonable start-up choice for a
stdio server. It justifies **one** lazy seam — `studio._graph_exec.ensure_graph`
already is one — not 275.

## Finding B — the 12 required ones are mostly `__init__` side effects

Of the 12 cycle-required lazy imports, **9 exist only because a package `__init__`
eagerly re-exports a submodule** that in turn imports back into the package:
`storage` (4), `config` (2), `agents.prompt_templates` (2), `operations` (1). E.g.
`storage.paths` imports nothing from `film_pipeline`, yet `project_storage` must import
it lazily, because importing `storage.paths` runs `storage/__init__`, which imports
`project_storage`.

The other three are real module cycles, two of them fixable by deleting code:

- **`orchestration.nodes.approval <-> nodes._repair_loop`.** `approval` imports
  `_repair_loop` only to re-export `_PHASE_NODES` and `repair_phase_node`, "to keep the
  historical `graph.nodes.approval` import paths working"
  ([approval.py:20](../../src/film_pipeline/orchestration/nodes/approval.py)). The
  `graph` package no longer exists. Two consumers remain (`studio/_graph_exec.py:508`,
  `nodes/__init__.py:36`); point them at `_repair_loop` and delete the re-export — the
  cycle disappears.
- **`mcp.contract <-> mcp.registry`.** `make_registry()` lives in `contract` and lazily
  imports `registry`, which imports `contract`. Move `make_registry` into `registry.py`
  (20 references). Doc 04 would restructure this anyway.
- `mcp/__init__ -> mcp.server`: a PEP 562 lazy attribute; fine as is.

## Finding C — shared internals spelled as private

**241** imports bring an underscore-prefixed *name* from a sibling module (152 distinct
names). The most shared:

| Name | importers |
|---|---:|
| `orchestration.services._get_services` | 12 |
| `orchestration.nodes._agent._save_artifact` | 7 |
| `orchestration.nodes._agent._run_agent` | 6 |
| `orchestration.nodes._agent._propagate_side_effects` | 6 |
| `orchestration.nodes._shared._phase_gate_updates` | 6 |

A function imported by 12 modules is the package's internal API, not a private helper.
The underscore now carries no information: it marks both "used in this file only" and
"used across the package". Convention worth adopting: **an underscore module is
package-private; the names inside it are not underscored.** Then `_x` means "this file",
and the module path says "this package". Apply when a module is touched for another
reason; it is not worth a sweep on its own.

## Recommendation

1. **Delete the `approval` re-export shim** (Finding B, first bullet). One commit;
   removes a module cycle and a lazy import.
2. **Move `make_registry` to `registry.py`** — or fold into doc 04's slice.
3. **Thin the package `__init__` files that cause cycles** (`storage`, `config`,
   `agents.prompt_templates`): a package root should re-export what consumers need
   without importing modules that import back into the package. The surface ratchet
   (`test_surface_ratchet.py`) will show whether any public name changes.
4. **Hoist function-level imports package by package**, starting with `post` (20, small
   package), then `governance`, `studio`, `orchestration`, `mcp`. Keep a lazy import only
   when it is cycle-required, a test patch point, or a shadowing/side-effect hazard —
   the categories are in `AGENTS.md`, not in the source.
5. **Add the guard** below so the count cannot silently grow back.

**Falsifiable check for each hoist commit:** `measure.py`'s not-cycle-required count for
that package goes to 0, mypy strict and the acyclicity test stay green, and
`python -X importtime -c "import film_pipeline.mcp.server"` does not grow by more
than a few ms (if it jumps by ~300 ms, a hoist pulled in LangGraph — revert that one).

## Guard to leave behind

`tests/unit/architecture/test_lazy_imports.py` ratchets two counts, both computed with
`measure.py`'s own reachability walk: `LAZY_EDGE_CEILING` (all function-level internal
imports) and `HOISTABLE_EDGE_CEILING` (those that are *not* cycle-required). Both may
only fall.

**Superseded during the migration:** the first version of this guard required each
function-level import to carry a `# lazy: <reason>` comment, and the migration was
tracked through those comments (`annotated` / `unexplained` in `measure.py`). That
regime was retired once the hoist landed. The reasons were ~29 repetitions of the same
two sentences, and a comment is a claim that rots — a later hoist left two of them
asserting a cycle that no longer existed. The reasons now live once in `AGENTS.md`, and
the guard counts instead of annotating; it is *stricter* than its predecessor, which
allowed a new function-level import as long as it carried a comment.

## What this does not establish

That hoisting changes no behaviour. Module import order can matter where a module has
import-time side effects (registries populated at import). The acyclicity and full test
suites are the check; run them per package, not once at the end.
