# OpenClaw MCP Operator Guide

This guide covers the aligned MCP behavior for OpenClaw.

The key rule is now:

- server mode is the source of truth
- project mode must match server mode

## Phase 0-8 Improvements (2026-06)

The following improvements are now live across the pipeline:

| Phase | What changed | Operator impact |
|-------|-------------|-----------------|
| 0 | Agents use correct model profiles (creative=temp 0.7, validators=temp 0.1) | Higher-quality creative output; validators are stricter |
| 0 | Model retry wrapper (3 attempts → escalate) | JSON parse failures auto-retry; agents no longer crash on bad output |
| 1 | Real human gates via `interrupt()` + `Command(resume=…)` | `approve_phase` / `request_revision` resume the graph; no `GraphRecursionError` |
| 1 | MemorySaver checkpointer + stall detection | Stalled phases show "escalate" action instead of infinite repair loop |
| 2 | `StudioGraphState` TypedDict | `artifact_refs` and `issues` auto-accumulate via reducers |
| 3 | Auto-increment artifact versions | Repair creates v2, v3 — never overwrites v1; `built_from` tracks dependencies |
| 3 | Staleness detection | `consistency_check_node` warns when artifacts were built from stale upstream versions |
| 4 | Living matrix via patches | Downstream phases emit `MatrixPatch` updating per-row `prompt_ref`, `asset_refs`, `validation_refs`, `status` |
| 5 | Structured repair feedback | Agents receive exact row-by-row fix instructions, not text blobs |
| 6 | Scoped context packets | Agents receive only phase-relevant data, reducing token cost ~80% |
| 7 | QC subgraph with parallel validators | 6 validators run concurrently via `Send` API |
| 8 | `top_p` + `frequency_penalty` sampling | Creative agents use `frequency_penalty=0.3` to reduce repetition |
| P0 | Graph state checkpointing | `.graph_state.json` persisted after every graph interaction for crash recovery |

## Modes

Use one of these startup commands:

```bash
make run-mcp-mock
make run-mcp-real
make run-mcp-headless   # real mode, tip: include auto-approve profile for headless runs
```

Notes:

- `make run-mcp` still exists as a legacy mock alias
- `FILM_PIPELINE_MCP_MODE=real` now drives the runtime construction
- real mode uses the real prompt-runner path, not canned mock responses
- the server now speaks stdio MCP directly for `initialize`, `tools/list`, and `tools/call`
- `run-mcp-headless` is identical to `run-mcp-real` — the headless behavior comes from the `auto-approve` profile at project creation time, not the server

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
- generate persisted reference images with `generate_reference_images` — a full 12-phase pipeline (see Step 5 below)
- inspect the orchestrator's decision state with `get_orchestrator_summary` (see Orchestrator Decision Loop below)
- get structured review packages with orchestrator recommendations via `review_phase_artifacts`
- see why approvals are blocked with `get_blockers` and `get_next_actions`
- run fully headless with the `auto-approve` profile (see Headless Mode below)

Real-mode project creation now aligns with the actual server mode:

- real server mode + real project mode: allowed
- mock server mode + mock project mode: allowed
- any mismatch: rejected

---

## Headless Mode (Auto-Approve)

For automated/headless runs (e.g., OpenClaw driving the pipeline end-to-end without
human intervention), layer the `auto-approve` profile on top of your provider stack.

### Profile

`profiles/auto-approve.yaml` — a thin, stackable layer:

```yaml
studio:
  require_human_approval: false
```

This sets `approved=True` and `human_approval_required=False` after every phase
node completes. The `await_approval_node` short-circuits (skips `interrupt()`),
and the graph advances through all 10 phases without pausing.

### How to use

Include `auto-approve` in the `approval_profile` or `auto_approve_profile` field
when creating a project:

```json
{
  "project_id": "auto-run-001",
  "title": "The Field Message",
  "slug": "the-field-message",
  "runtime_mode": "real",
  "provider_profile": "provider.seedance_primary",
  "quality_profile": "quality.studio",
  "film_type_profile": "film-type.narrative",
  "auto_approve_profile": "auto-approve"
}
```

