# Implementation Plan — Overview

**Author:** OpenClaw-orch
**Date:** 2026-06-19
**Status:** Planning → Implementation transition

---

## What This Is

This folder breaks the full implementation of the LangGraph Film Studio into **17 trackable phases** (00–16). Each phase is a self-contained markdown file with:

- Goal
- Dependencies (which phases must be done first)
- Deliverables (files to create or modify)
- Task checklist (trackable items)
- Acceptance criteria
- Risks

The phases follow the build order from [`docs/remaining-needs.md`](../remaining-needs.md) and [`docs/analysis-status-plan.md`](../analysis-status-plan.md), grounded in the architecture from [`docs/architecture-blueprint.md`](../architecture-blueprint.md) and the agent design from [`docs/agent-architecture.md`](../agent-architecture.md).

The Python project structure, tooling, and quality gates are inherited from [`~/my-projects/python-project-blueprint`](../../../../python-project-blueprint).

---

## Phase Index

| Phase | Name | File | Depends On | Human Gate? |
|-------|------|------|------------|-------------|
| 00 | Project Scaffolding | [00-scaffolding.md](00-scaffolding.md) | — | No |
| 01 | Schemas & Registries | [01-schemas-registries.md](01-schemas-registries.md) | 00 | No |
| 02 | MCP Tool Contracts | [02-mcp-tool-contracts.md](02-mcp-tool-contracts.md) | 01 | No |
| 03 | Config & Profile System | [03-config-profile-system.md](03-config-profile-system.md) | 01 | No |
| 04 | Artifact Store & Manifests | [04-artifact-store.md](04-artifact-store.md) | 01, 03 | No |
| 05 | LangGraph State Machine Skeleton | [05-langgraph-skeleton.md](05-langgraph-skeleton.md) | 01, 03, 04 | No |
| 06 | KB Context Packet Builder | [06-kb-context-builder.md](06-kb-context-builder.md) | 05 | No |
| 07 | Agent Registry & Prompt Runner | [07-agent-registry-prompt-runner.md](07-agent-registry-prompt-runner.md) | 05, 06 | No |
| 08 | Review Package Generator | [08-review-package-generator.md](08-review-package-generator.md) | 04, 07 | No |
| 09 | Validation Registry | [09-validation-registry.md](09-validation-registry.md) | 01, 07 | No |
| 10 | Mock Provider & Test Harness | [10-mock-provider-test-harness.md](10-mock-provider-test-harness.md) | 05, 07, 09 | No |
| 11 | Checkpoint/Resume & Rollback | [11-checkpoint-resume-rollback.md](11-checkpoint-resume-rollback.md) | 04, 05, 10 | No |
| 12 | E2E Mock Mini-Film | [12-e2e-mock-mini-film.md](12-e2e-mock-mini-film.md) | 05–11 | Yes (mock human) |
| 13 | Real Provider Adapter | [13-real-provider-adapter.md](13-real-provider-adapter.md) | 10, 12 | Yes |
| 14 | Post-Production Assembly | [14-post-production-assembly.md](14-post-production-assembly.md) | 10, 12 | Yes |
| 15 | Production Hardening | [15-production-hardening.md](15-production-hardening.md) | 12–14 | Yes |
| 16 | Productization & Release Readiness | [16-productization-release.md](16-productization-release.md) | 13–15 | Yes |

---

## Dependency Graph

```
00 Scaffolding
 └→ 01 Schemas & Registries
     ├→ 02 MCP Tool Contracts
     ├→ 03 Config & Profile System
     │   └→ 04 Artifact Store & Manifests ←── 01
     │       └→ 05 LangGraph Skeleton ←── 01, 03
     │           ├→ 06 KB Context Builder
     │           │   └→ 07 Agent Registry & Prompt Runner ←── 05
     │           │       ├→ 08 Review Package Generator ←── 04
     │           │       └→ 09 Validation Registry ←── 01
     │           │           └→ 10 Mock Provider & Test Harness ←── 05, 07
     │           │               └→ 11 Checkpoint/Resume & Rollback ←── 04, 05
     │           │                   └→ 12 E2E Mock Mini-Film ←── 05–11
     │           │                       ├→ 13 Real Provider Adapter
     │           │                       ├→ 14 Post-Production Assembly
     │           │                       └→ 15 Production Hardening ←── 12–14
     │           │                           └→ 16 Productization & Release Readiness ←── 13–15
```

---

## Target Package Layout

```
film-pipeline-langgraph/
├── pyproject.toml                          ← from blueprint, renamed
├── Makefile                                ← from blueprint
├── .pre-commit-config.yaml                 ← from blueprint
├── .python-version                         ← 3.12
├── .editorconfig                           ← from blueprint
├── .gitignore                              ← from blueprint + generated assets
├── AGENTS.md                               ← project-specific agent rules
├── CONTRIBUTING.md                         ← from blueprint
├── src/
│   └── film_pipeline/
│       ├── __init__.py
│       ├── py.typed
│       ├── config/                         ← Phase 03
│       ├── schemas/                        ← Phase 01
│       ├── artifacts/                      ← Phase 04
│       ├── graph/                          ← Phase 05
│       ├── kb/                             ← Phase 06
│       ├── agents/                         ← Phase 07
│       ├── review/                         ← Phase 08
│       ├── validation/                     ← Phase 09
│       ├── providers/                      ← Phase 10, 13
│       ├── checkpoints/                    ← Phase 11
│       ├── mcp/                            ← Phase 02
│       └── post/                           ← Phase 14
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── (existing planning docs)
│   └── implementation-plan/                ← this folder
├── profiles/                               ← Phase 03
├── film-knowledge-base/                    ← existing
└── .github/workflows/ci.yml                ← from blueprint
```

---

## Key Design Decisions

