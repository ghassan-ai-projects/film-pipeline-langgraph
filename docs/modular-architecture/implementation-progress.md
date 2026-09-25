# Implementation progress

Updated: 2026-09-25

## Current direction

The user approved the 20-module migration after the independent review and
asked for minimal-effort, highest-value rounds. Behavior must stay stable until
the migration is complete. Enola's measured findings are the structural
burndown signal; a round must not adjust filters or thresholds to lower counts.
The 21-phase historical roadmap is input, but its stale source paths and
behavior-changing acceptance clauses do not override this direction.

Order the remaining work by dependency and measured value: finish C-05's MCP
cycle, establish the pure `filmspec` vocabulary, then migrate duplicate owners
into `storage`, `projects`, `operations`, `studio`, `governance`, and
`orchestration` as their boundaries become ready. Keep existing packages
(`schemas`, `config`, `kb`, `constraints`, `providers`, `checkpoints`, `agents`,
`validation`, `generation`, `post`, and `mcp`) and add `budget` and
`devharness` only when their current responsibilities are ready to move.
Each round names the source and consumers and gets its own commit. From F-02
onward, tests and Enola were not run by user direction; R2-01 measured the tree
and found the gate **red**, and repaired it (see the R2-01 row). Every round
from R2-02 onward runs its own focused proof, the full `make ci-check`, and its
own Enola check before commit; a round with a red gate is not complete.
The last measured Enola result applies only to `7254827`. The
R-01b through R-01e behavior repairs remain deferred.

This log tracks implementation slices from the reviewed direction in
[06 — independent review and architecture decision](06-independent-review-and-decision.md).
It does not turn the superseded 20-module proposal into an execution plan.

## Per-slice quality gates

Each slice records its owner, consumers, review evidence, behavior tests, full
`make ci-check` result (including coverage of at least 90%), Enola result
against a comparable baseline, self-review, and commit. Earlier slices used
three independent review lenses; the current round records self-review only.
Focused
test runs use `--no-cov`; only the full suite establishes the coverage gate.

Enola checks use the docs-local snapshot at `enola-out/` with
`enola-config.yaml`. The default `.enola` baseline is stale and incomparable;
it is not a passing result. Enola currently checks cycle deltas only because no
layer intent is declared. Package ownership is reviewed against the approved
direction and tested at consumer boundaries.

## Migration-first directive and Enola burndown

The current priority is to complete the evidenced module-boundary migrations
before repairing the known behavior divergences. R-01b through R-01e remain
deferred until the migration exit bar is met.

The reviewed Enola receipt at `fb85baa` contains 115 insights: 5 directory-level
cycle findings (C1–C5) and 110 heuristic insights. The migration target is zero
cycle findings, matching §5 Step 4 of the approved decision. The current layer
count of zero is not evidence of a boundary pass because no layer intent is
declared. Heuristic insight counts are recorded separately from architecture
gate findings; Enola filters or thresholds must not be changed just to lower
the displayed count.

| Enola measure | Baseline | Migration target | Current status |
|---|---:|---:|---|
| Directory-level cycle findings | 5 (C1–C5) | 0 | Last measured: 0 at `d86db22`; current tree unmeasured |
| Declared layer violations | Not measured; no layer intent | No violations for any adopted rule | Not measured |
| Heuristic insights | 110 | Track by explainer; not the cycle gate | Last measured: 112 at `d86db22`; current tree unmeasured |

V-01 removed the measured `config → providers` import edge. The live Enola
report resolved one dependency-depth insight (115 to 114 total insights,
including 109 current heuristic insights) and introduced no finding. The check
ran at 20:07 UTC with:

```sh
enola check --json --baseline=docs/modular-architecture/enola-out docs/modular-architecture/enola-config.yaml
```

The checked-in receipt remains the pinned 115-insight baseline. C-01 removed
C1. Its live check at 18:32 UTC (20:32 CEST) was clean with four cycle insights and 115 total
insights (111 heuristic insights). It resolved C1 and the prior config
dependency-depth insight; the changed prompt-template dependency path produced
a new dependency-depth advisory, so the aggregate insight count stayed level.
No Enola filter or threshold changed.

C-02 removed C4. Its committed-tree check at 21:08 UTC was clean with three
current cycle insights and 114 total insights (111 heuristic insights). The
live cycle count fell from four to three, with no new finding; the pinned
receipt remains unchanged and no Enola filter or threshold changed.

C-03 removed C5. Its committed-tree check at 21:26 UTC was clean with two
current cycle insights and 112 total insights (110 heuristic insights). The
live cycle count fell from three to two, and one dependency-depth advisory
resolved; no finding was added. The pinned receipt remains unchanged and no
Enola filter or threshold changed.

## Progress ledger

