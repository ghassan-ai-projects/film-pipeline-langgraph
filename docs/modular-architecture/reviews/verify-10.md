# verify-10 — Independent verification of `audit/10-checkpoints-and-runtime-persistence.md`

**Verifier:** a second agent that did **not** write audit 10. Every claim below was
re-derived from a pristine snapshot of the audited commit; no anchor was taken from the
audit's own text.

- **Audited commit:** `fb85baa0e6b769b709791a96a89980089304bf13` (`fb85baa`).
- **File verified:** `docs/modular-architecture/audit/10-checkpoints-and-runtime-persistence.md`
  — 11 findings, `F-CRP-01` … `F-CRP-11`.
- **Method:** `git archive fb85baa | tar -x -C /tmp/crp-snap` (plus three extra pristine
  copies under `/tmp` for mutation runs). Probes: `PYTHONPATH=/tmp/crp-snap/src
  .venv/bin/python /tmp/crp-probes/<probe>.py`. Static checks re-run verbatim from the
  audit's own `Reproduce:` lines. **Scope deviation from the brief, recorded:** the repo's
  pytest config hard-wires `--cov-fail-under=90`, which makes any subset run fail by
  construction, so the cited test files were run with `--no-cov`. Mutation runs were
  executed against the disposable snapshot only; see "Command log".
- **Bar applied:** `00-methodology-and-quality-bar.md` §1.4 (O-taxonomy), §1.5 (severity =
  impact × drift), §1.6 (evidence rules), bar **A6**.

---

## 1. Verdicts

| finding id | verdict | one-line reason |
|---|---|---|
| F-CRP-01 | CONFIRMED (severity **disputed**) | Divergence reproduces exactly, including `StorageRootError`; a *fourth* poisoning path the audit missed makes it worse, but the finding's headline claim "five *independent* paths" is one path too many (R3 → R2 is a chain, not a coincident path) |
| F-CRP-02 | CONFIRMED | Two registries, split validate/execute reproduced verbatim; mutation of `app/_persistence.py:145` leaves the whole unit suite green (1866 passed, 3 skipped) |
| F-CRP-03 | CONFIRMED | Producer literal pinned, consumer key unpinned, no shared contract; mutation of `graph/nodes/_shared.py:190` leaves both named test files green (49 passed) |
| F-CRP-04 | CONFIRMED (repro had to be corrected) | Empty `artifact_versions` → empty invalidation report → `"No checkpoint found containing artifact 'x'."` reproduced; the audit's Appendix A.6 is not executable as written |
| F-CRP-05 | CONFIRMED, **downgraded High→Medium (4×3=12 → 3×3=9)** | Every cited absence proof re-ran true; the drifted lifecycle is dead code with no caller, so impact 4 overstates §1.5 |
| F-CRP-06 | CONFIRMED | Both id grammars and both `invalidation_report_ref` values verified at HEAD; no rollback audit action anywhere in `src/` |
| F-CRP-07 | CONFIRMED | Static map is not derived from the registry or from `built_from`; `grep -rn "DEPENDENCY_GRAPH" tests/` → no match |
| F-CRP-08 | CONFIRMED | Adoption-with-checkpoint-log reproduced: `rt.checkpoints size: 0`, on-disk log still 1 line |
| F-CRP-09 | CONFIRMED (one sub-claim **unsupported**) | The truth table reproduces byte-for-byte on the four required rows; the row-4 label `NO_PERSIST=0` is false under a presence test, and the storage-root sentence conflates "public default" with "effective root" |
| F-CRP-10 | CONFIRMED, **downgraded High→Medium (3×3=9 → 2×3=6)** | All four sites and the absence proof verified; mutation of `_text_only.py:9` leaves `tests/unit/mcp/tools/test_generation.py` green (41 passed) — but impact 3 requires a live caller, and only the auto path has one |
| F-CRP-11 | CONFIRMED | Reproduced verbatim: archived audit log `['create_project']` vs in-memory `['create_project', 'delete_project']` |

