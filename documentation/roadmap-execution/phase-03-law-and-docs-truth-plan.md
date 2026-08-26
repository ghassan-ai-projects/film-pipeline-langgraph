# Phase 03 — Law & Docs Truth (DRAFT)

**Status:** DRAFT — ground truth verified at Phase-01 planning time; candidate designs go through
the standard two-lens plan review before any implementation.
**Roadmap items:** P0 #8 (B-F8 boundary law amendment + CI edge scan, warn mode), P0 #9
(C-6 docs truth pass). Review detail: `../reviews/arch-lens-boundaries.md` (F-8),
`arch-lens-cognition.md` (F-6).

## Item 1 — Boundary law amendment [B-F8]

Ground truth:
- AGENTS.md "Sub-Package Boundaries" documents **12** sub-packages; `src/film_pipeline/` actually
  has **19**: agents, app, artifacts, checkpoints, cli, config, constraints, generation, graph, kb,
  mcp, observability, post, providers, review, schemas, testing, tui, validation.
- The law covers data-via-artifacts but has no behavior-reuse rule — root cause of post→validation
  (B-F1) and dispatch-table forks (B-F5).
- Schemas exception: domain modules import `schemas` freely today (law must say so explicitly).

Candidate design (per roadmap):
1. Rewrite the AGENTS.md table to list all 19 packages with their roles; mark the 7 ungoverned ones
   (app, cli, constraints, generation, observability, testing, tui) explicitly.
2. Add two rules: (a) schemas exception — any package may import `schemas`; (b) behavior-reuse rule
   — "domain→domain behavior reuse happens through the owning package's registry/service invoked by
   graph/mcp/app, never via cross-package imports".
3. Add `scripts/check_boundaries.py`: AST import-edge scan over `src/film_pipeline/`, enforcing the
   declared edge matrix in **warn mode** first (exit 0, prints findings); flips to enforce mode as a
   later phase once known breaches (post→validation, config→providers, agents→providers,
   generation→{artifacts,providers}, {app↔mcp} cycle) are repaired (P1#11/D12). Counting convention
   for lazy imports documented in-file (see round-4 note in `../reviews/arch-review-critic.md`).

## Item 2 — Docs truth pass [C-6]

Ground truth:
- `architecture-blueprint.md` "System Layers" (:19) has zero mentions of app/, tui/, or
  OperatorService (~40% of hotspot LOC per review §Ground truth).
- Operator guide tool catalog lags `register_all_tools` (`mcp/tools/registry.py:137`) with no sync
  mechanism; guide directs users to `get_blockers` (fixed truth-wise in Phase 02 item 3).

Candidate design (per roadmap):
1. Blueprint: add an "Application Layer" subsection under System Layers describing app/
   (StudioRuntime, OperatorService, graph execution glue), tui/ (Textual surfaces, MCP gateway),
   and cli/ — described as consumers of the MCP-first surface, not parallel product boundaries.
2. Regenerate the operator-guide tool catalog from the registry via a small script (or a unit test
   that asserts catalog ↔ registry equality — decide which in review; test-as-sync is simpler and
   CI-enforced) covering all 52 tools with real descriptions.
3. AGENTS.md: add a short "Adding an MCP tool" checklist (register in registry.py, schema policy
   pointer, tool-surface tests, operator-guide catalog entry).

## Acceptance criteria (phase bar)

1. AGENTS.md package table matches `ls src/film_pipeline` exactly; behavior-reuse + schemas rules
   present.
2. `scripts/check_boundaries.py` runs in CI (warn mode), reproduces the known breach list, exits 0;
   counting convention documented.
3. Blueprint describes app/tui/cli accurately; no contradiction with MCP-first law.
4. Tool-catalog sync mechanism exists and is green (test or generated-doc check).
5. `make ci-check` green; standard two plan reviews + three implementation reviews PASS ≥4/5.
