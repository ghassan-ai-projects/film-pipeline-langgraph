# Manual 4-Minute Mock Short

This is the recommended human-readable walkthrough for the repository.

It matches one executable test:

```bash
uv run --python 3.12 --group dev pytest tests/smoke/test_manual_4min_mock_short.py -q -s --no-cov
```

## Goal

Run one short film from idea through the full pre-generation pipeline and into QC-ready state, without triggering actual clip generation.

This proves:

- project creation
- idea intake
- approval flow
- critical artifact creation
- prompt-governed agent execution
- generation planning
- spend approval bookkeeping
- checkpoint and audit evidence
- routing and validation visibility

## Chosen Film Idea

`A silent four-minute pilgrimage short follows a young walker crossing five changing fields while birds, rain, blossoms, and insects pass a single message between sky and earth.`

Why this idea fits:

- it is short
- it is visually driven
- it does not depend on heavy dialogue
- it maps well to the current mock-first artifact pipeline

## Manual Operator Sequence

1. Create a project
2. Set it active
3. Submit the idea
4. Approve intake
5. Approve through constitution, development, script, visual development, and shot bible
6. Reach generation planning
7. Inspect the generation-planning artifacts
8. Plan a mock generation batch
9. Approve spend
10. Advance into generation, then QC-ready state, without calling actual clip execution
11. Inspect project summary, audit, routing, checkpoints, and validation report

## MCP Tool Sequence

Use this exact sequence:

```text
create_film_project
set_active_project
submit_idea
approve_intake
approve_phase    # constitution -> development
approve_phase    # development -> script
approve_phase    # script -> visual_dev
approve_phase    # visual_dev -> shot_bible
approve_phase    # shot_bible -> gen_planning
inspect_artifact # cost_estimate in gen_planning
plan_generation_batch
approve_generation_spend
approve_phase    # gen_planning -> generation
approve_phase    # generation -> qc
get_project_summary
get_validation_report
explain_agent_routing
get_audit_log
list_checkpoints
```

## What To Inspect

Expected artifact IDs by this point:

- `project_profile`
- `film_constitution`
- `treatment`
- `scene_list`
- `story_bible`
- `script`
- `reference_index`
- `shot_matrix`
- `cost_estimate`
- `consensus_report` once QC is entered

Expected visible evidence:

- active project summary with artifact count
- git-backed checkpoints after approvals
- routing decisions with `template_id` and `model_profile`
- validation report available through MCP
- audit log entries for create, submit, approve, and checkpoint creation

## What This Walkthrough Intentionally Does Not Do

- no paid provider clip generation
- no final assembly
- no audio post
- no color
- no delivery export

Those are outside the current practical workflow you asked for.