**Counts: CONFIRMED 11 / DOWNGRADED 2 (F-CRP-05, F-CRP-10, both already counted CONFIRMED
above) / REJECTED 0.** Net: 9 confirmed-as-scored, 2 confirmed-with-recomputed-severity,
0 rejected, 0 UNVERIFIED.

Every one of the 11 findings clears §1.6.3 (each has either a reproduced existing
divergence or a mutation scenario whose silence I executed, not merely predicted). **No
finding was rejected**, so under §1.6.6 nothing needs deleting or relabelling as a
hypothesis.

---

## 2. Expanded rows — non-CONFIRMED and disputed

### 2.1 F-CRP-05 — CONFIRMED evidence, recomputed severity

**Class claim** (O6 + O3) verified: `checkpoints/resume.py` is a complete second resume
lifecycle with no consumer, and `state/graph-state.json` is write-only.

```
$ grep -rn "ResumeManager\|ResumeSnapshot\|BranchManager" --include=*.py src/
src/film_pipeline/checkpoints/resume.py:26:class ResumeManager:
src/film_pipeline/checkpoints/__init__.py:9:from film_pipeline.checkpoints.resume import ResumeManager, ResumeSnapshot
   (no other hit outside the defining modules and the export surface)
$ grep -rn "read_graph_state" --include=*.py src/
src/film_pipeline/artifacts/project_storage.py:23:    snapshot = storage.read_graph_state("p1")     # docstring example
src/film_pipeline/artifacts/project_storage.py:167:    def read_graph_state(self, project_id: str) -> GraphStateSnapshot | None:
```

Both absence proofs are exact. So is the sole read-only mention in the test tree
(`tests/unit/artifacts/test_storage_boundary.py:152` is a *method-name allow-list* entry,
confirmed by reading `:145-160`, not a functional reader).

**Recomputed severity — DOWNGRADED to Medium (impact 3 × drift 3 = 9).** §1.5 impact 5 is
"wrong behavior reaches a human deliverable or corrupts durable data"; 3 is "wrong internal
behavior, recoverable". The audit scores 4 on the argument that "a crashed run cannot be
resumed from the on-disk snapshot". That is true, but the snapshot has **no reader and no
caller anywhere**, so the observable behaviour of a crashed run is exactly what it would be
if `checkpoints/resume.py` and `save_graph_state` did not exist: the resume path is
`app/_graph_exec.py:194` (`graph.get_state(config)`), which works whenever the checkpointer
is durable. The defect is an unowned, unused lifecycle — a B4 "assign or delete" item — not
corrupted durable data. Drift 3 stands: nothing fails if the dead modules change, and the
audit's own §5.6 already files them under "dead code with no ownership, not ownership
seams", which is in tension with scoring them at impact 4 here.

### 2.2 F-CRP-10 — CONFIRMED evidence, recomputed severity

**All four sites verified verbatim at HEAD:**

```
src/film_pipeline/app/_resume.py:14:_STALE_REQUEST_CODES = frozenset({"empty_generation_requests", "no_generation_requests"})
src/film_pipeline/app/services/_generation_ops.py:20:_STALE_REQUEST_CODES = frozenset({"empty_generation_requests", "no_generation_requests"})
src/film_pipeline/mcp/tools/generation/_text_only.py:9:_STALE_ISSUE_CODES = frozenset({"empty_generation_requests", "no_generation_requests"})
src/film_pipeline/graph/orchestrator_validators/planning_gates.py:254: "no_generation_requests", / :263: "empty_generation_requests",
```

Absence proof re-run: `grep -rn "_STALE_ISSUE_CODES\|_STALE_REQUEST_CODES" tests/ --include=*.py`
→ **exit 1, no match**. Mutation executed: in the pristine copy,
`_text_only.py:9` reduced to `frozenset({"empty_generation_requests"})`; then
`pytest tests/unit/mcp/tools/test_generation.py --no-cov` → **41 passed**. The audit's
"no test fails" claim is exactly right.

