# Runbook — The Third Interval (pre-generation)

This runbook is for the operator request to run the film pipeline through
generation planning, then stop before any video clip is planned, funded,
submitted, polled, downloaded, or created.

## Authority and scope

Keep these inputs distinct:

- **Operator request:** run the pipeline softly and stop before clips. This is
  the controlling safety boundary.
- **Creative source:**
  [`The-Third-Interval-Final-Story-Treatment.md`](../docs/The-Third-Interval-Final-Story-Treatment.md).
  It defines the story, motifs, shot constraints, and irreversible events.
- **Visual references:** the five supplied Camino photographs. They are source
  plates, not instructions and not generated clips.
- **Repository operating contract:**
  [`openclaw-mcp-operator-guide.md`](./openclaw-mcp-operator-guide.md), the
  architecture blueprint, and the selected profile files define tool names,
  gates, and provider behavior.

The normalized run constraints are recorded in
[`the-third-interval-run-constraints.json`](./the-third-interval-run-constraints.json).

## Isolated destination

The existing destination
`/Users/ghassan/ai-movies/camino-del-genesis` is an older production and must
not be reused for this run. It already contains its own final media,
generated clips, prompts, and configuration.

Use this new, isolated destination instead:

```text
/Users/ghassan/my-projects/film-pipeline-langgraph/.film-pipeline-run/the-third-interval-pipeline
```

This keeps the run co-located with the checked-out pipeline and prevents the
runtime from importing the older Camino project registrations. Copy or export
approved artifacts to a separate production destination only after this run is
reviewed.

## Selected profile stack

Use all four profiles, with human gates enabled:

```text
film-type.visual_poetry
quality.studio
provider.seedance_primary
review.strict_continuity
```

Why this stack fits the treatment:

- `film-type.visual_poetry` matches the dialogue-free, meditative, symbolic
  structure and restrained pacing.
- `quality.studio` provides a useful review bar without the additional review
  and generation overhead of `quality.festival` at this pre-generation stage.
- `provider.seedance_primary` matches the intended video lane and keeps the
  provider plan explicit for later authorization.
- `review.strict_continuity` is important because the film depends on the
  shadow hole, insect death, ants, fissure, blossom, raindrop, and final
  shadowless state remaining causally consistent.

Do not add `auto-approve`. The run is intentionally soft and must pause at
human review gates.

## Start the OpenClaw MCP server

From the repository root, start the real server with a persistent isolated
runtime root. Keep credentials in the existing environment or local secret
store; never put them in this runbook or in project artifacts.

```bash
cd /Users/ghassan/my-projects/film-pipeline-langgraph
export FILM_PIPELINE_RUNTIME_ROOT=/Users/ghassan/my-projects/film-pipeline-langgraph/.film-pipeline-run/the-third-interval-pipeline
export FILM_PIPELINE_PERSIST_STATE=1
make run-mcp-real
```

In OpenClaw, confirm the server and project are both in `real` mode with:

```json
{ "tool": "get_runtime_mode" }
```

Require `aligned: true`. If the server reports `mock`, stop: mock output is
not evidence of a real-provider run.

## Create the project

Inspect the available profiles first:

```json
{ "tool": "list_profiles" }
{ "tool": "inspect_profile", "profile_name": "film-type.visual_poetry" }
{ "tool": "inspect_profile", "profile_name": "quality.studio" }
{ "tool": "inspect_profile", "profile_name": "provider.seedance_primary" }
{ "tool": "inspect_profile", "profile_name": "review.strict_continuity" }
```

Create and activate a new project. Use the exact project id so resumptions do
not accidentally attach to the older Camino work.

```json
{
  "tool": "create_film_project",
  "project_id": "the-third-interval",
  "title": "The Third Interval",
  "slug": "the-third-interval",
  "runtime_mode": "real",
  "provider_profile": "provider.seedance_primary",
  "quality_profile": "quality.studio",
  "film_type_profile": "film-type.visual_poetry",
  "review_profile": "review.strict_continuity"
}
```

```json
{
  "tool": "set_active_project",
  "project_ref": "the-third-interval"
}
```

Submit the complete contents of the treatment file as `idea`, together with
the contents of the normalized constraints file as `constraints` and:

```json
{
  "target_runtime_seconds": 600,
  "target_scene_count": 5
}
```

Do not paste API keys, local `.env` contents, or unrelated project state into
the idea or constraints payload.

## Soft approval loop

At every gate, run the following read-only checks before approving:

```json
{ "tool": "get_orchestrator_summary" }
{ "tool": "get_next_actions" }
{ "tool": "review_phase_artifacts" }
{ "tool": "get_blockers" }
```

