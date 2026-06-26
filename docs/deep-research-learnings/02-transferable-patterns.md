# Transferable Patterns — ODR → FPL

Patterns from Open Deep Research that map directly to film pipeline needs.

## Pattern 1: Reflection Tool for Quality Gates

### ODR Implementation
```python
@tool(description="Strategic reflection tool for research planning")
def think_tool(reflection: str) -> str:
    """Use after each search to analyze results and plan next steps."""
    return f"Reflection recorded: {reflection}"
```

### FPL Equivalent
Replace the current orchestrator's rule-based `compute_actions()` with a reflection-driven approach:

```python
@tool(description="Creative reflection tool for film quality assessment")
def creative_reflection_tool(phase: str, analysis: str, decision: Literal["approve","revise","escalate"]) -> str:
    """Use after each film phase to evaluate creative quality and decide next steps.

    Called by the orchestrator after each phase completes. Forces deliberate
    pause for quality assessment before advancing.
    """
    return f"Creative reflection for {phase}: {decision} — {analysis[:200]}"
```

**Where to apply**: Replace `OrchestratorAgent.execute()` with tool-driven reflection. Instead of `{"action": "approve", ...}`, make the orchestrator's LLM call `creative_reflection_tool`.

**Why**: ODR's think_tool prevents the "rush to finish" anti-pattern. The film pipeline has the same problem — phases complete and auto-advance without meaningful quality assessment.

## Pattern 2: Structured Output Models for Every Agent

### ODR Implementation
```python
class Summary(BaseModel):
    summary: str
    key_excerpts: str

class Queries(BaseModel):
    queries: list[SearchQuery]

model.with_structured_output(Queries).ainvoke(prompt)
```

### FPL Equivalent
Add Pydantic output models for every agent:

```python
class ConstitutionOutput(BaseModel):
    theme: str
    tone: str
    emotional_promise: str
    visual_language: str
    camera_philosophy: str
    character_truths: list[CharacterTruth]
    taboo_mistakes: list[str]

class ScriptOutput(BaseModel):
    project_id: str
    title: str
    scenes: list[Scene]
    setup_payoff_map: list[SetupPayoffPair]
    total_scenes: int

# Then in agents:
class ConstitutionAgent(BaseAgent):
    def execute(self, model_output: dict) -> dict:
        parsed = ConstitutionOutput.model_validate(model_output)
        return parsed.model_dump()
```

**Where to apply**: Every agent that currently returns `dict[str, Any]`.

**Why**: Type safety, automatic validation, self-documenting schemas, and LangChain's `with_structured_output()` support.

## Pattern 3: Content Summarization Chain

### ODR Implementation
```python
# Truncate to configurable limit
result['raw_content'][:max_char_to_include]

# Summarize with dedicated model
summarization_model = init_chat_model(
    model=configurable.summarization_model,
    max_tokens=configurable.summarization_model_max_tokens,
).with_structured_output(Summary)

# Parallel summarization
summaries = await asyncio.gather(*summarization_tasks)
```

### FPL Equivalent
Add content compression when context grows too large:

```python
class ArtifactSummary(BaseModel):
    summary: str = Field(description="Concise summary")
    key_elements: str = Field(description="Critical elements that must be preserved")
    character_mentions: list[str] = Field(default_factory=list)
    location_mentions: list[str] = Field(default_factory=list)

async def compress_artifact_for_context(
    artifact_content: str,
    target_phase: str,
    max_chars: int = 8000
) -> ArtifactSummary:
    """Compress large artifacts to stay within context limits."""
    if len(artifact_content) <= max_chars:
        return ArtifactSummary(summary=artifact_content, key_elements="(full)")

    model = init_chat_model(model="deepseek/deepseek-chat")
    summarizer = model.with_structured_output(ArtifactSummary)

    return await asyncio.wait_for(
        summarizer.ainvoke([HumanMessage(content=f"Summarize for {target_phase}:\n{artifact_content[:30000]}")]),
        timeout=30.0
    )
```

**Where to apply**: `kb/packets.py` and `kb/curator.py` — when building KB context packets, compress large artifacts before injecting them.

**Why**: As films grow, the script (50+ scenes), shot matrix (100+ shots), and character bibles accumulate. Without compression, context windows overflow silently.

## Pattern 4: Token Limit Detection & Recovery

