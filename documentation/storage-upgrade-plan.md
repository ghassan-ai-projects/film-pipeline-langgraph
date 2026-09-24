# Storage Upgrade Plan — Complete Rewrite of Project Information Storage (v2)

Status: completed plan for the `storage-upgrade` branch. Revised after
adversarial critique (gap audit + traceability audit). Quality bar and end goal
(§1) govern every phase.

> **Owner decision (post-P5):** the migration tooling (D8, P6) and all
> backward-compatibility surfaces (legacy loaders, file fallbacks, the
> `FILM_PIPELINE_PERSIST_ROOT` alias, legacy ref forms, legacy-root adoption)
> were **removed** at the owner's request. Old-layout projects are not
> readable by this version and no migrator ships. D8/P6 text below is kept
> as design history only.

---

## 1. End goal and quality bar

**End goal.** Project information storage is rewritten so that: a human can open any
project folder and read its state and final results like a well-organized document set;
every stored artifact uses standard, documented, stable formats; the store is
schema-versioned and extensible without breaking readers; test output and production
output are separated by construction; and the non-standard data structures (raw dict
state dumps, colon-mangled refs, four sidecar conventions) are replaced with boring,
typed, efficient ones. All consumers — graph, MCP tools, review/validation/checkpoints/kb
— keep working through a small, stable API, and existing projects have a tested
  migration path (later removed by owner decision — see note above).

**Quality bar (every phase, no exceptions).**

1. `make ci-check` green: ruff format + lint, mypy strict, pytest ≥90% coverage, `uv build`.
2. Tests prove behavior, not coverage — including: a test that fails if a test run could
   write into production storage; a golden-layout test pinning the on-disk spec; a
   migration round-trip test on a committed old-layout fixture.
3. Every stored artifact envelope **and every mutable state file** carries an explicit
   schema version; unknown newer versions raise an actionable error
   (`SchemaTooNewError` naming kind/found/max/path/remedy). Derived files (index caches,
   generated markdown, README) carry no version — they are rebuildable by definition.
4. Contracts kept: MCP tool response shapes (§5) and the graph-side contract (§5a:
   LangGraph state schema, ref flow between nodes, checkpoint/resume protocol are
   unchanged — only persistence locations move). Every intentional breaking change is
   listed in §8 and documented **in the same phase that ships it**.
5. Docs updated with behavior in-phase (each phase bar names its doc deliverable).
6. No new dependencies; no abstraction layers without a concrete current need.
7. Process: one commit per phase; each phase reviewed by 3 reviewer subagents
   (correctness, cleanliness/design, completeness-vs-plan); all blocking findings fixed
   before commit. Loop ends only when CI is green, reviewers return no blocking findings,
   and the end goal is demonstrably met.

## 2. Root causes (from the 5-lens research, condensed)

| Complaint | Root cause (evidence) |
|---|---|
| Messy | 6 root-resolution sites, CWD-relative default `Path("projects")`, legacy auto-adoption scan replicating projects across roots (`app/_persistence.py:125-241`), root logic duplicated in `paths.py`, `store.py`, `graph/services.py`, `app/runtime.py`, `graph/graph.py`, `cli/run.py` |
| Results hard to read | Raw LangGraph state dumped verbatim to `project-state.json` (+ `.graph_state.json` copy) incl. `_orchestrator__*` private keys; markdown renderer is a payload-shape-sniffing key-value dump (`artifacts/store.py:191-263`); no per-project entry point or index |
| Inflexible | No readers of `schema_version`; `extra="ignore"` everywhere + unvalidated `load()`; hardcoded v1 loads at 10+ sites; phase unknown to refs → 6 brute-force phase scanners; layout fixed in module constants |
| Test/prod mixing | CWD default + scripts writing `projects/`; conftest needs 4 overlapping fixtures incl. monkeypatching `ArtifactStore.__init__`; `projects/` mixes real films and test debris; adoption copies test projects into `~/.film-pipeline/runtime/` |
| Strange data structures | State persisted as raw dict (AGENTS.md violation); refs `artifact:<id>:v<N>` parsed 8 ways, ambiguous with colon-bearing ids; `save()` returns `Path` used as ref by 4 MCP tools; every save writes body 2×+meta 2×+md; per-step write amplification ≈6 full-state writes; 4 sidecar conventions; JSON-inside-JSON review scores; dead parallel systems (`artifacts/versioning.py`, `artifacts/index.py`, `observability/` scaffolding, unused `approve/supersede`) |

