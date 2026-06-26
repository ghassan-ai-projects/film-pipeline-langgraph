# Critical Issues — FPL Codebase

Bugs, anti-patterns, and risks found during deep code review. These are not suggestions — they are problems that will cause failures in production.

## Issue 1: Non-Serializable State Hack

### Location
`graph/graph.py:39-56` — `_ServicesFilteringSerializer`

### Problem
The `GraphServices` object is injected as `_services` into graph state but can't be msgpack-serialized. The solution is a custom serializer that replaces non-serializable objects with `None`:

```python
class _ServicesFilteringSerializer(JsonPlusSerializer):
    def dumps_typed(self, obj):
        try:
            return super().dumps_typed(obj)
        except (TypeError, ValueError):
            return ("json", json.dumps({"__non_serializable_type__": type(obj).__qualname__}).encode())

    def loads_typed(self, data):
        result = super().loads_typed(data)
        if isinstance(result, dict) and "__non_serializable_type__" in result:
            return None
        return result
```

### Why it's dangerous
1. **Silent data loss**: On checkpoint restore, `_services` becomes `None`. The context variable fallback in `nodes.py:_get_services()` works, but there's zero indication that services were lost.
2. **Brittle**: Any new non-serializable field added to state will silently become `None` on restore.
3. **Anti-pattern**: Services should be in `RunnableConfig`, not state. ODR uses `RunnableConfig` for all service-like dependencies.

### Fix
Move `GraphServices` from state to `RunnableConfig`:

```python
# Instead of: state["_services"] = services
# Use: config["configurable"]["services"] = services

def _get_services(config: RunnableConfig) -> GraphServices:
    services = config.get("configurable", {}).get("services")
    if services is None:
        raise RuntimeError("GraphServices not found in config. Ensure runtime bootstrap is complete.")
    return services
```

Then remove the custom serializer. This eliminates data loss risk entirely.

---

## Issue 2: State Mutation via pop() in Node Functions

### Location
`graph/nodes.py:134-136` — `_run_agent()`

### Problem
```python
def _run_agent(state, agent_id, phase, task, *, task_type="create"):
    # Inject repair feedback into the task if present
    feedback = state.pop("_repair_feedback", "")
```

The function **mutates** the state dict by `pop()`ing a key. Since LangGraph nodes should return partial updates (not mutate state), this is:
1. A hidden side effect
2. Bug-prone: if `_run_agent` is called multiple times in a phase, the second call loses feedback
3. Non-idiomatic: LangGraph nodes return `dict` partial updates, not mutate in place

### Fix
Don't mutate state. Read the key and consume it explicitly:

```python
def _run_agent(state, agent_id, phase, task, *, task_type="create"):
    feedback = state.get("_repair_feedback", "")
    updates = {}
    if feedback:
        task = f"{feedback}\n\n{task}"
        updates["_repair_feedback"] = ""  # Clear it in the return value
    # ... rest of function ...
    return {**result, **updates}
```

---

## Issue 3: Deep Imports Inside Functions

### Location
Multiple nodes in `graph/nodes.py` — e.g., line 161-166:

```python
def _run_agent(state, ...):
    from film_pipeline.agents.base import BaseAgent
    from film_pipeline.agents.impl.assembly_agent import AssemblyAgent
    from film_pipeline.agents.impl.constitution_agent import ConstitutionAgent
    from film_pipeline.agents.impl.development_agent import DevelopmentAgent
    from film_pipeline.agents.impl.gen_planner_agent import GenPlannerAgent
    from film_pipeline.agents.impl.intake_agent import IntakeAgent
    # ... 10 more imports ...
```

### Problem
1. **Performance**: Every call to `_run_agent()` re-executes 15+ import statements
2. **Circular import risk**: These are inside the function to avoid circular imports — this is a smell. The module structure has circular dependency issues.
3. **Hard to test**: Mocking is harder with lazy imports inside functions

### Fix
Resolve the circular dependency at the module level. Two approaches:

**Option A: Lazy registry**
```python
# agents/__init__.py
_AGENT_CLASSES = {}  # populated lazily

def get_agent_class(agent_id: str):
    if not _AGENT_CLASSES:
        from film_pipeline.agents.impl import ALL_AGENTS
        for cls in ALL_AGENTS:
            _AGENT_CLASSES[cls.__name__] = cls
    return _AGENT_CLASSES.get(agent_id)
```

