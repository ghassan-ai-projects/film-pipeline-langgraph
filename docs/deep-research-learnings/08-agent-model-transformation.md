# The Real Agent Lesson from ODR → FPL

> **Note**: This document originally argued for replacing FPL's 14 agent classes with a single tool-bound agent. After discussion, the direction shifted: **keep the specialists, make them smarter with tools**. This revised version reflects the converged approach. Document 09 (`09-smart-sub-agents.md`) contains the implementation spec.

## The Core Insight

ODR doesn't have an `Agent` class. There's no `BaseAgent`, no `prepare → execute → validate` lifecycle, no agent registry. The LLM **is** the agent — bound with tools, making decisions through tool calls, producing structured outputs through Pydantic models.

FPL has 14 agent subclasses of `BaseAgent`, each with a rigid `prepare → execute → validate` pipeline. The agents don't *act* — they're glorified prompt templates that produce a JSON blob, which gets parsed and stored. The "agent" doesn't decide anything. It's a function. **But** these 14 classes encode real domain expertise (screenwriting, shot design, constitution building) that a generic tool-bound LLM would lose.

The path forward, defined in [09-smart-sub-agents.md](./09-smart-sub-agents.md), is: **keep the 14 specialist agents, give each one a toolbox for self-revision, self-assessment, and tool-driven decision-making.**

## What ODR Taught Us About Agents

### 1. The LLM is the Agent

```python
# ODR: The LLM is the agent. Tools are its capabilities.
model = init_chat_model(model=research_model)
model_with_tools = model.bind_tools([ConductResearch, ResearchComplete, think_tool])
response = model_with_tools.ainvoke(messages)

# The LLM decides: "I need to search for X" → calls search tool
# The LLM decides: "I need to think about this" → calls think_tool
# The LLM decides: "I'm done" → calls ResearchComplete
```

No `BaseAgent`. No `execute()`. No `validate()`. The model has agency.

### 2. Structured Output via Pydantic Models

```python
# Every decision is a Pydantic model, not a dict
class ClarifyWithUser(BaseModel):
    need_clarification: bool
    question: str | None

model.with_structured_output(ClarifyWithUser).ainvoke(...)
```

The model's output is validated by Pydantic BEFORE it reaches application code.

### 3. Tool-Based Decision Gates

```python
# The LLM MUST call a tool to advance
lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]
# - think_tool("reflection") to pause and reason
# - ConductResearch(research_topic="...") to delegate
# - ResearchComplete() to signal done
```

The orchestration decision is a validated tool call, not a raw JSON field.

### 4. Self-Terminating Loops

The supervisor and researcher loop until the LLM decides it's done — not until the graph code decides it's done. The LLM owns the termination decision.

## What FPL's Agents Are Missing

FPL's agents are *good parsers* but *bad agents*. They:
- Fill a template with context
- Call the LLM once
- Parse the JSON output into Pydantic models
- Return the result

But they can't:
- **Self-revise** when output is weak
- **Ask for missing context** during writing
- **Validate their own work** before returning
- **Signal when they're stuck** and need help

ODR's agents do all four through tools.

## The Solution (Defined in 09)

**Keep the 14 specialist agents. Give each one tools.**

Each specialist gets a curated set of domain-specific tools for self-improvement:

- **ScreenwriterAgent**: `check_scene_continuity`, `diagnose_dialogue_voice`, `revise_scene`, `signal_draft_complete`
- **ConstitutionAgent**: `validate_theme_coherence`, `stress_test_emotional_promise`, `check_visual_language_consistency`
- **ShotBibleAgent**: `validate_shot_scene_mapping`, `check_coverage_completeness`, `adjust_camera_for_emotion`
- **OrchestratorAgent**: `creative_reflection`, `approve_phase`, `request_revision`, `escalate_to_human`

Each agent self-revises up to 3 rounds before the orchestrator sees the output.

## What FPL Already Does Better Than ODR

FPL has strengths ODR lacks. These should be preserved:

1. **Artifact store with versioning** — git-backed checkpointing with branches
2. **KB context building** — scoped context packets per phase
3. **Human approval gates** — MCP-based approval surface critical for creative work
4. **Config profiles** — profile-based merging for different quality tiers
5. **Cost tracking and budget** — budget snapshots and generation ledger
6. **Multi-validator consensus** — multiple validators synthesized into a single report
7. **RCTCO prompt framework** — structured role/context/task/constraints/output

## Summary: The Transformation

| Aspect | Current FPL | After ODR-Inspired Fix |
|--------|------------|----------------------|
| **Agent model** | 14 BaseAgent subclasses | 14 BaseAgent subclasses + tool access |
| **Output** | Raw dicts (parsed to Pydantic post-hoc) | Pydantic structured_output at LLM call time |
| **Orchestration** | JSON field "action" | Tool calls (creative_reflection, approve_phase, request_revision) |
| **Revision** | Regenerate everything from scratch | Tool-driven scene-level revision |
| **Agency** | None — template filler | Self-revision + self-assessment |
| **Termination** | Graph-level gate routing | Agent signals completion via tool call |
| **Auditability** | Side-effect propagation in state dict | Tool call history in message trace |
