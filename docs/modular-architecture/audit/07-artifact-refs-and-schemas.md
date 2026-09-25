# 07 — Artifact References, Schema Registries, Statuses, and Versioning

- **Repo:** `${REPO_ROOT}`
- **Branch / commit audited:** `modular-app` @ `fb85baa0e6b769b709791a96a89980089304bf13`
  (`git log --oneline -1` → `fb85baa Merge pull request #29 from ghassan-ai-projects/storage-upgrade`)
- **Methodology:** `docs/modular-architecture/00-methodology-and-quality-bar.md` (bar A).
- **Domain cluster:** the `artifact:<phase>:<artifact_id>:v<N>` reference grammar, the
  kind/schema registry, payload schema-version rules, checksum/version enforcement
  reachability, artifact status lifecycle, and `GenerationStatus` lifecycle.
- **Revision note / self-describing verification record:** this file was corrected after
  independent verification (`docs/modular-architecture/reviews/verify-07.md`). Every dispute
  (`D1`–`D11`) and missed seam (`M1`–`M5`) was re-reproduced against HEAD before applying; the
  reproductions are recorded in the affected finding. Findings F-10–F-13 were added after
  verification and carry that verification verdict; **F-ARTIFACT-14** was added post-verification
  and `docs/modular-architecture/reviews/verify-17.md` §4 judged it **CORRECTED** (band High 12
  retained; novelty claim reduced to the schema-declaration half). All line numbers verified at
  `fb85baa`.
- **Findings after this revision: 14** — **2 Critical, 6 High, 6 Medium, 0 Low** (Critical: 02,
  05; High: 04, 06, 07, 10, 12, 14; Medium: 01, 03, 08, 09, 11, 13; Low: none). Mix reproducible
  with `grep -h '^- \*\*Severity:\*\*' docs/modular-architecture/audit/07-artifact-refs-and-schemas.md`.
- **Added post-verification (verified — CORRECTED):** F-ARTIFACT-14 — the closed-vocabulary
  schema seam (`pacing_style`, `film_type`, `phase`, `next_action`, `mode` re-declared as bare
  `str` across `schemas/**`), from `reviews/adversarial-coverage.md` §H10. Per
  `docs/modular-architecture/reviews/verify-17.md` §4 the 24/13 counts and all five executed
  asymmetries reproduce, and the pacing/phase ownership is now cited rather than claimed as new.
  Every existing finding keeps its verdict unchanged.

---

## 1. Coverage

Every file in the declared scope was read at HEAD and mapped to the cluster concern(s)
below. "Has findings" lists the finding ids that cite the file.

### 1.1 `src/film_pipeline/artifacts/**` (all 12 files)

| File | Cluster concern(s) it participates in | Status |
|---|---|---|
| `src/film_pipeline/artifacts/__init__.py` | Public re-export surface (errors, `REGISTRY`, `ArtifactStore`) | Clean, no distributed ownership found |
| `src/film_pipeline/artifacts/_layout.py` | Second storage-version axis (`storage_schema_version`), JSONL `SchemaTooNewError` | Has findings: F-ARTIFACT-04, F-ARTIFACT-05 |
| `src/film_pipeline/artifacts/envelope.py` | Ref-grammar-bearing `ArtifactEnvelope`, `SchemaTooNewError`, checksum, 3 `schema_version` fields | Has findings: F-ARTIFACT-04, F-ARTIFACT-05 |
| `src/film_pipeline/artifacts/manifest.py` | Asset manifest; `AssetEntry.kind` is a fourth kind vocabulary | Has findings: F-ARTIFACT-11 |
| `src/film_pipeline/artifacts/matrix_projection.py` | Ref parsing wrapper; malformed ref example in docstring | Has findings: F-ARTIFACT-01 |
| `src/film_pipeline/artifacts/paths.py` | `PHASE_DIR_MAP` — phase→directory map (the `<phase>` segment vocabulary) | Clean, no distributed ownership found |
| `src/film_pipeline/artifacts/project_storage.py` | Project gateway; reads `PHASE_DIR_MAP`, delegates manifest | Clean, no distributed ownership found |
| `src/film_pipeline/artifacts/registry.py` | **Kind registry**: `KindSpec` (kind slug, `schema_version`, `payload_model`, `mutable`), `MIGRATIONS`, `validate_artifact_id` | Has findings: F-ARTIFACT-03, F-ARTIFACT-04, F-ARTIFACT-08, F-ARTIFACT-09, F-ARTIFACT-12 |
| `src/film_pipeline/artifacts/rendering.py` | Markdown renderers keyed by kind; skips `schema_version` key | Clean, no distributed ownership found |
| `src/film_pipeline/artifacts/serialization.py` | Atomic writes, non-finite rejection | Clean, no distributed ownership found |
| `src/film_pipeline/artifacts/storage.py` | Storage root + marker (`LAYOUT_VERSION`, `MARKER_SCHEMA_VERSION`) | Has findings: F-ARTIFACT-04 |
| `src/film_pipeline/artifacts/store.py` | Per-kind schema check, checksum read, version numbering, status transitions, ref/id resolution | Has findings: F-ARTIFACT-01, F-ARTIFACT-02, F-ARTIFACT-03, F-ARTIFACT-05, F-ARTIFACT-06, F-ARTIFACT-09, F-ARTIFACT-10, F-ARTIFACT-12 |

### 1.2 `src/film_pipeline/schemas/**` (cluster-relevant files)

| File | Cluster concern(s) | Status |
|---|---|---|
| `src/film_pipeline/schemas/artifact.py` | **Normative ref grammar** (`ArtifactRef.from_string`/`to_string`), `ArtifactMetadata`, `ArtifactVersion` | Has findings: F-ARTIFACT-01, F-ARTIFACT-03, F-ARTIFACT-12 |
| `src/film_pipeline/schemas/_base.py` | `ArtifactStatus`, `ArtifactType`, `FilmPhase`, `ValidationStatus`, `GenerationStatus`, `SchemaBase`/`MutableSchemaBase` `schema_version` | Has findings: F-ARTIFACT-02, F-ARTIFACT-04, F-ARTIFACT-06, F-ARTIFACT-08, F-ARTIFACT-13 |
| `src/film_pipeline/schemas/runtime_state.py` | `ProjectRecord`/`GraphStateSnapshot` int `schema_version` (a separate axis) | Has findings: F-ARTIFACT-04 |
| `src/film_pipeline/schemas/__init__.py` | Re-export list for all of the above | Clean, no distributed ownership found |
| `src/film_pipeline/schemas/registries/__init__.py` | Re-exports registry **entry** schemas (agent/provider/validator/model) | Clean — distinct concern |
| `src/film_pipeline/schemas/registries/validator_registry.py` | `ValidatorThresholds`, `ValidatorRegistryEntry` (`output_schema="validation-report:v1"`) | Has findings: F-ARTIFACT-04 (third schema-version spelling) |
| `src/film_pipeline/schemas/registries/agent_registry.py` | Agent entry schema | Clean, no distributed ownership found |
| `src/film_pipeline/schemas/registries/model_registry.py` | Model registry schema | Clean, no distributed ownership found |
| `src/film_pipeline/schemas/registries/provider_registry.py` | Provider registry schema | Clean, no distributed ownership found |

### 1.3 Consumers of `ArtifactRef` / ref strings (read)

`grep -rn "ArtifactRef" src/film_pipeline --include='*.py'` (59 hits, 24 files) plus
`grep -rn "_parse_ref"` / `grep -rn "_save_artifact("`.

| Module | Concern consumed | Status |
|---|---|---|
| `src/film_pipeline/graph/nodes/_context.py` | Ref parse wrapper, ref-key→phase map, class-name→`ArtifactType` map | Has findings: F-ARTIFACT-01, F-ARTIFACT-02, F-ARTIFACT-13 |
| `src/film_pipeline/graph/subgraphs/qc.py` | **Parallel QC artifact-resolution**: latest-on-disk scan via `list_artifacts`, own validator→artifact-id table | Has findings: F-ARTIFACT-10 (previously omitted from this table — A1 gap corrected) |
| `src/film_pipeline/graph/nodes/_agent_artifacts.py` | Delegates version to `store.next_version` (correct) | Clean consumer (guard test: `tests/unit/graph/test_wrapup_nodes.py:94-96`) |
| `src/film_pipeline/graph/nodes/qc.py` | Ref resolution via pinned `state["artifact_refs"]`; saves `consensus_report` with a type value the enum rejects | Has findings: F-ARTIFACT-02, F-ARTIFACT-10 |
| `src/film_pipeline/graph/nodes/visual.py` | Ref resolution; saves `cost_estimate` inferred as `script` | Has findings: F-ARTIFACT-02 |
| `src/film_pipeline/graph/nodes/_generation_batch_planning.py` | `load_mutable_envelope` (bypasses schema check) | Has findings: F-ARTIFACT-05 |
| `src/film_pipeline/graph/nodes/_generation_prompts.py` | `_parse_ref` consumer | Clean, no distributed ownership found |
| `src/film_pipeline/graph/nodes/prep.py` | `_save_artifact` consumer (delegates version) | Clean consumer |
| `src/film_pipeline/graph/nodes/_visual_matrix_coverage.py` | `ArtifactRef.from_string` consumer | Clean consumer |
| `src/film_pipeline/graph/consistency.py` | `ArtifactRef.from_string` + `load_metadata` | Has findings: F-ARTIFACT-05 |
| `src/film_pipeline/graph/context_packets.py` | Structural `load_ref` protocol | Clean, no distributed ownership found |
| `src/film_pipeline/graph/orchestrator_validators/brief.py` | Ref parse + `version = 1` read default | Has findings: F-ARTIFACT-03 |
| `src/film_pipeline/mcp/tools/_profile_change.py` | Delegates version; writes `status=APPROVED` via `save()` | Has findings: F-ARTIFACT-06 |
| `src/film_pipeline/mcp/tools/bibles/_shared.py`, `src/film_pipeline/mcp/tools/bibles/shot.py`, `src/film_pipeline/mcp/tools/planning.py`, `src/film_pipeline/mcp/tools/reference_generation/index_files.py` | Local `_latest_artifact_version()+1` version derivation | Has findings: F-ARTIFACT-03 |
| `src/film_pipeline/mcp/tools/helpers.py` | `_latest_artifact_version` — third "latest version" rule | Has findings: F-ARTIFACT-03, F-ARTIFACT-10 |
| `src/film_pipeline/mcp/tools/validation.py` | Hardcoded `version=1` on validation-report save | Has findings: F-ARTIFACT-03 |
| `src/film_pipeline/mcp/tools/checkpoints.py` | Delegates to `store.next_version` (correct) | Clean consumer |
| `src/film_pipeline/mcp/tools/artifacts.py` | `list_artifacts` + `load` with unvalidated MCP `artifact_id` | Has findings: F-ARTIFACT-05, F-ARTIFACT-12 |
| `src/film_pipeline/post/assembly_agent.py`, `src/film_pipeline/post/subtitle_agent.py`, `src/film_pipeline/post/delivery_packaging_agent.py` | Hardcoded `version=1` on save | Has findings: F-ARTIFACT-03 |
| `src/film_pipeline/generation/executor_delivery.py` | `_asset_kind` writes the manifest kind vocabulary; sidecar `schema_version` | Has findings: F-ARTIFACT-04, F-ARTIFACT-11 |
| `src/film_pipeline/review/diff.py` | Second ref **formatter** (`_id_stem`) | Has findings: F-ARTIFACT-01 |
| `src/film_pipeline/generation/ledger.py` | Mutable persist + unconstrained `GenerationStatus` writer | Has findings: F-ARTIFACT-03, F-ARTIFACT-05, F-ARTIFACT-07 |
| `src/film_pipeline/generation/executor.py` | `GenerationStatus` writer via `update_row` | Has findings: F-ARTIFACT-07 |
| `src/film_pipeline/app/services/_browse_ops.py` | `load` consumer with a default `version: int = 1` | Has findings: F-ARTIFACT-03 (blast radius) |

No package in scope is omitted. `src/film_pipeline/graph/subgraphs/qc.py` was missing from the first
revision of this table; it is added above and filed as F-ARTIFACT-10.

---

## 2. Reference grammar site inventory

The grammar is declared in exactly one place —
`ArtifactRef.from_string` / `ArtifactRef.to_string` (`src/film_pipeline/schemas/artifact.py:31`, `:26`) —
but the *derived* forms and the *catalog vocabularies* the ref's `<phase>` and
`<artifact_id>` segments resolve against are re-derived outside it.