The pipeline will run intake → constitution → development → … → delivery without
any `interrupt()` calls. The graph still passes through `consistency_check` and
`await_approval` nodes, but approval is pre-granted.

### Verification

After project creation, check `get_runtime_mode`:

```json
{
  "ok": true,
  "aligned": true,
  "profile_stack": {
    "...": "...",
    "auto_approve_profile": "auto-approve"
  }
}
```

When `require_human_approval: false` is active:
- `compute_actions()` returns `advance_to_<next_phase>` instead of `wait_for_human`
- `after_phase()` routes directly to the next phase node
- No `interrupt()` is called — the graph never pauses

### Safety

If the `auto-approve` key is missing or malformed, the helper defaults to `True`
(gates ON). Removing the profile from the stack restores normal human gates
without any code changes.

---

## Orchestrator Decision Loop

The orchestrator is now **state-driven**, not phase-script-driven. It inspects
provider health, budget state, failure decisions, pending revisions, and
candidate vs approved artifact baselines before selecting the next action.

### Priority Order

When computing the next action, the orchestrator checks in this order:

| # | Check | Action if triggered |
|---|-------|---------------------|
| 1 | Human approval required | `wait_for_human` |
| 2 | Stalled phase (convergence exhausted) | `escalate` (new in Phase 1) |
| 3 | Blocking failure decision | `escalate_to_failure_handler` or `continue_unrelated_work` |
| 4 | Provider blocked (generation phase) | `continue_unrelated_work` |
| 5 | Budget threshold exceeded | `escalate_to_human` |
| 6 | Blocking validation issues | `handle_blockers` |
| 7 | Pending revision request | `revise` (force repair before approval) |
| 8 | Phase not yet approved | `present_review_package` |
| 9 | Approved, no blockers | `advance_to_<next_phase>` |

**Consistency check (Phase 3):** Every phase node now routes through a
`consistency_check_node` before approval. This node runs staleness detection
on new artifacts — if an artifact was built from a version that has since been
superseded, a warning is emitted. Warnings are informational in Phase 3
(non-blocking).

**Stall escalation (Phase 1):** When a phase fails 3 repair rounds without
convergence, the interrupt payload includes `"escalate"` in
`allowed_actions`. The operator can escalate, which marks the phase as stalled
and prevents further automatic repair attempts. The graph no longer enters the
infinite repair→approval loop that existed before Phase 1.

### Key Concepts

**Provider-Aware Routing**: If a video provider is blocked (quota, credit, auth,
outage), generation stops but planning, writing, and validation phases continue
normally. The orchestrator returns `continue_unrelated_work` instead of blocking
the entire pipeline.

**Budget Gates**: When `BudgetState.threshold_exceeded` is true, the orchestrator
routes to `escalate_to_human` — no phase can advance until the human resolves the
budget situation.

**Failure Classification**: Provider errors are triaged by the
`failure-handling-agent`. Its structured `FailureDecision` is persisted in
orchestrator state. If `safe_to_continue_other_work` is true, non-generation
phases proceed. Otherwise, the orchestrator escalates to the operator.

**Durable Revisions**: When a human requests revision (`request_revision`), the
request is stored as durable state. Approval is blocked until the revision is
resolved. Revision requests do not disappear into warnings.

**Candidate vs Approved Baselines**: Every artifact save records a candidate ref.
When a phase is approved (`approve_phase`), all candidate refs are promoted to
approved. Downstream phases resolve the latest approved version, never a stale
candidate.

**Multi-Model Consensus**: When multiple validators run against the same phase
(e.g., QC phase), the `ConsensusBuilder` produces a unified `ConsensusReport`
with agreement levels and surfaced disagreements — scores are never silently
averaged.

