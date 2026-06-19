# Phase 15 — Production Hardening

**Depends:** Phases 12 (E2E Mock), 13 (Real Provider), 14 (Post-Production)
**Blocks:** Phase 16 (Productization & Release Readiness)
**Human Gate:** Yes — all production changes require approval

---

## Goal

Harden the system for real production use. This includes: security hardening, observability and audit trail, cost and budget policy enforcement, model routing policy, secrets management, error recovery edge cases, performance optimization, documentation, and the production-readiness checklist that feeds the final productization phase.

---

## Deliverables

### Files to Create / Modify

#### Security (`src/film_pipeline/security/`)

- [   ] `secrets.py` — secret storage strategy, credential vault integration
- [   ] `redaction.py` — log and error redaction (no secrets in any output)
- [   ] `moderation.py` — content moderation checks before provider submission
- [   ] `__init__.py`

#### Observability (`src/film_pipeline/observability/`)

- [   ] `audit.py` — full audit trail (every MCP request, graph node, agent, model, KB context, cost, provider action)
- [   ] `metrics.py` — runtime metrics (phase duration, agent calls, validation scores, cost tracking)
- [   ] `explainability.py` — decision explainability (why was this agent chosen? why was this KB context selected?)
- [   ] `blockers.py` — blocking reason reporter
- [   ] `__init__.py`

#### Model Routing (`src/film_pipeline/agents/model_routing/`)

- [   ] `router.py` — model selection per agent role, cost-aware routing
- [   ] `fallback.py` — model fallback chain
- [   ] `profiles.py` — model profiles (creative_writer, strict_validator, visual_reasoner, schema_enforcer, cheap_draft, operations_triage)
- [   ] `__init__.py`

#### Additional Agents (Beyond MVP)

- [   ] `src/film_pipeline/agents/specialists/` — specialized agents added as needed:
  - [   ] `dialogue_agent.py`
  - [   ] `theme_agent.py`
  - [   ] `pacing_agent.py`
  - [   ] `character_arc_agent.py`
  - [   ] `shot_design_validator.py`
  - [   ] `bad_reference_detector.py`
  - [   ] `lessons_agent.py`
  - [   ] `cost_report_agent.py`
  - [   ] `postmortem_agent.py`

#### Documentation

- [   ] `docs/operations-guide.md` — how to operate the studio via MCP
- [   ] `docs/troubleshooting.md` — common issues and solutions
- [   ] `docs/provider-setup.md` — provider credential setup
- [   ] Update `README.md` — full setup and usage guide
- [   ] Update `AGENTS.md` — production agent rules

---

## Task Checklist

### Security Hardening

- [   ] Implement secret storage strategy:
  - [   ] Environment variables for API keys
  - [   ] No secrets in code, configs, artifacts, or logs
  - [   ] Per-provider credential health check
- [   ] Implement log and error redaction:
  - [   ] Scan all log entries for key patterns
  - [   ] Redact before writing to audit log
  - [   ] Redact error messages before returning to MCP
- [   ] Implement content moderation:
  - [   ] Check prompts before provider submission
  - [   ] Flag potentially moderated content
  - [   ] Require human approval for flagged content

### Observability

- [   ] Implement full audit trail:
  - [   ] Log every MCP request (request_id, project_id, tool, timestamp)
  - [   ] Log every graph node execution (node, agent, model, duration)
  - [   ] Log every KB context selection (packet_id, included_refs, excluded_refs)
  - [   ] Log every provider action (submit, poll, download, cost)
  - [   ] Log every validation result (validator, score, status)
  - [   ] Log every approval (approver, artifact, phase)
  - [   ] Log every routing decision (selected_agent, reason)
- [   ] Implement metrics:
  - [   ] Phase duration tracking
  - [   ] Agent call counts and success rates
  - [   ] Validation score distributions
  - [   ] Cost tracking (estimated vs actual)
  - [   ] Provider job success rates
- [   ] Implement explainability:
  - [   ] `explain_last_decision` — why was the last action taken?
  - [   ] `explain_agent_routing` — why was this agent selected?
  - [   ] `explain_kb_context` — why was this KB context chosen?
  - [   ] `get_blockers` — what is blocking progress and why?
- [   ] Implement `get_next_actions` — what can safely continue?