**Option B: Registry pattern** (ODR-style)
```python
# agents/registry.py already exists. Extend it:
class AgentRegistry:
    def get_class(self, agent_id: str):
        return self._classes[agent_id]  # Pre-registered at init

# Don't hardcode imports in _run_agent
```

---

## Issue 4: No Configurable Timeout on Model Calls

### Location
`agents/runner.py:117-185` — `PromptRunner.call_model()`

### Problem
```python
def call_model(self, prompt, *, model_profile, agent_id=None):
    for attempt in range(3):
        try:
            return self.model_adapter.chat_json(...)
        except ValueError:
            pass  # Retry
```

No timeout. A hanging model call blocks the entire pipeline. If the network drops or a provider hangs, the pipeline is deadlocked.

### Fix
Add `asyncio.wait_for()` with a configurable timeout:

```python
import asyncio

async def call_model(self, prompt, *, model_profile, agent_id=None, timeout_seconds=120):
    for attempt in range(3):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self.model_adapter.chat_json, ...),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            if attempt == 2:
                return {"status": "timeout", "error": "exhausted_retries"}
            timeout_seconds *= 1.5  # Back off
```

---

## Issue 5: Orchestrator Convergence May Stall Forever

### Location
`graph/edges.py:59-60` — `after_approval()`

### Problem
```python
def after_approval(state):
    if state.get("approved"):
        return next_map.get(phase, "end")
    if is_stalled(state, phase):
        return "await_approval"  # Stay at gate forever
    if state.get("issues"):
        return "repair"
    return "await_approval"
```

When `is_stalled()` returns True, the code routes to `await_approval`. But `await_approval` doesn't escalate — it just sits there. The pipeline is stuck.

### Fix
Stalled → escalate to human:

```python
if is_stalled(state, phase):
    # Mark for human intervention — don't loop forever
    state["human_approval_required"] = True
    state["_stalled_phase"] = phase
    return "await_approval"  # Gate will show "STALLED — needs human review"
```

And ensure the approval gate UI shows the stalled state clearly.

---

## Issue 6: OrchestratorAgent Output is Too Simple

### Location
`agents/impl/orchestrator_agent.py`

### Problem
```python
class OrchestratorAgent(BaseAgent):
    def execute(self, model_output):
        data = model_output.get("orchestrator_decision", model_output)
        action = str(data.get("action", "escalate")).strip().lower()
        if action not in ("approve", "revise", "escalate"):
            action = "escalate"
        return {"action": action, "feedback": ..., "preserve": ..., "reasoning": ...}
```

The orchestrator makes critical go/no-go decisions based on unstructured model output. If the model produces malformed JSON, or uses a different key name, the orchestrator silently escalates (blocking the pipeline).

Compare with ODR: every decision comes from a `with_structured_output(Feedback)` call with a proper Pydantic model.

### Fix
Use structured output:

```python
class OrchestratorDecision(BaseModel):
    action: Literal["approve", "revise", "escalate"] = Field(
        description="Decision after quality review"
    )
    quality_score: int = Field(default=3, ge=1, le=5)
    feedback: str = Field(default="", description="Specific, actionable feedback")
    preserve: list[str] = Field(default_factory=list, description="What to preserve")
    critical_issues: list[str] = Field(default_factory=list)

# In execute():
def execute(self, model_output):
    decision = OrchestratorDecision.model_validate(model_output)
    return decision.model_dump()
```

---

## Issue 7: Missing Dependency Between Shot Bible and Gen Planning

### Location
`graph/graph.py` — phase ordering

### Problem
The phases are:
```
script → visual_dev → shot_bible → gen_planning → generation
```

But `gen_planning` needs to verify every shot in the shot matrix maps to a valid scene in the script. There's no cross-reference validation between phases. If a shot references `scene_id: "sc_999"` that doesn't exist, it won't be caught until generation — or worse, it won't be caught at all and the prompt will be silently wrong.

### Fix
Add cross-phase reference validation in the orchestrator:

```python
# In await_approval_node, for phase "gen_planning":
def validate_shot_scene_references(state):
    script_ref = state.get("script_ref")
    shot_matrix_ref = state.get("shot_matrix_ref")

    script_scenes = {s["scene_id"] for s in load_artifact(script_ref).get("scenes", [])}
    shot_scenes = {r["scene_id"] for r in load_artifact(shot_matrix_ref).get("rows", [])}

    missing_scenes = shot_scenes - script_scenes
    if missing_scenes:
        return [{
            "code": "SHOT_SCENE_MISMATCH",
            "severity": "blocking",
            "message": f"Shots reference non-existent scenes: {missing_scenes}"
        }]
    return []
```

