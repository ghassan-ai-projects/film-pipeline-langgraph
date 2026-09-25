# 13 — Test Doubles, Fixtures, and the Test Harness

Audit of the "test doubles, fixtures, and test harness" cluster.
Conforms to `00-methodology-and-quality-bar.md` (bar A). Every anchor below was read at HEAD.

> **Post-verification state (fix loop).** This file was independently checked in
> `docs/modular-architecture/reviews/verify-13.md` (5 CONFIRMED, 2 DOWNGRADED, 0 REJECTED).
> The corrections below are applied in this version; a reader should treat this file, not the
> verdicts alone, as the current state.
>
> | Finding | Verdict | Change applied |
> |---|---|---|
> | F-TEST-01 | DOWNGRADED High 15 → **High 12** | the "no test exercises the canned payloads" claim was false and the mutation was backwards; both fixed, third wrapper divergence and the `arch-lens-flexibility.md` prior art added |
> | F-TEST-02 | DOWNGRADED High 10 → Medium 4 → **WITHDRAWN** | the validator-shape comparison was a false equivalence (`clip-validator` is an agent id, not in `MVP_VALIDATORS`); the replacement fallback-duplication proof was then also disproved, because both fallbacks are test-pinned. Moved to "Withdrawn findings / unverified hypotheses" per §1.6.6 |
> | F-TEST-03 | CONFIRMED High 12 | coverage wording corrected (`list_files`/`restore_files` have no direct references) |
> | F-TEST-04 | CONFIRMED High 10 | sandbox-assert anchor corrected to `:169` |
> | F-TEST-05 | CONFIRMED Medium 6 | no change |
> | F-TEST-06 | CONFIRMED High 12 | no change |
> | F-TEST-07 | CONFIRMED High 10 | undercount corrected (five entry sites) and the wrong grep parenthetical fixed |
> | F-TEST-08 | CONFIRMED Medium 8 | no change |
> | F-TEST-09..11 | not reviewed | three seams missed by the verifier, added by the author after re-verification at HEAD (section "Findings added after verification") |
>
> Total findings in this file: **10** (F-TEST-01, -03..-11), plus **1 withdrawn hypothesis**
> (F-TEST-02, preserved in "Withdrawn findings / unverified hypotheses").

---

## Coverage

- **Repo:** `${REPO_ROOT}`
- **Branch:** `modular-app`
- **Commit audited:** `fb85baa0e6b769b709791a96a89980089304bf13` (`fb85baa`, merge of the storage upgrade)
- **Working tree at audit time:** clean (`git status --porcelain` empty)
- **Program baseline:** per `00-methodology-and-quality-bar.md:200-203` and this repo's
  `docs/modular-architecture/README.md` (281 src `.py` / 180 test `.py`).

Files read **in full** for this cluster:

| Path | Lines | Role |
|---|---|---|
| `src/film_pipeline/testing/__init__.py` | 14 | package exports |
| `src/film_pipeline/testing/mock_model.py` | 58 | mock model adapter |
| `src/film_pipeline/testing/mock_human.py` | 56 | mock human actor + `DecisionProfile` |
| `src/film_pipeline/testing/scenarios.py` | 136 | 13 canned provider scenarios |
| `src/film_pipeline/testing/storage.py` | 22 | sandbox store helpers |
| `src/film_pipeline/testing/in_memory_git.py` | 193 | git backend double |
| `src/film_pipeline/providers/mock_provider.py` | 189 | mock video provider + `ScenarioStep` |
| `src/film_pipeline/providers/mock_image_provider.py` | 95 | mock image provider |
| `src/film_pipeline/app/mock_responses.py` | 435 | canned agent payloads (production `app` package) |
| `tests/conftest.py` | 166 | root isolation + production-separation guard |
| `tests/e2e/conftest.py` | 195 | e2e fixtures + `invoke_tool` |
| `tests/smoke/conftest.py` | 18 | e2e fixture re-export |
| `tests/unit/mcp/tools/conftest.py` | 34 | runtime-mode reset only |

Supporting files read (whole or targeted): `src/film_pipeline/providers/base.py`, `src/film_pipeline/providers/factory.py`,
`src/film_pipeline/providers/__init__.py`, `src/film_pipeline/providers/pricing.py`, `src/film_pipeline/app/_provider_seeds.py`, `src/film_pipeline/app/runtime.py`,
`src/film_pipeline/app/_persistence.py`, `src/film_pipeline/app/safety.py`, `src/film_pipeline/app/logging_setup.py`, `src/film_pipeline/cli/driver.py`,
`src/film_pipeline/agents/runner.py`, `src/film_pipeline/agents/mvp/__init__.py`, all 11 `src/film_pipeline/agents/impl/*.py` consumers,
`src/film_pipeline/agents/prompt_templates/registry.py`, `src/film_pipeline/agents/prompt_templates/defaults/spine.py`,
`src/film_pipeline/graph/services.py`, `src/film_pipeline/artifacts/store.py`, `src/film_pipeline/artifacts/storage.py`, `src/film_pipeline/artifacts/registry.py`,
`src/film_pipeline/checkpoints/git_backend.py`, `tests/unit/checkpoints/test_checkpoints.py`,
`tests/unit/agents/test_mvp_invariants.py`, `tests/unit/graph/test_startup_boundaries.py`,
`tests/unit/graph/test_shot_bible_structure.py`, `tests/unit/artifacts/test_storage.py`,
`tests/unit/artifacts/test_storage_boundary.py`, `tests/unit/providers/test_mock_provider.py`,
`tests/unit/generation/test_executor.py`, `tests/unit/mcp/tools/test_generation.py`,
`tests/unit/mcp/tools/test_reference_generation.py`, `tests/integration/test_generation_mcp.py`,
`tests/integration/test_artifact_spine.py`, `pyproject.toml`, `AGENTS.md`.

Out-of-scope but named for coverage (no findings raised here; ownership belongs to other clusters):
`tests/unit/**` non-mock helper construction, `tests/e2e/test_scenario_*.py` assertions,
`tests/smoke/test_*.py` workflows, `scripts/`, `profiles/`.

### Verdicts on the questions posed to this cluster

1. **Independent mock-provider implementations:** **2 shipped classes, one shared contract**
   (`MockVideoProvider` `src/film_pipeline/providers/mock_provider.py:45`, `MockImageProvider`
   `src/film_pipeline/providers/mock_image_provider.py:38`, both subclassing `BaseProviderAdapter`
   `src/film_pipeline/providers/base.py:39`), **plus ≥3 test-local doubles that bypass that contract**
   (`mock.MagicMock` at `tests/unit/mcp/tools/test_reference_generation.py:80-82`,
   `_FakeAdapter` at `tests/unit/mcp/tools/test_reference_generation_helpers.py:140`,
   `_ImageAdapter`/`_VideoAdapter` at `.../test_reference_generation_helpers.py:155-158`).
   The shared *base* is genuinely single-owner; the mock **registry entries** are not (F-TEST-07).
2. **Independent "mock agent/model response" sources:** **three** — `src/film_pipeline/app/mock_responses.py:97`
   (production), `src/film_pipeline/testing/mock_model.py:13` (shipped double), `src/film_pipeline/agents/runner.py:152-160`
   (in-runner generic fallback). The canned payloads **already diverge** from the real schema
   sources (`PromptTemplate.output_format` / `output_schema_ref`, agent `execute()` return keys):
   three wrapper divergences on the canned payloads (F-TEST-01, the third added after verification).
   The third source (`MockModelAdapter`) is dead-wired; the finding that once grouped these sources
   (F-TEST-02) is **withdrawn** for lack of a valid drift proof — see the hypotheses section.
3. **Fixture construction:** **partially centralized.** Only e2e (and smoke, by re-export) has a
   runtime/store fixture. Unit and integration re-implement construction inline:
   `grep -rn "ArtifactStore(" --include='*.py' tests | wc -l` = **64 in 17 files**;
   `grep -rn "StudioRuntime(" --include='*.py' tests | wc -l` = **95 in 30 files**;
   `grep -rn "PromptRunner()" --include='*.py' tests | wc -l` = **11**. There is **no**
   `tests/integration/conftest.py` (`find tests -name conftest.py` → root, e2e, smoke,
   `tests/unit/mcp/tools`). See the fixture table and F-TEST-05.
