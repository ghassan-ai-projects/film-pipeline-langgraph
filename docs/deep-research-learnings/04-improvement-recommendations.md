# Improvement Recommendations — Prioritized

Ranked by impact × effort. Each recommendation includes what to change, where, and how.

## Priority 1: Structured Output Schemas (CRITICAL)

### Problem
Every agent returns `dict[str, Any]`. No validation on model output shape. If a model hallucinates a field name, it silently propagates. Debugging is guesswork.

### Solution
Add Pydantic output models for every agent.

### Implementation

```python
# schemas/agent_outputs.py (new file)
from pydantic import BaseModel, Field

class ConstitutionAgentOutput(BaseModel):
    theme: str
    tone: str
    emotional_promise: str
    visual_language: str
    camera_philosophy: str
    quality_bar: str
    character_truths: list[dict[str, str]]
    taboo_mistakes: list[str]

class DevelopmentAgentOutput(BaseModel):
    treatment: dict[str, str]  # text, themes, act_map
    scenes: list[dict[str, str]]  # scene_id, dramatic_function, etc.

class ScreenwriterOutput(BaseModel):
    story_bible: dict[str, object]
    script: dict[str, object]  # title, scenes[], total_scenes

class ShotDesignOutput(BaseModel):
    shot_matrix: dict[str, object]  # rows[], coverage_groups[]

class VisualDevOutput(BaseModel):
    reference_entries: list[dict[str, object]]

class GenPlannerOutput(BaseModel):
    cost_estimate: dict[str, object]
    shot_groups: list[dict[str, object]]

class QCValidationOutput(BaseModel):
    consensus: dict[str, object]
```

Then wire into agents:

```python
# In ScreenwriterAgent.execute()
def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
    parsed = ScreenwriterOutput.model_validate(model_output)
    return parsed.model_dump()
```

### Files to modify
- New: `schemas/agent_outputs.py`
- Modify: Every agent in `agents/impl/` — add `.execute()` validation via Pydantic
- Modify: `agents/runner.py` — `PromptRunner.call_model()` could return `BaseModel` instead of `dict`

### Effort
Medium — ~15 agents, each needs an output model and validation call.

---

## Priority 2: Content Compression Chain (CRITICAL)

### Problem
As the pipeline progresses, context grows: script (50+ scenes) → shot matrix (100+ shots) → generation prompts. No mechanism to truncate or summarize. Will silently overflow context windows.

### Solution
Add configurable truncation and a summarization model for large artifacts.

### Implementation

```python
# kb/compression.py (new file)

from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
import asyncio

class ArtifactSummary(BaseModel):
    summary: str = Field(description="1-2 paragraph summary")
    key_elements: str = Field(description="Critical facts to preserve")
    character_ids: list[str] = Field(default_factory=list)
    location_ids: list[str] = Field(default_factory=list)

async def compress_artifact(
    content: str,
    target_phase: str,
    max_chars: int = 8000,
    model_id: str = "deepseek/deepseek-chat",
) -> str:
    """Compress artifact content for context injection."""
    if len(content) <= max_chars:
        return content

    truncation_limit = max_chars * 4  # Give summarizer more to work with
    model = init_chat_model(model=model_id, max_tokens=1024)
    summarizer = model.with_structured_output(ArtifactSummary)

    try:
        summary = await asyncio.wait_for(
            summarizer.ainvoke([{
                "role": "user",
                "content": (
                    f"Summarize this film artifact for use in '{target_phase}' phase.\n"
                    f"Preserve: all character names, locations, key dramatic elements.\n\n"
                    f"{content[:truncation_limit]}"
                )
            }]),
            timeout=30.0
        )
        return (
            f"[COMPRESSED from {len(content)} chars]\n"
            f"Summary: {summary.summary}\n"
            f"Key elements: {summary.key_elements}\n"
            f"Characters: {', '.join(summary.character_ids)}\n"
            f"Locations: {', '.join(summary.location_ids)}"
        )
    except asyncio.TimeoutError:
        # Timeout → just truncate
        return content[:max_chars] + "\n[TRUNCATED]"
```

**Integrate into KB context builder:**

```python
# In kb/curator.py or kb/packets.py
async def build_context_packet(self, ...):
    artifacts = await self._load_artifacts(project_id, phase)

    # Compress large artifacts in parallel
    compress_tasks = [
        compress_artifact(content, target_phase, max_chars=8000)
        for content in artifacts if len(str(content)) > 8000
    ]
    if compress_tasks:
        compressed = await asyncio.gather(*compress_tasks)
    ...
```

