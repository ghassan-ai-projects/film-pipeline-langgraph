# film-pipeline-langgraph

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

### Terminal Operator Console (Cockpit)

The TUI is a keyboard-first operator cockpit for creating a project from an idea,
reviewing generated artifacts, approving phases, requesting revisions, running
generation, and inspecting checkpoints, providers, audit events, and artifacts.

Start it from the repository root:

```bash
uv run film-pipeline-tui
```

Or start directly from the module:

```bash
uv run python -m film_pipeline.tui.app
```

To open directly into project creation:

```bash
uv run film-pipeline-tui --create
```

The default gateway is **in-process** (shared application service layer). It does
not require network access or provider keys for mock-mode project creation. To
use the MCP stdio gateway instead, set `FILM_PIPELINE_TUI_GATEWAY=mcp`.

#### Tabs

Press the number key to switch tabs:

| Key | Tab | Purpose |
|-----|-----|---------|
| `1` | **Dashboard** | Project rail, KPIs, pipeline table, and phase detail |
| `2` | **Review** | Current-phase artifacts, approval/revision, comments |
| `3` | **Generate** | Generation ledger: plan, approve spend, start, poll |
| `4` | **Scenes** | Scene list and per-scene shots |
| `5` | **Assets** | Generated clips, frames, reference images, manifest |
| `6` | **Matrix** | Living master film matrix |
| `7` | **Guide** | Command reference and shortcuts |
| `8` | **Validation** | Validator reports and QC issues |
| `9` | **Ops** | Checkpoints, provider health, audit log |

#### Action keys

| Key | Action |
|-----|--------|
| `n` | New project from idea |
| `i` | Submit / revise idea |
| `a` | Approve current phase (press once to prepare, twice to confirm) |
| `y` | Confirm approval (alternative to second `a`) |
| `r` | Request revision |
| `G` | Run generation (plan → approve spend → start → poll loop) |
| `V` | Run validation on demand |
| `c` | Add operator comment on selected target |
| `/` | Open command palette |
| `f5` | Refresh snapshot |
| `q` | Quit |

#### Basic create-from-idea flow

1. Press `n` (or run with `--create`) and fill in `project id`, `title`, optional
   `slug`, runtime mode `mock`/`real`, workflow mode `manual`, and the film idea.
   You can also type `/` then `create id | title | idea`.
2. The cockpit creates the project, submits the idea, runs intake, and opens the
   Dashboard.
3. Press `2` to open the Review tab and inspect the current phase artifacts.
4. Press `a` then `a` (or `a` then `y`) to approve and advance.
5. When you reach the **Generate** tab (`3`), press `G` to plan, approve spend,
   start, and poll the batch.
6. Visit **Assets** (`5`) to view delivered clips/frames and **Validation** (`8`)
   for QC reports.
7. Continue approving until the project reaches **delivery**.

#### Real-provider mode

Real mode uses Seedance via OpenRouter and Veo/Imagen via Google. Configure keys
in a local `.env` file or environment:

```bash
OPENROUTER_API_KEY=...
GOOGLE_API_KEY=...
```

Then launch in real mode with the `local-real-provider` profile:

```bash
FILM_PIPELINE_MCP_MODE=real uv run film-pipeline-tui
```

Generation with real providers incurs cost and polling latency. The cockpit shows
provider health and budget state in the Ops tab (`9`).

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
