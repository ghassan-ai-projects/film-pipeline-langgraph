# Phase 01 — Schemas & Registries

**Depends on:** Phase 00 (Scaffolding)
**Blocks:** Phases 02, 03, 04, 05, 09

---

## Goal

Define every canonical data structure, artifact schema, registry entry schema, and state domain as typed Pydantic models. These schemas are the contract layer — LangGraph state, MCP responses, agent I/O, and validation reports all depend on them.

---

## Deliverables

### Files to Create

#### Core Schemas (`src/film_pipeline/schemas/`)

- [ ] `project.py` — `ProjectProfile`, `ProjectIdentity`, `ProjectConfig`
- [ ] `film_constitution.py` — `FilmConstitution`
- [ ] `story_bible.py` — `StoryBible`, `Logline`, `Premise`, `Treatment`, `ActMap`, `SceneList`, `SetupPayoffMap`
- [ ] `character.py` — `CharacterBible`, `CharacterIdentity`, `VoiceRules`, `WardrobeRules`, `EmotionalArc`
- [ ] `environment.py` — `EnvironmentBible`, `EnvironmentZone`, `Viewpoint`, `LightingState`, `EnvironmentFingerprint`
- [ ] `camera.py` — `CameraLanguageBible`, `CameraProfile`
- [ ] `matrix.py` — `MasterFilmMatrixRow`, `CoverageGroup`, `ChainingConfig`
- [ ] `continuity.py` — `ContinuityLedgerEntry`, `StateRecord`
- [ ] `reference.py` — `ReferenceIndexEntry`, `ReferenceStrategy`
- [ ] `prompt.py` — `PromptRegistryEntry`, `RCTCOPrompt`
- [ ] `generation.py` — `GenerationLedgerRow`, `GenerationRequest`, `ResumeToken`
- [ ] `validation.py` — `ValidationReport`, `ValidationLedgerEntry`, `ConsensusReport`, `ReviewerScore`
- [ ] `assembly.py` — `AssemblyManifest`, `ClipOrder`, `TransitionPlan`, `AudioPlan`, `ColorPlan`
- [ ] `artifact.py` — `ArtifactMetadata`, `ArtifactVersion`, `ArtifactRef`
- [ ] `approval.py` — `ApprovalRecord`, `RevisionRequest`, `ReviewPackage`
- [ ] `issue.py` — `IssueRecord`, `IssueSeverity`
- [ ] `budget.py` — `BudgetState`, `CostEstimate`, `SpendRecord`
- [ ] `provider_health.py` — `ProviderHealthState`, `ProviderStatus`
- [ ] `kb.py` — `KBContextPacket`, `KBItemMetadata`, `KBConflictRecord`
- [ ] `checkpoint.py` — `CheckpointMetadata`, `RollbackRecord`, `InvalidationReport`
- [ ] `handoff.py` — `AgentHandoff`, `RoutingDecision`
- [ ] `audit.py` — `AuditLogEntry`
- [ ] `delivery.py` — `DeliveryPackage`, `DeliveryManifest`
- [ ] `__init__.py` — re-export all schemas

#### Registry Schemas (`src/film_pipeline/schemas/registries/`)

- [ ] `agent_registry.py` — `AgentRegistryEntry` (from agent-architecture.md contract)
- [ ] `provider_registry.py` — `ProviderRegistryEntry`, `ProviderCapabilities`, `CostProfile`
- [ ] `validator_registry.py` — `ValidatorRegistryEntry`, `ValidatorThresholds`
- [ ] `model_registry.py` — `ModelRegistryEntry`
- [ ] `__init__.py`

#### Schema Versioning

- [ ] All schemas include `schema_version: str = "v1"` field
- [ ] All schemas use Pydantic v2 with `model_config = ConfigDict(frozen=True)` where appropriate

### Files to Modify

- [ ] `src/film_pipeline/schemas/__init__.py` — aggregate exports

---

## Task Checklist

- [ ] Create `src/film_pipeline/schemas/` package
- [ ] Implement `project.py` with `ProjectProfile`, `ProjectIdentity`, `ProjectConfig`
- [ ] Implement `film_constitution.py`
- [ ] Implement `story_bible.py` (logline, premise, treatment, act map, scene list, setup/payoff)
- [ ] Implement `character.py` (character bible, identity block, voice rules, wardrobe, emotional arc)
- [ ] Implement `environment.py` (environment bible, zones, viewpoints, lighting states, fingerprint)
- [ ] Implement `camera.py` (camera language bible, profiles)
- [ ] Implement `matrix.py` (master film matrix row with all fields from architecture blueprint)
- [ ] Implement `continuity.py` (continuity ledger entry, state in/out records)
- [ ] Implement `reference.py` (reference index entry, reference strategy)
- [ ] Implement `prompt.py` (RCTCO prompt, prompt registry entry)
- [ ] Implement `generation.py` (generation ledger row, request, resume token)
- [ ] Implement `validation.py` (validation report, ledger entry, consensus report)
- [ ] Implement `assembly.py` (assembly manifest, clip order, transition/audio/color plans)
- [ ] Implement `artifact.py` (artifact metadata, version, ref)
- [ ] Implement `approval.py` (approval record, revision request, review package)
- [ ] Implement `issue.py` (issue record, severity levels)
- [ ] Implement `budget.py` (budget state, cost estimate, spend record)
- [ ] Implement `provider_health.py` (provider health state, status enum)
- [ ] Implement `kb.py` (KB context packet, item metadata, conflict record)
- [ ] Implement `checkpoint.py` (checkpoint metadata, rollback record, invalidation report)
- [ ] Implement `handoff.py` (agent handoff, routing decision)
- [ ] Implement `audit.py` (audit log entry)
- [ ] Implement `delivery.py` (delivery package, manifest)
- [ ] Create `registries/` sub-package with agent, provider, validator, model registry schemas
- [ ] Write unit tests for every schema (serialization round-trip, required fields, validation)
- [ ] Run `make ci-check`

---

## Acceptance Criteria

- [ ] Every data structure from `architecture-blueprint.md` Section "Core Film Data Structures" has a Pydantic model
- [ ] Every registry entry from `architecture-blueprint.md` Section "Extensibility Model" has a schema
- [ ] All schemas pass `mypy --strict`
- [ ] All schemas have unit tests with round-trip serialization
- [ ] `make ci-check` passes
- [ ] Schemas are importable as `from film_pipeline.schemas import ProjectProfile, MasterFilmMatrixRow, ...`

---

## Risks

| Risk | Mitigation |
|------|------------|
| Schema explosion — too many models too early | Only implement schemas referenced in phases 02–12; defer post-production schemas to phase 14 |
| Pydantic v2 breaking changes | Pin `pydantic>=2,<3`; use `model_config` not `Config` |
| Schema versioning drift | All models start at `v1`; add version migration only when needed |
