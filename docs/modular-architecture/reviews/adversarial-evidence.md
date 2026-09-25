# Adversarial evidence review — `docs/modular-architecture/audit/*.md`

Independent re-run of the audit-set evidence. Reviewer is not an author of any audit
file and did not consult the `verify-*.md` verdicts before running the reproductions.

- Repo: `${REPO_ROOT}`
- Branch: `modular-app`; audited baseline `fb85baa`; working tree clean throughout.
- All audit files are under `docs/`, which is gitignored, so no audit edit appears in
  `git status`.
- Scope: 14 files in `docs/modular-architecture/audit/`; normative rules read first in
  `docs/modular-architecture/00-methodology-and-quality-bar.md` §1.4–§1.6, §2 (A2/A5).

---

## 0. The corpus moved during the review — twice (pin warning)

The audit set is a **moving target**, and another process is actively rewriting it while
this review runs. Two waves were observed:

- **Wave 1, 2026-09-25 15:42:39.** `audit/10-checkpoints-and-runtime-persistence.md` grew
  from 11 to 16 findings (`F-CRP-12` … `F-CRP-16` appended; `F-CRP-01` … `F-CRP-11` were
  byte-identical before and after — verified by re-extracting every previously run
  `Reproduce` block and comparing).
- **Wave 2, 15:49–15:57.** `audit/02` (+1 finding), `03` (+2), `04` (+1), `05` (+1),
  `06` (19 findings, still changing between two readings at 15:56 and 15:57), `07` (+1),
  `09` (+1) and `14` (+1) were all appended to/rewritten. `01-ownership-map.md` and
  `04-extraction-roadmap.md` were also rewritten.
- `reviews/adversarial-roadmap.md` (15:40:55), `reviews/adversarial-coverage.md` (15:40:55)
  and `reviews/program-process-record.md` (15:48:05) were written in the same window.

Consequences:

1. Every verdict below is pinned to the snapshot in §1.1, taken at ~15:48–15:52. That
   revision **no longer exists on disk**.
2. The deterministic sample was recomputed after wave 1; the reviewed set is the **union**
   of the pre- and post-wave-1 samples (146 findings), so no finding selected at either
   instant is silently dropped. Wave 2 happened after all runs and is *not* covered by the
   per-finding verdicts.
3. Live count at report time is **189 findings**, not the 173 that
   `05-enforcement-and-guard-tests.md` §V5 asserts (`173 = 38C/88H/47M`), and not the 178
   of the §1.1 snapshot. The 173 claim was true when written; later edits to the same docs
   tree invalidated it, and two further edits invalidated 178 before this report was saved.