1. **MCP-first** — the MCP tool surface is the product boundary. LangGraph runs behind it.
2. **Mock before real** — mock provider + mock human actor prove the full pipeline at zero cost before any paid provider.
3. **Schemas before code** — every artifact, state, tool response, and registry entry has a formal schema before implementation.
4. **Blueprint tooling** — ruff, mypy strict, pytest with 90% coverage, pre-commit, CI matrix (3.12/3.13), `make ci-check`.
5. **Many small agents** — MVP starts with 19 agents (from agent-architecture.md), expand later.
6. **Human gates as interrupts** — LangGraph interrupts at 10 approval points, persisted as state.
7. **KB as governed retrieval** — not dumped into context; curated packets per agent per phase.

---

## First Implementation Slice

The smallest useful build (phases 00–05 + partial 07) proves:

```
MCP:  create_project, resolve_active_project, submit_idea
Graph: idea → config → constitution → treatment → review gate
Storage: artifact persistence, checkpoint
MCP:  inspect_state, approve_phase, request_revision
```

This proves the MCP-first spine before complex generation enters.

---

## Completeness Review

The implementation plan is strong on architecture, internal contracts, validation, and safety. It was not yet complete as a **full working product plan** because it primarily ended at "production hardening" instead of "operator-ready product release."

The main missing product-level concerns were:

- installable and runnable MCP server packaging
- operator quickstart and first-run workflow
- stable demo project and smoke-test path
- release/versioning workflow for shipping changes safely
- environment bootstrap for local, CI, and production-like execution
- final product acceptance gate that consolidates cross-phase completion

This overview now treats those as first-class deliverables by adding **Phase 16: Productization & Release Readiness** and by defining a single end-state checklist below.

---

## Full Working Product Definition

The product is considered fully working only when all of the following are true:

- A new operator can install dependencies, configure credentials, start the MCP server, and run the happy-path film workflow from docs alone.
- The MCP surface covers the full lifecycle: intake, planning, approvals, generation, validation, recovery, assembly, export, and inspection.
- The studio can complete a mock mini-film end to end with zero paid providers.
- The studio can complete at least one real-provider generation and carry it through validation and post-production into a delivery package.
- Human approval gates, budget controls, auditability, rollback, and resume all work under realistic failure conditions.
- The repo ships with docs, profiles, examples, smoke tests, and release checks that make the system operable by someone other than the original author.

---

## Definition of Ready for Real Providers

Do not connect paid providers until (from `remaining-needs.md`):

- [ ] Mock provider happy path passes
- [ ] Mock provider failure scenarios pass
- [ ] No-duplicate generation test passes
- [ ] Checkpoint/resume test passes
- [ ] Provider block handling works
- [ ] Budget approval works
- [ ] Generation ledger is stable
- [ ] Clip ingestion and asset manifests work
- [ ] Human approval gates are enforced
- [ ] Audit trail explains every provider action

---

## Tracking Conventions

- Each phase file contains a `- [ ]` checklist for every task.
- When work begins on a phase, mark tasks `- [x]` as they complete.
- Acceptance criteria must all be checked before a phase is considered done.
- If a phase is blocked, add a `## Blockers` section at the bottom of its file.

---

## Full Product Acceptance Checklist

Use this as the final ship/no-ship checklist for the whole program.

### 1. Foundation

- [ ] Project scaffolding, tooling, CI, and repo conventions are in place
- [ ] All core schemas and registries are implemented and versioned
- [ ] MCP tool contracts are documented with schemas, errors, and examples
- [ ] Config/profile resolution works for mock and real-provider modes
- [ ] Artifact store, manifests, and metadata rules are implemented

### 2. Core Runtime

- [ ] LangGraph supervisor graph runs with typed state and persisted interrupts
- [ ] KB context packet builder returns governed, explainable context packets
- [ ] Agent registry and prompt runner support the MVP specialist agents
- [ ] Review package generation works for every human approval gate
- [ ] Validation registry enforces blocking and non-blocking quality rules

### 3. Reliability And Recovery

- [ ] Mock provider implements the full provider contract
- [ ] Checkpoint, resume, invalidation, and rollback flows are implemented
- [ ] No duplicate provider submissions occur after ambiguous failures
- [ ] Provider blocks, quota exhaustion, and retry-safe failures are handled correctly
- [ ] Audit logs and explanations are available for graph, agent, KB, and provider decisions

### 4. End-To-End Product Behavior

- [ ] The mock mini-film happy path passes end to end
- [ ] Required revision and failure-path E2E scenarios pass
- [ ] At least one real-provider adapter passes contract and integration tests
- [ ] Post-production assembles a valid review cut and delivery package
- [ ] Delivery outputs include final video, manifests, validation report, cost report, and archives

### 5. Safety, Governance, And Cost

- [ ] Budget caps, spend approvals, and provider-switch approvals are enforced
- [ ] Creator and validator roles use distinct model-routing policy
- [ ] Secret handling and redaction prevent leakage in logs, artifacts, and errors
- [ ] Human gates are enforced before costly, risky, or publishing actions
- [ ] Moderation, policy conflicts, and project ambiguity are handled safely

### 6. Operator Readiness

- [ ] A fresh operator can bootstrap the repo from README and operations docs
- [ ] Provider setup, troubleshooting, and recovery docs are complete
- [ ] Example profiles and a sample project fixture are included
- [ ] MCP server startup, health checks, and smoke tests are documented and automated
- [ ] Release/version workflow, changelog expectations, and rollback guidance are documented

### 7. Quality Bar

- [ ] `make ci-check` passes
- [ ] Coverage target is met
- [ ] Unit, integration, and E2E suites all pass
- [ ] Key product smoke tests pass on a clean environment
- [ ] Documentation matches actual commands, paths, and tool names
