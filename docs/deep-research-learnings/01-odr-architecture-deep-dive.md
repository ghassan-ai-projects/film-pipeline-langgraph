# ODR Architecture Deep Dive

## 1. Graph Design Philosophy

### 1.1 Clean 4-Node Architecture

ODR's main graph (`deep_researcher.py`) uses a minimalist 4-node design:

```
START → clarify_with_user (optional clarification)
     → conduct_deep_research (with research → reflection loop)
     → generate_final_summary
     → END
```

Key principles:
- **Minimal nodes, maximal function**: Each node does one thing well
- **Self-directed loops**: The research node loops back to itself via reflection
- **No subgraphs needed**: The design is flat, using conditional edges for control flow
- **Explicit completion signals**: `ResearchComplete` tool call to signal done

### 1.2 Reflection as a First-Class Pattern

The `think_tool` is NOT just a utility — it's an architectural pattern:

```python
@tool(description="Strategic reflection tool for research planning")
def think_tool(reflection: str) -> str:
    """Use this tool after each search to analyze results and plan next steps."""
```

The tool enforces a *deliberate pause* in the workflow. The LLM MUST call it before deciding next steps. This prevents the "eager action" problem where an agent rushes to complete without evaluating quality.

### 1.3 The "Plan-and-Execute" Legacy Pattern

The legacy `graph.py` shows a sophisticated multi-stage approach:

```
generate_report_plan → human_feedback (interrupt)
    ↳ build_section_with_web_research (subgraph, parallel via Send)
        ↳ generate_queries → search_web → write_section (with grader loop)
    ↳ gather_completed_sections
    ↳ write_final_sections
    ↳ compile_final_report
```

This pattern is directly applicable to the film pipeline's script → shot_bible → generation chain where:
- Sections = scenes
- Web research = reference generation
- Section grading = clip validation

## 2. State Management

### 2.1 TypedDict with Reducers

ODR uses `TypedDict` with `Annotated` reducers for append-only fields:

```python
class ResearchState(TypedDict):
    topic: str
    research_brief: ResearchBrief  # Pydantic model
    search_history: Annotated[list[SearchResult], operator.add]  # accumulates
    completed: bool
```

FPL already does this (`StudioGraphState`), but ODR's pattern of embedding Pydantic models (not raw dicts) in the state is a clear upgrade.

### 2.2 Pydantic Models for Structured Output

Every node output in ODR is a Pydantic model:

```python
class ResearchComplete(BaseModel):
    """Signal that research is complete and ready for synthesis."""

class Summary(BaseModel):
    summary: str = Field(description="Key points...")
    key_excerpts: str = Field(description="Important excerpts...")

class Queries(BaseModel):
    queries: list[SearchQuery]
```

This means:
- Structured output parsing via `with_structured_output(Queries)`
- Automatic validation of model outputs
- Type-safe access to fields
- Serialization/deserialization is handled

FPL's agents return raw dicts. This is a major gap.

### 2.3 State Injection via config

ODR separates "graph state" from "runtime config":

```python
class Configuration(BaseModel):
    max_web_research_loops: int = 3
    research_model: str = "openai/gpt-4.1"
    search_api: SearchAPI = SearchAPI.TAVILY
    max_search_results: int = 5
    max_content_length: int = 10000
```

Config is passed through `RunnableConfig` and accessed via `Configuration.from_runnable_config(config)`. FPL uses `GraphServices` injected as `_services` in state, which is a similar pattern but with the non-serializable serializer hack.

## 3. Tool System Architecture

### 3.1 Tool Aggregation Pattern

ODR assembles tools at runtime from multiple sources:

```python
async def get_all_tools(config: RunnableConfig):
    tools = [tool(ResearchComplete), think_tool]  # core tools
    search_tools = await get_search_tool(search_api)  # provider-specific
    tools.extend(search_tools)
    mcp_tools = await load_mcp_tools(config, existing_tool_names)  # external
    tools.extend(mcp_tools)
    return tools
```

This is elegant — tools come from 3 sources (core, search API, MCP), and conflicts are resolved by deduplication. FPL doesn't have a comparable tool aggregation system.

### 3.2 MCP Tool Wrapping

ODR wraps MCP tools with comprehensive error handling:

```python
def wrap_mcp_authenticate_tool(tool):
    async def authentication_wrapper(**kwargs):
        try:
            return await original_coroutine(**kwargs)
        except BaseException as original_error:
            mcp_error = _find_mcp_error_in_exception_chain(original_error)
            if error_code == -32003:  # auth
                raise ToolException(user_friendly_message)
            raise original_error
    tool.coroutine = authentication_wrapper
```

This propagates clear, actionable errors to the LLM instead of raw MCP exceptions. FPL's MCP tools could benefit from this pattern.

### 3.3 Multi-Provider Search Abstraction

ODR abstracts search across providers:

```python
async def get_search_tool(search_api: SearchAPI):
    if search_api == SearchAPI.ANTHROPIC:
        return [{"type": "web_search_20250305", "max_uses": 5}]
    elif search_api == SearchAPI.OPENAI:
        return [{"type": "web_search_preview"}]
    elif search_api == SearchAPI.TAVILY:
        return [tavily_search]
```

Each provider has a different interface, but the abstraction gives the LLM a consistent `web_search` tool name. FPL's provider adapters (`veo_fast.py`, `seedance_openrouter.py`, `imagen4_gemini.py`) follow a similar pattern but could be more strongly abstracted.

## 4. Prompt Engineering

### 4.1 Centralized, Date-Aware Templates

