# Enola architecture snapshot — deterministic corroboration at HEAD

This document records what the repository's **enola** architecture tool measured
at the audited commit. It is machine-derived (parsed source + graph algorithms,
no model), so it is cited as *independent structural evidence* alongside the
manual audit, not as a replacement for it.

## Provenance

| Field | Value |
|---|---|
| Tool | `enola` 0.2.7-51-g72cd079 |
| Repo | `${REPO_ROOT}` |
| Branch / commit | `modular-app` / `fb85baa0e6b769b709791a96a89980089304bf13` |
| Working tree at snapshot | clean (`dirty: false`) |
| Snapshot id | `sha256:85cf714e8d2919f3a3ed11d61013c451b7280314bf616e8202a44b0518eec3ca` |
| Facts / insights | 7878 facts, 115 insights, 63 modules |
| Explainers with output | `cycles` 5, `god-class` 25, `hotspots` 58, `dependency-depth` 9, `exported-surface` 3, `complexity-outliers` 15 |
| Config | `docs/modular-architecture/enola-config.yaml` (copy of the repo's `mcp-arch.yaml`, with `docs/**` ignored and a docs-local output dir) |
| Output | `docs/modular-architecture/enola-out/` |

Reproduce:

```bash
enola --generate docs/modular-architecture/enola-config.yaml   # writes the docs-local snapshot
enola --explain  mcp-arch.yaml                                  # read-only report, writes nothing
```

> The repo's checked-in `.enola/` snapshot is **stale**: it was taken at
> `main@4f802b1` and still contains the `src/film_pipeline/tui/` package, which
> was deleted before this branch's base (`43af11a`, PR #28). Do not cite the
> checked-in `.enola/insights.json` for current structure. The docs-local
> snapshot above is the one taken at the audited commit.

## 1. Graph scale

| Metric | Value |
|---|---|
| Modules | 63 (source packages/sub-packages; test modules are consumers) |
| Symbols | 4521 (2111 functions, 1819 methods, 591 classes) |
| `imports` edges | 3320 (1790 internal, 893 stdlib, 637 external) |
| `calls` edges | 11953 |
| Cycles | **5** |
| Layer violations | **0 — because no layers are declared** |

The last row is the headline: enola grades layer boundaries only against an
`enola-intent.yaml` declaration, and this repository has none. The prose law in
`AGENTS.md:51` is therefore invisible to the only tool that could enforce it.
See `audit/14-module-boundaries-and-import-law.md` §F-BOUNDARY-01/04.

## 2. Cycles (exact, at HEAD)

| # | Cycle (module members) | Reading |
|---|---|---|
| C1 | `agents/prompt_templates` ↔ `agents/prompt_templates/defaults` | Package façade re-exports from the defaults sub-package, which imports the parent package. |
| C2 | `app` ↔ `mcp` and 5 sub-modules (`app`, `app/services`, `mcp`, `mcp/tools`, `mcp/tools/bibles`, `mcp/tools/generation`, `mcp/tools/reference_generation`) | The composition root and the product boundary are mutually dependent — corroborates `audit/14` F-BOUNDARY-03, and it is larger than the 2-package view. |
| C3 | `graph` ↔ `graph/nodes` ↔ `graph/orchestrator_validators` ↔ `graph/subgraphs` | Intra-package cycle; the graph's node layer and its validator/worker layer are mutually dependent. |
| C4 | `providers` ↔ `providers/adapters` | Provider façade re-exports adapters that import the parent package. |
| C5 | `schemas` ↔ `schemas/registries` | Schema façade re-exports registries that import the parent package. |

C1, C4, C5 are the classic "façade re-exports a child that imports the parent"
pattern and are cheap to break. C2 and C3 are design-level and are the ones the
target architecture must resolve (`03-target-architecture.md`).

## 3. Coupling hotspots (by fan-in / fan-out)

| Module | fan-in | fan-out | Criticality | Blast radius |
|---|---|---|---|---|
| `src/film_pipeline/schemas` | 509 | 1 | high | 58 |
| `src/film_pipeline/app` | 214 | 40 | high | 23 |
| `src/film_pipeline/graph` | 148 | 18 | high | 27 |
| `src/film_pipeline/artifacts` | 130 | 16 | high | 34 |
| `src/film_pipeline/mcp/tools` | 119 | 104 | high | 23 |
| `src/film_pipeline/graph/nodes` | 65 | 92 | high | 27 |

Readings used in the design:

- `schemas` is the shared kernel by measurement (509 fan-in), matching the manual
  count of 323 cross-package imports. Its public contract matters more than any
  other module's, which is why `audit/14` F-BOUNDARY-02 (72 files importing the
  private `schemas._base`) is a High finding.
- `mcp/tools` has the largest fan-out (104) of any module: it is the widest
  consumer and therefore the most likely place for parallel implementations of
  domain logic (corroborated by the validator-wiring duplication in
  `audit/08`).
- `app` (214 fan-in, 40 fan-out) is a dependency hub rather than a leaf
  composition root, which is the root of cycle C2.

## 4. God classes / concentrated symbols (fan-in ≥ 19)

