# Orchestrator verification notes — independent reproductions and corrections

Baseline: `fb85baa0e6b769b709791a96a89980089304bf13` (`modular-app`), clean tree.
Author: the orchestrating agent, not an audit author and not a per-audit verifier.
Purpose: record facts **I reproduced myself**, the defects they expose in the audit and
synthesis files, and the corrections that must be applied downstream. Every number here was
measured at the baseline commit; every command is given so it can be re-run.

This file exists because the audit set is a moving target: the 14 audit files were written
concurrently, verified independently, and then corrected in a fix loop, while the four
synthesis documents were being drafted from the pre-correction versions. Cross-cutting
numbers therefore drifted between files. These are the ones I checked.

---

## V1 — Validator threshold literals: `24 / 20` is wrong; the truth is `22 / 18`

**Claim found in the audits and syntheses.** "The score→status grammar exists as a class default
(85/75/65) and as **24** call-site literals, **20** of which use `block_below=75`."

**Measured truth.**

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run python - <<'PY'
import ast, pathlib
rows = []
for p in sorted(pathlib.Path("src").rglob("*.py")):
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "ValidatorThresholds":
            rows.append({k.arg: ast.literal_eval(k.value) for k in n.keywords})
print(len(rows), sum(1 for r in rows if r), sum(1 for r in rows if r.get("block_below") == 75))
PY
```

- **23** `ValidatorThresholds(` calls in `src/`. **22** carry all three literals; the 23rd is the bare
  default construct at `validation/thresholds.py:21`.
- Distribution: **18× (85, 75, 75)**, **3× (80, 70, 70)**, **1× (90, 80, 80)**.
- `block_below == review_at` in **22 of 22** cases. `block_below == 75` in **18**, not 20.
- The origin of `24`/`20` is a grep that also matched the `class ValidatorThresholds(` definition
  line and the Pydantic `Field(default=65.0, …)` line at `schemas/registries/validator_registry.py:14-19`.

**Conclusion unchanged.** `score_to_status(70)` with `(85, 75, 75)` returns `blocked`; sweeping
scores 0–100 over that threshold yields only `{pass, pass_with_notes, blocked}`. `NEEDS_REVISION`
is genuinely unreachable through the threshold band.

**Corrections applied / owed.**
- `01-ownership-map.md:78` — **fixed by me** to 22 call-site literals, 18 at `85/75/75`.
- `audit/03-config-profile-and-defaults.md:298` — already corrected by its author to 22/18.
- `audit/03-config-profile-and-defaults.md:747` — **was still 24/20**; fix requested from the audit-03 author.
- `02-duplication-ledger.md` entry `L-14` — **was still 24/20**; fix requested from the ledger author.

---

## V2 — `L-02` agent→profile map: the cited test path does not exist, and the seam is stronger than stated

**Measured truth.**

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
from film_pipeline.graph.nodes._context import _AGENT_PROFILE_MAP
from film_pipeline.agents.mvp import MVP_AGENTS
d = {a.agent_id: a.default_model_profile for a in MVP_AGENTS}
print(len(_AGENT_PROFILE_MAP), len(d))
print([(k, d.get(k), _AGENT_PROFILE_MAP.get(k)) for k in sorted(set(d) | set(_AGENT_PROFILE_MAP)) if d.get(k) != _AGENT_PROFILE_MAP.get(k)])
"
```

- `_AGENT_PROFILE_MAP` (`graph/nodes/_context.py:27`) has **21** entries; the `MVP_AGENTS` roster has
  **11** agents carrying a declared `default_model_profile`. **10** map keys have no roster entry.
- Two shared keys diverge: `intake-classifier-agent` (`creative_writer` declared at
  `agents/mvp/__init__.py:40` vs `operations_triage` in the map) and `structure-extractor-agent`
  (`schema_enforcer` declared at `:96` vs `strict_validator` in the map).

**Defect in the ledger's drift proof.** It cites `tests/unit/agents/test_model_routing*.py`. That
path does not exist. The real file is `tests/unit/agents/model_routing/test_routing.py` (142 lines),
and it does not compare the map with the roster at all. The actual roster check is
`tests/unit/graph/test_agent_profile_routing.py:35-40`, and it asserts **membership only** — it never
compares values. Two other tests in the same file pin the divergent values as if correct:
`:21` asserts `structure-extractor-agent == "strict_validator"` and `:25` asserts
`intake-classifier-agent == "operations_triage"`.

**Consequence.** The seam is worse than "a test pins the wrong map" — a test suite actively encodes
the wrong values as expected, so any fix must change the tests as well. And because the map is a
21-entry registry against an 11-agent roster with different cardinality, this is **O4 (parallel
registry)** in addition to the O1+O5 already recorded: the map is not derivable from the roster by
any mapping.

---

## V3 — The "eight forbidden domain→domain edges" count is not reproducible as an enumeration

**Claim found in `audit/14` and `02-duplication-ledger.md` `L-48`.** "At HEAD **eight** distinct
forbidden edges exist (`agents→providers`, `config→providers`, `generation→providers`,
`generation→artifacts`, `post→validation`, `testing→artifacts`, `testing→checkpoints`,
`testing→providers`)."

**All eight edges are real** — I confirmed each. The defect is that the number is presented as a
complete enumeration when it is the union of three *targeted* greps
(`agents|config|generation` → `providers`; `post` → `validation`;
`testing` → `artifacts|checkpoints|providers`). Those greps cannot see any other package pairing.

**Measured truth** (AST, `src/film_pipeline/**/*.py`, `ImportFrom`/`Import` at package granularity,
self-edges removed, `graph` and `mcp` excluded as sources because `AGENTS.md:51` exempts them):

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run python - <<'PY'
import ast, pathlib, collections
root = pathlib.Path("src/film_pipeline")
pkgs = {p.name for p in root.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
edges = collections.defaultdict(set)
for p in sorted(root.rglob("*.py")):
    rel = p.relative_to(root)
    if len(rel.parts) < 2: continue
    src = rel.parts[0]
    for n in ast.walk(ast.parse(p.read_text())):
        mods = [n.module] if isinstance(n, ast.ImportFrom) and n.module else (
            [a.name for a in n.names] if isinstance(n, ast.Import) else [])
        for m in mods:
            if m.startswith("film_pipeline.") and m.split(".")[1] in pkgs and m.split(".")[1] != src:
                edges[(src, m.split(".")[1])].add(str(rel))
print(len(edges))
PY
```

- **53** cross-package edges exist in total; **32** have a source other than `graph`/`mcp`.
- Removing `schemas` as a target (the contract layer every package must import) leaves **21**.
- Removing `artifacts` as a target too (the law's own words are "they communicate through
  `artifacts`", which reads as permission to use the storage façade) leaves **17**.
- Removing the composition roots `app` and `cli` leaves **7** domain→domain edges plus the three
  `testing→*` edges = the audit's eight minus `generation→artifacts`.

**What this means for the deliverable.** The count is not wrong so much as **undefined**: the law
never says whether `app`, `cli`, `testing`, `checkpoints`, `kb`, `constraints` and `review` are
"domain modules", and it never says whether importing the `artifacts` façade counts as
"communicating through `artifacts`" or as a forbidden edge. That ambiguity — not the count — is
what the target architecture must remove. Until an edge matrix is written, "eight" and "32" are
both defensible and neither is a fact.

**Required downstream.**
- `03-target-architecture.md` must publish an **explicit edge matrix** with an explicit definition
  of "domain module" (which packages are contract layers, which are composition roots, which are
  shipped-but-not-production `testing`), and state the resulting forbidden-edge count under that
  definition. Do not repeat "eight" without the definition.
- `05-enforcement-and-guard-tests.md` must make the guard test consume that matrix rather than a
  hand-maintained list, so the count is a derived number, not a written one.
- `02-duplication-ledger.md` `L-48` should say "eight edges under the audit's targeted grep; the
  law as written does not define the scope, so the enumeration is not authoritative".
- `01-ownership-map.md:268` said **7** edges — stale; **fixed by me** to 8 with the scope caveat.

---

## V4 — Private reach-ins: exact counts and anchors

Measured by AST over `src/film_pipeline/**/*.py`, counting cross-package `ImportFrom`s whose module
path contains a `_`-prefixed segment, plus imported names that are `_`-prefixed.

- **107 cross-package private-module import sites**: **106** to `film_pipeline.schemas._base`,
  **1** to `film_pipeline.app._persistence` (`mcp/server.py:248`).
- **72** distinct files outside `schemas` import `schemas._base`.
- **3 cross-package private-symbol import sites**:
  - `app/_graph_exec.py:319` → `graph.nodes._run_validators`
  - `app/_graph_exec.py:449` → `graph.nodes.approval._PHASE_NODES`
  - `config/profile_resolver.py:204` → `providers.credentials._env_var_for`
- `schemas` import surface: **322** `ImportFrom` statements total = **252** cross-package +
  **70** intra-package. (The "323" figure that circulated in `enola-architecture-facts.md:79` counts
  a docstring line at `schemas/__init__.py:5`; the AST number is 322.)

Note: an earlier summary of mine said "105 `schemas._base`"; the measured value is **106**. The
AST number is authoritative.

---

## V5 — Finding counts are no longer 148, and the class mix has changed

The `148 findings — 42 Critical, 80 High, 25 Medium, 1 Low` headline was taken **before** the fix
loops. The fix loops legitimately *added* findings that the verifiers had surfaced and the auditors
had missed. Counted from the corrected audit files (`grep -c '^- \*\*Severity:\*\*' audit/*.md`):

| Audit | Findings now | Note |
|---|---|---|
| 01 phase model | 10 | — |
| 02 orchestration state | 16 | — |
| 03 config / profiles | 13 | — |
| 04 agents / prompts | 12 | grew from 10 |
| 05 providers | 7 | — |
| 06 generation | 13 | — |
| 07 artifacts / refs | 13 | grew from 9 (F-10…F-13 added) |
| 08 validation / review | 11 | — |
| 09 KB / provenance | 13 | grew from 10 (F-11…F-13 added) |
| 10 checkpoints | 11 | — |
| 11 MCP / safety | 15 | grew from 12 (F-MCP-13…15 added) |
| 12 post / budget | 13 | grew from 12 |
| 13 test doubles | 10 live + 1 withdrawn | `F-TEST-02` **withdrawn** as unprovable per §1.6.6; F-TEST-09…11 added |
| 14 module boundaries | 6 | — |
| **Total** | **163 live** | |

Severity distribution of the 163 live findings: **38 Critical, 83 High, 41 Medium, 1 Low.**

**Required downstream.** `README.md`, `02-duplication-ledger.md` and `04-extraction-roadmap.md`
must not repeat `148 / 42 / 80 / 25 / 1`. Either state the corrected numbers above, or state the
count as of a named moment and label the post-verification additions separately. A withdrawn
finding must not be carried as a live concern anywhere.

---

## V10 — A "middleware" layer was considered and is measurably unworkable — record it as rejected

While reviewing the target architecture I tested an obvious alternative that none of the three
design documents states and rejects: instead of extracting 20 modules, introduce one **middleware**
module that owns the cross-cutting mechanisms (state channels, dispatch tables, generation ledger,
delivery manifest), so callers stop re-deriving policy and `schemas` stops being imported 143 times
for one private base. The design already rejects `common`/`utils` (`03` §9.8) but not this, which is
a different and more plausible shape.

I measured what it would have to carry:

```bash
# middleware-owned mechanisms and their fan-in (AST, cross-package ImportFrom, film_pipeline only)
```

| Mechanism that middleware would own | Consumers today |
|---|---|
| `schemas._base` as the enums/`SchemaBase` contract | **143** import sites; 107 of them private-module reach-ins, 72 files outside `schemas` |
| State channels / writer law (`graph.state_schema`) | 58 imports of `graph.nodes` + 16 of `graph.router` + 15 of `graph.orchestrator_validators`, from `mcp.tools` (72) and `app.services` (16) among others |
| Tool dispatch and request contracts | `mcp.tools` imported 72 times from outside `mcp` |
| Generation ledger / dispatch tables | `agents.impl` 36, `validation.impl` 28 |
| **Total cross-package import statements in `src/`** | **442**, across **144 of 281** files; **145** distinct deep (module-level) import targets |

**It is unworkable for a reason that is measurable, not stylistic.** Middleware would have to be
imported by *every* production module, so under the law in `03` §4.1 it can only sit at the bottom of
the layer DAG (L0/L1) — which means it cannot hold anything that has behaviour or state without
becoming a second `graph`. And splitting mechanisms upward is not available either, because the
consumers are not separable:

- **Farm-out to the test suite is refuted by measurement.** `05`'s registry mechanism lets
  `tests/architecture/` resolve the graph from the filesystem, so tests need not import production
  modules for *architecture* facts. But the suite's ordinary coupling is total: of **180** test
  modules, **all 180** import production packages, for **856** production-import statements
  (`schemas` 206, `app` 175, `graph` 121, `mcp` 80, `artifacts` 64). Requiring each test to build the
  middleware it needs would mean rewriting the suite against a new indirection, which is strictly
  more churn than extracting the modules.
- **The four existing guards prove the same thing from the other direction.** They must import
  production middleware to observe it — `test_channel_registry.py` needs
  `graph.state_schema`, `graph.orchestrator_state`, `graph.services`, `graph.nodes` and
  `app.mock_responses`; `test_config_contract.py` needs `config.profile_resolver`,
  `config.runtime_overrides`, `graph.nodes` and `mcp.tools`; `test_storage_boundary.py` needs
  `artifacts.project_storage`. A guard for a mechanism is a consumer of that mechanism.

**Required downstream.** `03` should add this as an explicitly rejected alternative in its decisions
record (a `D12` row or a §9.8 bullet): the middleware/inversion-of-control option is rejected because
(a) 442 cross-package import statements across 144 files give it 144 captive consumers on day one,
(b) the layer DAG forces it to the bottom, where it can hold no behaviour or state, and (c) all 180
test modules would need rewriting to consume it. State it with these numbers so a future reader can
re-run them rather than take the rejection on faith. This is not a new proposal — it is the
documentation of a live alternative and the measurement that kills it, which is what bar B8 asks for.

## V9 — Correcting our own anti-rot evidence: the orphaned canary is ours, and there are 17 more like it

Several documents in this program use the orphaned bytecode file
`tests/unit/__pycache__/test_guard_canary.cpython-312-pytest-9.1.1.pyc` as evidence that "a guard
canary was silently written and deleted in this repo before". **That framing is not supported, and
I am correcting it because I propagated it myself.**

Measured provenance:

```bash
git log --all --oneline -- '*test_guard_canary*'                 # empty — never committed
git check-ignore -v tests/unit/__pycache__/test_guard_canary*    # .gitignore:5 __pycache__/
stat -f "%Sm" -t "%m-%d %H:%M" tests/unit/__pycache__/test_guard_canary*.pyc   # 09-25 12:41
```

- The `.pyc` was created at **12:41 on 2026-09-25**, inside this session's window (the audited commit
  `fb85baa` was made at 13:16 that day, and this program's own `design/prototype-enforcement/` work
  happened after that). Its embedded string is
  `Canary: write into a watched production root; the session guard MUST fail.` and its recorded source
  path is `tests/unit/test_guard_canary.py`. It is **our** artifact — the enforcement prototype
  subagent's canary — not a pre-existing repo loss.
- It was never committed (`__pycache__/` is gitignored), so no `git log` can show a deletion.

**What IS true, and is a better argument.** A sweep for orphaned bytecode (a `.pyc` whose source no
longer exists) finds **18** such files under `tests/`, not one:

| Category | Count | Examples |
|---|---|---|
| Deleted by a real, traceable refactor | 7+ | the five `tests/e2e/test_tui_*.py` + `tests/integration/cli/conftest.py`, removed by `37e9c65 refactor(tui): remove TUI package, tests, entry point, and textual dependency` |
| Tracked helpers that moved or were renamed | 8 | `tests/unit/graph/_helpers.py`, `tests/unit/mcp/tools/test_helpers.py`, `tests/unit/generation/_helpers.py`, … |
| Never tracked at all | 1+ | `tests/__pycache__/_helpers.py`, `tests/unit/artifacts/test_migration.py` |
| This program's own prototype canary | 1 | `tests/unit/__pycache__/test_guard_canary.cpython-312-pytest-9.1.1.pyc` |

**Why this matters more, not less.** The correct reading is not "a guard silently died here" but
"**this repository's test-inventory churn leaves no trace at all**": 18 stale bytecode files
accumulated, nothing cleans them, and nothing enumerates the test set as data, so the disappearance
of a file is invisible. That is a stronger and *verified* motivation for the guard-registry mechanism
in `05-enforcement-and-guard-tests.md` §5.5 (a registry that fails when a guard family disappears)
than the unverified claim.

**Required downstream.** `02`, `03`, `05` and `reviews/program-process-record.md` must stop asserting
that the canary proves a historical guard loss. Replace with the measured statement above, citing
this note. The guard-registry design is unchanged; only its justification is corrected.

## V8 — `_AGENT_PROFILE_MAP` is a 21-row registry with 8 dead rows (strengthens L-02 and audit 04's F-AGENT-12)

I checked the map against every registry that could legitimise a row:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run python - <<'PY'
from film_pipeline.graph.nodes._context import _AGENT_PROFILE_MAP as M
from film_pipeline.validation.validators import MVP_VALIDATORS
from film_pipeline.agents.mvp import MVP_AGENTS
agents = {a.agent_id for a in MVP_AGENTS}
vals = {e.validator_id for e in MVP_VALIDATORS}
print(len(M), len(agents), len(vals), sorted(set(M) - agents - vals), sorted(set(M) & vals))
PY
```

- `_AGENT_PROFILE_MAP` has **21** rows. **11** name a registered agent (`MVP_AGENTS`), **2** name a registered validator (`scene-continuity-validator`, `full-movie-flow-validator`), and **8 name nothing in either registry**: `character-dossier-agent`, `config-inference-agent`, `continuity-ledger-agent`, `environment-bible-agent`, `generation-scheduler-agent`, `kb-curator-agent`, `prompt-composition-agent`, `visual-dev-agent`.
- Of those 8, **5 have zero references anywhere else in `src/`** (`grep -rn '"<id>"' src/ --include=*.py` excluding `_context.py`): `character-dossier-agent`, `config-inference-agent`, `continuity-ledger-agent`, `kb-curator-agent`, `prompt-composition-agent`. The other three have exactly one reference each elsewhere.

**Combined with V2 and audit 04's `F-AGENT-12`, the true shape of this seam is:** a 21-row hand-maintained map that (a) silently overrides 2 of 11 registered agents, (b) carries 2 validator rows that contradict the validator registry and the validator implementations, and (c) carries 8 rows for ids that no registry declares. Audit 04's `F-AGENT-12` is correct as written — I verified its two citations (`validation/validators/__init__.py:131`, `:151` are both `model_profile="multimodal_reviewer"` for `scene-continuity-validator` and `full-movie-flow-validator`) and its reproduce command reproduces exactly. It does not state the 8-dead-rows count.

**Required downstream.** `02` should fold the dead-row count into `L-02`; `03` should state that the target replaces the map with the registered descriptor's `default_model_profile` and that the map's validator rows are deleted, not migrated.

## V7 — A fifth artifact-ish vocabulary the audits only partly capture

Investigating `L-18`'s "enum-only" values turned up something the audits handle only in
passing. `ArtifactType` declares `CLIP`, `LAST_FRAME`, `MID_FRAME` with no registry entry and no
covering prefix, and I checked whether anything actually constructs them:

```bash
grep -rn '"last_frame"\|"mid_frame"\|"clip"' src/ --include=*.py | grep -v schemas/_base.py
```

- `generation/executor_delivery.py:132-148` — `_asset_kind(path)` classifies produced filenames into
  `last_frame`, `mid_frame`, `generated_clip`, `reference_sheet`, `audio_stem`, with a **fallthrough
  to `generated_clip` for any unrecognised file, including `.json`**. This is a fourth kind
  vocabulary. Audit 06 (`F-GEN-*`) and audit 07 (`F-ARTIFACT-11`, "fourth kind vocabulary") do
  capture it; `02` carries it. No correction needed, recorded here as cross-checked.
- `schemas/matrix.py:21` — `input_frame_type: str = Field(default="last_frame")`. This is a **fifth**
  vocabulary item: an untyped `str` whose only occurrence in the entire repository is its own
  definition — `grep -rn input_frame_type src/ tests/` returns exactly one hit, the field itself, and
  nothing outside `src/`. It reuses the same `last_frame`/`mid_frame` tokens that `ArtifactType`
  declares as artifact kinds, so a reader cannot tell whether the string means "an artifact kind" or
  "a frame-chaining mode".

**Required downstream.** Treat this as a small addition to `L-18` (or a sibling entry), not a new
program: one line stating that the target must decide whether `last_frame`/`mid_frame` are artifact
kinds, frame-chaining modes, or both, and must not leave a `str` field with zero readers carrying a
token that another vocabulary also owns. It is the same class as audit 09's F-06 "unwired dead
policy" (Medium) and should not be inflated above that.

## V6 — Verification coverage is complete except audit 10

`reviews/verify-01.md` … `reviews/verify-14.md` all exist; `verify-10.md` was the last authored.
Aggregate verdicts: **zero findings rejected**; roughly 20 findings had severity or class
corrected; verifiers surfaced roughly 30 seams the audits had missed. The audit files are the
corrected ground truth after their fix loops; the `verify-*.md` files are the record of what was
disputed and why.

**Anti-pattern to avoid.** Three separate files stated the same threshold count and all three were
wrong in the same direction, while a fourth file (audit 03 §2) had already corrected it. That is a
small instance of the exact failure this program audits: a number duplicated across owners with no
single authority and no guard. The target architecture should note it as motivating evidence for
the "one concern, one owner" rule rather than treating it as a documentation slip.

---

# Round 3 — reproducing the adversarial coverage pass (V11–V19)

The adversarial coverage review (`reviews/adversarial-coverage.md`) claims 13 ownership holes the
14 audits missed. A reviewer's finding is not evidence until it is reproduced, so I reproduced the
nine cheapest and most load-bearing before accepting any of them. All nine confirmed. Commands and
observed output below; nothing here is a paraphrase of the review.

## V11 — Confirms H1: the reference-sheet frame-role vocabulary is divergent *and executed*

```bash
UV_CACHE_DIR=$PWD/.uv-cache uv run python - <<'PY'
from film_pipeline.generation.compositor._layout import _CHAR_TILES
from film_pipeline.generation.compositor.environment import _ENV_TILES
from film_pipeline.generation.prompt_builder import _ENVIRONMENT_FRAME_ROLE_TEXT
print(len(_CHAR_TILES), len(_ENV_TILES), len(_ENVIRONMENT_FRAME_ROLE_TEXT))
print(sorted(set(_ENVIRONMENT_FRAME_ROLE_TEXT) - set(_ENV_TILES)))
PY
```

Observed: `13 8 10` and `['alt-angle-entrance', 'lighting-overcast-morning']`. The character pair is
exactly equal (13 tiles, 13 prompts, no difference either way); the environment pair is not. So a
prompt can legitimately request two environment roles that the compositor has no tile for, and
`schemas/reference.py` types `frame_role` as a free `str`, so nothing rejects them earlier. This is
an **existing** divergence, not a mutation scenario — the strongest §1.6.3 form.

## V12 — Confirms H3: two pacing alias tables with disjoint source vocabularies

```bash
UV_CACHE_DIR=$PWD/.uv-cache uv run python -c "
from film_pipeline.constraints._keywords import _PACING_KEYWORDS as K
from film_pipeline.graph.scope_contract import _PACING_ALIASES as A
print(len(K), len(A), sorted(set(K)-set(A)), sorted(set(A)-set(K)))"
```

Observed: `10 10 ['moderate', 'slow', 'slow cinema'] ['character_driven', 'irregular', 'narrative']`.
`_PACING_KEYWORDS['slow cinema'] == 'slow_cinema'`, while `normalize_pacing('slow cinema', 'narrative')`
returns `standard`, because `_PACING_ALIASES` has no `'slow cinema'` key and falls through to
`_FILM_TYPE_DEFAULT_PACING`. The canonical vocabulary is a `Literal` in `schemas/constraints.py:61`,
re-spelled as plain `str` in `graph/scope_contract.py:17-19` and `schemas/execution_brief.py:51`.
This also contradicts `01-ownership-map.md` §12's "`constraints` = SINGLE (clean)".

## V13 — Confirms H4: the capability-routing sets are dead *and* share no token with the roster

```bash
grep -n "preferred_capability" -r src/ | grep -v _agent_routing.py
sed -n '86,95p' src/film_pipeline/graph/nodes/_agent.py
```

Observed: `_REVIEW_CAPABILITIES` = `{review, validation, qc, inspecting}` and
`_REPAIR_CAPABILITIES` = `{repair, revision, replan, correcting}`; the 30 capabilities declared by
`MVP_AGENTS` intersect both sets in the **empty set**; and the sole production caller
(`graph/nodes/_agent.py:86`) passes `task_type`, `registry` and `preferred_agent_id` but **not**
`preferred_capability`. The only caller that supplies it is a test. So the branch is unreachable in
production *and* the tokens it compares against are not the roster's tokens — a future caller who
supplies a real roster capability would silently get the task-type fallback.

## V14 — Confirms H8: two identical generation-mode resolvers

`_parse_generation_mode` (`graph/nodes/_generation_batch_planning.py:20`) and
`_resolve_generation_mode` (`mcp/tools/generation/planning.py:21`) construct `GenerationMode` from a
string with the same silent `TEST` fallback. They differ only in whether the argument arrives as a
bare string or as `str(args.get("mode", "test"))` — that is, they are the same policy with two
bodies and no shared contract.

## V15 — Confirms H9: `_pending_row_updates` is a second, undeclared state key

```bash
grep -rn "_pending_row_updates" --include=*.py src/ tests/
```

Observed, exactly three sites: `graph/nodes/qc.py:421` writes it with `setdefault`,
`graph/nodes/qc.py:70` pops and consumes it, and `app/_graph_exec.py:336` **pops and discards** it.
It appears in no `TypedDict`, in no channel declaration and in no test. The third site is the
interesting one: the app execution path silently drops a patch the graph path applies.

## V16 — Confirms H6: a DISTRIBUTED concern in the map with no finding id

`01-ownership-map.md` (§9 region) carries
`| Compression / bounding | no single owner (3 sites + ad-hoc slices) | **DISTRIBUTED** | (recorded in audit 09) |`
— a DISTRIBUTED assertion whose Findings column names no `F-…` id, while `audit/09` analyses it in
prose without promoting it. That is a bar A6 record gap independent of whether the underlying seam
is severe. Reproduce: `grep -n "recorded in audit 09" 01-ownership-map.md`.

## V17 — Confirms H10: `pacing_style` is typed in one schema and bare in two, and is named nowhere

```bash
grep -rn "pacing_style" src/film_pipeline/schemas/ docs/modular-architecture/audit/
grep -rn "pacing_style" docs/modular-architecture/0*.md
```

Observed: three `src/` hits — a typed `Literal` in `schemas/constraints.py:61`, a bare `str` in
`schemas/execution_brief.py:51`, a bare `str` in `schemas/scope_contract.py:23` — and **zero** hits
in any audit file and **zero** in `01`–`05`. A normative field of the structural brief is invisible
to the whole deliverable.

## V18 — Confirms H12: the declared source of truth prints a phase the code rejects

`documentation/architecture-blueprint.md` prints `"current_phase": "visual_development"` (twice, in
JSON examples) while `schemas/_base.FilmPhase` has `visual_dev` and no `visual_development` member.
`AGENTS.md` names that blueprint as the architectural source of truth, so the drift is a real
reproduction hazard for a human copying the example.

## V19 — Confirms H13 and H11, and fixes the number method

- `scripts/`: 9 Python files / **1,678** lines, containing hardcoded phase-name literals
  (`"script"` ×13, `"development"` ×9, `"constitution"` ×8, `"intake"` ×6, `"visual_dev"` ×5,
  `"shot_bible"` ×5, `"gen_planning"` ×5) and no guard. Sampled by audit 11, never audited.
- **H11 is a defect in our own output, and it was worse than the adversary said.** The ownership
  map printed corpus totals and a class distribution that its own commands did not produce, because
  the class line had been measured over the ledger's *consolidated concerns* while the audit files
  were still being edited. Fix applied in `01-ownership-map.md`: one method, one command, numbers
  printed from that command; the second class distribution is explicitly withdrawn. The adversary's
  independently-derived O1/O2/O3/O4 counts (60/23/31/26) matched mine exactly, which is what
  convinced me the counting method — not the adversary — was the thing to standardise on.

**Required downstream (all 13).** Each surviving hole becomes a §1.7 finding in the audit that
should have owned it, then a concern in `02`, then scope in `04`, then a guard in `05`. A hole that
does not reproduce does not become a finding; a hole that is real but is a *documentation* defect
(H11) is fixed in the document rather than dressed up as a code finding. See
`reviews/program-process-record.md` §"The adversarial round".

## V20 — `F-CRP-12` is reachable through the declared entry point, not just a bare import

The audit-10 fix loop promoted the import-poisoning seam to `F-CRP-12` at Critical 5×5=25, and I
had already reproduced the mechanism (`graph/graph.py:201` module-level `build_graph()` →
`_default_checkpointer()` → `graph/graph.py:49` `checkpoint_dir.mkdir(parents=True, exist_ok=True)`
→ `ensure_storage_root` later refuses the root). The open question was severity, not mechanism: a
Critical that only fires in a contrived scenario should be downgraded. It is not contrived.

- `tests/conftest.py:99` sets `FILM_PIPELINE_NO_PERSIST=1` for the whole session and `:31` deletes
  `PERSIST_STATE` per test, so the suite can never trip it. That is *why* no test catches it — it is
  also why "the test suite is green" says nothing about this seam.
- `mcp/server.py:243-244` sets `FILM_PIPELINE_PERSIST_STATE=1` (via `setdefault`) as the **default**
  for a stdio MCP run unless `NO_PERSIST` is set. The bounded checkpointer is therefore on by default
  in the shipped MCP entry point.
- `langgraph.json` names `graph/graph.py:graph`, so the LangGraph tooling imports the module at
  process start — a bare import with whatever environment it inherits. `app/_graph_exec.py:37` and
  `app/smoke.py:14` do the same import lazily.
- The storage root is only initialized when an `ArtifactStore` is constructed
  (`artifacts/store.py:61`, `graph/services.py:49`), which is strictly later than module import.

So the reachable sequence is: an operator (or the MCP server itself) has persistence enabled → the
declared graph entry point is imported → the default root gains a `checkpoints/` child with no
`storage.json` → the first `ArtifactStore` construction raises `StorageRootError` and the app refuses
its own storage root. The failure is *loud at the point of use* and *silent at the point of cause*,
which is the worse ordering: the operator sees a refusal in a directory the application created.
Critical stands.

Two corrections to the audit's own narrative that I checked because they affect the claim: the
`mkdir` is at `graph/graph.py:49` (the verifier's original note cited `artifacts/storage.py:49`), and
`tests/conftest.py` neutralizes the path rather than merely avoiding it — worth stating, because it
is the difference between "untested" and "unreachable by the suite by construction".
