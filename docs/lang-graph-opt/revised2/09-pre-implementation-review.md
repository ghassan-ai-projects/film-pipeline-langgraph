# Revised2 — Pre-Implementation Review: Gaps, Risks, Go/No-Go

**Date:** 2026-06-22
**Purpose:** Adversarial review of the 8-phase plan before implementation. Surface what's missing,
what's risky, and what needs to be added before each phase can begin.

---

## Cross-Cutting Gaps (Affect Multiple Phases)

### Gap 1: No Feature Flag Strategy

**Severity:** High
**Affects:** All phases

Every phase changes runtime behavior. If Phase 1 breaks `submit_idea` in production, there's no way to revert without a git revert + redeploy. Each phase should be gated behind a feature flag:

```python
# In runtime or config:
FEATURE_FLAGS = {
    "use_langgraph_interrupts": False,   # Phase 1
    "use_typed_state": False,            # Phase 2
    "use_matrix_patches": False,         # Phase 4
    "use_scoped_context": False,         # Phase 6
    "use_structured_repair": False,      # Phase 5
}

# Phase 1 example:
if FEATURE_FLAGS.get("use_langgraph_interrupts"):
    return graph.invoke(state, config)  # new path
else:
    return _legacy_run_graph(state)      # old path
```

**Fix:** Add a `feature_flags` dict to `StudioRuntime` (or env vars). Each phase ships behind its flag. After validation, remove the flag and old code path.

### Gap 2: No Migration Path for In-Flight Projects

**Severity:** Medium
**Affects:** Phase 1, 2, 3, 4

If a project is mid-pipeline (e.g., at `script` phase with `human_approval_required=True`) when Phase 1 deploys, does it resume correctly? The state dict shape changes with Phase 2 (typed state). Old state dicts won't have new keys.

**Fix:** Add a `state_version: int` key to state. On load, if `state_version < CURRENT_VERSION`, run a migration function. Phase 2 sets `state_version = 2` after converting from dict to typed state.

### Gap 3: No Rollback Plan Per Phase

**Severity:** Medium
**Affects:** All phases

If Phase 4 (matrix patches) causes data corruption, how do we roll back? Patches are separate artifacts — rolling back means deleting patch artifacts and reverting to the base matrix. But there's no tool or runbook for this.

**Fix:** Each phase document includes a "Rollback" section: what artifacts to delete, what state to reset, what MCP tools to run.

### Gap 4: MCP Tool Compatibility Audit Not Done

**Severity:** Medium
**Affects:** Phase 1, 2, 4

Phase 1 changes how `approve_phase` and `request_revision` work. Phase 2 changes state shape. Phase 4 adds new artifact types (patches). All MCP tools that read/write state or artifacts need auditing:

| MCP Tool | Phase 1 Impact | Phase 2 Impact | Phase 4 Impact |
|----------|---------------|---------------|---------------|
| `submit_idea` | Returns after interrupt — compatible | State shape changes | None |
| `approve_phase` | Changed to graph resume | State shape changes | None |
| `request_revision` | Changed to graph resume | State shape changes | None |
| `list_artifacts` | None | None | New patch artifacts appear |
| `inspect_artifact` | None | None | Must handle patch artifacts |
| `get_orchestrator_summary` | None | Key names change | New fields in summary |
| `rollback_artifact` | None | None | Must handle patch invalidation |
| `rollback_to_checkpoint` | State restore changes | State shape changes | Patch refs in state |

**Fix:** Before each phase ships, run the full MCP tool test suite (`tests/integration/test_mcp_flow.py`) and verify all tools still return valid responses.

### Gap 5: Documentation Updates Not Planned

**Severity:** Low
**Affects:** Phase 1, 4

The operator guide (`docs/openclaw-mcp-operator-guide.md`) describes the current approval flow. Phase 1 changes it. Phase 4 adds matrix patch artifacts that operators can inspect. AGENTS.md needs updating when state schema changes.

**Fix:** Add a "Documentation" checklist item to each phase: which docs need updating.

---

## Per-Phase Gaps

### Phase 0 — Quick Wins

**Verified correct:**
- `run_from_template()` accepts `model_profile=` keyword argument ✅ (runner.py:167)
- langgraph `>=0.2,<0.3` supports profiles ✅ (pyproject.toml)

**Risks:**
- Mock mode uses `mock_responses` dict keyed on task string. If the task string changes (e.g., from quality instructions adding text), mock dispatch breaks.
- `PromptTemplate` is defined in `defaults.py` as a function return, not imported from a schema module. Adding `quality_instructions` field might require schema changes elsewhere.

**Missing:**
- Need to verify `PromptTemplate` class location. It may be a `prompt_templates/registry.py` import, not part of `defaults.py`. If it's a Pydantic model, adding a field is easy. If it's a dataclass or plain class, need to check.
- No test verifying mock mode still works after adding quality instructions to templates.