**Recomputed severity — DOWNGRADED to Medium (impact 2 × drift 3 = 6).** The drifted module
is reachable only through the text-only generation policy, whose sole caller is the
`plan_generation_batch` tool path (`mcp/tools/generation/_text_only.py`); the auto/resume
paths use `app/_resume.py:14`, which *is* pinned
(`tests/unit/app/test_resume_integrity.py:409-411`). A dormant copy whose divergence cannot
reach a live path is precisely §1.5's "recoverable internal" band, not 3. The audit's own
sentence — "the two *other* sites are mutually pinned … which is why the drift is 3 rather
than 4" — concedes that most of the vocabulary is bound; the impact integer should follow.

### 2.3 F-CRP-01 — CONFIRMED divergence, disputed framing (severity not changed)

**The expensive claim reproduces end-to-end.** Probe `/tmp/crp-probes/roots.py`, verbatim
output:

```
[S1] APP  project dir = <tmp>/s1/p1
[S1] CLI  project dir = <tmp>/s1/runs/default/artifacts/p1
[S1] SAME? False
[S2] after CLI run, children of storage root: ['runs']
[S2] CLI marker at <tmp>/s2/runs/default/artifacts/storage.json exists: True
[S2] app FAILED to open the storage root: StorageRootError
[S2] direct ArtifactStore(storage_root) -> StorageRootError
[S3] app runtime_root = <tmp>/rt3
[S3] APP  project dir = <tmp>/rt3/p1
[S3] CLI  project dir = <tmp>/s3/runs/default/artifacts/p1
```

and the R5 split (probe `/tmp/crp-probes/r5.py`):

```
[S4] R2 module-level cp dir    = <tmp>/storage/checkpoints
[S4] R5 app cp dir             = <tmp>/runtime/checkpoints
[S4] R2 == R5 dir? False
```

So: the CLI store root really is `<run_root>/artifacts` (`cli/driver.py:69`), the app store
root really is the runtime root itself (`app/runtime.py:75-77`), the same project id really
maps to two directories, and the CLI really poisons the shared root against the app. The
"unmarked, non-empty directory" mechanism is exactly `artifacts/storage.py:157-164`.

**Dispute D1 — "five independent paths" is four independent paths plus one chain.** §2.4
lists R1…R8, of which R4 (`app/runtime.py:58-69`) calls `configured_runtime_root()`, i.e.
**R3**, and R2 is defined as *derived from* R1. The finding's own de-facto-owner list quotes
`app/_persistence.py:41-42` as an owner, but that is not an independent answer — it delegates
to `default_runtime_root()` (`artifacts/storage.py:69`), which *is* R1. Independent formulas
are: {R1 storage root}, {R6 run root}, {`driver.py:69` store root}, {`graph.py:46` cp dir}.
The divergence and the severity are unaffected (5 × 4 = 20 → Critical stands; if anything I
would re-score drift 5, not 4, because the suite *pins the wrong value*:
`tests/unit/cli/test_help_snapshot.py` freezes `<storage root>/../runs/default`, and no test
composes `default_run_root()` with `driver.py:69`). Candidate needed: the count sentence.

**Dispute D2 — the audit understates F-CRP-01 by omitting the import-time poisoning path.**
See "Missed in scope" M1: `graph/graph.py:201` (`graph = build_graph()`) is executed on any
`import film_pipeline.graph.graph` while `PERSIST_STATE=1`, and it creates
`default_checkpoints_root()` inside the storage root. Probe output:

```
[S5] after `import graph.graph`, children of storage root: ['checkpoints']
[S5] app FAILED to open storage root after graph.graph import: StorageRootError
```

This is the *same* failure mode the finding's blast radius attributes to the CLI, reached
from the `langgraph.json` entry point alone. The audit folds it in as "two SQLite files
exist" (§2.4 last paragraph, §7.3) but never tests the poisoning consequence, which is the
stronger claim and belongs in the blast radius.

### 2.4 F-CRP-04 — CONFIRMED, repro corrected

All six anchors verified verbatim, including that `app/runtime.py:253` makes the omission
legal:

```
src/film_pipeline/app/runtime.py:253:        artifact_versions: dict[str, str] | None = None,
src/film_pipeline/checkpoints/manager.py:49:            artifact_versions=artifact_versions or {},
```

Probe `/tmp/crp-probes/manual_cp.py` (using the real MCP handlers, not a paraphrase):

