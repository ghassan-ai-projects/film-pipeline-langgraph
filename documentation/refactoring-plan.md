# Phased Refactoring Plan

**Goal:** Move the LangGraph Film Studio from a strong scaffold to a working product that satisfies `documentation/quality-criteria.md` and `documentation/product-completion/`.

**Completion contract:**

- `make ci-check` passes (coverage ≥ 90 %, lint, tests, build, product-gate).
- `make typecheck` passes.
- All critical-path MCP tools are non-stubbed and behavior-tested.
- At least one full `idea → validated clips` MCP-driven E2E scenario passes.
- Docs match code and contain real operator instructions.
- No new abstractions without concrete need; no dead code; no secrets.

## Phase 0 — Stabilize Quality Gates and Documentation Truth

**Objective:** Make `make ci-check` green and remove false confidence from docs.

### Tasks

1. Close the coverage gap to ≥ 90 %.
   - Target low-coverage modules first:
     - `mcp/tools/reference_generation.py` (42.91 %)
     - `mcp/tools/assembly.py` (52.78 %)
     - `mcp/tools/review.py` (62.07 %)
     - `mcp/tools/planning.py` (68.33 %)
     - `mcp/tools/validation.py` (70.77 %)
     - `mcp/tools/generation.py` (70.75 %)
     - `providers/adapters/imagen4_gemini.py` (68.24 %)
     - `mcp/tools/checkpoints.py` (78.12 %)
   - Add unit tests for branching paths, error branches, and helper functions.
   - Where code is genuinely unreachable, remove it rather than test it.
2. Update stale documentation to reflect measured state.
   - `documentation/acceptance-checklist.md`: fix ruff/mypy/coverage claims.
   - `documentation/product-completion/status-scorecard.md`: correct coverage and gate status.
   - `documentation/product-completion-plan/acceptance-checklist.md`: mark only completed items green.
   - `documentation/release-process.md`: remove reference to missing `test_secret_redaction.py`.
3. Fix `Makefile` / docs inconsistency.
   - Either add `typecheck` to `ci-check` or update `AGENTS.md` / `release-process.md` to say `typecheck` is run separately.
4. Remove dead code identified by the audit.
   - `app/runtime.py:_load_graph_state`
   - `app/runtime.py:_approve_current_phase`
   - `kb/curator.py` stub module (or give it real behavior)
   - Unused `_authority_sort_key` in `kb/packets.py`
5. Correct smoke-test docstring mismatch (`app/smoke.py` agent count).

### Validation

```bash
make ci-check
make typecheck
```

### Deliverables

- Coverage ≥ 90 %.
- All docs claiming gate status are truthful.
- No dead code from the audit list remains.

## Phase 1 — Harden Artifact and MCP Foundation

**Objective:** Make the MCP surface the safe, single product boundary and make artifacts the typed, versioned contract.

### Tasks

1. Enforce confirmation middleware in `mcp/server.py`.
   - Reject calls to `requires_confirmation=True` tools unless a confirmation token / flag is present.
   - Add tests proving rejection and acceptance.
2. Make MCP reads project-aware.
   - Resolve `project_ref` / `_envelope.resolved_project_id` before all reads, not just mutations.
   - Add tests for multi-project sessions.
3. Replace hardcoded `version=1` in bible/planning tools.
   - Add `ArtifactStore.next_version()` helper already exists; use it consistently.
   - Add tests proving repeated calls create new versions.
4. Implement persisted artifact status transitions.
   - Add `ArtifactStore.approve(artifact_id, version, approval_ref)`.
   - Add `ArtifactStore.supersede(artifact_id, version)`.
   - Update `versioning.py` to align with `ArtifactMetadata` or remove unused `ArtifactVersion`.
   - Back-fill tests for status lifecycle.
5. Eliminate `save_dict` from the public boundary.
   - Make it private or remove it.
   - Update post-production agents and reference-generation tools to pass Pydantic models.
6. Centralize path logic.
   - Move duplicated phase map and safe-id logic from `store.py` to `paths.py`.
   - Harden safe-id sanitization.
7. Convert `AssetEntry` / `AssetManifest` to Pydantic schemas with `pathlib.Path` and `schema_version`.
8. Implement or unregister MCP stubs.
   - `assembly.py`: implement coverage/assembly tools or move them to `allowed_stub_tools` and remove from operator docs.
   - `rollback_to_checkpoint`: implement real restore (covered in Phase 5).

### Validation

```bash
make test-unit
make test-integration
pytest tests/unit/mcp/tools -q
```

### Deliverables

- Confirmation middleware tested.
- Artifact status lifecycle persisted and tested.
- No public `save_dict`; all artifact saves schema-validated.
- Path logic centralized.

## Phase 2 — Wire Dynamic Routing and Human Gates

**Objective:** Replace the hardcoded phase runner with the state-driven router.

### Tasks

