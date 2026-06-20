# Documentation

This folder is the practical documentation layer for people using or extending the repository.

Use this folder first if you want to:

- get the project running locally
- understand the codebase layout
- follow one real end-to-end workflow
- onboard as a maintainer

Keep using `docs/` for:

- architecture source of truth
- hard product-completion standards
- phased implementation and acceptance tracking

## Read This First

- Product overview: [product-overview.md](./product-overview.md)
- Getting started: [getting-started.md](./getting-started.md)
- Repository structure: [repository-structure.md](./repository-structure.md)
- Code onboarding: [onboarding.md](./onboarding.md)
- Manual 4-minute mock short: [manual-4min-mock-short.md](./manual-4min-mock-short.md)

## Hard Acceptance References

- Product standard: [../docs/product-completion/00-product-standard.md](../docs/product-completion/00-product-standard.md)
- Product completion index: [../docs/product-completion/README.md](../docs/product-completion/README.md)
- Execution plan: [../docs/product-completion-plan/README.md](../docs/product-completion-plan/README.md)
- Acceptance checklist: [../docs/product-completion-plan/acceptance-checklist.md](../docs/product-completion-plan/acceptance-checklist.md)

## Verification Entry Points

- Full CI: `make ci-check`
- Release validation: `make release-check`
- Operator workflow smoke suite: `uv run --python 3.12 --group dev pytest tests/smoke/ -q --no-cov`
- Manual 4-minute walkthrough test:
  `uv run --python 3.12 --group dev pytest tests/smoke/test_manual_4min_mock_short.py -q -s --no-cov`
