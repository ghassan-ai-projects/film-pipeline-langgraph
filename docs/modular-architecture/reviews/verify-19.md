# verify-19 — Bar A6 adversarial closure for eight post-verification findings

**Verifier:** independent adversarial verifier (bar A6), did not write any audited finding.
**Repo:** `${REPO_ROOT}` · **Branch:** `modular-app`
**Commit under test:** `fb85baa0e6b769b709791a96a89980089304bf13`

```
$ git rev-parse HEAD
fb85baa0e6b769b709791a96a89980089304bf13
$ git status --porcelain          # at start, and at end of this review
(empty)
```

Pristine snapshot (all `src/` anchors and mutations were read/derived from here, never from the
live tree):

```
$ mkdir -p /tmp/v19 && git archive fb85baa0e6b769b709791a96a89980089304bf13 | tar -x -C /tmp/v19
```

Mutations were applied only to a throwaway copy `/tmp/v19work` (`cp -R /tmp/v19 /tmp/v19work`) and
each mutated file was restored from `/tmp/v19` immediately after the run; the real repo was never
touched. Scratch is confined to `/tmp`.

## Scope and method

Findings verified (only these eight; `F-ARTIFACT-14` and any other post-verification additions were
explicitly out of scope):

| # | Audit file | Id |
|---|---|---|
| 1 | `audit/07-artifact-refs-and-schemas.md` | `F-ARTIFACT-10` |
| 2 | `audit/07-artifact-refs-and-schemas.md` | `F-ARTIFACT-11` |
| 3 | `audit/07-artifact-refs-and-schemas.md` | `F-ARTIFACT-12` |
| 4 | `audit/07-artifact-refs-and-schemas.md` | `F-ARTIFACT-13` |
| 5 | `audit/08-validation-and-review.md` | `F-VR-12` |
| 6 | `audit/08-validation-and-review.md` | `F-VR-13` |
| 7 | `audit/08-validation-and-review.md` | `F-VR-14` |
| 8 | `audit/08-validation-and-review.md` | `F-VR-15` |

For each: every `path:line` anchor was re-resolved against `/tmp/v19`; every `Reproduce` command was
run verbatim (indented fences de-indented per §1.6.7) and its real output recorded; every drift proof
was attacked, and every claimed "no test fails" mutation was actually applied and the relevant tests
run; severity was re-scored with §1.5; double-counting was checked against the already-verified
findings named in the brief (audit 07 `F-ARTIFACT-01/02/03/08/09`; audit 08 `F-VR-01…F-VR-11`); class
and prior art were checked.

**Pinned revision of the objects reviewed (the files moved during this session).** Another agent
edited both audit files while this verification was running, after my first read and before some of
my reproduce runs. All verdicts below are against these exact revisions, whose line numbers are the
ones cited; earlier line numbers (`F-ARTIFACT-10` at 627, `F-VR-12` at 961) are superseded:

```
$ wc -l docs/modular-architecture/audit/07-artifact-refs-and-schemas.md
1055 docs/modular-architecture/audit/07-artifact-refs-and-schemas.md
$ wc -l docs/modular-architecture/audit/08-validation-and-review.md
1439 docs/modular-architecture/audit/08-validation-and-review.md
$ shasum -a 256 docs/modular-architecture/audit/07-artifact-refs-and-schemas.md \
               docs/modular-architecture/audit/08-validation-and-review.md
26b0a0998cff6cfd28e7565ac9bd99d50b49ac6e3f9b358c3d1416fa09a8e294  docs/modular-architecture/audit/07-artifact-refs-and-schemas.md
83dea2b092038a4f077abaa62da87e6ea64af377f2cc23f64e18d2aceb4ffae9  docs/modular-architecture/audit/08-validation-and-review.md
```

The moving target matters for two verdicts: `F-VR-15`'s title/count wording and `F-VR-14`'s
`F-VR-12`-adjacent reproduce line were corrected between my first and second read, so defects I
initially saw in the *old* revision are reported as **already fixed** and are not counted against the
current revision.

---

## F-ARTIFACT-10 — Two QC artifact-resolution paths disagree on which version is validated

**Anchor re-derivation** (audit `07` lines 653–685):

| Anchor | Resolves? | Line actually found |
|---|---|---|
| `src/film_pipeline/graph/nodes/qc.py:149-158` | yes | `149 for ref_str in state.get("artifact_refs", []):`; `152 parsed = ArtifactRef.from_string(ref_str)`; `156 artifact_data[parsed.artifact_id] = store.load(` |
| `src/film_pipeline/graph/subgraphs/qc.py:182-188` | yes | `182 # One index scan …`; `185 for meta in srv.artifact_store.list_artifacts(project_id):`; `187 if current is None or meta.version > current.version:` |
| `src/film_pipeline/graph/subgraphs/qc.py:153-160` `_VALIDATOR_ARTIFACTS` | yes | `153 _VALIDATOR_ARTIFACTS: dict[str, tuple[str, ...]] = {` … `160 }` |
| `src/film_pipeline/graph/graph.py:119` | **NO** | line 119 is `    # Human gate nodes`; the binding is at **`graph.py:115`** |
| `src/film_pipeline/graph/nodes/_repair_loop.py:47` | yes | `47 "qc": qc_node,` |
| `src/film_pipeline/mcp/tools/helpers.py:184-187` | yes | `184 def _latest_artifact_version(...)`, `187 return max(versions) if versions else 0` |
| `src/film_pipeline/artifacts/store.py:516-519` | yes | `516 def latest_version(...)`, `519 return int(meta["current_version"]) if meta is not None else 0` |
| prior art `documentation/reviews/arch-lens-dataflow.md:108` | yes | the `| Artifact resolution | Pinned versions … | Ignores refs entirely …` table row |

**Reproduce (verbatim) and real output:**

```
$ grep -rn "artifact_refs\|list_artifacts\|ArtifactRef.from_string" src/film_pipeline/graph/nodes/qc.py src/film_pipeline/graph/subgraphs/qc.py
src/film_pipeline/graph/nodes/qc.py:55:    new_refs = [r for r in (new_state.get("artifact_refs", []) or []) if _is_new_ref(r, original)]
src/film_pipeline/graph/nodes/qc.py:57:        updates["artifact_refs"] = new_refs
src/film_pipeline/graph/nodes/qc.py:92:            state.setdefault("artifact_refs", []).append(patch_ref)
src/film_pipeline/graph/nodes/qc.py:112:            state.setdefault("artifact_refs", []).append(ref)
src/film_pipeline/graph/nodes/qc.py:141:    """Load artifacts referenced by ``state["artifact_refs"]`` from their phases."""
src/film_pipeline/graph/nodes/qc.py:149:    for ref_str in state.get("artifact_refs", []):
src/film_pipeline/graph/nodes/qc.py:152:            parsed = ArtifactRef.from_string(ref_str)
src/film_pipeline/graph/nodes/qc.py:172:    artifact_refs: list[str] = state.get("artifact_refs", [])
src/film_pipeline/graph/nodes/qc.py:175:        consensus = ConsensusBuilder().build(reports, artifact_refs)
src/film_pipeline/graph/nodes/qc.py:183:        state.setdefault("artifact_refs", []).append(ref)
src/film_pipeline/graph/subgraphs/qc.py:185:    for meta in srv.artifact_store.list_artifacts(project_id):
```

The command prints the sites but not the count ("Two"), so the "two paths" magnitude is read off the
output rather than computed; that is a mild §1.6.4 gap, not a false output.

**Drift proof — attacked.** The structural divergence is real and I re-derived it by reading both
files: `_collect_artifacts` (`nodes/qc.py:140-161`) loads exactly the pinned
`state["artifact_refs"]` versions; `_load_artifact_for_validator`
(`subgraphs/qc.py:168-198`) ignores refs and takes the max version per `artifact_id` from
`list_artifacts`. Both paths are live:

