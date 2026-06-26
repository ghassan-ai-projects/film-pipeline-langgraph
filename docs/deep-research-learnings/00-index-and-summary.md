# Deep Research Learnings — Index & Executive Summary

Analysis date: 2026-06-24
Source project: `external-projects/open_deep_research` (v0.0.16, LangChain/LangGraph)
Target project: `my-projects/film-pipeline-langgraph`

## What Was Analyzed

### Open Deep Research (ODR)
- **Core implementation**: `deep_researcher.py` — 4-node LangGraph graph (plan → research → reflection → write)
- **Legacy variants**: Plan-and-execute (`legacy/graph.py`) and multi-agent supervisor (`legacy/multi_agent.py`)
- **Configuration system**: `configuration.py` — field-level config with env-var + UI override inheritance
- **State management**: Pydantic TypedDict states with proper reducer logic
- **Tool system**: Tavily search, MCP tool loading with auth, reflection tool (think_tool)
- **Prompt system**: Dedicated prompt templates per node, parameterized, date-injected
- **Evaluation**: 6-axis evaluation (relevance, structure, groundedness, correctness, completeness, overall quality) on a dedicated benchmark dataset
- **Testing & packaging**: `pyproject.toml` with ruff linting, Google-style docstrings, semantic versioning

### Film Pipeline LangGraph (FPL)
- **~60+ Python source files** across 15 packages
- **11-phase film pipeline**: intake → constitution → development → script → visual_dev → shot_bible → gen_planning → generation → qc → post → delivery
- **Orchestrator**: Autonomous quality gate between phases (approve/revise/escalate)
- **Agent system**: 14 agent implementations (constitution, development, screenwriter, visual_dev, shot_bible, gen_planner, qc, assembly, etc.)
- **Subgraphs**: Parallel QC, generation subgraphs
- **MCP surface**: Operator tools for approve_phase, request_revision
- **Checkpoint system**: Git-based artifact versioning with branch support
- **Config system**: Profile-based config merging (base + film-type + quality + provider + review)
- **Model routing**: Profile-based model selection (creative_writer, strict_validator, etc.)

## Key Documents in This Analysis

| # | Document | Focus |
|---|----------|-------|
| 01 | [ODR Architecture Deep Dive](./01-odr-architecture-deep-dive.md) | Technical architecture, patterns, and design decisions |
| 02 | [Transferable Patterns](./02-transferable-patterns.md) | What FPL can directly adopt from ODR |
| 03 | [Gap Analysis](./03-gap-analysis.md) | Critical gaps in FPL vs. ODR best practices |
| 04 | [Improvement Recommendations](./04-improvement-recommendations.md) | Prioritized, concrete improvements for FPL |
| 05 | [Critical Issues](./05-critical-issues.md) | Bugs, anti-patterns, and risks in current FPL codebase |
| 06 | [Architecture Comparison](./06-architecture-comparison.md) | Side-by-side comparison of both systems |
| 07 | [Implementation Roadmap](./07-implementation-roadmap.md) | Phased plan to apply learnings |
| 08 | [Agent Model Transformation](./08-agent-model-transformation.md) | What makes ODR agents powerful vs. FPL agents |
| 09 | [Smart Sub-Agents](./09-smart-sub-agents.md) | Give FPL agents tools for self-revision and self-assessment |
| 10 | [Context & Output Management](./10-context-and-output-management.md) | Input overflow and output truncation solutions |
| 11 | [Validation Comparison](./11-validation-comparison.md) | ODR's LLM-as-judge vs. FPL's rule-based validators |
| 12 | [Implementation Notes](./12-implementation-notes.md) | Applied, adapted, and deferred changes |

## Top 10 Findings (Prioritized)

1. **No structured output schema chain** — ODR uses Pydantic models for every node output; FPL uses raw dicts in most agents
2. **No evaluation framework** — ODR has a full 6-axis eval harness; FPL has none
3. **Reflection/think tool missing** — ODR's `think_tool` creates deliberate pauses for quality decisions; FPL has no equivalent
4. **Token limit handling absent** — ODR detects and handles token limit exceeded; FPL has only a basic 3-retry model fallback
5. **Prompt system is fragmented** — ODR has centralized prompt templates with consistent parameterization; FPL mixes dedicated templates with generic RCTCO assembly
6. **No content summarization chain** — ODR summarizes search results to stay within token limits; FPL has no content truncation or summarization for long artifacts
7. **MCP tool wrapping is primitive** — ODR wraps MCP tools with auth, error handling, name conflict detection; FPL's MCP tools are simpler
8. **No parallel summarization pattern** — ODR uses `asyncio.gather` to summarize multiple search results in parallel; FPL doesn't parallelize artifact processing
9. **Configuration is less granular** — ODR has field-level config with sensible defaults; FPL uses profile-based merging but lacks ODR's granularity
10. **No LLM-as-judge for quality** — ODR evaluates output quality with GPT-4.1; FPL's orchestration relies on rule-based validation
