# TUI Operator Console

This folder defines a complete terminal UI strategy for `film-pipeline-langgraph`.

The recommended product is an operator console built on top of a shared application-service
layer. MCP remains the public control surface, but both MCP and TUI should use the same
use-case services underneath.

## Why This Exists

The current product boundary is correct:

- MCP is the control surface.
- LangGraph is the execution engine.
- Human gates are mandatory.

What is missing is an operator experience that is faster than raw JSON-RPC or ad hoc
tool calls, plus a reusable service layer below MCP. The TUI should solve the operator
experience gap without creating a second backend or duplicating business rules.

## Recommended Reading Order

1. [00-product-intent.md](./00-product-intent.md)
2. [01-operator-jobs-and-personas.md](./01-operator-jobs-and-personas.md)
3. [02-ux-information-architecture.md](./02-ux-information-architecture.md)
4. [03-pipeline-flows.md](./03-pipeline-flows.md)
5. [04-technical-architecture.md](./04-technical-architecture.md)
6. [05-mcp-surface-and-view-models.md](./05-mcp-surface-and-view-models.md)
7. [06-flexibility-and-extension-model.md](./06-flexibility-and-extension-model.md)
8. [07-delivery-plan.md](./07-delivery-plan.md)
9. [08-risks-open-questions-and-acceptance.md](./08-risks-open-questions-and-acceptance.md)
10. [09-wireframes.md](./09-wireframes.md)
11. [10-shared-service-layer.md](./10-shared-service-layer.md)
12. [11-use-cases.md](./11-use-cases.md)
13. [12-workflow-modes.md](./12-workflow-modes.md)
14. [13-e2e-user-flows.md](./13-e2e-user-flows.md)
15. [14-scene-centric-workflow.md](./14-scene-centric-workflow.md)
16. [15-asset-centric-metadata-workflow.md](./15-asset-centric-metadata-workflow.md)
17. [16-structure-level-workflow.md](./16-structure-level-workflow.md)
18. [pages/README.md](./pages/README.md)

## Executive Summary

Recommended stack:

- Python TUI framework: `Textual`
- Shared backend: application services for project, review, artifact, validation,
  checkpoint, provider, and orchestration use cases
- Transport: MCP by default, optional in-process gateway for local development and tests
- Runtime model: request/response first, lightweight polling second, event stream later
- UI model: workspace shell with project navigator, phase board, review package viewer,
  approval queue, artifact inspector, validation panel, checkpoint/rollback console, and
  provider health board

Recommended build principles:

- Keep business logic below both surfaces.
- Keep the TUI stateless where possible.
- Derive durable truth from application services, typically reached through MCP.
- Add only ephemeral UI state locally: selection, filters, drafts, pane layout, refresh
  timers, and optimistic loading markers.

## Main Design Decision

The TUI should be an operator cockpit, not a creative writing interface and not a hidden
automation engine.

That means:

- strong visibility into orchestrator intent
- fast human approvals and revision loops
- clear candidate vs approved baseline comparisons
- safe rollback and spend-control UX
- drill-down inspection of artifacts, validations, and audit history

It does not mean:

- creating duplicated backend behavior
- editing internal graph state directly
- duplicating agent logic in the client
- storing project truth in local TUI files

## Refined Design Decision

The right layering is:

`TUI -> gateway -> application services <- MCP tools`

Not:

`TUI -> one logic path`

`MCP -> another logic path`

This lets the TUI move faster without forcing every internal interaction through JSON-RPC,
while still preserving MCP as the external product contract.
