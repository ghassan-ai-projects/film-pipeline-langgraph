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
make ci-check   # format + lint + mypy + test (90% coverage) + build
```

## Current Status

The repository is now centered on a clips-first workflow:

- critical-path agents execute through dedicated prompt templates
- runtime approvals create checkpoints and audit events
- artifacts, routing decisions, and validation reports are inspectable through MCP
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
- **State:** `get_current_phase`, `get_film_state`, `get_orchestrator_summary`, `get_next_actions`, `get_blockers`
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