## 3. Design decisions

**D1 — Backend: files + derived JSON index. No SQLite for artifacts.**
Human-primary deliverables stay browsable plain files; `index/artifacts.json` and
`index/assets.json` are derived caches regenerated on write (rebuildable, so drift
self-heals). The existing LangGraph `SqliteSaver` for graph checkpoints stays (moved
under the storage root in P4). Single-writer model per project documented; `fcntl.flock`
is taken **inside the store's mutating methods** (save/approve/supersede/state writes) on
`<project>/.storage.lock` — fixes the `next_version` TOCTOU without any call-site locks.

**D2 — One storage root, marker-gated; resolution rules.**
`resolve_storage_root(explicit)` = explicit arg > `FILM_PIPELINE_STORAGE_ROOT` env >
`FILM_PIPELINE_PERSIST_ROOT`-derived (deprecated alias, logs deprecation) > default
`~/.film-pipeline/projects` **for entry points only** (CLI, MCP server). Library
constructors take root as a **required argument** — no default anywhere; this includes
`ArtifactStore`, `paths.*` helpers, `StudioRuntime`, `GraphServices` (whose
`default_factory=ArtifactStore` becomes explicit construction via the resolved root).
Marker semantics: `init_storage_root(root)` creates `<root>/storage.json`
(`{layout_version, profile: "production"|"sandbox", schema_version, created_at}`);
constructing on a **fresh non-existent directory auto-inits** it; an **existing unmarked
directory that sniffs as a legacy film-pipeline store is marked in place** (upgrade-on-
open — the P6 migrator then brings projects forward; until then this is the bridge that
keeps existing users running without silent cross-root adoption); **any other pre-existing
directory is refused** with actionable guidance. A corrupt marker is refused with a
repair message. `StudioRuntime` resolves its root through the same
`resolve_storage_root()`/explicit-arg rule in P1 (non-persistent invocations get a
throwaway temp directory — never the CWD or home); its wider runtime tree keeps working
unchanged until P4 merges it. Legacy roots are never auto-adopted at runtime; the
adoption **write** path is removed in P1; the operator backend lists only the configured
root from P1 onward (legacy projects return via the P6 migrator — acceptable on this
branch because the branch merges only after P6). Layout versions: unmarked legacy trees
are v0; P1 markers stamp **v1** (old artifact layout, new root discipline); P2 bumps the
marker to **v2** when the new engine lands, and v1 roots become migration inputs.

**D3 — Per-project layout (v2).**

```
<root>/<project_id>/
├── project.json            # typed ProjectRecord: id, title, kind, phase, ref summary, timestamps
├── README.md               # GENERATED index: phase, next gate, links to current deliverables
├── artifacts/
│   └── <NN-phase>/<artifact_id>/
│       ├── meta.json       # CURRENT pointer + artifact-level state:
│       │                   #   schema_version, artifact_id, artifact_type, phase,
│       │                   #   current_version, status (candidate|approved|superseded
│       │                   #   applies to the artifact via its current version),
│       │                   #   updated_at, reviewed_by, validation_refs, approval_ref,
│       │                   #   kb_context_ref   ← full blueprint-required field set
│       ├── current.md      # GENERATED human view of current version (typed renderer)
│       └── versions/
│           └── v001.json   # immutable full envelope (payload + provenance + checksum)
├── media/                  # ALL binaries (generated + reference), one root
│   └── scenes/sc_001/shot_0001/take-001.mp4 + take-001.json (sidecar: kind, provider, sha256…)
├── index/{artifacts.json, assets.json}   # derived, regenerated on write
├── state/
│   ├── graph-state.json    # machine snapshot: {"schema_version": 1, "state": {…}}
│   │                       # (replaces project-state.json + .graph_state.json)
│   └── runs/<run_id>.json
├── checkpoints/checkpoints.jsonl   # append-only metadata (replaces rewritten checkpoints.json)
├── audit/audit-log.jsonl           # append-only (replaces rewritten array)
├── .gitignore                      # media/ excluded (template updated in P5; migrator rewrites old ones)
└── .git/                           # per-project checkpoint repo
```

