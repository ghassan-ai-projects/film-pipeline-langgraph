# Proposal A — Target Module Architecture and Dependency Law

Status: **independent architecture proposal** (program step 3 of
`00-methodology-and-quality-bar.md` §4). Written without reading any audit file.
Conforms to **Quality bar B** (§3 of the spec).

Revision: repo `film-pipeline-langgraph`, branch `modular-app`, commit
`fb85baa`. All line anchors verified at this commit.

Method: I built the package import matrix, the module-level SCC decomposition,
a private-name reach-in sweep, a registry-agreement diff, and a god-module
census from the tree myself. Every claim below is reproducible with the command
shown next to it. Findings are labeled with the O-classes of spec §1.4.

Read this document top to bottom if you are executing it. §2–§4 are evidence,
§5 is the design, §6 is the law, §7 is the conformance map, §8 is the extraction
work breakdown, §9 is the guard-test plan, §10 is where I think the obvious
answer is wrong, §11 is contract compatibility.

---

## 1. What this system actually is (in one page)

Reading `AGENTS.md`, `documentation/architecture-blueprint.md` and
`documentation/product-completion/00-product-standard.md`, the system has four
externally-visible contracts and everything else is implementation:

| Contract | Declared in | Must not break |
|---|---|---|
| **MCP tool surface** (tool names, JSON input/output shapes, `mutates_state` / `requires_confirmation` / `creates_checkpoint` flags) | `src/film_pipeline/mcp/contract.py:34` `ToolContract`, `mcp/tools/registry.py:137` `register_all_tools` | B7 — this is the product boundary |
| **LangGraph state schema** (channels + reducers) | `graph/state_schema.py:102` `StudioGraphState`, `graph/orchestrator_state.py` `ORCH_CHANNELS` | B7 — checkpoints embed it |
| **Checkpoint / resume / rollback protocol** | `checkpoints/manager.py`, `checkpoints/rollback.py`, `app/_resume.py` | B7 |
| **On-disk storage layout v2** (marker, envelope, artifact tree, index) | `artifacts/storage.py:35` `LAYOUT_VERSION = 2`, `artifacts/store.py:1-16` | B7 — operator install/inspect/recover story |

Everything else — agents, prompts, validators, KB, providers, generation — is
internal, and is where the ownership damage is.

Two structural facts drive the whole design:

1. **The codebase is organized by implementation phase, not by concern.** The 17
   packages map to build phases (`AGENTS.md` table), so one concern lands in
   whichever package happened to be built at the time. Evidence: "what makes a
   phase advance" lives in `graph/`, `review/`, `validation/` and `app/`
   simultaneously (§3, F-GATE-01).