**Go:** ✅ Ready. But verify `PromptTemplate` class location first.

---

### Phase 1 — Real Human Gates

**Verified correct:**
- LangGraph `>=0.2` supports `interrupt()` and `Command(resume=...)` ✅
- `submit_idea` MCP tool returns `human_approval_required` field — compatible with interrupt payload ✅
- `MemorySaver` available in langgraph ✅

**Critical risks:**

1. **Idempotency of pre-interrupt code.** `interrupt()` re-executes ALL code before it on resume. In `await_approval_node`, the payload construction reads state only — safe. But if we add a `build_review_package` call before `interrupt()`, that must be idempotent by key. **Mitigation:** Document the idempotency rule. Add `review_package_id` check in `ReviewPackageGenerator`.

2. **`run_graph()` returns after first interrupt.** Before Phase 1, `run_graph()` ran until recursion limit. After Phase 1, it returns at the first `interrupt()`. Callers that expected to get the final state will get a mid-pipeline state. **Mitigation:** `submit_idea` already checks `human_approval_required`. Other callers (tests, MCP tools) need review.

3. **`approve_phase` currently calls `runtime.approve_phase()` which manually calls `approve_phase_node()` + `_advance_to_next_phase()`. After Phase 1, it calls `graph.invoke(Command(resume="approve"))`. The graph resume runs `await_approval_node` from the top, then `approve_phase_node`, then the graph router advances to the next phase. **Verify:** The graph's `after_approval` edge must route to the correct next phase node. This already works today (it's what `after_approval()` does). The difference is that the graph advances automatically instead of the runtime manually calling `_run_phase_node()`.

4. **Thread ID must be stable.** `configurable.thread_id = project_id`. If the same project_id is used across restarts, `MemorySaver` won't persist. **Mitigation:** Phase 1 ships with `MemorySaver` (acceptable — projects are short-lived in mock mode). Phase 7 (or an intermediate phase) adds `SqliteSaver`.

**Missing:**
- No explicit removal plan for `GraphRecursionError` catch. It's in `run_graph()`. After Phase 1, `recursion_limit=50` can be removed entirely.
- `_advance_to_next_phase()` and `_run_phase_node()` in runtime.py — should be deprecated but kept for fallback behind feature flag.
- No test for: what happens if `approve_phase` is called when there's no pending interrupt? (Should raise a clear error.)

**Go:** ⚠️ Ready with mitigations. The biggest risk is idempotency. Add a pre-flight check: audit all code that runs before `interrupt()` for side effects.

---

### Phase 2 — Typed State

**Verified correct:**
- `TypedDict` with `Annotated[list, add]` reducers is the standard LangGraph pattern ✅
- `total=False` allows partial updates ✅

**Critical risks:**

1. **`add` reducer duplicates on interrupt replay.** If a node returns `{"artifact_refs": [ref]}`, and the node re-runs after an interrupt resume, `ref` is appended again. The list grows: `[ref, ref, ref]`. **Mitigation:** Use deterministic refs (they are — `artifact:shot_matrix:v1` is identical across replays). Add a dedup check in the `add` reducer: only append if not already present.

2. **`total=False` doesn't enforce types.** Any node can set `current_phase: int` and LangGraph won't reject it. The TypedDict is documentation, not enforcement. **Mitigation:** Add runtime validation in a `pre_node` middleware or accept that type safety is gradual. This is still an improvement over `dict`.

3. **Orchestrator state keys are untyped.** `_orchestrator__candidate_refs` and friends live outside the TypedDict. Continue to work via `total=False` but aren't typed. **Mitigation:** Accept for Phase 2. Type them in Phase 4 (when orchestrator state is folded into typed channels).

4. **Footgun: returning accumulated lists.** If a node does `return {"artifact_refs": state["artifact_refs"]}` instead of `return {"artifact_refs": [new_ref]}`, the `add` reducer double-appends the entire list. **Mitigation:** Add a linter rule or test helper that asserts nodes return new items for append channels.

**Missing:**
- No `state_version` migration path (Gap 2).
- Services removal from state is deferred — `_services` still injected at runtime. Plan says "Phase 2 doesn't change injection mechanism." This means `_services` remains in the dict but outside the TypedDict. Acceptable but messy.

**Go:** ⚠️ Ready. Add dedup to `add` reducer before shipping. Add a migration path for in-flight projects.

---

### Phase 3 — Artifact Versioning

**Verified correct:**
- `next_version()` pattern is standard ✅
- `built_from` field on `ArtifactMetadata` is a non-breaking addition ✅

