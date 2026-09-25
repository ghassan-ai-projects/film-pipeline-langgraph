# Adversarial architecture review — `03-target-architecture.md` and `05-enforcement-and-guard-tests.md`

Reviewer role: adversarial architecture + evidence adversary (bar B8).
Repo: `${REPO_ROOT}`, branch `modular-app`,
HEAD `fb85baa0e6b769b709791a96a89980089304bf13` (`git rev-parse HEAD`).
Every finding below is a measurement; every command is re-runnable.

---

## 0. Method and version pinning

### 0.1 Documents read, pinned by line count + mtime + sha256 (16-hex prefix)

| Document | Lines | mtime | sha256[:16] |
|---|---|---|---|
| `docs/modular-architecture/00-methodology-and-quality-bar.md` | 218 | 2026-09-25T14:27:35 | `6fc1ec700e9b8c06` |
| `docs/modular-architecture/01-ownership-map.md` | 371 | 2026-09-25T15:21:38 | `d59b931bcb217825` |
| `docs/modular-architecture/02-duplication-ledger.md` | 997 | 2026-09-25T15:21:46 | `cd1c95034acaf709` |
| `docs/modular-architecture/03-target-architecture.md` | 1918 | 2026-09-25T15:21:55 | `600b780f5227a451` |
| `docs/modular-architecture/04-extraction-roadmap.md` | 1339 | 2026-09-25T15:22:09 | `e12009b380cb5282` |
| `docs/modular-architecture/05-enforcement-and-guard-tests.md` | 2334 | 2026-09-25T15:23:24 | `afd0059755e16a1e` |
| `docs/modular-architecture/enola-architecture-facts.md` | 196 | 2026-09-25T14:39:30 | `e8575512539ea775` |
| `documentation/architecture-blueprint.md` | 2420 | — | (prior-art source of truth) |
| `AGENTS.md` (repo root) | 74 | — | — |

Pinning command:

```bash
cd docs/modular-architecture && for f in 00-*.md 01-*.md 02-*.md 03-*.md 04-*.md 05-*.md enola-architecture-facts.md; do
  printf "%-45s %6s lines  %s\n" "$f" "$(wc -l < $f)" "$(stat -f '%Sm' -t '%Y-%m-%dT%H:%M:%S' $f)"; done
python3 -c "import hashlib;[print(hashlib.sha256(open(f,'rb').read()).hexdigest()[:16],f) for f in [...]]"
```

### 0.2 Python used

