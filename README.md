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

### Terminal Operator Console

The TUI is a keyboard-first operator console for creating a project from an idea,
reviewing generated artifacts, approving phases, requesting revisions, and
inspecting checkpoints, providers, audit events, and artifacts.

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

Basic create-from-idea flow:

1. Choose `1. New project from idea`.
2. Enter `project id`, `title`, optional `slug`, runtime mode `mock`,
   workflow mode `manual`, and the film idea.
3. The console creates the project, submits the idea, runs intake, and opens the dashboard.
4. Use `4. Review workspace` to inspect the current phase.
5. Use `5. Approve phase` to advance, or `6. Request revision` to send notes.

The first implementation uses the in-process gateway over the shared
application service layer. It does not require network access or provider keys
for mock-mode project creation.

## Documentation

Practical docs live in [documentation/README.md](documentation/README.md).

- Product overview: [documentation/product-overview.md](documentation/product-overview.md)
- Getting started: [documentation/getting-started.md](documentation/getting-started.md)
- Repository structure: [documentation/repository-structure.md](documentation/repository-structure.md)
- Code onboarding: [documentation/onboarding.md](documentation/onboarding.md)
- Manual 4-minute mock short: [documentation/manual-4min-mock-short.md](documentation/manual-4min-mock-short.md)

Hard acceptance and product-completion docs remain in [docs/product-completion/README.md](docs/product-completion/README.md) and [docs/product-completion-plan/README.md](docs/product-completion-plan/README.md).

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