4. **Production/test separation guard:** `_production_roots_untouched` (`tests/conftest.py:111-140`)
   watches three fixed roots and compares path→size only; it is one of **three** overlapping
   enforcement sites with different scopes and **has no test of its own** (F-TEST-06). Separately,
   `src/film_pipeline/testing` **is shipped** — verified not only from `pyproject.toml:58-59` but from
   the built artifact: `dist/film_pipeline-0.4.0-py3-none-any.whl` contains all six
   `film_pipeline/testing/*.py` members at byte sizes identical to HEAD (e.g. `src/film_pipeline/testing/in_memory_git.py` 7630,
   `src/film_pipeline/testing/storage.py` 760) — while `pyproject.toml:95-98` excludes `*/testing/*` from coverage
   (see *Candidate module boundary*; prior art `audit/14:279-283`).
5. **`src/film_pipeline/app/mock_responses.py` is production code holding demo film data** that is simultaneously the
   shared test fixture (**31** occurrences across **13** test files;
   `grep -rn "default_mock_responses" --include='*.py' tests | wc -l` = 31). It is the *default*
   server payload (`src/film_pipeline/app/runtime.py:456` defaults `FILM_PIPELINE_MCP_MODE` to `"mock"`), so this is a
   shipped product surface, not only test data — but it is not bound to any real output schema
   (F-TEST-01). Prior art: **B-F4** (`documentation/architecture-review.md:107`) already moved this
   blob out of `testing/` into `app/`; this audit re-examines the *data*, not the import edge.

---

## Test-double inventory

`contract` = the type/interface the double claims to satisfy; `duplicates` = other places that
independently encode the same mock behavior.

| Double | Home (`file:line`) | Contract | Duplicates / notes |
|---|---|---|---|
| `MockVideoProvider` | `src/film_pipeline/providers/mock_provider.py:45` | `BaseProviderAdapter` (`src/film_pipeline/providers/base.py:39`), all 7 methods | Registry entry re-declared at `tests/e2e/conftest.py:69-81`, `tests/unit/providers/test_mock_provider.py:22-44`, `tests/unit/generation/test_executor.py:43-51`; production copy built by `src/film_pipeline/providers/factory.py:40-41` |
| `MockImageProvider` | `src/film_pipeline/providers/mock_image_provider.py:38` | `BaseProviderAdapter`; does not override `cancel` (inherits `src/film_pipeline/providers/base.py:90-93`) | Replaced by `mock.MagicMock` at `tests/unit/mcp/tools/test_reference_generation.py:80-82`; `_FakeAdapter`/`_ImageAdapter` at `tests/unit/mcp/tools/test_reference_generation_helpers.py:140,155-158` |
| `ScenarioStep` | `src/film_pipeline/providers/mock_provider.py:32` | plain frozen dataclass, no protocol | Exported from the **public** provider API (`src/film_pipeline/providers/__init__.py:13,25`) although only tests define scenarios |
| `ALL_SCENARIOS` (13 scenarios) | `src/film_pipeline/testing/scenarios.py:122-136` | `dict[str, list[ScenarioStep]]` | **Unused registry**: only `HAPPY_PATH_SEQUENTIAL_CHAIN` is referenced, by `tests/unit/test_testing_utils.py:106-108`; no src or test consumer of `ALL_SCENARIOS` |
| `MockModelAdapter` | `src/film_pipeline/testing/mock_model.py:13` | duck-typed `.register/.call/.agent_response/.validator_response` | Parallel to `src/film_pipeline/app/mock_responses.py:97` and `src/film_pipeline/agents/runner.py:152-160`; **dead-wired** — requested at `tests/e2e/conftest.py:124`, never used in the fixture body (`:132-138`) |
| `MockHumanActor` / `DecisionProfile` | `src/film_pipeline/testing/mock_human.py:20` / `:9` | duck-typed `.decide(phase, review_type, summary)` | **Dead fixture**: defined at `tests/e2e/conftest.py:37`, re-exported at `tests/smoke/conftest.py:12`, and requested as a fixture parameter by no test. *(Corrected after verification: `grep -rn "mock_human" --include='*.py' tests` returns **9 lines across 5 files** — the definition (`tests/e2e/conftest.py:37`) with its import (`:30`), the re-export (`tests/smoke/conftest.py:12`), `tests/unit/test_testing_utils.py:7,68` and `tests/unit/testing/test_mock_actors.py:7,54` (imports that instantiate `MockHumanActor` directly and assert the `actor_type` metadata), and `tests/unit/test_mcp.py:206,207` (synthetic `actor_type="mock_human"` envelopes) — the fixture itself is still unrequested.)* |
| `default_mock_responses()` | `src/film_pipeline/app/mock_responses.py:97` | `dict[str, dict[str, Any]]` — **no typed contract** | Real shape owners are `PromptTemplate.output_format`/`output_schema_ref` (`src/film_pipeline/agents/prompt_templates/registry.py:30`) and the agent `execute()` returns; 11 keys, 435 lines |
| `InMemoryGitBackend` | `src/film_pipeline/testing/in_memory_git.py:60` | subclasses `GitBackend` (`src/film_pipeline/checkpoints/git_backend.py:15`) but no parity test | Installed suite-wide at `tests/conftest.py:75-78`; the real backend is contracted separately at `tests/unit/checkpoints/test_checkpoints.py:20-33` |
| `sandbox_store_root` / `make_store` | `src/film_pipeline/testing/storage.py:15,20` | `init_storage_root(..., profile=PROFILE_SANDBOX)` + `ArtifactStore` | Bypassed by 64 direct `ArtifactStore(root=...)` sites (17 files); `grep -rln "make_store\|sandbox_store_root" --include='*.py' src tests | wc -l` = 7 files |
| `FakeArtifactStore` (×2, same name) | `tests/unit/graph/test_context_packets.py:12`; `tests/unit/graph/test_qc_subgraph.py:43` | undeclared `GraphServices.artifact_store` seam (`src/film_pipeline/graph/services.py:63`) | Constructors already disagree: `FakeArtifactStore(artifacts)` + `load_ref` vs `FakeArtifactStore()` + `list_artifacts` |
| `FakeRuntime` / `_FakeRuntime` (×5) | `tests/unit/app/test_app_ops.py:160,188,211`; `tests/unit/mcp/tools/test_reference_generation_helpers.py:143,160` | undeclared `StudioRuntime` seam | `grep -rn "class .*Fake" --include='*.py' tests | wc -l` = 23 local fakes, all contract-less |
| `_generic_mock_fallback` | `src/film_pipeline/agents/runner.py:152-160` | in-production fallback returning `{"status": "ok", ...}` | Third response source; hit by 11 no-arg `PromptRunner()` sites in tests, e.g. `tests/integration/test_generation_mcp.py:31` |

---

## Fixture construction sites

| Tier | How it builds storage / runtime | Centralized? |
|---|---|---|
| **root** `tests/conftest.py` | Autouse `_isolated_runtime_root` redirects `FILM_PIPELINE_RUNTIME_ROOT` / `FILM_PIPELINE_STORAGE_ROOT` to `tmp_path` (`:29-30`), deletes `FILM_PIPELINE_PERSIST_STATE`/`FILM_PIPELINE_MCP_MODE` (`:31,37`), resets singletons (`:43-44`). One `store_root` fixture delegating to `testing.storage.sandbox_store_root` (`:54-59`). **No runtime fixture.** | Partial — env policy only |
| **unit (general)** | Inline per test module: `ArtifactStore(root=tmp_path / "artifacts")` + `StudioRuntime(runtime_root=tmp_path / "runtime")` + manual `services` assignment, e.g. `tests/unit/mcp/tools/test_generation.py:42-51`, `tests/unit/graph/test_services.py:37,49`, `tests/unit/app/test_runtime.py:57-60`. 64 store sites / 95 runtime sites. | **No** |
| **unit/mcp/tools** | `tests/unit/mcp/tools/conftest.py:22-33` only force-resets the runtime mode and re-binds `get_runtime`; the tests still build runtimes inline (as above). | **No** |
| **integration** | **No `conftest.py`** (`find tests -name conftest.py` lists only root/e2e/smoke/`unit/mcp/tools`). Every test/fixture builds inline: `tests/integration/test_generation_mcp.py:30-44` (`PromptRunner()` at `:31`, `GraphServices` at `:34`, `ArtifactStore(root=tmp_path/"artifacts")` at `:36`, `StudioRuntime(runtime_root=...)` at `:39`), `tests/integration/test_artifact_spine.py:22-26`. 4 files in `tests/integration/` + 2 subdirs. | **No** |
| **e2e** | `tests/e2e/conftest.py:122-169`: `graph_services` builds `PromptRunner(mock_responses=default_mock_responses())` (`:132`) + `ArtifactStore(root=tmp_path / "artifacts")` (`:135`); `studio_runtime` builds `StudioRuntime(runtime_root=tmp_path/"e2e-runtime")` (`:155`) then overwrites `rt.services` (`:156`) and hand-writes health (`:158-161`). | Yes for this tier, but **bypasses** `GraphServices._artifact_store` / `_build_services_for_mode` |
| **smoke** | `tests/smoke/conftest.py:4-17` re-exports 13 e2e fixtures by name; `tests/smoke/test_operator_workflow.py:21` consumes `studio_runtime`. | Yes, via e2e |

