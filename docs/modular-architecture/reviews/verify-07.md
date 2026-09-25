# verify-07 — Adversarial verification of `audit/07-artifact-refs-and-schemas.md`

- **Repo:** `${REPO_ROOT}`
- **Branch / commit verified:** `modular-app` @ `fb85baa` (working tree clean; `git log --oneline -1` → `fb85baa Merge pull request #29 …`)
- **Audit under review:** `docs/modular-architecture/audit/07-artifact-refs-and-schemas.md`
- **Methodology applied:** `docs/modular-architecture/00-methodology-and-quality-bar.md` §1.4–§1.6, bar A (esp. A2/A3/A6/A7).
- **Verifier:** independent agent; no authorship of the audited file. No file under `src/`, `tests/`, or the audit was modified.
- **Reproductions:** throwaway probes run with `.venv/bin/python` and `/tmp/verify07.py`; all writes under `/tmp` only.

**Verdict convention used here** (state explicitly so the counts are unambiguous):

- **CONFIRMED** — anchors/quotes resolve at HEAD, the O-class is defensible, the drift proof holds (or a stronger equivalent proof exists that I reproduced), and severity is within one band of the audit's.
- **DOWNGRADED** — the seam is real but the finding as written contains a false/unreproducible claim, an overstated premise, or an overstated severity; the corrected severity is stated.
- **REJECTED** — the core claim is false or unverifiable.

**Counts: 5 CONFIRMED, 4 DOWNGRADED, 0 REJECTED.** The file does **not** meet bar A2/A3 as written; the corrected evidence below is sufficient for A2 after the author applies the disputes in §D.

---

## A. Anchor / quote spot-check (does the quoted text exist at HEAD?)

Every anchor I checked resolves, except the off-by-one sites noted per finding. Spot-check of the quotes:

| Anchor | Quote present? |
|---|---|
| `schemas/artifact.py:28` | ✅ `return f"artifact:{self.phase}:{self.artifact_id}:v{self.version}"` |
| `schemas/artifact.py:12,22-24,31-51` | ✅ |
| `review/diff.py:61-70` | ✅ `_id_stem`; `:70` = `return f"artifact:{parsed.phase}:{parsed.artifact_id}"` |
| `artifacts/registry.py:33,75,100-107,118-123,131-194,244-250` | ✅ |
| `artifacts/store.py:128,141,177,238,285,298,307,438,449,459,461-479,497-500,511-514,546,551,558-591,652-653,657-661,683-689,701-706` | ✅ |
| `artifacts/envelope.py:61,94-99,134,148,175` | ✅ |
| `artifacts/storage.py:35,36` | ✅ `LAYOUT_VERSION = 2` / `MARKER_SCHEMA_VERSION = 1` |
| `artifacts/_layout.py:52-55,124-134` | ✅ |
| `schemas/_base.py:23-24,27-74,273` | ✅ (enum has exactly 45 members) |
| `graph/nodes/_context.py:300-312,315-321,324-326` | ✅ |
| `graph/nodes/qc.py:88,109,152-154,180` | ✅ |
| `graph/nodes/visual.py:498` | ✅ |
| `generation/ledger.py:199-204,211,216,228,250-258` | ✅ |
| `mcp/tools/_profile_change.py:366,429,452` | ✅ |
| `mcp/tools/helpers.py:184-187,202` | ✅ |
| tests (`test_refs.py:11-14,20-33`, `test_diff.py:10-19`, `test_store_v2.py:73,128,141-149,178,202,478-483,661`, `test_post.py:299`, `test_wrapup_nodes.py:94-96`, `test_ledger.py:108-124`, `test_readability.py:145`) | ✅ all resolve |
| prior art (`audit-findings.md:45,83,85,168,170`; `storage-upgrade-review.md:27-29,100`; `clean-code-refactor/review-findings.md:36,55`) | ✅ all resolve and say what the audit says they say |

