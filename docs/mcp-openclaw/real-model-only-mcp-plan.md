# Real-Model-Only MCP Plan For OpenClaw

## Goal

When OpenClaw connects through MCP, it should use:

- real model calls for agent execution
- real provider adapters for generation
- real profile/config selection at project start
- real approval behavior

It must not silently fall back to mock model, mock provider, or mock-human behavior.

Mocks should remain available for tests and demo workflows, but not for the OpenClaw production path.

## Current State

The repository is closer than it was originally, but there are still gaps.

Evidence:

- The default MCP runtime uses `GraphServices.for_mock_runtime`: [src/film_pipeline/app/runtime.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/app/runtime.py:38)
- The global MCP runtime is created eagerly with that mock runtime: [src/film_pipeline/app/runtime.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/app/runtime.py:353)
- `for_mock_runtime()` injects canned mock prompt responses for the core agents: [src/film_pipeline/graph/services.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/graph/services.py:31)
- `make run-mcp` is explicitly documented as mock mode: [Makefile](/Users/ghassan/my-projects/film-pipeline-langgraph/Makefile:62)
- Profile selection exists in config code and YAML files, but MCP project creation does not accept or resolve profiles: [src/film_pipeline/config/resolver.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/config/resolver.py:1), [src/film_pipeline/mcp/tools/__init__.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/mcp/tools/__init__.py:40)
- The maintained operator walkthrough is the mock-first smoke path, not a real-provider path: [tests/smoke/test_manual_4min_mock_short.py](/Users/ghassan/my-projects/film-pipeline-langgraph/tests/smoke/test_manual_4min_mock_short.py:1)

Status update on June 20, 2026:

- MCP runtime mode alignment is implemented
- real-mode project creation resolves the profile stack and registers providers from it
- prompt continuity between phases is fixed
- the local real provider profile now uses `gemini-imagen-4` for the image lane instead of `mock-image-provider`
- real project creation rejects missing provider credentials up front
- MCP now has a real `generate_reference_images` path that runs a full 12-phase pipeline: structured prompt construction from CharacterBible + FilmConstitution, per-frame heuristic checks (5 Pillow checks), per-frame Gemini review (40-pt rubric with selective validation), identity consistency via seed locking + I2I drift detection, retry loop (3 attempts with feedback injection), provider tier routing (fast/standard/ultra), Pillow composite sheets (Character Identity 2048×2048, Environment Board 3840×2160), Gemini composite validation (50pt rubric), delta regeneration for failing tiles, and human-readable index persistence (`references/index/reference-index.json`)

## Root Causes

### 1. MCP runtime defaults to mock execution

The main runtime object is created with mock graph services. That makes mock behavior the default, not an explicit test mode.

### 2. There is no MCP configuration surface for project profiles

OpenClaw cannot ask:

- which profiles are available
- which provider stack is active
- which model routing profile is active
- whether this project is mock or real

As a result, the operator path cannot choose a real runtime contract up front.

### 3. Bootstrap does not enforce real-mode readiness

Bootstrap checks only basic filesystem presence. It does not verify:

- required API keys for the selected provider/model stack
- non-mock profile selection
- registered real providers
- real model adapter readiness
- whether OpenClaw is accidentally starting against mock mode

### 4. MCP project creation is too thin

`create_film_project` only accepts:

- `project_id`
- `title`
- `slug`

It does not accept:

- profile ids
- runtime mode
- provider preference
- budget cap
- review strictness
- film type

That prevents the operator from establishing a real execution contract before the first idea is submitted.

### 5. Provider/model registration is not productized

The codebase has real adapters, but there is no clear startup path that:

- loads the selected real profile
- registers the required providers
- wires model routing to real models
- blocks startup when a required dependency is missing

### 6. Test/demo concerns are mixed into product startup

Mocks are useful and should remain. The problem is that they are wired into the default MCP startup path instead of being isolated to test/demo entrypoints.

## Non-Goals

This plan does not propose:

- deleting mock providers or mock models
- removing smoke and e2e mock coverage
- connecting paid providers by default for every developer

The change is to make OpenClaw's production MCP path explicit, strict, and real-only.

## Target State

OpenClaw should have two clearly separated MCP modes.

