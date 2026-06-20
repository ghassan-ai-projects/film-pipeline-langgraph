# Code Onboarding

This is the fastest way to follow the code yourself.

## 1. Understand The Supported Product

Start with:

- [product-overview.md](./product-overview.md)
- [../docs/product-completion/README.md](../docs/product-completion/README.md)
- [../docs/product-completion-plan/README.md](../docs/product-completion-plan/README.md)

That tells you what the repository is actually trying to do, and what is intentionally out of scope.

## 2. Follow One Request End To End

Use this request path:

1. MCP tool in [src/film_pipeline/mcp/tools/__init__.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/mcp/tools/__init__.py)
2. Runtime method in [src/film_pipeline/app/runtime.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/app/runtime.py)
3. Phase node in [src/film_pipeline/graph/nodes.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/graph/nodes.py)
4. Agent implementation in `src/film_pipeline/agents/impl/`
5. Artifact write in [src/film_pipeline/artifacts/store.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/artifacts/store.py)

Good first paths to trace:

- `submit_idea`
- `approve_intake`
- `approve_phase`
- `plan_generation_batch`
- `get_project_summary`

## 3. Understand Prompt Execution

Read these in order:

1. [src/film_pipeline/agents/runner.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/agents/runner.py)
2. [src/film_pipeline/agents/prompt_templates/registry.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/agents/prompt_templates/registry.py)
3. [src/film_pipeline/agents/prompt_templates/defaults.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/agents/prompt_templates/defaults.py)
4. [src/film_pipeline/graph/nodes.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/graph/nodes.py)

Important rule:

- critical-path agents now go through dedicated templates
- `film-knowledge-base/promt.md` is manual reference only, not runtime input

## 4. Understand State And Artifacts

Read:

1. [src/film_pipeline/app/runtime.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/app/runtime.py)
2. [src/film_pipeline/graph/router.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/graph/router.py)
3. [src/film_pipeline/artifacts/store.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/artifacts/store.py)
4. [src/film_pipeline/schemas/_base.py](/Users/ghassan/my-projects/film-pipeline-langgraph/src/film_pipeline/schemas/_base.py)

Watch for:

- `current_phase`
- `approved`
- `human_approval_required`
- `issues`
- `_routing_decisions`
- artifact refs such as `script_ref`, `shot_matrix_ref`, `cost_estimate_ref`

## 5. Learn The Expected Behavior From Tests

Read tests from small to large:

1. `tests/unit/`
2. `tests/integration/test_mcp_flow.py`
3. `tests/integration/test_dynamic_routing.py`
4. `tests/integration/test_validation_runtime.py`
5. `tests/smoke/test_manual_4min_mock_short.py`
6. `tests/e2e/test_scenario_01_happy_path.py`

## 6. Use One Executable Reference Flow

Run:

```bash
uv run --python 3.12 --group dev pytest tests/smoke/test_manual_4min_mock_short.py -q -s --no-cov
```

Then compare the test with:

- [manual-4min-mock-short.md](./manual-4min-mock-short.md)

That pair is the best current onboarding reference because it shows both the human steps and the executable assertions.