- Budget and approvals remain **artifacts** (mutable kinds in the artifact tree), not
  `state/` files — `state/` holds only the graph snapshot and run records.
- Artifact ids: lowercase snake_case, no `:`/`/`, case-fold unique (APFS-safe),
  validated at save. The two colon-bearing producers are renamed in the same phase that
  turns validation on: `profile_change_proposal:<id>` → `profile_change_proposal__<id>`,
  `invalidation_report_profile_change:<id>` → `invalidation_report_profile_change__<id>`;
  the migrator maps legacy colon-id directories to the new names (round-trip tested).
- Phase dir names unchanged (`intake`, `01-vision`…`10-delivery`), generated from ONE
  enum-driven map (`paths.PHASE_DIR_MAP`); discovery's `_DISCOVERED_PHASE_ORDER` is
  derived from that map (amendment: derived rather than deleted, so write-side and
  discovery-side names cannot drift).
- `versions/` envelopes are immutable **except nothing** — `status` lives at artifact
  level in `meta.json` (current) and in the derived index; a non-current version is
  superseded by definition. `approve()`/`supersede()` mutate `meta.json` + index only.

**D4 — Envelope + registry + versioning.**
One envelope schema for all versioned artifacts:

```jsonc
{
  "kind": "film.studio/script",     // registry key; 1:1 with ArtifactType vocabulary
  "schema_version": 1,              // int, per kind
  "artifact_id": "script", "project_id": "…", "phase": "script",
  "artifact_type": "script",        // blueprint vocabulary preserved during migration
  "version": 1,
  "created_at": "2026-09-24T12:00:00.123Z",
  "created_by": "screenwriter-agent",
  "reviewed_by": null, "validation_refs": [], "approval_ref": null, "kb_context_ref": null,
  "parents": [{"artifact_id": "scene_list", "version": 1}],
  "built_from": {"scene_list": "artifact:script:scene_list:v1"},
  "prompt_template_version": null, "model_profile": null,     // product-completion-plan/02:61-66
  "change_summary": "", "checksum": "sha256:…",               // over canonical payload
  "payload": { …existing Pydantic model unchanged… }
}
```

- The envelope carries the **full `ArtifactMetadata` field set** (blueprint §5 /
  `artifact-store.md:151-167`) so `list_artifacts`, review packages, and the operator
  backend keep working without opening envelopes; a metadata-completeness test pins it.
- `ArtifactKindRegistry`: kind → (payload model, current schema_version, markdown
  renderer, mutability). **P2 includes a full inventory of all ~17 save sites and
  registers every kind**; saving an unregistered kind raises `KindNotRegisteredError`
  (loud, never a silent fallback); one save test per registered kind.
- Tolerant reader (unknown keys preserved + load warning), strict writer
  (`extra="forbid"` pre-serialization). Versioned bodies carry all metadata —
  `current.json` body duplication and per-version `.meta.json` sidecars die; `meta.json`
  is the thin current pointer. `ArtifactMetadata.schema_version: str "v1"` is dropped
  (migrator maps it; §8).
- Compat policy: support current schema_version per kind; a greater
  `schema_version` → `SchemaTooNewError` with remedy. The N−1 migration mechanism ships
  in P2 with one worked test even though all kinds start at 1.
- Mutable kinds (generation ledger, budget, prompt registries): single JSON file
  (`<artifact_id>.json`) written atomically with a `revision` counter — never
  masquerade as immutable versions. Fixes the ledger-pinned-to-v1 history destruction.

**D5 — Refs and version resolution (one model).**
The existing `schemas/artifact.py::ArtifactRef` is **extended** (optional `phase`,
`to_string()`/`from_string()`), becoming the single ref model — no second class.
Canonical string: `artifact:<phase>:<id>:v<N>`; the resolver also accepts legacy
`artifact:<id>:v<N>` (phase=None → resolved via the index). `store.save()` returns an
`ArtifactRef` (fixes the path-as-ref bug in planning/bibles/reference tools). The 8
ad-hoc parsers are deleted. `store.latest_version(project, phase, id)` becomes the only
"latest" idiom, replacing `next_version−1` and v1-hardcoded loads (behavior fix: repaired
v2+ artifacts become visible — §8). `list_artifacts` ordering: phase order → artifact_id
→ version desc (today: filesystem rglob order).

