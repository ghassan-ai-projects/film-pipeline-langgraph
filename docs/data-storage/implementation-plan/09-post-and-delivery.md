# Phase 09 — Post + Delivery Writers

> **Status:** 🟡 Blocked by 08 | **Depends on:** QC Node (08)

## Problem

Post-production and delivery nodes are flag-only. The schemas exist
(`AssemblyManifest`, `DeliveryPackage`, `DeliveryManifest`) but nothing
writes them. The pipeline cannot assemble clips, add audio/subtitles,
or produce a final deliverable.

## What to Build

### Part A: Assembly Manifest Writer

Wire `post_node` to call the assembly agent.

**Artifact:** `AssemblyManifest` contains:
- `clip_order: list[ClipOrderEntry]` — shot order with source asset refs
- `transitions: TransitionPlan` — between-shot transitions
- `audio_plan: AudioPlan` — music, SFX, dialogue tracks
- `color_plan: ColorPlan` — per-scene grading
- `missing_assets: list[str]` — shots that failed generation

**Storage:** `ArtifactStore.save()` → `09-post/assembly_manifest.v1.json`

### Part B: Audio + Subtitle Generation

These are currently agent stubs. Wire them to produce actual files:

- **Audio stems:** `09-post/audio/music_{id}.wav`, `09-post/audio/sfx_{id}.wav`
- **Subtitles:** `09-post/subtitles/{lang}.srt`

These may use external services (TTS, music generation) or be placeholder
files for now. The storage paths should be finalized.

### Part C: Review Cut Assembly

Combine generated clips into a single MP4 using the assembly manifest.
This is a programmatic operation (ffmpeg or similar), not an AI agent.

**Output:** `09-post/review_cut.v1.mp4`

### Part D: Delivery Package Writer

Wire `delivery_node` to produce the final package.

**Artifact:** `DeliveryPackage` contains:
- `final_video_ref` — path to final cut
- `review_cut_ref` — path to review cut
- `manifest: DeliveryManifest` — file listing
- `archive_refs: list[str]` — all artifacts to archive

**Storage:** `ArtifactStore.save()` → `10-delivery/delivery_package.v1.json`

**Binary output:** `10-delivery/final_cut.v1.mp4`, `10-delivery/stills/{shot_id}.png`

## Files to Create

- `src/film_pipeline/post/clip_assembler.py` — ffmpeg-based clip assembly
- `tests/unit/post/test_clip_assembler.py`

## Files to Modify

- `src/film_pipeline/graph/nodes.py` — Wire `post_node`, `delivery_node`
- `src/film_pipeline/post/assembly_agent.py` — Implement stub
- `src/film_pipeline/post/audio_design_agent.py` — Implement stub
- `src/film_pipeline/post/subtitle_agent.py` — Implement stub
- `src/film_pipeline/mcp/tools/__init__.py` — Add `assemble_review_cut`, `generate_delivery` tools

## Acceptance Criteria

1. `post_node` produces AssemblyManifest with clip order, transitions, audio plan
2. Audio stems and subtitle files written to correct paths
3. Review cut MP4 exists and contains all generated clips in order
4. `delivery_node` produces DeliveryPackage with final cut ref
5. Final cut includes all clips, audio, subtitles
6. Delivery stills extracted from key frames
7. Unit + integration tests (mock ffmpeg for tests)

## Risks

- **ffmpeg dependency**: Clip assembly requires ffmpeg. Mock in tests, check
  availability at runtime with clear error message.
- **Audio generation quality**: TTS and music generation may require paid
  services. Start with silence/placeholder audio for MVP.
- **Subtitle accuracy**: Generated subtitles from script dialogue may not
  match actual clip timing. Mitigation: generate from script text first,
  refine with actual clip durations later.
