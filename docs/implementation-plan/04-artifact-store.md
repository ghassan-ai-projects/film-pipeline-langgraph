# Phase 04 — Artifact Store & Manifests

**Depends on:** Phase 01 (Schemas), Phase 03 (Config & Profile System)
**Blocks:** Phase 05 (LangGraph Skeleton), Phase 08 (Review Package), Phase 11 (Checkpoint/Resume)

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