### ODR Implementation
```python
def is_token_limit_exceeded(exception, model_name=None) -> bool:
    provider = detect_provider(model_name)
    # OpenAI: "context_length_exceeded", "maximum context length"
    # Anthropic: "prompt is too long"
    # Gemini: "input too long"

def handle_token_limit_exceeded(state, config):
    reduced_notes = compress_research_notes(state["notes"], ...)
```

### FPL Equivalent
Add to `PromptRunner.call_model()`:

```python
def call_model(self, prompt, *, model_profile, agent_id=None):
    for attempt in range(3):
        try:
            return self.model_adapter.chat_json(...)
        except TokenLimitExceededError as e:
            if attempt == 2:
                raise  # Exhausted
            # Compress and retry
            prompt.rendered = self._compress_prompt(prompt.rendered, factor=0.5)
            _logger.warning(f"Token limit exceeded, compressing and retrying ({attempt+1}/3)")
        except ValueError:
            # Existing retry logic
            pass
```

**Where to apply**: `agents/runner.py` — `PromptRunner.call_model()` and `agents/model_adapter.py`.

**Why**: The film pipeline's context builds cumulatively (script → shot_bible → generation) and can easily exceed context limits.

## Pattern 5: Multi-Axis Quality Evaluation

### ODR Implementation
```python
# 6 evaluation axes, each with dedicated prompts and structured scoring
eval_relevance      → RelevanceScore (1-5, reasoning)
eval_structure      → StructureScore (1-5, reasoning)
eval_correctness    → vs. reference answer
eval_groundedness   → claims extracted and verified
eval_completeness   → vs. research brief
eval_overall_quality → 6 sub-scores
```

### FPL Equivalent
Add an evaluation framework for film artifacts:

```python
class FilmArtifactEvaluator:
    """Evaluates film artifacts against quality criteria."""

    EVAL_AXES = {
        "script": ["dramatic_structure", "character_voice", "scene_pacing", "dialogue_naturalness"],
        "constitution": ["thematic_coherence", "visual_language_clarity", "emotional_promise"],
        "shot_matrix": ["coverage_completeness", "duration_feasibility", "continuity_flow"],
        "generation": ["clip_quality", "character_consistency", "motion_smoothness", "prompt_fidelity"],
    }

    async def evaluate(self, artifact_type: str, content: dict, reference: dict) -> dict:
        evals = {}
        for axis in self.EVAL_AXES[artifact_type]:
            score = await self._eval_axis(axis, content, reference)
            evals[axis] = score
        return evals
```

**Where to apply**: New `evaluation/` package alongside `validation/`.

**Why**: Current validation is pass/fail based on heuristics, not quality. ODR shows how LLM-as-judge with structured scoring produces actionable feedback.

## Pattern 6: MCP Tool Wrapping with Auth & Error Handling

### ODR Implementation
```python
def wrap_mcp_authenticate_tool(tool):
    """Wrap MCP tool with auth error handling and user-friendly messages."""
    original_coroutine = tool.coroutine

    async def authentication_wrapper(**kwargs):
        try:
            return await original_coroutine(**kwargs)
        except BaseException as e:
            mcp_error = _find_mcp_error_in_exception_chain(e)
            if error_code == -32003:  # Auth required
                raise ToolException(f"Authentication required: {message} {url}")
            raise

    tool.coroutine = authentication_wrapper
    return tool
```

### FPL Equivalent
Enhance `mcp/server.py` tool registration:

```python
def wrap_film_mcp_tool(tool: BaseTool) -> BaseTool:
    """Wrap MCP tool with film-specific error handling."""
    original = tool.coroutine

    async def enhanced(**kwargs):
        try:
            return await original(**kwargs)
        except ProviderDownError:
            raise ToolException(
                "Video generation provider is currently unavailable. "
                "Use MCP tool 'check_provider_health' to see status."
            )
        except BudgetExceededError as e:
            raise ToolException(
                f"Budget limit reached: ${e.spent}/{e.cap}. "
                "Approve budget increase via MCP or switch to draft profile."
            )
        except ArtifactNotFoundError as e:
            raise ToolException(
                f"Artifact '{e.artifact_ref}' not found. "
                f"Check available artifacts via 'list_artifacts' tool."
            )

    tool.coroutine = enhanced
    return tool
```

**Where to apply**: `mcp/server.py` and `mcp/errors.py`.

**Why**: The MCP layer is the operator's interface — errors must be actionable, not raw stack traces.

## Pattern 7: Parallel Processing Within Nodes

