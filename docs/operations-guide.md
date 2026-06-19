# Operations Guide — film-pipeline-langgraph

## Prerequisites

- Python 3.12+
- `uv` package manager (`pip install uv`)
- Git
- (Optional) OpenRouter API key for real LLM agent execution

## Quick Start

```bash
git clone <repo-url>
cd film-pipeline-langgraph
make setup          # uv sync --group dev
make hooks          # install pre-commit hooks
make ci-check       # verify everything works
```

## Running the MCP Server

```bash
make run-mcp
```

This starts the MCP server on stdio. Connect any MCP-compatible client.

## Mock Demo Flow

```bash
make demo-project
```

This runs a complete mock-mode project: create project → submit idea → approve through phases.

## Key Commands

| Command | What it does |
|---------|-------------|
| `make setup` | Install dependencies via `uv sync` |
| `make ci-check` | Full pipeline: format, lint, typecheck, test, build |
| `make test` | Run all tests with coverage |
| `make test-unit` | Unit tests only |
| `make test-e2e` | End-to-end scenario tests |
| `make run-mcp` | Start MCP server |
| `make format` | Auto-format with ruff |
| `make lint` | Check lint rules |
| `make typecheck` | Run mypy strict type checking |

## Project Structure

```
src/film_pipeline/
  agents/         # Agent contracts (mvp/) and implementations (impl/)
  app/            # Runtime, bootstrap, smoke tests, health checks
  artifacts/      # Versioned artifact storage
  checkpoints/    # Git-backed checkpoint system
  graph/          # LangGraph state machine
  kb/             # Knowledge base retrieval
  mcp/            # MCP tool surface
  post/           # Post-production agents
  providers/      # Provider adapters (mock + real)
  schemas/        # Pydantic v2 type contracts
  validation/     # Validator registry and implementations
```

## Profiles

- `profiles/mock-demo.yaml` — safe demo with mock providers (no API keys needed)
- `profiles/local-real-provider.yaml` — real provider configuration (requires `OPENROUTER_API_KEY` in `.env`)

## Environment

Copy `.env.example` to `.env` and set your keys:

```bash
cp .env.example .env
# Edit .env to add OPENROUTER_API_KEY
```

## Health Checks

```bash
# Verify environment is ready
python -m film_pipeline.app.bootstrap

# Check provider health
# (via MCP: check_provider_health tool)
```

## Recovery Procedures

### Rollback After Bad Change

```bash
# Via MCP:
# 1. list_checkpoints → find the checkpoint_id to restore
# 2. rollback_to_checkpoint → restore project state
# 3. get_invalidation_report → see what downstream artifacts need re-generation
```

### Provider Quota Exhausted

When a provider reports `BLOCKED_QUOTA`:
1. Check `check_provider_health` for status
2. Wait for quota reset or switch providers via `resolve_provider_block`
3. Resume generation from latest checkpoint

### Network Error After Job Submission

The generation ledger preserves `provider_job_id` before risky transitions.
If polling fails after submit:
1. `get_generation_status` → check if job exists on provider
2. `resume_generation_polling` → poll existing job (no duplicate submit)

## Test Scenarios

34 E2E scenarios cover:
1. Happy path (idea → review cut)
2. Script revision loop
3. Reference validation failure
4. Provider quota exhausted
5. Network error / no duplicate submit
6. Continuity drift detection
7. Rollback after bad change
8. KB policy conflict resolution
9. Active project ambiguity
10. Dynamic blocked/available path routing
