# Demo Guide — film-pipeline-langgraph

For the maintained demo path, use:

- [docs/README.md](./README.md)

Fast commands:

```bash
make demo-project
uv run --python 3.12 --group dev pytest tests/smoke/test_manual_4min_mock_short.py -q -s --no-cov
make test-e2e
```

The manual 4-minute mock short is now the best single demo because it is both human-readable and executable.