2. **The one boundary that was deliberately fixed is the model to copy.** The
   storage rewrite pinned a single owner with *source-level* guard tests
   (`tests/unit/artifacts/test_storage_boundary.py:1-10`: "They are deliberately
   source-level checks. A structural rule that is only described in a docstring
   drifts; a rule with a failing test does not."). Graph startup boundaries
   (`tests/unit/graph/test_startup_boundaries.py`) and channel parity
   (`tests/unit/graph/test_channel_registry.py`) use the same technique. That is
   the enforcement mechanism this design copies — not the storage layout.

---

## 2. Recon: the dependency structure as it is

### 2.1 Package-level import matrix

Reproduce (`scripts/architecture/import_matrix.py` should be this, committed):

```bash
cd ${REPO_ROOT} && python3 - <<'PY'
import ast, os, collections
ROOT='src/film_pipeline'
pkgs=sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,d)) and d!='__pycache__')
pkgset=set(pkgs); edges=collections.Counter()
for dp,dn,fn in os.walk(ROOT):
    dn[:]=[d for d in dn if d!='__pycache__']
    for f in fn:
        if not f.endswith('.py'): continue
        p=os.path.join(dp,f); src=os.path.relpath(p,ROOT).split(os.sep)[0]
        for node in ast.walk(ast.parse(open(p).read())):
            mods=[a.name for a in node.names] if isinstance(node,ast.Import) else (
                [node.module or ''] if isinstance(node,ast.ImportFrom) and not node.level else [])
            for m in mods:
                t=m.split('.')[1] if m.startswith('film_pipeline.') else m
                if t in pkgset and t!=src: edges[(src,t)]+=1
for (a,b),n in sorted(edges.items(), key=lambda x:-x[1]): print(f"{a:12} -> {b:12} {n:3}")
PY
```

Result at `fb85baa` (cross-package import count, edge list; top 30 shown of 52):

| from → to | n | | from → to | n |
|---|---|---|---|---|
| `mcp → schemas` | 73 | | `app → artifacts` | 8 |
| `graph → schemas` | 50 | | `providers → schemas` | 8 |
| `validation → schemas` | 32 | | `generation → schemas` | 8 |
| `agents → schemas` | 27 | | `app → schemas` | 7 |
| `mcp → generation` | 23 | | `kb → schemas` | 7 |
| `artifacts → schemas` | 16 | | `mcp → app` | 7 |
| `app → graph` | 16 | | `mcp → artifacts` | 7 |
| `graph → validation` | 14 | | `mcp → graph` | 7 |
| `post → schemas` | 10 | | `mcp → validation` | 7 |
| `graph → agents` | 9 | | `mcp → agents` | 7 |
| | | | `generation → artifacts` | 7 |
| | | | **`app → mcp`** | **1** |

Three immediate readings:

- **`schemas` is the universal sink (323 inbound).** Any dependency law that
  omits it is not a law; §6 makes it an explicit Layer 1.
- **The declared domain-isolation law is already false.** `generation →
  artifacts` (7), `agents → providers` (4), `post → validation` (1), `config →
  providers` (2), `testing → artifacts/providers/checkpoints` (4) are all
  domain-module-to-domain-module imports. `AGENTS.md` is not describing this
  codebase.
- **There is a real package cycle: `app ↔ mcp`.** `app → mcp` is one line —
  `src/film_pipeline/app/product_gate.py:17`: `from film_pipeline.mcp.contract
  import make_registry`. `mcp → app` is seven lines, the root being
  `src/film_pipeline/mcp/tools/__init__.py:22`:
  `from film_pipeline.app.runtime import get_runtime`. This is a layering bug,
  not an import-order accident: an *entry point* (`app/product_gate.py`) lives
  inside a package that `mcp` also depends on.

### 2.2 Module-level cycles (SCCs)

Reproduce: Tarjan over the module import graph, including function-body imports.

| SCC | size | Reading |
|---|---|---|
| `mcp.tools.*` (37 modules) | 37 | **Benign but real.** `mcp.tools/__init__.py` re-exports every tool, and every tool imports `..helpers`, which imports `film_pipeline.mcp.tools` back (`mcp/tools/helpers.py:49-58`, deliberately, for monkeypatching). A façade that is also a dependency of its own members. |
| `graph.nodes`, `_repair_loop`, `approval`, `generation`, `prep`, `visual`, `orchestrator_validators`, `orchestrator_validators.brief` | 8 | **Not benign.** These modules mutually import each other's private helpers: `_repair_loop.py:199 → approval` (which re-imports `_repair_loop`), `orchestrator_validators/brief.py:179 → graph.nodes`. Node modules and gate policy are one tangle. |
| `artifacts`, `artifacts.registry`, `artifacts.store` | 3 | Packaging only: `store.py:30 → artifacts` (package `__init__`), `registry.py:129 → artifacts`. Fix is a one-line import target, no design change. |
| `app._persistence`, `app.runtime`; `app.services`, `operator`, `_project_discovery` | 2 + 3 | `_persistence.py:33 → runtime`, `runtime.py:19 → _persistence`; `operator.py:16 → app.services`, `app/services/__init__.py:3 → operator`. Façade-vs-implementation cycles. |
| `agents.prompt_templates.*` | 5 | `defaults/__init__.py:11,19,26` import data from `production/spine/validators`, each of which imports `registry`. Data/framework cycle. |
| `mcp._stdio_transport` / `mcp.server` | 2 | `server.py:10,13,17` import private transport functions from `_stdio_transport`, which imports `server`. |

Only 37 cycle-forming back-edges exist in total. That is a tractable number and
it means **an acyclicity law is achievable without a rewrite** — this is the
single most important feasibility fact in the proposal.

### 2.3 Private-name reach-ins across module boundaries

Reproduce: AST sweep for `from <mod> import _name` and for `alias._name` where
`alias` is a module alias from another package. Result: **383 hits.**

The cross-*package* ones (the ones a dependency law can forbid) are few and
specific:

| Site | Reaches into | Why it matters |
|---|---|---|
| `app/_graph_exec.py:63,74,191,243,377,409` → `film_pipeline.graph.nodes._SERVICES_CTX` | orchestration internals | The composition root sets a **contextvar inside another package** to inject dependencies. |
| `app/_graph_exec.py:449` → `film_pipeline.graph.nodes.approval._PHASE_NODES` | graph node table | An **entry-point module** indexes the graph's private node table to advance a phase manually. |
| `cli/driver.py:80,81` → `film_pipeline.app.runtime._RUNTIME_MODE_OVERRIDE`, `_RUNTIME` | app module globals | The CLI **mutates another module's module-level state** directly. |
| `config/profile_resolver.py:204` → `film_pipeline.providers.credentials._env_var_for` | provider internals | Profile validation depends on a private credential-naming convention. |
| `agents/model_adapter.py:36` → `film_pipeline.providers.adapters.seedance_openrouter.OPENROUTER_API` | a **concrete provider adapter** | The agent model layer hardcodes one vendor's adapter. Inverted dependency. |
| `app/_graph_exec.py:15,16` → `app._resume._approval_made_progress` etc. | intra-package privates | Acceptable-ish; listed for completeness. |

Quote, `app/_graph_exec.py:62-63`:

```python
    token = _gn._SERVICES_CTX.set(rt.services)
```

Quote, `config/profile_resolver.py:204`:

```python
    from film_pipeline.providers.credentials import _env_var_for, is_configured
```

### 2.4 Service-locator patterns

There are **four** ways to obtain runtime dependencies, and they are not
interchangeable:

1. `graph/services.py:53` — `GraphServices` dataclass: the declared bundle
   (`prompt_runner`, `artifact_store`, `agent_registry`, `validator_registry`,
   `kb_builder`). Good design; keep it.
2. `graph/nodes/_shared.py:11-13` — a **module-level contextvar**:
   ```python
   _SERVICES_CTX: contextvars.ContextVar[GraphServices | None] = contextvars.ContextVar(
       "_film_pipeline_services", default=None
   )
   ```
   read by `_get_services(state)` (`_shared.py:16-26`) which prefers the
   checkpointed state key `_services` (`graph/services.py:137`
   `SERVICES_KEY = "_services"`).
3. `mcp/tools/helpers.py:70-73` — `_services(rt)` asserts `rt.services is not
   None` and returns it; every tool handler reaches the whole `StudioRuntime`
   through `get_runtime()`.
4. `mcp/tools/__init__.py:22` — `from film_pipeline.app.runtime import
   get_runtime`, re-bound as a **package attribute** on purpose
   (`__init__.py:15-21`: "Submodules import `get_runtime` back from this package
   … so that tests which do `monkeypatch.setattr(film_pipeline.mcp.tools,
   "get_runtime", ...)` continue to affect every tool function").

`_services` appears in **112 references across 43 files**. This is the single
biggest coupling in the repo, and it is *deliberate* — it exists because the
same object graph is threaded through two different execution models (the MCP
request path and the LangGraph node path) that were never given a shared
composition root.

### 2.5 God modules

Reproduce: AST census of class/function spans ≥80 (function) / ≥200 (class)
lines.

| Entity | lines | Note |
|---|---|---|
| `artifacts/store.py:57` `ArtifactStore` | 605 | Already guarded; the one well-owned god object. |
| `app/services/operator.py:47` `OperatorService` | 437 | 39 methods; the use-case façade for all 15 MCP tool groups. |
| `agents/runner.py:69` `PromptRunner` | 403 | Model invocation + retry + mock + failure classification. |
| `app/runtime.py:36` `StudioRuntime` | 370 | 15 fields: `projects`, `graph`, `services`, `checkpoints`, `audit_events`, `provider_adapters`, `provider_health`, `project_roots`, `checkpoint_managers`, … |
| `generation/executor.py:55` `GenerationExecutor` | 355 | Owns the generation lifecycle steps. |
| `app/mock_responses.py:97` `default_mock_responses` | 339 | 339-line literal in production `src/`. |
| `validation/base.py:27` `BaseValidator` | 265 | Validator contract + scoring + status coercion. |
| `agents/model_adapter.py:72` `ModelAdapter` | 264 | HTTP transport + provider selection + credential lookup. |
| `mcp/tools/registry.py:137` `register_all_tools` | 248 | Declares every tool inline (name, group, handler, flags). |
| `constraints/extractor.py:106` `ConstraintExtractor` | 228 | |
| `generation/ledger.py:31` `GenerationLedgerManager` | 204 | |
| `artifacts/project_storage.py:64` `ProjectStorage` | 200 | |

By file density: `artifacts/store.py` (48 defs), `app/runtime.py` (46),
`app/services/operator.py` (40), `graph/orchestrator_state.py` (38),
`constraints/extractor.py` (35).

**`StudioRuntime` is the load-bearing problem**, not `ArtifactStore`: it is both
the session state store (projects, active project, audit, checkpoints, provider
health) *and* the dependency locator (`services`) *and* the graph handle holder
(`graph`). Three responsibilities, one mutable bag.

---

## 3. Seams: where responsibilities are actually smeared

Each finding uses the spec §1.7 shape. Classes per §1.4, severity per §1.5.

### F-SEV-01 — Issue severity has a normative enum and 48 literal copies

- **Class:** O1 (duplicated normative model) + O5 (policy-by-branch)
- **Severity:** High (impact 4 × drift 4 = 16 → borderline Critical)
- **Concern:** "What severity makes an issue block a phase" — one string value.
- **De-facto owners:**
  - `schemas/_base.py:197` — defines the vocabulary only —
    `"BLOCKING = \"blocking\""`
  - `graph/orchestrator_validators/_shared.py:11` — the only site that uses it
    properly — `'return {"severity": IssueSeverity.BLOCKING.value, "code": code, "message": message}'`
  - 48 other sites compare/emit the raw literal, e.g.
    `graph/nodes/_repair_loop.py:91` `'blocking = [i for i in issues if i.get("severity") == "blocking"]'`
- **Drift proof:** *mutation scenario.* Rename the enum member value at
  `schemas/_base.py:197` from `"blocking"` to `"blocked"`. `IssueSeverity.BLOCKING`
  changes; the 48 literal comparisons do not. No test fails, because every test
  that exercises a gate builds its fixture with the same literal
  (`graph/nodes/approval.py:55` counts `== "blocking"` and the fixtures do too).
  The gate silently stops parking phases.
- **Reproduce:** `grep -rn 'severity") == "blocking"\|"severity": "blocking"' src/film_pipeline --include=*.py | wc -l` → `48`
- **Blast radius:** `graph`, `app`, `mcp`, `cli`, `validation`, `config`. Human
  approval gates stop engaging; blockers stop blocking.
- **Candidate owner module:** `filmspec` — owns severity vocabulary and the
  single `is_blocking(issue)` predicate.
- **Extraction sketch:** replace all 48 comparisons with
  `filmspec.issues.is_blocking(issue)` / `filmspec.issues.blocking_issue(code, msg)`;
  guard test asserts the literal `"blocking"` never appears outside `filmspec/`.
- **Prior art:** new (no audit file consulted per program rules).

### F-PHASE-01 — The phase order and the gate map are declared four times

- **Class:** O1
- **Severity:** High (impact 5 × drift 3 = 15)
- **Concern:** "The ordered phases and the approval gate each phase parks at."
- **De-facto owners:**
  - `schemas/_base.py:77` — `class FilmPhase(StrEnum)` with 11 members (`"The canonical production phases of a film."`)
  - `graph/_action_routing.py:18` — `PHASE_ORDER = [` as bare strings
    (`"intake", "constitution", "development", ...`)
  - `graph/_action_routing.py:33` — `_PHASE_AGNOSTIC_PHASES = {...}` re-lists
    every phase except `generation`
  - `graph/_action_routing.py:49` — `APPROVAL_GATES = {"development": "treatment", ...}`
  - the gate value is then **re-typed at each node call site**, e.g.
    `graph/nodes/visual.py:597` `_phase_gate_updates(new_state, phase="gen_planning", gate="generation_spend")`
- **Drift proof:** *existing agreement, not divergence* — my diff confirms
  `set(PHASE_ORDER) ^ set(FilmPhase) == set()`, `_PHASE_AGNOSTIC_PHASES ==
  set(PHASE_ORDER) - {"generation"}`, and `set(APPROVAL_GATES) == set(PHASE_ORDER)`
  at `fb85baa`. **That is exactly why this is a finding.** Mutation scenario: add
  `"color"` to `FilmPhase` at `schemas/_base.py:77`. `PHASE_ORDER` keeps 11
  entries, `APPROVAL_GATES` has no `"color"` gate, and no test fails: the phase
  is simply unreachable, and `app/_graph_exec.py:427-441` (the manual advance)
  falls back to `next_phase = PHASE_ORDER[current_index + 1]` past it.
- **Reproduce:** the `diff_norm.py` snippet in §2.1's appendix; or
  `grep -n "PHASE_ORDER\|_PHASE_AGNOSTIC_PHASES\|APPROVAL_GATES" -r src/film_pipeline`
- **Blast radius:** all 9 `_phase_gate_updates` call sites, `cli/driver.py:139-214`,
  `app/_resume.py:31-32`, `mcp` intake/planning.
- **Candidate owner module:** `filmspec` — owns the phase lattice (order, gate
  per phase, agnostic/dependent classification).
- **Extraction sketch:** `FilmPhase` gains `order()`, `next_phase()`, `gate_for()`;
  `PHASE_ORDER`/`APPROVAL_GATES` become derived tuples, not literals.
- **Prior art:** new.

### F-AKIND-01 — The artifact-kind catalog and `ArtifactType` disagree today

- **Class:** O1 + O4 (parallel registries)
- **Severity:** High (impact 4 × drift 5 = 20 → Critical)
- **Concern:** "Which artifact kinds exist and which are storable."
- **De-facto owners:**
  - `schemas/_base.py:27` — `class ArtifactType(StrEnum)`, 45 values
    (`"Catalog of artifact types produced by the studio."`)
  - `artifacts/registry.py:126` `_register_defaults()` — 54 `_spec(...)`
    registrations, e.g. `artifacts/registry.py:162`:
    ```python
        "generation_ledger": _spec(
            "generation_ledger", payload_model=GenerationLedger, mutable=True
        ),
    ```
- **Drift proof:** *existing divergence.* Mechanical diff at `fb85baa`
  (see §2.1 appendix `diff_norm.py`):
  - registered but **not** in `ArtifactType`: `consensus_report`, `cost_estimate`,
    `execution_brief`, `matrix_patch`, `profile_change_approval`,
    `profile_change_proposal`, `project_profile`, `repair_feedback`,
    `scope_contract`, `shot_matrix`, `story_bible`, `subtitles` — 12 kinds.
  - in `ArtifactType` but **not** storable: `clip`, `last_frame`, `mid_frame`.
    Saving one raises `KindNotRegisteredError` at
    `artifacts/registry.py` (validate-on-save was added deliberately, so the
    failure is loud — but the *catalog* is still two lists).
  - `tests/unit/artifacts/test_store_v2.py:495-511` imports `REGISTRY` but never
    cross-checks it against `ArtifactType`. No test fails when they diverge.
- **Reproduce:**
  `grep -c "_spec(" src/film_pipeline/artifacts/registry.py` (54) vs
  `python3 -c "from film_pipeline.schemas._base import ArtifactType as A; print(len(A))"` (45)
- **Blast radius:** operators reading `ArtifactType` from MCP responses see 45
  kinds; the store accepts 54. Agents declaring `output_artifacts` are validated
  against neither consistently.
- **Candidate owner module:** `filmspec` owns the *kind set*; `storage` owns the
  *persistence spec* per kind (payload model, mutability, migrations,
  renderers). One registration line declares both.
- **Extraction sketch:** make `_register_defaults()` the source of truth and
  derive/validate `ArtifactType` from it, or delete `ArtifactType` and expose
  `filmspec.artifact_kinds()`. Guard test: every `REGISTRY` kind is a member and
  vice versa.
- **Prior art:** new.

### F-SVC-01 — Four service-locator mechanisms with no single writer

- **Class:** O3 (split state authority) + O5 + O7 (leaked internals)
- **Severity:** **Critical** (impact 5 × drift 4 = 20)
- **Concern:** "How a node or tool obtains the runtime dependency bundle."
- **De-facto owners:**
  - `graph/services.py:53-60` — the value type `GraphServices`
  - `graph/nodes/_shared.py:11-26` — contextvar fallback read
  - `app/_graph_exec.py:62-63` — the composition root writing the contextvar
    from *outside* the graph package: `token = _gn._SERVICES_CTX.set(rt.services)`
  - `app/runtime.py:36-52` — `StudioRuntime.services` field (a second copy)
  - `mcp/tools/helpers.py:70-73` — `rt.services` accessor for tools
  - `mcp/tools/__init__.py:22` — the monkeypatch-visible `get_runtime` indirection
- **Drift proof:** *existing divergence.* Two injection paths exist and disagree
  in precedence: `_get_services` (`_shared.py:23-26`) prefers the **state key**
  `_services` and only falls back to the contextvar, while
  `app/_graph_exec.py:63` sets the **contextvar only**. `StudioRuntime.services`
  is a third copy that is never reconciled with either. Mutation scenario: set
  `rt.services = None` after a graph run has begun; the contextvar still holds
  the old bundle, `_get_services` still works, and no test fails.
- **Reproduce:** `grep -rn "_services" src/film_pipeline --include=*.py | wc -l`
  → `112`; `grep -rln "_services" src/film_pipeline --include=*.py | wc -l` → `43`
- **Blast radius:** every graph node and every MCP tool. Also blocks unit
  testing: the monkeypatch contract in `mcp/tools/__init__.py:15-21` is a
  load-bearing behaviour that no type or test asserts.
- **Candidate owner module:** `orchestration` owns one `ServicesScope` context
  accessor (public); `studio` is the only writer; `operations` and `mcp` receive
  typed use-case objects instead of the runtime bag.
- **Extraction sketch:** promote `_SERVICES_CTX` to `orchestration.scope.services_scope(...)`;
  delete `StudioRuntime.services` in favour of the scope; convert
  `mcp/tools/helpers._services` into a constructor-injected `OperatorBackend`.
  Keep the `_services` **graph state channel** (B7 — see §10.6 and §11).
- **Prior art:** related guard test already exists for a different concern:
  `tests/unit/graph/test_startup_boundaries.py:30` (`test_graph_package_never_imports_testing_or_app`).

### F-VAL-01 — A validation report has two representations and two writers

- **Class:** O3 + O6 (parallel lifecycle)
- **Severity:** High (impact 4 × drift 4 = 16)
- **Concern:** "Where a validation report lives and what it is."
- **De-facto owners:**
  - `graph/nodes/qc.py:392` — the **graph** path keeps reports as raw dicts in
    state: `reports = state.setdefault("_validation_reports", [])`
  - `mcp/tools/validation.py:187` — the **MCP** path persists an artifact:
    `artifact_id="validation_report", artifact_type=ArtifactType.VALIDATION_REPORT`
  - `validation/base.py:265-270` — the enforcement rule ("Four-status contract:
    BLOCKED must have at least one blocking issue.")
- **Drift proof:** *existing divergence.* A report produced through the graph is
  a `dict` in `state["_validation_reports"]` and is never written to the
  versioned artifact store; a report produced through `run_validation` is a
  `ValidationReport` artifact that the graph never reads. Mutation scenario:
  tighten `BaseValidator._coerce_status` (`validation/base.py:245-290`) so a
  score-below-threshold report is `BLOCKED`. The MCP path reflects it; the graph
  path's `_validation_reports` dicts were built by
  `_append_validator_report` (`qc.py:390-400`) using the same call, so it also
  reflects it — but the *stored artifact history* and the *graph state* now
  disagree about which phases were reviewed, and nothing compares them.
- **Reproduce:** `grep -rn '_validation_reports\|"validation_report"' src/film_pipeline --include=*.py`
- **Blast radius:** `validation`, `graph`, `mcp`, `post` (delivery packaging reads
  validation report paths at `post/delivery_packaging_agent.py:14`).
- **Candidate owner module:** `validation` — single writer of the report
  artifact; everyone else reads a typed ref.
- **Extraction sketch:** `validation.run(...) -> ValidationReport` produces the
  artifact once; `qc` node stores `validation_report_ref` and reads it back
  through `storage`. Guard test: `store.save(` with a `VALIDATION_REPORT` payload
  appears exactly once in the tree, outside `validation/`.
- **Prior art:** new.

### F-GATE-01 — Phase-advancement policy is re-derived in five packages

- **Class:** O2 (duplicated invariant enforcement) + O5
- **Severity:** **Critical** (impact 5 × drift 4 = 20)
- **Concern:** "May this phase advance, and what may the human do here?"
- **De-facto owners:**
  - `graph/nodes/_shared.py:147-159` — the graph's gate updater
    (`_phase_gate_updates`) plus `_require_human_approval` (`:132-144`)
  - `graph/edges.py:100` — routing inserts a blocking issue inline
  - `graph/router.py:64` — a *second* blocking filter:
    `if isinstance(issue, dict) and issue.get("severity") == "blocking"`
  - `graph/_action_routing.py:49` — `APPROVAL_GATES`
  - `graph/orchestrator_validators/*` — pre-phase blocker gates
    (`_shared.py:11` `_blocking(...)`, `prep_gates.py:7`, `planning_gates.py:7`)
  - `review/actions.py:24` — `compute_available_actions(...)`, the human-facing
    duplicate of "which actions are blocked and why"
  - `app/services/operator.py:299-300,458` — the façade re-filters blocking
    issues for its DTOs
  - `mcp/tools/review.py:65` — a *third* blocking filter for the tool response
- **Drift proof:** *mutation scenario.* Change the rule at
  `graph/nodes/_shared.py:153` so that `require_human_approval=False` also clears
  `human_approval_required`. The graph path honours it;
  `review/actions.compute_available_actions` (`review/actions.py:24+`) computes
  availability from issues and checkpoints independently and keeps reporting the
  action as blocked; `mcp/tools/review.py:65` and `operator.py:299` keep
  surfacing the blockers. No test fails, because `review`'s tests build their own
  state fixtures. Three sources of truth for one answer.
- **Reproduce:** `grep -rn 'severity") == "blocking"' src/film_pipeline/{graph,review,app,mcp,cli} --include=*.py`
- **Blast radius:** human-in-the-loop is the product's safety mechanism
  (`architecture-blueprint.md`: "every major phase pauses for human review"). A
  divergence here either wedges the pipeline or lets work advance without review.
- **Candidate owner module:** `governance` — one pure decision function
  `evaluate(phase, reports, issues, config) -> PhaseDecision(advance | repair |
  escalate | await_human, blocked_reasons, available_actions)`.
- **Extraction sketch:** move `_action_routing` gate law, `orchestrator_validators/`,
  and `review/actions.py` under `governance`; make `graph.edges`, `graph.nodes`
  and `review` call the one function. `review`'s package-output half stays in
  `governance` too (one human-facing decision surface).
- **Prior art:** new.

### F-GEN-01 — The generation lifecycle is driven from two paths and the ledger→state projection is written by MCP

- **Class:** O6 + O2 + O3
- **Severity:** High (impact 5 × drift 3 = 15)
- **Concern:** "How a generation job advances and who may write its state."
- **De-facto owners:**
  - `generation/ledger.py:31` `GenerationLedgerManager` — the (good) single
    persistence authority for the `generation_ledger` artifact
    (`artifacts/registry.py:162`, `mutable=True`)
  - `graph/nodes/_generation_batch_planning.py:127` `_plan_generation_ledger` —
    the graph drives plan→approve→persist
  - `app/services/_generation_ops.py:70` `approve_generation_spend` — the MCP
    path drives the same steps through `GenerationExecutor`
  - `mcp/tools/generation/planning.py:177` `_sync_generation_requests_from_ledger(active, rows)`
    — **MCP writes the `generation_requests` channel of graph state** by hand
    (`planning.py:180`: "Publish dispatchable generation requests from ledger
    rows into graph state.")
  - the spend ceiling is enforced **only** in the graph:
    `_generation_batch_planning.py:45` `max_cost_usd = float(raw_cost) * 1.1`
- **Drift proof:** *existing divergence.* The MCP spend path takes
  `max_cost_usd` from the caller's tool argument and defaults to `-1.0`
  (`app/services/_generation_ops.py:70-72`); the graph path derives it as
  estimate × 1.1 (`_generation_batch_planning.py:36-45`). Both call
  `ledger.approve_spend`, so the *check* is single-owner, but the *ceiling
  policy* is not: an operator who calls `approve_generation_spend` with no
  argument gets unlimited approval from the MCP path and a 110% ceiling from the
  graph path. No test compares them.
- **Reproduce:** `grep -rn "approve_spend\|max_cost_usd" src/film_pipeline --include=*.py`
- **Blast radius:** money. `product-completion/00-product-standard.md` calls
  out "planning, spend approval, job submission bookkeeping, polling/resume,
  duplicate-prevention" as the behaviours that must be real even where video
  generation is mocked.
- **Candidate owner module:** `generation` owns the lifecycle *and* the spend
  ceiling policy; `orchestration` owns the projection from ledger rows to graph
  channels.
- **Extraction sketch:** add `generation.plan/approve/start/poll` returning
  `GenerationLedgerDelta`; delete `_sync_generation_requests_from_ledger` from
  `mcp` and move the projection to `orchestration.generation_projection`.
- **Prior art:** new.

### F-AGENTREG-01 — Three agent registries must agree and only a partial test pins them

- **Class:** O4 (parallel registries)
- **Severity:** Medium (impact 3 × drift 3 = 9)
- **Concern:** "Which agents exist, what they can do, and what class implements them."
- **De-facto owners:**
  - `agents/mvp/__init__.py:15` — `MVP_AGENTS: list[AgentRegistration]`, 11 agents
    (`"the agents wired into the current graph"`)
  - `agents/impl/registry.py:18` — `AGENT_CLASS_BY_ID: dict[str, type[BaseAgent]]`,
    12 keys, hardcoded ids (`"intake-classifier-agent": IntakeAgent, ...`)
  - `schemas/registries/agent_registry.py:8` — `AgentRegistryEntry`, a *serializable
    fourth* shape for the same facts
  - `agents/registry.py:58` `AgentRegistry._validate_contract` — the real
    invariant enforcement
- **Drift proof:** *partially pinned, therefore fragile.*
  `tests/unit/agents/test_mvp_invariants.py:40` asserts
  `get_agent_class(agent.agent_id) is not None` for every MVP agent — that
  catches registration without an implementation. It does **not** catch the
  reverse: `AGENT_CLASS_BY_ID` has 12 keys and `MVP_AGENTS` has 11, so one
  implementation (`visual-dev-agent` vs `reference-strategy-planner`, both
  mapped to `VisualDevAgent` at `impl/registry.py:25-26`) is already an
  unregistered alias. Mutation scenario: delete an agent from `MVP_AGENTS`; the
  class stays in `AGENT_CLASS_BY_ID` and the parity test still passes.
- **Reproduce:** `grep -c "agent_id=" src/film_pipeline/agents/mvp/__init__.py` → `11`;
  `grep -c '": ' /dev/null` — count keys in `AGENT_CLASS_BY_ID` at
  `agents/impl/registry.py:18-31` → 12.
- **Blast radius:** `agents`, `graph/nodes/_agent.py:100`
  (`impl=get_agent_class(resolved_agent_id)`), routing.
- **Candidate owner module:** `agents` — one `AgentCatalog` built from one
  declaration list; `impl/registry.py` becomes a lookup *by* the catalog.
- **Extraction sketch:** make `MVP_AGENTS` the registration source and have
  `AGENT_CLASS_BY_ID` validated as a total, surjective map over it; guard test
  asserts set equality both ways.
- **Prior art:** `tests/unit/agents/test_mvp_invariants.py` (partial).

### F-PRIV-01 — 383 private reach-ins make module boundaries nominal

- **Class:** O7
- **Severity:** High (impact 3 × drift 5 = 15)
- **Concern:** "Whether a module's declared boundary is real."
- **Evidence:** §2.3 table; the cross-package cases are the actionable ones.
- **Drift proof:** *mutation scenario.* Move `_SERVICES_CTX` into a new private
  module `graph/nodes/_scope.py` to fix a cycle. `app/_graph_exec.py:63` still
  reads `_gn._SERVICES_CTX` through the package `__init__` re-export, so it keeps
  importing successfully and no test fails; but the graph now has two contextvars
  and services are injected into one while nodes read the other. Only an
  end-to-end run would catch it, and there is no test that asserts "services are
  the same object in both paths".
- **Reproduce:** the AST sweep in §2.3 (383 hits).
- **Blast radius:** every package.
- **Candidate owner module:** n/a — this is a law (§6 L3), enforced by a test.
- **Extraction sketch:** §8 P3.
- **Prior art:** `tests/unit/artifacts/test_storage_boundary.py:56` already
  enforces exactly this class for one package.

### F-KBPATH-01 — The knowledge-base root is resolved by three CWD-relative call sites

- **Class:** O3 + O5
- **Severity:** Medium (impact 3 × drift 3 = 9)
- **Concern:** "Where the KB manifest lives."
- **De-facto owners:**
  - `kb/paths.py:11-12` — `Path("film-knowledge-base/manifest.yaml")`,
    `Path("film-knowledge-base/index/kb-manifest.yaml")`
  - `app/bootstrap.py:42` — same path as a string literal
  - `app/smoke.py:55` — same path again
- **Drift proof:** *existing duplication with a live hazard.* All three use
  relative paths, so behaviour depends on the process CWD. Mutation scenario:
  add a `FILM_PIPELINE_KB_ROOT` env override in `kb/paths.py:9`; `app/bootstrap.py:42`
  and `app/smoke.py:55` keep probing the CWD-relative path and keep failing with
  "not found" while `kb` succeeds. No test fails (tests are run from the repo
  root).
- **Reproduce:** `grep -rn "film-knowledge-base" src/film_pipeline --include=*.py`
- **Blast radius:** `kb`, `app` bootstrap/smoke, first-run operator experience.
- **Candidate owner module:** `kb` owns the KB root, through the same
  env/explicit-argument/marker discipline `artifacts/storage.py:1-10` uses.
- **Extraction sketch:** `kb.root.resolve_kb_root()`; delete the other two
  literals; guard test forbids the literal outside `kb/`.
- **Prior art:** new.

### F-RUNTIME-01 — `StudioRuntime` is session state, service locator, and graph handle at once

- **Class:** O3
- **Severity:** Medium (impact 3 × drift 4 = 12)
- **Concern:** "Who owns session state and dependency wiring."
- **Evidence:** `app/runtime.py:36-52` declares 15 fields spanning project
  registry (`projects`, `active_project_id`), dependency injection (`services`),
  graph handle (`graph`), checkpoints (`checkpoints`, `checkpoint_managers`),
  audit (`audit_events`), and providers (`provider_adapters`, `provider_health`).
  46 defs in one file.
- **Drift proof:** *existing divergence.* Project state lives both in
  `StudioRuntime.projects` (`runtime.py:43`) and on disk through
  `artifacts/project_storage.write_project_record`
  (guarded by `tests/unit/artifacts/test_storage_boundary.py:144-164` which
  requires `write_project_record` to exist on `ProjectStorage`). Nothing asserts
  the in-memory dict and the on-disk record agree after a mutation.
- **Reproduce:** `wc -l src/film_pipeline/app/runtime.py` → 370;
  `grep -n "    [a-z_]*:" src/film_pipeline/app/runtime.py | head -20`
- **Blast radius:** everything.
- **Candidate owner module:** `studio` (composition root, no domain logic) +
  `projects` (registry and active pointer) + `checkpoints` (checkpoint state).
- **Extraction sketch:** §8 P7–P9.
- **Prior art:** new.

---

## 4. Natural seams: the classification the spec asks for

Spec §1.2 defines ownership as N (normative model) + I (invariant enforcement) +
R (representation authority). Classifying the seams by *which of N/I/R is
actually being fought over* tells you how to cut, and it is not always where the
package boundary is:

| Seam | What is smeared | Cut shape |
|---|---|---|
| Film vocabulary (phases, gates, severities, statuses, artifact kinds) | **N only** — everyone agrees on behaviour today, they just re-declare the constants | One tiny pure module. Cheapest, highest-leverage cut. |
| Phase advancement / approval | **I** — five implementations of "may this advance" | One pure decision function. |
| Validation report | **R** — two representations, two writers | One writer in `validation`. |
| Generation ledger | **I + R at the policy layer** — `R` is already single-owner (`ledger.py`), but the ceiling *policy* and the state *projection* are not | Policy inward to `generation`; projection upward to `orchestration`. |
| Durable storage | already **N+I+R single-owner** | Do not touch. Extend its guard tests to the new law. |
| Runtime dependencies | **I** — four locators, no single writer | One scope object, one writer in `studio`. |
| Agent catalog | **N + O4** — three registries | One declaration, derived lookups. |
| KB root | **R** — three path resolvers | One resolver in `kb`. |

**The pattern:** most of this codebase's ownership debt is *normative-model
duplication* (O1) and *policy-by-branch* (O5), not state corruption. That is
good news: O1/O5 fixes are mechanical, low-risk, and independently shippable.
The two genuinely hard cuts are `governance` (F-GATE-01) and the service locator
(F-SVC-01), because both require touching the graph execution path.

---

## 5. Target module architecture

18 modules. Every module is justified by a current responsibility; there are no
"future flexibility" layers. Names are target package paths under
`src/film_pipeline/`.

Reading the catalog: **R** = responsibility, **Non-goals** = explicit "does
not", **Contract** = public surface, **Owns (N/I/R)** = what only it may define
/ enforce / write, **State** = mutable state it owns, **Deps** = allowed
outbound imports.

### 5.1 `filmspec` — the film-production vocabulary and its laws

- **R:** Defines the normative vocabulary of the studio — phases and their order,
  approval gates, issue severities and the block predicate, validation statuses,
  generation statuses, agent roles/families, and the set of legal artifact kinds
  — and the small pure laws over them (`next_phase`, `gate_for`, `is_blocking`,
  `may_advance` inputs).
- **Non-goals:** does not import anything (no `schemas`, no storage, no I/O); does
  not define payload *shapes* (that is `schemas`); does not decide *whether* to
  advance at runtime (that is `governance`); does not know about persistence
  specs per artifact kind (that is `storage`).
- **Contract:** `FilmPhase` (with `order()`, `next_phase()`, `gate_for()`,
  `is_agnostic()`, `generation_dependent()`), `ArtifactKind` (the 54-value
  catalog), `IssueSeverity`, `blocking_issue(...)`, `is_blocking(issue)`,
  `ValidationStatus`, `GenerationStatus`, `AgentRole`, `AgentFamily`, `AGENT_GATE_MAP`.
- **Owns:** N for all of the above, plus I for the pure predicates.
- **State:** none (module constants only).
- **Deps:** none. This is the only module with zero outbound imports.

### 5.2 `schemas` — typed payload contracts

- **R:** Defines every Pydantic payload exchanged or persisted: artifact payloads,
  MCP request/response envelopes, graph state snapshots, registry entry records.
- **Non-goals:** no enums/constants that `filmspec` owns (it imports them); no
  I/O; no validation of cross-object *policy* (only field-level schema validity).
- **Contract:** the existing 40 `schemas/*.py` public models, unchanged.
  `SchemaBase` (`schemas/_base.py:265`) stays here.
- **Owns:** N+R of payload shape only; it never writes artifacts.
- **State:** none.
- **Deps:** `filmspec`.

### 5.3 `config` — profile stack resolution

- **R:** Loads profile stacks from `profiles/`, merges them in declared order,
  validates the merged result, and produces the resolved-config dict consumed by
  the graph and runtime.
- **Non-goals:** does not know about providers' credentials (that moves to
  `providers`); does not read project storage; does not decide runtime mode.
- **Contract:** `load_profile_flex`, `ProfileStack`, `merge_profiles`,
  `validate_resolved_config`, `apply_runtime_overrides`.
- **Owns:** N+I for profile merge order and config validity.
- **State:** none (cached parsed YAML only, keyed by path+mtime).
- **Deps:** `filmspec`, `schemas`.

### 5.4 `kb` — knowledge-base retrieval

- **R:** Resolves the KB root, reads the manifest, retrieves and compresses
  entries, detects conflicts, and builds `KBContextPacket`s for a phase/agent/task.
- **Non-goals:** does not decide *which* agent gets which KB domains (agent
  contracts declare that; `orchestration` calls this module); does not write into
  project storage.
- **Contract:** `resolve_kb_root`, `load_manifest`, `search`, `build_packet`,
  `compress`, `detect_conflicts`.
- **Owns:** N+I+R for the KB root and the manifest format.
- **State:** owns the KB root resolution (env → explicit → repo layout), not the
  project storage root.
- **Deps:** `filmspec`, `schemas`.

### 5.5 `storage` — the durable representation authority (today's `artifacts`)

- **R:** Is the only module that reads or writes the studio storage root: root
  resolution and marker gating, project directory layout, the versioned artifact
  store with envelopes/checksums/migrations, the derived artifact index,
  manifest, and the on-disk project record / graph-state / checkpoint / audit
  files.
- **Non-goals:** does not import `orchestration`, `mcp`, `studio`, `operations`,
  `generation`, `checkpoints`, `validation`, `governance`, `providers`, `kb`,
  `agents`, `post` (this exact list is already enforced for the current package
  by `tests/unit/artifacts/test_storage_boundary.py:101-130`); does not own
  checkpoint *policy* (that is `checkpoints`); does not own KB paths.
- **Contract:** `ProjectStorage` (with `read/write_project_record`,
  `read/write_graph_state`, `read/append_checkpoints`, `read/append_audit_events`,
  `media_dir`, `read/write_manifest`, `git_backend`), `ArtifactStore`
  (`save`, `save_mutable`, `load`, `load_latest`, `list_artifacts`, `envelope`),
  `ArtifactKindRegistry` (`REGISTRY`, `KindSpec`, `migrate_payload`,
  `validate_artifact_id`), `resolve_storage_root`, `ensure_storage_root`,
  `PROFILE_PRODUCTION`, `PROFILE_SANDBOX`.
- **Owns:** N (persistence spec per kind: payload model, version, mutability,
  migration, renderer) + I (marker gating, checksum verification, kind
  registration on save) + R (every byte under the root).
- **State:** the storage root on disk and the in-process kind registry.
- **Deps:** `filmspec`, `schemas`. **Nothing else, ever.**

### 5.6 `providers` — external provider integration

- **R:** Declares the provider adapter port, implements the concrete model /
  image / video adapters, resolves credentials and dotenv, prices requests,
  classifies failures, and reports provider health.
- **Non-goals:** does not know about agents, prompts, or generation ledgers; does
  not decide which provider to use (the model router and the generation planner
  do).
- **Contract:** `BaseProviderAdapter`, `ProviderRegistry`, `ProviderEntry`,
  `credentials.lookup/env_or_dotenv/redact` (public — the private
  `_env_var_for` becomes `env_var_for`), `required_credentials(provider_ids)` (new
  home for `config`'s credential check), `estimate_cost_for_duration`,
  `classify_failure`, `health.check`.
- **Owns:** N+I for provider identity, credential naming, pricing, and the
  failure taxonomy.
- **State:** credential cache; adapter instances (built by `studio`).
- **Deps:** `filmspec`, `schemas`.

### 5.7 `checkpoints` — checkpoint and rollback lifecycle

- **R:** Owns the checkpoint lifecycle: creating checkpoints at phase boundaries,
  branching, invalidation propagation, resume payload selection, and rollback to
  a checkpoint.
- **Non-goals:** does not write project files itself (it goes through
  `storage.ProjectStorage`); does not import `orchestration` (the composition
  root injects the graph handle and the storage backend).
- **Contract:** `CheckpointManager`, `GitBackend` (structural protocol),
  `create_checkpoint`, `invalidate`, `resume_from`, `rollback`, `branches`.
- **Owns:** N+I for checkpoint semantics and invalidation rules; R is delegated
  to `storage`.
- **State:** git repository per project (via injected backend).
- **Deps:** `filmspec`, `schemas`, `storage`.

### 5.8 `agents` — agent catalog, prompts, and model invocation

- **R:** Declares the agent roster and its contracts, holds the versioned prompt
  framework and templates, routes a task to (agent, model profile, prompt), and
  executes the model call with retry and failure classification.
- **Non-goals:** does not import concrete provider adapters (only
  `providers.BaseProviderAdapter`, credentials, pricing, failure taxonomy); does
  not know about graph state or phases (it receives a task and context); does not
  write artifacts (`orchestration` saves agent outputs through `storage`).
- **Contract:** `AgentCatalog` (replaces `agents/registry.py` +
  `agents/impl/registry.py` + `mvp/__init__.py` as three registries),
  `AgentRegistration`, `MVP_AGENTS`, `capabilities_for`, `implementation_for`,
  `PromptTemplateRegistry`, `get_registry`, `PromptRunner.run`,
  `ModelRouter.select`, `ModelAdapter` (with the concrete-adapter import
  removed), `BaseAgent`.
- **Owns:** N+I for the agent catalog, prompt templates, model routing, and
  response parsing.
- **State:** in-process catalog + prompt registry (built once by `studio`).
- **Deps:** `filmspec`, `schemas`, `providers`.

### 5.9 `validation` — validator execution and report production

- **R:** Owns the validator registry and threshold policy, runs validators
  against artifacts, and is the **single writer** of `ValidationReport`
  artifacts.
- **Non-goals:** does not decide whether a phase may advance (that is
  `governance`, which consumes reports); does not import `orchestration`.
- **Contract:** `ValidatorRegistry`, `ValidatorRegistryEntry`, `BaseValidator`,
  `run_validators(...) -> ValidationReport`, `save_report(report, store, ...) -> ArtifactRef`,
  `load_latest_report(...)`, `score_to_status`, `thresholds`.
- **Owns:** N+I+R for validation reports and the blocked/passed law
  (`validation/base.py:265`: "Four-status contract: BLOCKED must have at least
  one blocking issue.").
- **State:** validator registry.
- **Deps:** `filmspec`, `schemas`, `storage`.

### 5.10 `governance` — the advancement and human-review control plane

- **R:** Decides, from a phase, its validation reports, its issues, and the
  resolved config, whether work may advance, must be repaired, must escalate, or
  must await a human — and owns the gate names, repair-loop bounds, review-package
  assembly, diffing, and the human-facing available/blocked action set.
- **Non-goals:** does not run validators (consumes `validation` reports); does not
  import `orchestration` (this is the invariant that keeps the graph acyclic — it
  is a pure function over values); does not execute agents; does not write
  checkpoints.
- **Contract:** `PhaseDecision` (`advance|repair|escalate|await_human`),
  `evaluate_phase(phase, reports, issues, resolved_config) -> PhaseDecision`,
  `gate_for(phase)`, `RepairPolicy` (max attempts), `compute_available_actions`,
  `build_review_package`, `diff_versions`, `blocking_issues(issues)`.
- **Owns:** N+I for advancement policy, gate identity, repair bounds, and
  review-package content.
- **State:** none. **This is deliberate** — a stateless decision module cannot
  join a cycle.
- **Deps:** `filmspec`, `schemas`, `storage` (to read artifacts it renders into a
  review package), `validation`.

### 5.11 `generation` — generation job lifecycle and media synthesis

- **R:** Owns the generation ledger lifecycle (plan → approve spend → start →
  poll → deliver/fail → retry/delta), the spend-ceiling policy, prompt
  preparation for provider calls, provider dispatch, frame/sheet review, and the
  reference-sheet compositor.
- **Non-goals:** does not write graph state channels (it returns deltas);
  does not import `orchestration`; does not import `agents` (it builds prompts
  from matrix rows via `prompt_builder`, not from agent prompt templates).
- **Contract:** `GenerationLedgerManager`, `LEDGER_ARTIFACT_ID`, `GenerationExecutor`,
  `plan`, `approve_spend` (with the ceiling derived **here**, not at call sites),
  `start`, `poll_once`, `delta_regenerate`, `build_prompt`, `compositor.render_*`,
  `frame_reviewer.review`.
- **Owns:** N+I+R for the generation ledger and its transitions, and I for the
  spend ceiling.
- **State:** the `generation_ledger` artifact (mutable, revision-counted) and
  in-flight provider job ids.
- **Deps:** `filmspec`, `schemas`, `storage`, `providers`.

### 5.12 `post` — post-production and delivery packaging

- **R:** Owns the assembly, subtitle, transition, audio-design and
  delivery-packaging agents' behaviour and the post-phase validators.
- **Non-goals:** does not implement the MCP stubs that call it; does not own
  assembly *policy* (the operator decides; this module builds the plan/package).
- **Contract:** `AssemblyAgent.build_plan`, `SubtitleAgent`, `TransitionAgent`,
  `AudioDesignAgent`, `DeliveryPackagingAgent.build_package`, `post.validators`.
- **Owns:** N+I for delivery package structure.
- **State:** none (produces artifacts through `storage`).
- **Deps:** `filmspec`, `schemas`, `storage`, `validation`.

### 5.13 `projects` — project identity and the active-project pointer

- **R:** Owns the project registry: creation (id, slug, root), durable record
  binding, lookup/list, and the single active-project pointer for a session.
- **Non-goals:** does not run the graph; does not expose MCP shapes; does not
  write storage files directly (uses `storage.ProjectStorage`).
- **Contract:** `ProjectRegistry` (`create`, `get`, `list`, `resolve(ref)`,
  `set_active`, `active`), `ProjectRecord`, `new_project_id`.
- **Owns:** N+I for project identity and R for the active pointer.
- **State:** the in-memory project map and active id — **one** place, replacing
  `StudioRuntime.projects` + `StudioRuntime.active_project_id`
  (`app/runtime.py:43-44`) and the independent re-derivation in
  `mcp/tools/helpers.py:34-47` `_active_project_id`.
- **Deps:** `filmspec`, `schemas`, `storage`.

### 5.14 `orchestration` — the LangGraph state machine (today's `graph`)

- **R:** Owns the pipeline graph: the typed state schema and its reducers, the
  phase topology and edges, node implementations that run agents and persist
  phase artifacts, interrupts and resume, the orchestrator working state and its
  channel registry, and the projections that turn domain deltas (generation
  ledger rows, KB packets, issue lists) into graph state.
- **Non-goals:** does not decide gate policy (calls `governance`); does not run
  validators (calls `validation`); does not drive the generation lifecycle (calls
  `generation`); does not write the storage root (calls `storage`); does not
  import `mcp`, `studio`, `operations`, `projects` or `devharness` (the last two
  of these are already enforced for `graph` by
  `tests/unit/graph/test_startup_boundaries.py:30`).
- **Contract:** `graph` (the compiled `langgraph.json` entry), `build_graph`,
  `StudioGraphState`, `ORCH_CHANNELS`, all reducers (`merge_unique`,
  `merge_generation_requests`, `merge_issues`), `GraphServices`/`ServicesScope`,
  `services_scope(...)` (public replacement for `_SERVICES_CTX`),
  `PHASE_ORDER` (re-exported from `filmspec` for compatibility),
  `project_generation_requests(...)`.
- **Owns:** N+I+R for graph state shape, channel write policy, phase topology,
  and checkpoint-visible state.
- **State:** the LangGraph checkpointed state per thread; the services scope.
- **Deps:** `filmspec`, `schemas`, `storage`, `config`, `kb`, `providers`,
  `agents`, `validation`, `governance`, `generation`.

### 5.15 `operations` — the operator use-case façade (today's `app/services`)

- **R:** Exposes the studio's operations as typed use cases (create/inspect
  project, run/resume/advance pipeline, plan/approve/poll generation, run
  validation, assemble, checkpoint/rollback, read audit) that both the MCP tool
  handlers and the local CLI driver call.
- **Non-goals:** does not construct the object graph (that is `studio`); does not
  know JSON tool schemas (that is `mcp`); does not talk to providers directly
  (uses `generation`/`providers`).
- **Contract:** `OperatorBackend` with one method per operation; typed
  `BackendOperationError` (`app/services/errors.py`), `GenerationWorkspace`,
  `ReviewWorkspace` (`app/services/models.py`).
- **Owns:** I for the operation-level preconditions (project must exist, phase
  must be at gate) and R for the operator-facing read models.
- **State:** none beyond the injected registry/runtime handles.
- **Deps:** `filmspec`, `schemas`, `orchestration`, `generation`, `projects`,
  `storage`, `checkpoints`, `validation`, `governance`, `config`, `providers`,
  `kb`, `post`.

### 5.16 `mcp` — the MCP product boundary

- **R:** Defines the external tool contract (names, JSON schemas, flags,
  idempotency), the request envelope and project resolution, error mapping, the
  registry, and the stdio server — and adapts each tool call to exactly one
  `operations` use case.
- **Non-goals:** does not import `orchestration` internals, `storage`,
  `generation`, `checkpoints` or `app`; does not hold a runtime singleton; does
  not re-derive project resolution (uses `projects.resolve`); no tool handler
  contains policy.
- **Contract:** `ToolContract`, `ToolGroup`, `ToolRegistry`, `make_registry`,
  `register_all_tools`, `RequestEnvelope`, `new_envelope`, `resolve_request`,
  `server.main`, the ~90 tool functions (names and JSON shapes frozen — B7).
- **Owns:** N+I for the external contract; R for MCP response shapes.
- **State:** the tool registry (built once).
- **Deps:** `filmspec`, `schemas`, `operations`, `projects`, `governance`,
  `validation`. **Nothing else.**

### 5.17 `studio` — composition root, process runtime, and entry points

- **R:** Builds the object graph (services scope, storage, registries, provider
  adapters, graph handle), owns process/session lifecycle (bootstrap, mode,
  persistence toggles, logging, health, safety, version, smoke), and hosts the
  entry points (`cli.run:main`, `mcp.server:main`, `app.product_gate:main`, the
  `langgraph.json` target).
- **Non-goals:** no domain rules; no MCP JSON shapes; nothing may import `studio`.
- **Contract:** `StudioRuntime` (now: services scope + graph handle + logging
  only — no project registry, no audit, no provider maps), `build_runtime`,
  `bootstrap`, `configure_logging`, `product_gate.main`, `cli.run.main`,
  `cli.driver.Driver`, `cli.io`.
- **Owns:** I for wiring correctness (exactly one services scope; exactly one
  storage root per process).
- **State:** process lifecycle state only.
- **Deps:** everything. It is the top of the graph.

### 5.18 `devharness` — the test harness (today's `testing`)

- **R:** Provides mock human actor, mock model adapter, in-memory git backend,
  storage factories, and scenario scripts for tests and mock-mode runs.
- **Non-goals:** must not be importable from any production module (already
  enforced for `graph` by `tests/unit/graph/test_startup_boundaries.py:30`).
- **Contract:** `MockHumanActor`, `DecisionProfile`, `MockModelAdapter`,
  `ALL_SCENARIOS`, `make_store`, `InMemoryGit`.
- **Owns:** nothing normative; it is a test double library.
- **State:** in-memory doubles.
- **Deps:** `filmspec`, `schemas`, `storage`, `providers`, `checkpoints`.

### Module count and the "fewer, larger modules" constraint

18 target modules against 17 current packages — **flat, not inflated.** Six
packages move boundaries (`graph` → `orchestration` + `governance` + `filmspec`;
`artifacts` → `storage` + `filmspec`; `app` → `studio` + `operations` +
`projects`; `review` → `governance`; `schemas` → `schemas` + `filmspec`;
`testing` → `devharness`), and one new module (`filmspec`) is added. I
explicitly rejected splitting `graph` per phase, splitting `storage` into
catalog/store, and introducing a `common`/`utils` module — see §10.

---

## 6. The dependency law

### 6.1 Judgment on the existing `AGENTS.md` law

> "`graph` and `mcp` may import across all sub-packages; domain modules must not
> import each other directly — they communicate through `artifacts`."

**Verdict: too vague, and wrong in its substance. Replace it.**

Three defects:

1. **It is already false and unenforced.** `generation → artifacts` (7),
   `agents → providers` (4), `post → validation` (1), `config → providers` (2),
   `testing → artifacts/providers/checkpoints` (4). Two of those
   (`generation → artifacts`, `agents → providers`) are *legitimate and should be
   allowed*; two (`post → validation`, `config → providers`) are accidental. A
   law that cannot distinguish them is not a law. There is no test for it.
2. **"they communicate through `artifacts`" is unenforceable as written and
   harmful if enforced.** Every module imports `schemas` (323 inbound edges).
   Under a literal reading, `validation → schemas` is illegal, which is absurd.
   Worse, if taken seriously it would force domain modules to exchange data by
   *reading and writing files* — the slowest, least type-safe, hardest-to-test
   channel available, and it would break the single-writer guarantee that the
   storage guard tests exist to protect. The real intent was "do not share
   mutable state", not "use the filesystem as IPC".
3. **It protects the wrong thing.** The observed damage is not imports; it is
   **private reach-ins** (F-PRIV-01, 383 sites), **duplicated normative models**
   (F-SEV-01/F-PHASE-01/F-AKIND-01) and **duplicated enforcement**
   (F-GATE-01/F-GEN-01). None of those is an "import across packages" problem —
   `graph` importing `validation` is fine; `app` writing
   `graph.nodes._SERVICES_CTX` is not.

### 6.2 Replacement law (normative)

> **Film Pipeline Modularity Law (v1)**
>
> **L1 — Direction.** Every module declares its layer. A module may import only
> modules in strictly lower layers (same-layer imports are forbidden except
> within a single module's own subpackages). The layer order is §6.3.
>
> **L2 — Acyclicity.** The module import graph must be acyclic, including
> function-body imports, `__init__` re-exports, and `TYPE_CHECKING` blocks when
> they name a module in the same or higher layer. No SCC may contain two
> modules.
>
> **L3 — Public surfaces only.** No module may import a private name
> (`from other import _x`) or a private submodule (`other._pkg`) from another
> module, and no module may assign to another module's module-level state. If a
> consumer needs a private thing, the owner must publish it or the design is
> wrong.
>
> **L4 — Persistence exclusivity.** Only `storage` may read or write the storage
> root, build project paths, or import layout/serialization internals. (Existing
> law; keep and extend to the whole tree.)
>
> **L5 — Model and invariant exclusivity.** A concern's normative model is
> declared in exactly one module and its invariant is enforced in exactly one
> place. Consumers import the model; they never re-declare a literal, a phase
> list, a gate name, a severity string, or an artifact-kind list, and they never
> re-implement the owner's predicate.
>
> **L6 — Composition-root singularity.** Only `studio` constructs the object
> graph. No module may hold a mutable module-level singleton of a domain object,
> and no module may read another's context variable or global.
>
> **L7 — Harness isolation.** Production modules must not import `devharness`.

**"Communicate through artifacts" is deleted.** Its replacement is: *modules
communicate through declared public contracts; artifacts are the durable medium
for concerns that must survive a process, and only `storage` writes them.*
Cross-module in-process calls with typed arguments are the normal case. This is
a strictly stronger, checkable statement, and it removes the incentive to
serialize everything.

### 6.3 Layer order (the DAG)

```
L0  filmspec
L1  schemas
L2  config        kb
L3  storage       providers
L4  projects      checkpoints      (checkpoints also depends on L3 storage)
L5  agents
L6  validation    generation      post
L7  governance
L8  orchestration
L9  operations
L10 mcp
L11 studio          (may import all; nothing imports studio except entry points)
--  devharness      (off-graph; may import L0-L6; nothing in production imports it)
```

Why this is acyclic by construction:

- **`filmspec` has zero imports**, so it cannot participate in a cycle.
- **`storage` imports only L0–L1.** The storage guard test already forbids
  `storage → {orchestration, mcp, studio, operations, generation, checkpoints,
  validation, governance, providers, kb, agents, post}`; the design keeps that
  exact list and renames packages.
- **`governance` is stateless and imports nothing above L6.** F-GATE-01's cycle
  risk (`governance ↔ orchestration`) is removed by making the gate decision a
  pure function over values: `orchestration` calls `governance.evaluate_phase(...)`;
  `governance` never calls back. The current `graph ↛ review` and
  `review ↛ graph` edges in the matrix are already consistent with this; the
  design makes it a law.
- **`generation → orchestration` is forbidden.** Today
  `mcp/tools/generation/planning.py:177` performs the ledger→graph-state
  projection. Moving that projection *up* into `orchestration`
  (`orchestration.project_generation_requests`) removes the only candidate for a
  `generation ↔ orchestration` cycle.
- **`operations` sits above `orchestration`** and is the only module allowed to
  sequence domain modules for a use case.
- **`app ↔ mcp` disappears** because `app` is split: `studio` (top, hosts
  `product_gate`, may import `mcp`) and `operations` (mid, imported *by* `mcp`).
  The current single edge `app/product_gate.py:17 → film_pipeline.mcp.contract`
  becomes legal because it is now `studio → mcp`.
- **`mcp → storage/generation/checkpoints/orchestration` all disappear.** MCP
  tools call `operations`. The current edges `mcp → generation` (23),
  `mcp → artifacts` (7), `mcp → graph` (7), `mcp → checkpoints` (3) are the
  largest single source of MCP bloat (46 files, 7.6k LOC) and all of it becomes
  illegal — correctly, because re-implementing orchestration behind the tool
  surface is F-GATE-01 and F-GEN-01.

### 6.4 How a checker enforces it

One committed test plus one committed matrix, both source-level (the technique
already proven at `tests/unit/artifacts/test_storage_boundary.py`):

`tests/unit/architecture/test_module_law.py`:

1. **`test_layer_direction`** — loads `scripts/architecture/layers.yaml` (the
   layer table of §6.3 as data, not code), AST-walks every `.py` under
   `src/film_pipeline/`, resolves each `film_pipeline.*` import (absolute,
   relative, function-body, `TYPE_CHECKING`) to a target module, and asserts
   `layer(target) < layer(source)`.
2. **`test_no_cycles`** — Tarjan SCC over the resolved module graph; asserts no
   SCC has size > 1 and reports the full cycle as the failure message.
3. **`test_no_private_reach_ins`** — asserts no module imports
   `other._name` / `other._subpkg`, and no module assigns an attribute on an
   alias of another module (catches `_gn._SERVICES_CTX.set(...)`).
4. **`test_no_module_state_singletons`** — asserts no module-level assignment of
   a mutable domain object (`dict(...)`, `list(...)`, a call returning a
   registry/runtime) outside `studio` and `storage`'s kind registry.
5. **`test_layers_yaml_covers_tree`** — every package directory under
   `src/film_pipeline/` appears in `layers.yaml`; fails on a new package
   (prevents silent layer-less modules).
6. **`test_devharness_not_imported_by_production`** — generalizes
   `tests/unit/graph/test_startup_boundaries.py:30` to all of L0–L11.

**Migration technique (this is what makes it shippable):** the checker ships in
P0 with an explicit `KNOWN_VIOLATIONS` allow-list file
(`scripts/architecture/violations-baseline.txt`) containing one line per current
offence and the phase that will remove it. Tests 1–4 pass when the violation set
equals the baseline. Every extraction phase deletes its lines from the baseline;
the final phase asserts the baseline is empty. This is how you get a mechanical
law, a green `make ci-check` on day one, and no ability for new violations to
sneak in. The baseline file is the program's burndown chart.

`make ci-check` should additionally run a tiny reporting step
(`scripts/architecture/import_matrix.py --fail-on-new`) so the reviewer sees the
matrix diff, but the *test* is the enforcement.

---

## 7. Conformance map

B4 requires every source file to be assigned. This table accounts for all 17
packages and all 281 files. Rules are exhaustive; the ambiguous/split cases are
enumerated file by file.

| Current package | files | → Target module(s) | Rule / enumeration |
|---|---|---|---|
| `schemas/` | 40 | `schemas` (all except enums) + `filmspec` | `_base.py` **splits**: `SchemaBase` (`:1-26`) → `schemas`; every enum (`FilmPhase` `:77`, `AgentRole` `:93`, `AgentFamily` `:105`, `ArtifactType` `:27`, `ArtifactStatus`, `IssueSeverity` `:195`, `ValidationStatus`, `GenerationStatus`, …) → `filmspec`. All other 39 files move 1:1 to `schemas/`. `registries/*` (4 files) stay in `schemas` as payload records. |
| `artifacts/` | 12 | `storage` 11 files + `filmspec` 1 | `registry.py` splits: the **kind set** → `filmspec`; `KindSpec`/migrations/renderers/`REGISTRY` stay in `storage`. `__init__`, `_layout`, `paths`, `serialization`, `envelope`, `manifest`, `rendering`, `storage`, `store`, `project_storage`, `matrix_projection` → `storage` 1:1. |
| `graph/` | 36 | `orchestration` 24 + `governance` 12 | → `governance`: `_action_routing.py` (gate law; `compute_actions` split out to `orchestration`), `_agent_routing.py` (**agent** routing → `agents` if capability-based selection is agent domain; otherwise `orchestration` — see §10.8), `consistency.py`, `scope_contract.py`, `orchestrator_validators/` (5 files). → `orchestration`: `graph.py`, `edges.py`, `router.py`, `state_schema.py`, `services.py`, `orchestrator_state.py`, `context_packets.py`, `nodes/` (19 files), `subgraphs/` (2 files). `router.py` keeps a `PHASE_ORDER` re-export from `filmspec` for compatibility. |
| `review/` | 4 | `governance` | All 4 (`actions.py`, `diff.py`, `generator.py`, `__init__.py`) — "what actions does the human have and what does the package show" is gate policy + its representation. |
| `validation/` | 14 | `validation` | All 14, 1:1. `registry.py`, `base.py`, `thresholds.py`, `consensus.py`, `impl/` (8 validators), `validators/`. |
| `agents/` | 35 | `agents` | All 35, 1:1, with three internal fixes: `impl/registry.py` + `registry.py` + `mvp/__init__.py` collapse into one catalog; `model_adapter.py:36` drops the concrete-adapter import; `_http_transport.py:18` uses the public `providers.credentials.redact`. |
| `providers/` | 14 | `providers` | All 14, 1:1. `credentials._env_var_for` → public `env_var_for`. |
| `generation/` | 17 | `generation` | All 17, 1:1. `compositor/` (4 files) stays inside `generation` (see §10.4). |
| `checkpoints/` | 7 | `checkpoints` | All 7, 1:1. |
| `post/` | 7 | `post` | All 7, 1:1. |
| `kb/` | 7 | `kb` | All 7, 1:1; `paths.py` becomes the only KB-root resolver. |
| `config/` | 7 | `config` | All 7, 1:1, minus the credential check in `profile_resolver.py:202-206`, which moves to `providers.required_credentials`. |
| `constraints/` | 3 | `agents` (extraction entry) + `schemas` | `extractor.py`/`_keywords.py` are a deterministic **intake analysis** step: target `agents/analysis/` (it is a producer of `project_constraints`, not a model). If the owner prefers zero agent coupling, it stays a standalone module `constraints` at L5; either is lawful. I recommend folding into `agents` to avoid a module with one caller. |
| `app/` | 21 | `studio` 16 + `operations` 4 + deleted 1 | → `operations`: `services/` (5 files). → `studio`: `runtime.py`, `_graph_exec.py`, `_persistence.py`, `_provider_seeds.py`, `_resume.py`, `bootstrap.py`, `health.py`, `logging_setup.py`, `product_gate.py`, `safety.py`, `smoke.py`, `version.py`, `__init__.py`, `mock_responses.py`, plus the runtime half of `runtime.py`. **`mock_responses.py` (339-line literal) moves to `devharness`** — it is fixture data, and it is currently importable from production `src/`. |
| `mcp/` | 46 | `mcp` | All 46, 1:1 structurally; `tools/*` handlers lose all direct imports of `orchestration`/`storage`/`generation`/`checkpoints` and call `operations`. `tools/helpers.py:70-73` `_services(rt)` and the `get_runtime` package attribute (`tools/__init__.py:22`) are **deleted**. |
| `cli/` | 4 | `studio` | All 4 (`run.py`, `driver.py`, `io.py`, `__init__.py`); `driver.py:80-81`'s writes to `_RUNTIME`/`_RUNTIME_MODE_OVERRIDE` become public `studio` calls. |
| `testing/` | 6 | `devharness` | All 6; **plus** `app/mock_responses.py`. |
| `profiles/` (repo root) | 13 yaml | `config` (data) | Consumed by `config.loader`; unchanged. Owned by `config` as its input contract. |
| `scripts/` (repo root) | 10 py | *stays where it is* | Manual operator scripts. Must not be importable from `src/`. Add to lint scope as non-production. |
| `langgraph.json` | 1 | `studio` (entry) | Target stays `graph/graph.py:graph` → becomes `orchestration/graph.py:graph`. This is the one **externally-visible path change** in the program and must be listed in the phase that ships it (B7). |
| `film-knowledge-base/` | data | `kb` (data) | Repo-root data dependency; root resolution moves into `kb`. |
| `tests/` | 180 py | per-module mirrors | Move `tests/unit/<pkg>/` alongside the target module name; add `tests/unit/architecture/`. |

**No orphan files.** Every `.py` under `src/film_pipeline/` is covered by a rule
above; the three packages that split (`schemas`, `artifacts`, `graph`) are
enumerated file-by-file; `app/mock_responses.py` is the only file that changes
*purpose* (production → harness).

---

## 8. Extraction sequence

Ordering is by real dependency, not by severity. Every phase ends with
`make ci-check` green (B5), and every phase shrinks
`scripts/architecture/violations-baseline.txt`.

| Phase | Work | Why it can ship alone | ci-check impact |
|---|---|---|---|
| **P0 — Law with a baseline** | Add `scripts/architecture/layers.yaml`, `import_matrix.py`, `violations-baseline.txt`, and `tests/unit/architecture/test_module_law.py`. Baseline = the exact current violation set (383 private reach-ins, 1 cycle, 52 outbound edges past layer). | No source change; the test asserts "violations == baseline". Green on the first run and it now blocks *new* violations. | +5 tests, no source change |
| **P1 — Extract `filmspec`** | Move enums out of `schemas/_base.py`; add `PHASE_ORDER`/`gate_for`/`next_phase`; re-export from `schemas._base` and `graph._action_routing` so every existing import path still resolves. | Pure relocation behind re-exports. `PHASE_ORDER` keeps its identity, so `app/_graph_exec.py:24`, `cli/driver.py:139`, `graph/router.py:33` are untouched. | Baseline unchanged; adds filmspec↔schemas direction test |
| **P2 — Severity and phase literals** | Replace all 48 `"blocking"` comparisons with `filmspec.is_blocking`; replace the 9 `_phase_gate_updates(..., gate=...)` literals with `gate_for(phase)`. Add the duplicate-literal sweep test. | Mechanical, test-covered by existing gate tests. This is the highest-value/lowest-risk phase. | Baseline: −48 literal sites |
| **P3 — Kill private reach-ins (L3)** | Publish `orchestration.services_scope(...)`; delete the `app/_graph_exec.py` writes to `_SERVICES_CTX`; publish a `studio` runtime accessor to replace `cli/driver.py:80-81`; make `providers.credentials.env_var_for` public and move `config`'s credential check to `providers.required_credentials`; drop the concrete-adapter import from `agents/model_adapter.py:36`; fix the `artifacts`/`mcp`/`app` façade cycles. | Each is a rename + a re-export. Breaks no external contract. | Baseline: −cross-package private hits (≈20 lines) |
| **P4 — Single validation report** | `validation.save_report`/`load_latest_report` become the only writer; `qc` node stores `validation_report_ref`; MCP calls the same function; add the single-writer guard test. | The report *payload shape* is unchanged, so MCP response shapes are unchanged (B7). | Baseline: −2 duplicate writers |
| **P5 — Generation lifecycle** | Move the spend ceiling into `generation` (`approve_spend(default_ceiling_from="cost_estimate")`); make `orchestration`'s `_plan_generation_ledger` and `operations`' `approve_generation_spend` call the same API; move `_sync_generation_requests_from_ledger` from `mcp` to `orchestration.project_generation_requests`. | Both callers keep their public behaviour; only the default ceiling changes for the MCP path — a deliberate, documented behaviour fix (list it in the phase note). | Baseline: −MCP→generation edges |
| **P6 — Extract `governance`** | Move `_action_routing` gate law, `orchestrator_validators/`, `review/*` into `governance`; introduce `evaluate_phase`; make `graph.edges`/`graph.nodes.approval`/`review` call it; keep `graph._action_routing` as a re-export shim. | The 8-module graph SCC is broken by moving the validators *out* first, then the gate law; the shim keeps node imports working. | Baseline: −graph SCC |
| **P7 — Extract `projects`** | Introduce `ProjectRegistry`; make `StudioRuntime` delegate `projects`/`active_project_id`; make `mcp/tools/helpers._active_project_id` call `projects.resolve`. | Session state move; `RequestEnvelope.resolved_project_id` semantics unchanged. | Baseline: −split project authority |
| **P8 — Extract `operations`** | `app/services/` → `operations/`; introduce `OperatorBackend` with an explicit constructor; convert MCP tool handlers from `get_runtime()` to injected operations; delete `mcp/tools/helpers._services`. | The riskiest phase (112 `_services` references, 43 files, plus monkeypatch-based tests). Ship it behind the existing integration tests; do it after P1–P7 have removed the ambiguity about what a tool needs. | Baseline: −112 reference sites |
| **P9 — Split `studio` from `operations`; fix `app↔mcp`** | Move `product_gate.py` to the top layer; delete the `get_runtime` package-attribute indirection; `cli/*` → `studio`; make `StudioRuntime` a wiring object only. | Breaks the 1-edge cycle and the locator. `langgraph.json` path updates here (B7 — list it). | Baseline: −cycle, −locators |
| **P10 — Sealed** | Baseline empty; add per-module guard tests (§9); remove all re-export shims (each shim gets a `# TODO(P10)` and a guard test that fails if a *new* shim is added). | Enforcement only. | Baseline empty, law sealed |

**Deliberately last, or never:** removing the `_services` LangGraph state channel
(§10.6); renaming the MCP tools; splitting `post` (out of product scope);
touching the storage layout.

---

## 9. Guard tests (one per module)

B6 requires at least one test per module that fails if ownership regresses. All
follow the proven source-level style of
`tests/unit/artifacts/test_storage_boundary.py`.

| Module | Guard test | Fails when |
|---|---|---|
| `filmspec` | `tests/unit/filmspec/test_no_duplicate_literals.py::test_severity_literal_never_reappears` — grep `src/film_pipeline/**` excluding `filmspec/` for `"severity": "blocking"` / `== "blocking"` / `"blocking"` comparisons | anyone re-types the severity literal (F-SEV-01 regresses) |
| `filmspec` | `::test_phase_order_is_derived_not_redeclared` — assert no other module contains a list literal of ≥3 consecutive `FilmPhase` values | a second phase order appears (F-PHASE-01) |
| `schemas` | `tests/unit/schemas/test_no_io.py` — assert no module under `schemas/` imports `pathlib`, `os`, `artifacts`/`storage`, or any `open(` | payload contracts grow I/O |
| `config` | `tests/unit/config/test_config_contract.py` (exists — extend) `::test_config_does_not_import_providers` | the credential check creeps back (F-PRIV-01) |
| `kb` | `tests/unit/kb/test_kb_root.py::test_kb_path_literal_only_in_kb` | `film-knowledge-base/` reappears outside `kb/` (F-KBPATH-01) |
| `storage` | `tests/unit/artifacts/test_storage_boundary.py` (exists) + new `::test_storage_never_imports_above_l1` with the §6.3 lattice | storage grows an upward dependency |
| `providers` | `tests/unit/providers/test_adapter_port.py::test_no_module_imports_a_concrete_adapter` | `agents`/`generation` reaches a concrete adapter (F-PRIV-01) |
| `checkpoints` | `tests/unit/checkpoints/test_storage_delegation.py::test_checkpoint_files_written_only_via_project_storage` | checkpoints writes project files itself |
| `agents` | `tests/unit/agents/test_catalog_parity.py::test_catalog_and_implementations_agree_both_ways` — set-equality of `MVP_AGENTS` ids and implementation keys | F-AGENTREG-01 regresses |
| `validation` | `tests/unit/validation/test_single_report_writer.py::test_validation_report_saved_once` — AST sweep for `ArtifactType.VALIDATION_REPORT` saves; exactly one outside `validation/` is a failure | F-VAL-01 regresses |
| `generation` | `tests/unit/generation/test_spend_ceiling_single_source.py::test_ceiling_derived_only_in_generation` — no `* 1.1` / threshold literal outside `generation/`; assert graph and operations approve at the same ceiling for the same ledger | F-GEN-01 regresses |
| `post` | `tests/unit/post/test_post_does_not_import_orchestration.py` | post starts driving the graph |
| `governance` | `tests/unit/governance/test_gate_decision_is_single_source.py` — for a matrix of (phase, reports, issues, config), assert `governance.evaluate_phase` is the only place a `PhaseDecision` is produced; plus `::test_governance_imports_nothing_above_l6` — the anti-cycle invariant | F-GATE-01 regresses, or governance joins a cycle |
| `projects` | `tests/unit/projects/test_single_active_project_authority.py::test_only_project_registry_writes_active_id` — AST sweep for assignments to `active_project_id` | split authority returns (F-RUNTIME-01) |
| `orchestration` | `tests/unit/graph/test_channel_registry.py` (exists) + `test_startup_boundaries.py` (exists) + new `::test_services_scope_is_single_writer` — no module outside `studio`/`orchestration` sets the services scope | F-SVC-01 regresses |
| `operations` | `tests/unit/operations/test_mcp_does_not_touch_domain_modules.py` — AST sweep asserting `mcp/**` imports nothing from `{orchestration, storage, generation, checkpoints, agents, providers, kb, config}` | the MCP surface re-implements orchestration again |
| `mcp` | `tests/unit/mcp/test_contract_freeze.py::test_tool_names_and_schemas_unchanged` — snapshot of `make_registry()` tool names + `input_schema`/`output_schema` keys | the externally-visible contract drifts (B7) |
| `studio` | `tests/unit/app/test_composition_root_singularity.py::test_no_module_level_domain_singleton` — no mutable module-level domain object outside `studio` | the locator pattern returns (L6) |
| `devharness` | `tests/unit/testing/test_harness_isolation.py` — no production module imports `film_pipeline.devharness` (generalizes `graph/test_startup_boundaries.py:30`) | fixtures leak into production startup |

---

## 10. Where I disagree with the obvious approach

Opinionated, concrete, and each one has a cost attached.

**10.1 Over-modularization: do not split `storage` into `catalog` + `store`.**
The obvious move after F-AKIND-01 is "the kind registry is a normative model, so
it must be its own module." I disagree. `artifacts/registry.py` contains not just
the kind set but `KindSpec` payload models, migration callables, renderers, and
`validate_artifact_id` — all of which are *persistence* concerns, and all of
which the store calls in the write path (`store.py:41-47` imports four names from
it). Splitting them creates a module that exists only to be imported by one other
module, adds a hop to every save, and buys nothing that F-AKIND-01's guard test
does not buy. The fix is *one registration line declares both the kind and its
spec*, plus a parity test — not a new module.

**10.2 Over-modularization: do not split `graph/nodes/` per phase.**
A tempting "clean" structure is `phases/intake`, `phases/visual`, `phases/qc`, …
I reject it. The 8-module SCC in §2.2 shows these modules already share
`_shared.py`, `_context.py` and `_agent.py`, and the channel-registry guard test
(`tests/unit/graph/test_channel_registry.py:1-10`) exists specifically because
node boundaries silently dropped writes ("the D-009 bug class"). Splitting per
phase multiplies the number of boundaries across which a channel write can die,
for zero ownership benefit: "run a phase node" is one responsibility with one
failure mode. Keep `nodes/` as an internal subpackage of `orchestration` and fix
the *gate policy* extraction instead (P6), which is where the actual duplication
is.

**10.3 Do not introduce `common`, `shared`, or `utils`.**
There is no such module in the design and there must never be one. Every
proposed member has a home: the number-word map in
`graph/nodes/_shared.py:29-51` is constraint-extraction vocabulary → `constraints`;
`_row_attr`/`_extract_rows` in `graph/orchestrator_validators/_shared.py:14-30`
is matrix-shape access → `schemas.matrix` (typed accessors) or `filmspec`;
`_extract_script_text` is script parsing → `schemas.script`. A `utils` module is
where ownership goes to die; L3 (no private reach-ins) plus this rule is what
forces the decision.

**10.4 Do not extract a `media`/`compositor` module now.**
`generation/compositor/` (4 files) renders reference sheets with PIL, and
`frame_reviewer`/`sheet_reviewer`/`frame_heuristics`/`frame_sidecar` (4 more
files) review generated frames. These *look* like a different concern from
provider dispatch. They are not, currently: they are only ever called from the
generation path, they share `_layout.py`'s private constants
(`generation/compositor/identity.py:9` imports 10 private names from
`_layout`), and creating a `media` module now would just move a private-import
tangle behind a package boundary. Revisit only if a second caller appears.

**10.5 Contract leakage: do not add per-layer DTO mapping.**
The obvious "clean architecture" instinct is `mcp` response models → `operations`
DTOs → `orchestration` state → `schemas` payloads, four shapes with mappers
between. That is 3× the maintenance for a system whose MCP tool responses are
*already* plain dicts built by `_ok(...)`/`_error(...)`
(`mcp/tools/helpers.py:28,33`) and whose artifact payloads are already Pydantic.
My design keeps **one** payload shape per artifact (in `schemas`) and **one**
MCP response shape (owned by `mcp`), and forbids intermediate DTOs. The B7 risk
is real but it is the opposite risk: the freeze test
(`tests/unit/mcp/test_contract_freeze.py`) protects the external shape, and
mapping layers would not protect it — they would only make the freeze harder to
read.

**10.6 Cycle risk: `governance` is where this design will break, so make it
stateless.** The highest-probability way to end up with a new cycle is
`governance` needing to read graph state or write a review-package artifact, and
`orchestration` needing a `PhaseDecision`. The design's answer is deliberate and
non-negotiable: `governance` takes *values* (reports, issues, config) and returns
a *value*; it may import `storage` to read artifacts it renders, never to write,
and it may never import `orchestration`. If a future requirement needs
`governance` to mutate state, that is a signal the requirement belongs in
`orchestration` or `operations`, not in `governance`.

**10.7 Migration cost: the baseline allow-list is the honest way, and the shims
are the real risk.** Two failure modes for a modularization program this size:
(a) it never lands because the law cannot be green until the work is done, or
(b) it lands but the old boundaries survive behind re-export shims that nobody
deletes. I choose the baseline file for (a) — it converts enforcement into a
monotonic burndown that starts green. For (b) I am explicitly hostile to
permanent shims: every shim added in P1–P9 must carry `# SHIM(P<phase>)` and the
final phase's checker fails if any `SHIM(` token remains, so shim removal is
itself enforced. Without that rule, `graph._action_routing.PHASE_ORDER`,
`schemas._base.FilmPhase`, and `app.services.operator` will all still exist in
two years.

**10.8 The law I am *not* writing: no "domain modules may not import each
other".** `generation → storage` is correct and necessary. `validation →
storage` is correct. `agents → providers` is correct (with the concrete-adapter
import removed). The `AGENTS.md` rule would forbid all three. A useful law
allows the downward edges and forbids the upward ones and the cycles. Anyone who
tries to "restore" the AGENTS.md sentence as written will produce a codebase that
re-reads artifacts from disk to exchange typed data, and will break the storage
single-writer guarantee in the process.

**10.9 The biggest risk to this design.** Not the module catalog — it is the
service-locator removal (P8/P9). `_services` has 112 references across 43 files
and a *deliberate* monkeypatch contract
(`mcp/tools/__init__.py:15-21`). If P8 is attempted first, or as one big commit,
it will either break the test suite for a week or force a permanent shim that
preserves the locator. Mitigation: P1–P7 first (they are all independent of the
locator), then P8 with the guard tests already in place. Do not let anyone
reorder P8 earlier because it is the "most architectural".

---

## 11. Contract compatibility (B7) — what breaks, and where it is declared

| Contract | Change | Phase |
|---|---|---|
| MCP tool names, JSON input/output schemas, flags | **Preserved**, frozen by `test_contract_freeze.py` | — |
| LangGraph state schema | **Preserved.** The `_services` channel stays declared (`graph/state_schema.py:102,112`); it is runtime-only and already stripped before persistence. Removing it is *rejected* (§10.6 / §11, and P10 "never"). | — |
| Checkpoint / resume / rollback protocol | **Preserved.** Storage layout is untouched; `ProjectStorage` method set is guarded by an existing test. | — |
| On-disk storage layout v2 | **Preserved.** | — |
| `langgraph.json` graph path | **Changes**: `./src/film_pipeline/graph/graph.py:graph` → `./src/film_pipeline/orchestration/graph.py:graph` | **P9** (documented there; a one-line config edit) |
| Internal Python import paths (`film_pipeline.graph.*`, `film_pipeline.artifacts.*`, `film_pipeline.app.services.*`) | **Changes**, with re-export shims for one program | P1–P9 |
| MCP `approve_generation_spend` default ceiling | **Behaviour fix**: now derives the 110% ceiling from the cost estimate instead of unlimited | **P5** (documented; the only intentional behaviour change in the program) |

---

## Appendix — reproduce commands

```bash
# 1. package import matrix + edge list
python3 /tmp/matrix.py            # see §2.1 for the inlined script

# 2. module-level SCCs (cycles)
python3 /tmp/cycles.py            # Tarjan over module import graph

# 3. cycle-forming back edges
python3 /tmp/backedges.py

# 4. private reach-ins (383)
python3 /tmp/private.py

# 5. normative-model diffs (ArtifactType vs REGISTRY; PHASE_ORDER vs FilmPhase vs gates)
python3 /tmp/diff_norm.py

# 6. blocking-severity literal count (48)
grep -rn 'severity") == "blocking"\|"severity": "blocking"' src/film_pipeline --include=*.py | wc -l

# 7. service-locator footprint (112 refs / 43 files)
grep -rn "_services" src/film_pipeline --include=*.py | wc -l
grep -rln "_services" src/film_pipeline --include=*.py | wc -l

# 8. cross-package private imports
grep -rn "^\s*from .* import _[a-z]" src/film_pipeline --include=*.py
```

Scripts 1–5 were scratch analyses. The two scripts that back named findings are
inlined below; the design assumes all of them are relocated to
`scripts/architecture/` under version control as part of **P0**, because a
finding whose reproduce command lives in `/tmp` is not reproducible.

### A.1 Normative-model diff (backs F-AKIND-01 and F-PHASE-01)

```bash
python3 - <<'PY'
import ast, re
b=open('src/film_pipeline/schemas/_base.py').read(); enums={}
for n in ast.parse(b).body:
    if isinstance(n,ast.ClassDef):
        v=[x.value.value for x in n.body if isinstance(x,ast.Assign) and isinstance(x.value,ast.Constant)]
        if v: enums[n.name]=set(v)
at, fp = enums.get('ArtifactType',set()), enums.get('FilmPhase',set())
reg=open('src/film_pipeline/artifacts/registry.py').read()
specs=set(re.findall(r'_spec\(\s*"([a-z][a-z0-9_]*)"', reg))
print("registry kinds NOT in ArtifactType:", sorted(specs-at))
print("ArtifactType values NOT registered:", sorted(at-specs))
ar=open('src/film_pipeline/graph/_action_routing.py').read()
ph=re.findall(r'"([a-z_]+)"', re.search(r'PHASE_ORDER = \[(.*?)\]', ar, re.S).group(1))
pagn=set(re.findall(r'"([a-z_]+)"', re.search(r'_PHASE_AGNOSTIC_PHASES = \{(.*?)\}', ar, re.S).group(1)))
apg=set(re.findall(r'"([a-z_]+)":', re.search(r'APPROVAL_GATES = \{(.*?)\n\}', ar, re.S).group(1)))
print("PHASE_ORDER ^ FilmPhase:", set(ph) ^ fp)
print("_PHASE_AGNOSTIC_PHASES ^ (PHASE_ORDER - generation):", pagn ^ (set(ph)-{'generation'}))
print("APPROVAL_GATES ^ PHASE_ORDER:", apg ^ set(ph))
PY
```

Expected output at `fb85baa`: 12 kinds / 3 values / three empty sets.

### A.2 Module SCC sweep (backs §2.2, and is the checker behind laws L1–L2)

Build the module graph from every `Import` and `ImportFrom` (absolute, relative,
and function-body), then run Tarjan over it. Expected at `fb85baa`: 7 non-trivial
SCCs of sizes `{2, 2, 3, 3, 5, 8, 37}` — **37 cycle-forming back edges in
total**, enumerated in §2.2. The 37-node SCC is the `mcp.tools.*` facade; the
8-node SCC is the graph/gate tangle that P6 breaks.

### A.3 Private reach-in sweep (backs F-PRIV-01)

AST-walk every module; record `from <other> import _name`, `other._subpkg`, and
`alias._attr` where `alias` resolves to a module from a different package.
Expected count at `fb85baa`: **383**. The cross-package subset is enumerated
in §2.3.
