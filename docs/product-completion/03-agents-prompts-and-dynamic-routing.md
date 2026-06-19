# 03 Agents, Prompts, And Dynamic Routing

---

## Goal

Make agents real, prompt-driven workers inside the product.

This area must deliver:

- real core agents
- adoption of the prompt framework by those agents
- dynamic agent routing by capability and state
- persisted handoffs and orchestration decisions

---

## Prompt Framework Requirement

The product standard is that core agents adopt the repository prompt framework in real execution.

For this project that means:

- each critical-path agent has a dedicated RCTCO template
- prompts are phase-specific and role-specific
- prompt outputs map directly into typed schemas
- prompt constraints include KB rules, artifact context, and output contract requirements

Generic fallback prompts are not sufficient for product completion.

---

## Dynamic Agent Requirement

Dynamic agents do not mean "many registered agents exist."

Dynamic agent behavior means:

- the orchestrator selects agents by capability, state, and task
- alternate agents can be chosen by policy, modality, or failure mode
- blocked work can route to repair agents while unrelated work proceeds where allowed
- routing decisions are stored and explainable

If the orchestrator always executes the same hardcoded path with no real selection logic, dynamic agents are not done.

---

## Required Core Agents

- orchestrator
- constitution creator
- treatment/development creator
- screenwriter
- visual development creator
- reference repair/reviewer
- shot bible creator
- generation planner
- QC synthesizer
- assembly/post agent

Optional later agents are not part of this minimum.

---

## Final Product Result

When this area is complete:

- core agents generate schema-valid outputs from real prompts
- prompt templates exist and are versioned for critical-path agents
- agent handoffs are persisted
- orchestrator can explain why a given agent was selected
- repair and review loops call the correct specialized agents

---

## Concrete Tests

### Unit Tests

- RCTCO template render per core agent
- prompt output parsing into schema
- capability-based lookup
- routing policy selection
- handoff persistence

### Integration Tests

- orchestrator selects different agents for create, review, and repair tasks
- agent output becomes persisted artifacts
- repair path routes to a repair-capable agent instead of generic retry
- routing explanation MCP tools reflect actual routing decisions

### Final Acceptance Tests

- script creation uses the screenwriter prompt template and stores a script artifact
- reference failure routes to reference-repair behavior
- QC issues route to QC or repair-capable agents

---

## Acceptance Criteria

This area is done only when all of the following are true:

- all critical-path agents have real prompt templates
- core agents produce schema-valid outputs in the supported flow
- agent invocation is visible through artifacts, handoffs, and audit
- routing decisions are capability-based and explainable
- repair and review flows execute specialized agent behavior
