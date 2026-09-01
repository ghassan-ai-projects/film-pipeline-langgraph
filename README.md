# film-pipeline-langgraph

> **Author:** [Ghassan Alhamoud](https://ghassan-alhamoud.com)

LangGraph-based film creation pipeline for taking a film idea through structured pre-production, generation planning, QC evidence, and validated handoff state.

The supported product target is:

- `idea -> approved artifacts -> generation planning -> QC-ready project state`
- MCP-first operation
- prompt-governed critical-path agents
- git-backed checkpoints, rollback, audit, and validation visibility

The current target does not include in-repo final editorial finishing, audio, color, or delivery export.

## Quick Start

```bash
make setup      # uv sync --group dev
make ci-check   # format + lint + test (90% coverage) + build + product-gate
```

Run the pipeline headlessly from an idea file:

```bash
uv run film-pipeline-run my-idea.txt
```

Run the terminal operator console:

```bash
uv run film-pipeline-tui
```

Equivalent module entry point:

```bash
uv run python -m film_pipeline.tui.app
```

## Current Status

The repository implements an 8-phase architecture optimization across the full
pipeline. All phases are committed and passing CI:

| Phase | Feature | Status |
|-------|---------|--------|
| 0 | Agent profile routing, quality instructions, model retry wrapper | ✅ |
| 1 | Real human gates via `interrupt()` + `MemorySaver` checkpointer | ✅ |
| 2 | Typed state contract (`StudioGraphState`) + partial-update nodes | ✅ |
| 3 | Auto-increment artifact versions + `built_from` dependency tracking | ✅ |
| 4 | Living Master Film Matrix via versioned downstream patches | ✅ |
| 5 | Structured repair feedback (`RepairFeedback` schema) | ✅ |
| 6 | Per-phase scoped context packets | ✅ |
| 7 | QC subgraph with `Send` API parallel validator fan-out | ✅ |
| 8 | Advanced sampling (`top_p` + `frequency_penalty`) | ✅ |

Key architectural changes from the baseline:
- Human gates use real LangGraph `interrupt()` — no more `GraphRecursionError`
  workaround. `approve_phase` / `request_revision` resume the graph via
  `Command(resume=…)`.
- `StateGraph(dict)` replaced with `StateGraph(StudioGraphState)` — typed
  state with append-only reducers for `artifact_refs`, `issues`, and
  `validation_report_refs`.
- All phase nodes return partial updates; deep-copy eliminated.
- `_save_artifact()` auto-increments versions — repair never overwrites.
- Downstream phases emit `MatrixPatch` artifacts updating individual matrix
  rows — the matrix is now living, not a frozen artifact.
- QC validators run in parallel via LangGraph `Send` API fan-out.
- Agent prompts receive only phase-relevant context (not all 8 artifacts).
- Creative agents use `frequency_penalty=0.3` to reduce repetition.
- Graph state persists to `.graph_state.json` for crash recovery.
- Fix stall infinite loop in `after_approval()` — stalled phases offer
  "escalate" action instead of looping repair → approval.

- critical-path agents execute through dedicated prompt templates
- runtime approvals create checkpoints and audit events
- artifacts, routing decisions, and validation reports are inspectable through MCP
- the orchestrator routes based on provider health, budget state, failure
  decisions, pending revisions, and candidate vs approved artifact baselines
- non-video generation lifecycle is behavior-tested
- manual finishing is expected to happen outside the repo

## Running

```bash
# Smoke test
python -m film_pipeline.app.smoke

# Run all tests
make test

# Run specific test markers
pytest -m e2e          # end-to-end
pytest -m integration  # integration

# Build package
make build
```

### Film Studio TUI

`film-pipeline-tui` is the terminal interface for making a film end to end —
create a project, review every scene, run generation, and reach delivery
without leaving the terminal.

```bash
uv run film-pipeline-tui             # start the studio
uv run film-pipeline-tui --create    # jump straight into project creation
uv run python -m film_pipeline.tui.app   # equivalent module entry point
```

The default gateway is **in-process** (shared application service layer). It does
not require network access or provider keys for mock-mode project creation. To
use the MCP stdio gateway instead, set `FILM_PIPELINE_TUI_GATEWAY=mcp`.

#### How it works

The studio has two screens:

- **Project gallery** — pick a project or create a new one (`n`).
- **Studio workspace** — one screen with three panes:
  - **Pipeline rail** (left): all eleven stages with status glyphs
    (`✔` done, `▸` current, `·` upcoming, `!` blocking issues). Click a stage
    to browse its artifacts.
  - **Content tabs** (center): `Scenes`, `Artifacts`, `Assets`, `Issues`
    (keys `1`–`4`). The most useful tab is selected automatically for the
    current stage — scenes during scripting, assets during generation.
  - **Reader** (right): whatever you select — a scene, an artifact, an asset —
    renders here as readable, screenplay-style text. Review the whole script
    scene by scene without an external editor.

An action bar under the workspace shows only the actions that are eligible
right now (approve, request revision, validate, generate), and a one-line
status bar reports what happened last.

Typical flow: `n` → fill in id/title/idea → `Create` (or `F2`) → review each
stage's output in the reader → `a` to approve (or `r` to request a revision
with a note) → `g` when you reach generation → `o` on an asset to open the
rendered clip → approve through QC/post/delivery. Done.

Keyboard shortcuts: `n` new project, `a` approve, `r` request revision,
`v` validate, `g` generate, `1`–`4` switch content tabs, `o` open selected
asset, `f5` refresh, `escape` home, `q` quit. Press `/` for the command
palette (`project <id>`, `stage <name>`, `revise <note>`, `assets`, `home`,
`help`).

