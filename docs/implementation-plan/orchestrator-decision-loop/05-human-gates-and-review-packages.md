# Phase 05 — Human Gates And Review Packages

**Depends on:** `04-versioning-and-approved-baselines.md`, Phase 08 (Review Package)
**Blocks:** Phases 06–07 in this folder

---

## Goal

Make human approval gates operate on real orchestrator-curated review packages instead of
artifact lists alone.

---

## Scope

At each major gate, the orchestrator should assemble:

- candidate artifacts under review
- diff from the last approved baseline
- validation results
- open issues
- risk summary
- cost impact
- orchestrator recommendation
- available and blocked actions

The human should be reviewing a decision package, not just browsing raw files.

---

## Files To Touch

- `src/film_pipeline/review/generator.py`
- `src/film_pipeline/review/summary.py` if created
- `src/film_pipeline/mcp/tools/__init__.py`
- `src/film_pipeline/app/runtime.py`
- `tests/unit/review/`
- `tests/integration/mcp/`

---

## Checklist

- [ ] Make `review_phase_artifacts` build and return a real `ReviewPackage`
- [ ] Include orchestrator recommendation in the package
- [ ] Include validation refs and unresolved issues
- [ ] Compare current candidate artifacts against the latest approved set
- [ ] Block approval when blocking issues are unresolved
- [ ] Make human revision actions capture notes into durable revision requests
- [ ] Add tests for script, generation-plan, and QC review packages

---

## Acceptance Criteria

- [ ] Human gates expose structured review packages instead of plain artifact lists
- [ ] Review packages include meaningful orchestrator recommendations
- [ ] Approval is blocked when blocking issues remain
- [ ] Revision notes from humans are preserved and visible in subsequent rounds
- [ ] The package clearly identifies the artifact versions under review

---

## Risks

| Risk | Mitigation |
|------|------------|
| Review packages become verbose but not useful | Keep summary and decisions concise; attach refs for detail |
| MCP review surface diverges from runtime behavior | Build packages from the same orchestrator state the runtime uses |