### Configuration
Add to config profiles:

```yaml
# profiles/base.studio.yaml
context:
  max_chars_per_artifact: 8000
  summarization_model: "deepseek/deepseek-chat"
  summarization_timeout_seconds: 30
```

### Files to modify
- New: `kb/compression.py`
- Modify: `kb/curator.py`, `kb/packets.py`
- Modify: `config/` — add context section to profile schema

### Effort
Medium — needs new module + integration into KB building.

---

## Priority 3: Token Limit Detection & Recovery (CRITICAL)

### Problem
`PromptRunner.call_model()` retries 3 times on ValueError, but doesn't distinguish between "bad JSON" and "token limit exceeded". On token limit, retrying with same prompt is pointless — it needs compression.

### Solution
Detect token limit errors and compress context before retry.

### Implementation

```python
# providers/failure_classifier.py — add token limit detection

def is_token_limit_exceeded(exception: Exception, model_id: str) -> bool:
    """Detect if an exception indicates token limit exceeded."""
    error_str = str(exception).lower()

    # Provider-specific patterns
    if "deepseek" in str(model_id).lower():
        return any(phrase in error_str for phrase in [
            "maximum context length", "context_length_exceeded",
            "too many tokens", "token limit"
        ])
    elif "gemini" in str(model_id).lower():
        return any(phrase in error_str for phrase in [
            "input too long", "maximum number of tokens",
            "token count exceeds"
        ])
    elif "openai" in str(model_id).lower():
        return any(phrase in error_str for phrase in [
            "context_length_exceeded", "maximum context length",
            "reduce the length"
        ])
    elif "anthropic" in str(model_id).lower():
        return any(phrase in error_str for phrase in [
            "prompt is too long", "input is too long"
        ])
    return False

def compress_prompt_for_retry(prompt_text: str, factor: float = 0.5) -> str:
    """Aggressively compress prompt content by truncating sections."""
    lines = prompt_text.split("\n")
    sections = {}
    current_section = "_header"

    for line in lines:
        if line.startswith("# "):
            current_section = line[2:].strip().lower().replace(" ", "_")
            sections[current_section] = []
        sections.setdefault(current_section, []).append(line)

    # Keep role and task intact, compress context
    compressed = []
    for section_name, section_lines in sections.items():
        if section_name in ("role", "core_task", "output"):
            compressed.extend(section_lines)
        elif section_name == "context":
            kept = max(1, int(len(section_lines) * factor))
            compressed.extend(section_lines[:kept])
            compressed.append(f"[... {len(section_lines) - kept} context lines truncated ...]")
        else:
            compressed.extend(section_lines[:3])

    return "\n".join(compressed)
```

**Integrate into PromptRunner:**

```python
# In agents/runner.py — call_model()
def call_model(self, prompt, *, model_profile, agent_id=None):
    # ... existing mock check ...

    model_id, max_tokens, temperature, top_p, freq_penalty = (
        self.model_router.resolve_model_params(model_profile)
    )

    for attempt in range(3):
        try:
            return self.model_adapter.chat_json(
                prompt.rendered, model=model_id, ...
            )
        except Exception as e:
            from film_pipeline.providers.failure_classifier import (
                is_token_limit_exceeded, compress_prompt_for_retry
            )
            if is_token_limit_exceeded(e, model_id):
                if attempt == 2:
                    raise  # Exhausted after 3 attempts
                prompt.rendered = compress_prompt_for_retry(
                    prompt.rendered, factor=0.7 - (attempt * 0.3)
                )
                _logger.warning(
                    f"Token limit exceeded for {model_profile}, "
                    f"compressed prompt and retrying (attempt {attempt+1}/3)"
                )
                continue
            # ... existing ValueError retry logic ...
```

### Files to modify
- Modify: `providers/failure_classifier.py` — add `is_token_limit_exceeded()` and `compress_prompt_for_retry()`
- Modify: `agents/runner.py` — integrate detection into retry loop
- Modify: `agents/model_adapter.py` — expose error details for detection

### Effort
Medium — touches core execution path, needs careful testing.

---

## Priority 4: Reflection/Think Tool (CRITICAL)