### Cost and Budget Policy

- [   ] Formalize budget policy in config:
  - [   ] Per-project budget cap
  - [   ] Per-phase budget cap
  - [   ] Per-provider budget cap
  - [   ] Max auto-approved cost
  - [   ] Human approval threshold
- [   ] Implement spend approval workflow:
  - [   ] Estimate cost before generation
  - [   ] Block if over budget
  - [   ] Require human approval if above threshold
  - [   ] Record actual cost after generation
  - [   ] Alert when approaching cap
- [   ] Implement provider switch approval:
  - [   ] No automatic switch unless profile allows
  - [   ] Human approval required for more expensive provider
  - [   ] Cost-impact analysis before switch

### Model Routing Policy

- [   ] Implement model profiles:
  - [   ] `creative_writer` — strong creative model for writing agents
  - [   ] `strict_validator` — precise model for validators
  - [   ] `visual_reasoner` — model strong at visual analysis
  - [   ] `schema_enforcer` — model strict about JSON schemas
  - [   ] `cheap_draft` — low-cost model for drafts
  - [   ] `operations_triage` — model for failure handling
- [   ] Implement routing rules:
  - [   ] Creator and validator use different models
  - [   ] High-impact artifacts get at least 2 independent reviews
  - [   ] Cost-aware: use cheaper model when possible
  - [   ] Fallback chain: if primary model unavailable, use fallback
- [   ] Implement multi-model review quorum:
  - [   ] Minimum reviewers per artifact type
  - [   ] Disagreement synthesis rules
  - [   ] Escalation on persistent disagreement

### Error Recovery Edge Cases

- [   ] Test and fix: process crash during generation
- [   ] Test and fix: provider outage mid-batch
- [   ] Test and fix: multiple simultaneous failures
- [   ] Test and fix: rollback during generation
- [   ] Test and fix: KB conflict during critical operation
- [   ] Test and fix: project ambiguity during expensive action
- [   ] Test and fix: validator service unavailable
- [   ] Test and fix: disk full during asset download

### Performance

- [   ] Profile graph execution time
- [   ] Optimize KB retrieval (cache frequent packets)
- [   ] Optimize artifact store I/O (batch reads)
- [   ] Optimize validation (parallel validators where independent)
- [   ] Optimize generation polling (configurable intervals)

### Documentation

- [   ] Write operations guide
- [   ] Write troubleshooting guide
- [   ] Write provider setup guide
- [   ] Update README with full setup and usage
- [   ] Update AGENTS.md with production rules
- [   ] Document all MCP tools with examples

### Production Readiness Checklist

- [   ] All E2E scenarios pass (1-10)
- [   ] Real provider adapter tested with 1-second test clip
- [   ] Budget enforcement verified with real costs
- [   ] Credential management verified
- [   ] No secrets in any log, artifact, or error
- [   ] Audit trail explains every action
- [   ] All validators produce correct reports
- [   ] Rollback tested with real artifacts
- [   ] Resume tested after crash
- [   ] Post-production produces valid delivery package
- [   ] Documentation complete
- [   ] `make ci-check` passes with 90% coverage

---

## Acceptance Criteria

- [   ] No secrets in any log, artifact, or error message
- [   ] Audit trail records every action with full context
- [   ] `explain_last_decision`, `explain_agent_routing`, `explain_kb_context` return meaningful explanations
- [   ] `get_blockers` correctly reports all blocking issues
- [   ] `get_next_actions` correctly reports available and blocked actions
- [   ] Budget enforcement blocks over-spend
- [   ] Human approval required for spend above threshold
- [   ] Model routing uses different models for creator and validator
- [   ] Multi-model review produces consensus with preserved disagreements
- [   ] All error recovery edge cases handled
- [   ] All E2E scenarios pass
- [   ] Documentation complete and accurate
- [   ] `make ci-check` passes
- [   ] 90% coverage maintained

---

## Risks

| Risk | Mitigation |
|------|------------|
| Scope creep — hardening never ends | Define "done" as the production readiness checklist; iterate from there |
| Performance regressions | Profile before and after optimization; benchmark E2E test duration |
| Security gaps | External security review; automated secret scanning in CI |
| Model routing complexity | Start with 2 profiles (creative_writer, strict_validator); add more only when needed |
