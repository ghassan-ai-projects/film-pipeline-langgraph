# Phase 09 — Validation Registry

**Depends on:** Phase 01 (Schemas), Phase 07 (Agent Registry)
**Blocks:** Phase 10 (Mock Provider & Test Harness)

---

## Goal

Implement the validation registry and validator framework. Validators are pluggable components that score artifacts against rubrics, produce structured validation reports, and enforce blocking thresholds. The registry makes validators discoverable by scope and modality.

Validation is a first-class subsystem, not scattered checks. Every important artifact gets validated by the right validators, and failing validation triggers explicit revision workflows.

---

## Deliverables

### Files to Create

#### Validation Engine (`src/film_pipeline/validation/`)

- [ ] `registry.py` — `ValidatorRegistry` class: register, lookup by id, lookup by scope, lookup by modality
- [ ] `base.py` — `BaseValidator` abstract class: validate(artifact, context) → ValidationReport
- [ ] `report.py` — validation report builder (structured output with score, status, issues, recommendations)
- [ ] `thresholds.py` — threshold checker (pass / review / block)
- [ ] `consensus.py` — multi-model consensus builder (parallel review, agreement level, disagreement synthesis)
- [ ] `families.py` — validator family grouping (writing, visual, cinematography, continuity, flow, output, assembly)
- [ ] `__init__.py`

#### MVP Validators (`src/film_pipeline/validation/validators/`)

- [ ] `logline_validator.py` — scope: artifact, modality: text
- [ ] `treatment_validator.py` — scope: artifact, modality: text
- [ ] `scene_writing_validator.py` — scope: scene, modality: text
- [ ] `dialogue_voice_validator.py` — scope: scene, modality: text
- [ ] `character_dossier_validator.py` — scope: artifact, modality: text+image
- [ ] `environment_bible_validator.py` — scope: artifact, modality: text+image
- [ ] `reference_usability_validator.py` — scope: artifact, modality: image
- [ ] `shot_design_validator.py` — scope: artifact, modality: text+camera
- [   ] `prompt_readiness_validator.py` — scope: artifact, modality: text
- [ ] `clip_quality_validator.py` — scope: clip, modality: video
- [ ] `prompt_adherence_validator.py` — scope: clip, modality: video
- [ ] `scene_continuity_validator.py` — scope: scene, modality: continuity
- [ ] `act_structure_validator.py` — scope: act, modality: text+flow
- [ ] `full_movie_flow_validator.py` — scope: full_movie, modality: flow+continuity
- [ ] `assembly_validator.py` — scope: delivery, modality: assembly
- [ ] `__init__.py`

#### Tests

- [ ] `tests/unit/validation/test_registry.py` — register, lookup by scope/modality
- [ ] `tests/unit/validation/test_report.py` — report building, threshold enforcement
- [ ] `tests/unit/validation/test_consensus.py` — multi-model consensus, disagreement
- [ ] `tests/integration/validation/test_validators.py` — each MVP validator produces correct report

---

## Task Checklist

- [ ] Implement `ValidatorRegistry` with register, lookup_by_id, lookup_by_scope, lookup_by_modality
- [ ] Implement `BaseValidator` abstract class:
  - [ ] `prepare(artifact, context)` — assemble validation inputs
  - [ ] `validate(model)` — run validation prompt (RCTCO)
  - [ ] `score(result)` — parse score from model output
  - [ ] `report()` — produce `ValidationReport` (from Phase 01 schema)
- [ ] Implement threshold checker:
  - [ ] `pass` (≥ 85): no action needed
  - [ ] `review` (75–84): pass with notes, no block
  - [   ] `block` (< 75): blocking issue, revision required
  - [ ] Thresholds configurable per profile
- [ ] Implement multi-model consensus builder:
  - [ ] Run same validation through multiple models independently
  - [ ] Collect independent scores
  - [   ] Calculate agreement level (high / medium / low)
  - [ ] Synthesize consensus status
  - [ ] Preserve disagreements in `ConsensusReport`
  - [ ] Orchestrator recommendation: revise, escalate, or approve
- [ ] Register all 15 MVP validators with contracts:
  - [ ] Each validator declares: scope, modalities, input_schema, output_schema, thresholds, blocking_conditions
- [ ] Write RCTCO validation prompt templates for each validator
- [ ] Write unit tests for registry, report, consensus
- [ ] Write integration tests for each validator (mock model → correct report)
- [ ] Run `make ci-check`

---

## Validation Report Schema (from Phase 01)

```json
{
  "validation_id": "validation:script:S001:v3",
  "validator_id": "scene-writing-validator",
  "scope": "scene",
  "modality": ["text"],
  "artifact_refs": ["artifact:script:S001:v3"],
  "score": 85,
  "status": "pass_with_notes",
  "blocking_issues": [],
  "warnings": ["Dialogue slightly dense for 30s runtime"],
  "recommended_actions": ["Consider trimming S001 dialogue by 2 lines"],
  "requires_human_review": false
}
```

---

## Validation Matrix

| Scale \ Modality | text | image | camera | continuity | flow | video | assembly |
|------------------|------|-------|--------|------------|------|-------|----------|
| artifact | logline, treatment, scene_writing, dialogue, character, environment, reference, prompt_readiness | reference_usability, character, environment | shot_design | — | — | — | — |
| clip | — | — | — | — | — | clip_quality, prompt_adherence | — |
| scene | scene_writing, dialogue | — | — | scene_continuity | — | — | — |
| act | — | — | — | — | act_structure | — | — |
| full_movie | — | — | — | — | full_movie_flow | — | — |
| delivery | — | — | — | — | — | — | assembly |

---

## Acceptance Criteria

- [ ] All 15 MVP validators are registered with valid contracts
- [ ] `lookup_by_scope("clip")` returns clip-level validators
- [ ] `lookup_by_modality("video")` returns video validators
- [   ] Threshold checker correctly enforces pass/review/block
- [ ] Multi-model consensus preserves disagreements
- [   ] Each validator produces a `ValidationReport` with correct schema
- [ ] Blocking issues prevent phase advancement
- [   ] Validation reports are stored in validation ledger (artifact store)
- [ ] All tests pass
- [ ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| Validator prompts too generic | Each validator gets a specific RCTCO prompt with narrow scope |
| Mock model returns invalid scores | Strict JSON parsing; score must be 0-100 integer |
| Consensus synthesis is lossy | Never average away disagreement; preserve individual scores |
