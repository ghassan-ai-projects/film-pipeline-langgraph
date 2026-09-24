# Phase 04 — Artifact Store & Manifests (v2, post storage-upgrade)

**Status:** implemented as described below. The storage upgrade
(`documentation/storage-upgrade-plan.md`) replaced the original store; this
document now describes the shipped design. Where the original phase-04 text
disagreed, it has been rewritten rather than annotated.

**Depends on:** Phase 01 (Schemas), Phase 03 (Config & Profile System)
**Blocks:** Phase 05 (LangGraph Skeleton), Phase 08 (Review Package), Phase 11 (Checkpoint/Resume)

---

## Goal

Versioned, typed, human-readable artifact persistence. One storage root
holds one directory per project; a human can open a project folder and read
its state and deliverables without tooling, while every machine consumer
works through one small API (`ArtifactStore`).

---

## Storage root

- Resolution: explicit argument > `FILM_PIPELINE_STORAGE_ROOT` >
  `~/.film-pipeline/projects` for entry points. Library constructors
  require an explicit root — there is no implicit default.
- Roots are marker-gated (`storage.json`: `layout_version`, `profile`,
  `schema_version`, `created_at`). Fresh directories auto-initialize;
  pre-existing directories without a marker — including old
  film-pipeline trees — and corrupt markers are refused with actionable
  errors.

## Per-project layout

```
<root>/<project_id>/
├── project.json                    # typed ProjectRecord entry point
├── README.md                       # GENERATED: phase + artifact links
├── artifacts/
│   └── <NN-phase>/<artifact_id>/
│       ├── meta.json               # current version + status (only mutable file)
│       ├── current.md              # GENERATED human view (typed renderer)
│       └── versions/vNNN.json      # immutable envelopes (provenance+payload+checksum)
├── media/scenes/<scene>/<shot>/    # generated media + take-NNN.json sidecars
├── index/artifacts.json            # derived index, regenerated on write
├── state/graph-state.json          # machine snapshot per mutating operation
├── checkpoints/checkpoints.jsonl   # append-only checkpoint metadata
├── audit/audit-log.jsonl           # append-only audit trail
├── .storage.lock                   # per-project write lock (flock)
├── .gitignore                      # media/ excluded from checkpoint commits
└── .git/                           # per-project checkpoint repository
```

## The artifact envelope

Every version is one immutable `versions/vNNN.json` file:

```jsonc
{
  "kind": "film.studio/script",
  "schema_version": 1,
  "artifact_id": "script",
  "artifact_type": "script",
  "project_id": "…", "phase": "script",
  "version": 1,
  "created_at": "2026-09-24T12:00:00.123Z", "created_by": "screenwriter-agent",
  "reviewed_by": [], "validation_refs": [], "approval_ref": null,
  "kb_context_ref": null,
  "parents": [{"artifact_id": "scene_list", "version": 1}],
  "built_from": {"scene_list": "artifact:script:scene_list:v1"},
  "prompt_template_version": null, "model_profile": null,
  "change_summary": "", "checksum": "sha256:…",
  "payload": { "…domain model…": true }
}
```

Rules:

- **Registry-gated.** `artifacts/registry.py` maps every artifact id to a
  `KindSpec` (kind key, payload schema version, mutability). Saving an
  unregistered id raises `KindNotRegisteredError`; ids must be lowercase
  snake_case (`sanitize_artifact_id` maps arbitrary entity ids injectively).
- **Tolerant reader, strict writer.** Unknown envelope fields are preserved
  with a logged warning; a `schema_version` newer than supported raises
  `SchemaTooNewError`; older payloads migrate through the registered
  migration chain (`register_migration` / `migrate_payload`).
- **Integrity.** Every envelope carries a payload checksum; reads verify it
  (`ChecksumMismatchError` on tamper or corruption). All writes are atomic
  (temp + fsync + rename) with deterministic, sorted-key JSON.
- **Status is artifact-level.** `meta.json` names the current version and
  its status; a non-current version is superseded by definition. The human
  approval gate is the production caller of `approve()`, which also files
  the artifact's human view under `deliverables/`.
- **Mutable kinds** (generation ledger) are the exception: a single
  revision-counted `<artifact_id>.json` written through `save_mutable`.

## Refs and reads

- Refs are `ArtifactRef` values with canonical string form
  `artifact:<phase>:<artifact_id>:v<N>`.
- `store.save()` returns the canonical ref of the stored version.
- `store.load_ref()` resolves any ref; `store.latest_version()` is the only
  "latest" idiom; unversioned reads return the current version, so repaired
  artifacts are visible to their consumers.
- `list_artifacts()` returns a defined order: phase order, then artifact
  id, then current version.

## Human views

`current.md` is generated per save through typed renderers
(`artifacts/rendering.py`): screenplay-style script scenes, tables for
scene lists and the shot matrix, findings sections for validation and
consensus reports, prose for treatments and constitutions, sections for
bibles — generic fallback for unregistered kinds. The project `README.md`
and `deliverables/` are generated the same way and must never be hand-edited.

## Asset manifests

`asset-manifest.json` per project records every generated asset:
`asset_id`, `path` (project-relative), `kind`, `scene_id`, `shot_id`,
`take`, `active`, `sha256`. The manifest API enforces the active-take
invariant (exactly one active clip per shot). Generated media lives under
`media/scenes/<scene>/<shot>/` with a `take-NNN.json` sidecar carrying the
same facts. (The physical move of the manifest to `index/assets.json` is
deferred — the manifest stays at the project root for now.)

## Path rules

- Every artifact path flows through `artifacts/paths.py`; no other module
  constructs paths manually. Media paths are project-relative.
- Checkpoints never track media (`.gitignore` covers `media/`).

## Concurrency and safety

Mutating store operations hold a per-project `flock` (`.storage.lock`), so
version allocation and status transitions cannot collide between threads or
sessions. Readers never take the lock; all reads consume atomically
replaced files.

## Acceptance criteria

- Golden-layout test pins the on-disk tree (`tests/unit/artifacts/test_store_v2.py`).
- Two concurrent savers produce distinct versions and valid JSON.
- Tampered payloads fail integrity checks; too-new schema versions are
  refused with actionable errors; older payloads migrate.
- The suite leaves real storage roots untouched (session guard), and guard
  tests forbid implicit roots, silent adoption, and unregistered kinds.