### Problem
The pipeline auto-advances through phases without a deliberate quality gate. The orchestrator evaluates outputs, but the *LLM making the orchestration decision* isn't forced to pause and reason before deciding.

### Solution
Add a `creative_review_tool` that the orchestrator MUST call before making decisions.

### Implementation

```python
# agents/tools.py (new file)
from typing import Literal, Annotated
from langchain_core.tools import tool

@tool(description="Strategic review tool for film quality assessment — MUST be called before making any orchestration decision")
def film_review_tool(
    phase: str,
    quality_assessment: Annotated[str, "Your detailed assessment of the phase output quality"],
    issues_found: Annotated[str, "Any issues or gaps you identified"],
    action: Annotated[Literal["approve", "revise", "escalate"], "Your decision after careful review"],
    reasoning: Annotated[str, "Why you chose this action — 2-3 sentences"]
) -> str:
    """Call this tool after reviewing phase output. Forces deliberate quality assessment.

    Use after examining:
    1. The phase's output artifacts
    2. Consistency with the film constitution
    3. Adherence to the execution brief
    4. Any validation reports
    """
    return (
        f"Film review for phase '{phase}':\n"
        f"Quality: {quality_assessment[:200]}\n"
        f"Issues: {issues_found[:200]}\n"
        f"Decision: {action}\n"
        f"Reasoning: {reasoning[:300]}"
    )
```

**Integrate into orchestrator:**

```python
# In OrchestratorAgent
class OrchestratorAgent(BaseAgent):
    def prepare(self, state, kb_context, task):
        # The orchestrator now uses the film_review_tool instead of
        # generating raw JSON decisions
        return {
            "project_id": str(state.get("project_id", "")),
            "current_phase": str(state.get("current_phase", "")),
            "task": task,
            "tools": [film_review_tool],  # Must call this
        }
```

Or alternatively, wire it into `await_approval_node`:

```python
# In graph/nodes.py — await_approval_node
async def await_approval_node(state, config):
    """Orchestrator reviews phase output and decides approve/revise/escalate."""
    phase = str(state.get("current_phase", ""))

    # Build review package with context
    review_context = _build_phase_context(state)

    # Run orchestrator with film_review_tool
    decision = await _run_orchestrator_review(state, review_context, tools=[film_review_tool])

    action = decision.get("action", "escalate")
    if action == "approve":
        return interrupt_for_gate(state, phase, APPROVAL_GATE_LABELS.get(phase, phase))
    elif action == "revise":
        return _request_revision(state, decision.get("feedback", ""))
    else:
        return _escalate_to_human(state, decision.get("reasoning", ""))
```

### Files to modify
- New: `agents/tools.py`
- Modify: `agents/impl/orchestrator_agent.py`
- Modify: `graph/nodes.py` — `await_approval_node`
- Modify: `graph/services.py` — add tools to orchestrator setup

### Effort
Medium — needs careful integration with the orchestration flow.

---

## Priority 5: Evaluation Framework (IMPORTANT)

### Problem
No way to measure if generated film artifacts are good. Validation is rule-based (pass/fail), not quality-based.

### Solution
Build an LLM-as-judge evaluation framework.

### Implementation

```python
# evaluation/ (new package)

# evaluation/judge.py
class FilmJudge:
    """LLM-as-judge for film artifact quality."""

    EVAL_PROFILES = {
        "script": [
            ("dramatic_structure", "Does the scene structure follow proper dramatic arcs?"),
            ("character_voice", "Are character voices distinct and consistent?"),
            ("scene_pacing", "Is pacing appropriate for the film type?"),
            ("dialogue_quality", "Is dialogue natural and purposeful?"),
        ],
        "constitution": [
            ("thematic_coherence", "Is the theme clear and consistent?"),
            ("visual_language", "Is the visual language well-defined?"),
            ("emotional_promise", "Is the emotional promise achievable?"),
        ],
        "shot_matrix": [
            ("coverage_completeness", "Are all required angles covered?"),
            ("duration_feasibility", "Are shot durations realistic?"),
            ("continuity_flow", "Do shots flow naturally?"),
        ],
    }

    async def evaluate(
        self,
        artifact_type: str,
        content: dict,
        reference: dict | None = None,
        model: str = "google/gemini-3-flash-preview"
    ) -> dict:
        """Evaluate artifact quality on all relevant axes."""
        scores = {}
        for axis, description in self.EVAL_PROFILES.get(artifact_type, []):
            scores[axis] = await self._score_axis(axis, description, content, reference, model)

        overall = sum(s["score"] for s in scores.values()) / max(len(scores), 1)
        return {"axes": scores, "overall_score": overall, "artifact_type": artifact_type}

    async def _score_axis(self, axis, description, content, reference, model):
        """Score a single quality axis."""
        from langchain.chat_models import init_chat_model
        from pydantic import BaseModel

        class AxisScore(BaseModel):
            score: int = Field(ge=1, le=5)
            reasoning: str

        llm = init_chat_model(model=model).with_structured_output(AxisScore)

        try:
            result = await asyncio.wait_for(
                llm.ainvoke([{
                    "role": "user",
                    "content": f"Evaluate this film artifact on '{description}':\n{json.dumps(content, indent=2)[:8000]}"
                }]),
                timeout=30.0
            )
            return {"score": result.score, "reasoning": result.reasoning}
        except Exception:
            return {"score": 3, "reasoning": "evaluation_failed"}
```