```
MCP create_checkpoint -> {'ok': True, 'checkpoint_id': 'checkpoint:p1:intake:42b3100d', ...}
checkpoint.artifact_versions = {}
get_invalidation_report.will_invalidate = []
rollback_artifact(no explicit cp) -> {'ok': False, 'error': "No checkpoint found containing artifact 'x'."}
```

**Dispute D3 — Appendix A.6 is not executable as written.** It calls
`set_candidate_ref(rt.get_project("p1"), "script", "artifact:script:v1")`, but the state key
is namespaced (`graph/orchestrator_state.py:27`
`_CANDIDATE_REFS = f"{_ORCH_NS}__candidate_refs"`), so seeding the raw dict key is invisible
to `get_candidate_refs`; and `runtime.create_checkpoint` is given no `artifact_versions`,
which is the point. In my run the seed line was a no-op (`candidate refs on state: None`)
and the empty map was produced by the *tool* path anyway — the finding survives — but the
appendix as printed does not demonstrate what it claims. Rewrite A.6 to drive
`mcp/tools/checkpoints.py:create_checkpoint` and read the result, as above.

### 2.5 F-CRP-09 — CONFIRMED truth table, two sub-claims corrected

**The truth table reproduces.** Probe `/tmp/crp-probes/truth.py`, verbatim:

```
None  | None     | P1=False | P2=False | P3=<storage root> | P4=production | P5=False | P6=True
None  | '1'      | P1=False | P2=False | P3=<tmp artifacts> | P4=sandbox | P5=False | P6=False
'1'   | None     | P1=True  | P2=True  | P3=<storage root> | P4=production | P5=True  | P6=True
'1'   | '1'      | P1=False | P2=False | P3=<tmp artifacts> | P4=sandbox | P5=False | P6=False
```

This confirms, mechanically: (a) `cli/run.py:226` returns `True` while
`app/_persistence.py:51`, `graph/graph.py:43` and `app/logging_setup.py:78-81` all return
disabled when both flags are unset — the row-1 divergence is real and unpinned in the safe
direction; (b) `NO_PERSIST=1` disables at every site; (c) `NO_PERSIST=0` **disables
persistence at every site** (`PERSIST_STATE=1, NO_PERSIST=0` → all six `False`), which is
the audit's §2.3 claim. Wait — see D5: the audit's row-4 *label* says otherwise, but its
§2.3 prose is right, and my probe confirms the prose.

**Dispute D4 — the finding's storage-root sentence is wrong about the *effective* root.**
F-CRP-09 says row 1 makes P3/P4 "resolve the *production* storage root and profile", and
F-CRP-09's Prior art says the storage plan's `use_persistent_runtime()` gate is "violated
for the CLI, which resolves `<storage root>/runs/default` … regardless of the flags".
`tests/conftest.py:98` sets `FILM_PIPELINE_NO_PERSIST=1` for the whole session, so the test
suite always takes the `_default_artifact_root()` temp branch. `P3 = <storage root>` in my
table is the value of the *public default function*, not the root the app uses; under a
composed `StudioRuntime` the root is `runtime_root` (`app/runtime.py:75-77`) or a per-pid
temp dir (`:67-69`). The finding needs to separate "the library default is home" from "the
effective root in a non-persistent run is temp". Impact is unchanged (the CLI's genuine
`<storage>/runs/default` write is separately confirmed in F-CRP-01), but two sentences must
be corrected.

**Dispute D5 — row 4 of §2.2 is mislabelled.** The table's fourth row is headed
`NO_PERSIST = 0`. But §2.3 correctly states every site tests *presence*, and my probe shows
`'1' | '0'` → P6=False, i.e. `NO_PERSIST=0` behaves exactly like `NO_PERSIST=1`. The row
labelled `1` in the table is the value *truthiness* would give; the value that row 4 should
carry is `NO_PERSIST=0`-as-unset-equivalent-if-you-believe-the-label — internally
inconsistent. Fix the header to `NO_PERSIST=0 (present)` or drop the row.