**Risks:**
1. `next_version()` scans filesystem. If the filesystem has stale `.v1.json` files from previous runs, it returns the wrong version. **Mitigation:** Use in-memory counter per `(project_id, artifact_id)` as primary, filesystem as fallback on cold start.

2. All existing tests assume `v1` in artifact ref strings. **Mitigation:** Audit tests — update where necessary. Accept that some tests will break and need fixing.

**Missing:**
- `load_metadata()` function on ArtifactStore. `check_staleness()` needs to load just metadata, not the full artifact body. The store currently has `load()` (full body) and `list_artifacts()` (metadata list). Need a `load_metadata(project_id, artifact_id)` that reads just the sidecar `.meta.json`.
- `consistency_check_node` is non-blocking. The plan says "informational only." Should it ever block? Decision needed.

**Go:** ✅ Ready. Add `load_metadata()` to ArtifactStore before implementing.

---

### Phase 4 — Matrix Patches

**Critical risks:**

1. **Patch loading tries multiple phases.** `load_patch()` iterates `[GEN_PLANNING, GENERATION, QC, POST]` to find a patch. This is brittle — if a patch is saved in a new phase, it won't be found. **Mitigation:** Store patches in a dedicated `matrix_patches/` directory or record the phase in the patch ref string (`artifact:matrix_patch_gen_planning:v1` includes the phase).

2. **`materialize_matrix()` does N file I/O operations.** For a 100-shot film with 4 phases of patches, that's 4 loads. Acceptable. But if patches accumulate over many repair rounds (e.g., 10 repair patches for shot_bible), it adds up. **Mitigation:** Cache the materialized matrix in state. Invalidate cache when new patches are added.

3. **Row not found in base matrix.** `apply_to()` silently skips unknown `shot_id`s. If a patch targets `shot_0099` but the base matrix only has 20 rows, the patch is silently dropped. **Mitigation:** Log a warning. Add a `skipped_rows` field to `MatrixPatch` to track this.

4. **`gen_planning_node` currently saves `cost_estimate` only.** Adding patch emission means the node now produces TWO artifacts (`cost_estimate` + `matrix_patch`). Existing tests that assert "gen_planning produces one artifact" will fail.

**Missing:**
- No `MatrixPatch` invalidation in `InvalidationEngine`. If a patch is rolled back, the dependency graph should know what downstream patches to invalidate.
- No test for: what happens if two patches update the same row? (Should be: later patch wins, same as now with sequential phases.)
- No `materialize_matrix()` cache. Every call loads from filesystem.

**Go:** ⚠️ Ready with mitigations. Fix patch loading (store in dedicated directory or include phase in ref). Add warning on unknown shot_ids.

---

### Phase 5 — Structured Repair

**Risks:**
1. **Validators don't know about shot_ids.** Most validators today validate whole artifacts (script, matrix as JSON blobs). Adding `shot_id` to findings requires each validator to parse rows and identify which row failed. This is a significant refactor of all 6 validators. **Mitigation:** Start with validators that already have row-level awareness (Gate A/B/C in `orchestrator_validators.py`). Then extend to LLM validators.

2. **`to_agent_context()` can produce very long text.** If 50 rows fail, the repair context could be 5K+ tokens — consuming the token budget saved by Phase 6 (scoped context). **Mitigation:** Cap failed rows at 20 in the context string. Show summary: "47 rows failed. Here are the first 20: ..."

**Missing:**
- No plan for how validators populate `shot_id`. This is the hardest part of Phase 5.
- `RepairFeedback` is saved as an artifact but there's no MCP tool to inspect it.

**Go:** ⚠️ Ready but highest implementation complexity. The validator refactoring is the long pole. Consider splitting into 5a (schema + repair node changes) and 5b (validator shot_id population).

---

### Phase 6 — Scoped Context

**Risks:**
1. **Builders do file I/O per agent call.** `build_gen_planning_context()` calls `materialize_matrix()` which does file I/O. For 10 agents, that's 10 matrix loads. **Mitigation:** Cache materialized matrix in state (Phase 4 fix). Builders read from state, not filesystem.

2. **Template migration is a versioning problem.** Changing `{script_content}` to `{scoped_context}` requires new template versions. Old templates still reference `{script_content}` which will be empty after migration. **Mitigation:** Keep `{X_content}` vars populated as fallback during migration. Add new template versions with `{scoped_context}`.

**Missing:**
- No cache strategy for context builders.
- No plan for which templates to migrate first (suggest: shot_bible → gen_planning → script → visual_dev → development → constitution).

**Go:** ✅ Ready with cache fix. Start with shot_bible template (biggest savings).

---

### Phase 7 — Subgraphs & Parallelism

**Risks:**
1. **`Send` duplicates state N times.** For 6 validators, 6 copies of `StudioGraphState`. Each copy includes `artifact_refs`, `issues`, etc. Memory impact is low for mock mode (state is small) but could grow. **Mitigation:** Acceptable. State is typically <10KB. 6 copies = 60KB.

