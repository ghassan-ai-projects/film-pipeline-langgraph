# Product Completion Plan

Created: 2026-06-20
Status: Active execution plan for taking the repository from "strong scaffold" to "finished product."

---

## Purpose

This folder is the implementation program for reaching product completion.

It is intentionally different from [`documentation/product-completion/`](../product-completion/):

- `documentation/product-completion/` defines the hard standard for what "done" means
- `documentation/product-completion-plan/` defines the phased work to get there

This plan is stricter than the earlier implementation plan in one important way:

- the first work is not "build more features"
- the first work is to remove hard-coded model behavior and make the prompt framework real

That is required because the product cannot truthfully claim dynamic agents, model policy, or prompt-governed execution while models are still baked into code paths and prompts remain generic.

The supported product target for this plan is:

- idea to validated clips
- all required approvals, validation, rollback, and audit behavior through MCP
- operator-visible clip handoff material for external finishing

The following are not required for completion of this plan:

- final cut assembly
- audio post
- color grading
- delivery package export

---

## Program Principles

- no core product claim without behavior tests
- no hidden hard-coded model selection in execution paths
- no core agent may bypass the prompt framework
- no MCP tool may claim product behavior while returning placeholders
- no secrets may be written to docs, logs, fixtures, snapshots, or artifacts
- only costly video generation execution may remain externally mocked; all surrounding runtime behavior must be real and tested

---

## Phase Order

| Phase | Focus | Why First |
|-------|-------|-----------|
| 00 | Program rules and acceptance control | Prevent soft claims and drifting standards |
| 01 | Model routing, prompt framework, and secret-safe config | Fix hard-coded models and generic prompt execution first |
| 02 | Core agent execution and persisted artifacts | Make critical agents do real work |
| 03 | Dynamic routing, handoffs, and explainability | Make agents truly dynamic rather than static wiring |
| 04 | Validation-driven runtime control | Make validators change what the system does |
| 05 | MCP surface completion and non-video generation flow | Finish the operator boundary through validated clips |
| 06 | E2E recovery, operator workflow, and release proof | Prove the whole product works for another operator |

---

## Files

- [00-program-rules.md](./00-program-rules.md)
- [01-model-routing-prompt-framework.md](./01-model-routing-prompt-framework.md)
- [02-core-agent-execution-and-artifacts.md](./02-core-agent-execution-and-artifacts.md)
- [03-dynamic-routing-and-handoffs.md](./03-dynamic-routing-and-handoffs.md)
- [04-validation-runtime-control.md](./04-validation-runtime-control.md)
- [05-mcp-surface-and-generation-runtime.md](./05-mcp-surface-and-generation-runtime.md)
- [06-e2e-operator-proof-and-release.md](./06-e2e-operator-proof-and-release.md)
- [acceptance-checklist.md](./acceptance-checklist.md)
- [acceptance-manifest.yaml](./acceptance-manifest.yaml)
- [status-tracker.md](./status-tracker.md)

---

## Delivery Rule

The project reaches product completion only when:

- every phase file in this folder meets its own acceptance criteria
- the global checklist in this folder is green
- the hard standard in [`documentation/product-completion/`](../product-completion/) is satisfied
- the repository validation evidence matches the claims

If this folder becomes more optimistic than the code or tests, this folder is wrong and must be corrected.
