# Implementation Notes

This file records how the ODR-derived recommendations were applied to this
repository. It is intentionally critical: recommendations were adapted when the
local architecture already solved the problem differently or when the proposed
change would have added risk without enough evidence.

## Applied

- Token-limit handling: provider failures now classify context-window errors,
  compress prompt context, and retry once before falling through normal failure
  handling.
- Model-call timeout: model adapter calls now pass a request timeout when the
  provider SDK supports it.
- Structured orchestrator decision: orchestrator output is validated with a
  Pydantic model instead of trusting raw dict fields.
- Runtime config overrides: allowlisted `FILM_PIPELINE_*` environment variables
  are applied after profile merge and before validation.
- Current-date prompt context: dedicated and generic prompts include the current
  UTC date so agents do not operate with stale assumptions.
- Artifact context bounds: large upstream artifacts are compressed
  deterministically before entering prompt variables, using
  `resolved_config.context.max_chars_per_artifact`.
- Cross-artifact validation: generation planning now checks shot matrix
  `scene_id` references against the persisted script.
- Mock runtime fixture extraction: canned mock responses live under
  `film_pipeline.testing.fixtures`, not inside graph services.
- LangGraph deployment entry point: `langgraph.json` points at a module-level
  compiled graph export.
- Coverage hardening: behavior-focused tests now cover matrix patch
  materialization, structured repair feedback, MCP JSON-RPC error wrapping,
  QC fan-out helpers, structure extraction, and assembly-manifest parsing.
- TUI/backend contract coverage: operator service tests now cover dashboard
  defaults, review/validation workspaces, artifact inspection, provider health,
  comments, and audit feed mapping; terminal formatting helpers are covered.
- QC synthesis coverage: consensus parsing now has direct tests for full dict
  output, direct reviewer-list output, fallback defaults, and validation.
- Model/provider coverage: multimodal model adapter tests now cover Gemini
  payloads, timeouts, HTTP error wrapping, JSON extraction fallbacks, and
  non-Google image fallback; Veo Fast provider contract tests cover payload,
  job lifecycle, download, metadata, cost, defaults, and missing credentials.
- TUI gateway coverage: in-process gateway delegation is covered end-to-end
  against a recording service double.

## Adapted

- The runtime override doc used `resolved_quality`, but this codebase uses
  `quality_profile`; the implementation follows the existing config schema.
- The context-compression recommendation suggested model-based summarization in
  the graph path. The implementation is deterministic and provider-free because
  graph prompt assembly must remain testable offline and must not introduce a
  second model failure before the actual agent call.
- The LangGraph config recommendation included an `auth` path that does not
  exist in this repo. The config omits it rather than referencing a broken
  symbol.
- MCP error wrapping and tool-name conflict detection were not reimplemented:
  `MCPServer.call()` already wraps tool errors into `MCPResponse`, and
  `ToolRegistry.register()` already rejects duplicate tool names.

## Remaining ODR Gaps

- `make ci-check` still fails the repository-wide coverage gate:
  `86.93%` total coverage versus the required `90%`. The functional suite is
  green, but ODR-quality acceptance still needs a deliberate coverage campaign.
- Structured output validation is not yet universal across every agent. The
  orchestrator is hardened, but several agents still accept flexible model
  dicts before constructing domain schemas.
- Reflection/tool-call orchestration remains a design decision, not a blind
  port. The current graph uses human gates and validator feedback; replacing
  orchestrator JSON decisions with tool calls should be done only with a clear
  contract for review actions and TUI visibility.
- Runtime tool aggregation across core, search, and external MCP sources is not
  present. Existing MCP tools have a registry and duplicate-name protection, but
  agents do not yet consume a unified runtime tool catalog.
