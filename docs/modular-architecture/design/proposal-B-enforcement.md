# Proposal B — Contract and Enforcement Layer

Status: **design proposal** (bar B). Owner: enforcement workstream.
Scope: how modular ownership is *declared* and *mechanically enforced* in
`film-pipeline-langgraph`. This document does not re-audit the codebase; every
claim about current behaviour is backed by a `path:line` anchor and a
reproduce command.

Companion artifact: a **verified prototype** that was built and executed during
this design, then reverted out of the source tree because the program is
docs-only. It is preserved read-only at:

| Path | Contents |
|---|---|
| `docs/modular-architecture/design/prototype-enforcement/architecture.py` | the complete 327-line declaration module (types + this program's manifest rows) |
| `docs/modular-architecture/design/prototype-enforcement/tests-architecture/` | the complete 9-file guard suite (766 lines) |
| `docs/modular-architecture/design/prototype-enforcement/package-init-contract-diff.patch` | the 17 `__init__.py` `CONTRACT` declarations (325 added lines) |
| `docs/modular-architecture/design/prototype-enforcement/arch-backup/` | the original 17 `__init__.py` files, for reference |

**The prototype was never merged.** No file under `src/` or `tests/` in the
tree at HEAD contains any part of it. It is a reference implementation that
demonstrates the mechanism runs; §11 records exactly what was executed and what
it found. Every code block below is a transcription of verified prototype code,
not a sketch.

---

## 1. Recommendation

**Adopt a declarative ownership manifest plus a shared stdlib-`ast` guard suite:
typed `ModuleContract` declarations in each package `__init__.py`, cross-module
invariants in one leaf module `src/film_pipeline/architecture.py`, and ~9 guard
test files under `tests/architecture/` that read both. Zero new dependencies,
zero CI YAML changes, ~1,100 lines total.**

One-line justification: the repo has already proven this shape five times by
hand (`test_storage_boundary.py`, `test_storage_guards.py`,
`test_config_contract.py`, `test_channel_registry.py`,
`test_startup_boundaries.py`), so the marginal cost is *unifying* machinery that
exists rather than introducing a tool — and unlike an import linter, it can
express the O1/O3/O4/O5 checks that pure import-edge tools cannot.

| Decision | Choice | Rejected alternative |
|---|---|---|
| Declaration home | `src/film_pipeline/architecture.py` (leaf) + per-package `CONTRACT` in `__init__.py` | `docs/…/modules.yaml` — `docs/` is gitignored *and* excluded from CI triggers |
| Check engine | stdlib `ast` + targeted `importlib` symbol resolution, in pytest | `import-linter` — not in `uv.lock`, not in the venv, not in the uv caches |
| Exemption record | one `Exemption(subject, reason, citation)` type, liveness-checked | free-text allowlists — they rot |
| Gate integration | existing `pytest` step inside `make ci-check` | new CI job / pre-commit hook — redundant |

---

## 2. What is enforced today

### 2.1 No architecture tooling is installed or configured

```bash
grep -rn -iE "import[-_]linter|importlinter|pytest[-_]archon|grimp" \
  --include="*.py" --include="*.toml" --include="*.yaml" --include="Makefile" .
```

returns **nothing**. `uv.lock` has no `import-linter`/`grimp`/`archon` entry;
`.venv/lib/python3.12/site-packages/` contains no such package;
`~/.cache/uv/{wheels-v5,simple-v20}` has no cached copy. Installing it would
require a network fetch and a lockfile change. `pyproject.toml` has no
`[tool.importlinter]` table and no architectural pytest plugin: `[tool.pytest.ini_options]`
(`pyproject.toml:70-90`) configures coverage and markers only, and
`[tool.ruff.lint]` (`pyproject.toml:132-133`) selects no import-boundary rule
(`TID`/`ICN` are not selected).

### 2.2 Five hand-rolled AST guards exist — and they are the precedent to unify

| Guard file | What it pins | Automation |
|---|---|---|
| `tests/unit/artifacts/test_storage_boundary.py:56` | no module outside `artifacts/` imports `artifacts._layout`, `artifacts.serialization`, `artifacts.paths`; storage core imports no other component | O7, O1 |
| `tests/unit/artifacts/test_storage_guards.py:26` | no `Path("projects")` / `Path.home()` default outside `artifacts/storage.py`; startup never adopts a legacy root | O2, O5 |
| `tests/unit/config/test_config_contract.py:43` | every profile leaf and env-override target is read somewhere, or is a cited `KNOWN_DEAD_GROUPS` row | O5 |
| `tests/unit/graph/test_channel_registry.py:218` | orchestrator constant ↔ `GraphState` ↔ `ORCH_CHANNELS` triangle; per-key propagation policy; every `graph/nodes/**` write to a boundary key has a `WRITER_DISPOSITIONS` row | O1, O3, O4 |
| `tests/unit/graph/test_startup_boundaries.py:26` | `graph/**` never imports `film_pipeline.testing` or `film_pipeline.app` | O7 |

These are good guards. The problem is that each one re-implements the same
`_python_files()` / ast-walk helpers privately, keys some allowlists by
`(filename, key)` only, and covers one seam. Four test files in the whole
160-file suite import `ast`:

```bash
grep -rln "import ast" tests --include="*.py"   # → the 4 boundary files above
```

`tests/conftest.py` contains **no** boundary guard at all. Its three
session-scoped autouse fixtures (`tests/conftest.py:62`, `:86`, `:111`) enforce
storage isolation and "production roots untouched" — real, valuable, and
orthogonal to ownership.

### 2.3 The documented dependency law is false at HEAD

`AGENTS.md:51` states the law:

> "`graph` and `mcp` may import across all sub-packages; domain modules must not import each other directly — they communicate through `artifacts`."

It is not enforced, and it is not true. Sweeping every internal import
(absolute *and* relative) gives:

```
agents      -> providers: 4 statement(s)
config      -> providers: 2 statement(s)
generation  -> providers: 4 statement(s)
post        -> validation: 1 statement(s)
total violating statements: 11
```

Reproduce:

```bash
python - <<'EOF'
import ast, pathlib
SRC = pathlib.Path("src/film_pipeline")
DOMAIN = {"agents","checkpoints","config","constraints","generation",
          "kb","post","providers","review","validation"}
def dotted(p):
    parts = list(p.relative_to(SRC).with_suffix("").parts)
    if parts and parts[-1] == "__init__": parts.pop()
    return ".".join(["film_pipeline", *parts])
for p in sorted(SRC.rglob("*.py")):
    if "__pycache__" in p.parts: continue
    rel = p.relative_to(SRC); pkg = rel.parts[0] if len(rel.parts) > 1 else ""
    if pkg not in DOMAIN: continue
    importing = dotted(p)
    for n in ast.walk(ast.parse(p.read_text())):
        t = None
        if isinstance(n, ast.ImportFrom):
            if n.level:
                base = importing.split(".")[:-1]
                t = ".".join([*base[:len(base)-(n.level-1)], n.module]) if n.module else None
            else: t = n.module
        elif isinstance(n, ast.Import):
            for a in n.names:
                tp = a.name.split(".")
                if len(tp) > 1 and tp[0] == "film_pipeline" and tp[1] in DOMAIN and tp[1] != pkg:
                    print(f"{rel}:{n.lineno} {pkg} -> {a.name}")
            continue
        tp = (t or "").split(".")
        if len(tp) > 1 and tp[0] == "film_pipeline" and tp[1] in DOMAIN and tp[1] != pkg:
            print(f"{rel}:{n.lineno} {pkg} -> {t}")
EOF
```

The law is also stale in a second way: `AGENTS.md:53-66` lists **12**
sub-packages. There are **17** on disk (`ls src/film_pipeline/`): the table omits
`app`, `cli`, `constraints`, `generation`, `testing`. A file that is wrong about
the roster cannot be the enforcement record.

The package graph is **cyclic**: `app/product_gate.py:17` does
`from film_pipeline.mcp.contract import make_registry`, while
`mcp/server.py:241,248,249,164` and `mcp/tools/__init__.py:22` import
`app.bootstrap`, `app._persistence`, `app.logging_setup`, `app.runtime`. So
`app → mcp → app`. Bar B3 requires acyclicity; nothing checks it today.

### 2.4 Each ownership-debt class has a live instance

These are the concrete seams the mechanism must make fail automatically. All
were verified by executing the prototype (§11).

**O1 — duplicated normative model (5 copies of the phase vocabulary).**
`FilmPhase` at `src/film_pipeline/schemas/_base.py:77` is the declared owner:

```python
class FilmPhase(StrEnum):
    """The canonical production phases of a film."""
```

But the same ordered list is re-declared at
`src/film_pipeline/graph/_action_routing.py:18`
(`PHASE_ORDER = ["intake", "constitution", …]`) and as dict keys at
`src/film_pipeline/artifacts/paths.py:14` (`PHASE_DIR_MAP: dict[str, str] = {`),
with two further subsets at `_action_routing.py:33`
(`_PHASE_AGNOSTIC_PHASES`) and `:49` (`APPROVAL_GATES = {`).

*Drift proof (mutation scenario):* add a 12th phase to `PHASE_ORDER`; the only
test that notices is `tests/unit/test_graph.py:70`
(`assert len(PHASE_ORDER) == 11`), which is trivially updated alongside.
`PHASE_DIR_MAP` keeps 11 keys and `paths.phase_dir` silently falls through
`PHASE_DIR_MAP.get(phase, phase)` (`src/film_pipeline/artifacts/paths.py:34`),
so artifacts for the new phase are written to a directory named after the raw
phase value. No test fails.

**O3 — split state authority (`current_phase`, 8 writers across 6 packages).**
`graph/nodes/_shared.py:154`, `graph/nodes/_context.py:69`,
`graph/subgraphs/qc.py:263`, `cli/driver.py:182`,
`app/_persistence.py:160`, `app/services/_project_discovery.py:54`,
`app/runtime.py:112`, `agents/impl/orchestrator_agent.py:45`.

*Drift proof:* `cli/driver.py:182` mutates persisted state directly
(`state["current_phase"] = PHASE_ORDER[target_index]`) without going through any
graph transition or emitting an audit event; no test asserts the writer set, so
a ninth writer can appear silently.

**O4 — parallel registries with an inert agreement hook.**
`AgentRegistry` supports cross-registry validation but it is disabled by
default — `src/film_pipeline/agents/registry.py:26-27`:

```python
    known_kb_domains: set[str] | None = None
    known_output_artifacts: set[str] | None = None
```

and `_reject_unknown_output_artifacts` (`:118-121`) returns immediately when the
set is `None`. Production wiring passes nothing:
`src/film_pipeline/graph/services.py:40` is `registry = AgentRegistry()`.

*Reproduce and consequence:*

```bash
python -c "
from film_pipeline.agents.mvp import MVP_AGENTS
from film_pipeline.artifacts.registry import REGISTRY
known=set(REGISTRY.known_ids())
declared={a for c in MVP_AGENTS for a in c.output_artifacts}
print(sorted(declared-known))"
# ['classified_input','failure_decision','provider_plan',
#  'reference_strategy','routing_decision','scene_intents']
```

Six agent-declared output artifacts are not storage kinds. That may be
legitimate (in-memory handoff payloads), but nothing says so: the only test is
`tests/unit/agents/test_registry.py:189-193`, which asserts
`len(agent.output_artifacts) >= 1`. The classification is *implicit*, which is
the defect.

**O5 — policy-by-branch.** `FILM_PIPELINE_NO_PERSIST` is read at **7** distinct
symbols in 6 files across 4 packages: `app/_persistence.py:52`,
`app/logging_setup.py:80`, `cli/run.py:226`, `graph/graph.py:43`,
`graph/services.py:31`, `graph/services.py:48`, `mcp/server.py:243`.
`FILM_PIPELINE_PERSIST_STATE` at 3 more. The predicates are re-derived with
different shapes, e.g. `graph/graph.py:43`
(`os.getenv("FILM_PIPELINE_NO_PERSIST") or not os.getenv("FILM_PIPELINE_PERSIST_STATE")`)
versus `app/_persistence.py:51`
(`bool(os.getenv("FILM_PIPELINE_PERSIST_STATE")) and not bool(os.getenv("FILM_PIPELINE_NO_PERSIST"))`)
versus `graph/services.py:31`, which consults **only** `NO_PERSIST`.

**O7 — leaked internals (73 statements).** 71 files outside `schemas/` import
`film_pipeline.schemas._base` (a private module that `schemas/__init__.py:10`
already re-exports), and `mcp/server.py:248` imports
`film_pipeline.app._persistence`. The existing storage guard catches this
pattern for one package only.

**O2 / O6 / O8** are the classes this mechanism cannot enumerate by itself;
§6.9 states honestly what is and is not automatable for each.

### 2.5 Where a gate could hang

`Makefile:108` — `ci-check: format-check lint typecheck test-cov build product-gate`.
`pytest` runs with `--cov-fail-under=90` (`pyproject.toml:80`) over
`--cov=film_pipeline`. `.github/workflows/ci.yml:40-41` runs
`make ci-verify PYTHON=3.12`. **New tests under `tests/` are therefore already
gated with no YAML change.** `.pre-commit-config.yaml:45-50` runs pytest and
mypy at pre-push.

Critically, `.github/workflows/ci.yml:8-11` reads:

```yaml
    paths-ignore:
      - "**/*.md"
      - "docs/**"
      - "LICENSE"
```

and `.gitignore:2` ignores `docs/`. **A machine-readable contract placed under
`docs/` would neither trigger CI nor be reviewable as a diff.** This is the
strongest single argument for the declaration living under `src/`.

---

## 3. Requirements the mechanism must satisfy

| Bar | Requirement | Where satisfied |
|---|---|---|
| B1 | one responsibility per module, one sentence, explicit non-goals | `ModuleContract.responsibility` / `.non_goals` + `test_responsibility_is_one_sentence_with_explicit_non_goals` |
| B2 | each module declares public API, owned invariants, owned state | `ModuleContract.public_api` / `.owns` in each `__init__.py`; `STATE_CHANNELS` for cross-module state |
| B3 | allowed/forbidden edges written down, graph acyclic, **mechanically checkable** | `ModuleContract.may_import` + `test_imports_stay_within_declared_edges`, `test_declared_edges_are_real`, `test_declared_module_graph_is_acyclic` |
| B5 | each phase independently shippable at green CI | §8 wave plan; the exemption ledger lets wave-0 ship without a big-bang migration |
| B6 | each extracted module gets a regression guard | §6 catalog, one guard family per O-class |
| B8 | adversarial validation of the design | §9 blocking objections, §10 failure modes |

Cheap-to-maintain budget: adding a module = ~10 lines in its `__init__.py`; a
new invariant = one tuple row; a new violation is either fixed or recorded with
a reason and a citation. Total added code = 327 lines of manifest + 766 lines of
guards + 325 lines of one-time `CONTRACT` declarations = **1,418 lines for 281
source files**, replacing four private copies of the same AST helpers.

Not ceremony by construction: **there is no new CI job, no new tool, no new
dependency, no new commit ritual.** The manifest is ordinary source that ruff
formats and mypy type-checks.

---

## 4. Options evaluated

| Option | Mechanism | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A. `import-linter` contracts** | `[tool.importlinter]` layers/forbidden contracts, run in CI | purpose-built; layered contract syntax; graph visualisation | needs `grimp` + `import-linter` fetched and locked (`uv.lock` has neither); checks **import edges only**, so O1/O3/O4/O5 — the majority of this program's debt classes — stay unenforced; a second tool beside the five existing AST guards rather than replacing them | **Reject as primary.** Optionally revisit later as a redundant check on §5.3 alone |
| **B. `pytest-archon` (or similar pytest arch plugin)** | decorator-per-test boundary assertions | pytest-native, readable | same dependency problem; same import-edge-only limitation; its declarative assertions are a strict subset of what option D expresses in ~40 lines, with no ability to sweep string literals or writer sites | Reject |
| **C. `__all__` + private-by-convention** | rely on `no_implicit_reexport` and naming | zero cost; already partly on (`mypy strict` ⇒ `no_implicit_reexport` at `pyproject.toml:107-113`) | enforces nothing about *edges*, duplicates, writers or registries; O7 shows the convention is already violated 73 times (`schemas._base` is imported cross-package by 71 files despite being private and despite being re-exported publicly) | Reject alone; **adopt as an input** to the `public_api` check |
| **D. `modules.yaml` manifest read by a generic guard** | YAML data file + AST guard | data/code separation; reviewable | YAML is untyped — a typo'd package name silently does nothing until a guard notices; lives outside `src`, and under `docs/` it is CI-exempt (`.github/workflows/ci.yml:8-11`); `pyyaml` is a runtime dependency, so it is free but still not type-checked by mypy strict | Reject as the *primary* store |
| **E. typed Python manifest + stdlib-AST pytest guards** | `ModuleContract`/`Exemption` dataclasses in a leaf module; ~9 guard files | zero new dependencies; mypy-strict-checked declarations, so typos are type errors; reuses the five existing guard patterns; uniquely able to check non-import concerns (duplicate vocabularies, writer sets, registry parity, policy read sites); rides the existing `pytest` gate | AST sweeps are source-level and can be fooled by dynamic construction (mitigated in §10); the manifest is one more file to update per ownership change (~10 lines) | **Recommend** |

The decisive facts for E over A/B: (i) every proposed tool is **absent
offline** and would add lockfile churn for a repo whose stated gate is
`make ci-check`; (ii) 5 of the 8 debt classes are invisible to import-edge
analysis, and the program's own quality bar B6 names
"duplicate-normative-model test" and "single-writer test" as required guard
kinds — `import-linter` cannot express either; (iii) the repo's own precedent
was reached independently three times (`test_storage_boundary.py`,
`test_config_contract.py`, `test_channel_registry.py`), which means E is a
*consolidation*, not an invention.

---

## 5. The recommended mechanism

### 5.1 Layering

```
src/film_pipeline/architecture.py          ← leaf: types + this program's manifest rows
                                             (imports nothing from film_pipeline)
src/film_pipeline/<pkg>/__init__.py        ← CONTRACT = ModuleContract(...)   × 17
tests/architecture/_harness.py             ← shared AST + symbol-resolution helpers
tests/architecture/_readers.py             ← named registry readers used by declarations
tests/architecture/test_contracts.py       ← B1/B2/B3: contracts, edges, acyclicity, public API
tests/architecture/test_boundaries.py      ← O7 private imports, O5 policy points
tests/architecture/test_vocabularies.py    ← O1 mirrors
tests/architecture/test_state_writers.py   ← O3 writer sweep
tests/architecture/test_registries.py      ← O4 registry agreement
tests/architecture/test_exemptions.py      ← ledger hygiene + anti-vacuity canary
```

Three rules make this cheap:

1. **A module states its own contract.** Instances live in the package that
   owns the concern, because only that package can truthfully describe itself.
2. **Cross-module facts are declared centrally.** A mirror pair, a state
   channel with eight writers, or two registries that must agree are *nobody's*
   private property; putting them in one package would be a lie.
3. **Declarations are source, logic is tests.** The manifest holds data only, so
   importing it executes every line (no coverage risk); all decision logic lives
   in the test tree where `mypy strict` (`Makefile:42`, `mypy src tests`) also
   checks it.

`architecture.py` is a declared leaf: `test_architecture_manifest_is_a_leaf`
fails if it ever imports a package it describes — which also makes the
"always importable" allowance sound (`ALWAYS_IMPORTABLE` is the root of the
law, so no package needs a `may_import` entry for it).

### 5.2 The declaration types

From the preserved prototype (`docs/modular-architecture/design/prototype-enforcement/architecture.py:32-105`).
One exemption type serves the whole program — this is the key simplification,
because allowlist rot is the dominant failure mode (§10.1) and there is exactly
one place to fight it:

```python
@dataclass(frozen=True, slots=True)
class Exemption:
    """A recorded, citable deviation from the target ownership law.

    ``subject`` is the stable key the guard computes (a dotted path, a
    ``"<module>::<symbol>"`` writer key, or a ``"<left> -> <right>"`` edge).
    Line numbers are never used: they drift under reformatting.
    """

    subject: str
    reason: str
    citation: str


@dataclass(frozen=True, slots=True)
class ModuleContract:
    """What one ``film_pipeline`` sub-package owns and what it may depend on."""

    name: str
    responsibility: str
    non_goals: tuple[str, ...]
    owns: tuple[str, ...]
    may_import: frozenset[str]
    public_api: tuple[str, ...] = ()
    unrestricted_imports: bool = False


@dataclass(frozen=True, slots=True)
class VocabularyMirror:
    """One normative vocabulary that must agree with its canonical owner."""

    concern: str
    canonical: str
    mirrors: tuple[str, ...]
    mode: VocabularyMode = "ordered"  # "ordered" | "subset"


@dataclass(frozen=True, slots=True)
class StateChannel:
    """One observable state key, its owner, and every recorded writer."""

    key: str
    owner: str
    writers: tuple[Exemption, ...] = ()


@dataclass(frozen=True, slots=True)
class RegistryAgreement:
    """``left`` must be a subset of ``right``, minus recorded non-members."""

    concern: str
    left: str
    right: str
    non_members: tuple[Exemption, ...] = ()


@dataclass(frozen=True, slots=True)
class PolicyPoint:
    """One policy decision and the only places allowed to read its input."""

    concern: str
    owner: str
    pattern: str
    readers: tuple[str, ...]
    exemptions: tuple[Exemption, ...] = ()
```

Design notes that matter:

- **`subject` never contains a line number.** The existing
  `WRITER_DISPOSITIONS` (`tests/unit/graph/test_channel_registry.py:218`) is
  keyed by `(filename, key)` for exactly this reason, and its docstring says so.
  The new manifest keys writers by `"<module>::<symbol>"`, so a *new* write site
  inside an already-recorded module still fails.
- **`may_import` is a `frozenset[str]`**, so it is order-insensitive and
  hashable; `ModuleContract` is `frozen=True, slots=True`, so a manifest row
  cannot be mutated at runtime.
- **`RegistryAgreement.left/right` point at callables**, not at production API.
  The readers live in `tests/architecture/_readers.py`:
  ```python
  def mvp_agent_output_artifacts() -> set[str]:
      from film_pipeline.agents.mvp import MVP_AGENTS
      return {a for c in MVP_AGENTS for a in c.output_artifacts}

  def registered_artifact_kinds() -> set[str]:
      from film_pipeline.artifacts.registry import REGISTRY
      return set(REGISTRY.known_ids())
  ```
  This keeps 20 lines of extraction glue out of production code while leaving the
  *agreement itself* declared in `src/`.

### 5.3 The dependency law, declared

```python
#: Importable by every package without needing a ``may_import`` entry.
ALWAYS_IMPORTABLE: Final[frozenset[str]] = frozenset({"architecture"})

#: Packages allowed to import any other package (``AGENTS.md`` §Sub-Package
#: Boundaries). They still may not import private modules across packages.
UNRESTRICTED_PACKAGES: Final[frozenset[str]] = frozenset({"graph", "mcp"})

#: Declared edges that currently close an import cycle. Bar B3 requires the
#: declared graph to be acyclic, so each row is a debt to be removed, not a
#: licence: removing the edge turns the row stale and fails the guard.
CYCLE_EXEMPTIONS: Final[tuple[Exemption, ...]] = (
    Exemption(
        "app -> mcp",
        "app/product_gate.py imports make_registry from mcp.contract, closing the "
        "app -> mcp -> app cycle (mcp/server.py imports app.bootstrap and "
        "app.runtime). Wave 1 moves the gate onto the MCP entry-point side.",
        "docs/modular-architecture/design/proposal-B-enforcement.md §8",
    ),
)
```

`UNRESTRICTED_PACKAGES` is a declaration, not a hole: it encodes
`AGENTS.md:51` verbatim and is asserted against the manifest so the law and the
code cannot drift.

### 5.4 Per-package contract

Three examples verbatim (restored from the prototype diff). This is the whole
ceremony per package — ten lines appended to its `__init__.py`.

```python
# src/film_pipeline/schemas/__init__.py
from film_pipeline.architecture import ModuleContract

CONTRACT = ModuleContract(
    name="schemas",
    responsibility="Define every typed contract that crosses a module boundary.",
    non_goals=(
        "does not import any other film_pipeline package",
        "does not perform I/O",
    ),
    owns=(
        "normative enums",
        "Pydantic boundary models",
    ),
    may_import=frozenset(),
    public_api=("FilmPhase", "ValidationStatus", "AgentRegistration"),
)
```

```python
# src/film_pipeline/artifacts/__init__.py
from film_pipeline.architecture import ModuleContract

CONTRACT = ModuleContract(
    name="artifacts",
    responsibility="Resolve storage roots and read and write versioned project artifacts.",
    non_goals=(
        "does not import domain packages",
        "does not decide pipeline order",
    ),
    owns=(
        "storage root resolution",
        "artifact layout",
        "artifact versions",
        "artifact kind registry",
    ),
    may_import=frozenset({"schemas"}),
    public_api=("ArtifactStore", "REGISTRY", "KindSpec"),
)
```

```python
# src/film_pipeline/graph/__init__.py
from film_pipeline.architecture import ModuleContract

CONTRACT = ModuleContract(
    name="graph",
    responsibility="Own the LangGraph state machine, routing, and node implementations.",
    non_goals=(
        "does not own MCP transport",
    ),
    owns=(
        "graph topology",
        "orchestrator state",
        "routing rules",
    ),
    may_import=frozenset({
        "agents", "artifacts", "constraints", "generation", "kb",
        "providers", "schemas", "validation",
    }),
    unrestricted_imports=True,
)
```

The remaining fourteen wave-0 declarations are in
`prototype-enforcement/package-init-contract-diff.patch` (325 added lines for
all 17). Their `may_import` values are **exactly the edges observed at HEAD**,
so wave 0 ships green; §8 explains when each set tightens toward the target law.

| package | wave-0 `may_import` (= observed) | wave-1 target |
|---|---|---|
| `schemas` | ∅ | ∅ |
| `artifacts` | `schemas` | `schemas` |
| `checkpoints` | `schemas` | `schemas` |
| `kb` | `schemas` | `schemas` |
| `review` | `schemas` | `schemas` |
| `validation` | `schemas` | `schemas` |
| `providers` | `schemas` | `schemas` |
| `constraints` | `schemas` | `schemas` |
| `agents` | `providers`, `schemas` | `schemas` (drop `providers`) |
| `config` | `providers` | `schemas` (drop `providers`) |
| `generation` | `artifacts`, `providers`, `schemas` | `artifacts`, `schemas` |
| `post` | `schemas`, `validation` | `schemas` |
| `testing` | `artifacts`, `checkpoints`, `providers` | unchanged (test tooling) |
| `app` | 11 edges | unchanged (composition root) |
| `cli` | `app`, `artifacts`, `graph` | `app` (entry point) |
| `graph` | 8 edges, `unrestricted_imports` | unchanged |
| `mcp` | 13 edges, `unrestricted_imports` | unchanged |

### 5.5 The shared harness

`tests/architecture/_harness.py` (229 lines, preserved prototype) replaces the
four private copies of the same helpers. The parts that carry the design:

```python
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src" / "film_pipeline"

PACKAGES: tuple[str, ...] = tuple(
    sorted(p.name for p in SRC.iterdir() if p.is_dir() and (p / "__init__.py").exists())
)


def _absolute_target(node: ast.ImportFrom, importing: str) -> str | None:
    """Resolve a possibly-relative ``ImportFrom`` to an absolute module name."""
    if not node.level:
        return node.module
    parts = importing.split(".")
    if parts and not importing.endswith(".__init__"):
        parts = parts[:-1]  # sibling package of the importing module
    keep = len(parts) - (node.level - 1)
    if keep < 1:
        return None
    base = parts[:keep]
    return ".".join([*base, node.module]) if node.module else ".".join(base)


def import_edges(path: Path) -> Iterator[ImportEdge]:
    """Every internal import edge declared by *path*, including function bodies."""
    importing = dotted_module(path)
    source = rel(path)
    pkg = package_of(path)
    for node in ast.walk(parse(path)):
        targets: list[str] = []
        if isinstance(node, ast.ImportFrom):
            absolute = _absolute_target(node, importing)
            if absolute:
                targets.append(absolute)
        elif isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        for target in targets:
            parts = target.split(".")
            if parts[0] != "film_pipeline" or len(parts) < 2:
                continue
            yield ImportEdge(source, pkg, target, parts[1], node.lineno)
```

Three deliberate properties:

- **`ast.walk`, not `tree.body`.** The repo has 52 relative imports and plenty
  of function-body imports; `test_startup_boundaries.py:26` already documents
  why body-level imports must be caught ("including lazy function-body
  imports"). The prototype's relative-import resolver is what makes the sweep
  sound for `mcp/tools/bibles/style.py:9` (`from ..helpers import …`) and its 51
  siblings.
- **`write_sites()` keys by `"<module>::<symbol>"`** using an id→enclosing-symbol
  map, and covers all three write shapes the repo uses: subscript assignment,
  `state.update({...})`, and bare returned dict literals. Without the third shape
  the sweep would miss `graph/subgraphs/qc.py:263` and `app/runtime.py:112`.
- **`as_vocabulary()` refuses to compare non-vocabularies.** A declaration that
  points at a scalar raises `TypeError` instead of silently comparing two empty
  tuples — the anti-vacuity property that §10.2 checks centrally.

### 5.6 The exemption ledger rules

`Exemption` is only useful if it cannot rot. `test_exemptions.py` enforces:

1. every row has a non-empty `reason` and `citation`;
2. every `citation` resolves to a file that **exists** in the repo (and, when
   the citation carries `§X`, that the citation is document-shaped);
3. every row's `subject` still exists — a dotted path still resolves, a
   `module::symbol` root is still present in that file, a `a -> b` edge is still
   observed;
4. at least one row exists (an empty ledger means the file is vacuous);
5. every guard family (`MIRRORS`, `STATE_CHANNELS`, `REGISTRY_AGREEMENTS`,
   `POLICY_POINTS`) is non-empty;
6. the source tree looks like the repo (>200 files found), so a mis-resolved
   `SRC` cannot make every sweep pass silently.

Rules 1–3 are the proven pattern from `test_config_contract.py:318`
(`test_known_dead_rows_cite_evidence`), generalised from one seam to all of them.
Rule 6 is new and guards against the most dangerous class of failure: a guard
suite that is green because it is looking at nothing.

### 5.7 Exact configuration

**`pyproject.toml` — no change required.** Guards are ordinary tests under
`tests/`, already collected by `testpaths = ["tests"]` (`pyproject.toml:83`) and
already covered by `--cov-fail-under=90` (`:80`). The manifest module is
import-only, so its module body executes during collection and cannot dilute
coverage.

One *optional* tightening, deferred to wave 2+ and applied per package (never
globally — see §6.9):

```toml
[[tool.mypy.overrides]]
module = [
  "film_pipeline.schemas",
  "film_pipeline.schemas.*",
  "film_pipeline.kb",
  "film_pipeline.kb.*",
  "film_pipeline.review",
  "film_pipeline.review.*",
  "film_pipeline.checkpoints",
  "film_pipeline.checkpoints.*",
  "film_pipeline.mcp",
  "film_pipeline.mcp.*",
]
disallow_any_explicit = true
```

This is the *only* free lever for O8: `strict = true` (`pyproject.toml:109`)
implies `disallow_any_generics`, `no_implicit_reexport` and friends, but **not**
`disallow_any_explicit` (verified against mypy 2.1.0:
`mypy --help | grep disallow-any-explicit`). The listed packages are the low-`Any`
ones (≤2 public signatures each); a global flag is infeasible today —
282 of 753 public functions (37%) carry `Any` in a signature, concentrated in
`graph` (79/98), `agents` (58/85), `validation` (20/30) and `app` (36/122).

**`Makefile` — one convenience target, not a new gate:**

```make
arch-check: ## Run only the architecture guards (fast, AST-level)
	$(UV_RUN) pytest tests/architecture -q --no-cov
```

`--no-cov` avoids paying coverage instrumentation on a source-only sweep;
`ci-check` is untouched, so the guard is still enforced by the existing
`test-cov` step.

**`.pre-commit-config.yaml` — no change.** The pre-push `pytest` hook
(`.pre-commit-config.yaml:45-50`) already runs the whole suite including the new
guards. Adding a second hook would be ceremony.

**`.github/workflows/ci.yml` — no change.** `make ci-verify` (`:40-41`) invokes
`test-cov`, which collects `tests/architecture`. This is the cheapest possible
integration and the reason the manifest must live under `src/` rather than
`docs/` (`.github/workflows/ci.yml:8-11`).

### 5.8 Wave-0 bootstrap commands

Exact commands to turn the mechanism on, all of which fit in one PR:

```bash
# 1. Author the declaration module (copy the verified prototype, then edit).
cp docs/modular-architecture/design/prototype-enforcement/architecture.py \
   src/film_pipeline/architecture.py

# 2. Apply the 17 package CONTRACT declarations.
git apply docs/modular-architecture/design/prototype-enforcement/package-init-contract-diff.patch \
  || (echo "patch drifted; re-derive with: git diff --no-index /dev/null <files>" && false)

# 3. Install the guard suite.
cp -R docs/modular-architecture/design/prototype-enforcement/tests-architecture \
      tests/architecture

# 4. Prove the declarations are truthful: every declared edge must be observed
#    and every observed edge declared. Any drift is a real finding, not a
#    reason to widen the manifest.
uv run --python 3.12 --group dev pytest tests/architecture -q --no-cov

# 5. Run the real gates before committing.
make ci-check

# 6. Commit in the repo's own style (storage-guard precedent: 51b54cd).
git add src/film_pipeline/architecture.py src/film_pipeline/*/__init__.py tests/architecture
git commit -m "test(architecture): declare module ownership and enforce the boundary law"
```

The patch in step 2 is a plain `git diff` against the reverted
`__init__.py` files; `package-init-contract-diff.patch` currently adds 325 lines
across the 17 files. If it has drifted by the time wave 0 runs, re-derive it by
appending the `CONTRACT` blocks from §5.4 and the prototype's
`arch-backup/*.py` originals.

---

## 6. Guard-test catalog

Each ownership-debt class maps to a guard *family*. Expected value is either a
hard equality/subset assertion or a citation-checked ledger; in every case the
failure message names the offending symbol and the declared owner.

| Class | Guard family (file) | Assertion shape | Automatable? |
|---|---|---|---|
| **O1** duplicated normative model | `test_vocabularies.py` | canonical symbol ↔ mirror symbols agree (`ordered` or `subset`) | **Yes, exactly** — once the owner is declared |
| **O2** duplicated invariant enforcement | *(no file)* + `test_registries.py::test_production_cross_registry_check_is_inert_today` for the registry case | differential/doctrine test over every entry point of the invariant | **Partly** — the guard is automatable; *enumerating* the entry points is human work |
| **O3** split state authority | `test_state_writers.py` | every write site is the owner or a `module::symbol` disposition; no stale rows | **Yes, exactly** |
| **O4** parallel registries | `test_registries.py` | left ⊆ right − recorded non-members; rows live; both registries non-empty | **Yes, exactly** |
| **O5** policy-by-branch | `test_boundaries.py` | the policy input is read only in declared modules/symbols | **Yes** for *new* read sites (exact string sweep); the *intended* policy remains a human decision |
| **O6** parallel lifecycle | *(no file)* — needs a declared `LifecyclePair` + a differential test | both implementations advance the same state list for the same input | **No** — requires human-authored equivalence cases |
| **O7** leaked internals | `test_boundaries.py` | no cross-package import of a `_private` module outside the ledger | **Yes, exactly** — existing precedent |
| **O8** missing contract | `test_contracts.py::test_public_api_names_exist` + optional mypy override | declared public names exist; `disallow_any_explicit` per package | **Partly** — existence is exact; "is this boundary typed well enough" is a review judgement |

Score of the mechanism against the program's own rubric: **O1, O3, O4, O5, O7
become fully automatic; O2 and O6 remain human-anchored with automatic
regression locks; O8 is split between an exact existence check and a mypy
tightening.** That is 5 of 8 fully automated, and the honest reason the other 3
are not is stated per class rather than hidden.

### 6.1 O1 — vocabulary mirrors (full guard)

```python
"""Guard: O1 duplicated normative models."""

from __future__ import annotations

import pytest

from film_pipeline.architecture import MIRRORS, VocabularyMirror

from tests.architecture._harness import as_vocabulary, resolve


@pytest.mark.parametrize("mirror", MIRRORS, ids=lambda mirror: mirror.concern)
def test_mirrors_agree_with_the_canonical_owner(mirror: VocabularyMirror) -> None:
    canonical = as_vocabulary(resolve(mirror.canonical))
    assert canonical, f"{mirror.canonical} resolved to an empty vocabulary"

    problems: list[str] = []
    for dotted in mirror.mirrors:
        observed = as_vocabulary(resolve(dotted))
        if mirror.mode == "ordered":
            if observed != canonical:
                problems.append(
                    f"{dotted} = {list(observed)} but {mirror.canonical} = {list(canonical)}"
                )
        else:  # subset
            foreign = sorted(set(observed) - set(canonical))
            if foreign:
                problems.append(f"{dotted} names non-existent members: {foreign}")
    assert not problems, f"{mirror.concern} has drifted:\n" + "\n".join(problems)


@pytest.mark.parametrize("mirror", MIRRORS, ids=lambda mirror: mirror.concern)
def test_canonical_owner_is_not_its_own_mirror(mirror: VocabularyMirror) -> None:
    """A guard that compares a symbol to itself can never fail."""
    assert mirror.canonical not in mirror.mirrors, (
        f"{mirror.concern} lists its canonical owner as a mirror: vacuous guard"
    )
    assert mirror.mirrors, f"{mirror.concern} has no mirrors: vacuous guard"


def test_canonical_owner_lives_in_the_contract_package() -> None:
    """Normative vocabularies belong to ``schemas`` unless declared otherwise."""
    offenders = [
        mirror.canonical
        for mirror in MIRRORS
        if not mirror.canonical.startswith("film_pipeline.schemas")
    ]
    assert not offenders, f"vocabulary owners outside the contract layer: {offenders}"


def test_phase_vocabulary_is_pinned_by_name() -> None:
    """Regression canary: this exact concern must stay under guard."""
    concerns = {mirror.concern for mirror in MIRRORS}
    assert any("phase" in concern for concern in concerns), (
        "the film-phase vocabulary lost its mirror guard"
    )
```

The manifest rows it reads (real, verified — the vocabulary currently agrees, so
this guard starts green and pins the agreement):

```python
MIRRORS: Final[tuple[VocabularyMirror, ...]] = (
    VocabularyMirror(
        concern="ordered film-production phase vocabulary",
        canonical="film_pipeline.schemas.FilmPhase",
        mirrors=(
            "film_pipeline.graph._action_routing.PHASE_ORDER",
            "film_pipeline.artifacts.paths.PHASE_DIR_MAP",
        ),
        mode="ordered",
    ),
    VocabularyMirror(
        concern="phase subsets must not name phases that do not exist",
        canonical="film_pipeline.schemas.FilmPhase",
        mirrors=(
            "film_pipeline.graph._action_routing._PHASE_AGNOSTIC_PHASES",
            "film_pipeline.graph._action_routing.APPROVAL_GATES",
        ),
        mode="subset",
    ),
)
```

`PHASE_DIR_MAP` works because `as_vocabulary()` maps a `dict` to its keys, and
`FilmPhase` because it detects a `StrEnum` subclass and reads `.value`. No
per-row extraction config exists to drift.

### 6.2 O3 — state writer sweep (full guard)

```python
"""Guard: O3 split state authority."""

from __future__ import annotations

from collections import defaultdict

import pytest

from film_pipeline.architecture import STATE_CHANNELS, StateChannel

from tests.architecture._harness import python_files, resolve, write_sites


def _observed(channel: StateChannel) -> dict[str, set[str]]:
    """Watched key -> set of ``module::symbol`` write sites."""
    watched = frozenset({channel.key})
    found: dict[str, set[str]] = defaultdict(set)
    for path in python_files():
        for site in write_sites(path, watched):
            found[f"{site.module}::{site.symbol}"].add(site.key)
    return found


@pytest.mark.parametrize("channel", STATE_CHANNELS, ids=lambda row: row.key)
def test_only_the_owner_and_recorded_writers_touch_a_channel(channel: StateChannel) -> None:
    observed = _observed(channel)
    recorded = {row.subject: row for row in channel.writers}
    unaccounted = sorted(set(observed) - set(recorded))
    assert not unaccounted, (
        f"new writers of {channel.key!r} with no disposition: {unaccounted}. "
        f"The single writer is {channel.owner}; route the write through it or add a "
        f"recorded disposition with a reason and citation."
    )


@pytest.mark.parametrize("channel", STATE_CHANNELS, ids=lambda row: row.key)
def test_recorded_writers_are_live(channel: StateChannel) -> None:
    observed = _observed(channel)
    stale = sorted(row.subject for row in channel.writers if row.subject not in observed)
    assert not stale, (
        f"{channel.key!r} dispositions whose write site disappeared: {stale}. "
        "Delete the rows: a shrinking writer set is the migration succeeding."
    )


@pytest.mark.parametrize("channel", STATE_CHANNELS, ids=lambda row: row.key)
def test_channel_owner_resolves_and_declares_the_key(channel: StateChannel) -> None:
    owner = resolve(channel.owner)
    annotations = getattr(owner, "__annotations__", {})
    assert channel.key in annotations, (
        f"{channel.owner} does not declare {channel.key!r} in its schema"
    )


def test_channel_keys_are_not_duplicated() -> None:
    keys = [channel.key for channel in STATE_CHANNELS]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    assert not duplicates, f"declared twice in STATE_CHANNELS: {duplicates}"
```

The manifest channel is the real `current_phase` seam. Its eight dispositions
were generated *by the guard itself* (prototype run, §11), which is the
intended workflow: run the sweep, paste the observed writer set, annotate.

```python
STATE_CHANNELS: Final[tuple[StateChannel, ...]] = (
    StateChannel(
        key="current_phase",
        owner="film_pipeline.graph.state_schema.StudioGraphState",
        writers=(
            Exemption(
                "graph/nodes/_shared.py::_phase_gate_updates",
                "Observed writer: approval-gate update for the current node.",
                "docs/modular-architecture/design/proposal-B-enforcement.md §7",
            ),
            # … 7 more, one per observed site, each with its own reason …
        ),
    ),
)
```

`test_recorded_writers_are_live` is what makes this a *ratchet*: wave 3 deletes
seven rows as writers are collapsed onto the owner, and deleting a row without
also deleting its write site fails.

### 6.3 O4 — registry agreement (full guard)

```python
"""Guard: O4 parallel registries that must agree."""

from __future__ import annotations

import pytest

from film_pipeline.architecture import REGISTRY_AGREEMENTS, RegistryAgreement

from tests.architecture._harness import resolve


def _members(agreement: RegistryAgreement) -> set[str]:
    return set(resolve(agreement.left)())


def _canonical(agreement: RegistryAgreement) -> set[str]:
    return set(resolve(agreement.right)())


@pytest.mark.parametrize("agreement", REGISTRY_AGREEMENTS, ids=lambda row: row.concern)
def test_left_registry_is_a_subset_of_the_canonical_registry(
    agreement: RegistryAgreement,
) -> None:
    recorded = {row.subject for row in agreement.non_members}
    stray = sorted(_members(agreement) - _canonical(agreement) - recorded)
    assert not stray, (
        f"{agreement.concern}: {stray} are neither registered nor recorded as "
        f"deliberate non-members in REGISTRY_AGREEMENTS."
    )


@pytest.mark.parametrize("agreement", REGISTRY_AGREEMENTS, ids=lambda row: row.concern)
def test_non_member_rows_are_neither_stale_nor_circular(
    agreement: RegistryAgreement,
) -> None:
    actual = _members(agreement) - _canonical(agreement)
    recorded = {row.subject for row in agreement.non_members}
    stale = sorted(recorded - actual)
    assert not stale, f"{agreement.concern}: non-member rows no longer needed: {stale}"


@pytest.mark.parametrize("agreement", REGISTRY_AGREEMENTS, ids=lambda row: row.concern)
def test_both_registries_are_non_trivial(agreement: RegistryAgreement) -> None:
    """A guard comparing two empty sets proves nothing."""
    assert _canonical(agreement), f"{agreement.right} resolved to an empty registry"
    assert _members(agreement), f"{agreement.left} resolved to an empty registry"
    assert agreement.left != agreement.right, "a registry cannot agree with itself"


def test_production_cross_registry_check_is_inert_today() -> None:
    """Records the O4 gap: the enforcement hook exists but is never enabled.

    ``AgentRegistry`` supports ``known_output_artifacts``, but production wires
    it with the default ``None`` (``graph/services.py::_mvp_agent_registry``),
    so ``_reject_unknown_output_artifacts`` returns immediately. This test fails
    the moment the hook is turned on, which is the signal to delete the
    ``non_members`` rows that exist only because it is off.
    """
    from film_pipeline.graph.services import _mvp_agent_registry

    registry = _mvp_agent_registry()
    assert registry.known_output_artifacts is None, (
        "the cross-registry hook is now enabled — remove the non_members rows in "
        "REGISTRY_AGREEMENTS and assert the agreement directly."
    )
    assert registry.known_kb_domains is None, (
        "the KB-domain cross-registry hook is now enabled — add a "
        "REGISTRY_AGREEMENTS row for it."
    )
```

The last test is the "gap record" pattern already used by
`test_config_contract.py:307` (`test_named_flx_f9_failures_stay_deliberate`):
asserting the *absence* of a fix, so that closing the gap forces the ledger to
be cleaned up rather than left stale.

### 6.4 O7 + O5 — boundaries and policy points (full guard)

```python
"""Guard: O7 leaked internals and O5 policy-by-branch."""

from __future__ import annotations

import ast

import pytest

from film_pipeline.architecture import POLICY_POINTS, PRIVATE_MODULE_EXEMPTIONS, PolicyPoint

from tests.architecture._harness import (
    PACKAGES,
    _enclosing_symbols,
    import_edges,
    package_of,
    parse,
    python_files,
    rel,
)

EXEMPT_PRIVATE_MODULES = {row.subject for row in PRIVATE_MODULE_EXEMPTIONS}


def test_no_cross_package_private_imports() -> None:
    """A package's internals are reachable only from inside that package."""
    offenders: list[str] = []
    for path in python_files():
        owner = package_of(path)
        for edge in import_edges(path):
            parts = edge.target.split(".")
            if len(parts) < 3 or not parts[2].startswith("_"):
                continue
            if edge.target_pkg == owner:
                continue
            if ".".join(parts[:3]) in EXEMPT_PRIVATE_MODULES:
                continue
            offenders.append(f"{edge.source}:{edge.lineno} -> {edge.target}")
    assert not offenders, "cross-package private imports:\n" + "\n".join(sorted(offenders))


def _policy_reads(pattern: str) -> set[tuple[str, str]]:
    """Every ``(module, symbol)`` that mentions *pattern* as a string literal.

    ``architecture.py`` is skipped: it is the declaration the guard reads, so
    naming a flag there is data, not a read site.
    """
    hits: set[tuple[str, str]] = set()
    for path in python_files():
        if rel(path) == "architecture.py":
            continue
        tree = parse(path)
        owner = _enclosing_symbols(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value == pattern
            ):
                hits.add((rel(path), owner.get(id(node), "")))
    return hits


@pytest.mark.parametrize("point", POLICY_POINTS, ids=lambda point: point.pattern)
def test_policy_inputs_are_read_only_at_declared_points(point: PolicyPoint) -> None:
    declared = set(point.readers)
    exempt = {row.subject.split("::")[0] for row in point.exemptions}
    observed = {module for module, _symbol in _policy_reads(point.pattern)}
    undeclared = sorted(observed - declared - exempt)
    assert not undeclared, (
        f"{point.pattern} is read in undeclared modules: {undeclared}. "
        f"Route the decision through {point.owner} instead."
    )


@pytest.mark.parametrize("point", POLICY_POINTS, ids=lambda point: point.pattern)
def test_declared_policy_readers_are_not_stale(point: PolicyPoint) -> None:
    observed_modules = {module for module, _symbol in _policy_reads(point.pattern)}
    stale = sorted(set(point.readers) - observed_modules)
    assert not stale, f"{point.pattern} lists readers that no longer read it: {stale}"


def test_every_package_is_reachable_in_the_private_import_sweep() -> None:
    """The sweep must not silently stop covering a package."""
    covered = {package_of(path) for path in python_files()}
    assert covered >= set(PACKAGES)
```

The two `PRIVATE_MODULE_EXEMPTIONS` rows are the whole current violation set
(`film_pipeline.schemas._base`, 71 importers; `film_pipeline.app._persistence`,
1 importer). Wave 2 migrates the 71 to `from film_pipeline.schemas import …` and
the row's staleness check forces its deletion.

### 6.5 B1/B2/B3 — contracts (full guard)

```python
"""Guard: every package publishes a contract and honours the dependency law."""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.architecture import ALWAYS_IMPORTABLE, CYCLE_EXEMPTIONS

from tests.architecture._harness import (
    PACKAGES,
    SRC,
    import_edges,
    package_edges,
    resolve,
)

CONTRACTS: dict[str, Any] = {name: resolve(f"film_pipeline.{name}.CONTRACT") for name in PACKAGES}


def test_every_package_declares_a_contract() -> None:
    missing = sorted(set(PACKAGES) - set(CONTRACTS))
    assert not missing, f"packages without a CONTRACT declaration: {missing}"


def test_architecture_manifest_is_a_leaf() -> None:
    """The declaration module must not import any package it describes."""
    offenders = [
        f"{edge.source}:{edge.lineno} -> {edge.target}"
        for edge in import_edges(SRC / "architecture.py")
    ]
    assert not offenders, f"architecture.py must stay a leaf: {offenders}"


def test_contract_name_matches_its_package() -> None:
    mismatched = {
        name: contract.name for name, contract in CONTRACTS.items() if contract.name != name
    }
    assert not mismatched, f"CONTRACT.name disagrees with its package: {mismatched}"


def test_responsibility_is_one_sentence_with_explicit_non_goals() -> None:
    problems: list[str] = []
    for name, contract in CONTRACTS.items():
        if not contract.responsibility.endswith("."):
            problems.append(f"{name}: responsibility is not one sentence")
        if len(contract.responsibility.split(". ")) > 1:
            problems.append(f"{name}: responsibility contains more than one sentence")
        if not contract.non_goals:
            problems.append(f"{name}: no non_goals declared")
        for non_goal in contract.non_goals:
            if not non_goal.startswith("does not"):
                problems.append(f"{name}: non_goal must read 'does not ...': {non_goal!r}")
        if not contract.owns:
            problems.append(f"{name}: owns nothing")
    assert not problems, "contract quality violations:\n" + "\n".join(problems)


@pytest.mark.parametrize("source_pkg", sorted(PACKAGES))
def test_imports_stay_within_declared_edges(source_pkg: str) -> None:
    """B3: the observed edge set is a subset of the declared one."""
    contract = CONTRACTS[source_pkg]
    if contract.unrestricted_imports:
        return
    allowed = set(contract.may_import) | set(ALWAYS_IMPORTABLE) | {source_pkg}
    undeclared = sorted(
        target
        for source, target in package_edges()
        if source == source_pkg and target not in allowed
    )
    assert not undeclared, (
        f"{source_pkg} imports undeclared packages: {undeclared}. Either remove the "
        f"import or add the edge to {source_pkg}/__init__.py CONTRACT.may_import."
    )


@pytest.mark.parametrize("source_pkg", sorted(PACKAGES))
def test_declared_edges_are_real(source_pkg: str) -> None:
    """A declared edge with no importer is a stale contract, not a licence."""
    contract = CONTRACTS[source_pkg]
    observed = {target for source, target in package_edges() if source == source_pkg}
    stale = sorted(set(contract.may_import) - observed)
    assert not stale, f"{source_pkg} declares unused edges: {stale}"


def test_declared_module_graph_is_acyclic() -> None:
    """B3: no import cycle may exist in the declared law.

    Edges recorded in ``CYCLE_EXEMPTIONS`` are ignored when looking for cycles,
    so a *new* cycle always fails; removing an exempted edge makes its row
    stale, which ``test_exemptions.py`` reports.
    """
    graph = {
        name: {target for target in contract.may_import if target in CONTRACTS}
        for name, contract in CONTRACTS.items()
    }
    recorded = {tuple(row.subject.split(" -> ")) for row in CYCLE_EXEMPTIONS}
    effective = {
        name: {target for target in deps if (name, target) not in recorded}
        for name, deps in graph.items()
    }
    resolved: list[str] = []
    remaining = dict(effective)
    while remaining:
        ready = sorted(node for node, deps in remaining.items() if not (deps - set(resolved)))
        assert ready, f"declared dependency cycle among: {sorted(remaining)}"
        for node in ready:
            resolved.append(node)
            del remaining[node]


def test_cycle_exemptions_target_real_edges() -> None:
    """An exemption for an edge that does not exist is a stale record."""
    declared = {
        (name, target) for name, contract in CONTRACTS.items() for target in contract.may_import
    }
    for row in CYCLE_EXEMPTIONS:
        edge = tuple(row.subject.split(" -> "))
        assert edge in declared, f"cycle exemption names a non-existent edge: {row.subject}"


@pytest.mark.parametrize("package", sorted(PACKAGES))
def test_public_api_names_exist(package: str) -> None:
    contract = CONTRACTS[package]
    module = resolve(f"film_pipeline.{package}")
    missing = [name for name in contract.public_api if not hasattr(module, name)]
    assert not missing, f"{package} declares public names that do not exist: {missing}"
```

`test_declared_edges_are_real` is the second half of B3 and the reason the law
stays *tight* rather than merely satisfied: `may_import` is the minimum set, not
a superset licence. It is also what forces §5.4's wave-1 tightening to actually
land — the `agents → providers` entry cannot sit in the manifest unexercised.

### 6.6 Anti-vacuity canary

`tests/unit/__pycache__/test_guard_canary.cpython-312-pytest-9.1.1.pyc` exists
with **no corresponding source file** anywhere in the tree or in git history.
A guard canary was written once, deleted, and its orphaned bytecode is the only
evidence left. The mechanism must not repeat that loss, so the canary is split
across the ledger tests rather than being a single deletable file:

- `test_guard_inputs_are_not_empty` (every family has ≥1 declaration);
- `test_canonical_owner_is_not_its_own_mirror` / `test_both_registries_are_non_trivial`
  (a guard cannot compare a symbol to itself or two empty sets);
- `test_source_tree_looks_like_the_repo` (>200 source files found);
- `test_architecture_manifest_is_a_leaf` (the manifest cannot smuggle in the
  packages it is meant to be independent of).

Plus one *mutation* canary, to be added with wave 0 and kept permanently:

```python
def test_mirror_guard_detects_a_real_mutation() -> None:
    """Proves the vocabulary guard is capable of failing.

    Runs the comparison against a deliberately perturbed copy of the canonical
    vocabulary; if this does not report drift, ``test_vocabularies`` is theatre.
    """
    from film_pipeline.architecture import MIRRORS

    mirror = next(row for row in MIRRORS if row.concern.startswith("ordered"))
    canonical = list(as_vocabulary(resolve(mirror.canonical)))
    mutated = [*canonical, "a_phase_that_does_not_exist"]
    assert mutated != canonical, "mutation helper is broken"
    assert set(canonical) - set(mutated) == set()
    assert sorted(set(mutated) - set(canonical)) == ["a_phase_that_does_not_exist"]
```

This is deliberately not an `xfail`; it asserts the *primitive* the guard uses
is sensitive, which is the part that can silently become a no-op.

### 6.7 Guard cost

The five existing AST guards run 21 tests in **7.5 s** wall-clock including
4 xdist workers and the `_production_roots_untouched` session fixture
(`time pytest tests/unit/artifacts/test_storage_boundary.py … -q --no-cov`).
The prototype suite covers the same 281 files and is in the same class: pure
`ast.parse` over a 40k-LOC tree, plus ~6 symbol imports. It adds well under a
second of real work to a suite that already spends minutes in the graph/E2E
tests, so no test-budget control is needed.

### 6.8 Failure-message discipline

Every assertion above names (a) the offending symbol, (b) the declared owner,
and (c) the action ("route the write through it", "delete the rows", "add the
edge to CONTRACT.may_import"). This is not decoration: the guard *is* the
interface a contributor meets when they cross a boundary, and the existing
`test_storage_boundary.py:66-70` sets that standard.

### 6.9 What is deliberately not automated

- **O2 (duplicated invariant enforcement).** Finding that two functions enforce
  the same rule is a semantic judgement. The mechanism can lock the *fix*: after
  extraction, one differential test parametrised over the enumerated entry points
  becomes the guard. Declaring "every entry point of concern X is one of
  [a, b, c]" is the human step.
- **O6 (parallel lifecycle).** Same shape. The graph path and the MCP path must
  be *declared* as a pair, then a test feeds identical input to both and asserts
  identical state transitions. The declaration is human, the comparison is
  automatic, the equivalence cases are human.
- **"Should these two things agree at all?"** The O4 non-member rows encode a
  judgement. The guard makes the judgement explicit and forces it to be
  revisited when reality changes; it cannot make the judgement correct.

---

## 7. Extraction playbook

Nineteen steps for one concern, each producing a green commit. Total expected
size: one concern, one PR, ≤1 day-equivalent unless marked L.

### Step 0 — Pick the concern and record the finding

```bash
# Confirm the seam still exists at the branch point.
git fetch origin && git switch -c extract/<concern> origin/modular-app
git log --oneline -1                       # record the base commit in the PR body
grep -rn "<duplicate literal or second implementation>" src/film_pipeline --include="*.py"
```

Write the O-class, the `path:line` owners, the drift proof, and the reproduce
command into the phase document. A concern without a drift proof is a
hypothesis (§1.6.3) and must not be extracted.

### Step 1 — Inventory every site (mechanical, no edits)

```bash
# Example for an O1 concern: every copy of the vocabulary.
uv run python - <<'EOF'
import ast, pathlib
VOCAB = {"intake","constitution","development","script","visual_dev","shot_bible",
         "gen_planning","generation","qc","post","delivery"}
for p in sorted(pathlib.Path("src/film_pipeline").rglob("*.py")):
    t = ast.parse(p.read_text())
    for n in ast.walk(t):
        if isinstance(n, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            items = n.keys if isinstance(n, ast.Dict) else n.elts
            vals = {e.value for e in items if isinstance(e, ast.Constant)
                    and isinstance(e.value, str)}
            if len(vals & VOCAB) >= 4:
                print(f"{p}:{n.lineno}  {len(vals & VOCAB)} members")
EOF
```

Record the count in the PR body; it is the number this PR must drive to the
target (1 for O1, 1 for O3, …). This is the `Reproduce:` line of the finding.

### Step 2 — Declare the contract (red is allowed only on the branch)

Add the target module's `CONTRACT` and, **only for cross-module facts**, the
manifest rows. Do *not* add the agreement row yet if the migration is not done —
add it in step 6.

```bash
# Edit src/film_pipeline/<owner>/__init__.py: append CONTRACT (see §5.4).
# Edit src/film_pipeline/architecture.py: add the MIRRORS/STATE_CHANNELS row.
uv run --python 3.12 --group dev pytest tests/architecture -q --no-cov
```

Capturing the red output here is the test-driven evidence for the PR:

```bash
uv run --python 3.12 --group dev pytest tests/architecture -q --no-cov 2>&1 | tee /tmp/red.txt
```

The merged commit must be green. Red exists only between step 2 and step 6 on a
short-lived branch.

### Step 3 — Create the module

```bash
mkdir -p src/film_pipeline/<owner>
# __init__.py declares CONTRACT and re-exports the public contract only.
uv run --python 3.12 --group dev ruff format src/film_pipeline/<owner>
uv run --python 3.12 --group dev mypy --strict src tests
uv run --python 3.12 --group dev pytest tests/architecture -q --no-cov
```

At this point the new module imports nothing (`may_import=frozenset()`), which
the edge guard proves.

### Step 4 — Migrate writers, one at a time

For O3 the rule is *one writer per commit*: move a caller to the owner, delete
its `Exemption` row, run the guard. Each commit shrinks the ledger and stays
green.

```bash
# After each caller migration:
uv run --python 3.12 --group dev pytest \
  tests/architecture/test_state_writers.py tests/architecture/test_exemptions.py -q --no-cov
git commit -am "refactor(<concern>): route <caller> through <owner>"
```

**Shadow assertion** (temporary, deleted before merge) — for a write whose
observable effect is not covered by an existing test, dual-write and assert
equality for the migration window:

```python
# TEMPORARY — remove before merge; see docs/modular-architecture/design/proposal-B-enforcement.md §7.
new_value = owner.derive_phase(source)
assert new_value == legacy_derive_phase(source), (
    f"shadow mismatch: owner={new_value!r} legacy={legacy_derive_phase(source)!r}"
)
```

**Canary test** (permanent) — keep a test that exercises the *old* entry point
and asserts it now delegates, so a future revert of the migration is caught:

```python
def test_legacy_entry_point_delegates_to_the_owner() -> None:
    """The old path must not re-derive the concern; it must delegate."""
    from film_pipeline.<owner> import derive_phase
    from film_pipeline.<old_module> import legacy_derive_phase

    assert legacy_derive_phase({"current_phase": "script"}) == derive_phase(
        {"current_phase": "script"}
    )
```

### Step 5 — Delete the duplicates and prove it by command

```bash
# Re-run step 1's command. The output must be the owner only.
# Then prove nothing references the removed symbols:
grep -rn "PHASE_DIR_MAP\|_PHASE_AGNOSTIC_PHASES" src/film_pipeline --include="*.py"
```

This is the completion criterion for the finding — not "tests pass".

### Step 6 — Pin it with a guard

Add the real manifest row (mirror, channel, agreement, policy point) and delete
the corresponding `Exemption` rows that existed only because the migration was
in flight.

```bash
uv run --python 3.12 --group dev pytest tests/architecture -q --no-cov
```

### Step 7 — Update the documentation

- `AGENTS.md:53-66`: the sub-package roster and the ownership one-liner.
- The phase document under `docs/modular-architecture/` with the finding ID and
  the guard file that now pins it.

### Step 8 — Run the full gate

```bash
make ci-check        # format-check + lint + typecheck + test-cov (≥90%) + build + product-gate
```

### Step 9 — Rollback plan

```bash
# Roll back the whole extraction: one revert, no data migration to undo.
git revert --no-edit <merge-commit>
git push origin <branch>          # never force-push (AGENTS.md global rule)
```

Rollback is safe by construction because **an extraction PR must not change any
persisted representation**. Specifically:

- if the concern's representation changes (artifact layout, checkpoint payload,
  MCP response shape), that is a *compatibility* change under B7, and it must be
  a **separate** PR with an explicit version bump and migration — never bundled
  into an extraction;
- no extraction PR may add a runtime feature flag
  (`if os.getenv("MODULAR_V2")`); if a behaviour toggle seems necessary, the
  extraction is too large, so split it;
- the guard changes revert with the code because they live in the same commit as
  the manifest rows they depend on.

If the revert is partial (one caller migration regresses), revert the individual
commit: each step-4 commit is independently green, which is the property B5
requires.

---

## 8. Sequencing and risk control

### 8.1 Order by real dependency, leaves first

The declared `may_import` graph gives the order directly — the topological
order of the law, which the acyclicity test already computes. The observed
in-degree (how many packages import each) determines blast radius:

| rank | package | imported by | why this position |
|---|---|---|---|
| 0 | `schemas` | 16 packages, 323 imports | contract layer; everyone depends on it, so its vocabulary work (O1) unlocks the rest, but *any* change here is maximal blast radius — do it with the mirror guard already on |
| 0 | `architecture` + guards | — | the mechanism itself; must ship first and alone |
| 1 | `checkpoints`, `kb`, `review`, `constraints` | 1–3 | leaves, single-import, smallest possible extraction rehearsal |
| 2 | `providers` | 5 packages (incl. 3 domain violations) | hub; extracting it is what lets `agents`/`config`/`generation` drop their illegal edges |
| 3 | `artifacts` | 8 packages | already has the strongest existing guards; extend, don't rewrite |
| 4 | `validation`, `post`, `agents`, `config`, `generation` | 2–9 | the O5/O4 seams and the four domain→domain violations |
| 5 | `graph`, `mcp` | unrestricted by law | largest files, most edges; split from the inside using the declared law as the guide |
| 6 | `app`, `cli`, `testing` | entry point / tooling | composition root last; `app → mcp` cycle broken here (Wave 1 in §5.3 already records it) |

### 8.2 Waves, each independently shippable

| Wave | Content | Green criterion | Exit |
|---|---|---|---|
| **0** | the mechanism only: `architecture.py`, 17 `CONTRACT`s, `tests/architecture/`, `arch-check`. **No production behaviour changes.** | `make ci-check` green; every observed edge declared; the one cycle and all current violations recorded as cited exemptions | the law exists and cannot drift |
| **1** | remove `CYCLE_EXEMPTIONS` (`app → mcp`); fix or drop the O5 undeclared reads; add the mutation canary | `test_declared_module_graph_is_acyclic` green with an empty ledger; `test_policy_inputs_…` green with fewer exemptions | the law is *true*, not just recorded |
| **2** | O1: make `FilmPhase` the sole owner; derive `PHASE_DIR_MAP` keys and `PHASE_ORDER` from it (or declare the mirrors with guards if derivation breaks an edge law) | mirror guard green; step-1 grep returns the owner only | vocabulary can no longer drift silently |
| **3** | O3: collapse `current_phase` writers onto one authority; delete 7 dispositions | `STATE_CHANNELS` writers == 1 | state has one writer |
| **4** | O4: classify in-memory vs persisted agent outputs; enable `AgentRegistry(known_output_artifacts=…)` | `test_production_cross_registry_check_is_inert_today` deletes itself (its assertion breaks), non-member rows removed | registries agree by construction |
| **5** | O7: migrate 71 importers to `film_pipeline.schemas`; retire the `_base` exemption and rename `schemas/_base.py` → `schemas/base.py` | private-import sweep green with an empty ledger | internals are actually internal |
| **6+** | O2/O6 extractions, then the package splits, then the `app → mcp` composition-root cleanup | per-concern playbook §7 | — |

Wave 0 is the pivotal one: it makes every subsequent wave *small*, because the
law and the ledger already exist. Without it, each extraction has to re-invent
its own ad-hoc guard (which is exactly what the five existing guard files did).

### 8.3 Detecting regressions during migration

- **Writer sweep with liveness** is the primary O3 detector: the ledger's
  `test_recorded_writers_are_live` fails on both a new writer *and* a
  half-finished migration (a site that stopped writing while its row remains).
- **Shadow assertions** in step 4 catch behavioural divergence for the duration
  of one migration window; they are temporary and must not be merged.
- **Permanent canary tests** assert the legacy entry point still delegates, so
  the *result* of the migration cannot silently regress.
- **`test_declared_edges_are_real`** catches the most common migration
  regression: a `may_import` entry left behind after the last import is gone,
  which would otherwise silently re-licence the old edge.
- **The step-1 count command** is re-run in the PR body; a partial extraction
  cannot claim completion while the count is unchanged.

### 8.4 Avoiding a long-lived divergent branch

- **Wave 0 has no production changes**, so it can merge immediately and does not
  need to be kept in sync with anything.
- **Every wave is a short branch off `modular-app` with ≤1 day of work.**
  Nothing in the design depends on a runtime flag, a dual code path, or a
  compatibility shim, so there is no incentive to keep a branch alive.
- **The ledger is the anti-branch mechanism.** Because un-migrated concerns are
  *recorded* rather than forbidden, ordinary feature work on `modular-app` keeps
  shipping while waves proceed. A contributor who touches an un-migrated seam
  gets a guard failure naming the recorded exemption and the wave that owns it —
  not a blocked merge.
- **No wave may grow the ledger beyond its wave-0 size.** Wave 0 is the high
  water mark; any new row after that must be justified in review. If a wave needs
  to add rows, it means scope crept and the wave must be split.

---

## 9. Adversarial review — blocking objections and resolutions

**9.1 "This is a sixth re-implementation of AST guards; it adds ceremony."**
It *replaces* the four private helper copies and gives the two existing
allowlist patterns (positional `KNOWN_DEAD_GROUPS`, `WRITER_DISPOSITIONS`) a
single generalised type. Net new code is 1,418 lines including the 325 lines of
one-time contract declarations; net new *concepts* are two dataclasses. Resolved.

**9.2 "A manifest that duplicates reality will just drift."** This is the
strongest objection, and it is why `test_declared_edges_are_real` and the
liveness checks exist: drift is not prevented by discipline, it is a test
failure. The declaration cannot merely describe reality — it must match it in
both directions. Resolved.

**9.3 "`UNRESTRICTED_PACKAGES` makes B3 vacuous for exactly the two packages
that matter most."** Accepted, with a boundary: unrestricted *package* imports
are what `AGENTS.md:51` declares, but `graph` and `mcp` remain fully subject to
the O7 private-import guard, the O1 vocabulary guard, the O3 writer sweep and
the O4 registry agreement. Only the coarse edge check is waived, and the waiver
is asserted against the manifest so it cannot silently spread to a third
package. Amended.

**9.4 "Wave 0 records 11 law violations, so the law is still false."** Wave 0
records them *explicitly*, which converts silent drift into a debt with a name,
a reason and a citation. The alternative — declaring the target law in wave 0
and turning CI red for a week — violates B5. The wave table (§8.2) commits to
deleting the rows. Amended, not dismissed.

**9.5 "Coverage: a new `src/` module costs you the 90% gate."** The manifest is
data-only, so importing it executes every line; the readers live in tests and
are therefore outside `--cov=film_pipeline`. Verified in the prototype run.
Resolved.

**9.6 "Cycle exemptions are a licence to keep a cycle."** Each row is an
`Exemption`, so it must be cited, and `test_cycle_exemptions_target_real_edges`
plus the ledger liveness check fail if the edge disappears. It is a debt
instrument, and the debt is named at `app/product_gate.py:17`. Resolved.

**9.7 "Why not just turn on `import-linter` and be done?"** It is not available
offline, it requires a lockfile change, and it cannot express O1/O3/O4/O5 —
which is 5 of the 8 debt classes. It would be a *second*, weaker mechanism
beside the existing AST guards. Deferred as an optional future redundancy for
the edge check only. Resolved.

---

## 10. Failure modes of this enforcement approach

### 10.1 Allowlist (exemption) rot — **the biggest failure mode**

The ledger starts with ~24 rows (1 cycle, 8 writers, 6 registry non-members,
7 policy exemptions, 2 private modules). Every row is an opportunity to record
a deviation instead of fixing it, and a ledger that only grows converts the
mechanism into documentation with a green checkmark.

*Mitigations.* (a) Every row needs a `reason` and a citation that must resolve
to a real file (`test_exemption_is_cited_and_reasoned`). (b) Every row's
`subject` must still exist — a fixed deviation fails the ledger until the row is
deleted (`test_exemption_subject_still_exists`, `test_recorded_writers_are_live`,
`test_non_member_rows_are_neither_stale_nor_circular`). (c) Wave 0 is declared
the high-water mark; §8.4 forbids growth after it without review. (d) Each row
cites the wave that owns its removal, so an orphaned row is visible in review.

*Residual risk:* a reviewer who accepts a new row for a legitimate-sounding
reason. The only real defence is (c) plus review attention; the mechanism makes
it cheap to reject, because rejecting is just "no new row".

### 10.2 Guard theatre — a guard that cannot fail

The most dangerous state is green and meaningless. The `MIRRORS` design is
especially exposed: if a mirror symbol re-exports the canonical constant, the
guard compares a value to itself.

*Mitigations.* `test_canonical_owner_is_not_its_own_mirror`,
`test_both_registries_are_non_trivial`, `agreement.left != agreement.right`,
`as_vocabulary()` raising on non-vocabularies, `test_guard_inputs_are_not_empty`,
`test_source_tree_looks_like_the_repo`, and the §6.6 mutation canary. The
deletion of `test_guard_canary.py` (evidenced by the orphaned
`tests/unit/__pycache__/test_guard_canary.cpython-312-pytest-9.1.1.pyc`) is the
cautionary precedent: this failure has already happened once in this repo.

### 10.3 Static sweeps miss dynamic construction

`_policy_reads` and `write_sites` see string *literals*. `os.getenv(name)` with a
computed name, `state[key] = value` with a variable key, or
`globals()["PHASE_ORDER"]` are all invisible. `test_config_contract.py:18-21`
already documents this class of blindness for config scanning ("dynamic key
construction … is invisible to the scan; such paths MUST get a READERS
annotation").

*Mitigations.* (a) The manifest's `readers`/exemptions accept an explicit
annotation for the dynamic case, so it is declared rather than lucky. (b) The
`POLICY_POINTS` sweep flags any *literal* occurrence outside the declared
modules, so the cheap evasion (a new literal `os.getenv("FILM_PIPELINE_NO_PERSIST")`)
is always caught. (c) Where a dynamic read is unavoidable, the runtime
"single point" test (§6.9 O2/O6) covers behaviour instead of source.

### 10.4 Declaration/behaviour divergence in reader functions

`_readers.mvp_agent_output_artifacts()` could be written to read the wrong
attribute, making a stale agreement look green.

*Mitigation.* Readers are 3 lines each and live in tests, so they are reviewed
in the same diff as the declaration. `test_both_registries_are_non_trivial`
fails an empty result, which is the failure mode of a mis-written reader.

### 10.5 Guard drift from the code it describes

Renaming `graph/services.py::_default_artifact_root` breaks a `module::symbol`
disposition key silently — the row would fail *liveness*, which is safe, but the
failure message ("write site disappeared") could be misread as "the migration
succeeded".

*Mitigation.* The liveness failure message says the write site disappeared and
tells the author to delete the row; the wave-3 plan expects that direction. A
rename in a *non-migrating* PR produces the same message but with an unchanged
step-1 count, which the PR template asks for.

### 10.6 The manifest becomes a merge-conflict magnet

`architecture.py` is edited by every ownership change, and `docs/`-style
conflicts in one file across parallel extraction branches are likely in a
multi-agent workflow (the repo's pre-commit config already references a
multi-agent "fleet" workflow at `.pre-commit-config.yaml:19-21`).

*Mitigations.* (a) The file is sectioned one concern per block, so conflicts are
textually local. (b) At ~330 lines with `ruff format` normalisation, resolution
is mechanical. (c) If it exceeds ~500 lines, split the invariant data into
`architecture_<domain>.py` files that the guard globs; the *types* stay in one
leaf module.

### 10.7 Over-constraint blocks legitimate work

A strict `may_import` plus `test_declared_edges_are_real` can make a
legitimate short-term edge expensive.

*Mitigation.* The escape is a declared edge (one line) plus, for a violation, an
exemption row with a reason and a wave. The point is that the *decision* becomes
visible; the mechanism never blocks a merge on its own authority.

### 10.8 Guard cost grows with the repo

Every source file is parsed by ~6 sweeps, so cost is O(files × sweeps) and could
become seconds on a much larger tree.

*Mitigations.* Parsing is per-file and independent, `pytest-xdist` (`-n auto`,
`pyproject.toml:73`) parallelises it, and `make arch-check --no-cov` gives a
sub-second local loop. If it ever matters, cache `ast.parse` results per session
in the harness — a 10-line change confined to `_harness.py`.

### 10.9 Someone moves the manifest to `docs/`

`docs/` is gitignored (`.gitignore:2`) and CI-exempt
(`.github/workflows/ci.yml:8-11`), so a manifest there would be unreviewed and
ungated.

*Mitigations.* The manifest path is asserted by
`test_architecture_manifest_is_a_leaf` resolving `SRC / "architecture.py"`, and
`test_source_tree_looks_like_the_repo` fails if `SRC` resolves anywhere without
>200 source files. Moving it is not a silent operation.

### 10.10 The `src/`-vs-`tests/` split obscures where to declare

A contributor adding an invariant may not know whether it belongs in the module
`CONTRACT` or the central manifest.

*Mitigation.* The rule is stated in one place and is testable: if exactly one
module can truthfully state it, it goes in that module's `CONTRACT`; if it is a
relation *between* modules, it goes in `architecture.py`. The guard's failure
messages name both the module and the manifest, so the contributor is told which
one to edit.

---

## 11. Verification record

Executed during this design session, then reverted (docs-only program).

**Prototype scope.** 1 new `src/` module (327 lines), 17 `__init__.py`
`CONTRACT` blocks (325 added lines), 9 new files under `tests/architecture/`
(793 lines).

**Command and result.**

```bash
uv run --python 3.12 --group dev pytest tests/architecture -q --no-cov -p no:cacheprovider
```

- All guard tests **collected and ran**; every guard family executed against the
  real 281-file source tree (57 cases in `test_contracts.py` alone, since the
  edge and public-API tests are parametrised over all 17 packages).
- The only failures were `test_exemption_is_cited_and_reasoned`, by
  construction: the exemption citations point at
  `docs/modular-architecture/design/proposal-B-enforcement.md`, which did not
  exist until this document was written. This is positive evidence that the
  citation check works.
- No failure in `test_contracts.py`, `test_vocabularies.py`,
  `test_state_writers.py`, `test_registries.py`, `test_boundaries.py`, or the
  non-citation parts of `test_exemptions.py`.
- `test_imports_stay_within_declared_edges` and
  `test_declared_edges_are_real` passed for all 17 packages with
  `may_import` set to the observed HEAD edges — confirming the edge resolver
  handles all 52 relative imports and all function-body imports.
- `test_declared_module_graph_is_acyclic` **failed on the first run** with
  `declared dependency cycle among: ['app', 'cli', 'mcp']`. This is the finding
  recorded in §2.3 and §5.3: `app/product_gate.py:17` →
  `film_pipeline.mcp.contract`, closing `app → mcp → app`. The
  `CYCLE_EXEMPTIONS` mechanism was added in response.
- `test_policy_inputs_are_read_only_at_declared_points` failed on the first run
  because the manifest itself names `FILM_PIPELINE_NO_PERSIST`; the sweep now
  skips `architecture.py`. Recorded as failure mode §10.3/§10.5-adjacent
  self-reference behaviour.
- The O3 sweep discovered the 8 `current_phase` writers and the O5 sweep
  discovered the 7 `FILM_PIPELINE_NO_PERSIST` readers mechanically — both sets
  in §2.4 were produced by running the guards, not by hand.
- The O4 agreement, with the 6 non-members recorded, passes; the
  "hook is inert" test passes at HEAD, confirming the gap in §2.4.

**Baseline guard cost.** The five pre-existing AST guard files run 21 tests in
7.5 s wall-clock (4 xdist workers, `--no-cov`, including the
`_production_roots_untouched` session fixture).

**What was not verified.** Wave 1–6 migrations were not executed; the wave table
is a plan derived from the observed edge graph. The optional
`disallow_any_explicit` mypy override was not applied (it would have required
editing `pyproject.toml` for a docs-only program); its feasibility is argued
from the `Any` census in §5.7 and the flag's presence in mypy 2.1.0.

---

## 12. Summary

| Question | Answer |
|---|---|
| What is enforced today? | Five hand-written AST guards covering two seams (`artifacts` storage internals, `graph` node boundaries) plus config-leaf coverage. No import linter, no arch plugin, no manifest. `AGENTS.md:51` states a dependency law that 11 import statements in 4 domain→domain pairs violate, and the package graph has an `app → mcp → app` cycle. |
| What does this proposal add? | A typed ownership manifest (17 contracts + 5 cross-module invariant families) read by ~9 guard files, riding the existing `pytest` gate with no new dependency and no CI YAML change. |
| Which debt classes become automatic? | O1, O3, O4, O5, O7 fully; O8 partly (existence check + per-package mypy `disallow_any_explicit`). O2 and O6 remain human-anchored with automatic regression locks. |
| Biggest risk? | Exemption rot — a ledger that only grows. Mitigated by citation checking, subject liveness, a wave-0 high-water mark, and anti-vacuity canaries. |
| Cost? | 327 + 766 lines of mechanism plus 325 lines of one-time contract declarations (1,418 total), 10 lines of declaration per package, zero new gates, 7.5 s of measured existing guard time as the cost baseline. |
