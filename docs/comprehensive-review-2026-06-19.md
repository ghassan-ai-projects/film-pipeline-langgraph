# Comprehensive Project Review — 2026-06-19

**Reviewer:** Qwen Code orchestrator
**Scope:** Full codebase, tests, docs, acceptance criteria, architecture alignment
**CI Status At Review Time:** ✅ Green (472 tests, 93.23% coverage, mypy strict, ruff, build)

> Update after follow-up fixes: the repo now passes the full local test suite at **488 tests / 90.88% coverage**. The Seedance adapter tests were repaired, MCP approval now advances phases and creates git-backed checkpoints, and some MCP/runtime review findings below are now partially resolved. The remaining gaps in this review still apply to real artifact-producing orchestration, deferred E2E scenarios, and stubbed MCP surfaces.

---

## Executive Summary

The project is a **well-engineered scaffold with strong infrastructure** but is **not yet a functional film studio**. All 17 implementation phases are marked complete, CI is green, and code quality is high. However, the acceptance criteria — particularly the E2E scenarios from Phase 12 and the productization deliverables from Phase 16 — are **substantially unmet**. The graph nodes are passthrough stubs, 84% of MCP tools return "not yet wired" stubs, and no real film production (idea → review cut) has been demonstrated end-to-end.

**Verdict:** Architecture-grade scaffold ready for real implementation. Not production-ready. Not demoable. The acceptance test suite proves infrastructure wiring, not studio behavior.

---

## 1. CI & Test Quality

### What's Strong

| Metric | Value |
|--------|-------|
| Tests passing | 472 |
| Coverage | 93.23% (threshold: 90%) |
| Source lines | ~8,700 |
| Test lines | ~5,700 |
| mypy strict | ✅ passes |
| ruff lint | ✅ passes |
| ruff format | ✅ passes |
| Build (sdist + wheel) | ✅ passes |

The test-to-code ratio (~0.65) is healthy. Unit tests are well-organized mirroring the source structure. Coverage is genuinely broad — most modules at 90-100%.

### What's Weak

**Coverage measures lines, not behavior.** The 93.23% coverage is real but misleading at the acceptance level:

- `mcp/tools/__init__.py` is at 67% — 46 stub handlers execute (returning `{"stub": True}`) but that's not meaningful coverage
- `graph/nodes.py` is at 100% but every node is a 4-line passthrough that sets `current_phase` and `human_approval_required`
- `state.py` is at 0% — the dataclass was replaced by a dict but the dead code remains
- `security/__init__.py` is at 0% — a 3-line re-export module
- `veo_fast.py` is at 42% — a stub adapter

**The E2E tests don't test end-to-end behavior.** They test that:
- The graph compiles ✅
- Infrastructure objects can be instantiated ✅
- Phase names are in the right order ✅
- Node functions set the right fields ✅

They do **not** test:
- An idea flowing through to a review cut ❌
- Mock human driving approvals through MCP ❌
- Mock provider generating clips ❌
- Validators scoring artifacts ❌
- Assembly agent producing a cut ❌

---

## 2. Acceptance Criteria Assessment

### Phase 12 — E2E Mock Mini-Film (CRITICAL GAP)

The plan defined **10 E2E scenarios** with detailed checklists. Only **2 test files exist**, and neither runs a real pipeline.

| Scenario | Plan Status | Actual Status |
|----------|-------------|---------------|
| 01 — Happy path (idea → review cut) | MUST PASS | ❌ Infrastructure smoke test only |
| 02 — Script revision | SHOULD PASS | ❌ Missing |
| 03 — Reference failure | SHOULD PASS | ❌ Missing |
| 04 — Quota exhausted | MUST PASS | ❌ Missing |
| 05 — Network error / no duplicate submit | MUST PASS | ❌ Missing |
| 06 — Continuity drift | MUST PASS | ❌ Missing |
| 07 — Rollback | SHOULD PASS | ❌ Missing |
| 08 — KB policy conflict | SHOULD PASS | ❌ Missing |
| 09 — Project ambiguity | SHOULD PASS | ❌ Missing |
| 10 — Dynamic flow | SHOULD PASS | ❌ Missing |

