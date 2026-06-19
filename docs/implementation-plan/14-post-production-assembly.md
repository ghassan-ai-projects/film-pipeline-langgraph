# Phase 14 — Post-Production Assembly

**Depends on:** Phase 10 (Mock Provider), Phase 12 (E2E Mock Mini-Film)
**Blocks:** Phase 15 (Production Hardening)
**Human Gate:** Yes — assembly approval required

---

## Goal

Implement post-production as a first-class graph phase, not an appendix. The assembly agent reads from the master film matrix and assembly manifest, assembles clips into a review cut, adds transitions, prepares audio and color plans, and produces a delivery package. Validation continues through post and delivery.

---

## Deliverables

### Files to Create

#### Post-Production (`src/film_pipeline/post/`)

- [ ] `assembly_agent.py` — assembles clips per assembly manifest
- [   ] `editor_agent.py` — selects takes, trims, orders clips
- [   ] `transition_agent.py` — plans and applies transitions
- [   ] `audio_design_agent.py` — creates audio plan (music, SFX, dialogue)
- [   ] `audio_sync_agent.py` — syncs audio to video
- [   ] `color_agent.py` — creates color plan, applies grading
- [   ] `subtitle_agent.py` — generates subtitle files
- [   ] `delivery_packaging_agent.py` — packages final delivery
- [   ] `__init__.py`

#### Post-Production Validators (`src/film_pipeline/validation/validators/`)

- [   ] `timeline_validator.py` — assembly completeness, clip ordering
- [   ] `transition_validator.py` — transition quality, continuity
- [   ] `audio_sync_validator.py` — audio/video sync
- [   ] `color_continuity_validator.py` — color consistency across clips
- [   ] `delivery_validator.py` — delivery package completeness

#### Tests

- [   ] `tests/unit/post/test_assembly.py` — clip ordering, manifest compliance
- [   ] `tests/unit/post/test_transitions.py` — transition planning
- [   ] `tests/unit/post/test_audio_plan.py` — audio plan generation
- [   ] `tests/unit/post/test_delivery_package.py` — delivery completeness
- [   ] `tests/integration/post/test_assembly_with_mock.py` — full assembly with mock clips

---

## Task Checklist

### Assembly

- [   ] Implement `AssemblyAgent`:
  - [   ] Read assembly manifest from artifact store
  - [   ] Read active takes from generated clip manifest
  - [   ] Order clips per manifest (respecting coverage group selections)
  - [   ] Assemble using ffmpeg (concatenate clips)
  - [   ] Produce review cut (MP4)
  - [   ] Record assembly metadata (duration, clip count, missing assets)
- [   ] Implement `EditorAgent`:
  - [   ] Inspect all angles in coverage groups
  - [   ] Select active takes (best quality, best continuity)
  - [   ] Choose clip order within coverage groups
  - [   ] Trim overlaps
  - [   ] Preserve continuity
- [   ] Implement `TransitionAgent`:
  - [   ] Plan transitions between clips (cut, dissolve, fade)
  - [   ] Apply transitions using ffmpeg
  - [   ] Record transition plan in assembly manifest

### Audio

- [   ] Implement `AudioDesignAgent`:
  - [   ] Create audio plan (music cues, SFX, dialogue overlay)
  - [   ] Plan based on scene intent and emotional arc
  - [   ] Record audio plan in assembly manifest
- [   ] Implement `AudioSyncAgent`:
  - [   ] Sync audio to video timeline
  - [   ] Validate sync (no drift, no gaps)

### Color

- [   ] Implement `ColorAgent`:
  - [   ] Create color plan (per-scene grading, overall look)
  - [   ] Apply color grading using ffmpeg filters
  - [   ] Record color plan in assembly manifest

### Delivery

- [   ] Implement `DeliveryPackagingAgent`:
  - [   ] Package final video (MP4, WebM)
  - [   ] Generate subtitle files (SRT)
  - [   ] Export audio stems (if configured)
  - [   ] Export stills (key frames)
  - [   ] Archive prompt and reference data
  - [   ] Generate validation report
  - [   ] Generate cost report
  - [   ] Generate credits/metadata
  - [   ] Create project archive
- [   ] Implement `SubtitleAgent`:
  - [   ] Generate subtitles from script
  - [   ] Time-align to clips

### Validators

- [   ] Implement `TimelineValidator`:
  - [   ] Check assembly completeness (no missing assets)
  - [   ] Check clip ordering matches manifest
  - [   ] Check total runtime matches target
- [   ] Implement `TransitionValidator`:
  - [   ] Check transition quality
  - [   ] Check continuity across transitions
- [   ] Implement `AudioSyncValidator`:
  - [   ] Check audio/video sync
  - [   ] Check no gaps or overlaps
- [   ] Implement `ColorContinuityValidator`:
  - [   ] Check color consistency across clips
  - [   ] Check color matches per-scene plan
- [   ] Implement `DeliveryValidator`:
  - [   ] Check delivery package completeness
  - [   ] Check all required files present
  - [   ] Check metadata and credits

### MCP Tool Wiring

- [   ] `assemble_review_cut` — triggers assembly, returns review cut
- [   ] `assemble_final_cut` — triggers final assembly with approved changes
- [   ] `export_delivery_package` — triggers delivery packaging

### Tests

- [   ] Write unit tests for all post agents
- [   ] Write integration test: full assembly with mock clips
- [   ] Verify assembly manifest is correctly produced
- [   ] Verify delivery package contains all required files
- [   ] Run `make ci-check`

---

## Delivery Package Contents

```
delivery/
├── final-video.mp4
├── final-video.webm
├── subtitles.srt
├── audio-stems/
│   ├── music.wav
│   ├── sfx.wav
│   └── dialogue.wav
├── stills/
│   ├── key-frame-001.png
│   └── key-frame-002.png
├── prompt-archive/
├── reference-archive/
├── validation-report.json
├── cost-report.json
├── credits.json
└── project-archive.zip
```

---

## Acceptance Criteria

- [   ] Assembly agent correctly orders clips per assembly manifest
- [   ] Review cut is produced as valid MP4
- [   ] Coverage group takes are correctly selected
- [   ] Transitions are planned and applied
- [   ] Audio plan is generated and synced
- [   ] Color plan is generated and applied
- [   ] Delivery package contains all required files
- [   ] All post-production validators pass
- [   ] MCP tools (`assemble_review_cut`, `assemble_final_cut`, `export_delivery_package`) work
- [   ] Assembly approval gate works (mock human can approve/reject)
- [   ] All tests pass (with mock clips)
- [   ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| ffmpeg complexity | Start with simple concatenation; add transitions/filters incrementally |
| Audio sync drift | Frame-accurate sync; validate after each step |
| Delivery package incomplete | Delivery validator enforces required files; fail if missing |
| Post-production scope creep | MVP: assembly + basic transitions + delivery package; defer advanced color/audio |
