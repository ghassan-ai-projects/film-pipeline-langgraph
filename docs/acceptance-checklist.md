# Acceptance Checklist — film-pipeline-langgraph v0.2.0

Created: 2026-06-19 | Based on comprehensive review findings.

---

## Code Quality Gates (CI)

- [x] `make format-check` passes (ruff format)
- [x] `make lint` passes (ruff check)
- [x] `make typecheck` passes (mypy strict)
- [x] `make test` passes (pytest, 488 tests)
- [x] Coverage ≥ 90% (current: 92.65%)
- [x] `make build` succeeds (sdist + wheel)

## Architecture Gates

- [x] Sub-package boundaries match architecture blueprint (16 sub-packages)
- [x] Pydantic v2 schemas for all type contracts (27 schemas)
- [x] MCP-first surface with tool registry (57 tools defined)
- [x] LangGraph StateGraph with 11 phase nodes + approval gates
- [x] Agent registry with 19 MVP agent contracts
- [x] Validator registry with 15 validator contracts
- [x] KB manifest with 12 curated items, layered retrieval
- [x] Mock provider with 13 scenario scripts
- [x] Git-backed checkpoint system with invalidation engine
- [x] Post-production agents (assembly, transitions, audio, delivery, subtitles)

## MCP Wiring (blocking gaps addressed 2026-06-19)

- [x] Project management tools (create, list, set_active, get_active)
- [x] Intake tools (submit_idea with graph execution)
- [x] Review tools (approve_phase, request_revision)
- [x] Assembly tools (assemble_review_cut, export_delivery_package)
- [x] State tools (get_current_phase, get_film_state, get_orchestrator_summary, get_next_actions, get_blockers)
- [x] Audit tools (get_audit_log, explain_last_decision, explain_agent_routing, explain_kb_context)
- [x] Checkpoint tools (list, create, get, compare_versions, list_artifact_versions, rollback_to_checkpoint, get_invalidation_report)
- [x] Provider tools (check_provider_health, resolve_provider_block, list_providers)
- [x] KB tools (kb_search, kb_get_item, kb_get_context_packet, kb_explain_context_choice)
- [ ] Generation tools (8 stubs pending provider wiring)
- [ ] Validation tools (2 stubs pending artifact integration)

## Productization Gates (Phase 16)

- [x] `app/runtime.py` — StudioRuntime singleton with checkpoint/audit/health methods
- [x] `app/smoke.py` — smoke test runner
- [x] `app/bootstrap.py` — environment validation
- [x] `app/health.py` — readiness checks
- [x] `app/version.py` — version metadata
- [x] `profiles/mock-demo.yaml` — safe demo profile
- [x] `profiles/local-real-provider.yaml` — real provider profile
- [x] `make run-mcp` target
- [x] `make demo-project` target
- [x] `make release-check` target
- [ ] `docs/operations-guide.md`
- [ ] `docs/runbook-first-film.md`
- [ ] `docs/release-process.md`
- [ ] `docs/demo-guide.md`

## E2E Acceptance Gates (Phase 12 — deferred to post-v0.2.1)

- [ ] Scenario 1: Happy path (idea → review cut, mock provider)
- [ ] Scenario 2: Script revision gate
- [ ] Scenario 3: Reference validation failure
- [ ] Scenario 4: Provider quota exhausted (MUST PASS)
- [ ] Scenario 5: Network error / no duplicate submit (MUST PASS)
- [ ] Scenario 6: Continuity drift detection (MUST PASS)
- [ ] Scenario 7: Rollback after bad style change
- [ ] Scenario 8: KB policy conflict resolution
- [ ] Scenario 9: Active project ambiguity
- [ ] Scenario 10: Dynamic flow (blocked + available paths)

## Known Limitations

- Graph nodes are label-transition stubs (set phase, approval flags) — no agents invoked
- No LangGraph interrupt mechanism used; GraphRecursionError as control flow
- 24 MCP tools remain as stubs (generation, validation, coverage groups)
- No per-agent RCTCO prompt templates (deferred)
- No real validator logic (validators return canned reports)
- No ffmpeg integration (post-production agents produce plans only)
- No continuous KB learning loop

## Sign-Off

- [ ] Architecture review approved
- [ ] CI/CD pipeline green
- [ ] Release tag created (v0.2.0)