---

## Findings

### F-TEST-01 — Canned agent payloads live in the production composition package and are bound to no output schema; three already contradict the real prompt-template or agent-impl wrapper

- **Class:** O8 (missing contract) + O1
- **Severity:** High (impact 3 × drift 4 = 12) — *downgraded from 15 after verification*
- **Concern:** the normative shape of a mock-mode agent response — which keys wrap the artifact — has no single owner and is not checked against the real agent output contract.
- **De-facto owners:**
  - `src/film_pipeline/app/mock_responses.py:97` — produces the payloads — `"def default_mock_responses() -> dict[str, dict[str, Any]]:"`
  - `src/film_pipeline/agents/prompt_templates/defaults/spine.py:306` — the real `treatment-agent` template mandates a `development` wrapper — `'  "development": {\n'`
  - `src/film_pipeline/app/mock_responses.py:143` — the canned response omits that wrapper — `"treatment": {`
  - `src/film_pipeline/agents/prompt_templates/defaults/spine.py:159` — the real `intake-classifier-agent` template mandates **flat** keys — `'  "identity": {\n'`
  - `src/film_pipeline/app/mock_responses.py:101` — the canned response wraps them anyway — `"intake": {`
  - `src/film_pipeline/agents/impl/screenwriter_agent.py:54` — the `screenwriter-agent` impl prefers a wrapper no producer writes — `'data = model_output.get("script_output", model_output)'`
  - `src/film_pipeline/agents/runner.py:365-367` — the production runner prefers the canned payload over the real adapter — `"mock_response = self._find_mock_response(prompt.core_task, agent_id=agent_id)\n        if mock_response is not None:\n            return mock_response"`
- **Drift proof:** *existing divergence*, three ways.
  - `treatment-agent`: template (`src/film_pipeline/agents/prompt_templates/defaults/spine.py:303-327`) → `{"development": {"treatment": …, "scenes": […]}}`; canned (`src/film_pipeline/app/mock_responses.py:142-175`) → `{"treatment": …, "scenes": […]}`. Tolerated only by the fallback at `src/film_pipeline/agents/impl/development_agent.py:76` — `'data = model_output.get("development", model_output)'`.
  - `intake-classifier-agent`: template (`src/film_pipeline/agents/prompt_templates/defaults/spine.py:156-177`) is flat (`identity`, `film_type`, …); canned (`src/film_pipeline/app/mock_responses.py:100-117`) adds an `intake` wrapper, tolerated only by `src/film_pipeline/agents/impl/intake_agent.py:35` — `'data = model_output.get("intake", model_output)'`.
  - `screenwriter-agent` *(added after verification)*: the impl prefers `script_output` (`src/film_pipeline/agents/impl/screenwriter_agent.py:54`), but the template declares flat `"story_bible"` + `"script"` (`src/film_pipeline/agents/prompt_templates/defaults/spine.py:407-410` — `'"Respond with valid JSON containing a story_bible and script:\n{\n'`) and the canned payload is likewise flat (`src/film_pipeline/app/mock_responses.py:176-177`). The only producer of the wrapper is a unit test (`tests/unit/agents/test_impl_agents.py:224,248`); `grep -rn "script_output" --include='*.py' src tests` returns **4** lines — the impl line, those two fixtures, and `tests/integration/test_artifact_spine.py:133` (a test *name* that contains the token, not a payload).
  - **What *is* guarded** (corrected after verification): the canned payloads are exercised end-to-end through the real agents and nodes — `tests/unit/graph/test_scope_contract_node_integration.py:90-114` drives `intake_node` → `development_node` → `script_node` over `GraphServices.for_mock_runtime(mock_responses=default_mock_responses())` (`:37`) and asserts `blocking == []` / `approved is True` (`:105-106`, `:113-114`); `tests/e2e/test_scenario_01_happy_path.py:75-93` drives phases through MCP tools and asserts artifacts and checkpoints appear. A payload that stops *parsing* therefore fails tests. **What is not guarded is template↔canned wrapper agreement**: no test reads `PromptTemplate.output_format` to compare it with a payload — the only test references to `output_format` are synthetic-template constructor arguments (`tests/unit/agents/test_prompt_template_registry.py:22`, `tests/unit/agents/test_runner.py:44`).
  - Mutation *(rewritten after verification — the previous mutation was backwards)*: change the wrapper declared at `src/film_pipeline/agents/prompt_templates/defaults/spine.py:306` (or add a `development` key to the canned payload at `src/film_pipeline/app/mock_responses.py:142`). Nothing fails: the agreement between `PromptTemplate.output_format` and the canned payload is unpinned, and both agents absorb the mismatch through `.get(<wrapper>, model_output)`. Deleting that fallback instead would break the *real* path, which is why the fallback is load-bearing rather than a guard.
  - The only guard over the *set* of canned payloads checks key presence and non-emptiness, not shape — `tests/unit/agents/test_mvp_invariants.py:65-69` — and it covers the **forward direction only** (contract → impl/template/profile/mock), as already recorded in `documentation/reviews/arch-lens-flexibility.md:16` and elaborated at `:37`.
  - Additional unbound naming: the canned shot artifact key is `shot_matrix` (`src/film_pipeline/app/mock_responses.py:341`, matched by `src/film_pipeline/agents/impl/shot_bible_agent.py:48`), while the agent contract declares `output_artifacts=["shot_bible", "master_film_matrix"]` (`src/film_pipeline/agents/mvp/__init__.py:120`) and the artifact registry registers **both** kinds with one renderer (`src/film_pipeline/artifacts/registry.py:157,192`).
- **Reproduce:**
  ```bash
  grep -n '"development"' src/film_pipeline/agents/prompt_templates/defaults/spine.py
  grep -n '"intake"' src/film_pipeline/app/mock_responses.py
  grep -rn "script_output" --include='*.py' src tests    # 4 lines: impl + 2 fixtures + 1 test name (:133)
  grep -rn "default_mock_responses" --include='*.py' tests | wc -l    # 31
  grep -rln "app.mock_responses import default_mock_responses" --include='*.py' tests | wc -l  # 13
  ```
- **Blast radius:** mock mode is the default server mode (`src/film_pipeline/app/runtime.py:456` — `'return _normalize_server_mode(os.getenv("FILM_PIPELINE_MCP_MODE", "mock"))'`). The three wrapper mismatches are currently *normalized away* by the tolerant fallbacks, so no wrong output reaches a human today (this is why drift is 4, not 5); what is missing is any test that would fail if the template and the canned payload disagreed. `src/film_pipeline/graph/services.py:69-91`, `src/film_pipeline/cli/driver.py:73-78`.
- **Candidate owner module:** `testing.doubles` (or `testing.mock_responses`) — the single normative owner of canned agent payloads, with payloads typed against the artifact schemas named by each template's `output_schema_ref`.
- **Extraction sketch:** move `default_mock_responses` behind the harness contract; declare each canned payload as a Pydantic fixture keyed by `agent_id`; make the wrapper convention per agent explicit and derived from the template/importer (not hand-written) — the three disagreements are `development` (`src/film_pipeline/agents/impl/development_agent.py:76`), `intake` (`src/film_pipeline/agents/impl/intake_agent.py:35`) and `script_output` (`src/film_pipeline/agents/impl/screenwriter_agent.py:54`); add a guard test that, for every `MVP_AGENTS` entry, asserts the wrapper key named by the agent impl's `execute()` is the same one the template's `output_format` declares and that the canned payload carries it (the existing end-to-end node tests already prove the payload parses). Production default wiring keeps calling it (`src/film_pipeline/app/runtime.py:438`, `src/film_pipeline/cli/driver.py:73`) or receives it by DI.
- **Prior art:** **B-F4** (`documentation/architecture-review.md:107`, `documentation/roadmap-execution/phase-01-state-safety-guardrails-plan.md:160-176`) relocated this blob from `testing/fixtures/` into `src/film_pipeline/app/mock_responses.py` and added the import-edge guard. **A7 citation added after verification:** `documentation/reviews/arch-lens-flexibility.md:16` already records the mock-response fixture as part of the "new agent" extension cost and states that `tests/unit/agents/test_mvp_invariants.py` "covers forward direction only"; `:37` names the reverse gaps. What is new here: the payloads are still schema-unbound and **three of eleven** now diverge from the real template/impl wrapper convention.

