# Phase 03 - Dynamic Routing, Handoffs, And Explainability

Depends on: Phase 02
Blocks: Phases 04-06

---

## Goal

Turn the agent system from static path execution into real capability-based routing with persisted handoffs and explainable decisions.

---

## Current Risk

The repository has agent registration and routing scaffolding, but product completion requires more than "many agents exist."

The system must prove:

- the orchestrator chooses agents based on task and state
- repair paths choose repair-capable agents
- review paths choose review-capable agents
- routing decisions are explainable to operators

---

## Product Result

When this phase is complete:

- dynamic routing selects different agents for create, review, repair, and QC tasks
- routing can react to validation findings, blocked providers, and project state
- handoffs are persisted with inputs, expectations, and outcomes
- audit/MCP explanations describe the real routing decisions made

---

## Implementation Work

### Routing Logic

- implement capability/state/policy-based agent selection
- allow alternate agent choice by:
  - task type
  - artifact type
  - blocked capability
  - repair requirement
  - validator outcome
- make fallback routing explicit rather than hidden retry behavior

### Handoff Persistence

- persist input artifact refs
- persist selected agent id
- persist routing reason
- persist expected output schema
- persist resulting artifact refs or failure reason

### Explainability

- align `explain_agent_routing` and related audit tools with actual routing data
- ensure explanations come from persisted decisions, not reconstructed guesses

---

## Files To Create Or Modify

- `src/film_pipeline/agents/registry.py`
- `src/film_pipeline/agents/handoff.py`
- `src/film_pipeline/graph/router.py`
- `src/film_pipeline/graph/nodes.py`
- `src/film_pipeline/observability/audit.py`
- `src/film_pipeline/mcp/tools/__init__.py`
- routing/handoff tests

---

## Mandatory Behavior Tests

- create flow selects the creator-capable agent
- review flow selects the review-capable agent
- repair flow after a failed validation selects a repair-capable agent instead of rerunning the same generic path
- routing explanation tool returns the real selected agent and reason
- handoff records contain input refs, output refs, and schema expectations

---

## Acceptance Criteria

- [ ] orchestrator selection is capability-based and state-aware
- [ ] alternate routing paths are tested
- [ ] repair and review use specialized routing behavior
- [ ] handoffs are persisted and queryable
- [ ] MCP explanation tools reflect actual routing records
- [ ] dynamic routing behavior is proven by integration tests

---

## Exit Condition

This phase is done when "dynamic agents" means observable runtime behavior, not just registration metadata.