---

## Issue 8: Mock Responses are Monolithic

### Location
`graph/services.py:210-500+` — `_default_mock_responses()`

### Problem
A single dict with 500+ lines of canned responses for every agent. This is:
1. **Code bloat**: The services.py file is ~500 lines of mock data
2. **Maintenance hell**: Changing a mock response requires editing this file
3. **Hard to discover**: New team members can't find mock data for individual agents
4. **Breaks separation of concerns**: Services shouldn't contain test data

### Fix
Move mock responses to individual test fixtures:

```python
# testing/fixtures/constitution_responses.py
CONSTITUTION_MOCK = {
    "constitution": {
        "theme": "Hope against despair...",
        ...
    }
}

# testing/fixtures/__init__.py
ALL_MOCKS = {
    "film-constitution-agent": CONSTITUTION_MOCK,
    "screenwriter-agent": SCREENWRITER_MOCK,
    ...
}

# services.py becomes:
from film_pipeline.testing.fixtures import ALL_MOCKS

@classmethod
def for_mock_runtime(cls, artifacts_root="projects"):
    return cls(
        prompt_runner=PromptRunner(mock_responses=ALL_MOCKS),
        ...
    )
```

---

## Issue 9: No Input Validation on Agent Registration

### Location
`agents/registry.py` — `AgentRegistry`

### Problem
Agents are registered without validating that:
1. Required capabilities are pre-defined
2. Allowed KB domains exist
3. Output artifact types are valid schemas
4. Model profiles exist in the router

A typo in an agent registration (e.g., `"allowed_kb_domains": ["scrip"]` instead of `"script"`) silently breaks context building with no error.

### Fix
Add validation on `register()`:

```python
def register(self, agent: AgentRegistration) -> None:
    # Validate model profile exists
    if agent.model_profile not in self.model_router.list_profiles():
        raise ValueError(f"Agent '{agent.agent_id}' references unknown model profile '{agent.model_profile}'")

    # Validate KB domains are known
    unknown_domains = set(agent.allowed_kb_domains) - self.known_kb_domains
    if unknown_domains:
        _logger.warning(f"Agent '{agent.agent_id}' references unknown KB domains: {unknown_domains}")

    # Validate output artifact types
    for artifact_type in agent.output_artifacts:
        if artifact_type not in ArtifactType.__members__:
            raise ValueError(f"Agent '{agent.agent_id}' produces unknown artifact type '{artifact_type}'")

    self._agents[agent.agent_id] = agent
```

---

## Issue 10: ScreenwriterAgent Doesn't Produce Story Bible and Script as Separate Artifacts

### Location
`graph/nodes.py` — `script_node`

### Problem
The screenwriter agent produces both `story_bible` and `script` in a single output dict:

```python
# Mock response for screenwriter-agent:
{
    "story_bible": {...},
    "script": {...}
}
```

But they're stored as one artifact with two sub-keys. This means:
1. Can't approve script independently of story bible
2. Can't version them independently
3. Orchestrator can't assess script quality without loading the entire bundle
4. Other agents (visual_dev, shot_bible) can't reference just the script

### Fix
Split into two agent runs or two artifacts from one run:

```python
# script_node should produce two separate artifacts:
return {
    "story_bible_ref": _persist_artifact(state, "story_bible", result["story_bible"]),
    "script_ref": _persist_artifact(state, "script", result["script"]),
}
```

---

## Summary: Risk Matrix

| Issue | Severity | Likelihood | Impact |
|-------|----------|------------|--------|
| #1 Non-serializable state hack | High | Low (only on checkpoint restore) | Data loss |
| #2 State mutation via pop() | Medium | Low | Subtle bugs |
| #3 Deep imports in functions | Low | Always | Perf + maintainability |
| #4 No timeout on model calls | High | Medium (networks drop) | Pipeline deadlock |
| #5 Orchestrator convergence stall | High | Medium (5+ revision rounds) | Pipeline stuck forever |
| #6 Orchestrator output too simple | High | Medium (malformed model output) | Wrong decisions |
| #7 Missing cross-phase validation | Medium | High (with real data) | Silent errors in generation |
| #8 Monolithic mock responses | Low | Always | Maintenance burden |
| #9 No agent registration validation | Medium | Low (typos in config) | Broken context building |
| #10 Script + bible not independent | Medium | Always | Poor modularity |