### Files to modify
- New: `evaluation/__init__.py`, `evaluation/judge.py`, `evaluation/prompts.py`, `evaluation/benchmarks.py`
- Modify: `graph/nodes.py` — add optional eval step after key phases
- Modify: `config/` — add eval model config

### Effort
Large — new package, benchmark dataset, integration into pipeline.

---

## Priority 6: Parallel Artifact Processing (IMPORTANT)

### Problem
KB context building loads artifacts sequentially. With 4-6 artifact types in later phases, this adds latency.

### Solution
Load and process artifacts in parallel using `asyncio.gather`.

### Implementation

```python
# kb/curator.py — enhance build_context_packet

async def build_context_packet_parallel(
    self,
    project_id: str,
    phase: str,
    agent_id: str,
    task: str,
    max_chars_per_artifact: int = 8000,
) -> KBContextPacket:
    """Build context packet with parallel artifact loading."""

    # Determine required artifacts
    required = self._get_required_artifacts(phase)

    # Load all in parallel
    async def load_one(artifact_type: str, version: int | None = None):
        try:
            data = self.artifact_store.load(project_id, FilmPhase(phase), artifact_type, version)
            if isinstance(data, dict):
                data["_artifact_type"] = artifact_type
            return data
        except Exception as e:
            _logger.warning(f"Failed to load {artifact_type}: {e}")
            return None

    load_tasks = [load_one(a_type, a_ver) for a_type, a_ver in required]
    artifacts = await asyncio.gather(*load_tasks)

    # Compress large ones in parallel
    compress_tasks = []
    for artifact in artifacts:
        if artifact is None:
            continue
        content_str = json.dumps(artifact)
        if len(content_str) > max_chars_per_artifact:
            compress_tasks.append(compress_artifact(content_str, phase, max_chars_per_artifact))
        else:
            compress_tasks.append(asyncio.sleep(0))  # no-op for small ones

    compressed = await asyncio.gather(*compress_tasks)

    # Assemble packet
    return self._assemble_packet(compressed, agent_id, task, phase)
```

### Files to modify
- Modify: `kb/curator.py`
- Modify: `graph/services.py` — `kb_for()` should use parallel loading

### Effort
Small-Medium — mainly refactoring existing sequential code.

---

## Priority 7: Runtime Config Overrides (IMPORTANT)

### Problem
Profiles are merged at startup. Can't override individual settings at runtime (e.g., "use draft quality for this run" or "skip visual_dev").

### Solution
Add environment variable overrides and runtime config injection.

### Implementation

```python
# config/runtime_overrides.py (new file)

import os

# Env var prefix for runtime overrides
_ENV_PREFIX = "FILM_PIPELINE_"

# Map of env var names to config paths
_OVERRIDE_MAP = {
    "FILM_PIPELINE_QUALITY": ("resolved_quality",),
    "FILM_PIPELINE_MAX_SCENES": ("limits", "max_scenes"),
    "FILM_PIPELINE_SKIP_VISUAL_DEV": ("studio", "skip_visual_dev"),
    "FILM_PIPELINE_MODEL_OVERRIDE": ("models", "creative_writer", "primary"),
    "FILM_PIPELINE_MAX_CONTEXT_CHARS": ("context", "max_chars_per_artifact"),
    "FILM_PIPELINE_SEARCH_API": ("generation", "search_api"),
    "FILM_PIPELINE_APPROVAL_MODE": ("studio", "require_human_approval"),
}

def apply_runtime_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides to resolved config."""
    for env_var, config_path in _OVERRIDE_MAP.items():
        value = os.environ.get(env_var)
        if value is not None:
            _set_nested(config, config_path, _coerce_type(value))
    return config

def _set_nested(d: dict, path: tuple[str, ...], value: Any) -> None:
    """Set a nested dict value by path."""
    for key in path[:-1]:
        d = d.setdefault(key, {})
    d[path[-1]] = value

def _coerce_type(value: str) -> Any:
    """Coerce string env var to appropriate type."""
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value
```

