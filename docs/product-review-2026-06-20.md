# Product Review — 2026-06-20

**Reviewer:** Qwen Code orchestrator
**Scope:** Full codebase, tests, docs, CI state, architecture alignment, product completeness
**Reference:** [Prior review (2026-06-19)](./comprehensive-review-2026-06-19.md)

---

## Executive Summary

The project has advanced **substantially** since the June 19 review. The spine graph nodes
(intake → constitution → development → script) now execute real agents, persist real
Pydantic artifacts, and route through dedicated prompt templates. Validators inspect
artifacts and produce blocking/warning findings that gate phase advancement. The MCP
surface is materially more real. CI is fully green across all gates.

The project is now a **functional pre-production scaffold with a real execution spine**.
It is not yet a complete film studio — generation, full MCP coverage, and true end-to-end
product flow remain unfinished. But the architecture is proving itself, and the gap
between "scaffold" and "product" has narrowed considerably.

| Dimension | June 19 | June 20 |
|-----------|---------|---------|
| Graph nodes real vs stub | 0/11 real | 7/11 real (intake, constitution, development, script, visual_dev, shot_bible, gen_planning, qc, post) |
| Agents producing artifacts | 0 real | 8 real (spine + visual + QC + post) |
| Validators changing runtime | 0 | 7 real (script structure, dialogue/voice, reference usability, prompt readiness, scene continuity, assembly, delivery completeness) |
| MCP critical tools wired | ~40% | ~90% of critical path |
| CI state | Green (93%) | Green (94%) |
| Product gate | Failing | Passing |

---

## 1. CI & Quality Gates — ✅ PASS

```
✅ ruff check .           — All checks passed
✅ ruff format --check .  — 232 files already formatted
✅ mypy src tests         — Success: no issues found in 232 source files
✅ pytest                 — All tests pass, 94.06% coverage (threshold: 90%)
✅ make product-gate      — Product gate: PASS
✅ make build             — Builds cleanly
✅ app.smoke              — 5/5 checks pass
```

All quality gates are green. This is a material improvement from June 19.

---

## 2. Architecture Alignment

### What Matches the Blueprint

| Blueprint element | Status | Evidence |
|-------------------|--------|----------|
| MCP-first operator surface | ✅ Strong | 57 tools, ~90% of critical path wired |
| LangGraph state machine | ✅ Strong | 11 phase nodes + approval gates + conditional routing |
| Pydantic v2 schemas | ✅ Strong | 27 schemas, all at 100% coverage |
| Phase-by-phase artifact production | ✅ Partial | Spine phases produce real artifacts; generation phase still flag-only |
| Human review gates | ✅ Strong | Approval → revision → repair cycle, git-backed checkpoints |
| Agent registry (capability-based) | ✅ Strong | 19 agents, dynamic routing by capability |
| Validator registry | ✅ Strong | 15 validators, blocking/warning classification |
| KB context builder | ✅ Strong | 12 items, layered retrieval, conflict resolution |
| Checkpoint & rollback | ✅ Strong | Git backend, invalidation engine, branch support |
| Mock provider | ✅ Strong | Full adapter contract, 13 scenario scripts |
| Real provider adapter | ✅ Present | Seedance OpenRouter (integration-tested), Veo (stub) |
| Profile system | ✅ Strong | YAML loader, merger, resolver, validator |

### What Diverges

- **Generation phase is flag-only.** This is the most significant gap — the `generation_node`
  only sets phase labels and flags but does not invoke providers.
- **Prompt framework partial adoption.** Critical-path agents use dedicated templates;
  non-critical agents fall through to generic RCTCO assembly. This is by design per the
  conditional-template-enforcement pattern, but the "non-critical" path is still a
  significant number of agents.
- **FilmStudioState dataclass is dead code (0% coverage).** Replaced by `dict` state for
  LangGraph compatibility. Should be removed or repurposed.

---

## 3. What Changed Since June 19

### Spine phases are now real

The four spine graph nodes (`intake_node`, `constitution_node`, `development_node`,
`script_node`) plus `visual_dev_node`, `shot_bible_node`, `gen_planning_node`, `qc_node`,
and `post_node` all invoke real agents through the prompt runner, persist artifacts
through `ArtifactStore`, and record handoff decisions. This is the most impactful change.

```
intake_node        → IntakeAgent        → project_profile artifact
constitution_node  → ConstitutionAgent  → film_constitution artifact
development_node   → DevelopmentAgent   → treatment + scene_list artifacts
script_node        → ScreenwriterAgent  → story_bible + script artifacts
visual_dev_node    → VisualDevAgent     → reference_index artifact
shot_bible_node    → ShotBibleAgent     → shot_matrix artifact
gen_planning_node  → GenPlannerAgent    → cost_estimate artifact
qc_node            → QCSynthesisAgent   → consensus_report + validator dispatch
post_node          → (via AssemblyAgent) → assembly_manifest artifact
```

