# Phase 06 — KB Context Packet Builder

**Depends on:** Phase 05 (LangGraph Skeleton)
**Blocks:** Phase 07 (Agent Registry & Prompt Runner)

---

## Goal

Implement the knowledge base context packet builder. The orchestrator should never dump the whole KB into an agent prompt. Instead, it builds a `KBContextPacket` per graph node — selecting canonical policies, active playbooks, case-study risks, and examples based on the current phase, agent, and task.

This is the studio memory system: governed retrieval with authority levels, conflict handling, and explainable context choices.

---

## Deliverables

### Files to Create

#### KB Engine (`src/film_pipeline/kb/`)

- [ ] `manifest.py` — KB manifest reader (item metadata, authority levels, tags)
- [ ] `index.py` — KB index (full-text search, tag-based filtering)
- [ ] `retrieval.py` — layered retrieval engine:
  - [ ] Deterministic retrieval (required canonical rules by id)
  - [ ] Tagged retrieval (by phase, domain, modality, risk)
  - [ ] Semantic retrieval (optional, embeddings later)
  - [ ] Example retrieval (format/pattern examples only)
- [ ] `packets.py` — `KBContextPacketBuilder` (assembles packets for agents)
- [ ] `conflicts.py` — conflict detection and resolution (canonical > playbook > case study > archive)
- [ ] `curator.py` — KB curator (ingestion, promotion, card creation)
- [ ] `__init__.py`

#### KB Structure (in `film-knowledge-base/`)

- [ ] `film-knowledge-base/index/kb-manifest.yaml` — manifest with all KB items
- [ ] `film-knowledge-base/index/source-registry.yaml` — source registry
- [ ] `film-knowledge-base/canonical/policies/` — canonical policy cards
- [ ] `film-knowledge-base/playbooks/` — active playbook cards
- [ ] `film-knowledge-base/case-studies/` — case study lesson cards

#### Initial KB Cards (Curated from Existing KB)

- [ ] `kb.policy.prompt.rctco.v1` — RCTCO prompt framework
- [ ] `kb.policy.generation.no_duplicate_submit.v1` — no duplicate generation
- [ ] `kb.policy.checkpoint.resume.v1` — checkpoint and resume policy
- [ ] `kb.policy.provider.adapter_contract.v1` — provider adapter contract
- [ ] `kb.policy.human.approval_gates.v1` — human approval gate policy
- [ ] `kb.policy.validation.thresholds.v1` — validation threshold policy
- [ ] `kb.playbook.reference_images.video_prompt_package.v1`
- [ ] `kb.playbook.environment.locked_prompt_block.v1`
- [ ] `kb.playbook.generation.sequential_chain.v1`
- [ ] `kb.lesson.environment_drift.primordial_stroke.v1`
- [ ] `kb.lesson.cost_overrun.postmortem.v1`
- [ ] `kb.lesson.moderation_failure.postmortem.v1`

#### Tests

- [ ] `tests/unit/kb/test_manifest.py` — manifest reading and validation
- [ ] `tests/unit/kb/test_retrieval.py` — deterministic, tagged, example retrieval
- [ ] `tests/unit/kb/test_packets.py` — packet building per agent/phase
- [ ] `tests/unit/kb/test_conflicts.py` — conflict detection and resolution
- [ ] `tests/integration/kb/test_context_for_agents.py` — each MVP agent gets correct KB slice

---

## Task Checklist

- [ ] Create `film-knowledge-base/index/kb-manifest.yaml` with initial item metadata
- [ ] Create `film-knowledge-base/index/source-registry.yaml`
- [ ] Implement `KBManifest` reader (loads manifest, validates authority levels)
- [ ] Implement `KBIndex` (tag-based filtering, full-text search via ripgrep/regex)
- [ ] Implement layered retrieval:
  - [ ] Deterministic: always include required canonical rules by id
  - [ ] Tagged: filter by phase, domain, modality, risk tags
  - [ ] Example: retrieve examples only when requested
- [ ] Implement `KBContextPacketBuilder`:
  - [ ] Input: project_id, phase, agent_id, task
  - [ ] Retrieve canonical policies first
  - [ ] Retrieve active playbooks second
  - [ ] Retrieve case-study risks third
  - [ ] Retrieve examples only if useful
  - [ ] Attach source refs and authority levels
  - [ ] Record excluded refs with reasons
  - [ ] Output: `KBContextPacket` (from Phase 01 schema)
- [ ] Implement conflict detection:
  - [ ] canonical > playbook > case study > archive
  - [ ] newer active version > older active version
  - [ ] superseded items excluded unless explicitly requested
  - [ ] conflicts recorded as `KBConflictRecord`
- [ ] Write initial KB cards (12 cards listed above)
- [ ] Implement per-agent KB access rules (allowed domains, blocked domains)
- [ ] Write unit tests for manifest, retrieval, packets, conflicts
- [ ] Write integration tests for agent-specific context
- [ ] Run `make ci-check`

---

## KB Context Packet Schema (from Phase 01)

```json
{
  "kb_context_id": "kbctx:S001-01:prompt-composition:v1",
  "project_id": "film_2026_0001",
  "phase": "generation",
  "agent_id": "prompt-composition-agent",
  "task": "compose video prompt for shot S001-01",
  "authority_policy_refs": ["kb.policy.prompt.rctco.v1", "kb.policy.generation.no_duplicate_submit.v1"],
  "playbook_refs": ["kb.playbook.reference_images.video_prompt_package.v1"],
  "case_study_refs": ["kb.lesson.environment_drift.primordial_stroke.v1"],
  "examples": [],
  "excluded_refs": [
    {"ref": "kb.archive.seedance_legacy_retry_rule.v1", "reason": "Superseded by current provider-block policy."}
  ]
}
```

---

## Acceptance Criteria

- [ ] KB manifest loads and validates all items
- [ ] Retrieval returns correct items by tag (phase, domain, modality, risk)
- [ ] Context packet builder produces correctly-scoped packets per agent
- [ ] Conflict detection: canonical policy wins over old case-study
- [ ] Excluded refs include reasons
- [ ] Each MVP agent gets only its allowed KB domains
- [ ] KB context packet is attachable to artifacts (`kb_context_ref`)
- [ ] All tests pass
- [ ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| KB is large and unstructured | Start with 12 curated cards; ingest more incrementally |
| Semantic retrieval needs embeddings | Defer embeddings; use tag-based + full-text for MVP |
| Conflict resolution edge cases | Document authority hierarchy; test with postmortem conflict scenario (E2E Scenario 8) |