```
$ grep -n 'add_node("qc_node"' src/film_pipeline/graph/graph.py
115:    builder.add_node("qc_node", build_qc_subgraph())  # Phase 7: parallel subgraph
$ sed -n '119p' src/film_pipeline/graph/graph.py          # the finding's cited line
    # Human gate nodes
$ grep -rn '_PHASE_NODES' src/film_pipeline/graph/nodes/_repair_loop.py | head -2
38:_PHASE_NODES: dict[str, Any] = {
209:    phase_fn = _PHASE_NODES.get(phase)
```

"`No test pins the agreement between the two resolution rules`" holds: `tests/unit/graph/test_qc_subgraph.py:9`
imports only `film_pipeline.graph.subgraphs.qc`, and `tests/unit/graph/test_qc_validator_dispatch.py:15`
imports only `film_pipeline.graph.nodes.qc`; no test imports both paths. Mutation scenario is sound
(no need to apply it: the two rules are different by construction).

**Defects found.**

1. **Wrong anchor, self-inconsistent within the same commit.** The drift proof cites
   `src/film_pipeline/graph/graph.py:119` for the forward binding. Line 119 is a comment; the binding
   is `graph.py:115`. This is not inherited from the prior-art doc alone — audit `08`'s `F-VR-03`
   (line 452 of the current file) cites the *correct* `src/film_pipeline/graph/graph.py:115` for the
   same statement, so the two audits disagree about the same line at the same commit. The audit's
   header claims "All line numbers verified at `fb85baa`"; this one was not.
2. **Basis gap (mild).** "Two QC artifact-resolution paths" and "two more 'latest' rules" are not
   computed by the recorded `Reproduce` command.

**Severity (§1.5).** High (impact 3 × drift 4 = 12) is defensible: a validator can evaluate a
different version than the human gate reviewed (wrong internal behaviour, recoverable), and no test
pins cross-path agreement. I considered raising impact to 4 (the verdict can corrupt a QC gate), but
the two paths still each validate *some* real version and the failure is recoverable — 3 is right.
**Band unchanged.**

**Double-counting.** Two overlaps the finding does not acknowledge:

- **`F-ARTIFACT-03`** (same audit, already verified, Medium 8) owns the "latest version" duplication
  and already lists `artifacts/store.py:516-519` and `mcp/tools/helpers.py:184-187` as competing
  rules; `F-ARTIFACT-10` re-cites those same two anchors in its blast radius without naming
  `F-ARTIFACT-03`.
- **`F-VR-03`** (audit 08, already verified, Critical 16) is the same two-live-QC-lifecycles owner
  seam (`graph.py:115` vs `_repair_loop.py:47` vs `_graph_exec.py:337`). `F-ARTIFACT-10` narrows it
  to version resolution and adds the two `latest` helpers, so it is not a pure duplicate — but the
  increment should be stated and the two must not be extracted independently.

**Class / prior art.** O6 is correct. Prior art is present and the cited line resolves.

### Verdict: `CONFIRMED-WITH-FIX` — High (3 × 4 = 12), band unchanged.
Fix the `graph.py:119` → `graph.py:115` anchor and add the cross-references to `F-ARTIFACT-03` and
`F-VR-03`.

---

## F-ARTIFACT-11 — `AssetEntry.kind` is a fourth kind vocabulary with live spelling drift and no validation

**Anchor re-derivation** (audit `07` lines 687–719): all resolve.

| Anchor | Resolves? | Line actually found |
|---|---|---|
| `src/film_pipeline/artifacts/manifest.py:21` | yes | `kind: str  # reference_sheet, generated_clip, last_frame, mid_frame, audio_stem` |
| `src/film_pipeline/generation/executor_delivery.py:132-148` | yes | `132 def _asset_kind(path: Path) -> str:`, `143 return "generated_clip"`, `148 return "generated_clip"` |
| `src/film_pipeline/artifacts/manifest.py:41,43,49` | yes | the three `== "generated_clip"` invariant consumers |
| `src/film_pipeline/schemas/_base.py:58` | yes | `CLIP = "clip"` |

**Reproduce (verbatim) and real output:**

```
$ grep -rn "generated_clip\|\"kind\"\|\.kind ==" src/film_pipeline --include='*.py'
src/film_pipeline/artifacts/manifest.py:21:    kind: str  # reference_sheet, generated_clip, last_frame, mid_frame, audio_stem
src/film_pipeline/artifacts/manifest.py:41:        if entry.kind == "generated_clip" and entry.active:
src/film_pipeline/artifacts/manifest.py:43:                if existing.shot_id == entry.shot_id and existing.kind == "generated_clip":
src/film_pipeline/artifacts/manifest.py:49:            if e.shot_id == shot_id and e.kind == "generated_clip" and e.active:
src/film_pipeline/artifacts/manifest.py:54:        return [e for e in self.entries if e.kind == kind]
src/film_pipeline/app/services/_browse_ops.py:95:            "kind": entry.kind,
src/film_pipeline/checkpoints/invalidation.py:21:    "generation_schedule": ["generated_clips"],
src/film_pipeline/agents/mvp/__init__.py:147:        input_artifacts=["generated_clip", "prompt_registry", "validation_ledger"],
src/film_pipeline/agents/_http_transport.py:91:    return any(param.kind == Parameter.VAR_KEYWORD for param in params.values()) or any(
src/film_pipeline/mcp/tools/artifacts.py:187:                "kind": entry.kind,
src/film_pipeline/validation/validators/__init__.py:109:        input_schema="generated_clip",
src/film_pipeline/validation/validators/__init__.py:119:        input_schema="generated_clip",
src/film_pipeline/generation/executor_delivery.py:105:        sidecar["files"].append({"path": relative, "kind": kind, "sha256": digest})
src/film_pipeline/generation/executor_delivery.py:143:        return "generated_clip"
src/film_pipeline/generation/executor_delivery.py:148:    return "generated_clip"
```

The inline zero-count claim is also true:

```
$ grep -rn "ArtifactType.CLIP\|ArtifactType.LAST_FRAME\|ArtifactType.MID_FRAME" src/
(exit=1)   # 0 hits
```

**Drift proof — attacked, and the mutation half is FALSIFIED.** I applied the finding's exact
mutation to `/tmp/v19work` (both `return "generated_clip"` in `_asset_kind` → `"clip"`) and ran every
test that touches the manifest and the delivery executor:

```
$ # pristine
$ PYTHONPATH=/tmp/v19/src .venv/bin/python -m pytest \
    /tmp/v19/tests/unit/test_artifacts_manifest.py /tmp/v19/tests/unit/test_artifacts.py \
    /tmp/v19/tests/unit/generation/test_executor.py /tmp/v19/tests/unit/generation/test_frame_sidecar.py \
    /tmp/v19/tests/unit/artifacts/test_state_persistence.py /tmp/v19/tests/unit/mcp/tools/test_artifacts.py \
    --no-cov -p no:cacheprovider -v | tail -1
============================== 91 passed in 3.34s ==============================
$ # mutated (_asset_kind -> "clip")
========================= 1 failed, 90 passed in 3.22s =========================
FAILED ../../../../tmp/v19work/tests/unit/artifacts/test_state_persistence.py::TestMediaLayout::test_second_delivery_does_not_re_record_sidecars
    clip_entries = [e for e in manifest.entries if e.kind == "generated_clip"]
>   assert len(clip_entries) == 2
E   assert 0 == 2
tests/unit/artifacts/test_state_persistence.py:408: AssertionError
```

