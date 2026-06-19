# Phase 00 — Project Scaffolding

**Depends on:** Nothing
**Blocks:** All subsequent phases

---

## Goal

Scaffold the Python project from `~/my-projects/python-project-blueprint` with all quality gates, CI, and tooling in place. Establish the package structure that all subsequent phases build into.

---

## Deliverables

### Files to Create

- [ ] `pyproject.toml` — renamed from blueprint: `name = "film-pipeline"`, package `film_pipeline`, add initial dependencies (langgraph, pydantic, mcp)
- [ ] `Makefile` — copied from blueprint verbatim, `PACKAGE` updated
- [ ] `.pre-commit-config.yaml` — copied from blueprint
- [ ] `.python-version` — `3.12`
- [ ] `.editorconfig` — copied from blueprint
- [ ] `.gitignore` — blueprint version + generated assets (`generated-assets/`, `references/`, `versions/`, `state/`)
- [ ] `AGENTS.md` — project-specific agent rules (bridge to blueprint's AGENTS.md patterns)
- [ ] `CONTRIBUTING.md` — copied from blueprint, adapted
- [ ] `SECURITY.md` — copied from blueprint
- [ ] `src/film_pipeline/__init__.py` — package init with `__version__`
- [ ] `src/film_pipeline/py.typed` — PEP 561 marker
- [ ] `tests/test_smoke.py` — smoke test proving package imports
- [ ] `.github/workflows/ci.yml` — CI pipeline from blueprint
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` — from blueprint
- [ ] `.github/dependabot.yml` — from blueprint
- [ ] `.agents/context/` — context files adapted for film-pipeline (architecture, project, testing, python-style, review-checklist)
- [ ] `.agents/prompts/` — prompt templates from blueprint

### Files to Modify

- [ ] `README.md` — update to reflect new package structure and tooling

### Directories to Create

- [ ] `src/film_pipeline/` with sub-package stubs: `config/`, `schemas/`, `artifacts/`, `graph/`, `kb/`, `agents/`, `review/`, `validation/`, `providers/`, `checkpoints/`, `mcp/`, `post/`
- [ ] `tests/unit/`, `tests/integration/`, `tests/e2e/`
- [ ] `profiles/` — empty for now

---

## Task Checklist

- [ ] Copy `pyproject.toml` from blueprint, rename to `film-pipeline` / `film_pipeline`
- [ ] Add dependencies: `langgraph>=0.2`, `pydantic>=2`, `mcp>=1.0`, `pyyaml>=6.0`
- [ ] Add dev dependencies from blueprint (coverage, mypy, pre-commit, pytest, pytest-cov, ruff)
- [ ] Copy `Makefile`, update `PACKAGE = film_pipeline`
- [ ] Copy `.pre-commit-config.yaml`
- [ ] Copy `.python-version`, `.editorconfig`, `.github/` directory
- [ ] Update `.gitignore` with film-specific entries
- [ ] Create `src/film_pipeline/__init__.py` and `py.typed`
- [ ] Create sub-package `__init__.py` stubs for all planned modules
- [ ] Create `tests/test_smoke.py`
- [ ] Write `AGENTS.md` with project-specific rules
- [ ] Write `.agents/context/` files for film-pipeline
- [ ] Run `uv sync --group dev`
- [ ] Run `make hooks`
- [ ] Run `make ci-check` — must pass

---

## Acceptance Criteria

- [ ] `uv sync --group dev` succeeds
- [ ] `make ci-check` passes (format-check, lint, typecheck, test, build)
- [ ] `import film_pipeline` works
- [ ] Pre-commit hooks installed and passing
- [ ] CI workflow runs on push/PR to main
- [ ] 90% coverage maintained
- [ ] `mypy --strict` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| Dependency conflicts between langgraph/pydantic/mcp | Pin versions, test import before committing |
| Blueprint assumes no app dependencies | Add as `dependencies` not `dev`, justify in AGENTS.md |