### 1. Demo/Test MCP Mode

Purpose:

- CI
- smoke tests
- local dry runs

Characteristics:

- explicit mock profile
- explicit mock runtime
- explicit mock providers
- explicit mock model adapter

### 2. OpenClaw Production MCP Mode

Purpose:

- real operator use
- real agent execution
- real provider-backed generation

Characteristics:

- explicit non-mock profile
- bootstrap fails if any required real dependency is missing
- mock provider/model/human are rejected
- every project records resolved profile, model routing, and provider stack

## Plan

## Phase 1. Introduce Explicit MCP Runtime Modes

Add an explicit runtime mode concept:

- `mock`
- `real`

Required changes:

- replace the eager global `StudioRuntime()` default with a factory/bootstrap path
- add a startup config source such as env var or CLI arg:
  - `FILM_PIPELINE_MCP_MODE=mock|real`
- make `make run-mcp` stop pretending one mode fits all
- add separate entrypoints:
  - `make run-mcp-mock`
  - `make run-mcp-real`

Rules:

- `mock` mode may use `GraphServices.for_mock_runtime()`
- `real` mode must never use `for_mock_runtime()`

Acceptance:

- starting real mode cannot succeed if mock graph services are still wired

## Phase 2. Add A Real Runtime Builder

Create a real runtime/service builder parallel to `for_mock_runtime()`.

It should:

- create a real `PromptRunner`
- use real model routing
- register real providers from the selected profile
- populate provider health state
- build artifact storage and KB services the same way as production

Required changes:

- add something like `GraphServices.for_real_runtime(...)`
- add a bootstrap path that resolves profiles before creating the runtime
- wire `ModelAdapter` into the prompt runner instead of canned responses

Acceptance:

- a real-mode startup performs actual model calls when agents run
- there are no canned prompt responses in the OpenClaw path

## Phase 3. Make Profiles First-Class In MCP

Add MCP tools for profile discovery and project setup.

Minimum tools:

- `list_profiles`
- `inspect_profile`
- `resolve_profile_stack`
- `create_film_project` extended to accept profile inputs

`create_film_project` should accept at least:

- `project_id`
- `title`
- `slug`
- `film_type_profile`
- `quality_profile`
- `provider_profile`
- `review_profile`
- optional project overrides

The server should persist the resolved config into project state and artifacts before intake proceeds.

Acceptance:

- OpenClaw can create a project with a real provider/model contract before `submit_idea`

## Phase 4. Enforce Real-Mode Bootstrap Validation

Extend bootstrap and health checks to validate real-mode prerequisites.

Bootstrap must verify:

- the selected profiles exist
- the resolved profile stack is conflict-free
- required provider credentials exist
- required model credentials exist
- no selected provider is mock
- no selected model route is mock
- required provider adapters can be instantiated

Health/readiness must expose:

- current MCP mode
- resolved profile ids
- resolved provider ids
- resolved model ids or routing map
- credential readiness

Acceptance:

- `run-mcp-real` fails fast with actionable errors
- readiness cannot report healthy if the active stack is still mock

## Phase 5. Reject Mock Dependencies In OpenClaw Real Mode

Real mode should have hard guards.

Guards:

- reject `mock-video-provider`
- reject `mock-image-provider`
- reject `mock-model`
- reject mock human approvals if production mode is selected

These checks should happen:

- at startup
- at project creation
- at generation planning
- at approval boundaries when relevant

Acceptance:

- OpenClaw cannot accidentally plan or execute a real project against mock infrastructure

## Phase 6. Wire Real Provider Registration

Today the runtime can register providers, but the product startup path does not clearly do that for OpenClaw.

Required changes:

- resolve provider profile
- instantiate adapters such as `seedance-openrouter` and `veo` variants from config
- register them into runtime on startup
- initialize health state for each provider
- expose them via `list_providers` and `check_provider_health`

Acceptance:

- `list_providers` in real mode returns the real configured providers
- `check_provider_health` reflects actual provider readiness

## Phase 7. Make Agent Execution Auditably Real

The operator needs proof that real models were used.

Persist on each critical-path agent execution:

- model provider
- model id
- prompt template id/version
- whether response was mock or live
- request timestamp

