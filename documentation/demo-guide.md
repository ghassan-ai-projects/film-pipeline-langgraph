# Demo Guide — film-pipeline-langgraph

The fastest way to see the pipeline work is the automated smoke/E2E suite.

## One-command demos

```bash
# Full mock-mode pipeline (create → approve → generation → QC → delivery)
make test-e2e

# Manual 4-minute mock short (human-readable output)
uv run --python 3.12 --group dev pytest tests/smoke/test_manual_4min_mock_short.py -q -s --no-cov

# Create a demo project via CLI headless mode
make demo-project
```

The manual 4-minute mock short is now the best single demo because it is both
human-readable and executable.

## Real mode

Real mode exercises the live LLM agents and provider registry via the headless
CLI. Set keys first:

```bash
export GOOGLE_API_KEY=...
export OPENROUTER_API_KEY=...
# Optional: only when a configured model profile uses zai/<model>.
export ZAI_API_KEY=...
# Coding-plan keys only: ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
uv run film-pipeline-run my-idea.md --runtime-mode real --confirm-real
```

To verify a provider adapter without running media generation:

```bash
RUN_REAL_E2E=1 uv run pytest tests/integration/providers/test_zai_llm_live.py \
  -v -s -n 0 --no-cov
```

Generation with real providers incurs cost and polling latency.