**Convergence Tracking**: If a phase goes through 3 repair rounds without
converging (e.g., validator score frozen), the orchestrator marks the phase as
stalled and offers `escalate` in the interrupt payload. The operator chooses
between: approve with known issues, roll back, or manually edit. The repair
feedback is structured (Phase 5) — agents receive exact row-by-row fix
instructions via `RepairFeedback`, not guesswork from text blobs.

**Matrix Patches (Phase 4):** Downstream phases (`gen_planning`, `generation`,
`qc`, `post`) emit `MatrixPatch` artifacts that update individual matrix rows.
For example, `gen_planning` sets `prompt_ref` and `status: "prompted"` on each
row. `qc_node` updates `validation_refs` and `status` based on per-row findings.
Use `materialize_matrix(store, project_id, base_ref, patch_refs)` to build the
current matrix from base + layered patches. Patch artifacts are versioned
(Phase 3) and never overwrite.

**Scoped Context (Phase 6):** Agents no longer receive all 8 artifact JSON blobs
truncated at 6000 chars. Each phase gets a scoped context packet — e.g.,
`shot_bible` receives the execution brief summary, not the full matrix.
Token savings: ~80% per agent call.

### Orchestrator Summary Tool

`get_orchestrator_summary` now returns a comprehensive state snapshot:

```json
{
  "ok": true,
  "project_id": "after-the-fall-001",
  "current_phase": "script",
  "approved": false,
  "human_approval_required": false,
  "issues": [...],
  "next_action": "present_review_package",
  "route_reason": "script phase needs creator",
  "eligible_actions": ["present_review_package", "approve_phase"],
  "blocked_actions": [],
  "candidate_refs": {"script": "artifact:script:v3", "scene_list": "artifact:scene_list:v2"},
  "approved_refs": {"script": "artifact:script:v2"},
  "pending_revisions": [],
  "active_review_cycle": {"phase": "script", "round_count": 0, "status": "active", "strategy": "single"},
  "provider_blocked": [],
  "budget_snapshot": {"cap_usd": 100.0, "spent_usd": 0.0, "remaining_usd": 100.0, "threshold_exceeded": false},
  "has_blocking_failures": false
}
```

### Review Package Tool

`review_phase_artifacts` now returns a structured `ReviewPackage` with
orchestrator recommendations:

```json
{
  "ok": true,
  "review_package": {
    "review_package_id": "review:...",
    "project_id": "after-the-fall-001",
    "phase": "script",
    "type": "script_review",
    "summary": "Review package for script phase",
    "artifacts": [...],
    "diff_from_approved": {"added": [...], "changed": [...], "removed": []},
    "validation_results": [...],
    "open_issues": [...],
    "risks": [],
    "cost_impact": {},
    "orchestrator_recommendation": "Review the candidate artifacts and approve or request revision.",
    "available_actions": ["approve_phase", "request_revision"],
    "blocked_actions": []
  },
  "router": {
    "next_action": "present_review_package",
    "eligible": ["present_review_package", "approve_phase"],
    "blocked": []
  }
}
```

---

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
- `auto-approve` — headless mode: skip all human approval gates

## Step 1. Start The Correct Server Mode

For OpenClaw production use:

```bash
make run-mcp-real
```

For fully automated/headless runs (no human approval pauses):