| Site | Parses / formats / validates | Notes |
|---|---|---|
| `src/film_pipeline/schemas/artifact.py:12` `_REF_VERSION_PATTERN = re.compile(r"^v(\d+)$")` | **Defines** the `v<N>` version segment grammar | Single definition |
| `src/film_pipeline/schemas/artifact.py:26-28` `to_string()` → `f"artifact:{self.phase}:{self.artifact_id}:v{self.version}"` | **Formats** the canonical ref | Single canonical formatter |
| `src/film_pipeline/schemas/artifact.py:31-51` `from_string()` — `parts = ref.split(":")`, `len(parts) != 4 or parts[0] != "artifact"`, `FilmPhase(parts[1])` | **Parses + validates** canonical ref; enforces phase ∈ `FilmPhase` | Single parser; does *not* validate the id charset (`:43-46` note) |
| `src/film_pipeline/schemas/artifact.py:22-24` `artifact_id: str` / `version: int = Field(ge=1)` / `phase: str` | **Validates** version ≥ 1; `phase` is a bare `str`, so direct construction bypasses the `FilmPhase` check | Grammar hole |
| `src/film_pipeline/review/diff.py:61-70` `_id_stem()` → `f"artifact:{parsed.phase}:{parsed.artifact_id}"` | **Re-formats** a second, version-less ref form ("stem") not owned by `ArtifactRef` | Second formatter |
| `src/film_pipeline/review/diff.py:67` `parsed = ArtifactRef.from_string(artifact_ref)` | Parses via canonical parser | Consumer |
| `src/film_pipeline/artifacts/matrix_projection.py:51-53` `_parse_artifact_ref()` → `ArtifactRef.from_string` | Thin wrapper re-declaration | Wrapper |
| `src/film_pipeline/artifacts/matrix_projection.py:33` docstring `(e.g. "artifact:shot_matrix:v1")` | **Documents a malformed ref** (3 segments; `from_string` rejects it, `tests/unit/artifacts/test_refs.py:28`) | Doc drift |
| `src/film_pipeline/graph/nodes/_context.py:324-326` `_parse_ref()` → `_ArtifactRef.from_string` | Thin wrapper re-declaration | Wrapper |
| `src/film_pipeline/graph/nodes/_context.py:293` `parsed = _ArtifactRef.from_string(ref)` | Parses via wrapper | Consumer |
| `src/film_pipeline/graph/nodes/_context.py:300-312` `_ARTIFACT_TYPE_BY_CLASS` | **Maps class name → `ArtifactType` value** — a parallel kind/type vocabulary | F-ARTIFACT-02 |
| `src/film_pipeline/graph/nodes/_context.py:315-321` `_infer_artifact_type()` | **Re-derives** the type; unknown/dead value → `SCRIPT` | F-ARTIFACT-02 |
| `src/film_pipeline/graph/nodes/_context.py:329-338` `_UPSTREAM_CONTENT_SOURCES` | **Re-binds** ref-key → `<phase>` string (e.g. `"script_ref": ("script", …)`) | F-ARTIFACT-13 (previously mis-tagged F-ARTIFACT-09) |
| `src/film_pipeline/artifacts/store.py:323` `parsed = ref if isinstance(ref, ArtifactRef) else ArtifactRef.from_string(ref)` | Parses via canonical parser | Consumer |
| `src/film_pipeline/artifacts/store.py:428` / `:449` / `:464` `self._safe_spec(artifact_id)` | **Resolves the `<artifact_id>` segment to a `KindSpec`** on read, fabricating a spec when unregistered | F-ARTIFACT-09 |
| `src/film_pipeline/artifacts/store.py:128` `spec = REGISTRY.spec_for(meta.artifact_id)` | Resolves id → kind on write; raises `KindNotRegisteredError` | Write-only enforcement |
| `src/film_pipeline/artifacts/store.py:120` and `:217` `validate_artifact_id(...)` | **The only id-charset enforcement** — both on the write path | F-ARTIFACT-12 |
| `src/film_pipeline/artifacts/store.py:435` / `:456` `self._version_path(project_id, phase.value, artifact_id, version)` | **Builds the read path from the raw `artifact_id`** with no validation | F-ARTIFACT-12 |
| `src/film_pipeline/artifacts/store.py:516-519` `latest_version()` | **Second "latest version" rule**, reading `meta.json` — duplicates `src/film_pipeline/mcp/tools/helpers.py:184-187` | F-ARTIFACT-03, F-ARTIFACT-10 |
| `src/film_pipeline/graph/subgraphs/qc.py:184-188` `for meta in srv.artifact_store.list_artifacts(project_id):` … `if current is None or meta.version > current.version:` | **Third resolution rule** — latest-on-disk, ignoring pinned refs; parallel to `src/film_pipeline/graph/nodes/qc.py:149-158` | F-ARTIFACT-10 |
| `src/film_pipeline/artifacts/store.py:323,428,435,449,456` and `src/film_pipeline/mcp/tools/artifacts.py:57,75` | Read side accepts an unvalidated `artifact_id` (MCP arg → path) | F-ARTIFACT-12 |
| `src/film_pipeline/artifacts/manifest.py:21` `kind: str  # reference_sheet, generated_clip, last_frame, mid_frame, audio_stem` | **Fourth kind vocabulary** (asset kinds), written at `src/film_pipeline/generation/executor_delivery.py:143` | F-ARTIFACT-11 |
| `src/film_pipeline/artifacts/_layout.py:124-134` `int(item.get(JSONL_STORAGE_VERSION_KEY, 1))` + raise `SchemaTooNewError` | Second, independent version-identifier enforcement for JSONL records | F-ARTIFACT-04, F-ARTIFACT-05 |
| `src/film_pipeline/artifacts/registry.py:33` `ARTIFACT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")` | **Validates the `<artifact_id>` segment charset** | Lives in registry, not on the ref type |
| `src/film_pipeline/artifacts/registry.py:56-66` `sanitize_artifact_id()` | Maps entity ids onto valid artifact ids (`:` → `_3a_`) | Adjacent grammar authority |
| `src/film_pipeline/artifacts/registry.py:118-123` `_kind_slug()` → `f"film.studio/{artifact_id.replace('_','-')}"` | **Derives** the stable kind key from the artifact id | Kind vocabulary |

**Independent ref-parse call sites (all routed through the one parser): 10.**
`src/film_pipeline/artifacts/store.py:323`, `src/film_pipeline/artifacts/matrix_projection.py:53`, `src/film_pipeline/graph/nodes/qc.py:152`, `src/film_pipeline/graph/nodes/_context.py:293`,
`src/film_pipeline/graph/nodes/_context.py:326`, `src/film_pipeline/graph/nodes/_visual_matrix_coverage.py:29`, `src/film_pipeline/graph/consistency.py:51`,
`src/film_pipeline/graph/orchestrator_validators/brief.py:54`, `src/film_pipeline/mcp/tools/helpers.py:202`, `src/film_pipeline/review/diff.py:67`.
**Independent ref *formatter* re-derivations: 1** (`src/film_pipeline/review/diff.py:70`), plus
**2 wrapper re-declarations** (`src/film_pipeline/graph/nodes/_context.py:324`, `src/film_pipeline/artifacts/matrix_projection.py:51`).

**Version-write derivation sites (see F-ARTIFACT-03): 1 owner + 9 independent
re-derivations.**
Owner: `src/film_pipeline/artifacts/store.py:141` (`next_version`) and `src/film_pipeline/artifacts/store.py:238` (mutable revision).
Hardcoded `version=1` (5): `src/film_pipeline/post/subtitle_agent.py:102`,
`src/film_pipeline/post/delivery_packaging_agent.py:171`, `src/film_pipeline/post/assembly_agent.py:126`,
`src/film_pipeline/mcp/tools/validation.py:191`, `src/film_pipeline/generation/ledger.py:228`.
Local `_latest_artifact_version(...) + 1` (4): `src/film_pipeline/mcp/tools/bibles/_shared.py:125`,
`src/film_pipeline/mcp/tools/bibles/shot.py:72`, `src/film_pipeline/mcp/tools/planning.py:75`,
`src/film_pipeline/mcp/tools/reference_generation/index_files.py:84`.
Correct delegations to `store.next_version` (3): `src/film_pipeline/graph/nodes/_agent_artifacts.py:69`,
`src/film_pipeline/mcp/tools/_profile_change.py:366`, `src/film_pipeline/mcp/tools/checkpoints.py:32`.
Read-side default (1): `src/film_pipeline/graph/orchestrator_validators/brief.py:51`.

---

## 3. Findings

### F-ARTIFACT-01 — The ref grammar has one parser but a second formatter and two wrapper re-declarations; the id charset is enforced only on write

- **Class:** O1 (the second formatter is a duplicated normative form; the id-charset
  gap is additionally O8, a seam with no typed contract)
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** The canonical artifact ref string `artifact:<phase>:<artifact_id>:v<N>` should be
  produced by exactly one formatter and parsed by exactly one parser, and the parser should
  enforce the same id charset the writer does.
- **De-facto owners:**
  - `src/film_pipeline/schemas/artifact.py:28` — canonical formatter — `return f"artifact:{self.phase}:{self.artifact_id}:v{self.version}"`
  - `src/film_pipeline/review/diff.py:70` — second formatter (version-less stem) — `return f"artifact:{parsed.phase}:{parsed.artifact_id}"`
  - `src/film_pipeline/artifacts/matrix_projection.py:51-53` and `src/film_pipeline/graph/nodes/_context.py:324-326` — re-declared
    parse wrappers — `def _parse_artifact_ref(artifact_ref: str) -> ArtifactRef:` / `def _parse_ref(ref_str: str) -> _ArtifactRef:`
  - `src/film_pipeline/artifacts/registry.py:33` — id-charset rule lives in the registry while the ref type
    keeps `phase: str` (`src/film_pipeline/schemas/artifact.py:24`) — `ARTIFACT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")`
- **Drift proof:** Reproduced asymmetry. `from_string` accepts any non-empty id
  (`src/film_pipeline/schemas/artifact.py:41` `if not parts[1] or not parts[2]:`), while
  `src/film_pipeline/artifacts/registry.py:49-53` rejects it:
  ```
  parsed id='../../etc/passwd' | validate_artifact_id: REJECTED
  parsed id='Bad-Id'          | validate_artifact_id: REJECTED
  ```
  `grep -rn "validate_artifact_id\|sanitize_artifact_id" tests/` → **0 hits**, so no test
  pins the agreement (drift 4). Mutation scenario also holds: change the segment scheme in
  `ArtifactRef.to_string` (`src/film_pipeline/schemas/artifact.py:28`); every ref written by `store.save`
  changes, but `src/film_pipeline/review/diff.py:70` keeps emitting `artifact:<phase>:<id>` stems and no test
  fails, because `tests/unit/review/test_diff.py:10-19` pins `_id_stem` against its own
  expected strings and `tests/unit/artifacts/test_refs.py:11-14` pins only the canonical
  round-trip. Distinct second divergence already present: `src/film_pipeline/artifacts/matrix_projection.py:33`
  documents `"artifact:shot_matrix:v1"`, a 3-segment ref that `from_string` rejects
  (`src/film_pipeline/schemas/artifact.py:34`) and `tests/unit/artifacts/test_refs.py:28` lists as malformed.
- **Reproduce:** `grep -rn "from_string\|to_string()\|_id_stem" src/film_pipeline --include='*.py'`
  and `.venv/bin/python -c "from film_pipeline.schemas.artifact import ArtifactRef; from film_pipeline.artifacts.registry import validate_artifact_id as v; r=ArtifactRef.from_string('artifact:script:Bad-Id:v1'); v(r.artifact_id)"`
- **Blast radius:** `src/film_pipeline/review/diff.py` (change/add/remove classification),
  `src/film_pipeline/artifacts/matrix_projection.py`, `src/film_pipeline/graph/nodes/_context.py`; a consumer that parses a ref
  produced by a different formatter gets a silent mis-group or a swallowed `ValueError`
  (`src/film_pipeline/graph/nodes/qc.py:153-154`, `src/film_pipeline/graph/nodes/_context.py:294-295`).
- **Candidate owner module:** `film_pipeline.artifacts.contract` — owns ref format/parse/stem
  and the id-charset rule (this is the concern genuinely shared across
  `schemas`/`review`/`graph`/`mcp`, per verify-07 §C5).
- **Extraction sketch:** Keep the `ArtifactRef` model in `src/film_pipeline/schemas/artifact.py` (dependency
  direction: `artifacts` → `schemas` already). Add `ArtifactRef.stem()` there; replace
  `review/diff._id_stem` with it; delete the two wrappers and import `ArtifactRef` directly.
  Guard test: assert `ArtifactRef.from_string(r).stem()` equals the version-stripped form of
  `r` for a table of refs, plus a real parser-vs-writer charset test
  (`artifact:script:Bad-Id:v1` accepted by the parser, rejected by `validate_artifact_id`).
- **Prior art:** `documentation/audit-findings.md:85` noted "Phase-to-directory mapping and
  safe-id logic are duplicated between `store.py` and `paths.py`" (the quoted short names are
  `src/film_pipeline/artifacts/store.py` and `src/film_pipeline/artifacts/paths.py`; that specific
  duplication is **fixed** at HEAD — `store` now uses `paths.PHASE_DIR_MAP`). The ref-*string*
  formatter duplication and the parser/writer charset asymmetry are **new**.
- **Verification dispute D1 applied:** the earlier §4 claim that
  `tests/unit/artifacts/test_refs.py:20-33` demonstrates the asymmetry was **false** — that
  test only asserts `ValueError` for malformed refs. The claim is removed from §4; the
  reproduced probe above replaces it.

### F-ARTIFACT-02 — `_ARTIFACT_TYPE_BY_CLASS` is a second kind→type registry whose two newest entries are values `ArtifactType` rejects, and the fallback silently writes `script`

- **Class:** O1
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** One place must map an artifact to its `ArtifactType`; the mapping must agree with
  the `ArtifactType` enum.
- **De-facto owners:**
  - `src/film_pipeline/schemas/_base.py:27-74` — the normative `ArtifactType` enum (45 members)
  - `src/film_pipeline/graph/nodes/_context.py:300-312` — parallel class→type map — `"CostEstimate": "cost_estimate_bom",` and `"ConsensusReport": "consensus_report",`
  - `src/film_pipeline/graph/nodes/_context.py:319-321` — silent fallback — `return _ArtifactType(_ARTIFACT_TYPE_BY_CLASS.get(class_name, "script"))` / `except ValueError:` / `return _ArtifactType.SCRIPT`
  - `src/film_pipeline/artifacts/registry.py:131-194` — the 47-kind id registry (the other vocabulary)