| Slice | Scope | Review | Focused proof | Full gate / coverage | Enola | Commit | Status |
|---|---|---|---|---|---|---|---|
| G-01 | Reference extraction: immutable phase sequence, graph destinations, app/CLI/resume consumers, and callable-registry parity | Three independent lenses complete; all findings addressed | Graph/app/CLI/dynamic-routing subset passed | PASS — `make ci-check`; 2,008 passed / 8 skipped; 91.62% coverage | PASS — comparable baseline; 0 cycle findings added or removed | `62b3eea` | Complete |
| O-01 | Freeze operator-path behavior at MCP call and stdio boundaries; compare graph/MCP validation and blocked-generation behavior | Three independent lenses complete; all findings resolved | PASS — 14 passed / 11 strict xfailed; `--runxfail` confirms all 11 fail at their intended divergences | PASS — `make ci-check`; 2,022 passed / 8 skipped / 11 xfailed; 91.69% coverage | PASS — clean against comparable baseline; no cycle findings changed | `8900416` | Complete |
| R-01a | Migration only: move checkpoint rollback manager orchestration and bookkeeping from MCP tools into `OperatorService` / app services while preserving active-project selection, confirmation, errors, and response projection | Three independent final reviews pass; first-round findings addressed | PASS — 63 passed / 10 strict xfailed across checkpoint service, MCP checkpoint, and O-01 divergence suites | PASS — `make ci-check`; 2,023 passed / 8 skipped / 11 xfailed; 91.69% coverage | PASS — docs-local snapshot baseline; clean, no cycle delta | `e5a74dc` | Complete |
| V-01 | Migration only: keep profile resolution/spec normalization in `config`; move credential policy and adapter composition behind providers/app services | Three final lenses pass; initial guard/test-fixture findings addressed; final audit has no remaining findings | PASS — six changed suites; all pass | PASS — `make ci-check`; 2,027 passed / 8 skipped / 11 xfailed; 91.71% coverage; source/wheel builds and product gate pass | PASS — live docs-local check at 20:07 UTC; clean, 0 new findings, 5 cycles unchanged, 1 dependency-depth finding resolved (114 total / 109 heuristic vs. 115 / 110 baseline); pinned receipt unchanged | `8fa6890` | Complete |
| C-01 | Break C1: `agents/prompt_templates` ↔ `agents/prompt_templates/defaults`, preserving the prompt-template public contract | Three final lenses pass; all first-round findings addressed | PASS — focused registry/identity suite | PASS — `make ci-check`; 2,029 passed / 8 skipped / 11 xfailed; 91.71% coverage; source/wheel builds and product gate pass | PASS — live docs-local check at 18:32 UTC; clean, 0 new findings, C1 removed (5→4 cycles); 115 total / 111 heuristic vs. 115 / 110 baseline; pinned receipt unchanged | `261f4a1` | Complete |
| C-02 | Break C4: `providers` ↔ `providers/adapters`; app owns adapter construction; preserve `providers.adapters` exports and builder behavior | Three plan reviews and three final implementation reviews pass; review findings addressed | PASS — all seven changed suites; builder IDs/aliases, full capabilities, defaults, copy isolation, and unsupported-ID behavior covered | PASS — `make ci-check`; 2,041 passed / 8 skipped / 11 xfailed; 91.73% coverage; source/wheel builds and product gate pass | PASS — committed-tree check at 21:08 UTC; clean, C4 removed (4→3 current cycles), no new finding; 114 total / 111 heuristic vs. 115 / 110 pinned baseline | `d02e439` | Complete |
| C-03 | Break C5: `schemas` ↔ `schemas/registries`; keep registry records owned/exported by `schemas.registries` | Three plan reviews and three final implementation reviews pass; findings addressed | PASS — schema contract and import-boundary suites; registry exports and import forms covered | PASS — `make ci-check`; 2,043 passed / 8 skipped / 11 xfailed; 91.73% coverage; source/wheel builds and product gate pass | PASS — committed-tree check at 21:26 UTC; clean, C5 removed (3→2 current cycles), no new finding, one dependency-depth advisory resolved; 112 total / 110 heuristic vs. 115 / 110 pinned baseline | `efd451e` | Complete |
| C-04 | Break C3: `graph` ↔ `graph/nodes` ↔ `graph/orchestrator_validators` ↔ `graph/subgraphs`, preserving callable and state contracts | Three plan and three implementation lenses pass; no remaining findings | PASS — 184 passed / 2 skipped / 10 xfailed across changed graph/app suites; moved graph factory compiles | PASS — `make ci-check`; 2,050 passed / 8 skipped / 11 xfailed; 91.73% coverage; strict mypy, source/wheel builds, and product gate pass | PASS — committed-tree check at 22:06 UTC; clean, C3 removed (2→1 cycles), no new findings; 113 total / 112 heuristic vs. pinned 115 / 110 | `1e3bf33` | Complete |
| C-05 | Break C2: move product gate to CLI, then move MCP registry assembly out of the eager tool facade | First cut reviewed; final self-review below | PASS — 430 MCP/CLI/graph tests with 1 skip and 11 expected failures; facade identity checked | PASS — `make ci-check` with offline build; 2,058 passed / 8 skipped / 11 xfailed; 91.72% coverage | PASS — clean against pinned baseline; 0 current cycle findings, 112 current insights versus 115 pinned and 113 before this round | `d86db22` | Complete |
| F-01 | Establish `filmspec` ownership of `FilmPhase`, immutable phase order, and successor; preserve schema/graph aliases | Self-review below | PASS — 5 phase tests, including identity and all successor edges | Same full gate as C-05 | Included in C-05 Enola check; no new cycle | `d86db22` | Complete |
| F-02 | Move pure artifact, agent, generation, validation, and issue enum vocabularies into `filmspec`; preserve schema aliases | Source owner and aliases inspected | Compatibility alias cases added, not run by user direction | Not run by user direction | Not run by user direction | `8085f3b` | Migrated; verification deferred |
| F-03 | Move phase gate, provider-dependence, and transition vocabularies into `filmspec`; preserve graph and schema aliases | Source tables and consumers inspected | Compatibility and phase-set cases added, not run by user direction | Not run by user direction | Not run by user direction | `0f7ba2a` | Migrated; verification deferred |
| S-01 | Move `schemas._base` to public `schemas.base`, retarget production imports, and keep explicit old-path aliases | Mechanical source import inventory; no old-path source import remains | Alias cases added, not run by user direction | Not run by user direction | Not run by user direction | `227eccc` | Migrated; verification deferred |
| P-01 | Move project reference resolution from MCP to `projects`; keep MCP aliases and retarget server | Pure resolution module inspected | Alias identity case added, not run by user direction | Not run by user direction | Not run by user direction | `15124c9` | Migrated; verification deferred |
| G-02 | Move pure review action policy into `governance`; keep review aliases and retarget package generation | Pure policy module inspected | Alias identity case added, not run by user direction | Not run by user direction | Not run by user direction | `224a6cc` | Migrated; verification deferred |
| ST-01 | Move canonical project/phase/media path layout into `storage`; keep artifact path aliases and retarget store consumers | Pure path owner and direct consumers inspected | Alias identity case added, not run by user direction | Not run by user direction | Not run by user direction | `9e94779` | Migrated; verification deferred |
| ST-02 | Move artifact ID validation and sanitization into `storage.contract`; preserve registry aliases and retarget store/MCP consumers | Identifier helpers and consumers inspected | Alias identity case added, not run by user direction | Not run by user direction | Not run by user direction | `e3c9c93` | Migrated; verification deferred |
| G-03 | Move review package generation and artifact diff into `governance`; keep review aliases and retarget MCP | Review modules and consumers inspected | Alias identity case added, not run by user direction | Not run by user direction | Not run by user direction | `d1344d5` | Migrated; verification deferred |
| OP-01 | Move operator view models and service errors into `operations`; preserve app-service aliases and retarget consumers | Leaf contracts and imports inspected | Alias identity case added, not run by user direction | Not run by user direction | Not run by user direction | `42b9aa5` | Migrated; verification deferred |
| ST-03 | Move immutable `KindSpec` and renderer type into `storage.contract`; preserve registry aliases and retarget store | Registry value object and consumers inspected | Alias identity case added, not run by user direction | Not run by user direction | Not run by user direction | `d10c18b` | Migrated; verification deferred |
| DH-01 | Move mock actors, in-memory Git, storage fixtures, and scenarios into `devharness`; keep `testing` aliases and wheel content during behavior freeze | Harness source modules inspected | Alias identity case added, not run by user direction | Not run by user direction | Not run by user direction | `0167bd9` | Migrated; packaging seal deferred |
| R2-01 | Repair the tree so the quality gate can run again: fix the broken test collection, the strict-mypy re-export errors, and the shim surfaces that caused them | Independent audit of the whole tree; no behavior change claimed | PASS — review, governance, testing, devharness, graph-boundary, and artifact suites; full `pytest --collect-only` over `tests/` | PASS — `make ci-check`; 1,986 passed / 7 skipped / 11 xfailed; 91.75% coverage; strict mypy, source/wheel builds, product gate | PASS — live docs-local check at 23:34 UTC; clean, zero cycle findings; 8,240 facts | `7254827` | Complete |
| R2-02 | Retire the `testing` compatibility package now that `devharness` owns the harness; retarget consumers and repair the startup-boundary guard that still watched the old path | Full-tree audit of shim consumers; every caller was a test, none in `src/` | PASS — conftest, e2e conftest, five artifact suites, graph startup-boundary suite, consolidated harness suite | PASS — `make ci-check`; 2,064 passed / 8 skipped / 11 xfailed; 91.75% coverage; strict mypy, source/wheel builds, product gate | PASS — clean, zero cycle findings | `bfc5106` | Complete |
| R2-03 | Replace nine hand-written alias-identity test modules with one suite derived from each alias's own export list | Verified the two suites were the same behaviour and the test tree was organized opposite to code ownership | PASS — 53 derived alias cases plus importability checks; governance behavior suites run from their new owner-aligned location | PASS — `make ci-check`; 2,100 passed / 8 skipped / 11 xfailed; 91.75% coverage; strict mypy, source/wheel builds, product gate | PASS — clean, zero cycle findings | `452f0b0` | Complete |
| R2-04 | Give the three duplicated runtime rules one owner: the stale-generation-request codes (3 copies), the text-only request row (2 copies), and the markdown-fence unwrapper (2 copies) | Reproduced all three against current source with `path:line` anchors before changing anything | PASS — filmspec vocabulary suite and generation review-parsing suite, including producer/consumer agreement and both-generation-path parity | PASS — `make ci-check`; 2,119 passed / 8 skipped / 11 xfailed; 91.87% coverage; strict mypy, source/wheel builds, product gate | PASS — clean, zero cycle findings | `9c8e1ae` | Complete |
| ST-04 | Complete the `storage` ownership move: relocate the artifact store, envelope, manifest, registry, project storage, renderers, layout, and serialization out of `artifacts`; retarget every consumer; keep `artifacts` as an identity-preserving facade | Independent plan with a scratch-copy dry run that reproduced two breakages before implementation | PASS — full suite; new `test_module_ownership.py` proves facade identity and single layout ownership; `langgraph.json` entrypoint imports | PASS — `make ci-check`; 2,150 passed / 8 skipped / 11 xfailed; 91.91% coverage; strict mypy, source/wheel builds, product gate | PASS — clean, zero cycle findings | `5a9819d` | Complete |
| R2-05 | Make weak assertions prove the behavior they name: two assertion-free git tests, an assertion-free import smoke test, a checkpointer test that never inspected the checkpointer, and a node test that never called the node; cover the three untested defensive branches in `graph/consistency.py` | Full-suite audit of assertion quality; each change verified against real behavior rather than assumed | PASS — checkpoints, graph, smoke, and new consistency suites; `graph/consistency.py` reaches 100% | PASS — `make ci-check`; 2,162 passed / 8 skipped / 11 xfailed; 91.95% coverage; strict mypy, source/wheel builds, product gate | PASS — clean, zero cycle findings | `d726df1` | Complete |
| D-02 | Correct `05-enforcement-and-guard-tests.md`: state that the guard suite was never implemented, and fix the false "exactly four `ast.parse` test files" measurement | Verified every claim against the tree: `tests/architecture/` absent, `architecture.py` absent, zero `ModuleContract` occurrences, 15 of 16 guards missing, measured count 8 not 4 | Documentation only; no test run required | N/A — docs-only change | N/A | `ef2fa73` | Complete |
| P-02 | Move project classification policy (folder-name kind rule, explicit-kind validation, derived title) from `app/services/_project_discovery.py` into `projects.classification`; keep the runtime-coupled discovery helpers in app | Verified the pure half has no runtime dependency and that removing it deletes one of the four FES #3 blockers | PASS — new classification suite covering the substring rule, canonicalization, actionable error, precedence, and owner re-export | PASS — `make ci-check`; 2,187 passed / 8 skipped / 11 xfailed; 91.97% coverage; strict mypy, source/wheel builds, product gate | PASS — clean, zero cycle findings | `018babb` | Complete |
| OP-02a | Break FES #3 without moving `OperatorService`: declare `operations.ports.RuntimePort` structurally, widen `_persistence.storage_for`/`artifact_root` to the port, and guard that no `operations` module imports `film_pipeline.app` | Plan review found the move as originally briefed would materialize a forbidden edge; verified the remaining coupling is only `runtime.services.artifact_store` | PASS — new runtime-port suite: protocol conformance for the real runtime and a fake, store/absent-services branches, and a source-level FES #3 guard with mutation cases | PASS — `make ci-check`; 2,200 passed / 8 skipped / 11 xfailed; 92.00% coverage; strict mypy, source/wheel builds, product gate | PASS — clean, zero cycle findings | `ea0df4e` | Complete |