**D6 — Serialization & ops rules.**
JSON: `indent=2, sort_keys=True, ensure_ascii=False`, UTF-8, LF, trailing newline —
one `serialization.py` module. JSONL for append-only logs. Timestamps RFC 3339 UTC `Z`.
All writes atomic (sibling temp + `os.replace` + fsync) via one helper; media downloads
included. `sha256` + `size_bytes` on artifact metadata and asset entries; `active-take`
invariant (exactly one active take per shot) enforced by the manifest API and tested.
Media naming `take-NNN.<ext>` + sidecar JSON (kind from sidecar, not suffix parsing).
Asset manifest paths project-relative. **Scope-trimmed tooling:** `storage_migrate`
(MCP tool + CLI, `requires_confirmation=True` per blueprint 2284-2285 /
acceptance-checklist:94) and a `storage_verify` *function* used by the migrator and
tests — the prune/export tool trio is deferred (non-goal).

**D7 — Test/prod separation.**
Single conftest structure replacing the four-fixture patchwork: (a) autouse
function-scoped env fixture pointing `FILM_PIPELINE_STORAGE_ROOT` at tmp (kept
function-scoped for xdist workers); (b) session-scoped guard snapshotting **path sets +
sizes** (not mtimes; tolerates missing dirs) of `~/.film-pipeline`, repo `projects/`,
`.film-pipeline-run` before the suite, asserting unchanged after, failing with the
differing paths; (c) a `store_root` fixture + `make_store()` helper that create and
mark a temp root — used to update all ~30 direct `ArtifactStore(root=tmp)` test
constructions in P2; (d) the `ArtifactStore.__init__` monkeypatch is deleted (no
default root left to redirect). CI guard tests, all landing in P1: (a) no
`Path("projects")` / bare `Path.home()` outside the storage module — **all** default-root
sites (incl. `manifest.py`, `generation/executor.py`, `mcp/tools/artifacts.py`,
`runtime.py`, `graph/services.py`) are fixed in P1 as one-line resolution changes so the
guard passes immediately; (b) `ArtifactStore()` without root raises; (c) existing
unmarked root refused; (d) suite-leaves-default-roots-clean; (e) no silent adoption.
Scripts under `scripts/` set `FILM_PIPELINE_STORAGE_ROOT` to a scratch dir (or take a
flag); `make scratch-clean` removes it.

**D8 — Migration old→new.** REMOVED BY OWNER DECISION — see P6 note above.
    The text below is retained as design history.
`storage_migrate` MCP tool + CLI sharing one pure module. **Full legacy-shape list:**
flat CWD `projects/`; `.film-pipeline-run/<run>/` (incl. nested `artifacts/` +
project dirs); `~/.film-pipeline/artifacts/`; `~/.film-pipeline/runtime/`; CLI run dirs
`~/.film-pipeline/runs/<name>/`; `~/.film-pipeline/checkpoints/checkpoints.sqlite`
(LangGraph SqliteSaver); trash root `~/.film-pipeline/trash/` (detected, listed, never
scanned as projects). Per-project **merge recipe** (runtime tree + artifact tree are two
halves of one project): union file sets, state content → `project.json`, `.gitignore`
rewritten to the new template, per-file sha256 into the ledger; artifact dirs renamed
per the colon-id map; **path-shaped refs inside migrated state normalized** to canonical
refs where resolvable, else marked `"dead_ref": true` (fixture includes path refs).
Git history: commits from before migration track legacy paths — rollback across the
migration boundary is documented as best-effort (restore via the store's re-materialize
from checkpoint metadata, not raw `git checkout`, wherever paths changed); post-migration
checkpoints track the new layout. Sqlite checkpoints are copied to
`<root>/checkpoints/checkpoints.sqlite`; resume of gates created pre-migration keeps
working (thread_id = project_id unchanged; legacy path-refs in restored state are
normalized on restore). Flow: detect → `--dry-run` plan → copy (never move) with
`migration-log.jsonl` → verify (re-hash + parse + layout invariants + `storage_verify`)
→ quarantine sources as `<name>.migrated-<timestamp>` (trash semantics; never
hard-delete) → idempotent (ledger + `layout_version` short-circuit). Requires
`confirmed=True`. We will NOT run migration against the user's real home data
autonomously; dry-run evidence only.

