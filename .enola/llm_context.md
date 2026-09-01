# Architecture Snapshot

## Repository Map

73 modules, 4737 symbols, grouped by area. Every module is in `facts.jsonl`, or query_facts(kind="module").

| Area | Modules | Symbols | Languages |
|------|---------|---------|-----------|
| `tests` | 30 | 2480 | python |
| `src` | 42 | 2248 | python |
| `docs` | 1 | 9 | python |

Largest modules:
- `tests/unit` — 323 symbols (python)
- `tests/unit/graph` — 301 symbols (python)
- `tests/unit/mcp/tools` — 294 symbols (python)
- `tests/unit/agents` — 236 symbols (python)
- `tests/unit/tui` — 214 symbols (python)
- `tests/unit/generation` — 163 symbols (python)
- `tests/unit/validation` — 161 symbols (python)
- `src/film_pipeline/mcp/tools` — 155 symbols (python)
- `src/film_pipeline/graph/nodes` — 152 symbols (python)
- `src/film_pipeline/schemas` — 133 symbols (python)
- `src/film_pipeline/app` — 127 symbols (python)
- `src/film_pipeline/graph` — 119 symbols (python)
- `tests/unit/providers` — 111 symbols (python)
- `src/film_pipeline/agents/impl` — 109 symbols (python)
- `tests/unit/app` — 102 symbols (python)
- `src/film_pipeline/generation` — 100 symbols (python)
- `tests/e2e` — 99 symbols (python)
- `src/film_pipeline/validation/impl` — 93 symbols (python)
- `src/film_pipeline/app/services` — 90 symbols (python)
- `src/film_pipeline/tui/gateways` — 86 symbols (python)

## Extraction Quality

- Files parsed: **475** / 720 seen (0 file(s) + 89 directory tree(s) skipped by ignore globs)
- Parse errors: 0
- Cross-repo analysis: not run (single-repo snapshot — append client/backend repos to enable unused-routes and coverage)

## Architecture Pattern

_No specific architecture pattern detected._

## Entry Points

41 handlers, 15 shown:
- **handler**: `src/film_pipeline/mcp/_stdio_transport.handle_jsonrpc` (src/film_pipeline/mcp/_stdio_transport.py)
- **handler**: `src/film_pipeline/mcp/server.main` (src/film_pipeline/mcp/server.py)
- **handler**: `tests/unit/agents/test_model_adapter.test_accepts_timeout_kw_handles_var_kwargs_and_rejects_plain_builtins` (tests/unit/agents/test_model_adapter.py)
- **handler**: `tests/unit/app/test_logging_setup.test_disabling_persistence_removes_an_existing_file_handler` (tests/unit/app/test_logging_setup.py)
- **handler**: `tests/unit/app/test_logging_setup.test_file_handler_when_persistent` (tests/unit/app/test_logging_setup.py)
- **handler**: `tests/unit/app/test_logging_setup.test_no_file_handler_without_persistence` (tests/unit/app/test_logging_setup.py)
- **handler**: `tests/unit/app/test_logging_setup.test_no_file_handler_without_runtime_root` (tests/unit/app/test_logging_setup.py)
- **handler**: `tests/unit/app/test_logging_setup.test_persistent_call_replaces_handler_for_a_new_runtime_root` (tests/unit/app/test_logging_setup.py)
- **handler**: `tests/unit/app/test_logging_setup.test_stderr_handler_installed_and_idempotent` (tests/unit/app/test_logging_setup.py)
- **handler**: `tests/unit/app/test_resume_integrity.test_preserve_external_requests_copies_when_resumed_empty` (tests/unit/app/test_resume_integrity.py)
- **handler**: `tests/unit/app/test_resume_integrity.test_preserve_external_requests_noop_when_resumed_has_own` (tests/unit/app/test_resume_integrity.py)
- **handler**: `tests/unit/constraints/test_extractor.test_project_id_is_preserved` (tests/unit/constraints/test_extractor.py)
- **handler**: `tests/unit/graph/test_router_validation_status.test_blocked_status_routes_to_handle_blockers` (tests/unit/graph/test_router_validation_status.py)
- **handler**: `tests/unit/kb/test_compression.test_compact_json_context_preserves_small_artifacts` (tests/unit/kb/test_compression.py)
- **handler**: `tests/unit/mcp/tools/test_config.test_get_runtime_mode_no_active_project_uses_server_mode` (tests/unit/mcp/tools/test_config.py)
- … and 26 more (query_facts(kind="route") for all)
- **main**: `docs/clean-code-refactor/tools/bar_check.main` (docs/clean-code-refactor/tools/bar_check.py)
- **main**: `src/film_pipeline/app/product_gate.main` (src/film_pipeline/app/product_gate.py)
- **main**: `src/film_pipeline/cli/run.main` (src/film_pipeline/cli/run.py)
- **main**: `src/film_pipeline/mcp/server.main` (src/film_pipeline/mcp/server.py)
- **main**: `src/film_pipeline/tui/app.main` (src/film_pipeline/tui/app.py)

