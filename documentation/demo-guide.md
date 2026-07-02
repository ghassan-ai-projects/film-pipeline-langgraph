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

## TUI cockpit demo (mock mode)

Launch the terminal cockpit:

```bash
uv run film-pipeline-tui
```

The default gateway is in-process and mock-mode requires no API keys.

### Keyboard walkthrough

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

### Scripted tmux mock session

A ready-to-run script is included:

```bash
./scripts/tui_tmux_mock_demo.sh
```

It launches the TUI in a detached tmux session, creates `tmux-demo`, approves
through the pipeline, runs generation with `G`, visits Assets/Scenes/Validation/Ops,
and captures rows 4-22 of the pane. The final capture shows:

```
phase 11/11: delivery (complete) | mock mode | providers 2/2 | next: film complete 🎬
```

To drive it manually with `tmux send-keys`:

```bash
SESSION=filmtui
tmux new-session -d -s $SESSION "cd $(pwd) && .venv/bin/python -m film_pipeline.tui.app"
sleep 2

# Create project via command palette
tmux send-keys -t $SESSION '/'
tmux send-keys -t $SESSION 'create demo-mock | Demo Mock | A 20-second demo about a lost key.'
tmux send-keys -t $SESSION Enter
sleep 6

# Approve phases until generation
for _ in {1..7}; do
  tmux send-keys -t $SESSION 'a' 'a'
  sleep 4
done

# Run generation batch
tmux send-keys -t $SESSION '3'  # Generate tab
sleep 1
tmux send-keys -t $SESSION 'G'  # plan → spend → start → poll
sleep 12

# Approve remaining phases
for _ in {1..5}; do
  tmux send-keys -t $SESSION 'a' 'a'
  sleep 4
done

# Inspect views
tmux send-keys -t $SESSION '5' '4' '8' '9'
sleep 2
tmux capture-pane -t $SESSION -p | sed -n '4,22p'
```

## TUI cockpit demo (real mode)

Real mode exercises the live provider adapters. Set keys first:

```bash
export OPENROUTER_API_KEY=...
export GOOGLE_API_KEY=...
FILM_PIPELINE_MCP_MODE=real uv run film-pipeline-tui
```

Because real generation costs money and polls for tens of seconds per clip, the
recommended real-mode demo uses the `local-real-provider` profile with a short
idea and then triggers `G` in the Generate tab. Watch the Ops tab (`9`) for
provider health and the Generate tab for batch progress.

For a fast, deterministic real-mode wiring test that does not spend money, run:

```bash
uv run --python 3.12 --group dev pytest tests/e2e/test_tui_real_mode.py -q -s --no-cov
```

This test runs the runtime in `server_mode="real"` with mocked provider adapters
so all views and the generation batch execute without network calls.
