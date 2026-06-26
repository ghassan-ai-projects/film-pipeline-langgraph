# Implementation Roadmap — Applying ODR Learnings to FPL

Phased plan to implement the improvements identified in the analysis.

## Phase 1: Foundation (Week 1) — Critical Fixes

**Goal**: Eliminate the 5 critical risks before they cause failures.

### Day 1-2: Structured Output Schemas
- [ ] Create `schemas/agent_outputs.py` with Pydantic models for all 14 agents
- [ ] Add `.execute()` validation to ConstitutionAgent, DevelopmentAgent, ScreenwriterAgent
- [ ] Add `.execute()` validation to VisualDevAgent, ShotBibleAgent, GenPlannerAgent
- [ ] Add `.execute()` validation to QCSynthesisAgent, AssemblyAgent, IntakeAgent, OrchestratorAgent
- [ ] Update prompt templates to include output schema information
- [ ] Add test: verify each agent's output validates against its schema

### Day 3: Token Limit Detection + Timeout Protection (Priorities 3 + 6b)
- [ ] Add `is_token_limit_exceeded()` to `providers/failure_classifier.py`
- [ ] Add `compress_prompt_for_retry()` to `providers/failure_classifier.py`
- [ ] Add `asyncio.wait_for(timeout=120)` to `PromptRunner.call_model()`
- [ ] Integrate token limit detection into retry loop
- [ ] Test: verify token limit detection works for DeepSeek, Gemini
- [ ] Test: verify timeout returns error dict, not crash
- [ ] NOTE: Also addresses 05-critical-issues.md Issue #4 (No Configurable Timeout)

### Day 4: Content Compression Chain
- [ ] Create `kb/compression.py` with `compress_artifact()` function
- [ ] Add `ArtifactSummary` Pydantic model
- [ ] Add config section for compression (max_chars, model, timeout)
- [ ] Integrate compression into `kb/curator.py` context building
- [ ] Test: large script (100+ scenes) compressed under 8K chars

### Day 5: Reflection Tool
- [ ] Create `agents/tools.py` with `film_review_tool`
- [ ] Wire into `OrchestratorAgent.prepare()` as required tool call
- [ ] Update `await_approval_node` to process tool-based decisions
- [ ] Test: orchestrator calls tool before making decision
- [ ] Test: tool output includes quality assessment + action + reasoning

---

## Phase 2: Quality & Resilience (Week 2) — Important Fixes

### Day 6-7: Fix Critical Issues (from 05-critical-issues.md)
- [ ] **Issue #1**: Move GraphServices from state to RunnableConfig (remove custom serializer)
- [ ] **Issue #2**: Fix state.pop() mutation in `_run_agent()`
- [ ] **Issue #3**: Resolve circular imports — extract agent class map to registry
- [ ] **Issue #4**: Timeout protection on model calls (already added Day 3, verify integration)
- [ ] **Issue #5**: Fix orchestrator convergence stall (stalled → escalate, not loop)
- [ ] **Issue #6**: Add Pydantic model for OrchestratorDecision with structured_output
- [ ] **Issue #7**: Add cross-phase reference validation (script↔shot_matrix)
- [ ] **Issue #10**: Split ScreenwriterAgent output into separate story_bible and script artifacts

### Day 8: Parallel Processing
- [ ] Refactor `kb/curator.py` to load artifacts in parallel via `asyncio.gather`
- [ ] Add parallel compression for large artifacts
- [ ] Benchmark: verify 3-4x speedup on KB context building
- [ ] Test: verify parallel loading handles partial failures gracefully

### Day 9: Runtime Config Overrides
- [ ] Create `config/runtime_overrides.py` with env var mapping
- [ ] Integrate into config merge pipeline
- [ ] Document all override vars
- [ ] Test: `FILM_PIPELINE_QUALITY=draft` skips festival-quality validation

### Day 10: Tool System + MCP + Cleanup
- [ ] Add ToolAggregator system (new `agents/tool_aggregator.py`)
- [ ] **Issue #8**: Extract mock responses to `testing/fixtures/`
- [ ] **Issue #9**: Add agent registration validation
- [ ] Add MCP tool error wrapping (Pattern 6 in 02-transferable-patterns.md)
- [ ] Create `langgraph.json` with graph export
- [ ] Add module-level `graph = build_graph()` export

---

## Phase 3: Evaluation Framework (Week 3) — Quality Measurement

### Day 11-12: Core Evaluation
- [ ] Create `evaluation/` package
- [ ] Create `FilmJudge` class with structured scoring
- [ ] Add evaluation axes for constitution, script, shot_matrix
- [ ] Add evaluation prompts for each axis
- [ ] Create evaluation config (model, timeout, axes)

### Day 13-14: Benchmark Dataset
- [ ] Curate test cases: 3-5 projects with known-good outputs
- [ ] Create benchmark runner
- [ ] Add pairwise comparison (A/B test pipeline changes)
- [ ] Add groundedness checker (verify generated content matches script)
- [ ] Add completeness checker (verify nothing missing from execution brief)

### Day 15: Integration + Documentation
- [ ] Wire evaluation into graph nodes (optional post-phase evaluation)
- [ ] Add evaluation results to orchestrator's review package
- [ ] Document evaluation framework
- [ ] Create evaluation runbook

---

## Phase 4: Enhancements (Week 4+) — Nice to Haves

### Optional Improvements
- [ ] Centralize all prompts into a single registry with date injection
- [ ] Add prompt versioning (hash-based, detect drift)
- [ ] Add structured output across all remaining agents
- [ ] Add comprehensive docstrings (Google-style, following ODR pattern)
- [ ] Add provider-native search tool abstraction (like ODR's SearchAPI)
- [ ] Add tool metadata for routing decisions
- [ ] Add comprehensive error propagation to MCP surface
- [ ] Add content deduplication for KB context building

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing tests during refactor | Run full test suite after each phase, fix before proceeding |
| Circular import issues from restructuring | Use registry pattern, validate with import test |
| Performance regression from compression | Benchmark before/after, keep configurable threshold |
| Reflection tool adds latency | Make optional via config, keep current flow as fallback |
| Evaluation model costs | Use cheap model (gemini-flash, deepseek) for eval, configurable |

## Testing Strategy

### Per-Phase Tests
- Phase 1: All model calls return schema-validated output; token limit + timeout work
- Phase 2: State serialization clean; no more state mutations; cross-phase validation catches errors
- Phase 3: Evaluation scores correlate with human judgment; benchmark catches regressions
- Phase 4: No regressions from enhancements

### Integration Tests
- Full pipeline run with mock providers: intake → delivery
- Pipeline recovery: inject error at each phase, verify graceful degradation
- Large film stress test: 100+ scenes, 500+ shots, verify no context overflow
- Checkpoint/restore: save mid-pipeline, restart, verify state integrity

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Schema validation coverage | 0% | 100% of agent outputs |
| Context overflow rate | Unknown (likely high on real data) | 0% with compression |
| Model call timeout protection | None | All calls |
| Quality measurement | None (rule-based only) | 6-axis automated eval |
| KB context build time | Sequential | 3-4x faster (parallel) |
| Pipeline latency (mock, 2 scenes) | Baseline | No regression |
| Graceful degradation paths | 0 | All phases |
