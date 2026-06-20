# OpenClaw MCP Operator Guide

This guide covers the aligned MCP behavior for OpenClaw.

The key rule is now:

- server mode is the source of truth
- project mode must match server mode

## Modes

Use one of these startup commands:

```bash
make run-mcp-mock
make run-mcp-real
```

Notes:

- `make run-mcp` still exists as a legacy mock alias
- `FILM_PIPELINE_MCP_MODE=real` now drives the runtime construction
- real mode uses the real prompt-runner path, not canned mock responses
- the server now speaks stdio MCP directly for `initialize`, `tools/list`, and `tools/call`

## Before Starting Real Mode

Set:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
export GOOGLE_API_KEY="AIza..."
```

Real-mode bootstrap expects `OPENROUTER_API_KEY`.
Real-mode project creation with the real provider stack also expects `GOOGLE_API_KEY`
because the image lane now uses Gemini Imagen 4 instead of `mock-image-provider`.

## What MCP Supports Now

OpenClaw can now:

- discover profiles with `list_profiles`
- inspect profiles with `inspect_profile`
- create a project with explicit `runtime_mode`
- verify mode alignment with `get_runtime_mode`
- inspect registered providers after project creation with `list_providers`

Real-mode project creation now aligns with the actual server mode:

- real server mode + real project mode: allowed
- mock server mode + mock project mode: allowed
- any mismatch: rejected

## Profile Naming

Use actual file stems:

- `provider.seedance_primary`
- `provider.free_or_low_cost`
- `quality.studio`
- `quality.draft`
- `quality.festival`
- `film-type.narrative`
- `film-type.visual_poetry`
- `film-type.experimental`
- `review.strict_continuity`
- `mock-demo`
- `local-real-provider`

## Step 1. Start The Correct Server Mode

For OpenClaw production use:

```bash
make run-mcp-real
```

Do not use `make run-mcp-mock` for real operator work.

## Step 2. Discover And Inspect Profiles

Call:

```text
list_profiles
inspect_profile
```

For real mode, inspect the profiles you plan to use and confirm they do not reference:

- `mock-*` providers
- `mock-*` models

Current real image lane:

- `provider.seedance_primary` registers `gemini-imagen-4` for image generation
- `local-real-provider` also uses `gemini-imagen-4`

Example profile ids:

```json
{ "profile_id": "provider.seedance_primary" }
```

```json
{ "profile_id": "quality.studio" }
```

## Step 3. Create The Project In The Same Mode As The Server

Example:

```json
{
  "project_id": "after-the-fall-001",
  "title": "After the Fall",
  "slug": "after-the-fall",
  "runtime_mode": "real",
  "provider_profile": "provider.seedance_primary",
  "quality_profile": "quality.studio",
  "film_type_profile": "film-type.narrative",
  "review_profile": "review.strict_continuity"
}
```

Behavior:

- if the server is running in `real`, the project must be `real`
- if the server is running in `mock`, the project must be `mock`
- if `runtime_mode` is omitted, it defaults to the server mode
- in real mode, mock provider/model profiles are rejected
- the selected profile stack is resolved and stored with the project
- providers are registered from the selected profile stack during project creation

## Step 4. Verify Alignment

Call:

```text
get_runtime_mode
```

Expected real-mode shape:

```json
{
  "ok": true,
  "server_mode": "real",
  "runtime_mode": "real",
  "project_runtime_mode": "real",
  "aligned": true,
  "profile_stack": {
    "film_type_profile": "film-type.narrative",
    "quality_profile": "quality.studio",
    "provider_profile": "provider.seedance_primary",
    "review_profile": "review.strict_continuity"
  }
}
```

If project mode and server mode differ, the tool returns an error.

## Step 5. Continue With The Film Workflow

After project creation, the normal MCP flow is unchanged:

1. `set_active_project`
2. `submit_idea`
3. `approve_intake`
4. `approve_phase`
5. inspect artifacts and validation as needed

Useful follow-up tools:

- `review_phase_artifacts`
- `inspect_artifact`
- `get_validation_report`
- `list_validation_issues`
- `request_revision`
- `list_providers`
- `check_provider_health`

## What Is Aligned Now

These behaviors are aligned:

- runtime mode is chosen at server startup
- the global runtime is rebuilt from that mode
- real mode uses the real model adapter path
- project creation cannot contradict server mode
- `get_runtime_mode` exposes both server and project mode
- provider registration is derived from the selected project profile stack
- real-mode provider stacks reject missing credentials before the project is created
- the real profile image lane uses `gemini-imagen-4`, not `mock-image-provider`

## What Is Still Missing

This is still not the final end-state.

Remaining gaps:

- resolved config is stored in project state, but not yet exposed as a dedicated first-class MCP artifact
- live-provider readiness and provider health are still lighter than the full target plan
- audit proof for live model/provider execution is still limited

So the correct interpretation is:

- real mode is now behaviorally aligned at the runtime/project contract level
- full live-provider productization is still in progress

## Decision Rule

Use this rule:

- if `make run-mcp-real` started the server and `get_runtime_mode` reports `aligned: true` with `server_mode=real`, OpenClaw is on the correct real-mode contract
- if either the startup mode or `get_runtime_mode` says `mock`, treat it as non-production

## Related Doc

Remaining productization work is tracked here:

- [real-model-only-mcp-plan.md](./mcp-openclaw/real-model-only-mcp-plan.md)