1. Declare all state keys in `StudioGraphState`.
   - Add `_services`, `_orchestrator__*`, `_routing_decisions`, `_validation_reports`, `_qc_reports`, and other runtime keys.
   - Migrate from undeclared dict keys to a Pydantic state model if LangGraph supports it cleanly.
2. Wire `after_phase()` / `compute_actions()` into the compiled graph.
   - Replace `phase_node → consistency_check → await_approval` hardwiring with conditional edges driven by `RouterResult`.
   - Remove the hardcoded `next_map` from `after_approval`.
3. Implement real phase subgraphs.
   - Each phase subgraph has its own router, creator agent node(s), validator node(s), and interrupt node.
   - Start with the critical spine: intake → constitution → development → script → visual dev → shot bible.
4. Make human gates mandatory by default.
   - `await_approval_node()` should call `interrupt()` first when policy requires human approval.
   - Orchestrator agent may prepare the review package / recommendation, not unilaterally approve.
5. Add graph-level integration tests.
   - `Command(resume={"action": "approve"})`
   - `Command(resume={"action": "request_revision"})`
   - Provider-blocked routing.
   - Budget-blocked routing.
6. Remove the global contextvar fallback for `GraphServices`.
   - Pass services explicitly through state/config.

### Validation

```bash
pytest tests/integration/test_dynamic_routing.py -v
pytest tests/e2e -v
```

### Deliverables

- Compiled graph routes via `compute_actions()`.
- Human gates cannot be silently bypassed.
- Resume/revision paths tested at graph level.

## Phase 3 — Reconcile Agent Registries and Capability-Based Routing

**Objective:** Make every declared MVP agent executable and selectable by capability.

### Tasks

1. Add an invariant contract test across all `MVP_AGENTS`.
   - Each agent has an implementation class.
   - Each agent has a dedicated prompt template.
   - Each agent has a resolvable model profile.
   - Each agent has a mock response for mock mode.
2. Fix mismatched mappings.
   - `failure-handling-agent` → new `FailureHandlingAgent` (see Phase 4).
   - `clip-validator` → appropriate validator implementation or rename.
3. Add missing implementations and templates.
   - `character-dossier-agent`, `environment-bible-agent`, `prompt-composition-agent`, `continuity-ledger-agent`, `generation-scheduler-agent`, `full-movie-flow-validator`, `kb-curator-agent`, `config-inference-agent`, `visual-dev-agent`.
   - If an agent is not in the current scope, remove it from the MVP roster.
4. Replace `_PHASE_DEFAULT_AGENTS` with capability-based selection.
   - Query the registry by `family`, `role`, and `capabilities`.
   - Keep current defaults only as a fallback.
5. Move agent-to-profile mapping out of `graph/nodes.py`.
   - Derive profile from agent contract or profile config.
6. Introduce real reviewer agents.
   - At least one agent claims `AgentRole.REVIEWER` so the review path does not fall back to validators.
7. Fix MCP bible real-mode path.
   - Use `PromptRunner.run_from_template()` and `ModelRouter.select()` instead of the nonexistent `resolve()`.

### Validation

```bash
pytest tests/unit/agents -v
pytest tests/integration/test_dynamic_routing.py -v
pytest tests/integration/test_artifact_spine.py -v
```

### Deliverables

- All MVP agents executable.
- Create routing is capability-based.
- Agent registry drift is prevented by invariant test.

## Phase 4 — Validation, Provider, and Generation Runtime Truth

**Objective:** Make validation, provider health, and generation real runtime behaviors governed by the ledger.

### Tasks

1. Fix validation thresholds.
   - `score_to_status` must use `review_at` so `[review_at, pass_at)` returns `NEEDS_REVISION`.
   - Add unit tests for all four statuses.
2. Wire validator registry into `GraphServices`.
   - Replace direct validator imports with registry-driven dispatch.
3. Wire provider registry into `StudioRuntime`.
   - Replace untyped `provider_adapters: dict[str, Any]` with `ProviderRegistry`.
4. Make `generation_node` ledger-backed.
   - Read/write `GenerationLedgerManager`.
   - Implement resume path that loads the ledger and continues from latest non-terminal row.
5. Implement real `FailureHandlingAgent`.
   - Classifies `FailureClass`, emits `FailureDecision`, routes graph.
6. Resolve `prompt_ref` before provider submission.
   - Add helper that loads prompt artifact and passes rendered text to `adapter.build_payload()`.
7. Consolidate provider health tracking.
   - Replace ad-hoc dict with `ProviderHealthTracker`.
   - Update health on submit/poll failures.
8. Implement provider capability enforcement.
   - Reject incompatible aspect ratio, duration, or model before submission.
9. Implement real polling for paid providers or clearly document that polling is mocked.

### Validation

```bash
pytest tests/unit/validation -v
pytest tests/integration/test_providers.py -v
pytest tests/integration/test_generation.py -v
pytest -m e2e
```

### Deliverables

- Validation reports change runtime behavior.
- Generation state is single-source-of-truth via ledger.
- Failure-handling agent classifies and routes errors.
- Provider health is consistent and observable.