### F-TEST-02 — *withdrawn during the fix loop* — see "Withdrawn findings / unverified hypotheses"

The original validator-shape drift proof was a false equivalence, and the replacement drift proof
(fallback duplication) was **also disproved** on re-check: both fallbacks are pinned by tests
(`tests/unit/agents/test_runner.py:48-57`, `tests/unit/test_testing_utils.py:80-85`,
`tests/unit/testing/test_mock_actors.py:59-64`), so no partial edit passes the suite. What remains is
dead code and incompleteness, which §1.3 excludes from ownership findings. The evidence and the
withdrawal reasoning are preserved verbatim in the section below so the ID stays traceable.

### F-TEST-03 — The session-wide git double replaces the only writer of checkpoint state and has no parity test against the real backend

- **Class:** O2 (duplicated invariant enforcement)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** the `GitBackend` contract's behavior for the whole suite.
- **De-facto owners:**
  - `tests/conftest.py:75-78` — installs the double for the entire session — `'from film_pipeline.testing.in_memory_git import InMemoryGitBackend\n\n    previous = get_git_backend_type()\n    set_git_backend_type(InMemoryGitBackend)'`
  - `src/film_pipeline/testing/in_memory_git.py:137-159` — re-implements commit semantics by hand — `'state.commits.append(_Commit(hash=digest, message=message, tree=tree))'`
  - `src/film_pipeline/checkpoints/git_backend.py:37-44` — the real implementation being mirrored — `'self._run("commit", "-m", message, "--allow-empty")\n        return self._run("rev-parse", "HEAD")'`
- **Drift proof:** `grep -rn "InMemoryGitBackend" --include='*.py' src tests` returns only its own module and `tests/conftest.py:75,78` — no test constructs it. The real backend is contracted directly (`tests/unit/checkpoints/test_checkpoints.py:22` — `'git = GitBackend.init_temp(Path(d))'`, covering commit/tag/branch/rollback and `is_clean`), so both backends are tested — but never against the **same** assertions. *(Corrected after verification: `list_files` and `restore_files` have **zero** direct references in that file — `grep -c "list_files\|restore_files" tests/unit/checkpoints/test_checkpoints.py` → `0` — and are exercised at most indirectly through `RollbackManager` at `src/film_pipeline/checkpoints/rollback.py:74,121`.)* Mutation: make `RollbackManager` depend on a path that is not present in the snapshot; the double's `restore_files` silently filters it (`src/film_pipeline/testing/in_memory_git.py:120-121` — `'selected = tree if only is None else {p: tree[p] for p in only if p in tree}'`) whereas the real backend raises (`src/film_pipeline/checkpoints/git_backend.py:57-59` — `'self._run("checkout", commit, "--", *files)'` with `_run` raising on non-zero). Every integration/e2e/unit test that touches rollback runs the double, so the divergent branch passes the suite.
- **Reproduce:**
  ```bash
  grep -rn "InMemoryGitBackend" --include='*.py' src tests
  grep -rn "class .*Fake\|class .*Stub" --include='*.py' tests | wc -l   # 23, none for GitBackend
  ```
- **Blast radius:** `checkpoints` (rollback/resume), `src/film_pipeline/app/_persistence.py` (backend injection at `:36`), every project-creating test (~30 files build `StudioRuntime`); a rollback regression can ship while the suite is green.
- **Candidate owner module:** `testing.doubles.git` — owns the double *and* the parity suite that runs both `GitBackend` and `InMemoryGitBackend` through one shared contract fixture.
- **Extraction sketch:** parameterize `tests/unit/checkpoints/test_checkpoints.py` over `[GitBackend, InMemoryGitBackend]` (the real one already runs there); where real-git-only semantics exist, add an explicit `pytest.skip` with a reason so divergence is enumerated rather than silent; move `InMemoryGitBackend` contract notes out of the docstring (`src/film_pipeline/testing/in_memory_git.py:1-21`) into the parity test.
- **Prior art:** New. `audit/14:271` records only that `src/film_pipeline/testing/in_memory_git.py` imports `checkpoints.git_backend`.

### F-TEST-04 — `make_store`/`sandbox_store_root` is bypassed by 64 direct store constructions, and the sandbox marker it writes is inert

- **Class:** O1 (duplicated normative model)
- **Severity:** High (impact 2 × drift 5 = 10)
- **Concern:** what a *test* storage root is (marker profile, initialization path).
- **De-facto owners:**
  - `src/film_pipeline/testing/storage.py:17` — the declared test-root builder, sandbox-profiled — `'return init_storage_root(path, profile=PROFILE_SANDBOX)'`
  - `src/film_pipeline/artifacts/store.py:60-61` — every direct construction silently stamps **production** — `'def __init__(self, root: Path) -> None:\n        self._root = ensure_storage_root(root)'` with `src/film_pipeline/artifacts/storage.py:116` — `'def init_storage_root(root: Path, *, profile: str = PROFILE_PRODUCTION) -> Path:'`
  - `tests/e2e/conftest.py:135` — the e2e fixture takes the direct path — `'artifact_store=ArtifactStore(root=tmp_path / "artifacts"),'`
  - `src/film_pipeline/graph/services.py:48-49` — production *does* choose the profile — `'profile = PROFILE_SANDBOX if os.getenv("FILM_PIPELINE_NO_PERSIST") else PROFILE_PRODUCTION\n    return ArtifactStore(root=ensure_storage_root(root, profile=profile))'`
- **Drift proof:** 64 direct `ArtifactStore(root=…)` sites in 17 test files produce a `"production"`-profiled marker; the 48 `make_store`/`sandbox_store_root` occurrences across 7 files (`--include='*.py' src tests`) produce `"sandbox"` — 45 occurrences in 6 test files plus 3 lines in `src/film_pipeline/testing/storage.py:15,20,22` (the two definitions and their internal call, not test call sites). No production code reads the *profile* field — `grep -rn "read_marker" --include='*.py' src` returns **2** lines, the definition (`src/film_pipeline/artifacts/storage.py:97`) and one call site (`:138`, a layout-version check that never inspects `profile`) — so the sandbox/production distinction is write-only. Mutation: change `_artifact_store`'s profile branch at `src/film_pipeline/graph/services.py:48` (or `ensure_storage_root`'s default); the e2e fixture (direct `ArtifactStore`) never observes it, and the only sandbox assertion pins the helper to itself (`tests/unit/artifacts/test_storage.py:163-169`; the quoted assertion is at `:169` — `'assert marker.profile == "sandbox"'`).
- **Reproduce:**
  ```bash
  grep -rn "ArtifactStore(" --include='*.py' tests | wc -l                    # 64
  grep -rln "ArtifactStore(" --include='*.py' tests | wc -l                   # 17
  grep -rn "make_store\|sandbox_store_root" --include='*.py' src tests | wc -l   # 48 (45 tests + 3 src)
  grep -rln "make_store\|sandbox_store_root" --include='*.py' src tests | wc -l  # 7 files (6 tests + 1 src)
  grep -rn "read_marker" --include='*.py' src   # 2 lines: def :97 + call :138 (neither reads profile)
  ```
- **Blast radius:** `artifacts.storage`, `graph.services`, every test tier; the test harness's only marker-level proof of "this is not production storage" is not applied where 64 tests build stores, and no consumer would notice if the marker changed meaning.
- **Candidate owner module:** `testing.harness` — owns the single test-root/store factory; `ArtifactStore` takes the profile explicitly so no caller can silently default to production.
- **Extraction sketch:** add `profile` to `ArtifactStore.__init__` (or require an already-marked root, refusing unmarked ones in tests); replace the 64 direct sites with the harness factory; guard test that no `tests/**` module constructs `ArtifactStore(`/`StudioRuntime(` directly (AST sweep, same style as `tests/unit/graph/test_startup_boundaries.py:26-42`).
- **Prior art:** `documentation/storage-upgrade-plan.md:77,90-91` defines `profile: "production"|"sandbox"` in the marker; `audit/14:269-270` notes the import edge. New here: the marker is unconsumed, and the harness helper is bypassed at 64 sites.

### F-TEST-05 — Fixture construction is re-implemented per tier; the e2e fixture bypasses the production composition root it is supposed to stand in for