ODR's prompts are in `prompts.py` with consistent patterns:

```python
report_planner_query_writer_instructions = """\
You are an expert technical writer...
Date: {today}
Topic: {topic}
Report organization: {report_organization}
Number of queries: {number_of_queries}
"""
```

Every prompt gets `{today}` injected for temporal awareness. FPL's prompt templates are in `agents/prompt_templates/` but don't consistently use date injection.

### 4.2 Context Truncation

ODR aggressively truncates webpage content:

```python
max_char_to_include = configurable.max_content_length  # configurable limit
result['raw_content'][:max_char_to_include]  # truncate
```

And uses a separate summarization model to condense content:

```python
summarization_model = init_chat_model(
    model=configurable.summarization_model,
    max_tokens=configurable.summarization_model_max_tokens,
).with_structured_output(Summary)
```

FPL has no equivalent content compression for large artifacts (e.g., script with 50+ scenes feeding into shot_bible context).

## 5. Parallel Execution Patterns

### 5.1 asyncio.gather for Tool Calls

ODR parallelizes search queries:

```python
search_tasks = [tavily_client.search(query, ...) for query in queries]
search_results = await asyncio.gather(*search_tasks)
```

And parallelizes summarization:

```python
summarization_tasks = [summarize_webpage(model, content) for content in contents]
summaries = await asyncio.gather(*summarization_tasks)
```

FPL uses LangGraph's `Send` API for parallel QC but doesn't parallelize within nodes.

### 5.2 Timeout Protection

Every async operation has a timeout:

```python
summary = await asyncio.wait_for(
    model.ainvoke([HumanMessage(content=prompt_content)]),
    timeout=60.0
)
```

FPL's `PromptRunner.call_model()` has a 3-retry fallback but no timeout protection.

## 6. Evaluation Framework

### 6.1 Multi-Axis Evaluation

ODR evaluates reports on 6 axes:

```python
eval_overall_quality  → research_depth, source_quality, analytical_rigor,
                         practical_value, balance_and_objectivity, writing_quality
eval_relevance        → score 1-5 with reasoning
eval_structure        → score 1-5 with reasoning
eval_correctness      → vs. reference answer
eval_groundedness     → claims extracted and verified
eval_completeness     → vs. research brief
```

Each evaluator is a structured LLM call (GPT-4.1) with a dedicated prompt. FPL has no comparable evaluation framework — validation is rule-based.

### 6.2 Data-Driven Benchmarking

ODR tests against a benchmark dataset (`run_evaluate.py`, `pairwise_evaluation.py`):

```python
eval_result = cast(OverallQualityScore,
    eval_model.with_structured_output(OverallQualityScore).invoke([...]))
```

FPL has testing infrastructure (`testing/`) but no quality evaluation benchmark dataset.

## 7. Error Handling & Resilience

### 7.1 Token Limit Detection

ODR detects token limit exceeded across providers:

```python
def is_token_limit_exceeded(exception, model_name=None) -> bool:
    provider = _detect_provider(model_name)
    # Check provider-specific error patterns
    # OpenAI: "context_length_exceeded", "maximum context length"
    # Anthropic: "prompt is too long"
    # Gemini: "input too long", "maximum number of tokens"
```

And re-prompts with context reduction:

```python
def handle_token_limit_exceeded(state, config):
    reduced_notes = compress_research_notes(state["notes"], ...)
    return {"notes": reduced_notes}
```

FPL's only error resilience is the 3-retry model fallback in `PromptRunner.call_model()`. Token limit handling is absent.

### 7.2 Graceful Degradation

ODR degrades gracefully at multiple levels:

```python
# Search failure
if not search_results:
    return "No valid search results found. Please try different queries."

# Summarization failure
except asyncio.TimeoutError:
    logging.warning("Summarization timed out, returning original content")
    return webpage_content

# MCP failure
except Exception:
    return []  # Return empty MCP tools
```

FPL has `failure_classifier.py` but the actual graceful degradation in nodes is less systematic.

## 8. Code Quality & Packaging

### 8.1 Google-Style Docstrings

Every function in ODR has thorough docstrings:

```python
async def generate_report_plan(state: ReportState, config: RunnableConfig):
    """Generate the initial report plan with sections.

    This node:
    1. Gets configuration for the report structure and search parameters
    2. Generates search queries to gather context for planning
    3. Performs web searches using those queries
    4. Uses an LLM to generate a structured plan with sections

    Args:
        state: Current graph state containing the report topic
        config: Configuration for models, search APIs, etc.

    Returns:
        Dict containing the generated sections
    """
```

FPL's docstrings are less consistent — some functions have them, many don't.

### 8.2 Strict Linting

```toml
[tool.ruff]
lint.select = ["E", "F", "I", "D", "D401", "T201", "UP"]
lint.ignore = ["UP006", "UP007", "UP035", "D417", "E501"]
```

### 8.3 Semantic Versioning

ODR: `version = "0.0.16"` with proper changelog discipline.
FPL: version in `app/version.py` but unclear how it's maintained.

## Summary: What Makes ODR Production-Grade

1. **Structured outputs everywhere** — Pydantic models for every node
2. **Deliberate reflection** — think_tool as architectural pattern
3. **Multi-layer error resilience** — timeouts, retries, token limit handling
4. **Data-driven evaluation** — 6-axis automated eval with benchmark dataset
5. **Content compression** — Summarization chain to stay within token limits
6. **Parallel execution** — asyncio.gather for independent operations
7. **Centralized prompts** — Single source of truth with parameter injection
8. **Clean documentation** — Google-style docstrings with numbered steps