2. **Worker nodes return temporary keys.** `_qc_reports`, `_qc_raw_reports` are internal keys that shouldn't appear in the TypedDict. **Mitigation:** Prefix with `_` (convention for transient). Document that `_`-prefixed keys are not part of the typed state contract.

3. **`qc_node` responsibilities must move into subgraph.** The current `qc_node` does: run validators, build consensus, save report, emit matrix patch. The subgraph replaces the validator part — but consensus building and patch emission must be in the subgraph's `reduce_reports` node.

**Missing:**
- No plan for generation subgraph (correctly deferred).
- Review gate subgraph duplicates `await_approval_node` from Phase 1. Should the review gate subgraph REPLACE `await_approval_node`? Or sit alongside it? **Decision needed.**

**Go:** ⚠️ Ready. Clarify: review gate subgraph replaces `await_approval_node` (not adds another gate). QC subgraph's `reduce_reports` must handle consensus + patch emission.

---

### Phase 8 — Agent Output Quality

**Critical risk:**

1. **`resolve_model_params` return type changes from 3-tuple to 5-tuple.** ALL callers break. Currently:
   ```python
   model_id, max_tokens, temperature = self.model_router.resolve_model_params(model_profile)
   ```
   After Phase 8:
   ```python
   model_id, max_tokens, temperature, top_p, frequency_penalty = ...
   ```
   **Every caller of `resolve_model_params` must be updated.** Grep: `runner.py:124`, `validation/base.py:138,146`. **Mitigation:** Add `resolve_model_params()` overload or use a dataclass return type. Simpler: add default `_` unpacking for callers that don't need new params. Or: add new method `resolve_model_params_extended()` and keep old signature.

2. **`frequency_penalty` not supported by all providers.** Gemini API uses `frequencyPenalty` (camelCase). OpenRouter uses `frequency_penalty` (snake_case). Need to verify the API format. **Mitigation:** Map to correct format in provider-specific adapters. For Phase 8, OpenRouter is the primary path — verify it supports `frequency_penalty`.

**Missing:**
- No verification that `frequency_penalty` is supported by `deepseek/deepseek-chat` and `google/gemini-3-flash-preview` via OpenRouter.

**Go:** ⚠️ Ready with signature fix. Use a dataclass return type for `resolve_model_params` to avoid breaking callers.

---

## Go/No-Go Summary

| Phase | Go? | Conditions |
|-------|-----|-----------|
| **0 — Quick Wins** | ✅ GO | Verify `PromptTemplate` class location first |
| **1 — Real Gates** | ⚠️ GO | 1. Audit pre-interrupt code for side effects. 2. Add feature flag. 3. Test idempotency. |
| **2 — Typed State** | ⚠️ GO | 1. Add dedup to `add` reducer. 2. Add `state_version` migration. 3. Document footgun (don't return accumulated lists). |
| **3 — Versioning** | ✅ GO | Add `load_metadata()` to ArtifactStore first |
| **4 — Matrix Patches** | ⚠️ GO | 1. Fix patch loading (dedicated dir or phase in ref). 2. Warn on unknown shot_ids. 3. Cache materialized matrix in state. |
| **5 — Structured Repair** | ⚠️ GO | 1. Split into 5a (schema) + 5b (validator refactoring). 2. Cap failed rows in context at 20. |
| **6 — Scoped Context** | ✅ GO | Add cache for context builders. Start with shot_bible template. |
| **7 — Subgraphs** | ⚠️ GO | 1. Clarify review gate subgraph vs await_approval_node. 2. QC subgraph must handle consensus + patch emission. |
| **8 — Agent Quality** | ⚠️ GO | 1. Fix `resolve_model_params` return type (use dataclass). 2. Verify `frequency_penalty` API compatibility. |

## Recommended Execution Order

```
Session 1: Phase 0 (30 min) → Phase 1 (2-3h)
Session 2: Phase 2 (3-4h) → Phase 3 (2-3h)
Session 3: Phase 4 (4-5h)
Session 4: Phase 5a + 5b (3-4h)
Session 5: Phase 6 (3-4h)
Session 6: Phase 7 QC subgraph (3-4h)
Session 7: Phase 8 (1-2h)
```

## Prerequisites Before ANY Phase Begins

1. [ ] Add `feature_flags` dict to `StudioRuntime` (10 min)
2. [ ] Add `state_version` key to state schema (5 min)
3. [ ] Audit MCP tools: run full `test_mcp_flow.py` to establish baseline (5 min)
4. [ ] Verify `PromptTemplate` class location for Phase 0 field addition (2 min)
5. [ ] Verify OpenRouter support for `frequency_penalty` and `top_p` (2 min)