- **Drift proof:** Existing divergence, verified mechanically and by execution:
  ```
  ArtifactType('cost_estimate_bom') -> ValueError
  ArtifactType('consensus_report')  -> ValueError (same probe)
  _infer_artifact_type(CostEstimate(...)) = script
  is dict? False
  ```
  The `CostEstimate` object passed at `src/film_pipeline/graph/nodes/visual.py:498` is a **pydantic model**, not
  a dict: `src/film_pipeline/agents/impl/gen_planner_agent.py:11` `def _build_cost_estimate(estimate_data: dict[str, Any]) -> CostEstimate:`,
  built at `:66` and returned as `"cost_estimate": cost_estimate` (`:70`). The `SCRIPT`
  outcome comes from the **dead `"cost_estimate_bom"` map value** at `src/film_pipeline/graph/nodes/_context.py:309`
  (rejected by `ArtifactType` → `except ValueError` → `SCRIPT`), not from a dict class name
  (verify-07 D2 corrected). Live consequences at HEAD: `src/film_pipeline/graph/nodes/qc.py:109`
  `ref = _save_artifact(state, report, "consensus_report", "qc")` and `:180`
  `ref = _save_artifact(state, consensus, "consensus_report", phase)`
  (`ConsensusBuilder().build` returns a `ConsensusReport` model, `src/film_pipeline/validation/consensus.py:25`);
  `src/film_pipeline/graph/nodes/qc.py:88` passes `artifact_type="consensus_report"` explicitly, which hits the
  `ValueError` branch at `src/film_pipeline/graph/nodes/_agent_artifacts.py:35-39`
  (`return _ArtifactType(artifact_type)` / `except ValueError:` / `return _ArtifactType.SCRIPT`).
  All persist `artifact_type=script` into the immutable envelope (`src/film_pipeline/artifacts/store.py:148`) and
  surface it at `src/film_pipeline/mcp/tools/artifacts.py:40`.
  `grep -rn "_infer_artifact_type\|_ARTIFACT_TYPE_BY_CLASS" tests/` → **0 hits**, so nothing
  fails if a site changes.
- **Reproduce:**
  ```
  .venv/bin/python -c "from film_pipeline.schemas._base import ArtifactType; ArtifactType('cost_estimate_bom')"
  grep -rn "_ARTIFACT_TYPE_BY_CLASS\|_infer_artifact_type" src/film_pipeline --include='*.py'
  ```
- **Blast radius:** Durable artifact metadata for every `consensus_report` and `cost_estimate`
  written through the graph path; any consumer that filters on `artifact_type`
  (`src/film_pipeline/mcp/tools/artifacts.py:40`, `src/film_pipeline/app/services/_browse_ops.py:126`), and the markdown view
  (`src/film_pipeline/artifacts/store.py:758` renders `type: script`).
- **Candidate owner module:** `film_pipeline.artifacts.contract` — one `type_for(artifact_id, obj)`
  resolver backed by the kind registry, with missing values added to `ArtifactType` or an explicit
  refusal instead of a silent `SCRIPT` default.
- **Extraction sketch:** Move `_ARTIFACT_TYPE_BY_CLASS`/`_infer_artifact_type` into `contract`;
  derive the map from a single table keyed by artifact id, add
  `CONSENSUS_REPORT = "consensus_report"` and `COST_ESTIMATE = "cost_estimate"` to `ArtifactType`,
  and raise on an unmapped class instead of defaulting. Guard test: for every registry kind, assert a
  type resolves or the kind is on an explicit "dict payload" allow-list; assert no map value is
  rejected by `ArtifactType`.
- **Prior art:** `docs/clean-code-refactor/review-findings.md:36` flagged a *style* nit in
  `_infer_artifact_type` ("hoist `type(artifact).__name__` lookup above the `try`") and
  `:55` records a separate `_preferred_providers` fallback. The dead `ArtifactType` values and the
  silent-wrong-type behavior are **new**.

### F-ARTIFACT-03 — The store owns version numbering, but 5 sites hardcode `version=1` and 4 sites re-derive "latest + 1" from a different source; all are silently discarded

- **Class:** O5
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** Exactly one rule decides the version number written for a new artifact version.
- **De-facto owners:**
  - `src/film_pipeline/artifacts/store.py:511-514` — the owner — `def next_version(...)` / `existing = _scan_versions(self._versions_dir(...))` / `return max(existing) + 1 if existing else 1`
  - `src/film_pipeline/artifacts/store.py:115-116` — declares `meta.version` advisory — "The store owns version numbering for immutable kinds (``meta.version``" / "is advisory)."
  - `src/film_pipeline/post/subtitle_agent.py:102`, `src/film_pipeline/post/delivery_packaging_agent.py:171`, `src/film_pipeline/post/assembly_agent.py:126`, `src/film_pipeline/mcp/tools/validation.py:191`, `src/film_pipeline/generation/ledger.py:228` — hardcode `version=1`
  - `src/film_pipeline/mcp/tools/helpers.py:184-187` — third rule, sourced from `meta.json` not `versions/` — `artifacts = store.list_artifacts(project_id, fp)` / `return max(versions) if versions else 0`
  - `src/film_pipeline/mcp/tools/bibles/_shared.py:125`, `src/film_pipeline/mcp/tools/bibles/shot.py:72`, `src/film_pipeline/mcp/tools/planning.py:75`, `src/film_pipeline/mcp/tools/reference_generation/index_files.py:84` — `_latest_artifact_version(...) + 1` (anchors corrected per verify-07 D10)
  - `src/film_pipeline/artifacts/store.py:516-519` — in-store duplicate of the same meta.json rule — `meta = _read_meta_file(self._meta_path(project_id, phase, artifact_id))` / `return int(meta["current_version"]) if meta is not None else 0`
- **Drift proof:** Mutation scenario (§1.6.3b). Change `store._save_locked` to honour
  `meta.version` (a natural "respect the caller" change); the five `version=1` sites then
  reset every post/validation/ledger artifact to v1 — overwriting prior versions on disk —
  while the four MCP sites compute `_latest_artifact_version()+1` from `meta.json`, which
  differs from `next_version`'s `versions/`-directory scan whenever `meta.json` is stale or
  unreadable (`_read_meta_file` returns `None` on a corrupt file, `src/film_pipeline/artifacts/store.py:701-706`).
  No test fails: `tests/unit/post/test_post.py:299` asserts only `ref.startswith("artifact:")`,
  and `tests/unit/artifacts/test_store_v2.py:73` pins the store-computed `v1`.
  **Downgraded High→Medium (verify-07 D-verdict):** the concern is *inert at HEAD* — the audit
  itself shows all caller values are discarded, and `_save_mutable_locked` derives its revision
  from the file (`src/film_pipeline/artifacts/store.py:233-238`), so there is a single effective writer and no wrong
  behavior occurs today. §1.5 impact 3 requires wrong internal behavior; this is a latent-policy
  duplication (impact 2), not a live seam. The "two sources" observation is a structural
  divergence, not an observed one: in every tested state `meta.json` `current_version` equals
  `max(versions/)`.
- **Reproduce:** `grep -rnE 'version\s*=\s*1\b' src/film_pipeline --include='*.py'` (6 hits) and
  `grep -rn "_latest_artifact_version\|latest_version(" src/film_pipeline --include='*.py'`
- **Blast radius:** `post/`, `src/film_pipeline/mcp/tools/validation.py`, `src/film_pipeline/generation/ledger.py`,
  `mcp/tools/{bibles,planning,reference_generation}/`; once activated, a wrong version number
  corrupts the append-only `versions/` history and every `artifact:<phase>:<id>:v<N>` ref held
  in graph state.
- **Candidate owner module:** `ArtifactStore` itself (per verify-07 §C5: the defect is
  intra-store caller discipline, not a distinct module). The store returns the ref, so callers
  must not compute a version at all.
- **Extraction sketch:** Remove `version` from the caller-built `ArtifactMetadata` sites by giving
  `ArtifactStore` a `save_candidate(artifact, *, artifact_id, phase, type, created_by, …)` helper that
  fills version/status; delete `_latest_artifact_version`, `ArtifactStore.latest_version`'s
  duplicate role, and the `version=1` literals. Guard test: write two versions through every save
  path and assert the second ref's version is 2 and that a static scan finds no
  `version=1`/`_latest_artifact_version` outside `ArtifactStore`.