### OP-02 — why the round was rescoped

The ledger previously listed "move `OperatorService` and its helper operations
out of `app/services` into `operations`" as a single round. Planning it found
that the move as briefed **cannot be done legally**: `03` §4.6.1 names
`operations → studio` as forbidden edge #3, and the four imports the move would
carry are exactly the four sites that section lists under "Removed by".

Because the edge law has no mechanical enforcement (`tests/architecture/` does
not exist), that violation would have landed silently. The round was therefore
split:

- **OP-02a (done, `ea0df4e`)** removes the runtime coupling structurally
  instead of relocating it. `operations.ports.RuntimePort` declares what the
  operator surface needs; `StudioRuntime` conforms without subclassing; the two
  persistence helpers accept the port. A source-level guard now fails if any
  `operations` module imports `film_pipeline.app`.
- **OP-02b (remaining)** is the physical file move. It is now unblocked for
  `_browse_ops`, `_checkpoint_ops`, and `_generation_ops`, but `operator.py`
  still imports `film_pipeline.app._provider_profiles` and the runtime
  accessors `get_runtime` / `reset_runtime`, which the port does not yet cover.
  Those need the same treatment before the move, and the `_project_discovery`
  helpers must reach `projects` rather than `operations`.

### R2-01 — the gate was broken, not merely unverified

