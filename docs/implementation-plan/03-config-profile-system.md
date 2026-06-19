# Phase 03 — Config & Profile System

**Depends on:** Phase 01 (Schemas & Registries)
**Blocks:** Phase 04 (Artifact Store), Phase 05 (LangGraph Skeleton)

---

## Goal

Implement the configuration-first design from the architecture blueprint. Users should be able to change pipeline behavior through config files alone — film type, quality level, provider strategy, review strictness, budget rules, and generation defaults — without changing core code.

Profiles are composable: base studio + film type + quality + provider + project override.

---

## Deliverables

### Files to Create

#### Config Engine (`src/film_pipeline/config/`)

- [ ] `loader.py` — profile loading, merging, and resolution
- [ ] `merger.py` — profile layering (later overrides earlier)
- [ ] `defaults.py` — studio defaults
- [ ] `validator.py` — config validation, conflict detection
- [ ] `__init__.py`

#### Profile Templates (`profiles/`)

- [ ] `base.studio.yaml` — base studio profile (phases, agents, validators, review gates)
- [ ] `film-type.narrative.yaml` — narrative short film
- [ ] `film-type.visual_poetry.yaml` — visual poetry
- [ ] `film-type.experimental.yaml` — experimental film
- [ ] `quality.draft.yaml` — draft quality (fast, single review)
- [ ] `quality.internal_review.yaml` — internal review quality
- [ ] `quality.studio.yaml` — studio quality (multi-model panel)
- [ ] `quality.festival.yaml` — festival quality (strict, multi-review, human-heavy)
- [ ] `provider.free_or_low_cost.yaml` — free/low-cost providers first
- [ ] `provider.seedance_primary.yaml` — Seedance as primary
- [ ] `provider.veo_primary.yaml` — Veo as primary
- [ ] `review.fast_single_review.yaml` — single reviewer, fast
- [ ] `review.multi_model_panel.yaml` — multi-model panel
- [ ] `review.human_heavy.yaml` — human review at every gate
- [ ] `review.strict_continuity.yaml` — strict continuity enforcement

#### Tests

- [ ] `tests/unit/config/test_profile_merging.py` — layering and override
- [ ] `tests/unit/config/test_config_validation.py` — conflict detection
- [ ] `tests/unit/config/test_defaults.py` — studio defaults completeness

---

## Task Checklist

- [ ] Implement `ProfileLoader` that reads YAML profiles from `profiles/` directory
- [ ] Implement `ProfileMerger` that layers profiles in order (base + film-type + quality + provider + review + project)
- [ ] Implement `ConfigValidator` that detects conflicts (e.g., festival quality + free_only budget)
- [ ] Create `base.studio.yaml` with default phases, agents, validators, approval gates
- [ ] Create film-type profiles (narrative, visual_poetry, experimental)
- [ ] Create quality profiles (draft, internal_review, studio, festival)
- [ ] Create provider profiles (free_or_low_cost, seedance_primary, veo_primary)
- [ ] Create review profiles (fast_single_review, multi_model_panel, human_heavy, strict_continuity)
- [ ] Define `ResolvedConfig` schema (output of merger) — covers agents, validators, providers, review strategy, budget, generation defaults, delivery modes
- [ ] Write unit tests for profile merging (override semantics)
- [ ] Write unit tests for conflict detection
- [ ] Run `make ci-check`

---

## Profile Fields (Resolved Config)

```yaml
# Output of profile resolution
phases: [intake, constitution, development, script, visual_dev, shot_bible, gen_planning, generation, qc, post, delivery]
agents:
  active: [orchestrator, intake-classifier, treatment-agent, screenwriter, ...]
  model_routing:
    creative_writer: "gpt-5"
    strict_validator: "gemini-flash"
validators:
  active: [logline-validator, treatment-validator, ...]
  thresholds:
    pass: 85
    review: 75
    block: 60
review:
  strategy: multi_model_panel
  min_reviewers: 2
  escalation_on_disagreement: true
providers:
  order: [seedance-openrouter, veo-3.1-fast]
  fallback_allowed: false
  max_duration_seconds: 15
budget:
  project_cap_usd: 50
  per_phase_cap_usd: 10
  max_auto_approved_cost: 1.0
  human_approval_above: 1.0
generation:
  default_mode: test
  duration_seconds: 1
  resolution: 480p
  re_anchor_every_n_clips: 5
  parallel_allowed: false
delivery:
  modes: [mp4, webm]
  include_subtitles: true
  include_audio_stems: false
```

---

## Acceptance Criteria

- [ ] `base.studio.yaml` + `film-type.narrative.yaml` + `quality.festival.yaml` resolves to a valid config
- [ ] Conflicts are detected and reported (e.g., festival + free_only)
- [ ] Project override profile merges last and overrides earlier layers
- [ ] `ResolvedConfig` is a Pydantic model from Phase 01 schemas
- [ ] All profile templates validate against their schema
- [ ] Unit tests pass
- [ ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| Profile explosion — too many knobs | Start with the fields above; add more only when a phase needs them |
| Merge semantics unclear | Document: "last value wins" for scalars, "union" for lists, "override" for nested dicts |
