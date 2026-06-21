# Phase 02 — Action Selection And Routing

**Depends on:** `01-orchestrator-state-model.md`
**Blocks:** Phases 03–07 in this folder

---

## Goal

Move orchestration from mostly phase-driven transitions to explicit action selection based on
current project evidence, provider health, budget state, and profile policy.

This phase should improve the router and decision flow without replacing every phase node.

---

## Scope

Teach the orchestrator to:

- compute eligible actions from state (including provider health and budget)
- select one next action
- select the most suitable agent, validator, or failure-handler for that action
- select the KB context slice for the chosen agent
- apply profile policy to review strategy and model routing
- record why the route was chosen

Actions should include at least:

- create
- review
- validate
- revise
- present_review_package
- approve
- escalate_to_human
- escalate_to_failure_handler
- continue_unrelated_work (when generation is blocked but planning/writing can proceed)
- pause

---

## Files To Touch

- `src/film_pipeline/graph/router.py`
- `src/film_pipeline/graph/edges.py`
- `src/film_pipeline/graph/nodes.py`
- `src/film_pipeline/agents/`
  Only where needed for orchestrator-facing interfaces
- `tests/unit/graph/`
- `tests/integration/graph/`

---

## Checklist

- [ ] Refine eligible-action computation to use approved refs, review cycles, revision state, provider health, and budget state
- [ ] Add explicit selected-action output, not just next phase output
- [ ] Add explainable routing reasons for selected actions
- [ ] Route to reviewer, validator, and failure-handler roles based on the selected action
- [ ] Split `escalate` into `escalate_to_human` (creative disputes, budget overruns, identity drift) and `escalate_to_failure_handler` (provider errors, ambiguous failures, duplicate risk)
- [ ] Add `continue_unrelated_work` action for when provider health blocks generation but planning/writing/validation phases remain valid
- [ ] Apply active profile policy to review strategy selection (single model vs multi-model panel per artifact type)
- [ ] Apply active profile policy to model routing (which model to use for creator vs validator)
- [ ] Select KB context slices based on the chosen agent's `allowed_kb_domains`
- [ ] Ensure repair and revision actions prefer targeted phase-local work
- [ ] Preserve current phase-node execution paths where possible
- [ ] Add unit tests for action selection across happy, provider-blocked, and failure scenarios
- [ ] Add integration tests for action selection after revision and validation failures

---

## Acceptance Criteria

- [ ] The router can select revise/review/validate without relying only on phase order
- [ ] Blocking review or validation results prevent phase advancement
- [ ] Routing decisions are stored with reasons and selected inputs
- [ ] The orchestrator can stay inside the same phase for additional work rounds
- [ ] Existing straight-line phase progression still works when no blockers exist
- [ ] Provider health blocks route to `escalate_to_failure_handler`, not a generic pause
- [ ] When a provider is blocked, `continue_unrelated_work` keeps planning/writing/validation phases active
- [ ] Profile policy determines whether a review uses single-model or multi-model validation
- [ ] Each agent handoff includes a KB context ref scoped to that agent's allowed domains

---

## Risks

| Risk | Mitigation |
|------|------------|
| Router logic becomes unreadable | Keep decision rules flat and data-driven; extract helpers only when repeated |
| Action model diverges from current graph | Keep mapping from selected action to existing nodes explicit and small |
