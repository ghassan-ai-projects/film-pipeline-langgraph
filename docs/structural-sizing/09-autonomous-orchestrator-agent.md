# 09 — Autonomous Orchestrator Agent (Pipeline Self-Drives)

## The Orchestrator IS an Agent

Not a validator. Not an external tool. Not a human gate. An autonomous LLM agent
that runs between creative phases, inspects output, reasons about quality, and
decides the next action — all without waiting for anyone.

```
┌──────────────────────────────────────────────────────────┐
│ Film Pipeline (self-driving)                             │
│                                                          │
│  intake → orchestrator → constitution → orchestrator →   │
│  development → orchestrator → script → orchestrator →    │
│  ... → delivery                                          │
│                                                          │
│  The orchestrator agent:                                 │
│  - Reads all artifacts produced so far                   │
│  - Reasons about structural quality                      │
│  - Decides: approve / revise / escalate                  │
│  - Produces creative, specific repair feedback           │
│  - Only escalates to human when truly stuck              │
└──────────────────────────────────────────────────────────┘
```

## How It Works

### The Agent

`OrchestratorAgent` — a `BaseAgent` subclass, just like `ConstitutionAgent` or
`ScreenwriterAgent`. It has:
- A prompt template (dedicated, versioned)
- `execute()` that parses the model's decision
- `validate()` that checks the decision is well-formed

### The Prompt

```
You are the orchestrator-agent. You review creative output against the
film's target runtime and constitution. You decide whether to approve,
request revision, or escalate to human.

TARGET: 600s narrative, standard pacing (~45s/scene, ~13 scenes expected)

CONSTITUTION:
  theme: "rediscovery through collision of paralysis and creativity"
  tone: "introspective, surreal, transformative"

PHASE OUTPUT (development):
  treatment: 6 scenes across 3 acts
  scene_list:
    s_001: Studio paralysis
    s_002: Canvas cracks, transition
    s_003: Cave exploration
    s_004: Artist leaves mark
    s_005: Return to studio
    s_006: Final creation

METRICS:
  scene_count: 6 (expected ~13 for 600s)
  estimated_content_duration: ~150s (gap: 450s)

ASSESS the output. Choose ONE action:

1. APPROVE — output is structurally sound for the target runtime.
   Respond: {"action": "approve", "reasoning": "..."}

2. REVISE — output needs specific improvements. Give ONE focused,
   creative suggestion. Reference specific scenes. Say what to
   preserve.
   Respond: {"action": "revise", "feedback": "...", "preserve": [...], "reasoning": "..."}

3. ESCALATE — output is fundamentally wrong, ambiguous, or this is
   the 3rd repair attempt without convergence. A human must decide.
   Respond: {"action": "escalate", "reasoning": "..."}
```

### The Decision

```json
{
  "action": "revise",
  "feedback": "6 scenes is too few for a 600s narrative at standard pacing. The cave exploration scene (s_003) is doing too much in one beat — discovering handprints, mammoths, AND having a realization. Split into: s_003a (first discovery, handprints), s_003b (deeper exploration, mammoth), s_003c (the realization moment). This gives more beats to fill the runtime while keeping the narrative arc.",
  "preserve": ["opening studio scenes are well-paced", "the crack transition is cinematic", "act structure (2-2-2) is balanced"],
  "reasoning": "At ~100s per scene, the current content density doesn't support the runtime. Standard pacing expects ~45s per scene with 2-3 action beats. The scenes have 1-2 action lines each — that fills ~15s, not 100s. Splitting the exploration scene into beats is the most natural expansion point."
}
```

### The Flow

```
development_node → produces treatment (6 scenes)
    ↓
consistency_check → informational warnings only
    ↓
orchestrator_agent → runs autonomously
    ↓
    ├─ action=approve → approve_phase → advance to script
    ├─ action=revise  → repair (re-run development with feedback)
    │                   → orchestrator re-reviews
    └─ action=escalate → interrupt() → wait for human
```

## What Makes It Autonomous

1. **No `interrupt()` for approve/revise.** The orchestrator decides these itself.
   Only `escalate` triggers `interrupt()` for human intervention.

2. **Sequential, single-issue repair.** Each round, the orchestrator identifies
   ONE issue. The agent fixes that one thing. Next round, the orchestrator finds
   the next issue (if any). Not batch — focused.

3. **Convergence tracking.** After 3 rounds without approval, the orchestrator
   escalates. The human sees the full reasoning trail: round 1 issue, round 2
   response, round 3 issue.

4. **Creative, not formulaic.** The orchestrator doesn't say "expected 13, got 6."
   It says "this specific scene could be split into discovery beats." It reasons
   about content, not numbers.

## Implementation

### New: `OrchestratorAgent` class
- File: `src/film_pipeline/agents/impl/orchestrator_agent.py`
- Extends `BaseAgent`
- `execute()`: parses `{action, feedback?, preserve?, reasoning}`
- `validate()`: checks action is one of {approve, revise, escalate}

### New: prompt template
- File: `src/film_pipeline/agents/prompt_templates/defaults.py`
- Template ID: `orchestrator-review-v1`
- Agent ID: `orchestrator-agent`
- Context vars: target_runtime, film_type, constitution_summary, phase_output_summary, metrics, convergence_round

### Modified: `await_approval_node`
- Currently: `interrupt()` → human decides
- New: call orchestrator agent first
  - If action=approve: call `approve_phase_node(state)`
  - If action=revise: inject feedback, return for repair routing
  - If action=escalate: `interrupt()` → human decides
- Only `interrupt()` on escalate (or if orchestrator agent is unavailable)

### Modified: `_run_agent` agent_map
- Add `"orchestrator-agent": OrchestratorAgent`

### Removed: human gate dependency
- The orchestrator IS the gate for approve/revise decisions
- Human only sees escalate cases
- With auto-approve profile: orchestrator still runs (quality review) but gates are bypassed

## Key Difference From Doc 07

| Aspect | Doc 07 (OpenClaw external) | Doc 09 (Autonomous) |
|--------|---------------------------|---------------------|
| Brain location | Outside pipeline (OpenClaw) | Inside pipeline (agent) |
| Decision maker | External LLM via MCP | Internal LLM agent |
| Human involvement | OpenClaw mimics human | Agent decides, human on escalate |
| Latency | Round-trip: pipe → MCP → OpenClaw → MCP → pipe | Single LLM call inside pipeline |
| Cost | Same (one LLM call per review) | Same |
| Autonomy | Depends on OpenClaw being connected | Pipeline drives itself |