- **Class:** O5 (policy-by-branch: "how a test runtime is built" re-derived at every call site)
- **Severity:** Medium (impact 2 × drift 3 = 6)
- **Concern:** one construction policy for test storage/runtime across unit, integration, e2e, smoke.
- **De-facto owners:**
  - `tests/e2e/conftest.py:155-156` — the e2e fixture replaces the runtime's services by hand — `'rt = StudioRuntime(runtime_root=tmp_path / "e2e-runtime")\n    rt.services = graph_services'`
  - `src/film_pipeline/app/runtime.py:433-443` — the real composition root it bypasses — `'def _build_services_for_mode(server_mode: str, *, artifacts_root: Path | None = None) -> GraphServices:'`
  - `tests/integration/test_generation_mcp.py:31-36` — the integration tier re-implements the same wiring with no fixture — `'runner = PromptRunner()\n    registry = AgentRegistry()\n    registry.register_many(MVP_AGENTS)\n    services = GraphServices(\n        prompt_runner=runner,\n        artifact_store=ArtifactStore(root=tmp_path / "artifacts"),'`
  - `tests/smoke/conftest.py:4-17` — smoke only re-exports e2e fixtures — `'from tests.e2e.conftest import (  # noqa: F401'`
- **Drift proof:** mutation — add required wiring to `StudioRuntime.__init__`/`_build_services_for_mode` (e.g. seed `ModelRouter`, provider registry, health). The e2e and integration fixtures assign `rt.services`/`rt.provider_health` directly (`tests/e2e/conftest.py:156,158-161`) and never call the composition root, so they keep the old shape and no test fails; only the unit tests that do call `StudioRuntime(server_mode="mock")` (`tests/unit/app/test_runtime.py:19`) observe the change. Counts: 95 `StudioRuntime(` sites in 30 files, 64 `ArtifactStore(` sites in 17 files, 11 no-arg `PromptRunner()` sites, and **no** `tests/integration/conftest.py`.
- **Reproduce:**
  ```bash
  find tests -name conftest.py
  grep -rn "StudioRuntime(" --include='*.py' tests | wc -l   # 95
  grep -rln "StudioRuntime(" --include='*.py' tests | wc -l  # 30 files
  grep -rn 'tmp_path / "runtime"' --include='*.py' tests | wc -l   # 102
  ```
- **Blast radius:** all four test tiers; a composition-root change is exercised by one tier only, so e2e "passing" is weak evidence that the shipped wiring works.
- **Candidate owner module:** `testing.harness` — one `make_runtime(...)` / `make_services(...)` factory per runtime mode, consumed by all tiers; e2e keeps only scenario-specific overrides.
- **Extraction sketch:** introduce `tests/harness.py` (or `testing.harness`) with `mock_runtime(tmp_path, mode=...)`; port e2e and integration fixtures first (fewest sites), then the 30 unit files; delete the dead `mock_model` parameter (`tests/e2e/conftest.py:124`) as part of the port; guard test that `tests/integration/` has a conftest.
- **Prior art:** New.

### F-TEST-06 — The production-separation invariant is enforced in three places with different scopes; the primary guard has no test and cannot see same-size writes

- **Class:** O2 (duplicated invariant enforcement)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** "a test run must not write into production storage" — one policy, three partial enforcement sites, no owner.
- **De-facto owners:**
  - `tests/conftest.py:121-125` — the snapshot guard watches exactly three roots — `'watched = {\n        "home-film-pipeline": Path.home() / ".film-pipeline",\n        "cwd-projects": Path("projects").resolve(),\n        "cwd-film-pipeline-run": Path(".film-pipeline-run").resolve(),\n    }'`
  - `tests/conftest.py:29-31` — per-test env redirection, the actual write-prevention mechanism — `'monkeypatch.setenv("FILM_PIPELINE_RUNTIME_ROOT", str(tmp_path / "runtime-root"))\n    monkeypatch.setenv("FILM_PIPELINE_STORAGE_ROOT", str(tmp_path / "storage-root"))\n    monkeypatch.delenv("FILM_PIPELINE_PERSIST_STATE", raising=False)'`
  - `tests/conftest.py:98-100` — session-scoped redirect written with raw `os.environ` — `'os.environ["FILM_PIPELINE_NO_PERSIST"] = "1"\n    session_root = tmp_path_factory.mktemp("film-pipeline")\n    os.environ["FILM_PIPELINE_STORAGE_ROOT"] = str(session_root / "storage")'`
- **Drift proof:** no test references the guard — `grep -rn "_production_roots_untouched" --include='*.py' tests` returns only its definition (`:112`) — so deleting `tests/conftest.py:111-140` leaves the suite green and the separation policy unenforced beyond env redirection. The comparison is path→size only: `tests/conftest.py:136-138` — `'added = sorted(set(new) - set(old))[:10]'` / `'resized = sorted(key for key in set(old) & set(new) if old[key] != new[key])[:10]'`; an in-place rewrite of a real artifact with identical byte length is invisible. `_snapshot_tree` also skips every `logs` component and `*.log` (`tests/conftest.py:160-161` — `'if "logs" in parts or relative.endswith(".log"):\n            continue'`), which is intentional (`:118-120`) but means the file-handler write path (`src/film_pipeline/app/logging_setup.py:93` — `'expected_log = (log_dir / "film_pipeline.log").resolve()'`) is unchecked.
- **Reproduce:**
  ```bash
  grep -rn "_production_roots_untouched" --include='*.py' tests
  grep -rn "_isolated_runtime_root\|_clean_production_state_stores" --include='*.py' tests
  ```
- **Blast radius:** `tests/conftest.py` consumers = the whole suite; `artifacts.storage`, `src/film_pipeline/app/safety.py:75-79` (delete safety zone derives from the same resolved root).
- **Candidate owner module:** `testing.safety` — one owner for the separation invariant, exposing a snapshot/baseline check plus a self-test.
- **Extraction sketch:** keep one guard; add a self-test that fails when the guard is deregistered (session fixture set assertion) and a unit test that feeds `_snapshot_tree` a same-size rewrite and asserts detection (hash or content digest instead of size); route all three env writes through `monkeypatch` so no site can leak into the worker env (`src/film_pipeline/app/services/operator.py:191` — `'os.environ["FILM_PIPELINE_MCP_MODE"] = mode'` — is the production writer whose leak `tests/conftest.py:37` compensates for).
- **Prior art:** `documentation/storage-upgrade-plan.md:288-295` (P1 roots/marker/separation) is the precedent; new here: the guard's blind spots and absence of self-test.

### F-TEST-07 — Mock-provider registry entries are re-derived in five places and already disagree