## Dependency Rules

282 internal module dependencies. The modules that reach furthest; traverse() or query_facts(kind="dependency") for the edges themselves.

| Module | Depends on |
|--------|------------|
| `tests/e2e` | 20 modules |
| `src/film_pipeline/mcp/tools` | 16 modules |
| `tests/unit` | 15 modules |
| `tests/unit/mcp/tools` | 14 modules |
| `src/film_pipeline/graph/nodes` | 12 modules |
| `tests/unit/graph` | 11 modules |
| `src/film_pipeline/app` | 10 modules |
| `src/film_pipeline/graph` | 8 modules |
| `tests/integration` | 8 modules |
| `tests/unit/agents` | 8 modules |
| `tests/unit/tui` | 7 modules |
| `tests/unit/validation` | 7 modules |
| `src/film_pipeline/agents` | 6 modules |
| `src/film_pipeline/app/services` | 6 modules |
| `src/film_pipeline/mcp/tools/generation` | 6 modules |
| `src/film_pipeline/mcp/tools/reference_generation` | 6 modules |
| `tests/unit/generation` | 6 modules |
| `src/film_pipeline/tui` | 5 modules |
| `tests/unit/providers` | 5 modules |
| `tests/unit/tui/widgets` | 5 modules |
| `src/film_pipeline/generation` | 4 modules |
| `src/film_pipeline/graph/subgraphs` | 4 modules |
| `src/film_pipeline/tui/screens` | 4 modules |
| `tests/unit/app` | 4 modules |
| `tests/unit/app/services` | 4 modules |
| `src/film_pipeline/graph/orchestrator_validators` | 3 modules |
| `src/film_pipeline/mcp/tools/bibles` | 3 modules |
| `src/film_pipeline/providers` | 3 modules |
| `src/film_pipeline/tui/widgets` | 3 modules |
| `src/film_pipeline/validation` | 3 modules |
| `src/film_pipeline/validation/impl` | 3 modules |
| `tests` | 3 modules |
| `tests/unit/cli` | 3 modules |
| `tests/unit/config` | 3 modules |
| `tests/unit/post` | 3 modules |
| `src/film_pipeline/agents/impl` | 2 modules |
| `src/film_pipeline/cli` | 2 modules |
| `src/film_pipeline/mcp` | 2 modules |
| `src/film_pipeline/post` | 2 modules |
| `src/film_pipeline/providers/adapters` | 2 modules |
| `src/film_pipeline/tui/gateways` | 2 modules |
| `src/film_pipeline/validation/validators` | 2 modules |
| `tests/integration/cli` | 2 modules |
| `tests/integration/providers` | 2 modules |
| `tests/smoke` | 2 modules |
| `tests/unit/artifacts` | 2 modules |
| `tests/unit/checkpoints` | 2 modules |
| `tests/unit/constraints` | 2 modules |
| `tests/unit/kb` | 2 modules |
| `tests/unit/observability` | 2 modules |
| `tests/unit/review` | 2 modules |
| `src/film_pipeline` | 1 modules |
| `src/film_pipeline/agents/mvp` | 1 modules |
| `src/film_pipeline/agents/prompt_templates` | 1 modules |
| `src/film_pipeline/agents/prompt_templates/defaults` | 1 modules |
| `src/film_pipeline/artifacts` | 1 modules |
| `src/film_pipeline/checkpoints` | 1 modules |
| `src/film_pipeline/config` | 1 modules |
| `src/film_pipeline/constraints` | 1 modules |
| `src/film_pipeline/generation/compositor` | 1 modules |