Real mode rule:

- `mock=false` must be enforced in these execution records

Acceptance:

- `explain_agent_routing` and audit tools can prove the run used real models

## Phase 8. Add Real-Mode Operator Docs

Document a separate OpenClaw operator path.

It should include:

- required env vars
- how to choose a real profile stack
- how to confirm readiness before project creation
- how to verify real providers/models are active
- how to detect accidental mock mode

This doc set should not reuse the current mock-first walkthrough as the main OpenClaw guide.

## Phase 9. Add Real-Mode Tests

Do not rely only on docs.

Required tests:

- unit tests for mode guards
- unit tests for profile resolution in project creation
- integration tests for startup failure when credentials are missing
- integration tests for provider registration from real profiles
- MCP integration tests that verify real mode rejects mock provider/model ids

For networked real-provider tests:

- keep them separate and explicitly marked
- do not run them in default unit CI

## Implementation Order

1. Add explicit MCP mode and split startup entrypoints.
2. Add real runtime builder and remove mock as the default for production startup.
3. Add MCP profile/config tools and extend `create_film_project`.
4. Add strict bootstrap/readiness checks for real mode.
5. Add hard guards against mock dependencies in real mode.
6. Register real providers from resolved profile config.
7. Persist live model/provider execution evidence.
8. Add operator docs and integration tests.

## Concrete File-Level Plan

Files likely to change:

- `src/film_pipeline/app/runtime.py`
  Why: remove eager mock default from the product path.
- `src/film_pipeline/graph/services.py`
  Why: add real runtime service construction.
- `src/film_pipeline/app/bootstrap.py`
  Why: validate real-mode readiness and credentials.
- `src/film_pipeline/app/health.py`
  Why: expose mode and real-stack readiness.
- `src/film_pipeline/mcp/tools/__init__.py`
  Why: add profile/config MCP tools and enforce real-mode guards.
- `src/film_pipeline/mcp/server.py`
  Why: initialize the correct runtime mode and startup contract.
- `src/film_pipeline/config/resolver.py`
  Why: drive profile resolution for MCP project creation.
- `src/film_pipeline/providers/registry.py`
  Why: support startup registration from config.
- `Makefile`
  Why: split mock and real MCP entrypoints.
- `documentation/getting-started.md`
  Why: stop implying a single mock-first MCP command is the operator path.
- `docs/openclaw-mcp-operator-guide.md`
  Why: point OpenClaw at the real-mode workflow once available.

Files likely to add:

- `src/film_pipeline/app/runtime_factory.py`
  Why: keep mode-specific runtime construction out of the state container.
- `tests/integration/test_mcp_real_mode.py`
  Why: verify the real-mode MCP contract.
- `tests/unit/app/test_bootstrap_real_mode.py`
  Why: verify fail-fast behavior.

## Acceptance Criteria

The OpenClaw MCP path is fixed when all of these are true:

1. `run-mcp-real` exists and starts only with a non-mock resolved profile stack.
2. OpenClaw can discover and choose profiles through MCP before project creation.
3. `create_film_project` persists resolved real config into project state.
4. Agent execution uses live model adapters, not canned responses.
5. Generation planning and execution use only real configured providers in real mode.
6. Health/readiness clearly reports active mode, providers, and model routes.
7. Audit data proves whether a run was live or mock.
8. Real mode rejects any mock provider/model usage.

## Recommended First Slice

The smallest useful first implementation is:

1. add `run-mcp-real`
2. add `FILM_PIPELINE_MCP_MODE`
3. add real-mode bootstrap failure on mock runtime
4. extend `create_film_project` with profile inputs
5. persist resolved config in project state
6. reject `mock-*` providers/models in real mode

That does not finish the entire product, but it closes the most dangerous gap:

- OpenClaw thinks it is operating a real studio while the runtime is still mock-backed

## Summary

The problem is not just "mock models exist."

The real problem is that the product startup contract is ambiguous, and the MCP surface does not let OpenClaw establish or verify a real execution contract.

The fix is:

- explicit real vs mock MCP modes
- profile-aware MCP project setup
- strict bootstrap guards
- real provider/model registration
- audit evidence that proves the run was live
