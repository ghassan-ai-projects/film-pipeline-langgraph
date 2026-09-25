# Audit 14 — Module boundaries, package public APIs, and the import law

Audited at `modular-app` = `fb85baa`. Method: AST scan of every `.py` under
`src/film_pipeline/` building the package-level import matrix, plus source reads
for the enforcement surfaces. All counts below are reproducible with the
commands shown.

## Verification record (self-describing)

Independently verified under bar **A6** by `reviews/verify-14.md` (312 lines — a second
agent that did not write this file, working from its own pristine snapshot of `fb85baa`).
The verifier reproduced the §2 import matrix exactly and recorded **seven disputes**,
all applied in this revision (severity band corrections, the five-cycle scope, the
broken F-BOUNDARY-05 `Reproduce` command, and three false novelty claims).

**§1.5 severity rule applied — the band is a function of the score.** A post-verification
mechanical pass found three findings here whose recorded band contradicted their recorded
score: `F-BOUNDARY-02`, `F-BOUNDARY-03` and `F-BOUNDARY-06` read `Medium` at
`impact 3 × drift 3 = 9`, which §1.5 places in **High** (9–15). They are re-banded to
**High** with **no change to impact, drift, evidence, drift proof or verdict** — only the
label. The earlier use of these three findings as precedent for "the verifier's band word
wins" is **withdrawn, not preserved**; that precedent was cited from
`audit/10-checkpoints-and-runtime-persistence.md` §"Verification record", which has since
applied the same §1.5 rule to its own `F-CRP-05`/`F-CRP-13` and no longer points here.
`00-methodology-and-quality-bar.md` §1.5 names this file's three findings
(`F-BOUNDARY-02/03/06`, "3×3=9 recorded Medium") among the five violations its round-3
mechanical check found.

- **Findings at the reviewed revision (6, `F-BOUNDARY-01`…`F-BOUNDARY-06`):** recorded
  bands then were **0 Critical, 3 High, 3 Medium, 0 Low**; the three `Medium` labels are
  exactly the three re-banded above, so under the §1.5 rule the same six scores are
  **0 Critical, 6 High, 0 Medium, 0 Low**. Axis corrections applied: F-BOUNDARY-01 and
  F-BOUNDARY-04 `16 → 12`; F-BOUNDARY-02 `16 → 9`; F-BOUNDARY-05 `9 → 12`.
- **Added post-verification (PENDING VERIFICATION):** `F-BOUNDARY-07` — `scripts/`
  sits outside every CI gate (ruff, mypy, pytest, coverage) and re-spells the phase,
  artifact-id and MCP-tool vocabularies as bare literals, so an operator harness can
  silently skip phases and still exit 0 — High (impact 3 × drift 5 = 15) — added from
  the adversarial coverage pass (`reviews/adversarial-coverage.md` §H13). Not yet
  re-checked by an independent verifier.
- **Findings after this revision: 7** — **0 Critical, 7 High, 0 Medium, 0 Low**
  (`F-BOUNDARY-01`…`F-BOUNDARY-07`).
- **The mix is mechanically checkable.** Run from the repo root; it parses every
  `- **Severity:**` bullet, recomputes `impact × drift`, maps the score to the §1.5 band
  and flags any label that disagrees with it:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run python - <<'PY'
import pathlib, re
doc = pathlib.Path("docs/modular-architecture/audit/14-module-boundaries-and-import-law.md").read_text()
BANDS = [(16, "Critical"), (9, "High"), (4, "Medium"), (1, "Low")]
mix: dict[str, int] = {}
mismatch = 0
for m in re.finditer(
    r"- \*\*Severity:\*\* (\w+) \(impact (\d) × drift (\d) = (\d+)\)", doc
):
    band, impact, drift, score = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    assert impact * drift == score, (impact, drift, score)
    expected = next(b for t, b in BANDS if score >= t)
    flag = "" if band == expected else "   <-- MISMATCH"
    mismatch += band != expected
    print(f"impact {impact} × drift {drift} = {score:>2}  ->  {expected:<8} (recorded {band}){flag}")
    mix[expected] = mix.get(expected, 0) + 1