## Phase 5 — KB, Config, Checkpoint Provenance and Safety

**Objective:** Make provenance, config governance, and recovery real runtime behaviors.

### Tasks

1. Wire `KBContextPacketBuilder` into `GraphServices`.
   - Initialize in `for_mock_runtime` and `for_real_runtime`.
2. Stamp `kb_context_ref` on every artifact.
   - Pass real `kb_context_id` into `_save_artifact`.
   - Update `_record_handoff` to include `kb_context_id`.
   - Update MCP bible/generation tools to set `kb_context_ref`.
3. Persist checkpoint metadata.
   - Write `CheckpointMetadata` to JSON under the project root.
   - Rehydrate `StudioRuntime.checkpoints` from disk on load.
4. Make rollback safe and artifact-aware.
   - Split into preview mode (returns invalidation report + confirmation token) and execute mode (requires token).
   - Persist `InvalidationReport` as an artifact.
   - Update runtime project state after rollback.
5. Compute invalidation transitively.
   - Use actual artifact parent chains instead of the static `DEPENDENCY_GRAPH`.
6. Implement mid-project profile-change flow.
   - Bump `profile_version`, produce new `project-config.resolved.yaml` artifact, run invalidation, gate on human approval.
7. Expand config validation.
   - Validate provider/model/validator existence, style-choice compatibility, approval gates, delivery modes, budget completeness.
8. Refactor `_resolve_project_config` to use the `ProjectConfig` schema.
   - Produce the documented `project-config.resolved.yaml` artifact with sources, inferred values, assumptions, conflicts, and approval record.

### Validation

```bash
pytest tests/unit/checkpoints -v
pytest tests/unit/kb -v
pytest tests/unit/config -v
pytest tests/e2e/test_scenario_07_rollback.py -v
```

### Deliverables

- Every artifact has a real `kb_context_ref`.
- Checkpoints survive restart.
- Rollback requires confirmation and produces invalidation artifact.
- Profile changes are versioned and approved.
- Config validation matches blueprint.

## Phase 6 — TUI as MCP Consumer and Unified Operator Surface

**Objective:** Eliminate the parallel internal-only TUI surface.

### Tasks

1. Add an `MCPStudioGateway` for the TUI.
   - Speaks stdio JSON-RPC to the MCP server.
2. Switch the TUI default gateway to the MCP gateway.
   - Keep `InProcessStudioGateway` only for tests.
3. Unify TUI and MCP execution paths.
   - Refactor MCP handlers and `OperatorService` to share thin use-case functions, or remove `OperatorService` and route TUI through MCP.
4. Replace the broad `except Exception` in `runtime.approve_phase`.
   - Handle specific exceptions; let others propagate with actionable messages.
5. Expand TUI command coverage.
   - KB search, checkpoint creation, provider health, generation planning/spend approval, rollback.
6. Remove dead code (`_load_graph_state`, `_approve_current_phase`).

### Validation

```bash
pytest tests/unit/tui -v
pytest tests/integration/test_mcp_flow.py -v
# Manual: run TUI against MCP server in mock mode
```

### Deliverables

- TUI exercises the same MCP tools as OpenClaw.
- No internal-only operator surface remains.
- Approval errors are specific and actionable.

## Phase 7 — E2E Behavior Proof and Operator Documentation

**Objective:** Prove the product works end to end and is operable by a human.

### Tasks

1. Rewrite E2E scenarios as MCP-driven workflows.
   - Use `invoke_tool` / MCP server for every action.
   - Assert on persisted artifacts, validation reports, checkpoints, audit events.
2. Implement a real rollback E2E.
   - Create artifacts, roll back, assert prior phase and artifact content restored.
3. Implement provider failure/recovery E2E.
   - Submit through provider adapter, simulate failure, pause, resume.
4. Implement `idea → validated clips` happy-path E2E.
   - Drive through intake → constitution → development → script → visual dev → shot bible → generation planning → mock generation → QC.
5. Write real operator documentation.
   - `documentation/runbook-first-film.md`: install, create project, submit idea, approve phases, inspect artifacts, recover from provider block.
   - `documentation/operations-guide.md`: MCP server modes, profile selection, checkpoint/rollback, budget gates.
   - `documentation/demo-guide.md`: step-by-step demo with expected outputs.
6. Update `openclaw-mcp-operator-guide.md` to match actual tool names and remove references to stubs.

### Validation

```bash
pytest -m e2e -v
make release-check
```

### Deliverables

- All E2E scenarios pass and prove operator-visible behavior.
- Operator docs contain real instructions.
- `make release-check` passes.

## Cross-Phase Rules

- Each phase must keep `make ci-check` green before the next phase starts.
- Add or update tests in the same PR as production changes.
- Do not add abstractions unless they remove repeated or proven complexity.
- Update docs immediately when behavior changes.
- Keep changes scoped to the phase; deliberate cross-phase work is allowed but must be called out.

## Tracking

This plan is tracked as a runtime goal. See the active goal for current phase, budget, and completion status.