```bash
make run-mcp-headless
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

## Step 4.5. Generate Visual Development Bibles (Pre-Generation)

Before `generate_reference_images`, the pipeline needs locked character and
environment descriptions for structured prompt construction. Generate them
with the bible tools:

```json
{ "tool": "generate_character_bible" }
{ "tool": "generate_environment_bible" }
{ "tool": "generate_camera_bible" }
{ "tool": "generate_style_bible" }
```

These produce `CharacterBible`, `EnvironmentBible`, `CameraLanguageBible`,
and `StyleBible` artifacts in the artifact store under `04-visual-dev/`.
The reference image pipeline reads them for:

- **CHAR_DESC block** — `CharacterBible.identity_block` (locked character description)
- **ENV_BASE block** — `EnvironmentBible.locked_prompt_block` (locked environment description)
- **Color palette** — `EnvironmentBible.color_palette` rendered in environment board
- **Camera language** — `CameraLanguageBible` profiles for shot bible prompts
- **Style reference** — `StyleBible` for style boards

> **Status:** 🟡 Planned. Without them, the reference image pipeline falls back to LLM-generated
> prompt text, losing the locked, invariant descriptions.

## Step 5. Generate Reference Images In Visual Dev

After the script phase reaches `visual_dev`, the `generate_reference_images`
MCP tool executes a full 12-phase pipeline that turns the planned
`reference_index` entries into validated image assets.

### 5a. Invoke Generation

```json
{
  "reference_ids": ["char-leo-front-face", "env-studio-wide"],
  "force": false
}
```

Both `reference_ids` and `force` are optional:
- `reference_ids` — filter to specific entries; omit to generate all.
- `force` — regenerate even if an `asset_path` already exists.

### 5b. Pipeline (what happens inside)

The single MCP call runs sequentially:

| Phase | What happens | Key detail |
|-------|-------------|------------|
| Prompt build | Structured prompt from CharacterBible / FilmConstitution | 7-block character prompt, 7-block environment prompt |
| Provider routing | tier field → fast ($0.02) / standard ($0.05) / ultra ($0.10) | seed propagated across same-subject frames for identity consistency |
| Identity consistency | Anchor frame first (front-face for chars, wide-establishing for envs) | seed locked; I2I fallback when Gemini detects subject drift `< 7` |
| Heuristic checks | 5 free Pillow checks per frame | file_exists, not_corrupt, min_resolution ≥ 512, has_content (color variance), face_present (character-only) |
| Gemini per-frame review | 40-pt rubric: Subject (10) + Prompt Match (10) + Artifacts (10) + Technical (10) | threshold ≥ 28 (70%); selective — skips env lighting variants, spot-checks alt angles |
| Retry loop | Max 3 attempts per frame | actionable_feedback injected into retry prompt; best_score tracked |
| Composite sheets | Pillow builds Character Identity Sheets (2048×2048, 20 tiles) and Environment Boards (3840×2160, 8 tiles) | center-crop + resize, labels in margins, gray placeholders for missing frames |
| Composite validation | Gemini reviews complete sheets — character 50pt, environment 50pt rubric | ≥ 80% threshold; generates failing_tiles and bad_reference_tags |
| Delta regeneration | Tile-level retry for failing tiles only | max 3 iterations, best composite score retained |
| Index persistence | `references/index/reference-index.json` + `reference-validation-summary.json` | human-readable |

### 5c. Response Shape

```json
{
  "ok": true,
  "generated": 14,
  "skipped": 0,
  "failed": 0,
  "results": [
    {
      "reference_id": "char-leo-front-face",
      "status": "validated",
      "asset_path": "references/characters/leo/master-frames/char-leo-front-face.png",
      "quality_score": 85.0
    },
    {
      "reference_id": "env-studio-lighting-ambient",
      "status": "generated",
      "asset_path": "references/environments/studio/master-frames/env-studio-lighting-ambient.png"
    }
  ],
  "reference_index_ref": "artifact:reference_index:v1"
}
```

Status values:
- `validated` — Gemini review passed (≥28/40).
- `generated` — review skipped (acceptable per selective validation rules).
- `failed` — heuristic checks failed on final retry.
- `needs_regeneration` — Gemini review failed on final retry.
- `skipped` — asset already existed and `force` was false.

### 5d. Output Directory Structure

```
references/
├── index/
│   ├── reference-index.json          # All entries with asset_path, validation, locked
│   └── reference-validation-summary.json  # Counts and average scores
├── characters/
│   └── {id}/
│       ├── master-frames/            # Individual frame PNGs
│       │   ├── char-{id}-front-face.png
│       │   ├── char-{id}-profile-right.png
│       │   └── ...
│       └── identity-sheet.png        # Composite Character Identity Sheet
└── environments/
    └── {id}/
        ├── master-frames/            # Individual frame PNGs
        │   ├── env-{id}-wide.png
        │   ├── env-{id}-alt-angle-01.png
        │   └── ...
        └── environment-board.png     # Composite Environment Board
