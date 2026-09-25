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
        ci-check ci-verify clean scratch-clean product-gate

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

test: ## Run all tests (fast, no coverage)
	$(UV_RUN) pytest --no-cov

test-unit: ## Run unit tests only (fast, no coverage)
	$(UV_RUN) pytest tests/unit tests/test_smoke.py --no-cov

test-integration: ## Run integration tests
	$(UV_RUN) pytest -m "integration and not real_provider" --no-cov

test-e2e: ## Run end-to-end tests
	$(UV_RUN) pytest -m e2e --no-cov

test-cov: ## Run pytest with coverage enforcement (90% threshold)
	$(UV_RUN) pytest --cov-report=term-missing

build: ## Build sdist and wheel
	uv build

run-mcp: ## Start the MCP server in mock mode (legacy alias)
	$(UV_RUN) python -m film_pipeline.mcp.server

run-mcp-mock: ## Start the MCP server in explicit mock mode
	FILM_PIPELINE_MCP_MODE=mock $(UV_RUN) python -m film_pipeline.mcp.server

run-mcp-real: ## Start the MCP server in explicit real mode
	FILM_PIPELINE_MCP_MODE=real $(UV_RUN) python -m film_pipeline.mcp.server

run-mcp-headless: ## Start MCP server in real mode (use auto-approve profile for headless runs)
	@echo "Tip: When creating projects, include 'auto-approve' in your profile stack to skip human gates."
	FILM_PIPELINE_MCP_MODE=real $(UV_RUN) python -m film_pipeline.mcp.server

demo-project: ## Create and run a demo project in mock mode
	$(UV_RUN) python -m film_pipeline.studio.smoke
	@echo "Demo project created and smoke test passed."

release-check: ## Run release validation (ci-check + smoke + docs)
	@echo "Running release checks..."
	@$(MAKE) ci-check
	@echo "Checking required profiles..."
	@test -f profiles/mock-demo.yaml || (echo "Missing profiles/mock-demo.yaml" && exit 1)
	@test -f profiles/local-real-provider.yaml || (echo "Missing profiles/local-real-provider.yaml" && exit 1)
	@echo "Checking required docs..."
	@test -f documentation/acceptance-checklist.md || (echo "Missing documentation/acceptance-checklist.md" && exit 1)
	@test -f documentation/product-completion-plan/acceptance-checklist.md || (echo "Missing documentation/product-completion-plan/acceptance-checklist.md" && exit 1)
	@test -f documentation/operations-guide.md || (echo "Missing documentation/operations-guide.md" && exit 1)
	@test -f documentation/runbook-first-film.md || (echo "Missing documentation/runbook-first-film.md" && exit 1)
	@test -f documentation/release-process.md || (echo "Missing documentation/release-process.md" && exit 1)
	@test -f documentation/demo-guide.md || (echo "Missing documentation/demo-guide.md" && exit 1)
	@echo "Checking app smoke test..."
	@$(UV_RUN) python -m film_pipeline.studio.smoke
	@echo "Checking pytest smoke tests..."
	@$(UV_RUN) pytest tests/smoke/ -q --no-cov
	@echo "  Release check passed"

product-gate: ## Enforce the working-product acceptance gate
	@echo "Running working-product gate..."
	@$(UV_RUN) python -m film_pipeline.cli.product_gate

precommit: ## Run all pre-commit hooks
	$(UV_RUN) pre-commit run --all-files

hooks: ## Install the pre-commit git hook
	$(UV_RUN) pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push

ci-check: format-check lint typecheck test-cov build product-gate ## Run the full CI pipeline locally
	@echo "  CI check passed"

ci-verify: format-check lint typecheck test-cov product-gate ## CI validation without packaging (used by GitHub Actions)
	@echo "  CI verify passed"

clean: ## Remove local caches and build artifacts
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache .venv
	rm -rf build dist htmlcov
	rm -rf src/*.egg-info src/*/*.egg-info

scratch-clean: ## Remove the developer scratch storage used by scripts/
	rm -rf .scratch
