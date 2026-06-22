# 10 — Autonomous Orchestrator: Implementation Plan

## What Changes

The `await_approval_node` currently pauses for human input via `interrupt()`.
Replace with: run `OrchestratorAgent` autonomously. Only `interrupt()` on escalate.

```
BEFORE:
  await_approval → interrupt() → human → approve/revise/escalate

AFTER:
  await_approval → OrchestratorAgent.run() →
    approve → approve_phase_node → advance
    revise  → inject feedback → repair routing
    escalate → interrupt() → human
```

## Files

### New: `src/film_pipeline/agents/impl/orchestrator_agent.py`

```python
class OrchestratorAgent(BaseAgent):
    def execute(self, model_output):
        data = model_output.get("orchestrator_decision", model_output)
        action = str(data.get("action", "escalate"))
        return {
            "action": action,
            "feedback": str(data.get("feedback", "")),
            "preserve": [str(p) for p in data.get("preserve", [])],
            "reasoning": str(data.get("reasoning", "")),
        }

    def validate(self, result):
        return result.get("action") in ("approve", "revise", "escalate")
```

### New: prompt template in `defaults.py`

```python
def _orchestrator_review() -> PromptTemplate:
    return PromptTemplate(
        template_id="orchestrator-review-v1",
        agent_id="orchestrator-agent",
        version=1,
        role="You are the orchestrator-agent. You review creative output...",
        core_task="Assess the phase output against the target runtime...",
        context_template=(
            "TARGET: {target_runtime_seconds}s {film_type}, {pacing_style} pacing\n"
            "CONSTITUTION: {constitution_summary}\n"
            "PHASE OUTPUT ({current_phase}):\n{phase_output_summary}\n"
            "METRICS: {metrics_summary}\n"
            "CONVERGENCE ROUND: {convergence_round} of 3\n"
        ),
        constraints="Choose ONE action. Give specific creative feedback...",
        output_format='{"action": "approve|revise|escalate", ...}',
    )
```

### Modified: `await_approval_node` in `nodes.py`

```python
def await_approval_node(state):
    if state.get("approved"):
        return state  # auto-approve short-circuit (unchanged)

    # Run orchestrator agent autonomously
    result = _run_orchestrator(state)
    action = result.get("action", "escalate")

    if action == "approve":
        return approve_phase_node(state)
    if action == "revise":
        state["_repair_feedback"] = result.get("feedback", "")
        state["_repair_preserve"] = result.get("preserve", [])
        return state  # routing sends to repair
    # escalate: fall through to interrupt()
    ...
```

### Modified: `_run_agent` agent_map in `nodes.py`

```python
agent_map = {
    ...
    "orchestrator-agent": OrchestratorAgent,
}
```

### Modified: phase context injection in `nodes.py`

`_inject_artifact_context` already loads upstream artifacts. Add a helper
`_build_phase_context(state)` that produces the summary strings the
orchestrator agent needs:
- `target_runtime_seconds`, `film_type`, `pacing_style`
- `constitution_summary` (theme + tone, 200 chars)
- `phase_output_summary` (current phase artifacts, key fields)
- `metrics_summary` (scene count, estimated duration, gap)

## Steps

1. Create `OrchestratorAgent` class
2. Add prompt template to registry
3. Add `_build_phase_context` helper to nodes.py
4. Modify `await_approval_node` to call orchestrator agent
5. Add to `_run_agent` agent_map
6. Tests: unit test orchestrator decisions, smoke test autonomous flow

## What Gets Removed

- Human gate as the primary decision mechanism — becomes escalate-only
- Hard validators (Gate A/B/C) — orchestrator agent handles quality assessment
- `consistency_check_node` validators → informational only (warnings, not blocking)

## OpenClaw Integration

OpenClaw still works. It can:
- Drive the pipeline via MCP (as before)
- The orchestrator agent auto-approves/revises without OpenClaw
- OpenClaw only sees escalate cases (or can inspect anytime via MCP tools)
- `get_phase_context` MCP tool surfaces orchestrator decisions for visibility
