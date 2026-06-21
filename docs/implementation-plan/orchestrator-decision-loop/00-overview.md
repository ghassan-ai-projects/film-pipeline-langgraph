# Orchestrator Decision Loop — Incremental Implementation Plan

**Purpose**

Make the orchestrator the real brain of the studio without a big-bang rewrite.

## Source Documents

This plan is grounded in:

- [`architecture-blueprint.md`](../architecture-blueprint.md) — orchestrator layer (§2), matrix operating rules, failure-handling agent, provider health, multi-model review, profile system
- [`agent-architecture.md`](../agent-architecture.md) — orchestrator routing rules, escalation rules, handoff pattern, creator/reviewer/validator loop, agent families and contracts
- [`PROGRESS.md`](../PROGRESS.md) — 17-phase baseline: all phases 00–16 are complete or partial, 488 tests, 90.88% coverage

## Dependency On The 17-Phase Baseline

This plan layers on top of the completed 17-phase implementation. It does not replace any
phase. Key dependencies:

| Existing Phase | What This Plan Uses |
|----------------|---------------------|
| 01 (Schemas) | Artifact schemas, `FilmPhase`, state domains |
| 04 (Artifact Store) | Versioned storage, manifests, metadata |
| 05 (LangGraph) | StateGraph, interrupts, phase nodes, conditional edges |
| 07 (Agent Registry) | 19 MVP agent contracts, RCTCO runner |
| 08 (Review Package) | `ReviewPackageGenerator`, `ArtifactDiff`, `AvailableActions` |
| 09 (Validation) | 15 MVP validators, threshold checker, `ConsensusBuilder` |
| 10 (Mock Provider) | `MockVideoProvider`, `MockImageProvider`, scenario scripts |
| 11 (Checkpoints) | Git backend, resume manager, invalidation, rollback |
| 13 (Real Provider) | `SeedanceOpenRouterProvider`, `VeoFastProvider` |

## Target Model

```text
inspect state (including provider health, budget, failure records)
-> compute eligible actions
-> choose next best action (driven by profile policy)
-> select KB context slice for the chosen agent
-> choose creator/reviewer/validator/failure-handler
-> run work
-> review/validate (single or multi-model, per profile)
-> synthesize consensus when multiple reviewers disagree
-> decide revise / continue / human gate / escalate to failure-handler / escalate to human
-> persist versions, decisions, and state
-> repeat
```

This plan is intentionally incremental. It should strengthen the current graph and runtime
instead of replacing them wholesale.

---

## Why This Plan Exists

The repo vision already says the orchestrator should drive dynamic flow. The current code
only partially does that. Today, orchestration is split across:

- graph nodes
- router helpers
- runtime approval helpers
- review tooling
- validator and artifact infrastructure

That is workable for bootstrapping, but not enough for:

- multi-round review and revision
- evidence-driven routing
- approved-version baselines
- explainable orchestration decisions
- safe escalation when the system is not converging
- failure-handling agent integration (the agent is registered but the orchestrator does not route to it)
- provider-health-aware routing (generation can be blocked while planning/writing continues)
- profile-driven review strategy and model routing at decision time

---

## Design Goals

1. Make orchestration state-driven, not phase-script-driven.
2. Preserve existing phase nodes where possible.
3. Avoid broad refactors that destabilize working code.
4. Add missing lifecycle behavior around review, revision, and approval.
5. Integrate the failure-handling agent into the decision loop.
6. Make the orchestrator provider-health-aware — continue unrelated work when only generation is blocked.
7. Drive routing decisions from profile policy (review strategy, validator strictness, model routing).
8. Make decisions inspectable through MCP and stored artifacts.

---

## Non-Goals

This plan does **not** require:

- replacing LangGraph with a new runtime
- rewriting every phase node at once
- introducing a large new abstraction layer before there is a concrete need
- forcing every phase to become a subgraph immediately
- changing all schemas unless required for a specific orchestration gap
- re-implementing the failure-handling agent (it exists in the agent registry; this plan wires it into the routing loop)
- building a new budget system (the `BudgetState` schema exists; this plan makes routing budget-aware)

---

## Rollout Principles

### 1. Wrap, do not rewrite

Prefer introducing orchestrator services and decision records around existing nodes instead
of replacing all node logic in one step.

### 2. Add explicit state, then route from it

First make decisions and review state durable. Then change routing to depend on them.

### 3. Preserve backward-compatible entry points

Current MCP tools and runtime methods should keep working while orchestration becomes more
intelligent behind them.

### 4. Treat approval and revision as first-class state transitions

A revision request must create durable state and force the next valid action to be revision,
not silent continuation.

### 5. Only approved versions move downstream

Candidate artifacts may be reviewed many times. The next phase should consume the latest
approved version only.

---

## Phase Sequence

1. `01-orchestrator-state-model.md`
   Add the state and records the orchestrator needs to reason well.

2. `02-action-selection-and-routing.md`
   Move from static-ish routing to explicit eligible actions and selected action records.

3. `03-review-revision-loop.md`
   Make multi-round review and targeted repair real and enforceable.

4. `04-versioning-and-approved-baselines.md`
   Fix version lineage and downstream approved baselines.

5. `05-human-gates-and-review-packages.md`
   Make human review consume real review packages and orchestrator recommendations.

6. `06-mcp-visibility-and-operator-tools.md`
   Expose orchestrator reasoning, state, and review lifecycle clearly through MCP.

7. `07-rollout-validation.md`
   Add tests and rollout checks so the new behavior lands safely.

---

## Suggested Validation Commands

Run after each phase:

```bash
make test-unit
```

Run after integration-heavy phases:

```bash
make test-integration
```

Run before final completion:

```bash
make ci-check
```

---

## Success Criteria For The Overall Plan

- the orchestrator can choose the next action from current evidence (including provider health and budget)
- review and revision can happen multiple times in one phase
- revision requests create new versions and do not disappear into warnings
- human gates operate on real review packages with orchestrator recommendations
- only approved artifacts become downstream baselines
- operator tools can explain why the graph chose its next step
- the failure-handling agent is invoked for provider errors, and its structured decisions route the graph
- unrelated work (planning, writing, validation) can continue when only generation is blocked by provider health
- review strategy (single vs multi-model) and model routing are driven by the active profile, not hard-coded

---

## Risks

| Risk | Mitigation |
|------|------------|
| Broad orchestration rewrite breaks stable paths | Land behavior in narrow phases and keep existing phase nodes alive |
| State model grows ad hoc | Add a small, explicit orchestrator state domain first |
| Revision loops become infinite | Add bounded policy and convergence signals |
| Version history remains inconsistent | Fix artifact lineage before widening approval behavior |
| MCP tools expose stale or partial state | Add orchestrator-facing inspection after state model is stable |
| Failure-handling agent integration adds routing complexity | Route to failure-handler only for classified provider/runtime errors; keep happy path unchanged |
| Provider health checks add latency | Cache health state in orchestrator state; refresh on provider interaction, not every action |
