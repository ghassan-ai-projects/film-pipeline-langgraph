# Implementation Progress

**Last updated:** 2026-06-19
**Branch:** main (10 commits)
**Tests:** 256 passing, CI green (92% coverage)

## Completed Phases

| Phase | Name | Commit | Tests | Coverage | Status |
|-------|------|--------|-------|----------|--------|
| 00 | Scaffolding | `d473712` | 3 | 100% | ✅ |
| 01 | Schemas & Registries | `d473712` | 52 | 99% | ✅ |
| 02 | MCP Tool Contracts | `d473712` | 30 | — | ✅ |
| 03 | Config & Profile System | `527ac6a` | 25 | 95% | ✅ |
| 04 | Artifact Store | `8613f6f` | 20 | 94% | ✅ |
| 05 | LangGraph Skeleton | `c22d2af` | 18 | 92% | ✅ |
| 06 | KB Context Packet Builder | `a71fa04` | 46 | 92% | ✅ |
| 07 | Agent Registry & Prompt Runner | `469403c` | 32 | 92% | ✅ |
| 08 | Review Package Generator | `6849259` | 30 | 92% | ✅ |

## Phase 05 — Gaps Identified & Fixed

- ✅ `state.py`, `nodes.py`, `edges.py`, `graph.py`, `router.py`, `__init__.py`
- ✅ `interrupts.py` — 10 gate interrupt points (fixed in `7e44c87`)
- ✅ `subgraphs/` — 11 phase subgraph stubs (fixed in `7e44c87`)
- ⚠️ **Deferred:** Graph persistence via artifact store (save/load state) — needed before Phase 12
- ⚠️ **Deferred:** Audit logging per node execution — needed before Phase 12

## Phase 06 — Gaps Identified & Fixed

- ✅ `manifest.py`, `retrieval.py`, `packets.py`, `conflicts.py`, `__init__.py`
- ✅ `curator.py` — stub created (fixed in `7e44c87`)
- ✅ kb-manifest.yaml, source-registry.yaml — 12 initial cards
- ⚠️ **Deferred:** `index.py` (full-text KB search) — tag-based retrieval in `retrieval.py` covers current needs

## Phase 07 — Gaps Identified

- ✅ `registry.py`, `base.py`, `runner.py`, `handoff.py`, `__init__.py`
- ✅ 19 MVP agent contracts in `mvp/__init__.py`
- ✅ Mock model adapter in `PromptRunner.call_model()`
- ⚠️ **Deferred:** Per-agent RCTCO prompt templates — runner builds generic prompts from contract metadata; specific templates needed for real model calls (Phase 12+)

## Deferred Items (not blocking phases 08–11)

| Item | Phase | Reason | Target Phase |
|------|-------|--------|-------------|
| Graph persistence (save/load via artifact store) | 05 | Needs checkpoint infrastructure (Phase 11) | 11 |
| Audit logging per node execution | 05 | Needs artifact store wiring | 11 |
| KB index.py (full-text search) | 06 | Tag-based retrieval sufficient for MVP | 12 |
| Per-agent RCTCO prompt templates | 07 | Generic prompts from contracts work for E2E mock | 12 |

## Pending Phases (09–16)

- **09**: Validation Registry (depends on 01, 07) ← NEXT
- **10**: Mock Provider & Test Harness (depends on 05, 07, 09)
- **11**: Checkpoint/Resume & Rollback (depends on 04, 05, 10)
- **12**: E2E Mock Mini-Film (depends on 05–11)
- **13**: Real Provider Adapter (depends on 10, 12)
- **14**: Post-Production Assembly (depends on 10, 12)
- **15**: Production Hardening (depends on 12–14)
- **16**: Productization & Release (depends on 13–15)

## Key Conventions
- All code in `src/film_pipeline/`
- Tests in `tests/unit/`, `tests/integration/`, `tests/e2e/`
- `make ci-check` = format-check + lint + mypy strict + pytest (90% cov) + build
- Commit style: `feat: implement Phase XX — description`
- Node names in StateGraph must not conflict with state field names (use `*_node` suffix)
- KB manifest items use dot-separated ids with version suffix (`kb.policy.prompt.rctco.v1`)
- `interrupts.py`: `interrupt_for_gate()` marks state for human review; nodes call it before returning
