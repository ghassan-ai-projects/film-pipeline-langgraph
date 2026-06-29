# World-Class Quality Criteria — Film Pipeline LangGraph

This document defines the quality bar for the LangGraph Film Studio. Every refactor, feature, or fix should move the codebase closer to satisfying all criteria. Criteria are grouped by architectural concern and are ordered by priority.

## A. Architecture & Boundaries

| ID | Criterion | Why it matters |
|----|-----------|----------------|
| A1 | **MCP-first product boundary.** Every user-visible action is reachable through an MCP tool before it is exposed through any other UI. | Prevents hidden internal APIs and makes OpenClaw a first-class operator. |
| A2 | **Sub-package boundary respect.** Domain modules communicate through typed artifacts; only `graph` and `mcp` may import across sub-packages. | Keeps the 12 implementation phases decoupled and testable. |
| A3 | **Registry-driven extensibility.** Agents, validators, providers, schemas, prompts, review strategies, and delivery modes are registered via explicit contracts. | New capabilities should not require rewriting the orchestrator. |
| A4 | **State-driven dynamic routing.** The orchestrator selects the next action by capability, state, validation results, and policy — not by a hard-coded sequence. | Required for the studio OS behavior described in the blueprint. |
| A5 | **Artifact-centric data flow.** Every output is a versioned artifact with complete metadata and lineage; no raw dicts cross module boundaries. | Makes provenance, rollback, and review possible. |
| A6 | **Configuration-first behavior.** Quality, provider, review, and creative behavior are controlled by composable profiles; switching profiles requires no code change. | Allows per-film adaptation without forks. |
| A7 | **Contract-first registries.** Every registry item declares `id`, `type`, `version`, `capabilities`, `input_schema`, `output_schema`, `cost_profile`, `failure_modes`, and `enabled`. | Makes registry entries discoverable and safe to route. |

## B. Agentic Execution

| ID | Criterion | Why it matters |
|----|-----------|----------------|
| B1 | **RCTCO prompt framework adoption.** All core creator, reviewer, validator, and orchestrator prompts use Role / Core Task / Context / Constraints / Output Format. | Prevents vague prompts and unparsable outputs. |
| B2 | **Separation of creator / reviewer / validator / orchestrator.** The orchestrator coordinates; it does not write artifacts or validate its own output. | Prevents conflict of interest and hidden failures. |
| B3 | **Capability-based agent selection.** Agents are discovered and selected by capability, not hard-coded filenames or phase maps. | Supports dynamic routing and extension. |
| B4 | **Validators govern runtime behavior.** Validation reports use a uniform schema, and `BLOCKED` / `NEEDS_REVISION` findings actually stop or loop the pipeline. | Without this, validation is theater. |
| B5 | **Mandatory human review gates.** Human gates are enforced where policy requires them; mock-human approvals are rejected in production mode. | Protects creative and spend decisions. |
| B6 | **First-class mock provider.** The mock provider implements the same adapter contract as real providers and is not a special path in the orchestrator. | Enables cheap, deterministic E2E testing. |
| B7 | **Failure-handling agent.** Provider, validation, budget, and continuity errors are classified and routed to retry, re-anchor, provider-switch, escalate, or stop-until-resolved. | Expensive failures require differentiated handling. |

## C. Code Quality & Safety

| ID | Criterion | Why it matters |
|----|-----------|----------------|
| C1 | **mypy strict clean.** The full `src` and `tests` trees pass `mypy --strict`. | Catches interface drift and undeclared state keys. |
| C2 | **Type hints on public APIs.** All public functions, methods, and module-level constants have type annotations. | Required by AGENTS.md and supports maintainability. |
| C3 | **Pydantic v2 at boundaries.** All cross-module contracts use Pydantic models; raw `dict` is not a public transport format. | Enforces schemas and produces good errors. |
| C4 | **Pathlib for filesystem paths.** No stringly-typed paths in public interfaces. | Consistency and safety on all platforms. |
| C5 | **Specific exceptions with actionable messages.** Avoid bare `except Exception` and generic error strings. | Failures must be debuggable and routable. |
| C6 | **Minimal abstractions.** Do not add layers, helpers, or indirection "for future flexibility" without a current concrete need. | Keeps the codebase readable and changeable. |
| C7 | **No dead code or orphaned stubs.** Production modules do not contain unused functions, commented-out experiments, or registered no-op tools. | Dead code misleads operators and agents. |
| C8 | **No secrets or machine-specific data.** Credentials live in `.env` only; no private keys or account details in source. | Security and portability. |

## D. Test & Behavior Evidence

| ID | Criterion | Why it matters |
|----|-----------|----------------|
| D1 | **90%+ line coverage enforced.** `pytest --cov` passes the configured threshold. | Baseline safety net. |
| D2 | **Behavior coverage, not just line coverage.** Tests prove agent execution, validation gates, approval flow, checkpoint/rollback, provider health, and resume. | Line coverage can hide missing behavior. |
| D3 | **Test isolation and correct markers.** Unit tests do not make network calls; integration and E2E tests are explicitly marked. | Keeps the fast suite fast and deterministic. |
| D4 | **Realistic fixtures.** Tests use fixtures that exercise parsing, error paths, and state transitions, not only happy-path mocks. | Catches edge cases early. |
| D5 | **E2E scenarios prove operator-visible behavior.** Each scenario drives the system through MCP tools and asserts on persisted artifacts, validation reports, checkpoints, and audit events. | The only way to prove the product works end to end. |

## E. Observability & Operations

| ID | Criterion | Why it matters |
|----|-----------|----------------|
| E1 | **Structured audit trail.** Every state mutation, approval, rollback, and spend decision produces a durable audit record. | Required for accountability and debugging. |
| E2 | **Provider health tracked independently of jobs.** Health state is refreshed and surfaced separately from individual generation jobs. | Allows pausing affected queues while other work continues. |
| E3 | **Budget and spend approval gates.** Spend approvals are real, cost estimates are exposed, and caps are enforced before submission. | Prevents runaway costs. |
| E4 | **Error classification and human-readable messages.** Errors are classified so the orchestrator and operators can act on them. | Reduces MTTR and supports the failure-handling agent. |
| E5 | **Appropriate logging.** Use logging levels consistently; avoid noisy `print` statements in production code. | Keeps operator output useful. |

## F. Documentation & Consistency

| ID | Criterion | Why it matters |
|----|-----------|----------------|
| F1 | **Docs match code.** Tool names, commands, file paths, and behavior descriptions in docs reflect the current implementation. | Stale docs mislead operators and downstream agents. |
| F2 | **Comments describe current behavior.** Docstrings and comments do not describe aspirational or retired behavior. | Prevents confusion during refactors. |
| F3 | **Operator docs are practical.** README, operations guide, runbook, and demo guide contain install, run, inspect, recover, and release instructions. | The product must be operable by a human. |
| F4 | **Product completion standards reflect reality.** Checklists and scorecards report measured results, not desired results. | Prevents false confidence. |

## Measurement

- Run `make ci-check` to verify C1, D1, and build health.
- Run `make product-gate` to verify the working-product acceptance gate.
- Run `pytest -m e2e` to verify D5.
- Review this checklist before marking any phase complete.