### Validators change runtime behavior

The QC node's `_run_validators()` dispatches real validators against loaded artifacts.
Blocking findings are added to `state["issues"]`, which prevents phase advancement via
`compute_actions()`. Validators for: script structure, dialogue voice, reference usability,
prompt readiness, scene continuity, assembly, and delivery completeness.

### MCP surface is substantially real

`get_validation_report` now either reads stored QC-node reports or falls back to live
validator dispatch. `get_project_summary` iterates all phases to build a real artifact
inventory. `submit_idea` runs the graph through `intake_node`. `approve_phase` now
creates git-backed checkpoints.

### Dynamic agent routing

`route_agent()` in `graph/router.py` selects agents by capability, phase, and task type
(create/review/repair). Fallback logic exists. Handoff records persist routing decisions
with deduplication on replay.

### Prompt template enforcement

Nine critical-path agents now receive dedicated prompt templates via
`prompt_templates/registry`. Non-critical agents fall through to generic RCTCO assembly.
Template versions and model profiles are tracked in handoff records.

---

## 4. Remaining Gaps

### 4.1 Generation phase (critical)

`generation_node` is still a 7-line flag-only stub:
```python
def generation_node(state):
    new_state["current_phase"] = "generation"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    return new_state
```

This is the biggest remaining gap. The generation ledger manager, provider adapters, and
MCP generation tools all exist — they just aren't connected to the graph node yet.

### 4.2 E2E scenarios lack behavioral depth

All 10 E2E scenario files exist and pass, but they primarily test that infrastructure
compiles and basic state transitions occur. They do not yet prove full MCP-driven
product flows. The scenario result standard in `docs/product-completion/06-e2e-acceptance-and-release.md`
requires: actions through MCP, artifacts created and persisted, approvals stored,
validation reports stored, checkpoint behavior visible, audit records explaining outcomes.
Most scenarios don't yet meet this standard.

### 4.3 MCP stubs remain

~12 non-critical MCP tools still return stubs:
- `find_project`, `get_project_summary` (partially real), `get_intake_analysis` (partial),
  `approve_intake`, `start_generation_batch`, `promote_test_to_production`,
  `rollback_artifact`, `plan_coverage_group`, `list_coverage_groups`,
  `inspect_coverage_group`, `approve_coverage_generation`, `assemble_final_cut`

One critical-path tool (`start_generation_batch`) is in the allowed_stub list — this is
acceptable per the acceptance manifest since expensive video generation execution may be
mocked, but the surrounding behavior should be real.

### 4.4 No full idea → validated-clips flow

No test demonstrates a complete end-to-end: create project → submit idea → approve intake →
produce constitution → approve → produce development → approve → produce script → approve →
produce visual development → shot bible → gen planning → generate clips → QC validate →
deliver. The spine exists but the full chain hasn't been proven in a single test.

### 4.5 Delivery node is stub

`delivery_node` only sets flags. The downstream editorial and delivery pipeline is
intentionally out of current completion scope per the README, but the delivery node
still needs to produce a delivery_package artifact for the system to be internally consistent.

### 4.6 FilmStudioState dataclass dead code

`src/film_pipeline/graph/state.py` is at 0% coverage — it was replaced by a `dict` state
for LangGraph compatibility. Either remove it or repurpose it as a typed view over the dict.

---

## 5. Per-Phase Assessment

| Phase | Graph Node | Agent | Artifacts | Validators | Verdict |
|-------|-----------|-------|-----------|------------|---------|
| intake | ✅ Real | ✅ IntakeAgent | ✅ project_profile | — | Done |
| constitution | ✅ Real | ✅ ConstitutionAgent | ✅ film_constitution | — | Done |
| development | ✅ Real | ✅ DevelopmentAgent | ✅ treatment, scene_list | — | Done |
| script | ✅ Real | ✅ ScreenwriterAgent | ✅ story_bible, script | ✅ ScriptStructure, DialogueVoice | Done |
| visual_dev | ✅ Real | ✅ VisualDevAgent | ✅ reference_index | ✅ ReferenceUsability | Done |
| shot_bible | ✅ Real | ✅ ShotBibleAgent | ✅ shot_matrix | ✅ SceneContinuity | Done |
| gen_planning | ✅ Real | ✅ GenPlannerAgent | ✅ cost_estimate | ✅ PromptReadiness | Done |
| generation | ⚠️ Flag-only | — | — | — | **Not started** |
| qc | ✅ Real | ✅ QCSynthesisAgent | ✅ consensus_report | ✅ All validators dispatched | Done |
| post | ✅ Real | ✅ (via AssemblyAgent) | ✅ assembly_manifest | ✅ Assembly | Done |
| delivery | ⚠️ Flag-only | — | — | ✅ DeliveryCompleteness | **Minimal** |

