# Documentation

This folder is the practical documentation layer for people using or extending the repository.

Use this folder first if you want to:

- get the project running locally
- understand the codebase layout
- follow one real end-to-end workflow
- onboard as a maintainer

This folder is also where architecture source of truth, hard product-completion
standards, and phased implementation/acceptance tracking live (the old `docs/`
folder was retired and folded in here).

## Read This First

- Architecture blueprint: [architecture-blueprint.md](./architecture-blueprint.md)
- OpenClaw MCP operator guide: [openclaw-mcp-operator-guide.md](./openclaw-mcp-operator-guide.md)

## Operator & Release References

- Operations guide: [operations-guide.md](./operations-guide.md)
- Runbook (first film): [runbook-first-film.md](./runbook-first-film.md)
- Runbook (The Third Interval, pre-generation): [runbook-the-third-interval.md](./runbook-the-third-interval.md)
- Release process: [release-process.md](./release-process.md)
- Demo guide: [demo-guide.md](./demo-guide.md)
- Acceptance checklist: [acceptance-checklist.md](./acceptance-checklist.md)

## Hard Acceptance References

- Product standard: [product-completion/00-product-standard.md](./product-completion/00-product-standard.md)
- Product completion index: [product-completion/README.md](./product-completion/README.md)
- Execution plan: [product-completion-plan/README.md](./product-completion-plan/README.md)
- Acceptance checklist: [product-completion-plan/acceptance-checklist.md](./product-completion-plan/acceptance-checklist.md)

## Verification Entry Points

- Full CI: `make ci-check`
- Release validation: `make release-check`
- Operator workflow smoke suite: `uv run --python 3.12 --group dev pytest tests/smoke/ -q --no-cov`
- Manual 4-minute walkthrough test:
  `uv run --python 3.12 --group dev pytest tests/smoke/test_manual_4min_mock_short.py -q -s --no-cov`
