# Phase 02 — MCP Tool Contracts

**Depends on:** Phase 01 (Schemas & Registries)
**Blocks:** Phase 05 (LangGraph Skeleton), Phase 12 (E2E)

---

## Goal

Define the MCP tool surface as formal contracts — tool name, input schema, output schema, permissions, idempotency, mutation flag, checkpoint behavior, confirmation requirements, and error contracts. Implement the MCP server skeleton with tool registration and dispatch, backed by LangGraph but initially stubbed.

The MCP contract is the product boundary. Every major capability must be reachable through an MCP tool before it is exposed through any other interface.

---

## Deliverables

### Files to Create

#### MCP Contract Spec (`docs/implementation-plan/mcp-tool-catalog.md`)

- [ ] Full catalog of all MCP tools with input/output schemas, permissions, idempotency, mutation flags

#### MCP Server (`src/film_pipeline/mcp/`)

- [ ] `server.py` — MCP server setup, tool registration, dispatch
- [ ] `tools/` — tool implementations grouped by domain:
  - [ ] `project.py` — `create_film_project`, `list_projects`, `find_project`, `set_active_project`, `get_active_project`, `get_project_summary`
  - [ ] `intake.py` — `submit_idea`, `get_intake_analysis`, `approve_intake`
  - [ ] `state.py` — `get_current_phase`, `get_film_state`, `get_orchestrator_summary`, `get_next_actions`, `get_blockers`
  - [ ] `review.py` — `review_phase_artifacts`, `approve_phase`, `request_revision`
  - [ ] `artifact.py` — `list_artifacts`, `inspect_artifact`, `list_shots`, `inspect_shot`, `inspect_scene`, `inspect_reference`, `inspect_continuity_report`
  - [ ] `validation.py` — `get_validation_report`, `list_validation_issues`
  - [ ] `generation.py` — `plan_generation_batch`, `approve_generation_spend`, `start_generation_batch`, `get_generation_status`, `resume_generation_polling`, `list_active_generations`, `cancel_generation_request`, `promote_test_to_production`
  - [ ] `kb.py` — `kb_search`, `kb_get_item`, `kb_get_context_packet`, `kb_explain_context_choice`, `kb_list_sources`
  - [ ] `checkpoint.py` — `list_checkpoints`, `create_checkpoint`, `get_checkpoint`, `compare_versions`, `list_artifact_versions`, `rollback_artifact`, `rollback_to_checkpoint`, `get_invalidation_report`
  - [ ] `coverage.py` — `plan_coverage_group`, `list_coverage_groups`, `inspect_coverage_group`, `approve_coverage_generation`
  - [ ] `assembly.py` — `assemble_review_cut`, `assemble_final_cut`, `export_delivery_package`
  - [ ] `audit.py` — `get_audit_log`, `explain_last_decision`, `explain_agent_routing`, `explain_kb_context`
  - [ ] `provider.py` — `check_provider_health`, `resolve_provider_block`, `list_providers`
- [ ] `errors.py` — MCP error types, error response schema
- [ ] `middleware.py` — project resolution middleware, request envelope creation
- [ ] `__init__.py`

#### Tests

- [ ] `tests/unit/mcp/test_tool_registration.py` — every tool is registered
- [ ] `tests/unit/mcp/test_project_resolution.py` — project lookup, ambiguity handling
- [ ] `tests/unit/mcp/test_request_envelope.py` — envelope creation and validation
- [ ] `tests/integration/mcp/test_stub_dispatch.py` — tools return stubbed responses with correct schemas

---

## Task Checklist

- [ ] Write `docs/implementation-plan/mcp-tool-catalog.md` with full tool definitions
- [ ] Define `MCPToolContract` schema (name, description, input_schema, output_schema, mutates_state, requires_confirmation, creates_checkpoint, idempotency_key)
- [ ] Implement `src/film_pipeline/mcp/server.py` with tool registration framework
- [ ] Implement project resolution middleware (exact id → slug → title → alias → fuzzy → ask)
- [ ] Implement request envelope creation (`RequestEnvelope` schema)
- [ ] Implement stub responses for all tools (return empty/placeholder data with correct schema)
- [ ] Implement error response schema and error handling
- [ ] Write unit tests for tool registration
- [ ] Write unit tests for project resolution and ambiguity
- [ ] Write integration tests for stub dispatch
- [ ] Run `make ci-check`

---

## MCP Tool Groups (Minimum)

| Group | Tools | Phase Implemented |
|-------|-------|-------------------|
| Project | `create_film_project`, `list_projects`, `find_project`, `set_active_project`, `get_active_project`, `get_project_summary` | Phase 05 |
| Intake | `submit_idea`, `get_intake_analysis`, `approve_intake` | Phase 07 |
| State | `get_current_phase`, `get_film_state`, `get_orchestrator_summary`, `get_next_actions`, `get_blockers` | Phase 05 |
| Review | `review_phase_artifacts`, `approve_phase`, `request_revision` | Phase 08 |
| Artifact | `list_artifacts`, `inspect_artifact`, `list_shots`, `inspect_shot`, `inspect_scene`, `inspect_reference` | Phase 04 |
| Validation | `get_validation_report`, `list_validation_issues` | Phase 09 |
| Generation | `plan_generation_batch`, `approve_generation_spend`, `start_generation_batch`, `get_generation_status`, `resume_generation_polling`, `cancel_generation_request`, `promote_test_to_production` | Phase 10 |
| KB | `kb_search`, `kb_get_item`, `kb_get_context_packet`, `kb_explain_context_choice` | Phase 06 |
| Checkpoint | `list_checkpoints`, `create_checkpoint`, `rollback_to_checkpoint`, `get_invalidation_report` | Phase 11 |
| Audit | `get_audit_log`, `explain_last_decision`, `explain_agent_routing` | Phase 05 |
| Provider | `check_provider_health`, `resolve_provider_block`, `list_providers` | Phase 10 |
| Coverage | `plan_coverage_group`, `list_coverage_groups`, `inspect_coverage_group` | Phase 13 |
| Assembly | `assemble_review_cut`, `assemble_final_cut`, `export_delivery_package` | Phase 14 |

---

## Acceptance Criteria

- [ ] `mcp-tool-catalog.md` documents every tool with input/output schema
- [ ] MCP server starts and registers all tools
- [ ] Tool dispatch returns correctly-typed stub responses
- [ ] Project resolution handles exact match, alias, fuzzy, and ambiguity
- [ ] Request envelope is created for every mutation
- [ ] Error responses follow a consistent schema
- [ ] All MCP tool tests pass
- [ ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| MCP library API changes | Pin `mcp>=1.0`; abstract behind our own `MCPToolContract` |
| Tool surface too large for first pass | Implement stubs only; real behavior filled by later phases |
| Project resolution edge cases | Test ambiguity scenario from e2e-test-scenarios.md Scenario 9 |
