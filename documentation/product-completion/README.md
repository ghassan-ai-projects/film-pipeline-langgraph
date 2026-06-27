# Product Completion Index

Created: 2026-06-19
Status: Execution plan for turning the current scaffold into a real product with no core functionality missing.

---

## Purpose

This folder defines what "done" means in hard product terms.

The standard is not:

- the architecture exists
- tests are green
- stubs have the right shape
- the graph changes phase labels

The standard is:

- a film can move from idea to validated clips through MCP
- every core phase performs real work
- agents use the prompt framework for real outputs
- dynamic agent routing is operational
- validation changes runtime behavior
- checkpoints and rollback restore meaningful project state
- generation is safe and recoverable
- clip outputs, validation evidence, and handoff material are real
- another operator can run the product from docs alone

The current product target does not include final editorial finishing inside this repository.

For the supported path today:

- the repository must reach approved, validated clip outputs
- the system must produce the evidence needed to hand those clips to an external NLE
- final assembly, audio mix, color, and delivery packaging are out of current completion scope

If a capability depends on placeholders, stubs, or manual developer intervention, it is not done.

---

## Document Map

- [Status Scorecard](./status-scorecard.md)
- [00 Product Standard](./00-product-standard.md)
- [01 Runtime And Graph](./01-runtime-and-graph.md)
- [02 Phase Execution And Artifacts](./02-phase-execution-and-artifacts.md)
- [03 Agents, Prompts, And Dynamic Routing](./03-agents-prompts-and-dynamic-routing.md)
- [04 Validation And MCP Product Surface](./04-validation-and-mcp-product-surface.md)
- [05 Generation, Providers, And Post](./05-generation-providers-and-post.md)
- [06 End-To-End Acceptance And Release](./06-e2e-acceptance-and-release.md)

---

## Delivery Rule

The project is only product-complete when every document in this folder reaches its acceptance criteria.
