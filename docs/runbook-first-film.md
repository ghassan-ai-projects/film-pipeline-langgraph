# Runbook — First Film

Step-by-step walkthrough for producing your first film with the pipeline in mock mode
(no API keys, no cost). Each step is a real MCP tool invocation — every tool response
is backed by runtime state, not placeholders.

## Prerequisites

```bash
git clone <repo-url> && cd film-pipeline-langgraph
make setup
make ci-check   # verify everything works
```

## Step 1: Start the MCP Server

```bash
make run-mcp
```

This starts the MCP server on stdio. All subsequent steps use MCP tools.

## Step 2: Create a Project

```
Tool: create_film_project
Args: project_id="my-first-film", title="The Last Signal", slug="last-signal"
```

You now have an active project. Verify:

```
Tool: list_projects          → shows ["my-first-film"]
Tool: get_project_summary    → project metadata + empty artifact list
```

## Step 3: Submit an Idea

```
Tool: submit_idea
Args: idea="In a world without sound, a musician discovers a frequency that can heal."
```

The graph runs intake → produces a classified profile. Check:

```
Tool: get_intake_analysis    → shows classified genre, runtime, risks
Tool: get_current_phase      → "intake"
```

## Step 4: Review and Approve Intake

```
Tool: review_phase_artifacts  → lists intake artifacts
Tool: get_validation_report   → if any validators fired
Tool: get_next_actions        → eligible=["approve"], blocked=[]
Tool: approve_intake
```

Approval creates a git-backed checkpoint and advances to constitution phase.

## Step 5: Advance Through Constitution → Development → Script

Repeat the review-approve cycle for each phase:

### Constitution
```
Tool: approve_phase           → advances past intake
Tool: get_current_phase       → "constitution"
Tool: review_phase_artifacts  → see FilmConstitution artifact
Tool: approve_phase
```

### Development
```
Tool: get_current_phase       → "development"
Tool: review_phase_artifacts  → Treatment + SceneList artifacts
Tool: approve_phase
```

### Script
```
Tool: get_current_phase       → "script"
Tool: review_phase_artifacts  → StoryBible + Script artifacts
Tool: approve_phase
```

## Step 6: Inspect Your Film's Artifacts

```
Tool: list_artifacts           → all artifacts across all phases
Tool: inspect_artifact         → artifact_id="film_constitution" (view contents)
Tool: list_shots               → shots from the shot bible
Tool: inspect_scene            → scene_id="sc_001" (view a scene)
Tool: get_project_summary      → full project state
```

## Step 7: Validation and QC

```
Tool: get_validation_report    → 0+ validation reports with scores
Tool: list_validation_issues   → blocking issues (if any) + warnings
Tool: get_blockers             → what's preventing next phase
```

If validators find blocking issues, the phase won't advance until they're resolved.
Repairable findings route to repair behavior automatically.

## Step 8: Generation Planning (Non-Video)

```
Tool: plan_generation_batch    → creates ledger rows for each shot
  Args: provider="seedance", model="2.0", mode="test"

Tool: list_active_generations  → see all PREPARED rows
Tool: approve_generation_spend → mark rows SUBMITTED (budget gate optional)
  Args: max_cost_usd=5.00

Tool: start_generation_batch   → submit to provider (mock in demo mode)
Tool: resume_generation_polling → poll for completion
  Args: generation_id="gen:<project>:<shot>:<uuid>"
```

## Step 9: Promote to Production

```
Tool: promote_test_to_production  → moves TEST→PRODUCTION for completed rows
Tool: get_generation_status       → verify mode changed
```

## Step 10: Recovery and Audit

### View What Happened
```
Tool: get_audit_log           → every action timestamped
Tool: explain_agent_routing   → which agent handled each task and why
Tool: explain_last_decision   → most recent decision with reasoning
```

### Checkpoints and Rollback
```
Tool: list_checkpoints         → all git-backed checkpoints
Tool: create_checkpoint        → manual snapshot with reason
  Args: reason="Before risky style change"
Tool: rollback_to_checkpoint   → restore project to a checkpoint
  Args: checkpoint_id="..."
Tool: get_invalidation_report  → what downstream artifacts need re-generation
```

### Provider Issues
```
Tool: check_provider_health    → see block status
Tool: list_providers           → all registered providers
Tool: resolve_provider_block   → unblock a provider
```

## Step 11: Clip Handoff

```
Tool: assemble_review_cut      → build assembly plan from generated media
  Args: shot_ids=[...], clip_paths=[...]
Tool: inspect_artifact         → view assembly manifest
```

The clip handoff evidence (shot IDs, source asset refs, transitions, duration) is
sufficient for external finishing tools. No in-repo assembly or delivery export is
required for product completion.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| "No active project" | Run `set_active_project` first |
| Phase won't advance | Check `get_blockers` for blocking validation issues |
| Generation stuck | `get_generation_status` → `resume_generation_polling` |
| Duplicate submit fear | Ledger tracks `provider_job_id` — re-poll, don't re-submit |
| Wrong agent selected | `explain_agent_routing` shows routing decisions |

## Quick Reference: Full Happy Path

```
create_film_project → submit_idea → approve_intake → approve_phase (×3) →
plan_generation_batch → approve_generation_spend → start_generation_batch →
resume_generation_polling → promote_test_to_production → assemble_review_cut
```
