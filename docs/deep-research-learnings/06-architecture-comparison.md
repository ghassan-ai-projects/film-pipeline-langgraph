# Architecture Comparison — ODR vs. FPL

Side-by-side technical comparison of both systems.

## System Overview

| Dimension | Open Deep Research | Film Pipeline LangGraph |
|---|---|---|
| **Purpose** | Automated research and report generation | Automated film production from idea to delivery |
| **Framework** | LangGraph + LangChain | LangGraph + LangChain |
| **Language** | Python 3.11+ | Python 3.12+ |
| **Scale** | ~10 Python files (core), ~30 files total | ~60+ Python files, 200+ docs |
| **Phases** | 1 phase (research → report) | 11 phases (intake → delivery) |
| **Graph style** | Flat with loops | Linear with approval gates |

## Graph Architecture

### ODR: Flat Graph with Self-Looping
```
START
  ↓
clarify_with_user (optional)
  ↓
conduct_deep_research ←──┐ (loop: research → reflection → research)
  ↓                        │
generate_final_summary ────┘
  ↓
END
```

**Key characteristics:**
- 4 nodes, minimal edges
- Self-looping via conditional edges (not subgraphs)
- Research agent decides when to stop (ResearchComplete tool)
- Reflection is mandatory between searches

### FPL: Linear Pipeline with Human Gates
```
START
  ↓
phase_router (conditional entry)
  ↓
[intake → gate] → [constitution → gate] → [development → gate] → [script → gate]
  ↓
[visual_dev → gate] → [shot_bible → gate] → [gen_planning → gate]
  ↓
[generation → gate] → [qc (subgraph) → gate] → [post → gate] → [delivery → gate]
  ↓
END
```

**Key characteristics:**
- 15+ nodes, extensive edge routing
- Each phase → consistency_check → await_approval → next phase
- Human gates between every phase (configurable auto-approve)
- Subgraph for QC (parallel validation)
- Repair loop for failed phases

## State Management

### ODR State
```python
class ResearchState(TypedDict):
    # Scalars (last-write-wins)
    topic: str
    research_brief: ResearchBrief  # Pydantic model!
    completed: bool

    # Append-only (operator.add)
    search_history: Annotated[list[SearchResult], operator.add]
    web_research_results: Annotated[list, operator.add]
    notes: Annotated[list[str], operator.add]
    messages: Annotated[list[BaseMessage], add_messages]
```
**Pattern**: Pydantic models embedded in TypedDict. Type-safe, validated, serializable.

### FPL State
```python
class StudioGraphState(TypedDict, total=False):
    # Scalars (last-write-wins)
    project_id: str
    current_phase: str
    approved: bool
    completed: bool

    # Ref pointers (scalar strings)
    constitution_ref: str
    script_ref: str
    shot_matrix_ref: str
    # ... 15+ ref pointers ...

    # Append-only
    artifact_refs: Annotated[list[str], add]
    issues: Annotated[list[dict[str, object]], add]
    validation_report_refs: Annotated[list[str], add]
    generation_requests: Annotated[list[dict[str, object]], add]

    # Snapshots (dicts)
    budget_snapshot: dict[str, object]
    provider_health_snapshot: dict[str, object]
    resolved_config: dict[str, object]
```
**Pattern**: Strings as ref pointers to persistent artifacts. Lightweight state, artifacts in store. Good for checkpoint size. But ref pointers are strings — no type safety on what they point to.

## Agent System

### ODR: LLM-as-Agent (Tool-Calling Pattern)
```python
# LLM calls tools directly — no agent class abstraction
model = init_chat_model(model=research_model)
model_with_tools = model.bind_tools(tools)
response = await model_with_tools.ainvoke(messages)
```
**Pattern**: Lean. LLM is the agent. No BaseAgent subclassing. Tools are the interface.

### FPL: Agent Class Hierarchy
```python
class BaseAgent(ABC):
    """Standard lifecycle: prepare → execute → validate."""
    def prepare(self, state, kb_context, task) -> dict
    def execute(self, model_output) -> dict
    def validate(self, result) -> bool

class ScreenwriterAgent(BaseAgent): ...
class ConstitutionAgent(BaseAgent): ...
# 14 agent subclasses
```
**Pattern**: Rich abstraction with lifecycle hooks. Each agent has defined inputs, outputs, KB domains. Good for complex domain-specific workflows.

**Trade-off**: ODR's approach is simpler but less structured. FPL's approach has more overhead but better separation of concerns for a 14-agent system.

## Prompt System

### ODR
```python
# Centralized in prompts.py
report_planner_query_writer_instructions = """\
You are an expert technical writer...
Date: {today}
Topic: {topic}
Report organization: {report_organization}
Number of queries: {number_of_queries}
"""

# Used with .format()
prompt = template.format(today=get_today_str(), topic=topic, ...)
```
**Pattern**: Simple format strings, all in one file. No versioning, no role/constraint/output separation.

### FPL
```python
# Dedicated PromptTemplate class with RCTCO framework
@dataclass
class RCTCOPrompt:
    role: str       # Who the agent is
    core_task: str  # What to do
    context: str    # KB context
    constraints: str # Rules
    output_format: str  # Expected schema

# Mix of dedicated templates + generic assembly
template = registry.get_template("screenwriter-agent")
rendered = template.render(scenes=scenes_data, characters=character_data, ...)
```
**Pattern**: Structured RCTCO format with a template registry. Dedicated templates for critical agents, generic assembly for utility agents. Stronger than ODR's simple format strings.