| Symbol | Dependents |
|---|---|
| `app/runtime.StudioRuntime.create_project` | 103 |
| `schemas/_base.SchemaBase` | 99 |
| `app/runtime.StudioRuntime.set_active` | 95 |
| `app/runtime.get_runtime` | 95 |
| `app/runtime.StudioRuntime.get_active` | 78 |
| `mcp/tools/helpers._ok` / `_error` | 57 / 53 |
| `app/runtime.StudioRuntime._run_phase_node` | 33 |
| `generation/prompt_builder.build_structured_prompt` | 33 |
| `artifacts/store.ArtifactStore.save` | 27 |
| `schemas/artifact.ArtifactRef.from_string` | 27 |
| `app/runtime.reset_runtime` | 26 |
| `agents/model_adapter.ModelAdapter.chat` | 25 |
| `providers/credentials.lookup` | 25 |
| `constraints/extractor.extract_constraints` | 23 |
| `generation/ledger.GenerationLedgerManager.plan_batch` | 23 |
| `app/mock_responses.default_mock_responses` | 22 |
| `app/services/operator.OperatorService._state_for_project` | 21 |
| `artifacts/project_storage.ProjectStorage.project_dir` | 20 |
| `checkpoints/git_backend.GitBackend.init_temp` | 20 |
| `graph/services.GraphServices.for_mock_runtime` | 20 |

Two readings matter for modularization:

1. `StudioRuntime` (three symbols in the top five, 103/95/78 dependents) is the
   single largest concentration of authority in the codebase. Any module
   extraction that keeps calling `get_runtime()` inherits the god object; the
   target architecture must give modules explicit dependencies instead.
2. `app/mock_responses.default_mock_responses` (22 dependents) and
   `mcp/tools/helpers._ok/_error` (57/53) being top-coupled confirms that test
   doubles and response shaping are load-bearing cross-cutting concerns, not
   incidental helpers (`audit/13`, `audit/11`).

## 5. Exported surface

| Module | Public symbols |
|---|---|
| `graph/orchestrator_state` | 38/38 (100%) |
| `artifacts/project_storage` | 32/33 (97%) |
| `schemas/_base` | 19/19 (100%) |

100% public surfaces with high fan-in mean these modules have *no encapsulation
boundary*: every symbol is importable and therefore part of the de-facto
contract. `orchestrator_state` at 38/38 is the orchestration state model; the
audit treats it as the natural owner of orchestrator state
(`audit/02`), and this measurement says its contract is currently unbounded.

## 6. Complexity outliers (top)

| Symbol | Cyclomatic complexity |
|---|---|
| `graph/nodes/visual._reconcile_shot_matrix_to_brief` | 29 |
| `app/logging_setup.configure_logging` | 23 |
| `graph/nodes/_generation_prompts._resolve_prompt_for_request` | 15 |
| `graph/nodes/visual._reconcile_durations` | 15 |
| `graph/nodes/visual._balance_act_rows` | 14 |
| `artifacts/rendering.render_consensus_report` / `render_script` / `render_validation_report` | 13 each |
| `graph/state_schema.merge_issues` | 12 |
| `graph/subgraphs/qc._load_artifact_for_validator` | 12 |
| `mcp/tools/planning._fallback_video_route` | 12 |
| `providers/adapters/imagen4_gemini._extract_image_bytes` | 12 |
| `schemas/constraints.render_constraints` | 12 |

These are candidate *follow-on* extractions (not ownership seams): they are
single-owner functions that are simply large. They are recorded here so the
roadmap does not confuse size with distributed ownership.

## 7. Dependency depth

`cli` (18) → `app` (17) → `graph` (10) → `agents/impl`/`post` (6) → `agents`,
`config`, `generation` (5) → `validation/impl` (5).

Depth is measured over the whole chain, so `cli` and `app` being deepest is
expected for entry points. What matters is that `graph` at depth 10 sits above
five domain packages, i.e. the graph layer transitively owns execution of all of
them — which is why the graph is a legitimate cross-package importer under the
current law, and why the target law must keep an explicit orchestration module
rather than trying to make every module a leaf.

## 8. Reconciliation use

`enola` is used in this program in three ways:

1. **Corroboration** — every audit finding that claims coupling was checked
   against the snapshot (cycles, fan-in, exported surface) and disagreements are
   recorded in the verification files.
2. **Baseline for the extraction** — a `docs/modular-architecture/enola-config.yaml`
   equivalent should be wired into CI with an `enola-intent.yaml` layer
   declaration before the first extraction phase, so each phase is graded on the
   architecture delta rather than on tests alone. See
   `05-enforcement-and-guard-tests.md`.
3. **Impact analysis** — `enola blame`/`impact_analysis` answer "what depends on
   this symbol" exactly, without greps, when a module boundary is being moved.

## 9. Caveats

- The snapshot's `docs/**` exclusion keeps this program's own documentation out
  of the map; the repo's checked-in `mcp-arch.yaml` does not exclude `docs/`, so
  `enola --explain mcp-arch.yaml` includes documentation tooling.
- enola reports 63 modules at sub-package granularity; the audit's cluster map
  uses 17 top-level packages plus `graph/*` and `mcp/tools/*` sub-structures, so
  counts are not directly comparable.
- Test modules appear as consumers in fan-in counts; they are deliberately not
  part of any proposed module-law declaration except through the `testing`
  package.
