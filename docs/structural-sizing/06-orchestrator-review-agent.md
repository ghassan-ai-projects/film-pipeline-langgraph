# 06 — Orchestrator Review Agent (Practical Design)

## What Changes

The `consistency_check_node` currently runs hard validators (Gate A/B/C) that
check numeric invariants. Replace with an LLM-powered orchestrator review agent
that reasons about quality holistically.

## Architecture

```
phase_node → orchestrator_review → await_approval → [next_phase | repair]
                  │
                  │ loads all artifacts produced so far
                  │ reads target_runtime, film_type, constitution
                  │ calls orchestrator-review-agent (LLM)
                  │ returns: {status, single_issue?}
                  │
                  ├─ status=pass → advance to next phase
                  └─ status=needs_revision → single issue → repair
```

## The Orchestrator Review Agent

### Input (context packet)
```
TARGET: 600s narrative, standard pacing
CONSTITUTION: theme="rediscovery through primal creativity", tone="introspective, surreal"
ARTIFACTS PRODUCED:
  - project_profile (intake)
  - film_constitution (constitution)
  - treatment (development) — 6 scenes
  - scene_list (development) — 6 scenes
  - story_bible (script)
  - script (script) — 6 scenes, ~150s estimated content
```

### Task
```
You are the orchestrator-review-agent. Review the artifacts produced so far
against the target runtime and film constitution. Your job is NOT to count
scenes or check numbers — it's to assess whether the creative output is
structurally sufficient for the intended runtime.

Consider:
1. Does the scene count provide enough narrative beats for {target_runtime}s?
2. Is each act proportionally developed?
3. Would the content fill the intended duration?
4. Is the visual language consistent with the constitution?

If everything is sufficient: respond with {"status": "pass", "reasoning": "..."}

If you find exactly ONE issue: respond with {
  "status": "needs_revision",
  "issue": {
    "severity": "blocking",
    "what": "specific, actionable description of the problem",
    "suggestion": "one concrete, creative suggestion for fixing it",
    "preserve": "what's good and should be kept"
  },
  "reasoning": "..."
}
```

### Output
```json
{
  "status": "needs_revision",
  "issue": {
    "severity": "blocking",
    "what": "6 scenes averaging ~100s each is feasible but the scenes are light on content. Scene 3 (cave exploration) has only 2 action lines — it needs more discovery beats to fill its duration.",
    "suggestion": "Expand scene 3 into 2-3 discovery moments: first the handprints, then the mammoth, then the artist's realization. Each moment needs 2-3 action lines.",
    "preserve": "The opening studio scenes are rich and well-paced. The cave transition is cinematic. Keep those."
  },
  "reasoning": "For 600s at standard pacing (~45s/scene), we'd expect ~13 scenes. At 6 scenes (~100s each), the current script content is too thin — most scenes have 1-2 action lines which at standard pacing would fill ~15s, not 100s. The structure needs more beats per scene or more scenes."
}
```

## Sequential Repair Flow

```
Round 1: Orchestrator reviews → "scenes are too thin" → repair phase re-runs script
Round 2: Orchestrator reviews → "scene count improved but act 2 is light" → repair
Round 3: Orchestrator reviews → "structure is solid" → pass → advance
```

Each round:
1. Orchestrator produces ONE issue (or pass)
2. Repair injects that issue as feedback into the phase agent
3. Agent re-runs with focused feedback ("fix this one thing")
4. Orchestrator re-reviews

## Convergence (unchanged)

The existing `repair_phase_node` already tracks convergence:
- Max 3 rounds per phase
- After 3 rounds → stalled → escalate to human
- The human sees the orchestrator's reasoning trail

## How This Replaces Hard Validators

| Current (hard) | New (agent) |
|---------------|-------------|
| Gate A: `shot_count == required` | Orchestrator: "Shot count of 24 feels appropriate for this story's pacing" |
| Gate B: `clip_count > 0, cost > 0` | Orchestrator: "6 shot groups at $11.16 is reasonable, proceed" |
| Gate B: `prompt_ref filled` | Orchestrator skips — it knows this is gen_planning's output |

The orchestrator can still check numbers, but it does so with context.
"13 shots for a 180s film at standard pacing (7.5s avg) = 97.5s total.
We're 82s short. I suggest adding..." — this is reasoning, not a formula.

## What About Cost?

Each orchestrator review is an LLM call. For a 10-phase pipeline with 1-3 repair
rounds per phase: ~15-30 orchestrator calls. At ~2K input tokens each: ~30-60K
tokens total. Acceptable for the quality improvement.

## Implementation

### New agent: `orchestrator-review-agent`
- Prompt template: loads target runtime, film type, constitution, current phase artifacts
- Model profile: `strict_validator` (temperature 0.1 for consistent assessments)
- Output schema: `{status: "pass"|"needs_revision", issue?: {...}, reasoning: "..."}`

### Modified: `consistency_check_node`
- Currently runs hard validators via `_run_script_validators`, etc.
- Replace with: call orchestrator-review-agent
- If `status == "needs_revision"`: append single issue to state
- If `status == "pass"`: clear issues (if any were leftover)

### Modified: `repair_phase_node`
- Currently injects all blocking issues as feedback
- Change: inject only the FIRST blocking issue (one at a time)
- The orchestrator will re-review after repair and find next issue

### Removed: Gate A/B/C validators in `orchestrator_validators.py`
- `validate_shot_structure` — replaced by orchestrator review
- `validate_planning_completeness` — replaced
- Keep `validate_execution_brief` (cross-validation of structure extractor output)
- Keep `load_execution_brief` (utility, not a validator)

### New: `OrchestratorReview` schema
```python
class OrchestratorIssue(SchemaBase):
    severity: str  # "blocking" | "warning"
    what: str
    suggestion: str
    preserve: str = ""

class OrchestratorReview(SchemaBase):
    status: str  # "pass" | "needs_revision"
    issue: OrchestratorIssue | None = None
    reasoning: str
```

## Phase Order (unchanged)

The flow stays the same. Only the internals of `consistency_check_node` and
`repair_phase_node` change — they become LLM-powered instead of rule-based.