```

### 5e. Inspect Individual Results

Use `inspect_reference` to read a single entry from the updated index:

```json
{ "reference_id": "char-leo-front-face" }
```

Response includes all rich metadata now:

```json
{
  "ok": true,
  "reference": {
    "reference_id": "char-leo-front-face",
    "subject_type": "character",
    "subject_id": "leo",
    "frame_role": "front-face",
    "expression": "neutral",
    "lighting": "key-light",
    "tier": "standard",
    "asset_path": "references/characters/leo/master-frames/char-leo-front-face.png",
    "provider": "gemini-imagen-4",
    "generation_status": "validated",
    "quality_score": 85.0,
    "retry_count": 0,
    "best_score": 34.0,
    "validation": {
      "score": 34.0,
      "reports": ["{\"subject\": {\"score\": 9}, ...}"],
      "status": "passed"
    },
    "ai_usability": {
      "score": 85.0,
      "notes": "Good facial detail, matches prompt well."
    },
    "locked": false
  }
}
```

### 5f. Get Validation Summary

`get_validation_report` for `visual_dev` runs the ReferenceUsabilityValidator
against the updated artifact store. It provides aggregate validation counts
and blocking issues.

The per-frame Gemini scores and composite validation results are available
through:
- `inspect_reference` — per-entry `validation` and `ai_usability` fields.
- `references/index/reference-index.json` — complete index on disk.
- `references/index/reference-validation-summary.json` — aggregate counts.

## Step 6. Continue With The Film Workflow

After reference images are generated, continue through the remaining phases:

### 6a. Shot Bible

```json
{ "tool": "generate_shot_bible" }
```

Produces `MasterFilmMatrix` (every shot as a row) and `ContinuityLedger`
(state_in/state_out chain). Approve at the shot_bible phase gate.

### 6b. Generation Plan + Budget

```json
{ "tool": "initialize_budget", "cap_usd": 100.0 }
{ "tool": "generate_plan" }
```

Produces `BudgetState` (spend tracker) and `GenerationPlan` (ordered shot list
with provider routing and cost estimates). Approve at the gen_planning gate.

### 6c. Validation

```json
{ "tool": "run_validation" }
```

Runs phase-appropriate validators and persists `ValidationReport` to the
artifact store. Available for `visual_dev` and `script` phases.

### 6d. Generation

```json
{ "tool": "plan_generation_batch" }
{ "tool": "approve_generation_spend" }
{ "tool": "start_generation_batch" }
```

### 6e. Review Cut Assembly

```json
{ "tool": "assemble_review_cut" }
```

Concatenates generated clips into `09-post/review_cut.v1.mp4` (requires ffmpeg).

### 6f. Checkpoints

```json
{ "tool": "create_checkpoint", "label": "pre-generation" }
```

Snapshots artifact versions for rollback safety.

The full sequential workflow is:

1. `set_active_project`
2. `submit_idea`
3. `approve_intake` → `approve_phase` (constitution) → `approve_phase` (development) → `approve_phase` (script)
4. `generate_character_bible` + `generate_environment_bible` + `generate_camera_bible` + `generate_style_bible`
5. `approve_phase` (visual_dev)
6. `generate_reference_images`
7. `approve_phase` (visual_dev — post-generation review)
8. `generate_shot_bible` → `approve_phase` (shot_bible)
9. `initialize_budget` + `generate_plan` → `approve_phase` (gen_planning)
10. `create_checkpoint` → `plan_generation_batch` → `approve_generation_spend` → `start_generation_batch`
11. `run_validation` → `approve_phase` (generation)
12. `assemble_review_cut` → `approve_phase` (post) → `approve_phase` (delivery)

Useful follow-up tools:

- `get_orchestrator_summary` — full orchestrator state (route reason, candidate/approved refs, pending revisions, provider health, budget, failures)
- `get_next_actions` — what the orchestrator wants to do next and why
- `review_phase_artifacts` — structured review package with orchestrator recommendation
- `inspect_artifact`
- `inspect_reference` — per-entry metadata including `validation`, `ai_usability`, `quality_score`
- `get_validation_report` — phase-level aggregate validation
- `list_validation_issues`
- `request_revision` — creates durable revision state; blocks approval until resolved
- `list_providers`
- `check_provider_health`
- `get_blockers` — see why approval is blocked

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
- visual-dev references can now be generated and persisted through MCP
- bible generation: `generate_character_bible`, `generate_environment_bible`, `generate_camera_bible`, `generate_style_bible`
- shot bible: `generate_shot_bible` produces MasterFilmMatrix + ContinuityLedger
- generation planning: `initialize_budget`, `generate_plan`
- validation: `run_validation` persists ValidationReport to artifact store
- checkpoints: `create_checkpoint` snapshots artifact versions
- **orchestrator routing**: `get_next_actions` returns state-driven priority-based routing with provider health, budget, and failure awareness
- **orchestrator summary**: `get_orchestrator_summary` includes candidate/approved refs, pending revisions, review cycles, provider health, budget snapshot, and failure status
- **review packages**: `review_phase_artifacts` returns structured `ReviewPackage` with orchestrator recommendations
- **durable revisions**: `request_revision` persists revision requests that block approval until resolved
- **candidate→approved promotion**: `approve_phase` promotes all candidate refs to approved baselines
- **consensus reports**: QC phase produces `ConsensusReport` artifacts with agreement levels

## Mid-Project Profile Changes

The profile stack can be changed after project creation, but the change must be
proposed, reviewed, and explicitly approved. This prevents silent drift in
quality, provider, or review settings.

### Propose A Change

```json
{
  "tool": "propose_profile_change",
  "reason": "Switch to draft quality for faster iteration",
  "quality_profile": "quality.draft"
}
```

The tool resolves the projected configuration, computes a diff, and stores a
pending `ProfileChangeProposal` artifact. The change is **not** applied yet.

### Approve A Change

```json
{
  "tool": "approve_profile_change",
  "proposal_id": "profile-change:abc123",
  "confirmed": true,
  "approved_by": "operator-name",
  "note": "Approved for iteration pass."
}
```

Approval:

- bumps `profile_version` on the project
- re-resolves and stores a new `project_config` artifact
- registers providers from the new stack
- creates an invalidation report for downstream artifacts
- stores a `ProfileChangeApproval` artifact

Because `approve_profile_change` mutates project configuration, it requires
`confirmed: true`.

## Operator Comments

Target-scoped operator notes are persisted per project:

```json
{
  "tool": "add_operator_comment",
  "target_type": "scene",
  "target_id": "SC_004",
  "body": "Dialogue voice drifts here — tighten Mara's diction.",
  "phase": "script",
  "source": "openclaw"
}
```

List comments:

```json
{
  "tool": "list_operator_comments",
  "include_resolved": false
}
```

## TUI As MCP Consumer

The terminal UI can run through the same MCP tool surface as OpenClaw.

- Default: `MCPStudioGateway` spawns the MCP server over stdio JSON-RPC
- Legacy: set `FILM_PIPELINE_TUI_GATEWAY=inprocess` to use the in-process service gateway

```bash
# Default — TUI calls MCP tools
FILM_PIPELINE_TUI_GATEWAY=mcp uv run --python 3.12 --group dev python -m film_pipeline.tui.app

