# Release Process — film-pipeline-langgraph

## Version Policy

- `pyproject.toml` `version` field is the source of truth
- Bump version before release:
  - Patch: bug fixes, doc updates, internal changes (e.g., `0.2.0` → `0.2.1`)
  - Minor: new features, unstubbed tools, phase completions (e.g., `0.2.0` → `0.3.0`)
  - Major: breaking API changes, provider contract changes (e.g., `0.x` → `1.0`)
- Update `version` in `pyproject.toml` and commit as `chore: bump version to X.Y.Z`

## Pre-Release Checklist

```bash
# 1. All quality gates pass
make ci-check

# 2. Product gate passes (stub detection, manifest checks)
make product-gate

# 3. No unexpected stubs in critical paths
uv run --python 3.12 --group dev pytest tests/unit/app/test_product_gate.py -v

# 4. All 10 E2E scenarios pass with meaningful assertions
make test-e2e

# 5. Docs match code
# - documentation/README.md is current
# - documentation/operations-guide.md matches the repo workflow
# - documentation/runbook-first-film.md matches the executable smoke test
# - README.md is up to date

# 6. No secrets in code, docs, or artifacts
uv run --python 3.12 --group dev pytest tests/integration/providers/test_secret_redaction.py -v

# 7. Build succeeds
make build
```

## Build and Publish

```bash
make build                          # Builds source dist + wheel → dist/
ls dist/film_pipeline-*.tar.gz      # Source distribution
ls dist/film_pipeline-*.whl         # Wheel
```

For PyPI (if publishing):
```bash
uv run twine check dist/*
uv run twine upload dist/*
```

## CI Pipeline

`.github/workflows/ci.yml` runs:
- Python 3.12 + 3.13 matrix
- `uv sync --group dev --frozen`
- `make ci-check` (format-check → lint → mypy strict → pytest 90% → build)
- Pre-commit hooks on push (ruff format, lint, mypy) and pre-push (pytest + build)

## Release Notes

Release notes go in the GitHub release. For each release, document:

- Phase completion status (which phases are done)
- New unstubbed MCP tools
- New validators or agents
- Breaking changes (if any)
- Known limitations (video-adjacent stubs, mock providers)

## Acceptance Gate

Before declaring product-complete, verify against `documentation/product-completion-plan/acceptance-checklist.md`:

```
make product-gate
```

All items under "Final Ship Checklist" must be green:
- product gate green
- lint green
- mypy green
- tests green
- coverage >= 90%
- build green
- docs match commands and product behavior
- no core functionality missing under the allowed-stub policy

## Documentation Entry Point

Practical documentation lives in:

- [documentation/README.md](./README.md)
