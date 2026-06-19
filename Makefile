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
        ci-check clean

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

precommit: ## Run all pre-commit hooks
	$(UV_RUN) pre-commit run --all-files

hooks: ## Install the pre-commit git hook
	$(UV_RUN) pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push

ci-check: format-check lint typecheck test build ## Run the full CI pipeline locally
	@echo "  CI check passed"

clean: ## Remove local caches and build artifacts
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache .venv
	rm -rf build dist htmlcov
	rm -rf src/*.egg-info src/*/*.egg-info