- **Prior art:** `documentation/audit-findings.md:45` ("`version=1` is hard-coded in bible and
  planning save paths, overwriting prior artifacts") and `:168` ("Replace hardcoded `version=1` …").
  **Status at HEAD: partially fixed.** The bible/planning paths now use
  `_latest_artifact_version()+1`; the store owns numbering; `approve`/`supersede` exist. But five
  hardcoded sites remain and four local derivations were introduced.
  **A7 addition (verify-07 M2/C6):** `documentation/reviews/arch-lens-dataflow.md:71` already
  states *"Pick one source of truth; the current design pays for both and gets neither"* about
  latest-version resolution, and `:108` documents the sequential-vs-parallel QC resolution split.

### F-ARTIFACT-04 — `schema_version` is overloaded across eleven declarations, several inside the artifact path with different types and meanings, and three are written but never validated on read

- **Class:** O8 (verify-07 D-verdict: "one name, several meanings" is a missing typed
  contract for the axes, not one model defined twice; O1 was a stretch)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** One name should identify one version rule; a reader of an artifact must be able to
  tell which generation gate applies.
- **De-facto owners (all named `schema_version` unless noted):**
  - `src/film_pipeline/schemas/_base.py:273` — per-model **string** — `schema_version: str = Field(default="v1", description="Schema version identifier.")`
  - `src/film_pipeline/schemas/_base.py:280` — `MutableSchemaBase` **string** — `schema_version: str = Field(default="v1", description="Schema version identifier.")`
  - `src/film_pipeline/artifacts/registry.py:75` — per-kind payload **int** (normative) — `schema_version: int = 1`
  - `src/film_pipeline/artifacts/envelope.py:94-99` — per-kind payload **int** persisted; the envelope explicitly
    supersedes the base field — `schema_version: int = Field(ge=0, description=("Per-kind payload schema version; the envelope itself is v1. …`
  - `src/film_pipeline/artifacts/envelope.py:134` — **meta file format** int — `schema_version: int = Field(default=1, ge=1, description="Meta file format version.")`
  - `src/film_pipeline/artifacts/envelope.py:175` — **index format** int — `schema_version: int = Field(default=1, ge=1, description="Index format version.")`
  - `src/film_pipeline/artifacts/storage.py:36` — marker schema version (`MARKER_SCHEMA_VERSION = 1`) alongside
    `LAYOUT_VERSION = 2` (`:35`); read at `:108` but the gate compares only `layout_version`
    (`:140`) — a **third write-only axis**
  - `src/film_pipeline/artifacts/_layout.py:54-55` — a *renamed* second axis — `JSONL_STORAGE_VERSION = 1` / `JSONL_STORAGE_VERSION_KEY = "storage_schema_version"`
  - `src/film_pipeline/schemas/registries/validator_registry.py:29` — a third spelling — `output_schema: str = "validation-report:v1"`
  - `src/film_pipeline/schemas/runtime_state.py:30` and `:48` — `ProjectRecord`/`GraphStateSnapshot` **int**
  - `src/film_pipeline/generation/executor_delivery.py:95` — sidecar literal `"schema_version": 1`, written by
    `write_media_sidecar` (`src/film_pipeline/artifacts/project_storage.py:214`) with **no reader** in `src/`
  - (`schemas/constraints.py:148 `data.pop("schema_version", None)` consumes axis 1)
- **Drift proof:** `src/film_pipeline/artifacts/_layout.py:52-53` documents the overload as deliberate:
  "Deliberately a distinct key: ``schema_version`` inside a record is / the per-model string
  version from ``SchemaBase`` and means something else." Existing un-validated axes:
  `ArtifactCurrentMeta.schema_version` is serialized at `src/film_pipeline/artifacts/store.py:191` and `:291`
  (constructors at `:166`/`:279`) but `_read_meta_file` (`src/film_pipeline/artifacts/store.py:701-706`) never reads it and
  no code compares it to a maximum; `ArtifactIndex.schema_version` is serialized at
  `src/film_pipeline/artifacts/store.py:414` and never read back; the marker axis is read at `src/film_pipeline/artifacts/storage.py:108` but only
  `layout_version` is compared at `:140`. The only `schema_version` comparisons in `src/` are
  `store.py:465/469` (immutable envelope vs `KindSpec`) and `src/film_pipeline/app/_persistence.py:110`
  (project record) — `grep -rn "schema_version" src/film_pipeline --include='*.py'` confirms.
  Mutation scenario: bump `ArtifactCurrentMeta.schema_version` to 2 at `src/film_pipeline/artifacts/envelope.py:134`; every
  write stamps 2 and every read ignores it — no test fails
  (`tests/unit/artifacts/test_store_v2.py:202,661` assert only the *written* index value `1`).
- **Reproduce:** `grep -rn "schema_version" src/film_pipeline --include='*.py'`
- **Blast radius:** `src/film_pipeline/artifacts/envelope.py`, `src/film_pipeline/artifacts/storage.py`, `src/film_pipeline/artifacts/_layout.py`,
  `src/film_pipeline/schemas/_base.py`, `src/film_pipeline/schemas/runtime_state.py`,
  `src/film_pipeline/schemas/registries/validator_registry.py`, `src/film_pipeline/generation/executor_delivery.py`; a future
  migration author cannot tell which `schema_version` a given reader enforces, and meta/index/
  marker/sidecar format upgrades are silent.
- **Candidate owner module:** `ArtifactStore` for the artifact-path axes (per verify-07 §C5);
  a typed `SchemaGeneration` value object per axis with a named checker.
- **Extraction sketch:** Rename to explicit names (`payload_schema_version`, `meta_format_version`,
  `index_format_version`, `jsonl_storage_version`, `marker_schema_version`,
  `sidecar_format_version`), keep the string `SchemaBase.schema_version` out of the artifact
  path, and route every persisted-axis read through a `check_readable(kind, found)` that raises
  `SchemaTooNewError`. Guard test: a table asserting each persisted version field is compared by
  exactly one checker.
- **Prior art:** `documentation/reviews/storage-upgrade-review.md:100` records that a "dead
  `ArtifactMetadata.schema_version`" was removed. At HEAD the overload is **not** resolved: the
  *inherited* `SchemaBase.schema_version` (`src/film_pipeline/schemas/_base.py:273`) is still present on every
  artifact model, and multiple artifact-path version axes remain.
- **Verification disputes D3 applied:** the count is now stated as **eleven declarations**
  (matching the reproduce grep) rather than "eight"; the marker axis and the extra axes above
  are added; the write anchors are corrected to `src/film_pipeline/artifacts/store.py:191`/`:291`.

### F-ARTIFACT-05 — `SchemaTooNewError` and checksum enforcement are path-dependent: the mutable read path, `load_metadata`, and `list_artifacts` bypass the checked reader

- **Class:** O2
- **Severity:** Critical (impact 4 × drift 4 = 16; verify-07 recomputed upward from High 12)
- **Concern:** Every artifact read must apply the same "was this written by a newer build?" and
  integrity check.
- **De-facto owners:**
  - `src/film_pipeline/artifacts/store.py:461-468` — the checked reader — `def _read_checked_envelope(self, path: Path, artifact_id: str) -> ArtifactEnvelope:` … `if envelope.schema_version > spec.schema_version:` / `raise SchemaTooNewError(`
  - `src/film_pipeline/artifacts/store.py:438` and `:459` — only callers of the checked reader —
    `return self._read_checked_envelope(path, artifact_id).payload` / `return self._read_checked_envelope(path, artifact_id)`
  - `src/film_pipeline/artifacts/store.py:298` — mutable read uses the unchecked reader — `return _read_envelope(path).payload`
  - `src/film_pipeline/artifacts/store.py:307` — `return _read_envelope(path)`
  - `src/film_pipeline/artifacts/store.py:449-455` — `load_envelope` **routes mutable kinds to the unchecked
    reader** — `if self._safe_spec(artifact_id).mutable:` / `envelope = self.load_mutable_envelope(project_id, phase, artifact_id)` / `return envelope`
  - `src/film_pipeline/artifacts/store.py:546` and `:551` — metadata read uses the unchecked reader —
    `record = _envelope_to_metadata(_read_envelope(version_path), ArtifactStatus.SUPERSEDED)` /
    `_read_envelope(envelope_path), ArtifactStatus(str(meta["status"]))`
  - `src/film_pipeline/artifacts/store.py:497-500` — list path reads raw meta.json —
    `meta = _read_meta_file(meta_path)` / `results.append(_meta_record_to_metadata(meta))`
- **Drift proof:** Reproduced asymmetry (verify-07 D4 applied):
  ```
  load_mutable(v2): NO ERROR                       <- mutable bypass CONFIRMED
  load_envelope(mutable, v2): NO ERROR             <- audit's "would raise" was FALSE
  load_envelope(immutable, v99) raised SchemaTooNewError   <- contrast: immutable check works
  ```
  The contrast is with an **immutable** envelope, not a mutable one: `src/film_pipeline/artifacts/store.py:449-455` routes a
  mutable kind to `load_mutable_envelope` → `_read_envelope` (`:307`), which has no schema check.
  Bump the `generation_ledger` kind's `schema_version` in `src/film_pipeline/artifacts/registry.py:162-164`; a stored mutable
  envelope is read by `GenerationLedgerManager.load` via `store.load_mutable`
  (`src/film_pipeline/generation/ledger.py:57`) with no `SchemaTooNewError` and no `migrate_payload`, while an
  immutable artifact read through `store.load_envelope` raises. Likewise
  `src/film_pipeline/graph/consistency.py:57` (`store.load_metadata`) and `src/film_pipeline/mcp/tools/artifacts.py` (`list_artifacts`)
  never reach the check. No test fails: `tests/unit/artifacts/test_store_v2.py:141-149` exercises
  only the immutable version-file path (`raw["schema_version"] = 99`) → drift **4**, not 3. The
  checksum gap is the same root cause: `_read_envelope` verifies `checksum` (`src/film_pipeline/artifacts/store.py:683-689`),
  but the list/index path reads `meta.json` via `_read_meta_file` and never validates
  `ArtifactCurrentMeta.checksum` (`src/film_pipeline/artifacts/envelope.py:148`).
- **Reproduce:** `grep -rn "_read_checked_envelope\|_read_envelope\|_read_meta_file\|_safe_spec" src/film_pipeline/artifacts/store.py`
- **Blast radius:** `src/film_pipeline/generation/ledger.py` (mutable ledger — the audit trail for spend),
  `src/film_pipeline/graph/consistency.py`, `src/film_pipeline/mcp/tools/artifacts.py`, `src/film_pipeline/app/services/_browse_ops.py`; a build that
  bumps a mutable kind's schema silently misreads durable state instead of refusing.
- **Candidate owner module:** `ArtifactStore` (verify-07 §C5: the defect lives entirely inside
  `src/film_pipeline/artifacts/store.py`; a "contract" module would be a move, not a distinct owner).
- **Extraction sketch:** Make `_read_checked_envelope` the only envelope reader; have
  `load_mutable`, `load_mutable_envelope`, and `load_metadata` call it (mutable specs carry the same
  `SchemaTooNewError` check), and validate `ArtifactCurrentMeta` (including its checksum) in
  `_read_meta_file`. Guard test: parametrise over `load`, `load_ref`, `load_envelope`,
  `load_mutable`, `load_metadata` and assert each raises `SchemaTooNewError` for a too-new envelope.
- **Prior art:** `documentation/reviews/storage-upgrade-review.md:27-29` claims "**Versioning
  (§1.3)** is enforced per-kind through the registry and checksum-verified on load
  (`ChecksumMismatchError`), with `SchemaTooNewError` carrying kind/found/max/path/remedy." That
  claim is **true only for the immutable path**; the mutable/metadata/list gaps are **new**.

### F-ARTIFACT-06 — Artifact status has two writers with different side effects, `save_mutable` cannot express APPROVED, and REJECTED/ARCHIVED are unreachable

- **Class:** O2 (verify-07 D5: `src/film_pipeline/artifacts/store.py` *is* the single writer of `meta.json`; the
  APPROVED ⇒ deliverable invariant is enforced in `_transition_status_locked` and bypassed in
  `_save_locked`, which is duplicated/partial invariant enforcement, not split state authority)
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** One module writes artifact `status` and enforces the legal transitions and their
  side effects.
- **De-facto owners:**
  - `src/film_pipeline/artifacts/store.py:558-591` — declared transition API — `def approve(` (CANDIDATE→APPROVED) / `def supersede(` (APPROVED→SUPERSEDED)
  - `src/film_pipeline/artifacts/store.py:177` — `save()` writes a caller-chosen status directly — `status=meta.status,` with the comment at `:172-176` "Callers may pre-approve a written artifact (e.g. profile-change / config snapshots); the store never invents a higher status."
  - `src/film_pipeline/artifacts/store.py:285` — the mutable path forces CANDIDATE, ignoring the caller — `status=ArtifactStatus.CANDIDATE,`
  - `src/film_pipeline/artifacts/store.py:652-653` — only `approve()` produces the deliverable side effect — `if next_status == ArtifactStatus.APPROVED:` / `self._record_deliverable(project_id, phase, artifact_id)`
  - `src/film_pipeline/mcp/tools/_profile_change.py:429` and `:452` — second APPROVED writer via `_save_intake_artifact` — `status=ArtifactStatus.APPROVED,`
  - `src/film_pipeline/schemas/_base.py:23-24` — declared but never entered — `REJECTED = "rejected"` / `ARCHIVED = "archived"`
- **Drift proof:** Existing divergence. `_save_intake_artifact` (`src/film_pipeline/mcp/tools/_profile_change.py:350-378`)
  calls `store.save(body, meta)` with `status=APPROVED`; `save()` persists it
  (`src/film_pipeline/artifacts/store.py:177`) but never calls `_record_deliverable`, so `profile_change_approval__*` and
  `project_config_v<N>` artifacts are APPROVED with **no** `deliverables/` entry, whereas an artifact
  approved via `store.approve` gets one (`src/film_pipeline/artifacts/store.py:652-653`). `grep -rn "_record_deliverable"`
  prints two lines — the definition at `src/film_pipeline/artifacts/store.py:386` and exactly one
  **call** at `src/film_pipeline/artifacts/store.py:653` — so the side effect has a single call
  site. Additionally `grep -rn "REJECTED\|ARCHIVED"
  src/film_pipeline` returns only the enum definitions at `src/film_pipeline/schemas/_base.py:23-24` and an unrelated
  repair-prompt string (`src/film_pipeline/schemas/repair.py:60`), so two of five declared lifecycle states have no
  transition at all. No test pins the cross-path agreement (`tests/unit/artifacts/test_readability.py:145` covers only
  `approve`).
- **Reproduce:** `grep -rn "status=ArtifactStatus\|REJECTED\|ARCHIVED\|_record_deliverable" src/film_pipeline --include='*.py'`
- **Blast radius:** `src/film_pipeline/mcp/tools/_profile_change.py` (profile-change approvals), `src/film_pipeline/artifacts/store.py`
  (`save_mutable` for the generation ledger), every reader of `status`
  (`src/film_pipeline/mcp/tools/review.py:27`, `src/film_pipeline/mcp/tools/artifacts.py:43`, `src/film_pipeline/app/services/_browse_ops.py:77`); a
  reviewer sees `approved` with no deliverable, or a ledger whose status cannot advance past
  `candidate`.
- **Candidate owner module:** `ArtifactStore` (verify-07 §C5). One transition table
  (`candidate→{approved,rejected,archived}`, `approved→superseded`, `superseded→∅`) consulted by
  `save`, `save_mutable`, `approve`, and `supersede`, with the deliverable side effect bound to the
  transition rather than to one method.
- **Extraction sketch:** Introduce `ArtifactStatusPolicy.assert_transition(current, next)` and call it
  from both `_save_locked`/`_save_mutable_locked` and `_transition_status_locked`; route the
  profile-change pre-approval through an explicit path that also records the deliverable, or forbid
  pre-approval and require `approve`. Guard test: a transition-matrix test covering every (from, to)
  pair and an "approved implies deliverable" invariant across all writers.
- **Prior art:** `documentation/audit-findings.md:83` noted "`save()` always writes
  `status=CANDIDATE`; there is no persisted `approve` / `supersede`." That is **fixed** at HEAD
  (`approve`/`supersede` exist and persist, `src/film_pipeline/artifacts/store.py:558-591`). The remaining split — pre-approved
  saves bypassing the deliverable side effect, and unreachable REJECTED/ARCHIVED — is **new**.

### F-ARTIFACT-07 — `GenerationStatus` transitions are enforced nowhere: `update_row` accepts an arbitrary status and two modules write it from 8 call sites

- **Class:** O6 (one generation lifecycle implemented twice: graph executor vs MCP dispatch;
  secondarily O2 — no transition enforcement)
- **Severity:** High (impact 4 × drift 3 = 12; verify-07 downgrade — the original Critical proof
  was falsified by execution)
- **Concern:** One module owns the generation ledger row lifecycle and refuses illegal transitions.
- **De-facto owners:**
  - `src/film_pipeline/generation/ledger.py:199-204` — unconstrained writer — `def update_row(` / `**updates: object,`
  - `src/film_pipeline/generation/ledger.py:211` — applies them blindly — `row = row.model_copy(update=updates)`
  - `src/film_pipeline/generation/ledger.py:126-131` — the terminal set (used by cost accounting) —
    `terminal = {` / `GenerationStatus.COMPLETED,` / `GenerationStatus.FAILED,` / `GenerationStatus.CANCELLED,` / `GenerationStatus.TIMED_OUT,`
  - `src/film_pipeline/generation/ledger.py:250-258` — one hardcoded legal transition inside a private helper —
    `if row.status == GenerationStatus.PREPARED:` … `"status": GenerationStatus.SUBMITTED,`
  - `src/film_pipeline/generation/executor.py:196-201` (RUNNING), `:293-298` (COMPLETED), `:399-405` (FAILED) — writer module 1 (3 status writes)
  - `src/film_pipeline/mcp/tools/generation/dispatch.py:31-38` (FAILED), `:100-106` (RUNNING), `:239-245`
    (`status=new_status` from the separate `_generation_status` mapping at `:182-196`),
    `:272-276` and `:295-300` (CANCELLED) — writer module 2 (5 status writes)
  - non-status `update_row` call sites: `src/film_pipeline/generation/executor.py:257`, `src/film_pipeline/mcp/tools/generation/dispatch.py:172`
- **Drift proof:** Reproduced illegal transition with a real cost consequence (verify-07 D6
  replaced the falsified proof):
  ```
  after COMPLETED estimate = 0
  after COMPLETED->CANCELLED estimate = 0        <- audit's original proof was FALSE
  after COMPLETED->RUNNING estimate = 5.0        <- valid proof: illegal non-terminal edge
  ```
  `update_row(..., status=GenerationStatus.RUNNING)` on a `COMPLETED` row is accepted and
  persisted (`src/film_pipeline/generation/ledger.py:211,216`), and `estimate_total_cost` (`src/film_pipeline/generation/ledger.py:123-132`) then counts the
  row again, corrupting spend accounting. No test fails:
  `tests/unit/generation/test_ledger.py:108-124` asserts only that PREPARED→RUNNING is accepted
  and persisted (drift 3: that test would have to be edited when validation is added, but nothing
  fails if another module invents a new edge). Two independent writer modules already exist
  (`src/film_pipeline/generation/executor.py`, `src/film_pipeline/mcp/tools/generation/dispatch.py`).
- **Reproduce:** `grep -rn "update_row(" src/film_pipeline --include='*.py'` — prints **11** lines:
  the definition (`src/film_pipeline/generation/ledger.py:199`) plus **10 call sites**, 8 of which
  pass a `status` and 2 do not, across the 2 writer modules
  (`src/film_pipeline/generation/executor.py`, `src/film_pipeline/mcp/tools/generation/dispatch.py`)
- **Blast radius:** `generation/` spend accounting and the per-project audit ledger
  (`generation_ledger` is persisted as a mutable artifact, `src/film_pipeline/artifacts/registry.py:162-164`); a
  completed-then-rerun row corrupts cost estimates and the resume/poll loop.
- **Candidate owner module:** `GenerationLedgerManager` (or a `generation`-local transition table),
  per verify-07 §C5 — this lifecycle is domain-specific, not an artifact-contract concern.
- **Extraction sketch:** Add a `GENERATION_TRANSITIONS: dict[GenerationStatus, frozenset[GenerationStatus]]`
  next to the enum, validate in `update_row`, and expose named methods
  (`mark_running`, `mark_completed`, `mark_failed`, `mark_cancelled`) so the two writer modules stop
  passing raw statuses. Guard test: exhaustive transition-matrix test plus an
  `update_row` test asserting an illegal transition raises.
- **Prior art:** `documentation/reviews/arch-lens-dataflow.md:108` already documents the
  sequential-vs-parallel QC split; the generation status seam itself is **new**.
- **Verification disputes D6 applied:** proof replaced; class is O6/O2, not O3 (the ledger
  representation has a single writer, `_persist`); the earlier claim that
  `src/film_pipeline/generation/executor.py:200`/`:296`/`:402` is a *second provider-status mapping* is removed — those are
  bare `status=GenerationStatus.X` literals, and only `src/film_pipeline/mcp/tools/generation/dispatch.py:182-196` maps
  `ProviderJobStatus → GenerationStatus`.

### F-ARTIFACT-08 — The kind registry and `ArtifactType` are parallel vocabularies; only the map values no enum member can hold are defects

- **Class:** O4
- **Severity:** Medium (impact 2 × drift 4 = 8; verify-07 downgrade from High 12)
- **Concern:** The set of artifact kinds and the set of artifact types should have a declared,
  enforceable relationship.
- **De-facto owners:**
  - `src/film_pipeline/artifacts/registry.py:131-217` — 47 **exact** kinds + 8 prefixes; id is the storable key —
    `"shot_matrix": _spec("shot_matrix", renderer=rendering.render_shot_matrix),` / `registry.register_prefix("checkpoint_", _spec("checkpoint", payload_model=CheckpointState))`
  - `src/film_pipeline/schemas/_base.py:27-74` — 45 `ArtifactType` values; the type is what the envelope stores —
    `SCRIPT = "script"` / `MASTER_FILM_MATRIX = "master_film_matrix"`
  - `src/film_pipeline/graph/nodes/_context.py:300-312` — the ad-hoc bridge between them (F-ARTIFACT-02)
- **Drift proof:** Existing set difference, verified mechanically, stated on **two explicitly
  labelled bases** (the finding's text and its reproducer previously used different ones).
  **Basis A — exact registry ids only (`47`) vs `ArtifactType` (`45`); this is the basis the
  reproducer prints:** 8 registry ids have no `ArtifactType` value (`consensus_report`,
  `cost_estimate`, `execution_brief`, `project_profile`, `scope_contract`, `shot_matrix`,
  `story_bible`, `subtitles`) and **6** `ArtifactType` values have no exact registry id
  (`checkpoint`, `clip`, `invalidation_report`, `last_frame`, `mid_frame`, `rollback_record`).
  **Basis B — the same comparison after adding the 8 `register_prefix` kinds
  (`matrix_patch_`, `repair_feedback_`, `profile_change_proposal_`, `profile_change_approval_`,
  `invalidation_report_`, `rollback_record_`, `checkpoint_`, `project_config_v`):** `54` vs `45`,
  `registry-only` = 12 (`+ matrix_patch, profile_change_approval, profile_change_proposal,
  repair_feedback`) and `enum-only` = **3** (`clip`, `last_frame`, `mid_frame`). The three that
  Basis B absorbs are **not** dead spellings: `checkpoint`, `invalidation_report` and
  `rollback_record` each have a registered prefix spec with a payload model
  (`src/film_pipeline/artifacts/registry.py:210-215`; `CheckpointState` / `InvalidationReport` /
  `RollbackRecord`), and `invalidation_report_*` and `rollback_record_*` ids are written through
  `ArtifactStore.save` (`src/film_pipeline/mcp/tools/checkpoints.py:32-43,61-76`;
  `src/film_pipeline/mcp/tools/_profile_change.py:468-476`). `checkpoint_` has a registered spec
  but no live `ArtifactStore` writer at HEAD (checkpoint metadata is stored as records), so
  `spec_for` resolves it but nothing writes it yet. Only the three unmatched on **both** bases
  (`clip`, `last_frame`, `mid_frame`) are dead enum values. Nothing compares the two sets; the
  registry's guard raises only on the *write* side (`src/film_pipeline/artifacts/registry.py:107`
  `raise KindNotRegisteredError(artifact_id)`).
  **Downgraded High→Medium (verify-07 D-verdict):** `src/film_pipeline/graph/nodes/_context.py:300-312` shows
  deliberate many-kinds→one-type projection (`StoryBible → script`, `ProjectProfile →
  project_config`, `MasterFilmMatrix → shot_bible`) — `ArtifactType` is intentionally coarser
  than the registry id set, so the set difference is not itself debt. Only the map values no
  enum member can hold (`cost_estimate_bom`, `consensus_report`) are actual defects, and those
  are filed as F-ARTIFACT-02.
- **Reproduce:**
```
python3 - <<'PY'
import ast
b=ast.parse(open('src/film_pipeline/schemas/_base.py').read())
types={a.value.value for n in b.body if isinstance(n,ast.ClassDef) and n.name=='ArtifactType'
       for a in n.body if isinstance(a,ast.Assign) and isinstance(a.value,ast.Constant)}
r=ast.parse(open('src/film_pipeline/artifacts/registry.py').read())
exact={k.value for n in ast.walk(r) if isinstance(n,ast.AnnAssign)
       and getattr(n.target,'id','')=='exact' and isinstance(n.value,ast.Dict) for k in n.value.keys}
print('exact basis 47/45; registry-only:',sorted(exact-types)); print('enum-only:',sorted(types-exact))
PY
```
- **Blast radius:** Limited today: `ArtifactType` is the envelope's typed label and the dead
  members are unused. `clip`/`last_frame`/`mid_frame` are dead enum entries — the live spellings
  are the `AssetEntry.kind` manifest strings (F-ARTIFACT-11).
- **Candidate owner module:** `film_pipeline.artifacts.contract` — the registry becomes the single
  kind catalog and `ArtifactType` is validated against it.
- **Extraction sketch:** Add a `kind_of(artifact_id) -> ArtifactType` column to `KindSpec` and a
  test asserting every exact registry id either maps to an `ArtifactType` member or is on an
  explicit non-storable allow-list. Guard test: registry-agreement invariant (methodology §B6).
- **Prior art:** `documentation/audit-findings.md:170` verified; the artifact kind/type claim is new.
- **Verification disputes D7/D8 applied:** the false parenthetical that `clip`/`last_frame`/
  `mid_frame` "are declared (and used in `reference_generation`)" is deleted —
  `grep -rn "ArtifactType.CLIP\|ArtifactType.LAST_FRAME\|ArtifactType.MID_FRAME" src/` and
  `grep -rn "clip\|last_frame\|mid_frame" src/film_pipeline/mcp/tools/reference_generation/*.py`
  both return **zero hits**.
- **Adversarial-evidence correction (F-08 was the replay's one PROOF-FALSE):** the drift proof
  previously said "3 `ArtifactType` values have no exact registry id" while the reproducer printed
  `enum-only` = **6** — the 3 was the prefix-inclusive basis, the 6 the exact-id basis, and the
  sentence named only the latter. Both bases are now labelled above, the six A-basis values are
  enumerated, and the three that Basis B absorbs are classified with code evidence
  (`docs/modular-architecture/reviews/adversarial-evidence.md` §3.1, §4).

### F-ARTIFACT-09 — `KindNotRegisteredError` is enforced on write but fabricated away on read, so the kind catalog can silently drift

- **Class:** O2
- **Severity:** Medium (impact 2 × drift 3 = 6; verify-07 downgrade from High 9)
- **Concern:** The registry is the single authority for which artifact ids exist; read must not
  invent a kind the registry does not know.
- **De-facto owners:**
  - `src/film_pipeline/artifacts/registry.py:8-9` — declared invariant — "Unknown ids raise :class:`KindNotRegisteredError` at save time so the catalog / cannot silently drift"
  - `src/film_pipeline/artifacts/registry.py:100-107` — the authority — `def spec_for(...)` … `raise KindNotRegisteredError(artifact_id)`
  - `src/film_pipeline/artifacts/store.py:128` — write path raises — `spec = REGISTRY.spec_for(meta.artifact_id)`
  - `src/film_pipeline/artifacts/store.py:657-661` — read path fabricates — `except KindNotRegisteredError:` / `return KindSpec(artifact_id=artifact_id, kind=f"film.studio/{artifact_id}")`
  - `src/film_pipeline/artifacts/store.py:428`, `:449`, `:464` — the three read callers of the fabricating helper
- **Drift proof:** Reproduced asymmetry:
  ```
  load(unregistered): NO ERROR -> fabricated read
  SchemaTooNewError: kind='film.studio/cost-estimate' found=99 max_supported=1
  ```
  A directory placed by any writer (a hand-edited project, a kind removed from the registry) is
  read successfully with a fabricated `kind="film.studio/<id>"` and `schema_version=1`. Mutation
  scenario: delete one entry from `registry._register_defaults`; save refuses the id
  (`src/film_pipeline/artifacts/store.py:128`) but reading a pre-existing on-disk artifact still succeeds — no test fails,
  because the only registry test path (`tests/unit/artifacts/test_store_v2.py`) round-trips
  registered kinds. The `v0 → migrate_payload → KeyError` branch (`src/film_pipeline/artifacts/registry.py:244-250`) is real
  (verified by reading).
  **Downgraded High→Medium (verify-07 D-verdict):** the real defect is "read returns data with a
  spec that was never registered and an error reporting a fabricated `max_supported=1`" —
  recoverable and invisible unless a kind is removed or renamed (impact 2).
- **Reproduce:** `grep -rn "_safe_spec\|spec_for\|KindNotRegisteredError" src/film_pipeline --include='*.py'`
- **Blast radius:** `src/film_pipeline/artifacts/store.py` read paths (all of them), `src/film_pipeline/mcp/tools/artifacts.py`,
  `src/film_pipeline/app/services/_browse_ops.py`; a removed/renamed kind is unreadable-by-design on write but
  readable-with-wrong-metadata on read.
- **Candidate owner module:** `ArtifactStore` (verify-07 §C5: intra-store read policy).
- **Extraction sketch:** Delete `_safe_spec`; make `_read_checked_envelope` take the `KindSpec`
  resolved by `REGISTRY.spec_for` and let `KindNotRegisteredError` propagate (or raise a typed
  `UnknownArtifactKindError` carrying the path). Guard test: place an artifact under an unregistered
  id and assert every read path raises the same typed error.
- **Prior art:** New (no prior art asserts this seam).
- **Verification dispute D9 applied:** the false claim that the error names "the wrong kind" is
  deleted. `src/film_pipeline/artifacts/store.py:466-468` passes `envelope.kind` (the kind **from the file**); the fabricated
  value is `max_supported` (reproduced `max_supported=1`).

### F-ARTIFACT-10 — Two QC artifact-resolution paths disagree on which version is validated (added after verification, M1)

- **Class:** O6 (one QC lifecycle implemented twice: pinned-ref sequential node vs latest-on-disk Send subgraph)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** "Which artifact version does QC validate?" must have one answer.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/qc.py:149-158` — sequential path resolves the **pinned** refs —
    `for ref_str in state.get("artifact_refs", []):` … `parsed = ArtifactRef.from_string(ref_str)` … `artifact_data[parsed.artifact_id] = store.load(project_id, FilmPhase(parsed.phase), parsed.artifact_id, parsed.version)`
  - `src/film_pipeline/graph/subgraphs/qc.py:182-188` — parallel path ignores refs and scans **latest-on-disk** —
    `# One index scan replaces the old all-phase brute force: latest version` / `for meta in srv.artifact_store.list_artifacts(project_id):` / `if current is None or meta.version > current.version:`
  - `src/film_pipeline/graph/subgraphs/qc.py:153-160` `_VALIDATOR_ARTIFACTS` — its own validator→artifact-id table,
    parallel to `src/film_pipeline/graph/nodes/qc.py`'s ref-key/family tables
- **Drift proof:** Mutation scenario, and an existing structural divergence. Change which version
  QC should validate (e.g. a repair produces `script v2` but the approved/pinned ref in
  `state["artifact_refs"]` remains `v1`): the sequential node validates v1 while the subgraph
  silently validates the latest v2 on disk. `src/film_pipeline/graph/graph.py:119` binds the normal flow to the subgraph
  and `src/film_pipeline/graph/nodes/_repair_loop.py:47` maps `"qc"` to the sequential node, so the two paths are both live.
  No test pins the agreement between the two resolution rules.
  `documentation/reviews/arch-lens-dataflow.md:108` already tabulates this
  ("Artifact resolution | Pinned versions parsed from `state["artifact_refs"]` … | Ignores refs
  entirely; scans **all** `FilmPhase` values for latest-on-disk").
- **Reproduce:** `grep -rn "artifact_refs\|list_artifacts\|ArtifactRef.from_string" src/film_pipeline/graph/nodes/qc.py src/film_pipeline/graph/subgraphs/qc.py`
- **Blast radius:** QC gate correctness — the version a validator evaluates can differ from the
  version the human gate reviewed; `src/film_pipeline/mcp/tools/helpers.py:184-187` and
  `src/film_pipeline/artifacts/store.py:516-519` provide two more "latest" rules for the same decision.
- **Candidate owner module:** the QC subsystem (one resolution helper) consuming a single
  version-resolution rule from `ArtifactStore`.
- **Extraction sketch:** Extract one `resolve_artifact(store, state, artifact_id)` used by both
  `src/film_pipeline/graph/nodes/qc.py` and `src/film_pipeline/graph/subgraphs/qc.py`, with the pinned-ref-first / latest-fallback
  order owned in one place. Guard test: run both paths against a state whose pinned ref is v1
  while v2 exists and assert they resolve the same version.
- **Prior art:** `documentation/reviews/arch-lens-dataflow.md:108` (previously uncited — A7 gap
  corrected). The coverage omission (A1) is corrected in §1.3.

### F-ARTIFACT-11 — `AssetEntry.kind` is a fourth kind vocabulary with live spelling drift and no validation (added after verification, M3)

- **Class:** O1
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** Asset kinds are a closed vocabulary; they should come from the same kind authority
  or have their own typed enum.
- **De-facto owners:**
  - `src/film_pipeline/artifacts/manifest.py:21` — free-form string with a comment as the only vocabulary —
    `kind: str  # reference_sheet, generated_clip, last_frame, mid_frame, audio_stem`
  - `src/film_pipeline/generation/executor_delivery.py:132-148` — the writer/classifier —
    `def _asset_kind(path: Path) -> str:` … `return "generated_clip"` (`:143`)
  - `src/film_pipeline/artifacts/manifest.py:41,43,49` — the invariant consumers —
    `if entry.kind == "generated_clip" and entry.active:` / `and existing.kind == "generated_clip"` / `if e.shot_id == shot_id and e.kind == "generated_clip" and e.active:`
  - `src/film_pipeline/schemas/_base.py:58` — the normative enum's conflicting spelling — `CLIP = "clip"`
- **Drift proof:** Existing divergence: the manifest vocabulary uses `"generated_clip"` while
  `ArtifactType.CLIP` is `"clip"` — the same concept, two spellings, and `ArtifactType.CLIP` has
  **zero** references in `src/`
  (`grep -rn "ArtifactType.CLIP\|ArtifactType.LAST_FRAME\|ArtifactType.MID_FRAME" src/` → 0 hits).
  There is no `AssetKind` enum and no validation on `AssetEntry.kind`; the "one active clip per
  shot" invariant is enforced only by string equality at `src/film_pipeline/artifacts/manifest.py:41-44`. Mutation scenario:
  change `_asset_kind` to return `"clip"` (matching `ArtifactType.CLIP`); `add_take` no longer
  deactivates the previous take and `active_take` returns `None`, so multiple takes become
  active — no test fails.
- **Reproduce:** `grep -rn "generated_clip\|\"kind\"\|\.kind ==" src/film_pipeline --include='*.py'`
- **Blast radius:** `src/film_pipeline/artifacts/manifest.py` take-selection invariants, `src/film_pipeline/generation/executor_delivery.py`,
  media/delivery asset selection; a drifted spelling silently breaks the one-active-take rule.
- **Candidate owner module:** `film_pipeline.artifacts.contract` — one `AssetKind` enum (or a
  registry-derived kind) shared by the manifest writer and readers.
- **Extraction sketch:** Add `AssetKind(StrEnum)` and type `AssetEntry.kind: AssetKind`; have
  `_asset_kind` return a member. Guard test: a membership test over every value `_asset_kind` can
  return plus the take-deactivation invariant.
- **Prior art:** New. (The audit's first revision marked `src/film_pipeline/artifacts/manifest.py` "Clean"; that was
  wrong and is corrected in §1.1.)

### F-ARTIFACT-12 — Read paths never validate the `artifact_id`, so an unvalidated MCP argument reaches the filesystem path builder (added after verification, M4)

- **Class:** O8 (no typed contract on the read-side id; caller passes a raw string and it is used
  to build a path)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** The id charset the writer enforces must be enforced on the read side too.
- **De-facto owners:**
  - `src/film_pipeline/artifacts/store.py:120` and `:217` — the **only** id validation, both write-side —
    `validate_artifact_id(meta.artifact_id)`
  - `src/film_pipeline/artifacts/store.py:435` and `:456` — read paths build the path from the raw id —
    `path = self._version_path(project_id, phase.value, artifact_id, version)`
  - `src/film_pipeline/mcp/tools/artifacts.py:57,75` — the MCP tool passes the argument straight through —
    `artifact_id = str(args.get("artifact_id", ""))` … `content = store.load(project_id, fp, artifact_id, version)`
  - `src/film_pipeline/artifacts/registry.py:47-53` — the rule that is bypassed — `def validate_artifact_id(artifact_id: str) -> None:`
- **Drift proof:** Reproduced path traversal with the intermediate phase directory present (which
  any real project has after a save):
  ```
  version path exists()? True | resolved: /tmp/probe12b-.../outside/versions/v001.json
  load(traversal) raised: ValidationError ... input_value={'pwned': True}
  ```
  The planted file **outside the storage root** was opened and parsed; its content is echoed in
  the validation error. `grep -rn "validate_artifact_id\|sanitize_artifact_id" tests/` → **0 hits**,
  so nothing pins read-side validation (drift 4). `from_string` accepting
  `artifact:script:../../etc/passwd:v1` while `validate_artifact_id` rejects it is reproduced in
  F-ARTIFACT-01.
- **Reproduce:**
  `.venv/bin/python -c "from film_pipeline.schemas.artifact import ArtifactRef; print(ArtifactRef.from_string('artifact:script:../../etc/passwd:v1').artifact_id)"`
  and `grep -rn "validate_artifact_id" src/film_pipeline --include='*.py'`
- **Blast radius:** every read path (`store.load`, `load_ref`, `load_envelope`, `load_metadata`),
  `src/film_pipeline/mcp/tools/artifacts.py` (`inspect_artifact`), `src/film_pipeline/app/services/_browse_ops.py`; a constrained
  file read outside the storage root for paths shaped `…/versions/vNNN.json`, plus file content
  leaked into validation errors. If any deployment treats the MCP tool boundary as untrusted,
  raise impact to 4 (Critical 16).
- **Candidate owner module:** `ArtifactStore` — validate the id at the read boundary
  (`_version_path`/`_artifact_dir`) exactly as `save` does.
- **Extraction sketch:** Call `validate_artifact_id(artifact_id)` (or resolve through
  `REGISTRY.spec_for`) at the top of `load`, `load_envelope`, `load_metadata`, `load_ref`, and
  `_artifact_dir`, so no path is built from an unvalidated segment. Guard test: assert
  `store.load(project, phase, "../../etc/passwd", 1)` raises `ValueError` and that no read path
  escapes the resolved root.
- **Prior art:** New (the first revision mentioned the charset only as a Medium side-note in
  F-ARTIFACT-01, with the wrong guard-test citation — verify-07 D1/M4).

### F-ARTIFACT-13 — `_UPSTREAM_CONTENT_SOURCES` is a fifth artifact-ref-key→phase vocabulary (added after verification, M5)

- **Class:** O1
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** The phase a ref belongs to should be derived from the ref/`FilmPhase` authority,
  not re-tabulated per consumer.
- **De-facto owners:**
  - `src/film_pipeline/schemas/_base.py:77-90` — the normative phase vocabulary — `class FilmPhase(StrEnum):`
  - `src/film_pipeline/artifacts/paths.py:14-26` — the phase→directory map — `PHASE_DIR_MAP: dict[str, str] = {`
  - `src/film_pipeline/graph/nodes/_context.py:329-338` — a parallel ref-key→phase table —
    `"constitution_ref": ("constitution", "constitution_content"),` … `"execution_brief_ref": ("shot_bible", "execution_brief_content"),`
- **Drift proof:** Mutation scenario: add or rename a phase in `FilmPhase`; the
  `_UPSTREAM_CONTENT_SOURCES` literals keep the old phase names and no test fails (nothing
  cross-checks the table against `FilmPhase`). The table also hard-codes which ref keys are
  injected, duplicating knowledge that `ArtifactRef` already carries in its `<phase>` segment.
- **Reproduce:** `grep -rn "_UPSTREAM_CONTENT_SOURCES\|PHASE_DIR_MAP\|class FilmPhase" src/film_pipeline --include='*.py'`
- **Blast radius:** `src/film_pipeline/graph/nodes/_context.py` prompt-context injection; a renamed phase silently
  drops upstream content from prompts.
- **Candidate owner module:** `ArtifactStore`/`ArtifactRef` (derive phase from the ref) with the
  consumer keeping only the content-key mapping.
- **Extraction sketch:** Replace the phase string in each entry with a phase derived from the ref
  (`ArtifactRef.from_string(ref).phase`) or validate the table against `FilmPhase` at import.
  Guard test: assert every phase literal in the table is a `FilmPhase` value.
- **Prior art:** New; `documentation/reviews/arch-lens-dataflow.md:85` discusses
  `_UPSTREAM_CONTENT_SOURCES` for the approval seam, not this vocabulary duplication.
- **§2 correction:** the inventory previously attributed this site to F-ARTIFACT-09; it is now
  correctly attributed to F-ARTIFACT-13.

---

### F-ARTIFACT-14 — Five closed-vocabulary fields are re-declared as bare `str` across `schemas/**` (`pacing_style`, `film_type`, `phase`, `next_action`, `mode`) (added post-verification)

- **Class:** O1 (one vocabulary re-spelled; O4 for the parallel declaration)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** A field that carries a closed vocabulary in one model (`Literal`/`StrEnum`) is a bare
  `str` in a sibling model, so the vocabulary is validated at one declaration and silently accepts
  anything at the other. `pacing_style` (H10) is one instance of a **five-field, 24-declaration**
  seam inside `schemas/**` — 13 declarations are bare `str` — and this schema layer is not named by
  the coverage table in §1.2 (`src/film_pipeline/schemas/execution_brief.py`, `src/film_pipeline/schemas/constraints.py`, `src/film_pipeline/schemas/scope_contract.py` are not
  listed there).
- **De-facto owners:**
  - `src/film_pipeline/schemas/constraints.py:61` — the only closed `pacing_style` declaration —
    `pacing_style: Literal["slow_cinema", "standard", "dynamic"] | None = Field(`
  - `src/film_pipeline/schemas/execution_brief.py:51` — bare `str`; the vocabulary lives only in the description —
    `pacing_style: str = Field(` / `default="standard", description="Pacing style: 'slow_cinema', 'standard', 'dynamic'."`
  - `src/film_pipeline/schemas/scope_contract.py:23` — bare `str` on the persisted forward scope contract —
    `pacing_style: str = Field(` / `default="standard",` / `description="Canonical pacing: 'slow_cinema', 'standard', or 'dynamic'.",`
  - `src/film_pipeline/schemas/constraints.py:57`, `src/film_pipeline/schemas/project.py:36` — `film_type` closed (`FilmType`) —
    `film_type: FilmType | None = Field(` / `film_type: FilmType = FilmType.NARRATIVE`
  - `src/film_pipeline/schemas/scope_contract.py:22` — the same field bare —
    `film_type: str = Field(default="narrative")`
  - `src/film_pipeline/schemas/_base.py:77`, `src/film_pipeline/schemas/approval.py:21,35,49`, `src/film_pipeline/schemas/artifact.py:60`,
    `src/film_pipeline/schemas/checkpoint.py:33` — `phase` closed (`FilmPhase`) — `class FilmPhase(StrEnum):` /
    `phase: FilmPhase`
  - `src/film_pipeline/schemas/artifact.py:24`, `src/film_pipeline/schemas/failure.py:27,70`, `src/film_pipeline/schemas/issue.py:17`,
    `src/film_pipeline/schemas/kb.py:48`, `src/film_pipeline/schemas/matrix_patch.py:41`, `src/film_pipeline/schemas/repair.py:41`,
    `src/film_pipeline/schemas/validation.py:75` — the same field bare — `phase: str`
  - `src/film_pipeline/schemas/generation.py:73-80` — `next_action` closed — `next_action: Literal[` … `"submit",
    "poll", "download", "validate", "wait_human", "stop"` — vs `src/film_pipeline/schemas/generation.py:43` —
    `next_action: str`
  - `src/film_pipeline/schemas/generation.py:24,57` — `mode` closed (`GenerationMode`) — `mode: GenerationMode` —
    vs `src/film_pipeline/schemas/budget.py:31` — `mode: str`
- **Drift proof:** Existing divergence **and** mutation scenario, both silent. **Existing
  (executed):** `ProjectConstraints(pacing_style="measured")` → `REJECTED (literal_error)` while
  `ExecutionBrief(pacing_style="measured")` and `StoryScopeContract(pacing_style="measured")` →
  `ACCEPTED`. The live producer `src/film_pipeline/agents/impl/structure_extractor_agent.py:59`
  (`pacing_style=str(data.get("pacing_style", "standard"))`) writes the LLM's raw string into the
  brief, `src/film_pipeline/graph/orchestrator_validators/brief.py:113` prices it with
  `avg_shot_duration_for(brief.pacing_style)`, and `src/film_pipeline/graph/scope_contract.py:125-126` silently maps
  every unrecognized value onto `STANDARD` — executed: `avg_shot_duration_for("measured") == 6.5 ==
  avg_shot_duration_for("standard")` — so a non-canonical brief is costed at standard pacing with no
  error path. `tests/unit/agents/test_impl_agents.py:603`
  (`assert brief.pacing_style == "measured"`) actively pins the out-of-vocabulary acceptance. The
  same asymmetry executes for the other four fields: `ProjectProfile(film_type="also_nonsense")` →
  `REJECTED (enum)` vs `StoryScopeContract(film_type="also_nonsense")` → `ACCEPTED`;
  `ApprovalRecord(phase="bogus")` → `REJECTED (enum)` vs `MatrixPatch(phase="bogus")` →
  `ACCEPTED`; `GenerationLedgerRow(next_action="bogus")` → `REJECTED (literal_error)` vs
  `ResumeToken(next_action="bogus")` → `ACCEPTED`; `GenerationLedgerRow(mode="bogus")` →
  `REJECTED (enum)` vs `SpendRecord(mode="bogus")` → `ACCEPTED`. **Mutation:** rename or extend the
  `src/film_pipeline/schemas/constraints.py:61` `Literal` (e.g. `"slow_cinema"` → `"slow"`); `src/film_pipeline/schemas/execution_brief.py:51` and
  `src/film_pipeline/schemas/scope_contract.py:23` keep accepting the old spelling and no test fails, because no test compares
  the declarations — `grep -rn "pacing_style" tests/` returns value-echo assertions only, and
  `tests/unit/agents/test_impl_agents.py:603` pins the divergence rather than the agreement.
- **Reproduce:**
```bash
cd ${REPO_ROOT}
grep -rnE "^    (pacing_style|film_type|phase|next_action|mode): " src/film_pipeline/schemas/ --include='*.py' | wc -l      # -> 24 declarations
grep -rnE "^    (pacing_style|film_type|phase|next_action|mode): str" src/film_pipeline/schemas/ --include='*.py' | wc -l # -> 13 bare str
UV_CACHE_DIR="$PWD/.uv-cache" uv run python - <<'PY'
from datetime import UTC, datetime

from pydantic import ValidationError

from film_pipeline.graph.scope_contract import avg_shot_duration_for
from film_pipeline.schemas.approval import ApprovalRecord
from film_pipeline.schemas.budget import SpendRecord
from film_pipeline.schemas.constraints import ProjectConstraints
from film_pipeline.schemas.execution_brief import ExecutionBrief
from film_pipeline.schemas.generation import GenerationLedgerRow, ResumeToken
from film_pipeline.schemas.matrix_patch import MatrixPatch
from film_pipeline.schemas.project import ProjectIdentity, ProjectProfile
from film_pipeline.schemas.scope_contract import StoryScopeContract

NOW = datetime.now(UTC)


def scope(**over):
    kw = dict(project_id="p", target_runtime_seconds=60, avg_shot_duration_seconds=6.5,
              target_scene_count=10, min_scene_count=8, target_shot_count=40,
              shots_per_scene_low=3, shots_per_scene_high=6)
    kw.update(over)
    return StoryScopeContract(**kw)


def ledger_row(**over):
    kw = dict(generation_request_id="r", generation_id="g", project_id="p", shot_id="s",
              mode="test", provider="prov", model="m", prompt_ref="pr")
    kw.update(over)
    return GenerationLedgerRow(**kw)


CASES = [
    ("ProjectConstraints ", "pacing_style=measured",
     lambda: ProjectConstraints(project_id="p", pacing_style="measured")),
    ("ExecutionBrief     ", "pacing_style=measured",
     lambda: ExecutionBrief(project_id="p", target_runtime_seconds=60, pacing_style="measured")),
    ("StoryScopeContract ", "pacing_style=measured", lambda: scope(pacing_style="measured")),
    ("ProjectProfile     ", "film_type=also_nonsense",
     lambda: ProjectProfile(identity=ProjectIdentity(project_id="p", slug="s", title="t"),
                            target_runtime_seconds=60, film_type="also_nonsense")),
    ("StoryScopeContract ", "film_type=also_nonsense", lambda: scope(film_type="also_nonsense")),
    ("ApprovalRecord     ", "phase=bogus",
     lambda: ApprovalRecord(approval_id="a", project_id="p", phase="bogus", action="approve",
                            approver_id="u", created_at=NOW)),
    ("MatrixPatch        ", "phase=bogus",
     lambda: MatrixPatch(patch_id="x", matrix_ref="r", phase="bogus")),
    ("GenerationLedgerRow", "next_action=bogus", lambda: ledger_row(next_action="bogus")),
    ("ResumeToken        ", "next_action=bogus",
     lambda: ResumeToken(resume_token="t", project_id="p", generation_id="g", graph_node="n",
                         last_safe_step="l", next_action="bogus", created_at=NOW)),
    ("GenerationLedgerRow", "mode=bogus", lambda: ledger_row(mode="bogus")),
    ("SpendRecord        ", "mode=bogus",
     lambda: SpendRecord(spend_id="s", project_id="p", generation_id="g", provider="prov",
                         amount_usd=1.0, mode="bogus", created_at=NOW)),
]
for label, arg, fn in CASES:
    try:
        fn()
        print(f"{label} {arg:24} ACCEPTED")
    except ValidationError as exc:
        print(f"{label} {arg:24} REJECTED ({exc.errors()[0]['type']})")
print("avg_shot_duration_for(measured) =", avg_shot_duration_for("measured"),
      "(standard =", avg_shot_duration_for("standard"), ")")
PY
```
  ```
  ProjectConstraints  pacing_style=measured    REJECTED (literal_error)
  ExecutionBrief      pacing_style=measured    ACCEPTED
  StoryScopeContract  pacing_style=measured    ACCEPTED
  ProjectProfile      film_type=also_nonsense  REJECTED (enum)
  StoryScopeContract  film_type=also_nonsense  ACCEPTED
  ApprovalRecord      phase=bogus              REJECTED (enum)
  MatrixPatch         phase=bogus              ACCEPTED
  GenerationLedgerRow next_action=bogus        REJECTED (literal_error)
  ResumeToken         next_action=bogus        ACCEPTED
  GenerationLedgerRow mode=bogus               REJECTED (enum)
  SpendRecord         mode=bogus               ACCEPTED
  avg_shot_duration_for(measured) = 6.5 (standard = 6.5 )
  ```
- **Blast radius:** `schemas/**` consumers: `src/film_pipeline/constraints/extractor.py:146` and
  `src/film_pipeline/graph/nodes/prep.py:179` (`updates["pacing_style"] = contract.pacing_style`),
  `src/film_pipeline/graph/state_schema.py:138` (`pacing_style: str`), `src/film_pipeline/agents/impl/structure_extractor_agent.py:59`,
  `src/film_pipeline/graph/orchestrator_validators/brief.py:113`, and the phase-bearing records
  (`MatrixPatch`, `KBContextPacket`, `IssueRecord`, `ValidationLedgerEntry`, `FailureDecision`)
  whose `phase` strings feed routing and prompt context. A user's pacing/film-type intent can be
  silently normalized to `standard`/`narrative`, changing the planned shot-density band and the
  `brief_runtime_inconsistent` gate outcome with no error.
- **Candidate owner module:** `schemas` — the shared-vocabulary block in `src/film_pipeline/schemas/_base.py` (the
  smallest correct owner; it already owns `FilmPhase`/`FilmType`/`GenerationMode`) declares
  `PacingStyle` and `NextAction` aliases and every model annotates with those names. This is the
  schema-contract cluster, not `ArtifactStore`.
- **Extraction sketch:** add `PacingStyle = Literal["slow_cinema", "standard", "dynamic"]` and
  `NextAction = Literal["submit", "poll", "download", "validate", "wait_human", "stop"]` beside the
  enums in `src/film_pipeline/schemas/_base.py`; annotate `src/film_pipeline/schemas/constraints.py:61`, `src/film_pipeline/schemas/execution_brief.py:51`, `src/film_pipeline/schemas/scope_contract.py:23`
  with `PacingStyle`; the eight `phase: str` sites with `FilmPhase`; `src/film_pipeline/schemas/scope_contract.py:22` with
  `FilmType`; `src/film_pipeline/schemas/budget.py:31` with `GenerationMode`; `src/film_pipeline/schemas/generation.py:43` with `NextAction`. Guard test:
  reflect over `SchemaBase` subclasses, group annotations by field name, and assert one identical
  type per name — allow-listing the same-name/different-domain fields measured and excluded here
  (`role`, `status`, `outcome`, `severity`). Migration risk to record: typing these fields starts
  rejecting values that are accepted today (`"measured"`; the bare phase literals passed into
  `MatrixPatch.phase` at `src/film_pipeline/graph/nodes/visual.py:536`, `src/film_pipeline/graph/nodes/qc.py:78`,
  `src/film_pipeline/graph/nodes/generation.py:88`), so normalize the producers first
  (`src/film_pipeline/constraints/extractor.py:146`, `src/film_pipeline/agents/impl/structure_extractor_agent.py:59`,
  `graph/scope_contract.normalize_pacing`) and repoint `tests/unit/agents/test_impl_agents.py:587,603`.
- **Prior art:** `documentation/reviews/prep-production-implementation-plan.md:112` asks to
  "Unify the **pacing vocabulary** (profile `pacing` ↔ code `pacing_style`) and make it
  profile-driven"; `documentation/reviews/hardcoded-values-inventory.md:35` records pacing as
  **DEAD — vocab mismatch**, and `:46-48` upgrades it to **RESOLVED** with the claim "canonical
  vocabulary centralized in `src/film_pipeline/schemas/constraints.py:61`" — that "centralized" claim is what this
  finding refutes at the schema layer. `reviews/adversarial-coverage.md` §H10 is the provenance;
  §H3 holds the wider alias-table divergence. **Ownership split (program-wide rule, applied
  exactly — one half per finding id, each cited rather than claimed):**
  **`audit/07` F-ARTIFACT-14 (this finding)** owns the **schema-declaration** half — a closed
  vocabulary typed `Literal`/`StrEnum` in one model and bare `str` in a sibling model, quantified
  here as **5 field names / 24 declarations / 13 bare `str`**, plus the `schemas`-layer reflection
  guard test. **`docs/modular-architecture/audit/03-config-profile-and-defaults.md` F-CFG-14** owns
  the **pacing mapping-rule** half — the two alias tables
  (`src/film_pipeline/constraints/_keywords.py:46`,
  `src/film_pipeline/graph/scope_contract.py:33`) and the silent `standard` fallback (re-scored to
  Medium 8 under this split); it already lists `src/film_pipeline/schemas/constraints.py:61` and
  `src/film_pipeline/schemas/execution_brief.py:51-53` as its owners, nominates `schemas` as the
  pacing owner and shares the `tests/unit/agents/test_impl_agents.py:603` pin, so those are **not**
  new here — only `src/film_pipeline/schemas/scope_contract.py:23`
  (`StoryScopeContract.pacing_style`) is new on the pacing side.
  **`docs/modular-architecture/audit/01-phase-model-and-transitions.md` F-PHASE-02** owns the
  **phase-vocabulary** half — `audit/01`'s coverage table already records
  (`docs/modular-architecture/audit/01-phase-model-and-transitions.md:95`) that "`FilmPhase` at
  `:77-90` is the only canonical *type*; every other site uses raw strings (**F-PHASE-02**)", so the
  eight `phase: str` sites above are that finding's evidence extended, not new here —
  `src/film_pipeline/schemas/artifact.py:24` specifically is also owned by `audit/07`
  **F-ARTIFACT-01**. The genuinely new and un-owned material here is the `film_type`, `next_action`
  and `mode` asymmetries, the one `src/film_pipeline/schemas/scope_contract.py:23` site, the 24/13
  quantification, and the `schemas`-layer guard test.
  `docs/modular-architecture/audit/12-post-delivery-constraints-budget.md` holds no pacing finding
  (`grep -n "pacing"` → 0); its F-BUD-05 covers `_NUMBER_WORDS` in
  `src/film_pipeline/constraints/_keywords.py`, not pacing.
- **Provenance:** uncovered by the adversarial coverage pass (`reviews/adversarial-coverage.md` §H10); added post-verification.

---

## 4. Ownership map

| Concern | De-facto owner(s) at HEAD | Single owner? | Guard test that pins it |
|---|---|---|---|
| On-disk project layout (filenames, relpaths) | `src/film_pipeline/artifacts/_layout.py` | Yes | `tests/unit/artifacts/test_storage_boundary.py` (per `documentation/artifact-store.md`); `test_store_v2.py::TestGoldenLayout` |
| Storage-root resolution + marker gate | `src/film_pipeline/artifacts/storage.py` | Yes | `tests/unit/artifacts/test_store_v2.py` root/marker tests |
| Atomic/durable/non-finite-safe writes | `src/film_pipeline/artifacts/serialization.py` | Yes | `tests/unit/artifacts/test_store_v2.py:478-483` (`test_checksum_rejects_non_finite`) |
| Phase→directory map | `src/film_pipeline/artifacts/paths.py:14` | Yes | Golden-layout test |
| Kind catalog (id → kind slug/schema_version/payload_model/mutable/renderer) | `src/film_pipeline/artifacts/registry.py` | Yes for the id axis | `tests/unit/artifacts/test_store_v2.py:178` (spec schema_version) |
| **Ref grammar (`artifact:<phase>:<id>:v<N>`)** | `src/film_pipeline/schemas/artifact.py` (N+I) + `src/film_pipeline/review/diff.py` (second format) + 2 wrappers | **No** | `tests/unit/artifacts/test_refs.py:11-14` pins the canonical round-trip; `tests/unit/review/test_diff.py:10-19` pins `_id_stem` separately → **F-ARTIFACT-01** |
| **artifact id charset** | `src/film_pipeline/artifacts/registry.py:33` + `src/film_pipeline/artifacts/store.py:120,217` (write only) | **No** | none — `grep -rn "validate_artifact_id" tests/` → 0 hits → **F-ARTIFACT-12** |
| **kind ↔ `ArtifactType` mapping** | `src/film_pipeline/schemas/_base.py` enum + `src/film_pipeline/artifacts/registry.py` ids + `src/film_pipeline/graph/nodes/_context.py` map | **No** | none (`grep -rn "_ARTIFACT_TYPE_BY_CLASS" tests/` → 0) → **F-ARTIFACT-02, F-ARTIFACT-08** |
| **asset kind vocabulary** | `src/film_pipeline/artifacts/manifest.py:21` + `src/film_pipeline/generation/executor_delivery.py:143` | **No** | none → **F-ARTIFACT-11** |
| **version number on write** | `src/film_pipeline/artifacts/store.py:141,238` (owner) + 5 hardcoded `version=1` + 4 local `latest+1` | **No** | `tests/unit/graph/test_wrapup_nodes.py:94-96` pins the store path only → **F-ARTIFACT-03** |
| **"latest version" rule** | `store.next_version` (scan `versions/`), `store.latest_version` (meta.json), `mcp/tools/helpers._latest_artifact_version` (meta.json) | **No** | none for the three agreeing → **F-ARTIFACT-03, F-ARTIFACT-10** |
| **QC artifact resolution** | `src/film_pipeline/graph/nodes/qc.py:149-158` (pinned) vs `src/film_pipeline/graph/subgraphs/qc.py:184-188` (latest) | **No** | none → **F-ARTIFACT-10** |
| **payload schema generation (`schema_version`) + migrations** | `src/film_pipeline/artifacts/registry.py:75,229` (N) + `src/film_pipeline/artifacts/store.py:461-479` (I, immutable only) | **No** | `tests/unit/artifacts/test_store_v2.py:141-149` immutable only → **F-ARTIFACT-04, F-ARTIFACT-05** |
| **meta/index/marker format versions** | `src/film_pipeline/artifacts/envelope.py:134,175`, `src/film_pipeline/artifacts/storage.py:36` written, never gated | **No** | none → **F-ARTIFACT-04** |
| **checksum** | `src/film_pipeline/artifacts/envelope.py:61` (compute) + `src/film_pipeline/artifacts/store.py:683` (verify on envelope read) | Partial | `tests/unit/artifacts/test_store_v2.py:128,478`; meta/index checksum unverified → **F-ARTIFACT-05** |
| **artifact status transitions** | `src/film_pipeline/artifacts/store.py:558-591` (approve/supersede) + `save` pre-approval + `save_mutable` | **No** | `test_readability.py::test_approve_phase_marks_artifacts_approved_and_fills_deliverables` → **F-ARTIFACT-06** |
| **`GenerationStatus` lifecycle** | `src/film_pipeline/generation/ledger.py:199` + `src/film_pipeline/generation/executor.py` + `src/film_pipeline/mcp/tools/generation/dispatch.py` | **No** | `tests/unit/generation/test_ledger.py:108-124` pins permissiveness, not a transition law → **F-ARTIFACT-07** |
| **ref-key→phase binding for prompt context** | `src/film_pipeline/graph/nodes/_context.py:329-338` vs `src/film_pipeline/schemas/_base.py:77` / `src/film_pipeline/artifacts/paths.py:14` | **No** | none → **F-ARTIFACT-13** |
| **`ValidationStatus`** | `validation/thresholds.py:score_to_status` (score→status) + `src/film_pipeline/validation/consensus.py:88` (aggregate) | Yes, per sub-concern | `tests/unit/validation/` threshold/consensus tests |
| Registry *entry* schemas (agent/provider/validator/model) | `schemas/registries/**` | Yes, distinct concern | registry schema tests — **not** part of this cluster's findings |

## 5. Clean concerns (single-owner, with the guard that pins them)

- **Canonical ref parse/format round-trip.** `ArtifactRef` is the only type that parses the full
  ref; `tests/unit/artifacts/test_refs.py:11-14` pins the round trip and `:20-33` pins rejection of
  3-segment forms (`"artifact:script:v1"`). Clean *as a parser*; the leak is the second formatter
  (F-ARTIFACT-01) and the missing read-side id validation (F-ARTIFACT-12).
- **Immutable version numbering.** `ArtifactStore.next_version` scans `versions/` and is the only
  writer of `vNNN.json`; `tests/unit/artifacts/test_store_v2.py:73` and
  `tests/unit/graph/test_wrapup_nodes.py:94-96` pin v1→v2 increments. Clean for the immutable path.
- **Checksum computation and immutable verification.** `payload_checksum` is defined once
  (`src/film_pipeline/artifacts/envelope.py:61`) and verified in `_read_envelope` (`src/film_pipeline/artifacts/store.py:683`); pinned by
  `tests/unit/artifacts/test_store_v2.py:128` and `:478`. Clean for envelope reads.
- **Storage boundary.** `documentation/artifact-store.md` declares `film_pipeline.artifacts` the
  only component that knows the on-disk layout, and `tests/unit/artifacts/test_storage_boundary.py`
  enforces it (no outside import of `_layout`/`serialization`/`paths`). Clean.
- **Renderer selection.** `src/film_pipeline/artifacts/store.py:762-763` states the registry owns renderer selection
  ("there is no second table here to drift out of sync with the kind slugs"), and
  `_renderer_for` delegates to `REGISTRY.renderer_for` (`src/film_pipeline/artifacts/store.py:770-772`). Clean.
- **`ValidationStatus` scoring.** `src/film_pipeline/validation/thresholds.py:12-29` maps score→status in one place;
  `src/film_pipeline/validation/consensus.py:88-98` aggregates separately (a different sub-concern). No duplication
  found within this cluster's scope.

## 6. Candidate module boundary — artifact-contract owner

**Proposed module:** `film_pipeline.artifacts.contract` (single responsibility: *own the artifact
reference/kind vocabulary and its cross-package contract*). Non-goals: it does **not** know
on-disk layout, does **not** write files, and does **not** own the payload models.

### 6.1 What the existing storage owner already covers (do not rebuild)

`documentation/artifact-store.md` ("One owner for storage") and `artifacts/**` already own,
single-handedly and with guard tests:

1. On-disk layout and relpaths — `src/film_pipeline/artifacts/_layout.py:38-55`, guarded by
   `tests/unit/artifacts/test_storage_boundary.py`.
2. Root resolution + marker gate — `src/film_pipeline/artifacts/storage.py:82-165`.
3. Atomic/durable/non-finite-safe writes — `src/film_pipeline/artifacts/serialization.py:28-102`.
4. Phase→directory map — `src/film_pipeline/artifacts/paths.py:14-26`.
5. Kind catalog and payload-model wiring — `src/film_pipeline/artifacts/registry.py:69-221`.
6. Immutable version numbering — `src/film_pipeline/artifacts/store.py:511-514`; mutable revision count —
   `src/film_pipeline/artifacts/store.py:233-238`.
7. Checksum compute/verify for envelope reads — `src/film_pipeline/artifacts/envelope.py:61-81`,
   `src/film_pipeline/artifacts/store.py:683-689`.
8. Immutable `SchemaTooNewError` + migration chaining — `src/film_pipeline/artifacts/store.py:461-479`,
   `src/film_pipeline/artifacts/registry.py:237-252`.
9. `approve`/`supersede` — `src/film_pipeline/artifacts/store.py:558-591`.
10. Renderer lookup — `src/film_pipeline/artifacts/registry.py:112-115`.

### 6.2 What leaks out of that owner (the case for a distinct contract module)

**Scope narrowed per verify-07 §C5.** Most of the first revision's "leaks" are defects *inside*
`src/film_pipeline/artifacts/store.py`, not cross-module leaks; a distinct module is justified only for concerns
genuinely consumed outside `artifacts/**`.

Genuinely shared → `artifacts.contract`:

| Leak | Evidence |
|---|---|
| The ref's **derived/stem form** is formatted outside the ref type | `src/film_pipeline/review/diff.py:70` |
| The ref's **id-charset** is not on the ref type and is enforced write-only | `src/film_pipeline/artifacts/registry.py:33`, `src/film_pipeline/artifacts/store.py:120,217`; reads build paths raw (`src/film_pipeline/artifacts/store.py:435,456`) |
| The **kind↔type vocabulary** is triple-defined and unenforced | `src/film_pipeline/schemas/_base.py:27-74`, `src/film_pipeline/artifacts/registry.py:131-217`, `src/film_pipeline/graph/nodes/_context.py:300-312` |
| The **asset kind vocabulary** is a free-form string | `src/film_pipeline/artifacts/manifest.py:21`, `src/film_pipeline/generation/executor_delivery.py:143` |
| The **ref-key→phase binding** is re-tabulated | `src/film_pipeline/graph/nodes/_context.py:329-338` |

Intra-owner defects → fix in place, nominate `ArtifactStore` / `GenerationLedgerManager`:

| Leak | Evidence | Owner |
|---|---|---|
| **Version-on-write policy** re-derived at 9 call sites | 5× `version=1`, 4× `_latest_artifact_version()+1` (inventory §2) | `ArtifactStore` (F-03) |
| **"latest version"** has three rules / two sources | `src/film_pipeline/artifacts/store.py:511-514` vs `:516-519` vs `src/film_pipeline/mcp/tools/helpers.py:184-187`; prior art `arch-lens-dataflow.md:71` | `ArtifactStore` (F-03, F-10) |
| **Schema-generation policy** on eleven declarations, three write-only | `src/film_pipeline/artifacts/envelope.py:94,134,175`, `src/film_pipeline/schemas/_base.py:273,280`, `src/film_pipeline/artifacts/registry.py:75`, `src/film_pipeline/artifacts/storage.py:36`, `src/film_pipeline/artifacts/_layout.py:54-55`, `src/film_pipeline/schemas/registries/validator_registry.py:29`, `src/film_pipeline/schemas/runtime_state.py:30,48`, `src/film_pipeline/generation/executor_delivery.py:95` | `ArtifactStore` (F-04) |
| **Read-time enforcement** is per-path (mutable/meta/list bypass) | `store.py:298,307,449-455,546,551,497-500` vs `:438,459,461` | `ArtifactStore` (F-05) |
| **Kind resolution on read** fabricates instead of refusing | `src/film_pipeline/artifacts/store.py:657-661` | `ArtifactStore` (F-09) |
| **Artifact status** invariant bypassed by pre-approved saves | `src/film_pipeline/artifacts/store.py:177` vs `:285`; `src/film_pipeline/mcp/tools/_profile_change.py:429,452` vs `src/film_pipeline/artifacts/store.py:652-653` | `ArtifactStore` (F-06) |
| **`GenerationStatus`** has no transition law and two writer modules | `src/film_pipeline/generation/ledger.py:199-217`; `src/film_pipeline/generation/executor.py`; `src/film_pipeline/mcp/tools/generation/dispatch.py` | `GenerationLedgerManager` (F-07) |

### 6.3 Public contract of the proposed owner

- `ArtifactRef` (re-exported from `schemas`) + `stem()`.
- `type_for(artifact_id, payload) -> ArtifactType` (no silent `SCRIPT`).
- `AssetKind` enum + `kind_for_asset(path)`.
- `phase_for_ref_key(ref_key) -> FilmPhase` (or a validated table).
- `kind_spec_for(artifact_id) -> KindSpec` (raising, used by all read and write paths).

**Dependency law:** `schemas` must remain importable by `artifacts` (today `artifacts` imports
`schemas`), so the `ArtifactRef` **model** stays in `src/film_pipeline/schemas/artifact.py`; the contract module owns
the *catalog and shared vocabulary* and may import both `schemas` and `artifacts.registry`. The
resulting edge set is `graph|mcp|post|review|generation → artifacts.contract → {schemas,
artifacts.registry}` and is acyclic. The read-enforcement, status, and version defects stay in
`ArtifactStore`/`GenerationLedgerManager`; moving them into `contract` would be a rename, not a
distinct owner (AGENTS.md: no abstractions without a current concrete need).

### 6.4 Extraction order (each step leaves `make ci-check` green)

1. `ArtifactStore`: validate the id on every read path and require `_read_checked_envelope` for
   mutable/metadata/list reads (F-ARTIFACT-05, F-ARTIFACT-12).
2. `ArtifactStore`: `save_candidate(...)`; delete the 9 caller-side version derivations and unify
   the "latest version" rule (F-ARTIFACT-03).
3. `GenerationLedgerManager`: transition table + named status methods (F-ARTIFACT-07).
4. `ArtifactStore`: status transition/invariant table (F-ARTIFACT-06) and delete `_safe_spec`
   (F-ARTIFACT-09).
5. New `film_pipeline.artifacts.contract` module: `ArtifactRef.stem()`, kind↔type resolver with the missing enum values,
   `AssetKind`, and the validated ref-key→phase table (F-01, F-02, F-08, F-11, F-13).
6. QC: one `resolve_artifact` shared by `src/film_pipeline/graph/nodes/qc.py` and `src/film_pipeline/graph/subgraphs/qc.py`
   (F-ARTIFACT-10).

## 7. Unverified hypotheses (excluded from findings)

- Whether any *external* MCP client keys behavior on the persisted `artifact_type` value (which
  would raise F-ARTIFACT-02's impact above 4) was **not** verified — no external client is in this
  repo.
- The exact upstream origin of the malformed `"artifact:shot_matrix:v1"` docstring example
  (`src/film_pipeline/artifacts/matrix_projection.py:33`) is **not** verified; only that it contradicts the parser is.
- F-ARTIFACT-12's traversal was reproduced reading a JSON file shaped `…/versions/vNNN.json`
  outside the storage root. Whether an attacker can reach such a shaped file in a real deployment
  was **not** enumerated; the impact is left at 3 for that reason.
- `src/film_pipeline/schemas/registries/agent_registry.py`, `src/film_pipeline/schemas/registries/model_registry.py`, `src/film_pipeline/schemas/registries/provider_registry.py` were read
  only for cluster relevance; a full parallel-registry audit of those three is outside this
  cluster and is **not** claimed here.