**D9 — Readability.**
Registry-keyed typed markdown renderers replace payload-shape sniffing for the major
artifact classes (script/treatment/scene list/matrix/bibles/validation reports/review
packages) with a generic fallback. Generated per-project `README.md` (phase, gate,
deliverable links) and `deliverables/` populated by the **runtime approval path**
(`_graph_exec.approve_phase` → store status transition → deliverables/README
regeneration — the first production caller of the status machine; today every delivered
film says `"candidate"`). Test asserts a delivered project has approved statuses and a
non-empty `deliverables/`.

## 4. Explicit non-goals (deferred; keep the rewrite scoped)

- Domain schema retyping beyond what storage forces (`MatrixPatch.set` typing, free-text
  status strings → StrEnums, naive datetimes) and the JSON-inside-JSON review-scores
  fix (`mcp/tools/reference_generation/outcomes.py:72,90`) — separate follow-up.
- Fountain screenplay format (script renderer emits screenplay-style Markdown; Fountain
  projection is future work).
- SQLite/LFS for artifacts; concurrent multi-writer support; remote storage.
- `storage_prune` / `storage_export` operator tools (deferred; only `storage_migrate`
  + the `storage_verify` function ship).
- Migrating the knowledge base (`film-knowledge-base/`) — separate storage, untouched.
- Deleting the user's existing project data — the migrator quarantines; operators decide.
- Accepted residual rawness: `state/graph-state.json` remains a machine snapshot of the
  LangGraph state (incl. `_orchestrator__*` keys) — the human surface is `project.json`,
  `README.md`, and the typed renderers. Retyping graph-state channels is graph-phase work.

## 5. Preserved MCP product contracts

`_ok/_error` envelope; `list_artifacts` row fields (artifact_id, artifact_type, phase,
version, status); `list_assets` row fields (asset_id, kind, scene_id, shot_id, take,
active, path); `review_package` model dump + router block; `inspect_artifact` body
passthrough (payload schemas unchanged; P2 keeps `load()` returning the payload dict);
checkpoint tool fields (checkpoint_id, project_id, phase, created_at, reason, git short
hash). Contract tests pin each row shape against the new store.

**§5a Graph-side contract (equally preserved):** LangGraph state schema, the
refs-in-state flow between nodes, the human-gate interrupt/resume protocol, and the
checkpointer wiring are unchanged by this rewrite — only *where and how* persistence
lands on disk moves. "Persist state after every mutating operation"
(product-completion/01:46-48) is preserved: P4 replaces the 6-write blast with ONE
atomic `graph-state.json` snapshot per mutation plus append-only JSONL audit.

## 6. Phases (each: implement → 3 reviews → fix → commit → docs updated in-phase)

- **P1 — Roots, marker, separation.** D2, D7, scripts redirect, all five CI guard
  tests, GraphServices/StudioRuntime/manifest/executor/MCP-tool root sites fixed,
  adoption **write** path removed, conftest rework, deprecated
  `FILM_PIPELINE_PERSIST_ROOT` alias (later removed entirely by owner decision).
  Old layout still fully functional at this phase (only root resolution changed). Docs: root/env/marker section in operator docs +
  `FILM_PIPELINE_STORAGE_ROOT` reference.
  Bar: guard (a) passes; constructing on a foreign unmarked root raises, a legacy-shaped
  root is marked in place (upgrade-on-open), a corrupt marker is refused; the
  `use_persistent_runtime()` gate is preserved (non-persistent invocations never write
  home or CWD); runtime/checkpoint/run defaults all derive from `resolve_storage_root()`;
  suite-clean guard green; `ArtifactStore()` without root raises; legacy projects on
  disk untouched.