Both forms the task allows; measurements are from the repo venv.

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run python <script>     # AST/import/graph measurements
./.venv/bin/python -c "import film_pipeline.graph.graph"  # import-side-effect probe
```

### 0.3 Scratch location

All scripts live in `/tmp/adv/` (`imports.py`, `assign.py`, `matrix.py`). Nothing
under `src/`, `tests/`, or the repo root was written.

---

## 1. OBJECTIONS

### O-01 — **Blocking** — the guard suite's own inputs live under `docs/`, which is gitignored and CI-exempt

- **Exact claim attacked.** `05:244-250`: "`architecture.py` is a declared **leaf** … The declaration **must live under `src/`**. `docs/` is gitignored (`.gitignore:2`) and CI-exempt (`.github/workflows/ci.yml:10-11`), so a manifest there is unreviewable as a diff and untriggered by CI."
- **Contradicting code.** `05:1856-1858` (`test_guard_registry.py`) sets `_LEDGER = _REPO / "docs" / "modular-architecture" / "02-duplication-ledger.md"` and `05:1894` does `_LEDGER.read_text()` with no existence guard. `04:269` (P0 acceptance) names `test_matrix_matches_03_4_3`, i.e. a test that must read `03-target-architecture.md` §4.3.
- **Evidence.**
  ```
  $ git check-ignore -v docs/modular-architecture/02-duplication-ledger.md
  .gitignore:2:docs/	docs/modular-architecture/02-duplication-ledger.md
  $ git ls-files docs | wc -l
  0
  $ sed -n '10,13p' .github/workflows/ci.yml
        paths-ignore:
          - "**/*.md"
          - "docs/**"
  ```
- **Why it matters.** On a fresh CI checkout the file does not exist; `read_text()` raises `FileNotFoundError`, which pytest reports as an *error*, so `make ci-check` cannot be green. The mechanism's central selling point ("zero CI-YAML change", `05:80`) is false as written.
- **Smallest fix.** Move the `L-NN` id list and the §4.3 matrix rows into the tracked `src/film_pipeline/architecture.py` (or a tracked `tests/architecture/_ledger_ids.py` generated from the ledger) and have the ledger *reference* them, not the reverse.

### O-02 — **Blocking** — three documents specify three different forbidden-edge sets, and the guard hardcodes the count it claims to derive

- **Exact claims attacked.** `03:1655-1657`: "the HEAD forbidden-edge count is **10** … The count is **derived** by the guard from `ModuleContract.may_import` and the observed edge set — never written into a document." `05:1135-1137`: "A guard that hardcodes `8` is the same failure mode as the prose law it replaces. So this design encodes no edge count … every count is derived by the test at run time."
- **Contradicting code.** `05:1175`: `assert len(edges) == 53, f"cross-package edge set changed: {len(edges)}"`; `04:269`: acceptance = "derived forbidden count = **10**"; `05:1176-1185` derives the forbidden set with `s not in COMPOSITION_ROOTS | UNRESTRICTED_PACKAGES | SHIPPED_NOT_PRODUCTION and t not in CONTRACT_LAYERS and not (ARTIFACTS_FACADE_IS_CONTRACT and t == "artifacts")`.
- **Evidence.** Re-ran the 05 §3.9 scope over the real 53-edge set:
  ```
  $ UV_CACHE_DIR="$PWD/.uv-cache" uv run python  # /tmp/adv/forbidden.py
  total edges 53
  guard's derived forbidden set under 05 §3.9 scope ( 4 ):
     agents -> providers
     config -> providers
     generation -> providers
     post -> validation
  ```
  `03:1154-1157` explicitly declares three of those four **allowed**: "the `agents → providers`, `generation → providers`, `generation → artifacts`, `post → validation` and `testing → *` edges that the audit's greps called violations are **allowed** by §4.3". The `mcp → *` edges that make up 9 of 03's 10 are excluded by the guard because `UNRESTRICTED_PACKAGES = frozenset({"graph","mcp"})` (`05:373`).
- **Why it matters.** The signature artefact of D12 ("the count is a *result*, not a source", `03:1665-1666`) is three different numbers: 10 (03/04) and 4 (05) for the same tree. An author cannot know what `make arch-check` will demand, and the roadmap's P0 acceptance can never be satisfied by the guard as printed.
- **Smallest fix.** Delete the `assert len(edges) == 53`; replace `UNRESTRICTED_PACKAGES`/`ARTIFACTS_FACADE_IS_CONTRACT` in the guard with reads of `CONTRACT.may_import` so one authority (the manifest) produces one count.

### O-03 — **Blocking** — the O7 private-import guard is arithmetically unsatisfiable against its own ledger, and hardcodes the totals it calls derived

- **Exact claim attacked.** `05:941-943`: "The guard **enumerates all 107 + 3 from the AST** — never from a three-line offender list — and asserts the *derived* totals, so a fourth private-symbol site or a 108th private-module site fails without anyone editing a number."
- **Contradicting code.** `05:999-1004`:
  ```python
  assert len(modules) == 107, f"private-module sites changed: {len(modules)}"
  assert by_module["film_pipeline.schemas._base"] == 106
  assert by_module["film_pipeline.app._persistence"] == 1
  assert len(symbols) == 3, f"private-symbol sites changed: {symbols}"
  assert len(modules) + len(symbols) == len(EXEMPT) + len(_SYMBOL_EXEMPT)
  ```
  with `EXEMPT = {row.subject for row in PRIVATE_MODULE_EXEMPTIONS}` (`05:956`) and the ledger's `PRIVATE_MODULE_EXEMPTIONS` holding **2 per-module rows** (`05:1526-1543`).
- **Evidence.** The last assertion requires `107 + 3 == 2 + len(_SYMBOL_EXEMPT)`, i.e. `len(_SYMBOL_EXEMPT) == 108`, while §3.7 and §5.2 declare exactly **3** private-symbol sites. Site counts (110) are compared to row counts (5). The four preceding assertions are literal integers, contradicting the docstring one line above ("not written into the test as a licence").
- **Why it matters.** The guard that is supposed to prove O7 cannot pass at W0, and the "derived, never edited" guarantee is false: the O7 totals (107/106/1/3) and the edge total (53) are maintained by hand across `tests/architecture/`.
- **Smallest fix.** Compare like with like — `len(EXEMPT)` must count *sites* (a per-site ledger) or the assertion must sum `by_module` values against per-module rows — and derive the four totals from `_private_sites()` where possible.

### O-04 — **Major** — L1 (layer direction) is declared but never read by any guard

- **Exact claim attacked.** `03:1096-1098` maps L1/L2 to `test_imports_stay_within_declared_edges`, `test_declared_edges_are_real`, `test_declared_module_graph_is_acyclic`; `05:1144` declares `MODULE_LAYERS: Final[Mapping[str, int]]` as "the matrix's SCOPE, which is the contract".
- **Evidence.** `MODULE_LAYERS` occurs exactly twice in 05 — its definition (`05:1144`) and prose (`05:1192`). The three edge guards (`05:1226-1246`, `05:1249-1266`) read only `may_import`, `package_edges()` and `CYCLE_EXEMPTIONS`; none reads `MODULE_LAYERS`. Acyclicity alone permits any DAG, including a same-layer or upward `may_import` (e.g. `post → governance`, L7→L8) that forms no cycle.
- **Why it matters.** L1 is the rule that makes the graph "acyclic by construction" (`03:1073-1078`). The construction proof is sound; the machine check of it does not exist. A same-layer edge added to a package `CONTRACT` ships green.
- **Smallest fix.** Add `test_declared_edges_go_strictly_down_one_layer()` iterating `may_import` against `MODULE_LAYERS`.

### O-05 — **Major** — `public_api` is write-only metadata; consumers bypass B2 through public submodules

- **Exact claim attacked.** `03:1851` (B2): "`ModuleContract.public_api` … + `test_public_api_names_exist`"; `05:260`: "every name must exist in the package namespace".
- **Evidence.** `05:1083-1096` is the whole `public_api` guard: `missing = [name for name in contract.public_api if not hasattr(module, name)]` plus `assert CONTRACTS[package].public_api`. Nothing compares cross-package imports to `public_api`. And `05:425-431` admits the example's own contract omits the real gateway: "`public_api` omits `ProjectStorage` on purpose. `hasattr(artifacts, "ProjectStorage")` is **False**". Real cross-package imports of names absent from `05:406-413`:
  ```
  $ grep -rn "artifacts\.\(project_storage\|store\|registry\|storage\)" src/ --include=*.py | grep -v "^src/film_pipeline/artifacts/"
  src/film_pipeline/app/_persistence.py:20:from film_pipeline.artifacts.project_storage import (
  src/film_pipeline/app/_graph_exec.py:23:from film_pipeline.artifacts.project_storage import graph_state_location
  src/film_pipeline/graph/graph.py:17:from film_pipeline.artifacts.storage import default_checkpoints_root
  src/film_pipeline/app/runtime.py:25:from film_pipeline.artifacts.storage import default_runtime_root, resolve_storage_root
  src/film_pipeline/mcp/tools/_profile_change.py:20:from film_pipeline.artifacts.registry import sanitize_artifact_id
  src/film_pipeline/generation/.../frame_sidecar.py:7:from film_pipeline.artifacts.project_storage import ProjectStorage
  ```
  `03:551-557` (storage's declared contract) also omits `default_checkpoints_root`, `default_runtime_root`, `graph_state_location`, `sanitize_artifact_id`.
- **Why it matters.** L3 forbids *private* reaches but not reaching arbitrary public submodules, so the declared contract is descriptive, not authoritative — the O8 class it claims to close. The target's own storage contract is missing four names that consumers import today and that the target still needs (`orchestration` gets `default_checkpoints_root` from `storage`, per O-06).
- **Smallest fix.** Add `test_cross_package_imports_use_the_declared_public_api` (with an exemption ledger seeded from today's violations), and add the four missing names to `03:551-557`.

### O-06 — **Major** — §5 names `orchestration` and `projects` as checkpoint-metadata consumers; §4.3 forbids both imports

- **Exact claim attacked.** `03:1173`: "**Checkpoint metadata** … Read-only consumers: `operations`, `studio`, `orchestration` (refs only), `projects` (discovered projects)".
- **Evidence.** Parsing the §4.3 matrix (`/tmp/adv/matrix.py`) yields:
  ```
  orchestration -> checkpoints: False
  projects      -> checkpoints: False
  operations -> checkpoints: True
  studio     -> checkpoints: True
  ```
  `03:1058` is the orchestration row (no `cp`), `03:1050-1051` the projects/checkpoints rows (neither has `cp`); `03:658` lists checkpoints' inbound as "`operations`, `studio`, `devharness`". `projects` and `checkpoints` are both L4, so `projects → checkpoints` is also barred by L1 (`03:955-957`).
- **Why it matters.** Either §5 is wrong about two named consumers, or the matrix forbids necessary edges for the two modules the task flagged. The real system makes it worse: `orchestration` builds and owns the LangGraph checkpoint DB itself —
  ```
  $ sed -n '41,51p' src/film_pipeline/graph/graph.py
  def _default_checkpointer(runtime_root: Path | None = None)...
      checkpoint_dir = runtime_root / "checkpoints" if runtime_root is not None else default_checkpoints_root()
      checkpoint_db = checkpoint_dir / "checkpoints.sqlite"
      checkpoint_dir.mkdir(parents=True, exist_ok=True)
  ```
  — so the target has two checkpoint mechanisms (`checkpoints`' JSONL lifecycle vs orchestration's SQLite saver) and no declared edge between them.
- **Smallest fix.** Either add `orchestration → checkpoints` / `projects → checkpoints` (re-layer `checkpoints` below L4 or move `default_checkpoints_root`'s contract into `checkpoints`) or correct §5 and state explicitly that the LangGraph checkpointer is not the `checkpoints` module's concern.

### O-07 — **Major** — D10/L8 "no unrestricted modules" is true only by redefinition

- **Exact claim attacked.** `03:984-987` (L8): "The target law has **no unrestricted modules**"; `03:1596`: "Encode no unrestricted modules in the **target** law".
- **Evidence.** Parsed matrix out-degrees: `studio` 18 of the other 19 production modules, `operations` 16. `03:1129` (Composition roots): "**May import everything**". `03:916` (studio): "**Allowed outbound.** every module L0–L11." The enforcement ships a first-class unrestricted flag — `05:300` `unrestricted_imports: bool = False`, `05:373` `UNRESTRICTED_PACKAGES = frozenset({"graph", "mcp"})` — and `05:1228-1229` `if contract.unrestricted_imports: return`, i.e. the mechanism's own escape hatch.
- **Why it matters.** A module that enumerates all 18 targets and one flagged `unrestricted_imports=True` are behaviourally identical under every guard. L8's ban is a naming convention, not a property; `studio` is an unrestricted composition root under a new name, exactly the concern the task names.
- **Smallest fix.** State L8 as "no module is *coarsely* exempt; every module's outbound set is finite and declared", and delete `UNRESTRICTED_PACKAGES`/`unrestricted_imports` from the target manifest (keep them only as W0 pre-images with a removal wave).

### O-08 — **Major** — `budget`'s own abandon trigger is half-unsatisfiable under the same document's matrix

- **Exact claim attacked.** `03:1764-1767`: "The module survives only if `record_spend` has ≥2 call sites (generation + post/assembly) or the cap gates ≥2 domains."
- **Evidence.**
  ```
  $ grep -rn "record_spend\|SpendRecord" src/ | grep -v __pycache__
  src/film_pipeline/schemas/budget.py:23:class SpendRecord(MutableSchemaBase):
  src/film_pipeline/schemas/__init__.py:49:from film_pipeline.schemas.budget import BudgetState, CostEstimate, SpendRecord
  src/film_pipeline/schemas/__init__.py:252:    "SpendRecord",
  ```
  → **0** `record_spend` call sites. `post → budget` is forbidden by the matrix (post row = `fs,sc,st,va`, `03:1056`) and `03:780` / `03:696-699` do not list `budget`. `D5` only ever names `generation` as the caller: `03:1463-1464` "`generation` calls `authorize_spend` before dispatch and `record_spend` after completion".
- **Why it matters.** The trigger that is supposed to prove `budget` is not over-modularization cannot be evaluated as written — the named second caller is architecturally impossible. The module survives only on the unmeasured second disjunct.
- **Smallest fix.** Rewrite the trigger to the measurable disjunct ("`authorize_spend` is called from ≥2 modules" or "the cap gates generation *and* governance"), and drop the `post/assembly` parenthetical.

### O-09 — **Major** — `projects`' merge trigger cannot be executed, because "merge into `studio`" violates L6

- **Exact claim attacked.** `03:1768-1769`: "`projects` — if after W10 the active pointer has exactly one writer and no second consumer beyond `mcp.resolve`, merge into `studio`."
- **Evidence.** `03:977-979` (L6): "Only `studio` constructs the object graph … no module reads another's context variable or global"; `03:917` (studio inbound): "**Allowed inbound.** `mcp`? **No** — … nothing imports `studio`." The active-pointer writer in the target is `operations` (L10), below `studio` (L12); it cannot import `studio`. At HEAD the pointer already has multiple writers:
  ```
  $ grep -rn "set_active\|active_project_id" src/ --include=*.py | grep -v __pycache__ | wc -l   # 70
  src/film_pipeline/app/runtime.py:204:    def set_active(self, project_id: str) -> None:
  src/film_pipeline/app/services/operator.py:155,199,213,321,335: self.runtime.set_active(...)
  src/film_pipeline/mcp/tools/projects.py:144,233: rt.set_active(project_id)
  ```
- **Why it matters.** A falsifiability claim whose prescribed action is forbidden by the design's own law is not falsifiable: even if the condition were met, the trigger cannot be carried out, so the "merge" branch is decorative.
- **Smallest fix.** State the trigger as "merge into `operations`" (the writer's own layer) or delete the merge clause and justify `projects` on the two-writer/two-consumer measurement.

### O-10 — **Major** — `budget → config` is forbidden, but the cap lives in config; "one cap derivation" is unsupported

- **Exact claim attacked.** `03:694` (budget responsibility): "resolves the project cap once"; `03:1478` (D5 consequences): "One cap derivation; one refusal path".
- **Evidence.** Cap representations in `src/`:
  ```
  src/film_pipeline/schemas/budget.py:39:    cap_usd: float = Field(default=0.0, ge=0)
  src/film_pipeline/schemas/project.py:43:    budget_cap_usd: float | None = Field(default=None, ge=0, ...)
  src/film_pipeline/schemas/constraints.py:93:    budget_cap_usd: float | None = Field(...)
  src/film_pipeline/config/validator.py:55:    cap: float = float(budget.get("project_cap_usd", 0))
  src/film_pipeline/graph/nodes/_context.py:424:        for key in ("project_cap_usd", "max_total_usd"):
  src/film_pipeline/mcp/tools/planning.py:22:        cap = float(cast(float, args.get("cap_usd", 100.0)))
  ```
  `budget`'s allowed outbound is `filmspec, schemas, storage` (`03:707`); `budget → config` is absent from the matrix. The profile cap (`profiles/base.studio.yaml:33 budget:`) is reachable only through `config`.
- **Why it matters.** Either the cap is injected by `studio` at composition time — which makes `studio`, not `budget`, the N/I owner of the cap value, contradicting `03:703-704` — or `budget` reads `ProjectRecord.budget_cap_usd`, which is a *different* value from the profile cap, so the duplication survives under a new owner. Neither yields "one cap derivation".
- **Smallest fix.** Declare the cap's single source explicitly (project record vs resolved config) and either add the edge (`budget → config`) or state that `studio` resolves it and passes the value, moving N out of `budget`.

### O-11 — **Major** — the W1 tightening plan removes an edge 03 declares allowed

- **Exact claim attacked.** `05:1269-1271`: "wave-1 tightening (`agents` dropping `providers`, `config` dropping `providers`) actually has to land rather than being announced."
- **Evidence.** `03:685` (agents allowed outbound): "`filmspec`, `schemas`, `providers`"; the §4.3 agents row contains `pv`; `03:1154-1157` lists `agents → providers` among the edges that are "**allowed** by §4.3". Current reality is `agents -> providers 4` sites (AST sweep).
- **Why it matters.** 05's W1 work item would delete a legitimate, measured, design-approved edge and red `test_imports_stay_within_declared_edges` until 4 real call sites are refactored. This is either a second design (agents must not import providers) stated nowhere in 03, or a copy-paste of the audit's over-count that 03 explicitly refuted.
- **Smallest fix.** Delete `agents` from 05's W1 tightening list; keep only `config` dropping `providers`.

### O-12 — **Major** — the `config → providers` migration covers only one of its two live sites

- **Exact claim attacked.** `03:1140`: "1. `config → providers` (target `config` may import only `filmspec`, `schemas`)"; `03:1216`: "the credential check at `profile_resolver.py:202-206` moves to `providers.required_credentials`, called by `studio`."
- **Evidence.** Two sites, not one:
  ```
  $ grep -n "from film_pipeline.providers" src/film_pipeline/config/profile_resolver.py
  179:    from film_pipeline.providers.factory import build_provider_adapter
  204:    from film_pipeline.providers.credentials import _env_var_for, is_configured
  ```
  `:179` is inside `register_project_providers`, which is live on three call paths:
  ```
  $ grep -rn "register_project_providers" src/ --include=*.py
  src/film_pipeline/app/services/operator.py:147
  src/film_pipeline/mcp/tools/_profile_change.py:129
  src/film_pipeline/mcp/tools/projects.py:192
  ```
- **Why it matters.** The one non-MCP forbidden edge does not disappear by moving the credential check; the adapter-factory call is a separate, non-credential `config → providers` dependency (`03:487-490` says config "does not resolve provider credentials" but says nothing about building adapters). W1's "law truth" claim (`05:1554`) is therefore not deliverable as scoped.
- **Smallest fix.** Move `register_project_providers` to `operations`/`studio` and add it to W1's file list, or add the edge to the matrix with a reason.

### O-13 — **Major** — §8's persistence-divergence row names two sites that agree; the real divergence is elsewhere

- **Exact claim attacked.** `03:1732`: "Two formulas currently disagree (`graph/graph.py:43` vs `app/_persistence.py:51`), which means the same env combination can mean 'persist' in one path and 'ephemeral' in another (F-CRP-09)."
- **Evidence.** Both formulas are `PERSIST_STATE ∧ ¬NO_PERSIST`:
  ```
  src/film_pipeline/graph/graph.py:43: if os.getenv("FILM_PIPELINE_NO_PERSIST") or not os.getenv("FILM_PIPELINE_PERSIST_STATE"):
  src/film_pipeline/app/_persistence.py:51-52: return bool(os.getenv("FILM_PIPELINE_PERSIST_STATE")) and not bool(os.getenv("FILM_PIPELINE_NO_PERSIST"))
  ```
  `not(A or not B) == (B and not A)`. The genuinely divergent sites are `graph/services.py:31,48` (`NO_PERSIST` only), `app/logging_setup.py:80`, `cli/run.py:226`, with `mcp/server.py:243-244` forcing `PERSIST_STATE=1`. `05:787-789` names `graph/services.py:31` correctly; 03 does not.
- **Why it matters.** The B7 row "Explicitly broken (behaviour), documented" points a verifier at a non-divergence; the W6 fix and its test ("a test asserts every consumer reports the same mode") would be aimed at the wrong pair.
- **Smallest fix.** Replace the cited pair with `graph/graph.py:43` vs `graph/services.py:31,48` in `03:1732`.

### O-14 — **Major** — §8 omits at least three persisted-representation changes, so single-`git revert` (B5/§9.7-iii) is unproven

- **Exact claim attacked.** `03:1719-1720`: "**Nothing breaks silently**: every 'broken' row names the wave that ships it"; `03:1826-1829` (§9.7-iii): abandon if an extraction "changes a persisted representation and therefore cannot be reverted by a single `git revert`".
- **Evidence.** §8's table (`03:1722-1736`) has no row for:
  (a) **`artifact_type` labels.** `03:1631-1638` (D11): W4 changes `type_for` from "silently falls back to `script`" to the correct type, and admits "Data already written with `artifact_type=script` … the wrong stored *type label* is not migrated". A revert of W4 restores the writer but leaves W4-era labels on disk.
  (b) **The `budget` durable document.** `03:705-706`: "the durable budget/spend document under the project (written through `storage`)" — a new persisted file introduced by W8, absent from §8.
  (c) **`kb_context_ref` stamping.** `03:1176`: "every `storage` artifact-write path passes a ref (1 of 12 today → 12 of 12)" — W? expands persisted artifact meta from 1/12 to 12/12, absent from §8.
  The only generic row is `03:1735` "Internal Python import paths — Broken with one-program shims".
- **Why it matters.** B5's "each extraction … is independently shippable and revertible by one `git revert`" is the program's core cost argument; three write-side representation changes ship without a declared compatibility/migration note, so their reverts are not equivalent to no-op.
- **Smallest fix.** Add one §8 row per write-side change naming the wave, whether it is additive/read-compatible, and the migration owner; or move each into a B7 PR with a version bump.

### O-15 — **Major** — exemption liveness cannot detect a *fixed* dotted-path or symbol violation (the stated anti-rot guarantee is false)

- **Exact claim attacked.** `05:1572-1577` (rule 2): "**Subject is live.** … A **fixed** deviation fails the ledger until the row is deleted. This is what makes the ledger a ratchet: … fixing the site *without* deleting the row fails liveness." Repeated at `05:2178-2180` and `03:1104`.
- **Evidence.** The liveness predicate for a dotted path is existence, not violation:
  `05:1695-1697`: "a dotted module/package path -- `importlib.util.find_spec` must resolve it; `<module>::<symbol>` -- the symbol root must still appear in that module."
  So `PRIVATE_MODULE_EXEMPTIONS` row `film_pipeline.schemas._base` (`05:1528`) stays "live" while `_base.py` exists, even after all 72 importers are migrated — the row's *violation* is gone but `find_spec` still resolves. Likewise a `module::symbol` writer row stays live while the symbol is merely *present*, not while it still writes.
- **Why it matters.** Rot can be one-directional for the two families whose liveness is existence-based: rows survive after the fix, so the "burndown" never shrinks to zero and the final "ledger must be empty" check is deferred indefinitely without any guard failing.
- **Smallest fix.** Make `subject_is_live` violation-aware for these families — for a private-module row, require the AST sweep to still observe ≥1 importer; for a writer row, require `write_sites()` to still observe the write.

### O-16 — **Major** — the anti-deletion registry is a hand-maintained expectation that can be edited in the same commit, and its own size is stated four ways

- **Exact claim attacked.** `05:2219-2220`: "Because the registry lives in a different file from the guards it names, deleting a guard fails a test that is still present." `05:1773-1774`: "a **registry that lives in a different file from the guards it names**, so deleting a guard fails a test that is still present."
- **Evidence.** The expected set is a literal tuple: `05:1799-1812`. Deleting `test_state_writers.py` **and** its `GuardFile(...)` row (or re-homing its `concerns` onto a surviving entry) in one commit satisfies all four registry tests (`05:1861`, `1880`, `1886`, `1893`): there is no independent enumeration of the expected guards and no `concerns`-vs-assertions check. `05:2222-2224` concedes the coordinated case ("no in-repo mechanism can defeat a coordinated deletion") — but the same-commit edit of the registry *is* the coordinated case, so the mechanism reduces to review, exactly what it claims to replace.
- **Evidence (size inconsistency).** `03:238-241`: "B's nine files (`_harness.py`, `_readers.py`, `test_contracts.py`, `test_boundaries.py`, `test_vocabularies.py`, `test_state_writers.py`, `test_registries.py`, `test_exemptions.py`, `__init__.py`)" = **9**, and `test_boundaries.py` appears nowhere in 05. `05:1799` comment: "11 guard files"; the tuple at `05:1800-1811` has **12** entries; `05:2215`: "all **ten** new guard files and the four legacy guards".
- **Why it matters.** The mechanism that protects every other guard has no protection, and four mutually inconsistent counts make the registry unverifiable by a reader.
- **Smallest fix.** Generate the registry from a directory scan and assert the *names* against a checked-in sorted manifest whose diff is reviewed; pick one count and use it in 03/05.

### O-17 — **Major** — §5.5 rule 6 (all eight declaration families non-empty) has no implementing test; the vacuities it claims to close are open

- **Exact claim attacked.** `05:1840-1844`: "**every declaration family is present and non-empty** — `MIRRORS`, `STATE_CHANNELS`, `REGISTRY_AGREEMENTS`, `POLICY_POINTS`, `PRIVATE_MODULE_EXEMPTIONS`, `CYCLE_EXEMPTIONS`, `NORMATIVE_NUMBERS`, `LIFECYCLES` each have ≥1 declaration … so deleting a *manifest family* is caught."
- **Evidence.** The printed `test_guard_registry.py` (`05:1846-1900`) contains exactly four tests (`:1861`, `:1880`, `:1886`, `:1893`) and none inspects any family. `test_guard_inputs_are_not_empty` (`05:1709-1714`) asserts only `MIRRORS`, `STATE_CHANNELS`, `REGISTRY_AGREEMENTS`, `POLICY_POINTS` — **4 of 8**. `PRIVATE_MODULE_EXEMPTIONS` and `CYCLE_EXEMPTIONS` have no non-empty assertion; `_LEDGER` is empty if both are emptied, and every `_LEDGER` loop (`05:1677`, `1699`) passes vacuously. `NORMATIVE_NUMBERS`/`LIFECYCLES` are protected only by their own files' `assert`/import (`05:912`), but the `concerns` metadata itself is never checked against assertions.
- **Why it matters.** This is a concrete vacuity 05 does **not** list: deleting two of the eight declaration families empties the anti-rot ledger while the suite stays green. It is the same class as the empty-set case the document promises to prevent.
- **Smallest fix.** Add `test_every_declaration_family_is_present_and_non_empty()` importing all eight names and asserting each, plus a count assertion in `test_exemptions.py`.

### O-18 — **Major** — the "module earns its place by N+I+R" rule fails for five of the twenty modules by their own declarations

- **Exact claim attacked.** `03:1759-1761`: "A module earns its place by owning a concern that satisfies N+I+R (`00` §1.2)"; `00:32-41` defines ownership as *all three* of N, I, R.
- **Evidence.** `03` states `State: None` / no R for the following:
  - `filmspec` — `03:450` "**State.** None. Module constants only"; `03:448-449` "Owns. N for every vocabulary above; I for the pure predicates".
  - `config` — `03:494` "**State.** None."
  - `constraints` — `03:535` "**State.** None."
  - `governance` — `03:806` "**State.** none."
  - `devharness` — `03:937` "Owns. **nothing normative**; it is a test-double library".
- **Why it matters.** The document's own anti-over-modularization test (`03:1757-1763`) cannot be applied literally to the modules it is meant to protect; four are N+I-only (legitimately so) and one owns no concern at all. The rule is therefore prose that no module can be held to, while §9.1 uses it to defend `budget`/`projects`/`governance`.
- **Smallest fix.** Restate the earning rule as "owns N+I, or owns R, or is a declared composition root / harness", and record which exemption each of the five claims.

### O-19 — **Major** — the stated architectural source of truth is never cited; the contradiction is silent

- **Exact claim attacked.** `AGENTS.md:8`: "The architectural source of truth is `documentation/architecture-blueprint.md`." `AGENTS.md:51`: "domain modules must not import each other directly — they communicate through `artifacts`."
- **Evidence.** `grep -rn "architecture-blueprint" docs/modular-architecture/*.md` → **0 hits** across 00–05. The blueprint defines its own system layers (`documentation/architecture-blueprint.md:19-118`) and a design rule at `:15-16`: "do not treat MCP as a late wrapper around an internal app. The MCP contract is the product boundary. LangGraph is the execution engine behind that boundary." The target instead makes `mcp` a thin L11 adapter over `operations` (`03:873-891`) with a 6-module `may_import` set, without reconciling the blueprint. The `AGENTS.md:51` contradiction **is** declared (`03:953`, `03:989-998`), and 04 plans to update the roster (`04:1270`), so only the blueprint half is silent.
- **Why it matters.** B9 requires each module to be justified by an audit finding *or an existing contract*; the existing contract that governs layering is not consulted. A reader who treats the blueprint as authoritative gets two incompatible layer models with no recorded decision.
- **Smallest fix.** Add a "prior art" subsection to 03 §2 that reads the blueprint's layer model and records explicitly whether `mcp`-as-adapter and L0–L12 supersede it, with the reason.

### O-20 — **Major** — the citation guard either skips or mis-fails on every published ledger row

- **Exact claim attacked.** `05:1569-1571` (rule 1): "**Citation resolves.** … when it carries `§X`, the cited file has a matching `## X` heading. *(proven pattern: `test_known_dead_rows_cite_evidence`)*".
- **Evidence.** The proven pattern is `tests/unit/config/test_config_contract.py:318`: `section = re.search(r"§([A-Z])", locator)` — a literal `§` is required. The generalization at `05:1682` drops it: `match = re.search(r"§?([A-Z]{1,3})", locator)`, then `05:1684` requires `^##+ {letter}[.: ]`. Running that against the wave-0 rows given at `05:1534` / `05:1540` / `05:1553`:
  ```
  'F-BOUNDARY-02' -> group(1)= 'F'   heading pattern: ^##+ F[.: ]   14-...law.md -> False
  'F-BOUNDARY-05' -> group(1)= 'F'   heading pattern: ^##+ F[.: ]   14-...law.md -> False
  'C2'            -> group(1)= 'C'   heading pattern: ^##+ C[.: ]   01-ownership-map.md -> False
  ```
  The actual headings are `### F-BOUNDARY-02 — …` (`audit/14-…md:169`), so the regex can never match. Conversely a numeric locator such as `§4.6` matches no `[A-Z]` and silently skips the heading assertion. The `§`-optional form is therefore strictly worse than the pattern it claims to generalize: it fails on finding ids and no-ops on numeric sections.
- **Why it matters.** Rule 1 is one of three anti-rot rules; as written the wave-0 ledger cannot ship green (the same failure mode `03:242-245` says was "resolved by this file existing").
- **Smallest fix.** Require the `§` prefix and resolve finding ids by their own heading pattern (`^### F-BOUNDARY-02 —`) as a second, explicit case.

### O-21 — **Minor** — the "bare import" side-effect claim omits the env condition that triggers it

- **Exact claim attacked.** `03:1189`: "the module-level `graph = build_graph()` at `graph/graph.py:201` that creates `<storage root>/checkpoints/` **on a bare import** … **Critical 5×5=25**".
- **Evidence.** `graph/graph.py:43` returns `MemorySaver()` unless `FILM_PIPELINE_PERSIST_STATE` is set. Probe with `./.venv/bin/python`:
  ```
  FILM_PIPELINE_PERSIST_STATE=1 FILM_PIPELINE_STORAGE_ROOT=/tmp/advroot_a  -> checkpoints dir after import: YES
  (PERSIST_STATE unset)         FILM_PIPELINE_STORAGE_ROOT=/tmp/advroot_b  -> checkpoints dir after import: NO
  ```
  `05:1915` states the condition correctly ("With `PERSIST_STATE=1` and no `RUNTIME_ROOT`"); 03 does not. The defect is real; the "bare import" framing overstates its reach.
- **Smallest fix.** Add "when `FILM_PIPELINE_PERSIST_STATE` is set" to `03:1189`.

### O-22 — **Minor** — the B7 MCP freeze is asserted in the present tense although the test does not exist at HEAD

- **Exact claim attacked.** `03:1724`: "**Preserved.** Names and shapes frozen by `tests/unit/mcp/test_contract_freeze.py::test_tool_names_and_schemas_unchanged` (a `make_registry()` name + schema-key snapshot)."
- **Evidence.** `grep -rn "test_tool_names_and_schemas_unchanged\|test_contract_freeze" tests/` → 0 hits; `tests/unit/mcp/` contains only `__init__.py` and `tools/`. The row's trailing clause "(freeze test added W0/W11)" reveals it is a plan; the main sentence reads as an existing guarantee.
- **Why it matters.** B7's "preserved" claim is not presently backed by a test, so any W0–W10 change could alter a tool schema without a red gate until W11.
- **Smallest fix.** Move the freeze test into W0 (it is a snapshot, no refactor needed) and phrase the row as "will be frozen by".

### O-23 — **Minor** — `architecture.py` is a whole-distribution import-time dependency, and coverage of it proves nothing

- **Exact claim attacked.** `05:243-245`: "`architecture.py` is a declared **leaf** (imports nothing from `film_pipeline`), so importing it executes every line and cannot dilute coverage"; `05:1387-1390` (D2 revisit trigger at ~500 lines).
- **Evidence.** Every package `__init__.py` imports `ModuleContract` from it (`05:237-239`, `05:386`), so every `import film_pipeline.*` executes the whole manifest. The leaf claim is currently satisfiable because all cross-module references are strings (`05:447` `canonical="film_pipeline.schemas.FilmPhase"`), so no `schemas` type is imported — but any future `ModuleContract` field typed with a schema would break `test_architecture_manifest_is_a_leaf` or force a `TYPE_CHECKING` import that L2 counts. Coverage of a data module is trivially 100 % and constrains nothing.
- **Why it matters.** The SPOF is real (a syntax/Name error in one 330→500-line file breaks all 281 modules' import), but the doc's justification addresses the wrong risk. No threshold or lint protects the manifest itself.
- **Smallest fix.** Keep the leaf, add a size/`ruff`-clean self-check, and pre-commit to the `architecture_<domain>.py` split at a stated line count rather than "~500".

---

## 2. Attacks that failed (the design survives)

### FA-1 — The allowed-edge matrix *is* internally consistent and acyclic by construction
Parsed §4.3 programmatically (`/tmp/adv/matrix.py`, layers from §4.2, columns mapped by abbreviation). Every one of the 20 rows' `•` targets is strictly lower: **0** self-edges and **0** non-lower edges. Kahn closure over all 20 modules completes with a full topological order. The same-layer concern is clean: the L2 trio (`config`,`kb`,`constraints`) imports only L0–L1. `03:1073-1078` is correct as stated.

### FA-2 — The §4.6 package-level forbidden count (10) is accurate for the mapping the doc uses
`UV_CACHE_DIR=… uv run python /tmp/adv/imports.py` reproduces **53 distinct cross-package edges** — exactly `03:1119`'s number. Mapping the 17 packages onto the 20 targets (app→studio/operations) reproduces exactly the doc's list: `config → providers` plus the nine `mcp → *` edges. The document's audit of the *audit's* "eight" is honest and re-runnable. (FA-2 is why O-02 is about 03-vs-05 scope, not about 03's arithmetic.)

### FA-3 — The conformance map covers the tree with zero orphans
`/tmp/adv/assign.py`: all **281** `.py` files assign to exactly one target under §6.1 rules; `UNASSIGNED: []`. Every per-package count matches the document (schemas 40, artifacts 12, graph 36, review 4, validation 14, agents 35, providers 14, generation 17, checkpoints 7, post 7, kb 7, config 7, constraints 3, app 21, mcp 46, cli 4, testing 6, top-level 1; sum 281). The 20-file random sample (seed 7) assigned correctly, including the split cases `app/services/__init__.py → operations` and `graph/_action_routing.py → governance`. No `__main__.py`, no `.pyi`, no generated files exist; `scripts/` (9 files) is covered by the "stays" rule (`03:1265`). B4's claim survives.

### FA-4 — The two edges the task flagged hardest are actually legal
`operations → checkpoints: True` and `mcp → projects: True` from the parsed matrix; `orchestration → projects: False` with `03:825-826` stating that non-goal consistently. No contradiction, no missing edge, for these three pairs.

### FA-5 — `budget`/`projects`/`governance` do not straightforwardly fail their consumer tests
`budget`'s cap is read by `generation` (authorize) and `governance` (verdict input) — 2 target modules. `projects` has `operations` (writer) + `mcp` (reader) + `studio` (constructor); the active pointer has multiple writing call paths today (70 `active_project|set_active` hits). `governance`'s target inbound is 4 modules (`03:808`). Only `constraints` has a single external consumer today (graph only: `graph -> constraints 2`), and `03:1775-1776` deliberately declines to merge it. The "name a module whose trigger says merge" attack does not land on the module set as a whole — it lands only on the *wording* of the `budget`/`projects` triggers (O-08/O-09).

### FA-6 — The import-time filesystem defect is real and reproducible
Under `FILM_PIPELINE_PERSIST_STATE=1` and a fresh `FILM_PIPELINE_STORAGE_ROOT`, `import film_pipeline.graph.graph` creates `<root>/checkpoints/` (probe above). The design found a genuine lifecycle bug that no AST sweep can see, and `05:1909-1926` states that limitation honestly. The attack succeeds only on 03's phrasing (O-21), not on the finding.

### FA-7 — `architecture.py` can be a leaf with the manifest as shown
All cross-module references in `05:444-463` and `05:1394-1401` are dotted strings, not imports, so `test_architecture_manifest_is_a_leaf` is satisfiable and no `ModuleContract` field shown requires a `schemas` type. The leaf premise holds for the declared content (O-23 is about fragility, not a false claim).

---

## 3. Bar B verdicts (00 §3)

| Bar | Verdict | The one decisive fact |
|---|---|---|
| **B1** one responsibility + non-goals | **PARTIALLY MET** | All 20 modules have a responsibility sentence and non-goals in 03 §3, but the enforcing test `test_responsibility_is_one_sentence_with_explicit_non_goals` (`05:258`, `03:1850`) is never defined anywhere in 05. |
| **B2** declared contract (API, invariants, state) | **PARTIALLY MET** | `public_api` is checked only for existence (`05:1088-1096`); nothing checks imports against it, and `05:425-431` concedes the worked example's `public_api` omits the real gateway `ProjectStorage`. |
| **B3** edges written, acyclic, mechanically checkable | **PARTIALLY MET** | The matrix is genuinely acyclic (FA-1), but L1 layer direction is unenforced (O-04) and 03/04/05 disagree on the forbidden set (O-02: 10 vs 10 vs 4). |
| **B4** every source file assigned, no orphans | **MET** | 281/281 assigned, 0 unassigned, all 18 per-package counts reproduced exactly (FA-3). |
| **B5** independently shippable, each green, `git revert`-able | **PARTIALLY MET** | Ordering is topological and waves claim green, but ≥3 write-side persisted-representation changes ship with no §8 compatibility row, so their single-revert property is undemonstrated (O-14). |
| **B6** ≥1 regression guard per extracted module | **PARTIALLY MET** | Guard families are named per concern, but the guards hardcode 53/107/106/1/3 (O-02, O-03), one arithmetic assertion is unsatisfiable against the declared ledger (O-03), and the anti-deletion loop is review-only (O-16). |
| **B7** MCP/graph/checkpoint contracts preserved or the break documented | **PARTIALLY MET** | §8 lists four declared breaks, but its persistence row names a non-divergence (O-13), the MCP freeze test does not exist at HEAD (O-22), and three persisted-representation changes are unlisted (O-14). |
| **B8** adversarial validation; all blocking objections resolved | **NOT MET** | §9 and D10–D13 are substantive self-attack, but this review raises three Blocking objections (O-01…O-03) that are unresolved, and `00:170` requires exactly that for the bar. |
| **B9** every module justified by a finding/contract, no speculation | **PARTIALLY MET** | Every module cites evidence, but `governance`'s core API (`evaluate_phase`, `advance_decision`, `PhaseDecision`) has **0** occurrences in `src/` and `budget.record_spend` has **0** call sites, and the repo's declared source of truth (`documentation/architecture-blueprint.md`) is cited **0** times. |

---

## 4. Blunt closing verdict

**Executable as written: no.** The *module catalog and the layer DAG* are the strong half — the matrix is internally consistent, acyclic, and its conformance map is exact (281/281). The *enforcement mechanism* is the weak half and is currently unbuildable in CI: its two authoritative inputs live under a gitignored, CI-excluded `docs/` tree (O-01); it publishes four different forbidden-edge/guard counts across three documents while asserting that "the count is derived" (O-02, O-16); and its flagship O7 guard is arithmetically unsatisfiable against its own ledger (O-03). These are not review quibbles — `make arch-check` cannot be green at W0.

What I would refuse to sign off on:
1. **W0 as specified.** No commit until the ledger ids/matrix live under `src/` (or a tracked test fixture) and the `110 == 2 + n` / `len(edges) == 53` assertions are removed or corrected.
2. **The "no unrestricted modules" claim (D10/L8).** `studio` imports 18 of 19 targets and the manifest still ships `unrestricted_imports`. Either re-word the law or remove the flag.
3. **The `budget`/`projects`/`governance` justification.** Two of the three abandon triggers are unfalsifiable or forbidden by L6, and `record_spend`/`evaluate_phase` have zero call sites at HEAD; the modules may still be right, but they are not yet *measured* right.
4. **The B5 revertibility claim.** Three persisted representations change without a §8 row (`artifact_type` labels, the budget document, `kb_context_ref` stamping).
5. **The §8 compatibility table as evidence.** It misnames the divergent persistence pair and cites a freeze test that does not exist.

---

## 5. Working tree

```
$ git status --porcelain
(empty)
```

Nothing under `src/`, `tests/`, or the repo root was written; all scratch work
was in `/tmp/adv/`. The only file created by this review is
`docs/modular-architecture/reviews/adversarial-architecture.md` (under gitignored
`docs/`, so `git status --porcelain` stays empty).