So "**no test fails**" is false: `test_second_delivery_does_not_re_record_sidecars` pins the live
spelling end-to-end through `deliver_completed_job` → `_asset_kind` → `add_take`, and additionally
asserts the one-active-take invariant at `:411`. The *consequence* the finding predicts is real in
isolation — I reproduced it directly (two active takes, `active_take` → `None`) — but the mutation is
**not silent**, so §1.6.3(b) fails. What survives is only the "existing divergence" half
(`"generated_clip"` vs `ArtifactType.CLIP == "clip"`), and that divergence is between a **dead**
enum member (`ArtifactType.CLIP` has zero references, per the finding's own grep) and the live
manifest strings — which is precisely the observation audit 07's already-verified `F-ARTIFACT-08`
records (it names `clip`/`last_frame`/`mid_frame` as dead enum entries and says "the live spellings
are the `AssetEntry.kind` manifest strings (**F-ARTIFACT-11**)"). The genuinely new and live part is
"`AssetEntry.kind` has no enum and `_asset_kind` has no direct test", which the finding should state
instead of the falsified mutation.

**Severity (§1.5).** Impact 2 (recoverable, no deliverable corruption) stands. Drift must drop:
because the one-active-take consequence is pinned end-to-end by
`test_second_delivery_does_not_re_record_sidecars`, the residual unpinned risk is only the
`_asset_kind` classifier itself (no test names it). I re-score drift **3**, giving **Medium
(2 × 3 = 6)**. Band unchanged (Medium), score down from 8.

**Double-counting.** `F-ARTIFACT-08` (already verified, Medium 8) already states the enum-vs-manifest
spelling divergence and points forward to this id; `F-ARTIFACT-11`'s prior art says only "New" and
does not acknowledge the read-across.

**Class / prior art.** O1 is defensible (two vocabularies for one concept), though O8 ("a bare `str`
seam with no typed contract") is the closer fit for the live defect. Prior art correctly notes the
first revision's "Clean" marking of `manifest.py` was wrong.

### Verdict: `CORRECTED` — Medium (2 × 3 = 6). The mutation proof must be replaced.

---

## F-ARTIFACT-12 — Read paths never validate the `artifact_id`

**Anchor re-derivation** (audit `07` lines 721–762): all resolve.

| Anchor | Resolves? | Line actually found |
|---|---|---|
| `src/film_pipeline/artifacts/store.py:120` / `:217` | yes | `validate_artifact_id(meta.artifact_id)` (both in save paths) |
| `src/film_pipeline/artifacts/store.py:435` / `:456` | yes | `path = self._version_path(project_id, phase.value, artifact_id, version)` |
| `src/film_pipeline/mcp/tools/artifacts.py:57,75` | yes | `57 artifact_id = str(args.get("artifact_id", ""))`; `75 content = store.load(project_id, fp, artifact_id, version)` |
| `src/film_pipeline/artifacts/registry.py:47-53` | yes | `47 def validate_artifact_id(artifact_id: str) -> None:` … raise at 50–53 |

The only `validate_artifact_id` occurrences in `src/` are the import (`store.py:47`), the two
write-path calls (120, 217), the definition (`registry.py:47`) and a comment
(`schemas/artifact.py:43`); no read path calls it.

**Reproduce (verbatim) and real output:**

```
$ .venv/bin/python -c "from film_pipeline.schemas.artifact import ArtifactRef; print(ArtifactRef.from_string('artifact:script:../../etc/passwd:v1').artifact_id)"
../../etc/passwd
$ grep -rn "validate_artifact_id" src/film_pipeline --include='*.py'
src/film_pipeline/artifacts/store.py:47:    validate_artifact_id,
src/film_pipeline/artifacts/store.py:120:        validate_artifact_id(meta.artifact_id)
src/film_pipeline/artifacts/store.py:217:        validate_artifact_id(meta.artifact_id)
src/film_pipeline/artifacts/registry.py:47:def validate_artifact_id(artifact_id: str) -> None:
src/film_pipeline/schemas/artifact.py:43:        # Note: the id charset is enforced by save() (validate_artifact_id), not
$ grep -rn "validate_artifact_id\|sanitize_artifact_id" tests/          # inline claim, re-run
(exit=1)   # 0 hits
```

**Drift proof — attacked, and CONFIRMED by full reproduction.** The finding's quoted probe output is
not itself a `Reproduce` bullet, so I re-derived the traversal end-to-end against `/tmp/v19` with a
valid storage root, the intermediate phase directory present (exactly the precondition the finding
states), and a planted file outside the root:

```
$ PYTHONPATH=/tmp/v19/src .venv/bin/python - <<'PY'
from pathlib import Path
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.schemas._base import FilmPhase
from film_pipeline.schemas.artifact import ArtifactRef
root = Path("/tmp/v19probe2/store")
store = ArtifactStore(root)                       # creates a valid storage root + marker
(root / "p1" / "artifacts" / "03-script").mkdir(parents=True, exist_ok=True)
outside = Path("/tmp/v19probe2/outside/versions"); outside.mkdir(parents=True, exist_ok=True)
(outside / "v001.json").write_text('{"pwned": true}')
aid = "../../../../outside"
vp = store._version_path("p1", "script", aid, 1)
print("version path exists()?", vp.exists(), "| resolved:", vp.resolve())
print("ref parse:", ArtifactRef.from_string(f"artifact:script:{aid}:v1").artifact_id)
try:
    print("load returned:", store.load("p1", FilmPhase.SCRIPT, aid, 1))
except Exception as e:
    print("load(traversal) raised:", type(e).__name__)
    print(str(e)[:300])
PY
storage root: /tmp/v19probe2/store
version path exists()? True | resolved: /private/tmp/v19probe2/outside/versions/v001.json
ref parse: ../../../../outside
load(traversal) raised: ValidationError
9 validation errors for ArtifactEnvelope
kind
  Field required [type=missing, input_value={'pwned': True}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
schema_version
  Field required [type=missing, input_value={'pwned': True}, input_type=dict
```

The planted file outside the storage root was opened and parsed, and its content was echoed in the
validation error — the finding's claim reproduces exactly (the only difference is the probe
directory name). `validate_artifact_id` rejects the id (verified: `Invalid artifact id
'../../../../outside': must match ^[a-z][a-z0-9_]*$`), and no test pins read-side validation.

**Minor note.** The strongest evidence (the traversal) comes from a probe that is not shipped as a
`Reproduce` bullet; the shipped bullet only shows `from_string` accepting the id. This is a mild
§1.6.4/A2 gap, not a false claim. The "0 hits in tests" claim is likewise inline rather than in the
`Reproduce` block, but I re-ran it and it is true.

**Severity (§1.5).** High (3 × 4 = 12) confirmed. Impact 3 (constrained arbitrary file read of
`*/versions/vNNN.json` plus content leakage into errors; recoverable, single-user local tool by
default) with drift 4 (nothing pins it). The finding's conditional escalation to impact 4 / Critical
16 if the MCP boundary is treated as untrusted is well-founded and correctly stated as a condition,
not assumed.

**Double-counting.** None. `F-ARTIFACT-01` (already verified) touches the id charset but only as a
parser/writer asymmetry with the wrong guard-test citation; this finding explicitly supersedes that
side-note. Class O8 is correct; prior art "New" is accurate.

### Verdict: `CONFIRMED` — High (3 × 4 = 12).

---

## F-ARTIFACT-13 — `_UPSTREAM_CONTENT_SOURCES` is a fifth artifact-ref-key→phase vocabulary

**Anchor re-derivation** (audit `07` lines 764–790): all resolve.

| Anchor | Resolves? | Line actually found |
|---|---|---|
| `src/film_pipeline/schemas/_base.py:77-90` | yes | `77 class FilmPhase(StrEnum):` … `90 DELIVERY = "delivery"` |
| `src/film_pipeline/artifacts/paths.py:14-26` | yes | `14 PHASE_DIR_MAP: dict[str, str] = {` … `26 }` |
| `src/film_pipeline/graph/nodes/_context.py:329-338` | yes | `329 _UPSTREAM_CONTENT_SOURCES: dict[str, tuple[str, str]] = {` … `337 "execution_brief_ref": ("shot_bible", "execution_brief_content"),` / `338 }` |
| prior art `documentation/reviews/arch-lens-dataflow.md:85` | yes | the bullet naming `_UPSTREAM_CONTENT_SOURCES` for the approval seam |

**Reproduce (verbatim) and real output:**

```
$ grep -rn "_UPSTREAM_CONTENT_SOURCES\|PHASE_DIR_MAP\|class FilmPhase" src/film_pipeline --include='*.py'
src/film_pipeline/artifacts/store.py:78:            self._artifacts_base(project_id) / paths.PHASE_DIR_MAP.get(phase, phase) / artifact_id
src/film_pipeline/artifacts/store.py:357:                phase_dirname = paths.PHASE_DIR_MAP.get(meta.phase.value, meta.phase.value)
src/film_pipeline/artifacts/store.py:495:                else f"{paths.PHASE_DIR_MAP.get(phase.value, phase.value)}/*/meta.json"
src/film_pipeline/artifacts/store.py:501:        phase_order = {name: index for index, name in enumerate(paths.PHASE_DIR_MAP)}
src/film_pipeline/artifacts/paths.py:14:PHASE_DIR_MAP: dict[str, str] = {
src/film_pipeline/artifacts/paths.py:34:    return project_dir(project_slug, root) / PHASE_DIR_MAP.get(phase, phase)
src/film_pipeline/artifacts/project_storage.py:133:        from film_pipeline.artifacts.paths import PHASE_DIR_MAP
src/film_pipeline/artifacts/project_storage.py:136:        for phase, dirname in reversed(PHASE_DIR_MAP.items()):
src/film_pipeline/graph/nodes/_context.py:329:_UPSTREAM_CONTENT_SOURCES: dict[str, tuple[str, str]] = {
src/film_pipeline/graph/nodes/_context.py:351:    for ref_key, (_phase_name, content_key) in _UPSTREAM_CONTENT_SOURCES.items():
src/film_pipeline/schemas/_base.py:77:class FilmPhase(StrEnum):
```

**Drift proof — attacked, and FALSIFIED on both readings of the mutation.**

The finding says the table's phase string is a live duplicated vocabulary and that "a renamed phase
silently drops upstream content from prompts". The only consumer is `_context.py:351`, where the
phase element is bound to `_phase_name` and **never read**:

```
$ sed -n '350,358p' src/film_pipeline/graph/nodes/_context.py
    for ref_key, (_phase_name, content_key) in _UPSTREAM_CONTENT_SOURCES.items():
        ref = str(state.get(ref_key, "") or "").strip()
        if not ref:
            continue
        try:
            context_vars[content_key] = _compact_upstream_content(state, services, project_id, ref)
        except (FileNotFoundError, ValueError, KeyError) as exc:
            _record_context_load_failure(state, ref_key, ref, exc)
            continue

$ # AST check: is `_phase_name` ever loaded anywhere in the module?
F-ARTIFACT-13 AST proof: '_phase_name' appears as a Load anywhere in _context.py = False
loop line: for ref_key, (_phase_name, content_key) in _UPSTREAM_CONTENT_SOURCES.items():
```

The actual phase used at load time comes from the **ref itself**:
`_compact_upstream_content` (`_context.py:361-373`) does
`parsed = _parse_ref(ref)` then `FilmPhase(parsed.phase)`. The table's phase column is dead data.

Mutation 1 (mutate the thing the finding is about — the table's phase literals): set every phase
literal to `"zzz_phase"` and run the context tests:

```
MUTATION 5: F-ARTIFACT-13 table phase literals -> zzz_phase
--- F-ARTIFACT-13 mutated (context set) ---
============================== 31 passed in 2.85s ==============================
```

Silent — but also **behaviourally inert**, so §1.6.3's "divergent behavior" requirement is not met:
this is a dead duplicate, not distributed ownership (`§1.3`).

Mutation 2 (the finding's own wording — "add or rename a phase in `FilmPhase`"): rename
`FilmPhase.CONSTITUTION = "constitution"` → `"constitution_x"` and run graph + artifacts + schemas:

```
MUTATION (stated in the finding): rename a FilmPhase value
================== 19 failed, 348 passed, 2 skipped in 4.64s ==================
```

Not silent at all. So under either interpretation the stated drift proof fails: the mutation is either
silent-and-inert or loud-and-detected. The specific blast-radius claim ("a renamed phase silently
drops upstream content from prompts") is **false** — the phase column is never consulted.

**Severity (§1.5).** With the phase column inert, the "fifth phase vocabulary" has no drift
consequence. What remains is a dead duplicated column that looks authoritative (a readability
hazard) plus the live ref-key→content-key policy, which is a different concern than the one filed. I
score impact 1 (cosmetic) × drift 2 = 2 → Low, but per §1.6.3 the finding as written has no valid
drift proof at all.

**Double-counting.** `F-ARTIFACT-08`'s verified statement that `ArtifactType` is intentionally
coarser than the registry is adjacent but not the same; no direct duplicate.

**Class / prior art.** O1 as labelled, but §1.3 excludes inert/dead duplication from distributed
ownership. The ordinal "fifth" is not computed by any command (`§1.6.4` gap). Prior art is present
and honest (the `:85` citation correctly disclaims the approval-seam discussion).

### Verdict: `REJECTED` — the §1.6.3 drift proof fails (the phase column it mutates is provably never read, and renaming `FilmPhase` — the finding's own words — fails 19 tests). If the authors want to keep anything here it must be re-filed under §1.6.6 as a Low dead-code/readability item (or replaced by the live ref-key policy concern), not carried among findings.

---

## F-VR-12 — Consensus artifacts are persisted with `artifact_type = script`

**Anchor re-derivation** (audit `08` lines 991–1071): all resolve.

| Anchor | Resolves? | Line actually found |
|---|---|---|
| `src/film_pipeline/graph/nodes/qc.py:83-89` | yes | `83 patch_ref = _save_artifact(`; `88 artifact_type="consensus_report",`; `89 )` |
| `src/film_pipeline/graph/nodes/qc.py:109` | yes | `ref = _save_artifact(state, report, "consensus_report", "qc")` |
| `src/film_pipeline/graph/nodes/_agent_artifacts.py:35-39` | yes | `35 if artifact_type is not None:` … `39 return _ArtifactType.SCRIPT` |
| `src/film_pipeline/graph/nodes/_context.py:310,318-321` | yes | `310 "ConsensusReport": "consensus_report",`; `318 try:` … `321 return _ArtifactType.SCRIPT` |
| `src/film_pipeline/schemas/_base.py:27-75` | yes | `class ArtifactType(StrEnum):` at 27 (45 members, body ends 74) |
| `src/film_pipeline/artifacts/store.py:754-758` | yes | `756 details = [`; `758 f"- type: {meta.artifact_type.value}",` |

**Reproduce (verbatim) and real output:**

```
$ ./.venv/bin/python - <<'PY'   (the finding's script, verbatim)
infer ConsensusReport -> script
resolve consensus_report+MatrixPatch -> script
spec_for(consensus_report).kind = film.studio/consensus-report
spec_for(matrix_patch_qc).kind = film.studio/matrix-patch
$ grep -rn "consensus_report" src/film_pipeline/schemas/_base.py
(exit=1)   # nothing
$ grep -rn "artifact_type ==\|artifact_type in" --include=*.py src | wc -l
       0
```

**Defect: §1.6.7 — the drift-proof output block is not the command's output.** The finding prints
(lines 1017–1023) a five-line block and presents it as "verified by direct call at HEAD", then gives
the script under `Reproduce`. Two lines are embellished and one is not printed by the script at all:

| Stated output line | Actual command output |
|---|---|
| `spec_for(consensus_report).kind = film.studio/consensus-report \| renderer = render_consensus_report` | `spec_for(consensus_report).kind = film.studio/consensus-report` (no `\| renderer = …`) |
| `spec_for(matrix_patch_qc).kind = film.studio/matrix-patch \| payload_model = MatrixPatch` | `spec_for(matrix_patch_qc).kind = film.studio/matrix-patch` (no `\| payload_model = …`) |
| `consensus_report in ArtifactType? False` | **not printed by the command at all** |

The extra facts are independently true (I confirmed the renderer/payload model by reading
`registry.py:199`/`rendering.py` and `ArtifactType` by grep), but a reader running the `Reproduce`
block gets different output. This is exactly the failure mode §1.6.7 was added for, in the
text-vs-command direction of the flagged `F-ARTIFACT-08` pattern.

**Drift proof — attacked, substance CONFIRMED.** The "existing divergence" half reproduces
(`_infer_artifact_type(ConsensusReport) -> script`, `_resolve_artifact_type("consensus_report", …) ->
script`, while the registry kind is `film.studio/consensus-report` and `consensus_report ∉
ArtifactType`), and the mutation claim's premise holds: no test references
`_ARTIFACT_TYPE_BY_CLASS` / `_infer_artifact_type` / `_resolve_artifact_type`:

```
$ grep -rn "_ARTIFACT_TYPE_BY_CLASS\|_infer_artifact_type\|_resolve_artifact_type" tests/
(exit=1)   # 0 hits
```

**Double-counting — significant, cross-audit.** This is substantially the same owner seam as audit
07's already-verified **`F-ARTIFACT-02`** (Critical 4 × 4 = 16): same two map/coercion sites
(`_context._ARTIFACT_TYPE_BY_CLASS` / `_agent_artifacts._resolve_artifact_type`), same
`"consensus_report"` string rejected by `ArtifactType`, same silent `SCRIPT` substitution, and
`F-ARTIFACT-02` already cites `qc.py:88`'s explicit `artifact_type="consensus_report"` argument and
`qc.py:109`/`:180`. `F-VR-12`'s only genuine increment is the *correction* that the id-keyed registry
still fires the `consensus_report` renderer (the verifier's M3 claim was wrong) — a valuable
correction, but the underlying defect is double-filed at two different severities (16 vs 12) with no
cross-reference. `F-VR-12` does not cite `F-ARTIFACT-02` at all.

**Prior art — wrong anchor.** The finding cites
`docs/clean-code-refactor/BASELINE.md:261` as "(stringly-typed artifact typing noted)". Line 261 is:

```
$ sed -n '261p' docs/clean-code-refactor/BASELINE.md
| src/film_pipeline/validation/consensus.py | 4 | 97 | 0 | 1 | PASS |  |  |
```

and `grep -n "stringly\|artifact type\|artifact_type" docs/clean-code-refactor/BASELINE.md` returns
nothing. The citation is misattributed (it is the `consensus.py` coverage row — which is what
`F-VR-04` correctly cites it for). Per §1.6.8/A7 this prior-art claim is unverifiable as written.

**Severity (§1.5).** High (3 × 4 = 12): the consequence is wrong metadata on durable artifacts plus a
live trap for the first `artifact_type` filter; the markdown body is correct. Defensible on its own
terms, but it must be reconciled with `F-ARTIFACT-02`'s Critical 16 for the same mechanism — one of
the two scores is wrong, or the increment must be shown to justify the difference.

**Class.** O8 compounded with O1 is correct.

### Verdict: `CONFIRMED-WITH-FIX` — High (3 × 4 = 12), band unchanged, subject to reconciling the double-count and severity with `F-ARTIFACT-02` (Critical 16).

---

## F-VR-13 — `consensus_report_ref`/`qc_patch_ref` cross the node boundary unregistered

**Anchor re-derivation** (audit `08` lines 1073–1154): every anchor resolves.

| Anchor | Resolves? | Line actually found |
|---|---|---|
| `src/film_pipeline/graph/nodes/qc.py:29-30` | yes | `29 # Ref-valued state keys …`; `30 _QC_REF_KEYS: tuple[str, ...] = ("consensus_report_ref", "qc_patch_ref")` |
| `src/film_pipeline/graph/nodes/qc.py:42` | yes | `updates = _collect_updates(gate_updates, new_state, state, _QC_REF_KEYS)` |
| `src/film_pipeline/graph/nodes/qc.py:61-64` | yes | `61 for key in ref_keys:` … `64 updates[key] = val` |
| `src/film_pipeline/graph/nodes/_agent_handoff.py:9-12` | yes | the "which keys cross the node boundary … ORCH_CHANNELS" claim |
| `src/film_pipeline/graph/orchestrator_state.py:93-165` | yes | `ORCH_CHANNELS` tuple spans 93–165; no row for either key |
| `src/film_pipeline/graph/state_schema.py:157,167` | yes | `157 consensus_report_ref: str`; `167 qc_patch_ref: str` |
| `tests/unit/graph/test_channel_registry.py:35-37,71-72,200-205,292-293` | yes | sweep scope, `startswith("_orchestrator")` at 72, the "no hidden local key lists" test at 200, `_sweep_scope` return at 293 |
| prior art `documentation/reviews/arch-lens-dataflow.md:119` | **NO** | line 119 is `**RECOMMENDATION — unify, don't isolate.**` (the QC-core recommendation) |

**Reproduce (verbatim) and real output:**

```
$ grep -rn "consensus_report_ref\|qc_patch_ref" src/film_pipeline/graph/orchestrator_state.py
(exit=1)   # 0 rows
$ grep -rn "_QC_REF_KEYS\|ref_keys" src/film_pipeline/graph/nodes/qc.py
src/film_pipeline/graph/nodes/qc.py:30:_QC_REF_KEYS: tuple[str, ...] = ("consensus_report_ref", "qc_patch_ref")
src/film_pipeline/graph/nodes/qc.py:42:    updates = _collect_updates(gate_updates, new_state, state, _QC_REF_KEYS)
src/film_pipeline/graph/nodes/qc.py:51:    ref_keys: tuple[str, ...],
src/film_pipeline/graph/nodes/qc.py:61:    for key in ref_keys:
$ grep -n "_EXTRA_SWEEP_KEYS" -A 3 tests/unit/graph/test_channel_registry.py
35:_EXTRA_SWEEP_KEYS = frozenset(
36-    {"artifact_refs", "generation_requests", "_qc_reports", "_qc_raw_reports"}
37-)
38-
--
293:    return frozenset(spec.key for spec in ORCH_CHANNELS) | _EXTRA_SWEEP_KEYS
$ grep -n "startswith(\"_orchestrator\")" tests/unit/graph/test_channel_registry.py
72:    registered = {spec.key for spec in ORCH_CHANNELS if spec.key.startswith("_orchestrator")}
81:        field for field in StudioGraphState.__annotations__ if field.startswith("_orchestrator")
102:    if key.startswith("_orchestrator"):
```

**Drift proof — attacked, mutation CONFIRMED silent.**

```
MUTATION 3: F-VR-13 rename state_schema fields 157/167
applied
--- F-VR-13 mutated (all graph tests) ---
======================== 255 passed, 2 skipped in 3.47s ========================
```

All 255 graph tests pass after renaming the two `StudioGraphState` fields while `qc.py` keeps writing
the old names. The structural-blindness claims are also verified by reading: the parity test filters
to `startswith("_orchestrator")` (`:72`), and `_sweep_boundary_writes` only records
`isinstance(target.slice, ast.Constant)` subscripts in scope (`:282-288`), so `updates[key]` at
`qc.py:64` is invisible.

**Defects.**

1. **Prior-art anchor is wrong.** "the broader 'state keys are declared in more than one place'
   theme is `documentation/reviews/arch-lens-dataflow.md:119`" — line 119 is the QC-core
   `RECOMMENDATION`. The phrase does not occur in the file at all
   (`grep -rn "declared in more than one place\|state keys are"` → no hits). The real prior art is
   `arch-lens-dataflow.md:8` (`F-1 — The side-channel propagation allowlist is a fixed key list …`)
   and its lines 13–17, 53, which say exactly this. As written, the A7 citation is unverifiable.
2. **The evidence block is from an unshipped script.** The
   `'consensus_report_ref': in ORCH_CHANNELS=False in sweep_scope=False in GraphState=True` output is
   attributed to `/tmp/sweep.py`, which is not part of the finding. The `Reproduce` greps do allow a
   reader to re-derive each conjunct (I did), but §1.6.4 requires the command that produces the
   printed output to be recorded.
3. **Minor basis gap.** The claimed count/magnitude is descriptive; no numeric magnitude is printed.

**Double-counting — disclosed and acceptable.** The finding explicitly differentiates itself from
`F-VR-05` ("F-VR-05 covers the *two writers*, this finding covers the *unregistered channel*"), and I
agree the invariants differ. No silent duplicate.

**Severity (§1.5).** The drifted value is a *policy/registration* fact, and at HEAD the two keys do
survive the node boundary (`_collect_updates` copies them by hand), so there is no live wrong
behaviour. The finding's own blast radius is future-facing ("a future channel-policy change silently
skips them"). The program has already set precedent for exactly this: verify-07 downgraded
`F-ARTIFACT-03` and `F-ARTIFACT-08` to **impact 2** as "latent-policy duplication … the concern is
inert at HEAD". By the same rule this is impact 2 × drift 4 = **Medium (8)**, not High (3 × 4 = 12).
`F-VR-05` keeps impact 3 because it has a live routing defect; `F-VR-13` does not.

**Class.** O5 is a stretch ("policy-by-branch" is normally N call sites of one decision); O8/O7 fit
better for "a node declares its own boundary key set". I would not reject over the label, but it
should be justified or changed.

### Verdict: `DOWNGRADED` — **Medium (impact 2 × drift 4 = 8)** (was High 12). Fix the prior-art anchor to `arch-lens-dataflow.md:8` (and `:13-17`/`:53`), and ship the sweep command.

---

## F-VR-14 — `validation_refs` vs the registered `validation_report_refs` channel

**Anchor re-derivation** (audit `08` lines 1156–1214): all resolve.

| Anchor | Resolves? | Line actually found |
|---|---|---|
| `src/film_pipeline/mcp/tools/validation.py:274-276` | yes | `274 active["_validation_reports"] = reports`; `275 active.setdefault("validation_refs", []).extend(saved_refs)`; `276 rt.projects[project_id] = active` |
| `src/film_pipeline/graph/state_schema.py:173` | yes | `validation_report_refs: Annotated[list[str], merge_unique]` |
| `src/film_pipeline/graph/orchestrator_state.py:163` | yes | `"validation_report_refs", "append_only", "append-only report-ref reducer channel"` |
| `src/film_pipeline/graph/nodes/_agent_handoff.py:31` | yes | `validation_report_refs`` are append-only reducer channels;` |
| `src/film_pipeline/app/_graph_exec.py:470` | yes | `"validation_report_refs": merge_unique,` |

**Reproduce (verbatim) and real output:**

```
$ grep -rn "validation_refs\|validation_report_refs" --include=*.py src
src/film_pipeline/artifacts/store.py:155:            validation_refs=meta.validation_refs,
src/film_pipeline/artifacts/store.py:182:            validation_refs=meta.validation_refs,
src/film_pipeline/artifacts/store.py:540:            "validation_refs": list(meta.get("validation_refs", [])),
src/film_pipeline/artifacts/store.py:724:        validation_refs=envelope.validation_refs,
src/film_pipeline/artifacts/store.py:745:        validation_refs=list(raw.get("validation_refs", [])),
src/film_pipeline/artifacts/store.py:823:    for key in ("characters", "asset_refs", "reference_refs", "validation_refs"):
src/film_pipeline/artifacts/envelope.py:109:    validation_refs: list[str] = Field(default_factory=list)
src/film_pipeline/artifacts/envelope.py:145:    validation_refs: list[str] = Field(default_factory=list)
src/film_pipeline/app/_graph_exec.py:470:        "validation_report_refs": merge_unique,
src/film_pipeline/graph/nodes/qc.py:428:                    append={"validation_refs": [report.validator_id]},
src/film_pipeline/graph/nodes/_agent_handoff.py:31:    ``issues`` and ``validation_report_refs`` are append-only reducer channels;
src/film_pipeline/graph/state_schema.py:173:    validation_report_refs: Annotated[list[str], merge_unique]
src/film_pipeline/graph/orchestrator_state.py:163:        "validation_report_refs", "append_only", "append-only report-ref reducer channel"
src/film_pipeline/checkpoints/manager.py:32:        validation_refs: list[str] | None = None,
src/film_pipeline/checkpoints/manager.py:51:            validation_refs=validation_refs or [],
src/film_pipeline/mcp/tools/validation.py:275:    active.setdefault("validation_refs", []).extend(saved_refs)
src/film_pipeline/schemas/repair.py:53:    validation_report_refs: list[str] = Field(default_factory=list)
src/film_pipeline/schemas/matrix.py:72:    validation_refs: list[str] = Field(default_factory=list)
src/film_pipeline/schemas/audit.py:29:    validation_refs: list[str] = Field(default_factory=list)
src/film_pipeline/schemas/checkpoint.py:42:    validation_refs: list[str] = Field(default_factory=list)
src/film_pipeline/schemas/artifact.py:66:    validation_refs: list[str] = Field(default_factory=list)
src/film_pipeline/schemas/artifact.py:91:    validation_refs: list[str] = Field(default_factory=list)
$ grep -rn "validation_report_refs" --include=*.py src | wc -l   # 5, none a writer
       5
```

**Drift proof — attacked and CONFIRMED, including the count basis.** The `wc -l` in the `Reproduce`
block really does print `5`, matching the text; the five hits are exactly the ones the finding
enumerates. I additionally checked the "written only at `validation.py:275`, read nowhere" half:

```
$ grep -rn '\["validation_refs"\]\|get("validation_refs"' --include=*.py src tests
src/film_pipeline/mcp/tools/validation.py:275:    active.setdefault("validation_refs", []).extend(saved_refs)
$ grep -rn "validation_refs" --include=*.py tests
tests/unit/artifacts/test_store_v2.py:325:            validation_refs=["validation:abc"],
tests/unit/artifacts/test_store_v2.py:333:        assert envelope.validation_refs == ["validation:abc"]
```

The only test hits are the per-artifact `ArtifactEnvelope.validation_refs` field, not the project-state
key — so the project-state key is read nowhere. Mutation confirmed silent:

```
MUTATION 1: F-VR-14 remove validation_report_refs ORCH_CHANNELS row
--- F-VR-14 mutated (channel registry) ---
======================== 27 passed, 1 skipped in 2.81s =========================
# pristine baseline: 29 passed, 2 skipped (31 items) -> mutant collects 28 items
```

No test fails. One nuance worth recording: the collection count drops from 31 to 28 because three
tests are parametrized over `ORCH_CHANNELS` (`test_channel_registry.py:113,132,150,163`), so CI stays
green while coverage shrinks. That is still "nothing fails" as claimed.

**Severity (§1.5).** Medium (2 × 4 = 8) is correct: the live consequence is that the
report↔artifact relation is not reconstructible from graph state for MCP-run validations
(recoverable, no deliverable corruption), and nothing pins the registered channel to a writer.

**Double-counting.** None: `F-VR-13` owns a different key pair
(`consensus_report_ref`/`qc_patch_ref`); the neighbouring theme is shared but the keys, writers and
consequences are distinct.

**Class / prior art.** O3 is correct. Prior art is honest: it acknowledges the audit's own §4.3
listed the key without a finding, and otherwise states "new at HEAD". No defect found.

### Verdict: `CONFIRMED` — Medium (2 × 4 = 8).

---

## F-VR-15 — The registered `run_validation` tool cannot reach four of the six declared phase arms

**Anchor re-derivation** (audit `08` lines 1216–end): all resolve.

| Anchor | Resolves? | Line actually found |
|---|---|---|
| `src/film_pipeline/mcp/tools/validation.py:297-306` | yes | `297 try:`; `298 if phase_str == "visual_dev":`; `300 elif phase_str == "script":`; `305 if not reports:`; `306 return _ok(message="No validators found for this phase.")` |
| `src/film_pipeline/mcp/tools/validation.py:138-157` | yes | the four unreachable arms — `139 phases=("gen_planning",)`, `144 phases=("shot_bible",)`, `149 phases=("post", "assembly")`, `154 phases=("delivery",)` |
| `src/film_pipeline/mcp/tools/registry.py:240` | yes | `_register(registry, "run_validation", ToolGroup.VALIDATION, run_validation, mutates=True)` |
| `src/film_pipeline/mcp/tools/validation.py:343-347` | yes | `345 reports=_run_live_validators(rt, store, project_id, fp, phase_str),`; `346 source="live",` |
| `tests/unit/mcp/tools/test_validation.py:45-58` | yes | `53 active["current_phase"] = "intake"`; `57 assert result["ok"] is True`; `58 assert result["message"] == "No validators found for this phase."` |
| `tests/unit/mcp/tools/test_validation.py:227-240,243-256` | yes | the two other assertions of the same message (visual_dev / script) |
| `src/film_pipeline/app/services/operator.py:310` | yes | `310 def run_validation(self, project_id: str | None = None) -> ValidationWorkspace:` |

**Reproduce (current revision, verbatim) and real output:**

```
$ grep -n "def run_validation" -A 30 src/film_pipeline/mcp/tools/validation.py
280:async def run_validation(args: dict[str, object]) -> dict[str, object]:
...
297-    try:
298-        if phase_str == "visual_dev":
299-            reports, saved_refs = _validate_visual_dev(rt, store, project_id, fp, active)
300-        elif phase_str == "script":
301-            reports, saved_refs = _validate_script(store, project_id, fp)
302-    except Exception as exc:
303-        return _error(f"Validation run failed: {exc}")
304-
305-    if not reports:
306-        return _ok(message="No validators found for this phase.")
$ grep -n "_live_validator_specs" -A 36 src/film_pipeline/mcp/tools/validation.py | grep "phases="
45:129-            phases=("script",),
50:134-            phases=("visual_dev",),
55:139-            phases=("gen_planning",),
60:144-            phases=("shot_bible",),
65:149-            phases=("post", "assembly"),
70:154-            phases=("delivery",),
$ grep -rn '"run_validation"' src/film_pipeline/mcp/tools/registry.py
src/film_pipeline/mcp/tools/registry.py:240:    _register(registry, "run_validation", ToolGroup.VALIDATION, run_validation, mutates=True)
$ grep -n "No validators found for this phase" -r src tests
src/film_pipeline/mcp/tools/validation.py:306:        return _ok(message="No validators found for this phase.")
tests/unit/mcp/tools/test_validation.py:58:    assert result["message"] == "No validators found for this phase."
tests/unit/mcp/tools/test_validation.py:240:    assert result["message"] == "No validators found for this phase."
tests/unit/mcp/tools/test_validation.py:256:    assert result["message"] == "No validators found for this phase."
```

The six-arm claim is now directly countable from the recorded command, and the current title
("four of the six declared phase arms (five of the seven phases)") correctly resolves the earlier
"four of the six phases" vs five-phase-names ambiguity. That wording defect was present in the
revision I first read and is **fixed** in the pinned revision — I do not count it.

**Drift proof — attacked, mutation CONFIRMED silent.**

```
MUTATION 2: F-VR-15 add intake arm to _live_validator_specs
--- F-VR-15 (mcp validation) ---
============================== 23 passed in 2.97s ==============================
```

The registered tool's `if/elif` is a literal two-branch dispatch, so an added arm is unreachable and
no test fails. The "exactly one consumer / one call site" claim is confirmed:
`_live_validator_specs` is defined at 123, consumed at 166 and called from `get_validation_report` at
345 (read-only registration at `registry.py:191`, `mutates=True` only for `run_validation`).

**Double-counting — real and material.** Audit 08's already-verified **`F-VR-07`** already contains
this exact divergence in its drift proof (current file, lines 737–743):

> "The MCP arm is narrower still than its table implies: the *registered* `run_validation` tool …
> dispatches only two phases — `…:298-301` (`if phase_str == "visual_dev":` / `elif phase_str ==
> "script":`) — and otherwise returns the success-shaped `if not reports:` / `return _ok(message="No
> validators found for this phase.")` (`:305-306`), so its `delivery` `_PhaseSpec` is unreachable
> through that tool."

`F-VR-15` is the post-verification sibling of the first-round `F-VR-07` describing the same owners
(`mcp/tools/validation.py:298-306`, `registry.py:240`). Its increment is narrower than claimed: it
generalises from "delivery unreachable" to "all four non-dispatched arms unreachable" and adds the
observation that `tests/unit/mcp/tools/test_validation.py` pins the refusal as correct. The
`F-VR-15` prior art ("**What is new at HEAD**: the divergence is now shown to exist *inside* the MCP
module") is inaccurate: `F-VR-07`'s corrected drift proof already showed it. The two must be merged
or explicitly cross-referenced so the same dispatch gap is not counted twice.

**Severity (§1.5).** High (3 × 4 = 12) is defensible on its own: `ok: true` with no reports for a
declared phase is a live, misleading success response (wrong internal/operator-facing behaviour,
recoverable), and the mutation is silent. But because it is the same seam as `F-VR-07` (already
High 12), the pair should not both carry High — one finding, one score.

**Class / prior art.** O4 + O5 is correct. Prior art
`documentation/reviews/arch-lens-boundaries.md:161` resolves (the hardcoded QC/MCP validator tables
bullet). No missing prior art.

### Verdict: `CONFIRMED-WITH-FIX` — High (3 × 4 = 12), band unchanged, conditional on merging/ cross-referencing with `F-VR-07`.

---

## Summary verdict table

| Finding | Verdict | Severity as filed | Severity after review | Principal defect |
|---|---|---|---|---|
| `F-ARTIFACT-10` | **CONFIRMED-WITH-FIX** | High 12 | High 12 (unchanged) | `graph.py:119` should be `graph.py:115` (contradicts `F-VR-03`); unacknowledged overlap with `F-ARTIFACT-03`/`F-VR-03` |
| `F-ARTIFACT-11` | **CORRECTED** | Medium 8 | **Medium 6** (2 × 3) | Mutation proof falsified: `test_second_delivery_does_not_re_record_sidecars` fails |
| `F-ARTIFACT-12` | **CONFIRMED** | High 12 | High 12 | none (traversal reproduced end-to-end; `Reproduce` could ship the probe) |
| `F-ARTIFACT-13` | **REJECTED** | Medium 8 | **Low 2** (1 × 2) if re-filed as dead code | §1.6.3 proof fails: phase column never read; `FilmPhase` rename fails 19 tests |
| `F-VR-12` | **CONFIRMED-WITH-FIX** | High 12 | High 12 (band), reconcile with `F-ARTIFACT-02` 16 | Stated output block is not the command's output (§1.6.7); wrong prior-art anchor; cross-audit duplicate of `F-ARTIFACT-02` |
| `F-VR-13` | **DOWNGRADED** | High 12 | **Medium 8** (2 × 4) | Latent, not live (precedent: `F-ARTIFACT-03`/`F-ARTIFACT-08`); wrong prior-art anchor `:119`; unshipped `/tmp/sweep.py` |
| `F-VR-14` | **CONFIRMED** | Medium 8 | Medium 8 | none |
| `F-VR-15` | **CONFIRMED-WITH-FIX** | High 12 | High 12 (band) | Double-counts `F-VR-07`, whose drift proof already states the same dispatch gap |

**Tally:** 2 CONFIRMED, 3 CONFIRMED-WITH-FIX, 1 CORRECTED, 1 DOWNGRADED, 1 REJECTED.

---

## What the authors should fix

1. **`F-ARTIFACT-10` — wrong anchor (must fix).** `src/film_pipeline/graph/graph.py:119` is
   `# Human gate nodes`; the forward binding is at `graph.py:115`. Audit 08's `F-VR-03` already
   records 115, so the two audits currently disagree at the same commit. Also cite `F-ARTIFACT-03`
   and `F-VR-03` explicitly and state the increment (version-resolution rule; two `latest` helpers).
2. **`F-ARTIFACT-11` — replace the falsified drift proof.** Delete "no test fails": the mutation
   `_asset_kind -> "clip"` fails
   `tests/unit/artifacts/test_state_persistence.py::TestMediaLayout::test_second_delivery_does_not_re_record_sidecars`
   (asserts `len(clip_entries) == 2` at `:408` and the one-active-take invariant at `:411`). Re-base
   the finding on (a) the existing vocabulary divergence and (b) the genuinely untested
   `_asset_kind` classifier, and re-score to Medium 6 (drift 3). Cross-reference `F-ARTIFACT-08`.
3. **`F-ARTIFACT-12` — no correction required.** Consider promoting the traversal probe into the
   `Reproduce` block (the two shipped commands do not produce the paths-outside-root evidence), and
   move the `tests/` zero-hit grep into it.
4. **`F-ARTIFACT-13` — reject or re-file, do not patch.** The phase element of
   `_UPSTREAM_CONTENT_SOURCES` is provably dead: `_context.py:351` binds it to `_phase_name` and no
   `Load` of that name exists in the module, and `_compact_upstream_content` derives the phase from
   `_parse_ref(ref)`. Setting every phase literal to `"zzz_phase"` passes all 31 context tests, and
   the finding's own mutation ("rename a `FilmPhase`") fails 19 tests. Either move it to §1.6.6 as a
   Low dead-code cleanup (remove the unused column) or re-file the live concern (the ref-key →
   content-key injection policy) with a real drift proof.
5. **`F-VR-12` — fix the output block, the prior-art anchor, and the double-count.**
   (a) The printed drift-proof block has two lines embellished with `| renderer = …` /
   `| payload_model = …` and one line (`consensus_report in ArtifactType? False`) the script never
   prints; either print them in the `Reproduce` script or paste the real four-line output.
   (b) `docs/clean-code-refactor/BASELINE.md:261` is the `validation/consensus.py` coverage row, not
   "stringly-typed artifact typing" (the phrase is absent from the file); cite the correct prior art
   or drop it.
   (c) Cross-reference `F-ARTIFACT-02` (Critical 16) and reconcile severity — the same
   map/coercion/`consensus_report` seam is currently filed twice at 16 and 12.
6. **`F-VR-13` — downgrade to Medium 8 and fix prior art/evidence.** No live behavioural
   divergence today (the keys survive via `_collect_updates`), so impact is 2 under the precedent set
   for `F-ARTIFACT-03`/`F-ARTIFACT-08`. `documentation/reviews/arch-lens-dataflow.md:119` is the
   QC-core recommendation; the actual theme is `:8` (F-1) and `:13-17`/`:53`. Ship the sweep command
   that produces the `in ORCH_CHANNELS=… in sweep_scope=… in GraphState=…` block instead of citing
   `/tmp/sweep.py`. Retain the disclosed `F-VR-05` differentiation.
7. **`F-VR-14` — no correction required.** The `wc -l` basis matches (5), the mutation is silent, and
   the key is written only at `validation.py:275` and read nowhere. Optionally note that removing the
   row silently drops three parametrized `test_channel_registry` cases while staying green.
8. **`F-VR-15` — resolve the `F-VR-07` double-count.** `F-VR-07`'s corrected drift proof already
   states that the registered `run_validation` tool dispatches only two phases and returns the
   success-shaped refusal, so the same gap is filed twice at High 12. Merge them, or make `F-VR-15`
   the owning finding for the dispatch gap and reduce `F-VR-07`'s drift proof to a cross-reference.
9. **Both files — pin the moving target.** Both audit files were edited during this verification
   (`07` at `26b0a099…`, `08` at `83dea2b0…`). Any verdict in an already-written verifier file that
   cites line numbers now points at the wrong lines; dependent documents should be re-derived rather
   than hand-patched, per §1.6.8.
10. **General (A2/§1.6.4).** Across these eight, the printed magnitude/ordinal ("two paths",
    "fifth vocabulary", "four of the six arms") is frequently not produced by the recorded
    `Reproduce` command. Where a count matters, make the command print it (as `F-VR-14`'s `wc -l`
    does); this is the same text-vs-command basis weakness flagged for `F-ARTIFACT-08`.

---

## Appendix — raw evidence

Full transcript files (scratch only, not deliverables): `/tmp/v19-repro-a.txt`,
`/tmp/v19-repro-b.txt`, `/tmp/v19-mutations.txt`.

Mutation matrix actually executed (all in `/tmp/v19work`; every file restored afterwards; verified
byte-identical `.py` sources to `/tmp/v19`):

| # | Finding | Mutation | Test set | Result | Silent? |
|---|---|---|---|---|---|
| 1 | `F-VR-14` | delete `validation_report_refs` `ORCH_CHANNELS` row | `tests/unit/graph/test_channel_registry.py` | 27 passed, 1 skipped (was 29/2) | **yes** |
| 2 | `F-VR-15` | add `phases=("intake",)` arm | `tests/unit/mcp/tools/test_validation.py` | 23 passed | **yes** |
| 3 | `F-VR-13` | rename `state_schema.py:157,167` fields | `tests/unit/graph` | 255 passed, 2 skipped | **yes** |
| 4 | `F-ARTIFACT-11` | `_asset_kind` returns `"clip"` | manifest/executor/state-persistence set | **1 failed**, 90 passed (was 91 passed) | **NO** |
| 5 | `F-ARTIFACT-13` | table phase literals → `"zzz_phase"` | context set | 31 passed | silent but inert |
| 6 | `F-ARTIFACT-13` | `FilmPhase.CONSTITUTION = "constitution_x"` (the finding's own wording) | graph + artifacts + schemas | **19 failed**, 348 passed, 2 skipped | **NO** |
| 7 | `F-ARTIFACT-12` | traversal probe with intermediate phase dir present | direct call | path resolves outside root; file parsed; content in `ValidationError` | live divergence reproduced |

Constraint compliance: the only file written by this verifier is
`docs/modular-architecture/reviews/verify-19.md`; no `src/`, `tests/`, root config, or audit file was
modified; no git state-changing command was run; `git status --porcelain` is empty (`docs/` is
gitignored).
