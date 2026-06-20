# Runbook — First Film

The maintained walkthrough now lives here:

- [documentation/manual-4min-mock-short.md](../documentation/manual-4min-mock-short.md)

Use that document for the practical operator flow.

Use this executable companion to verify the same path:

```bash
uv run --python 3.12 --group dev pytest tests/smoke/test_manual_4min_mock_short.py -q -s --no-cov
```

This repo’s current practical workflow stops before real clip generation and before in-repo final assembly.