## Critical Modules

| Module | Fan-In | Fan-Out | Criticality |
|--------|--------|---------|-------------|
| `src/film_pipeline/schemas` | 410 | 1 | high |
| `src/film_pipeline/app` | 194 | 33 | high |
| `src/film_pipeline/graph` | 141 | 16 | high |
| `tests/unit/graph` | 0 | 153 | high |
| `src/film_pipeline/mcp/tools` | 73 | 73 | high |
| `src/film_pipeline/graph/nodes` | 62 | 83 | high |
| `tests/unit/mcp/tools` | 0 | 135 | high |
| `tests/unit` | 0 | 133 | high |
| `tests/e2e` | 17 | 87 | high |
| `src/film_pipeline/tui` | 65 | 19 | high |

## Risk Zones

- **Cyclic dependency detected (2 modules)** (confidence: 100%): The following modules form a dependency cycle: src/film_pipeline/agents/prompt_templates -> src/film_pipeline/agents/prompt_templates/defaults -> src/film_pipeline/agents/prompt_templates. This can cause initialization issues, make refactoring harder, and indicates tight coupling.
- **Cyclic dependency detected (7 modules)** (confidence: 100%): The following modules form a dependency cycle: src/film_pipeline/app -> src/film_pipeline/app/services -> src/film_pipeline/mcp -> src/film_pipeline/mcp/tools -> src/film_pipeline/mcp/tools/bibles -> src/film_pipeline/mcp/tools/generation -> src/film_pipeline/mcp/tools/reference_generation -> src/film_pipeline/app. This can cause initialization issues, make refactoring harder, and indicates tight coupling.
- **Cyclic dependency detected (4 modules)** (confidence: 100%): The following modules form a dependency cycle: src/film_pipeline/graph -> src/film_pipeline/graph/nodes -> src/film_pipeline/graph/orchestrator_validators -> src/film_pipeline/graph/subgraphs -> src/film_pipeline/graph. This can cause initialization issues, make refactoring harder, and indicates tight coupling.
- **Cyclic dependency detected (2 modules)** (confidence: 100%): The following modules form a dependency cycle: src/film_pipeline/providers -> src/film_pipeline/providers/adapters -> src/film_pipeline/providers. This can cause initialization issues, make refactoring harder, and indicates tight coupling.
- **Cyclic dependency detected (2 modules)** (confidence: 100%): The following modules form a dependency cycle: src/film_pipeline/schemas -> src/film_pipeline/schemas/registries -> src/film_pipeline/schemas. This can cause initialization issues, make refactoring harder, and indicates tight coupling.
- **Cyclic dependency detected (4 modules)** (confidence: 100%): The following modules form a dependency cycle: src/film_pipeline/tui -> src/film_pipeline/tui/gateways -> src/film_pipeline/tui/screens -> src/film_pipeline/tui/widgets -> src/film_pipeline/tui. This can cause initialization issues, make refactoring harder, and indicates tight coupling.

---

*Generated at 2026-08-29T08:56:12Z in 556.848792ms. 8189 facts, 80 insights.*
