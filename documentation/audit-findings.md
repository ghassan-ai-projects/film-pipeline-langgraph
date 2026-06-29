# Full Codebase Audit Findings

**Audited:** 2026-06-29
**Branch:** `main` (pulled to `28888cb`)
**Scope:** `src/film_pipeline/`, `tests/`, `documentation/`, `profiles/`
**Method:** Parallel expert scans against `documentation/quality-criteria.md`, `AGENTS.md`, and `documentation/architecture-blueprint.md`, plus `make test-unit`, `make lint`, `make typecheck`.

## Baseline Verified State

| Gate | Result |
|------|--------|
| `make test-unit` | 1323 passed, 11 warnings, 12.16s |
| `make lint` | pass |
| `make typecheck` | pass (375 files) |
| `pytest` coverage | **87.43 %** — fails the 90 % threshold in `pyproject.toml` |
| `make product-gate` | pass (but product gate is shallow) |

`make ci-check` currently fails because coverage is below 90 %.

## Executive Summary

The repository is a strong, well-typed scaffold with good unit-test coverage for isolated modules. It is **not yet a working product** by its own standards. The highest-impact gaps are:

1. **Coverage gate is red** and several critical paths are thinly tested.
2. **MCP-first contract is incomplete:** dangerous operations lack confirmation enforcement, several critical tools are stubs, read tools ignore `project_ref`, and creator tools bypass the LangGraph orchestrator.
3. **Dynamic routing exists only on paper:** the compiled graph uses a hardcoded phase map; the `compute_actions()` router is tested but unwired.
4. **Agent registries are inconsistent:** the MVP roster declares 20 agents, but implementation classes, prompt templates, and profile mappings are missing or mis-mapped for many of them.
5. **Artifact layer is only half-real:** raw `dict` saves bypass Pydantic, status transitions are not persisted, and required metadata fields (`kb_context_ref`, `approval_ref`, etc.) are often empty.
6. **Validation/provider/generation runtime is bifurcated:** registries exist but are not wired into runtime services; the graph's `generation_node` does not consult the generation ledger; validation has a dead `NEEDS_REVISION` status.
7. **KB, config, and checkpoint provenance are incomplete:** `kb_context_ref` is not stamped on artifacts, config resolution skips prompt inference and approval, checkpoint metadata is in-memory only, and rollback lacks confirmation.
8. **TUI bypasses the MCP contract** through an internal `OperatorService`, creating two divergent operator surfaces.
9. **Documentation is inconsistent** with measured state and with itself.

## Detailed Findings by Layer

### 1. MCP Tool Surface

**Severity: High**

- `requires_confirmation` is declared in the registry but never enforced in `server.py:56-130`.
- `rollback_to_checkpoint` (`checkpoints.py:143-154`) returns success without restoring state.
- `assembly.py` exposes five coverage/assembly tools that are registered no-ops (`_stub`).
- Bible tools (`bibles.py`) directly instantiate agents and save artifacts, bypassing LangGraph.
- Read tools ignore `project_ref` and always use the global active project.
- `version=1` is hard-coded in bible and planning save paths, overwriting prior artifacts.
- Tool descriptions are auto-generated and useless to LLM callers.

**Architecture impact:** MCP is not the safe, single product boundary the blueprint requires.

### 2. Graph / Orchestration

**Severity: High**

- `after_phase()` and `compute_actions()` are implemented but not wired into the compiled graph.
- `edges.py:71-84` hardcodes the phase sequence in `after_approval`.
- All `subgraphs/*.py` files are one-line stubs re-exporting flat nodes.
- `_services` and orchestrator state keys are not declared in `StudioGraphState`.
- `await_approval_node()` can auto-approve via the orchestrator agent before calling `interrupt()`.
- `generation_node`, `post_node`, and `delivery_node` are empty or mis-assigned shells.
- Checkpointer/rollback is not integrated into graph resume.

**Architecture impact:** The graph is a linear phase runner, not the state-driven studio OS described in the blueprint.

### 3. Agents Layer

**Severity: High**

- `agents/impl/registry.py` covers only 12 of 20 MVP agents and contains semantic mismaps (`failure-handling-agent` → `AssemblyAgent`, `clip-validator` → `QCSynthesisAgent`).
- Dedicated prompt templates are missing for ~9 declared agents.
- Create routing uses `_PHASE_DEFAULT_AGENTS`, not capability-based selection.
- No agent claims the `REVIEWER` role, so review falls back to validators.
- `_AGENT_PROFILE_MAP` in `graph/nodes.py` hardcodes every agent-to-profile binding.
- `BaseAgent.run` ignores the output of `prepare`.
- MCP bible real-mode calls `ModelRouter.resolve()`, which does not exist.

**Architecture impact:** The orchestrator cannot reliably select or execute many declared agents.

### 4. Artifacts Layer

**Severity: High**