- **P2 — Artifact engine swap.** D3 artifact tree, D4 envelope/registry (full kind
  inventory + `KindNotRegisteredError`), atomic writes + checksums, `meta.json` +
  `versions/` + `current.md`, derived `index/artifacts.json`, colon-id producer rename,
  **rollback path mapping** (restore by mapped tracked paths, not raw ids — layout
  changed so git paths changed), **compat shim**: exact P2 signatures `save→Path`,
  `load→payload dict`, `list_artifacts→list[ArtifactMetadata]`, `next_version`,
  `load_metadata`, `approve`, `supersede` — proven by the rewritten
  `tests/unit/test_artifacts.py` + `tests/unit/artifacts/test_store_v2.py`
  (amendment: coverage distributed instead of one named shim file; the signature
  tests move/delete with the shim in P3). Direct test store constructions stay
  as-is (amendment: fresh-directory auto-init makes `ArtifactStore(root=tmp)`
  and `make_store()` equivalent in tests; `make_store()` is the pattern for new
  tests). `save` honors a caller-provided `meta.status` (e.g. pre-approved
  config snapshots) but owns version numbering for immutable kinds;
  golden-layout test; parent-chain + status-transition tests; N−1 migration mechanism
  test; read-only **legacy loader** so old-layout projects stay listable/loadable
  (tested). (Legacy loader later removed by owner decision.) Docs: artifact layout
  v2 sketch in artifact-store.md.
- **P3 — Refs, versions, consumers.** D5 across graph/mcp/generation/app; delete the 8
  parsers and 6 phase scanners; fix path-as-ref (save returns `ArtifactRef`); fix v1
  hardcodes; ledger becomes a mutable kind; `store._root` private access replaced by
  public API; shim deleted; defined `list_artifacts` ordering. Docs: ref grammar.
- **P4 — State persistence collapse.** `project.json` typed record
  (`schemas/runtime_state.py::ProjectRecord`, extra="allow" for runtime keys,
  schema_version-gated on read); single `state/graph-state.json` written once
  per mutating operation from `auto_checkpoint` (guarded; unserializable
  values degrade via `str()`); `project-state.json`, `.graph_state.json`,
  `intake/graph_state` artifact removed (legacy records still restore,
  and a typed record always wins over a stale legacy file); JSONL append-only
  audit + checkpoints (id-deduped, torn lines warn); per-project flock wraps
  save/save_mutable/transitions (`.storage.lock`; the InMemoryGitBackend now
  raises on unknown pathspecs like real git); operator freshness re-pointed;
  gate → restart → resume test proves persistence-after-every-mutation.
  Amendments: the dead `graph_state` registry entry was removed; the dead
  `metadata.py` module was deleted in P2 (earlier than P7); follow-ups noted
  for P7: `delete_project` archival is not under the project lock (documented
  as requiring quiescence) and a pre-existing `test_mcp` get_runtime
  mock-leak flake. Docs: state files table.
- **P5 — Readability + media.** D9 typed renderers (registered by kind in
  `artifacts/rendering.py`; screenplay-style script, tables for scene list and
  shot matrix, findings sections for reports, bible sections), generated
  project `README.md` regenerated on save/approve, deliverables-on-approve wired
  at `_graph_exec.approve_phase` (the production caller of the status machine),
  generated media unified under `media/scenes/<scene>/<shot>/` with one
  `take-NNN.json` sidecar convention (kind/take/sha256), `assets.json`
  project-relative + sha256, active-take invariant enforced by the manifest
  API + test, `_PROJECT_GITIGNORE` covers `media/` + checkpoint-never-tracks-
  media test.
  Amendments: provider filenames are kept (renaming to `take-NNN.<ext>` is
  deferred to P6 where legacy media moves anyway — downstream consumers parse
  delivered names); reference media still lives in the runtime tree via
  `reference_generation` (a known open item — P6 shipped without it; reference
  media still lives in the runtime tree); the asset-manifest filename stays
  `asset-manifest.json` in place (the physical move to `index/assets.json` is
  deferred — P6 shipped without it). Docs: browsing guide.