F-02 through DH-01 recorded "not run by user direction" and were therefore
never actually validated. R2-01 measured the tree and found it **red**: three
independent defects that made `make ci-check` impossible to pass, all of them
consequences of the migration rounds themselves.

1. **The whole test suite could not be collected.** `tests/unit/review/test_diff.py`
   imported the private `_id_stem` from `film_pipeline.review.diff`, a four-line
   alias module created by G-03 that never carried the private helper. pytest
   aborted collection with `ImportError`, so *no* test in the repository could
   run. Fixed by importing from the owner, `film_pipeline.governance.diff`,
   which is the same pattern the other alias tests use.
2. **Strict mypy failed with 16 errors in six files.** `graph/_action_routing.py`
   bound `APPROVAL_GATES` through a plain `import ... as`, which mypy does not
   accept as an explicit re-export, and the five `testing/*` shims re-exported
   standard-library names (`Path`, `dataclass`, `field`, `Any`, `StrEnum`) that
   merely leaked out of the `devharness` modules they alias.
3. **The shim surfaces were wider than any consumer needed.** The `testing/*`
   shims now re-export only the symbols that are actually used and declare
   `__all__`. Object identity is unchanged, and the removed names had no
   consumer in `src/`, `tests/`, or `scripts/`.

The behavior freeze held: no functional code path changed, and the diff is
limited to import surfaces. The Enola check is clean against the docs-local
receipt with zero cycle findings.

A full-tree audit run alongside this round also corrected two premises that
later rounds depended on, and they are recorded here rather than in a chat log:

- `src/film_pipeline/testing/*.py` are **alias shims, not duplicate copies**.
  `git show --stat 0167bd9` shows the modules were reduced, not added
  (`testing/in_memory_git.py | 202 +--------------------`); today every line is
  an `X as X` re-export, and they have live consumers in `tests/`. They are
  retarget-first material, never "delete as duplicated".
- `src/film_pipeline/schemas/_base.py` is **not a pure shim** despite being
  small: it has roughly 90 import sites, including four under `scripts/` that
  pytest never executes and that would therefore break silently. It is the most
  expensive retarget in the repository and must be scheduled late, not early.

## Remaining migration work

The target module names now exist except `budget`, `orchestration`, and
`studio`. Presence is not completion: several newly created packages own only
their pure contracts while stateful code still lives at the old path. The next
rounds should keep existing behavior and use the lowest-risk dependency order:

1. Move the remaining artifact registry, envelope, store, manifest, and project
   storage implementation into `storage`, retaining read/write format and old
   import aliases. Then move project discovery and the active-project authority
   into `projects`.
2. Move `OperatorService` and its helper operations out of `app/services` into
   `operations`, with MCP consumers retargeted and the existing runtime lookup
   behavior preserved during the move.
3. Move graph execution/composition into `orchestration`, and runtime,
   bootstrap, logging, and entry-point composition into `studio`. This requires
   a deliberate `langgraph.json` path migration and compatibility review for
   import-time checkpointer creation and persisted state.
4. Establish `budget` as the owner of the existing spend rules without
   changing ceilings or approval behavior. Complete the outstanding governance
   routing and generation/validation ownership moves after their callers use
   the new package boundaries.
5. Retarget test harness consumers to `devharness`, remove obsolete aliases
   after consumers are migrated, make the requested wheel exclusion, and align
   `AGENTS.md`, operator docs, and boundary guards with the delivered tree.

The production code still has compatibility modules under `artifacts`,
`app/services`, `graph`, `review`, `mcp.resolution`, `schemas._base`, and
`testing`. They are intentional migration shims for now; deleting them before
their consumers move would change imports. R-01b through R-01e remain behavior
repairs for after the migration.
| R-01b | Keep provider-blocked generation paused after approval in compiled graph and app fallback | Deferred behavior fix; not part of migration scope | Pending | Pending | Pending | Pending | Deferred until migration exit |
| R-01c | Share validation result handoff, issue identity, and QC row-patch persistence across graph, app, and MCP | Deferred behavior fix; not part of migration scope | Pending | Pending | Pending | Pending | Deferred until migration exit |
| R-01d | Read and write MCP stdio as newline-delimited JSON at the process boundary | Deferred behavior fix; not part of migration scope | Pending | Pending | Pending | Pending | Deferred until migration exit |
| R-01e | Make graph/checkpointer bootstrap explicit and unify persistence root/mode selection while preserving `langgraph.json` loading | Deferred behavior fix; not part of migration scope | Pending | Pending | Pending | Pending | Deferred until migration exit |
| B-01 | Review and migrate the remaining measured import-boundary debt against `AGENTS.md` and the approved ownership map; make no package-count-driven moves | Pending boundary inventory and three lenses per seam | Pending | Pending | Pending | Pending | Queued after cycle burndown |
| D-01 | Align product documentation with exercised operator behavior | Not started | Not started | Pending | Pending | Pending | Queued |

The C-01 through C-05 rows are a measured cycle burndown. The user has now
authorized the larger target migration. The remaining behavior repairs stay
deferred until the migration is complete. D-01 follows the relevant behavior
work so that it describes exercised behavior.

The user's Enola cycle exit bar is **zero total cycle findings**. C-05 meets
that bar; completing the graph slice alone did not.

