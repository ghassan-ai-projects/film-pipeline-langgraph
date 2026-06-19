# AGENTS.md — Film Pipeline LangGraph

Canonical instructions for coding agents in this repository. Read this file first, then load only the context files needed for the task.

## Purpose

This repository implements the **LangGraph Film Studio** described in `docs/`. It is an MCP-first, LangGraph-orchestrated, multi-agent system that drives a film from idea through delivery with mandatory human review gates.

The architectural source of truth is `docs/architecture-blueprint.md`. The phased implementation plan is `docs/implementation-plan/`. Read those before writing code.

## Engineering Priorities

1. Correctness and safety.
2. Simplicity of design and implementation.
3. Test evidence for changed behavior.
4. Consistency with the docs and existing patterns.
5. Speed of implementation.

If two options both work, choose the one that is easier to read, easier to test, and easier for the next agent to extend.

## Read Order

Before editing:

1. Read this file.
2. Read [README.md](README.md).
3. Check the worktree with `git status --short`.
4. Read the relevant phase file in `docs/implementation-plan/` (e.g. `01-schemas-registries.md`).
5. Read the relevant architectural doc in `docs/` for that phase.
6. Make a short plan before editing.

## Plan First

Before editing code, write a short plan covering:

- files to create or modify
- why each file is needed
- validation commands (`make ci-check` for production changes)
- risks or assumptions
- whether the test can be written before implementation

## Build, Test, and Lint

Primary commands:

```bash
make setup          # uv sync --group dev
make hooks          # install pre-commit hooks
make ci-check       # format-check + lint + typecheck + test + build
make test-unit      # unit tests only
make test-integration
make test-e2e
```

The full pipeline runs `make ci-check`: ruff format, ruff lint, mypy strict, pytest with 90% coverage, and `uv build`.

## Python Standards

- Add type hints to public functions, methods, and module-level constants.
- Prefer `pathlib.Path` over stringly-typed filesystem paths.
- Use Pydantic v2 for all schemas (never raw dicts across boundaries).
- Use `dataclass(frozen=True)` for internal value objects when Pydantic is overkill.
- Raise specific exceptions with actionable messages.
- Keep modules focused and side effects minimal.

## Sub-Package Boundaries

The 12 sub-packages under `src/film_pipeline/` map 1:1 to implementation phases. The orchestrator (`film_pipeline.graph`) and MCP (`film_pipeline.mcp`) are the only modules that may import across all sub-packages. Domain modules must not import each other directly; they communicate through artifacts stored in `film_pipeline.artifacts`.

| Sub-package | Phase | Purpose |
|-------------|-------|---------|
| `config` | 03 | Profile loading, merging, validation |
| `schemas` | 01 | Typed Pydantic contracts |
| `artifacts` | 04 | Versioned storage, manifests |
| `graph` | 05 | LangGraph state machine |
| `kb` | 06 | Knowledge base retrieval |
| `agents` | 07 | Agent registry, prompt runner |
| `review` | 08 | Review package generator |
| `validation` | 09 | Validator registry |
| `providers` | 10, 13 | Provider adapters (mock + real) |
| `checkpoints` | 11 | Checkpoints, resume, rollback |
| `mcp` | 02 | MCP tool surface |
| `post` | 14 | Post-production agents |

## Operating Rules

- Keep changes scoped to a single phase unless the change spans phases deliberately.
- Do not overwrite user changes.
- Prefer straightforward solutions over clever ones.
- Do not add new abstractions, helpers, or dependencies unless they remove repeated or proven complexity.
- Keep repo facts in files, not in chat history.
- For production-code changes, add or update tests in the same change.
- For production behavior changes, write the test before implementation when feasible.
- Explain new dependencies, generated artifacts, workflow permission changes, and public behavior changes in the final handoff.

## Forbidden Changes

- Do not add secrets, credentials, or machine-specific private data.
- Do not add network calls to unit tests (mark them `integration` or `e2e`).
- Do not add abstraction layers "for future flexibility" without a current concrete need.
- Do not replace direct code with indirection unless at least one current pain point is removed.
- Do not bypass the MCP-first contract to expose internal APIs to the outside.
- Do not connect paid providers before Phase 12 E2E baseline passes.

## Definition of Done

A task is done when:

- The requested scope is complete and the diff avoids unrelated refactors.
- The implementation is the simplest correct change that fits current requirements.
- Production-code behavior changes include meaningful tests (90% coverage maintained).
- `make ci-check` passes for code changes; narrower checks for docs-only changes.
- Documentation is updated when behavior, commands, or expectations change.
- Secrets are not added; security-sensitive changes are called out.

## Review Checklist

Before handoff:

1. Re-read changed files for vague or duplicated guidance.
2. Confirm `AGENTS.md` points to smaller context files instead of absorbing everything.
3. Confirm tests were added for production-code changes.
4. Confirm complexity was justified and unnecessary abstraction was avoided.
5. Confirm tests prove the changed behavior, not just raise coverage.
6. Run the relevant validation commands and record failures accurately.
7. Summarize changed files, validation, remaining risks, and suggested next improvements.