**Integrate into config loading:**

```python
# config/merger.py
def merge_and_resolve(base_profile: str, overlays: list[str]) -> dict:
    config = _merge_profiles(base_profile, overlays)
    config = apply_runtime_overrides(config)  # Apply env var overrides last
    return config
```

### Files to modify
- New: `config/runtime_overrides.py`
- Modify: `config/merger.py`

### Effort
Small — isolated change, no architecture impact.

---

## Priority 8a: Tool Aggregation System (IMPORTANT)

### Problem
ODR has a `get_all_tools()` function that aggregates tools from three sources (core, search API, MCP) at runtime, with name conflict detection and metadata tagging. FPL has no comparable system. Tools are registered ad-hoc in `mcp/server.py` and provider adapters. There's no unified tool aggregation, no conflict detection, and no tool metadata for routing decisions.

This was identified as gap #7 in the gap analysis (tool aggregation + MCP conflict system).

### Solution
Add a `ToolAggregator` that mirrors ODR's pattern.

```python
# agents/tool_aggregator.py (new file)

from dataclasses import dataclass, field
from langchain_core.tools import BaseTool

@dataclass
class ToolAggregator:
    """Aggregates tools from multiple sources at runtime."""

    core_tools: list[BaseTool] = field(default_factory=list)
    mcp_tools: list[BaseTool] = field(default_factory=list)
    provider_tools: list[BaseTool] = field(default_factory=list)

    def get_all_tools(
        self,
        phase: str | None = None,
        include_mcp: bool = True,
        include_providers: bool = False
    ) -> list[BaseTool]:
        """Assemble complete toolkit with deduplication."""
        tools: list[BaseTool] = list(self.core_tools)
        existing_names = {t.name for t in tools}

        if include_mcp:
            for tool in self.mcp_tools:
                if tool.name in existing_names:
                    logging.warning(
                        f"MCP tool '{tool.name}' conflicts with existing tool — skipping"
                    )
                    continue
                tools.append(tool)
                existing_names.add(tool.name)

        if include_providers:
            for tool in self.provider_tools:
                if tool.name in existing_names:
                    logging.warning(
                        f"Provider tool '{tool.name}' conflicts — skipping"
                    )
                    continue
                tools.append(tool)
                existing_names.add(tool.name)

        return tools
```

### Files to modify
- New: `agents/tool_aggregator.py`
- Modify: `graph/services.py` — add ToolAggregator to GraphServices
- Modify: `mcp/server.py` — register tools through aggregator instead of directly

### Effort
Small — isolated new class, minimal integration changes.

---

## Priority 8b: MCP Tool Error Wrapping (NICE TO HAVE)

### Problem
When MCP tools fail, raw exceptions propagate to the operator console. Need user-friendly, actionable error messages.

### Solution
Wrap all MCP tools with domain-specific error handling.

### Implementation
See Pattern 6 in [02-transferable-patterns.md](./02-transferable-patterns.md) for full code.

### Files to modify
- New: `mcp/error_wrapper.py`
- Modify: `mcp/server.py` — wrap tools on registration

### Effort
Small — focused MCP layer change.

---

## Priority 9: LangGraph Cloud Deployment Config (NICE TO HAVE)

### Problem
No `langgraph.json` at project root. Can't use LangGraph Studio or Cloud deployment.

### Solution
Add `langgraph.json` at project root with graph export.

### Implementation

```json
{
    "dockerfile_lines": [],
    "graphs": {
        "Film Pipeline": "./src/film_pipeline/graph/graph.py:graph"
    },
    "python_version": "3.12",
    "dependencies": ["."],
    "auth": {
        "path": "./src/film_pipeline/app/health.py:auth"
    }
}
```