## Tool System

### ODR
```python
# Runtime tool aggregation from 3 sources
tools = [tool(ResearchComplete), think_tool]        # Core
tools.extend(await get_search_tool(search_api))     # Provider tools
tools.extend(await load_mcp_tools(config, names))   # External (MCP)

# Tool wrapping for error handling
wrapped = wrap_mcp_authenticate_tool(tool)

# Tool metadata for routing decisions
tool.metadata = {"type": "search", "name": "web_search"}
```
**Pattern**: Aggregation + wrapping + metadata. Tools are first-class objects with lifecycle management.

### FPL
```python
# MCP tools registered in mcp/server.py
# Provider tools in providers/adapters/
# No centralized tool aggregation
# No tool wrapping for error handling
# No tool metadata

# Agents call PromptRunner directly — no tool-based interface
```
**Pattern**: MCP surface exists but no internal tool aggregation. Agents don't use tool-calling — they use the PromptRunner.execute() pattern.

**Gap**: FPL doesn't use LangChain's tool-calling pattern for internal agents. The orchestrator makes decisions via raw JSON outputs, not tool calls.

## Error Handling

### ODR
```
Model call → timeout(60s) → structured_output_retry(3x)
    ↓ fail
Summarization → timeout(60s) → return raw content
    ↓ fail
Search → empty results → helpful message
    ↓ fail
MCP → auth error → ToolException with URL
    ↓ fail
Token limit → detect provider → compress → retry
    ↓ fail
Return graceful degradation result
```
**Pattern**: Defense in depth. Every layer has fallback behavior. Errors propagate as actionable messages to the LLM.

### FPL
```
Model call → ValueError retry(3x, decreasing temp)
    ↓ fail
Return: {"status": "model_failure", "error": "all_retries_exhausted"}
    ↓
No timeout
No token limit detection
No content compression
No graceful degradation in nodes
```
**Pattern**: Single retry path. No timeout. No content-aware error recovery.

## Evaluation

### ODR: 6-Axis LLM Judge
```
Overall Quality → {research_depth, source_quality, analytical_rigor,
                    practical_value, balance, writing_quality}
Relevance → score 1-5 + reasoning
Structure → score 1-5 + reasoning
Correctness → vs reference answer
Groundedness → claims extracted and verified
Completeness → vs research brief
```
**Pattern**: Comprehensive, automated, data-driven. Benchmark dataset for regression testing.

### FPL: Rule-Based Validation
```
Script structure → check scene count, dialogue lines
Scene continuity → check scene_id references
Reference usability → check image dimensions, file existence
Assembly → check clip ordering
```
**Pattern**: Structural validation only. No quality assessment. Pass/fail binary. No benchmark dataset.

## Configuration

### ODR: Field-Level with Env Var Overrides
```python
class Configuration(BaseModel):
    max_web_research_loops: int = Field(default=3, ge=1, le=10)
    research_model: str = Field(default="openai/gpt-4.1")
    search_api: SearchAPI = Field(default=SearchAPI.TAVILY)
    max_search_results: int = Field(default=5, ge=1, le=20)
    max_content_length: int = Field(default=10000, ge=1000)
    # ... 15+ fields ...
```
**Pattern**: Every setting is a typed field with validation and default. Overridable via env vars with sensible defaults.

### FPL: Profile-Based Merging
```yaml
# profiles/base.studio.yaml
# profiles/film-type.narrative.yaml
# profiles/quality.draft.yaml
# profiles/provider.seedance_primary.yaml
# profiles/review.strict_continuity.yaml
```
**Pattern**: Declarative profiles merged at startup. Flexible but harder to do "quick overrides" for individual runs. No env var override path.

## Code Quality

| Metric | ODR | FPL |
|--------|-----|-----|
| Docstrings | Google-style, consistent ✅ | Mixed, inconsistent ⚠️ |
| Type hints | Throughout ✅ | Throughout ✅ |
| Linting | Ruff with strict rules ✅ | Pre-commit with ruff ✅ |
| Tests | Limited unit tests ⚠️ | Mock infrastructure + test scenarios ✅ |
| Package structure | Flat, 3 packages | Deep, 15 packages |
| Dependency count | ~40 deps | ~40+ deps |
| py.typed marker | ✅ | Unknown ❓ |
| Versioning | Semantic (0.0.16) ✅ | Has version.py ❓ |

## What Each Project Does Better

### ODR Wins
1. **Structured output**: Pydantic models for every node output
2. **Error resilience**: Multi-layer defense with graceful degradation
3. **Evaluation**: Comprehensive, automated quality measurement
4. **Tool system**: Clean aggregation + wrapping + metadata
5. **Simplicity**: 4-node graph, easy to understand and debug
6. **Content management**: Truncation, summarization, deduplication
7. **Token limit handling**: Detection + compression + retry

### FPL Wins
1. **Rich domain model**: 14 specialized agents, not generic LLM
2. **Artifact versioning**: Git-based checkpointing with branches
3. **Human gates**: 10 structured approval points with MCP surface
4. **KB system**: Domain-specific knowledge base with context building
5. **Mock infrastructure**: Full mock runtime for testing without real models
6. **Config system**: Profile-based merging for different quality tiers
7. **Pipeline complexity**: Handles 11 phases with inter-phase dependencies
8. **Orchestrator state**: Rich decision context (provider health, budget, convergence)
9. **Prompt framework**: RCTCO structure is cleaner than raw format strings
10. **Observability**: Audit trails, metrics, blocker tracking, cost ledgers
