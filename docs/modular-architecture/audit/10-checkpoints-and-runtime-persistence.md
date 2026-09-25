# 10 — Checkpoints, Rollback, Resume, and Runtime Persistence Mode

Status: audit artifact under `00-methodology-and-quality-bar.md` (bar A).
Cluster: **Checkpoints, rollback, resume, runtime persistence mode**.

## Verification record (self-describing)

Independently verified under bar **A6** by `reviews/verify-10.md` (447 lines — a second
agent that did not write this file, working from its own pristine snapshot of the same
commit). The five post-verification findings (`F-CRP-12`…`F-CRP-16`) were verified in a
second round by `reviews/verify-15.md` (948 lines) against a pinned `fb85baa` snapshot:
**DOWNGRADED 1 (`F-CRP-12`), CONFIRMED-WITH-FIX 2 (`F-CRP-13`, `F-CRP-14`), CORRECTED 1
(`F-CRP-15`), STRENGTHENED 1 (`F-CRP-16`), REJECTED 0**; all corrections are applied
below, and `F-CRP-17` was added from verify-15 §7 item 3 (see the note in that finding).

- **Verdicts at the first reviewed revision (11 findings, `F-CRP-01`…`F-CRP-11`):**
  **CONFIRMED 11 / DOWNGRADED 2 / REJECTED 0 / UNVERIFIED 0.** Net: 9 confirmed as
  scored, 2 confirmed with recomputed severity.
- **Downgrades applied (D8, recomputed integers):** `F-CRP-05`
  impact 4→3 (score 12→9) and `F-CRP-10` impact 3→2 (score 9→6). Both keep every
  anchor and drift proof unchanged; the recomputed rationale is stated inline in
  each finding.