## C-04 plan — graph composition and shared-owner imports

- **Owner and consumers:** move complete supervisor-graph construction to
  `app.graph_factory`, the existing composition layer. `graph` retains phase
  nodes, routing, state schema, service definitions, validators, and the QC
  subgraph. `graph.services` owns the runtime service context/accessor, and
  `graph.orchestrator_state` owns the human-approval policy read. Validators
  and subgraphs depend on these owners directly; they do not import
  `graph.nodes`.
- **Measured cycle:** Enola's C3 is
  `graph → graph/nodes → graph/orchestrator_validators → graph/subgraphs →
  graph`. `graph/graph.py` is the composition source that imports nodes and the
  QC subgraph. Nodes call validators; validator `brief.py` reaches back into
  the node package for service lookup and artifact-ref parsing. The QC
  subgraph also reaches into nodes for service lookup and approval policy.
  Removing the composition edge and the sibling-to-node helper imports breaks
  the measured cycle without adding a runtime package.
- **Code and tests:** moved `graph/graph.py` intact to
  `app/graph_factory.py`; update `langgraph.json` and every in-repository
  consumer. Do not leave a `graph.graph` forwarding module, which would restore
  an edge from `graph` to the app composition package. Preserve `build_graph`,
  `_default_checkpointer`, routing destinations, node callables, state
  channels, and the exported `graph` object. Move `_SERVICES_CTX` and
  `_get_services` into `graph.services`; preserve state-key-first lookup and
  ContextVar fallback when `_services` is absent. Extend the existing graph
  services test to prove both branches, and the existing app resume-integrity
  test to seed a prior ContextVar value and prove it is restored after an
  execution failure. Retarget
  app execution and node consumers to the service owner. Move
  `_require_human_approval` into
  `graph.orchestrator_state`; retarget node gate logic and QC. In validator
  `brief.py`, use `ArtifactRef.from_string` from the schema owner rather than
  importing the node package's `_parse_ref`. Remove the now-misowned private
  helper exports from `graph.nodes`. Extend the existing graph startup-boundary
  test with an AST rule that forbids direct graph modules from importing nodes
  or subgraphs, and forbids validator/subgraph modules from importing nodes;
  cover absolute, relative, and package-re-export/alias forms (including
  `from film_pipeline.graph import nodes as ...` and `from . import nodes`).
  Retarget existing builder,
  checkpointer, service-context, approval-policy, QC, routing, and gate tests;
  add no duplicate behavior tests and make no deferred behavior fixes.
- **Explicitly deferred behavior:** retain the current module-level
  `graph = build_graph()` and eager checkpointer selection, including any
  import-time filesystem effect. R-01e's explicit bootstrap and persistence
  policy repair stay deferred until after migration, per the user's
  migration-first direction. This move changes the composition owner/path only.
- **Deliberate import-path migration:** `film_pipeline.graph.graph` is removed;
  the application composition module is `film_pipeline.app.graph_factory`, and
  `langgraph.json` points to its `graph` object. All discovered in-repository
  code and entrypoint consumers will be migrated. There is no graph-level
  compatibility shim because that would recreate the C3 edge.
- **Files:** `graph/graph.py` (move), `app/graph_factory.py` (new),
  `langgraph.json`, `app/_graph_exec.py`, `app/smoke.py`,
  `graph/services.py`, `graph/orchestrator_state.py`,
  `graph/nodes/{__init__,_shared,_agent,_agent_artifacts,_context,_visual_matrix_coverage,approval,generation,prep,qc,visual,wrapup}.py`,
  `graph/orchestrator_validators/brief.py`, `graph/subgraphs/qc.py`,
  `tests/unit/graph/test_services.py`,
  `tests/unit/app/test_resume_integrity.py`, and the existing graph builder,
  context, gate, QC, phase-sequence, checkpointer, and end-to-end consumer
  tests.
- **Validation:** focused changed graph/app suites with `--no-cov -n 0`,
  `UV_CACHE_DIR=.uv-cache make ci-check` (coverage at least 90%, strict typing,
  build and product gate), `langgraph.json` entrypoint import, Enola against
  `docs/modular-architecture/enola-out`, and `git diff --check`. Close C-04
  only when all three plan and implementation lenses pass, all in-repo imports
  use the app composition owner, the C3 cycle is removed (2→1 current cycles),
  no cycle is added, and the full quality gate passes.
- **Plan and implementation reviews:** all six independent reviews passed with
  no remaining actionable findings. Boundary review confirmed removal of the
  measured C3 return path and coverage of the import forms; behavior review
  confirmed preserved callable and state contracts; quality review found no
  dead exports, weak or duplicate tests, or maintainability issue.
  **Implementation proof:** changed graph/app suites pass (184 passed,
  2 skipped, 10 xfailed), and the app-owned graph factory compiles.
  The first full-gate attempt stopped at Ruff on import ordering in eight
  retargeted test files; Ruff fixed these mechanical issues. The rerun passed
  the full gate with 91.73% coverage, and strict mypy, source/wheel builds, and
  the product gate passed. The committed-tree Enola check at 22:06 UTC was
  clean: C3 was removed, current cycles fell from two to one, and no cycle was
  added. The pinned receipt remains unchanged. Commit: `1e3bf33`.
- **Plan review detail:** boundary review required the user's migration-first
  priority to be recorded against the R-01e sequencing recommendation; the
  existing eager checkpointer behavior remains deliberately deferred. Behavior
  review required tests for state-first service lookup, ContextVar fallback,
  and exact restoration of a prior context value after failure. Quality review
  required package re-export and alias cases in the AST guard. All findings were
  resolved before implementation.

## C-05 plan — move the repository product gate out of app

- **Measured cycle:** the remaining cycle is Enola C2, the seven-member path
  `app → app/services → mcp → mcp/tools → mcp/tools/bibles →
  mcp/tools/generation → mcp/tools/reference_generation → app`, documented in
  `enola-architecture-facts.md` and audit 14. C-04 removed C3; the committed
  Enola check now reports one current cycle insight. A source census found the
  only app-to-MCP import in `app/product_gate.py`: it imports
  `mcp.contract.make_registry`. That repository-evidence checker is run by the
  Makefile and tested from `tests/unit/app/test_product_gate.py`; it is not
  part of app runtime or the operator service.