**4 of 4 MUST-PASS scenarios are unimplemented.** The existing "happy path" test verifies graph compilation and registry population — it does not submit an idea, run the graph through phases, generate clips, or assemble a cut.

The universal checks from Phase 12 are also unverified:
- ❌ No artifact verification (expected_artifacts.json fixture doesn't exist)
- ❌ No approval record verification per phase
- ❌ No shot-to-matrix-row mapping verification
- ❌ No continuity ledger verification
- ❌ No validation report verification
- ❌ No audit log verification
- ❌ No mock generation ledger verification

### Phase 16 — Productization (SIGNIFICANT GAPS)

The plan defined specific deliverables. What exists vs. what's missing:

| Deliverable | Status |
|-------------|--------|
| `app/smoke.py` | ✅ Exists (58% coverage) |
| `app/runtime.py` | ✅ Exists |
| `app/bootstrap.py` | ❌ Missing |
| `app/health.py` | ❌ Missing |
| `app/version.py` | ❌ Missing |
| `scripts/run_local_mcp.py` | ❌ Missing |
| `scripts/create_demo_project.py` | ❌ Missing |
| `scripts/release_check.py` | ❌ Missing |
| `profiles/mock-demo.yaml` | ❌ Missing |
| `profiles/local-real-provider.yaml` | ❌ Missing |
| `examples/demo-project/` | ❌ Missing |
| `docs/operations-guide.md` | ❌ Missing |
| `docs/runbook-first-film.md` | ❌ Missing |
| `docs/release-process.md` | ❌ Missing |
| `docs/demo-guide.md` | ❌ Missing |
| `docs/acceptance-checklist.md` | ❌ Missing |
| `make run-mcp` target | ❌ Missing |
| `make demo-project` target | ❌ Missing |
| `make release-check` target | ❌ Missing |

**Acceptance criteria for Phase 16 are largely unmet:**
- ❌ A new operator cannot install and run from documentation alone
- ❌ No `make run-mcp` command
- ❌ No bootstrap validation with actionable failure messages
- ❌ No health checks
- ❌ No demo project
- ❌ No release-check command
- ❌ No example profiles
- ❌ No acceptance checklist document

---

## 3. Architecture & Structure

### What's Excellent

The sub-package structure is **textbook-clean** and maps 1:1 to the architecture blueprint:

```
src/film_pipeline/
├── schemas/       27 Pydantic v2 models — all at 100% coverage
├── mcp/           Tool registry, contract, envelope, server, 57 tool definitions
├── config/        Layered profile merge system (loader, merger, resolver, validator)
├── artifacts/     Versioned store, manifest, metadata, index, paths
├── graph/         StateGraph, 11 nodes, 11 subgraphs, edges, router, interrupts
├── kb/            Manifest (12 items), retrieval, conflicts, packets, curator
├── agents/        Registry (19 agents), base, runner, handoff, model routing
├── review/        Generator, diff engine, actions calculator — all 100% coverage
├── validation/    Registry (15 validators), base, thresholds, consensus
├── providers/     Mock (video + image), Seedance adapter, VeoFast stub, health, registry
├── checkpoints/   Git backend, manager, resume, rollback, invalidation, branches
├── post/          Assembly, transitions, audio, delivery, subtitles, validators
├── observability/ Audit trail, metrics, blockers
├── security/      Credential redaction wrapper
├── testing/       Mock human (7 profiles), mock model, 13 scenarios
└── app/           Runtime singleton, smoke runner
```

- Domain isolation is respected — sub-packages don't cross-import
- Pydantic v2 schemas are consistent and well-typed
- The config system (layered YAML merge with conflict detection) is production-quality
- The mock provider with scenario scripts is a genuinely useful test harness
- Git-backed checkpoints with invalidation engine is well-designed
- Credential redaction in the Seedance adapter is correct

### What's Weak

**The graph is a skeleton, not an engine.** Every phase node does the same thing:

```python
def script_node(state):
    new_state = deepcopy(state)
    new_state["current_phase"] = "script"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "script"
    return new_state
```

No agent is invoked. No artifact is created. No KB context is retrieved. No validation runs. No provider is called. The graph transitions phase labels but produces nothing.

**The runtime uses GraphRecursionError as normal control flow:**

```python
try:
    return graph.invoke(state, config={"recursion_limit": 3})
except GraphRecursionError:
    # Fall back to streaming to get the latest state
    ...
```

This is a code smell. The graph cycles between phase nodes and `await_approval` without a real interrupt mechanism. LangGraph's `interrupt_before` / `interrupt_after` should be used for human gates, not recursion limits.

**The 11 subgraph files exist but are not wired into the graph.** `build_graph()` uses flat nodes, not subgraphs. The subgraphs in `graph/subgraphs/` are standalone modules that aren't composed into the supervisor graph.

**State is a raw `dict[str, Any]`, not the typed `FilmStudioState`.** The `state.py` dataclass exists at 0% coverage — it was abandoned in favor of dicts. This contradicts the architecture blueprint's "typed state" principle and the AGENTS.md "Pydantic v2 for all schemas" rule.

---

## 4. MCP Surface

### Wired Tools (9 of 57 — 16%)

| Tool | Works? | Notes |
|------|--------|-------|
| `create_film_project` | ✅ | Creates in-memory dict state |
| `list_projects` | ✅ | Returns project IDs |
| `set_active_project` | ✅ | Sets active project ID |
| `get_active_project` | ✅ | Returns active project summary |
| `submit_idea` | ⚠️ | Runs graph with recursion_limit=3, catches GraphRecursionError |
| `approve_phase` | ⚠️ | Calls approve_phase_node directly, bypassing graph |
| `request_revision` | ⚠️ | Calls request_revision_node directly, bypassing graph |
| `assemble_review_cut` | ✅ | Calls AssemblyAgent.build_plan |
| `export_delivery_package` | ✅ | Calls DeliveryPackagingAgent.build_package |

### Stub Tools (46 of 57 — 84%)

All return `{"stub": True, "message": "Not yet wired to orchestrator."}`. This includes:
- All generation tools (plan_generation_batch, start_generation_batch, etc.)
- All checkpoint tools (list_checkpoints, create_checkpoint, rollback_to_checkpoint)
- All validation tools (get_validation_report, list_validation_issues)
- All KB tools (kb_search, kb_get_context_packet)
- All audit tools (get_audit_log, explain_last_decision)
- All provider tools (check_provider_health, list_providers)
- All coverage tools

The PROGRESS.md says "9 tools fully wired" but `get_current_phase` and `get_film_state` are listed as "partially wired" — they return stubs when no active project exists. In practice, only 7 tools do real work.

**The MCP-first principle is architecturally present but not operationally delivered.** The contract, envelope, and registry infrastructure is excellent. The actual wiring is minimal.

---

## 5. Agent & Validation Systems

### Agents

- 19 agent contracts registered with proper metadata (domain, capabilities, KB domains, input/output artifacts)
- `BaseAgent` lifecycle (prepare → execute → validate) is well-structured
- `RCTCOPromptRunner` builds structured prompts from contracts
- `MockModelAdapter` returns canned responses per agent_id
- `HandoffManager` records agent-to-agent transitions

**Gap:** No agent actually produces artifacts. The `execute()` method calls the mock model and returns a canned dict. There are no per-agent RCTCO prompt templates (acknowledged as deferred). The agents are metadata shells, not working specialists.

### Validation

- 15 validator contracts registered
- `BaseValidator` has a proper validate → score → report lifecycle
- Threshold system (pass ≥ 85, review ≥ 75, block < 75) is correct
- `ConsensusBuilder` handles multi-model agreement with shared findings and disagreements

**Gap:** Validators are metadata, not logic. The `validate()` method returns a canned `ValidationReport`. No validator actually inspects an artifact against a rubric. The consensus builder works on synthetic reports, not real validation output.

### Knowledge Base

- 12 KB items loaded from YAML (6 canonical, 3 playbooks, 3 case studies)
- Authority conflict resolution (canonical > playbook > case study) works correctly
- `KBContextPacketBuilder` assembles per-agent/per-phase packets
- Tag-based retrieval is functional

**Gap:** No full-text search (acknowledged as deferred). The KB is static YAML — no continuous learning loop as the vision describes. The curator.py is a stub.

---

## 6. Provider & Checkpoint Systems

### Providers (Strongest Implementation Area)

- `MockVideoProvider` is genuinely well-built: generates real placeholder MP4/PNG/JSON files, implements full `BaseProviderAdapter` contract, supports 13 scenario scripts
- `MockImageProvider` generates placeholder PNGs
- `ProviderRegistry` + `ProviderHealthTracker` work correctly
- `SeedanceOpenRouterProvider` is a real adapter using stdlib `urllib`, testable via `_http_opener` injection — this is the best pattern in the codebase
- Credential redaction in error messages is proper
- `VeoFastProvider` is a stub (acknowledged)

### Checkpoints

- `GitBackend` wraps git commands for commit/tag/branch/restore — works correctly
- `CheckpointManager`, `ResumeManager`, `RollbackManager`, `InvalidationEngine`, `BranchManager` are all implemented and tested
- The invalidation engine's dependency graph is a good design
- Coverage is strong (92-97% across the module)

**Gap:** Checkpoints are not wired to MCP tools (all 8 checkpoint tools are stubs). The graph doesn't create checkpoints after approvals. The runtime doesn't persist state to the artifact store.

---

## 7. Post-Production

- 6 agents implemented: Assembly, Transition, AudioDesign, DeliveryPackaging, Subtitle
- 4 post-validators: assembly, transitions, delivery, subtitles
- All produce structured plans/manifests, not raw files
- Coverage is 90-100% across the module

**Gap:** No ffmpeg integration (acknowledged as deferred). Agents produce plans, not rendered output. This is acceptable for the current phase but means no real film can be assembled.

---

## 8. Code Quality

### Strengths

- **Type safety:** mypy strict passes across the entire codebase. Type hints are on every public function.
- **Consistency:** Every module follows the same patterns — `from __future__ import annotations`, Pydantic v2, dataclasses for internal values.
- **Error handling:** Specific exceptions with actionable messages. The Seedance adapter's OSError + HTTPError handling with redaction is exemplary.
- **Testability:** Constructor injection throughout (mock model, mock HTTP opener, mock human). Tests don't need monkey-patching.
- **No secrets:** Credentials are looked up via env vars, redacted in all error paths.

### Issues

1. **Dead code:** `state.py` (FilmStudioState dataclass) is unused at 0% coverage. Should be deleted or wired in.
2. **Dead code:** `security/__init__.py` at 0% — a re-export module that nobody imports.
3. **Recursion-as-control-flow:** The runtime catching `GraphRecursionError` as normal operation is a design smell. Use LangGraph interrupts.
4. **Inconsistent state mutation:** MCP tools mutate `rt.projects` dict directly, bypassing any state validation.
5. **`strict=False` in zip:** `test_graph_execution.py` line with `zip(nodes, PHASE_ORDER, strict=False)` — should be `strict=True` since the lengths are known to match.
6. **No integration between subsystems:** The graph doesn't call agents, agents don't call the KB, validation doesn't inspect artifacts, checkpoints aren't created by the graph. Each subsystem works in isolation but they're not composed.

---

## 9. Documentation

### What's Good

- 15 docs in `docs/` covering vision, architecture, KB model, agent architecture, implementation plan (17 phases), and several design deep-dives
- `PROGRESS.md` is detailed and honest about deferred items
- Architecture blueprint is comprehensive (2,421 lines)
- README is clear with phase table and quick start

### What's Missing

- No operations guide
- No runbook for first film
- No release process
- No demo guide
- No acceptance checklist
- No API reference for MCP tools
- The README claims "14+ wired" MCP tools but only 9 are wired (7 doing real work)

---

## 10. Summary Scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Code quality** | 9/10 | Excellent typing, patterns, testability |
| **Architecture alignment** | 8/10 | Structure matches blueprint; graph is a skeleton |
| **Test coverage (lines)** | 9/10 | 93.23%, well above 90% threshold |
| **Test coverage (behavior)** | 4/10 | Tests prove wiring, not studio behavior |
| **E2E acceptance** | 2/10 | 0 of 4 MUST-PASS scenarios implemented |
| **MCP wiring** | 3/10 | 9 of 57 tools wired, 7 doing real work |
| **Productization** | 2/10 | Most Phase 16 deliverables missing |
| **Agent execution** | 3/10 | Contracts exist, no real agent produces artifacts |
| **Validation execution** | 3/10 | Registry exists, no validator inspects artifacts |
| **Provider system** | 9/10 | Mock provider + Seedance adapter are excellent |
| **Checkpoint system** | 8/10 | Well-implemented but not wired to graph/MCP |
| **Post-production** | 7/10 | Good plan-level agents, no rendering |
| **Documentation** | 7/10 | Strong architecture docs, missing ops/runbook |

**Overall: 6/10** — A high-quality scaffold that needs another implementation pass to become functional.

---

## 11. Recommendations

### Immediate (to meet Phase 12 acceptance)

1. **Implement E2E Scenario 1 for real.** Submit idea → run graph → mock human approves through MCP → mock provider generates clips → validators score → assembly agent produces cut. This is the single most important gap.
2. **Wire graph nodes to subsystems.** Each phase node should: retrieve KB context, invoke the appropriate agent, create an artifact, run validation, create a review package, and interrupt for human approval.
3. **Use LangGraph interrupts** (`interrupt_before`) instead of recursion-limit catching for human gates.
4. **Wire checkpoint tools to MCP.** The checkpoint system is built and tested — connect it.
5. **Replace dict state with typed state.** Either use `FilmStudioState` or delete it. Don't leave dead typed state alongside dict state.

### Near-term (to meet Phase 16 acceptance)

6. **Create the missing productization files:** bootstrap.py, health.py, profiles/, scripts/, docs/operations-guide.md, docs/acceptance-checklist.md.
7. **Add `make run-mcp`, `make demo-project`, `make release-check` targets.**
8. **Fix the README** — it claims "14+ wired" MCP tools; the actual number is 9 (7 doing real work).
9. **Implement the remaining 3 MUST-PASS E2E scenarios** (quota, network error, continuity drift).

### Strategic

10. **Wire the 46 stub MCP tools** in priority order: generation → validation → checkpoint → KB → audit → provider → coverage.
11. **Implement per-agent RCTCO prompt templates** so agents produce real artifacts, not canned responses.
12. **Implement real validator logic** so validators inspect artifacts against rubrics, not return canned reports.
13. **Connect the continuous learning loop** — feed review findings, generation failures, and cost data back into the KB.
14. **Add ffmpeg integration** for post-production rendering (or clearly document that agents produce plans only).

---

## 12. Verdict

The project has **excellent bones**. The architecture is sound, the code is clean, the test infrastructure is strong, and the mock provider/checkpoint systems are genuinely production-quality. The team correctly built the contract layer before the execution layer.

However, the project is **not complete by its own acceptance criteria**. Phase 12 defined 4 MUST-PASS E2E scenarios — zero are implemented. Phase 16 defined specific productization deliverables — most are missing. The graph is a label-transition machine, not a film studio. The acceptance tests prove that infrastructure compiles, not that films get made.

The PROGRESS.md is honest about deferred items, which is good. But the phase status table marking all 17 phases as ✅ overstates completion. Phases 12 and 16 should be marked as **partially complete** or **in progress**.

**The next milestone should be: a single idea flowing through the full pipeline to a review cut, driven entirely through MCP tools, with mock provider and mock human, verifiable by a test that checks real artifacts at each phase.** Everything else follows from proving that spine works.
