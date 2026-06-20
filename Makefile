# ---------------------------------------------------------------------------
# film-pipeline-langgraph - Makefile
# ---------------------------------------------------------------------------
# Run `make help` to list all targets.
# Run `make ci-check` to run the full CI pipeline locally.
# ---------------------------------------------------------------------------

PYTHON ?= 3.12
PACKAGE ?= film_pipeline
UV_RUN = uv run --python $(PYTHON) --group dev

.DEFAULT_GOAL := help

.PHONY: help setup lock format format-check lint lint-fix typecheck test \
        test-cov test-unit test-integration test-e2e build precommit hooks \
        ci-check clean product-gate

help: ## Show this help message
	@echo "Available targets:"
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Create or update the project environment with dev dependencies
	uv sync --group dev

lock: ## Refresh the lockfile
	uv lock

format: ## Format code with Ruff
	$(UV_RUN) ruff format .

format-check: ## Verify formatting
	$(UV_RUN) ruff format --check .

lint: ## Run Ruff lint checks
	$(UV_RUN) ruff check .

lint-fix: ## Auto-fix Ruff lint findings
	$(UV_RUN) ruff check --fix .

typecheck: ## Run mypy in strict mode
	$(UV_RUN) mypy src tests

test: ## Run all tests with coverage
	$(UV_RUN) pytest

test-unit: ## Run unit tests only
	$(UV_RUN) pytest tests/unit tests/test_smoke.py

test-integration: ## Run integration tests
	$(UV_RUN) pytest -m integration

test-e2e: ## Run end-to-end tests
	$(UV_RUN) pytest -m e2e

test-cov: ## Run pytest and generate HTML coverage output
	$(UV_RUN) pytest --cov-report=html

build: ## Build sdist and wheel
	uv build

run-mcp: ## Start the MCP server (mock mode)
	$(UV_RUN) python -m film_pipeline.mcp.server

demo-project: ## Create and run a demo project in mock mode
	$(UV_RUN) python -m film_pipeline.app.smoke
	@echo "Demo project created and smoke test passed."

release-check: ## Run release validation (ci-check + smoke + docs)
	@echo "Running release checks..."
	@$(MAKE) ci-check
	@echo "Checking required profiles..."
	@test -f profiles/mock-demo.yaml || (echo "Missing profiles/mock-demo.yaml" && exit 1)
	@test -f profiles/local-real-provider.yaml || (echo "Missing profiles/local-real-provider.yaml" && exit 1)
	@echo "Checking required docs..."
	@test -f docs/acceptance-checklist.md || (echo "Missing docs/acceptance-checklist.md" && exit 1)
	@echo "Checking smoke test..."
	@$(UV_RUN) python -m film_pipeline.app.smoke
	@echo "  Release check passed"

product-gate: ## Enforce the working-product acceptance gate
	@echo "Running working-product gate..."
	@$(UV_RUN) python -m film_pipeline.app.product_gate

precommit: ## Run all pre-commit hooks
	$(UV_RUN) pre-commit run --all-files

hooks: ## Install the pre-commit git hook
	$(UV_RUN) pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push

ci-check: format-check lint typecheck test build product-gate ## Run the full CI pipeline locally
	@echo "  CI check passed"

clean: ## Remove local caches and build artifacts
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache .venv
	rm -rf build dist htmlcov
	rm -rf src/*.egg-info src/*/*.egg-info