- **Owner and consumers:** move the complete checker to
  `cli/product_gate.py`, an outer command invoked by CI. The CLI layer may
  compose MCP's registry for the repo-level product check; app modules will
  have no MCP dependency. Preserve the checker and its current dependencies,
  manifest paths, return values, output, and stub detection. Retarget the
  Makefile command and move the existing product-gate tests to
  `tests/unit/cli/test_product_gate.py`, updating only import and monkeypatch
  paths. Update the focused test command in `documentation/release-process.md`
  to the new test path, and update `app/__init__.py` to drop its stale claim that
  app owns product gates. Remove `app/product_gate.py` without a forwarding
  shim, which would restore the cycle.
- **Boundary guard:** add an app-package AST guard forbidding
  `film_pipeline.mcp` imports across `src/film_pipeline/app`. Resolve absolute,
  relative, and package-re-export forms, including
  `from film_pipeline import mcp as module`. For a nested app package, parse
  `from ... import mcp` from `film_pipeline.app.services` and assert it resolves
  to `film_pipeline.mcp` through the filesystem-derived package path. Exercise
  these forms in focused resolver cases. This pins the single dependency
  direction needed to close C2; it does not add a general architecture
  framework.
- **Scope discipline:** do not alter MCP startup, tool schemas, runtime
  creation, operator service behavior, or the current test-visible injection
  hooks. The existing imports from MCP into app remain the established
  operator-to-service delegation path. No behavior repair is included.
- **Validation:** run the product-gate and app-boundary suites, all directly
  affected CLI/MCP startup and registry suites with `--no-cov -n 0`, then
  `UV_CACHE_DIR=.uv-cache make ci-check` (coverage at least 90%, strict typing,
  build and product gate), run `python -m film_pipeline.cli.product_gate`,
  Enola against `docs/modular-architecture/enola-out`, and `git diff --check`.
  Close C-05 only when all six reviews pass, no in-repository consumer uses the
  old path, the full gate passes, and committed-tree Enola is clean with zero
  total cycle findings. Search `src`, `tests`, `Makefile`, and the active
  release process for the old module/test paths. Keep the pinned receipt,
  filters, and thresholds unchanged.
- **Plan review:** all three independent lenses pass. Boundary review found the
  active release-process test command, now included in the migration and
  old-path search. Quality review found a relative-import example one level
  too shallow; the plan now specifies the correct nested target and requires
  asserting its resolution. Both findings were re-reviewed and resolved.
- **Implementation progress:** product gate and test were moved to `cli`; the
  Makefile and active release-process command now use the new path. The app
  boundary guard passes absolute, relative, package-re-export, and nested
  relative-import cases. The package description no longer assigns product
  gate ownership to app. Focused proof is 20 tests passing, the moved module
  prints `Product gate: PASS`, and the active old-path search is clean. All
  three implementation reviews pass for this cut. However, Enola still reports
  one cycle: `mcp` → `mcp/tools` → `mcp/tools/bibles` →
  `mcp/tools/generation` → `mcp/tools/reference_generation` → `mcp`. This
  remaining finding was wholly within the MCP package, so the app-to-MCP move
  alone did not meet the zero-cycle exit bar. The extension moved registry
  assembly from `mcp.tools.registry` to `mcp.registry` and made the tool facade
  lazy. A `.pyi` file preserves static callable types without eagerly loading
  every handler. The public facade, registry function, and test runtime hook
  retain their identities. Enola now reports zero cycles and 112 total insights
  against the original pinned 115. The full gate passed with an offline build;
  this avoids an unavailable PyPI DNS lookup without changing dependencies.

## Current round self-review

- The registry move deletes its old module and changes only its import owner.
  Runtime registration order remains the source order of the moved function.
- The lazy tool facade preserves `__all__`, `dir()`, callable identity, and the
  `tools.get_runtime` patch point. Focused MCP tests cover all operator paths;
  the new facade test checks the three formerly cyclic subpackages directly.
- `filmspec.FilmPhase` is the one class; `schemas.FilmPhase` is an alias.
  `PHASE_SEQUENCE` and `next_phase` are likewise aliases from the old graph
  path. No serialized value or routing result changed.
- No dead copy of the registry or phase enum remains. No duplicate behavior
  test was added; the new assertion checks export identity across the moved
  boundary. Known xfailed behavior is unchanged.

## V-01 plan

- **Owner and consumers:** `config.profile_resolver` keeps profile loading,
  stack canonicalization, project-config resolution, and provider-spec
  normalization. App composition owns creating/registering adapters and deriving
  the required provider IDs for a credential check. `providers.credentials`
  owns provider-to-environment-variable mapping and env/`.env` lookup.
  `OperatorService` exposes the app operations to MCP without giving MCP direct
  dependencies on provider implementations.
- **Planned code and tests:** move profile adapter registration and
  profile-aware credential checks out of config into a private app composition
  helper at `app/_provider_profiles.py`; keep `_provider_seeds.py` focused on
  default runtime providers. Replace the three registration call sites in
  `OperatorService`, MCP project creation, and profile-change approval, plus the project-creation
  credential call. Keep the real-mode gate, ordering, error DTO, empty-spec
  no-op, global runtime mutation, and approval flow unchanged. Retain existing
  provider-spec normalization tests; move credential-policy tests to the
  provider/app owner. Strengthen the existing service-create, MCP-create, and
  profile-approval tests to assert registration and health at their consumers;
  add only the missing app-composition and import-direction proofs in the
  existing config/provider/app/MCP test files. Keep the pre-resolution mock-ID
  scan separate because changing its parser or timing would expand this
  migration into an input-validation behavior change.
- **Files:** `config/profile_resolver.py`, `providers/credentials.py`,
  `app/_provider_profiles.py` (new), `app/services/operator.py`,
  `mcp/tools/projects.py`, `mcp/tools/_profile_change.py`,
  `tests/unit/config/test_profile_resolver.py`,
  `tests/unit/providers/test_credentials.py`,
  `tests/unit/app/test_provider_profiles.py` (new),
  `tests/unit/app/services/test_operator_service.py`,
  `tests/unit/mcp/tools/test_config.py`, and the existing project-creation
  contract cases in `tests/unit/test_mcp.py`.