- **Band rule (normative, `00-methodology-and-quality-bar.md` §1.5 — replaces the
  earlier "band convention" note):** the band is a **function of the score**, so
  arithmetic wins over a band word; a verifier who disagrees with a band changes the
  *axes*, not the label. Findings re-banded here by score: `F-CRP-05` (the impact axis
  changed 4→3 ⇒ 12→9 ⇒ **High**), `F-CRP-13` (4×4=16 ⇒ **Critical**), `F-CRP-12`
  (verifier's axes 3×5=15 ⇒ **High**), `F-CRP-15` (verifier's axes 2×2=4 ⇒ **Medium**),
  `F-CRP-16` (verifier's axes 2×5=10 ⇒ **High**).
- **Missed seams folded in as new findings (verifier §3 + verify-15 §7):** `F-CRP-12`
  (= M1, **High 3×5=15** after verify-15), `F-CRP-13` (= M2, Critical 4×4=16),
  `F-CRP-14` (= M3, High 4×3=12), `F-CRP-15` (= M4, Medium 2×2=4, corroborating
  `F-CRP-04`), `F-CRP-16` (= M5, High 2×5=10), `F-CRP-17` (unrecorded logs-poisoner
  instance, High 4×3=12).
- **Promotion evidence:** M1/M2/M3 were re-run by this author against the pristine
  snapshot and are now findings with full §1.7 records and Appendix A.9–A.11
  reproducers; they were previously only marginal notes in F-CRP-01's blast radius
  and §7.3–§7.4. `F-CRP-17` is reproduced by this author in Appendix A.13.
- **Findings after this revision: 17** — **5 Critical, 9 High, 3 Medium, 0 Low**
  (Critical: 01, 02, 03, 04, 13; High: 05, 06, 07, 08, 09, 12, 14, 16, 17; Medium: 10,
  11, 15). The mix is *derived from the bullets, never asserted* — reproduce it from
  the repo root with:

  ```bash
  .venv/bin/python - <<'PY'
  import collections, pathlib, re
  text = pathlib.Path("docs/modular-architecture/audit/10-checkpoints-and-runtime-persistence.md").read_text()
  band = lambda s: "Critical" if s >= 16 else "High" if s >= 9 else "Medium" if s >= 4 else "Low"
  rows = re.findall(r"^- \*\*Severity:\*\* ([A-Za-z]+) \(impact (\d) × drift (\d) = (\d+)\)", text, re.M)
  mix: collections.Counter[str] = collections.Counter()
  for label, impact, drift, score in rows:
      assert int(impact) * int(drift) == int(score), (label, impact, drift, score)
      assert label == band(int(score)), (label, band(int(score)), impact, drift, score)
      mix[band(int(score))] += 1
  print(len(rows), "findings:", dict(mix))
  # -> 17 findings: {'Critical': 5, 'High': 9, 'Medium': 3, 'Low': 0}
  PY
  ```
- **Candidate-owner collisions recorded (verifier §4 + verify-15 §7):**
  `audit/03:928` (storage-root single ownership; the first verification pinned `:825`),
  `audit/03:484` F-CFG-08 with owner `audit/03:514` (three-way persistence-policy owner
  collision, escalated by `audit/11` F-MCP-09 at `audit/11:322`),
  `audit/01:262` F-PHASE-04 — see §6.5 and §6.7. Sibling audits are being edited
  concurrently, so these are cited by finding id **and** line.

## Audit record

- Repo: `${REPO_ROOT}`
- Branch: `modular-app`
- **Commit audited: `fb85baa0e6b769b709791a96a89980089304bf13` (`fb85baa`)** —
  `git rev-parse HEAD` at audit start.
- Method: every anchor below was re-read from a pristine snapshot of that commit
  (`git archive fb85baa | tar -x -C <tmp>`), not from the working tree. Line
  numbers are HEAD line numbers.
- **Concurrent-edit caveat (recorded, not evidence):** during this audit a
  *different* agent dirtied the working tree (`?? .arch-backup/`,
  `?? src/film_pipeline/architecture.py`, `?? tests/architecture/`, and
  `M src/film_pipeline/*/__init__.py` including `src/film_pipeline/checkpoints/__init__.py`, one of
  which was momentarily syntactically invalid — `src/film_pipeline/app/__init__.py`, `public_api=(,)`).
  No finding below depends on any working-tree state; all quotes come from
  `fb85baa`.
- Probes were executed with the repo venv against the pristine snapshot:
  `PYTHONPATH=<snapshot>/src UV_CACHE_DIR=.uvcache .venv/bin/python <probe>`.
  Reproducers are in Appendix A.

### Scope drift at HEAD (verified, not assumed)

The task brief names `checkpoints/branching.py` and omits `src/film_pipeline/checkpoints/resume.py`.
At `fb85baa` the package contains `branches.py` (no `branching.py`) **and**
`resume.py`. Both were read; the file list below is the authoritative coverage.

---

## 1. Coverage

Every file below was read in full (or, for the two very large files, the sections
listed) at HEAD, and is marked *has findings* or *clean*.

### 1.1 Primary cluster

| File | Lines | Verdict |
|---|---|---|
| `src/film_pipeline/checkpoints/__init__.py` | 21 | clean (export surface only) |
| `src/film_pipeline/checkpoints/manager.py` | 70 | **findings** F-CRP-01,02,04 |
| `src/film_pipeline/checkpoints/git_backend.py` | 90 | clean (single production backend; see §5.3) |
| `src/film_pipeline/checkpoints/rollback.py` | 122 | **findings** F-CRP-02,06 |
| `src/film_pipeline/checkpoints/branches.py` | 44 | **finding** F-CRP-05 (dead parallel lifecycle) |
| `src/film_pipeline/checkpoints/invalidation.py` | 67 | **finding** F-CRP-07 |
| `src/film_pipeline/checkpoints/resume.py` | 68 | **finding** F-CRP-05 |
| `src/film_pipeline/app/_persistence.py` | 265 | **findings** F-CRP-01,02,08 |
| `src/film_pipeline/app/_resume.py` | 107 | **finding** F-CRP-03,10 |
| `src/film_pipeline/app/_graph_exec.py` | 484 | **findings** F-CRP-02,04,05,11,16 |
| `src/film_pipeline/app/runtime.py` | 461 | **findings** F-CRP-01,02,04,09,11,13,14,15,17 |
| `src/film_pipeline/app/logging_setup.py` | 126 | **findings** F-CRP-09, F-CRP-17 (`configure_logging` mkdirs `<root>/logs` before the runtime opens the root) |
| `src/film_pipeline/app/safety.py` | 132 | **finding** F-CRP-14 (`persist_root()` is a third root notion; promoted from F-CRP-01's notes by verifier M3) |
| `src/film_pipeline/graph/services.py` | 137 | **finding** F-CRP-09 |
| `src/film_pipeline/graph/graph.py` | 201 | **findings** F-CRP-01,05,09,12 |
| `src/film_pipeline/mcp/server.py` | 270 | **findings** F-CRP-01,09,17 (`main` mkdirs `logs/` then opens the root) |
| `src/film_pipeline/cli/run.py` | 297 | **findings** F-CRP-01,09 |
| `src/film_pipeline/cli/driver.py` | 246 | **finding** F-CRP-01 |
| `src/film_pipeline/artifacts/storage.py` | 165 | **findings** F-CRP-01,12,13 |
| `src/film_pipeline/artifacts/project_storage.py` | 287 | clean as the on-disk layout owner; cited by F-CRP-01,02,08 |
| `src/film_pipeline/artifacts/store.py` | 834 | read §28-147 (write path/lock), §330-419 (README/index/deliverables); **no finding** (see §7) |
| `src/film_pipeline/artifacts/_layout.py` | 164 | clean (single layout constant module) |

### 1.2 Grep-beyond surface (grep hits inside this cluster)

Command: `grep -rn "FILM_PIPELINE_NO_PERSIST\|FILM_PIPELINE_PERSIST_STATE\|FILM_PIPELINE_RUNTIME_ROOT\|checkpoints\[\|checkpoint_managers\|run_id\|audit\|resume" --include=*.py src/ tests/ scripts/`

| File | Lines | Verdict |
|---|---|---|
| `src/film_pipeline/mcp/tools/checkpoints.py` | 331 | **findings** F-CRP-02,04,06,15 |
| `src/film_pipeline/mcp/tools/audit.py` | 75 | **finding** F-CRP-11 (direct `rt.audit_events` read, line 35) |
| `src/film_pipeline/mcp/tools/_profile_change.py` | — | read §430-472; **finding** F-CRP-07 (second `InvalidationEngine` caller) |
| `src/film_pipeline/mcp/tools/generation/_text_only.py` | — | **finding** F-CRP-10 (line 9) |
| `src/film_pipeline/app/services/_browse_ops.py` | 165 | read; read-only checkpoint/audit views (lines 132-165) — no finding |
| `src/film_pipeline/app/services/_generation_ops.py` | 287 | **finding** F-CRP-10 (line 20) |
| `src/film_pipeline/graph/edges.py` | 134 | read; **no finding** — its ordering table is pinned (see §5.4) |
| `src/film_pipeline/graph/_action_routing.py` | — | read §18-31, §310-345; `PHASE_ORDER` definition |
| `src/film_pipeline/graph/router.py` | 103 | clean (stable re-export surface) |
| `src/film_pipeline/graph/orchestrator_validators/planning_gates.py` | — | **finding** F-CRP-10 (emitter of the stale issue codes) |
| `src/film_pipeline/graph/nodes/_shared.py` | — | **finding** F-CRP-03 (`_apply_external_state`, line 167-193) |
| `src/film_pipeline/graph/nodes/approval.py` | — | read §193-260; consumer of `_external_state` |
| `src/film_pipeline/graph/consistency.py` | 84 | **finding** F-CRP-07 (provenance-based staleness) |
| `src/film_pipeline/graph/orchestrator_state.py` | — | read §179-210 (`get_candidate_refs`); cited by F-CRP-04 |
| `src/film_pipeline/testing/in_memory_git.py` | 193 | read; no finding (see §7) |
| `src/film_pipeline/schemas/runtime_state.py` | — | read §1-49; cited by F-CRP-05 |
| `src/film_pipeline/schemas/checkpoint.py` | — | read §1-80; cited by F-CRP-04,06 |
| `scripts/_scratch_bootstrap.py` | — | read §15-25; env writer (F-CRP-09 blast radius) |

### 1.3 Entry points (A1)

| Entry point | Persistence relevance |
|---|---|
| `cli.run.main` | **has findings** (F-CRP-01,09) — `src/film_pipeline/cli/run.py:193`, `:226` |
| `mcp.server.main` | **has findings** (F-CRP-01,09) — `src/film_pipeline/mcp/server.py:243-251` |
| `langgraph.json → src/film_pipeline/graph/graph.py:graph` | **has findings** (F-CRP-01,05,12) — module-level `graph = build_graph()` at `src/film_pipeline/graph/graph.py:201` opens a checkpointer at import time, which under `PERSIST_STATE=1` writes an unmarked `checkpoints/` directory *inside* the storage root and makes the root unopenable (F-CRP-12) |
| `app.product_gate.main` | not in cluster; verified to contain no persistence/checkpoint/root reference: `grep -n "persist\|checkpoint\|runtime_root" src/film_pipeline/app/product_gate.py` → no match |

### 1.4 Packages touched

`checkpoints`, `app` (+`app/services`), `graph` (+`graph/nodes`,
`graph/orchestrator_validators`), `mcp` (+`mcp/tools`, `mcp/tools/generation`),
`cli`, `artifacts`, `schemas`, `testing`, plus `scripts/`. No package in the
cluster is omitted.

---

## 2. Persistence-policy truth table (drift proof)

### 2.1 The derivation sites

The policy question "is durable persistence enabled?" is re-derived **seven times
across six modules** (P1–P6 are six sites; `src/film_pipeline/graph/services.py:31` and `:48` are two
distinct formulas reaching two different decisions — root vs profile), plus one
entrypoint that *rewrites* the environment (P7) and one three-way root branch (P8).
The "six sites" phrasing used for `F-CRP-09` therefore means six *modules/sites*, seven
*derivations* (verifier dispute D6).

| Site | Anchor | Expression (verbatim) |
|---|---|---|
| **P1** | `src/film_pipeline/app/_persistence.py:51` | `return bool(os.getenv("FILM_PIPELINE_PERSIST_STATE")) and not bool(` / `os.getenv("FILM_PIPELINE_NO_PERSIST")` |
| **P2** | `src/film_pipeline/graph/graph.py:43` | `if os.getenv("FILM_PIPELINE_NO_PERSIST") or not os.getenv("FILM_PIPELINE_PERSIST_STATE"):` / `return MemorySaver()` |
| **P3** | `src/film_pipeline/graph/services.py:31` | `if os.getenv("FILM_PIPELINE_NO_PERSIST"):` (chooses a temp artifact root) |
| **P4** | `src/film_pipeline/graph/services.py:48` | `profile = PROFILE_SANDBOX if os.getenv("FILM_PIPELINE_NO_PERSIST") else PROFILE_PRODUCTION` (chooses a storage profile) |
| **P5** | `src/film_pipeline/app/logging_setup.py:78` | `enabled = (` / `False` / `if os.getenv("FILM_PIPELINE_NO_PERSIST")` / `else (_persistence.use_persistent_runtime() if persist_enabled is None else persist_enabled)` |
| **P6** | `src/film_pipeline/cli/run.py:226` | `persist_enabled=not bool(os.getenv("FILM_PIPELINE_NO_PERSIST")),` |
| **P7** | `src/film_pipeline/mcp/server.py:243` | `if not os.getenv("FILM_PIPELINE_NO_PERSIST"):` / `os.environ.setdefault("FILM_PIPELINE_PERSIST_STATE", "1")` |
| **P8** | `src/film_pipeline/app/runtime.py:58-69` | three-way root branch (see §2.4) |

So: **P1 ≠ P3 = P4 = P6** as formulas; P3 and P4 are two derivations, not one. P2 ≡ P1
as a formula; P5 = P1 with an injected override; P7 is not a reader but the only writer
of the `PERSIST_STATE` default; P8 decides a *root*, not a boolean, and is the only site
that consults `FILM_PIPELINE_RUNTIME_ROOT` before the policy gate (see F-CRP-13).

### 2.2 Truth table (mechanically evaluated; Appendix A.1)

Rows are the five meaningful env combinations. All sites test **presence**
(`bool(os.getenv(...))`), never value — so `"0"`/`"false"` count as *set*
(§2.3). Row 5 is the concrete proof of that: `NO_PERSIST=0` is present, hence it
behaves exactly like `NO_PERSIST=1`, and every site returns the falsy/disabled value.
(An earlier revision of this table mislabelled row 4 as `NO_PERSIST=0` while printing
the unset-row values — verifier dispute D5; the row is now split so label and values
agree.)

| `PERSIST_STATE` | `NO_PERSIST` | P1 `use_persistent_runtime()` | P2 checkpointer | P3/P4 store default root / profile | P5 logging file handler | P6 CLI `persist_enabled` | Agree? |
|---|---|---|---|---|---|---|---|
| unset | unset | `False` | `MemorySaver` | `<storage_root>` / `production` | `False` (no file) | **`True`** | **NO** |
| unset | `1` | `False` | `MemorySaver` | temp dir / `sandbox` | `False` | `False` | yes |
| `1` | unset | `True` | `SqliteSaver` | `<storage_root>` / `production` | `True` | `True` | yes |
| `1` | `1` | `False` | `MemorySaver` | temp dir / `sandbox` | `False` | `False` | yes |
| `1` | `0` (present) | `False` | `MemorySaver` | temp dir / `sandbox` | `False` | `False` | yes |

Observed divergence: **row 1** — `src/film_pipeline/cli/run.py:226` reports persistence enabled
while the policy authority (`src/film_pipeline/app/_persistence.py:51`) and the graph checkpointer
(`src/film_pipeline/graph/graph.py:43`) are disabled. In that same row P3/P4 *return* the production
storage-root default and the `production` profile. **This is a library default, not
the effective root of a composed run** (verifier dispute D4): `tests/conftest.py:98`
sets `FILM_PIPELINE_NO_PERSIST=1` for the whole session, so the suite never takes the
production branch, and in a composed `StudioRuntime` the effective root is
`runtime_root` (`src/film_pipeline/app/runtime.py:75-77`) or a per-pid temp dir (`:67-69`) — never
`_default_artifact_root()`'s return value. The exposure is confined to a **bare**
`GraphServices()` construction — `src/film_pipeline/graph/services.py:63`
`artifact_store: ArtifactStore = field(default_factory=lambda: _artifact_store(None))` —
which writes to the real root with the `production` profile while the policy says
persistence is off.

Conditional sites:
- **P2** is conditional on `runtime_root` only for the *path*
  (`src/film_pipeline/graph/graph.py:46`), never for the mode.
- **P4** is unconditional-both-ways (always a profile).
- **P5** is conditional on the caller's `persist_enabled` override
  (`src/film_pipeline/app/logging_setup.py:81`); `src/film_pipeline/cli/run.py:224-227` and `src/film_pipeline/mcp/server.py:251`
  (`configure_logging(configured_runtime_root())` → override `None`) exercise
  different arms.
- **P7** is conditional on `NO_PERSIST` and is *side-effecting*: under the MCP
  server, simply importing/starting the entrypoint changes the value every later
  reader sees. Under the CLI it never runs.

### 2.3 Presence-truthiness hazard (verified, not a divergence)

All six modules use presence tests, so `NO_PERSIST=0` **disables** persistence.
Probe (Appendix A.2):

```
PERSIST_STATE=1 NO_PERSIST=0 -> use_persistent_runtime(): False | checkpointer: InMemorySaver
```

Every site agrees on this, so it is a shared hazard rather than a drift, but it
is exactly the failure mode that makes a *documented* default dangerous once the
policy is re-derived in seven places with no shared constant/enum.

### 2.4 Root resolution: four independent formulas plus one derived chain

`src/film_pipeline/artifacts/storage.py` owns R1 and defines R2 *in terms of* R1
(`tests/unit/artifacts/test_storage.py:63-70` pins the derivation), and
`src/film_pipeline/app/_persistence.py:41-42` (R3) **delegates** to `default_runtime_root()`, which is
R1. Counting convention (verifier dispute D1): the independent formulas are
**{R1 storage root}, {R6 run root}, {`src/film_pipeline/cli/driver.py:69` store root}, {`src/film_pipeline/graph/graph.py:46`
checkpointer dir}** — four — while **{R3 → R2 → R1}** is one derived chain, not a
fifth independent answer. An earlier revision's headline said "five independent
paths"; that was one too many and is corrected here. R4 composes R3/R2/R1 and the
per-pid temp fallback.

| # | Anchor | Returns | Kind |
|---|---|---|---|
| R1 | `src/film_pipeline/artifacts/storage.py:82-89` | storage root: explicit → `FILM_PIPELINE_STORAGE_ROOT` → `~/.film-pipeline/projects` | **independent formula** |
| R2 | `src/film_pipeline/artifacts/storage.py:61-79` | three derived defaults, all from R1: `default_runtime_root() == resolve_storage_root()` (`:69`), `default_checkpoints_root() == resolve_storage_root()/"checkpoints"` (`:74`), `default_run_root() == resolve_storage_root()/"runs"/"default"` (`:79`) | derived from R1 |
| R3 | `src/film_pipeline/app/_persistence.py:39-42` | runtime root: `FILM_PIPELINE_RUNTIME_ROOT` → R2 | derived chain (env → R2 → R1) |
| R4 | `src/film_pipeline/app/runtime.py:58-69` | root: R3 if `RUNTIME_ROOT` set; else R2 if P1; else `tempfile.gettempdir()/"film_pipeline_runtime_<pid>"` | composition of R3/R2 + temp fallback |
| R5 | `src/film_pipeline/graph/graph.py:46` | checkpointer dir: `runtime_root/"checkpoints"` if a runtime root was passed, else **R2** (`default_checkpoints_root()`) | **independent formula** |
| R6 | `src/film_pipeline/cli/driver.py:69` | artifact store root: `runtime_root/"artifacts"` | **independent formula** |
| R7 | `src/film_pipeline/app/runtime.py:190-194` | `_artifact_root()`: store root, else R1 — **no caller in `src/`** (dead; `grep -rn "_artifact_root" src/` returns only this definition and `graph/services._default_artifact_root`) | derived from R1 (dead) |
| R8 | `src/film_pipeline/app/safety.py:25-32` | "persist base": `resolve_storage_root().resolve().parent` | derived from R1 (see F-CRP-14) |

They do **not** always coincide. R4 composes R2 into the store root
(`src/film_pipeline/app/runtime.py:71-77`: "the artifact store opens the runtime root itself, so
state and artifacts are siblings"), so the app's project directory is
`<root>/<project_id>`. R6 makes the CLI's store root `<run_root>/artifacts`, so
the CLI's project directory is `<run_root>/artifacts/<project_id>` — a different
path for the same project id (probe, Appendix A.3):

```
CLI  project dir = <storage>/runs/default/artifacts/p1
APP  project dir = <storage>/p1
SAME PROJECT DIR? False
```

R5 also splits: the module-level `graph = build_graph()` at `src/film_pipeline/graph/graph.py:201`
(`langgraph.json`'s target) uses R2, while every app run passes
`runtime_root=rt.runtime_root` (`src/film_pipeline/app/_graph_exec.py:39`), so two SQLite
checkpointer files exist whenever `runtime_root != storage_root`.

---

## 3. Checkpoint state authority map

Legend: **W** = writer, **R** = reader. "In-memory" = process state; "disk" =
durable representation.

### 3.1 `CheckpointMetadata` (the checkpoint record)

| Representation | Writers | Reader(s) | Single / distributed |
|---|---|---|---|
| `StudioRuntime.checkpoints: dict[str, CheckpointMetadata]` (`src/film_pipeline/app/runtime.py:48`) | `src/film_pipeline/app/runtime.py:270` (create), `src/film_pipeline/app/_persistence.py:143` (restore), `src/film_pipeline/app/runtime.py:198` (delete-prune) | `runtime.list_checkpoints` (`:283-284`), `get_checkpoint` (`:287`), `src/film_pipeline/mcp/tools/checkpoints.py:101,129,137-138,151,163,209,226,290,318`, `src/film_pipeline/app/services/_browse_ops.py:135` | **distributed** — 1 of 2 registries |
| `CheckpointManager.checkpoints: dict[str, CheckpointMetadata]` (`src/film_pipeline/checkpoints/manager.py:23`) | `src/film_pipeline/checkpoints/manager.py:57` (create), `src/film_pipeline/app/_persistence.py:145` (restore) | `src/film_pipeline/checkpoints/rollback.py:40` (`RollbackManager.rollback_to_checkpoint`), via `src/film_pipeline/mcp/tools/checkpoints.py:184,268` | **distributed** — 1 of 2 registries |
| `checkpoints/checkpoints.jsonl` (disk) | **single**: `src/film_pipeline/app/_persistence.py:236` → `ProjectStorage.append_checkpoints` (`src/film_pipeline/artifacts/project_storage.py:194`) | `src/film_pipeline/app/_persistence.py:138` (restore only) | **single writer** (clean) |
| git commit + annotated tag (the durable payload) | `src/film_pipeline/checkpoints/manager.py:40-41`; `src/film_pipeline/checkpoints/rollback.py:52,122`; `src/film_pipeline/app/runtime.py:128`; `src/film_pipeline/artifacts/project_storage.py:262` | `GitBackend.list_files/log` (`src/film_pipeline/checkpoints/git_backend.py:61-69`) | distributed across 5 commit sites, one backend |

In-memory metadata: **3 modules, 5 assignment sites, 2 registries, no single
writer.** On-disk JSONL: **1 writer.** Git: 5 commit/tag sites over one backend.

### 3.2 Other runtime-persistence state

| Field / file | Writers | Readers | Verdict |
|---|---|---|---|
| `project.json` (`ProjectRecord`) | **single funnel**: `src/film_pipeline/app/_persistence.py:259-265` → `ProjectStorage.write_project_record` (`src/film_pipeline/artifacts/project_storage.py:152`); the runtime wrapper `_persist_project_state` has 17 call sites, all reaching this one writer (`grep -rn "persist_project_state" src/` → 21 hits = 2 definitions + 17 wrapper calls + 2 module-function calls) | `src/film_pipeline/app/_persistence.py:102,210`; `src/film_pipeline/artifacts/store.py:343`; `src/film_pipeline/app/services/_browse_ops.py` freshness | **single writer** (clean) |
| `state/graph-state.json` (`GraphStateSnapshot`) | **single**: `src/film_pipeline/app/_graph_exec.py:141` → `ProjectStorage.write_graph_state` (`:179`) | **zero production readers** — `grep -rn "read_graph_state" src/` returns only the docstring example (`src/film_pipeline/artifacts/project_storage.py:23`) and the definition (`:167`) | **write-only** (F-CRP-05) |
| LangGraph checkpointer DB | LangGraph itself via `graph.invoke` (`src/film_pipeline/app/_graph_exec.py:72,212,382,393`); connection/root chosen at `src/film_pipeline/graph/graph.py:46-51` | `graph.get_state(config)` (`src/film_pipeline/app/_graph_exec.py:194,380`) | **2 root derivations** (R5) + an import-time third: `src/film_pipeline/graph/graph.py:201` (`graph = build_graph()`) opens R2 with no runtime at all — **F-CRP-12** |
| `audit/audit-log.jsonl` | **single disk writer**: `src/film_pipeline/app/_persistence.py:249` → `ProjectStorage.append_audit_events` (`:199`); in-memory appenders: `src/film_pipeline/app/runtime.py:292`, `src/film_pipeline/app/_persistence.py:152` | `src/film_pipeline/app/_persistence.py:150` (restore), `runtime.get_audit_log` (`:305`), `src/film_pipeline/mcp/tools/audit.py:29`, `src/film_pipeline/app/services/_browse_ops.py:156-165` | single disk writer; **no writer for rollbacks** (F-CRP-06) |
| `RollbackRecord` | `src/film_pipeline/checkpoints/rollback.py:83` (in-memory `records`, never persisted, never read) and `src/film_pipeline/mcp/tools/checkpoints.py:66` (persisted as an `ArtifactType.ROLLBACK_RECORD` envelope) | none for `rollback.records` (`grep -rn "\.records\b" src/` → only `src/film_pipeline/checkpoints/rollback.py:92` append); the artifact is readable via the store | **split authority 2/2** (F-CRP-06) |
| `BranchMetadata` | `src/film_pipeline/checkpoints/branches.py:37` (`BranchManager.branches`) | none in `src/` | **dead** (F-CRP-05) |
| `ResumeSnapshot` | `src/film_pipeline/checkpoints/resume.py:53` (`ResumeManager.snapshots`) | none in `src/` (tests only) | **dead** (F-CRP-05) |
| Run record / `run_id` | **no writer** — `grep -rn "run_id" --include=*.py src/` → no match; no `class .*Run` in `schemas/`; `default_run_root()` (`src/film_pipeline/artifacts/storage.py:79`) is only consumed by `src/film_pipeline/cli/run.py:193` and used for logs/artifacts | — | **absent concern** |

### 3.3 In-memory checkpoint registries: observed divergence

Probe (Appendix A.4), after a runtime restart on the same root:

```
B. after restart: rt.checkpoints has cp?       True
B. after restart: manager.checkpoints has cp?  True
C. rollback after clearing ONLY the manager dict -> {"ok": false,
   "error": "Checkpoint not found: checkpoint:p1:intake:493cb926"}
```

The MCP rollback path *validates* against `rt.checkpoints`
(`src/film_pipeline/mcp/tools/checkpoints.py:290` `cp = rt.get_checkpoint(checkpoint_id)`) and then
*executes* against `manager.checkpoints`
(`src/film_pipeline/checkpoints/rollback.py:40` `checkpoint = self.checkpoint_manager.get(checkpoint_id)`).
Two registries, one logical state.

---

## 4. Findings

### F-CRP-01 — Run, runtime, storage, and checkpoint roots are resolved by four independent formulas (plus one derived env→R2→R1 chain) that do not coincide

- **Class:** O5 (policy-by-branch) with O3 (split state authority over "where state lives")
- **Severity:** Critical (impact 5 × drift 4 = 20). *Verifier note (D1): the verifier
  would re-score drift **5**, not 4, because `tests/unit/cli/test_help_snapshot.py`
  freezes the *wrong* help text and no test composes `default_run_root()` with
  `src/film_pipeline/cli/driver.py:69`. The score is unchanged at 20 either way (5×5 would raise it);
  the count sentence, not the severity, was the defect.*
- **Concern:** One rule — "where does a run's state live?" — is re-derived at four
  independent call sites; the CLI's answer differs from the app's, and the CLI's
  answer makes the shared storage root unopenable for the app.
- **De-facto owners:**
  - `src/film_pipeline/artifacts/storage.py:79` — the run root (*inside* the storage root) — `"return resolve_storage_root() / "runs" / "default""`
  - `src/film_pipeline/cli/driver.py:69` — the store root as a *subdirectory* of the run root — `"artifacts_root = str(runtime_root / "artifacts")"`
  - `src/film_pipeline/app/runtime.py:75-77` — the store root as the runtime root itself — `"self.services = _build_services_for_mode("` / `"self.server_mode, artifacts_root=self.runtime_root"`
  - `src/film_pipeline/graph/graph.py:46` — the checkpointer dir from `runtime_root`, else from the storage root — `"runtime_root / "checkpoints" if runtime_root is not None else default_checkpoints_root()"`
  - `src/film_pipeline/app/_persistence.py:41-42` — a **derived chain**, not an independent answer — `"raw_root = os.getenv("FILM_PIPELINE_RUNTIME_ROOT", "").strip()"` / `"return Path(raw_root) if raw_root else default_runtime_root()"` (delegates to `default_runtime_root()`, itself R1)
  - `src/film_pipeline/cli/run.py:114` — documents a fifth answer in help text — `"Default: <storage root>/../runs/default (see FILM_PIPELINE_STORAGE_ROOT)."`
- **Verifier disputes applied:** **D1** — the count is *four independent formulas plus
  the R3→R2→R1 chain*, not "five independent paths" (see §2.4). **D2/M1** — the
  storage-root refusal is **not** only a CLI consequence: a bare
  `import film_pipeline.graph.graph` reaches it too, and that stronger case is now
  finding **F-CRP-12**; the blast radius below records both.
- **Drift proof:** *existing divergence*, reproduced mechanically. The CLI writes
  its marker at `<storage>/runs/default/artifacts/storage.json`
  (`src/film_pipeline/cli/driver.py:69` → `src/film_pipeline/graph/services.py:49` → `src/film_pipeline/artifacts/storage.py:129`), so
  the storage root itself becomes a non-empty, unmarked directory; the app then
  refuses to open it (`src/film_pipeline/app/runtime.py:62` → `ensure_storage_root` →
  `src/film_pipeline/artifacts/storage.py:160` `raise StorageRootError(...)`). Observed
  (Appendix A.5): `after CLI run, children of storage root: ['runs']` then
  `app FAILED to open the storage root: StorageRootError`. Independently reachable
  by import alone (F-CRP-12): `after import, children of storage root: ['checkpoints']`
  then the same `StorageRootError`. Additionally the
  project directory is `<run_root>/artifacts/<pid>` for the CLI vs `<root>/<pid>`
  for the app (Appendix A.3), breaking the "one root for the whole project
  folder" invariant asserted in `src/film_pipeline/app/runtime.py:71-75`. No test covers the CLI
  layout: `tests/unit/artifacts/test_storage.py:63-70` pins
  `default_run_root() == root / "runs" / "default"` but never composes it with
  `src/film_pipeline/cli/driver.py:69`, and `:81-84` pins the app path only for a default-constructed
  `StudioRuntime`. The
  operator-facing help text (`src/film_pipeline/cli/run.py:114`) is already wrong today
  (`<storage root>/../runs/default` vs `<storage root>/runs/default`), and
  `tests/unit/cli/test_help_snapshot.py:55` pins that the *wrong* text stays.
- **Reproduce:** run from the repo root, no substitution. The block inlines Appendix
  A.5 (CLI marker path) and Appendix A.9 (import path); the static half follows it, and
  the verified output is shown after the block.

  ```bash
  PYTHONPATH=src .venv/bin/python - <<'PY'
  import os, tempfile
  from pathlib import Path

  tmp = Path(tempfile.mkdtemp(prefix="crp01_"))
  os.environ["FILM_PIPELINE_STORAGE_ROOT"] = str(tmp / "storage")

  # Appendix A.5 - the CLI layout writes its marker under <storage>/runs/default/artifacts
  from film_pipeline.artifacts.storage import (
      default_run_root, ensure_storage_root, resolve_storage_root,
  )
  from film_pipeline.artifacts.store import ArtifactStore

  ArtifactStore(root=default_run_root() / "artifacts")
  print("CLI: children of storage root:", sorted(p.name for p in resolve_storage_root().iterdir()))
  try:
      ensure_storage_root(resolve_storage_root())
      print("CLI: app opened storage root: OK")
  except Exception as exc:
      print(f"CLI: app FAILED: {type(exc).__name__}")

  # Appendix A.9 - a bare import of the langgraph target poisons a fresh root
  tmp2 = Path(tempfile.mkdtemp(prefix="crp01b_"))
  os.environ["FILM_PIPELINE_STORAGE_ROOT"] = str(tmp2 / "storage")
  os.environ["FILM_PIPELINE_PERSIST_STATE"] = "1"
  os.environ.pop("FILM_PIPELINE_NO_PERSIST", None)
  os.environ.pop("FILM_PIPELINE_RUNTIME_ROOT", None)
  import film_pipeline.graph.graph  # module-level `graph = build_graph()` at src/film_pipeline/graph/graph.py:201

  print("IMPORT: children of storage root:", sorted(p.name for p in (tmp2 / "storage").iterdir()))
  try:
      ensure_storage_root(tmp2 / "storage")
      print("IMPORT: app opened storage root: OK")
  except Exception as exc:
      print(f"IMPORT: app FAILED: {type(exc).__name__}")
  PY
  grep -rn "default_run_root()\|runtime_root / \"artifacts\"\|artifacts_root=self.runtime_root\|runtime_root / \"checkpoints\"" --include=*.py src/
  ```

  Output (this author, from the repo root at `fb85baa`):

  ```
  CLI: children of storage root: ['runs']
  CLI: app FAILED: StorageRootError
  IMPORT: children of storage root: ['checkpoints']
  IMPORT: app FAILED: StorageRootError
  ```
- **Blast radius:** `src/film_pipeline/cli/driver.py`, `src/film_pipeline/cli/run.py`, `src/film_pipeline/app/runtime.py`,
  `src/film_pipeline/graph/services.py`, `src/film_pipeline/graph/graph.py`, `src/film_pipeline/artifacts/storage.py`,
  `src/film_pipeline/mcp/server.py` (via `configured_runtime_root`), `scripts/_scratch_bootstrap.py`.
  User-visible: (a) the storage root becomes unopenable for the MCP server / app
  after **either** a headless CLI run (`['runs']`) **or** a bare import of
  `film_pipeline.graph.graph` under `PERSIST_STATE=1` (`['checkpoints']`) — the
  latter is F-CRP-12 and needs no runtime at all; (b) the same project id maps to
  different directories on the two entry points; (c) with
  `FILM_PIPELINE_RUNTIME_ROOT` set, two SQLite checkpointer files exist
  (`<runtime_root>/checkpoints/...` from the app vs `<storage>/checkpoints/...`
  from the `langgraph.json` module-level graph at `src/film_pipeline/graph/graph.py:201`).
- **Candidate owner module:** `runtime_persistence` — owns the persistence policy
  and the one `RootLayout` value object. **Collision resolved (§6.5):** the
  storage-root *resolver* (R1) stays single-owned by `src/film_pipeline/artifacts/storage.py`
  (`audit/03:825`, guard `tests/unit/artifacts/test_storage.py:29-78` — unchanged);
  what is unowned at HEAD is the **composition** of the roots —
  policy → `studio`, lifecycle → `checkpoints`, bytes → `storage`. This module owns
  the composition only, not R1.
- **Extraction sketch:** introduce `PersistenceMode` + `RootLayout` (fields:
  `storage_root`, `runtime_root`, `checkpoint_root`, `run_root`) resolved once;
  make `src/film_pipeline/cli/driver.py:69`, `src/film_pipeline/app/runtime.py:75`, `src/film_pipeline/graph/graph.py:46` and
  `src/film_pipeline/graph/services.py:49` consume it. Decide the run root once (today two
  contradictory answers: nested `runs/` per `src/film_pipeline/artifacts/storage.py:79` and the CLI's
  `artifacts/` subdir per `src/film_pipeline/cli/driver.py:69`). Guard test: build a CLI run and an app
  runtime from one env, assert `RootLayout` equality and that the storage root
  still opens.
- **Prior art:** `documentation/storage-upgrade-plan.md:297` sets the bar
  ("runtime/checkpoint/run defaults all derive from `resolve_storage_root()`"),
  and `:224` records `~/.film-pipeline/runs/<name>/` as the run-dir shape; **new
  at HEAD** is the CLI's `runtime_root/"artifacts"` store root and the resulting
  marker poisoning, neither of which is covered by the plan's P1 bar.

### F-CRP-02 — Checkpoint metadata lives in two in-memory registries; the rollback path validates against one and executes against the other

- **Class:** O3 (split state authority)
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** One checkpoint record, two in-memory registries, with different
  readers on the validate and execute halves of the same operation.
- **De-facto owners:**
  - `src/film_pipeline/app/runtime.py:48` — registry A — `"checkpoints: dict[str, CheckpointMetadata] = field(default_factory=dict)"`
  - `src/film_pipeline/checkpoints/manager.py:23` — registry B — `"checkpoints: dict[str, CheckpointMetadata] = field(default_factory=dict)"`
  - `src/film_pipeline/app/_persistence.py:143` + `:145` — the restore path writes both (the mutation below deletes `:145`; `:144` is only the `if`) — `"rt.checkpoints[meta.checkpoint_id] = meta"` / `"manager.checkpoints[meta.checkpoint_id] = meta"`
  - `src/film_pipeline/app/runtime.py:270` / `src/film_pipeline/checkpoints/manager.py:57` — create writes both, in two modules
  - `src/film_pipeline/mcp/tools/checkpoints.py:290` — validates against A — `"cp = rt.get_checkpoint(checkpoint_id)"`
  - `src/film_pipeline/checkpoints/rollback.py:40` — executes against B — `"checkpoint = self.checkpoint_manager.get(checkpoint_id)"`
- **Verifier disputes applied:** **D10** — the de-facto-owner anchor is now written as
  `:143` + `:145` (not the range `:143-145`), because `:144` is the `if` guard and
  `:145` is the assignment the mutation removes.
- **Drift proof:** *existing divergence*, reproduced (Appendix A.4):
  after a normal create both registries hold the record, but clearing **only**
  registry B (the state `src/film_pipeline/app/_persistence.py:145` produces) makes
  `rollback_to_checkpoint` return
  `{"ok": false, "error": "Checkpoint not found: checkpoint:p1:intake:493cb926"}`
  while `rt.get_checkpoint(cp_id)` still finds it. Mutation scenario: delete
  `src/film_pipeline/app/_persistence.py:145` — the verifier executed this mutation and the whole
  unit suite stayed green (1866 passed, 3 skipped) — and
  `tests/unit/artifacts/test_state_persistence.py:288`
  (`assert rt2.list_checkpoints("resume-p")`) still passes because it only reads
  registry A, and no test performs restart-then-rollback (the only rollback tests,
  `tests/unit/mcp/tools/test_checkpoints.py:110-121`, create and roll back in one
  runtime).
- **Reproduce:** Appendix A.4; static — the pattern includes `manager.checkpoints` so the
  registry-B restore write at `src/film_pipeline/app/_persistence.py:145` appears (the
  narrower "two registries" wording alone would not print it):
  `grep -rn "checkpoint_managers\|rt\.checkpoints\|self\.checkpoints\|manager\.checkpoints" --include=*.py src/`
- **Blast radius:** `src/film_pipeline/app/_persistence.py`, `src/film_pipeline/app/runtime.py`,
  `src/film_pipeline/checkpoints/manager.py`, `src/film_pipeline/checkpoints/rollback.py`,
  `src/film_pipeline/mcp/tools/checkpoints.py`, `src/film_pipeline/app/services/_browse_ops.py`. User-visible: a
  checkpoint listed by `list_checkpoints` can be rejected by
  `rollback_to_checkpoint`; the two APIs disagree about existence.
- **Candidate owner module:** `runtime_persistence.checkpoints` — one registry,
  one writer, projection views for consumers.
- **Extraction sketch:** delete `CheckpointManager.checkpoints`; give
  `RollbackManager` the registry (or a lookup callable) instead of a manager
  object. Guard test: restart → rollback must succeed; a test asserting
  `len(rt.checkpoints) == len(manager.checkpoints)` for every restore is the
  cheap version.
- **Prior art:** `documentation/audit-findings.md:117` ("Checkpoint metadata is
  in-memory only; `CheckpointManager` never persists it") — **partially fixed**:
  the JSONL append now exists (`src/film_pipeline/app/_persistence.py:236`), but the *two-registry*
  split is new at HEAD and is a different defect from the one recorded there.

### F-CRP-03 — The resume seam between `src/film_pipeline/app/_resume.py` and the graph is stringly-typed with no shared contract

- **Class:** O8 (missing contract) with O5 (policy re-derived at two ends)
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** The producer and consumer of the resume payload's `_external_state`
  vocabulary agree only by matching string literals.
- **De-facto owners:**
  - `src/film_pipeline/app/_resume.py:104` — producer — `"external_state["remove_issue_codes"] = sorted(_STALE_REQUEST_CODES)"`
  - `src/film_pipeline/app/_resume.py:106` — envelope key, raw dict — `"payload["_external_state"] = external_state"`
  - `src/film_pipeline/graph/nodes/_shared.py:190` — consumer — `"remove_codes = external_state.get("remove_issue_codes")"`
  - `src/film_pipeline/graph/nodes/approval.py:140` — second consumer, same opaque dict — `"external_state = decision.get("_external_state")"`
- **Drift proof:** mutation scenario with a silent failure. Change the consumer
  literal at `src/film_pipeline/graph/nodes/_shared.py:190` to any other key: the stale generation
  blockers are never dropped, so `auto_checkpoint`-restored resumes fall through
  `src/film_pipeline/app/_graph_exec.py:232` (`if _approval_stalled(state, active, current_phase):`)
  into `advance_to_next_phase` and audit `resume_stalled_manual_advance`
  (`src/film_pipeline/app/_graph_exec.py:233-240`) — a manual state-machine advance where
  `src/film_pipeline/app/_graph_exec.py:176-178` promises the fallback fires "only when no
  checkpoint exists". No test fails: the producer literal is pinned
  (`tests/unit/app/test_resume_integrity.py:409-411` asserts
  `external["remove_issue_codes"]`) but the consumer key is not — the only
  consumer test, `tests/unit/graph/test_real_human_gates.py:371-400`, passes only
  `generation_requests` in `_external_state` and never asserts
  `remove_issue_codes`.
- **Reproduce:** `grep -rn "_external_state\|remove_issue_codes" --include=*.py src/ tests/`
  → producer at `src/film_pipeline/app/_resume.py:104`, consumer at `src/film_pipeline/graph/nodes/_shared.py:190`,
  no shared constant; consumer-side test coverage absent.
- **Blast radius:** `src/film_pipeline/app/_resume.py`, `src/film_pipeline/app/_graph_exec.py`,
  `src/film_pipeline/graph/nodes/_shared.py`, `src/film_pipeline/graph/nodes/approval.py`. User-visible: approval at
  the generation gate can be applied by the manual fallback instead of the graph,
  or stall.
- **Candidate owner module:** `graph.resume_protocol` (or a typed
  `ResumePayload` in `app._resume`) — one dataclass for the resume envelope.
- **Extraction sketch:** replace the raw dict with a typed
  `ResumeExternalState(generation_requests=..., remove_issue_codes=...)`; the
  graph consumes the type. Guard test: a round-trip test that builds the payload
  and applies it to a graph state, asserting the stale codes disappear.
- **Prior art:** new.

### F-CRP-04 — `CheckpointMetadata.artifact_versions` has two writers with different rules; rollback and invalidation silently no-op for MCP-created checkpoints

- **Class:** O3 (split state authority over one field) with O8 (the rollback
  tools depend on an undeclared non-empty invariant)
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Verifier disputes applied:** **D9** — the causal claim is corrected: the MCP tool
  *could* pass `artifact_versions` (`src/film_pipeline/app/runtime.py:253` accepts it; confirmed at
  runtime, `"artifact_versions" in StudioRuntime.create_checkpoint.__code__.co_varnames`
  → `True`) and still does not; the defect is that **no factory derives it** — the only
  derivation lives in the auto path (`src/film_pipeline/app/_graph_exec.py:102-103`), which is recorded as
  the corroborating `F-CRP-15` (M4). **D3** — Appendix A.6 was not executable as printed
  (it seeded the raw `"script"` key while `get_candidate_refs` reads the namespaced
  `_ORCH_NS__candidate_refs` key, `src/film_pipeline/graph/orchestrator_state.py:27`); it is rewritten to
  drive the real MCP tool path.
- **Concern:** The same checkpoint field is populated by the auto path and left
  empty by the manual API path, but every rollback/invalidation feature keys on it.
- **De-facto owners:**
  - `src/film_pipeline/app/_graph_exec.py:102-103` — auto path fills it — `"candidate_refs = get_candidate_refs(state)"` / `"artifact_versions = dict(candidate_refs)"`
  - `src/film_pipeline/mcp/tools/checkpoints.py:112-116` — manual path omits it — `"cp = rt.create_checkpoint("` / `"project_id=active["project_id"],"` / `"phase=active.get("current_phase", "intake"),"` / `"reason=reason,"`
  - `src/film_pipeline/app/runtime.py:253` — the omission is legal — `"artifact_versions: dict[str, str] | None = None,"`
  - `src/film_pipeline/checkpoints/manager.py:49` — the default becomes empty — `"artifact_versions=artifact_versions or {},"`
  - `src/film_pipeline/mcp/tools/checkpoints.py:228` — rollback-by-artifact requires it — `"if cp.git_commit and artifact_id in cp.artifact_versions:"`
  - `src/film_pipeline/mcp/tools/checkpoints.py:274` — invalidation scope comes from it — `"list(cp.artifact_versions.keys()),"`
- **Drift proof:** *existing divergence*, reproduced (Appendix A.6):
  after `create_checkpoint` through the MCP tool,
  `checkpoint.artifact_versions = {}` and
  `get_invalidation_report(...).will_invalidate == []`; the auto path is pinned by
  `tests/unit/app/test_runtime.py:37` (`assert cp.artifact_versions.get("script") == "artifact:script:v1"`),
  and no test asserts the manual path's map, so the divergence is unobserved.
  `rollback_artifact` with no explicit checkpoint then answers
  `"No checkpoint found containing artifact 'x'."` (`src/film_pipeline/mcp/tools/checkpoints.py:235`)
  although the checkpoint exists.
- **Reproduce:** Appendix A.6; static:
  `grep -rn "artifact_versions" --include=*.py src/film_pipeline/app src/film_pipeline/mcp src/film_pipeline/checkpoints`
- **Blast radius:** `src/film_pipeline/mcp/tools/checkpoints.py` (`rollback_artifact`,
  `rollback_to_checkpoint`, `get_invalidation_report`, `list_artifact_versions`),
  `src/film_pipeline/checkpoints/rollback.py` (`_invalidation_report`), `src/film_pipeline/app/_graph_exec.py`.
  User-visible: the documented `create_checkpoint` tool produces a rollback target
  that reports zero invalidation and cannot be found by artifact.
- **Candidate owner module:** `runtime_persistence.checkpoints` — the checkpoint
  factory must derive `artifact_versions` itself.
- **Extraction sketch:** move the `get_candidate_refs` derivation from
  `src/film_pipeline/app/_graph_exec.py:102-103` into the single checkpoint factory so both paths
  produce the same record; or make the rollback tools refuse a checkpoint with an
  empty map instead of returning an authoritative-looking empty report. Guard
  test: MCP create → `get_invalidation_report` is non-empty for a project with
  candidate refs. The repair has a second half (`F-CRP-15`): the read projection
  `_checkpoint_summary` (`src/film_pipeline/mcp/tools/checkpoints.py:85-93`) drops the field, so
  `list_checkpoints` cannot show the map even after the factory derives it.
- **Prior art:** new (the closest prior note is
  `documentation/audit-findings.md:118` on rollback confirmation, which *is*
  fixed: `src/film_pipeline/mcp/tools/checkpoints.py:249-254`).

### F-CRP-05 — Two resume implementations plus a write-only crash-recovery snapshot

- **Class:** O6 (parallel lifecycle) with O3 (write-only representation)
- **Severity:** High (impact 3 × drift 3 = 9). *Verifier downgrade (D8) changed the
  **impact axis** 4→3, giving score 12→9; per §1.5 the band is a function of the score,
  so the band is **High** — the "Medium" in the verifier's prose is not applied (a
  verifier who wants Medium must lower an axis to a 4–8 score, and the verifier's own
  reasoning keeps drift at 3). Axis rationale: §1.5's impact 5 is "wrong behavior
  reaches a human deliverable or corrupts durable data"; the drifted lifecycle has **no
  caller anywhere in `src/`** (§5.6,
  `grep -rn "ResumeManager\|ResumeSnapshot\|BranchManager" src/` → export surface
  only), so a crashed run behaves exactly as it would in a tree without
  `src/film_pipeline/checkpoints/resume.py`: the live resume path is
  `src/film_pipeline/app/_graph_exec.py:194` (`graph.get_state(config)`). Drift 3
  stands, so the score is 9 and the band is High.*
- **Concern:** "Resume an interrupted run" is implemented by the LangGraph
  checkpointer + `src/film_pipeline/app/_resume.py`, while `src/film_pipeline/checkpoints/resume.py` ships an unused
  snapshot manager and `state/graph-state.json` is written but never read.
- **De-facto owners:**
  - `src/film_pipeline/app/_graph_exec.py:194` — real resume path A — `"snapshot = graph.get_state(config)"`
  - `src/film_pipeline/app/_graph_exec.py:209-210` — resume fallback B — `"if not snapshot.values and not snapshot.next:"` / `"return advance_to_next_phase(rt, dict(active))"`
  - `src/film_pipeline/app/_resume.py:81` — resume payload builder — `"def _build_resume_payload("`
  - `src/film_pipeline/checkpoints/resume.py:26` — parallel, unused implementation — `"class ResumeManager:"` with `"snapshots: dict[str, list[ResumeSnapshot]] = field(default_factory=dict)"` (`:33`)
  - `src/film_pipeline/app/_graph_exec.py:141` — snapshot writer — `"storage.write_graph_state(project_id, snapshot)"`
  - `src/film_pipeline/schemas/runtime_state.py:9` — documented purpose — `"- ``state/graph-state.json`` — :class:`GraphStateSnapshot`, the machine-only"`
- **Drift proof:** (a) *dead parallel lifecycle*: `grep -rn "ResumeManager\|ResumeSnapshot"`
  finds no consumer in `src/` — only `src/film_pipeline/checkpoints/__init__.py:9,18,19` and
  `tests/unit/checkpoints/test_checkpoints.py:100-128`; likewise `BranchManager`
  (`src/film_pipeline/checkpoints/branches.py:13`) is exported (`src/film_pipeline/checkpoints/__init__.py:5`) and
  tested (`tests/unit/checkpoints/test_checkpoints.py:235-246`) but never used.
  (b) *mutation scenario* for the snapshot: change the field written at
  `src/film_pipeline/app/_graph_exec.py:138` (`GraphStateSnapshot(state=safe)`) — no behaviour
  changes, because `grep -rn "read_graph_state" src/` returns only the definition
  (`src/film_pipeline/artifacts/project_storage.py:167`) and a docstring example (`:23`); the only
  reader in the repo is the boundary-allowlist list at
  `tests/unit/artifacts/test_storage_boundary.py:152`. So the "crash recovery"
  snapshot (`src/film_pipeline/app/_graph_exec.py:90-93` comment) cannot recover anything, and the
  claimed crash-recovery resume actually depends on the checkpointer, which is
  `MemorySaver` unless the env flags say otherwise (F-CRP-09).
- **Reproduce:** `grep -rn "ResumeManager\|ResumeSnapshot\|BranchManager" --include=*.py src/`
  and `grep -rn "read_graph_state" --include=*.py src/`
- **Blast radius:** `src/film_pipeline/checkpoints/resume.py`, `src/film_pipeline/checkpoints/branches.py`,
  `src/film_pipeline/app/_graph_exec.py`, `src/film_pipeline/artifacts/project_storage.py`,
  `src/film_pipeline/schemas/runtime_state.py`, `src/film_pipeline/graph/graph.py:201` (import-time checkpointer).
  User-visible: a crashed run cannot be resumed from the on-disk snapshot; the
  "P4 persistence-after-every-mutation" claim (test docstring,
  `tests/unit/artifacts/test_state_persistence.py:261-265`) rests on the manual
  fallback, not on the snapshot.
- **Candidate owner module:** fold `src/film_pipeline/checkpoints/resume.py`/`branches.py` into the
  checkpoint owner or delete them; make the snapshot an explicit contract of the
  resume path.
- **Extraction sketch:** either delete the two dead modules (B9: no module without
  a caller) or make `resume` the single entry point that reads
  `state/graph-state.json` and rebuilds the checkpointer thread. Guard test:
  restart → resume must assert the snapshot was *read* (e.g. a spy on
  `read_graph_state`).
- **Prior art:** `documentation/audit-findings.md:124` notes
  "`runtime.approve_phase` catches `Exception` and falls back to manual phase
  advancement" — **narrowed but not gone**: the catch now re-raises
  (`src/film_pipeline/app/_graph_exec.py:216-229`) and the fallback is gated on an empty snapshot
  (`:209`), but the *stalled* trigger (`:232`) still advances manually. The dead
  `src/film_pipeline/checkpoints/resume.py` is new.

### F-CRP-06 — Rollback records have two authorities and no audit event

- **Class:** O3 (split state authority) with O1 (duplicated record grammar)
- **Severity:** High (impact 4 × drift 3 = 12)
- **Concern:** The rollback record is built twice with different ids/refs, one
  copy is discarded, and no rollback ever reaches the runtime audit log although
  the module claims to own "audit".
- **De-facto owners:**
  - `src/film_pipeline/checkpoints/rollback.py:22` — claims the concern — `""""Orchestrates rollback operations with invalidation and audit."""`
  - `src/film_pipeline/checkpoints/rollback.py:84,87` — in-memory record, fabricated ref, id keyed on checkpoint — `"rollback_id=f"rollback:{checkpoint_id}:{uuid4().hex[:8]}","` / `"invalidation_report_ref=f"invalidation:{checkpoint_id}","`
  - `src/film_pipeline/checkpoints/rollback.py:92` — appended to a list nobody reads — `"self.records.append(record)"`
  - `src/film_pipeline/mcp/tools/checkpoints.py:67,70` — persisted record, different id grammar and real ref — `"rollback_id=f"rollback:{project_id}:{uuid4().hex[:8]}","` / `"invalidation_report_ref=inv_ref,"`
  - `src/film_pipeline/mcp/tools/checkpoints.py:269` — the returned record is thrown away — `"_record, _report = rm.rollback_to_checkpoint(checkpoint_id, performed_by="operator")"`
- **Drift proof:** *existing divergence* plus mutation scenario. Existing: the two
  constructors of the same `RollbackRecord` (`src/film_pipeline/schemas/checkpoint.py:60`) emit
  different `rollback_id` grammars (checkpoint-keyed vs project-keyed) and
  different `invalidation_report_ref` values (a fabricated `invalidation:<id>`
  string vs a real artifact ref) for the same operation. Mutation: wire
  `_record` into the MCP response (the obvious next step) and the operator sees
  the fabricated ref; `RollbackManager.records` has no reader
  (`grep -rn "\.records\b" src/` → only the append). Rollbacks are also absent
  from the audit trail: `grep -rn "_record_audit" src/film_pipeline/mcp/tools/checkpoints.py src/film_pipeline/checkpoints/`
  → no match, and no `_record_audit` call site anywhere in `src/` passes a
  rollback action (the actions observed are `create_project`, `delete_project`,
  `set_active`, `create_checkpoint`, `auto_checkpoint_failed`, `approve_phase`,
  `request_revision`, `run_validation`, `resume_failed`,
  `resume_stalled_manual_advance`, `create_film_project`, `approve_profile_change`,
  `generate_reference_images`, `add_operator_comment`).
- **Reproduce:** `grep -rn "_record_audit" --include=*.py src/film_pipeline/mcp/tools/checkpoints.py src/film_pipeline/checkpoints/`
  → no match (no rollback is audited); `grep -rn "\.records\b" --include=*.py src/`
  → only the append at `src/film_pipeline/checkpoints/rollback.py:92`. Appendix A.6 shows
  the MCP path returning persisted refs only.
- **Blast radius:** `src/film_pipeline/checkpoints/rollback.py`, `src/film_pipeline/mcp/tools/checkpoints.py`,
  `src/film_pipeline/app/runtime.py:291` (audit writer), `src/film_pipeline/mcp/tools/audit.py:35`,
  `src/film_pipeline/app/services/_browse_ops.py:156`. User-visible: a destructive, human-confirmed
  rollback is invisible in `get_audit_log`, and two grammar-compatible records
  disagree about identity.
- **Candidate owner module:** `runtime_persistence.rollback` — owns `RollbackRecord`
  creation, persistence and the audit event.
- **Extraction sketch:** have `RollbackManager` return the record only via a
  single factory used by the MCP layer (delete the local constructor), and record
  one audit event per rollback inside it. Guard test: after `rollback_to_checkpoint`,
  `rt.get_audit_log(project_id)` contains a rollback action and exactly one
  record exists in the store.
- **Prior art:** `documentation/audit-findings.md:118` (rollback without
  confirmation — fixed at `src/film_pipeline/mcp/tools/checkpoints.py:249-254`); the record/audit
  split is new.

### F-CRP-07 — Invalidation depends on a second, hand-maintained dependency model while the graph records real artifact parentage

- **Class:** O4 (parallel registries that must agree, nothing enforces agreement)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** "What depends on what" has a static map in `checkpoints` and a
  recorded `built_from` provenance chain in `graph`; the rollback report uses the
  former.
- **De-facto owners:**
  - `src/film_pipeline/checkpoints/invalidation.py:10` — static one-hop family map — `"DEPENDENCY_GRAPH: dict[str, list[str]] = {"`
  - `src/film_pipeline/checkpoints/invalidation.py:48-51` — one hop only — `"deps = DEPENDENCY_GRAPH.get(atype, [])"` / `"for dep in deps:"` / `"if dep not in will_invalidate and dep not in types:"`
  - `src/film_pipeline/graph/consistency.py:63` — the other model, from real provenance — `"built_from = getattr(metadata, "built_from", {}) or {}"`
  - `src/film_pipeline/graph/nodes/_agent_artifacts.py:126` — where that provenance is recorded — `"original. Populates ``built_from`` with current upstream artifact refs"`
  - `src/film_pipeline/mcp/tools/_profile_change.py:460-465` — a second caller of the static map, with a fourth hardcoded type list — `"engine = InvalidationEngine()"` / `"report = engine.report("` / `"rollback_target=f"profile-change:{proposal_id}","` / `"artifact_types=["project_config", "prompt_package", "generation_plan", "coverage_group"],"`
- **Drift proof:** mutation scenario. Add a new artifact family to the registry
  (`src/film_pipeline/artifacts/registry.py`, e.g. a new downstream kind) and a recorded
  `built_from` edge for it; `DEPENDENCY_GRAPH` is not derived from the registry or
  the provenance, so `InvalidationEngine.report` under-reports and the persisted
  `InvalidationReport` looks authoritative. No test fails: the only tests of the
  map assert its own literals
  (`tests/unit/checkpoints/test_checkpoints.py:135-152` —
  `"assert "treatment" in deps"`), and `grep -rn "DEPENDENCY_GRAPH" tests/` → no
  match, so nothing checks agreement with the registry or with `built_from`.
  Note the map is *also* keyed on family names that the rollback path supplies as
  `artifact_versions.keys()` (`src/film_pipeline/mcp/tools/checkpoints.py:274`), so the two
  vocabularies are coupled with no validation.
- **Reproduce:** `grep -rn "DEPENDENCY_GRAPH" --include=*.py src/` (only
  `src/film_pipeline/checkpoints/`) and `grep -rn "DEPENDENCY_GRAPH" --include=*.py tests/`
  → no match; `grep -rn "built_from" --include=*.py src/`
- **Blast radius:** `src/film_pipeline/checkpoints/invalidation.py`, `src/film_pipeline/checkpoints/rollback.py`,
  `src/film_pipeline/mcp/tools/checkpoints.py`, `src/film_pipeline/mcp/tools/_profile_change.py`,
  `src/film_pipeline/graph/consistency.py`. User-visible: a rollback reports fewer invalidated
  artifacts than were actually built from the reverted ones, so stale downstream
  artifacts keep their "current" status.
- **Candidate owner module:** `artifacts.provenance` — own the dependency model,
  derive rollback impact from recorded `built_from` (plus a declared
  family-level default for artifacts that predate provenance).
- **Extraction sketch:** make `InvalidationEngine` take a provenance source instead
  of the module-level dict; keep `DEPENDENCY_GRAPH` only as a documented fallback
  for artifacts without `built_from`. Guard test: a registry-completeness test
  (`every registry kind with upstream deps appears in the effective graph`) and a
  transitive-closure test on a synthetic 3-hop chain.
- **Prior art:** `documentation/audit-findings.md:120` — "Invalidation uses a
  static one-hop map instead of actual artifact parentage" — **still present,
  unchanged** at HEAD; what is new is the second static caller
  (`src/film_pipeline/mcp/tools/_profile_change.py:460`) and the demonstration that no test binds
  the map to the registry or to `built_from`.

### F-CRP-08 — Artifact-only ("discovered") projects get a checkpoint manager but never restore their checkpoint log

- **Class:** O3 (split state authority) with O6 (two restore entry points)
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** Checkpoint restore happens in one of the two project-registration
  paths.
- **De-facto owners:**
  - `src/film_pipeline/app/_persistence.py:131` — restore path restores checkpoints — `"_restore_checkpoints(rt, storage, project_id)"`
  - `src/film_pipeline/app/_persistence.py:191-192` — adoption path registers a manager and persists, without restoring — `"rt.checkpoint_managers[project_id] = checkpoint_manager_for(storage, project_id)"` / `"persist_project_state(rt, project_id)"`
  - `src/film_pipeline/app/_persistence.py:207-211` — only projects with a typed record take the restore path — `"restored = sum("` … `"if storage.read_project_record(project_id) is not None"`
- **Drift proof:** *existing divergence*, reproduced (Appendix A.7): a project
  directory containing `artifacts/01-vision/x/meta.json` and a
  `checkpoints/checkpoints.jsonl` with one record is adopted
  (`adopted: True`, `discovered flag: True`, manager registered) but
  `rt.checkpoints size: 0` and `manager dict size: 0` — the on-disk log
  (`on-disk log still has 1 line: 1`) is invisible to every reader in §3.1.
  Mutation scenario: the same asymmetry makes any future "restore" logic added to
  one path silently not apply to the other; no test exercises adoption with a
  checkpoint log.
- **Reproduce:** Appendix A.7, standalone — run from the repo root, no substitution;
  observed output follows the block.

  ```bash
  PYTHONPATH=src .venv/bin/python - <<'PY'
  import json, os, tempfile
  from pathlib import Path
  tmp = Path(tempfile.mkdtemp(prefix="crp08_"))
  os.environ["FILM_PIPELINE_STORAGE_ROOT"] = str(tmp)
  os.environ["FILM_PIPELINE_MCP_MODE"] = "mock"
  from film_pipeline.artifacts.storage import init_storage_root
  from film_pipeline.app.runtime import StudioRuntime
  root = tmp
  init_storage_root(root)
  d = root / "disc" / "artifacts" / "01-vision" / "x"; d.mkdir(parents=True)
  (d / "meta.json").write_text("{}")
  (root / "disc" / "checkpoints").mkdir(parents=True)
  (root / "disc" / "checkpoints" / "checkpoints.jsonl").write_text(
      json.dumps({"storage_schema_version": 1, "checkpoint_id": "checkpoint:disc:intake:deadbeef",
                  "project_id": "disc", "phase": "intake", "reason": "on disk"}) + "\n")
  rt = StudioRuntime(server_mode="mock", runtime_root=root)
  print("adopted:", "disc" in rt.projects)
  print("rt.checkpoints size:", len(rt.checkpoints))
  print("rt.list_checkpoints('disc'):", rt.list_checkpoints("disc"))
  print("manager dict size:", len(rt.checkpoint_managers["disc"].checkpoints))
  print("on-disk log line count:", len((root / "disc" / "checkpoints" / "checkpoints.jsonl").read_text().splitlines()))
  PY
  ```

  ```
  adopted: True
  rt.checkpoints size: 0
  rt.list_checkpoints('disc'): []
  manager dict size: 0
  on-disk log line count: 1
  ```
- **Blast radius:** `src/film_pipeline/app/_persistence.py`, `src/film_pipeline/mcp/tools/checkpoints.py`,
  `src/film_pipeline/app/services/_browse_ops.py`, `src/film_pipeline/app/runtime.py`. User-visible: pre-existing
  projects (the adoption case the storage plan explicitly supports) appear to have
  no checkpoint history, so rollback is unavailable for them although the history
  is on disk.
- **Candidate owner module:** `runtime_persistence` — one project-registration
  routine that always performs record + checkpoint + audit restore.
- **Extraction sketch:** fold `_adopt_discovered_project` and
  `_restore_state_project` into one function with a `discovered: bool` flag so the
  restore steps cannot be forgotten. Guard test: adopt a fixture project with a
  checkpoint log and assert `rt.list_checkpoints(project_id)` is non-empty.
- **Prior art:** new.

### F-CRP-09 — "Persistence enabled?" is re-derived at six sites (seven derivations), and the `PERSIST_STATE` default is set by only one entry point

- **Class:** O5 (one policy decision re-derived at N call sites)
- **Severity:** High (impact 3 × drift 3 = 9)
- **Verifier disputes applied:** **D6** — the count is six *sites*, seven *derivations*
  (`src/film_pipeline/graph/services.py:31` root and `:48` profile are two formulas; §2.1). **D4** — the
  row-1 sentence below is corrected: P3/P4 return the *library default root/profile*,
  which is **not** the effective root of a composed non-persistent run (the suite never
  takes that branch — `tests/conftest.py:98` sets `NO_PERSIST=1` session-wide; a composed
  `StudioRuntime` uses `runtime_root` at `src/film_pipeline/app/runtime.py:75-77` or a per-pid temp dir at
  `:67-69`). **D7** — the prior art now cites `audit/03:484` **F-CFG-08**, which already
  reports this concern (7 read sites / 6 modules, High 4×3=12, candidate owner
  `app/_persistence` at `audit/03:514`); `audit/11:322` already raises the resulting
  three-owner collision. Reconciled in §6.7.
- **Sub-case boundary (verify-15 §3.5):** the root branch
  `src/film_pipeline/app/runtime.py:58-69` counted under P8 here is itself scored
  separately as **`F-CRP-13`** (Critical 4×4=16), because that branch adds a second
  defect — a durable write performed under an explicit "do not persist" policy. The
  split is deliberate: this finding scores the *boolean policy* (seven derivations,
  no owner) at the "wrong branch" band; `F-CRP-13` scores the *root that branch
  selects*. Read `F-CRP-13` as the high-severity sub-case of P8, not as a rival
  finding; §2.1's P8 row and §6.7 carry the same split.
- **Concern:** One policy decision (durable persistence on/off) has seven
  derivations at six sites and no owner; the default that makes it *on* lives in
  the MCP entry point.
- **De-facto owners:** the six sites in §2.1 — `src/film_pipeline/app/_persistence.py:51`,
  `src/film_pipeline/graph/graph.py:43`, `src/film_pipeline/graph/services.py:31`, `src/film_pipeline/graph/services.py:48`,
  `src/film_pipeline/app/logging_setup.py:78-81`, `src/film_pipeline/cli/run.py:226` — plus the defaulting writer
  `src/film_pipeline/mcp/server.py:243-244` — `"if not os.getenv("FILM_PIPELINE_NO_PERSIST"):"` /
  `"os.environ.setdefault("FILM_PIPELINE_PERSIST_STATE", "1")"` — and the root
  branch `src/film_pipeline/app/runtime.py:58-69`.
- **Drift proof:** *existing divergence* (truth-table row 1, §2.2): with both
  flags unset, P1/P2/P5 report disabled while `src/film_pipeline/cli/run.py:226` reports
  `persist_enabled=True`; P3/P4 additionally return the *library's public default*
  — `<storage root>` and the `production` profile (verifier D4). That default is not
  the effective root of a composed run: the suite never takes the production branch
  because `tests/conftest.py:98` sets `FILM_PIPELINE_NO_PERSIST=1` for the whole
  session, and under a composed `StudioRuntime` the effective root is `runtime_root`
  (`src/film_pipeline/app/runtime.py:75-77`) or a per-pid temp dir (`:67-69`). The residual exposure is
  a **bare** `GraphServices()` construction (`src/film_pipeline/graph/services.py:63`), which does write
  to the real root with the `production` profile while the policy says persistence is
  off. Mutation scenario for the unpinned sites: `src/film_pipeline/graph/services.py:31`
  and `:48` are not referenced by any test for the both-unset case
  (`grep -rn "NO_PERSIST" tests/` → `tests/unit/app/test_logging_setup.py:148,168`,
  `tests/unit/graph/test_graph.py:27`, `tests/unit/test_entrypoints.py:34`), so
  making them agree with P1 (`and PERSIST_STATE`) or diverge further is silent.
  Only one combination is pinned for P1-vs-P2
  (`tests/unit/app/test_logging_setup.py:157-171`
  `test_no_persist_wins_for_runtime_checkpointer`), and the CLI's divergent value
  is itself pinned (`tests/unit/test_entrypoints.py:30`
  `configure.assert_called_once_with(runtime_root, persist_enabled=True)` with
  `NO_PERSIST` deleted and `PERSIST_STATE` unset) — i.e. the suite locks in the
  disagreement.
- **Reproduce:** Appendix A.1 (truth table); static:
  `grep -rn "FILM_PIPELINE_NO_PERSIST\|FILM_PIPELINE_PERSIST_STATE" --include=*.py src/`
- **Blast radius:** `src/film_pipeline/app/_persistence.py`, `src/film_pipeline/app/runtime.py`,
  `src/film_pipeline/app/logging_setup.py`, `src/film_pipeline/graph/graph.py`, `src/film_pipeline/graph/services.py`, `src/film_pipeline/cli/run.py`,
  `src/film_pipeline/cli/driver.py`, `src/film_pipeline/mcp/server.py`, `scripts/_scratch_bootstrap.py`. User-visible:
  a CLI run without `PERSIST_STATE` writes a log file but keeps graph state in a
  `MemorySaver`, so gates are not crash-resumable even though the CLI reports
  persistence on; `NO_PERSIST=0` disables persistence everywhere (§2.3).
- **Candidate owner module:** `runtime_persistence.policy` — one
  `PersistenceMode` resolution consumed by all six sites.
- **Extraction sketch:** a single `resolve_persistence_policy()` returning an enum
  (`DURABLE` / `EPHEMERAL` / `SUBPROCESS_SANDBOX`) plus a `RootLayout`; every site
  in §2.1 calls it (logging takes the resolved flag as a parameter, not a
  formula); move `src/film_pipeline/mcp/server.py:243-244`'s defaulting into the policy resolver so
  all entry points get it. Guard test: parametrized over all four flag
  combinations asserting one policy value per combination, plus the CLI's
  `configure_logging` argument equals the resolved policy.
- **Prior art:** `documentation/storage-upgrade-plan.md:297-298` states the
  intent ("the `use_persistent_runtime()` gate is preserved (non-persistent
  invocations never write home or CWD)") — **violated for the CLI**, which
  resolves `<storage root>/runs/default` (the real home tree) whenever a
  `--runtime-root` is not given, regardless of the flags (the CLI write is separately
  proved in F-CRP-01; the library-default sentence above is the part verifier D4
  corrects). **Colliding prior art (bar A7, verifier D7):**
  `audit/03-config-profile-and-defaults.md:484` **F-CFG-08** reports the same
  `FILM_PIPELINE_NO_PERSIST` re-derivation across the same six modules, at severity
  High 4×3=12, and nominates `app/_persistence` as owner (`audit/03:514`);
  `audit/11-mcp-surface-safety-and-entrypoints.md:322` already records the resulting
  **three-way owner collision** (`app/_persistence` / `runtime_persistence` /
  `app.bootstrap`). One concern, three owners — to be resolved once in
  `03-target-architecture.md`; see §6.7 for this file's position.

### F-CRP-10 — The stale generation-request code set is defined three times and emitted a fourth time

- **Class:** O1 (duplicated normative model)
- **Severity:** Medium (impact 2 × drift 3 = 6). *Verifier downgrade (D8): impact 3→2.
  The drifted copies are reachable only through the text-only generation policy
  (`src/film_pipeline/mcp/tools/generation/_text_only.py`, sole caller the `plan_generation_batch` tool
  path) and the operator-planning path; the auto/resume path uses
  `src/film_pipeline/app/_resume.py:14`, which **is** pinned
  (`tests/unit/app/test_resume_integrity.py:409-411`). A dormant copy whose divergence
  cannot reach a live path is §1.5's "recoverable internal" band, not the
  durable-data band.*
- **Concern:** A closed vocabulary of issue codes is copied into three frozensets
  and produced in a fourth module; no shared constant exists.
- **De-facto owners:**
  - `src/film_pipeline/app/_resume.py:14` — `"_STALE_REQUEST_CODES = frozenset({"empty_generation_requests", "no_generation_requests"})"`
  - `src/film_pipeline/app/services/_generation_ops.py:20` — same literal, different module
  - `src/film_pipeline/mcp/tools/generation/_text_only.py:9` — same literal, third name — `"_STALE_ISSUE_CODES = frozenset({"empty_generation_requests", "no_generation_requests"})"`
  - `src/film_pipeline/graph/orchestrator_validators/planning_gates.py:254,263` — the emitter — `""no_generation_requests","` / `""empty_generation_requests","`
- **Drift proof:** mutation scenario with a silent failure. Mutate
  `src/film_pipeline/mcp/tools/generation/_text_only.py:9` (drop `"no_generation_requests"`): the
  text-only path stops clearing that blocker while `src/film_pipeline/app/_resume.py:14` still
  clears it, and no test fails — `grep -rn "_STALE_ISSUE_CODES\|_STALE_REQUEST_CODES" tests/`
  → no match, and `tests/unit/mcp/tools/test_generation.py:683-695` never seeds a
  stale blocker. The verifier **executed** this mutation against a disposable
  snapshot (`pytest tests/unit/mcp/tools/test_generation.py --no-cov` → **41 passed**,
  `verify-10.md` §2.2/§6). Same for `src/film_pipeline/app/services/_generation_ops.py:20`. (The two *other*
  sites are mutually pinned through `tests/unit/app/test_resume_integrity.py:409-411`
  and `tests/unit/test_orchestrator_validators.py:267`, which is why the drift is
  3 rather than 4.)
- **Reproduce:** `grep -rn "_STALE_REQUEST_CODES\|_STALE_ISSUE_CODES\|no_generation_requests\|empty_generation_requests" --include=*.py src/ tests/`
  → the three frozensets plus both emitter literals at
  `src/film_pipeline/graph/orchestrator_validators/planning_gates.py:254,263`
- **Blast radius:** `src/film_pipeline/app/_resume.py`, `src/film_pipeline/app/services/_generation_ops.py`,
  `src/film_pipeline/mcp/tools/generation/_text_only.py`, `src/film_pipeline/graph/orchestrator_validators/planning_gates.py`.
  User-visible: a text-only or operator-planned generation gate can keep a stale
  blocking issue after the requests exist, looping repair or forcing the manual
  advance path (F-CRP-03).
- **Candidate owner module:** `graph.orchestrator_validators` (the emitter owns the
  vocabulary) exporting `STALE_GENERATION_REQUEST_CODES`.
- **Extraction sketch:** move the frozenset next to the emitter and import it in
  the three consumers; add a guard test asserting the three consumers use the
  exported constant (e.g. `module._STALE_* is STALE_GENERATION_REQUEST_CODES` or,
  after the refactor, that the flat module no longer redefines it).
- **Prior art:** new.

### F-CRP-11 — Audit persistence is keyed on live registry membership, so the project-deletion event never reaches disk

- **Class:** O3 (split state authority between the in-memory audit list and its persisted log) with O7 (a writer reaching into another structure's mutation order)
- **Severity:** Medium (impact 2 × drift 3 = 6)
- **Concern:** The audit writer decides whether to persist based on
  `project_roots` membership; the delete path removes that membership before
  recording the event.
- **De-facto owners:**
  - `src/film_pipeline/app/runtime.py:292` — appends to memory unconditionally — `"self.audit_events.append("`
  - `src/film_pipeline/app/runtime.py:301-303` — persists conditionally — `"project_id = str(details.get("project_id", ""))"` / `"if project_id and project_id in self.project_roots:"` / `"self._persist_audit_events(project_id)"`
  - `src/film_pipeline/app/runtime.py:173-178` — removes the membership first, then records — `"project_root = self.project_roots.pop(project_id, None)"` … `"self._record_audit("system", "delete_project", project_id=project_id)"`
- **Drift proof:** *existing divergence*, reproduced (Appendix A.8): the archived
  project's audit log contains only `['create_project']` while the in-memory trail
  is `['create_project', 'delete_project']`. Mutation scenario: move the
  `_record_audit` call above the `project_roots.pop`
  (`src/film_pipeline/app/runtime.py:173`) and the event is persisted — no test asserts either
  behavior (`grep -rn "delete_project" tests/` → no audit assertion).
- **Reproduce:** Appendix A.8; static:
  `grep -n "project_roots.pop\|_record_audit\|in self.project_roots" src/film_pipeline/app/runtime.py`
- **Blast radius:** `src/film_pipeline/app/runtime.py`, `src/film_pipeline/mcp/tools/audit.py` (reads
  `rt.audit_events`, `:35`), `src/film_pipeline/app/services/_browse_ops.py:156`. User-visible: the
  durable audit trail shipped with an archived project cannot explain the
  project's disappearance, and the event is lost on restart.
- **Candidate owner module:** `runtime_persistence.audit` — one audit writer that
  always persists, independent of registry membership.
- **Extraction sketch:** make `_record_audit` take the project root as an
  argument (or resolve it before detach) instead of consulting
  `self.project_roots`; record deletion in the archived directory before archiving.
  Guard test: create → delete with `force=True` → assert the archived audit log
  contains `delete_project`.
- **Prior art:** new.

---

**Added by independent verification (verifier §3, seams M1–M5).** These five were not
in the reviewed revision; each was re-run by this author against the pristine snapshot
(`git archive fb85baa`) before being written up. `F-CRP-12`–`14` are the verifier's
ranked seams M1–M3; `F-CRP-15`/`16` are the corroborating and recorded-only items
M4/M5.

### F-CRP-12 — A bare `import film_pipeline.graph.graph` creates `<storage root>/checkpoints/` at import time, after which the storage root is unopenable

- **Class:** O5 (policy-by-branch) with O7 (an import-time side effect reaching another
  module's root)
- **Severity:** Critical (impact 5 × drift 5 = 25). *Verifier missed-seam M1; reproduced
  by this author (Appendix A.9).*
- **Concern:** `langgraph.json`'s target module builds the graph — and therefore the
  checkpointer — at import time; with `PERSIST_STATE=1` and no runtime root that
  `mkdir`s a directory *inside* the storage root before any runtime exists, leaving it
  non-empty and unmarked, so `ensure_storage_root` refuses the app's own root.
- **De-facto owners:**
  - `src/film_pipeline/graph/graph.py:201` — the import-time build — `"graph: CompiledStateGraph = build_graph()"`
  - `src/film_pipeline/graph/graph.py:181` — the module-level call reaches the default checkpointer (no runtime root is passed) — `"checkpointer=checkpointer or _default_checkpointer(runtime_root=runtime_root)"`
  - `src/film_pipeline/graph/graph.py:43-46` — the persistent branch and its root — `"if os.getenv("FILM_PIPELINE_NO_PERSIST") or not os.getenv("FILM_PIPELINE_PERSIST_STATE"):"` … `"runtime_root / "checkpoints" if runtime_root is not None else default_checkpoints_root()"`
  - `src/film_pipeline/artifacts/storage.py:74` — the derived root is *inside* the storage root — `"return resolve_storage_root() / "checkpoints""`
  - `src/film_pipeline/graph/graph.py:49` — the import-time side effect — `"checkpoint_dir.mkdir(parents=True, exist_ok=True)"`
  - `src/film_pipeline/artifacts/storage.py:160-164` — the later refusal — `"raise StorageRootError("` … `f"{MARKER_FILENAME} marker and does not look like a film-pipeline "`
- **Drift proof:** *existing divergence*, reproduced by this author (Appendix A.9):
  ```
  after import, children of storage root: ['checkpoints']
  app FAILED: StorageRootError: Refusing to use <tmp>/storage ...
  ```
  An `import` alone is sufficient — no runtime, no CLI, no MCP server. Drift 5:
  `tests/conftest.py:98` sets `os.environ["FILM_PIPELINE_NO_PERSIST"] = "1"`
  session-wide, so every test module that imports `film_pipeline.graph.graph`
  (`tests/unit/graph/test_graph.py:12`, `tests/unit/test_graph.py:7`,
  `tests/unit/graph/test_real_human_gates.py:11`,
  `tests/unit/app/test_resume_integrity.py:187`,
  `tests/unit/app/test_logging_setup.py:165`) takes the `MemorySaver` branch at
  `src/film_pipeline/graph/graph.py:43-44` and never reaches `src/film_pipeline/graph/graph.py:49`. The failure needs a
  fresh process with `PERSIST_STATE=1`, which no test creates.
- **Reproduce:** Appendix A.9; static:
  `grep -rn "graph: CompiledStateGraph = build_graph()\|checkpoint_dir.mkdir" --include=*.py src/`
- **Blast radius:** `src/film_pipeline/graph/graph.py`, `src/film_pipeline/artifacts/storage.py`, and every entry point that
  imports the module — `langgraph.json:4`
  (`"film_pipeline": "./src/film_pipeline/graph/graph.py:graph"`), and transitively the
  app and MCP server, whose `ensure_storage_root` call (`src/film_pipeline/app/runtime.py:62` … in
  `load_persisted_projects`) then refuses the root. User-visible: after one import in a
  process, the documented storage root can no longer be opened, and the error names a
  marker the operator never removed; the durable checkpoint database sits in the
  *storage* root's namespace, where the layout owner does not expect it.
- **Candidate owner module:** `runtime_persistence` — the graph factory consumes a
  resolved `RootLayout`/checkpointer handle; importing a module is not a durable side
  effect.
- **Extraction sketch:** keep `build_graph()` as the only constructor and move the
  module-level instance behind a lazy accessor (or delete it if `langgraph.json` can
  point at a factory), so importing the module is side-effect-free and the checkpointer
  root comes from the resolved policy object. Guard test: import the module with
  `PERSIST_STATE=1` and a fresh `FILM_PIPELINE_STORAGE_ROOT`, then assert
  `resolve_storage_root()` still opens and has no `checkpoints/` child.
- **Prior art:** new as a finding — the mechanism appeared earlier only as §7.3's
  "two SQLite files" observation, which missed the refusal. The violated bar is
  `documentation/storage-upgrade-plan.md:297-298` (non-persistent invocations must not
  write into the user's tree; here even a *persistent* import writes into the storage
  root with no runtime to own it). *Anchor correction:* verify-10 M1 lists the `mkdir`
  as `src/film_pipeline/artifacts/storage.py:49`; at `fb85baa` that line is a `StorageMarker` field — the
  `mkdir` is `src/film_pipeline/graph/graph.py:49` and the root derivation is `src/film_pipeline/artifacts/storage.py:74`.

### F-CRP-13 — Setting `FILM_PIPELINE_RUNTIME_ROOT` bypasses the persistence-policy gate, so a "non-persistent" runtime writes durable state

- **Class:** O5 (one policy decision re-derived at N call sites — here *not* consulted)
  with O3 (split authority over "may I write durably?")
- **Severity:** Critical (impact 4 × drift 4 = 16). *Verifier missed-seam M2; reproduced
  by this author (Appendix A.10). The verifier wrote "High" beside a recomputed
  4×4=16; per §1.5 the band is a function of the score, so the band is **Critical** and
  the axes stand as verified.*
- **Concern:** The root branch checks `FILM_PIPELINE_RUNTIME_ROOT` **before** the
  `use_persistent_runtime()` gate, so a runtime whose own policy reports "not
  persistent" still gets a real on-disk root and writes durable markers there.
- **De-facto owners:**
  - `src/film_pipeline/app/runtime.py:59-63` — the env branch precedes the gate — `"if os.getenv("FILM_PIPELINE_RUNTIME_ROOT", "").strip():"` / `"self.runtime_root = configured_runtime_root()"` / `"elif use_persistent_runtime():"`
  - `src/film_pipeline/app/runtime.py:75-77` — the store root *is* that root — `"self.services = _build_services_for_mode("` / `"self.server_mode, artifacts_root=self.runtime_root"`
  - `src/film_pipeline/artifacts/storage.py:116-126` — opening the root writes the durable marker — `"write_json_atomic(marker_path(root), asdict(marker))"` / `"return root"`
  - `src/film_pipeline/app/_persistence.py:259-265` — the project record funnel (§5.1) — `"persist_project_state"` → `ProjectStorage.write_project_record`
- **Drift proof:** *existing divergence*, reproduced by this author (Appendix A.10):
  ```
  [A] use_persistent_runtime()      = False (policy says: not persistent)
  [A] StudioRuntime.runtime_root    = <tmp>/real-runtime-root
  [A] artifact_store.root           = <tmp>/real-runtime-root
  [A] durable project.json written? = True
  [A] durable storage marker?       = True
  ```
  The policy authority and the root branch disagree about whether this process may
  write durably. Drift 4: no test covers the combination — the storage-guard test
  deletes `PERSIST_STATE` but not `RUNTIME_ROOT`
  (`tests/unit/artifacts/test_storage_guards.py:63`), and the policy test pins both
  flags but not the root branch
  (`tests/unit/app/test_logging_setup.py:148-171`). The storage plan's own bar — quoted
  in F-CRP-09's Prior art, "non-persistent invocations never write home or CWD"
  (`documentation/storage-upgrade-plan.md:297`) — is violated by design.
- **Reproduce:** Appendix A.10; static:
  `grep -n "FILM_PIPELINE_RUNTIME_ROOT\|use_persistent_runtime" src/film_pipeline/app/runtime.py`
- **Blast radius:** `src/film_pipeline/app/runtime.py`, `src/film_pipeline/artifacts/storage.py`, `src/film_pipeline/app/_persistence.py`.
  User-visible: a caller who explicitly forces a non-persistent process (no
  `PERSIST_STATE`, or `NO_PERSIST=1`) but passes a runtime root still gets durable
  `project.json` + `storage.json` there; the §2.1 derivation table has no column for
  this case because the branch is about a *root*, not the policy boolean.
- **Candidate owner module:** `runtime_persistence.policy` — the resolved policy decides
  the mode; `RootLayout` is its output, not an independent input.
- **Extraction sketch:** resolve `PersistenceMode` first and derive the root from it:
  an explicit `RUNTIME_ROOT` may override *where* a durable runtime lives, but a
  non-persistent mode should either refuse the override (fail closed) or explicitly
  promote the mode to `RUN_SCOPED` and say so in the returned policy object. Guard
  test: `RUNTIME_ROOT` set with `PERSIST_STATE` unset ⇒ the resolved policy's mode is
  not `DURABLE`, and no `storage.json`/`project.json` appears under that root; or the
  inverse contract if promotion is chosen.
- **Prior art:** new. `audit/11-mcp-surface-safety-and-entrypoints.md:303-309` proves
  the same entry-point hazard from the MCP side (`NO_PERSIST=1` + `RUNTIME_ROOT` set)
  but attributes it to the entry points; the root branch here is the third derivation.

### F-CRP-14 — `SafetyService.persist_root()` ignores the runtime root in use, so deletion archives cross-root

- **Class:** O5 (a second, independent derivation of "the root I may delete under")
  with O7 (a destructive operation reaching a root it does not own)
- **Severity:** High (impact 4 × drift 3 = 12). *Verifier missed-seam M3; reproduced by
  this author (Appendix A.11).*
- **Concern:** The trash base is derived from the *storage* root's parent, not from
  `rt.runtime_root`, so deleting a project created under an explicit runtime root
  moves it into a completely different tree.
- **De-facto owners:**
  - `src/film_pipeline/app/safety.py:25-32` — the safe-delete base — `"def persist_root() -> Path:"` … `"return resolve_storage_root().resolve().parent"`
  - `src/film_pipeline/app/safety.py:111` — the trash destination — `"root = trash_root or (persist_root() / "trash")"`
  - `src/film_pipeline/app/runtime.py:153-157` — the delete path archives the project root there — `"project_root = self._detach_project_state(project_id)"` / `"self._archive_directory("` / `"project_root, trash_prefix=f"project-{project_id}-", force=force"`
  - `src/film_pipeline/app/runtime.py:181-188` — the mover — `"move_to_trash(path, prefix=trash_prefix)"`
- **Drift proof:** *existing divergence*, reproduced by this author (Appendix A.11):
  ```
  [B] runtime root in use           = <tmp>/explicit-run-root
  [B] safety.persist_root()         = <tmp>            (the storage root's parent)
  [B] archive created under         = ['<tmp>/trash/project-p9-...-p9']
  [B] archive inside runtime root?  = False
  ```
  This corrects §7.4's "no divergence observed": the *value* of `persist_root()` agrees
  with `default_run_root()`'s parent, but its *use* is bound to neither
  `rt.runtime_root` nor the store root. Drift 3 (partially pinned, in the wrong
  direction): `tests/unit/app/test_runtime.py:96-123` constructs the runtime with
  `runtime_root=tmp_path / "runtime"` **and** a different `FILM_PIPELINE_STORAGE_ROOT`
  (`:97-103`), then asserts the archive exists under `persist / "trash"` (`:119-123`) —
  i.e. the suite freezes the cross-root destination instead of the invariant "deletion
  archives inside the runtime root". *Anchor correction:* verify-10 M3 cites
  `src/film_pipeline/app/runtime.py:111` for the trash expression; that expression is
  `src/film_pipeline/app/safety.py:111`, as quoted above.
- **Reproduce:** Appendix A.11; static:
  `grep -rn "persist_root()" --include=*.py src/film_pipeline/app/`
- **Blast radius:** `src/film_pipeline/app/safety.py`, `src/film_pipeline/app/runtime.py`, `mcp/tools/*` (any caller of
  `delete_project`). User-visible: an operator working in an explicit runtime root (or
  a run-scoped temp root, `src/film_pipeline/app/runtime.py:67-69`) finds the archived project in
  `~/.film-pipeline/trash` — outside the tree they were told is in use — and a
  non-persistent process writes into the user's home tree, contradicting
  `documentation/storage-upgrade-plan.md:297`.
- **Candidate owner module:** `runtime_persistence` — one `RootLayout` per runtime;
  `SafetyService` receives the trash root as a value, never re-derives it.
- **Extraction sketch:** pass the resolved `RootLayout` (or just `trash_root`) into
  `SafetyService`/`move_to_trash`; delete `persist_root()`'s global derivation and make
  the safe-zone check operate on the same layout. Guard test: create a project under
  `runtime_root=<tmp>/rt` with a different `STORAGE_ROOT`, delete it, and assert the
  archive is under `<tmp>/rt/trash` and *not* under the storage-root parent.
- **Prior art:** the derivation is recorded (not scored) in §7.4 and in
  `audit/03-config-profile-and-defaults.md`'s env inventory; the cross-root *use* is
  new.

### F-CRP-15 — The checkpoint summary projection drops `artifact_versions`, so the derived map would be invisible to the operator

- **Class:** O8 (a projection that silently omits part of the record)
- **Severity:** Medium (impact 2 × drift 3 = 6). *Verifier missed-seam M4, recorded as
  corroborating `F-CRP-04`; no score is added to that finding.*
- **Concern:** `F-CRP-04` localizes the defect to the tool not passing
  `artifact_versions`; the second half is that the *read* path also drops the field, so
  even a correctly derived map cannot be seen through `list_checkpoints`.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/checkpoints.py:85-93` — the summary shape, without the map — `"def _checkpoint_summary(cp: CheckpointMetadata) -> dict[str, object]:"` … `""reason": cp.reason,"`
  - `src/film_pipeline/mcp/tools/checkpoints.py:102` — `list_checkpoints` returns only summaries — `"return _ok(checkpoints=[_checkpoint_summary(c) for c in cps])"`
  - `src/film_pipeline/mcp/tools/checkpoints.py:132` — the other summary consumer — `"return _ok(**_checkpoint_summary(cp))"`
  - `src/film_pipeline/app/runtime.py:253` — the factory *can* carry the field — `"artifact_versions: dict[str, str] | None = None,"` (confirmed at runtime: `"artifact_versions" in StudioRuntime.create_checkpoint.__code__.co_varnames` → `True`)
  - `src/film_pipeline/app/_graph_exec.py:102-103` — the only derivation — `"candidate_refs = get_candidate_refs(state)"` / `"artifact_versions = dict(candidate_refs)"`
- **Drift proof:** *existing divergence* (shared with `F-CRP-04`, Appendix A.6): the
  MCP-created checkpoint has `artifact_versions = {}` and
  `get_invalidation_report(...).will_invalidate == []`, while the auto path's map is
  pinned (`tests/unit/app/test_runtime.py:35`). Mutation scenario: add
  `"artifact_versions": cp.artifact_versions` to `_checkpoint_summary` and no test
  fails — `grep -rn "artifact_versions" tests/unit/mcp/tools/test_checkpoints.py`
  matches only `model_copy(update={"artifact_versions": ...})` injections into the
  *record* (`:277,348,367`) and the unrelated `list_artifact_versions` tool
  (`:16,102,105,230,232`); nothing asserts the summary's key set. So the projection is
  free to drift from the record it projects.
- **Reproduce:** `grep -n "_checkpoint_summary\|artifact_versions" src/film_pipeline/mcp/tools/checkpoints.py`
  and Appendix A.6.
- **Blast radius:** `src/film_pipeline/mcp/tools/checkpoints.py`, `src/film_pipeline/app/services/_browse_ops.py`
  (checkpoint views). User-visible: `list_checkpoints` cannot show which artifacts a
  checkpoint covers, so the operator must guess why a later rollback reports no
  invalidation; the projection makes the empty map look like a property of the record.
- **Candidate owner module:** `runtime_persistence.checkpoints` — one serialization of
  `CheckpointMetadata` (the projection is part of the public contract and must be
  derived from the record, not hand-listed).
- **Extraction sketch:** serialize from the model (`cp.model_dump()`, or an explicit
  field list asserted equal to the model's fields) so a new field cannot be silently
  omitted; add a guard test asserting the summary keys
  ⊇ `{"checkpoint_id", "artifact_versions", ...}`. Pair with the `F-CRP-04` factory
  fix — either alone leaves the seam half-owned.
- **Prior art:** new; the read-projection half is not mentioned in
  `documentation/audit-findings.md` or in the reviewed revision.

### F-CRP-16 — The revision fallback's `_resume_to_repair` flag has an unobserved production consumer

- **Class:** O8 (an undeclared dict-key contract between `app` and `graph`) with O6 (a
  second resume/recovery lifecycle)
- **Severity:** Low (impact 1 × drift 3 = 3). *Verifier missed-seam M5, recorded not
  scored; this revision keeps it Low and gives it the drift proof the verifier did not
  reproduce.*
- **Concern:** `request_revision`'s no-interrupt fallback hands the graph two raw
  private keys, and the production node that consumes one of them is reached by no
  test; the same manual-advance seam `F-CRP-03`/`F-CRP-05` describe for `approve_phase`
  is unmentioned for the revision path.
- **De-facto owners:**
  - `src/film_pipeline/app/_graph_exec.py:381-393` — the negative branch of `_has_pending_human_interrupt` — `"if _has_pending_human_interrupt(snapshot):"` … `"recovery_state["_revision_note"] = note"` / `"recovery_state["_resume_to_repair"] = True"` / `"state = graph.invoke(recovery_state, config)"`
  - `src/film_pipeline/app/_graph_exec.py:151-160` — the predicate with a single call site — `"def _has_pending_human_interrupt(snapshot: Any) -> bool:"`
  - `src/film_pipeline/graph/state_schema.py:203-204` — the two keys are schema fields, not a typed payload — `"_revision_note: str"` / `"_resume_to_repair: bool"`
  - `src/film_pipeline/graph/nodes/_repair_loop.py:198` — the production consumer — `"if state.get("_resume_to_repair"):"`
  - `src/film_pipeline/graph/graph.py:193` — the entry route that reads the same key — `"if state.get("_resume_to_repair"):"`
  - `src/film_pipeline/app/_graph_exec.py:232-240` — the manual-advance seam shared with `approve_phase` — `"if _approval_stalled(state, active, current_phase):"` … `"return advance_to_next_phase(rt, dict(active))"`
- **Drift proof:** mutation scenario with a silent failure. Remove the branch at
  `src/film_pipeline/graph/nodes/_repair_loop.py:198-205` (the production consumer): the revision
  fallback enters the bounded repair loop without materializing the revision update,
  and **no test fails** — the only test that exercises this recovery
  (`tests/unit/app/test_resume_integrity.py:176-220`) replaces the whole node
  (`monkeypatch.setattr(graph_module, "repair_phase_node", fake_repair)`, `:202`) and
  asserts only the *input dict keys* (`:155-156`) or its own double's dict
  (`:192,199,213`); `grep -rn "_repair_loop" tests/` matches only channel-registry
  allow-list rows (`tests/unit/graph/test_channel_registry.py:222-224`). Impact 1
  (§1.5, cosmetic/internal): the failure is a recovery-of-last-resort path, it is
  audited as `resume_failed` (`src/film_pipeline/app/_graph_exec.py:400-406`) and re-raised, and no
  durable data is corrupted.
- **Reproduce:** `grep -rn "_resume_to_repair\|_revision_note" --include=*.py src/ tests/`
  → producer `src/film_pipeline/app/_graph_exec.py:391-392`; consumers `src/film_pipeline/graph/graph.py:193`,
  `src/film_pipeline/graph/nodes/_repair_loop.py:198`, `src/film_pipeline/graph/nodes/approval.py:273`; the only tests are
  the fake-graph assertions above.
- **Blast radius:** `src/film_pipeline/app/_graph_exec.py`, `src/film_pipeline/graph/nodes/_repair_loop.py`,
  `src/film_pipeline/graph/nodes/approval.py`, `src/film_pipeline/graph/state_schema.py`. User-visible: after an operator
  requests a revision on a run whose checkpoint has no live interrupt, the repair loop
  can start from the un-revised state; F-CRP-03's stalled-manual-advance consequence
  then applies to a second entry point.
- **Candidate owner module:** `runtime_persistence.resume_coordinator` — owns the
  recovery payload as a type (`ResumeExternalState`/`ResumePayload`) and the fallback
  condition; the repair consumer reads the type, not a raw key.
- **Extraction sketch:** fold the revision recovery payload into the same typed
  envelope as `F-CRP-03` (one dataclass with `revision_note`, `resume_to_repair`,
  `remove_issue_codes`), and route both `approve_phase` and `request_revision`
  fallbacks through one `resume_coordinator` decision. Guard test: a real-graph
  (non-monkeypatched) `repair_phase_node` test asserting the revision update is
  materialized for the fallback input, plus a round-trip test on the typed payload.
- **Prior art:** `documentation/audit-findings.md:124` (approval fallback) covers the
  `approve_phase` half only; the revision-path consumer is new. Overlaps
  `audit/01:258` F-PHASE-04 (successor-phase duplication) only through the shared
  manual-advance seam; see §6.7.

---

## 5. Clean concerns (with the guard that pins them)

### 5.1 The on-disk project record has a single writer

`src/film_pipeline/artifacts/project_storage.py:152-156` is the only writer of `project.json`.
`write_project_record` has exactly one caller, `src/film_pipeline/app/_persistence.py:265`
(`grep -rn "write_project_record" src/` → definition + that one call); the module
function `persist_project_state` is reached from exactly two places
(`src/film_pipeline/app/runtime.py:97` delegate and `src/film_pipeline/app/_persistence.py:192`), and the runtime
wrapper `_persist_project_state` has 17 call sites
(`grep -rn "persist_project_state" src/` → 21 hits = 2 definitions + 17 wrapper
calls + 2 module-function calls). Guard:
`tests/unit/artifacts/test_state_persistence.py:110-125` round-trips the record
and asserts the canonical filename; `tests/unit/artifacts/test_storage_boundary.py:150-157`
pins the layout allowlist.

### 5.2 The append-only JSONL logs have one writer each

`ProjectStorage.append_checkpoints` / `append_audit_events`
(`src/film_pipeline/artifacts/project_storage.py:189,199`) are called only from
`src/film_pipeline/app/_persistence.py:236,249`. Guard:
`tests/unit/artifacts/test_state_persistence.py:196-213`
(`test_checkpoint_jsonl_appends_without_duplicates`) and `:215-232` (audit
idempotence).

### 5.3 The checkpoint git backend is one implementation behind one injection seam

`src/film_pipeline/artifacts/project_storage.py:266-278` holds the injected type; production
injects the single `GitBackend` at `src/film_pipeline/app/_persistence.py:36`
(`set_git_backend_type(GitBackend)`), and the test double replaces it at
`tests/conftest.py:75-83`. Guard:
`tests/unit/artifacts/test_storage_boundary.py:181-188` pins the
"no backend injected → RuntimeError" refusal
(`src/film_pipeline/artifacts/project_storage.py:251-254`). Gap: nothing pins behavioural parity
between `GitBackend` and `src/film_pipeline/testing/in_memory_git.py` — see §7.

### 5.4 Resume's phase-progress rule re-derives the graph's ordering, but the pair is pinned

`src/film_pipeline/app/_resume.py:31-32` decides "approval made progress" by comparing
`PHASE_ORDER` indices (`"return PHASE_ORDER.index(current_phase) > PHASE_ORDER.index(previous_phase)"`),
while the graph advances by a *separate* table,
`src/film_pipeline/graph/edges.py:40` `_NEXT_PHASE_AFTER_APPROVAL`, consumed at
`src/film_pipeline/graph/edges.py:119` (`"return _NEXT_PHASE_AFTER_APPROVAL.get(phase, "end")"`),
and the manual fallback uses index arithmetic again
(`src/film_pipeline/app/_graph_exec.py:441` `"next_phase = PHASE_ORDER[current_index + 1]"`).
That is O1-shaped duplication, but the two tables are bound end-to-end: skip a
phase in `_NEXT_PHASE_AFTER_APPROVAL` and
`tests/e2e/test_scenario_11_full_flow_3min.py:106`
(`advance = _approve_to_phase(rt, "shot_bible")`) fails; change the phase list and
`tests/unit/test_graph.py:70` (`assert len(PHASE_ORDER) == 11`) fails. Recorded as
**clean-with-caveat**: a refactor should still derive one from the other, and
`grep -rn "_NEXT_PHASE_AFTER_APPROVAL" tests/` → no match means only the e2e path
protects it.

### 5.5 The checkpointer mode agrees with the policy authority in all four combinations

Mechanically evaluated (Appendix A.1): P2 ≡ P1 for all four rows, so the
"SQLite only when persistence is explicitly enabled" claim
(`src/film_pipeline/graph/graph.py:42`) holds. Partial guard: the combination
(`PERSIST_STATE=1, NO_PERSIST=1`) is pinned twice
(`tests/unit/app/test_logging_setup.py:148-160,167-171` and
`tests/unit/graph/test_graph.py:16-29` covers `PERSIST_STATE=1` / `PERSIST_STATE`
unset with `NO_PERSIST` absent). **Gap:** no parametrized test walks all four
combinations; (`PERSIST_STATE` unset, `NO_PERSIST=1`) is not asserted for P2
anywhere.

### 5.6 Dead code with no ownership

`src/film_pipeline/app/runtime.py:190-194` (`_artifact_root`) has no caller in `src/`
(`grep -rn "_artifact_root" src/`); `src/film_pipeline/checkpoints/branches.py` and
`src/film_pipeline/checkpoints/resume.py` are exported and unit-tested but unused in `src/`
(§3.2, F-CRP-05). These are not ownership seams; they are B4 "assign or delete"
candidates.

---

## 6. Candidate module boundary — `runtime_persistence`

### 6.1 One-sentence responsibility and non-goals

`runtime_persistence` decides **whether a run persists, where its roots are, and
is the single writer of every runtime state file and checkpoint record**.
Non-goals: it does not own artifact payload layout (`artifacts._layout` /
`ProjectStorage` keep that), does not own graph topology or phase ordering
(`graph`), and does not own the git plumbing (`checkpoints.git_backend` remains a
backend behind its port).

### 6.2 N / I / R

- **N (normative model):** `PersistenceMode` enum; `RootLayout` value object
  (`storage_root`, `runtime_root`, `checkpoint_root`, `run_root`) with the
  coincidence invariants; the `ResumePayload`/`ResumeExternalState` types; the
  `STALE_GENERATION_REQUEST_CODES` vocabulary; the `RollbackRecord` factory rule.
- **I (invariant enforcement):** exactly one of {durable, ephemeral, run-scoped}
  per process; the storage root marker rule; "a project's record, snapshot,
  checkpoints, audit and artifacts live in one directory"; "a checkpoint's
  `artifact_versions` is derived, not caller-supplied"; "every destructive
  operation emits an audit event"; the resume fallback condition; an explicit root
  override cannot silently promote a non-persistent process to durable (F-CRP-13);
  deletion archives inside the runtime root in use (F-CRP-14); importing a module
  writes nothing durable (F-CRP-12); a public projection is derived from the record
  it projects (F-CRP-15).
- **R (representation authority):** single writer for
  `project.json`, `state/graph-state.json`, `checkpoints/checkpoints.jsonl`,
  `audit/audit-log.jsonl`, the in-memory checkpoint/audit registries, and the
  LangGraph checkpointer choice+root.

### 6.3 Declared public contract

```python
class PersistenceMode(StrEnum): DURABLE; EPHEMERAL; RUN_SCOPED

def resolve_persistence() -> PersistencePolicy        # mode + precedence, one place
def resolve_roots(policy: PersistencePolicy) -> RootLayout

class CheckpointStore:            # the single checkpoint registry + JSONL writer
    def create(...) -> CheckpointMetadata          # derives artifact_versions
    def get(id) / list(project_id) / latest_for_artifact(project_id, artifact_id)
    def append_to_disk(project_id) -> None

class AuditTrail:
    def record(actor, action, *, project_id, **details) -> None   # always persists
    def read(project_id, limit) -> list[AuditEvent]

class ResumeCoordinator:          # owns Command(resume=...) payload + fallback
    def resume_approval(rt, active, phase) -> dict
    def resume_revision(rt, active, note) -> dict
```

### 6.4 Dependency law

`runtime_persistence` may import `schemas`, `artifacts` (public gateway only) and
the `checkpoints` *backend port*; it must not import `graph`, `mcp`, `cli`, or
`app.services`. `app`, `cli`, `mcp` and `graph` consume it; `graph` receives the
checkpointer root and the `ResumePayload` type through the runtime contract, never
by reading env vars (`src/film_pipeline/graph/graph.py:43`, `src/film_pipeline/graph/services.py:31,48` are the two
violations to remove).

### 6.5 Conformance map (files this module absorbs or governs)

| File | Disposition |
|---|---|
| `src/film_pipeline/app/_persistence.py` | becomes the module's `persistence` core |
| `src/film_pipeline/app/_resume.py` | becomes `resume_coordinator`; typed payload |
| `src/film_pipeline/checkpoints/manager.py` | becomes `CheckpointStore`; drops its public `checkpoints` dict |
| `src/film_pipeline/checkpoints/rollback.py` | consumes `CheckpointStore` + `AuditTrail`; record factory moved here |
| `src/film_pipeline/checkpoints/resume.py` | **delete** (unused) or fold into `resume_coordinator` |
| `src/film_pipeline/checkpoints/branches.py` | **delete** or fold into `CheckpointStore` |
| `src/film_pipeline/checkpoints/invalidation.py` | moves behind `artifacts.provenance` for its data source |
| `src/film_pipeline/app/runtime.py` checkpoint/audit/root members | become thin delegates / removed |
| `src/film_pipeline/app/logging_setup.py:78-81`, `src/film_pipeline/graph/graph.py:43`, `src/film_pipeline/graph/services.py:31,48`, `src/film_pipeline/cli/run.py:226`, `src/film_pipeline/mcp/server.py:243` | replace the formula with the resolved policy object |
| `src/film_pipeline/app/safety.py:25-32,111` | **new row (F-CRP-14):** `persist_root()` is deleted; the trash root arrives as a `RootLayout` field |
| `src/film_pipeline/graph/graph.py:201` | **new row (F-CRP-12):** the module-level `graph = build_graph()` moves behind a lazy accessor; importing the module has no durable side effect |

**Candidate-owner collision with `audit/03:825` — resolved in favour of this module's
*composition* role (verifier §4; `audit/03`'s own D8 reconciliation).**
`audit/03:825` records "**Storage root** resolution | `src/film_pipeline/artifacts/storage.py` |
`STORAGE_ROOT_ENV` declared and read only at `:28`/`:86`; consumers use
`resolve_storage_root()` | guards `tests/unit/artifacts/test_storage.py:29-78`,
`tests/unit/artifacts/test_storage_guards.py`". That row is **not** contradicted:
the *resolver* R1 stays in `src/film_pipeline/artifacts/storage.py`, and its guard tests stay with it.
What is unowned at HEAD is the **composition** of the roots —
**policy** (`src/film_pipeline/app/_persistence.py`, `src/film_pipeline/mcp/server.py`, `src/film_pipeline/cli/run.py`) → **studio**
(`src/film_pipeline/app/runtime.py`), **lifecycle** (`src/film_pipeline/graph/graph.py`, `src/film_pipeline/graph/services.py`) →
**checkpoints**, **bytes** (`src/film_pipeline/artifacts/storage.py` / `ProjectStorage`) → **storage**.
`runtime_persistence.RootLayout` owns that composition and consumes R1; it does not
redefine or relocate R1, so no guard from `audit/03:825` is reassigned. `F-CRP-01`,
`F-CRP-12`, `F-CRP-13` and `F-CRP-14` are all defects of the *composition* (R2–R8).

### 6.7 Prior-art and candidate-owner collisions (verified against the sibling audits)

| This file's nomination | Colliding/overlapping nomination | Resolution recorded here |
|---|---|---|
| `runtime_persistence` / `RootLayout` (F-CRP-01, 12–14) | `audit/03:825` — storage-root resolution single-owned by `src/film_pipeline/artifacts/storage.py`, guards `tests/unit/artifacts/test_storage.py:29-78` | **Not a collision after §6.5:** R1 stays; the module owns the R2–R8 composition. No guard reassigned. |
| `runtime_persistence.policy` (F-CRP-09) | `audit/03:462` **F-CFG-08** (same `NO_PERSIST` re-derivation, 7 read sites / 6 modules, High 4×3=12, owner `app/_persistence` at `audit/03:492`); `audit/11:309` already flags a **third** owner (`app.bootstrap`) | **Three owners, one concern.** This file's position: `config.environment` reads raw env (audit 03's invariant 5), `runtime_persistence.policy` owns the *decision*, `app.bootstrap` owns *when* bootstrap runs. Severity difference 12 vs 9 is reconciled by scope: `audit/03` counts the root/profile branch (F-CRP-09 + F-CRP-13 here) while this file scores the boolean policy alone. To be resolved once in `03-target-architecture.md`. *Housekeeping:* `audit/11:309`'s line pointer into this file (`audit/10:817-850`) is stale after this revision — cite `F-CRP-09` by id, not by line. |
| `graph.resume_protocol` (F-CRP-03) / `resume_coordinator` (F-CRP-16) | `audit/01:258` **F-PHASE-04** — "the successor-phase function is implemented twice inside the graph" (`src/film_pipeline/graph/edges.py:40` `_NEXT_PHASE_AFTER_APPROVAL`) | **Overlapping but distinct:** 01 owns the phase-successor table; this file owns the *resume payload* and the manual-advance fallback that reads phase order (`src/film_pipeline/app/_resume.py:31-32`, §5.4). Cite 01 in the resume seam; no owner moved. |
| `artifacts.provenance` (F-CRP-07) | `audit/07` nominates `artifacts.contract`/`ArtifactStore` for the kind registry; `audit/06:931` gives `artifacts` "every byte written under a project" | **Coherent, not colliding:** the `built_from` dependency *model* has no owner in 06/07. Cross-cluster flag for `03-target-architecture.md`. |
| `runtime_persistence.checkpoints` / `.rollback` (F-CRP-02/04/06/15) | `audit/14:48,364-379` (edge counts; `testing→checkpoints` boundary) | **Adjacent, not colliding:** audit 14 nominates no checkpoint owner. |
| `runtime_persistence.audit` (F-CRP-11) | none found in 03/07/14 | no collision. |

### 6.6 Guard tests that must fail if the seam regresses

1. `test_single_persistence_policy`: all flag combinations → one `PersistenceMode`;
   every consumer (logging, checkpointer, artifact store, CLI) reports the same.
2. `test_one_checkpoint_registry`: create → restart → rollback succeeds; no second
   registry exists (import/attribute test).
3. `test_roots_coincide`: CLI run root and app runtime root produce the same
   `RootLayout` for one project id, and the storage root still opens afterwards.
4. `test_checkpoint_artifact_versions_always_derived`: MCP create and auto
   checkpoint yield a non-empty map when candidate refs exist.
5. `test_resume_payload_round_trip`: builder → `_apply_external_state` clears the
   stale codes (producer/consumer contract).
6. `test_rollback_is_audited`: one rollback → exactly one audit event + one
   persisted `RollbackRecord`.
7. `test_delete_project_is_audited_on_disk`: archived audit log contains the
   deletion.
8. Import-boundary test: `checkpoints`/`runtime_persistence` never read
   `FILM_PIPELINE_*` env vars outside the policy module.
9. `test_import_has_no_durable_side_effect` (F-CRP-12): with `PERSIST_STATE=1` and a
   fresh `FILM_PIPELINE_STORAGE_ROOT`, importing `film_pipeline.graph.graph` creates
   no child of the storage root and the root still opens.
10. `test_runtime_root_respects_policy` (F-CRP-13): `RUNTIME_ROOT` set with
    `PERSIST_STATE` unset ⇒ the resolved mode is not `DURABLE`, and no
    `storage.json`/`project.json` is written under that root (or promotion to
    `RUN_SCOPED` is explicit in the returned policy).
11. `test_delete_archives_inside_runtime_root` (F-CRP-14): delete a project created
    under `runtime_root=<tmp>/rt` with a different `STORAGE_ROOT`; the archive is under
    `<tmp>/rt/trash`, not the storage-root parent.
12. `test_checkpoint_summary_exposes_derived_versions` (F-CRP-15): the
    `list_checkpoints` summary carries `artifact_versions` for a checkpoint whose
    record has a non-empty map.

---

## 7. Borderline observations (not findings under §1.6.3)

Recorded for the reconciliation step; none has a drift proof that meets §1.6.3, so
none is a finding.

1. `src/film_pipeline/artifacts/store.py:343` reads the record filename as the literal
   `"project.json"` instead of using `_layout.PROJECT_FILENAME` (`:38`) or
   `ProjectStorage.project_record_name()` (`:107`), and `src/film_pipeline/artifacts/store.py:70-71`
   (`return self._root / project_id`) duplicates `ProjectStorage.project_dir`
   (`:98-100`). A rename of the layout constant **is** caught
   (`tests/unit/artifacts/test_state_persistence.py:120-121` asserts the literal),
   so the mutation is loud, not silent — but the failure points at the test, not
   at `store.py`, so the second site is easy to miss. Impact is cosmetic (README
   falls back to `phase="intake"`).
2. `src/film_pipeline/testing/in_memory_git.py:60` re-implements `git add -A` / gitignore semantics
   (§`_is_ignored`, `:91-114`) for ~50 test modules. Its docstring claims parity
   (`:11-16`) but no parity test binds it to `GitBackend`
   (`grep -rn "InMemoryGitBackend" tests/` → `tests/conftest.py` only). I could
   not produce a concrete behavioural divergence in the audit budget, so this
   stays an explicitly labelled observation, not a finding.
3. **Promoted in this revision (was a borderline note):** `src/film_pipeline/graph/graph.py:201`
   (`graph: CompiledStateGraph = build_graph()`) opens a checkpointer at *import*
   time using R2, while `app` builds its own with R5; the reviewed revision folded
   this into F-CRP-01 and tested only the "two SQLite files" consequence. It is now
   finding **F-CRP-12**, because the import also `mkdir`s inside the storage root and
   makes it unopenable (Appendix A.9). The two-checkpointer-file consequence remains
   part of F-CRP-01's blast radius.
4. **Corrected and promoted in this revision:** `src/film_pipeline/app/safety.py:32` derives the
   safe-delete base as `resolve_storage_root().resolve().parent`, i.e. a *fourth* root
   notion (`~/.film-pipeline`), used for the trash destination
   (`src/film_pipeline/app/safety.py:111`; the reviewed revision cited `src/film_pipeline/app/runtime.py:142`). The
   derivation "agrees with `default_run_root()`'s parent today" — true of the *value*,
   false of the *use*: nothing binds it to `rt.runtime_root`, so a project created
   under an explicit runtime root is archived into a different tree. Now finding
   **F-CRP-14** (Appendix A.11).
5. `src/film_pipeline/app/runtime.py:190-194` (`_artifact_root`) is dead *and* correct (it returns the
   store root or R1); F-CRP-12/13 show the live root derivations are the weaker ones.
   Recorded so the reconciliation step does not "fix" the dead function instead of
   the live branch.

---

## 8. Unverified / limits

- I did not execute the full test suite (the working tree was concurrently dirty and
  running it would test another agent's mid-flight edits, not `fb85baa`). All
  "no test fails" claims are static: they rest on the exact `grep` commands cited
  per finding, each showing the mutation site is unreferenced by any test.
- **The independent verifier executed the mutations and test files** against its own
  pristine snapshots (`verify-10.md` §6): F-CRP-02 → `tests/unit -m "not integration
  and not e2e"` **1866 passed, 3 skipped**; F-CRP-03 → the two named test files
  **49 passed**; F-CRP-10 → `tests/unit/mcp/tools/test_generation.py` **41 passed**;
  the cited checkpoint/persistence files unmutated → **40 passed**. Those three
  findings' silence proofs are therefore *executed*, not merely predicted.
- **The M1/M2/M3 reproducers (Appendix A.9–A.11) were run by this author** against
  `/tmp/audit_head` (a `git archive fb85baa` snapshot) with the repo venv, and their
  outputs are pasted verbatim in the appendix; A.6 was likewise re-run after the D3
  rewrite. The remaining mutation scenarios (F-CRP-01/04/06/07/08/09/11/12/15/16)
  are still static predictions with the cited absence greps.
- Severity scores use the §1.5 rubric; the impact/drift integers are stated in each
  finding so a verifier can re-score without re-deriving the evidence. The band is
  derived from the score (§1.5), never relabelled; the header carries the mechanical
  check (`impact × drift` → band → mix) that asserts this for every finding.
- §7's remaining items (1, 2 and 5) are deliberately **not** findings; nothing in §4
  relies on them. Items 3 and 4 were **promoted** in this revision to F-CRP-12 and
  F-CRP-14 respectively.
- No claim in this document is based on the working tree; every anchor was
  re-read from `git archive fb85baa`.

---

## Appendix A — Reproducers

All probes below were run as
`PYTHONPATH=<snapshot>/src UV_CACHE_DIR=.uvcache .venv/bin/python <file>`
from the repo root, with `FILM_PIPELINE_STORAGE_ROOT` and
`FILM_PIPELINE_RUNTIME_ROOT` pointed at a fresh temp directory (no real home
writes).

### A.1 Persistence-policy truth table

```python
import itertools, os, tempfile
from pathlib import Path
tmp = Path(tempfile.mkdtemp())
os.environ["FILM_PIPELINE_STORAGE_ROOT"] = str(tmp / "storage")
os.environ["FILM_PIPELINE_RUNTIME_ROOT"] = str(tmp / "runtime")
from langgraph.checkpoint.memory import MemorySaver
from film_pipeline.app._persistence import use_persistent_runtime
from film_pipeline.graph.graph import _default_checkpointer
from film_pipeline.graph import services as svc
for persist, nopersist in itertools.product([None, "1"], [None, "1"]):
    for k in ("FILM_PIPELINE_PERSIST_STATE", "FILM_PIPELINE_NO_PERSIST"):
        os.environ.pop(k, None)
    if persist: os.environ["FILM_PIPELINE_PERSIST_STATE"] = persist
    if nopersist: os.environ["FILM_PIPELINE_NO_PERSIST"] = nopersist
    cp = _default_checkpointer(runtime_root=tmp / "runtime")
    print(persist, nopersist, "P1=", use_persistent_runtime(),
          "P2=", not isinstance(cp, MemorySaver),
          "P3=", svc._default_artifact_root(),
          "P5=", False if os.getenv("FILM_PIPELINE_NO_PERSIST") else use_persistent_runtime(),
          "P6=", not bool(os.getenv("FILM_PIPELINE_NO_PERSIST")))
    if not isinstance(cp, MemorySaver): cp.conn.close()
```

Expected output equals §2.2 (row 1 shows `P6=True` with `P1=P2=P5=False`).

### A.2 Presence-truthiness hazard

```python
import os, tempfile
from pathlib import Path
tmp = Path(tempfile.mkdtemp()); os.environ["FILM_PIPELINE_PERSIST_STATE"] = "1"
os.environ["FILM_PIPELINE_NO_PERSIST"] = "0"
from film_pipeline.app._persistence import use_persistent_runtime
from film_pipeline.graph.graph import _default_checkpointer
print(use_persistent_runtime(), type(_default_checkpointer(runtime_root=tmp)).__name__)
# -> False InMemorySaver
```

### A.3 Root comparison (CLI vs app)

```python
run_root = default_run_root()                                  # src/film_pipeline/cli/run.py:193
rt_cli = HeadlessDriver.setup_runtime("mock", run_root)         # src/film_pipeline/cli/driver.py:69
rt_app = StudioRuntime(server_mode="mock")                      # src/film_pipeline/app/runtime.py:62
# CLI project dir  = <storage>/runs/default/artifacts/p1
# APP project dir  = <storage>/p1
```

### A.4 Two checkpoint registries

```python
rt  = StudioRuntime(server_mode="mock", runtime_root=root)
rt.create_project("p1", title="T"); rt.set_active("p1")
cp  = rt.create_checkpoint("p1", "intake", "first")
rt3 = StudioRuntime(server_mode="mock", runtime_root=root)      # restart
rt3.checkpoint_managers["p1"].checkpoints.clear()               # simulate: line 145 absent
rt3.set_active("p1")
rollback_to_checkpoint({"confirmed": True, "checkpoint_id": cp.checkpoint_id})
# -> {"ok": False, "error": "Checkpoint not found: checkpoint:p1:intake:..."}
# while rt3.get_checkpoint(cp.checkpoint_id) is not None
```

### A.5 CLI poisons the shared storage root

```python
run_root = default_run_root()
ArtifactStore(root=run_root / "artifacts")      # markers <storage>/runs/default/artifacts
print(sorted(p.name for p in resolve_storage_root().iterdir()))   # ['runs']
ArtifactStore(root=resolve_storage_root())      # -> StorageRootError
```

### A.6 Manual checkpoint has empty `artifact_versions` (drives the real MCP tool)

Rewritten for verifier dispute **D3**: the reviewed revision seeded the *raw* state key
`set_candidate_ref(state, "script", ...)`, which writes `"script"` while
`get_candidate_refs` reads the namespaced key
(`src/film_pipeline/graph/orchestrator_state.py:27` `_CANDIDATE_REFS = f"{_ORCH_NS}__candidate_refs"`), so
the seed was a no-op and the appendix did not demonstrate what it claimed. The corrected
probe drives `src/film_pipeline/mcp/tools/checkpoints.py:create_checkpoint` and reads the result:

```python
import asyncio, os, tempfile
from pathlib import Path
tmp = Path(tempfile.mkdtemp(prefix="a6_"))
os.environ["FILM_PIPELINE_STORAGE_ROOT"] = str(tmp / "storage")
os.environ["FILM_PIPELINE_MCP_MODE"] = "mock"
os.environ.pop("FILM_PIPELINE_PERSIST_STATE", None)

from film_pipeline.app.runtime import reset_runtime
from film_pipeline.graph.orchestrator_state import set_candidate_ref, get_candidate_refs
from film_pipeline.mcp.tools.checkpoints import (
    create_checkpoint, get_invalidation_report, rollback_artifact,
)

rt = reset_runtime("mock")
rt.create_project("p1", title="T"); rt.set_active("p1")
state = rt.get_project("p1")
set_candidate_ref(state, "script", "artifact:script:v1")   # namespaced key, correct API
rt.projects["p1"] = state
rt._persist_project_state("p1")
print("candidate refs on state:", get_candidate_refs(rt.get_project("p1")))

created = asyncio.run(create_checkpoint({"reason": "manual"}))
print("MCP create_checkpoint ->", {k: created[k] for k in ("ok", "checkpoint_id") if k in created})
cp = rt.get_checkpoint(created["checkpoint_id"])
print("checkpoint.artifact_versions =", cp.artifact_versions)
inv = asyncio.run(get_invalidation_report({"checkpoint_id": cp.checkpoint_id}))
print("get_invalidation_report.will_invalidate =", inv.get("will_invalidate"))
rb = asyncio.run(rollback_artifact({"confirmed": True, "artifact_id": "script"}))
print("rollback_artifact(no explicit cp) ->", {k: rb[k] for k in ("ok", "error") if k in rb})
```

Observed output (re-run by this author against `/tmp/audit_head`):

```
candidate refs on state: {'script': 'artifact:script:v1'}
MCP create_checkpoint -> {'ok': True, 'checkpoint_id': 'checkpoint:p1:intake:fee99b09'}
checkpoint.artifact_versions = {}
get_invalidation_report.will_invalidate = []
rollback_artifact(no explicit cp) -> {'ok': False, 'error': "No checkpoint found containing artifact 'script'."}
```

### A.7 Discovered project loses its checkpoint log

```python
init_storage_root(root)
d = root / "disc" / "artifacts" / "01-vision" / "x"; d.mkdir(parents=True)
(d / "meta.json").write_text("{}")
(root / "disc" / "checkpoints").mkdir(parents=True)
(root / "disc" / "checkpoints" / "checkpoints.jsonl").write_text(
    json.dumps({"storage_schema_version": 1, "checkpoint_id": "checkpoint:disc:intake:deadbeef",
                "project_id": "disc", "phase": "intake", "reason": "on disk"}) + "\n")
rt = StudioRuntime(server_mode="mock", runtime_root=root)
# adopted: True | discovered flag: True | manager registered: True
# rt.checkpoints size: 0 | rt.list_checkpoints('disc'): [] | manager dict size: 0
# on-disk log still has 1 line: 1
```

### A.8 Delete audit never reaches disk

```python
rt.create_project("p1", title="T")
rt.delete_project("p1", force=True)
# archived audit log actions: ['create_project']
# in-memory actions:          ['create_project', 'delete_project']
```

### A.9 (M1) A bare import poisons the storage root — F-CRP-12

```python
import os, tempfile
from pathlib import Path
tmp = Path(tempfile.mkdtemp(prefix="m1_"))
os.environ["FILM_PIPELINE_STORAGE_ROOT"] = str(tmp / "storage")
os.environ["FILM_PIPELINE_PERSIST_STATE"] = "1"
os.environ.pop("FILM_PIPELINE_NO_PERSIST", None)
os.environ.pop("FILM_PIPELINE_RUNTIME_ROOT", None)

import film_pipeline.graph.graph as g          # module-level `graph = build_graph()` at :201
print("after import, children of storage root:", sorted(p.name for p in (tmp/"storage").iterdir()))
from film_pipeline.artifacts.storage import ensure_storage_root
try:
    ensure_storage_root(tmp / "storage")
    print("app opened storage root: OK")
except Exception as exc:
    print(f"app FAILED: {type(exc).__name__}: {str(exc)[:70]}...")
```

Observed output (this author, `/tmp/audit_head`):

```
after import, children of storage root: ['checkpoints']
app FAILED: StorageRootError: Refusing to use /var/folders/.../T/m1_hs...
```

### A.10 (M2) `RUNTIME_ROOT` bypasses the policy gate — F-CRP-13

```python
import os, tempfile
from pathlib import Path
tmp = Path(tempfile.mkdtemp(prefix="m23_"))
os.environ["FILM_PIPELINE_STORAGE_ROOT"] = str(tmp / "storage")
os.environ["FILM_PIPELINE_MCP_MODE"] = "mock"
os.environ.pop("FILM_PIPELINE_PERSIST_STATE", None)
os.environ.pop("FILM_PIPELINE_NO_PERSIST", None)

from film_pipeline.app._persistence import use_persistent_runtime
from film_pipeline.app.runtime import StudioRuntime

root = tmp / "real-runtime-root"
os.environ["FILM_PIPELINE_RUNTIME_ROOT"] = str(root)
rt = StudioRuntime(server_mode="mock")
print("[A] use_persistent_runtime()      =", use_persistent_runtime(), "(policy says: not persistent)")
print("[A] StudioRuntime.runtime_root    =", rt.runtime_root)
print("[A] artifact_store.root           =", rt.services.artifact_store.root)
rt.create_project("p2", title="T")
print("[A] durable project.json written? =", (root / "p2" / "project.json").exists())
print("[A] durable storage marker?       =", (root / "storage.json").exists())
```

Observed output (this author, `/tmp/audit_head`):

```
[A] use_persistent_runtime()      = False (policy says: not persistent)
[A] StudioRuntime.runtime_root    = <tmp>/real-runtime-root
[A] artifact_store.root           = <tmp>/real-runtime-root
[A] durable project.json written? = True
[A] durable storage marker?       = True
```

### A.11 (M3) Delete archives cross-root — F-CRP-14

The second half of the same probe (`/tmp/m2_m3.py`):

```python
os.environ["FILM_PIPELINE_RUNTIME_ROOT"] = str(tmp / "explicit-run-root")
rt2 = StudioRuntime(server_mode="mock")
rt2.create_project("p9", title="T")
print("[B] runtime root in use           =", rt2.runtime_root)
print("[B] safety.persist_root()         =", safety.persist_root())
rt2.delete_project("p9", force=True)
arch = [str(p) for p in tmp.rglob("project-p9-*")]
print("[B] archive created under         =", arch)
print("[B] archive inside runtime root?  =", any(str(rt2.runtime_root) in a for a in arch))
```

Observed output (this author, `/tmp/audit_head`; `persist_root()` is printed after
`.resolve()`, hence `/private/var/...` on macOS):

```
[B] runtime root in use           = <tmp>/explicit-run-root
[B] safety.persist_root()         = /private/var/folders/.../T/m23_...   (= <tmp>, the storage root's parent)
[B] archive created under         = ['<tmp>/trash/project-p9-20260925-132709-428339-p9']
[B] archive inside runtime root?  = False
```

### A.12 (M4) The summary projection drops `artifact_versions` — F-CRP-15

Static + runtime check (no probe file needed):

```python
import inspect
from film_pipeline.app.runtime import StudioRuntime
import film_pipeline.mcp.tools.checkpoints as c
print("factory accepts artifact_versions:", "artifact_versions" in StudioRuntime.create_checkpoint.__code__.co_varnames)
print("summary keys:", [l.strip() for l in inspect.getsource(c._checkpoint_summary).splitlines() if '":' in l])
```

Observed output (this author, `/tmp/audit_head`):

```
factory accepts artifact_versions: True
summary keys: ['"checkpoint_id": cp.checkpoint_id,', '"project_id": cp.project_id,', '"phase": cp.phase.value,', '"created_at": cp.created_at.isoformat(),', '"reason": cp.reason,']
```

### Static commands used verbatim in findings

```bash
grep -rn "FILM_PIPELINE_NO_PERSIST\|FILM_PIPELINE_PERSIST_STATE" --include=*.py src/
grep -rn "default_run_root()\|runtime_root / \"artifacts\"\|artifacts_root=self.runtime_root" --include=*.py src/
grep -rn "checkpoint_managers\|rt\.checkpoints\|self\.checkpoints\|manager\.checkpoints" --include=*.py src/
grep -rn "_external_state\|remove_issue_codes" --include=*.py src/ tests/
grep -rn "artifact_versions" --include=*.py src/film_pipeline/app src/film_pipeline/mcp src/film_pipeline/checkpoints
grep -rn "ResumeManager\|ResumeSnapshot\|BranchManager" --include=*.py src/
grep -rn "read_graph_state" --include=*.py src/
grep -rn "\.records\b" --include=*.py src/
grep -rn "_record_audit" --include=*.py src/film_pipeline/mcp/tools/checkpoints.py src/film_pipeline/checkpoints/
grep -rn "DEPENDENCY_GRAPH" --include=*.py src/
grep -rn "DEPENDENCY_GRAPH" --include=*.py tests/          # no match
grep -rn "built_from" --include=*.py src/
grep -rn "_STALE_REQUEST_CODES\|_STALE_ISSUE_CODES\|no_generation_requests\|empty_generation_requests" --include=*.py src/ tests/
grep -rn "_NEXT_PHASE_AFTER_APPROVAL" --include=*.py tests/   # no match
grep -rn "run_id" --include=*.py src/                         # no match
# added in this revision (F-CRP-12..16)
grep -rn "graph: CompiledStateGraph = build_graph()\|checkpoint_dir.mkdir" --include=*.py src/
grep -n "FILM_PIPELINE_RUNTIME_ROOT\|use_persistent_runtime" src/film_pipeline/app/runtime.py
grep -rn "persist_root()" --include=*.py src/film_pipeline/app/
grep -n "_checkpoint_summary\|artifact_versions" src/film_pipeline/mcp/tools/checkpoints.py
grep -rn "_resume_to_repair\|_revision_note" --include=*.py src/ tests/
grep -rn "_repair_loop" --include=*.py tests/
# band derivation asserted in the header (must print 16 findings: 6/6/3/1)
# see the Verification record block; run it after any severity edit
```