- `ArtifactStore.save_dict()` allows raw dicts across the public boundary; used by post-production and reference-generation tools.
- `save()` always writes `status=CANDIDATE`; there is no persisted `approve` / `supersede`.
- `versioning.py` helpers are not integrated with `ArtifactStore`.
- Phase-to-directory mapping and safe-id logic are duplicated between `store.py` and `paths.py`.
- `created_by` is hard-coded to `"graph_node"` instead of the agent id.
- `AssetEntry.path` is a `str`, not `pathlib.Path`.
- `ArtifactIndex` is exported but unused; `list_artifacts` scans disk recursively.

**Architecture impact:** Artifacts do not yet provide the versioned, lineage-complete contract the blueprint requires.

### 5. Validation, Providers, Generation

**Severity: High**

- `score_to_status` ignores `review_at`, making `NEEDS_REVISION` unreachable.
- `ValidatorRegistry` exists but `GraphServices.validator_registry` is `None`; validators are imported directly.
- `generation_node` never consults the generation ledger; ledger is only used by MCP tools.
- `start_generation_batch` passes `prompt_ref` (a reference string) as the prompt text to providers.
- `failure-handling-agent` is mapped to `AssemblyAgent`.
- Provider `poll()` methods for paid providers are stubbed to complete immediately.
- Provider health is tracked in an ad-hoc dict instead of the typed `ProviderHealthTracker`.
- No provider capability enforcement before submission.

**Architecture impact:** Validation cannot express revision loops; generation state can diverge between graph and ledger; real provider submission is broken.

### 6. KB, Config, Checkpoints

**Severity: Medium-High**

- `kb_context_ref` is declared on `ArtifactMetadata` but almost never populated.
- `GraphServices.kb_builder` is `None`; graph nodes receive synthetic KB packets.
- Config resolution skips prompt inference, orchestrator normalization, and human approval.
- `ProjectConfig` Pydantic schema is defined but unused.
- Mid-project profile changes are unsupported.
- Checkpoint metadata is in-memory only; `CheckpointManager` never persists it.
- `rollback_to_checkpoint` executes immediately without enforcing confirmation.
- `BranchManager` creates a git branch but does not root it at the checkpoint commit or check it out.
- Invalidation uses a static one-hop map instead of actual artifact parentage.

**Architecture impact:** Provenance, safe recovery, and config governance are not yet real runtime behaviors.

### 7. TUI and App Services

**Severity: Medium**

- TUI uses `InProcessStudioGateway` which calls `OperatorService` directly, bypassing MCP.
- `OperatorService` reaches into runtime internals (`runtime.projects`, `artifact_store._root`).
- `runtime.approve_phase` catches `Exception` and falls back to manual phase advancement.
- Dead code: `_load_graph_state`, `_approve_current_phase`.
- TUI lacks commands for generation planning, KB, checkpoints, provider health, and rollback.

**Architecture impact:** Two operator surfaces can diverge; the TUI is not a true MCP consumer.

### 8. Tests and Documentation

**Severity: High**

- Coverage is **87.43 %**, below the 90 % threshold.
- E2E scenarios are shallow; most inject state manually and do not drive full MCP workflows.
- `rollback_to_checkpoint` E2E only asserts `ok=True`, giving false confidence.
- `acceptance-checklist.md` and `status-scorecard.md` report stale/incorrect coverage and gate status.
- `product-completion-plan/acceptance-checklist.md` claims green for items that are not green.
- Operator docs (`operations-guide.md`, `runbook-first-film.md`, `demo-guide.md`) are redirects, not instructions.
- `release-process.md` references a missing test file.
- `Makefile` `ci-check` does not include `typecheck`, contradicting `AGENTS.md` and `release-process.md`.

**Architecture impact:** Docs and tests currently give a false sense of completion.

## Risk Heat Map

| Risk | Likelihood | Impact | Mitigation priority |
|------|------------|--------|---------------------|
| `make ci-check` fails on main | certain | high | Phase 0 |
| Dangerous MCP mutations without confirmation | certain | high | Phase 1 |
| Graph does not route dynamically | certain | high | Phase 2 |
| Declared agents cannot execute | high | high | Phase 3 |
| Validation cannot express revision | certain | medium | Phase 4 |
| Generation state diverges from ledger | high | high | Phase 4 |
| Artifact provenance incomplete | certain | medium | Phase 1, 5 |
| TUI/MCP behavior divergence | high | medium | Phase 6 |
| Stale docs mislead operators | certain | medium | Phase 0, 6, 7 |

## Recommended First Actions

1. Close the coverage gap and fix the docs so `make ci-check` is green.
2. Add confirmation enforcement to dangerous MCP tools.
3. Replace hardcoded `version=1` and raw `save_dict` with real artifact lifecycle methods.
4. Wire `compute_actions()` / `after_phase()` into the compiled graph and remove the hardcoded `next_map`.
5. Reconcile the three agent registries with an invariant contract test.
6. Fix `score_to_status` so `NEEDS_REVISION` is reachable.
7. Stamp `kb_context_ref` on every artifact by wiring `KBContextPacketBuilder` into `GraphServices`.
8. Add an MCP-client gateway for the TUI.

See `documentation/refactoring-plan.md` for the full phased execution plan.