- **Validation:** PASS — focused changed tests ran serially and passed;
  `UV_CACHE_DIR=.uv-cache make ci-check` passed (2,027 passed, 8 skipped,
  11 xfailed, 91.71% coverage, source/wheel builds, product gate); Enola's
  live check reported 114 total / 109 heuristic insights, five unchanged
  cycles, and zero new findings; `git diff --check` passed.
- **Migration exit bar:** config imports no app/provider modules; app owns the
  adapter and profile credential composition; providers owns credential
  lookup/mapping; all three call paths preserve their current registration,
  health, preflight, and response contracts; three final review lenses pass;
  full CI remains above 90%; Enola shows the `config → providers` package edge
  at zero and no new cycle. The overall cycle target remains zero and is tracked
  by C-01 through C-05, not claimed by V-01.

## V-01 review record

The boundary review found the first AST import guard missed relative imports
and imports re-exported through `film_pipeline`; the guard now resolves relative
levels and imported aliases, with regression cases for both forms. The behavior
review found the missing-key fixture needed to configure Seedance while
asserting both Google-key providers in profile order; project, provider, and
health state remain unchanged when preflight rejects creation. The quality
review confirmed the added coverage extends existing consumer tests without
duplication. All three final reviews passed. The focused changed suites and
full gate passed. The live Enola check exited clean at 20:07 UTC with no new
finding and one dependency-depth insight resolved; the checked-in receipt is
still the pinned baseline at `fb85baa`. The code is committed as `8fa6890`.

## C-01 plan

- **Owner and consumers:** `agents._prompt_template` owns the shared immutable
  `PromptTemplate` value object. The prompt registry and defaults keep their
  compatibility imports; defaults depend on a narrow registrar protocol rather
  than importing the concrete registry back from the parent package.
- **Planned code and tests:** move the dataclass without changing its fields or
  rendering behavior; update registry/default factories and the runner's
  type-only import to the shared owner; retain package and registry re-exports.
  Extend the existing registry suite to prove import identity, registry
  singleton reuse, the seven validator templates, and representative template
  identity across repeated registry loads. Do not freeze template iteration
  order, for which there is no caller contract.
- **Files:** `agents/_prompt_template.py`, `agents/prompt_templates/registry.py`,
  `agents/prompt_templates/defaults/{__init__,production,spine,validators}.py`,
  `agents/runner.py`, and
  `tests/unit/agents/test_prompt_template_registry.py`.
- **Validation:** focused registry/identity tests passed. Full
  `UV_CACHE_DIR=.uv-cache make ci-check` passed (2,029 passed, 8 skipped,
  11 xfailed, 91.71% coverage, source/wheel builds, product gate). The committed
  tree's comparable Enola check ran at 18:32 UTC / 20:32 CEST, was clean with
  four cycle insights and zero new findings; `git diff --check` passed.
- **Migration exit bar:** no import path from defaults back into the prompt
  registry; old public/registry imports still identify the same class; the C1
  cycle is removed; all three review lenses approve; full CI stays above 90%.

## C-01 review record

The boundary lens caught `agents/runner.py`'s `TYPE_CHECKING` import as a
remaining parent-package edge; it now imports from `_prompt_template`, and the
final Enola run confirms C1 is gone (five cycle findings to four). The behavior
lens confirmed that the legacy package and registry imports preserve class
identity and template loading. The quality lens rejected an insertion-order
assertion without a consumer contract. The first full check caught strict-mypy
implicit-reexport errors; an explicit `PromptTemplate as PromptTemplate`
re-export resolved them without changing the public export. All three final
reviews passed, with no remaining actionable finding.

The live Enola result is clean, with zero new findings. It resolved C1 and the
prior config dependency-depth insight; the updated prompt-template dependency
path adds a dependency-depth advisory. Therefore total insights remain 115
(four cycles and 111 heuristic insights), compared with the pinned 115-insight
receipt (five cycles and 110 heuristic insights). This change removes a cycle;
it does not claim the whole heuristic inventory declined. The checked-in
baseline remains pinned at `fb85baa`. Code commit: `261f4a1`.

## C-02 plan

- **Owner and consumers:** `app` owns adapter construction and registration
  composition. `providers.adapters` owns and exports the concrete adapters;
  provider contracts, credentials, pricing, and registry remain in `providers`.
  The approved `06` direction and V-01 already place runtime composition in
  `app`; no new phase package is introduced.
- **Measured edges:** the C4 cycle has both `providers/__init__.py`'s concrete
  Imagen re-export and `providers/factory.py`'s three imports of adapter
  implementations. Adapter modules also import provider base, credential, and
  pricing modules, which form the return edge. Removing only the package
  re-export would therefore leave C4 intact.
- **Planned code and tests:** move the builder body intact to
  `app/_provider_factory.py`, retarget profile/default seeding consumers and
  every in-repo test caller, and delete `providers/factory.py` without a
  forwarding shim. Remove `Imagen4GeminiProvider` from the root providers
  facade; keep all three exports in `providers.adapters`. Add one table-driven
  builder test for every supported provider ID/alias, concrete adapter class,
  default model and entry facts, plus the unsupported-ID error. Retarget the
  existing pricing test's adapter imports to the package exports and remove its
  now-duplicated Imagen factory-rate assertion. Add a focused import-direction
  guard so provider-root modules cannot reintroduce imports from the adapters
  subpackage.
- **Deliberate import-path migration:** `film_pipeline.providers.factory` and
  `film_pipeline.providers.Imagen4GeminiProvider` are removed. No in-repository
  consumer imports the root Imagen alias. The canonical adapter export surface
  remains `film_pipeline.providers.adapters`; builder signature, selected
  classes, provider aliases, entry defaults, and returned adapter behavior
  remain unchanged. A forwarding shim is excluded because it would recreate
  the measured providers-to-adapters edge.
- **Files:** `providers/factory.py` (moved), `providers/__init__.py`,
  `app/_provider_factory.py` (new), `app/_provider_profiles.py`,
  `app/_provider_seeds.py`, `tests/unit/app/test_provider_factory.py` (new),
  `tests/unit/providers/test_import_boundaries.py` (new),
  `tests/unit/app/test_provider_profiles.py`,
  `tests/unit/providers/test_pricing.py`,
  `tests/unit/mcp/tools/test_generation.py`,
  `tests/integration/test_reference_generation_mcp.py`, and
  `tests/unit/test_mcp.py`.