- **P6 — Migration.** OWNER DECISION (post-merge of P1–P5): the migration
  tooling was removed entirely — old-layout projects are no longer readable,
  and no migrator ships. D8 below is retained as history only.
  ~~D8 complete migrator + committed old-layout fixtures (incl. a
  runtime-tree project, colon-id artifacts, path-shaped refs) + round-trip tests
  (dry-run writes nothing; migrate → verify passes; re-run no-op; quarantine; rollback
  documented); `storage_verify` function; operator migration guide.
  Amendments: the migrator physically re-layouts legacy artifact trees into
  `artifacts/<phase>/<id>/` v2 envelopes (the legacy read-path stays for
  pre-migration use only); legacy `project-state.json` becomes the typed
  `project.json`; colon-id directories are renamed; P2-era versioned ledgers
  become revision-counted mutable files; path-shaped refs in records are
  blanked and recorded under `migrated_dead_refs`; the migration ledger is a
  sibling of the storage root (`migration-log.jsonl`); the InMemoryGitBackend
  honors `.gitignore` and `HEAD` (needed by the checkpoint-media test).
  **Unblocks merge.**
- **P7 — Dead code removal + docs + version.** Delete `artifacts/versioning.py`,
  `artifacts/index.py`, observability scaffolding, unused path helpers, `.fleet/`
  debris; full rewrite of `documentation/artifact-store.md` + blueprint storage
  sections; version bump 0.4.0 (pre-1.0 precedent: 0.3.0 shipped the breaking TUI
  removal as a minor); final full CI + closing review.

Each phase's Done = its bar + quality bar §1 + `make ci-check` + reviewer sign-off.

## 7. Risks and mitigations

- Blast radius ~45 files → phase slicing (P2 shim; P3/P4 consumer groups; shim deletion
  same phase it's replaced).
- Import-time env constants are load-bearing for test ordering → converted to per-call
  resolution in P1 with the conftest rework in the same phase.
- Old projects unreachable between P1 and P6 → read-only legacy loader (P2) kept them
  loadable; later removed by owner decision (old projects unsupported).
- `inspect_artifact` raw passthrough means payload-shape drift is externally visible →
  payload models untouched; MCP contract tests pin shapes.
- Envelope generic + mypy strict → validated early in P2 (Pydantic v2 generics);
  fallback: envelope as concrete model with typed payload accessors.
- Home data contamination is real → migrator is copy+quarantine only; no autonomous
  execution on user data; dry-run evidence recorded.

## 8. Documented intentional breaking changes (shipped in the phase marked)

1. `ArtifactStore()` / `paths.*` / `StudioRuntime` require explicit root; env resolution
   via `FILM_PIPELINE_STORAGE_ROOT` (`FILM_PIPELINE_PERSIST_ROOT` deprecated alias) (P1).
2. Legacy roots no longer auto-adopted at runtime; operator lists the configured root
   only until migration. Legacy-shaped roots opened explicitly are marked in place
   (upgrade-on-open) rather than refused (P1).
3. On-disk artifact layout v2 (envelopes; `current.json` body copies and per-version
   `.meta.json` sidecars removed; `ArtifactMetadata.schema_version: str` dropped)
   behind `layout_version` + migrator (P2).
4. Colon-bearing artifact ids renamed (`profile_change_proposal__<id>`,
   `invalidation_report_profile_change__<id>`); ids validated lowercase snake_case (P2).
5. Rollback restores by mapped tracked paths; rollback of pre-migration git commits into
   v2 trees is best-effort and documented (P2/P6).
6. Ref grammar gains phase: `artifact:<phase>:<id>:v<N>`; legacy form still parses (P3).
7. `*_ref` values in MCP responses become canonical refs instead of filesystem paths
   (planning/bibles/reference tools) (P3).
8. v1-hardcoded reads return the actual latest version (repaired artifacts become
   visible) (P3).
9. `project-state.json` / `.graph_state.json` / `intake/graph_state` replaced by
   `project.json` + `state/graph-state.json` (P4).
10. Asset paths inside manifests become project-relative; media layout unified under
    `media/` with `take-NNN` naming (P5).
11. Status becomes an artifact-level property (current version's state) instead of
    per-version sidecar data; `supersede` semantics preserved (non-current = superseded).
    `save()` honors a caller-provided status (pre-approved writes stay approved) (P2).
