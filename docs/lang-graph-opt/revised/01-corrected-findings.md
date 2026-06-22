# 01 - Corrected Findings

Date: 2026-06-22

## Executive Summary

The existing `docs/lang-graph-opt/` notes are right about the biggest symptom: the current graph
does not behave like a durable, resumable LangGraph application. It uses `StateGraph(dict)`,
manual deep copies, state flags for human approval, and `GraphRecursionError` as normal control
flow.

The root cause is not one file. It is a system mismatch:

- LangGraph is present, but runtime approval and phase advancement mostly happen outside the
  graph.
- Artifacts are durable, but versioning is not actually advancing beyond `v1` in the graph node
  save path.
- The Master Film Matrix schema already has fields for downstream production state, but graph
  phases do not write those fields back.
- Validation is structured enough to block, but findings are flattened into `state["issues"]`
  and are not linked back to rows, artifact metadata, or review decisions.
- Prompt context is built by loading full artifacts, compacting JSON to 6000 characters, and
  hoping the model sees enough.

## What The Original Notes Got Right

### Real interrupts are missing

`src/film_pipeline/graph/graph.py` registers `await_approval` as a passthrough node. Phase nodes
set `human_approval_required`, then `after_approval()` routes back to `await_approval` until the
runtime hits the recursion limit. `StudioRuntime.run_graph()` catches `GraphRecursionError` and
streams values to recover the latest state.

This violates the product standard in `docs/product-completion/01-runtime-and-graph.md`: graph
pause/resume must use explicit semantics, not recursion failure handling.

The current LangGraph docs confirm the intended pattern: `interrupt()` pauses execution, requires
a checkpointer and a stable `thread_id`, and resumes with `Command(resume=...)`.

### State is too loose

`StateGraph(dict)` gives no state contract, no reducer behavior, no channel ownership, and no
typing for graph-visible state. The helper module `orchestrator_state.py` compensates with
namespaced keys, but the graph still accepts any key from any node.

The risk is not theoretical. There are multiple write styles in play:

- top-level keys like `current_phase`, `approved`, `artifact_refs`, `issues`
- service injection via `_services`
- transient repair feedback via `_repair_feedback`
- namespaced orchestrator data via helper functions
- persisted runtime state in `project-state.json`

The product needs a canonical runtime state model. The code currently has a convention.

### Deep-copy node style blocks LangGraph's strengths

Every major node starts with `new_state = deepcopy(state)` and returns the full state. LangGraph
can merge partial updates through state channels and reducers, but the current style bypasses
that model. It also makes side effects harder to reason about because nodes both mutate copied
state and call durable services.

### Subgraphs are planned but not real

The architecture blueprint calls for top-level project graph, phase subgraphs, action nodes,
validation nodes, human interrupt nodes, repair nodes, rollback nodes, provider-block nodes, and
wrap/lesson nodes.

The code has a `subgraphs/` directory, but the modules are re-export stubs. Actual phase logic
is concentrated in `src/film_pipeline/graph/nodes.py`.

### The matrix is not living yet

`MasterFilmMatrixRow` has `prompt_ref`, `provider_plan_ref`, `asset_refs`, `validation_refs`,
`post_refs`, and `status`. Those are the right fields. The graph does not systematically write
them.

Current behavior:

- `shot_bible_node` saves `shot_matrix`.
- `gen_planning_node` saves `cost_estimate` and may put `generation_requests` in state.
- `generation_node` validates dispatch readiness only.
- `qc_node` saves a consensus report.
- `post_node` saves an assembly manifest.

The matrix row lifecycle is therefore mostly aspirational.

## What The Original Notes Overreached On

### Do not make the matrix the only source of truth in graph state

The original notes repeatedly say "the matrix IS the state." That is too strong for this product.

The architecture blueprint says every output becomes a versioned artifact with metadata. MCP is
the product boundary. Review, rollback, audit, and delivery all depend on durable artifacts and
artifact metadata. LangGraph checkpoints are operational state, not a replacement for the
artifact store.

Better rule:

**Graph state carries refs, current working snapshots where useful, pending updates, and resume
context. ArtifactStore remains authoritative for durable production data.**

For the matrix, that means:

- Keep `shot_matrix` as a durable versioned artifact.
- Add matrix row patches as first-class artifacts or metadata-linked events.
- Materialize the latest matrix from base artifact plus approved patches.
- Keep a small graph-state projection for active rows, blockers, and pending repair input.

### Do not assume all LangGraph features are equally valuable

`Send`, `Command`, subgraphs, reducers, stores, streaming, and checkpointers are all useful, but
they solve different problems.

Priority should follow product risk:

1. Interrupts plus checkpointer because human review gates are mandatory.
2. Typed state because runtime state is the product control plane.
3. Artifact versioning and lineage because rollback and audit are production features.
4. Row-level matrix patches because generation/post depend on shot-level status.
5. `Send` for parallel validators and generation batches once state and persistence are stable.

### Do not treat chat-like output quality as only temperature and max tokens

The notes correctly identify model profile routing and weak system prompts, but quality also
depends on artifact contracts:

- Agents must receive scoped structured context, not truncated JSON blobs.
- Agents must produce schema-valid artifacts with enough detail for downstream validators.
- Repairs must preserve approved-good material and target failed fields.
- Review packages must expose what changed and why, so the human can guide revisions.

Creative temperature helps. It will not fix a lossy context pipeline.

## 5 Whys: Why Human Gates Are Fragile

1. Why does the graph stop at review gates by hitting `GraphRecursionError`?
   Because `await_approval` is a passthrough node that routes to itself until recursion limit.

2. Why is `await_approval` a passthrough instead of an interrupt?
   Because approval was implemented as runtime/MCP state mutation rather than graph resume.

3. Why did runtime/MCP take over phase advancement?
   Because the graph was not compiled with a checkpointer and did not have interrupt resume
   semantics.

4. Why was there no checkpointer?
   Because the repo built semantic git-backed checkpoints for approved milestones, and that
   was treated as enough.

5. Why is that insufficient?
   Git checkpoints are excellent audit milestones, but they do not persist every graph step or
   provide native interrupted execution state.

Root cause:

**Two checkpoint concepts were conflated. LangGraph checkpointers are operational execution
memory. Git checkpoints are semantic production milestones. The system needs both.**

## 5 Whys: Why The Matrix Does Not Stay Current

1. Why do matrix row fields stay empty?
   Because downstream phases save separate artifacts and do not patch matrix rows.

2. Why do downstream phases not patch rows?
   Because the artifact interface is whole-document save/load, and graph state stores only a
   string ref to the matrix.

3. Why is the matrix only a ref?
   Because the current architecture treats artifacts as opaque prompt context instead of typed
   dependency objects.

4. Why is prompt context the main data-sharing mechanism?
   Because `_inject_artifact_context()` loads upstream artifacts and serializes them into prompt
   variables for every critical-path agent.

5. Why is this fragile?
   Because context is truncated, unscoped, and not linked back to row-level provenance.

Root cause:

**The artifact system is durable but not queryable enough for row-level production state. The
matrix needs versioned patch semantics and scoped projections, not just whole-file JSON loading.**

## Corrected Problem Statement

The problem is not "LangGraph is unused." LangGraph is used, but the code uses only the basic
graph shape while routing, approval, persistence, repair semantics, and durable artifact lineage
are split across runtime methods, graph nodes, and custom helpers.

The product needs one coherent execution contract:

- MCP tools submit structured commands.
- Runtime resolves project and invokes or resumes LangGraph.
- LangGraph owns phase execution, pause/resume, repair routing, and state transitions.
- ArtifactStore owns durable typed outputs and metadata.
- Git checkpoints record approved semantic milestones.
- LangGraph checkpointer records operational execution state.
- Review packages are generated from graph state plus artifact metadata, not from ad hoc flags.

## Evidence Summary

| Area | Current Evidence | Impact |
|---|---|---|
| Graph state | `StateGraph(dict)` in `graph.py` | No typed contract or reducers |
| Human gates | `await_approval` is `_passthrough` | Recursion-limit control flow |
| Runtime resume | `run_graph()` catches `GraphRecursionError` | Pause/resume is not explicit |
| Service injection | `_services` stored in graph state | Serialization and state purity risk |
| Artifact save | `_save_artifact()` sets `version=1` | Repair overwrites same version path |
| Matrix lifecycle | Row fields exist but downstream writes are missing | Generation/post cannot rely on matrix |
| Context | `_compact_json_context(..., max_chars=6000)` | Large artifacts are truncated |
| Validators | Reports append to flat `issues` | Findings are not row-linked |

## Sources Checked

- `docs/architecture-blueprint.md`
- `docs/vision-and-direction.md`
- `docs/product-completion/00-product-standard.md`
- `docs/product-completion/01-runtime-and-graph.md`
- `src/film_pipeline/graph/graph.py`
- `src/film_pipeline/app/runtime.py`
- `src/film_pipeline/graph/nodes.py`
- `src/film_pipeline/schemas/matrix.py`
- `src/film_pipeline/artifacts/store.py`
- `src/film_pipeline/schemas/artifact.py`
- LangGraph docs: overview, interrupts, persistence, graph API
