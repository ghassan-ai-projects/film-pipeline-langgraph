# Gap Analysis — ODR vs. FPL

Systematic comparison of capabilities. ✅ = present, ⚠️ = partial, ❌ = missing.

## 1. Architecture & Design

| Capability | ODR | FPL | Gap |
|---|---|---|---|
| Clean graph with minimal nodes | ✅ 4 nodes | ⚠️ 15+ nodes, many passthrough | FPL's graph is complex; consider collapsing passthrough nodes into edges |
| Reflection/think tool pattern | ✅ think_tool | ❌ | No deliberate pause mechanism between phases |
| Plan-then-execute workflow | ✅ (legacy) | ⚠️ Partially (intake→spine→generation) | Spine exists but no explicit "plan" phase that reviews before executing |
| Human-in-the-loop gates | ✅ interrupt() | ✅ interrupt_for_gate() | Comparable |
| Parallel subgraph execution | ✅ Send() API | ✅ Send() API (QC subgraph) | Comparable |
| Multi-agent supervisor pattern | ✅ (legacy) | ⚠️ OrchestratorAgent exists but doesn't supervise agents — it reviews outputs | No agent-to-agent handoff supervision |

## 2. State Management

| Capability | ODR | FPL | Gap |
|---|---|---|---|
| TypedDict state with reducers | ✅ | ✅ | Comparable |
| Pydantic models in state | ✅ (ResearchBrief, SearchResult) | ❌ Records raw dicts | Major gap — no type safety within state values |
| Structured output parsing | ✅ with_structured_output() | ❌ | Agents return raw dicts, no schema validation on model output |
| State injection pattern | ✅ RunnableConfig | ✅ GraphServices (\_services in state) | Different approach, both valid |
| Orchestrator state domain | ❌ | ✅ dedicated orchestrator_state.py | FPL advantage — richer decision context |

## 3. Tool System

| Capability | ODR | FPL | Gap |
|---|---|---|---|
| Runtime tool aggregation | ✅ get_all_tools() | ❌ | No tool aggregation system |
| MCP tool wrapping (auth+errors) | ✅ wrap_mcp_authenticate_tool() | ⚠️ Basic MCP tools exist | Missing auth wrapping and user-friendly error messages |
| Tool name conflict resolution | ✅ Skip with warning | ❌ | MCP tools are added without name conflict checks |
| Provider-abstracted tools | ✅ SearchAPI abstraction | ⚠️ Provider adapters exist but less unified | Provider adapters are independent files, not a unified tool system |
| Tool metadata for routing | ✅ tool.metadata["type"] = "search" | ❌ | No tool metadata for dynamic routing decisions |

## 4. Error Handling & Resilience

| Capability | ODR | FPL | Gap |
|---|---|---|---|
| Token limit detection | ✅ Per-provider detection | ❌ | Can't detect token limit exceeded |
| Context reduction on limit | ✅ compress and retry | ❌ | No context compression on failure |
| Timeout protection | ✅ asyncio.wait_for(60s) | ❌ | No timeout on model calls |
| Graceful degradation | ✅ Multi-level | ⚠️ failure_classifier.py exists | Classifier exists but nodes don't use it |
| Structured output retry | ✅ max_structured_output_retries | ✅ 3-retry model fallback | FPL's retry is on raw dict, ODR's is on structured output |
| Error propagation to LLM | ✅ ToolException with messages | ❌ | Errors likely bubble up as raw exceptions |

## 5. Content Management

| Capability | ODR | FPL | Gap |
|---|---|---|---|
| Content truncation | ✅ max_content_length config | ❌ | No content length limits |
| Summarization chain | ✅ Dedicated summarization model | ❌ | No content summarization |
| Parallel content processing | ✅ asyncio.gather | ❌ | No parallel artifact loading/processing |
| Deduplication | ✅ URL dedup in search | ⚠️ Artifact versioning prevents some dupes | No explicit deduplication for context building |

## 6. Quality & Evaluation

