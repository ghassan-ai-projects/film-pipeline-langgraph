# AGENTS.md — Film Pipeline LangGraph

Canonical instructions for coding agents in this repository. Read this file first, then load only the context files needed for the task.

## Purpose

This repository implements the **LangGraph Film Studio** described in `documentation/`. It is an MCP-first, LangGraph-orchestrated, multi-agent system that drives a film from idea through delivery with mandatory human review gates.

The architectural source of truth is `documentation/architecture-blueprint.md`. Hard acceptance and product-completion standards are in `documentation/product-completion/` and `documentation/product-completion-plan/`. Read those before writing code.

## Engineering Priorities

1. Correctness and safety.
2. Simplicity of design and implementation.
3. Test evidence for changed behavior.
4. Consistency with the docs and existing patterns.
5. Speed of implementation.

If two options both work, choose the one that is easier to read, easier to test, and easier for the next agent to extend.

## Plan First

Before editing code, plan: files to touch, why each is needed, validation commands, risks.

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

The 12 sub-packages under `src/film_pipeline/` map 1:1 to implementation phases. `graph` and `mcp` may import across all sub-packages; domain modules must not import each other directly — they communicate through `artifacts`.

| Sub-package | Phase |
|-------------|-------|
| `config` | 03 — Profile loading, merging |
| `schemas` | 01 — Pydantic contracts |
| `artifacts` | 04 — Versioned storage |
| `graph` | 05 — LangGraph state machine |
| `kb` | 06 — Knowledge base |
| `agents` | 07 — Agent registry, prompts |
| `review` | 08 — Review packages |
| `validation` | 09 — Validator registry |
| `providers` | 10, 13 — Provider adapters |
| `checkpoints` | 11 — Checkpoints, resume |
| `mcp` | 02 — MCP tool surface |
| `post` | 14 — Post-production |

## Operating Rules

- Keep changes scoped to a single phase unless the change spans phases deliberately.
- Do not overwrite user changes. Prefer straightforward solutions over clever ones.
- Do not add abstractions, helpers, or dependencies unless they remove repeated or proven complexity.
- For production-code changes, add or update tests in the same change.
- Keep repo facts in files, not in chat history.

## Forbidden Changes

- No secrets, credentials, or machine-specific private data.
- No network calls in unit tests (mark them `integration` or `e2e`).
- No abstraction layers "for future flexibility" without a current concrete need.
- No bypassing the MCP-first contract to expose internal APIs.
- No paid providers before Phase 12 E2E baseline passes.

## Done

A task is done when: scope is complete with no unrelated refactors, the simplest correct change fits requirements, production changes have tests (90% coverage), `make ci-check` passes, docs are updated when behavior changes, and secrets are not added.

Before handoff: re-read changed files for vague guidance, confirm tests prove behavior (not just coverage), run validation, and summarize remaining risks.
