# Repository Structure

This is the shortest accurate map of the code.

## Main Flow

`src/film_pipeline/mcp/tools/__init__.py`
-> MCP tool handlers
-> `src/film_pipeline/app/runtime.py`
-> `src/film_pipeline/graph/nodes.py`
-> agent implementations in `src/film_pipeline/agents/impl/`
-> artifact persistence in `src/film_pipeline/artifacts/store.py`

## Important Packages

`src/film_pipeline/app/`
- Runtime lifecycle, smoke checks, product gate, health/bootstrap.

`src/film_pipeline/mcp/`
- MCP contracts, registration, server entrypoint, and tool handlers.

`src/film_pipeline/graph/`
- Phase nodes, graph construction, routing, and graph services.

`src/film_pipeline/agents/`
- Agent contracts, prompt runner, model routing, and concrete agent implementations.

`src/film_pipeline/agents/prompt_templates/`
- Dedicated critical-path templates.

`src/film_pipeline/artifacts/`
- Typed artifact persistence, metadata, indexing, and lineage.

`src/film_pipeline/validation/`
- Validator registry and validator implementations.

`src/film_pipeline/checkpoints/`
- Git-backed checkpoints, invalidation, resume, and rollback.

`src/film_pipeline/providers/`
- Mock and real provider adapters, health, credentials, and failure classification.

`src/film_pipeline/kb/`
- Knowledge-base manifest loading, retrieval, and context packet construction.

`tests/unit/`
- Small behavioral units.

`tests/integration/`
- Cross-boundary runtime and MCP behavior.

`tests/e2e/`
- Scenario-level product behavior.

`tests/smoke/`
- Operator workflow checks tied to docs/runbook behavior.

## Files Worth Reading First

1. [README.md](/Users/ghassan/my-projects/film-pipeline-langgraph/README.md)
2. [src/film_pipeline/app/runtime.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/app/runtime.py)
3. [src/film_pipeline/graph/nodes.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/graph/nodes.py)
4. [src/film_pipeline/mcp/tools/__init__.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/mcp/tools/__init__.py)
5. [src/film_pipeline/agents/runner.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/agents/runner.py)
6. [src/film_pipeline/agents/prompt_templates/defaults.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/agents/prompt_templates/defaults.py)
7. [tests/smoke/test_manual_4min_mock_short.py](/Users/ghassan/my-projects/film-pipeline-langgraph/tests/smoke/test_manual_4min_mock_short.py)