And add module-level graph export:

```python
# graph/graph.py — add at module level
from film_pipeline.graph.graph import build_graph
graph = build_graph()  # Exported for langgraph.json
```

### Files to modify
- New: `langgraph.json`
- Modify: `graph/graph.py` — add module-level `graph`

### Effort
Trivial.

---

## Priority 9b: Extract Mock Responses + Agent Registration Validation (NICE TO HAVE)

### Problem (from 05-critical-issues.md #8 and #9)

1. **Monolithic mock responses**: `graph/services.py` has ~500 lines of canned responses in a single dict. Maintenance burden, breaks separation of concerns.
2. **No agent registration validation**: `agents/registry.py` doesn't validate that registered agents reference known model profiles, KB domains, or artifact types. Typos silently break context building.

### Solution

**For mocks (#8)**: Move mock responses to individual test fixtures per agent:

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
```

**For validation (#9)**: Add validation to `AgentRegistry.register()`:

```python
def register(self, agent: AgentRegistration) -> None:
    # Validate model profile exists
    if agent.model_profile not in self.model_router.list_profiles():
        raise ValueError(f"Unknown model profile '{agent.model_profile}'")

    # Validate KB domains are known
    unknown_domains = set(agent.allowed_kb_domains) - self.known_kb_domains
    if unknown_domains:
        logging.warning(f"Unknown KB domains: {unknown_domains}")

    # Validate output artifact types
    for artifact_type in agent.output_artifacts:
        if artifact_type not in ArtifactType.__members__:
            raise ValueError(f"Unknown artifact type '{artifact_type}'")

    self._agents[agent.agent_id] = agent
```

### Files to modify
- New: `testing/fixtures/` directory with per-agent mock response files
- Modify: `graph/services.py` — import from fixtures instead of inline dict
- Modify: `agents/registry.py` — add validation on register()

### Effort
Small — extract existing code, add validation checks.

---

## Priority 6b: Timeout Protection on Model Calls (IMPORTANT)

> **Note**: This was identified as a CRITICAL gap in the initial gap analysis (#4 in 03-gap-analysis.md) and as Issue #4 in 05-critical-issues.md. While less impactful than structured outputs or context compression, a hung model call blocks the entire pipeline. Moved to IMPORTANT priority with token limit detection on Day 3.

### Problem
`PromptRunner.call_model()` has no timeout. A hanging model call blocks the entire pipeline.

### Solution
Add `asyncio.wait_for()` wrapper.

### Implementation

```python
# agents/runner.py
import asyncio

async def call_model_with_timeout(
    self, prompt, *, model_profile, agent_id=None, timeout_seconds: int = 120
) -> dict[str, Any]:
    """Call model with timeout protection."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(self.call_model, prompt, model_profile=model_profile, agent_id=agent_id),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        _logger.error(f"Model call timed out after {timeout_seconds}s for {model_profile}")
        return {
            "status": "timeout",
            "agent": agent_id or "unknown",
            "error": f"Model call timed out after {timeout_seconds}s",
            "profile": model_profile,
        }
```

### Files to modify
- Modify: `agents/runner.py`

### Effort
Trivial — single function change.

---

## Summary: Implementation Order

| Order | Priority | Change | Effort | Impact |
|-------|----------|--------|--------|--------|
| 1 | CRITICAL | Structured output schemas | Medium | Very High |
| 2 | CRITICAL | Content compression chain | Medium | Very High |
| 3 | CRITICAL | Token limit detection | Medium | High |
| 4 | CRITICAL | Reflection/think tool | Medium | High |
| 5 | IMPORTANT | Evaluation framework | Large | High |
| 6 | IMPORTANT | Timeout protection | Trivial | Medium |
| 7 | IMPORTANT | Parallel artifact processing | Small-Medium | Medium |
| 8 | IMPORTANT | Runtime config overrides | Small | Medium |
| 8a | IMPORTANT | Tool aggregation system | Small | Medium |
| 8b | NICE | MCP tool error wrapping | Small | Medium |
| 9a | NICE | LangGraph Cloud config | Trivial | Low |
| 9b | NICE | Extract mocks + agent registration validation | Small | Medium |
| 6b | IMPORTANT | Timeout protection | Trivial | Medium |

**Estimated total effort**: 2-3 weeks for all critical + important items. 1 additional week for the evaluation framework.