4. The three WRONG-OUTPUT findings (`F-BOUNDARY-01`, `F-PHASE-02`, `F-ARTIFACT-08`) and the
   three FAILS-TO-RUN findings (`F-MCP-02`, `F-CFG-04`, `F-CRP-01`) were re-checked against
   the wave-2 bytes: for `F-ARTIFACT-08` (`enum-only` stays 3) and `F-BOUNDARY-01` ("eight
   distinct forbidden edges") both the `Reproduce` block and the contradicting sentence are
   **byte-identical**, so those verdicts stand on the live revision. `F-PHASE-02`'s file
   (audit 01) was not touched.

**Current (wave-2) hashes, for anyone re-running against today's bytes** — these are *not*
the versions I reviewed:

| Audit file | sha256 (first 16) | lines | findings |
|---|---|---:|---:|
| `01-phase-model-and-transitions.md` | `75547299df2c9091` | 596 | 11 |
| `02-orchestration-state-and-routing.md` | `3461386e9cc547f8` | 1160 | 18 |
| `03-config-profile-and-defaults.md` | `4d22bdd20c2d3837` | 1057 | 15 |
| `04-agent-registry-and-prompts.md` | `99811acae85363bb` | 633 | 13 |
| `05-provider-runtime-and-health.md` | `d798187aef0da898` | 1155 | 9 |
| `06-generation-runtime-and-ledger.md` | `49cf7b0d5601ee6e` | 1214 | 19 |
| `07-artifact-refs-and-schemas.md` | `77b732add65fd85a` | 1030 | 14 |
| `08-validation-and-review.md` | `f5142f98b55ed9a5` | 1388 | 15 |
| `09-kb-context-and-provenance.md` | `5e8f4f5237558cd1` | 861 | 14 |
| `10-checkpoints-and-runtime-persistence.md` | `6ba776724489c3d6` | 1719 | 16 |
| `11-mcp-surface-safety-and-entrypoints.md` | `3cf4f35732914a81` | 468 | 15 |
| `12-post-delivery-constraints-budget.md` | `81e07510e9a55f2b` | 1205 | 13 |
| `13-test-doubles-and-harness.md` | `1b6d4e8443030916` | 526 | 10 |
| `14-module-boundaries-and-import-law.md` | `c84128b4afac8454` | 662 | 7 |
| **Total** | | 15 141 | **189** |

An audit set that is rewritten while it is being adversarially reviewed cannot be
certified as a fixed artifact; the pin itself is a finding.

---

## 1. Method

### 1.1 Pinned snapshot (sha256, line count, mtime at read time)

| Audit file | sha256 (first 16) | lines | mtime | findings |
|---|---|---:|---|---:|
| `01-phase-model-and-transitions.md` | `75547299df2c9091` | 596 | 2026-09-25 15:16:13 | 11 |
| `02-orchestration-state-and-routing.md` | `5c9a9182171f6932` | 1052 | 2026-09-25 15:18:08 | 17 |
| `03-config-profile-and-defaults.md` | `866a75711b25af41` | 959 | 2026-09-25 15:09:55 | 13 |
| `04-agent-registry-and-prompts.md` | `cd88545d37a09181` | 588 | 2026-09-25 15:09:55 | 12 |
| `05-provider-runtime-and-health.md` | `8351740c4b16e4f2` | 1029 | 2026-09-25 15:23:21 | 8 |
| `06-generation-runtime-and-ledger.md` | `1fcff1e5c53a581b` | 1090 | 2026-09-25 15:12:06 | 16 |
| `07-artifact-refs-and-schemas.md` | `a184d57295c8aca8` | 904 | 2026-09-25 15:04:18 | 13 |
| `08-validation-and-review.md` | `f5142f98b55ed9a5` | 1388 | 2026-09-25 15:26:16 | 15 |
| `09-kb-context-and-provenance.md` | `d77d871e8342ef40` | 767 | 2026-09-25 15:01:03 | 13 |
| `10-checkpoints-and-runtime-persistence.md` | `6ba776724489c3d6` | 1719 | 2026-09-25 15:42:39 | 16 |
| `11-mcp-surface-safety-and-entrypoints.md` | `3cf4f35732914a81` | 468 | 2026-09-25 15:04:17 | 15 |
| `12-post-delivery-constraints-budget.md` | `81e07510e9a55f2b` | 1205 | 2026-09-25 15:04:06 | 13 |
| `13-test-doubles-and-harness.md` | `1b6d4e8443030916` | 526 | 2026-09-25 14:59:09 | 10 |
| `14-module-boundaries-and-import-law.md` | `6bc51d6392e4ff11` | 425 | 2026-09-25 15:06:56 | 6 |
| **Total** | | 12 316 | | **178** |

Heading census: 180 lines match `^### F-<ID> —`; two are the withdrawn `F-TEST-02`
(one stub in the Findings list of audit 13 and one hypothesis block in its Withdrawn
section). **178 live findings: 39 Critical, 88 High, 50 Medium, 1 Low.**

### 1.2 Sampling rule (deterministic, reproducible)

Applied to the pinned snapshot, in `(filename, appearance order)`:

1. **every Critical finding** — 39;
2. **plus every finding whose `Reproduce` block is a multi-line fenced bash/python block**
   — 106;
3. **plus every 3rd finding of the remainder** (`index % 3 == 0` over the ordered rest)
   — 18.

That rule yields 142 on the post-expansion snapshot. Because the set expanded mid-review,
the reviewed set is the union with the 140 selected pre-expansion: **146 sampled findings**
(4 findings leave the post-expansion sample and 6 enter it purely because audit 10 grew and
shifted the every-3rd cursor: `F-MCP-05/08/11/14` out, `F-CRP-12/14` and
`F-MCP-01/07/10/13` in). All 146 were run.

### 1.3 How reproductions were executed

- Each `Reproduce` block was extracted from raw markdown and written to `/tmp/advrev/runs/`,
  then run with `bash <file>` from the repo root, output captured to `/tmp` only.
- **De-indentation.** 12 of 14 audit files indent their fenced code under a list bullet
  (audit 05 uses both 2-space and 4-space indents; audits 03/06/07/12/13 indent every
  fence). A markdown renderer strips the list indent; running the raw markdown bytes gives
  a spurious `IndentationError`. I stripped the fence's own indent from every line before
  running (this is the *generous* reading). A reader who copies raw markdown rather than
  rendered markdown gets `IndentationError` on those blocks — a real portability defect,
  reported here but **not** counted as a claim failure.
- Only the interpreter path was adapted: `.venv/bin/python` was used as written (it exists);
  repo-wide scratch scripts used `UV_CACHE_DIR="$PWD/.uv-cache" uv run python`.
- Interpreter: `.venv/bin/python` = CPython **3.12.13** (uv-managed).
- Per-command timeout 180 s, concurrency 6. No command was observed to write into the
  repo; the tree was clean before and after. The one command containing a literal
  placeholder (`F-CRP-01`, `<snapshot>`) was run and failed, as recorded in §3.2.
- No `git checkout/clean/stash`; no write to `src/`, `tests/` or the repo root.
- Guard command: `UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest <4 files> -q` and again with
  `--no-cov`.

### 1.4 Tooling caveat

The inline (`- **Reproduce:** \`…\``) blocks were extracted with a backtick-span
heuristic. Two multi-command inline blocks were mis-split by that heuristic and were
re-run by hand (`F-ARTIFACT-01`, `F-CFG-04`); the manual results are the ones reported.

---

## 2. Tally

| Audit file | findings | sampled | REPRODUCES | WRONG-OUTPUT | FAILS-TO-RUN | NO-REPRODUCE | WOULD-WRITE |
|---|---:|---:|---:|---:|---:|---:|---:|
| `01-phase-model-and-transitions.md` | 11 | 11 | 10 | 1 | 0 | 0 | 0 |
| `02-orchestration-state-and-routing.md` | 17 | 16 | 16 | 0 | 0 | 0 | 0 |
| `03-config-profile-and-defaults.md` | 13 | 8 | 4 | 0 | 1 | 3 | 0 |
| `04-agent-registry-and-prompts.md` | 12 | 6 | 6 | 0 | 0 | 0 | 0 |
| `05-provider-runtime-and-health.md` | 8 | 7 | 7 | 0 | 0 | 0 | 0 |
| `06-generation-runtime-and-ledger.md` | 16 | 15 | 15 | 0 | 0 | 0 | 0 |
| `07-artifact-refs-and-schemas.md` | 13 | 7 | 6 | 1 | 0 | 0 | 0 |
| `08-validation-and-review.md` | 15 | 15 | 15 | 0 | 0 | 0 | 0 |
| `09-kb-context-and-provenance.md` | 13 | 13 | 13 | 0 | 0 | 0 | 0 |
| `10-checkpoints-and-runtime-persistence.md` | 16 | 8 | 7 | 0 | 1 | 0 | 0 |
| `11-mcp-surface-safety-and-entrypoints.md` | 15 | 11 | 10 | 0 | 1 | 0 | 0 |
| `12-post-delivery-constraints-budget.md` | 13 | 13 | 13 | 0 | 0 | 0 | 0 |
| `13-test-doubles-and-harness.md` | 10 | 10 | 10 | 0 | 0 | 0 | 0 |
| `14-module-boundaries-and-import-law.md` | 6 | 6 | 5 | 1 | 0 | 0 | 0 |
| **TOTAL** | **178** | **146** | **137** | **3** | **3** | **3** | **0** |

All 108 fenced findings executed (105 REPRODUCES, 3 WRONG-OUTPUT). Of the 38 sampled
inline/prose blocks: 32 REPRODUCES, 3 FAILS-TO-RUN, 3 NO-REPRODUCE.

`rc != 0` was **not** treated as failure: 8 fenced commands exit 1 because the claim is
"no matches" or because an `ls` is expected to fail (`F-BOUNDARY-04`, `F-PROV-08`,
`F-VR-02`, `F-VR-04`, `F-VR-12`, `F-KBCTX-09`, `F-KBCTX-11`, `F-KBCTX-12`) and their output
supports the claim. Ambiguous case, not a defect: `F-BOUNDARY-04`'s second grep is
*expected* to find nothing, so the exit-1 is the evidence.

---

## 3. Every non-REPRODUCES item

### 3.1 WRONG-OUTPUT (3)

**`F-BOUNDARY-01` — the headline count is not produced by the finding's own command.**
- Command (verbatim, 3 greps): `grep -rn "from film_pipeline.providers" src/film_pipeline/agents src/film_pipeline/config src/film_pipeline/generation` / `grep -rn "from film_pipeline.validation" src/film_pipeline/post` / `grep -rn "from film_pipeline.artifacts\|from film_pipeline.checkpoints\|from film_pipeline.providers" src/film_pipeline/testing`
- Audit claim: *"at HEAD **eight** distinct forbidden edges exist (agents→providers, config→providers, generation→artifacts, generation→providers, post→validation, testing→artifacts, testing→checkpoints, testing→providers)"*; the drift proof says these eight *"are the union of this finding's three targeted greps"*.
- Actual: the three greps emit 15 statements covering **7** distinct edges — `agents→providers`, `config→providers`, `generation→providers`, `post→validation`, `testing→providers`, `testing→artifacts`, `testing→checkpoints`. There is **no `generation→artifacts` line**: the generation grep pattern only matches `from film_pipeline.providers`.
- The underlying divergence is real: my own AST sweep finds `generation→artifacts` at 7 statements (`generation/ledger.py:14`, `executor.py:22`, `executor_delivery.py:14,19`, `executor_prompts.py:13`, `frame_sidecar.py:7`, `compositor/_layout.py:10`) and reproduces the audit's separate 53/32/21/17 pair-sweep ladder exactly. So the defect is the evidence, not the claim.
- Minimal correction: add `from film_pipeline.artifacts` to the generation grep, or change the sentence to "seven from these greps, eight including `generation→artifacts` (`grep -rn 'from film_pipeline.artifacts' src/film_pipeline/generation`)".

**`F-PHASE-02` — the Reproduce command prints 323, the audit says 359.**
- Command and its own inline comment (verbatim): `grep -rnE '"(intake|…|delivery)"' src/film_pipeline --include='*.py' | wc -l   # 359 any-position occurrences`
- Audit claim: *"129/359 are the measured lower bounds"* and the comment `# 359 any-position occurrences`.
- Actual: `323`. (The line-initial grep in the same block reproduces exactly: `129` entries / `16` files.) The 359 figure is only obtainable with `grep -roE` (per-occurrence), which the file-level preamble of audit 01 does use: `grep -roE … | wc -l` → `359`.
- Minimal correction: change the Reproduce block to `grep -roE … | wc -l` (or relabel the `-rnE` result as 323 lines).

**`F-ARTIFACT-08` — the Reproduce command prints 6, the finding text says 3.**
- Command (verbatim, tail): `print('exact basis 47/45; registry-only:',sorted(exact-types)); print('enum-only:',sorted(types-exact))`
- Audit claim: *"3 `ArtifactType` values have no exact registry id (`clip`, `last_frame`, `mid_frame`) … `enum-only` stays 3"*.
- Actual: `enum-only: ['checkpoint', 'clip', 'invalidation_report', 'last_frame', 'mid_frame', 'rollback_record']` — **6** on the exact-only basis the command computes.
- The number 3 is correct on a *different* basis: after adding the 8 `register_prefix` kinds, `enum-only` = 3 (`clip`, `last_frame`, `mid_frame`). The sentence says "no exact registry id", i.e. the command's basis, so text and command contradict each other.
- Minimal correction: "3 once the 8 prefix kinds are included; 6 on the exact-only basis the reproducer prints".

### 3.2 FAILS-TO-RUN (3)

**`F-MCP-02`** — `grep -n "invoke_tool(rt, \"approve_intake\"|…" scripts/` has no `-r`, so it aborts: `grep: scripts/: Is a directory`, exit 2. The first command (`grep -rn "import_module(\"film_pipeline.mcp.tools\")" src/ scripts/`) runs and prints 3 hits. Minimal correction: `grep -rn … scripts/`.

**`F-CFG-04`** — the grep counts reproduce exactly (`pass_at=` → `22`, `block_below=75` → `18`), but the "best re-derived by AST" command is written as a multi-line `python -c "…"` string whose body is indented inside the JSON-ish quoting:
`.venv/bin/python -c "import ast,pathlib\n  zw=exp=0\n  for p in …"` → `IndentationError: unexpected indent` at `<string>`, line 2. The underlying claim is true: running the same AST logic from a heredoc gives `22 22`. Minimal correction: use a `<<'PY'` heredoc, or put the whole program on one line.

**`F-CRP-01`** — `Reproduce:` is `PYTHONPATH=<snapshot>/src .venv/bin/python` → `Appendix A.5`, i.e. a placeholder plus a pointer; executing it yields `/tmp/…: line 1: snapshot: No such file or directory`. The static half of the same bullet (`grep -rn "default_run_root()\|…" src/`) does run. Minimal correction: inline the Appendix A.5/A.9 commands (or drop the placeholder).

### 3.3 NO-REPRODUCE (3)

- **`F-CFG-02`** — there is **no `- **Reproduce:**` bullet at all**. A complete, runnable divergence one-liner exists but is buried in the Drift-proof prose:
  `.venv/bin/python -c "from film_pipeline.graph.nodes import _AGENT_PROFILE_MAP as M;from film_pipeline.agents.mvp import MVP_AGENTS as A;print([(a.agent_id,a.default_model_profile,M.get(a.agent_id)) for a in A if a.default_model_profile!=M.get(a.agent_id)])"`.
  I ran it: `[('intake-classifier-agent', 'creative_writer', 'operations_triage'), ('structure-extractor-agent', 'schema_enforcer', 'strict_validator')]` — the divergence is real and confirmed. Minimal correction: promote that one-liner into a `Reproduce` bullet.
- **`F-CFG-05`** — `Reproduce: the two commands above.` No command in the block. Minimal correction: restate them.
- **`F-CFG-13`** — `Reproduce: the commands recorded in §4.` No command in the block. Minimal correction: restate them.

---

## 4. Drift-proof replay

61 sampled findings assert an **existing divergence** (as opposed to a mutation scenario).
Method: (a) 12 were replayed with commands I wrote myself from the cited owners; (b) the
other 49 were checked by independently executing the finding's own divergence demo and
confirming the produced state is divergent — for greps, that means the two cited sites
both exist with the contradictory content the finding names.

| Verdict | Count |
|---|---:|
| PROOF-HOLDS | 60 |
| PROOF-FALSE | 1 |
| PROOF-UNVERIFIABLE | 0 |

**PROOF-FALSE — `F-ARTIFACT-08`.** The divergence (registry kinds vs `ArtifactType`) exists
and is confirmed, but the proof's stated magnitude is wrong: it says 3 `enum-only` on the
exact-id basis while its own command prints 6 (see §3.1). A proof whose two numbers
contradict each other does not hold as written.

**PROOF-HOLDS but the evidence command is broken — `F-BOUNDARY-01`.** The divergence (8
forbidden domain→domain edges) is real and I reproduced all 8 by AST, so the proof holds;
the supplied command only demonstrates 7 (see §3.1). This is counted PROOF-HOLDS with a
WRONG-OUTPUT command, not PROOF-FALSE.

Independently replayed from my own commands (all PROOF-HOLDS unless noted):
`F-CFG-02` (2 of 11 agents' declared profile ≠ used profile), `F-AGENT-12` (both validator
profiles `multimodal_reviewer` vs map `strict_validator`), `F-ARTIFACT-02` (2 dead
`_ARTIFACT_TYPE_BY_CLASS` values rejected by `ArtifactType`), `F-BUD-04` (`state["budget_cap"]`
has zero writers), `F-GEN-07` (`media_scene_dir` has zero production callers),
`F-MCP-05` (`_STALE_ISSUE_CODES` vs `_STALE_REQUEST_CODES`), `F-POST-01` (two `AssemblyAgent`
classes), `F-KBCTX-02` (three distinct `kbctx:` grammars), `F-VR-04` (`ConsensusBuilder`
raises `AttributeError` on a dict), `F-VR-12` (`ConsensusReport` → `script`), `F-OST-16`
(`ORCH_CHANNELS` omits `_routing_decisions`/`_validation_reports`/…), `F-ARTIFACT-08` (FALSE).

Notable non-divergence proofs that nonetheless reproduced: `F-PHASE-01`'s executed
graph-vs-app split — output exactly `GRAPH continue_unrelated_work` / `APP generation`;
`F-VR-01` — `scene-writing-validator DIFFERS ['blocking_conditions']`, the other five
`AGREES`.

---

## 5. Anchor verification

Every `path:line` (or `path:line-line`) in every sampled finding's **De-facto owners** list
was resolved against the file system at the pinned snapshot.

| Metric | Count |
|---|---:|
| anchors checked | 730 |
| resolved to an existing file | 730 (100 %) |
| — resolved literally / with the `src/film_pipeline/` prefix | 681 |
| — resolved via unique basename | 35 |
| — ambiguous **short-path** spelling needing cluster context | 14 |
| line number past EOF | 0 |
| quoted text not found at the anchor (off-by-N) | 0 |
| verbatim-quote mismatch | 1 |

**The 14 short-path anchors.** These are written relative to the cluster instead of the
repo (`generation.py:108`, `qc.py:35`, `_shared.py:153`, `approval.py:217`,
`subgraphs/qc.py:262`, and the same spellings in `F-OST-02/06/07/10`, `F-CFG-04`,
`F-MCP-04/11`, `F-POST-07`). A reader cannot resolve them without knowing the cluster's
directory; `qc.py` alone has two candidates (`graph/nodes/qc.py`, `graph/subgraphs/qc.py`).
I resolved all 14 by hand to `graph/nodes/*`, `graph/subgraphs/*`,
`validation/validators/__init__.py` and `mcp/tools/registry.py`, and **every one landed on
the quoted content**, so this is a readability/§1.6.1 defect, not a wrong anchor. Minimal
correction: prefix the paths.

**The 1 verbatim-quote mismatch.** `F-PHASE-10`, owner
`src/film_pipeline/graph/nodes/qc.py:361` — the quote is
`"(({\"post\", \"assembly\", \"qc\"}, _run_assembly_validators),"` but the source at `:366`
reads `({"post", "assembly", "qc"}, _run_assembly_validators),` (one opening paren, not two).
The anchor and the semantic claim are right; the quote is mistyped.

No anchor pointed at a missing file, at a line past EOF, or at unrelated content.

---

## 6. Guards — pass, and not vacuous

Command (as specified):

```
UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest \
  tests/unit/artifacts/test_storage_boundary.py \
  tests/unit/graph/test_startup_boundaries.py \
  tests/unit/config/test_config_contract.py \
  tests/unit/graph/test_channel_registry.py -q
```

- **As written this command exits 1**, not 0: the repo's `pyproject.toml` addopts include
  `--cov=film_pipeline --cov-fail-under=90`, and running only these four files yields
  28.49 % coverage → `FAIL Required test coverage of 90% not reached`. That is the coverage
  gate, not a guard failure. Add `--no-cov`.
- With `--no-cov`: **49 test items — 47 passed, 2 skipped, 0 failed** (`EXIT=0`);
  per file: `test_storage_boundary.py` 8, `test_config_contract.py` 7,
  `test_channel_registry.py` 31, `test_startup_boundaries.py` 3. The two skips are
  provider/optional-extra skips inside `test_startup_boundaries.py`.

**Vacuity check (guard theatre?).** Demonstrated, not asserted. I loaded
`tests/unit/graph/test_channel_registry.py` in-process, confirmed its three registry guards
pass on the real data, then mutated only the *input* in memory (no file written):

| Guard | baseline | mutation | result |
|---|---|---|---|
| `test_registry_rows_are_unique` | pass | append a duplicate `OrchChannelSpec` | **fails** — `duplicate ORCH_CHANNELS rows: ['_orchestrator__candidate_refs']` |
| `test_every_schema_declared_orchestrator_key_has_a_registry_row` | pass | empty `ORCH_CHANNELS` | **fails** — `GraphState orchestrator keys without registry row: [...]` |
| `test_every_orchestrator_constant_has_a_registry_row` | pass | empty `ORCH_CHANNELS` | **fails** — `orchestrator constants without ORCH_CHANNELS row: [...]` |

Verdict: **not guard theatre**. At least the channel-registry guards derive their
expectations from the production artifacts and can actually fail. Caveat on the other two
files (read, not exhaustively mutation-tested): `test_config_contract.py` and
`test_storage_boundary.py` contain explicit "known dead / deliberately failing" allow-lists
(`test_known_dead_rows_cite_evidence`, `test_named_flx_f9_failures_stay_deliberate`), which
is the classic place for a guard to become self-satisfying; those specific rows would need
individual mutation testing to certify, which is outside this pass.

---

## 7. Absence claims

119 sampled findings lean on an absence ("no test does X", "grep returns nothing", "zero
callers", "nothing else reads this"). I attacked the checkable ones with commands of my own:

| Claim | Independent command | Result |
|---|---|---|
| `F-PHASE-02` no test references `PHASE_DIR_MAP` | `grep -rn -E "PHASE_DIR_MAP" tests --include=*.py` | **ABSENT — holds** |
| `F-PHASE-02` no test pins `FilmPhase` membership | `grep -rn -E "list\(FilmPhase\)\|len\(FilmPhase\)\|set\(FilmPhase\)" tests` | **ABSENT — holds** (tests pin `len(PHASE_ORDER) == 11`, a different object) |
| `F-GEN-11` `merge_generation_requests` untested | `grep -rn "merge_generation_requests" tests` | **ABSENT — holds** |
| `F-BUD-02` `update_budget_snapshot` has zero non-test callers | `grep -rn "update_budget_snapshot" src` | only the definition — **holds** |
| `F-GEN-02` `deliver_completed_job` has exactly one call site | `grep -rn "deliver_completed_job" src` | def + import + 1 call — **holds** |
| `F-GEN-07` `media_scene_dir` has zero production callers | `grep -rn "media_scene_dir(" src` | only the definition — **holds** |
| `F-POST-02` nothing writes `failure_decision` | `grep -rn '"failure_decision"' src` | only `mvp/__init__.py:162` (the declaration) — **holds** |
| `F-TEST-04` "bypassed by 64 direct store constructions" | `grep -rn "ArtifactStore(" tests` | exactly **64** — **holds** |
| `F-BOUNDARY-04` no import-linter config exists | `grep -nE "import-linter\|importlinter\|pytest-arch\|archon" pyproject.toml .pre-commit-config.yaml` | **ABSENT — holds** |
| `F-AGENT-04` no `model_adapter` fixture in `test_bibles.py` | `grep -n "llm_enabled\|model_adapter" tests/unit/mcp/tools/test_bibles.py` | **ABSENT — holds** |
| `F-TEST-09` omitted counts 3 / 5 | `grep -rn 'mock.patch("film_pipeline.mcp.tools.get_runtime"' tests \| wc -l`; `grep -rn 'mcp_tools.get_runtime = \|tools_pkg.get_runtime = ' tests \| wc -l` | **3 / 5 — holds** (though neither command is inside the `Reproduce` block) |

I found **no surviving false absence claim** in the sampled set. The false-absence defects
that prior verifiers recorded appear to have been fixed: the absences I tested are all
genuine. Two adjacent caveats, both evidence-hygiene rather than falsehoods:
`F-BOUNDARY-01`'s 53/32/21/17 AST ladder is reproducible (I get exactly 53/32/21/17 on
distinct package pairs) but the finding never states the sweep command; `F-TEST-09` and
`F-VR-02` quote counts (`3`, `5`, `65`) that their `Reproduce` block does not run.

---

## 8. Verdict on bar A2/A5

The audit set **does not meet bar A2 "zero unsourced claims" / A5-style evidence quality as
written**, but it is close and the failures are repairable rather than systemic. Of 146
sampled findings, 137 reproduce end-to-end; 3 state a result their own command contradicts
(`F-BOUNDARY-01` is the serious one — a Critical claim whose headline count is not produced
by its evidence); 3 have `Reproduce` blocks that cannot be run as written (a `grep` missing
`-r`, a `python -c` with an indented body, a `<snapshot>` placeholder); and 3 do not have a
`Reproduce` block at all (`F-CFG-02` buries a working one-liner in the drift proof;
`F-CFG-05`/`F-CFG-13` point at other sections). Add the mechanical defects: 100 % of the
sample's anchor paths resolve but 14 use un-resolvable short-path spellings, 1 verbatim quote
is mistyped, and 12 of 14 files indent their code fences such that a naive copy of the raw
markdown fails with `IndentationError`. The underlying architecture claims are, in the
overwhelming majority, real and independently confirmed — this is an audit with a strong
signal and a weak last mile. A2 is met only after correcting the three contradicting
commands, promoting/restating the three missing `Reproduce` blocks, fixing the three broken
commands, and prefixing the short-path anchors. As written, the set is **not** fully
reproducible by a reader who is not the author.

---

## 9. Cleanliness

- `git status --porcelain` → **empty** (verified before the review and after writing the
  report; `docs/` is gitignored, so no audit or review file is tracked).
- Exactly one repo file was created: `docs/modular-architecture/reviews/adversarial-evidence.md`.
  Nothing under `src/`, `tests/`, or the repo root was touched; all scratch files, run
  captures and the concurrency snapshot live under `/tmp/advrev/`.
- No reproduce command wrote into the repository; no `git checkout`/`clean`/`stash` was run.

### Top 5 worst evidence defects (ordered)

1. `F-BOUNDARY-01` — Critical finding; the three `Reproduce` greps yield **7** edges while the
   text claims **8**, and the 8th (`generation→artifacts`) is real but absent from the evidence.
2. `F-PHASE-02` — Critical finding; the `Reproduce` command prints **323**, the text and its
   own inline comment say **359** (`-rnE` vs `-roE`).
3. `F-ARTIFACT-08` — `Reproduce` prints `enum-only` = **6**, the text says **3**.
4. Commands that cannot be run as written: `F-MCP-02` (`grep` missing `-r` on `scripts/`,
   exit 2), `F-CFG-04` (indented `python -c` body → `IndentationError`), `F-CRP-01`
   (`PYTHONPATH=<snapshot>/src`, a placeholder).
5. `F-CFG-02`, `F-CFG-05`, `F-CFG-13` — no runnable `Reproduce` block; `F-CFG-05`/`F-CFG-13`
   are prose pointers ("the two commands above", "the commands recorded in §4").