# Legacy — TUI calls services directly
FILM_PIPELINE_TUI_GATEWAY=inprocess uv run --python 3.12 --group dev python -m film_pipeline.tui.app
```

When using the MCP gateway, every TUI action (create project, submit idea,
approve phase, add comment, list checkpoints, etc.) is dispatched through the
same `tools/call` JSON-RPC endpoint that OpenClaw uses.

### Redesigned Studio Interface

The TUI is organized around the film pipeline itself instead of a dense cockpit:

- **Project gallery** — the home screen lists projects; create a new film or open
  an existing one.
- **Studio workspace** — three-pane layout for the active project:
  - **Left rail**: pipeline stages from intake through delivery; the current
    stage is highlighted, done stages are marked, and stages with blocking
    issues show a warning badge.
  - **Center workspace**: contextual header, action bar, and tables for the
    selected stage's artifacts and validation issues.
  - **Right drawer**: inspector for the selected artifact or issue.
- **Action bar**: always shows the most relevant actions for the current stage
  (validate, approve phase, request revision, next, inspect) as clickable
  buttons; no commands need to be memorized.
- **Command palette** — press `/` to toggle a power-user palette for commands
  such as `project <id>`, `approve`, `validate`, `revise <note>`, `assets`, and
  `home`.
- **Keyboard shortcuts** — `n` creates a project, `r` refreshes, `a` approves the
  current phase, `v` runs validation, `escape` returns home, and `q` quits.

## What Is Resolved (as of 2026-06-29)

These previously-missing items are now implemented:

- **Orchestrator decision loop**: State-driven routing with 8-tier priority (human gate → failure decisions → provider health → budget → blocking issues → pending revisions → review packages → phase advance)
- **Provider-aware routing**: `continue_unrelated_work` when generation is blocked but planning/writing can proceed
- **Budget gates**: `escalate_to_human` on threshold exceeded
- **Failure classification**: `escalate_to_failure_handler` routes to `failure-handling-agent` with structured `FailureDecision` persistence
- **Durable revision state**: `request_revision` creates persistent `RevisionRequest` that blocks approval until resolved
- **Candidate vs approved baselines**: `approve_phase` promotes candidates to approved; downstream phases resolve approved versions
- **Multi-model consensus**: `ConsensusBuilder` produces `ConsensusReport` with agreement levels and surfaced disagreements
- **Convergence tracking**: 5-round stall detection with escalation
- **Review packages**: `review_phase_artifacts` returns structured `ReviewPackage` with orchestrator recommendations
- **Expanded orchestrator summary**: `get_orchestrator_summary` includes route reason, candidate/approved refs, pending revisions, review cycles, provider health, budget, and failure status
- **Versioned profile changes**: `propose_profile_change` and `approve_profile_change` implement approved mid-project profile changes with configuration diffing and downstream invalidation
- **Operator comments over MCP**: `add_operator_comment` and `list_operator_comments` persist target-scoped notes through the MCP surface
- **TUI MCP gateway**: `MCPStudioGateway` lets the terminal UI consume the same MCP tool surface as OpenClaw

## What Is Still Missing

- live-provider health polling is manual (operator must call tools); no automated health-check loop
- audit proof for live model/provider execution is still limited
- delta regeneration has no dedicated MCP tool — it runs internally during `generate_reference_images` but OpenClaw cannot request targeted tile-level retries independently
- composite validation results (failing tiles, bad reference tags) are computed during generation but not surfaced as a callable MCP artifact — they only appear in the Gemini response logged to the console
- `get_validation_report` for `visual_dev` uses the pre-existing ReferenceUsabilityValidator (macro-level checks) rather than the Gemini per-frame and composite review scores; individual frame scores are accessible via `inspect_reference` per-entry
- shot bible, generation plan, QC, post, and delivery nodes are all flag-only — see implementation plan phases 06-10
- frame metadata sidecars, sheet manifests, and additional composite templates are planned — see implementation plan phases 03-05
- multi-model parallel dispatch (running validators simultaneously on different models) is wired at the profile/strategy level but actual parallel model execution requires provider-level work


## Decision Rule

Use this rule:

- if `make run-mcp-real` started the server and `get_runtime_mode` reports `aligned: true` with `server_mode=real`, OpenClaw is on the correct real-mode contract
- if either the startup mode or `get_runtime_mode` says `mock`, treat it as non-production

## Related Doc

Remaining productization work is tracked here:

- [real-model-only-mcp-plan.md](./mcp-openclaw/real-model-only-mcp-plan.md)
