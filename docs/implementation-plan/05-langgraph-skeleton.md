# Phase 05 — LangGraph State Machine Skeleton

**Depends on:** Phase 01 (Schemas), Phase 03 (Config), Phase 04 (Artifact Store)
**Blocks:** Phases 06, 07, 10, 11, 12

---

## Goal

Implement the top-level LangGraph supervisor graph with phase routing, interrupt points for human approval, conditional edges for dynamic routing, and the typed global state model. This is the execution engine behind the MCP surface.

The graph must answer: What phase are we in? What is blocking? What can safely continue? What needs human review? What changed since last approval?

---

## Deliverables

### Files to Create

#### Graph State (`src/film_pipeline/graph/`)

- [ ] `state.py` — `FilmStudioState` TypedDict / Pydantic model with all state domains
- [ ] `nodes.py` — graph node definitions (one per phase + router + gates)
- [ ] `edges.py` — conditional edge functions (routing logic)
- [ ] `interrupts.py` — human approval interrupt points (10 gates)
- [ ] `graph.py` — `build_graph()` function assembling the full supervisor graph
- [ ] `router.py` — dynamic action router (computes eligible actions, blocked actions, next action)
- [ ] `subgraphs/` — phase subgraphs:
  - [ ] `intake.py`
  - [ ] `constitution.py`
  - [ ] `development.py`
  - [ ] `screenwriting.py`
  - [ ] `visual_dev.py`
  - [ ] `shot_bible.py`
  - [ ] `gen_planning.py`
  - [ ] `generation.py`
  - [ ] `qc.py`
  - [ ] `post.py`
  - [ ] `delivery.py`
- [ ] `__init__.py`

#### State Domains (in `state.py`)

- [ ] `project` — project identity, config, resolved profile
- [ ] `orchestrator` — current phase, eligible actions, blockers, routing decisions
- [ ] `kb_context` — current KB context packet refs
- [ ] `film_constitution` — theme, tone, visual language, camera philosophy
- [ ] `narrative` — logline, premise, treatment, act map, scene list
- [ ] `characters` — character bibles
- [ ] `environments` — environment bibles
- [ ] `camera_language` — camera language bible
- [ ] `scene_intents` — scene intent sheets
- [ ] `shot_bible` — master film matrix, continuity ledger
- [ ] `reference_strategy` — reference index, strategy
- [ ] `generation_plan` — prompt registry, provider plan, generation schedule
- [ ] `assets` — generated clips, frames, audio
- [ ] `validation` — validation ledger, consensus reports
- [ ] `approvals` — approval records, revision requests
- [ ] `issues` — issue records
- [ ] `budget` — budget state, spend records
- [ ] `provider_health` — provider health states
- [ ] `runtime_errors` — failure decisions, resume tokens
- [ ] `timeline` — audit log entries
- [ ] `delivery` — assembly manifest, delivery package

#### Tests

- [ ] `tests/unit/graph/test_state.py` — state initialization, transitions
- [ ] `tests/unit/graph/test_router.py` — action eligibility, blocking, routing
- [ ] `tests/unit/graph/test_interrupts.py` — interrupt/resume at each gate
- [ ] `tests/integration/graph/test_phase_transitions.py` — phase → phase transitions
- [ ] `tests/integration/graph/test_dynamic_routing.py` — blocked path + available path (Scenario 10)

---

## Task Checklist

- [ ] Define `FilmStudioState` with all state domains as typed fields
- [ ] Implement graph nodes for each phase (initially stubs that update state and transition)
- [ ] Implement the dynamic router:
  - [ ] Compute eligible actions based on current state
  - [ ] Compute blocked actions with reasons
  - [ ] Select next action (explainable routing decision)
- [ ] Implement 10 human approval interrupt points:
  1. Concept approval
  2. Treatment approval
  3. Script approval
  4. Shot bible approval
  5. Character/environment reference approval
  6. Prompt readiness approval
  7. Batch generation approval
  8. Output/QC approval
  9. Assembly approval
  10. Final delivery approval
- [ ] Implement conditional edges:
  - [ ] Normal progression (phase approved → next phase)
  - [ ] Revision loop (revision requested → re-run creator agent → re-validate)
  - [ ] Failure edge (validation blocked → issue → orchestrator decision)
  - [ ] Provider-block edge (provider blocked → pause queue → wait for resolution)
  - [ ] Rollback edge (rollback requested → invalidation report → confirm → restore)
- [ ] Implement `build_graph()` assembling the supervisor graph with subgraphs
- [ ] Implement graph persistence (save/load state via artifact store)
- [ ] Implement audit logging (every node execution writes `AuditLogEntry`)
- [ ] Write unit tests for state, router, interrupts
- [ ] Write integration tests for phase transitions and dynamic routing
- [ ] Run `make ci-check`

---

## Graph Shape

```
START
  → intake
  → [interrupt: config approval]
  → constitution
  → [interrupt: constitution approval]
  → development
  → [interrupt: treatment approval]
  → screenwriting
  → [interrupt: script approval]
  → visual_dev
  → [interrupt: reference approval]
  → shot_bible
  → [interrupt: shot bible approval]
  → gen_planning
  → [interrupt: prompt readiness + spend approval]
  → generation
  → [interrupt: batch acceptance]
  → qc
  → [interrupt: QC approval]
  → post
  → [interrupt: assembly approval]
  → delivery
  → [interrupt: final delivery approval]
  → END
```

Each phase internally: `router → creator agent → reviewer → validator → orchestrator synthesis → [interrupt]`

---

## Acceptance Criteria

- [ ] Graph builds and compiles without errors
- [ ] State can be serialized and deserialized (persistence)
- [ ] Router computes eligible and blocked actions correctly
- [ ] All 10 interrupt points pause execution and persist state
- [ ] Revision loop works (request → re-run → re-validate → re-review)
- [ ] Dynamic routing: blocked path doesn't prevent independent work (Scenario 10)
- [ ] Audit log records every node execution with routing decision
- [ ] Phase transitions follow the approved sequence
- [ ] All tests pass
- [ ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| LangGraph API changes | Pin `langgraph>=0.2,<0.3`; abstract behind our `build_graph()` |
| State too large for memory | Use LangGraph's checkpointer; persist to artifact store |
| Subgraph complexity | Start with stub subgraphs; fill with real agents in Phase 07 |
| Interrupt resumability | Test: interrupt → serialize → deserialize → resume |
