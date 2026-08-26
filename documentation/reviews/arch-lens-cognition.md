# LENS-COGNITION — How fast can a competent engineer reason about and safely change this codebase?

Repo: film-pipeline-langgraph @ `arch-improvement-review`, HEAD `e811d1d`. 307 py files / 41.5k LOC.
Method: simulated newcomer discovery paths with real greps/reads; read hotspot structures end-to-end;
sampled tests, reports (.fleet/reports/D-00x.md), and documentation against source.

**Overall verdict:** the codebase is *locally* very readable — module docstrings are honest, functions
are small, naming inside modules is consistent. The cost is *global*: one concept routinely wears
2–4 names across layers (`server_mode`/`runtime_mode`/`workflow_mode`; "rollback record" in two
stores), the graph state is a stringly-keyed dict whose real schema lives in comments, the test
suite pins a lazy-binding implementation detail 68 times, and the architecture blueprint describes
a system that is missing its two biggest layers (`app/`, `tui/`). A newcomer can make a contained
change in under an hour; they can make an *unsafe* change in under an hour too, because the
couplings that bite (ref-string format, density numbers, get_runtime binding) are invisible at
the edit site.

---

## Mission 1 — Newcomer walkthrough experiments

### Finding 1.1 — Task "change how shot density defaults are computed": fast to find, easy to break silently

**Walk actually taken (stranger simulation):**
1. `grep -ri "density"` → 2 src hits: `graph/scope_contract.py` (docstring: "Single source of truth
   for the scene/shot density model") and `validation/impl/script_structure.py` (`_flag_density_warnings`
   — an unrelated dialogue-density concept). **Hops: 1 grep + 1 false lead.**
2. Read `src/film_pipeline/graph/scope_contract.py` (134 lines) → `_DENSITY` table (L26-30),
   `_PACING_ALIASES` (L33-46), `_FILM_TYPE_DEFAULT_PACING` (L49-55). Change site found. **Hops: 1 read.**
3. To know what breaks: grep importers of `scope_contract` → `graph/nodes/prep.py:157-177`
   (`_attach_scope_contract`), `graph/orchestrator_validators/brief.py:78-95`
   (`avg_shot_duration_for` recomputes runtime consistency with 20% tolerance). **Hops: 1 grep + 2 reads.**