print("\nmix:", ", ".join(f"{mix.get(b, 0)} {b}" for _, b in BANDS))
print("mismatches:", mismatch)
PY
```

  Output at HEAD: seven `High` lines, then
  `mix: 0 Critical, 7 High, 0 Medium, 0 Low` and `mismatches: 0`. This is the invariant
  the target architecture should turn into a guard test (it is the check that found the
  three re-banded findings).
- **Bar A1 scope closure:** this file now carries the explicit `scripts/` and
  `documentation/` scope record (§"A1 coverage closure" below), which
  `01-ownership-map.md:391,397-411` already cites it as carrying. No package in the
  A1 list is silently omitted.

## Coverage

| Scope | Verdict |
|---|---|
| All 17 sub-packages' `__init__.py` public surfaces | audited — see §3 |
| Package-level import matrix (281 source files) | measured — see §2 |
| `AGENTS.md` §"Sub-Package Boundaries" law | audited — law is violated, see F-BOUNDARY-01 |
| Cycle detection | measured — one 2-cycle at package granularity, five cycles at directory-module granularity (§2a), see F-BOUNDARY-03 |
| Cross-package private-module / private-symbol imports | measured — see F-BOUNDARY-05 |
| Boundary enforcement tests (`tests/`) | audited — two import-boundary suites + two AST contract guards, see F-BOUNDARY-04 and "Clean concerns" |
| `src/film_pipeline/testing` (test-only package inside `src`) | audited — see F-BOUNDARY-06 |
| `scripts/` (9 files / 1,678 lines) | audited only to the A1 depth — **has findings**, see F-BOUNDARY-07 and §"A1 coverage closure" |
| `documentation/` (62 files / 15,350 lines) | declared prior art, **not audited as source** — drift recorded as a scope decision, see §"A1 coverage closure" |
| `profiles/`, `Makefile`, `langgraph.json` | out of cluster (entry points cluster 11) |

## A1 coverage closure — `scripts/` and `documentation/`

Bar A1 requires `scripts/` to be mapped to at least one concern and explicitly marked
"has findings" or "clean", and forbids silently omitting a package. `documentation/` is
not in A1's list, but `AGENTS.md:9` makes it authoritative, so it needs an explicit
decision too rather than an implicit one. `01-ownership-map.md:391,397-411` already
points at *this* file as the place both records live; this section is that record. Both
are **scope decisions with evidence**, not audited product modules.

### `scripts/` — operator tooling, outside every gate

- **Measured size.** 9 tracked Python files / **1,678 lines**
  (`wc -l $(git ls-files 'scripts/*.py') | tail -1`).
- **Inspected.** Every phase-name, artifact-id and MCP-tool-name string literal in all
  9 files, and the control flow that consumes them (the five approval loops, the
  `test-full-pipeline-direct.py` phase gate, the `e2e-real-auto-approve.py` artifact
  check); the CI configuration that governs them (`pyproject.toml:59,83,94,127`,
  `Makefile:36,42`); the absence of any import of them from `src/` or `tests/`; and the
  11 prose mentions of `scripts/` in `documentation/` (7 files — design proposals for
  *new* scripts plus one deprecation note; none treats the existing files as a contract).
- **NOT inspected.** The runtime behaviour of the 9 scripts: their MCP call sequences
  beyond the phase loop, provider/credential handling, cleanup and scratch-root
  handling, and `test-full-pipeline.py` (a 233-line subprocess MCP driver) line by line.
  **`scripts/` was not fully audited in this pass and cannot honestly be claimed as
  audited.** What is audited is the one concern A1 turns on — whether a product
  normative model has a second, unguarded owner outside `src/`.
- **Scope decision.** `scripts/` is **operator tooling, not a product module**. It is
  classified **has findings**: F-BOUNDARY-07 (High, 3 × 5 = 15).
- **Reason.** It is neither shipped nor importable — absent from the wheel
  (`packages = ["src/film_pipeline"]`, `pyproject.toml:59`) and from the sdist
  (`pyproject.toml:62-68`); imported by nothing under `src/` or `tests/`
  (`grep -rnE '^\s*(from|import)\s+scripts|_scratch_bootstrap' src/ tests/ --include='*.py' | wc -l`
  → `0`); named by no *operator* document — the only prose hits are
  `documentation/reviews/storage-upgrade-review.md:48` (records
  `scripts/_scratch_bootstrap.py` as deprecated) and the design proposals at
  `documentation/architecture-review.md:273`,
  `documentation/reviews/arch-lens-boundaries.md:240,269` that ask for a *new*
  `scripts/check_boundaries.py`. But it is the repo's only live end-to-end harness
  (`scripts/e2e-real-auto-approve.py:28` sets `FILM_PIPELINE_MCP_MODE = "real"`), and it is a
  third, unguarded spelling of three vocabularies whose owners are in `schemas`,
  `artifacts` and `mcp` — so "clean" would be false.
- **Residual risk.** F-BOUNDARY-07 is the measured, reproducible slice (vocabulary
  ownership). Everything else in those 1,678 lines — a stale MCP call shape, a bypassed
  confirmation gate, an unguarded credential path — remains **unmeasured and unguarded**
  by this audit. `scripts/` should be re-audited as a cluster if it is ever promoted
  from dev tooling to a supported operator entry point.

### `documentation/` — declared source of truth, used only as prior art

- **Measured size.** 62 Markdown files / **15,350 lines**; the file `AGENTS.md:9` names
  as the architectural source of truth, `documentation/architecture-blueprint.md`, is
  **2,420 lines**.
- **Inspected.** `documentation/architecture-blueprint.md:1570` and `:1655` (the two
  machine-readable `current_phase` examples), plus a repo-wide sweep of `documentation/`
  for `visual_development`, `"current_phase"` and `Visual Dev`.
- **NOT inspected.** The remaining ~2,415 lines of the blueprint and the other 61
  Markdown files, except where a cluster audit already cites them as prior art. (The two
  YAML manifests read by `app.product_gate` are outside the Markdown count above; they
  were grepped for phase values, not read line by line — see the scope decision.)
- **Scope decision.** `documentation/` is **prior art for the owning audits, not audited
  as source**. Its one measured drift is recorded here as a **documentation-drift scope
  decision, not a numbered finding** — the promotion test is whether the drift can cause
  a silent failure in *shipped* behaviour, and it cannot: `documentation/` is in neither
  the wheel nor the sdist (`pyproject.toml:59,62-68`), and **the blueprint is read by
  nothing** (`grep -rln "architecture-blueprint" tests/ src/` → no matches). Two
  documentation files *are* on a runtime path —
  `documentation/product-completion/acceptance-manifest.yaml` and
  `documentation/product-completion-plan/acceptance-manifest.yaml`, parsed by
  `src/film_pipeline/app/product_gate.py:19-20` — but they carry tool names and file
  paths, not phase values, so they are outside this drift.
- **Why it is still a hazard, and which side is wrong.** `AGENTS.md:9` makes the
  blueprint authoritative, and `documentation/architecture-blueprint.md:1570,1655` print
  `"current_phase": "visual_development"`, a value the schema rejects
  (`src/film_pipeline/schemas/_base.py:77-90`: `VISUAL_DEV = "visual_dev"`; no member
  spells `visual_development`). **The blueprint is the wrong side, not the code.**
  `visual_dev` is the value carried in state (`src/film_pipeline/graph/state_schema.py:116`), and in the
  artifact directory layout (`src/film_pipeline/artifacts/paths.py:14-26`, `"visual_dev": "04-visual-dev"`)
  and in the MCP surface (`src/film_pipeline/mcp/tools/registry.py` phase arguments); `FilmPhase` is the
  only enum either side can validate against. The blueprint's *prose* heading
  (`documentation/architecture-blueprint.md:1812`, "Phase 4. Visual Development") is
  fine — hyphenated display names are used elsewhere in the code
  (`src/film_pipeline/agents/prompt_templates/defaults/production.py:11` `_visual_development_creator`).
  Only the two JSON state values are machine-wrong, and the sibling operator document
  gets the same field right (`documentation/openclaw-mcp-operator-guide.md:308`,
  `"current_phase": "script"`). The cost is a reproduction hazard for an agent
  implementing from the blueprinted JSON, not a shipped defect.
- **Residual risk.** Unmeasured drift in the rest of those 15,350 lines of prose that is
  declared authoritative but pinned by nothing. The concrete evidence: no guard exists,
  and a phase name the code rejects survives in the source of truth.

**Reproduce (both scopes, exact output at `fb85baa`):**

```bash
# --- scripts/ is outside every gate -------------------------------------------------
wc -l $(git ls-files 'scripts/*.py') | tail -1                       # 1678
UV_CACHE_DIR="$PWD/.uv-cache" uv run --python 3.12 --group dev ruff check --no-cache . 2>&1 | grep -c scripts/   # 0
UV_CACHE_DIR="$PWD/.uv-cache" uv run --python 3.12 --group dev ruff check --no-cache scripts/*.py 2>&1 | grep -Eo 'Found [0-9]+ errors' # Found 66 errors
grep -rn "scripts/" tests/ --include='*.py' | wc -l                  # 0
grep -rnE '^\s*(from|import)\s+scripts' src/ tests/ --include='*.py' | wc -l  # 0

# --- documentation/ drift, and which side rejects which value -----------------------
UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
from film_pipeline.schemas._base import FilmPhase
try: FilmPhase('visual_development')
except ValueError as e: print('REJECTED:', e)
print('canonical:', FilmPhase.VISUAL_DEV.value)"
# -> REJECTED: 'visual_development' is not a valid FilmPhase
# -> canonical: visual_dev
grep -rn '"current_phase"' documentation/
# -> architecture-blueprint.md:1570, :1655  "visual_development"  (invalid)
# -> openclaw-mcp-operator-guide.md:308     "script"              (valid)
grep -rln "architecture-blueprint" tests/ src/                       # (no matches: no guard)
```

## 1. The declared law

`AGENTS.md:51`:

> The 12 sub-packages under `src/film_pipeline/` map 1:1 to implementation
> phases. `graph` and `mcp` may import across all sub-packages; domain modules
> must not import each other directly — they communicate through `artifacts`.

Three problems with the declared law itself, before evidence of violation:

1. It says **12** sub-packages; there are **17** (`ls src/film_pipeline`).
2. "communicate through `artifacts`" is false as a design statement: `artifacts`
   is a *storage* component (it owns the on-disk layout), not a message bus. Most
   cross-domain data already flows through `schemas` (322 imports) and
   `graph` state (131), not `artifacts` (51).
3. The law is prose only. Nothing in `pyproject.toml`, `Makefile`, or
   `.pre-commit-config.yaml` checks it.

## 2. Measured package-level import matrix

`src → dst` counts (AST, non-`__pycache__`):

| from \ to | schemas | graph | agents | mcp | providers | generation | artifacts | validation | app | config | kb | checkpoints | post | review | constraints | testing | cli |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| agents | 27 | · | · | · | 4 | · | · | · | · | · | · | · | · | · | · | · | · |
| app | 7 | 16 | 1 | 1 | 4 | 2 | 8 | 1 | · | 2 | 3 | 4 | · | · | · | · | · |
| artifacts | 16 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| checkpoints | 5 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| cli | · | 4 | · | · | · | · | 1 | · | 4 | · | · | · | · | · | · | · | · |
| config | · | · | · | · | 2 | · | · | · | · | · | · | · | · | · | · | · | · |
| constraints | 6 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| generation | 8 | · | · | · | 4 | · | 7 | · | · | · | · | · | · | · | · | · | · |
| graph | 50 | · | 9 | · | 2 | 4 | 3 | 14 | · | · | 2 | · | · | · | 2 | · | · |
| kb | 7 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| mcp | 73 | 7 | 7 | · | 6 | 23 | 7 | 7 | 7 | 6 | 5 | 3 | 2 | 1 | · | · | · |
| post | 10 | · | · | · | · | · | · | 1 | · | · | · | · | · | · | · | · | · |
| providers | 8 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| review | 3 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| testing | · | · | · | · | 1 | · | 2 | · | · | · | · | 1 | · | · | · | · | · |
| validation | 32 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |

Observations that matter for modularization:

- `schemas` is the universal kernel: **322** `ImportFrom` statements (252 cross-package + 70
  intra-package), and no package is exempt. *(Corrected after `reviews/verify-14.md`: the earlier
  "323" counted a docstring line at `src/film_pipeline/schemas/__init__.py:5`.)* The matrix has 16 source rows because
  `schemas` has no cross-package row of its own.
- `graph` and `mcp` are the two consumers that legitimately fan out, matching
  the law.
- Several **domain→domain** edges exist that the law forbids (§F-BOUNDARY-01).
- `app` → everything (composition root, expected) but `app` is also imported by
  `mcp` and `cli`, so `app` is not purely a leaf composition root.

## 2a. All cycles at HEAD (added per verify-14)

The §2 matrix scan checked only top-level 2-cycles. The deterministic enola snapshot at
the same commit (`docs/modular-architecture/enola-out/receipt.json`,
`commit fb85baa…, dirty:false`) reports **5** cycles at directory-module granularity, and
`reviews/verify-14.md` reproduced exactly the same 5 with an independent Tarjan SCC:

| # | Cycle members | Class |
|---|---|---|
| C1 | `src/film_pipeline/agents/prompt_templates` ↔ `src/film_pipeline/agents/prompt_templates/defaults` | façade re-export; cheap |
| C2 | `app` → `src/film_pipeline/app/services` → `mcp` → `src/film_pipeline/mcp/tools` → `src/film_pipeline/mcp/tools/bibles` → `src/film_pipeline/mcp/tools/generation` → `src/film_pipeline/mcp/tools/reference_generation` → `app` (**7 modules**) | design-level |
| C3 | `graph` ↔ `src/film_pipeline/graph/nodes` ↔ `src/film_pipeline/graph/orchestrator_validators` ↔ `src/film_pipeline/graph/subgraphs` (**4 modules**) | intra-package, design-level |
| C4 | `providers` ↔ `src/film_pipeline/providers/adapters` | façade re-export; cheap |
| C5 | `schemas` ↔ `src/film_pipeline/schemas/registries` | façade re-export; cheap |

Consequence for F-BOUNDARY-03's proposed fix: splitting `app.product_gate` (or adding
`app.contracts`) is **not shown to break the 7-module C2 cycle**, and C3 is not addressed
by it at all. The target architecture must resolve C2 and C3 explicitly; see
`03-target-architecture.md` §"cycle-breaking" and `reconciliation-notes.md` R2.

## 3. Package public-API surfaces

| Package | `__init__.py` lines | Assessment |
|---|---|---|
| `schemas` | 273 | Real façade (29 imports, large `__all__`) — but bypassed, see F-BOUNDARY-02 |
| `graph` | 6 | Almost no façade; consumers import deep submodules |
| `app` | 8 | Composition interfaces only |
| `artifacts` | 53 | Intentional façade, guarded by tests |
| `mcp` | 42 | Façade exists |
| `generation` | 48 | Façade exists |
| `agents`, `providers`, `validation`, `post` | 22–27 | Thin façades |
| `cli`, `constraints` | 3–13 | Minimal |
| `testing` | 14 | Ships in `src/` (see F-BOUNDARY-06) |

---

## Findings

### F-BOUNDARY-01 — The declared domain-isolation law is violated, unenforced, and partly wrong
- **Class:** O7/O8 (missing contract; enforcement absent). **Correction (verify-14):** O5 is a
  stretch — no policy is re-derived at N call sites here; it is declared once and ignored.
- **Severity:** High (impact 3 × drift 4 = 12). *Corrected from an internally inconsistent
  "High (4 × 4 = 16)": per §1.5 a score of 16 is Critical, and no user-visible/durable-data impact
  is demonstrated, so impact drops to 3.*
- **Concern:** which packages may depend on which.
- **De-facto owners:**
  - `AGENTS.md:51` — declares the law — `"domain modules must not import each other directly — they communicate through artifacts"`
  - `src/film_pipeline/agents/runner.py:17` — `from film_pipeline.providers.failure_classifier import (` — a domain→domain edge
  - `src/film_pipeline/config/profile_resolver.py:204` — `from film_pipeline.providers.credentials import _env_var_for, is_configured` — domain→domain edge *and* a private symbol of another package
  - `src/film_pipeline/generation/executor.py:29` — `from film_pipeline.providers.base import (` — domain→domain edge
  - `src/film_pipeline/generation/ledger.py:14` — `from film_pipeline.artifacts.store import ArtifactStore` — generation owns ledger state but depends on the storage façade
  - `src/film_pipeline/post/delivery_packaging_agent.py:190` — `from film_pipeline.validation.impl.delivery_completeness import (` — post→validation, reaching an **implementation** module, not a registry
  - `src/film_pipeline/testing/storage.py:11-12` — `from film_pipeline.artifacts...` / `from film_pipeline.artifacts.store import ArtifactStore`
- **Drift proof (existing divergence):** the law says domain modules must not
  import each other; at HEAD **eight** distinct forbidden edges exist
  (agents→providers, config→providers, generation→artifacts, generation→providers,
  post→validation, testing→artifacts, testing→checkpoints, testing→providers).
  *(Corrected from "seven" after `reviews/verify-14.md`; the original sentence said
  seven but listed eight. A contributor adding the next forbidden edge — the
  ninth — gets no signal: no test, no lint, no import-linter config exists,
  F-BOUNDARY-04.)*
  **Scope caveat (orchestrator, `reviews/orchestrator-verification-notes.md` V3):** the
  eight above are what the single AST sweep under **Reproduce** below produces under the
  only "forbidden" definition the current law permits (source not the exempt `graph`/`mcp`
  and not the composition root/entry point `app`/`cli`; target not `schemas`). The same
  sweep prints the wider ladder: **53** distinct cross-package `(from, to)` pairs, **32**
  with a source other than the exempt `graph`/`mcp`, **21** once `schemas` is removed as a
  target and **17** once `artifacts` is removed as well. The law never defines "domain
  module" (are `app`, `cli`, `testing`, `checkpoints`, `kb`, `constraints`, `review` in
  scope?) nor whether importing the `artifacts` façade is the sanctioned "communicate
  through `artifacts`" or a forbidden edge. **The count is therefore undefined, and that
  is the finding**: there is no edge matrix to count against.
  `03-target-architecture.md` must publish that matrix before any count is quoted as fact.
  `graph→validation` (14 imports, e.g. `src/film_pipeline/graph/nodes/qc.py:265-352`) is
  permitted by the law's `graph` exemption but reaches `validation.impl.*` directly.
- **Reproduce:** one AST sweep, run from the repo root. It replaces the three targeted
  greps this block previously carried: those emitted only **7** of the eight edges because
  the `generation` grep matched `from film_pipeline.providers` but not
  `from film_pipeline.artifacts`, so it missed `generation→artifacts` — real at 7
  statements: `src/film_pipeline/generation/ledger.py:14`,
  `src/film_pipeline/generation/executor.py:22`,
  `src/film_pipeline/generation/executor_delivery.py:14,19`,
  `src/film_pipeline/generation/executor_prompts.py:13`,
  `src/film_pipeline/generation/frame_sidecar.py:7`,
  `src/film_pipeline/generation/compositor/_layout.py:10`.
  The sweep prints the ladder and then the eight forbidden edges with statement counts:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run python - <<'PY'
import ast, collections, pathlib
ROOT = pathlib.Path("src/film_pipeline")
EXEMPT = {"graph", "mcp"}   # the law's cross-package exemption
ROOTS = {"app", "cli"}      # composition root + entry point: may reach anything
edges = collections.Counter()
for f in sorted(ROOT.rglob("*.py")):
    if "__pycache__" in f.parts:
        continue
    src = f.relative_to(ROOT).parts[0]
    for n in ast.walk(ast.parse(f.read_text())):
        if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("film_pipeline."):
            dst = n.module.split(".")[1]
            if dst != src:
                edges[(src, dst)] += 1
print(f"all distinct cross-package (from,to) pairs : {len(edges)}")       # 53
non_em = {k: v for k, v in edges.items() if k[0] not in EXEMPT}
print(f"excluding graph/mcp as source             : {len(non_em)}")       # 32
no_sch = {k: v for k, v in non_em.items() if k[1] != "schemas"}
print(f"and excluding schemas as target           : {len(no_sch)}")      # 21
no_art = {k: v for k, v in no_sch.items() if k[1] != "artifacts"}
print(f"and excluding artifacts as target         : {len(no_art)}")      # 17
forb = {k: v for k, v in no_sch.items() if k[0] not in ROOTS}
print(f"\nforbidden domain->domain edges: {len(forb)}")                  # 8
for (s, d), n in sorted(forb.items()):
    print(f"  {s}->{d}: {n} statement(s)")
PY
```

  Output at `fb85baa`:

```
all distinct cross-package (from,to) pairs : 53
excluding graph/mcp as source             : 32
and excluding schemas as target           : 21
and excluding artifacts as target         : 17

forbidden domain->domain edges: 8
  agents->providers: 4 statement(s)
  config->providers: 2 statement(s)
  generation->artifacts: 7 statement(s)
  generation->providers: 4 statement(s)
  post->validation: 1 statement(s)
  testing->artifacts: 2 statement(s)
  testing->checkpoints: 1 statement(s)
  testing->providers: 1 statement(s)
```

  *(Evidence replaced per `reviews/adversarial-evidence.md` §3.1: the claim of eight edges
  was correct and independently reproduced, but the block's own three greps could not
  produce it.)*
- **Blast radius:** every package pairing. The real consequence is that
  "domain module" is not a usable concept: refactors cannot rely on a
  dependency direction, and a change in `providers` internals can silently
  affect `agents`, `config`, and `generation`.
- **Candidate owner module:** `module-law` (a declared dependency contract +
  executable guard), not a runtime module.
- **Extraction sketch:** replace the prose law with an explicit edge matrix
  (allowed / forbidden / requires-contract), encode it as an executable test
  (§F-BOUNDARY-04), and either fix each violating edge by adding a contract
  module or legalize it explicitly with a rationale.
- **Prior art:** *(corrected per verify-14)* `documentation/architecture-review.md:73-76`
  already enumerates five of the eight violating edges, and its Finding 8 measures the
  "12 vs 19 packages" miscount; `documentation/reviews/arch-lens-boundaries.md` discusses
  boundaries qualitatively. What is **new here** is the complete 17×17 matrix and the
  8-edge count at HEAD.

### F-BOUNDARY-02 — `schemas._base` is a private module used as the public kernel by 72 non-schema files
- **Class:** O7 (leaked internals). **Correction (verify-14): O1 rejected** — no second
  *definition* of any enum or constant is demonstrated, and §1.4 O1 requires one.
- **Severity:** High (impact 3 × drift 3 = 9). *Axes corrected from "High (4 × 4 = 16)"
  per verify-14: O1 was rejected and the rename failure is loud rather than silent (see
  drift proof), so only façade completeness drifts quietly. Band re-stated from
  `Medium` to `High` under the §1.5 rule that the band is a function of the score — the
  axes did not change and the score is 9.*
- **Concern:** where shared base types/enums/statuses are defined and reached.
- **De-facto owners:**
  - `src/film_pipeline/schemas/_base.py` — defines `SchemaBase`,
    `ValidationStatus` (`:122`), `GenerationStatus` (`:168`), etc.
  - `src/film_pipeline/schemas/__init__.py:25-28` — re-exports them publicly —
    `"SchemaBase"`, `"ValidationStatus"` are in `__all__` (`:249`, `:266`)
  - but consumers import the private module instead, e.g.
    `src/film_pipeline/graph/_action_routing.py:16`,
    `src/film_pipeline/mcp/tools/validation.py:24`,
    `src/film_pipeline/validation/base.py:17`,
    `src/film_pipeline/providers/health.py:8`,
    `src/film_pipeline/artifacts/store.py:51`.
- **Drift proof (existing divergence, corrected per verify-14):** of the 16 distinct
  names outsiders import from `schemas._base`, **two are not bound in
  `src/film_pipeline/schemas/__init__.py` at all** — `TRANSITION_TYPES` and `LEGACY_TRANSITION_ALIASES`
  (consumed by e.g. `src/film_pipeline/post/transition_agent.py:8`). The declared façade
  is therefore already incomplete, not merely at risk. *(The original claim that a
  removed symbol would silently break 72 files is **withdrawn**: mypy strict and normal
  import resolution make a move or rename loud immediately.)* Measured split: 37 files
  inside `schemas` + **72 files outside** import `schemas._base`.
- **Reproduce:**
  ```bash
  grep -rl "schemas._base" src/film_pipeline --include='*.py' | wc -l        # 109
  grep -rl "schemas._base" src/film_pipeline --include='*.py' | grep -vc '^src/film_pipeline/schemas/'  # 72
  ```
- **Blast radius:** all 17 packages. A move or rename of a base type is **loud**
  (mypy strict catches it); what drifts silently is *façade completeness* — two
  names outsiders already import (`TRANSITION_TYPES`, `LEGACY_TRANSITION_ALIASES`)
  are not re-exported, so the public contract is already narrower than its users.
- **Candidate owner module:** `schemas` public contract (`src/film_pipeline/schemas/__init__.py`)
  as the only legal import surface; `_base` becomes truly private and a guard
  test bans `schemas._base` imports from outside `src/film_pipeline/schemas/`.
- **Extraction sketch:** mechanical import rewrite (72 files) from
  `schemas._base` to `schemas`; add `test_schemas_public_surface` that fails on
  any `from film_pipeline.schemas._...` outside the package. Low risk, high
  signal.
- **Prior art:** not previously recorded as an ownership seam.

### F-BOUNDARY-03 — `app` ↔ `mcp` import cycle
- **Class:** O8 (missing contract) + cycle
- **Severity:** High (impact 3 × drift 3 = 9). *Band re-stated from `Medium` to `High`
  under the §1.5 rule that the band is a function of the score — the axes did not change
  and the score is 9.*
- **Concern:** who owns the composition root / runtime accessor.
- **De-facto owners:**
  - `src/film_pipeline/app/product_gate.py:17` — `from film_pipeline.mcp.contract import make_registry` (app → mcp)
  - `src/film_pipeline/mcp/server.py:164` — `from film_pipeline.app.runtime import get_runtime`
  - `src/film_pipeline/mcp/server.py:241` — `from film_pipeline.app.bootstrap import validate_environment`
  - `src/film_pipeline/mcp/server.py:248` — `from film_pipeline.app._persistence import configured_runtime_root`
  - `src/film_pipeline/mcp/tools/__init__.py:22` — `from film_pipeline.app.runtime import get_runtime`
  - `src/film_pipeline/mcp/server.py:249` — `from film_pipeline.app.logging_setup import configure_logging` *(added per verify-14)*
  - `src/film_pipeline/mcp/tools/generation/planning.py:136-137` — `app.services.errors`, `app.services.operator` *(added per verify-14)*

  This is a **package-granularity** 2-cycle; at directory-module granularity the same
  cycle has **7 members** (`app`, `src/film_pipeline/app/services`, `mcp`, `src/film_pipeline/mcp/tools`, `src/film_pipeline/mcp/tools/bibles`,
  `src/film_pipeline/mcp/tools/generation`, `src/film_pipeline/mcp/tools/reference_generation`) — see the cycle section below.
- **Drift proof:** the cycle is real at package granularity. Because the imports
  are function-body (lazy), mypy and pytest do not flag it, and import order
  determines which side can be constructed first in a fresh interpreter. Any new
  module-level import on either side can turn a lazy cycle into an
  `ImportError` at startup; nothing pins the laziness.
- **Reproduce:**
  ```bash
  grep -rn "from film_pipeline.mcp" src/film_pipeline/app
  grep -rn "from film_pipeline.app" src/film_pipeline/mcp
  ```
- **Blast radius:** startup of all three entry points.
- **Candidate owner module:** split `app.product_gate` (a *verification* tool, not
  the composition root) out of `app`, or move the runtime accessor behind a
  tiny `app.contracts` interface that `mcp` may import without importing `app`
  internals.
- **Extraction sketch:** introduce `app.contracts` (Protocol + `get_runtime`
  accessor), have `mcp` import only that, move `product_gate` to a `tools/`
  or `verification/` module that may depend on `mcp`.
- **Prior art:** *(corrected per verify-14)* not new — `documentation/reviews/arch-lens-boundaries.md:215-226`
  (Finding 7) and `documentation/architecture-review.md:78,110` (B-F7) both already state
  "exactly one package-level cycle `{app ↔ mcp}`, held together by lazy imports". What is new
  here is the 7-member directory-module view and the added import sites.

### F-BOUNDARY-04 — Boundary rules are enforced by two bespoke per-package AST tests; there is no global law
- **Class:** O8 (missing contract) + O5 (the enforcement policy is re-implemented per package).
  *(re-verified: `reviews/verify-14.md` confirmed the enforcement gap; it did not
  separately examine the O5 classification.)*
- **Severity:** High (impact 3 × drift 4 = 12). *Corrected from the internally inconsistent
  "High (4 × 4 = 16)"; §1.5 makes 16 Critical.*
- **Concern:** mechanical enforcement of module boundaries.
- **De-facto owners:**
  - `tests/unit/artifacts/test_storage_boundary.py:1` — hand-written AST sweeps:
    `test_only_storage_imports_layout_facts`, `test_only_storage_imports_path_helpers`,
    `test_no_layout_constants_leak_outside_storage`,
    `test_storage_core_does_not_import_other_components`,
    `test_storage_core_has_no_runtime_checkpoints_dependency`
  - `tests/unit/graph/test_startup_boundaries.py:1` — hand-written AST sweep banning
    `film_pipeline.testing` and `film_pipeline.app` from `graph/`
  - **No other package has an *import* boundary test.** *(verify-14 correction: two further
    hand-written **AST contract guards** exist and are not import boundaries —
    `tests/unit/config/test_config_contract.py` (profile-leaf reads) and
    `tests/unit/graph/test_channel_registry.py` (orchestrator constants ↔ schema ↔ registry
    parity) — so "the only two mechanically guarded boundaries" would be overbroad.)*
    `pyproject.toml` has no `import-linter`/`archon`/`pytest-arch`/`tach`/`grimp` section;
    `.pre-commit-config.yaml` runs ruff/mypy only, and ruff's rule selection has no
    import-layering rule.
- **Drift proof (mutation scenario):** add
  `from film_pipeline.validation.impl.assembly import AssemblyValidator` to
  `src/film_pipeline/post/subtitle_agent.py` — a post→validation edge the law forbids. Nothing
  fails: `tests/unit/post/` has no boundary test, ruff has no import rules
  configured for this, and mypy does not model package layering. The storage and
  graph suites are structurally excellent and reusable; they simply do not
  generalize.
- **Reproduce:**
  ```bash
  ls tests/unit/*/test_*boundar*.py tests/unit/*/test_*architect*.py 2>/dev/null
  grep -n "import-linter\|importlinter\|archon\|pytest-arch" pyproject.toml .pre-commit-config.yaml
  ```
- **Blast radius:** every package except `artifacts` and `graph`.
- **Candidate owner module:** `module-law` — one declarative edge matrix + one
  parameterized guard suite replacing the two bespoke files.
- **Extraction sketch:** generalize the two existing AST patterns into
  `tests/unit/architecture/test_module_law.py` driven by a single
  `MODULE_LAW` table; keep the storage/graph suites as thin specializations or
  fold them in. See independent design `design/proposal-B-enforcement.md`.
- **Prior art:** *(corrected per verify-14)* the "global absence is new" claim is false —
  `documentation/reviews/arch-lens-boundaries.md:269` and
  `documentation/roadmap-execution/phase-03-law-and-docs-truth-plan.md:28` already propose the
  CI edge scan (`scripts/check_boundaries.py`). What is new here is the measured proof that
  neither exists and the two additional AST contract guards above.

### F-BOUNDARY-05 — Cross-package imports of private modules and private symbols
- **Class:** O7 (leaked internals)
- **Severity:** High (impact 3 × drift 4 = 12), *raised from Medium after verify-14 added the
  two `app→graph` private-symbol reach-ins below; the originally cited anchors alone would be
  Medium (3 × 3 = 9).*
- **Concern:** encapsulation of a package's internal modules/symbols.
- **De-facto owners / offenders (cross-package only; intra-package uses omitted):**
  - `src/film_pipeline/mcp/server.py:248` —
    `from film_pipeline.app._persistence import configured_runtime_root` (private module of another package)
  - `src/film_pipeline/config/profile_resolver.py:204` —
    `from film_pipeline.providers.credentials import _env_var_for, is_configured` (private **function** of another package)
  - `src/film_pipeline/app/_graph_exec.py:319` —
    `from film_pipeline.graph.nodes import _run_validators` (private **symbol** of another package; added per verify-14)
  - `src/film_pipeline/app/_graph_exec.py:449` —
    `from film_pipeline.graph.nodes.approval import _PHASE_NODES` (added per verify-14)
  - `src/film_pipeline/schemas._base` — imported by 72 files outside `schemas` (see F-BOUNDARY-02)
- **Drift proof (mutation scenario):** rename `_env_var_for` to `env_var_for`
  inside `src/film_pipeline/providers/credentials.py`. `mypy` fails in `src/film_pipeline/config/profile_resolver.py:204`
  — so this edge is at least type-checked. Now rename a *field or default* rather
  than a symbol (e.g. change the env-var derivation rule): both sites still
  compile and diverge silently. The `app._persistence` import from `mcp` is
  worse: it is a private module with a public function; moving
  `configured_runtime_root` breaks `src/film_pipeline/mcp/server.py` with no contract check.
- **Reproduce:** *(command replaced per verify-14 — the original `^from`-anchored grep saw only
  column-0 imports and returned 42 `schemas._base` lines, finding neither of the offenders it
  cited, both of which are indented.)* Works at any indentation and for both import forms:
  ```bash
  .venv/bin/python - <<'PY'
  import ast, pathlib
  root = pathlib.Path("src/film_pipeline")
  for f in sorted(root.rglob("*.py")):
      if "__pycache__" in f.parts: continue
      pkg = f.relative_to(root).parts[0]
      tree = ast.parse(f.read_text())
      for n in ast.walk(tree):
          if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("film_pipeline."):
              parts = n.module.split(".")
              cross = parts[1] != pkg
              private_mod = len(parts) > 2 and parts[2].startswith("_")
              private_sym = [a.name for a in n.names if a.name.startswith("_") and a.name != "*"]
              if cross and (private_mod or private_sym):
                  print(f"{f}:{n.lineno} -> {n.module} {private_sym}")
  PY
  ```
  Result at HEAD: **107 private-module sites** (105 `schemas._base` + 1 `app._persistence`; the
  former is F-BOUNDARY-02's systemic case) and **3 cross-package private-symbol sites**
  (`src/film_pipeline/config/profile_resolver.py:204`, `src/film_pipeline/app/_graph_exec.py:319`, `src/film_pipeline/app/_graph_exec.py:449`).
- **Blast radius:** `schemas` (systemic), `mcp`→`app` (`_persistence`), `providers`→`config`
  (`_env_var_for`), and `app`→`graph` (`_run_validators`, `_PHASE_NODES`).
- **Candidate owner module:** enforce "private means private": a public
  `credentials` contract (`is_configured`, `lookup`, `env_var_for`) and a public
  `app.contracts.configured_runtime_root`.
- **Extraction sketch:** promote the two names, add a guard test banning
  `from film_pipeline.<pkg>._<mod> import` across package boundaries.
- **Prior art:** *(corrected per verify-14)* not new —
  `documentation/reviews/arch-lens-boundaries.md:43` (Finding 2, medium) already records
  `src/film_pipeline/config/profile_resolver.py:204 → _env_var_for`, with a target design that makes the symbol
  public. New here: the two `app→graph` private-symbol sites and the 107-site count.

### F-BOUNDARY-06 — `film_pipeline.testing` ships in the production package and is a cross-domain consumer
- **Class:** O8 (missing contract) + O7
- **Severity:** High (impact 3 × drift 3 = 9). *Band re-stated from `Medium` to `High`
  under the §1.5 rule that the band is a function of the score — the axes did not change
  and the score is 9.*
- **Concern:** where test doubles live and what they may depend on.
- **De-facto owners:**
  - `src/film_pipeline/testing/storage.py:11-12` — imports `artifacts.storage`
    (`PROFILE_SANDBOX`, `init_storage_root`) and `artifacts.store.ArtifactStore`
  - `src/film_pipeline/testing/in_memory_git.py:29` — `from film_pipeline.checkpoints.git_backend import GitBackend`
  - `src/film_pipeline/testing/scenarios.py:5` — `from film_pipeline.providers.mock_provider import ScenarioStep`
  - `src/film_pipeline/testing/mock_model.py`, `mock_human.py`
  - Meanwhile mock **providers** live in `src/film_pipeline/providers/` (`src/film_pipeline/providers/mock_provider.py`,
    `src/film_pipeline/providers/mock_image_provider.py`) and canned agent responses live in
    `src/film_pipeline/app/mock_responses.py:1` — three different homes for test doubles.
- **Drift proof:** `tests/unit/graph/test_startup_boundaries.py` exists precisely
  because `film_pipeline.testing` once leaked into production startup. The
  package is inside the shipped wheel (`pyproject.toml` `packages =
  ["src/film_pipeline"]`) and is excluded from coverage. *(verify-14 correction: the omit
  list has **two** entries — `*/testing/*` **and** `src/film_pipeline/mcp/tools/__init__.py`
  (`pyproject.toml:95-98`) — so "the only excluded package" holds, but the originally
  quoted one-line config was truncated.)* There is no rule stating what `src/film_pipeline/testing/` may
  import, so its cross-domain edges (artifacts, checkpoints, providers) are unpoliced.
- **Reproduce:**
  ```bash
  grep -rn "class .*Mock\|class .*Fake\|class .*Stub" src/film_pipeline --include='*.py'
  grep -n "omit" pyproject.toml
  ```
- **Blast radius:** packaging (wheel contents), test fidelity, production startup.
- **Candidate owner module:** keep one `testing` package but give it a contract:
  it may depend on domain **public façades** only, never on `_private` modules;
  consolidate mock providers/responses under it or explicitly legalize their
  current homes.
- **Extraction sketch:** decision needed (see `04-extraction-roadmap.md`):
  either exclude `src/film_pipeline/testing/` from the wheel (dev-only) or keep shipping it and
  make `src/film_pipeline/app/mock_responses.py` + `src/film_pipeline/providers/mock_*` import from it.
- **Prior art:** `tests/unit/graph/test_startup_boundaries.py:1` docstring records
  the historical leak.

### F-BOUNDARY-07 — `scripts/` is outside every CI gate and re-spells the phase, artifact-id and MCP-tool vocabularies as bare literals
- **Class:** O1 (duplicated normative model) + O4 (parallel registries)
- **Severity:** High (impact 3 × drift 5 = 15). Impact 3, not 4–5: these are dev/operator
  harnesses, not shipped code, so no human deliverable is corrupted. Drift 5 by §1.5's own
  definition — "no test can fail when one site changes": `scripts/` is out of ruff
  (`pyproject.toml:127` `exclude = ["scripts/", "langgraph.json"]`), out of mypy
  (`Makefile:42` runs `mypy src tests`), out of pytest (`pyproject.toml:83`
  `testpaths = ["tests"]`) and out of coverage (`pyproject.toml:94`
  `source = ["film_pipeline"]`).
- **Concern:** who owns the phase, artifact-id and MCP-tool vocabularies on the operator
  side of the repo.
- **De-facto owners (script re-spelling; canonical owner in brackets):**
  - `scripts/e2e-real-auto-approve.py:113-121` — a 7-name list — `"PHASES = ["` … `"gen_planning",`
  - `scripts/test-full-pipeline-direct.py:58-66` — a 7-name dict — `"phase_labels = {"` … `"gen_planning": "GENERATION PLAN",` — **the only copy that gates control flow**
  - `scripts/test-camino.py:86-94` (7) — `"for phase, label in ["` … `("gen_planning", "GEN PLANNING"),` — `phase` is never read in the body
  - `scripts/test-neon-ramen.py:76-85` (8) and `scripts/test-real-pipeline.py:87-96` (8) — the same tuple shape, same dead `phase`
  - `scripts/test_real_mcp_operator.py:213` — `'for phase_name in ["constitution", "development", "script"]:'` — `phase_name` reaches only log text
  - `scripts/diagnose-agent-output.py:205,218,234` — `'if target in ("constitution", "all"):'` and the same for `development` / `script`
  - `src/film_pipeline/schemas/_base.py:77-90` — canonical — `"class FilmPhase(StrEnum):"` … `'VISUAL_DEV = "visual_dev"'`
  - **The enum is already imported in four of the offending files** — `scripts/test-camino.py:21`, `scripts/test-neon-ramen.py:25`, `scripts/test-real-pipeline.py:36`, `scripts/test-full-pipeline-direct.py:17` — `"from film_pipeline.schemas._base import FilmPhase"` — and `scripts/test-camino.py:110` uses `list(FilmPhase)` for its artifact sweep while the loop at `:86` uses bare strings.
  - artifact ids — `scripts/test-camino.py:130` and `scripts/test-neon-ramen.py:119` — `'for aid in ["project_profile", "film_constitution", "treatment", "scene_list", "script"]:'`; also `scripts/test-real-pipeline.py:141-148`, `scripts/e2e-real-auto-approve.py:176-183`; canonical `src/film_pipeline/schemas/_base.py:27-74` `ArtifactType`
  - module layout — `scripts/test-camino.py:117` — `'sm_path = SCRATCH_ARTIFACTS / PROJECT_ID / "05-shot-bible" / "shot_matrix.v1.json"'`; canonical `src/film_pipeline/artifacts/paths.py:14-26` (`PHASE_DIR_MAP`, `"shot_bible": "05-shot-bible"`)
  - MCP tool names — 56 literal lines in 6 files, e.g. `scripts/e2e-real-auto-approve.py:85` — `'"create_film_project",'`; canonical `src/film_pipeline/mcp/tools/registry.py:148` — `'_register(registry, "submit_idea", ToolGroup.INTAKE, submit_idea, mutates=True)'`
  - agent ids — `scripts/diagnose-agent-output.py:207,220,236` — `'agent_id="treatment-agent",'` (also `film-constitution-agent`, `screenwriter-agent`); canonical `src/film_pipeline/agents/mvp/__init__.py:15` `MVP_AGENTS: list[AgentRegistration] = [` (`:45` `film-constitution-agent`, `:59` `treatment-agent`)
- **Measured inventory (canonical-derived, not grep-alternation-derived):** **50 lines /
  53 occurrences** of phase-name literals — `script` 13, `development` 9, `constitution` 8,
  `intake` 6, `visual_dev` 5, `shot_bible` 5, `gen_planning` 5, `generation` 2 — plus
  **10 lines / 14 occurrences** of artifact-id-only literals, **56 MCP-tool-name** lines
  and **3 roster agent-id** lines, across **8 of the 9 files**. The `grep -cE '"(intake|…)"'`
  form quoted in `reviews/adversarial-coverage.md` §H13 also returns 50, but it hardcodes
  the vocabulary it measures; the command below derives the set from `FilmPhase` instead.
- **Drift proof (mutation scenario):** rename the value of `FilmPhase.VISUAL_DEV` from
  `visual_dev` to anything else — the blueprint already spells it `visual_development`
  (see the A1 section above). State then carries `visual_development` while
  `scripts/test-full-pipeline-direct.py:63` still holds `"visual_dev"`; the gate at
  `:73-76` compares them and on mismatch only prints
  `print(f"⚠️  Expected phase '{expected}', got '{active_phase}' — skipping...")` and
  executes `continue`. The script has no `sys.exit` and no re-`raise` (its last line is
  `print("\n🎬 Done!")`, `:143`), so it exits **0** with that phase never approved — a
  red end-to-end run reported as green. The other three harnesses are worse: their
  `phase` loop variable is never read (`scripts/test-camino.py:86`,
  `scripts/test-neon-ramen.py:76`, `scripts/test-real-pipeline.py:87` iterate tuples but
  branch on `rt.get_active()`), so their lists drift invisibly. **No test, lint or
  type-check can fail on either mutation** — the gate commands below show that nothing
  in CI ever executes or even parses these files.
- **Reproduce:** all commands run from the repo root (the `ruff` scope check must be, or
  the `scripts/*.py` glob does not resolve).

```bash
# canonical-derived inventory: the vocabulary set comes from FilmPhase, not a hardcoded alternation
UV_CACHE_DIR="$PWD/.uv-cache" uv run python - <<'PY'
import pathlib, re, sys
sys.path.insert(0, "src")
from film_pipeline.schemas._base import FilmPhase
pat = re.compile("|".join(f'"{p.value}"' for p in FilmPhase))
lines = occ = 0
for f in sorted(pathlib.Path("scripts").glob("*.py")):
    for ln in f.read_text().splitlines():
        m = pat.findall(ln)
        lines += bool(m); occ += len(m)
print(f"phase-literal lines={lines} occurrences={occ}")   # phase-literal lines=50 occurrences=53
PY
# the H13 grep form, for cross-check
grep -cE '"(intake|constitution|development|script|visual_dev|shot_bible|gen_planning|generation|qc|post|delivery)"' scripts/*.py | awk -F: '{s+=$2} END{print s}'   # 50
# no gate can fail when one of these sites changes
UV_CACHE_DIR="$PWD/.uv-cache" uv run --python 3.12 --group dev ruff check --no-cache . 2>&1 | grep -c scripts/   # 0
UV_CACHE_DIR="$PWD/.uv-cache" uv run --python 3.12 --group dev ruff check --no-cache scripts/*.py 2>&1 | grep -Eo 'Found [0-9]+ errors' # Found 66 errors
grep -rn "scripts/" tests/ --include='*.py' | wc -l   # 0
```
- **Blast radius:** the five phase-approval harnesses (`scripts/test-camino.py`,
  `scripts/test-neon-ramen.py`, `scripts/test-real-pipeline.py`,
  `scripts/test-full-pipeline-direct.py`, `scripts/e2e-real-auto-approve.py`), plus
  `scripts/test_real_mcp_operator.py` and `scripts/diagnose-agent-output.py`, plus any future script copied from them or written by an
  agent reading `scripts/` as the worked example of driving the MCP surface. User-visible
  consequence: false-green end-to-end verification of a pipeline that spends real
  provider money (`scripts/e2e-real-auto-approve.py:28` sets `FILM_PIPELINE_MCP_MODE = "real"`),
  and a stale storage-layout literal (`"05-shot-bible"`) that silently reads nothing if
  the directory is renamed.
- **Candidate owner module:** `phase-model` (per `docs/modular-architecture/02-duplication-ledger.md` L-15 and
  F-PHASE-02) owns `FilmPhase`/`PHASE_ORDER`; `schemas._base.ArtifactType` and
  `artifacts.paths.PHASE_DIR_MAP` own the other two. `scripts/` should keep no vocabulary
  of its own — it imports those owners, or a thin `scripts/_vocab.py` re-export if scripts
  stay outside the package.
- **Extraction sketch:** (1) delete each parallel list and derive it from the owned
  order table (`src/film_pipeline/graph/_action_routing.py:18` `PHASE_ORDER`); note that
  `FilmPhase` declaration order happens to equal `PHASE_ORDER` today, so
  `[p.value for p in FilmPhase][:7]` is *equivalent but still a silent coupling* — use the
  owner. (2) Replace artifact-id literals with `ArtifactType.X.value`. (3) Replace
  `"05-shot-bible"` with `PHASE_DIR_MAP[FilmPhase.SHOT_BIBLE]` or a `ProjectStorage` path
  helper. (4) Guard test: an AST scan over `scripts/*.py` that fails on any `ast.Constant`
  string equal to a `FilmPhase` / `ArtifactType` member value or a name in the MCP tool
  contract table, plus removing `scripts/` from `pyproject.toml:127` so ruff lints it at
  all (66 errors today).
- **Prior art:** the *concern* is not new — `docs/modular-architecture/02-duplication-ledger.md:384`
  (L-15) records the phase-vocabulary duplication as Critical (4×4=16) with owner
  `phase-model`, and `docs/modular-architecture/audit/01-phase-model-and-transitions.md`
  F-PHASE-02 enumerates the eleven `src/` definitions. Audit 01's coverage table
  (`docs/modular-architecture/audit/01-phase-model-and-transitions.md:103`) and its "Unverified hypotheses and
  coverage gaps" section (`:576-578`) record the scripts lists verbatim as
  `"outside the \`src\` ownership map"` and `"I read the lists but did not audit script
  behavior."` **New here:** the scripts-side anchors and counts
  (50/53 phase, 10/14 artifact-id, 56 tool-name), the fact that four files import
  `FilmPhase` and then re-spell it, the live silent-skip gate at
  `scripts/test-full-pipeline-direct.py:73-76`, the `"05-shot-bible"` layout literal, and the
  proof that `scripts/` is outside all four CI gates.
- **Provenance:** uncovered by the adversarial coverage pass (`reviews/adversarial-coverage.md` §H13); added post-verification.

---

## Clean concerns (single-owner, already guarded)

| Concern | Owner | Guard |
|---|---|---|
| Storage layout & writes | `artifacts` (`ProjectStorage`) | `tests/unit/artifacts/test_storage_boundary.py` (5 AST rules + façade-API assertion) |
| Graph must not import test fixtures / composition root | `graph` | `tests/unit/graph/test_startup_boundaries.py` (AST sweep incl. lazy imports + fresh-interpreter check) |
| Profile-leaf reads (config contract) | `config` | `tests/unit/config/test_config_contract.py` (AST read-sweep + `KNOWN_DEAD_GROUPS` citations) — *added per verify-14* |
| Orchestrator constants ↔ schema ↔ registry parity | `graph` | `tests/unit/graph/test_channel_registry.py` (triangle completeness, propagation parity, writer sweep) — *added per verify-14* |

These are the **four** hand-written AST guards in the repo — two import boundaries
(`artifacts`, `graph`) and two contract guards (`config`, `graph`). Reproduce the count of
four from the repo root (`grep -rln "^import ast" tests/unit --include='*.py' | sort` →
exactly those four files). They are the precedent to generalize, not to copy file-by-file.

## Candidate module boundary

A `module-law` concern, owned by:

- **Normative model:** one explicit table of `(from, to) → allowed | forbidden |
  via-contract`, replacing `AGENTS.md:51`.
- **Invariant enforcement:** one parameterized AST-based guard suite under
  `tests/unit/architecture/`, plus the existing storage/graph specializations
  folded in.
- **Representation authority:** the table itself is the only place the law is
  written; docs link to it instead of restating it.

This candidate is a *meta* module (test + declaration), not a runtime import
target — see `design/proposal-B-enforcement.md` for mechanism options.