| Capability | ODR | FPL | Gap |
|---|---|---|---|
| Automated evaluation | ✅ 6-axis LLM-judge eval | ❌ | No automated quality evaluation |
| Benchmark dataset | ✅ Deep Research Bench | ❌ | No evaluation dataset |
| Pairwise comparison | ✅ A/B testing framework | ❌ | No comparative evaluation |
| Groundedness checking | ✅ Claims extracted and verified | ❌ | No groundedness verification |
| Structured scoring | ✅ 1-5 scales with reasoning | ❌ | No structured quality scoring |
| Evaluation prompts | ✅ Centralized in tests/prompts.py | ❌ | No evaluation prompts |

## 7. Prompt System

| Capability | ODR | FPL | Gap |
|---|---|---|---|
| Centralized prompts | ✅ Single prompts.py | ⚠️ Split across templates + inline | Dedicated templates exist but generic RCTCO assembly for non-critical agents |
| Date injection | ✅ Every prompt gets {today} | ❌ | No date injection |
| Parameterized consistently | ✅ Format strings | ⚠️ Template.render() | Template system is good but inconsistent |
| Role/task/context/constraints/output structure | ❌ (implicit) | ✅ RCTCO framework | FPL advantage — structured prompt building |
| Prompt versioning | ❌ | ❌ | Neither has prompt version tracking |

## 8. Testing & Observability

| Capability | ODR | FPL | Gap |
|---|---|---|---|
| Unit tests | ⚠️ Limited | ✅ testing/ package | FPL advantage |
| Integration tests | ❌ | ✅ e2e-test-scenarios.md | FPL advantage |
| Mock provider | ❌ | ✅ mock_provider.py, mock_image_provider.py | FPL advantage |
| Mock human gates | ❌ | ✅ mock_human.py | FPL advantage |
| Evaluation dataset | ✅ | ❌ | ODR advantage |
| Audit trail | ❌ | ✅ audit.py, ledger.py | FPL advantage |
| Cost tracking | ❌ | ✅ budget.py, ledger.py | FPL advantage |

## 9. Configuration

| Capability | ODR | FPL | Gap |
|---|---|---|---|
| Field-level config | ✅ Configuration(BaseModel) | ⚠️ Profile-based merging | Different approaches. ODR's is more granular. |
| Env var overrides | ✅ | ❌ (profile-based) | FPL can't override individual fields via env vars |
| Config validation | ✅ Pydantic validation | ⚠️ config/validator.py exists | Validator exists but doesn't validate all fields |
| Sensible defaults | ✅ Every field has default | ⚠️ Some defaults, some required | Some FPL configs have no defaults, requiring complex profiles |
| Runtime config injection | ✅ RunnableConfig | ✅ GraphServices | Comparable |

## 10. Code Quality

| Capability | ODR | FPL | Gap |
|---|---|---|---|
| Google-style docstrings | ✅ Consistent | ⚠️ Inconsistent | Some FPL functions have docstrings, many don't |
| Type hints | ✅ Throughout | ✅ Throughout | Comparable |
| Ruff linting | ✅ Strict config | ✅ pre-commit-config.yaml | Comparable |
| py.typed marker | ✅ | ❓ Unknown | Check if FPL ships types |
| Semantic versioning | ✅ 0.0.16 | ❓ version.py exists | Unclear versioning discipline |

## Gap Severity Summary

### 🔴 Critical (must fix)
1. **No structured output schemas** — agents return raw dicts, no validation
2. **No content compression** — context windows will overflow on real films
3. **No token limit handling** — will crash on large scripts/shot matrices
4. **Missing reflection pattern** — no deliberate quality pause between phases

### 🟡 Important (should fix)
5. **No quality evaluation framework** — can't measure if output is good
6. **No timeout on model calls** — can hang indefinitely
7. **No tool aggregation/conflict system** — MCP tools added without checks
8. **No parallel artifact processing** — sequential KB context building
9. **No date injection in prompts** — temporal awareness gap
10. **MCP error messages not user-friendly** — raw exceptions surface to operator

### 🟢 Nice to have
12. **No pairwise evaluation** — can't A/B test pipeline changes
13. **No groundedness verification** — can't verify if generated content matches script
14. **Inconsistent docstrings** — some agents well-documented, others bare
15. **No runtime config overrides** — can't tweak individual settings via env vars
