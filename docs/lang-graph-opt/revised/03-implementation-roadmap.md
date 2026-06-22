# 03 - Implementation Roadmap

Date: 2026-06-22

## Guiding Rule

Make the graph and runtime correct before making them clever.

Do not start with parallelism or broad subgraph extraction. Start by replacing the fragile
approval loop, making state typed enough to trust, and fixing artifact lineage.

## Phase 0 - Preserve The Existing Analysis

Status: done by this folder.

Actions:

- Keep `docs/lang-graph-opt/` unchanged.
- Use this `revised/` folder as the implementation-aligned version.

Validation:

- No code behavior changes.

## Phase 1 - Real Human Gates

Goal:

Replace recursion-limit approval gates with LangGraph interrupts.

Files likely touched:

- `src/film_pipeline/graph/graph.py`
- `src/film_pipeline/graph/nodes.py`
- `src/film_pipeline/graph/interrupts.py`
- `src/film_pipeline/app/runtime.py`
- `src/film_pipeline/mcp/tools/__init__.py`
- `tests/unit/test_graph.py`
- `tests/unit/app/test_app_ops.py`
- `tests/integration/test_mcp_flow.py`

Implementation:

1. Compile graph with a checkpointer.
2. Replace `_passthrough` `await_approval` with an interrupting gate node.
3. Make MCP approval/revision tools call graph resume with `Command(resume=...)`.
4. Keep git checkpoint creation after approved phase transitions.
5. Remove `GraphRecursionError` as normal control flow.

Tests:

- initial run pauses with an interrupt payload
- approving resumes into the next phase
- requesting revision resumes into repair path
- blocking issues prevent approval
- runtime restart can resume a pending gate when using the durable checkpointer

Risk:

- Code before `interrupt()` runs again on resume. Any side effects before the interrupt must be
  idempotent. Review package creation should therefore either be idempotent by key or happen
  before gate as a saved artifact ref passed in the interrupt payload.

## Phase 2 - Typed State Contract

Goal:

Replace `StateGraph(dict)` with a typed state schema and reducers for append-only channels.

Files likely touched:

- `src/film_pipeline/graph/state.py` or new `src/film_pipeline/graph/state_schema.py`
- `src/film_pipeline/graph/graph.py`
- `src/film_pipeline/graph/orchestrator_state.py`
- `src/film_pipeline/graph/nodes.py`
- graph and runtime tests

Implementation:

1. Add `StudioGraphState`.
2. Type append-only channels: issues, artifact refs, validation refs, review refs, audit refs.
3. Move services out of state. Prefer injected node closures or `config["configurable"]`.
4. Convert a small number of nodes to return partial updates.
5. Keep compatibility helpers for existing state keys during migration.

Tests:

- reducers append rather than replace on expected channels
- scalar channels replace correctly
- service injection is not persisted in runtime state
- mypy remains strict

Risk:

- Reducers can duplicate refs if nodes replay after interrupts. Add idempotent append helpers or
  deterministic refs before fully relying on additive reducers.

## Phase 3 - Artifact Versioning And Dependency Metadata

Goal:

Make durable artifacts reliable enough to support repair, rollback, and stale-data detection.

Files likely touched:

- `src/film_pipeline/artifacts/store.py`
- `src/film_pipeline/artifacts/index.py`
- `src/film_pipeline/schemas/artifact.py`
- `src/film_pipeline/graph/nodes.py`
- `src/film_pipeline/checkpoints/invalidation.py`
- artifact tests

Implementation:

1. Add next-version allocation to ArtifactStore or a graph artifact service.
2. Stop hardcoding `version=1` in `_save_artifact()`.
3. Persist parent refs and built-from refs.
4. Attach validation report refs and approval refs when known.
5. Add stale dependency detection using artifact metadata.

Tests:

- saving the same artifact id twice creates `v1`, then `v2`
- metadata parent refs match state inputs
- rollback invalidation can see downstream artifacts through metadata
- repaired phase does not overwrite the prior candidate

Risk:

- Existing tests may assume `v1`. Update tests to assert current ref rather than fixed version
  where appropriate.

## Phase 4 - Matrix Patches

Goal:

Make the Master Film Matrix living through row-level patch artifacts.

Files likely touched:

- `src/film_pipeline/schemas/matrix.py`
- new `src/film_pipeline/schemas/matrix_patch.py`
- new `src/film_pipeline/artifacts/matrix_projection.py`
- `src/film_pipeline/graph/nodes.py`
- `src/film_pipeline/graph/orchestrator_validators.py`
- generation, validation, post tests

Implementation:

1. Add `MatrixPatch`, `MatrixRowUpdate`, and row status transition schemas.
2. Add a projection helper that materializes matrix plus approved/candidate patches.
3. Make `gen_planning_node` emit prompt/provider plan patches.
4. Make `generation_node` emit asset/status patches.
5. Make `qc_node` emit validation/status patches.
6. Make `post_node` emit assembly/post patches.

