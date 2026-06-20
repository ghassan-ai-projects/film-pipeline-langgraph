# Getting Started

## Prerequisites

- Python 3.12+
- `uv`
- Git

Optional for real provider work:

- `OPENROUTER_API_KEY`
- `GOOGLE_API_KEY`

## First Setup

```bash
git clone <repo-url>
cd film-pipeline-langgraph
make setup
make ci-check
```

## Useful Commands

```bash
make run-mcp
make demo-project
make test
make test-e2e
make release-check
```

## Fastest Safe Validation

If you want one quick confidence check:

```bash
uv run --python 3.12 --group dev pytest tests/smoke/ -q --no-cov
```

If you want one end-to-end reference walkthrough:

```bash
uv run --python 3.12 --group dev pytest tests/smoke/test_manual_4min_mock_short.py -q -s --no-cov
```

Then read:

- [manual-4min-mock-short.md](./manual-4min-mock-short.md)
- [onboarding.md](./onboarding.md)