**Dispute D6 (minor) — "six sites with two formulas" is seven formulas.** `graph/services.py:31`
and `:48` are both counted as one entry (P3/P4 share a table row) but are two distinct
formulas reaching two different decisions (root vs profile). The count sentence in the
finding title should say "six sites, seven derivations" or the table should split P3/P4.

**Cross-cluster collision (must be reconciled, not scored).** F-CRP-09 duplicates
`audit/03-config-profile-and-defaults.md` **F-CFG-08** ("`FILM_PIPELINE_NO_PERSIST` is one
policy decision re-derived in six modules", candidate owner `app/_persistence:492`) —
same concern, same seven read sites, different severity (03 scores 4×3=12, 10 scores
3×3=9) and a different nominated owner. `audit/11:309` already flags this collision
explicitly and proposes a three-way split. Evidence rule §1.6 does not require de-duping
across clusters, but bar A7 does require citing the prior art: F-CRP-09's Prior art names
only `documentation/storage-upgrade-plan.md`, and **must** also cite audit 03's F-CFG-08.

---

## 3. Missed in scope

Ordered by severity. Each is a checkpoint/resume/persistence seam the audit did not report.
They are recorded here as verifier findings, not silently merged into the audit.

### M1 — `import film_pipeline.graph.graph` alone poisons the storage root (Critical, 5×5=25)

- `graph/graph.py:201` — `graph: CompiledStateGraph = build_graph()`
- `graph/graph.py:41-46` — `_default_checkpointer(runtime_root=None)` → `default_checkpoints_root()`
- `artifacts/storage.py:74` — `return resolve_storage_root() / "checkpoints"`
- `artifacts/storage.py:49` — `checkpoint_dir.mkdir(parents=True, exist_ok=True)`

With `PERSIST_STATE=1` and no `RUNTIME_ROOT`, merely importing the module named by
`langgraph.json` creates `<storage root>/checkpoints/`, leaving a non-empty unmarked
directory that `ensure_storage_root` then refuses. Reproduced (`/tmp/crp-probes/r5.py`):
`[S5] after import graph.graph, children of storage root: ['checkpoints']` →
`[S5] app FAILED to open storage root after graph.graph import: StorageRootError`.
The audit's §7.3 records the two-checkpointer-files consequence but never the refusal, and
F-CRP-01 attributes the refusal only to the CLI. Impact 5 (storage root unusable), drift 5
(no test imports the entry-point module against a fresh root and then opens a runtime).

### M2 — `NO_PERSIST` does not gate the root when `RUNTIME_ROOT` is set: a "non-persistent" runtime writes durable state (High, 4×4=16)

- `app/runtime.py:59-63` — `if os.getenv("FILM_PIPELINE_RUNTIME_ROOT", "").strip(): self.runtime_root = configured_runtime_root()` (the policy gate at `:61` is in the *elif*)
- `app/runtime.py:75-77` — store root = `runtime_root`
- `artifacts/storage.py:129-159` — the store then writes `storage.json` and is durable

Probe `/tmp/crp-probes/missed.py`, verbatim:

```
[A] use_persistent_runtime() = False (policy says: not persistent)
[A] StudioRuntime.runtime_root       = <tmp>/real-runtime-root
[A] artifact_store.root              = <tmp>/real-runtime-root
[A] durable project.json written?    = True
[A] durable storage marker written?  = True
```

No test covers this combination: `tests/unit/artifacts/test_storage_guards.py:63` deletes
`PERSIST_STATE` but not `RUNTIME_ROOT`; `tests/unit/app/test_logging_setup.py:148-171`
pins both flags but not the root branch. The storage plan's own bar — quoted by the audit in
F-CRP-09's Prior art, "non-persistent invocations never write home or CWD" — is violated by
design here, and the audit's six-site derivation table has no column for it.

### M3 — `SafetyService.persist_root()` ignores the root in use; delete archives cross-root (High, 4×3=12)

- `app/safety.py:25-32` — `return resolve_storage_root().resolve().parent` — the audit cites this anchor in F-CRP-01's de-facto owner list (R8) but files it as a non-finding
- `app/runtime.py:111` — `root = trash_root or (persist_root() / "trash")`
- `app/runtime.py:153-157` — `delete_project` archives `project_root` to that trash

Probe `/tmp/crp-probes/missed.py`, verbatim:

```
[B] runtime root in use               = <tmp>/explicit-run-root
[B] safety.persist_root()             = <tmp>/home/.film-pipeline
[B] archive actually created under    = ['project-p2-...-p2']
[B] runtime root still contains p2?   = False
```

A project created under an explicit runtime root is moved into a trash directory derived
from a completely different root. The audit's §7.4 records the derivation and explicitly
says "no divergence observed" — that is true of `persist_root()`'s *value* versus
`default_run_root()`'s parent, but not of its *use*: nothing binds it to `rt.runtime_root`.
No test asserts where `delete_project` archives to relative to the runtime root
(`tests/unit/app/test_runtime.py:96-124` sets `STORAGE_ROOT` and asserts only that one
archive exists).

### M4 — `create_checkpoint`'s omitted argument is not the (main) cause of the empty map (Medium, corroborating)

- `mcp/tools/checkpoints.py:167-176` — `list_checkpoints` returns `_checkpoint_summary(c)`, which drops `artifact_versions` (`:85-93`)
- `app/runtime.py:247-279` — `create_checkpoint` **accepts** `artifact_versions` (`:253`, confirmed at runtime: `"artifact_versions" in StudioRuntime.create_checkpoint.__code__.co_varnames` → `True`)

The audit's F-CRP-04 localizes the defect to the tool not passing the argument. The deeper
cause is that the *derivation* lives in `app/_graph_exec.py:102-103` (the auto path) and no
factory owns it — which the audit's own extraction sketch says — but the finding's de-facto
owner list implies the tool could simply pass more. Worth stating explicitly; no score
change.

### M5 — `request_revision` ignores `_has_pending_human_interrupt`'s negative branch twice (Low, recorded not scored)

`app/_graph_exec.py:381-393` falls back to `graph.invoke(recovery_state, config)` when no
human interrupt is pending; `app/_graph_exec.py:232` then applies `_approval_stalled` and
advances manually. This is the same manual-advance seam F-CRP-03 and F-CRP-05 describe for
`approve_phase`, unmentioned for the revision path. No divergence reproduced; recorded for
the reconciliation step only.

---

## 4. Candidate-owner collisions (§6.3 of the audit)

| audit 10 nomination | colliding nomination | assessment |
|---|---|---|
| `runtime_persistence` (§6, F-CRP-01/08) — owns persistence policy + one `RootLayout` | `audit/03:825` records **Storage root resolution** as *single-owned* by `artifacts/storage.py` with guard tests `tests/unit/artifacts/test_storage.py:29-78`, `test_storage_guards.py` | **Real collision.** `resolve_storage_root()` has one reader path today; the audit's `RootLayout` would move R1 out of `artifacts`. Defensible (it is the *composition* of R1–R8 that is unowned, not R1 itself) but §6.5's conformance map must say so, and the guard tests cited by 03 must be reassigned. |
| `runtime_persistence.policy` (F-CRP-09) | `audit/03:492` — `app/_persistence`; `audit/11:309` — `app.bootstrap` (third owner), with an explicit open reconciliation item | **Already escalated by audit 11.** Audit 10 must add the F-CFG-08 prior-art citation (see D6). No collision with `projects`/`config` candidate owners beyond this. |
| `artifacts.provenance` (F-CRP-07) | `audit/07` nominates `film_pipeline.artifacts.contract` / `ArtifactStore` for the kind registry; `audit/06:931` gives `artifacts` "every byte written under a project" | **Coherent, not colliding.** `built_from` is recorded at `graph/nodes/_agent_artifacts.py:126` and read at `graph/consistency.py:63`; the dependency *model* has no owner in 06 or 07. But note the candidate owner is in a *different cluster's* package — flag for `03-target-architecture.md`. |
| `runtime_persistence.audit` (F-CRP-11) | none found in 03/07/14 | no collision. |
| `runtime_persistence.checkpoints` / `.rollback` (F-CRP-02/04/06) | `audit/14:48` shows `checkpoints` has 5 outgoing edges and `:364-379` treats `testing→checkpoints` as the boundary question only | **Adjacent, not colliding.** Audit 14 does not nominate a checkpoints owner. |
| `graph.resume_protocol` (F-CRP-03) | `audit/01:235` proposes deriving `_NEXT_PHASE_AFTER_APPROVAL` from a single phase owner | **Overlapping but distinct** — resolved by citing 01 at the resume seam. |

No collision found with the `projects` candidate owners (`audit/11:261,400`) or the
`config` candidate owners (`audit/03:160,362,533,569,602,650,688`).

---

## 5. Disputes requiring the author to fix

| id | finding | required change |
|---|---|---|
| D1 | F-CRP-01 | "five independent paths" → four independent paths plus the R3→R2 chain; or show that R3 is intended as an independent answer. |
| D2 | F-CRP-01 | Add the import-time poisoning of `graph/graph.py:201` to the blast radius with the `StorageRootError` consequence (currently only "two SQLite files"). |
| D3 | F-CRP-04 | Appendix A.6 is not executable (`set_candidate_ref` writes the raw key, not the `_ORCH_NS`-prefixed one); replace with the MCP-tool-driven repro. |
| D4 | F-CRP-09 | Separate "public default root is `<storage root>`" from "effective root in a non-persistent run is a per-pid temp dir" (`tests/conftest.py:98` proves the suite never takes the production branch). |
| D5 | F-CRP-09 §2.2 | Row 4 is labelled `NO_PERSIST=0` while the row's values are those of an *unset* flag; §2.3 contradicts it. Fix the label or drop the row. |
| D6 | F-CRP-09 | Seven independent derivations, not six (`graph/services.py:31` and `:48` are two). |
| D7 | F-CRP-09 Prior art | Cite `audit/03` F-CFG-08 (A7 requires prior-art citation for a concern another audit already owns), in addition to the storage plan. |
| D8 | F-CRP-05, F-CRP-10 | Apply the recomputed severities (3×3=9 and 2×3=6) or state why dead/auto-only code carries impact 4/3. |
| D9 | F-CRP-04 | Correct the causal claim: the tool *can* pass `artifact_versions` (`app/runtime.py:253`); the defect is that no factory derives it. |
| D10 | F-CRP-02 | Stale anchor: `~:145` in the de-facto owner list is `manager.checkpoints[...] = meta`; the assignment the mutation deletes is `:145`, and `:144` is the `if`. Acceptable as a range, but `:143-145` should be written as `:143` + `:145`. |

Non-blocking: none of D1–D10 changes a CONFIRMED/rejected outcome; all 11 findings stand.

---

## 6. Command log (reproducibility)

```bash
# pristine snapshot at the audited commit
git archive fb85baa | tar -x -C /tmp/crp-snap            # + /tmp/crp-snap2, /tmp/crp-snap3 for mutations

# truth table (§2.2/§2.3) — /tmp/crp-probes/truth.py
PYTHONPATH=/tmp/crp-snap/src .venv/bin/python /tmp/crp-probes/truth.py

# root divergence, CLI poisoning, R5 split (§2.4) — /tmp/crp-probes/roots.py, r5.py
PYTHONPATH=/tmp/crp-snap/src .venv/bin/python /tmp/crp-probes/roots.py
PYTHONPATH=/tmp/crp-snap/src .venv/bin/python /tmp/crp-probes/r5.py

# two registries + rollback disagreement (F-CRP-02) — /tmp/crp-probes/registries.py
PYTHONPATH=/tmp/crp-snap/src .venv/bin/python /tmp/crp-probes/registries.py

# manual checkpoint / invalidation / rollback_artifact (F-CRP-04) — manual_cp.py
# discovery + delete audit (F-CRP-08/11) — discovery.py
# missed seams M2/M3 — missed.py
PYTHONPATH=/tmp/crp-snap/src .venv/bin/python /tmp/crp-probes/{manual_cp,discovery,missed}.py

# mutation 1 (F-CRP-02): app/_persistence.py:145 restore removed
cd /tmp/crp-snap && PYTHONPATH=/tmp/crp-snap/src .venv/bin/python -m pytest tests/unit \
    -m "not integration and not e2e" --no-cov -p no:cacheprovider     # 1866 passed, 3 skipped

# mutation 2 (F-CRP-03): graph/nodes/_shared.py:190 key renamed
cd /tmp/crp-snap2 && PYTHONPATH=/tmp/crp-snap2/src .venv/bin/python -m pytest \
    tests/unit/graph/test_real_human_gates.py tests/unit/app/test_resume_integrity.py \
    --no-cov -p no:cacheprovider                                      # 49 passed

# mutation 3 (F-CRP-10): _text_only.py:9 drops "no_generation_requests"
cd /tmp/crp-snap3 && PYTHONPATH=/tmp/crp-snap3/src .venv/bin/python -m pytest \
    tests/unit/mcp/tools/test_generation.py --no-cov -p no:cacheprovider   # 41 passed

# cited test files, unmutated HEAD
cd /tmp/crp-snap && PYTHONPATH=/tmp/crp-snap/src .venv/bin/python -m pytest \
    tests/unit/mcp/tools/test_checkpoints.py tests/unit/artifacts/test_state_persistence.py \
    --no-cov -p no:cacheprovider                                      # 40 passed

# static absence proofs, re-run verbatim from each finding's "Reproduce:" line
grep -rn "ResumeManager\|ResumeSnapshot\|BranchManager" --include=*.py src/
grep -rn "read_graph_state" --include=*.py src/ tests/
grep -rn "DEPENDENCY_GRAPH" --include=*.py src/ tests/          # tests/: no match
grep -rn "_STALE_REQUEST_CODES\|_STALE_ISSUE_CODES" --include=*.py src/ tests/   # tests/: no match
grep -rn "_NEXT_PHASE_AFTER_APPROVAL" --include=*.py tests/     # no match
grep -rn "run_id" --include=*.py src/                           # no match
grep -rn "_record_audit" --include=*.py src/film_pipeline/mcp/tools/checkpoints.py src/film_pipeline/checkpoints/  # no match
grep -rn "artifact_versions" --include=*.py src/film_pipeline/app src/film_pipeline/mcp src/film_pipeline/checkpoints
grep -rn "FILM_PIPELINE_NO_PERSIST\|FILM_PIPELINE_PERSIST_STATE" --include=*.py src/
grep -rn "\.records\b" --include=*.py src/                      # only rollback.py:92 append
grep -rn "_artifact_root" --include=*.py src/                   # definition + services helper only
```

**Repository untouched.** `git status --porcelain` is empty and `git log --oneline -1` is
`fb85baa Merge pull request #29 …`. All probes and all four mutated copies live under
`/tmp`; no file under `src/`, `tests/`, or the repo root was created, modified, or deleted,
and no `git checkout`/`git clean`/`make ci-check` was run. The only file written inside the
repository is this document.

---

## 7. Overall verdict

**Audit 10 meets bar A.** All 11 findings have valid anchors at `fb85baa`, every quoted
string appears at its cited line, every O-class is defensible under §1.4 (O3/O5/O6/O8/O1/O4
all correctly applied), every drift proof was either reproduced as an existing divergence
(F-CRP-01/02/04/08/09/11) or executed as a mutation that leaves the suite green
(F-CRP-02/03/05/06/07/10), and no finding is a bare hypothesis. Two severities were
recomputed downward (F-CRP-05 → Medium 9, F-CRP-10 → Medium 6) because impact integers 4
and 3 were applied to dead and auto-path-only code respectively; the remaining nine scores
stand as written. Ten disputes (D1–D10) require text corrections — two of them are factual
(Appendix A.6 is not executable; §2.2 row 4 is mislabelled) and one is a bar-A7 omission
(no prior-art citation to `audit/03` F-CFG-08) — but **none changes a verdict**. The audit
also understates its most serious concern: the storage-root refusal it attributes to the CLI
is independently reachable from a bare `import film_pipeline.graph.graph` (M1), and the
non-persistent path writes durable state whenever `FILM_PIPELINE_RUNTIME_ROOT` is set (M2);
both should be folded into F-CRP-01 before reconciliation.
