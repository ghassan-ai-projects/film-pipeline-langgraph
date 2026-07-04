# Demo Guide — film-pipeline-langgraph

The fastest way to see the pipeline work is the automated smoke/E2E suite or a
tmux-driven TUI session.

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

## Interactive TUI

The redesigned studio interface and the legacy cockpit are both available while
the redesign is being proven:

```bash
# Redesigned interface
uv run --python 3.12 --group dev python -m film_pipeline.tui.app

# Legacy cockpit
uv run --python 3.12 --group dev python -m film_pipeline.tui.cockpit
```

### New redesigned TUI

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

### Legacy cockpit

The legacy cockpit is a keyboard-first operator console with numbered tabs and a
command palette. Launch it with:

```bash
uv run film-pipeline-tui-legacy
```

The default gateway is in-process and mock-mode requires no API keys.

| Step | Keys | What happens |
|------|------|--------------|
| Create project | `n` | Fill `demo-1`, `Demo One`, idea, `mock` mode |
| Review phase | `2` | Inspect current-phase artifacts |
| Approve | `a` `a` | Prepare and confirm approval |
| Generate | `3` then `G` | Plan shots, approve spend, start, poll |
| View assets | `5` | Delivered clips + last/mid frames |
| QC | `8` | Validator reports |
| Ops | `9` | Checkpoints, provider health, audit |
| Finish | `a` `a` through delivery | Project reaches `delivery` |

A ready-to-run tmux mock session is included for the legacy cockpit:

```bash
./scripts/tui_tmux_mock_demo.sh
```

It launches the legacy TUI in a detached tmux session, creates `tmux-demo`,
approves through the pipeline, runs generation with `G`, visits
Assets/Scenes/Validation/Ops, and captures rows 4-22 of the pane. The final
capture shows:

```
phase 11/11: delivery (complete) | mock mode | providers 2/2 | next: film complete 🎬
```

A tmux demo for the redesigned studio is also available:

```bash
./scripts/tui_new_tmux_mock_demo.sh
```

It launches the redesigned TUI, creates a new project through the modal form,
approves phases with `a`, runs generation with `g`, opens the asset viewer via
the command palette, and captures the final pane.

## TUI cockpit demo (real mode)

Real mode exercises the live LLM agents and provider registry. Set keys first:

```bash
export OPENROUTER_API_KEY=...
export GOOGLE_API_KEY=...
FILM_PIPELINE_MCP_MODE=real uv run film-pipeline-tui
# or for the legacy cockpit
FILM_PIPELINE_MCP_MODE=real uv run film-pipeline-tui-legacy
```

The included real-mode E2E test uses live agents for scripts and prompts but
swaps the video/image adapters to zero-cost mocks, so no clips or reference
images are generated:

```bash
FILM_PIPELINE_RUN_REAL_LLM=1 uv run --python 3.12 --group dev \
  pytest tests/e2e/test_tui_real_mode.py -q -s --no-cov
```

To exercise actual provider adapters and generate real media, use the
`local-real-provider` profile, keep the idea short, and trigger `G` in the
Generate tab. Watch the Ops tab (`9`) for provider health and the Generate tab
for batch progress. This incurs cost and polling latency.