State is persisted to `~/.film-pipeline/` (runtime state and graph checkpoints)
and `projects/` (artifacts), so existing projects are loaded when the TUI starts.

#### Real-provider mode

Real mode uses Seedance via OpenRouter and Veo/Imagen via Google. Configure keys
in a local `.env` file or environment:

```bash
OPENROUTER_API_KEY=...
GOOGLE_API_KEY=...
```

Chat agents retain the existing DeepSeek/Gemini routing defaults. The z.ai
adapter is opt-in: set a profile's `primary` model to
`zai/glm-5.3-flash` in the resolved project configuration, then provide
`ZAI_API_KEY`. OpenRouter/Gemini remain configured for media lanes and model
fallbacks:

```bash
ZAI_API_KEY=...  # only needed when a configured profile uses zai/<model>
# Coding-plan keys ONLY work against the coding endpoint — with the default
# endpoint they fail with error 1113 "Insufficient balance".
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
```

For example, opt one profile into z.ai without changing the adapter or the
other profiles:

```yaml
model_profiles:
  creative_writer:
    primary: zai/glm-5.3-flash
```

Then launch in real mode:

```bash
uv run film-pipeline-tui --real
```

To verify the optional z.ai adapter without running media generation:

```bash
RUN_REAL_E2E=1 uv run pytest tests/integration/providers/test_zai_llm_live.py \
  -v -s -n 0 --no-cov
```

The live checks are excluded from `make test-integration` and must be enabled
explicitly because they call the configured provider.

Generation with real providers incurs cost and polling latency.

### Headless CLI

`film-pipeline-run` drives the full pipeline from a single idea file with no
human gates. It creates a project, submits the idea, and auto-approves every
phase gate until the requested target phase.

Supported idea file formats: `.txt`, `.md`, `.pdf`.

```bash
# Mock mode (default) — fast, zero-cost, no confirmation needed
uv run film-pipeline-run my-idea.txt

# Real providers — requires configured keys and explicit confirmation
uv run film-pipeline-run my-idea.md --runtime-mode real --confirm-real

# Or confirm via environment variable (useful in scripts / CI)
FILM_PIPELINE_CONFIRM_REAL=1 uv run film-pipeline-run my-idea.md --runtime-mode real

# Custom target phase, runtime, and scene count
uv run film-pipeline-run my-idea.pdf \
  --target-phase shot_bible \
  --target-runtime-seconds 180 \
  --target-scene-count 12
```

By default the CLI stops after `shot_bible`, producing candidate artifacts
across intake, constitution, development, script, visual_dev, and shot_bible.

## Documentation

Practical docs live in [documentation/README.md](documentation/README.md).

- Architecture blueprint: [documentation/architecture-blueprint.md](documentation/architecture-blueprint.md)
- OpenClaw MCP operator guide: [documentation/openclaw-mcp-operator-guide.md](documentation/openclaw-mcp-operator-guide.md)

Hard acceptance and product-completion docs live in [documentation/product-completion/README.md](documentation/product-completion/README.md) and [documentation/product-completion-plan/README.md](documentation/product-completion-plan/README.md).

## MCP Surface

- **Project:** `create_film_project`, `list_projects`, `find_project`, `set_active_project`, `get_active_project`, `get_project_summary`
- **Intake:** `submit_idea`, `get_intake_analysis`, `approve_intake`
- **State:** `get_current_phase`, `get_film_state`, `get_orchestrator_summary` (route reason, candidate/approved refs, pending revisions, review cycles, provider health, budget, failures), `get_next_actions`, `get_blockers`
- **Review:** `review_phase_artifacts`, `approve_phase`, `request_revision`
- **Artifact:** `list_artifacts`, `inspect_artifact`, `list_shots`, `inspect_shot`, `inspect_scene`, `inspect_reference`
- **Validation:** `get_validation_report`, `list_validation_issues`
- **Generation:** `generate_reference_images`, `plan_generation_batch`, `approve_generation_spend`, `start_generation_batch`, `get_generation_status`, `resume_generation_polling`, `list_active_generations`, `cancel_generation_request`, `promote_test_to_production`
- **KB:** `kb_search`, `kb_get_item`, `kb_get_context_packet`, `kb_explain_context_choice`
- **Checkpoint:** `list_checkpoints`, `create_checkpoint`, `get_checkpoint`, `compare_versions`, `list_artifact_versions`, `rollback_artifact`, `rollback_to_checkpoint`, `get_invalidation_report`
- **Audit:** `get_audit_log`, `explain_last_decision`, `explain_agent_routing`, `explain_kb_context`
- **Provider:** `check_provider_health`, `resolve_provider_block`, `list_providers`
- **Coverage:** `plan_coverage_group`, `list_coverage_groups`, `inspect_coverage_group`, `approve_coverage_generation`
- **Assembly:** `assemble_review_cut`, `assemble_final_cut`, `export_delivery_package`

## Requirements

- Python ≥ 3.12
- `uv` for package management
- Git for checkpoint operations
- Optional: provider keys via environment variables or a local `.env` file
- `OPENROUTER_API_KEY` for real Seedance/OpenRouter calls
- `GOOGLE_API_KEY` for Gemini Imagen 4 and Veo-family adapters
- `ZAI_API_KEY` when a configured profile uses a z.ai chat model
  (`glm-5.3-flash`); ordinary z.ai keys use `https://api.z.ai/api/paas/v4`, while coding-plan keys use
  `https://api.z.ai/api/coding/paas/v4`
