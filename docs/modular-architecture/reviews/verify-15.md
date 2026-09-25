# verify-15 — Second-round verification of `audit/10` findings `F-CRP-12` … `F-CRP-16`

**Verifier:** an agent that did **not** write audit 10 and did **not** write `verify-10.md`.
Bar **A6** (`docs/modular-architecture/00-methodology-and-quality-bar.md:138-141`), evidence
rules §1.6, severity rubric §1.5, O-taxonomy §1.4.

**Scope:** the five findings the author folded in after the first verification
(`audit/10` §4 "Added by independent verification", seams M1–M5). `F-CRP-01` … `F-CRP-11`
are *not* re-verdict here; they are touched only where a new finding cites them
(double-count check) or where the header/§6.5/§6.7 arithmetic is checked.

---

## 0. Method and pinned revisions

### 0.1 Pristine source snapshot

```
$ mkdir -p /tmp/v15 && git archive fb85baa0e6b769b709791a96a89980089304bf13 | tar -x -C /tmp/v15
$ cd /tmp/v15 && git rev-parse HEAD
fatal: not a git repository (or any of the parent directories): .git
[exit 128]
$ cd ${REPO_ROOT} && git rev-parse HEAD
fb85baa0e6b769b709791a96a89980089304bf13
$ git status --porcelain            # empty, before and after this verification
```

`git archive` strips `.git`, so the snapshot itself cannot answer `git rev-parse HEAD`;
its identity is **the archive's source commit**, `fb85baa`, and the workspace HEAD was
`fb85baa` with a clean porcelain at both the start and the end of this session. Every
`src/` and `tests/` quote below was read from `/tmp/v15` (or a copy of it), never from the
working tree.

Python:

```
$ cd ${REPO_ROOT}
$ PYTHONPATH=/tmp/v15/src UV_CACHE_DIR=$PWD/.uv-cache uv run python <probe>
```

`PYTHONPATH` was confirmed to shadow the editable install:

```
$ PYTHONPATH=/tmp/v15/src ... uv run python -c "import film_pipeline, film_pipeline.graph.graph as g; print(film_pipeline.__file__); print(g.__file__)"
/tmp/v15/src/film_pipeline/__init__.py
/tmp/v15/src/film_pipeline/graph/graph.py
```

Baseline suite run on the snapshot (used as the control for every mutation):

```
$ cd /tmp/v15 && PYTHONPATH=/tmp/v15/src .venv/bin/python -m pytest tests/unit tests/test_smoke.py \
    --no-cov -p no:cacheprovider --junitxml=/tmp/base.xml
BASE EXIT=0
tests=1872 failures=0 errors=0 skipped=3
```

### 0.2 The audit file moved while this verification ran — revision pinned

`docs/modular-architecture/audit/10-checkpoints-and-runtime-persistence.md` is
**gitignored** (`git check-ignore -v` → `.gitignore:2:docs/`), so there is no VCS record of
its revisions. It changed under this verifier:

| when | lines | note |
|---|---|---|
| first read (start of session) | 1718 | `F-CRP-12` at :888, `F-CRP-13` at :946, band word for `F-CRP-13` = **High** |
| mid-session | 1786 → 1788 | author actively editing |
| **pinned revision verified here** | **1826** | sha256 `2a2d05f47819ddf6d5cf4462bc37522e9eb60756bfab01ca13e2e9a8d86ec9b9` |

```
$ cp docs/modular-architecture/audit/10-checkpoints-and-runtime-persistence.md /tmp/audit10-pinned.md
$ shasum -a 256 /tmp/audit10-pinned.md
2a2d05f47819ddf6d5cf4462bc37522e9eb60756bfab01ca13e2e9a8d86ec9b9  /tmp/audit10-pinned.md
$ wc -l /tmp/audit10-pinned.md
1826 /tmp/audit10-pinned.md
$ sleep 15 && shasum -a 256 docs/.../10-checkpoints-and-runtime-persistence.md
2a2d05f47819ddf6d5cf4462bc37522e9eb60756bfab01ca13e2e9a8d86ec9b9   # stable
```

**All line numbers for the audit document in this report refer to that pinned revision.**
The two sibling audits cited by §6.5/§6.7 were pinned the same way (they were also moving):

```
$ shasum -a 256 /tmp/audit03-pinned.md /tmp/audit11-pinned.md /tmp/audit01-pinned.md
81bdf80e50e673ed0f30a5ea5f18ebe1d7c3bc7ce9c0d0de6a107a88e61129a3  audit/03
d9553935e48608db42393b1196eff747b4fae4ed2ccc16a65be43f704ca0c09e  audit/11
4b017d0a727eb851a2ebeb82a56fae472e3d22342414936c910ccb077618b77a  audit/01
```

A consequence the author must accept: the anchor corrections in §6.5/§6.7 are **against
revisions that moved after this report**; I give the line *and the quoted text* so the
pointer can be re-found by content.

---

## 1. Verdicts

| finding | claimed | verdict | corrected score → band |
|---|---|---|---|
| `F-CRP-12` | Critical 5×5=25 | **DOWNGRADED** | **3×5=15 → High** |
| `F-CRP-13` | Critical 4×4=16 | **CONFIRMED-WITH-FIX** | 4×4=16 → Critical (stands) |
| `F-CRP-14` | High 4×3=12 | **CONFIRMED-WITH-FIX** | 4×3=12 → High (stands) |
| `F-CRP-15` | Medium 2×3=6 | **CORRECTED** | **2×2=4 → Medium** |
| `F-CRP-16` | Low 1×3=3 | **STRENGTHENED** | **2×5=10 → High** |

Nothing is `REJECTED`: all five have a reproduced mechanism. Nothing is a bare
`CONFIRMED`: every one of the five needs a correction.

---

## 2. `F-CRP-12` — import-time `<storage root>/checkpoints/` — **DOWNGRADED**

### 2.1 Anchors (all read from `/tmp/v15`)

| anchor | quoted text | resolves? |
|---|---|---|
| `graph/graph.py:201` | `graph: CompiledStateGraph = build_graph()` | ✅ exact |
| `graph/graph.py:181` | `checkpointer=checkpointer or _default_checkpointer(runtime_root=runtime_root)` | ✅ exact |
| `graph/graph.py:43-46` | `if os.getenv("FILM_PIPELINE_NO_PERSIST") or not os.getenv("FILM_PIPELINE_PERSIST_STATE"):` … `runtime_root / "checkpoints" if runtime_root is not None else default_checkpoints_root()` | ✅ both ends inside range |
| `artifacts/storage.py:74` | `return resolve_storage_root() / "checkpoints"` | ✅ exact |
| `graph/graph.py:49` | `checkpoint_dir.mkdir(parents=True, exist_ok=True)` | ✅ exact |
| `artifacts/storage.py:160-164` | `raise StorageRootError(` … `f"{MARKER_FILENAME} marker and does not look like a film-pipeline "` | ✅ inside range |
| `langgraph.json:4` | `"film_pipeline": "./src/film_pipeline/graph/graph.py:graph"` | ✅ exact |

**Anchor defect (1).** Blast radius, pinned `audit/10:1032-1033`:

> "the app and MCP server, whose `ensure_storage_root` call
> (`src/film_pipeline/app/runtime.py:62` … in `load_persisted_projects`) then refuses the root"

`app/runtime.py:62` is **not** an `ensure_storage_root` call:

```
$ awk 'NR>=58 && NR<=63 {printf "%d|%s\n", NR, $0}' src/film_pipeline/app/runtime.py
58|        if self.runtime_root is None:
59|            if os.getenv("FILM_PIPELINE_RUNTIME_ROOT", "").strip():
60|                self.runtime_root = configured_runtime_root()
61|            elif use_persistent_runtime():
62|                self.runtime_root = default_runtime_root()
63|                self.runtime_root.mkdir(parents=True, exist_ok=True)

$ grep -rn "ensure_storage_root" src/
src/film_pipeline/artifacts/store.py:50:from film_pipeline.artifacts.storage import ensure_storage_root
src/film_pipeline/artifacts/store.py:61:        self._root = ensure_storage_root(root)
src/film_pipeline/artifacts/storage.py:129:def ensure_storage_root(root: Path, *, policy)
src/film_pipeline/graph/services.py:19:    ensure_storage_root,
src/film_pipeline/graph/services.py:49:    return ArtifactStore(root=ensure_storage_root(root, profile=profile))
```

It is not reached through `load_persisted_projects` either — that function only *reads*
`rt.services.artifact_store`:

```
$ grep -n "def load_persisted_projects" -A 8 src/film_pipeline/app/_persistence.py
196:def load_persisted_projects(rt: StudioRuntime) -> int:
202:    storage = storage_for(rt)
203:    if storage is None or not storage.root.is_dir():
204:        return 0
```

The real refusal chain is `app/runtime.py:75-77` (`_build_services_for_mode(…, artifacts_root=self.runtime_root)`)
→ `graph/services.py:49` → `artifacts/store.py:61` → `artifacts/storage.py:160`. The
sentence must be re-anchored or deleted.

### 2.2 Reproduce

Appendix A.9, run verbatim:

```
$ PYTHONPATH=/tmp/v15/src UV_CACHE_DIR=$PWD/.uv-cache uv run python /tmp/v15probes/a9_fcrp12.py
after import, children of storage root: ['checkpoints']
app FAILED: StorageRootError: Refusing to use /var/folders/ww/8_r3txq94072x14t1k4pwbv40000gn/T/m1_lp...
STORAGE_ROOT= /var/folders/ww/.../T/m1_lpq4k8me/storage
```

Byte-for-byte as claimed. Static reproduce:

```
$ grep -rn "graph: CompiledStateGraph = build_graph()\|checkpoint_dir.mkdir" --include=*.py src/
src/film_pipeline/graph/graph.py:49:    checkpoint_dir.mkdir(parents=True, exist_ok=True)
src/film_pipeline/graph/graph.py:201:graph: CompiledStateGraph = build_graph()
```

### 2.3 Mechanism attack — the refusal does **not** fire through any real entry point

I reproduced the author's claim and then attacked its blast radius. **The durable side
effect is reachable from a real entry point; the stated consequence is not.**

`mcp.server:main` — this is the documented way to run the product
(`documentation/runbook-the-third-interval.md:76-81`: `export FILM_PIPELINE_PERSIST_STATE=1`,
`make run-mcp-real`). Replicating `mcp/server.py:243-257` in order, against a fresh root:

```
$ PYTHONPATH=/tmp/v15/src ... uv run python /tmp/v15probes/mcp_order_noroot.py
[N] use_persistent_runtime() = True
[N] configured_runtime_root() = /var/folders/.../mcpnr_a14gjhj7/storage
[N] storage children after configure_logging: ['logs']
[N] graph.graph imported by logging?  False
[N] StudioRuntime FAILED: StorageRootError Refusing to use .../mcpnr_a14gjhj7/storage as project storage: it exists wi
[N] graph.graph imported after runtime? False
```

The MCP server poisons the same root **six lines earlier** via
`configure_logging(configured_runtime_root())` → `app/logging_setup.py:90-92`
(`log_dir = Path(runtime_root) / "logs"; log_dir.mkdir(...)`), and **never imports
`film_pipeline.graph.graph` at all**. Any MCP start that would have been broken by
`checkpoints/` is already broken by `logs/`; `F-CRP-12`'s documented consequence is
attributed to the wrong line. (I am *not* filing this as a sixth finding — it is outside my
assignment — but it is a reachable, unrecorded instance of the same seam and the author
should record it: see §7 item 5.)

Same probe with the documented explicit runtime root (runbook lines 78-79):

```
$ PYTHONPATH=/tmp/v15/src ... uv run python /tmp/v15probes/mcp_order_explicitroot.py
[E] explicit root children after configure_logging: ['logs']
[E] storage children after configure_logging: MISSING
[E] StudioRuntime FAILED: StorageRootError Refusing to use .../explicit-run as project storage: it exists without a storage.json marker and doe
[E] graph.graph imported? False
```

Other entry points:

* `cli.run:main` — the CLI's store root is `<run_root>/artifacts` = `<storage>/runs/default/artifacts`
  (`cli/run.py:193` → `cli/driver.py:69`); it never opens the bare storage root, so
  `<storage>/checkpoints` cannot block it. (`ArtifactStore(root=resolve_storage_root())`
  failing is `F-CRP-01`'s CLI case, not this one.)
* `app.product_gate:main` — `app/product_gate.py:139-145` reads two YAML manifests and
  prints lines; it never touches a storage root.
* `app.smoke` — `app/smoke.py:11-19` imports `build_graph()` and therefore *does* poison the
  root, but never re-opens it. `langgraph.json:4` likewise (the LangGraph CLI imports the
  module and never calls `ensure_storage_root`).
* No single-process entry point imports `graph.graph` **before** it opens the storage root,
  because the app's import is lazy and gated on runtime construction:
  `app/_graph_exec.py:34-40` (`if rt.graph is None: from film_pipeline.graph.graph import build_graph`).

**`pytest` / `make ci-check`: never hits it, and nothing pins the ordering.** `tests/conftest.py:98`
sets `FILM_PIPELINE_NO_PERSIST=1` session-wide before test modules import, so every
`import film_pipeline.graph.graph` takes the `MemorySaver` branch at `graph/graph.py:43-44`.
My baseline full unit suite (1872 tests) is green. The *root formula* is pinned
(`tests/unit/artifacts/test_storage.py:64` asserts `default_checkpoints_root() == root / "checkpoints"`),
but the **import-time side effect at `graph/graph.py:201` is not**: nothing in `src/` or
`tests/` imports the module-level `graph` object —

```
$ grep -rn "from film_pipeline.graph.graph import" --include=*.py src/ tests/
src/film_pipeline/app/_graph_exec.py:37:        from film_pipeline.graph.graph import build_graph
src/film_pipeline/app/smoke.py:14:        from film_pipeline.graph.graph import build_graph
tests/unit/graph/test_graph.py:12:from film_pipeline.graph.graph import _default_checkpointer, build_graph
tests/unit/app/test_logging_setup.py:165:    from film_pipeline.graph.graph import _default_checkpointer
tests/unit/graph/test_graph.py / test_state_schema.py / test_real_human_gates.py, tests/unit/test_graph.py, tests/e2e/test_graph_execution.py
```

so drift **5** on that site is defensible, while drift for the root formula is not 5.

**Reversible?** Yes, trivially. The refusing error names the directory and tells the
operator to remove it (`artifacts/storage.py:160-164`). The poisoned root only ever becomes
unopenable if it was *unmarked and empty* beforehand — i.e. it never held pipeline data.
No durable data is lost or corrupted.

### 2.4 Severity verdict — DOWNGRADED, High (impact 3 × drift 5 = 15)

§1.5: impact 5 = "wrong behavior reaches a human deliverable or corrupts durable data";
3 = "wrong internal behavior, recoverable". The demonstrated effect is a durable SQLite DB
written into the **wrong namespace** (the storage root, not the resolved runtime root) plus
a manual-cleanup blocker on a root that had no pipeline data, fully reversible by
`rm -rf <storage>/checkpoints`. That is impact **3**, not 5. Drift **5** stands (executed:
the suite cannot fail; the import-order side effect is unpinned).

**15 is High** under §1.5 and under the pinned revision's now-normative band rule
(`audit/10:19-25`). If the author can exhibit a real entry point where the `graph.graph`
import precedes the first `ensure_storage_root` in the same process *and* the storage root
is the store root, impact 4 (4×5=20, Critical) is available — my probes above are the
counter-evidence that says it does not exist today.

### 2.5 Drift-proof verdict

§1.6.3(a) satisfied: an existing divergence, reproduced. The drift *narrative* is accurate
about `tests/conftest.py:98`. Keep it, but drop "the app and MCP server … then refuses the
root" and the `app/runtime.py:62` pointer.

### 2.6 Double-count check

Not a restatement of `F-CRP-01`. The pinned `F-CRP-01` already carries a **D2/M1** dispute
note that *cross-references* `F-CRP-12` instead of scoring the import case twice
(`audit/10:357-361` + `:370-371`); the two-checkpointer split is scored only under
`F-CRP-01`. Clean.

---

## 3. `F-CRP-13` — `RUNTIME_ROOT` bypasses the policy gate — **CONFIRMED-WITH-FIX**

### 3.1 Anchors

| anchor | quoted text | resolves? |
|---|---|---|
| `app/runtime.py:59-63` | `if os.getenv("FILM_PIPELINE_RUNTIME_ROOT", "").strip():` / `self.runtime_root = configured_runtime_root()` / `elif use_persistent_runtime():` | ✅ all three exact |
| `app/runtime.py:75-77` | `self.services = _build_services_for_mode(` / `self.server_mode, artifacts_root=self.runtime_root` | ✅ exact |
| `artifacts/storage.py:116-126` | `write_json_atomic(marker_path(root), asdict(marker))` (:125) / `return root` (:126) | ✅ inside range |
| `app/_persistence.py:259-265` | `persist_project_state` → `storage.write_project_record(project_id, record)` | ✅ exact |

No anchor defect.

Note on the band: at the revision this verification *started* against (1718 lines, sha
`f7d53ca8…` copy) this finding printed **High (4×4=16)** with a band-edge note. The pinned
revision prints **Critical (4×4=16)** under a normative "band is a function of the score"
rule. I checked that rule for convenience, as instructed:

```
$ # the header's own reproducibility script, run against the pinned snapshot
$ .venv/bin/python - <<'PY'   # verbatim from audit/10:39-52, path substituted
... band = lambda s: "Critical" if s >= 16 else "High" if s >= 9 else "Medium" if s >= 4 else "Low"
... rows = re.findall(r"^- \*\*Severity:\*\* ([A-Za-z]+) \(impact (\d) × drift (\d) = (\d+)\)", text, re.M)
...
16 findings: {'Critical': 6, 'High': 6, 'Medium': 3, 'Low': 1}
```

Every `label` now equals `band(impact × drift)` and the header's "6 Critical, 6 High,
3 Medium, 1 Low" reproduces. The earlier inconsistency (score 16 → Critical for
`F-CRP-02/03/04` but High for `F-CRP-13`; score 9 → High for `F-CRP-08/09` but Medium for
`F-CRP-05`, in one document) **is fixed in the pinned revision**. No band-edge complaint
remains. The sibling precedent the old note cited (`audit/14`'s `Medium (3×3=9)`) is now
inconsistent with the normative rule and should be reconciled program-wide, but that is
audit 14's problem.

### 3.2 Reproduce

Appendix A.10, verbatim:

```
$ PYTHONPATH=/tmp/v15/src ... uv run python /tmp/v15probes/a10_a11.py
[A] use_persistent_runtime()      = False (policy says: not persistent)
[A] StudioRuntime.runtime_root    = /var/folders/.../m23_h788e32j/real-runtime-root
[A] artifact_store.root           = /var/folders/.../m23_h788e32j/real-runtime-root
[A] durable project.json written? = True
[A] durable storage marker?       = True
```

Exactly as printed. Static reproduce:

```
$ grep -n "FILM_PIPELINE_RUNTIME_ROOT\|use_persistent_runtime" src/film_pipeline/app/runtime.py
22:    use_persistent_runtime,
59:            if os.getenv("FILM_PIPELINE_RUNTIME_ROOT", "").strip():
61:            elif use_persistent_runtime():
```

### 3.3 Mechanism attack

The mechanism is real and stronger than the finding states: it is not only "no
`PERSIST_STATE`" but also **`NO_PERSIST=1`**, because the env branch is taken before
`use_persistent_runtime()` is ever consulted. `StudioRuntime` therefore writes
`project.json` + `storage.json` while the process's own "never persist" switch is on. That
is a genuine contract violation. Confirmed.

Two defects in the **drift-proof paragraph** (pinned `audit/10:1079-1082`):

> "Drift 4: no test covers the combination — the storage-guard test deletes
> `PERSIST_STATE` but not `RUNTIME_ROOT` (`tests/unit/artifacts/test_storage_guards.py:63`)"

**Defect (1).** The cited test deletes **both**:

```
$ awk 'NR>=61 && NR<=64 {printf "%d|%s\n", NR, $0}' tests/unit/artifacts/test_storage_guards.py
61|        monkeypatch.setenv(STORAGE_ROOT_ENV, str(tmp_path / "real-storage"))
62|        monkeypatch.delenv("FILM_PIPELINE_RUNTIME_ROOT", raising=False)
63|        monkeypatch.delenv("FILM_PIPELINE_PERSIST_STATE", raising=False)
```

`:63` is the `PERSIST_STATE` deletion; `RUNTIME_ROOT` is deleted at `:62`.

**Defect (2).** "No test covers the combination" is false as worded. The combination
(`RUNTIME_ROOT` set, `PERSIST_STATE` unset, `NO_PERSIST=1`) is the **default for every
test in the suite**:

```
$ awk 'NR>=17 && NR<=31 {printf "%d|%s\n", NR, $0}' tests/conftest.py
17|@pytest.fixture(autouse=True)
18|def _isolated_runtime_root(
29|    monkeypatch.setenv("FILM_PIPELINE_RUNTIME_ROOT", str(tmp_path / "runtime-root"))
30|    monkeypatch.setenv("FILM_PIPELINE_STORAGE_ROOT", str(tmp_path / "storage-root"))
31|    monkeypatch.delenv("FILM_PIPELINE_PERSIST_STATE", raising=False)
```

with `NO_PERSIST=1` at `:98`. What is true — and is the real drift claim — is that **no
test asserts the invariant** (the two flags agreeing on the mode).

I executed the fix-direction mutation (gate the root branch behind the policy) against a
disposable snapshot:

```
$ # /tmp/v15-mut13: app/runtime.py:59  ->  if os.getenv("FILM_PIPELINE_RUNTIME_ROOT", "").strip() and use_persistent_runtime():
$ cd /tmp/v15-mut13 && PYTHONPATH=/tmp/v15-mut13/src .venv/bin/python -m pytest tests/unit tests/test_smoke.py \
    --no-cov -p no:cacheprovider --junitxml=/tmp/mut13.xml
MUT13 EXIT=1
tests=1872 failures=1 errors=0 skipped=3
  FAIL: tests.unit.artifacts.test_storage_guards.TestNoSilentAdoption test_runtime_ignores_legacy_cwd_projects
```

and the one failure is **collateral, not pinning**:

```
>       assert runtime.projects == {}
E       AssertionError: assert {'p1': {...}} == {}
/private/tmp/v15-mut13/tests/unit/artifacts/test_storage_guards.py:69: AssertionError
```

i.e. with the branch gated off, the suite's runtimes all fall into the shared per-pid temp
root and one test sees another test's leaked project. One incidental failure out of 1872
supports "**almost nothing pins this**" → drift 4 stands.

### 3.4 Severity verdict — CONFIRMED, Critical (impact 4 × drift 4 = 16)

Impact 4: a durable write performed under an explicit "do not persist" policy, to an
operator-supplied root; more than recoverable internal wrongness, short of data corruption.
Drift 4: supported by the executed mutation (1 incidental failure, no assertion of the
invariant). 4×4=16 is Critical under §1.5 and the pinned header's rule. The axis values
stand as verified; only the supporting sentence must be corrected.

### 3.5 Double-count check — **partial restatement of `F-CRP-09`**

`F-CRP-09` already counts this exact site:

```
$ awk 'NR>=851 && NR<=856 {printf "%d|%s\n", NR, $0}' /tmp/audit10-pinned.md
851|- **De-facto owners:** the six sites in §2.1 — `src/film_pipeline/app/_persistence.py:51`, …
853|  `src/film_pipeline/app/logging_setup.py:78-81`, `src/film_pipeline/cli/run.py:226` — plus the defaulting writer
854|  `src/film_pipeline/mcp/server.py:243-244` — … — and the root
856|  branch `src/film_pipeline/app/runtime.py:58-69`.
```

`F-CRP-09` (O5, 3×3=9) and `F-CRP-13` (O5, 4×4=16) name **the same lines**, the same class,
and the same candidate owner (`runtime_persistence.policy`). §2.1's P8 row already says the
root branch "is the only site that consults `FILM_PIPELINE_RUNTIME_ROOT` before the policy
gate (see F-CRP-13)". The §6.7 distinction ("this file scores the boolean policy alone")
is real but must be stated **inside `F-CRP-09`** too, otherwise one site carries two O5
scores with two different bands. Recommendation: make `F-CRP-13` an explicitly labelled
sub-case of `F-CRP-09`'s P8, keep the higher score, and say so in both blocks.

---

## 4. `F-CRP-14` — `persist_root()` cross-root deletion — **CONFIRMED-WITH-FIX**

### 4.1 Anchors

| anchor | quoted text | resolves? |
|---|---|---|
| `app/safety.py:25-32` | `def persist_root() -> Path:` … `return resolve_storage_root().resolve().parent` | ✅ :25 and :32 |
| `app/safety.py:111` | `root = trash_root or (persist_root() / "trash")` | ✅ exact |
| `app/runtime.py:153-157` | `project_root = self._detach_project_state(project_id)` / `self._archive_directory(` / `project_root, trash_prefix=f"project-{project_id}-", force=force` | ✅ exact |
| `app/runtime.py:181-188` | `move_to_trash(path, prefix=trash_prefix)` (:184) | ✅ inside range |

### 4.2 Reproduce

Appendix A.11, verbatim (second half of the A.10 probe):

```
[B] runtime root in use           = /var/folders/.../m23_h788e32j/explicit-run-root
[B] safety.persist_root()         = /private/var/folders/.../T/m23_h788e32j
[B] archive created under         = ['/var/folders/.../m23_h788e32j/trash/project-p9-20260925-140052-533618-p9']
[B] archive inside runtime root?  = False
```

Exactly as printed. Static reproduce, run verbatim — **and it returns three lines, not two**:

```
$ grep -rn "persist_root()" --include=*.py src/film_pipeline/app/
src/film_pipeline/app/safety.py:25:def persist_root() -> Path:
src/film_pipeline/app/safety.py:75:    if _is_under(resolved, persist_root()):
src/film_pipeline/app/safety.py:111:    root = trash_root or (persist_root() / "trash")
```

### 4.3 Anchor defect (1)

The finding's owner list and §6.5's conformance row both describe `persist_root()` as
`:25-32,111`. The **second use site** is `app/safety.py:75`, inside `is_safe_to_delete`:

```
$ awk 'NR>=58 && NR<=79 {printf "%d|%s\n", NR, $0}' src/film_pipeline/app/safety.py
58|def is_safe_to_delete(path: Path) -> bool:
75|    if _is_under(resolved, persist_root()):
76|        return True
```

Deleting `persist_root()` (the stated fix) **must** edit `:75`; §6.5's row
`src/film_pipeline/app/safety.py:25-32,111` (`/tmp/audit10-pinned.md:1403`) therefore
under-specifies the change. More importantly it hides a split the new owner must resolve:
the *value* of the trash root moves to `RootLayout`, while
`is_safe_to_delete` / `require_safe_to_delete` (`:82-89`) still decide *whether a path is
deletable* from a separately-derived base. §6.5 should name that predicate explicitly
(stays in `app/safety`, consumes `RootLayout`).

### 4.4 Mechanism attack

Real, reproduced, and correctly characterised by the finding: the *value* of
`persist_root()` agrees with `default_run_root()`'s parent today, but its *use* is bound to
neither `rt.runtime_root` nor the store root, so a delete under an explicit runtime root
moves the project into a different tree. The drift characterisation in the finding is
honest and I confirmed it against the suite:

```
$ awk 'NR>=96 && NR<=123 {printf "%d|%s\n", NR, $0}' tests/unit/app/test_runtime.py
98|    monkeypatch.setenv("FILM_PIPELINE_STORAGE_ROOT", str(persist / "projects"))
101|    runtime_root=tmp_path / "runtime",
120|    trash_root = persist / "trash"
121|    archived = list(trash_root.glob("project-p-trash-*"))
122|    assert len(archived) == 1
```

The suite freezes the cross-root destination (`persist/"trash"`, not
`tmp_path/"runtime"/trash`) — the mutation is therefore loud but *locks in the defect*,
which is exactly why drift is 3 and not 5.

### 4.5 Severity verdict — CONFIRMED, High (4×3=12)

Impact 4: a destructive operation reaching a root it does not own; recoverable because the
archive is intact. Drift 3: partially pinned, in the wrong direction. Stands.

### 4.6 Double-count check

Not a restatement of `F-CRP-01`/`F-CRP-09`. §2.4's **R8** row records the same
derivation, but `F-CRP-01` scores root *non-coincidence*; `F-CRP-14` scores the
destructive *use*. §7.4's "no divergence observed" correction is legitimate. Clean.

---

## 5. `F-CRP-15` — checkpoint summary drops `artifact_versions` — **CORRECTED**

### 5.1 Anchors

| anchor | quoted text | resolves? |
|---|---|---|
| `mcp/tools/checkpoints.py:85-93` | `def _checkpoint_summary(cp: CheckpointMetadata) -> dict[str, object]:` … `"reason": cp.reason,` | ✅ :85 … :92 inside range |
| `mcp/tools/checkpoints.py:102` | `return _ok(checkpoints=[_checkpoint_summary(c) for c in cps])` | ✅ exact |
| `mcp/tools/checkpoints.py:132` | `return _ok(**_checkpoint_summary(cp))` | ✅ exact |
| `app/runtime.py:253` | `artifact_versions: dict[str, str] \| None = None,` | ✅ exact |
| `app/_graph_exec.py:102-103` | `candidate_refs = get_candidate_refs(state)` / `artifact_versions = dict(candidate_refs)` | ✅ exact |

`:102-103` really is the only derivation:

```
$ grep -rn "artifact_versions" src/film_pipeline/app src/film_pipeline/mcp src/film_pipeline/checkpoints
app/runtime.py:253,267  (parameter pass-through)      app/_graph_exec.py:103,110  (the derivation)
checkpoints/manager.py:30,49  (defaults to {})        mcp/tools/checkpoints.py:149-324  (reads only)
```

### 5.2 Reproduce

Appendix A.12 verbatim:

```
factory accepts artifact_versions: True
summary keys: ['"checkpoint_id": cp.checkpoint_id,', '"project_id": cp.project_id,', '"phase": cp.phase.value,', '"created_at": cp.created_at.isoformat(),', '"reason": cp.reason,']
```

Static reproduce reproduces byte-for-byte. So the *stated defect* is real: the projection
omits the map.

### 5.3 The printed drift proof is **falsified** — executed

Pinned `audit/10:1173-1179`:

> "Mutation scenario: add `"artifact_versions": cp.artifact_versions` to
> `_checkpoint_summary` and no test fails — … nothing asserts the summary's key set."

The grep is accurate (it only finds the string `artifact_versions`), but the conclusion is
wrong: the summary's key set **is** asserted, by an `==` against a literal set that does not
name the field:

```
$ awk 'NR>=45 && NR<=59 {printf "%d|%s\n", NR, $0}' tests/unit/mcp/tools/test_checkpoints.py
45|    listed = asyncio.run(list_checkpoints({"project_id": "proj-cp-1"}))
52|    row = next(c for c in rows if c["checkpoint_id"] == checkpoint_id)
53|    assert set(row) == {
54|        "checkpoint_id",
55|        "project_id",
56|        "phase",
57|        "created_at",
58|        "reason",
59|    }
```

I ran the finding's own mutation against a disposable snapshot:

```
$ # /tmp/v15-mut15: added  "artifact_versions": cp.artifact_versions,  to _checkpoint_summary
$ cd /tmp/v15-mut15 && PYTHONPATH=/tmp/v15-mut15/src .venv/bin/python -m pytest tests/unit/mcp/tools/test_checkpoints.py --no-cov -q
>       assert set(row) == {
E       AssertionError: assert {'artifact_ve...id', 'reason'} == {'checkpoint_...id', 'reason'}
E         Extra items in the left set:
E         'artifact_versions'
tests/unit/mcp/tools/test_checkpoints.py:53: AssertionError
FAILED tests/unit/mcp/tools/test_checkpoints.py::test_create_and_list_checkpoints
```

**The printed §1.6.3(b) proof fails.** Under §1.6.6 that alone would move the finding to a
hypothesis — except that a *different*, valid silent mutation exists, so the seam is real:

* adding a field to `CheckpointMetadata` leaves the summary's hand-written literal and the
  test's expected set unchanged → silent;
* and there is a **second, unpinned projection** the finding never anchors.

### 5.4 Anchor/count defect (2) — the finding undercounts its own seam

```
$ awk 'NR>=132 && NR<=145 {printf "%d|%s\n", NR, $0}' src/film_pipeline/app/services/_browse_ops.py
132|def list_checkpoints(svc: OperatorService, project_id: str | None = None) -> list[dict[str, str]]:
136|    return [
137|        {
138|            "checkpoint_id": checkpoint.checkpoint_id,
139|            "project_id": checkpoint.project_id,
140|            "phase": str(checkpoint.phase.value),
141|            "reason": checkpoint.reason,
142|            "created_at": checkpoint.created_at.isoformat(),
143|        }
144|        for checkpoint in checkpoints
145|    ]
```

The identical 5-key literal, dropped field included. It appears in the finding only inside
the blast radius (`/tmp/audit10-pinned.md:1182`), never as a de-facto owner, and the
reproduce command does not reach it. Its key set is **not** pinned:

```
$ grep -rn "list_checkpoints" tests/unit/app/services/
tests/unit/app/services/test_operator_service.py:180:        checkpoints = service.list_checkpoints("gate-test")
$ awk 'NR>=183 && NR<=184 ...'
183|        assert len(checkpoints) >= 1
184|        assert checkpoints[-1]["phase"] == "constitution"
```

So the honest seam is "**two** hand-listed projections of `CheckpointMetadata`; the MCP one
is pinned by `test_checkpoints.py:53-59`, the operator one is not".

### 5.5 Severity verdict — CORRECTED, Medium (impact 2 × drift 2 = 4)

Keep impact 2 (the operator cannot see the map; no wrong deliverable, no corruption — the
finding's own rationale). Drift drops 3 → **2**: one of the two projections is pinned by an
exact key-set assertion, so the `artifact_versions` omission cannot change silently; only
the `_browse_ops` copy and future model-field additions drift unwatched. 2×2=4 = Medium
(the band is unchanged under §1.5, but the score and the proof are wrong as printed).

### 5.6 Double-count check — disclosure is honest, evidence is borrowed

`F-CRP-15` is **not** a restatement of `F-CRP-04`: `F-CRP-04` owns the *write* authority
(two writers of `artifact_versions`; rollback/invalidation silently no-op for MCP-created
checkpoints), `F-CRP-15` owns the *read* projection. Distinct, and the finding says so
("corroborating `F-CRP-04`; no score is added"). But its printed "existing divergence" is
`F-CRP-04`'s divergence — a shared Appendix A.6 cannot establish a *projection* seam. The
projection seam needs its own mutation proof (model-field addition / `_browse_ops` copy),
which the author must write.

---

## 6. `F-CRP-16` — unobserved `_resume_to_repair` consumer — **STRENGTHENED**

### 6.1 Anchors

| anchor | quoted text | resolves? |
|---|---|---|
| `app/_graph_exec.py:381-393` | `if _has_pending_human_interrupt(snapshot):` / `recovery_state["_revision_note"] = note` / `recovery_state["_resume_to_repair"] = True` / `state = graph.invoke(recovery_state, config)` | ✅ all inside range |
| `app/_graph_exec.py:151-160` | `def _has_pending_human_interrupt(snapshot: Any) -> bool:` | ✅ exact |
| `graph/state_schema.py:203-204` | `_revision_note: str` / `_resume_to_repair: bool` | ✅ exact |
| `graph/nodes/_repair_loop.py:198` | `if state.get("_resume_to_repair"):` | ✅ exact |
| `graph/graph.py:193` | `if state.get("_resume_to_repair"):` | ✅ exact |
| `app/_graph_exec.py:232-240` | `if _approval_stalled(state, active, current_phase):` / `return advance_to_next_phase(rt, dict(active))` | ✅ :232 and :240 |
| `app/_graph_exec.py:400-406` | `rt._record_audit(` / `"resume_failed",` | ✅ inside range |
| `tests/unit/app/test_resume_integrity.py:155-156,192,199,202,213` | the fake-graph assertions | ✅ exact |
| `tests/unit/graph/test_channel_registry.py:222-224` | `_repair_loop.py` allow-list rows | ✅ exact |

**Anchor defect (1) — the mutation range is off by one.** The `if` branch runs
`_repair_loop.py:198-**206**`, not `:198-205`; line 206 is the branch's last statement:

```
$ awk 'NR>=197 && NR<=208 {printf "%d|%s\n", NR, $0}' src/film_pipeline/graph/nodes/_repair_loop.py
197|    revision_update: dict[str, Any] = {}
198|    if state.get("_resume_to_repair"):
199|        from film_pipeline.graph.nodes.approval import request_revision_node
200|        from film_pipeline.graph.state_schema import merge_issues
201|
202|        revision_update = request_revision_node(state)
203|        existing_issues = list(state.get("issues", []) or [])
204|        state = dict(state)
205|        state.update(revision_update)
206|        state["issues"] = merge_issues(existing_issues, revision_update.get("issues", []))
207|
208|    phase = str(state.get("current_phase", ""))
```

Deleting only 198-205 leaves `state["issues"] = merge_issues(existing_issues, …)` referencing
deleted locals. The author's own reproduction instruction is not executable as written.

**Anchor defect (2) — the consumer enumeration is incomplete.** The reproduce line lists
"producer `:391-392`; consumers `graph/graph.py:193`, `_repair_loop.py:198`,
`approval.py:273`". The command's real output has 15 lines and also contains two writers the
finding omits:

```
$ grep -rn "_resume_to_repair\|_revision_note" --include=*.py src/ tests/
src/film_pipeline/app/_graph_exec.py:391:                recovery_state["_revision_note"] = note
src/film_pipeline/app/_graph_exec.py:392:                recovery_state["_resume_to_repair"] = True
src/film_pipeline/graph/nodes/_repair_loop.py:198:    if state.get("_resume_to_repair"):
src/film_pipeline/graph/nodes/_repair_loop.py:242:    result["_resume_to_repair"] = False        <-- omitted
src/film_pipeline/graph/nodes/approval.py:186:            state["_revision_note"] = note     <-- omitted
src/film_pipeline/graph/nodes/approval.py:273:    revision_note = str(state.get("_revision_note", ""))
src/film_pipeline/graph/nodes/approval.py:284:        "_revision_note": "",
src/film_pipeline/graph/graph.py:193:    if state.get("_resume_to_repair"):
src/film_pipeline/graph/state_schema.py:203:    _revision_note: str
src/film_pipeline/graph/state_schema.py:204:    _resume_to_repair: bool
tests/unit/app/test_resume_integrity.py:155,156,192,199,213
```

`_repair_loop.py:242` clears the flag on the repair result — it is part of the contract the
finding says has no shared type. Also `tests/unit/app/test_resume_integrity.py:176-220` is
`:178-221` in the file (def at :178, last assert at :221).

### 6.2 Is the consumer dead code? **No — the brief's premise does not hold**

The finding does **not** claim "no production consumer"; it claims an **unobserved**
consumer. That is accurate and the consumer is live:

```
$ awk 'NR>=118 && NR<=125 {printf "%d|%s\n", NR, $0}' src/film_pipeline/graph/graph.py
124|    builder.add_node("repair", repair_phase_node)
$ awk 'NR>=192 && NR<=198 {printf "%d|%s\n", NR, $0}' src/film_pipeline/graph/graph.py
193|    if state.get("_resume_to_repair"):
194|        return "repair"
```

`graph/graph.py:193-194` routes a `_resume_to_repair=True` input to the `"repair"` node,
which is `repair_phase_node` (`graph/graph.py:124`) — the function containing
`_repair_loop.py:198`. The producer is `app/_graph_exec.py:386-393`, the fallback used when
`request_revision` finds no pending interrupt. The path is reachable end to end in
production. **§1.6.6 does not apply; this stays a finding.**

### 6.3 Drift proof — executed, and it is silent

I removed the whole branch (198-206) in a disposable snapshot and ran the full unit suite:

```
$ cd /tmp/v15-mut16 && PYTHONPATH=/tmp/v15-mut16/src .venv/bin/python -m pytest tests/unit tests/test_smoke.py \
    --no-cov -p no:cacheprovider --junitxml=/tmp/mut16.xml
MUT16 EXIT=0
tests=1872 failures=0 errors=0 skipped=3
```

Baseline for comparison: `tests=1872 failures=0 errors=0 skipped=3`. **The mutation is
completely silent across the entire suite** — the only test that drives this recovery
(`tests/unit/app/test_resume_integrity.py::test_real_graph_recovers_failed_start_and_reaches_approval`)
monkeypatches `repair_phase_node` away (`:202`) and asserts its own double's dict
(`:219 assert reached_repair == [True]`, fed from the input at `:213`). §1.6.3(b) holds —
and by §1.5's own definition ("5 = no test can fail when one site changes; 1 = a test
already pins the agreement") the drift axis is **5**, not 3.

### 6.4 Severity verdict — STRENGTHENED, High (impact 2 × drift 5 = 10)

The finding's impact-1 rationale is internally inconsistent with its own drift proof and
blast radius. It says impact 1 = "cosmetic/internal" because "the failure … is audited as
`resume_failed` and re-raised" — but deleting the branch **does not raise**: the mutation
ran green, the graph completed, and nothing was audited. What actually happens is that
`request_revision_node` is never called, so `add_revision_request` is never recorded, the
revision issues are never merged, and the repair loop runs from the un-revised state — the
exact consequence the Blast radius paragraph describes. That is §1.5 impact **2** (an
operator-visible wrong behavior confined to a last-resort recovery path, recoverable by
re-requesting), at worst 3; either way **2×5=10 or 3×5=15, both High**.

### 6.5 Double-count check

Distinct from `F-CRP-03` (which owns the `approve_phase` payload) and from
`audit/01` F-PHASE-04 (phase-successor table). §6.7's "overlapping but distinct" resolution
is sound; the manual-advance seam is genuinely shared (`app/_graph_exec.py:232-240`), and
the finding cites it rather than claiming it. Clean.

---

## 7. §6.5 / §6.7 collision resolution and its anchors

Checked as instructed against `audit/03` and `audit/11` at their pinned revisions
(§0.2 hashes).

| cited by audit 10 | what is actually there | verdict |
|---|---|---|
| `audit/03:825` — "**Storage root** resolution \| `artifacts/storage.py` \| `STORAGE_ROOT_ENV` declared and read only at `:28`/`:86` … guards `tests/unit/artifacts/test_storage.py:29-78`" (header `audit/10:54`, §6.5 `:1406-1418`, §6.7 `:1425`) | `FILM_PIPELINE_SEARCH_API \| config/runtime_overrides.py:20 \| single (override table)`. The quoted row is at **`audit/03:928`** | ❌ **wrong line** (text right, pointer wrong) |
| `audit/03:462` **F-CFG-08** (header `:55`, §6.7 `:1426`, and `F-CRP-09`'s D7 `:844-846`) | line 462 is the first line of **F-CFG-07**'s drift proof. F-CFG-08's heading is **`audit/03:484`** | ❌ **wrong line** |
| `owner app/_persistence at audit/03:492` (§6.7 `:1426`, D7 `:846`) | `:492` is the `graph/services.py:31` reader row. F-CFG-08's "Candidate owner module: `app/_persistence`" is **`audit/03:514`** | ❌ **wrong line** |
| `audit/11:309` (three-way owner collision) | the "Open reconciliation item (added after verification) — this concern already has three candidate owners" paragraph | ✅ **correct** |
| `audit/01:235,258` **F-PHASE-04** (header `:56`, §6.7 `:1427`) | `:235` is inside F-PHASE-02; `:258` is F-PHASE-03's candidate owner. F-PHASE-04's heading is **`audit/01:262`** | ❌ **wrong lines** (not in my brief, reported for completeness) |
| `audit/11:309`'s pointer *into this file* (`audit/10:817-850`) | the housekeeping note at `/tmp/audit10-pinned.md:1426` is fair: in the pinned revision `F-CRP-09` starts at `:834`, and `audit/11`'s pointer cites `resolve_persistence()` by line | ✅ the note is correct; the stale pointer belongs to audit 11 |

**Does the resolution avoid assigning one concern to two owners?** Substantively, mostly
yes; the citations are broken. Specifically:

* **R1 stays put.** `audit/03:928` single-owns storage-root *resolution*; `runtime_persistence`
  owns only the R2–R8 *composition*. That is a coherent compose-vs-resolve split and no
  existing guard is reassigned. But §6.2's N bullet declares `RootLayout` with a
  `storage_root` field (`/tmp/audit10-pinned.md:1341-1344`) and §6.3's contract has
  `resolve_roots(policy) -> RootLayout` (`:1365`), while §6.5's prose assigns only "the
  composition" to the module (`:1413-1419`) and says R1 is untouched — the boundary must
  state explicitly that `RootLayout.storage_root` **copies R1's answer** and is not a second
  resolution site, or the collision simply moves one level up.
* **F-CRP-14 splits a concern without saying so.** §6.5 (`:1403`) assigns the trash root to
  `RootLayout` but leaves `app/safety.py:75` — `is_safe_to_delete`'s `persist_root()`
  reference — unmentioned (§4.3). The row must name the predicate that stays with `safety`
  and the value that moves.
* **`app.bootstrap` / `runtime_persistence.policy` / `app/_persistence`**: the three-way
  collision is correctly escalated once (audit 11) rather than triplicated. One concern,
  three candidate owners, resolution deferred to `03-target-architecture.md` — acceptable
  and consistently stated.

---

## 8. What the author should fix

1. **`F-CRP-12` — re-score to High (3×5=15).** The refusal consequence does not fire
   through `cli.run:main`, `mcp.server:main`, `app.product_gate:main` or `langgraph.json`
   (the MCP server fails earlier, via `logs/`; the LangGraph target never opens the storage
   root), the effect is reversible by deleting one directory, and the suite never hits it.
   Keep the drift proof; keep the durable-side-effect claim. If a real-entry-point
   single-process refusal is demonstrated, impact 4 → 20/Critical is available.
2. **`F-CRP-12` — delete or re-anchor** `src/film_pipeline/app/runtime.py:62` /
   "in `load_persisted_projects`" in the blast radius. Correct chain:
   `app/runtime.py:75-77` → `graph/services.py:49` → `artifacts/store.py:61` →
   `artifacts/storage.py:160`.
3. **Record the missing instance of the same seam** (outside the five, but the MCP entry
   point's actual failure): `mcp/server.py:251 configure_logging(configured_runtime_root())`
   → `app/logging_setup.py:90-92` mkdirs `<root>/logs` before `StudioRuntime.__post_init__`
   calls `ensure_storage_root`, so `mcp.server:main` refuses a fresh root with or without
   `graph.graph`, and `tests/unit/test_entrypoints.py:29-43` cannot see it because
   `configure_logging` is monkeypatched to a `MagicMock`.
4. **`F-CRP-13` — fix the absence proof.** `tests/unit/artifacts/test_storage_guards.py:63`
   deletes `PERSIST_STATE`; `RUNTIME_ROOT` is deleted at `:62`. "No test covers the
   combination" is false: `tests/conftest.py:17-31` + `:98` make it the suite default. The
   defensible wording is "no test asserts the invariant" — supported by my executed
   mutation (gating the branch behind the policy fails exactly one test, incidentally, out
   of 1872).
5. **`F-CRP-13` / `F-CRP-09` — state the sub-case relationship.** `F-CRP-09` already lists
   `src/film_pipeline/app/runtime.py:58-69` as an owner; `F-CRP-13` re-scores the same
   lines. Say in both blocks that `F-CRP-13` is the root-selection sub-case of P8, so one
   site does not read as two independent seams with two bands.
6. **`F-CRP-14` — add `app/safety.py:75`** (`if _is_under(resolved, persist_root()):`) to
   the owner list and to §6.5's row (`:1403`), and say that
   `is_safe_to_delete`/`require_safe_to_delete` stays with `app/safety` while only the trash
   *value* moves to `RootLayout`.
7. **`F-CRP-15` — rewrite the drift proof; it is falsified as printed.**
   `tests/unit/mcp/tools/test_checkpoints.py:53-59` asserts `set(row) == {5 keys}`, so
   adding `artifact_versions` to `_checkpoint_summary` fails the test (executed). Supply the
   valid silent mutation instead (add a field to `CheckpointMetadata`; or the un-pinned
   `_browse_ops` copy) and re-score drift 3 → 2 (2×2=4, Medium).
8. **`F-CRP-15` — promote `src/film_pipeline/app/services/_browse_ops.py:132-145` from
   blast radius to de-facto owner** and extend the reproduce command to both projections;
   there are two hand-listed serializations, and only one is key-set-pinned.
9. **`F-CRP-16` — fix the mutation range to `_repair_loop.py:198-206`** (the printed
   198-205 leaves a `NameError`), add `_repair_loop.py:242` and `approval.py:186` to the
   consumer list, and correct the test range to `tests/unit/app/test_resume_integrity.py:178-221`.
10. **`F-CRP-16` — re-score to High (impact 2 × drift 5 = 10).** The consumer is live
    (`graph/graph.py:124`, routed at `:193-194`), so it is not dead code and §1.6.6 does not
    apply; but the executed mutation leaves all 1872 tests green, which is drift 5 by §1.5,
    and the finding's impact-1 rationale ("audited as `resume_failed` and re-raised")
    describes a failure the mutation does not produce.
11. **Re-anchor the collision citations.** `audit/03:825` → **`audit/03:928`**;
    `audit/03:462` (F-CFG-08) → **`audit/03:484`**; `audit/03:492` (owner) →
    **`audit/03:514`**; `audit/01:235,258` (F-PHASE-04) → **`audit/01:262`**. These appear
    in the header (`:54-56`), §6.5 (`:1406-1418`), §6.7 (`:1425-1427`) and `F-CRP-09`'s D7
    (`:844-846`). Cite by finding id **and** by text, since both sibling audits are also
    being edited.
12. **Note the concurrency.** `audit/10` grew 1718 → 1826 lines while this verification ran,
    and `audit/03`/`audit/01` moved too. Line numbers in this report are pinned to the
    hashes in §0.2.

---

## 9. Command log (evidence-bearing commands and real output)

```bash
# snapshot + identity
mkdir -p /tmp/v15 && git archive fb85baa0e6b769b709791a96a89980089304bf13 | tar -x -C /tmp/v15
cd /tmp/v15 && git rev-parse HEAD          # fatal: not a git repository (exit 128)
git -C ${REPO_ROOT} rev-parse HEAD
#   fb85baa0e6b769b709791a96a89980089304bf13
git status --porcelain                     # (empty)

# audit revision pin
cp docs/modular-architecture/audit/10-...md /tmp/audit10-pinned.md
shasum -a 256 /tmp/audit10-pinned.md       # 2a2d05f47819ddf6d5cf4462bc37522e9eb60756bfab01ca13e2e9a8d86ec9b9
wc -l /tmp/audit10-pinned.md               # 1826

# F-CRP-12 / 13 / 14 / 15 appendices, verbatim
PYTHONPATH=/tmp/v15/src UV_CACHE_DIR=$PWD/.uv-cache uv run python /tmp/v15probes/a9_fcrp12.py
#   after import, children of storage root: ['checkpoints']
#   app FAILED: StorageRootError: Refusing to use /var/folders/.../T/m1_lp...
PYTHONPATH=/tmp/v15/src UV_CACHE_DIR=$PWD/.uv-cache uv run python /tmp/v15probes/a10_a11.py
#   [A] use_persistent_runtime() = False ... [A] durable project.json written? = True
#   [A] durable storage marker? = True
#   [B] runtime root in use = .../explicit-run-root
#   [B] safety.persist_root() = /private/var/folders/.../T/m23_h788e32j
#   [B] archive created under = ['.../trash/project-p9-20260925-140052-533618-p9']
#   [B] archive inside runtime root? = False
PYTHONPATH=/tmp/v15/src UV_CACHE_DIR=$PWD/.uv-cache uv run python /tmp/v15probes/a12.py
#   factory accepts artifact_versions: True
#   summary keys: ['"checkpoint_id": ...', '"reason": cp.reason,']

# F-CRP-12 entry-point attack
PYTHONPATH=/tmp/v15/src UV_CACHE_DIR=$PWD/.uv-cache uv run python /tmp/v15probes/mcp_order_noroot.py
#   [N] storage children after configure_logging: ['logs']
#   [N] graph.graph imported by logging?  False
#   [N] StudioRuntime FAILED: StorageRootError ...
#   [N] graph.graph imported after runtime? False
PYTHONPATH=/tmp/v15/src UV_CACHE_DIR=$PWD/.uv-cache uv run python /tmp/v15probes/mcp_order_explicitroot.py
#   [E] explicit root children after configure_logging: ['logs']
#   [E] StudioRuntime FAILED: StorageRootError ...
#   [E] graph.graph imported? False

# static reproduce commands, verbatim
grep -rn "graph: CompiledStateGraph = build_graph()\|checkpoint_dir.mkdir" --include=*.py src/
grep -n "FILM_PIPELINE_RUNTIME_ROOT\|use_persistent_runtime" src/film_pipeline/app/runtime.py
grep -rn "persist_root()" --include=*.py src/film_pipeline/app/
grep -n "_checkpoint_summary\|artifact_versions" src/film_pipeline/mcp/tools/checkpoints.py
grep -rn "_resume_to_repair\|_revision_note" --include=*.py src/ tests/
grep -rn "_repair_loop" tests/
grep -rn "ensure_storage_root" src/
grep -rn "artifact_versions" src/film_pipeline/app src/film_pipeline/mcp src/film_pipeline/checkpoints
grep -rn "FILM_PIPELINE_RUNTIME_ROOT" tests/
grep -rn "artifact_versions" tests/unit/mcp/tools/test_checkpoints.py

# mutation experiments (disposable copies under /tmp only)
cd /tmp/v15      && PYTHONPATH=/tmp/v15/src      .venv/bin/python -m pytest tests/unit tests/test_smoke.py \
    --no-cov -p no:cacheprovider --junitxml=/tmp/base.xml   # EXIT=0  tests=1872 failures=0 errors=0 skipped=3
cd /tmp/v15-mut16 && PYTHONPATH=... .venv/bin/python -m pytest ... --junitxml=/tmp/mut16.xml
#   removed _repair_loop.py:198-206  ->  EXIT=0  tests=1872 failures=0 errors=0 skipped=3   (silent)
cd /tmp/v15-mut13 && PYTHONPATH=... .venv/bin/python -m pytest ... --junitxml=/tmp/mut13.xml
#   gated RUNTIME_ROOT branch behind use_persistent_runtime()  -> EXIT=1  failures=1
#   FAIL: tests.unit.artifacts.test_storage_guards.TestNoSilentAdoption test_runtime_ignores_legacy_cwd_projects
cd /tmp/v15-mut15 && PYTHONPATH=... .venv/bin/python -m pytest tests/unit/mcp/tools/test_checkpoints.py --no-cov -q
#   added "artifact_versions" to _checkpoint_summary  ->  FAILED test_create_and_list_checkpoints
#   AssertionError at tests/unit/mcp/tools/test_checkpoints.py:53

# header band-mix script, verbatim (path substituted to the pinned copy)
.venv/bin/python - <<'PY' ... PY
#   16 findings: {'Critical': 6, 'High': 6, 'Medium': 3, 'Low': 1}

# collision anchors
awk 'NR>=823 && NR<=827' /tmp/audit03-pinned.md     # :825 = FILM_PIPELINE_SEARCH_API row
grep -n "Storage root\*\* resolution" /tmp/audit03-pinned.md   # :928
awk 'NR>=460 && NR<=464' /tmp/audit03-pinned.md     # :462 = F-CFG-07 drift proof
grep -n "^### F-CFG-08" /tmp/audit03-pinned.md      # :484
awk 'NR>=505 && NR<=515' /tmp/audit03-pinned.md     # candidate owner at :514
awk 'NR>=307 && NR<=311' /tmp/audit11-pinned.md     # :309 = three-owner item (correct)
grep -n "^### F-PHASE-04" /tmp/audit01-pinned.md    # :262
```