Off-by-one anchors found (not fatal, but they violate §1.6.1's "points at the defining/enforcing line"): F-ARTIFACT-03's four "local `latest+1`" sites are cited as `_shared.py:124`, `shot.py:71`, `planning.py:74`, `index_files.py:83`; the actual `_latest_artifact_version(...) + 1` call lines are **125, 72, 75, 84** respectively (the cited lines are the opening `next_version = (` / `version = (` of the two-line statement). F-ARTIFACT-04 cites `store.py:166`/`:279` as where `ArtifactCurrentMeta.schema_version` is "written"; those are the constructor openings — the serializing writes are `store.py:191` and `:291`.

---

## B. Per-finding verdicts

### F-ARTIFACT-01 — second formatter + wrappers; id charset enforced only on write

- **Verdict: CONFIRMED** (severity corrected upward within the same band).
- **O-class:** O1 is defensible for the `review/diff.py:70` formatter (a second, version-less ref form with normative content, per §1.3 it is *not* mere convenience duplication). The two `_parse_*` wrappers are thin delegations, not duplicated models; a stricter label would be O1 (formatter) + O8 (id-charset contract is not on `ArtifactRef`). Not a rejection.
- **Drift proof:** Valid. I confirmed the asymmetry the finding is built on:
  ```
  $ .venv/bin/python -c "from film_pipeline.schemas.artifact import ArtifactRef;
  from film_pipeline.artifacts.registry import validate_artifact_id as v;
  r=ArtifactRef.from_string('artifact:script:../../etc/passwd:v1'); print(repr(r.artifact_id));
  ... validate -> REJECTED"
  parsed id='../../etc/passwd'; validate_artifact_id: REJECTED
  parsed id='Bad-Id';          validate_artifact_id: REJECTED
  ```
  `schemas/artifact.py:41-51` accepts any non-empty id; `artifacts/registry.py:47-53` rejects it. `grep -rn "validate_artifact_id\|sanitize_artifact_id" tests/` → **zero hits**, so no test pins the agreement: drift likelihood **4**, not 3. `artifacts/matrix_projection.py:33` really does document the 3-segment `"artifact:shot_matrix:v1"`, which `from_string` rejects (`schemas/artifact.py:34`).
- **Severity recompute:** impact 2 × drift 4 = **8 (Medium)**. The audit's `2 × 3 = 6` is understated but same band; not a downgrade.
- **Candidate owner:** `artifacts.contract` is reasonable here — this is the one finding whose concern (ref codec) is genuinely shared by `schemas`/`review`/`graph`/`mcp` and not already inside the store.
- **Prior art:** Correct; `audit-findings.md:85` says what is quoted and the specific `store`↔`paths` duplication is indeed fixed at HEAD (`store.py:78` uses `paths.PHASE_DIR_MAP`).
- **Dispute D1:** the ownership map (§4, line 531) says *"`test_refs.py:20-33` shows `from_string` accepts ids `validate_artifact_id` rejects"*. That is **false**: `tests/unit/artifacts/test_refs.py:20-33` is `test_malformed_refs_are_rejected` and asserts only `ValueError` for malformed refs; it contains no invalid-charset-but-4-segment case. The asymmetry is real (I reproduced it) but the cited guard test does not exist.

### F-ARTIFACT-02 — `_ARTIFACT_TYPE_BY_CLASS` values the enum rejects; silent `SCRIPT` fallback

- **Verdict: CONFIRMED** (one sub-claim false; see D2).
- **Anchors/class:** All resolve; `graph/nodes/_context.py:309-310` are the two dead values, `:319-321` the fallback, `artifacts/registry.py:131-194` the other vocabulary. O1 fits.
- **Drift proof (reproduced):**
  ```
  F02 CostEstimate: type name = CostEstimate | is dict? False | inferred = script
  F02 ConsensusReport: type name = ConsensusReport | inferred = script
  F02 ArtifactType('cost_estimate_bom') -> ValueError (confirmed)
  F02 ArtifactType('consensus_report') -> ValueError (confirmed)
  ```
  The live consequences are real: `qc.py:109` and `:180` pass a `ConsensusReport` model (builder returns a model, `validation/consensus.py:25`), `qc.py:88` passes the literal `"consensus_report"` (`_agent_artifacts.py:37` raises and falls back), and `visual.py:498` passes a `CostEstimate`. All four persist `artifact_type=script` into the immutable envelope.
- **Severity recompute:** impact 4 × drift 4 = **16 (Critical)** — unchanged. `grep -rn "_infer_artifact_type\|_ARTIFACT_TYPE_BY_CLASS" tests/` → zero hits, so nothing fails if a site changes (drift 4).
- **Candidate owner:** reasonable (a shared type resolver is a real cross-module contract).
- **Prior art:** Correct; `clean-code-refactor/review-findings.md:36` is a style nit and `:55` is the unrelated `_preferred_providers` fallback.
- **Dispute D2:** the finding states `visual.py:498`'s object *"is a dict from `result.get("cost_estimate")`, so `type(artifact).__name__` is `"dict"` → `SCRIPT`"*. **False.** `agents/impl/gen_planner_agent.py:11,66` build a `CostEstimate` pydantic model, and the probe prints `type name = CostEstimate | is dict? False`. The *outcome* (`SCRIPT`) still holds — but via the dead `"cost_estimate_bom"` map value at `_context.py:309`, not via a dict. The mechanism must be corrected.

### F-ARTIFACT-03 — version numbering re-derived at 9 sites

- **Verdict: DOWNGRADED → Medium (impact 2 × drift 4 = 8)** (audit: High 12).
- **Anchors/class:** All write-site anchors resolve (`post/subtitle_agent.py:102`, `post/delivery_packaging_agent.py:171`, `post/assembly_agent.py:126`, `mcp/tools/validation.py:191`, `generation/ledger.py:228`; `helpers.py:184-187`). The four "local `latest+1`" anchors are off by one (see §A). O5 fits.
- **Why the downgrade:** the concern is **inert at HEAD**, by the audit's own admission ("all are silently discarded"). `store.py:141` unconditionally overwrites `meta.version` with `self.next_version(...)`, and `_save_mutable_locked` (`store.py:233-238`) derives its revision from the file. So none of the 9 caller-side derivations can produce divergent behavior today; there is a single effective writer. §1.5 impact 3 requires "wrong internal behavior" — none occurs. The audit's "second, already-true divergence" (two rules reading different sources) is not an observed divergence: in every tested/normal state `meta.json` `current_version` == `max(versions/)`. This is a latent-policy duplication (impact 2), not a live seam.
- **Drift proof as a mutation scenario:** §1.6.3(b) makes it formally admissible; drift likelihood 4 stands (no test asserts that `meta.version` is ignored).
- **Candidate owner:** `ArtifactStore` itself is the honest owner; proposing `artifacts.contract` for this is weak (see C5).
- **Prior art:** `audit-findings.md:45,168` verified. **A7 gap:** `documentation/reviews/arch-lens-dataflow.md:71` already states *"Pick one source of truth; the current design pays for both and gets neither"* about latest-version resolution, and `:108` documents the sequential-vs-parallel QC resolution split. F-ARTIFACT-03 does not cite it (see M2).

### F-ARTIFACT-04 — `schema_version` overloaded across "eight" axes; meta/index write-only

- **Verdict: CONFIRMED** (severity 3 × 4 = 12 High holds), with disputes.
- **Anchors:** `schemas/_base.py:273`, `registry.py:75`, `envelope.py:94-99,134,175`, `storage.py:36`, `_layout.py:54-55`, `validator_registry.py:29` all resolve with the quoted text. `storage.py:108` reads the marker `schema_version` and `storage.py:140` compares only `layout_version`, so the marker's schema axis is also write-only — a third unvalidated axis the drift proof omits.
- **Drift proof:** Valid in substance. `ArtifactCurrentMeta.schema_version` (`envelope.py:134`) and `ArtifactIndex.schema_version` (`envelope.py:175`) are written (`store.py:191,291,414`) and never compared; the only `schema_version` comparisons in `src/` are `store.py:465/469` and `app/_persistence.py:110` (grep-confirmed). `tests/unit/artifacts/test_store_v2.py:202,661` assert only the written index value `1`. Mutation scenario holds.
- **Class:** O1 is a stretch ("one name, several meanings" is not "one model defined twice"); O8 (missing typed contract for the axes) is more precise. Not a downgrade.
- **Disputes D3:** (a) the title/document says "**eight** distinct axes", but the audit's own reproduce command surfaces more: `schemas/runtime_state.py:30` and `:48` (`ProjectRecord`/`GraphStateSnapshot` int), `schemas/_base.py:280` (`MutableSchemaBase` string), `schemas/constraints.py:148` pop, and — inside the generation artifact path the audit itself scopes — `generation/executor_delivery.py:95` `"schema_version": 1` in the take sidecar, which is written by `write_media_sidecar` (`artifacts/project_storage.py:214`) and has **no reader** in `src/`. The count must be fixed or the list explicitly scoped. (b) `store.py:166`/`:279` are constructors, not the writes.

### F-ARTIFACT-05 — `SchemaTooNewError`/checksum enforcement is path-dependent

- **Verdict: CONFIRMED** (severity recomputed **upward**: impact 4 × drift 4 = **16 Critical**; audit said High 12).
- **Anchors/class:** `store.py:461-468` checked reader, `:438`/`:459` sole callers (grep-confirmed), `:298`/`:307` unchecked mutable reads, `:546`/`:551` unchecked metadata reads, `:497-500` meta.json list path, `:683-689` checksum verify, `envelope.py:148` `ArtifactCurrentMeta.checksum`. O2 fits exactly.
- **Drift proof (reproduced):**
  ```
  F05 load_mutable(schema_version=2): NO ERROR -> mutable bypass CONFIRMED
  F05 load_envelope(mutable, v2): NO ERROR -> audit 'would raise' is FALSE
  F05 load_envelope(immutable, v2) raised SchemaTooNewError (immutable check works)
  ```
  The audit's own guard-test citation (`test_store_v2.py:141-149`) exercises only the immutable `versions/vNNN.json` path, so **no test fails** for the mutable/meta/list paths: drift likelihood is 4, not 3. The meta/index checksum gap is equally real (`_read_meta_file` at `store.py:701-706` returns raw JSON and never validates `ArtifactCurrentMeta.checksum`).
- **Candidate owner:** weak — this defect lives entirely inside `artifacts/store.py`; a "contract" module would not be a distinct module, just a move (see C5).
- **Prior art:** `storage-upgrade-review.md:27-29` quote verified verbatim; the audit's claim that it holds only for the immutable path is correct.
- **Dispute D4:** the finding says the same mutable file *"read through `store.load_envelope` (`store.py:449`) would raise"*. **False and self-contradicting:** `store.py:449-455` routes mutable kinds to `load_mutable_envelope` → `_read_envelope` (`:307`), which has no schema check. My probe shows no error. The contrast must be drawn against an *immutable* envelope (`store.load_envelope` on `cost_estimate` does raise).

### F-ARTIFACT-06 — two APPROVED writers, different side effects; REJECTED/ARCHIVED unreachable

- **Verdict: CONFIRMED** (High 9; drift arguably 4 → 12, still High).
- **Anchors:** `store.py:558-591`, `:177`, `:285`, `:652-653`; `_profile_change.py:429`/`:452`; `schemas/_base.py:23-24` — all resolve. `grep -rn "_record_deliverable"` shows the single call at `store.py:653`; `_save_locked` (`:137-198`) never calls it. `grep -rn "REJECTED\|ARCHIVED"` returns only `schemas/_base.py:23-24` plus the unrelated `schemas/repair.py:60` string, as claimed.
- **Drift proof:** The existing divergence (APPROVED via `save()` gets no `deliverables/` entry while `approve()` does) is real. No test pins the cross-path agreement (`test_readability.py:145` covers only `approve`). Drift 3 is defensible; 4 also defensible.
- **Class dispute D5:** O3 ("one logical state written by 2+ modules with no single writer") does not fit: `artifacts/store.py` *is* the single writer of `meta.json`; `_profile_change.py` only passes a status through `save()`. The precise class is **O2** (the APPROVED⇒deliverable invariant is enforced in one path, `_transition_status_locked`, and bypassed in `_save_locked`) or O5. Reclass, keep severity.
- **Candidate owner:** weak for the same reason (intra-store); the transition table can live in `ArtifactStore`.
- **Prior art:** `audit-findings.md:83` verified; the "fixed at HEAD" statement about `approve`/`supersede` is accurate.

### F-ARTIFACT-07 — `GenerationStatus` has no transition law; two writer modules

- **Verdict: DOWNGRADED → High (impact 4 × drift 3 = 12) until the drift proof is replaced.** (audit: Critical 16)
- **Anchors/counts:** `grep -rn "update_row(" src/film_pipeline` gives exactly the 10 call sites and 8 status-bearing sites across 2 modules that the audit lists (`executor.py:196,257,293,399`; `dispatch.py:31,100,172,239,272,295`); `ledger.py:199-204,211,216,250-258`; `dispatch.py:182-196`. All ✓.
- **Why the downgrade — the stated drift proof is falsified by execution:**
  ```
  F07 cost=5 COMPLETED->CANCELLED estimate 0->0 changed=False; ->RUNNING 5.0 changed=True
  ```
  The audit claims `update_row(..., status=CANCELLED)` on a `COMPLETED` row changes `estimate_total_cost` *"because the row is no longer terminal"*. `CANCELLED` **is** in the terminal set (`generation/ledger.py:126-131`), so the total is unchanged. The finding's headline consequence is false as written.
- **The seam is nevertheless real and I supply a valid proof:** `update_row` accepts `COMPLETED → RUNNING` (illegal, non-terminal) and the total goes `0 → 5.0`, corrupting spend accounting; no test fails (`test_ledger.py:108-124` only asserts PREPARED→RUNNING is accepted). With that proof, impact 4 × drift 4 = 16 stands — but the finding cannot ship on its current proof (§1.6.3).
- **Class dispute D6:** O3 does not fit (the ledger representation has a single writer, `_persist`). This is **O6** (one generation lifecycle implemented twice: graph executor vs MCP dispatch) or O2 (no transition enforcement). Reclass required.
- **Additional evidence problem:** "the provider-status vocabulary is mapped onto `GenerationStatus` twice: `dispatch.py:182-196` (`_generation_status`) and `executor.py:200`/`:296`/`:402`". The executor lines are bare `status=GenerationStatus.RUNNING/COMPLETED/FAILED` literals, not a provider-status mapping; only `dispatch.py:182-196` maps `ProviderJobStatus → GenerationStatus`. The claim of a *second mapping* is unsupported.
- **Candidate owner:** `GenerationLedgerManager` / a `generation`-local transition table is more distinct than `artifacts.contract`; the audit's own hedge ("or a dedicated `generation.ledger_status` owner") is the better half.

### F-ARTIFACT-08 — kind registry vs `ArtifactType`: 8-id / 3-id mismatch

- **Verdict: DOWNGRADED → Medium (impact 2 × drift 4 = 8)** (audit: High 12).
- **Reproduce command:** the AST script in the finding is *reproducible and matches its numbers*: `registry-only: [consensus_report, cost_estimate, execution_brief, project_profile, scope_contract, shot_matrix, story_bible, subtitles]` (8) and `enum-only: [checklist…]` → `['clip','last_frame','mid_frame']` (3). So the headline count is not fabricated.
- **Why the downgrade:** the *premise* overstates debt. `graph/nodes/_context.py:300-312` shows deliberate many-kinds→one-type projection (`StoryBible → script`, `ProjectProfile → project_config`, `MasterFilmMatrix → shot_bible`), i.e. `ArtifactType` is intentionally coarser than the registry id set. Treating every set difference as a "mismatch that nothing enforces" misreads the design; only the map values that *no* enum member can hold (`cost_estimate_bom`, `consensus_report`) are actual defects — and those are F-ARTIFACT-02, which the audit already files. Impact 2, not 3.
- **False support for the blast radius (D7):** the finding says `clip`/`last_frame`/`mid_frame` *"are declared (and used in `reference_generation`)"*. `grep -rn "ArtifactType.CLIP\|ArtifactType.LAST_FRAME\|ArtifactType.MID_FRAME" src/` → **zero hits**; `grep -rn "clip\|last_frame\|mid_frame" src/film_pipeline/mcp/tools/reference_generation/*.py` → **zero hits**. The members are dead enum entries (the live spellings are the manifest strings, see M1). The parenthetical must be deleted.
- **Count ambiguity (D8):** including prefix kinds, the registry vocabulary is 54, and `registry-only` becomes 12 (`+ matrix_patch, profile_change_approval, profile_change_proposal, repair_feedback`); the "8-id" headline is an artifact of counting only the exact dict. State the comparison as exact-ids-only, or count prefixes.
- **Candidate owner:** reasonable for a shared kind↔type catalog.
- **Prior art:** `audit-findings.md:170` verified; the artifact kind/type claim is indeed new.

### F-ARTIFACT-09 — `KindNotRegisteredError` enforced on write, fabricated away on read

- **Verdict: DOWNGRADED → Medium (impact 2 × drift 3 = 6)** (audit: High 9).
- **Anchors:** `registry.py:8-9,100-107`; `store.py:128,428,449,464,657-661` — all resolve. The fabricated-read behavior is real:
  ```
  F09 load(unregistered id): NO ERROR -> fabricated read CONFIRMED
  ```
- **Why the downgrade — the stated consequence is false (D9):** the finding claims a too-new artifact *"raises `SchemaTooNewError` naming the wrong kind"*. But `store.py:466-468` passes `envelope.kind`, i.e. the kind **from the file**, never the fabricated `spec.kind`. My probe:
  ```
  F09 too-new unregistered raised SchemaTooNewError | kind=film.studio/cost-estimate | max_supported=1
  ```
  The wrong value is `max_supported` (fabricated `1`), not the kind name. The v0→`migrate_payload`→`KeyError` branch (`registry.py:244-250`) *is* real and verified by reading; the mutation scenario (delete a registration, write refuses at `store.py:128`, a pre-existing on-disk artifact still reads) is valid.
- **Severity:** the real defect is "read returns data with a spec that was never registered and an error that reports a max version of 1", recoverable and invisible unless a kind is removed/renamed → impact 2 × drift 3 = 6.
- **Candidate owner:** weak — intra-store read policy.
- **Prior art:** "New" is acceptable; I found no prior art asserting this seam.

---

## C. Cross-cutting checks

**C5 — "candidate owner module `film_pipeline.artifacts.contract`" is only partially reasonable.** §6.2's "leaks" are dominated by defects *inside* `artifacts/store.py` (per-path read enforcement F-05, `_safe_spec` fabrication F-09, status writers F-06, `latest_version`/`next_version` duplication M2). These are intra-owner inconsistencies, not cross-module leaks; renaming/moving them into `artifacts.contract` does not create a distinct owner and risks an oversplit that §B9/AGENTS.md ("no abstractions without current concrete need") warns against. A distinct shared module is justified only for the concerns genuinely consumed outside `artifacts/**`: the ref/stem codec (F-01), the kind→type resolver (F-02/F-08), and the registry-agreement invariant. F-03/F-05/F-06/F-07/F-09 should nominate `ArtifactStore` (or `GenerationLedgerManager`) as the owner.

**C6 — prior art (A7) is otherwise handled well.** All cited prior-art anchors in `documentation/audit-findings.md`, `documentation/reviews/storage-upgrade-review.md`, and `docs/clean-code-refactor/review-findings.md` resolve and say what the audit claims. The one clear omission is `documentation/reviews/arch-lens-dataflow.md:71,108` for the version-source-of-truth seam (see M2); F-ARTIFACT-03 and F-ARTIFACT-07 both touch it.

---

## D. Missed in scope (inverse check)

The audit's declared scope is the ref grammar, kind/schema registry, `schema_version` rules, checksum/version enforcement reachability, artifact-status and `GenerationStatus` lifecycles, and it claims *"No package in scope was silently omitted."* I found these distributed-ownership seams inside that scope:

**M1 — `graph/subgraphs/qc.py` is an entire parallel artifact-resolution path that the coverage table omits (most serious omission).**
`graph/subgraphs/qc.py:163-203` resolves each validator's artifact by scanning **latest-on-disk**:
```
183:    # One index scan replaces the old all-phase brute force: latest version
185:    for meta in srv.artifact_store.list_artifacts(project_id):
187:        if current is None or meta.version > current.version:
```
while `graph/nodes/qc.py:140-158` resolves the **pinned refs** in `state["artifact_refs"]` (`ArtifactRef.from_string` → `store.load(..., parsed.version)`). Two QC implementations, two different answers to "which version does QC validate", in the audit's exact declared concern ("`v<N>` reference grammar … version enforcement reachability"). §1.3 lists `graph/nodes/qc.py` but never `graph/subgraphs/qc.py`; §1.1's "No package … silently omitted" is not true for this file. This is an O6 parallel-lifecycle / O5 version-source seam with a real drift proof (change which version QC should pin; the subgraph keeps scanning latest and no test fails) and it is already prior art (`documentation/reviews/arch-lens-dataflow.md:108`). It also duplicates the kind vocabulary: `_VALIDATOR_ARTIFACTS` (`graph/subgraphs/qc.py:153-160`) vs the ref-key/`_collect_artifacts` table in `graph/nodes/qc.py`.

**M2 — two "latest version" rules with two sources, spanning the store itself.**
`artifacts/store.py:511-514` (`next_version`) scans `versions/`; `artifacts/store.py:516-519` (`latest_version`) reads `meta.json` `current_version`. `mcp/tools/helpers.py:184-187` (`_latest_artifact_version`) is a *third* implementation of the same meta.json rule, and it is consumed by `graph/orchestrator_validators/brief.py`, `mcp/tools/artifacts.py:71,86,139`, `mcp/tools/validation.py:119,235`, `generation/executor_prompts.py:21`, `app/services/_browse_ops.py:110` (`version: int = 1` default), etc. F-ARTIFACT-03 notes the helpers rule but never the in-store duplicate or the `max(1, latest_version(...))` read pattern; F-ARTIFACT-05 does not note that `list_artifacts` (the source of that rule) is the same unchecked path. This is prior art (`arch-lens-dataflow.md:71`: *"Pick one source of truth"*).

**M3 — a fourth kind vocabulary with real spelling drift, marked "Clean".**
`artifacts/manifest.py:21` `kind: str  # reference_sheet, generated_clip, last_frame, mid_frame, audio_stem`; the writer is `generation/executor_delivery.py:132-148` (`return "generated_clip"` at `:143`); the invariant consumers are `artifacts/manifest.py:41,43,49` (`entry.kind == "generated_clip"`). The normative enum says `schemas/_base.py:58 CLIP = "clip"`, `:46 REFERENCE_SHEET`, `:59-60 LAST_FRAME`/`MID_FRAME`. There is no `AssetKind` enum, no validation, and the two vocabularies already disagree (`generated_clip` vs `clip`) while nothing fails. §1.1 marks `artifacts/manifest.py` "Clean, no distributed ownership found", and F-ARTIFACT-08 compares only registry ids to `ArtifactType` — this is the same O1/O4 pattern one file over, with a *live* divergence.

**M4 — read-side `artifact_id` is never charset-validated (the title claim of F-ARTIFACT-01, under-proved).**
`validate_artifact_id` is called only at `store.py:120` (in `save`) and `store.py:217` (`save_mutable`). No read path calls it: `store.py:323,428,435,449,456` build paths directly from the ref/arg, and `mcp/tools/artifacts.py:60,74` pass `artifact_id` straight from MCP args into `store.load`. My probe shows `from_string` accepts `artifact:script:../../etc/passwd:v1` while `validate_artifact_id` rejects it, and no test covers this (zero hits for `validate_artifact_id` in `tests/`). F-ARTIFACT-01 mentions the charset, but as a Medium side-note with a wrong guard-test citation (D1); it should be a first-class statement that *reads* never validate the id.

**M5 (minor) — `_UPSTREAM_CONTENT_SOURCES` is a fifth artifact-id→phase vocabulary; the audit tags it `F-ARTIFACT-09` but that finding never discusses it.** `graph/nodes/_context.py:329-338` re-binds `"script_ref" → ("script", …)` etc. §2 line 106 attributes this to F-ARTIFACT-09, whose body is exclusively about `KindNotRegisteredError`; no finding claims it. It is an unguarded parallel of the phase vocabulary (`schemas/_base.py:77-90`, `artifacts/paths.py:14-26`).

---

## E. Disputes requiring the author to fix

| # | Finding | Required fix |
|---|---|---|
| D1 | F-ARTIFACT-01 | Delete the §4 claim that `test_refs.py:20-33` shows `from_string` accepting ids `validate_artifact_id` rejects — that test only asserts rejection of malformed refs. Add a real guard test (e.g. `artifact:script:Bad-Id:v1` accepted by the parser, rejected by the writer) or drop the claim. |
| D2 | F-ARTIFACT-02 | Fix the `visual.py:498` mechanism: the object is a `CostEstimate` model, not a `dict` (`agents/impl/gen_planner_agent.py:11,66`); the `SCRIPT` result comes from the dead `"cost_estimate_bom"` value (`_context.py:309`). |
| D3 | F-ARTIFACT-04 | Reconcile "eight axes" with the reproduce grep (add `schemas/runtime_state.py:30,48`, `generation/executor_delivery.py:95`, `schemas/_base.py:280`, `schemas/constraints.py:148`, or state the scope explicitly); add the marker `schema_version` (`storage.py:36,108`) to the write-only list; move the `store.py:166/:279` anchors to `:191/:291`. |
| D4 | F-ARTIFACT-05 | Delete "the same file read through `store.load_envelope` (`store.py:449`) would raise" — for mutable kinds it does not; contrast with an immutable envelope instead. |
| D5 | F-ARTIFACT-06 | Reclass O3 → O2 (or O5); the store is the single writer of the status representation. |
| D6 | F-ARTIFACT-07 | Replace the falsified drift proof (COMPLETED→CANCELLED leaves `estimate_total_cost` unchanged because CANCELLED is terminal, `ledger.py:126-131`) with the reproduced COMPLETED→RUNNING proof; reclass O3 → O6/O2; drop the claim that `executor.py:200/:296/:402` is a second provider-status mapping. |
| D7 | F-ARTIFACT-08 | Delete "(and used in `reference_generation`)": `clip`/`last_frame`/`mid_frame` have no references in `src/`; the live spellings are the `AssetEntry.kind` strings (M1/M3). |
| D8 | F-ARTIFACT-08 | State the comparison basis (exact ids only, 47/45) or include the 8 prefix kinds (54/45, `registry-only` = 12). |
| D9 | F-ARTIFACT-09 | Delete "naming the wrong kind": `SchemaTooNewError` at `store.py:466-468` reports `envelope.kind`; the fabricated value is `max_supported` (reproduced `max_supported=1`). |
| D10 | F-ARTIFACT-03 | Fix the four off-by-one anchors (`_shared.py:125`, `shot.py:72`, `planning.py:75`, `index_files.py:84`) and cite `documentation/reviews/arch-lens-dataflow.md:71,108` as prior art. |
| D11 | Coverage (A1) | Add `graph/subgraphs/qc.py` to §1.3 and either file M1 as a finding or record it as an explicitly single-owner claim with a guard test; currently §1.1's "no package omitted" is false. |

---

## F. Overall verdict

**Confirmed 5 (F-ARTIFACT-01, 02, 04, 05, 06); downgraded 4 (F-ARTIFACT-03 → Medium 8, F-ARTIFACT-07 → High 12, F-ARTIFACT-08 → Medium 8, F-ARTIFACT-09 → Medium 6); rejected 0 — the seam inventory is real but the file does not meet bar A2/A3 as written (four drift proofs contain false or unreproducible claims), and it also fails A1 (missed `graph/subgraphs/qc.py`, the parallel QC artifact-resolution path) and A7 (uncited `arch-lens-dataflow.md` prior art); after applying D1–D11 it can meet A2/A3.**
