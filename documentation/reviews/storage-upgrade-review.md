# storage-upgrade branch — review record

Review of branch `storage-upgrade` (P1–P7, 8 commits on merge base `43af11a`) against
the quality bar and end goal in `documentation/storage-upgrade-plan.md` §1.

Three reviewer lenses were used, as the plan's §1.7 process requires: **correctness**,
**cleanliness/design**, and **completeness-vs-plan**. Findings were verified
independently before any fix; each fix step is its own commit.

## Baseline (HEAD `b51ed00`, before fixes)

`make ci-check` green: ruff format + lint, mypy strict, **1968 passed / 8 skipped**,
coverage **91.72%** (gate 90%), `uv build` 0.4.0, product gate PASS.

The 8 skips are all legitimate opt-in cases: 1 `reportlab`-not-installed, 2
`RUN_REAL_E2E`-gated Z.ai live tests, 3 `RUN_REAL_E2E`/credential-gated e2e tests,
2 append-only policy tests covered elsewhere by design.

Quality-bar items spot-checked empirically at baseline:

- **Test/prod separation (§1.2a) is a real guard.** A canary test writing
  `.film-pipeline-run/GUARD_CANARY_SHOULD_TRIP.txt` made the session guard fail with
  `added=['GUARD_CANARY_SHOULD_TRIP.txt']`. It is not vacuously true.
- **Golden layout (§1.2b) is genuinely pinned.** `test_store_v2.py::TestGoldenLayout`
  asserts the exact file set (`meta.json`, `current.md`, `versions/v001.json`,
  `index/artifacts.json`, `README.md`, `.storage.lock`, `storage.json`).
- **Versioning (§1.3)** is enforced per-kind through the registry and checksum-verified
  on load (`ChecksumMismatchError`), with `SchemaTooNewError` carrying
  kind/found/max/path/remedy.
- **D9 deliverables-on-approve** is real and tested
  (`test_readability.py::test_approve_phase_marks_artifacts_approved_and_fills_deliverables`).
- P7 deletions left **zero dangling references** (`versioning`, `index`, `metadata`,
  `observability`, `.fleet/`); the b51ed00 compat removal left no bridge residue.

## Incident: repo-local `projects/` directory deleted during review

While probing whether the conftest production-roots guard actually fires, a reviewer's
canary wrote `projects/guard-probe-should-fail/`, and a follow-up cleanup line
(`rm -rf projects`) deleted the whole repo-local `projects/` directory.

Impact assessment (verified, not assumed):

- `projects/` was gitignored by `8613f6f` (Phase 04, Jun 19) and **never tracked** in any
  commit — `git ls-files projects` is empty, `git log --all -- projects` is empty. Git
  cannot and need not restore it.
- This branch's own P1 (`b57df74`) deliberately removed the CWD-relative `Path("projects")`
  default root, and scripts were redirected to `.scratch/` via
  `scripts/_scratch_bootstrap.py`. The directory was already deprecated by this branch.
- All real project state survives: `~/.film-pipeline/runtime/` (35 projects, 5.0 MB) and
  `~/.film-pipeline/artifacts/` (736 KB). Only `proj_test` has no runtime counterpart.
- No build input depends on it: nothing in `Makefile`, `pyproject.toml`, or
  `.pre-commit-config.yaml` references it, and `tests/conftest.py::_snapshot_tree`
  explicitly tolerates a missing root.

Conclusion: **no unique film data was lost**; the deleted directory held deprecated
legacy test debris. It was deliberately **not** reconstructed. Recovery from
`~/.film-pipeline/runtime/` remains possible if a legacy project copy is ever wanted,
but the branch declares the legacy layout unreadable by design.

## Blocking findings and fixes

### B1 — Non-finite numbers wrote permanently unreadable artifacts (fixed in `fa8903a`)

Found by the correctness lens. `payload_checksum` used `json.dumps` defaults,
emitting bare `Infinity`/`NaN` (not legal JSON). The checksum was computed over
that non-canonical form while `ArtifactEnvelope.model_validate` normalized the
float on read, so the recomputed checksum differed and every load raised
`ChecksumMismatchError`. The write reported **success** and the artifact was
unreadable forever. Reachable from a live MCP path: `initialize_budget` passed
an unchecked `cap_usd` into the unbounded `BudgetState.per_phase_caps_usd`.

Fixed failing closed at the write boundary (`serialization.dump_json`),
independently in `payload_checksum` (`allow_nan=False`), and at the MCP input.
The 6 new regression tests were verified to fail against the pre-fix code.

### B2 — Projects were split across two directories (fixed in `d9f6f18`)

Found by the completeness lens and independently reproduced. `project.json`,
`state/`, `checkpoints/`, and `audit/` were written to
`<root>/runtime/<project_id>/`, while `artifacts/`, `README.md`, `deliverables/`,
and `index/` were written to `<root>/artifacts/<project_id>/`. §1's end goal
("a human can open any project folder and read its state and final results")
was therefore unmet, the D3 diagram was not implemented, and the tests encoded
the split as correct so nothing could catch it. Plan D2 had in fact required
P4 to merge the two trees; the merge never happened.

Fixed by making the runtime root the storage root. One project folder now holds
everything, verified by an end-to-end tree dump and pinned by a new guard test
(`test_runtime_and_artifact_roots_coincide`).

## Fix commits

| Commit | Scope |
|---|---|
| `e9e34d7` | Public `store.root` in tests; `list_assets` row contract tightened; incident recorded |
| `fa8903a` | **BLOCKING** non-finite rejection at all three boundaries; renderer map moved into `KindSpec` |
| `266f04f` | **BLOCKING** single-folder project layout (runtime root = storage root) |
| `dfa6cb1` | MAJOR: `save()` refuses `SUPERSEDED`; mutable refs raise instead of substituting current |
| `c107521` | D6: every storage write atomic; parent-directory fsync for rename durability |
| `3d09675` | Dead `paths.artifact_dir`/`artifact_path` (legacy colon-mangling) and dead `ArtifactMetadata.schema_version` removed |
| `dac022e` | JSONL storage version enforced on read; §5 `list_artifacts`/`list_checkpoints` row contracts pinned |

## Verification of the end goal

Running four real pipeline phases through `StudioRuntime` produces exactly one
project folder containing everything the D3 diagram specifies:

```
<root>/p1/
├── project.json          ← typed record (human + MCP entry point)
├── README.md             ← generated index with working relative links
├── artifacts/<NN-phase>/<id>/{meta.json, current.md, versions/vNNN.json}
├── index/artifacts.json
├── audit/audit-log.jsonl
├── .gitignore
└── .storage.lock
```

`<root>` itself contains only `p1/` and `storage.json` — no second tree. The
generated README renders a browsable artifact index, and `current.md` for the
script artifact renders a screenplay-style document (scene headings, dialogue)
rather than a key-value dump, confirming the D9 renderers work through the real
pipeline. §1's first clause ("a human can open any project folder and read its
state and final results") is therefore met.

Test evidence is behavior-based, not coverage-based: every behavior-asserting
regression test added here was run against the pre-fix code and confirmed to
fail (non-finite ×6, status/mutable-ref ×3), and the production-roots guard was
re-verified to trip by canary injection after each structural change.