Tests:

- gen planning patch sets `prompt_ref`, `provider_plan_ref`, and `status=prompted`
- generation patch sets `asset_refs` and `status=generated`
- QC patch appends `validation_refs` and blocks failed rows
- projection preserves unpatched rows
- rollback invalidates downstream patches

Risk:

- Whole-matrix saves are simpler but hide change intent. Do patches first for new downstream
  updates, then decide whether to also materialize full matrix versions for convenience.

## Phase 5 - Structured Repair Feedback

Goal:

Stop asking agents to infer exact repairs from flat issue strings.

Files likely touched:

- `src/film_pipeline/schemas/issue.py`
- new `src/film_pipeline/schemas/repair.py`
- `src/film_pipeline/graph/nodes.py`
- `src/film_pipeline/validation/base.py`
- validator implementations
- repair tests and e2e scenarios

Implementation:

1. Extend validator findings with optional `artifact_id`, `shot_id`, `field`, and
   `recommended_action`.
2. Save repair feedback as a typed artifact.
3. Pass `repair_feedback_ref` through graph state.
4. Update agents/templates to preserve passed rows and modify failed fields.
5. Clear or supersede issues that were resolved by a repair attempt.

Tests:

- row-level issue becomes row-level repair feedback
- repair feedback preserves passed row ids
- repaired output creates a new artifact version
- convergence escalation interrupts for human guidance after max rounds

Risk:

- Some validators are artifact-level and cannot name rows. Keep `global_issues` for those.

## Phase 6 - Scoped Context Packets

Goal:

Replace broad truncated JSON prompt injection with phase-specific context packets.

Files likely touched:

- `src/film_pipeline/kb/packets.py`
- `src/film_pipeline/graph/nodes.py`
- `src/film_pipeline/agents/prompt_templates/defaults.py`
- agent implementation tests

Implementation:

1. Create artifact context packet builders per phase.
2. Use matrix projections to select active row slices.
3. Put artifact refs and concise summaries in prompts.
4. Keep full artifact loading inside deterministic validators and projection helpers, not in
   generic prompt injection.
5. Add context-size tests for large matrices.

Tests:

- 100-row matrix context includes all active row ids without truncation loss
- screenwriter does not receive provider internals
- provider planner receives budget/provider policy and planned rows
- QC validators receive only relevant artifact slices

Risk:

- Prompt templates will need careful migration. Preserve current template ids and add new
  versions rather than silently changing old contracts.

## Phase 7 - Subgraphs And Parallelism

Goal:

Use LangGraph subgraphs and `Send` where they improve reliability or throughput.

Start order:

1. Approval gate subgraph.
2. QC validator fan-out subgraph.
3. Generation batch subgraph.

Files likely touched:

- `src/film_pipeline/graph/subgraphs/qc.py`
- `src/film_pipeline/graph/subgraphs/generation.py`
- `src/film_pipeline/graph/subgraphs/review_gate.py`
- `src/film_pipeline/graph/graph.py`
- related tests

Tests:

- QC subgraph fans out validators and reduces reports deterministically
- generation subgraph can resume a partially complete batch
- failed worker creates a provider/blocker issue without losing successful worker outputs

Risk:

- Parallelism makes idempotency mandatory. Do not fan out paid provider calls until duplicate
  prevention and job ledger recovery are tested.

## Phase 8 - Agent Output Quality

Goal:

Improve creative completeness without weakening schema discipline.

Files likely touched:

- `src/film_pipeline/agents/model_routing/__init__.py`
- `src/film_pipeline/agents/runner.py`
- `src/film_pipeline/agents/prompt_templates/defaults.py`
- agent tests

Implementation:

1. Map agent ids to model profiles.
2. Route creative agents to creative profiles.
3. Keep validators on strict profiles.
4. Add quality instructions to creative templates.
5. Require enough detail through schema fields and validation, not prose style alone.

Tests:

- screenwriter uses creative profile
- provider planner uses operational profile
- validators use strict profile
- generated script/treatment artifacts meet minimum structural/detail thresholds

Risk:

- Higher temperature can reduce schema validity. Use retries or schema repair around JSON parsing
  rather than loosening artifact contracts.

## Recommended First PR

Implement Phase 1 only.

Acceptance criteria:

- `submit idea` reaches a real interrupt payload.
- `approve phase` resumes the same graph thread.
- No supported test path relies on `GraphRecursionError`.
- Existing git checkpoint creation still happens on approval.
- MCP remains the only operator-facing control path.

This gives the repo a trustworthy execution spine. The matrix, repair, and parallelism work will
be much safer after that.