- **Validation:** run the focused changed suites with `--no-cov`, full
  `UV_CACHE_DIR=.uv-cache make ci-check` (coverage at least 90%), Enola against
  the docs-local receipt, and `git diff --check`. Close C-02 only when Enola
  removes C4 (four cycles to three), adds no cycle, and the full suite/build/
  product gate pass.

## C-02 plan review record

The boundary review found that removing only the root Imagen export would not
remove the measured edge: `providers/factory.py` imports all three concrete
adapters. The selected plan moves that construction module to the existing app
composition layer and removes both parent-to-adapter sources. Behavior review
confirmed that the builder can move intact and required a table-driven proof
for every ID/alias and unsupported-ID behavior. Quality review required
retargeting existing callers/tests instead of duplicating the factory assertion,
and using `providers.adapters` in the existing pricing test to verify its
export surface. All three final plan reviews pass. They also identified the two
source-visible import paths being removed; this migration is documented above
and preserves in-repository behavior without a cycle-preserving compatibility
shim.

## C-02 implementation review record

The boundary review confirmed app-owned construction adds no providers-to-app
edge and that the AST guard covers absolute and relative adapter imports. The
behavior review confirmed the builder body/signature stayed intact, the local
factory imports preserve lazy loading and the existing monkeypatch seam, and
the tests do not consult ambient credentials. The quality review required the
factory matrix to compare the full `ProviderCapabilities` value and to cover
the omitted `provider_type` and empty profile-model defaults; those cases were
added before final review. All three final reviews passed with no remaining
finding.

The focused changed suites, Ruff checks, formatting, and `git diff --check`
passed. `make ci-check` passed with 2,041 passed, 8 skipped, 11 xfailed,
91.73% coverage, source and wheel builds, and the product gate. The live
committed-tree Enola check at 21:08 UTC was clean: current cycles fell from
four to three, with 114 total insights (111 heuristics) against the pinned
115-insight baseline. Code commit: `d02e439`.

## C-03 plan

- **Owner and consumers:** `schemas` continues to own and root-export its
  nonregistry contract models. `schemas.registries` owns and exports the ten
  registry models and records; its existing package export surface remains
  canonical. No production consumer imports those ten names from the root
  `schemas` package.
- **Measured cycle:** `schemas/__init__.py` imports
  `schemas.registries` to re-export the registry models, while registry
  modules import the shared `schemas._base` definitions. Remove the root-to-
  subpackage imports and aliases so the internal registry-to-schema-base
  dependency is one-way. Keep `_base.py` in place: moving a shared schema base
  or adding a package is not needed to break this measured cycle.
- **Planned code and tests:** remove the ten registry names from
  `schemas/__init__.py` and its `__all__`, and state the two export surfaces in
  its module docstring. Leave registry model definitions, subpackage exports,
  validation behavior, and existing `schemas.registries` consumers unchanged.
  Add an AST guard that scans direct `schemas` modules and rejects imports from
  `schemas.registries`; test its resolver against absolute module imports,
  `from schemas import registries` re-exports, `from . import registries`, and
  `from .registries import ...`. Retain the existing registry model tests,
  which import and instantiate all ten registry exports from the canonical
  subpackage. Do not add duplicate serialization coverage for unchanged model
  behavior.
- **Deliberate import-path migration:** the root aliases
  `film_pipeline.schemas.AgentRegistryEntry`, `CostProfile`, `ModelRegistry`,
  `ModelRegistryEntry`, `ProviderCapabilities`, `ProviderRegistry`,
  `ProviderRegistryEntry`, `ValidatorRegistry`, `ValidatorRegistryEntry`, and
  `ValidatorThresholds` are removed. Their direct exports remain available
  from `film_pipeline.schemas.registries`. Repository search found no source
  consumer of the removed aliases; no forwarding or lazy-attribute shim is
  planned because it would recreate the measured parent-to-child dependency.
- **Files:** `src/film_pipeline/schemas/__init__.py` and a focused
  `tests/unit/schemas/test_import_boundaries.py`; existing registry
  constructor/export coverage stays in `tests/unit/test_schemas.py` without
  changes unless review or test execution demonstrates a real gap.
- **Validation:** focused schema and import-boundary suites with
  `--no-cov -n 0`, full `UV_CACHE_DIR=.uv-cache make ci-check` (coverage at
  least 90%), Enola against the docs-local receipt, and `git diff --check`.
  Close C-03 only when Enola lowers the current cycle count from three to two,
  adds no cycle, the canonical registry exports remain exercised, and the
  complete build/product/coverage gates pass.

## C-03 plan review record

The boundary review confirmed the root facade is the only `schemas` to
`schemas/registries` source edge; the registry modules can retain their shared
`schemas._base` imports because they become a one-way dependency. Behavior
review confirmed no in-repository consumer uses the removed root aliases, the
canonical registry package exports all ten names, and the existing schema
tests import and instantiate those names. It corrected an initial plan claim
that those registry cases were JSON round-trips; no duplicate serialization
tests are needed for unchanged model behavior. Quality review confirmed that
one direct-module AST guard plus the existing model tests is sufficient and
that moving the base or adding a package would expand scope without helping
the measured cycle. All three plan reviews passed before implementation began.

## C-03 implementation review record

The boundary review confirmed the root-to-registry edge is gone while the
registry modules retain their one-way dependency on the shared schema base.
The import-direction guard covers absolute module imports, package
re-exports, and relative imports; it scans every direct module in `schemas`.
The behavior review confirmed the ten moved root aliases have no in-repository
consumers and the canonical registry package exports and current model tests
remain intact. It caught and corrected docstring wording that could have
implied `PromptRegistry` and `PromptRegistryEntry` also moved. The quality
review caught a stale plan-state row and that was updated before completion.
All three final reviews passed with no remaining finding.

The focused schema/import-boundary suites passed. `make ci-check` passed with
2,043 passed, 8 skipped, 11 xfailed, 91.73% coverage, source and wheel builds,
and the product gate. The committed-tree Enola check at 21:26 UTC was clean:
current cycles fell from three to two, one dependency-depth advisory resolved,
and no new finding appeared. It reported 112 total insights (110 heuristics)
against the pinned 115-insight baseline. Code commit: `efd451e`.

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
