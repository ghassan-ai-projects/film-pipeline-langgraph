# Operations Guide — film-pipeline-langgraph

The maintained practical docs now live in `documentation/`.

Start here:

- [documentation/getting-started.md](../documentation/getting-started.md)
- [documentation/repository-structure.md](../documentation/repository-structure.md)
- [documentation/onboarding.md](../documentation/onboarding.md)
- [documentation/manual-4min-mock-short.md](../documentation/manual-4min-mock-short.md)

Core commands:

```bash
make setup
make ci-check
make run-mcp
make release-check
uv run --python 3.12 --group dev pytest tests/smoke/test_manual_4min_mock_short.py -q -s --no-cov
```
