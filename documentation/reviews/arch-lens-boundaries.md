# LENS-BOUNDARIES — Module Boundaries / Layering / Coupling

Repo: `film-pipeline-langgraph` @ `arch-improvement-review`, HEAD `e811d1d`.
Scope: sub-package boundaries per AGENTS.md law — *"graph and mcp may import across all sub-packages; domain modules must not import each other directly — they communicate through artifacts."*
Method: AST-extracted every `from film_pipeline.*` import in `src/film_pipeline` (module-level and function-body separately), Tarjan SCC for cycles, then read the offending files. All edges below were read at source, not inferred.

**Headline fact:** `src/film_pipeline/` contains **19 packages**, not 12. Unlisted in the AGENTS.md boundary table: `app`, `tui`, `cli`, `testing`, `observability`, `constraints`, `generation`. The law is undefined for 7 of 19 packages — see Finding 8.

---

## Finding 1 — post → validation: real law breach, and it smuggles a duplicated rule set

**EVIDENCE**
- `src/film_pipeline/post/delivery_packaging_agent.py:190` (lazy, inside `validate()`):
  `from film_pipeline.validation.impl.delivery_completeness import DeliveryCompletenessValidator`
- The only post→validation edge in the codebase (AST-verified). It is a domain→domain direct import: breach by the letter of the law.

What post actually needs is not just the class — it re-implements the validator's *input contract*:
- `post/delivery_packaging_agent.py:48-77` `_completeness_check_artifact()` fabricates a synthetic artifact dict ("Canonical basenames stand in for real paths because the validator only checks that each manifest slot is present and non-empty") — post hard-codes knowledge of `DeliveryCompletenessValidator.run()`'s expected shape.
- `post/delivery_packaging_agent.py:11-17` `_COMPLETION_REQUIREMENTS` + `is_complete`/`missing_items` (lines 37-45) duplicate "what makes delivery complete", which is also encoded inside `validation/impl/delivery_completeness.py`. Two sources of truth.
- Bonus duplication: local `DeliveryPackage` dataclass (line 20) vs `film_pipeline.schemas.delivery.DeliveryPackageModel` (line 147).

**SEVERITY:** medium

