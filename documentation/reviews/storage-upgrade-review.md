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
