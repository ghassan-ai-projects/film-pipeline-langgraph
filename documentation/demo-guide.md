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

```bash
uv run film-pipeline-tui
```

The studio starts at a project gallery. Create or open a project to enter a
single studio workspace: pipeline stages on the left, content tabs
(`Scenes` / `Artifacts` / `Assets` / `Issues`, keys `1`–`4`) in the center, and a
reader pane on the right that renders whatever you select as readable,
screenplay-style text. The action bar under the workspace shows only the
actions eligible right now.

A complete mock-mode film, step by step:

| Step | Keys | What happens |
|------|------|--------------|
| Create project | `n`, fill the form, `F2` | Project created, intake runs |
| Read a stage's output | select a row, read right pane | Scene/artifact opens in the reader |
| Approve a phase | `a` | Pipeline advances; workspace follows |
| Request changes | `r`, type a note | Revision routed to the right agent |
| Generate | `g` (at the generation stage) | Plan → spend approval → render → poll |
| Open a clip | `o` on an asset row | Opens with the system player |
| Finish | `a` through QC/post/delivery | Status reaches `delivery — complete` |

A ready-to-run tmux mock session drives all of the above automatically:

```bash
./scripts/tui_tmux_mock_demo.sh
```

It launches the TUI in a detached tmux session, creates a project through the
form, approves phases with `a`, runs generation with `g`, switches to the
Assets tab, and captures the final pane.

The TUI persists runtime state and LangGraph checkpoints under `~/.film-pipeline/`
and project artifacts under `projects/`, so existing projects are loaded
automatically on startup.

## TUI demo (real mode)

Real mode exercises the live LLM agents and provider registry. Set keys first:

```bash
export OPENROUTER_API_KEY=...
export GOOGLE_API_KEY=...
export ZAI_API_KEY=...
# Coding-plan keys only: ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
uv run film-pipeline-tui --real
```

The included real-mode E2E test uses live agents for scripts and prompts but
swaps the video/image adapters to zero-cost mocks, so no clips or reference
images are generated:

```bash
FILM_PIPELINE_RUN_REAL_LLM=1 uv run --python 3.12 --group dev \
  pytest tests/e2e/test_real_tui_e2e.py -q -s --no-cov
```

To exercise actual provider adapters and generate real media, use the
`local-real-provider` profile, keep the idea short, and press `g` at the
generation stage. This incurs cost and polling latency.
