# Boundary audit: what is enforced and what still leaks

Date: 2026-09-29. Source checkpoint: `6118b3b99543`, rechecked at `0c8f3f2c08b5` on `improve-modular-2`. The intervening committed diff touched only generation execution/dispatch and two integration tests; the boundary counts remained the same. This audit reads the boundary guards and the stable runtime/MCP surfaces. It does not review the other agent's generation and validation behavior changes. Findings should be rechecked before implementation.

## Verdict

**The adopted module boundaries are partly respected, but “no internals are exposed or leaked” is not true.** An independent scan found exactly the two known cross-package private-module imports and two known private-symbol imports. The current package import graph has no directed cycle. The focused architecture tests pass. Those are useful results, but the guards do not cover every Python access form, one cycle guard misses cycles longer than two packages, the documented Enola command currently enforces no policy, and several declared interfaces expose internal handles or mutable state.

This audit uses the boundary the project actually adopted: no new private reach-ins, no external calls to runtime-private persistence/audit methods, no private-global writes, declared package-root exports, and no package cycles. [AGENTS.md](../../AGENTS.md) and [the independent decision](../modular-architecture/06-independent-review-and-decision.md#4-target-shape) explicitly reject the old per-package “Allowed outbound” import law. An ordinary import of a public submodule is therefore not a finding by itself. Python's `__all__` controls wildcard imports and documents a surface; it cannot make a submodule inaccessible.

## Reproducible inventory

| Check | Result at the checkpoint | Limit |
|---|---|---|
| Focused boundary, public-surface, surface-ratchet, and package-cycle tests | Pass (`uv run pytest -q --no-cov tests/unit/architecture/test_boundary_law.py tests/unit/architecture/test_public_surface.py tests/unit/architecture/test_surface_ratchet.py tests/unit/architecture/test_package_acyclicity.py`) | A passing test only covers its detector. |
| Independent AST scan of absolute `Import` and `ImportFrom` forms | 2 cross-package private modules; 2 private symbols | Dynamic imports and reflective access are outside this count. |
| Independent DFS over `_cross_package_edges()` | 67 directed package edges; no cycle | The guard's own `_mutual_pairs()` is weaker than this check (B1). |
| Runtime-resolved `__all__` scan | 51 underscore-prefixed names declared across four package roots | Declared private names are deliberately exempted from the root leak guard (B5). |
| Documented Enola command | Exit 0 with “nothing enforced: no policy set” | The installed version defaults `--fail-on` to none, contrary to AGENTS.md (B3). |

The full `make ci-check` run on the concurrent working tree did **not** pass: formatting, lint, and mypy passed; pytest reported 2,358 passed, 8 skipped, 4 expected failures, and two failures in `test_lazy_imports.py`. Its ratchet counted 43 function-level internal imports (ceiling 42), including 32 classed as hoistable (ceiling 31). At the time of the run, the other agent's uncommitted `orchestration/execution.py` added a function-level import of `orchestration.nodes._agent_artifacts`; the report does not change or adjudicate that in-progress slice. Coverage was 91.71%; the build step did not run after pytest failed. This is a working-tree validation result, not a defect caused by this documentation audit.

Replay the guard and graph counts from the repo root (the private-import counts are the existing guard's narrower measurement; a separate scan of both absolute import forms found no additional current crossing):

```bash
uv run python - <<'PY'
from graphlib import TopologicalSorter
from tests.unit.architecture.test_boundary_law import _measure_private_imports
from tests.unit.architecture.test_package_acyclicity import _cross_package_edges, _mutual_pairs
from tests.unit.architecture._surface_scan import packages, declared_surface
modules, symbols = _measure_private_imports()
edges = _cross_package_edges()
dependencies = {}
for source, target in edges:
    dependencies.setdefault(source, set()).add(target)
    dependencies.setdefault(target, set())
tuple(TopologicalSorter(dependencies).static_order())
private_exports = {p: sum(n.startswith("_") for n in (declared_surface(p) or ())) for p in packages()}
print(modules, symbols)
print("edges", len(edges), "directed cycles", 0, "mutual pairs", _mutual_pairs(edges))
print({p: n for p, n in private_exports.items() if n})
print("three-node probe", _mutual_pairs({("a", "b"): {"a.py"}, ("b", "c"): {"b.py"}, ("c", "a"): {"c.py"}}))
PY
```

The current, recorded private crossings are:

| Importer | Reached internal | Source | Status |
|---|---|---|---|
| `mcp` | `studio._persistence` | [`mcp/server.py:41`](../../src/film_pipeline/mcp/server.py) | Known private-module exception for runtime-root selection before startup. |
| `mcp` | `studio._operator_runtime` | [`mcp/tools/helpers.py:20`](../../src/film_pipeline/mcp/tools/helpers.py) | Known private-module exception for profile provider composition. |
| `agents` | `providers.http_transport._accepts_timeout_kw` | [`agents/model_adapter.py:27`](../../src/film_pipeline/agents/model_adapter.py) | Known private-symbol compatibility alias. |
| `agents` | `providers.http_transport._open_with_timeout` | [`agents/model_adapter.py:30`](../../src/film_pipeline/agents/model_adapter.py) | Known private-symbol compatibility alias. |

These four crossings are **existing, explicitly recorded debt**, not newly discovered regressions. The tables in [`test_boundary_law.py:48–103`](../../tests/unit/architecture/test_boundary_law.py) require their counts not to grow or become stale. The owner should replace a crossing only when the caller has a useful public operation; a pass-through re-export added solely to satisfy a guard would hide the dependency.

## Findings, ordered by effect on confidence

### B1 — “Acyclic” test only detects mutual pairs (guard defect)

[`test_package_acyclicity.py:82–100`](../../tests/unit/architecture/test_package_acyclicity.py) calls `_mutual_pairs()`, which reports an edge `A -> B` only if `B -> A` also exists. A three-package cycle `A -> B -> C -> A` has no mutual pair. A synthetic three-edge probe returned `[]`; the test would pass it. The independent DFS over the current 67 edges found no directed cycle, so this is a **false-negative capability**, not evidence of a present package cycle.

The file's second test cannot exercise its stated condition either: `_cross_package_edges()` drops self-edges at [line 74](../../tests/unit/architecture/test_package_acyclicity.py), while `test_no_package_imports_itself_via_the_root()` looks for self-edges in that output. Treat it as an ineffective check, not proof that self-imports are absent.

**Why it matters:** a future three-package cycle can pass the required architecture test and make initialization order or ownership harder to reason about. **Repair criterion:** replace the pair check with a full directed-cycle or strongly connected component check; inject a three-node cycle and verify the test fails. Decide separately whether same-package root imports are prohibited, then inspect them before filtering self-edges. Do not turn this into the rejected allowed-import law.

### B2 — Private-access detector misses valid Python forms (guard defect)

[`_measure_private_imports()`](../../tests/unit/architecture/test_boundary_law.py) inspects only `ast.ImportFrom` at [lines 174–180](../../tests/unit/architecture/test_boundary_law.py). In a temporary tree, `import film_pipeline.studio._persistence as secret` produced no finding. [`_measure_private_attribute_writes()`](../../tests/unit/architecture/test_boundary_law.py) builds module aliases only from `ast.Import` at [lines 466–476](../../tests/unit/architecture/test_boundary_law.py); `from film_pipeline.studio import runtime as rt_mod; rt_mod._RUNTIME = object()` also produced no finding. No production use of those two shapes was found by the independent scan.

**Why it matters:** the guard can stay green while a new private dependency or private-global write appears. **Repair criterion:** test the real detector with temporary source files in both syntactic forms, then make it resolve both `Import` and `ImportFrom` aliases and nested private segments. Keep the existing debt table exact; do not broaden it to absorb a new crossing. Reflective `getattr`/`setattr` and dynamic imports remain a stated limit unless a concrete caller requires them.

### B3 — The documented Enola command is report-only on this installation (gate configuration defect)

The required command in [`AGENTS.md:57–59`](../../AGENTS.md) exited 0 while printing **“nothing enforced: no policy set.”** `enola check --help` says this installed version defaults `--fail-on` to **none**; [`enola-config.yaml`](../modular-architecture/enola-config.yaml) sets no failure policy. This contradicts [`AGENTS.md:86`](../../AGENTS.md), which says cycles are the default failure policy. An exit-0 receipt from the documented command therefore cannot certify the absence of a new blocking cycle.

Running the same check with `--fail-on=cycles` exited **1** on one reported three-module `orchestration` cycle. That is **not proof of a new current-tree cycle**: `enola baseline show` dates the pinned snapshot to 2026-09-27 on dirty `improve-modular` commit `74490e2cc9e1`, older than this checkpoint, and [the earlier progress ledger](PROGRESS.md) records an `orchestration` root-collapse artifact. The independent top-level-package DFS above found no cycle; it measures a different granularity.

**Repair criterion:** once the concurrent work reaches a clean commit, regenerate and pin the docs-local baseline from that clean tree, verify the snapshot's package identities, then invoke Enola with an explicit `--fail-on=cycles` in the required check and record its exit code. Reproduce the remaining cycle before classifying it as real or a grouping artifact. Do not lower a filter or threshold to make the result green. Update AGENTS.md's default-policy claim to match the installed CLI.

### B4 — MCP tools receive and mutate live runtime state (ownership leak)

[`ToolContext.runtime: Any` and `project_state()`](../../src/film_pipeline/mcp/tools/context.py) hand a handler the concrete runtime and a mutable project `dict`. [`StudioRuntime.get_project()`](../../src/film_pipeline/studio/runtime.py) returns the mapping in `self.projects` without copying or an operation boundary. A temporary-root probe confirmed `get_project("probe") is runtime.projects["probe"]`; changing `current_phase` on the returned mapping immediately changed runtime state. Current handlers also assign `rt.projects[project_id]` directly, for example [`mcp/tools/helpers.py:66`](../../src/film_pipeline/mcp/tools/helpers.py), [`mcp/tools/validation.py:263`](../../src/film_pipeline/mcp/tools/validation.py), and [`mcp/tools/generation/_text_only.py:76`](../../src/film_pipeline/mcp/tools/generation/_text_only.py). Others read registry and audit internals directly ([`mcp/tools/projects.py:214–227`](../../src/film_pipeline/mcp/tools/projects.py), [`mcp/tools/audit.py:37`](../../src/film_pipeline/mcp/tools/audit.py)).

This is an **in-process ownership leak**, not a demonstrated remote MCP authorization bypass. The existing handlers usually call `persist_project_state` after a write, but the type and API do not require persistence, audit, or validation when a caller mutates the live mapping. The private-import and package-surface guards cannot see this because every field is publicly named on `StudioRuntime`.

**Repair criterion:** as functional workflows move to their owners, give handlers narrow read results and use-case operations for state changes. Start with one proven duplicated workflow (the validation and generation work in [09](09-functional-boundaries.md)), and assert its persisted state and audit result at `MCPServer.call`. Avoid copying every runtime field into a new generic port; [`RuntimePort`](../../src/film_pipeline/operations/ports.py) already shows how such surfaces can grow. Keep `ToolContext`'s resolved project identity, but make its access to mutable state deliberate per operation.

### B5 — Package roots explicitly publish private names and a runtime handle (surface-design debt)

The runtime-resolved `__all__` inventory contains 22 underscore-prefixed template constructors in [`agents/prompt_templates/defaults/__init__.py`](../../src/film_pipeline/agents/prompt_templates/defaults/__init__.py), 26 internal graph helpers in [`orchestration/nodes/__init__.py`](../../src/film_pipeline/orchestration/nodes/__init__.py), two MCP generation helpers in [`mcp/tools/generation/__init__.py`](../../src/film_pipeline/mcp/tools/generation/__init__.py), and one bible helper in [`mcp/tools/bibles/__init__.py`](../../src/film_pipeline/mcp/tools/bibles/__init__.py). That is 51 names the packages explicitly declare as exportable even though their leading underscores say “internal.” The surface tests accept them: [`test_surface_ratchet.py:115–126`](../../tests/unit/architecture/test_surface_ratchet.py) excludes underscore names from its undeclared-root leak check, and the ratchet counts `__all__` size rather than checking whether each name belongs to the intended API. Replacing one valid export with another while keeping the count constant also passes that count check; this is a known limit of a size ratchet, not proof that the interface stayed the same.

Separately, [`mcp/tools/__init__.py:29,92`](../../src/film_pipeline/mcp/tools/__init__.py) exports `get_runtime` alongside tool handlers. It gives in-process callers the ambient, mutable `StudioRuntime` outside `MCPServer.call`'s project resolution and confirmation path. The current `src/` search found no production consumer of that facade export; tests import or patch it. This is an **exposed Python handle**, not evidence that an external MCP client can call `get_runtime` as a tool.

**Repair criterion:** classify each underscore export by real production consumer and test fixture. Keep the two public template loaders; move tests that need a helper to its defining module where practical, then remove only unsupported facade exports with compatibility tests. Record exact names for the stable public exports if a rename should require review. For `mcp.tools.get_runtime`, first migrate the patch fixture and any documented in-process consumer, then remove it from the tool facade if no consumer contract needs it. Do not infer that `__all__` prevents direct Python imports; the maintainable goal is a truthful documented surface and no routine cross-owner reach-in.

## Root cause (five whys)

1. **Why can internal state be reached?** Tool context passes the whole runtime and its live project mapping.
2. **Why does the interface allow that?** `Any` and public mutable dataclass fields let handlers implement their own writes.
3. **Why is exposure not flagged?** The guards mostly examine import spelling, root `__all__`, and counts; they do not own use-case state transitions.
4. **Why can a guard pass while a boundary regresses?** Two detectors omit valid syntax, the cycle test recognizes only two-way pairs, and the documented Enola invocation is report-only.
5. **Why did this persist?** The modularity program measured directory surfaces and import edges more thoroughly than the end-to-end authority of a project mutation. The next improvement is to verify one operation and its observable result across each entry path, while making the detectors complete for the rules they claim.

The last point is an inference from this audit's code paths and guard history, not a claim about every historical design decision.

## Scope and next checks

- Audit these findings against a stable commit after the concurrent generation and validation work lands. The source checkpoint above does not cover its uncommitted behavior; the full check captured one added lazy import while that work was in progress.
- For B1/B2, a red test on a deliberately injected bad graph/import is the acceptance proof; a green current-tree test alone is insufficient.
- For B3, treat the current Enola exit 0 as a diagnostic run, not a gate pass. The explicit cycle-policy check failed against an old, dirty baseline, so the architecture gate remains unverified until the baseline is refreshed on a clean tree.
- For B4, characterize one state-changing MCP action at the server boundary. Check refusal, persisted project state, audit event, and restart behavior. This will tell whether replacing direct mapping access removes a real failure path.
- For B5, preserve import compatibility where production callers exist. An underscore in `__all__` is an API-design inconsistency; it is not automatically a runtime bug.
- Run `make ci-check`, `uv run mypy src tests`, and the repaired docs-local Enola gate on each eventual production slice. Even an enforcing Enola pass would not prove that a tool confirms a request or persists a complete state change.

## Implementation status

Date: 2026-09-29. Added after the findings above were implemented. This section
records executed results; where a finding's own criterion was only partly met, it
says which part and why.

### What landed

| Commit | Finding | Falsifiable result |
|---|---|---|
| `28abf60` + `fbf8823` | B1 | injected sibling cycle: architecture test exits **1** (baseline 0) |
| `54577c7` + `46a2c0b` | B2 | 4 uncovered forms now detected; tree unchanged at 2 modules + 2 symbols |
| `8d3bb60` + baseline re-pin | B3 | `make enola` enforces `cycles`; baseline re-pinned at clean `7895d8c` |
| `9806210` | B4 | 10 direct mapping writes → 1 declared operation; guard + boundary test |
| `7895d8c` | B5 | 51 private exports measured, 36 unimported; ratchet + injection proof |

### B1 — the guard now finds a real cycle, and the audit's other half was a false alarm

The mutual-pair check is replaced by Tarjan strongly connected components over a
**full topological sort of the package graph**, and each reported cycle names the
files creating every edge.

Three git commits were needed because I got it wrong twice, and both corrections
came from injecting rather than reading:

1. `28abf60` replaced `_mutual_pairs` with `_cycles` and reported **0 cycles over
   85 edges** — and I wrote that the orchestration finding was a `TYPE_CHECKING`
   artifact. Both claims were false.
2. `fbf8823` fixed the causes. `_packages()` read only top-level directories, so
   `orchestration.nodes` and `orchestration.subgraphs` **were not graph nodes at
   all**; and attributing the importing file to every enclosing package fabricated
   a `generation <-> generation.compositor` cycle that does not exist.

Measured at the tip: **37 package nodes, 174 edges, 5 strongly connected
components, 1 real cycle.**

- Four components (`agents`, `generation`, `mcp`, `schemas`/`governance`/
  `validation` shapes) are a package and its own subpackage importing each other.
  That is inherent to Python — `pkg/__init__.py` publishes `pkg.sub`, and
  `pkg/sub/mod.py` imports names from `pkg` — so it is excluded by an **edge-level**
  rule (`_inherent_nesting_only`): a component is inherent when every edge runs
  between a package and one of its descendants.
- The fifth is real and is the one this audit's command hinted at:
  `orchestration.nodes <-> orchestration.subgraphs`, via
  `nodes/_repair_loop.py -> subgraphs.qc` and `subgraphs/qc.py ->
  nodes._agent_artifacts`. Siblings, so the parent does not order them.

**Correction to this document's B3 text.** It says the reported orchestration
cycle is probably an artifact because the edge is `TYPE_CHECKING`-only. It is
**not** `TYPE_CHECKING`: `_repair_loop.py:70` is a *function-level* import, which
is exactly why `test_lazy_imports.py` counts it in the cycle-required floor of 11.
It is a genuine runtime cycle, recorded in `KNOWN_PACKAGE_CYCLES` with the reason
rather than hidden, and asserted non-stale. The audit's independent DFS over 67
edges found no cycle because it used the same collapsed node set the guard did.

Acceptance proof, run against real files:

```
BASELINE arch test exit=0
INJECTED arch test exit=1     (agents.impl -> agents.prompt_templates, a sibling edge)
reverted: True
```

The self-edge test is also repaired: it previously searched for self-edges in a
graph that filters them out, so it could never fail. It now measures them directly
and reports the two real ones (`agents/__init__.py` lines 14-15).

### B2 — capability added, and the tree was not hiding anything

Both detectors were widened: the reach-in detector reads `ast.Import` (with and
without `as`) and resolves relative imports; the write detector builds module
handles from both import spellings. Demonstrated against the real detectors first:

```
from film_pipeline.studio._persistence import x     -> 1 finding
import film_pipeline.studio._persistence as secret  -> 0 findings (before)
from film_pipeline.studio import runtime as rt_mod
rt_mod._RUNTIME = object()                          -> 0 findings (before)
```

Measured after: the **same** two private modules, the same two private symbols, no
attribute writes. So B2's own prediction — "the guard can stay green while a new
private dependency appears" — is a real gap in coverage but not a live
concealment, and the docstring says so rather than implying a cleanup happened.

Two limits are **asserted in the tests** instead of assumed:
`importlib.import_module`/`__import__` (runtime strings), and a bare
`from pkg import name` (ambiguous: module handle or function, indistinguishable
without importing).

### B3 — the gate enforces nothing, and now it enforces once

Confirmed at the CLI: `enola check --help` says `--fail-on` defaults to none, and
the documented command printed *"nothing enforced: no policy set"* while exiting
0. **Every "Enola exit 0" receipt recorded by the earlier program was therefore
evidence of nothing.** That includes receipts in doc 09's implementation section.

Fixed in three parts: `make enola` passes `--fail-on=cycles`; the policy is also
stated in `enola-config.yaml` (which this CLI does not read — verified, and
recorded so the setting is not mistaken for enforcement); `make enola-baseline`
re-pins from a **clean** HEAD and refuses a dirty tree, which is how the previous
baseline came to be dated `dirty: true` three days and a rename behind.
`AGENTS.md` is corrected: it claimed cycles were the default policy.

The baseline is now pinned at `7895d8c` and the gate reports **"PASS — no
architectural change"** with a live policy.

**What this gate still cannot do**, stated because the audit's criterion asked for
a green enforcement run and that is not the same as a cycle check: injecting a new
sibling cycle on the current tree still exits **0**. A baseline pinned from the
same commit cannot catch a change to that commit. The cycle check is the
architecture test, proven above; this gate catches drift from the pinned state.

### B4 — the reach-in was real, and redundant

Characterized before changing anything:

```
get_project() is runtime.projects[id]   -> True
rt.projects['p'] = active               -> changed nothing (self-assignment)
active['current_phase'] = 'MUTATED'     -> runtime already saw it
```

So all ten write sites were redundant; the defect was that the write was the only
place the intent appeared, with persistence and audit optional and no guard able
to see the difference. `RuntimePort.apply_project_state` is that intent as one
operation and persists in the same call; ten sites use it (4 `mcp`, 6
`orchestration/execution.py`), `GraphHost` declares it, and
`test_boundary_law.py` fails on any new `runtime.projects[...] = …` outside
`studio`.

`get_project` still returns the live mapping, deliberately: making it copy would
change every caller to fix what the named operation already solves, and
`test_the_live_mapping_is_shared_and_the_operation_says_so` fails if that changes.
The audit's requested boundary characterization is
`tests/integration/test_boundary_state_ownership.py`: one state-changing action at
`MCPServer.call`, asserting the reported state reaches durable storage, that a
refused action leaves state untouched, and that the operation refuses an unknown
project.

### B5 — mostly done; one part reverted, with the reason

`test_declared_private_exports_do_not_grow` records the 51 names per package and
fails on growth or a stale row. Measured: **none has an importer outside its own
package, and 36 have no importer at all.** That is a narrower finding than this
document's "the surface is not truthful": they are intra-package names a grouped
`__init__` publishes for its own callers, kept out of the documented surface by
the underscore.

**`mcp.tools.get_runtime` was left in place.** It has no production consumer — no
`src` module imports it from the facade, and `mcp.server` reads the accessor from
`studio.runtime` — so removing it is right in principle. I removed it, migrated 49
test patch sites to the owner, and **reverted**: the suite went order-sensitive
(different tests failing in different orders across runs, everything passing in
isolation and on the pristine tree). The correct change removes the export and
migrates the fixtures *together*, in one slice, running the full suite between
steps. It is recorded here so the next attempt does not repeat the blind version.

### Verification on these slices

- `make ci-check` after each commit; at the tip 2,375 passed, 8 skipped, 1 xfailed,
  92.74% coverage, build and product gate pass.
- `uv run ruff format --check`, `uv run ruff check`, `uv run mypy src tests`: clean
  over 517 files. One commit (`46a2c0b`) exists only to fix a test-file annotation
  that `mypy src` cannot see — `src` and `tests` must be checked together.
- `make enola`: exit 0, with `--fail-on=cycles` and a baseline pinned at `7895d8c`.
- Acceptance proofs, all by injection and each reverted in the same run: B1 (cycle
  test exits 1), B2 (four import forms, previously invisible), B4 (the guard fails
  on a synthetic `rt.projects[...] = …`), B5 (a new private export fails both
  ratchets).

### Still open

- **The orchestration cycle is unfixed.** Removing it means giving
  `orchestration.nodes` and `orchestration.subgraphs` a shared module below both,
  which is a structural change to the QC path.
- **`mcp.tools.get_runtime` remains exported**, as described above.
- **`get_validation_report`'s live fallback and the QC failure channel** were
  closed by doc 09's slices, not by this document.
- **B3's gate is a drift check, not a cycle check.** Keep both.

## Adversarial review round

Date: 2026-09-29, after the implementation above. Six independent reviewers were
given the branch with different lenses — correctness, test-vacuity, guard
self-audit, MCP contracts, persistence, hygiene — each told to reproduce what it
claimed and to report its own injections. **Every issue below was then reproduced
here before being fixed**, and the ones that were not real are recorded as such.

The pattern worth keeping: the reviewers found five defects in *my own* work, and
four of them were guards or tests that could not fail.

### Fixed — behaviour

**R1. A stale `provider` string wrote a terminal ledger state.**
`GenerationExecutor.poll_row` routed an unregistered provider through `_poll_row`,
which wrote `FAILED` — terminal — so a row whose `provider` merely named something
not yet registered could never be polled again once it was. Reproduced: after an
error response the row read `failed / wait_human / unknown_provider`, and
`is_terminal(...)` was `True`. `origin/main` pre-checked the adapter and left the
row untouched. Now `poll_row` raises `GenerationRowProviderMissing` before any
write, the row is unchanged, and the error text matches `origin/main`
(`"Provider 'x' not registered."`). Pinned by
`test_unregistered_provider_leaves_the_row_pollable`, which also proves the row
still delivers once the provider exists.

**R2. A validator that crashed discarded every report that succeeded.** The handler
returned an error for the whole run, so a phase with two validators where one
raised produced a failed action and no evidence of the other's findings. The
*contract* stays as it was — a crashing validator fails the action, which
`test_run_validation_exception` pins — but the error now carries `reports`,
`saved_refs` and `validator_failures`. The frozen envelope for an ordinary pass is
unchanged, so `test_run_validation_report_and_ref_shape` still holds.

**R3. `_validation_failures` was reported and then dropped.** `run_validation` read
the channel into its outcome and never wrote it back, even though it is registered
`full` in `ORCH_CHANNELS` and the QC path carries it — so a later reader of project
state saw a clean pass. Reproduced: `outcome.failures == ('Boom: kaboom',)` while
`project["_validation_failures"]` was `None`. Now carried back.

**R4. `validation_report_refs` grew without bound** while `_validation_reports` was
replaced, so the branch's own invariant (`len(refs) == len(reports)`, asserted by
`_assert_evidence_is_durable`) held only on the first call. Reproduced: three runs
gave `refs=1,2,3` against `reports=1,1,1`. The channel now describes the latest
pass. Pinned by `test_refs_do_not_grow_across_passes`.

### Fixed — guards that could not fail

**R5. The cycle guard ignored relative imports.** `visit_ImportFrom` returned early
on `node.level`, so a real cycle spelled `from ..nodes import _x` was invisible
while the identical absolute spelling was reported — and `test_boundary_law.py`
resolved relative imports correctly all along, so the two guards disagreed about
the same file. Reproduced with a synthetic two-package cycle: relative spelling
`[]`, absolute spelling `[['mcp.tools.bibles', 'mcp.tools.generation',
'mcp.tools.bibles']]`. Relative imports now resolve against the importer's own
module, and both spellings report the same cycle.

**R6. `_root_self_imports()` measured 2 sites against a ceiling of 556.** The
filter split the rendered entry on `": "` and counted dots in what remained — but
`_self_edge_sources` emits `"{path}: imports {module} by full name"`, so the
"module" half was the whole sentence and its dot count was 2, never 3. Every real
site was rejected; the guard's own `assert found` passed on two accidental
survivors; an injected 554 sites of the exact shape it polices left it green. The
primitive is now the structured `(path, module)` pair with the string form as a
projection, the count is the measured **98**, and the ceiling is **100**.

**R7. The live-state guard missed the bypass it was written for.** It matched only
`X.projects[...] = ...`; the review walked past it with
`active = ctx.project_state(); active[pid] = state` — the same defect by the
route the finding itself describes, because `project_state()` hands back the live
mapping. Now matches a replacement on any name bound from
`project_state()`/`get_project()`/`get_active()` in the same function, verified by
injecting that exact bypass. Field writes (`active["idea"] = …`) are excluded by
key, and `cli/driver.py` is recorded in `KNOWN_LIVE_STATE_MUTATIONS` as the one
benign shape (headless composition root).

**R8. `test_a_state_changing_action_persists_what_it_returns` could not fail.**
Deleting `persist_project_state` from `apply_project_state` left all five tests in
the file green, because `create_project` had written a record earlier in the same
call. Replaced by `test_the_operation_persists_in_the_same_call`, which snapshots
the record, changes the state, calls the operation, and requires the file to
change — it fails when the persist line is removed.

### Not fixed, deliberately

- **`make enola` reports exit 2 whatever `enola` returned.** That is GNU `make`
  semantics, reproduced on a two-line probe makefile, not a defect in the recipe:
  the real status is printed on the `enola exit N` line. The target now says so at
  the call site, since `make` cannot distinguish regression (1) from declined (3).
- **`enola-baseline` will pin a baseline that launders an existing cycle.** Its
  precondition is tree cleanliness, which is orthogonal. This is the documented
  property of a pinned baseline (see the config comment and AGENTS.md), not a bug
  in the target.
- **A raised `KNOWN_PRIVATE_REACH_INS` row with matching new reach-ins is
  invisible.** Inherent to a per-row ratchet, and a reviewer sees the row edit.
- **`mcp.tools.get_runtime` remains exported**, for the reason recorded above.

### Reviewers' claims not reproduced

- "`_inherent_nesting_only` filters real cycles" — brute-forced over 16,204 cyclic
  graphs of 4 and 6 nodes: none contained a sibling edge, so none was suppressed.
- "The injected-cycle acceptance test re-implements the detector" — it calls
  `_cycles`/`_mutual_pairs`/`_inherent_nesting_only` from the module under test;
  only the input graph is synthetic.
- "The MCP tool surface changed" — 75 tools on both revisions with zero field
  differences across name, group, description, args schema, and all four flags.
- "Report-artifact versioning disturbs other consumers" — candidate refs only, and
  repeated runs accumulate distinct versions without clobbering.

### Verification

`make ci-check` 2,379 passed, 8 skipped, 1 xfailed, 92.68% coverage, product gate
PASS. `uv run mypy src tests` clean over 517 files. `make enola` exit 0. The graph
counts in the section above were re-measured after these fixes and are unchanged:
**37 nodes, 174 edges, 5 components, 1 real cycle.**
