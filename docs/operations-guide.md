# Operations Guide — film-pipeline-langgraph

The maintained practical docs now live in `docs/`.

Start here:

- [docs/README.md](./README.md)
- [OpenClaw MCP Operator Guide](./openclaw-mcp-operator-guide.md)
- [Runbook - First Film](./runbook-first-film.md)
- [Release Process](./release-process.md)

Core commands:

```bash
make setup
make ci-check
make run-mcp
make release-check
uv run --python 3.12 --group dev pytest tests/smoke/test_manual_4min_mock_short.py -q -s --no-cov
```