### ODR Implementation
```python
# Parallel search
search_tasks = [tavily_client.search(q, ...) for q in queries]
results = await asyncio.gather(*search_tasks)

# Parallel summarization
summarization_tasks = [summarize_webpage(model, content) for content in contents]
summaries = await asyncio.gather(*summarization_tasks)
```

### FPL Equivalent
Parallelize artifact validation and KB context building:

```python
async def build_kb_context_parallel(
    project_id: str, phase: str, agent_id: str, task: str
) -> KBContextPacket:
    """Build KB context with parallel artifact loading."""

    # Load artifacts in parallel
    artifact_ids = get_required_artifacts(phase)
    load_tasks = [
        artifact_store.load_async(project_id, phase, aid, version)
        for aid, version in artifact_ids
    ]
    artifacts = await asyncio.gather(*load_tasks, return_exceptions=True)

    # Summarize in parallel
    summarize_tasks = [
        compress_artifact_for_context(content, phase)
        for content in artifacts if not isinstance(content, Exception)
    ]
    summaries = await asyncio.gather(*summarize_tasks)

    return assemble_context_packet(summaries, agent_id, task)
```

**Where to apply**: `kb/curator.py`, `kb/packets.py`, and graph nodes that load multiple artifacts.

**Why**: Current KB context building loads artifacts sequentially. With 4-6 artifact types per phase, parallel loading cuts context-building time by 3-4x.

## Pattern 8: Centralized Prompt Registry with Date Injection

### ODR Implementation
```python
# prompts.py — all templates in one place
summarize_webpage_prompt = """\
Date: {date}
..."""
report_planner_query_writer_instructions = """\
Date: {today}
Topic: {topic}
..."""

# Injected at runtime
prompt_content = summarize_webpage_prompt.format(
    webpage_content=webpage_content,
    date=get_today_str()
)
```

### FPL Equivalent
Add date context to all prompts:

```python
class DateAwareTemplate(PromptTemplate):
    """Prompt template that always includes date context."""

    def render(self, **kwargs) -> str:
        kwargs.setdefault("date", datetime.now().strftime("%Y-%m-%d"))
        return super().render(**kwargs)
```

**Where to apply**: All templates in `agents/prompt_templates/`.

**Why**: Temporal context is critical for film generation — models should know the current date for cultural awareness in creative writing.

## Pattern 9: Graceful Degradation at Every Level

### ODR Implementation
```python
# Search: return empty with helpful message
if not search_results:
    return "No valid search results found. Please try different queries."

# Summarization: return original content
except asyncio.TimeoutError:
    return webpage_content
except Exception:
    return webpage_content

# MCP: return empty list
except Exception:
    return []
```

### FPL Equivalent
Enhance error resilience in graph nodes:

```python
async def visual_dev_node(state: dict, config: RunnableConfig) -> dict:
    try:
        result = await _run_agent(state, "reference-strategy-planner", "visual_dev", task)
    except ProviderUnavailableError:
        # Degrade: skip reference generation, use text-only description
        result = _fallback_text_references(state)
        state.setdefault("issues", []).append({
            "code": "FALLBACK_VISUAL_DEV",
            "severity": "warning",
            "message": "Reference images could not be generated. Using text-only descriptions."
        })
    except TokenLimitExceededError:
        # Degrade: compress context and retry once
        state["_compressed_context"] = True
        result = await _run_agent(state, "reference-strategy-planner", "visual_dev", task)

    return result
```

**Where to apply**: All phase nodes in `graph/nodes.py`.

**Why**: A failure in one phase shouldn't block the entire pipeline. Degradation paths keep the pipeline moving.

## Pattern 10: Clean Graph Entry Point

### ODR Implementation
```json
// langgraph.json
{
    "graphs": {
        "Deep Researcher": "./src/open_deep_research/deep_researcher.py:deep_researcher"
    },
    "auth": {
        "path": "./src/security/auth.py:auth"
    }
}
```

### FPL Equivalent
FPL already has `graph/graph.py:build_graph()` but it's not exposed as a LangGraph Cloud deployable entry point. Add:

```json
// langgraph.json (at project root)
{
    "graphs": {
        "Film Pipeline": "./src/film_pipeline/graph/graph.py:graph"
    },
    "auth": {
        "path": "./src/film_pipeline/app/health.py:auth"
    }
}
```

With a module-level compiled graph:

```python
# graph/graph.py
graph = build_graph()  # Module-level for langgraph.json
```

**Where to apply**: New `langgraph.json` at project root + module-level graph export.

**Why**: Enables LangGraph Studio debugging and Cloud deployment.