---

## 6. Test Quality Assessment

### Strengths

- 94.06% coverage, genuinely broad across all modules
- Test structure mirrors source structure
- Unit tests are well-organized and focused
- Integration tests exist for MCP flow, artifact spine, dynamic routing, validation runtime
- E2E scaffold exists for all 10 required scenarios
- Smoke tests validate operator workflow ("manual 4-min mock short")

### Weaknesses

- High coverage masks behavioral gaps in generation and delivery paths
- `mcp/tools/__init__.py` is at ~67% — stub handlers execute but don't test real behavior
- `veo_fast.py` at 42% — stub adapter with minimal meaningful coverage
- E2E tests don't yet prove the scenario result standard (artifacts, approvals, validation reports, audit records)
- No test proves an agent → model → artifact round-trip with a real LLM (all mock model adapter)

---

## 7. Documentation Assessment

| Doc | Status | Notes |
|-----|--------|-------|
| README.md | ✅ | Accurate, complete MCP tool listing |
| AGENTS.md | ✅ | Clear conventions, boundaries, forbidden changes |
| architecture-blueprint.md | ✅ | Comprehensive, 2400+ lines |
| agent-architecture.md | ✅ | Detailed roster, handoff patterns |
| kb-operating-model.md | ✅ | Retrieval, authority, context packets |
| e2e-test-scenarios.md | ✅ | 10 scenarios defined with mock human profiles |
| acceptance-checklist.md | ✅ | Honest self-assessment with verified evidence |
| product-completion/ (7 docs) | ✅ | Hard standards, concrete criteria |
| product-completion-plan/ | ✅ | Execution plan with program rules |
| operations-guide.md | ✅ | Setup, recovery, troubleshooting |
| runbook-first-film.md | ✅ | Step-by-step walkthrough |
| release-process.md | ✅ | Publish checklist |
| demo-guide.md | ✅ | Mock-mode quick start |
| implementation-plan/ (19 docs) | ✅ | Per-phase deliverables with PROGRESS.md |

Documentation is comprehensive and honest. The acceptance checklist correctly notes that
coverage was 86.82% at time of writing (now 94.06%), and the product-completion docs set
the right bar.

---

## 8. Security & Hygiene

| Concern | Status |
|---------|--------|
| `.env` git-ignored | ✅ |
| Credential redaction in logs | ✅ |
| No secrets in source or tests | ✅ |
| `.env.example` provides template | ✅ |
| No network calls in unit tests | ✅ |
| Mock provider isolates paid APIs | ✅ |

No security concerns found.

---

## 9. Recommendations

### Immediate (next 1-2 phases)

1. **Wire the generation node.** Connect `GenerationLedgerManager`, provider adapters, and MCP
   generation tools to the graph. The infrastructure exists — it needs orchestration.

2. **Complete the delivery node.** Produce a `delivery_package` artifact from the assembly
   manifest, even if it's a plan-level artifact (not actual rendered files).

3. **Deepen E2E scenarios.** Upgrade at least scenarios 1 (happy path) and 2 (script revision)
   to assert: artifacts created, approvals stored, validation reports stored, checkpoint
   behavior visible, audit records explain outcomes. Use the mock human through MCP tools.

4. **Remove dead code.** Delete or repurpose `state.py` (the unused `FilmStudioState` dataclass
   at 0% coverage).

### Medium-term

5. **Complete remaining MCP stubs.** The 12 non-critical stubs should be wired or explicitly
   deferred with tracking issues.

6. **Prove full idea → validated-clips flow.** Write an integration or E2E test that drives the
   complete spine through MCP with mock human, mock model, and mock provider. This is the
   single test that proves the product works.

7. **Veo adapter.** Complete the VeoFast stub with real HTTP calls (requires `GOOGLE_API_KEY`).

### Low-priority

8. **Per-agent RCTCO templates for all 19 agents.** Currently only critical-path agents get
   dedicated templates. The generic fallback works but isn't ideal.

9. **KB full-text search (`index.py`).** Tag-based retrieval is sufficient today.

---

## 10. Overall Verdict

**Current state:** Pre-production scaffold with a real execution spine (7/11 graph nodes
real). Architecture is proving itself. CI is fully green. MCP is substantially real. The
project is no longer a "promising scaffold" — it's a scaffold with working pre-production.

**Not yet:** A complete film studio. The generation phase, full MCP coverage, and true
end-to-end product proof remain unfinished.

**Score:** 7.5/10 (up from 6.6/10 on June 19)

**Next milestone:** When the generation node is wired and one full E2E scenario proves
`idea → validated clips` through MCP, this product crosses into "working studio" territory.
