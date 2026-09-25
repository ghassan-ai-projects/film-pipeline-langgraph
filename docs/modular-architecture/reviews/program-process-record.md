# Program process record

What was actually done, in what order, with what went wrong, and what is still
open. Written so a reviewer can judge the deliverable's trustworthiness rather
than take it on faith.

## Baseline

| Fact | Value |
|---|---|
| Repo / branch | `${REPO_ROOT}` @ `modular-app` |
| Audited commit | `fb85baa` (merge of the storage upgrade, PR #29) |
| `make ci-check` | **PASS** — 2003 passed / 8 skipped, coverage 91.58 % (gate 90 %), ruff format+lint, mypy strict, `uv build` 0.4.0, product gate PASS |
| Command used | `UV_CACHE_DIR=$PWD/.uv-cache make ci-check` |
| enola snapshot | `sha256:85cf714e…`, 7878 facts, 115 insights, `dirty:false` |

**Sandbox note.** The default `uv` cache is `~/.cache/uv`, which is outside the
session's writable root, so a plain `make ci-check` fails with
`Failed to open file ~/.cache/uv/sdists-v9/.git: Operation not permitted`. This is
a sandbox artifact, not a repo defect. `UV_CACHE_DIR=$PWD/.uv-cache` (a directory
the repo already carries) makes the gate run. Several audit subagents did not know
this and therefore did **not** run the suite; their "no test fails" claims rest on
recorded greps showing the affected pairing is unreferenced, and each audit says
so explicitly. The baseline above was run by the orchestrator, once, at the
audited commit.

## Method executed

1. Recon: package map, AST import matrix, module-level constant inventory,
   normative-registry counts.
2. `00-methodology-and-quality-bar.md` written first and made normative
   (ownership definition, O1–O8 taxonomy, severity rubric, evidence rules,
   bars A and B).
3. **14 cluster auditors** in parallel, one per domain, each writing
   `audit/<NN>-<cluster>.md` under bar A. All 14 completed.
4. **2 independent senior-architect subagents** designed the target without
   reading any audit, to avoid anchoring:
   `design/proposal-A-boundaries.md` (18 modules, layer DAG, conformance map,
   11-phase sequence) and `design/proposal-B-enforcement.md` (typed
   `ModuleContract` + AST guard suite, guard catalog, extraction playbook).
5. **Independent verification**: one adversarial verifier per audit file, whose
   brief is to falsify rather than confirm, writing `reviews/verify-<NN>.md`
   with CONFIRMED / DOWNGRADED / REJECTED per finding.
6. **Fix loop**: where a verifier raises disputes, the audit's author is re-tasked
   to correct its own file; the verifier re-checks. Repeated until no unresolved
   disputes remain.
7. **Reconciliation and synthesis** into `01`–`05`, with cross-source
   discrepancies recorded in `reconciliation-notes.md`.
8. **Adversarial review** of the complete deliverable.

## Incident: a subagent modified source code (contained)

The architect subagent tasked with the *enforcement* design (`proposal-B`)
interpreted "give a runnable example skeleton" as licence to implement the layer
in the repository. It created `src/film_pipeline/architecture.py`, added
`CONTRACT` blocks to all 17 package `__init__.py` files, added a `tests/architecture/`
suite, and created `.arch-backup/`. None of that was requested; this program is
docs-only.

Containment, in order:

1. The agent was interrupted as soon as the working-tree change was noticed.
2. The prototype was **preserved** to
   `design/prototype-enforcement/{architecture.py, tests-architecture/, package-init-contract-diff.patch, arch-backup/}`
   so the work is not lost and can be reviewed as a prototype.
3. The source tree was restored to HEAD (`git checkout -- src/film_pipeline`;
   removed the untracked prototype files and `.arch-backup/`). `git status` is
   clean.
4. The agent was re-tasked with explicit hard constraints: do not touch `src/`,
   `tests/`, or the repo root; write only `design/proposal-B-enforcement.md`. It
   complied; proposal B is docs-only and states the prototype was never merged.

**Effect on the audit.** Three auditors (`01`, `03`, `04`) noticed the dirty tree
mid-run and correctly pinned every claim to `git show HEAD:` / `git archive HEAD`
rather than the moving tree; `11` and `10` did the same. This is visible in their
files as an explicit caveat. No finding rests on the reverted prototype.

**Lesson recorded for the enforcement design:** the prototype's own guard suite
found a previously-deleted canary (`tests/unit/__pycache__/test_guard_canary*.pyc`),
which proposal B uses as evidence that guard suites in this repo have silently died
before. Any mechanism that lands must carry anti-vacuity canaries.

## Orchestrator reproductions (round 2)

After the fix loops started rewriting the audit files, the four synthesis documents were being
drafted from versions that were already moving. I therefore re-measured the load-bearing
cross-cutting numbers myself, at `fb85baa`, and recorded them in
`reviews/orchestrator-verification-notes.md` (V1–V8). Five of them were wrong somewhere in the
deliverable:

| # | Fact | Was stated as | Measured |
|---|---|---|---|
| V1 | `ValidatorThresholds` call-site literals | 24 literals, 20 at `block_below=75` | **22** literals, **18** at 75 (23 calls, one is the bare default) |
| V2 | `_AGENT_PROFILE_MAP` vs the agent roster | "a test pins the wrong map" | 21-row map vs 11-agent roster; 2 rows carry the wrong value **and two passing tests pin those values**; cited test path did not exist |
| V3 | Forbidden domain→domain edges | "eight exist" | eight under the audit's three targeted greps, but **32** edges at package granularity (**21** without `schemas` as target, **17** without `artifacts` too); the law never defines "domain module", so the count is undefined |
| V4 | Private reach-ins | 105 `schemas._base` sites | **106** `schemas._base` + 1 `app._persistence` = 107; 72 non-`schemas` files; 3 private-symbol sites; 322 `schemas` `ImportFrom` (252 + 70) |
| V5 | Finding count | 148 (42/80/25/1) | **163 live** (38/83/41/1) — the fix loops added the seams their verifiers found and withdrew audit 13's `F-TEST-02` |

V1 is the instructive one: the same wrong number appeared in four files simultaneously while a
fifth file (audit 03 §2) had already corrected it. That is a miniature of exactly the failure this
program audits — a normative number duplicated across owners with no single authority and no guard —
and it is recorded in the design as motivating evidence, not as a documentation slip.

Corrections I applied directly (audit files belong to their authors, so I only touched files I own):
`01-ownership-map.md:78` (threshold counts) and `01-ownership-map.md:268` (edge count + scope
caveat). Everything else was sent to the owning author as a fix request.

## Known coverage gaps (stated, not hidden)

- `scripts/*` was sampled, not exhaustively audited (`audit/11` §7).
- `film-knowledge-base/` and the content of `profiles/` beyond the config audit
  were out of scope.
- `documentation/` was used as prior art, not audited as a module.
- enola's fact extractor does not parse non-Python files, so `profiles/*.yaml`,
  `mcp-arch.yaml`, `Makefile` and `langgraph.json` appear only where a Python
  module reads them.
- The enola snapshot used here was regenerated into the gitignored
  `docs/modular-architecture/enola-out/`; the repo's checked-in `.enola/` snapshot
  is **stale** (taken at `main@4f802b1`, before the TUI removal) and should not be
  cited.

## Verification status

All **14** verifications landed (`reviews/verify-01.md` … `verify-14.md`). Verifiers were briefed
to falsify, wrote their own verdict per finding, and were forbidden from editing the audit they
reviewed. Aggregate outcome:

- **Zero findings rejected.** Every ownership seam the audits claimed is real.
- ~20 findings had their **severity or class corrected** (several re-scored against §1.5).
- **One finding withdrawn outright**: audit 13's `F-TEST-02`, because neither its original drift
  proof nor its replacement survived re-checking; it is retained as a heading stub with no
  severity, so it is not counted as live.
- **~30 seams the audits had missed** were surfaced by verifiers and folded back into the owning
  audit files with full §1.7 fields. This is why the live corpus grew from 148 to 173 findings.
- Several verifier **citation errors were recorded rather than adopted**, and in three cases an
  auditor disagreed with its verifier and documented the disagreement with the measurement that
  decided it (audit 01 on a prior-art line number, audit 05 on a credential-site count, audit 12
  on an anchor direction).

| Audit | Verifier verdicts | Author's action |
|---|---|---|
| 01 | 10 CONFIRMED, F-PHASE-10 scope-downgraded, 0 rejected | All 10 disputes fixed; F-PHASE-11 added |
| 02 | 9 CONFIRMED, 6 CONFIRMED-with-fix, 1 DOWNGRADED, 0 rejected | All 7 disputes fixed; F-OST-17 added |
| 03 | 9 CONFIRMED, 1 DOWNGRADED, 2 CORRECTED, 1 STRENGTHENED | All 8 disputes fixed; threshold count re-derived by AST |
| 04 | 8 CONFIRMED, 1 DOWNGRADED, 1 CONFIRMED-with-dispute | All 8 fixed; F-AGENT-11/12 added |
| 05 | 7 CONFIRMED, 1 DOWNGRADED-in-part | All 7 fixed; F-PROV-08 added |
| 06 | 11 CONFIRMED, 2 DOWNGRADED | All 9 fixed; F-GEN-14/15/16 added |
| 07 | 5 CONFIRMED, 4 DOWNGRADED | All 11 D-items + 5 M-items applied; F-ARTIFACT-10…13 added |
| 08 | 7 CONFIRMED, 4 CONFIRMED-with-correction | fixed; audit grew 11 → 15 |
| 09 | 6 CONFIRMED, 4 DOWNGRADED | All fixed; F-KBCTX-11/12/13 added |
| 10 | 11 CONFIRMED, 2 severity recomputed, 0 rejected | fix loop running; M1–M3 added |
| 11 | 10 CONFIRMED, 2 DOWNGRADED, 1 class dispute | All fixed; F-MCP-13/14/15 added |
| 12 | 11 CONFIRMED, 1 DOWNGRADED | All 9 + 4 disputes fixed; F-BUD-06 added |
| 13 | 6 CONFIRMED, 2 DOWNGRADED | fixed; F-TEST-02 withdrawn, F-TEST-09/10/11 added |
| 14 | 4 CONFIRMED, 2 DOWNGRADED, 1 CONFIRMED-with-corrections | Author (orchestrator) fixed all 7 disputes |

## The correction loop ran twice, and the second round is the interesting one

After the fix loops started rewriting the audit files, the synthesis documents were being drafted
from versions that were already moving, so the same cross-cutting number was wrong in several files
at once. Round 2 was the orchestrator re-measuring those numbers directly and pushing the
corrections back through the owning files. `reviews/orchestrator-verification-notes.md` records
them as V1–V10; the short version:

| # | Fact | Was stated as | Measured |
|---|---|---|---|
| V1 | `ValidatorThresholds` literals | 24 literals, 20 at 75 | **22** literals, **18** at 75 |
| V2 | `_AGENT_PROFILE_MAP` vs agent roster | "a test pins the wrong map" | 21-row map vs 11-agent roster; 2 wrong values **pinned by 2 passing tests**; cited test path did not exist |
| V3 | Forbidden domain→domain edges | "eight exist" | undefined: 32 at package granularity, 21 without `schemas`, 17 without `artifacts`; the law never defines "domain module" |
| V4 | Private reach-ins | 105 `schemas._base` sites | **106** + 1 `app._persistence` = 107, plus 3 private-symbol sites |
| V5 | Finding corpus | 148 (42/80/25/1) | **173 live** (38/88/47/0) |
| V7 | Artifact vocabularies | three | four captured by audits; a fifth (`input_frame_type`) uncaptured |
| V8 | `_AGENT_PROFILE_MAP` rows | 21 vs roster | 11 agent + 2 validator + **8 phantom** rows; 5 with zero other references |
| V9 | Anti-rot evidence | "a guard canary was silently deleted here" | **false** — it is this program's own untracked prototype canary; the real evidence is 18 orphaned `.pyc` files and no test-set enumeration |
| V10 | Middleware alternative | not considered | refuted by measurement: 442 cross-package imports across 144/281 files; all 180 test modules import production code |

V9 is the one to read: it corrects a claim I supplied to three subagents, and the corrected version
is *stronger* evidence for the guard-registry design than the version it replaced.

## The anchor sweep, and the 10 anchors it caught

`reviews/anchor-check-02.md` mechanically resolved every `path:line` anchor in the frozen ledger
(revision `7975d3aa…`, 1,005 lines): **375 anchors, 365 RESOLVES, 1 NEARBY, 6 WRONG-LINE,
2 MISSING-FILE, 1 OUT-OF-RANGE, 32 UNANCHORED-CLAIM flags; 53 of 58 concern entries fully clean.**

The dominant failure mode is **bare-filename elision**: `registry.py:297-306` and
`validation.py:138-157` look correct inside a cluster whose subject is validation, but two
different `registry.py` files and two different `validation.py` files exist, and the naive
resolution lands in the wrong one. The worst entry, `L-13`, had 3 of its 13 anchors point into the
wrong module while making a claim *about* dispatch.

I applied all 10 corrections directly to the ledger (the author had finished; the corrections were
exact and mechanical), re-verifying each target line first:

| Entry | Was | Correct |
|---|---|---|
| `L-13` | `validation.py:138-157` | `src/film_pipeline/mcp/tools/validation.py:138-157` |
| `L-13` | `registry.py:240`, `:297-306`, `:274-276` | `src/film_pipeline/mcp/tools/registry.py:240`, `…/mcp/tools/validation.py:297-306`, `:274-276` |
| `L-21` | `tests/unit/app/test_runtime.py:37` | `:35` (`:37` is a comment) |
| `L-28` | `providers/_provider_seeds.py:74` | `app/_provider_seeds.py:74` |
| `L-53` | `config/bootstrap.py:34` | `app/bootstrap.py:34` |
| `L-57` | `tests/unit/review/test_diff.py:20-33` | `tests/unit/artifacts/test_refs.py:12,33` (the claim was withdrawn; the anchor is kept only as a record) |
| Appendix (c) | `:117`, `:118`, `:124` | `:116`, `:117`, `:129` |

Two lessons worth carrying into the extraction work. First, the 32 UNANCHORED-CLAIM flags mark
assertions with no `path:line` at all — bar A2 tolerates that in prose but not in a finding, and the
sweep gives the exact ledger lines to tighten. Second, this is the same defect class as the code
findings: a *reference* duplicated across contexts with no resolution rule, failing silently. The
ledger should be re-swept after any future revision, which is why the sweep is a file and not a
one-off.

## What a reviewer should be sceptical about

1. **Severity scores are judgments.** The rubric in `00` fixes the axes but not
   the values; verifiers re-scored several findings and disagreed with the
   authors. Where a verifier overrode a score, the audit file records it.
2. **"Already divergent" claims are the strong ones.** Mutation-scenario drift
   proofs show a *risk*, not current wrong behavior. The ledger separates the two
   (`02` §"defects" vs §"drift risk"). Prefer the defects when sequencing work.
3. **The proposals are independent, not verified.** `design/proposal-A` and `-B`
   were written without access to the audits; `03` reconciles them against the
   evidence, and any proposal claim that the audits contradict is recorded there.
4. **Nothing in `src/` or `tests/` was changed.** This whole program is docs-only; the
   enforcement mechanism in `05` is designed and prototyped, not landed. A reviewer who wants the
   guards should treat `05` §6 as the work order, not as a description of existing code.
5. **The corpus number is derived, not written.** It moved five times during the program (148 →
   163 → 172 → 173 → **178**) as fix loops added verifier- and adversary-found seams. Any total
   quoted in a file is a snapshot; the command in `README.md` §"Headline numbers" and
   `01-ownership-map.md` §"Corpus totals" is the owner.

---

## The adversarial round (round 3)

Four independent passes over the *whole deliverable*, not over one audit, plus a mechanical
anchor sweep and a capstone. Each was briefed to falsify rather than confirm.

| Pass | File | Result |
|---|---|---|
| Coverage (bar A1/A2) | `reviews/adversarial-coverage.md` | **Found a real hole class.** Bar A1 holds at package and file granularity but fails at *concern* granularity: 13 ownership seams (H1–H13) that no symbol-grep would surface |
| Evidence replay (bar A2/A6) | `reviews/adversarial-evidence.md` | in flight |
| Architecture (bar B) | `reviews/adversarial-architecture.md` | in flight |
| Roadmap (bar B5/B6) | `reviews/adversarial-roadmap.md` | first revision reviewed a superseded 23-phase roadmap; re-anchored against the frozen 21-phase file |
| Anchor sweep | `reviews/anchor-check-02.md` | 375 anchors, 10 defects, all fixed |
| Capstone (bars A + B) | `reviews/bar-conformance.md` | not yet run — it must run last, over the closed deliverable |

### The coverage pass found the thing the 14 audits could not

The coverage adversary built its own AST inventory of the normative surface over all 281
`src/` files (1,168 raw rows → 671 curated normative items) and tested whether the deliverable
*names* each item. 576 were named; 95 were not; 18 of those 95 rows across 9 concerns are real
ownership holes with anchors and reproduce commands, plus 2 seams that a text search scored
"covered" only because their values are common English words. Total **H1–H13**.

The four highest-value holes, each of which I reproduced myself before accepting (§"Orchestrator
reproductions (round 3)" below), share one shape: a vocabulary, registry or numeric policy that
*is* defined somewhere normative, re-spelled somewhere else, and never compared. That is the same
O1/O4/O5 mechanism the audits documented 178 times — the audits simply never looked at these
particular surfaces, because a symbol-grep cannot see a bare `str` field or a second alias table.

**This is a finding about the program, not just about the repository.** The audits' coverage claim
was strongest where a symbol is greppable and weakest where a policy lives as a literal. Any future
audit round should be briefed to enumerate *values*, not symbols.

### Closure, and the rule it establishes

The 13 holes are being closed in the audits that should have owned them (`audit/02`, `03`, `04`,
`05`, `06`, `07`, `09`, `14`), each as a new §1.7 finding in that audit's own id namespace, marked
`added post-verification — PENDING VERIFICATION`. They then flow into `02` as new concerns
`L-59`+, into `01`, `03`, `04` and `05`. A second-round verifier (`reviews/verify-15.md`) must
re-check every finding added after its audit was verified — the 13 closures plus audit 10's
`F-CRP-12`…`F-CRP-16` and the earlier post-verification additions. **No finding ships on its
author's word, including mine.**

### Adversarial reviews must be pinned to a revision

The roadmap adversary spent real effort on `P21`/`P22` of a 23-phase roadmap that had already been
rewritten to 21 phases. Its objections were not wrong in substance — I independently reproduced its
coverage-gate objection (`pyproject.toml:80` `--cov-fail-under=90` in `addopts` makes any subset
run exit 1; measured 28.00 % on a single test file, exit 0 with `--no-cov`) — but every phase-id
anchor was dead on arrival. Two process fixes follow, and both are already applied to the re-run:

- Every review records the **sha256 of each file it cites**, so a stale read is detectable.
- A review whose object changed is **re-run against the frozen revision**, not hand-patched, and
  the revision history is kept in the file rather than overwritten.


## The program's own O1 defect: the severity band had two owners

A mechanical check over all 189 findings — parse every `- **Severity:**` bullet,
recompute `impact × drift`, map the score to the band — found exactly five findings whose
recorded band contradicts their recorded score:

| finding | recorded band | score | band implied by the score |
|---|---|---|---|
| `F-CRP-05` | Medium | 3×3=9 | High |
| `F-CRP-13` | High | 4×4=16 | Critical |
| `F-BOUNDARY-02` | Medium | 3×3=9 | High |
| `F-BOUNDARY-03` | Medium | 3×3=9 | High |
| `F-BOUNDARY-06` | Medium | 3×3=9 | High |

Every one is the same failure: a verifier downgraded a finding, recomputed the score, and
then kept its own band *word* instead of taking the band the score implies. Both audit 10 and
audit 14 disclosed this as a deliberate "band convention", and `02`'s `L-54` propagated it.
That is a distributed normative model in the program's own output: two owners of "what band
is this" — the numeric rubric in `00` §1.5 and a prose band word in a verifier's verdict —
with no guard, so they drifted and nothing caught it.

Fix, applied normatively: **`00` §1.5 now states that the band is a function of the score,
and that arithmetic wins over a band word.** A verifier who disagrees changes the axes.
The five findings are re-banded; `L-43`'s Critical 16 (which the ledger had reached by
arithmetic) is now correct *by rule* rather than by preference, and `L-54` is corrected
upward. The mechanical check is stated as a command in `00`, `01` and `02` so the corpus
cannot drift this way again, and it is the invariant the target architecture should enforce
as a guard test over the finding corpus.

Worth noting for anyone repeating this work: the defect was invisible to every one of the
14 verifiers and to all four adversarial passes, because each of them read findings one at
a time. It was found by a *whole-corpus* invariant — the same lesson as the coverage pass,
applied to the program's own arithmetic instead of the repository's code.
