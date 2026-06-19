# film-pipeline-langgraph

LangGraph-based film creation pipeline — a professional, human-supervised AI film studio operating system built MCP-first.

An orchestrator agent coordinates 19 expert agents, uses a curated knowledge base (12 items), validates work at multiple levels, and pauses for human review at every major phase.

## Quick Start

```bash
make setup      # uv sync --group dev
make ci-check   # format + lint + mypy + test (90% coverage) + build
```

## Architecture

```
MCP Surface (tools/)
       ↓
LangGraph State Machine (graph/)
       ↓
19 Agents (agents/) ← KB Context Packets (kb/) ← KB Manifest (12 items)
       ↓
Review Packages (review/) ← Human Approval Gates
       ↓
Validation (validation/) ← 15 Validators ← Consensus
       ↓
Providers (providers/) ← Mock (0 cost) ← Real (requires API keys)
       ↓
Checkpoints (checkpoints/) ← Git-backed ← Resume ← Rollback
       ↓
Post-Production (post/) ← Assembly, Audio, Delivery, Subtitles
```

## Phase Completion

| Phase | Description | Status |
|-------|-------------|--------|
| 00 | Scaffolding | ✅ |
| 01 | Schemas & Registries | ✅ |
| 02 | MCP Tool Contracts | ✅ |
| 03 | Config & Profile System | ✅ |
| 04 | Artifact Store | ✅ |
| 05 | LangGraph Skeleton | ✅ |
| 06 | KB Context Packet Builder | ✅ |
| 07 | Agent Registry & Prompt Runner | ✅ |
| 08 | Review Package Generator | ✅ |
| 09 | Validation Registry | ✅ |
| 10 | Mock Provider & Test Harness | ✅ |
| 11 | Checkpoint/Resume & Rollback | ✅ |
| 12 | E2E Happy Path | ✅ |
| 13 | Real Provider Adapter | ✅ |
| 14 | Post-Production Assembly | ✅ |
| 15 | Production Hardening | ✅ |
| 16 | Productization | ✅ |

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

## MCP Tools (33+ wired, 57 total)

The MCP surface drives the entire pipeline. Wired tools connect to the runtime backend; stubs return placeholder responses for tools pending full wiring.

- **Project:** `create_film_project`, `list_projects`, `find_project`, `set_active_project`, `get_active_project`, `get_project_summary`
- **Intake:** `submit_idea`, `get_intake_analysis`, `approve_intake`
- **State:** `get_current_phase`, `get_film_state`, `get_orchestrator_summary`, `get_next_actions`, `get_blockers`
- **Review:** `review_phase_artifacts`, `approve_phase`, `request_revision`
- **Artifact:** `list_artifacts`, `inspect_artifact`, `list_shots`, `inspect_shot`, `inspect_scene`, `inspect_reference`
- **Validation:** `get_validation_report`, `list_validation_issues`
- **Generation:** `plan_generation_batch`, `approve_generation_spend`, `start_generation_batch`, `get_generation_status`, `resume_generation_polling`, `list_active_generations`, `cancel_generation_request`, `promote_test_to_production`
- **KB:** `kb_search`, `kb_get_item`, `kb_get_context_packet`, `kb_explain_context_choice`
- **Checkpoint:** `list_checkpoints`, `create_checkpoint`, `get_checkpoint`, `compare_versions`, `list_artifact_versions`, `rollback_artifact`, `rollback_to_checkpoint`, `get_invalidation_report`
- **Audit:** `get_audit_log`, `explain_last_decision`, `explain_agent_routing`, `explain_kb_context`
- **Provider:** `check_provider_health`, `resolve_provider_block`, `list_providers`
- **Coverage:** `plan_coverage_group`, `list_coverage_groups`, `inspect_coverage_group`, `approve_coverage_generation`
- **Assembly:** `assemble_review_cut`, `assemble_final_cut`, `export_delivery_package`

## Key Conventions

- **MCP-first:** All operations through MCP tools, no direct API
- **Mock first:** No paid generation until E2E mock baseline passes
- **RCTCO prompts:** All agent prompts follow Role/Core Task/Context/Constraints/Output
- **Human gates:** Every phase pauses for human approval
- **Authority hierarchy:** canonical > active_playbook > case_study > raw_archive
- **Validation thresholds:** Pass ≥ 85, Review ≥ 75, Block < 60

## Docs

- [Architecture Blueprint](docs/architecture-blueprint.md)
- [Implementation Plan](docs/implementation-plan/)
- [Agent Architecture](docs/agent-architecture.md)
- [KB Operating Model](docs/kb-operating-model.md)

## Requirements

- Python ≥ 3.12
- `uv` for package management
- Git for checkpoint operations
- Optional: `OPENROUTER_API_KEY` for real provider calls (Seedance 2.0)