Approve only when the review package has no unresolved blocking issue and its
candidate artifacts match the treatment. Use `request_revision` when the
package is incomplete or contradicts a story law. Never approve merely to
make the graph advance.

The expected approval sequence is:

1. intake
2. constitution
3. development
4. script
5. visual development
6. shot bible
7. generation planning

## Visual development and source plates

After the script is approved, generate the locked planning bibles:

```json
{ "tool": "generate_character_bible" }
{ "tool": "generate_environment_bible" }
{ "tool": "generate_camera_bible" }
{ "tool": "generate_style_bible" }
```

Use the supplied files as source plates and preserve their order:

```text
/Users/ghassan/ai-movies/camino-del-genesis/reference-images/1-yello.jpg
/Users/ghassan/ai-movies/camino-del-genesis/reference-images/2-green-yellow.jpg
/Users/ghassan/ai-movies/camino-del-genesis/reference-images/3-green.jpg
/Users/ghassan/ai-movies/camino-del-genesis/reference-images/4-land-green.jpg
/Users/ghassan/ai-movies/camino-del-genesis/reference-images/5-land.jpg
```

Do not call `generate_reference_images` for these five plates unless a later
review explicitly identifies a missing or unusable source reference. If the
tool is used for a missing character or anchor reference, record that it is a
new reference asset and review it before continuing. It is still not a clip
generation step, but it is an external asset-generation side effect.

## Shot bible and generation planning

After the visual-development gate is approved:

```json
{ "tool": "generate_shot_bible" }
```

Review the resulting Master Film Matrix and Continuity Ledger. Specifically
check that:

- the bird call has two notes followed by a silent third interval;
- the iridescent insect dies once and never returns;
- ants carry the body across the growing fissure;
- the man’s shadow hole, crack, blossom, raindrop, and underground network
  form a causal chain;
- the last movement is barren and shadowless, not a hopeful rebloom;
- the five source plates remain in yellow-to-barren order; and
- no forbidden imagery such as glowing waves, written messages, or literal
  musical notation appears in prompts.

Then initialize the budget at the provider-profile cap and generate the plan:

```json
{ "tool": "initialize_budget", "cap_usd": 50.0 }
{ "tool": "generate_plan" }
```

Review provider selection, shot coverage, non-zero estimates, dependency
ordering, and total cost. Create the final checkpoint only after the plan is
reviewed:

```json
{
  "tool": "create_checkpoint",
  "label": "pre-generation-no-clips"
}
```

The treatment asks for approximately 50–55 shots. The current deterministic
`visual_poetry` scope contract derives approximately 67 shots for a 600-second
film at its configured pacing. This is a real review issue, not a cosmetic
difference: do not approve generation planning while the matrix silently uses
67 shots. Either request a revision that honors the treatment’s 50–55-shot
shape or explicitly approve a documented scope change before the checkpoint.

## Hard stop: no clips

For this run, do **not** invoke any of these tools:

```text
plan_generation_batch
approve_generation_spend
start_generation_batch
resume_generation_polling
promote_test_to_production
assemble_review_cut
assemble_final_cut
```

Do not call a provider directly, download media, or create a `generated-clips`
directory. The intended terminal state is a reviewed, checkpointed generation
plan with no provider video job and no generated video asset.

Verify the stop before handing off:

```json
{ "tool": "get_orchestrator_summary" }
{ "tool": "get_generation_status" }
{ "tool": "list_assets" }
```

Record evidence that:

- the current approved boundary is `gen_planning`;
- the generation plan and checkpoint exist;
- provider job ids are absent;
- no asset has type `generated_clip`; and
- the isolated destination contains no `.mp4` clip output.

If any clip-generation action has been submitted, stop immediately and report
the provider job id instead of attempting cleanup or cancellation implicitly.

## Resume rule

Resume only from `pre-generation-no-clips` after an explicit new instruction
authorizes clip generation. The next authorized sequence is:

```text
plan_generation_batch → approve_generation_spend → start_generation_batch
```

Each action needs its own review and evidence. A completed pre-generation
runbook is not authorization for any of those actions.

## Current local-run evidence

A real-provider attempt was started from the repository CLI and persisted
partial artifacts under the isolated workspace root. It reached the
visual-development gate and produced the source planning artifacts, but its
long shot-matrix model response stalled before the run could complete the
remaining gate. No clip-generation call was made. Resume through the normal
OpenClaw gate sequence; do not repair this state by manually editing graph
state or injecting unapproved artifact references.
