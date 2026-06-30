# Demo Guide — film-pipeline-langgraph

For the maintained demo path, use:

- [documentation/README.md](./README.md)

Fast commands:

```bash
make demo-project
uv run --python 3.12 --group dev pytest tests/smoke/test_manual_4min_mock_short.py -q -s --no-cov
make test-e2e
```

The manual 4-minute mock short is now the best single demo because it is both human-readable and executable.

## Interactive TUI

Launch the redesigned studio interface:

```bash
uv run --python 3.12 --group dev python -m film_pipeline.tui.app
```

The new interface starts at a project gallery. Create or open a project to enter
a three-pane studio workspace: pipeline stages on the left, contextual actions
and artifact/issue tables in the center, and an inspector on the right. Common
actions are always visible as buttons; press `/` for the command palette.

For real model generation, launch with `--real` after setting your API keys:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
export GOOGLE_API_KEY="..."
uv run --python 3.12 --group dev python -m film_pipeline.tui.app --real
```

The TUI persists runtime state and LangGraph checkpoints under `~/.film-pipeline/`
and project artifacts under `projects/`, so existing projects are loaded
automatically on startup.

See the operator guide for the full TUI walkthrough:
[openclaw-mcp-operator-guide.md](./openclaw-mcp-operator-guide.md).
