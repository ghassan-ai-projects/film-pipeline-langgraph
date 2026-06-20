# Phase 05 - MCP Surface Completion And Non-Video Generation Runtime

Depends on: Phase 04
Blocks: Phase 06

---

## Goal

Finish the operator product boundary by replacing remaining important stubs and making the non-video generation lifecycle real, safe, and recoverable.

---

## Allowed Stub Policy

Only costly video rendering execution may remain externally mocked.

The following behavior may not remain stubbed:

- project lookup and summary needed by operators
- intake analysis and approval
- generation planning
- spend approval
- job submission bookkeeping
- status polling and resume
- duplicate-prevention
- promotion bookkeeping
- rollback mechanics
- coverage-group planning
- final-cut assembly bookkeeping

---

## Product Result

When this phase is complete:

- operators can use MCP for the real supported lifecycle
- generation bookkeeping is idempotent and recoverable
- runtime can resume polling without duplicate submit
- rollback and recovery behavior is meaningful
- remaining non-video product-surface gaps are closed

---

## Implementation Work

### MCP Surface Completion

- replace remaining important stubbed tools with real behavior
- ensure tool results are backed by runtime state, artifacts, ledger data, or audit records

### Generation Runtime

- complete planning, approval, local ledgering, status lookup, cancellation, resume, and promotion bookkeeping
- make provider-job correlation and duplicate-prevention explicit
- allow safe failure handling after job id creation

### Rollback And Assembly

- make rollback mutation tools operate on meaningful stored state
- make final-cut assembly produce operator-visible output records even if costly media generation remains mocked

---

## Files To Create Or Modify

- `src/film_pipeline/mcp/tools/__init__.py`
- `src/film_pipeline/generation/ledger.py`
- `src/film_pipeline/app/runtime.py`
- `src/film_pipeline/checkpoints/`
- `src/film_pipeline/post/`
- generation/MCP integration tests

---

## Mandatory Behavior Tests

- planning a generation batch creates persistent ledger rows
- approving spend changes runtime state and audit trail
- polling/resume after partial failure does not duplicate submit
- cancellation updates the stored request state
- promotion bookkeeping updates the correct artifact lineage
- rollback restores meaningful prior state
- final-cut assembly creates a real output record

---

## Acceptance Criteria

- [ ] important remaining MCP stubs are replaced with real behavior
- [ ] non-video generation lifecycle is behavior-tested end to end
- [ ] duplicate-prevention is proven
- [ ] rollback behavior is meaningful and tested
- [ ] final-cut assembly is no longer a placeholder surface
- [ ] MCP operator flow can be exercised without hidden internal APIs

---

## Exit Condition

This phase is done when the MCP boundary is close enough to complete that an operator can drive the supported product without fake surfaces.