4. Tests that pin exact numbers: `tests/unit/graph/test_scope_contract.py:36-38` (9.0/6.5/4.0),
   `:51` (`target_shot_count == 46`), `tests/unit/test_orchestrator_validators.py:341` ("33 shots at
   slow_cinema (avg 9.0s)"), `tests/unit/constraints/test_extractor.py:42` (`target_shot_count == 24`).

**Friction points (concrete):**
- **F1 — concept wears three names.** The task says "shot density"; the file is `scope_contract`;
  the schema is `schemas/scope_contract.py::StoryScopeContract`; the knobs are called "pacing".
  Grepping "shot count", "pacing", or "runtime" never lands on the density table. Only "density" does.
- **F2 — hidden validator coupling.** Changing `_DENSITY` changes what `brief_runtime_inconsistent`
  accepts (`orchestrator_validators/brief.py:78-95`): existing briefs validated under old density
  fail under new ones at ±20% tolerance. Nothing at the edit site hints at this; it only surfaces as
  e2e/integration failures or, worse, silently different gate outcomes on stored projects.
- **F3 — name collision on "density".** `validation/impl/script_structure.py:94` `_flag_density_warnings`
  is about dialogue/action-line density (>15 lines / >10 lines), not shot density. A newcomer must
  read both files to rule one out.
- **F4 — blueprint gives no path.** `documentation/architecture-blueprint.md:1069` mentions "shot
  density" once, as a film_type "control" — no pointer to where it's computed.

**SEVERITY:** Medium. **COGNITIVE COST:** ~15 min to find, ~1–2 h to be *confident* about blast radius.
The single-source-of-truth refactor already done here is good; what's missing is inbound-edge discoverability.
**TARGET DESIGN:** keep `scope_contract.py`; add a one-line pointer in architecture-blueprint.md's
film_type section ("computed in `graph/scope_contract.py`"), and rename the validator helper
`_flag_density_warnings` → `_flag_scene_size_warnings` to kill the collision.
**MIGRATION:** doc line + one function rename (private, 2 call sites at script_structure.py:94,206).
**EFFORT:** S. **RISK:** Low.

### Finding 1.2 — Task "add an MCP tool for listing rollback records": the surface area is undocumented, and 'the data' has two conflicting homes

**Walk actually taken:**
1. `ls mcp/tools/` → 20 modules + registry. `checkpoints.py` looks like the home (docstring:
   "Checkpoint / version / rollback tools"). **Hop 1.**
2. Read `mcp/tools/checkpoints.py` (332 lines). Existing tools follow a clear pattern:
   `rt = tools_pkg.get_runtime()` → args parsing → `_ok(...)`/`_error(...)`.
   **Discovery trap #1:** "rollback records" turn out to be *written* by `_save_rollback_artifacts`
   (L47-78) as artifacts of type `ArtifactType.ROLLBACK_RECORD`, but *also* constructed independently
   inside `checkpoints/rollback.py:76-93` (`_record_rollback`, id format `rollback:{checkpoint_id}:...`,
    appended to an in-memory `self.records`) vs the tool-side id format `rollback:{project_id}:...`.
   Two producers, two id schemes, two stores (artifact store vs RollbackManager memory/audit).
   A newcomer cannot tell which store `list_rollback_records` should read without archaeology.
3. Registration mechanics: read `registry.py` → `_tool_contract` (L101-117), `_register` (L120-134),
   `register_all_tools` (L137+). Touchpoint list for one existing analog (`list_checkpoints`):
   `mcp/tools/checkpoints.py`, `registry.py` import block + `_register` call,
   `tests/unit/mcp/tools/test_checkpoints.py`, prose docs (`openclaw-mcp-operator-guide.md` §"What MCP
   Supports Now", L61+, manually curated, incomplete). **Trap #2:** the same tool name also exists on
   a *second* surface — `OperatorService.list_checkpoints` (`app/services/operator.py:409`) wired into
   TUI gateways (`tui/gateways/inprocess.py:113`, `tui/gateways/mcp.py:268`). Nothing tells the
   newcomer whether the TUI surface must grow the twin too. **Hops: ~5 reads + 2 greps.**
4. Test seam requirement: every tool resolves runtime via package-attribute lazy binding; documented
   only if you happen to read `helpers.py:57-60` or `tools/__init__.py:14-22`.

**Friction points:**
- **F1 — dual rollback-record stores with divergent ids** (artifact-store `RollbackRecord` from
  `checkpoints.py:67-77` vs `RollbackManager._record_rollback` at `checkpoints/rollback.py:83-91`,
  which returns a record whose `invalidation_report_ref="invalidation:{checkpoint_id}"` is a ref
  format nothing else produces). Listing "the" rollback records is ambiguous by construction.
- **F2 — auto-generated tool descriptions.** `registry.py:112`: description is literally
  `f"MCP tool: {name}"` — zero semantics reach MCP clients; the real contract lives only in code.
- **F3 — undeclared touchpoint count.** Adding a tool = 4–6 edits across 3 packages + prose docs,
  none listed anywhere. AGENTS.md documents sub-package *boundaries* but not the MCP-tool checklist.
- **F4 — ToolGroup choice is guesswork** (`mcp/contract.py:25-40` — CHECKPOINT vs AUDIT both plausible).

**SEVERITY:** High (this is the repo's primary extension path). **COGNITIVE COST:** ~2–4 h including
the two-trap detours; risk of picking the wrong record store ships silently.
**TARGET DESIGN:** (a) one authoritative producer: `RollbackManager` persists via artifact store only,
tool-side duplicate writer deleted; (b) add an "Adding an MCP tool" checklist section to AGENTS.md
(handler module → registry import+register → group choice → unit test file → operator-guide entry);
(c) replace `_tool_contract` boilerplate descriptions with per-tool one-liners passed at `_register` site.
**MIGRATION:** checklist is pure docs (S); description strings are 60 mechanical edits, doable per-group;
store unification needs the D-00-style report treatment (M, see debt register R-COG-3).
**EFFORT:** S/M/M. **RISK:** Low / Low / Medium (id-format consumers).

---

## Mission 2 — Hotspot anatomy

### Finding 2.1 — `app/services/operator.py` (473 LOC): one class = the whole operator API; breadth, not depth

Structure: single `OperatorService` class, ~45 public methods + 10 private helpers
(outline L53-467). It is honestly documented as "intentionally thin" (L2-4), and mostly is — but:

Distinct reasons-to-change packed in one class: (1) project lifecycle use-cases
(create/set_active/submit_idea), (2) four workspace view-models (dashboard/review/validation/generation,
L221-367), (3) review mutations (approve_phase/request_revision), (4) browse/inspect delegation
(L389-419 → `_browse_ops`), (5) generation delegation (L340-367 → `_generation_ops`), (6) comments,
(7) audit feed, (8) dashboard status heuristics (`_status_for_state`, `_recommendation`, L452-473).
That is **≥6 reasons-to-change**; any TUI screen change, any runtime API change, and any new use-case
all land here.

**Layering leak (worst concrete spot):** `operator.py:209-213` — the service mutates graph state
directly (`state["idea"] = idea.strip()`) and writes back into the runtime's project map
(`self.runtime.projects[project_id] = next_state`). The "thin service" reaches around `StudioRuntime`'s
API into its internals; every reader must learn that `runtime.projects` is public-by-convention.

**SEVERITY:** Medium. **TARGET DESIGN split (named):**
- `ProjectLifecycleService` (create/set_active/submit_idea/settings/profile resolution, L89-196)
- `WorkspaceViews` (get_dashboard/get_review_workspace/get_validation_workspace/get_generation_workspace
  + `_status_for_state`/`_recommendation`/`_has_blockers` — pure state→view-model mapping)
- `OperatorMutations` (approve_phase, request_revision, run_validation, comments)
with browse/generation ops staying in their existing `_browse_ops`/`_generation_ops` modules and the
facade shrinking to constructor + delegation (~150 lines).
**MIGRATION:** mechanical move-method; `tests/unit/app/services/test_operator_service.py` (653 LOC)
already exercises through the facade so it survives unchanged. Do it after runtime.projects access is
funneled into one `runtime.save_project_state(state)` method.
**EFFORT:** M. **RISK:** Low (behavior-preserving, high test coverage).

### Finding 2.2 — `agents/runner.py` (471 LOC): three products in one class — prompts, retry ladder, mock plumbing

Structure: `RCTCOPrompt` (L31-54, rendering), `_ResolvedCallParams` (L56), `PromptRunner` (L69+):
prompt assembly (`build_rctco` L86, `_role_section`/`_kb_context_section`/`_constraint_section`
L103-133, `_json_instruction_suffix` L195), mock machinery INSIDE the production class
(`_find_mock_response` L134, `_generic_mock_fallback` L153), the 3-attempt model-call ladder
(`_chat_once` L202, `_attempt_normal_call` L222, `_attempt_structured_retry` L260,
`_attempt_fallback_model` L311, `_all_retries_exhausted` L295, orchestrated by `call_model` L346-382),
template plumbing (`run_from_template` L397, `_template_to_prompt` L426), and handoff creation
(`create_handoff` L449).

**Reasons-to-change: ≥5** (prompt format; retry/compression policy; mock-registry mechanics;
template adaptation; handoff schema). The retry ladder itself is well-factored (each attempt is a
named method returning `(result, carried_prompt)`); the problem is everything else sharing the class.

**Second finding — errors-as-dicts contract:** failure is signaled by returning
`{"status": "model_failure", ...}` (`runner.py:300-309`), not raising. Callers must remember to check;
nothing in the type system distinguishes a result from a failure envelope. Combined with the `assert
adapter is not None` at L211, the failure protocol is implicit folklore.

**SEVERITY:** Medium-High (agents/ is phase 07 core; every agent behavior tweak lands here).
**TARGET DESIGN split (named):**
- `rctco.py` → `RCTCOPrompt` + `build_rctco` + sections + template adaptation (pure string work)
- `call_ladder.py` → `ModelCallLadder.call(prompt_text, params)` owning attempts/compression/exhaustion,
  raising `ModelCallExhausted` (or returning a typed `CallOutcome` union) instead of status dicts
- `mock_responses.py` → canned-response registry, injected into the ladder
`PromptRunner` remains as thin composition.
**MIGRATION:** extract mock registry first (only tests touch it), then ladder; `run()`/`run_from_template()`
signatures preserved as façade methods so callers don't change.
**EFFORT:** M (mocks S, ladder M). **RISK:** Medium — retry behavior is subtle (compression factors
0.6/0.35 carried across attempts, L240/L281); needs characterization tests before moving.

### Finding 2.3 — `graph/nodes/_context.py` (470 LOC): four unrelated jobs behind an apologetic name

Structure (outline L20-456): (1) `_AGENT_PROFILE_MAP` — a 22-row **agent→model-profile config table**
(L27-52) living inside a context module; (2) phase-context summarization (`_build_phase_context`,
`_constitution_summary`, `_metrics_summary`, `_apply_phase_output_sections`, `_build_dependency_map`);
(3) artifact summarization/previews (`_load_phase_artifacts`, `_summarize_phase_artifact`,
`_scene_preview_lines`, `_shot_preview_lines`, ...); (4) upstream-artifact injection incl. a second
ref parser and `_UPSTREAM_CONTENT_SOURCES` routing table (L298-403); (5) model/config plumbing
(`_model_overrides_for`, `_inject_config_context`, `_preferred_providers`, `_artifact_context_max_chars`).

**Reasons-to-change: 4–5.** Adding an agent means editing this file (profile map) AND the agents
registry — the map duplicates knowledge that belongs beside agent registration. The module name
`_context.py` tells a scanner nothing; the underscore-prefix convention hides 470 load-bearing LOC
from directory skims.

**SEVERITY:** Medium. **TARGET DESIGN split (named):**
- `graph/nodes/agent_profiles.py` → `_AGENT_PROFILE_MAP` (+ ideally merged into agents/registry)
- `graph/nodes/prompt_context.py` → phase-context builders & previews
- `graph/nodes/upstream_injection.py` → ref parsing, `_UPSTREAM_CONTENT_SOURCES`, injectors
config-context helpers fold into prompt_context.
**MIGRATION:** pure moves, imports updated via nodes/__init__ re-exports; no signature changes.
**EFFORT:** S-M. **RISK:** Low.

---

## Mission 3 — Naming & vocabulary drift

### Finding 3.1 — "mode" means three things, all adjacent in the same state schema

**EVIDENCE:** `state_schema.py:121,124,125` declares `server_mode`, `runtime_mode`, `workflow_mode`
side by side; `operator.py:234` reads `str(state.get("runtime_mode", state.get("server_mode", "")))`
— a fallback chain proving even the code isn't sure which is authoritative; `DashboardSummary`
exposes it as `runtime_mode`. `app/runtime.py:45` owns `server_mode`; `create_runtime(server_mode=...)`.

One concept (which environment am I running in) + one concept (how autonomous is the loop) wear
three names, with fallback-or chains instead of a single accessor.

**SEVERITY:** High (every newcomer trips within the first hour — I did, in `get_dashboard`).
**TARGET DESIGN:** `environment_mode` (mock/real server) and `approval_policy` (manual/auto);
one property each on StudioRuntime; deprecate aliases with explicit mapping in `_persistence.py:164`.
**EFFORT:** M (state key migration touches persistence + TUI + tests). **RISK:** Medium (persisted
checkpoint/project JSON carries the old keys — needs tolerant reads).

### Finding 3.2 — The artifact-ref string format has 6 builders and ≥8 parsers

**EVIDENCE:** built as `f"artifact:{id}:v{version}"` in `graph/nodes/_agent_artifacts.py:142`,
`mcp/tools/checkpoints.py:44`, `mcp/tools/_profile_change.py:376`, `post/subtitle_agent.py:109`,
`post/delivery_packaging_agent.py:178`, `post/assembly_agent.py:133` (that last trio hardcodes `v1`);
parsed via `split(":")` in `artifacts/matrix_projection.py:51`, `graph/context_packets.py:180`,
`graph/nodes/qc.py:171`, `graph/nodes/_context.py:292` and `:322`, `graph/_visual_matrix_coverage.py:24`,
`graph/consistency.py:74`, `generation/executor_prompts.py:68`. Meanwhile a Pydantic `ArtifactRef`
schema EXISTS (`schemas/artifact.py`, used by `_context.py:_parse_ref`).

AGENTS.md says "never raw dicts/stringly-typed across boundaries"; the single most-traveled boundary
in the system violates it 14 times. Changing the ref format (e.g., adding project scoping) requires
finding all 14 sites with no shared constant to grep for except the literal `"artifact:"`.

**SEVERITY:** High. **TARGET DESIGN:** `ArtifactRef.parse(s)` / `.render()` as the only two touchpoints;
builders/parsers call them. **MIGRATION:** introduce pair, sweep call sites mechanically
(grep `split(":")` + `artifact:{`), each sweep trivially verifiable. **EFFORT:** M. **RISK:** Low
(refactor is behavior-preserving; mypy strict catches stragglers).

### Finding 3.3 — project/state/run conflation; blocker/gate/check near-misses

**EVIDENCE:** `rt.get_project(project_id)` returns the *graph state dict* (`helpers.py:44-52`,
used as `state` everywhere); `operator.py:207-213` names the same object `state` then stores it under
`runtime.projects[project_id]`. "Gate" appears as `prep_gates.py`, "Gate A/B/C" in comments
(`orchestrator_state.py:70-72`), while the router calls the same family `blocked`/`eligible` actions
(`operator.py:240-241`), validators emit issues with `severity == "blocking"`
(`orchestrator_state.py:297-298`), and `_action_routing.py:90` has yet another `_is_blocking_issue`.
Four words — gate, blocker, blocking issue, blocked action — for one concept with subtly different
producers. UNCERTAIN: full census not taken; sampled instances suffice to show drift exists.

**SEVERITY:** Medium-Low individually; compounds with 3.1. **TARGET DESIGN:** glossary section in
AGENTS.md ("state = graph state dict; gate = orchestrator_validators check; blocker = issue with
severity=blocking surfaced by router"); unify `_is_blocking_issue` helpers (there are ≥2 copies:
`_action_routing.py:90`, `app/services/operator.py` `_blocking_state_issues`).
**EFFORT:** S (glossary + helper dedup). **RISK:** Low.

---

## Mission 4 — Tests as spec

### Finding 4.1 — The suite pins a binding *implementation detail* 68 times

**EVIDENCE:** `monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)` occurs 68×
across 11 unit test files (8 matching the exact quoted pattern; file count critic-corrected from an
initial overcount of 32) (e.g., `tests/unit/mcp/tools/test_bibles.py:88,146,166,179,...`;
`test_validation.py:26,38,54,...`). This forces production structure: `tools/__init__.py:14-22`
carries a comment block explaining tools MUST re-import `get_runtime` from the package so patches
propagate, and `helpers.py:57-60` repeats the warning. Tests aren't asserting a contract here —
they're enforcing a module-layout constraint (lazy attribute binding) on production.

**Cost:** anyone who "cleans up" the import to `from film_pipeline.app.runtime import get_runtime`
inside a tool module passes mypy and breaks dozens of tests non-obviously. Conversely, the seam makes
every tool test a fake-runtime test — cheap but blind to wiring reality (see 4.3 contrast).

**SEVERITY:** High (largest single tax on safe refactoring). **TARGET DESIGN:** dependency injection
at registration time — `ToolContext` object holding `runtime_factory`, bound in `register_all_tools`;
handlers receive ctx. Then exactly ONE test constructs real runtime; tool tests inject fakes via the
public seam. **MIGRATION:** add optional `rt=` kwarg path first, migrate tests per-module
(16-test files), then remove package-attr patching. Do NOT big-bang: D-003's history shows this seam
is load-bearing (`.fleet/reports/D-003.md:8-13`). **EFFORT:** L. **RISK:** Medium.

### Finding 4.2 — Exemplars and weak spots

**Good exemplars (names assert observable behavior; arrange via public API):**
1. `tests/unit/graph/test_scope_contract.py` — `test_never_fewer_shots_than_scenes`,
   `test_is_deterministic`, `test_unknown_pacing_and_film_type_default_to_standard` (L29,64,69):
   properties, not implementation; survives internal rewrites.
2. `tests/unit/mcp/tools/test_checkpoints.py` — drives real runtime in mock mode through the public
   tool functions; asserts `result["ok"]`, id prefixes, listing contains created (L33-56). This is
   what every MCP tool test should look like — note it uses NO monkeypatch.
3. `tests/unit/test_orchestrator_validators.py` — `test_passes_when_shot_counts_match` /
   `test_blocks_on_shot_count_mismatch` / `test_blocks_on_runtime_mismatch` (L74,90,107): pass/fail
   pairs read like the validator's spec.

**Weak exemplars:**
1. `tests/unit/app/test_app_ops.py` — 31 monkeypatches; `monkeypatch.setattr(bootstrap,
   "validate_environment", list)` (L125,148) replaces a function with the builtin `list` type to
   fake an empty result: pure implementation pinning, illegible to newcomers, breaks on any refactor
   of bootstrap internals regardless of behavior.
2. `tests/unit/tui/test_app_redesign.py` (2138 LOC) — names are fine
   (`test_approve_disabled_when_not_eligible` L160) but the file is an unindexed monolith mixing
   gallery/studio/generation concerns; finding "the test for X" is a scroll hunt; name ("redesign")
   encodes a past UI epoch, not behavior domain.
3. `tests/unit/test_mcp.py` (1301 LOC) — top-level grab-bag (registry + projects + state +
   checkpoints...) parallel to the well-split `tests/unit/mcp/tools/*` tree; duplicated coverage with
   different styles invites drift about where new tests go.

**Monkeypatch-vs-contract balance overall:** unit suite covers 88.6% alone (given), and much of that
is earned through the fake-runtime seam rather than contracts; the KNOWN FACTS gaps confirm the blind
spots — brief.py StoryBible cross-checks have zero unit exercise (no `story_bible` reference anywhere
in `tests/unit/test_orchestrator_validators.py`), `app/_resume.py` staleness quartet
(`_STALE_REQUEST_CODES`, `_has_stale_generation_request_blocker`, L14-79) is tested only indirectly
via `tests/unit/graph/test_real_human_gates.py`, and `graph/nodes/qc.py` translation helpers
(`_issue_entry` L426, `_as_shots_view` L223) are imported by NO test (tests target
`graph/subgraphs/qc` instead — `tests/unit/graph/test_qc_subgraph.py:9`).

**TARGET DESIGN:** per-file rule of thumb already half-followed: prefer real-runtime-in-mock-mode
(test_checkpoints.py style); monkeypatch only process boundaries; split monolith test files along the
same seams as src. **EFFORT:** M (mostly moves + a few real-runtime fixtures). **RISK:** Low.

---

## Mission 5 — Deferred-debt register (consolidated)

Sources: `.fleet/reports/D-003.md` deferred sites (§DEFERRED, L39-55 + FLAGS_PROPOSALS L102-111),
route_agent dormant arms, known duplications (bible coercion, ledger-direct, visual_dev normalizer
per D-001.md:88-89), plus cognition-lens findings above.

| ID | Debt | Evidence | Why it taxes cognition | Payoff if paid | Effort | Risk |
|----|------|----------|------------------------|----------------|--------|------|
| DBT-1 | ~18–20 near-verbatim active-project preambles left unconverted by D-003 (ID-only x~15, tuple-helper x2, fallback-to-active x2, find_project x1) | D-003.md:39-55,103-111; validation.py::_require_project, _profile_change.py::_active_state | Reader must diff 3 preamble shapes per tool to spot the real difference | One `_active_project_id`-style helper + optional `fallback_active=` flag; −~80 LOC, one resolution semantic | S-M | Low (behavior deltas at None-handling need per-site eyeballing) |
| DBT-2 | route_agent repair/review/failure_handler arms unreachable from production (no caller passes task_type≠default) | _agent_routing.py:143-181; _agent.py:190 default; zero `task_type=` call sites in src outside _agent.py | 199-line router read fully; ~half guards for paths nothing triggers; tests keep dead branches green (test_graph.py, test_services.py) | Either wire failure-handler arm into the graph's failure path or mark arms `# dormant:` + skip their tests; −~90 LOC attention | S (mark) / L (wire) | Low mark / Medium wire (product decision) |
| DBT-3 | Dual rollback-record producers & id formats (artifact-store vs in-memory manager) | mcp/tools/checkpoints.py:67-77 vs checkpoints/rollback.py:76-93 | Makes any rollback-audit feature ambiguous at the data-model level (Finding 1.2-F1) | Single writer; `list_rollback_records` becomes a trivial tool | M | Medium (id-format consumers: audit feed, e2e scenario_07) |
| DBT-4 | Ledger-direct duplication: MCP generation tools construct GenerationLedgerManager directly; OperatorService path uses GenerationExecutor | generation/status.py:19-21,43-46; dispatch.py:28-246 vs app/services/_generation_ops.py:143-163 | Two lifecycles for row-status transitions; fixes must be applied twice (D-005a ripple hit exactly this) | Route MCP tools through executor/service ops; one owner for status mapping | M-L | Medium (status mapping subtleties, see D-005a.md:57) |
| DBT-5 | visual_dev_agent normalizer ~80% overlap with shared normalize_model_output (intentionally divergent: raises AttributeError on raw str, per R-105) | agents/impl/visual_dev_agent.py:42,57; agents/impl/_model_output.py:16; D-001.md:88-89 | Every normalizer change re-audits both; divergence rationale lives only in fleet reports | Extract shared core + explicit `strict=True` variant; document delta at definition site (not in .fleet/) | S-M | Medium (edge-behavior is contractual; tests exist at test_impl_agents.py:480-507) |
| DBT-6 | run_agent_for_phase: fully dead public-shaped function (zero callers in src AND tests) | graph/nodes/_agent.py:188-230; absent from nodes/__init__ exports | Reader assumes lifecycle entry point; docstring promises routing behavior nobody uses | Delete (or export+wire if intended API) | S | Low (grep-proven dead) |
| DBT-7 | get_runtime lazy-binding seam pinned by 68 monkeypatch sites (Finding 4.1) | 11 test files (see corrected F-4.1); tools/__init__.py:14-22; helpers.py:57-60 | Constrains import layout forever; blocks clean extraction of tool modules | DI via ToolContext at registration | L | Medium |
| DBT-8 | Ref-format scatter (Finding 3.2): 6 builders, 8 parsers, ArtifactRef schema unused at these sites | See Finding 3.2 evidence | Format changes require archaeology; post/* hardcodes `:v1` | parse/render chokepoints | M | Low |
| DBT-9 | Untested spec-bearing helpers: qc.py translation helpers, _resume staleness quartet, brief.py StoryBible cross-checks | Known-facts verified in Finding 4.2/4.3 | Future editors change behavior with green CI | Characterization tests before any of the above refactors touch those files | M | Low |

Recommended order: DBT-9 (characterize first — it de-risks everything else), DBT-6+DBT-1 (quick wins),
DBT-8, DBT-3, DBT-2 decision, DBT-4, DBT-7 last (largest, most invasive).

---

## Mission 6 — Documentation-code trust (3 samples against architecture-blueprint.md)

### Finding 6.1 — Claim "Every major capability should be reachable through an MCP tool before it is exposed through any other UI" (blueprint §System Layers 1, L23-43): PARTIALLY STALE

Reality: a parallel direct-service surface (`app/` + `tui/`) reaches the same capabilities WITHOUT the
MCP layer — `tui/gateways/inprocess.py:113-114` calls `OperatorService.list_checkpoints`, bypassing
`ToolRegistry` entirely; `OperatorService.submit_idea/approve_phase` (operator.py:197-341) duplicate
MCP tool logic at the service layer. Not wrong to exist, but the blueprint's MCP-first invariant is
described as absolute when it's actually "two surfaces, one shared runtime". A reader would build the
next feature MCP-only and then wonder why the TUI needs a twin method.

### Finding 6.2 — Claim implied by "Core State Domains" (blueprint L135-159: 21 tidy domain keys) and AGENTS.md "Use Pydantic v2 for all schemas (never raw dicts across boundaries)" (AGENTS.md:44): MISLEADING

Real state is a raw dict (`dict[str, Any]`) threaded through every node; the operative schema is
(a) a TypedDict-ish declaration (`state_schema.py:115-160`) plus (b) a shadow namespace of
`_orchestrator__*` keys whose shapes live ONLY in comments (`orchestrator_state.py:18-72`, e.g.
"# Shape: list[RevisionRequest] (serialized as dict)"). `orchestrator_state.py:8-10` admits it:
"Operates on the existing dict-based graph state to avoid a broad refactor." A reader implementing
against the blueprint would define Pydantic state objects and fight every node signature.

### Finding 6.3 — Blueprint omits ~40% of the codebase's real estate: MISLEADING BY ABSENCE

`grep -n "tui\|TUI\|OperatorService\|app/" documentation/architecture-blueprint.md` → zero hits.
No mention of `src/film_pipeline` layout at all. Meanwhile AGENTS.md:49-66 documents **12**
sub-packages; the tree has **19** (`cli`, `constraints`, `generation`, `observability`, `testing`,
`tui`, `app` unmapped to phases — count critic-corrected from an initial 21). The blueprint's six "System Layers" describe the LangGraph/MCP
core faithfully (that part matches well — orchestrator, agents, KB, artifacts all check out), but a
newcomer reading only it would not know the operator application layer — containing 3 of the 10
largest files (operator.py 473, studio.py 471, runtime.py 464) — exists.

Also stale-in-detail: blueprint's only "shot density" mention (L1069) doesn't point at
`scope_contract.py` (Finding 1.1-F4); `openclaw-mcp-operator-guide.md`'s tool catalog (L61-81) is
hand-curated prose that already lags the registry (omits checkpoint/rollback/state families listed
in registry.py:137+) with no sync mechanism.

**SEVERITY:** High collectively. **TARGET DESIGN:** (1) add "Application Layer (app/, tui/)" section
to blueprint with the two-surfaces diagram; (2) regenerate AGENTS.md table to 19 packages or mark the
phase-table as historical; (3) generate the operator-guide tool list from `register_all_tools` via a
script (tools are already enumerable). **EFFORT:** S for docs, S for the generator script. **RISK:** Low.
**UNCERTAIN:** whether product-completion docs (unread here) already cover the app/tui layer somewhere.

---

## Top-3 priorities

1. **Break the get_runtime test-seam lock-in (DBT-7 / Finding 4.1)** — highest leverage: it taxes every
   future refactor of the MCP/tool layer, is the single most repeated pattern in the suite (68 sites),
   and its constraint is currently enforced only by comments. Pair with characterization tests from
   DBT-9 so the conversion is provable.
2. **Chokepoint the artifact-ref format (DBT-8 / Finding 3.2)** — cheapest high-severity fix with
   immediate safety payoff: 14 scattered build/parse sites collapse to two functions; removes the most
   likely silent-corruption vector when the ref scheme evolves (rollback ids already show format drift).
3. **Document the real topology (Findings 6.1-6.3 + 1.2-F3)** — blueprint app/tui section, AGENTS.md
   package table + "adding an MCP tool" checklist, generated tool catalog. Pure-docs effort (days)
   that converts the two walkthrough traps (dual surfaces, unknown touchpoints) into signposts.

**UNCERTAIN markers:** full synonym census (3.3) was sampled, not exhaustive; DBT-2 "wire vs delete"
is a product decision needing owner input; whether persisted checkpoint JSON embeds `server_mode`
keys (affects 3.1 migration risk) was inferred from `_persistence.py:164` but not round-trip tested.
