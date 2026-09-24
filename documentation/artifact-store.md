# Phase 04 — Artifact Store & Manifests

**Depends on:** Phase 01 (Schemas), Phase 03 (Config & Profile System)
**Blocks:** Phase 05 (LangGraph Skeleton), Phase 08 (Review Package), Phase 11 (Checkpoint/Resume)

> **Storage upgrade note (2026-09).** The artifact engine now writes **layout
> v2** (see `documentation/storage-upgrade-plan.md`, decisions D3/D4). Per
> artifact: `artifacts/<NN-phase>/<artifact_id>/` holds
> `meta.json` (current version + status — the only mutable file),
> `current.md` (generated human view), and immutable
> `versions/vNNN.json` envelopes carrying provenance, payload, and a payload
> checksum. A derived `index/artifacts.json` is regenerated on every write.
> **Ref grammar (P3):** artifact references are canonical
> `artifact:<phase>:<artifact_id>:v<N>` strings, carried by the typed
> `ArtifactRef` model (`to_string()`/`from_string()`); the legacy phase-less
> form still parses, and `ArtifactStore.load_ref()` resolves either one.
> Reads default to the latest version (`ArtifactStore.latest_version()`),
> so repaired artifacts are visible to their consumers. The generation
> ledger is stored as a revision-counted single file
> (`generation_ledger.json`, envelope field `revision`), no longer a
> rewritten "v1" version.
> Every artifact id must be lowercase snake_case and registered in
> `artifacts/registry.py` (kind → payload model, schema version, mutability);
> unregistered ids are refused at save time. Envelopes carry an int
> `schema_version`; readers reject newer versions with `SchemaTooNewError`
> and migrate older ones via the registered migration chain. Legacy
> pre-upgrade projects remain readable read-only until the storage migration
> command (P6) moves them forward. The sections below describe the original
> phase-04 contract; where they disagree with layout v2, the plan and the
> code win (the full doc rewrite lands with the upgrade's final phase).

---

## Goal

Implement the artifact storage layer: versioned artifact persistence, asset manifests, and the directory structure that every phase, agent, and validator reads from and writes to. This is the canonical artifact registry — one source of truth for all outputs.

---

## Deliverables

### Files to Create

#### Artifact Store (`src/film_pipeline/artifacts/`)

- [ ] `store.py` — `ArtifactStore` class: save, load, list, version, supersede
- [ ] `manifest.py` — asset manifest management (reference, generated clip, frame, audio, assembly, delivery)
- [ ] `paths.py` — canonical path resolution per project, phase, and artifact type
- [ ] `metadata.py` — artifact metadata writer/reader (attaches metadata to every artifact)
- [ ] `versioning.py` — artifact version tracking (v1, v2, v3...), parent linking, status transitions
- [ ] `index.py` — artifact index (queryable registry of all artifacts in a project)
- [ ] `__init__.py`

#### Storage Structure (per project)

```
projects/<project_slug>/
├── 01-vision/
├── 02-development/
├── 03-script/
├── 04-visual-dev/
├── 05-shot-bible/
├── 06-generation-plan/
├── 07-generated-assets/
│   └── shots/
│       └── S001-01/
│           ├── take-001.mp4
│           ├── take-002.mp4
│           ├── last-frame.png
│           └── mid-frame.png
├── 08-validation/
├── 09-post/
├── 10-delivery/
├── intake/
│   ├── raw-user-input.md
│   ├── intake-analysis-report.json
│   ├── project-brief.v1.yaml
│   └── project-config.resolved.yaml
├── references/
│   ├── index/
│   │   └── reference-index.json
│   ├── characters/
│   ├── environments/
│   ├── props/
│   ├── style/
│   └── scale/
├── versions/
│   ├── artifacts/
│   └── checkpoints/
└── state/
    ├── graph/
    ├── budget/
    └── approvals/
```

#### Artifact File Layout

Small projects optimize for human review over large-scale indexing. Each artifact is stored in
its own directory. The current candidate is always obvious, and historical versions are tucked
under `versions/`.

```
projects/<project_slug>/<phase>/<artifact_id>/
├── current.json
├── current.meta.json
├── current.md
└── versions/
    ├── v001.json
    ├── v001.meta.json
    ├── v002.json
    └── v002.meta.json
```

Rules:

- `current.json` is the machine-readable artifact body the MCP tools inspect by default.
- `current.md` is a generated human-readable review view for filesystem inspection.
- `current.meta.json` contains the active artifact metadata.
- `versions/` contains immutable historical JSON bodies and metadata.
- Version files do not live next to the current files.
- Scene and matrix artifacts should render useful Markdown: script text, scene intent, camera
  movement, environment, references, and asset refs.

#### Asset File Layout

Generated/reviewable media is organized by scene first, then shot. This matches the human review
workflow: inspect a scene, inspect its shots, then choose or revise takes.

```
projects/<project_slug>/07-generated-assets/scenes/<scene_id>/<shot_id>/
├── take_001.mp4
├── take_001.meta.json
├── take_002.mp4
├── first_frame.png
├── last_frame.png
└── review.md
```

The root `asset-manifest.json` remains the machine-readable table of assets. Each entry should
include `scene_id`, `shot_id`, `kind`, `take`, `active`, and `path` so the MCP tools can show actual
files available for review.

#### Tests

- [ ] `tests/unit/artifacts/test_store.py` — save, load, version, supersede
- [ ] `tests/unit/artifacts/test_manifest.py` — manifest creation and query
- [ ] `tests/unit/artifacts/test_paths.py` — path resolution
- [ ] `tests/unit/artifacts/test_versioning.py` — version chains and status
- [ ] `tests/unit/artifacts/test_index.py` — index queries

---

## Task Checklist

- [ ] Implement `ArtifactStore` with methods: `save(artifact, metadata)`, `load(artifact_id, version)`, `list(phase)`, `list_by_type(type)`, `supersede(artifact_id, new_version)`
- [ ] Implement canonical path resolver (`paths.py`) following the directory structure above
- [ ] Implement artifact metadata attachment (every artifact gets `ArtifactMetadata` from Phase 01)
- [ ] Implement version tracking: candidate → approved → superseded; parent_version linking
- [ ] Implement asset manifest types:
  - [ ] `ReferenceAssetManifest`
  - [ ] `GeneratedClipManifest`
  - [ ] `FrameExtractionManifest`
  - [ ] `AudioAssetManifest`
  - [ ] `AssemblyManifest`
  - [ ] `DeliveryManifest`
- [ ] Implement artifact index (in-memory + JSON file per project) for querying by phase, type, status, version
- [ ] Implement active-take selection for generated assets (one take active per shot)
- [ ] Write unit tests for all store operations
- [ ] Write unit tests for manifest operations
- [ ] Write unit tests for path resolution
- [ ] Run `make ci-check`

---

## Artifact Metadata (Every Artifact)

```json
{
  "artifact_id": "artifact:script:S001:v1",
  "artifact_type": "script_scene",
  "project_id": "film_2026_0001",
  "phase": "screenwriting",
  "version": 1,
  "status": "candidate",
  "parents": ["artifact:scene-intent:S001:v1"],
  "created_by": "screenwriter-agent",
  "reviewed_by": [],
  "validation_refs": [],
  "approval_ref": null,
  "kb_context_ref": null,
  "created_at": "2026-06-19T12:00:00Z"
}
```

---

## Acceptance Criteria

- [ ] Artifacts can be saved, loaded, listed, versioned, and superseded
- [ ] Every artifact has metadata with all required fields
- [ ] Version chains are correct (v1 → v2 → v3, parent linking)
- [ ] Status transitions work (candidate → approved → superseded)
- [ ] Asset manifests track generated files and their relationships
- [ ] Active-take selection works (only one active take per shot)
- [ ] Artifact index supports queries by phase, type, status
- [ ] Path resolution follows the canonical directory structure
- [ ] All tests pass
- [ ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| Git vs external storage for large media | Metadata + manifests in git; media files referenced by path, optionally git LFS later |
| Concurrent writes | Single-writer model (orchestrator is the only writer); file-based locking if needed |
| Path conventions drift | Centralize in `paths.py`; no other module constructs paths manually |
