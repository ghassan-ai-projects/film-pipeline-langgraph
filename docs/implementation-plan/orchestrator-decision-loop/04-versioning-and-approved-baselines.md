# Phase 04 — Versioning And Approved Baselines

**Depends on:** `03-review-revision-loop.md`, Phase 04 (Artifact Store), Phase 11 (Checkpoints)
**Blocks:** Phases 05–07 in this folder

---

## Goal

Make artifact version history trustworthy and make approved versions the only downstream
baselines.

This phase is critical because the orchestrator cannot reason correctly if it cannot tell the
difference between:

- latest candidate
- latest approved
- superseded versions

---

## Scope

Fix version and approval behavior for:

- candidate writes
- revised writes
- approval transitions
- superseding old versions
- downstream artifact selection

Do this incrementally. Avoid replacing the entire artifact store interface if a smaller fix
to the active write path is enough.

---

## Files To Touch

- `src/film_pipeline/artifacts/store.py`
- `src/film_pipeline/artifacts/versioning.py`
- `src/film_pipeline/graph/nodes.py`
- `src/film_pipeline/app/runtime.py`
- `tests/unit/artifacts/`
- `tests/integration/artifacts/`
- `tests/integration/graph/`

---

## Checklist

- [ ] Stop writing every artifact as `version=1`
- [ ] Create version-chain helpers for candidate, approved, and superseded transitions
- [ ] Link revision outputs to their parent versions
- [ ] Record approval against the approved version
- [ ] Mark superseded versions explicitly
- [ ] Ensure downstream phases resolve the latest approved ref for each needed artifact family
- [ ] Add tests for v1 -> v2 -> v3 lineage, approval, and supersede transitions

---

## Acceptance Criteria

- [ ] Revised artifacts produce new versions instead of overwriting older ones
- [ ] Approval marks a specific artifact version as approved
- [ ] Older active versions can be marked superseded
- [ ] The next phase reads the latest approved version, not the latest candidate
- [ ] Version history remains inspectable for rollback and audit

---

## Risks

| Risk | Mitigation |
|------|------------|
| Version logic spreads into many callers | Centralize next-version and approval logic in artifact helpers |
| Downstream readers accidentally use candidate refs | Add explicit approved-ref resolution helpers and tests |