- **Class:** O1 (duplicated normative model)
- **Severity:** High (impact 2 × drift 5 = 10) — CONFIRMED; count corrected after verification
- **Concern:** the `ProviderRegistryEntry` (capabilities, models, cost) of the mock providers.
- **De-facto owners:**
  - `src/film_pipeline/providers/factory.py:96-103` — production's built entry for `mock-video-provider` falls through to the generic branch — `'return ProviderCapabilities(\n        text_to_video=True,\n        image_to_video=True,\n        return_last_frame=True,\n        max_duration_seconds=30,\n        aspect_ratios=["16:9"],'`
  - `tests/unit/providers/test_mock_provider.py:27-35` — the unit-tier entry declares more — `'capabilities=ProviderCapabilities(\n            text_to_video=True,\n            image_to_video=True,\n            return_last_frame=True,\n            max_duration_seconds=30,\n            aspect_ratios=["16:9", "9:16"],\n            supports_audio=True,\n            supports_seed=True,'`
  - `tests/e2e/conftest.py:69-81` — the e2e entry — `'entry = ProviderRegistryEntry(\n        provider_id="mock-video-provider",'`
  - `tests/unit/generation/test_executor.py:43-51` — a fourth capability literal — `'capabilities=ProviderCapabilities(\n            text_to_video=True,\n            image_to_video=True,\n            return_last_frame=True,\n            max_duration_seconds=30,\n            aspect_ratios=["16:9"],\n            supports_audio=True,\n            supports_seed=True,'`
  - `tests/unit/test_schemas.py:946-955` — a fifth hand-built entry for the same id *(added after verification)* — `'e = ProviderRegistryEntry(\n        provider_id="mock-video-provider",'` with `capabilities=ProviderCapabilities(text_to_video=True, return_last_frame=True, max_duration_seconds=30)` (`:950-954`) and `failure_modes=["timeout", "quota"]` (`:956`)
- **Drift proof:** *existing divergence* — for the same `provider_id`, the factory entry has `aspect_ratios=["16:9"]`, `supports_audio=False`, `supports_seed=False`, while `tests/unit/providers/test_mock_provider.py:31-34` has `["16:9","9:16"]`, `supports_audio=True`, `supports_seed=True` and adds `failure_modes` (`:36-43`); `tests/unit/test_schemas.py:950-954` declares neither audio nor seed nor aspect-ratio variation. Nothing compares them; the production path used by `src/film_pipeline/app/_provider_seeds.py:56-65` builds via the factory (`:64` — `'build_provider_adapter(provider_id, provider_type=provider_type)'`), so a capability added for tests never reaches mock-mode runtime. Impact is currently **latent** because no consumer reads the divergent flags: `grep -rn "supports_audio" --include='*.py' src` returns only the schema default (`src/film_pipeline/schemas/registries/provider_registry.py:19`) — *(corrected after verification: `src/film_pipeline/providers/factory.py` contains **no** `supports_audio` token — `grep -n "supports_audio" src/film_pipeline/providers/factory.py` → no match)*. The same capability literal is also duplicated for a different id at `tests/unit/generation/test_executor_download_failed.py:41-50` (`provider_id="download-error-provider"`), so the duplication is a pattern, not a one-off.
- **Reproduce:**
  ```bash
  grep -rn 'provider_id="mock-video-provider"' --include='*.py' src tests   # 8 hits; 4 are entry sites (the 5th, src/film_pipeline/providers/factory.py:96-103, has no literal)
  grep -rn "ProviderCapabilities(" --include='*.py' tests | wc -l           # 10 literal capability blocks
  grep -n "supports_audio" src/film_pipeline/providers/factory.py || echo "no supports_audio in src/film_pipeline/providers/factory.py"
  ```
- **Blast radius:** `providers.factory`, `src/film_pipeline/app/_provider_seeds.py`, `generation` (cost/capability selection), five test files.
- **Candidate owner module:** `providers` (factory) as the single owner of registry entries; `testing.harness` consumes `build_provider_adapter(...)` and never hand-builds an entry.
- **Extraction sketch:** make `_default_capabilities` special-case the mock ids (or declare canonical entries next to `PROVIDER_PRICING` in `src/film_pipeline/providers/pricing.py:37-38`); replace all four test literals with `build_provider_adapter("mock-video-provider")` (the fifth entry site is production's `src/film_pipeline/providers/factory.py:96-103`); guard test asserting the built entry is stable for each mock id.
- **Prior art:** New. *(Count and grep parenthetical corrected after verification; the verifier's own `verify-13.md:184-188` also records the fifth entry.)*

### F-TEST-08 — No declared protocol for the `GraphServices` seams, so each tier invents its own store/runner fake; two same-named fakes already disagree

- **Class:** O8 (missing contract)
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** the typed seam a test double implements for graph services.
- **De-facto owners:**
  - `src/film_pipeline/graph/services.py:62-63` — fields typed as concrete classes, not protocols — `'prompt_runner: PromptRunner = field(default_factory=PromptRunner)\n    artifact_store: ArtifactStore = field(default_factory=lambda: _artifact_store(None))'`
  - `tests/unit/graph/test_context_packets.py:12-19` — fake #1, constructed with data, has `load_ref` — `'class FakeArtifactStore:\n    def __init__(self, artifacts: dict[str, dict[str, Any]]) -> None:'`
  - `tests/unit/graph/test_qc_subgraph.py:43-50` — fake #2, no-arg, has `list_artifacts` — `'class FakeArtifactStore:\n    def __init__(self) -> None:\n        self.calls: list[tuple[str, FilmPhase, str, int]] = []'`
  - `tests/unit/mcp/tools/test_reference_generation_helpers.py:143-148` — a duck-typed runtime — `'class _FakeRuntime:\n        def list_providers(self) -> list[str]:\n            return ["video-provider-1"]'`
- **Drift proof:** *existing divergence* between the two `FakeArtifactStore` classes (different constructors, disjoint method sets: `load_ref` vs `list_artifacts`), both standing in for the same `services.artifact_store` attribute consumed by graph nodes (`src/film_pipeline/graph/nodes/_context.py:100` — `'data = services.artifact_store.load('`, also `:127`, `:370`). Mutation: add a method to `ArtifactStore` that a node starts calling; neither fake has it, and the failures land as `AttributeError` in whichever tier happens to exercise that node — the fake's coverage cannot be enumerated because no protocol lists what a store double must provide. `grep -rn "class .*Fake" --include='*.py' tests | wc -l` = 23 contract-less fakes.
- **Reproduce:**
  ```bash
  grep -rn "class .*Fake" --include='*.py' tests | wc -l   # 23
  grep -rn "class FakeArtifactStore" --include='*.py' tests
  ```
- **Blast radius:** `graph` node tests, `mcp.tools` tests, `app` tests (`FakeRuntime` ×3 at `tests/unit/app/test_app_ops.py:160,188,211`).
- **Candidate owner module:** `testing.protocols` — declared `typing.Protocol` definitions for the artifact-store and runtime seams, with one shared in-memory implementation; or narrow `GraphServices` field types so doubles must satisfy the real type.
- **Extraction sketch:** extract the minimal method set each double needs from its consumers, declare it as a `Protocol`, type `GraphServices.artifact_store` against it, ship one `InMemoryArtifactStore` in `testing/`, and delete the 23 ad-hoc fakes as consumers migrate; guard test = `mypy` on the test suite (already `strict` for `tests.*`, `pyproject.toml:119-121`) plus a guard that each fake's class is decorated as implementing the protocol.
- **Prior art:** New.

---

## Findings added after verification

These three seams were **missed by `verify-13.md`**; each was re-verified by the author at HEAD
before filing. They were added during the fix loop and are therefore outside the
CONFIRMED/DOWNGRADED verdicts recorded in the header. The third verifier-missed item —
`src/film_pipeline/agents/impl/screenwriter_agent.py:54`'s unbound `script_output` wrapper — is folded into **F-TEST-01**
(it is the same concern); the first, second and fourth are filed below as F-TEST-09..11.
Where the verifier gave a count, the reproduced count differs and is stated.

### F-TEST-09 — "How a test supplies the runtime to MCP tools" is re-derived at dozens of call sites with no owner

- **Class:** O5 (policy-by-branch) + O2
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** one policy for injecting the `StudioRuntime` singleton into `film_pipeline.mcp.tools`.
- **De-facto owners:**
  - `tests/conftest.py:51` — autouse rebind of the genuine accessor for every test — `'tools_pkg.get_runtime = reset_runtime.__globals__["get_runtime"]'`
  - `tests/unit/mcp/tools/conftest.py:29` and `:34` — a second autouse rebind, before and after each test in that package — `'tools_pkg.get_runtime = get_runtime'`
  - `tests/unit/mcp/tools/test_artifacts.py:130` — the dominant test-local pattern — `'monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)'`
- **Drift proof:** three mechanisms, no owner, and a partial edit is invisible. Reproduced counts at HEAD: `grep -rn 'monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime"' --include='*.py' tests | wc -l` = **67**; `grep -rn 'mock.patch("film_pipeline.mcp.tools.get_runtime"' --include='*.py' tests | wc -l` = **3**; `grep -rn 'mcp_tools.get_runtime = \|tools_pkg.get_runtime = ' --include='*.py' tests | wc -l` = **5** (3 of them the two conftests, 2 a save/restore pair at `tests/unit/mcp/tools/test_planning.py:29,33`); `grep -rln 'mcp.tools.get_runtime\|mcp_tools.get_runtime\|tools_pkg.get_runtime' --include='*.py' tests | wc -l` = **12 files** (source files only; without `--include='*.py'` the same grep counts `__pycache__` bytecode and reads **31** in a working tree — the `--include` gap that `F-TEST-10`/`F-TEST-11` also carried, and which made this count environment-dependent). Mutation: delete either autouse conftest — the other silently compensates for most tests, so the suite stays green while the per-test rebinding guarantee disappears. This is the exact failure class the rebind at `tests/conftest.py:46-48` guards against — `'Defensively rebind the tool->runtime function to the genuine one: a stale MagicMock must never survive into the next test regardless of how it got there.'` (the `:32-37` comment documents the separate `FILM_PIPELINE_MCP_MODE` leak).
- **Reproduce:**
  ```bash
  grep -rn 'monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime"' --include='*.py' tests | wc -l   # 67
  grep -rn 'mock.patch("film_pipeline.mcp.tools.get_runtime"' --include='*.py' tests | wc -l           # 3
  grep -rn 'mcp_tools.get_runtime = \|tools_pkg.get_runtime = ' --include='*.py' tests | wc -l         # 5
  grep -rln 'mcp.tools.get_runtime\|mcp_tools.get_runtime\|tools_pkg.get_runtime' --include='*.py' tests | wc -l   # 12
  ```
- **Blast radius:** `mcp.tools` (every registered tool resolves the runtime through this one attribute), all four test tiers.
- **Candidate owner module:** `testing.harness` — one runtime-injection context manager/fixture that performs the rebinding and restores the genuine accessor on exit; conftests call it once and tests request it instead of patching.
- **Extraction sketch:** replace the two autouse rebinds and the test-local patches with one shared helper; guard test asserting the accessor identity is restored after each test and that no `tests/**` module assigns `film_pipeline.mcp.tools.get_runtime` directly.
- **Prior art:** New. `verify-13.md:207-214` listed 6 test-local sites; the reproduced count is 71+ across 12 files.

### F-TEST-10 — `provider_health` holds two incompatible value types and the declared writer is bypassed

- **Class:** O3 (split state authority)
- **Severity:** Medium (impact 2 × drift 4 = 8) — latent: no production path is fed the object type today
- **Concern:** the value type stored in `StudioRuntime.provider_health`.
- **De-facto owners:**
  - `src/film_pipeline/app/runtime.py:386-387` — the declared writer, stores a plain dict — `'def set_provider_health(self, provider_id: str, status: str, reason: str = "") -> None:\n        self.provider_health[provider_id] = {"status": status, "reason": reason}'`
  - `src/film_pipeline/app/runtime.py:51` — the field admits both, untyped by value — `'provider_health: dict[str, Any] = field(default_factory=dict)'`
  - `tests/e2e/test_scenario_04_quota_exhausted.py:35` and `:53` — tests store `ProviderHealthState` **objects** in the same mapping — `'rt.provider_health["mock-video-provider"] = health'`
  - `tests/e2e/conftest.py:158-161` — another site writes a plain dict — `'rt.provider_health["mock-video-provider"] = {'`
- **Drift proof:** the declared readers require a mapping, not a model: `src/film_pipeline/mcp/tools/providers.py:24` — `'return _ok(provider_id=provider_id, status=health["status"], reason=health.get("reason", ""))'` — and `src/film_pipeline/app/health.py:48` — `'if h and h.get("status") != "healthy":'`; the declared reader type is `dict[str, Any] | None` (`src/film_pipeline/app/runtime.py:389`). `ProviderHealthState` is a Pydantic `MutableSchemaBase` (`src/film_pipeline/schemas/provider_health.py:12`), so it supports neither `health["status"]` nor `h.get("status")`. Mutation: pass the value that `tests/e2e/test_scenario_04_quota_exhausted.py:35` stores to `check_provider_health` (`src/film_pipeline/mcp/tools/providers.py:21`) or `_record_provider_status` (`src/film_pipeline/app/health.py:47`) → `TypeError`/`AttributeError`; no test does, and no test pins the value type, so the split passes today.
- **Reproduce:**
  ```bash
  grep -n "provider_health" src/film_pipeline/app/runtime.py
  grep -rn "ProviderHealthState" --include='*.py' tests/e2e
  grep -rn 'health\["status"\]\|h.get("status")' --include='*.py' src/film_pipeline
  ```
- **Blast radius:** `app.health` (`src/film_pipeline/app/health.py:47-49`), `mcp.tools.providers` (`check_provider_health` `:21-24`, `list_providers` `:44`), e2e scenario 4 (`tests/e2e/test_scenario_04_quota_exhausted.py:35,53`) and the shared `studio_runtime` fixture (`tests/e2e/conftest.py:158-161`) — scenario 5 (`tests/e2e/test_scenario_05_network_error.py`) has no `provider_health` at all.
- **Candidate owner module:** `app.runtime` — `provider_health` typed `dict[str, ProviderHealthState]` with `set_provider_health` as the single writer; tests use the writer instead of assigning the dict.
- **Extraction sketch:** change the field type, have `set_provider_health` construct `ProviderHealthState`, update `get_provider_health`/`get_all_health` returns, port `tests/e2e/conftest.py:158-161` and `test_scenario_04:35,53` to the writer; guard test asserting every stored value is a `ProviderHealthState`.
- **Prior art:** New. (`verify-13.md:215-220` notes it as a missed seam.)

### F-TEST-11 — e2e can build a real `GitBackend` in the tier where the session installs the in-memory double

- **Class:** O6 (parallel lifecycle) + O2
- **Severity:** Medium (impact 2 × drift 4 = 8) — latent: the fixture is currently unrequested
- **Concern:** which git backend an e2e test receives.
- **De-facto owners:**
  - `tests/conftest.py:78` — the suite-wide install — `'set_git_backend_type(InMemoryGitBackend)'`
  - `tests/e2e/conftest.py:113-114` — a fixture that builds the real backend directly, bypassing the injected type — `'def git_backend(tmp_path: Path) -> GitBackend:\n    return GitBackend.init_temp(tmp_path / "repo")'`
- **Drift proof:** the same tier can construct two backends with different semantics (subprocess git + real `.git` versus the in-process store). It is currently **latent**: `grep -rn "git_backend\|checkpoint_manager" --include='*.py' tests/e2e tests/smoke | grep -v "def \|import"` prints only `tests/e2e/conftest.py:119` and `tests/smoke/conftest.py:6,7` (the unfiltered form adds just the definitions/imports, `tests/e2e/conftest.py:17,113,118`) — no e2e or smoke test requests either fixture. Mutation: a new e2e test that requests `git_backend` gets real git while `studio_runtime` in the same file uses the double; no test fails, and the tier silently mixes semantics (the double's `restore_files` filter at `src/film_pipeline/testing/in_memory_git.py:120-121` no longer applies to that test).
- **Reproduce:**
  ```bash
  grep -rn "GitBackend.init_temp" --include='*.py' tests/e2e tests/smoke
  grep -rn "git_backend\|checkpoint_manager" --include='*.py' tests/e2e tests/smoke | grep -v "def \|import"   # tests/e2e/conftest.py:119; tests/smoke/conftest.py:6,7
  ```
- **Blast radius:** `checkpoints` e2e coverage; dead fixture today.
- **Candidate owner module:** `testing.harness` — one backend-selection policy (the injected type) for every tier; real-git fixtures renamed and used only where git semantics are asserted.
- **Extraction sketch:** delete `tests/e2e/conftest.py:113-119`, or rename to `real_git_backend` and restrict it to tests that assert git-specific behavior; guard test asserting e2e/smoke repositories come from the injected backend type.
- **Prior art:** New. (`verify-13.md:223-225` notes it as a missed seam.)

---

## Withdrawn findings / unverified hypotheses (not findings)

### F-TEST-02 (withdrawn) — Three independent "mock model response" sources; the shipped one is dead-wired

**Status: hypothesis, not a finding.** This block was filed as a High/Medium O1 finding and is
withdrawn here. It fails §1.6.3: neither the original drift proof nor its replacement survives
re-checking, and §1.3 excludes the residue (dead code + incompleteness) from ownership findings.

- **Class (as filed):** O1 (duplicated normative model) — *withdrawn*
- **Original drift proof — false equivalence, withdrawn after verification:** the claim that
  `src/film_pipeline/app/mock_responses.py:371`'s `clip-validator` `consensus` payload contradicts
  `MockModelAdapter.validator_response()` (`src/film_pipeline/testing/mock_model.py:47-52`) **does not hold**.
  `clip-validator` is an MVP *agent* id (`src/film_pipeline/agents/mvp/__init__.py:143`) implemented by
  `QCSynthesisAgent` (`src/film_pipeline/agents/impl/registry.py:28`) and is **not** in `MVP_VALIDATORS`, whose 15 ids
  are all `*-validator` (`src/film_pipeline/validation/validators/__init__.py:14,24,34,44,54,64,74,85,95,106,116,127,137,147,158`).
  Its `consensus` body is consumed by `src/film_pipeline/agents/impl/qc_synthesis_agent.py:20` and is that agent's declared output,
  not a validator response.
- **Replacement drift proof — also disproved (author re-check during the fix loop):** the remaining
  candidate was the duplicated "response when nothing is registered":
  `src/film_pipeline/testing/mock_model.py:31-36` versus `src/film_pipeline/agents/runner.py:160`. **Both are pinned by tests**, so the
  mutation does not exist:
  - `tests/unit/agents/test_runner.py:48-57` and `:138-149` assert the runner fallback exactly —
    `'assert result == {\n            "status": "ok",\n            "agent": "mock",\n            "output": {"_warning": "generic_fallback"},\n        }'`.
  - `tests/unit/test_testing_utils.py:80-85` asserts the double's placeholder — `'assert output["agent"] == "unknown"'` / `'assert output["mock_model"] is True'` — and `tests/unit/testing/test_mock_actors.py:59-64` pins `resp["status"] == "ok"` / `resp["mock_model"] is True`.
  Changing either site fails a test, so there is no §1.6.3(b) "partial edit passes every test while producing divergent behavior".
- **Residue (verified, but hygiene/incompleteness):**
  - `MockModelAdapter` reaches no runtime path: the only fixture that requests it never uses it —
    `tests/e2e/conftest.py:124` (`"    mock_model: MockModelAdapter,"`) versus the body at `:132`
    (`"runner = PromptRunner(mock_responses=default_mock_responses())"`). Ruff cannot catch the unused
    argument (`pyproject.toml:136` ignores `ARG001` for tests).
  - `_generic_mock_fallback` is a third response source reachable from any no-arg `PromptRunner()`
    (`grep -rn "PromptRunner()" --include='*.py' tests | wc -l` = 11, e.g.
    `tests/integration/test_generation_mcp.py:31`, `tests/unit/mcp/tools/test_generation.py:42`).
  - `ALL_SCENARIOS` and `MockHumanActor`'s fixture are likewise unused (see "Clean concerns").
- **Reproduce:**
  ```bash
  grep -rn "MockModelAdapter" --include='*.py' tests src
  grep -rn "PromptRunner()" --include='*.py' tests | wc -l   # 11
  grep -rn "clip-validator" --include='*.py' src/film_pipeline/validation/validators/ || echo "not a validator id"
  grep -n "generic_fallback" tests/unit/agents/test_runner.py   # the fallback IS pinned
  ```
- **If it is ever revived:** the candidate owner is `testing.doubles` — one response source, with cans
  injected as data (F-TEST-01) and `PromptRunner`'s fallback reduced to an explicit error outside mock
  mode; it needs a *new* drift proof (for example a consumer that must accept both sources), not the
  two disproved ones.
- **Prior art:** `docs/modular-architecture/audit/14-module-boundaries-and-import-law.md:273` notes the
  three homes for doubles as a packaging/contract issue. `verify-13.md:64-89` downgraded it to Medium 4;
  this file goes further and withdraws it, per §1.6.6 ("downgrade it to an explicitly labeled
  'unverified hypothesis' section — never leave it among findings").

---

## Clean concerns

| Concern | Single owner | Evidence / guard |
|---|---|---|
| Provider adapter contract | `src/film_pipeline/providers/base.py:39` `BaseProviderAdapter` | Both shipped mocks subclass it (`src/film_pipeline/providers/mock_provider.py:45`, `src/film_pipeline/providers/mock_image_provider.py:38`); the factory dispatches both by id (`src/film_pipeline/providers/factory.py:40-43`); `tests/unit/providers/test_mock_provider.py` contracts both classes across their methods (`:48` `TestMockVideoProvider`, `:231` `TestMockImageProvider`). Caveat: the contract is not enforced for *test-local* provider doubles (F-TEST-07, F-TEST-08). |
| Graph must not import test fixtures or the composition root | `graph` (enforced by test) | `tests/unit/graph/test_startup_boundaries.py:26-42` (AST sweep incl. lazy imports) and `:45-65` (fresh-interpreter `sys.modules` probe); repaired under B-F4; also recorded as clean in `audit/14:307`. |
| `film_pipeline.testing` import direction | `testing` package as a consumer | `src/film_pipeline/testing/storage.py:11`, `src/film_pipeline/testing/in_memory_git.py:29`, `src/film_pipeline/testing/scenarios.py:5` are the only cross-package edges; they are public façades. Not guarded mechanically (`audit/14:282-283`) — see candidate boundary. |
| Mock human decision surface | `src/film_pipeline/testing/mock_human.py:9-16` (7 profiles) | Single owner, but 3 of the 7 collapse to a bare `"approve"` (`:42-47`) making `APPROVE_SPEND_UNDER_LIMIT`, `STOP_ON_PROVIDER_BLOCK`, `CONFIRM_ROLLBACK` behaviorally identical; the fixture is also unused (`tests/e2e/conftest.py:37`). Recorded here as an unused-surface caveat, not as distributed ownership (§1.3 excludes incompleteness). |

Noted but **not** filed as ownership findings (dead code / hygiene, §1.3 excludes incompleteness and
duplication-of-convenience):

- `ALL_SCENARIOS` (`src/film_pipeline/testing/scenarios.py:122-136`) — 12 of 13 scenarios and the registry are unreferenced;
  only `HAPPY_PATH_SEQUENTIAL_CHAIN` is used (`tests/unit/test_testing_utils.py:106-108`).
- `MockHumanActor` and `MockModelAdapter` fixtures are dead-wired (the evidence originally filed as
  F-TEST-02, now a withdrawn hypothesis — see the hypotheses section above).
- Two docstring claims in `src/film_pipeline/testing/in_memory_git.py:8-9` ("~50 test modules", "minutes of pure overhead") were not
  independently counted for this audit; the verified counts above (95 runtime sites / 30 files) are used instead.

---

## Candidate module boundary

**Test-harness / doubles owner — `film_pipeline.testing` with a declared contract and a
tier-agnostic factory surface.**

- **One responsibility:** be the single normative owner of every test double, canned payload,
  fixture factory, and the production-separation invariant; ship nothing that production imports
  except through explicit dependency injection.
- **Non-goals:** it does *not* own the real contracts it doubles (`src/film_pipeline/providers/base.py`,
  `src/film_pipeline/artifacts/store.py`, `src/film_pipeline/checkpoints/git_backend.py`, the agent output schemas); it does not import
  `_private` modules of any package; it does not define production defaults.
- **Normative model (N):** one `DoubleContract` set —
  (a) mock provider registry entries produced only by `providers.factory.build_provider_adapter`
  (`src/film_pipeline/providers/factory.py:18-44`); (b) canned agent payloads typed per `agent_id` against the artifact
  schemas named by `PromptTemplate.output_schema_ref` (`src/film_pipeline/agents/prompt_templates/registry.py:30`);
  (c) one test-root/store/runtime factory with an explicit profile;
  (d) one `MockModelAdapter`, no in-runner fallback (`src/film_pipeline/agents/runner.py:152-160` to be removed or
  gated to explicit mock mode).
- **Invariant enforcement (I):** parity test running real and double backends through one contract
  fixture (`GitBackend` vs `InMemoryGitBackend`); schema-conformance test routing each canned payload
  through its agent class's `execute()`/`validate()` and asserting the template's declared output
  wrapper; a production-separation guard with a self-test (detects same-size rewrites, fails if the
  guard is removed) and a single env-write site; AST guard that no `tests/**` module constructs
  `ArtifactStore(`/`StudioRuntime(` outside the harness factory.
- **Representation authority (R):** the harness factory is the only writer of test storage roots and
  test runtimes; `provider_health` seeding goes through `StudioRuntime.set_provider_health`
  (`src/film_pipeline/app/_provider_seeds.py:37`) rather than direct dict assignment (`tests/e2e/conftest.py:158-161`).
- **Packaging decision (prior art `audit/14:290-296`):** either exclude `testing/` from the wheel or
  declare it a shipped dev-support package; today it is shipped (verified in
  `dist/film_pipeline-0.4.0-py3-none-any.whl`) and coverage-excluded (`pyproject.toml:95-98`), so the
  parity/guard tests proposed above are its only mechanical safety net. F-TEST-03's parity suite is
  the minimum bar for shipping it.

---

## Unverified items (explicitly labeled — not findings)

1. **No mutation experiments were executed.** Every drift proof above is either an existing
   divergence read at HEAD (F-TEST-01, -02, -04, -07, -08) or a code-path argument (F-TEST-03, -05, -06).
   The claimed silent failures were reasoned from the cited code, not observed by running a mutated suite.
2. **`_production_roots_untouched` was not exercised.** The same-size-overwrite blind spot (F-TEST-06)
   follows from `_snapshot_tree` storing sizes only (`tests/conftest.py:163`); no test was run to confirm
   a same-size rewrite is indeed undetected end-to-end.
3. **`src/film_pipeline/testing` wheel membership** was verified against the locally built
   `dist/film_pipeline-0.4.0-py3-none-any.whl` (member sizes match HEAD) rather than by building a fresh
   wheel at this commit; `dist/` is not tracked in git.
4. **Test-tier counts** (`64`/`95`/`11`/`102`, and F-TEST-09's `67`/`3`/`31`) were produced by the
   greps shown inline; they count *syntactic construction sites*, not distinct logical fixtures, and
   include retries inside `pytest.raises`.
5. **F-TEST-09..11 are author-added after the verification pass** and are therefore not covered by
   `verify-13.md`'s CONFIRMED/DOWNGRADED verdicts. Each was read and grep-reproduced at HEAD before
   filing, but no second independent agent has reviewed them yet.
6. **F-TEST-02 is withdrawn to the hypotheses section.** The author disproved both its original and
   replacement drift proofs during this fix loop; no valid mutation scenario for the
   "three mock-response sources" concern was found. It should not be counted as a finding or used in
   the duplication ledger until a real drift proof exists.
