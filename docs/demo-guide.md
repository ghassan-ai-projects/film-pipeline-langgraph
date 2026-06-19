# Demo Guide — film-pipeline-langgraph

## 5-Minute Mock Demo

Run a complete film pipeline in mock mode (no API keys, no cost):

```bash
make demo-project
```

This executes:
1. Creates a project with a sample idea
2. Runs the LangGraph through intake → constitution → development → script
3. Each phase invokes real agent code with mock model responses
4. Artifacts are persisted to the artifact store
5. Phase approvals create git-backed checkpoints

## Inspect the Results

After `make demo-project`, you can inspect:

```bash
# List projects
# (via MCP: list_projects tool)

# Check current phase
# (via MCP: get_current_phase)

# List artifacts created
# (via MCP: list_artifacts)

# Inspect a specific artifact
# (via MCP: inspect_artifact --artifact_id film_constitution)

# View validation report
# (via MCP: get_validation_report)

# View audit log
# (via MCP: get_audit_log)
```

## What's Real vs Mock

| Layer | Status |
|-------|--------|
| Graph execution | Real — LangGraph state machine |
| Agent contracts | Real — 19 registered agents |
| Agent implementations | Real — 4 spine agents (Intake, Constitution, Development, Screenwriter) |
| Validator implementations | Real — ScriptStructure, DialogueVoice |
| Prompt framework | Real — RCTCO template rendering |
| Artifact storage | Real — Pydantic models persisted to disk |
| Checkpoints | Real — Git-backed with invalidation engine |
| MCP tools | Real — 31 wired, 20 stubbed |
| Model calls | Mock — canned responses (swap `ModelAdapter` for real OpenRouter) |
| Video generation | Mock — placeholder files (real generation requires provider API keys) |

## Switching to Real LLM

1. Set `OPENROUTER_API_KEY` in `.env`:
   ```
   OPENROUTER_API_KEY=sk-or-v1-...
   ```

2. The `PromptRunner` will auto-detect the key and call OpenRouter.
   Or pass a `ModelAdapter` explicitly via `GraphServices`.

## E2E Test Scenarios

Run all 34 E2E scenarios:

```bash
make test-e2e
```

Or a specific scenario:

```bash
uv run pytest tests/e2e/test_scenario_02_script_revision.py -v
```
