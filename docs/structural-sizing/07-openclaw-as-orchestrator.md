# 07 — OpenClaw as the Orchestrator (MCP-First Design)

## Principle: The Brain Is Outside The Pipeline

The pipeline is an execution engine. OpenClaw is the operator. Quality assessment,
structural reasoning, and creative direction happen in OpenClaw — not inside the
pipeline's LangGraph nodes.

```
┌─────────────────────────────────────────────────────┐
│ OpenClaw (the brain)                                │
│                                                     │
│  inspect → reason → decide → direct → verify        │
│     │                            │         │         │
│     ▼                            ▼         ▼         │
│  MCP tools:              request_revision  approve   │
│  inspect_phase_summary                              │
│  review_phase_artifacts                             │
│  get_phase_context                                  │
└──────────────┬──────────────────────────────────────┘
               │ MCP (stdio JSON-RPC)
               ▼
┌──────────────────────────────────────────────────────┐
│ Film Pipeline (the hands)                            │
│                                                      │
│  intake → constitution → development → script → ...  │
│                                                      │
│  consistency_check: informational only               │
│  await_approval: pauses for OpenClaw                 │
│  repair: re-runs phase with injected feedback        │
└──────────────────────────────────────────────────────┘
```

## How OpenClaw Solves The Sizing Problem

### Scenario: 6 scenes for 600s target

```
1. Phase completes → pipeline pauses at await_approval
2. OpenClaw: get_phase_context(phase="development")
   → returns:
     target_runtime: 600s
     film_type: narrative
     pacing: standard (~45s/scene expected)
     artifacts:
       treatment: 6 scenes across 3 acts
       scene_list: 6 scenes
     metrics:
       scene_count: 6
       expected_scenes_for_runtime: ~13
       estimated_duration: ~150s (based on content length)

3. OpenClaw reasons (it's an LLM):
   "The treatment has 6 scenes for a 600s narrative at standard pacing.
    That's ~100s per scene — unusual for narrative. Expected ~13 scenes
    at ~45s each. The scene content is light — most have 1-2 action lines
    and would fill ~15s not 100s. I need to ask for more narrative beats."

4. OpenClaw: review_phase_artifacts(phase="development")
   → structured review confirming the assessment

5. OpenClaw: request_revision(
     phase="development",
     feedback="The 6-scene structure needs expansion for a 600s film.
       Scene 3 (cave exploration) should be split into discovery moments.
       Add 2-3 scenes in act 2 to develop the confrontation.",
     preserve=["opening studio scenes", "crack transition"]
   )

6. Pipeline: repair → re-runs development with feedback
7. OpenClaw: get_phase_context → checks result
8. If satisfied: approve_phase → advance to script
```

## What The Pipeline Does NOT Do

The pipeline does NOT:
- Judge whether 6 scenes is "enough" for 600s
- Auto-generate repair feedback based on formulas
- Block approval based on numeric thresholds
- Run LLM-powered orchestrator review agents internally

The pipeline DOES:
- Execute agents when asked
- Run informational consistency checks (staleness)
- Pause at approval gates for OpenClaw to inspect
- Accept structured repair feedback and re-run agents
- Track convergence (3 rounds → escalate to OpenClaw)

## Required MCP Tool Changes

### New: `get_phase_context`
```
Returns everything OpenClaw needs to assess phase output quality:
- target_runtime, film_type, pacing_style
- constitution (theme, tone, visual_language)
- current phase output summary (key fields, not full text)
- upstream artifact summaries
- structural metrics (scene count, estimated duration, shot count)
```

This is the "context packet" — OpenClaw doesn't need to call 5 separate
`inspect_artifact` calls. One call gives it the full picture.

### Enhanced: `review_phase_artifacts`
```
Already exists. Enhance to include:
- target runtime comparison (actual vs expected)
- structural metrics alongside artifact content
- the orchestrator's internal consistency warnings
```

### Enhanced: `request_revision`
```
Already exists. Enhance to accept structured feedback:
- feedback: string (creative direction)
- preserve: list[str] (what to keep)
- target_artifact: string (which artifact needs work — treatment, script, etc.)
```

### Removed: Internal Gate A/B/C Validators
```
The hard validators (validate_shot_structure, validate_planning_completeness)
become informational checks whose output is surfaced through get_phase_context
as "consistency_warnings" — non-blocking. OpenClaw decides whether to act on them.
```

## OpenClaw's Decision Loop

```
for each phase:
    1. Wait for phase to complete (pipeline pauses at await_approval)
    2. get_phase_context → assess quality
    3. IF structural concerns:
       a. review_phase_artifacts → confirm assessment
       b. request_revision with specific feedback
       c. GOTO 2 (re-inspect after repair)
    4. IF satisfied: approve_phase → advance
    5. IF convergence exhausted: escalate to human
```

## Why This Is Better

### vs Hard Validators
OpenClaw can say "6 scenes might work if they're dense enough — let me check the
content" instead of mechanically rejecting at `count < 13`.

### vs Internal Orchestrator Agent
OpenClaw already IS an LLM with full context. Adding a second LLM inside the
pipeline to do the same job is redundant and doubles token cost. One brain,
one set of MCP tools.

### vs Current "Approve Everything"
The auto-approve profile skips all quality checks. With OpenClaw in the loop,
every phase gets reviewed — but by an LLM that can reason contextually, not
a hard validator that can only count.

## What OpenClaw's Prompt Should Look Like

```
You are operating a film production pipeline. Your job is to review each
phase's output against the film's target runtime and creative constitution.

When reviewing:
- Compare the output to the target runtime. If it looks structurally insufficient,
  ask for specific creative expansion (not just "add more scenes").
- Give concrete, actionable feedback — reference specific scenes or elements.
- Preserve what's good. Don't ask the agent to rewrite everything.
- If the output is structurally sound, approve and move on.
- After 3 repair attempts without improvement, escalate to human.

Current film: {film_type}, {target_runtime}s, {pacing} pacing
Constitution: {theme_summary}
```

## Implementation Plan

### Step 1: Add `get_phase_context` MCP tool
- New tool that assembles a context packet from state and artifacts
- Returns target runtime, metrics, artifact summaries
- ~200 lines in `mcp/tools/__init__.py`

### Step 2: Enhance `review_phase_artifacts`
- Add structural metrics to the review package
- Include consistency warnings as informational

### Step 3: Enhance `request_revision`
- Accept structured feedback with `preserve` and `target_artifact` fields

### Step 4: Remove blocking from consistency validators
- Gate A/B/C validators become informational (severity: warning, not blocking)
- Their output surfaces through `get_phase_context`

### Step 5: OpenClaw operator prompt
- Write an OpenClaw system prompt for the operator role
- Include the decision loop: inspect → review → revise → approve

### Not changed
- Phase nodes, graph structure, auto-approve profile
- The pipeline keeps its current structure
- Only MCP tools and validator severities change
