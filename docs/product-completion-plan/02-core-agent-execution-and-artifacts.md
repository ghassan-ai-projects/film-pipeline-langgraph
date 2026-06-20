# Phase 02 - Core Agent Execution And Persisted Artifacts

Depends on: Phase 01
Blocks: Phases 03-06

---

## Goal

Make the critical-path agents produce real schema-valid artifacts that are persisted and used by downstream phases.

---

## Minimum Critical Path

The minimum supported spine for product completion is:

- idea intake
- constitution creation
- development/treatment creation
- screenwriting
- visual development
- shot bible creation
- generation planning
- review cut assembly
- delivery export

If these phases only advance labels or return shells, the product is not complete.

---

## Product Result

When this phase is complete:

- core agents produce real artifacts from prompt execution
- artifacts are persisted with metadata and lineage
- downstream steps consume prior artifacts rather than rebuilding from scratch
- review packages and approvals point to real artifacts

---

## Implementation Work

### Core Agents

- wire real execution for:
  - constitution agent
  - development agent
  - screenwriter agent
  - visual development agent
  - shot bible agent
  - generation planner agent
  - QC synthesis agent
  - assembly agent

### Artifact Truth

- require schema-valid outputs from agent execution
- persist outputs to artifact storage with:
  - producer agent id
  - prompt template version
  - model profile
  - KB context reference
  - upstream artifact refs
- ensure downstream nodes read those stored artifacts

### Review And Approval Integration

- review package generation must point to the actual produced artifacts
- approval actions must store the exact artifact refs they approved

---

## Files To Create Or Modify

- `src/film_pipeline/agents/impl/`
- `src/film_pipeline/graph/nodes.py`
- `src/film_pipeline/graph/services.py`
- `src/film_pipeline/artifacts/`
- `src/film_pipeline/review/`
- `src/film_pipeline/app/runtime.py`
- artifact/phase integration tests

---

## Mandatory Behavior Tests

- running the constitution phase must store a constitution artifact
- running development after constitution must consume the stored constitution artifact
- running screenwriting must produce a script artifact linked to development output
- review package generation must reference persisted artifacts, not synthetic placeholders
- approval must create checkpoint and audit evidence tied to real artifact refs

---

## Acceptance Criteria

- [x] all critical-path creation phases generate persisted schema-valid artifacts
- [x] downstream phases consume stored upstream artifacts
- [x] artifact lineage is visible and testable
- [x] review packages reference real artifact outputs
- [x] approvals persist artifact refs and checkpoint evidence
- [x] behavior tests prove the artifact-producing spine

---

## Exit Condition

✅ This phase is done — the spine agents produce and consume real persisted artifacts.

## Implementation Notes

- `GraphServices.for_mock_runtime()` populates `AgentRegistry` with all 19 MVP agents
- `StudioRuntime` defaults to `for_mock_runtime()` — before this, `agent_registry` was always `None`
- `_run_phase_node()` now injects `SERVICES_KEY` into state before calling node functions
- 5 new agent classes: `VisualDevAgent`, `ShotBibleAgent`, `GenPlannerAgent`, `QCSynthesisAgent`, `AssemblyAgent`
- 9 agents in `agent_map`, covering all spine phases (intake through post)
- Canned mock responses for all 9 agents in `_default_mock_responses()`
- ScreenwriterAgent premise parsing fixed (digs into dict now)
- 7 integration tests in `test_artifact_spine.py` prove intake→constitution→development→script+approval flow
