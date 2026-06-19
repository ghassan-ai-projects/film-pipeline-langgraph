# Implementation Progress

**Last updated:** 2026-06-19
**Branch:** main (15 commits)
**Tests:** 345 passing, CI green (90.61% coverage)

## Completed Phases

| Phase | Name | Commit | Tests | Status |
|-------|------|--------|-------|--------|
| 00 | Scaffolding | `d473712` | 3 | ✅ |
| 01 | Schemas & Registries | `d473712` | 52 | ✅ |
| 02 | MCP Tool Contracts | `d473712` | 30 | ✅ |
| 03 | Config & Profile System | `527ac6a` | 25 | ✅ |
| 04 | Artifact Store | `8613f6f` | 20 | ✅ |
| 05 | LangGraph Skeleton | `c22d2af` | 18 | ✅ |
| 06 | KB Context Packet Builder | `a71fa04` | 46 | ✅ |
| 07 | Agent Registry & Prompt Runner | `469403c` | 32 | ✅ |
| 08 | Review Package Generator | `6849259` | 30 | ✅ |
| 09 | Validation Registry | `4a0506e` | 28 | ✅ |
| 10 | Mock Provider & Test Harness | `aeccd67` | 37 | ✅ |
| 11 | Checkpoint/Resume & Rollback | `aa831b9` | 20 | ✅ |
| 12 | E2E Happy Path (conftest + scenario 1) | (pending commit) | 4 | ✅ |
| 13 | Real Provider Adapter (skeleton) | — | — | 🟡 |
| 14 | Post-Production Assembly (skeleton) | — | — | 🟡 |
| 15 | Production Hardening (skeleton) | — | — | 🟡 |
| 16 | Productization & Release (skeleton) | — | — | 🟡 |

## Phase 05-07 Gaps

See [PROGRESS.md history] for gap analysis. All critical structural gaps filled.
Deferred items: graph persistence, audit logging, KB full-text index, per-agent prompt templates.
None block E2E mock tests.

## Phases 13-16 Status

Skeleton modules created with documentation referencing the implementation plan files.
These phases require real-world dependencies (API keys, ffmpeg, credentials, production
environment) and should be implemented after Phase 12 E2E mock baseline fully passes.

| Module | Files | Status |
|--------|-------|--------|
| `providers/adapters/` | seedance_openrouter.py (stub) | 🟡 Needs API key |
| `post/` | __init__.py | 🟡 Needs ffmpeg |
| `security/` | __init__.py | 🟡 |
| `observability/` | __init__.py | 🟡 |
| `app/` | __init__.py, smoke.py | ✅ Smoke runner works |

## Architecture Summary (Phases 00-12)

```
src/film_pipeline/
├── schemas/         # 27 Pydantic v2 schemas (Phase 01)
├── config/          # Profile loader, merger, resolver, validator (03)
├── artifacts/       # Versioned storage, manifests, paths (04)
├── graph/           # StateGraph, 11 phase nodes, interrupts, subgraphs (05)
├── kb/              # Manifest, retrieval, conflicts, packets, curator (06)
├── agents/          # Registry, base, runner (RCTCO), handoff, 19 MVP (07)
├── review/          # Generator, diff engine, actions calculator (08)
├── validation/      # Registry, base, thresholds, consensus, 15 MVP (09)
├── providers/       # BaseAdapter, mock video/image, registry, health (10)
├── checkpoints/     # Git backend, manager, resume, invalidation, rollback (11)
├── testing/         # Mock human (7 profiles), mock model, 13 scenarios (10)
├── mcp/             # Tool contracts, server, resolution, errors (02)
├── post/            # Post-production (skeleton) (14)
├── security/        # Secrets, redaction (skeleton) (15)
├── observability/   # Audit, metrics (skeleton) (15)
└── app/             # Smoke tests, bootstrap (skeleton) (16)
```

## Key Conventions
- All code in `src/film_pipeline/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/e2e/`
- `make ci-check` = format + lint + mypy strict + pytest (90% cov) + build
- Commit: `feat: implement Phase XX — description`
- Node names: use `*_node` suffix to avoid StateGraph field conflicts
- KB items: dot-separated ids with version suffix (`kb.policy.prompt.rctco.v1`)
- Providers: all implement `BaseProviderAdapter` contract
- Mock first: never connect paid providers until Phase 12 E2E baseline passes
