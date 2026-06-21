# Phase 08 — QC Node + Validation Writers

> **Status:** 🟡 Blocked by 07 | **Depends on:** Generation Plan + Budget (07)

## Problem

The `qc_node` is flag-only. `ValidationReport` schema exists but no writer
produces it. `IssueRecord` schema doesn't exist.

Without structured validation, the pipeline has no automated quality gate
between generation and post-production. The Gemini per-frame review and
composite validation (implemented in the reference image pipeline) prove
the concept but are not integrated into the broader QC system.

## What to Build

### Part A: QC Node Implementation

Wire `qc_node` to run validators for the current phase:

```
phase == "visual_dev"  → ReferenceUsabilityValidator
phase == "shot_bible"  → (new) ShotBibleValidator
phase == "gen_planning" → PromptReadinessValidator
phase == "generation"  → (new) GenerationValidator
phase == "post"        → (new) AssemblyValidator
```

Each validator produces a `ValidationReport` with:
- `validator_id`, `scope`, `modalities`
- `score` (0-100), `status` (passed / failed / needs_revision)
- `blocking_issues: list[ValidationIssue]`
- `warnings: list[ValidationIssue]`
- `recommended_actions: list[str]`

**Storage:** `ArtifactStore.save()` → `08-validation/validation_report_{scope}.v1.json`

### Part B: IssueRecord Schema

New Pydantic model for cross-cutting issue tracking:

```python
class IssueRecord(SchemaBase):
    issue_id: str           # unique, e.g. "ISS-001"
    phase: str              # which phase detected the issue
    artifact_id: str        # which artifact has the issue
    code: str               # machine-readable issue code
    message: str            # human-readable description
    severity: str           # blocking / warning / info
    status: str             # open / resolved / wont_fix
    created_at: str
    resolved_at: str | None
    resolution: str | None
```

### Part C: Validation Ledger

The `ValidationLedgerEntry` schema exists. Write it alongside each
`ValidationReport` to maintain an aggregate ledger of all validations.

### Part D: Wire Gemini Results

The existing per-frame Gemini review and composite validation in the reference
image pipeline produce scores that are stored in entry dicts and logged to
console. Upgrade this to write proper `ValidationReport` artifacts.

## Files to Create

- `src/film_pipeline/schemas/issue.py` — IssueRecord schema
- `src/film_pipeline/validation/impl/shot_bible_validator.py`
- `src/film_pipeline/validation/impl/generation_validator.py`
- `src/film_pipeline/validation/impl/assembly_validator.py`
- `tests/unit/schemas/test_issue.py`
- `tests/unit/validation/test_shot_bible_validator.py`
- `tests/unit/validation/test_generation_validator.py`

## Files to Modify

- `src/film_pipeline/schemas/__init__.py` — Export IssueRecord
- `src/film_pipeline/graph/nodes.py` — Wire `qc_node`
- `src/film_pipeline/mcp/tools/__init__.py` — Update `get_validation_report` to read new reports
- `src/film_pipeline/validation/__init__.py` — Export new validators

## Acceptance Criteria

1. `qc_node` runs phase-appropriate validators and produces `ValidationReport`
2. `IssueRecord` schema passes mypy strict + round-trip
3. `ValidationLedgerEntry` written alongside each report
4. `get_validation_report` returns reports from artifact store (not just in-memory)
5. Gemini per-frame review results written as `ValidationReport` artifacts
6. Composite validation results written as `ValidationReport` artifacts
7. Unit + integration tests

## Risks

- **Validator quality**: New validators (ShotBible, Generation, Assembly) are
  agent-based. They need good prompt templates and test fixtures.
- **Validation fatigue**: Running validators at every phase gate adds latency.
  Mitigation: make QC optional per phase via a `validation_mode` config
  (strict / relaxed / skip).
- **Backward compatibility**: Current `get_validation_report` reads from
  `_validation_reports` in state. New path reads from artifact store.
  Need to support both during migration.