**WHY IT HURTS:** if the validator ever starts checking that manifest paths are real/non-empty (its docstring suggests it currently doesn't), post's fabricated `"subtitles.srt"` strings silently produce false **pass** results on an actual delivery gate. Changing completeness rules requires editing two files in two packages; missing one yields a package that says complete while QC says incomplete.

**TARGET DESIGN:** invert the dependency. Move the "run completeness check" behavior into validation as the canonical entry point — e.g. `validation/impl/delivery_completeness.py::check_package(package_like) -> ValidationReport` — or have graph/mcp (the sanctioned orchestrators) run the validator over the persisted `DeliveryPackageModel` artifact after `DeliveryPackagingAgent.persist()`. post keeps only building/persisting; it never imports validation.

**MIGRATION STEPS**
1. Add `check_delivery_package(model: DeliveryPackageModel) -> ValidationReport` to `validation/impl/delivery_completeness.py`; make it consume the schema model, not an ad-hoc dict (kills `_completeness_check_artifact`).
2. Repoint `mcp/tools/assembly.py::export_delivery_package` (the caller of `.validate()`) to call the validator itself after persisting.
3. Delete `DeliveryPackagingAgent.validate()` + `_completeness_check_artifact`; keep `_COMPLETION_REQUIREMENTS` only where the schema derives `is_complete`.
4. Test: unit test that a package missing subtitles fails via the new path; grep gate: no `from film_pipeline.validation` under `src/film_pipeline/post/`.

**EFFORT:** S. **RISK:** low (single call site, behavior preserved).

---

## Finding 2 — config → providers: wiring logic parked in the wrong layer, incl. a private-symbol import

**EVIDENCE** (`config/profile_resolver.py`)
- Line 179 (lazy, in `register_project_providers()`): `from film_pipeline.providers.factory import build_provider_adapter`
- Line 204 (lazy, in `missing_provider_credentials()`): `from film_pipeline.providers.credentials import _env_var_for, is_configured` ← imports an underscore-private symbol across a package boundary.
- Both functions take `rt: Any` and call `rt.clear_providers()/register_provider()/set_provider_health()` (lines 185-196) — config reaching up into runtime objects.
- Module docstring (line 1): "Neutral profile stack resolution used by MCP tools and OperatorService" — so this coupling is load-bearing: `mcp/tools/projects.py:8`, `mcp/tools/_profile_change.py:20`, `app/services/operator.py:37` all transit it.

Why does config know providers? Because parsing provider specs out of profiles (`provider_specs_from_raw`, lines 83-170) is legitimately config work — but *building adapters*, *registering them on a runtime*, and *checking credentials* are provider/runtime concerns that were co-located with the parser instead of layered on top of it.

**SEVERITY:** medium

**WHY IT HURTS:** any change to adapter construction or credential env-var naming now requires touching `config` (phase 03), breaking the phase-scoping rule; the `_env_var_for` import can break silently on any rename inside providers because private symbols have no compatibility contract. New contributor reading `config/` reasonably assumes the package is profile-loading only, then discovers runtime mutation side effects.

**TARGET DESIGN:** split the file along its existing seam:
- Keep in `config/profile_resolver.py`: `load_profile_flex`, `canonicalize_profile_stack`, `resolve_project_config`, `provider_specs*` (pure spec parsing).
- Move `register_project_providers` + `missing_provider_credentials` to a new `providers/bootstrap.py` (or into `app/_provider_seeds.py`, which already does lazy provider wiring at `app/_provider_seeds.py:24,46,71`). Make `providers.credentials._env_var_for` public (`env_var_for`) since two packages need it.

**MIGRATION STEPS**
1. Create `providers/bootstrap.py` with the two functions verbatim; add public alias `env_var_for = _env_var_for` in `providers/credentials.py`.
2. Update the three call sites (grep `register_project_providers|missing_provider_credentials`): `mcp/tools/projects.py`, `mcp/tools/_profile_change.py`, `app/services/operator.py`.
3. Delete the functions from config. Grep gate: no `from film_pipeline.providers` under `config/`.

**EFFORT:** S. **RISK:** low (pure move; mypy strict will catch stragglers).

---

## Finding 3 — agents → providers: four edges; one couples agent transport to a concrete adapter module

**EVIDENCE**
- `agents/runner.py:17`: `from film_pipeline.providers.failure_classifier import compress_prompt_for_retry, is_token_limit_exceeded`
- `agents/model_adapter.py:31`: `from film_pipeline.providers.adapters.seedance_openrouter import OPENROUTER_API` (used at line 98: `f"{OPENROUTER_API}/chat/completions"`) — a generic chat adapter importing a constant owned by one specific media-provider adapter.
- `agents/model_adapter.py:32`: `from film_pipeline.providers.credentials import lookup` (used with hardcoded id `lookup("seedance-openrouter")`, line ~59).
- `agents/_http_transport.py:18`: `from film_pipeline.providers.credentials import redact`

Judgment, edge by edge:
- `runner → failure_classifier`: acceptable shared logic, but token-limit classification/retry-shaping is agent-execution concern living in the providers package (phase 10); it makes providers a de facto misc drawer.
- `model_adapter → OPENROUTER_API`: worst of the four. `ModelAdapter` is presented as the model-agnostic chat transport behind `ModelRouter` ("Model selection always flows through the ModelRouter — no hardcoded model strings"), yet its base URL comes from `providers/adapters/seedance_openrouter.py:27`. Renaming/moving the seedance adapter breaks the agent chat path with zero signal.
- `credentials.lookup/redact`: small, stable utilities; low harm.

Note there are effectively TWO provider HTTP stacks: `providers/adapters/*` (media generation) and `agents/_http_transport.py` + `model_adapter.py` (LLM chat). The split is defensible; the leaked shared constants are not.

**SEVERITY:** low-medium (runner/failure_classifier), medium for the `OPENROUTER_API` edge.

**WHY IT HURTS:** the OpenRouter URL is a deployment constant masquerading as one adapter's property. Moving chat to another gateway means editing `agents/` to import a different adapter module, or duplicating the constant — both drift risks. Also muddies the phase story: agents (07) cannot be touched without loading providers (10/13) semantics.

**TARGET DESIGN:** move transport-neutral constants/utilities to neutral homes:
- `OPENROUTER_API` → `providers/credentials.py` (or a tiny `providers/endpoints.py`) next to `lookup`; seedance adapter imports it from there like everyone else.
- `failure_classifier` → either stays (document it as shared) or moves to `agents/_retry.py`; if it stays, rename mentally: providers is allowed to host cross-cutting LLM-API utilities, but AGENTS.md should say so.
- `redact`/`lookup` already fine where they are once endpoints join them.

**MIGRATION STEPS**
1. Add `OPENROUTER_API` to `providers/credentials.py`; re-export from `seedance_openrouter.py` for compat; repoint `agents/model_adapter.py:31`.
2. Optional: relocate `failure_classifier` under `agents/`; update `providers` tests.
3. Doc: one line in AGENTS.md marking `providers/credentials.py` as the shared credentials/endpoints utility for both stacks.

**EFFORT:** S. **RISK:** low.

---

## Finding 4 — graph → testing: production factory imports the test-fixtures package

**EVIDENCE**
- `graph/services.py:72` (lazy, inside `GraphServices.for_mock_runtime()`): `from film_pipeline.testing.fixtures.mock_responses import default_mock_responses`
- Production callers: `app/runtime.py:445-446` (`_build_services_for_mode`: `return GraphServices.for_mock_runtime()` when server_mode != "real") and `cli/driver.py:71-73`.
- The imported payload ships in the wheel: `src/film_pipeline/testing/fixtures/mock_responses.py` is 392 lines of canned demo-film responses (intake identity "Demo Film", target_runtime_seconds=20, …). `testing/` totals 663 LOC and also contains `mock_human.py`, `mock_model.py`, `scenarios.py`.

This is precisely the violation the mission suspected: `graph` (phase 05, production state machine) depends on the package named `testing`. Mock mode is a product feature (default server_mode is "mock"), but its fixture data lives under a package whose name promises dev-only contents — nothing stops a future cleanup from deleting/moving `testing/` as "test code" and breaking default startup.

**SEVERITY:** high (naming/lifecycle hazard, cheap to fix)

**WHY IT HURTS:** the package name lies about runtime status. Any tooling or agent that prunes test-only code (or a packaging decision to exclude `testing` from the wheel) removes the default runtime path. Conversely, refactors of mock responses must preserve production demo behavior, which nobody assumes for files under `testing/`.

**TARGET DESIGN:** mock mode data belongs to the composition root, not the state machine, and not a package named testing:
- Move `fixtures/mock_responses.py` → `app/mock_responses.py` (production mock-mode data, clearly documented).
- `GraphServices.for_mock_runtime` should accept the responses mapping as a parameter (dependency injection); `app.runtime._build_services_for_mode` supplies `default_mock_responses()`.
- `testing/` keeps `mock_human/mock_model/scenarios` and may import from `app.mock_responses` if e2e scenarios want the same canned data (testing→app is already an accepted direction; tui→app precedent). If you want zero testing→prod dependency, have tests import both.

**MIGRATION STEPS**
1. Add parameter `mock_responses: dict[str, dict[str, Any]] | None = None` to `for_mock_runtime`; fall back to empty dict.
2. Move file to `app/mock_responses.py`; update `app/runtime.py:446` and `cli/driver.py:73` to pass it.
3. Update ~14 test call sites (mechanical: they call `for_mock_runtime(artifacts_root=...)`; keep working unchanged via the optional param).
4. Grep gate: no `from film_pipeline.testing` anywhere under `src/film_pipeline/{graph,mcp}`.

**EFFORT:** S. **RISK:** low (behavior identical; tests unaffected by signature addition).

---

## Finding 5 — mcp thickness: generation lifecycle implemented twice (drift is live today) plus duplicated dispatch tables

The known fact is confirmed and is worse than "two implementations that can drift": **they have already drifted**, and there are three overlapping copies of the lifecycle.

**5a. Submit/poll lifecycle: `generation/executor.py` vs `mcp/tools/generation/dispatch.py`**

- Executor (`generation/executor.py:145-193` `_dispatch_row`): resolves the *actual prompt* (`resolve_shot_prompt(self._store, project_id, row.shot_id, shot_row, row.prompt_ref)`), uses per-row duration (`float(shot_row.get("duration_seconds", 5))`), records `submitted_at`, sets `next_action="poll"`.
- MCP tool (`mcp/tools/generation/dispatch.py:74-87` `_submit_one_row`): sends `prompt=row.prompt_ref` — the raw ledger ref string, **not the resolved prompt** — and hardcodes `duration=5.0` (line 78).
- Polling: executor `poll_once`/`_poll_row` (lines 196-293) downloads completed outputs and marks rows COMPLETED with artifacts; MCP `resume_generation_polling` (lines 190-242) rebuilds a synthetic `ProviderJob(status=SUBMITTED)` by hand (lines 216-223), maps status via `_generation_status` (173-187), and only updates ledger status — no download/completion handling.
- Consequence today: starting a batch via the MCP tool produces different provider payloads than starting it via OperatorService/executor, and polling via MCP can strand rows in RUNNING that the executor path would complete.

**5b. Planning defaults drift**

- `mcp/tools/generation/planning.py:74-75`: `provider = str(args.get("provider", "mock-video-provider"))`, `model = str(args.get("model", "mock-fast"))` hardcoded in the tool, then `mgr.plan_batch(...)` directly (line 84).
- `app/services/_generation_ops.py:60-63`: `svc.runtime.default_video_provider()` + `executor.plan(project_id, provider=..., model=...)`.
- Two planning paths resolve provider/model differently and write through different layers (ledger manager vs executor).

**5c. Text-only policy duplicated nearly verbatim**

| app/services/_generation_ops.py | mcp/tools/generation/_text_only.py |
|---|---|
| `_STALE_REQUEST_CODES` (:20) | `_STALE_ISSUE_CODES` (:9) — same frozenset |
| `_is_text_only_policy` (:208) | `_is_text_only_policy` (:12) — identical |
| `_text_only_request` (:240) | `_completed_request_row` (:16) — identical fields, identical `text-only-{project_id}-{shot_id}` ids |
| fallback shot "all" (:232) | fallback shot "all" (:58) |
| `_record_text_only_manifest` (:287-305), asset_id `"text-only-delivery"` | `_ensure_text_only_manifest_entry` (:76-97), same asset_id/kind |
| `svc.runtime.projects[...] = ...; svc.runtime._persist_project_state(...)` (:166-167) | `rt.projects[...] = active; rt._persist_project_state(...)` (:117-118) |

Extra smells in 5c: the MCP copy reads `store._root` (private attribute of `ArtifactStore`, `_text_only.py:85,97`); both copies invoke the runtime's private `_persist_project_state`. `runtime.py:69` does the same `getattr(store, "_root", None)` reach-in — three consumers of a private attr that deserves a public `root` property.

**5d. Validator dispatch tables duplicated, registry bypassed**

- `graph/nodes/qc.py:285-372`: seven lazy-import helpers hardcoding phase→validator classes (`_run_script_validators`, `_run_reference_validators`, … ).
- `mcp/tools/validation.py:73-115`: six near-identical helpers with the same mapping.
- Meanwhile `validation/registry.py` provides `ValidatorRegistry.lookup_by_scope/modality` and `graph/services.py:61` carries `validator_registry: Any = None  # ValidatorRegistry` — never populated, never used for dispatch (verified: only reference outside schemas/tests is the dead field and `app/smoke.py:81`). Adding a validator requires editing both hardcoded tables or QC and the MCP surface disagree.

**Counter-evidence for balance:** delegation already exists where someone did it right — `mcp/tools/generation/planning.py:118-119 preview_generation_prompts` calls `OperatorService(rt).preview_generation_prompts(...)`. The pattern to generalize is in the tree.

**SEVERITY:** high (5a/5b behavioral drift on a money-spending path), medium (5c/5d).

**WHY IT HURTS:** the MCP-first contract means MCP tools ARE the product surface; having them bypass `GenerationExecutor` means every fix to prompt resolution, durations, cost accounting, or output download must be hand-ported into tool code or the two surfaces sell different behavior. The text-only twins mean a policy change (e.g. new stale-issue code) fixes one surface and not the other.

**TARGET DESIGN:** MCP tools become thin handlers over domain services (the law's spirit: mcp = tool surface, phase 02):
- `dispatch.py`: `start/resume/cancel` delegate to `GenerationExecutor.start/poll_once/cancel` (add a small `cancel(project_id, generation_id)` to the executor; reuse its ProviderJob construction). Delete `_submit_one_row`, `_poll_row_status`, `_generation_status`, manual `ProviderJob(...)` builds.
- `planning.py::plan_generation_batch` delegates to `executor.plan(...)`; drop the `mock-video-provider`/`mock-fast` literals in favor of `rt.default_video_provider()` unless explicitly overridden in args.
- Extract the text-only policy into ONE module — natural home `generation/text_only.py` (domain owns policy; app and mcp both call it). Kill both local copies.
- Single validator dispatch source: either populate `GraphServices.validator_registry` and dispatch via `ValidatorRegistry.lookup_by_scope`, or (simpler, matches current style) one shared table `validation/dispatch.py::PHASE_VALIDATORS: dict[str, tuple[type, ...]]` consumed by `qc.py` and `mcp/tools/validation.py`.

**MIGRATION STEPS**
1. Add `GenerationExecutor.cancel()`; port `cancel_generation_request` to delegate.
2. Repoint `start_generation_batch`/`resume_generation_polling` to executor methods; delete drifted helpers; add integration tests asserting identical payloads via MCP path vs operator path (this test would fail today — write it first).
3. Move text-only policy to `generation/text_only.py`; both callers import it.
4. Introduce `validation/dispatch.py::PHASE_VALIDATORS`; replace both helper families.
5. Add `ArtifactStore.root` public property; replace three `_root` reach-ins.

**EFFORT:** M (steps 1-2), S (3-5). **RISK:** medium — MCP generation tools are covered by product-completion critical-tool gates; change behind contract-preserving envelopes with e2e runs before/after.

---

## Finding 6 — app as composition root: mostly genuine wiring; leakage is in privates and triplicated operator surfaces

Read in full: `app/runtime.py` (464 LOC), `app/services/operator.py` (473 LOC).

Wiring verdict: **mostly clean.** runtime.py delegates persistence/graph/checkpoints to `_persistence`/`_graph_exec`/`_provider_seeds` modules (lines 75-91, 212-238); operator.py is a facade of thin delegates onto `_browse_ops`, `_generation_ops`, `_project_discovery` (e.g. lines 340-368 are one-liners). The 900+ combined LOC decompose into ~40 small methods; there is no hidden business algorithm.

Real leakage found:

1. **Private reach-ins across layers:** `svc.runtime._persist_project_state(project_id)` (`app/services/_generation_ops.py:167`), same call in `mcp/tools/generation/_text_only.py:118`; `getattr(store, "_root", None)` (`app/runtime.py:69`, `mcp/tools/generation/_text_only.py:85`). Composition root calling a private method of the object it composed is a design smell, and MCP tools doing it crosses a layer.
2. **Constructor side effects:** `StudioRuntime.__post_init__` (runtime.py:56-71) picks roots from env, creates directories, and loads persisted projects — a dataclass constructor performing filesystem IO; hard to instantiate for tests without temp dirs.
3. **Three parallel operator surfaces** with partially duplicated orchestration: MCP tools (`review_phase_artifacts` builds ReviewPackage via generator + compute_actions, mcp/tools/review.py:33-100), `OperatorService.get_review_workspace` (operator.py:256-277, its own recommendation logic `_recommendation` :464), and `StudioRuntime.approve_phase/run_validation/request_revision` (:223-238). Same state, three shapes, two implementations of "what should the operator do next".
4. `operator._resolve_and_store_profiles` (operator.py:124) correctly uses config — composition done right; no issue.

**SEVERITY:** low-medium (items 1 and 3 medium; item 2 low)

**WHY IT HURTS:** renaming `_persist_project_state` or `ArtifactStore._root` breaks MCP tools and services invisibly to type-checkers' public-API expectations (mypy catches it only because everything is in-repo; any future extraction breaks). The triple surface means TUI, CLI, and MCP users can see different recommendations for the same project state.

**TARGET DESIGN:** make the composition root's contracts explicit: promote `_persist_project_state` → public `persist_project_state`, add `ArtifactStore.root` property; funnel "next action" computation through one place — `graph.router.compute_actions` already exists, so `OperatorService._recommendation` and the MCP review tool should both derive their strings from its output rather than each maintaining heuristics. Optionally split runtime construction out of `__post_init__` into `create_runtime()` (which already exists at :418) so the dataclass stays pure.

**MIGRATION STEPS**
1. Rename the persist method publicly, keep private alias one release; update 3 call sites.
2. Add `ArtifactStore.root`; update runtime.py:69 and _text_only.py.
3. Replace `_recommendation` heuristic with mapping over `compute_actions(state).next_action` (single source).
4. (Optional) move `__post_init__` body into `create_runtime`.

**EFFORT:** S (1-2), M (3). **RISK:** low.

---

## Finding 7 — circular-import risks: exactly one package-level cycle (app ↔ mcp) held together by lazy imports; 198 lazy cross-package imports overall

**EVIDENCE**
- SCC analysis of module-level intra-project imports finds one cycle: **{app, mcp}**.
  - `mcp/tools/__init__.py:22`: `from film_pipeline.app.runtime import get_runtime` (module level)
  - `app/product_gate.py:17`: `from film_pipeline.mcp.contract import make_registry` (module level)
- It survives only because `mcp/contract.py` imports stdlib only — i.e., the cycle is one careless `contract.py` import away from ImportError at startup. Additionally `mcp/server.py:164,241` lazily imports `app.runtime.get_runtime` / `app.bootstrap.validate_environment`.
- The seam is even documented as a hack: `mcp/tools/__init__.py` comment block — "`get_runtime` must be bound on this package *before* importing `registry` … so that tests which monkeypatch … continue to affect every tool function."
- Lazy cross-package imports total **198** (critic recount): mcp 109, graph 42, app 24, post 10, cli 5, artifacts 3, config 2, generation 2, tui 1 (AST count). Notable clusters: `graph/nodes/qc.py` (14, mostly validators — see 5d), `mcp/tools/**` (109 — mix of cycle avoidance and deferred-cost style), `app/_graph_exec.py` auto_checkpoint lazily importing schemas (:97-99), `artifacts/matrix_projection.py` lazily importing schemas (:59-69).

Judgment: most lazies are not cycle-breakers (schemas never imports anything; those could be hoisted safely). The genuinely load-bearing ones cluster around app↔mcp and the qc/validation dispatch. They hide true fan-out from any static boundary checker and make import order fragile.

**SEVERITY:** medium

**WHY IT HURTS:** a new contributor adding `from film_pipeline.mcp.tools import X` inside `mcp/contract.py` (to share a schema default, say) gets an opaque partial-initialization ImportError that depends on which entry point ran first. The monkeypatch-binding hack means tool behavior differs depending on whether code imported `film_pipeline.mcp.tools.get_runtime` vs `film_pipeline.app.runtime.get_runtime` — two names for one thing invites patching one and wondering why nothing changed.

**TARGET DESIGN:** break the cycle at the sanctioned seam — composition belongs to app, not mcp:
- Invert the `get_runtime` dependency: define a tiny runtime-accessor protocol in mcp (or pass a `RuntimeFactory` into `register_all_tools(registry, runtime_factory)`); `mcp/server.py` binds it at startup from app. Then `mcp/tools/__init__.py` no longer imports app at module level, and the binding comment dies.
- Keep `app/product_gate.py → mcp.contract` (one-directional, contract-only) — legal once tools don't pull app back.
- Hygiene pass: hoist obviously-safe lazies (anything importing `schemas`, `artifacts`, `kb`, `validation.impl` used unconditionally) to module level; leave genuinely optional/deferred ones with a `# lazy:` comment convention so a future import-linter can whitelist deliberately.

**MIGRATION STEPS**
1. Change `ToolRegistry`/`register_all_tools` to accept a runtime accessor callable; thread through `make_registry()`; bind from `mcp/server.py` and tests.
2. Remove top-level `from film_pipeline.app.runtime import get_runtime` from `mcp/tools/__init__.py`; update the ~30 tool modules' `tools_pkg.get_runtime()` to use the accessor.
3. Hoist safe lazies (schemas/artifacts/kb groups); rerun the SCC check as a CI script (30-line AST script, add to `scripts/`).

**EFFORT:** M. **RISK:** medium — touches every tool module's runtime access; mechanical but broad; the monkeypatch tests pin the exact behavior being changed, so they need updating in the same commit.

---

## Finding 8 — the 12-phase 1:1 mapping is strained: 7 of 19 packages ungoverned, and three phase-numbering schemes coexist

**EVIDENCE**
- Directories under `src/film_pipeline/`: agents, app, artifacts, checkpoints, cli, config, constraints, generation, graph, kb, mcp, observability, post, providers, review, schemas, testing, tui, validation (+ py.typed) = **19**.
- AGENTS.md table lists 12. Ungoverned: `app`, `tui`, `cli`, `testing`, `observability`, `constraints`, `generation`.
- Three numbering schemes: blueprint film phases 0-10 (documentation/architecture-blueprint.md lines 1719-1967: "Phase 0. Project Intake" … "Phase 10. Wrap"), AGENTS.md implementation phases 01-14, and the FilmPhase enum values in code (intake, constitution, development, script, visual_dev, shot_bible, gen_planning, generation, qc, assembly, delivery — visible in `graph/nodes/qc.py:139-147`).
- Where new phases actually plugged in: phase 14 (`post`) immediately needed validation behavior → Finding 1 breach. Generation logic grew its own `generation` package (executor, ledger, compositor, prompt_builder, frame reviewers — 17 files) that appears nowhere in the boundary table yet is imported by graph (allowed), mcp (allowed), and app (ungoverned direction). `constraints` (clean: imports only schemas) and `observability` (clean: one schemas import) behave well but have no stated rules.
- The "communicate through artifacts" rule covers *data* flow but has no answer for *behavior* reuse between domains — which is exactly what post needed (validator) and what qc/mcp duplicate (dispatch tables). That gap, not carelessness, produced Findings 1 and 5d.

Where would a NEW phase plug in? Today: create package N+1, import schemas freely, get pulled into graph/mcp/app — then discover it needs an existing domain's behavior and either breach the law (like post) or fork it (like the dispatch tables). The mapping is holding for data, failing for behavior.

**SEVERITY:** medium (documentation/law debt that converts into code breaches)

**WHY IT HURTS:** the law is the first thing every coding agent reads; when it misdescribes the tree (12 vs 19) and lacks a behavior-reuse mechanism, agents either over-breach or invent private seams. Phase-scoped changes ("Keep changes scoped to a single phase") are unjudgeable for 7 packages.

**TARGET DESIGN:** amend AGENTS.md Sub-Package Boundaries to codify reality:
1. Table gains rows: `generation` (13 — generation execution/ledger), `app` (composition root; may import all), `tui` (UI; imports app models only), `cli` (entry point), `testing` (dev harness; must not be imported by production — enforce after Finding 4), `observability`, `constraints`.
2. State the schemas exception explicitly: every package may import `schemas` (it is the contract layer; 60+ edges already say so).
3. Add the behavior-reuse rule domains currently lack: domain→domain *data* flows through artifacts; domain→domain *behavior* is exposed via a registry or service owned by the exporting domain (ValidatorRegistry pattern), invoked by graph/mcp/app — never by direct impl-class imports (this retroactively legalizes the intended end-state of Findings 1 and 5d).
4. Reconcile numbering: one paragraph mapping film phases ↔ implementation phases ↔ FilmPhase enum, or drop implementation-phase numbers from the table.

**MIGRATION STEPS**
1. Land the AGENTS.md edit (S, pure docs).
2. Add a CI import-boundary check driven by the amended table (the AST edge-scan used here generalizes; ~50-line script in `scripts/check_boundaries.py`).
3. Fold Findings 1/2/4 fixes in as the first violations the new gate catches going forward.

**EFFORT:** S (docs+script). **RISK:** none (doc), low (CI gate may flag pre-existing edges — start in warn mode).

---

## Top 3 priorities

1. **Consolidate the generation lifecycle behind `GenerationExecutor` (Finding 5a/5b/5c).** The drift is live: MCP `start_generation_batch` sends unresolved `prompt_ref` and hardcoded `duration=5.0` (dispatch.py:78) while the executor path resolves prompts and honors row durations; MCP planning defaults to `mock-video-provider`/`mock-fast` (planning.py:74-75) regardless of configured providers; the text-only policy exists twice. This is a money-spending path with two behaviors. Effort M, risk medium, highest value.
2. **Move mock-mode fixtures out of `testing/` and out of `graph` (Finding 4).** Production default startup depends on `film_pipeline.testing.fixtures.mock_responses` imported from `graph/services.py:72`. One S-sized move + DI parameter eliminates a package-name lie that invites deletion-by-cleanup. Effort S, risk low.
3. **Amend the boundary law for the 19-package reality and define the behavior-reuse rule (Finding 8), then enforce with a CI edge scan.** This is the root cause of Findings 1, 2 and 5d recurring: the law has no answer for domain→domain behavior needs. Docs + a 50-line checker. Effort S, risk none/low, prevents the whole finding class.

Uncertain items, marked UNCERTAIN: whether `GraphServices.validator_registry` was intended to become the dispatch mechanism (field exists, never populated — intent UNCERTAIN); whether excluding `testing/` from the wheel is desired (packaging config in pyproject.toml was not audited for this lens); exact historical reason for the `duration=5.0` literal in dispatch.py (could be deliberate simplification, but it diverges from executor behavior regardless).
