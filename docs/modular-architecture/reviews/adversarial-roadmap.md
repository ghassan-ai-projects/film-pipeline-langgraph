# Adversarial review — `04-extraction-roadmap.md`

Status: **adversarial review record, bar B5/B6 attack.** This file attacks the
extraction roadmap of `04-extraction-roadmap.md` against the real tree at
`modular-app@fb85baa`. It does not summarise the roadmap; it records objections,
the commands that produced them, and the verdict.

> **Superseded revision notice.** Revision 1 below (sections 0–5) reviewed the
> **23-phase (`P0`–`P22`) text at `04-extraction-roadmap.md` sha256
> `e12009b3…`, 1339 lines, mtime 2026-09-25T15:22:09**. That text is superseded.
> The frozen text is **21 phases (`P0`–`P20`), 1381 lines, sha256 `4f5a8db1…`,
> mtime 2026-09-25T15:39:16**. **`## Revision 2 — re-anchored against the frozen
> 21-phase roadmap`** (at the end of this file) re-adjudicates every objection
> below against the frozen text and is the operative verdict. Do not cite
> Revision 1's phase ids (`P21`/`P22`) or its line anchors against the frozen
> document.

## 0. Method, pins and commands

**Document under attack (pinned).**

```
$ wc -l docs/modular-architecture/04-extraction-roadmap.md
1339 docs/modular-architecture/04-extraction-roadmap.md
$ shasum -a 256 docs/modular-architecture/04-extraction-roadmap.md
e12009b380cb5282c9610400abd3aa1f059d041e372a60b7401152af412df862
$ stat -f '%N mtime=%Sm' -t '%Y-%m-%dT%H:%M:%S' docs/modular-architecture/04-extraction-roadmap.md
docs/modular-architecture/04-extraction-roadmap.md mtime=2026-09-25T15:22:09
```

Tree: `${REPO_ROOT}`, branch `modular-app`,
`git rev-parse HEAD` = `fb85baa0e6b769b709791a96a89980089304bf13`.

**Note on phase count.** The briefing says "21 phases P0–P20". The document has
**23 phases, P0–P22** (mechanical parse of the phase-table rows); `03` §2.5 still
calls the roadmap "its `P0`–`P20`". All counts below are against the real 23.

**Read in this order:** `00` (bars B5/B6), `02` (L-01…L-58), `03` (modules, law,
wave spine W0–W12), `05` (mechanism, playbook), `04` (the roadmap). Also read:
`reviews/verify-10.md`, `documentation/storage-upgrade-plan.md`.

**Commands used (all reproducible at `fb85baa`).**

```bash
# L-id coverage
grep -oE 'L-[0-9]{2}' docs/modular-architecture/04-extraction-roadmap.md | sort -u
comm -23 <(seq -w 1 58 | sed 's/^/L-/') <(grep -oE 'L-[0-9]{2}' docs/.../04-extraction-roadmap.md | sort -u)
# phase dependency graph (parsed the 'Depends on' column, DFS cycle check)
uv run --python 3.12 python - <<'PY'  # printed: 23 phases, non-earlier deps: [], cycles: []
# baseline test count
UV_CACHE_DIR="$PWD/.uv-cache" uv run --python 3.12 --group dev pytest --collect-only -q --no-cov
# subset-run coverage behaviour
UV_CACHE_DIR="$PWD/.uv-cache" uv run --python 3.12 --group dev pytest tests/unit/graph/test_channel_registry.py -q
UV_CACHE_DIR="$PWD/.uv-cache" uv run --python 3.12 --group dev pytest tests/unit/graph/test_channel_registry.py -q --no-cov
# change surface
grep -rn 'get_runtime' src/ tests/ --include='*.py'   # 158 refs / 54 files ; 243 refs / 41 files
grep -rn '_services' src/ tests/ --include='*.py'     # 112 / 43 ; 83 / 24
find src/film_pipeline/mcp/tools -type f -not -path '*__pycache__*' | wc -l   # 39
find src/film_pipeline/app/services -type f -not -path '*__pycache__*' | wc -l # 7
grep -rn '"blocking"' src/film_pipeline --include='*.py' | wc -l              # 59
grep -rn '_phase_gate_updates' src/ --include='*.py' | wc -l                  # 19
grep -rn '_phase_gate_updates' src/ --include='*.py' | grep -c 'gate='        # 9
```

All commands ran via `uv run` with `UV_CACHE_DIR="$PWD/.uv-cache"`. No command
from `make ci-check` was run; no file under `src/`, `tests/` or the repo root was
written.

---

## 1. OBJECTIONS

### O-1 — Blocking — P22 cannot be green: shim removal breaks two declared entry points CI actually executes

**Claim attacked** (`04-extraction-roadmap.md:1135-1144`): "**P22** … **Files.**
Every `# SHIM(W<n>)` re-export (`schemas/_base.py`, `graph/_action_routing.py`,
`app/services/operator.py`, `app/product_gate.py`, …)" … "delete shims"; acceptance
(`:268`) "`grep -rn "SHIM(W" src/` → 0"; size (`:1223`) "**S**".

**Evidence.**

```bash
$ grep -n 'product_gate\|product-gate' Makefile
98:product-gate: ## Enforce the working-product acceptance gate
100:	@$(UV_RUN) python -m film_pipeline.app.product_gate
108:ci-check: format-check lint typecheck test-cov build product-gate
$ sed -n '39p' pyproject.toml
film-pipeline-run = "film_pipeline.cli.run:main"
$ grep -rln 'film_pipeline\.cli' tests/ --include='*.py' | wc -l   # 8
$ grep -rln 'film_pipeline\.app' tests/ --include='*.py' | wc -l   # 69
$ grep -n 'test_help_snapshot\|tests/unit/cli' docs/.../04-extraction-roadmap.md   # (no output)
$ grep -n 'Makefile' docs/.../04-extraction-roadmap.md
343:...`Makefile` (UV_CACHE_DIR pin)          # P0 only
387:...`Makefile` (`arch-check`)              # P1 only
```

`make ci-check`/`ci-verify` run `product-gate` (`Makefile:108`, and CI runs
`make ci-verify` in `.github/workflows/ci.yml`). After P22 deletes
`app/product_gate.py`, `python -m film_pipeline.app.product_gate` raises
`ModuleNotFoundError`; no phase's Files/Steps/Deletions list contains
`Makefile:100`. `cli/` → `studio` is fixed by `03:1220` ("`cli/` | 4 | `studio`
4"), so `pyproject.toml:39` (`film_pipeline.cli.run:main`) is a renamed entry
point; P21 lists `pyproject.toml:59,95-98` — deliberately not `:39`. Eight test
files import `film_pipeline.cli` (e.g. `tests/unit/cli/test_help_snapshot.py:12`
`from film_pipeline.cli.run import _build_parser`) and 69 import
`film_pipeline.app`; none is named in P21/P22.

**Why it matters.** P22 is the seal phase; its own acceptance ("CI@90 %") is
unmeetable once shims are deleted, because the gate step that runs first in
`ci-check` fails. The plan leaves the tree with a broken console script and a
broken CI target at the exact commit that claims to be the clean end state.

**Smallest fix.** Add `pyproject.toml:[project.scripts]` and `Makefile`
`product-gate` to P21's Files, migrate the 8 + 69 test importers in P21, and let
P22 assert `SHIM(` tokens are gone *after* re-running `make product-gate` from the
new module path.

### O-2 — Blocking — P21 promotes a known Critical import-time defect to the declared `langgraph.json` entry point; its fix is deferred past P21

**Claim attacked** (`04-extraction-roadmap.md:1120-1121`): "**B7:** `langgraph.json`
→ `./src/film_pipeline/orchestration/graph.py:graph` (the graph object name and id
are unchanged)".

**Evidence.**

```bash
$ sed -n '201p' src/film_pipeline/graph/graph.py
graph: CompiledStateGraph = build_graph()
$ grep -n 'M41\|poisons\|import-time' docs/.../04-extraction-roadmap.md
1189:...adding the Critical missed seam M1).
$ sed -n '390p' docs/.../03-target-architecture.md
| **M41** | **`import film_pipeline.graph.graph` alone poisons the storage root** ... **Critical (5×5=25)** — the highest-severity missed seam in the program (verify-10 M1) | `studio`/`orchestration`/`checkpoints` | no import-time side effect: the compiled graph is built by `studio` ... |
$ sed -n '1174p' docs/.../04-extraction-roadmap.md
...M1 (Critical) belongs here too ... | after P19 and P21 |
```

`langgraph.json` is an entry point (`00:209-211`). P21 points the platform's
importer at the module whose module-level `build_graph()` (`graph/graph.py:201`,
`03:390` M41) is the defect. The roadmap schedules exactly one fix location for M41: DB-6,
trigger "after P19 and P21" — i.e. after the phase that ships the defective path.

**Why it matters.** B5 "leaves `make ci-check` green on its own" can hold while
the shipped entry point is defective, because no `ci-check` step imports the
module through `langgraph.json`. P21 ships the defect as the product surface.

**Smallest fix.** Move the M41 fix into P21 (construct the compiled graph in
`studio` after `RootLayout` resolves) or keep `langgraph.json` on the old path
until DB-6 lands, and add the import-time-no-write guard from `03` M41 to P21's
guard list.

### O-3 — Blocking — P12's acceptance/evidence requires the `meta.json` B7 change that P12's own rollback excludes

**Claim attacked** (`04-extraction-roadmap.md:793-794`): "**Tests.** …
mutable save→read preserves the ref"; (`:804-806`): "**Evidence.** … a mutable
artifact saved with a ref reads it back (today `null`)."; against (`:800-802`):
"**Rollback.** … **B7:** serialising `kb_context_ref` into `meta.json` changes
persisted representation, so it ships as its own documented compatibility change;
P12 covers root, ids, stamping point and builder wiring only."

**Evidence.**

```bash
$ sed -n '538p' src/film_pipeline/artifacts/store.py
            "kb_context_ref": meta.get("kb_context_ref"),
$ sed -n '270,291p' src/film_pipeline/artifacts/store.py
    def _write_mutable_meta(...):   # builds ArtifactCurrentMeta WITHOUT kb_context_ref
$ sed -n '251p' src/film_pipeline/artifacts/store.py
            kb_context_ref=meta.kb_context_ref,   # envelope DOES carry it
```

Today the envelope carries the ref (so an envelope round-trip already passes);
the only path that returns `null` is `load_metadata` via `meta.json`
(`store.py:538`), which P12 explicitly puts out of scope. "today `null`" therefore
identifies the excluded change.

**Why it matters.** The acceptance criterion cannot be met as written: either the
implementer ships the B7 `meta.json` change inside P12 (violating sequencing
principle 8 and the phase's own rollback) or the named evidence fails.

**Smallest fix.** Move the `meta.json` provenance migration into its own
documented B7 phase and change P12's evidence to the envelope round-trip
(`load_mutable_envelope`) that is true at baseline.

### O-4 — Blocking — `--cov-fail-under=90` is wired into `addopts`: every subset guard run fails by construction, so the B6 red/green demonstration cannot be executed as the roadmap writes it

**Claim attacked** (`04-extraction-roadmap.md:414-416`): "**Evidence.** The
red/green canary: add one synthetic private import on a scratch branch, show
`pytest tests/architecture` fails naming the offender, remove it."; done-rule
(`:1232-1234`): "The phase's guard test is shown red against a synthetic
re-introduction of the seam, then green with it removed."

**Evidence.**

```bash
$ sed -n '78,81p' pyproject.toml
  "--cov=film_pipeline",
  "--cov-report=term-missing",
  "--cov-fail-under=90",
$ UV_CACHE_DIR="$PWD/.uv-cache" uv run --python 3.12 --group dev pytest tests/unit/graph/test_channel_registry.py -q
TOTAL                                                               16073  10768   3956    153    28.00%
FAIL Required test coverage of 90% not reached. Total coverage: 28.00%
EXIT=1
$ UV_CACHE_DIR="$PWD/.uv-cache" uv run --python 3.12 --group dev pytest tests/unit/graph/test_channel_registry.py -q --no-cov
....................s...s......                                          [100%]
EXIT=0
```

`05` §6/§7.1 consistently uses `--no-cov` (`05:1978,1990,2003,2040,2086`); the
roadmap's P1 evidence omits it.

**Why it matters.** As written, the mandated canary exits 1 on coverage for *any*
subset, so "fails naming the offender" is not demonstrable and "then green" is
impossible without an undocumented flag. B6's canary requirement is unenforceable
as written.

**Smallest fix.** State `--no-cov` (or `make arch-check`) in P1's evidence and in
the §5 done-rule, matching `05` §6.

### O-5 — Major — P1's acyclicity guard is blind to 4 of the 5 recorded cycles (C1, C3, C4, C5 are intra-package)

**Claim attacked** (`04-extraction-roadmap.md:247`): P1 adds
"`test_contracts.py::test_declared_module_graph_is_acyclic`"; acceptance "every
observed edge declared"; `03` B3 requires "the resulting module graph is acyclic;
the law is mechanically checkable (import test or linter)".

**Evidence.**

```bash
$ sed -n '1225,1230p' docs/.../05-enforcement-and-guard-tests.md
def test_declared_module_graph_is_acyclic() -> None:
    graph = {
        name: {t for t in c.may_import if t in CONTRACTS} for name, c in CONTRACTS.items()
    }
```

`CONTRACTS` is built in P1 from "All 17 current `src/film_pipeline/*/__init__.py`"
(`04:383`). `03` §4.4 lists the cycles as **C1** `agents/prompt_templates` ↔
`agents/prompt_templates/defaults`, **C3** `graph` ↔ `graph/nodes` ↔
`graph/orchestrator_validators` ↔ `graph/subgraphs`, **C4** `providers` ↔
`providers/adapters`, **C5** `schemas` ↔ `schemas/registries`. All four are
inside one top-level package, so both endpoints collapse to the same `CONTRACTS`
key and the Kahn sweep never sees the edge. Only **C2** (`app` ↔ `mcp`) is a
top-level cycle. `05` §7.1 confirms enola is not in `ci-check` ("Total new CI
jobs: zero"; `arch-check` is "optional"); `.github/workflows/ci.yml` runs only
`make ci-verify`.

**Why it matters.** P2's acceptance "cycle C2 edge gone; no new cycle"
(`04:248`) and P3's "C1/C4/C5 source edges removed" (`:477-479`) rest on a guard
that cannot detect C1/C3/C4/C5; regression of those four has no failing test
(B6 unmet for L-48), and the phase can be green while the design's own cycle list
is unchanged.

**Smallest fix.** Key the manifest on enola's module nodes (or add sub-package
`CONTRACT`s for `agents.prompt_templates`, `providers.adapters`,
`schemas.registries`, and the `graph` sub-modules), or add a pytest wrapper that
parses enola's `check --fail-on=cycles` output and fails on a non-empty delta.

### O-6 — Major — P11's own step list leaves two profile authorities at the merge commit and CI green; the dual-owner invariant is falsified by the document itself

**Claim attacked** (`04-extraction-roadmap.md:240-242`): "Every phase additionally
passes the **ownership-uniqueness check**: at every intermediate commit, no
concern it touches has two authoritative owners"; and (`:773-774`): "**Ownership
check.** While `_FALLBACK_PROFILES` and the YAML coexist, the phase note names the
authority and the guard asserts equality until the copy is deleted."

**Evidence.**

```bash
$ sed -n '764p' docs/.../04-extraction-roadmap.md
**Deletions.** `_FALLBACK_PROFILES` or the YAML copy (pick `config`); dead
$ sed -n '773,774p' docs/.../04-extraction-roadmap.md
**Ownership check.** While `_FALLBACK_PROFILES` and the YAML coexist, the phase
note names the authority and the guard asserts equality until the copy is deleted.
$ grep -rn '_FALLBACK_PROFILES' src/ --include='*.py'
src/film_pipeline/agents/model_routing/__init__.py:18:_FALLBACK_PROFILES: dict[str, dict[str, object]] = {
src/film_pipeline/agents/model_routing/__init__.py:84:    profiles: ... default_factory=lambda: dict(_FALLBACK_PROFILES))
```

P11's Deletions leave the choice open ("or … (pick `config`)"), and the ownership
check is written for the coexistence state ("until the copy is deleted"). The
phase's own acceptance (`:257`) is `CI@90 %` with "every consumer reports the same
persistence mode" — achievable with both copies present, guarded by equality.

**Why it matters.** This is the exact prohibited end state: at P11's merge, the
YAML and `_FALLBACK_PROFILES` both define model-profile defaults, a guard makes
them agree, and both look authoritative. The document says the reader may leave
it that way. L-24 is claimed retired by P11 (`:147`) while the second owner
survives.

**Smallest fix.** Delete `_FALLBACK_PROFILES` inside P11 and make the guard assert
the deletion (no second copy), not equality between two live copies; move any
residual to a named phase, not an open choice.

### O-7 — Major — P7's merge is green with an 8/6 kind mismatch while the named guard promises agreement: two owners of the kind set

**Claim attacked** (`04-extraction-roadmap.md:253`): P7's guard
"`tests/unit/filmspec/test_artifact_kind_parity.py::test_registry_and_enum_agree`"
and acceptance "8/6 mismatch recorded as cited exemptions"; P7 step (`:613-618`):
"Declare the kind set once in `filmspec`; keep the kind catalog/specs in
`storage` … the mechanical parity guard lands here, the declaration lands in P8."

**Evidence.**

```bash
$ sed -n '104,105p' docs/.../04-extraction-roadmap.md
artifact kinds: 47 registered (canonical) / 45 enum / 39 shared; 8 registry-only (added to filmspec);
$ UV_CACHE_DIR=... uv run --python 3.12 python -c \
  "from film_pipeline.schemas._base import ArtifactType; print(len(list(ArtifactType)))"
45
$ grep -n 'test_artifact_kind_parity' docs/.../04-extraction-roadmap.md
253:...tests/unit/filmspec/test_artifact_kind_parity.py::test_registry_and_enum_agree...
```

At P7 `ArtifactType` (45 members) and `storage`'s registry (47 exact ids) are both
live and disagree by 8 and 6 while the named guard is `…agree`; the mismatch is
"recorded as cited exemptions". The declaration that reconciles them is deferred
to P8.

**Why it matters.** A guard named "agree" that is satisfied by an exemption row
for a live 8/6 divergence is guard theatre for the exact concern (L-18) it claims
to pin, and P7's merge commit has two normative kind lists. B6 requires the test
to fail if ownership regresses; here it is green while the divergence exists.

**Smallest fix.** Either land the declaration in P7 (as `03` D11 ultimately
requires) or rename/scope the guard to a one-directional coverage assertion and
state explicitly that `storage.REGISTRY` is the sole kind authority until P8.

### O-8 — Major — P8 changes how persisted artifacts are read, on the document's own "one unverified caveat", with no corpus test

**Claim attacked** (`04-extraction-roadmap.md:254`): P8 acceptance
"checksum/schema/traversal checks fire on every read entry" and "**B7
(additive):** … stored `artifact_type=script` labels not migrated (03 D11)";
(`:663-665`): "Stored `artifact_type=script` labels are **not migrated** (D11: no
reader keys on them; retained as the program's one unverified caveat)";
(`:673-674`): "Replace the
`script` fallback with a loud refusal"; (`:675-676`): "**Rollback.** One revert. No on-disk
migration is performed, so the property holds".

**Evidence.**

```bash
$ sed -n '683p' src/film_pipeline/artifacts/store.py
    if envelope.checksum and envelope.checksum != payload_checksum(envelope.payload):
$ sed -n '293,299p' src/film_pipeline/artifacts/store.py
    def load_mutable(...):  # uses _read_envelope directly, no schema_version gate
```

P8 step 5 replaces the silent `script` fallback with "a loud refusal" while
admitting the assumption that nothing keys on stored `script` labels is unverified.
The program performs no on-disk migration (consistent with the prior art's
owner decision to ship no migrator), so the only protection is that no existing
storage root exercises the removed fallback — which no test in P8's list does
(P8 Tests are round-trip/corruption/compositor, all on freshly written data).

**Why it matters.** The phase's `make ci-check` green is not evidence that
pre-existing roots still load, so P8 is shippable only "with caveat": a real
deployment may start refusing artifacts whose `artifact_type` is outside the
declared set, and the roadmap calls the assumption unverified in the same row that
claims the read gate is closed.

**Smallest fix.** Add a committed fixture of a v2 storage root written before P8
(including a `script`-typed artifact) and assert the read gate's behavior on it;
if the fixture fails, the label migration becomes its own B7 phase.

### O-9 — Major — "three intentional behaviour changes" is an undercount; P14 and P18 change behaviour silently relative to the stated containment rule

**Claim attacked** (`04-extraction-roadmap.md:220-223`): "**Blast-radius
containment by construction.** A phase may not change a persisted representation.
The program's three intentional behaviour changes are `03` §8's: the W8 ceiling
(P17), the W6 persistence precedence (P11) and the W11 `langgraph.json` path
(P21)."

**Evidence.**

```bash
$ sed -n '855,861p' docs/.../04-extraction-roadmap.md
**Per F-VR-02 ...** the defect is the zero-width `[block_below, review_at)` band in
all 22 explicit literals, so the guard asserts `block_below < review_at` ...
$ sed -n '1014,1015p' docs/.../04-extraction-roadmap.md
**Rollback.** One revert; the shim reverts with it. The divergence fix changes
operator-visible gating intentionally — record it.
$ sed -n '1726p;1732p' docs/.../03-target-architecture.md
| ... MCP `approve_generation_spend` default ceiling ... This is the **only intentional behaviour change** in the program; W8's phase note carries it ...
| Persistence-mode precedence ... **Explicitly broken (behaviour), documented.** ...
```

P14 fixes a zero-width band that today makes every explicitly-thresholded
validator emit `BLOCKED` where it should emit `NEEDS_REVISION` ("baseline: 22/22
have `block_below == review_at`", `:873`); P18 changes "operator-visible gating"
by its own text. Both are behaviour changes not in the list of three. `03` §8 even
says the ceiling is the **only** change while its own table marks persistence
precedence "Explicitly broken (behaviour)".

**Why it matters.** An implementer following §1.8 would treat P14 as a pure
refactor and P18 as internal, and would not produce the B7 documentation the
program requires for a behaviour change — contradicting B7 ("the breaking change
is listed and documented in the phase that ships it").

**Smallest fix.** Make the list authoritative and complete (P11, P14, P17, P18,
P21) in §1.8 and in the P14/P18 acceptance rows.

### O-10 — Major — P20's size is measured too low: two file counts are wrong and the test-migration surface is never counted

**Claim attacked** (`04-extraction-roadmap.md:1055`): "**Files.** `app/services/`
(5 files) → `operations/`; `mcp/tools/**` (46 files)"; (`:1060-1062`): "tests
migrate from monkeypatching the package `get_runtime` to injection"; size (`:1221`)
"**L**".

**Evidence.**

```bash
$ find src/film_pipeline/mcp/tools -type f -not -path '*__pycache__*' | wc -l
39
$ find src/film_pipeline/app/services -type f -not -path '*__pycache__*' | wc -l
7
$ grep -rn 'get_runtime' src/ --include='*.py' | wc -l ; grep -rln 'get_runtime' src/ --include='*.py' | wc -l
158
54
$ grep -rn 'get_runtime' tests/ --include='*.py' | wc -l ; grep -rln 'get_runtime' tests/ --include='*.py' | wc -l
243
41
$ grep -rn '_services' tests/ --include='*.py' | wc -l ; grep -rln '_services' tests/ --include='*.py' | wc -l
83
24
```

The `_services` src number (112 / 43) is exactly right (`:1077`), but the phase
never counts the 41 test files / 243 `get_runtime` references it must convert, nor
the 24 test files / 83 `_services` references. Its own enumerated surface is
understated (39 tool modules, 7 service files). `05` §6 notes monkeypatch
migration is "the human step"; `grep -rln monkeypatch tests/ | wc -l` = 41.

**Why it matters.** `L` is "5+ day-equivalents"; the phase touches ≥93 source
files and ≥41 test files plus the 39 tool handlers, and sits in the tail with P18
and P21 (`:1258-1260`). An `L` estimate here is the plan's critical path error.

**Smallest fix.** Re-measure and restate P20's Files from the commands above;
split the phase by tool group with an explicit per-group test-migration count
(which the Migration steps already permit) and re-label the groups M rather than
one L.

### O-11 — Major — DB-8 has no concrete trigger: half of L-19 is deferred to "a separate feature release" with no phase or authority

**Claim attacked** (`04-extraction-roadmap.md:142`): L-19 is scheduled
"**P12** (W6) — Render half deferred to DB-8"; (`:1176`): "**DB-8** | KB packet
content rendered into prompts | L-19 (render half) | … **feature completion**, not
ownership extraction. | **separate feature release**".

**Evidence.** `04:115-120` claims "**49 concerns are scheduled and 9 deferred**"
and `:1186-1188` "**Why the deferred set is safe.** … each sits downstream of an
authority a scheduled phase creates". DB-8's trigger is not a phase, a wave, or a
named downstream authority; it is "separate feature release". The ledger's L-19
title is "KB packet **construction and delivery to prompts**"
(`02:426`), and P12 keeps "Prompt rendering of packet content remains DB-8"
(`:791`).

**Why it matters.** This is the one deferred item with no concrete trigger — the
review's definition of an unowned concern — and it is excluded from the 9-deferred
count because L-19 is counted among the 49 scheduled. The 58/58 arithmetic is
therefore true only for primary phases.

**Smallest fix.** Either name the phase/authority that unblocks the render half
(e.g. fold it into P12 with a packet-content template test) or move L-19 wholly
into the deferred set with an explicit trigger and correct the 49/9 split.

### O-12 — Major — DB-4 defers provider health/registry behind P18 although nothing in their dependency chain requires governance

**Claim attacked** (`04-extraction-roadmap.md:1172`): "**DB-4** | Provider health,
registry, failure classification | L-09, L-28 (+L-27 classifier half) | … |
after P18"; (`:1188`): "L-09/L-28 need the state model from P5 and the gate from
P18".

**Evidence.** `03` §3 places `providers` at the provider layer and `governance` at
L8; `04:132` assigns L-09 to `providers` (+`orchestration`) and `:151` L-28 to
`providers`. Provider health is a four-representation state problem
(`04:1172`: "the checkpointed one routing reads has **no producer**") whose inputs
are the state model (P5) and `storage` (P8). No provider-health path consumes a
gate verdict; P18's own scope (`:985-1022`) is advancement/gate law and does not
mention providers.

**Why it matters.** A Major Critical concern (L-09 is 4×5=20) is held behind a
phase that cannot change it, with no invariant requiring the gate. That is the
"deferral to avoid hard work" pattern: the trigger is later than the real
dependency, and nothing in the plan forces it after P18 either (DB-4 has no phase
id).

**Smallest fix.** Re-trigger DB-4 on P8 (state + storage) — or name the specific
P18 output it consumes — and give it a phase id so the trigger is a commitment,
not a bucket.

### O-13 — Major — target modules named as phase products are not produced by any earlier phase; one artifact is "created/owned" by two phases

**Claim attacked** (`04-extraction-roadmap.md:246-268`, the "Module created /
owned" column): P11 "`config`; `studio.resolve_persistence()`"; P16
"`orchestration.project_generation_requests`"; P5 "`orchestration` state"; P7
"`filmspec` kind vocabulary; `storage.contract`"; P8 "`storage` +
`storage/contract.py`".

**Evidence.**

```bash
$ grep -n 'studio.resolve_persistence\|orchestration.project_generation_requests' docs/.../04-extraction-roadmap.md
696:...publish a `studio` runtime accessor...      # P9, before studio exists
755:...`studio.resolve_persistence()` is the one truth table...
922:Move the ledger→state projection up into `orchestration.project_generation_requests`...
$ grep -n 'storage/contract' docs/.../04-extraction-roadmap.md
609:...new `src/film_pipeline/storage/contract.py`...   # P7 Files
638:...`storage/contract.py`...                          # P8 Files
$ grep -n 'final module renames' docs/.../04-extraction-roadmap.md
1142:**Steps.** Rename modules to the target catalog; delete shims...
```

P11 depends only on P10 (`:257`) but its stated product is `studio.resolve_persistence()`;
`studio` is first "created / owned" by P21 (`:267`). P11's own Files (`:743-749`)
are `app/_persistence.py`, `graph/graph.py`, `config/*` — i.e. the work happens in
`app`, and the `studio.` prefix is forward-naming. P22 is where "final module
renames to the `03` catalog" happens (`:1142`), so `orchestration`/`studio` do not
exist as module names in P5/P11/P16. Independently, `storage/contract.py` is
listed as created in both P7 and P8, and `filmspec` in P3, P7 and P8.

**Why it matters.** The `Depends on` column is checked in §2.1 ("every phase's
`Depends on` is either an earlier phase … or a lower-numbered wave", `:288-289`),
but the **product** of P11/P16 is a module that the module column assigns to a
later phase. An engineer cannot tell from the plan whether P11 creates
`film_pipeline/studio/` (breaking R-1's "renames staged last") or edits
`app/_persistence.py` under a future name.

**Smallest fix.** Use current module paths in the product column until P22, mark
the target name in parentheses, and list each new file in exactly one phase.

### O-14 — Major — W4's exit condition names two artifact kinds that appear in no phase; P7 has no dependency on the same-wave P6 whose changes move its parity baseline

**Claim attacked** (`04-extraction-roadmap.md:278`): "**W4 — registry agreement
(O4)** … `AgentRegistry(known_output_artifacts=…)` enabled; kinds declared | P6
enables the catalog agreement; P7 declares the kind set; P8 applies `03` D11";
P7 `Depends on` = "P3" (`:253`).

**Evidence.**

```bash
$ sed -n '208p' docs/.../03-target-architecture.md
| **W4 — registry agreement (O4)** | enable `AgentRegistry(known_output_artifacts=…)`; add `CONSENSUS_REPORT`/`COST_ESTIMATE` etc. to the kind vocabulary; declare the 3 media kinds non-storable | `agents`, `storage`, `filmspec` | −6 non-member rows | B wave 4; R1 |
$ grep -n 'CONSENSUS_REPORT\|COST_ESTIMATE' docs/.../04-extraction-roadmap.md
(no output)
```

The wave spine `03` §2.5 W4 (which the roadmap declares authoritative and says
"wins" for wave order, `:22`, `:36`) requires adding `CONSENSUS_REPORT` and
`COST_ESTIMATE` to the kind vocabulary. No P-phase mentions either name. P6
(`agents`) and P7 (`storage`/`filmspec`) are both in W4 and P7 does not depend on
P6, so whichever merges second moves the kind set that the other's parity
exemption count ("8/6", `:253`) was recorded against.

**Why it matters.** The W4 exit condition is claimed satisfied (`:278`) without
the two kinds the spine names, and the recorded 8/6 exemption is a moveable
number that a parallel phase can invalidate — so the "wave exit" is asserted, not
demonstrated.

**Smallest fix.** Assign the two kind additions to a named phase (P6 or P7), make
P7 depend on P6 (or serialize them), and re-derive the mismatch count in P8's
step 4 guard rather than recording it at P7.

### O-15 — Minor — P4's two literal counts disagree with the tree and with `03`

**Claim attacked** (`04-extraction-roadmap.md:487-488`): "48 severity sites
across `graph`, `app`, `mcp`, `cli`, `validation`, `config`; the 19
`_phase_gate_updates(..., gate=...)` literals".

**Evidence.**

```bash
$ for p in graph app mcp cli validation config; do printf '%s ' $p; grep -rn '"blocking"' src/film_pipeline/$p --include='*.py' | wc -l; done
graph 12 / app 4 / mcp 3 / cli 2 / validation 33 / config 3      # sum = 57
$ grep -rn '"blocking"' src/film_pipeline --include='*.py' | wc -l
59
$ grep -rn '_phase_gate_updates' src/ --include='*.py' | wc -l          # 19 calls
$ grep -rn '_phase_gate_updates' src/ --include='*.py' | grep -c 'gate=' # 9 with gate=
$ sed -n '206p' docs/.../03-target-architecture.md
... replace 48 `"blocking"` literals and 9 inline `gate=` literals ...
```

`03` says 9 `gate=` literals (matches the tree); the roadmap's "19" conflates the
call count with the literal count. The severity total is 57 in the six named
packages (59 repo-wide), not 48.

**Why it matters.** These numbers are the phase's burndown target ("48 → 0",
`:510`); a wrong target makes done-rule #1 unverifiable.

**Smallest fix.** Re-derive both counts with the AST sweep `05` §6 step 1 uses and
record the command in §0.3.

### O-16 — Minor — P12's "11 write paths that construct `kb_context_ref=None`" does not match the tree

**Claim attacked** (`04-extraction-roadmap.md:787-788`): "One provenance stamping
point so the 11 write paths that construct `kb_context_ref=None` route through
it."; (`:804-805`): "11 write paths stamp through one function".

**Evidence.**

```bash
$ grep -rn 'kb_context_ref=None' src/ --include='*.py' | wc -l
0
$ grep -rn 'kb_context_ref' src/film_pipeline --include='*.py' | wc -l
24
$ grep -rn 'ArtifactMetadata(' src/film_pipeline --include='*.py' | wc -l
15
```

**Why it matters.** The phase's Step-1 inventory number (the PR's burndown
number, `05` §6) cannot be reproduced from the claim as written; the real set is
the 15 `ArtifactMetadata(...)` constructions that omit the field.

**Smallest fix.** Restate as "the 15 `ArtifactMetadata(...)` constructions that
leave `kb_context_ref` at its `None` default" and give the AST query.

### O-17 — Minor — cross-document arithmetic drift: `03` says the roadmap's phase ids are `P0–P20`, and "9-file guard suite" is 10 files after P0

**Claim attacked** (`03:192` / `03` §2.5): "`04-extraction-roadmap.md` is
authoritative for **phase ids, ordering and per-phase acceptance** (its
`P0`–`P20`)"; and `04:247` "`tests/architecture/`" + "9-file guard suite" vs
`04:343` P0 creating `tests/architecture/test_architecture_manifest.py`.

**Evidence.** Mechanical parse: 23 phase rows (P0…P22). P0 Files (`:343`) adds a
10th file before P1's suite ("9-file", `:383-387`, matching `03:204`).

**Why it matters.** The design document that the roadmap says "wins for wave
order" undercounts the roadmap's phases by two, and the guard-suite size the
roadmap and `05` both state is off by one after P0. A reader reconciling the two
cannot tell whether P21/P22 are sanctioned or out-of-design.

**Smallest fix.** Update `03` §2.5 to `P0–P22` and state that P0's manifest test
is the 10th `tests/architecture/` file.

### O-18 — Minor — the plan contradicts the prior art's recorded shim lesson without acknowledging it

**Claim attacked** (`04-extraction-roadmap.md:224-227`): "Shims are `# SHIM(W<n>)`
and are removed by guard in P22"; against the precedent's own mitigation
(`documentation/storage-upgrade-plan.md` §7): "Blast radius ~45 files → phase
slicing (P2 shim; P3/P4 consumer groups; **shim deletion same phase it's
replaced**)" and its P2/P3 phase text ("the signature tests move/delete with the
shim in P3").

**Evidence.** The roadmap's shim windows: `app/product_gate.py` SHIM(W1) created
P2 (`:447`), deleted P22 (`:1138`); `schemas/_base.py` SHIM(W2) created P3
(`:464`), re-used as SHIM(W5) in P10 (`:726`), deleted P22; `graph/_action_routing`
SHIM(W9) created P18 (`:996`), deleted P22. Every window spans 4–20 phases.

**Why it matters.** `00:14-16` makes the prior art "a source of guard-test
precedent", not the template, so divergence is allowed — but the divergence is
from a recorded lesson, and the roadmap never says why the longer window is safe
(the precedent's stated risk was exactly this).

**Smallest fix.** Add one paragraph in §1.9 arguing why W12-removal is safe
(the shims are re-exports of the same object, guarded by identity canaries) or
move each shim's deletion into the phase that last needs it.

### O-19 — Minor — P3's Deletions omit the C1/C4/C5 `CYCLE_EXEMPTIONS` rows that `05`'s liveness rule makes mandatory

**Claim attacked** (`04-extraction-roadmap.md:472-473`): "**Deletions.** The enum
definitions in `schemas/_base.py`; the duplicated phase class sets; the three
cycle-forming re-export edges."

**Evidence.**

```bash
$ sed -n '1572,1576p' docs/.../05-enforcement-and-guard-tests.md
2. **Subject is live.** Every row's `subject` still exists — a dotted path still
resolves ... an `a -> b` edge is still observed. A **fixed** deviation fails the
ledger until the row is deleted.
$ sed -n '434,435p' docs/.../04-extraction-roadmap.md   # P2 does name its row
`CYCLE_EXEMPTIONS`; the canary that a re-introduced `app → mcp` import fails.
$ sed -n '437,438p' docs/.../04-extraction-roadmap.md
**Deletions.** The temporary top-level file is itself deleted in P21 ...
```

P2 names its ledger row ("the ledger row is deleted now", `:438`); P3 deletes the
C1/C4/C5 source edges but never names their `CYCLE_EXEMPTIONS` rows. `05` §6 step 6
covers this generically, so the phase is executable, but the burndown number P3
must drive to zero is left implicit while P2's is explicit.

**Smallest fix.** Add "and the three `CYCLE_EXEMPTIONS` rows for C1/C4/C5" to
P3's Deletions.

---

## 2. Phase-by-phase shippability

Shippable-alone = could this phase's merge commit be green and revertible in
isolation, per B5, as the document scopes it. "Caveat" = green is achievable but
the stated evidence or a stated dependency does not support the claim.

| Phase | Shippable alone? | The one fact that decides it |
|---|---|---|
| P0 | yes | Inert declaration data; no production module imports `architecture.py` (`:371-372`). |
| P1 | with caveat | `graph`/`mcp` keep `unrestricted_imports=True` (`:391`), and the acyclicity guard sees only C2 (O-5). |
| P2 | with caveat | `app/product_gate.py` becomes a re-export but `Makefile:100` still runs it with `python -m`; the `__main__` behavior is unspecified (O-1). |
| P3 | with caveat | C1/C4/C5 go, but their `CYCLE_EXEMPTIONS` rows are not named (O-19) and P7's kind parity is not yet possible (O-14). |
| P4 | with caveat | "one commit per module" (`:493`) leaves the other modules' literals authoritative at intermediate commits; the guard canary needs `--no-cov` (O-4). |
| P5 | with caveat | Channels are additive (`:544-545`) but no old-checkpoint resume test is in the list; `orchestration` is not yet a module (O-13). |
| P6 | yes | Step 2 deletes `_AGENT_PROFILE_MAP` in the same commit as the descriptor (`:570-574`). |
| P7 | no | Green with an 8/6 kind mismatch and a guard named "agree" (O-7); no dependency on P6 (O-14). |
| P8 | with caveat | Read gate changes behavior on stored data under an explicitly unverified assumption (O-8). |
| P9 | with caveat | Requires a "`studio` runtime accessor" (`:696-697`) although `studio` is created in P21 (O-13). |
| P10 | yes | Import-path-only with a shim; revert is clean (`:734`). |
| P11 | no | Its own ownership check keeps `_FALLBACK_PROFILES` and the YAML both live at merge (O-6). |
| P12 | no | Evidence requires the `meta.json` change its rollback excludes (O-3). |
| P13 | with caveat | MCP `run_validation` "set becomes the union" (`:833`) is a behaviour change not in the list of three (O-9). |
| P14 | with caveat | Fixes the 22/22 zero-width band — a status-visible behaviour change not in the list of three (O-9). |
| P15 | with caveat | "MCP poll records media/manifest (documented)" (`:261`) changes MCP-side side effects; ledger payload preserved. |
| P16 | with caveat | Product named `orchestration.project_generation_requests` before the rename (O-13). |
| P17 | with caveat | The `approve_generation_spend` default change is the one honestly-listed behaviour change (`:263`, `03` §8). |
| P18 | with caveat | Its own text: "changes operator-visible gating intentionally — record it" (`:1014-1015`), missing from §1.8 (O-9). |
| P19 | yes | `resolved_project_id` semantics unchanged; `projects` created below `mcp` (`:1044`). |
| P20 | no | Enumerated surface is wrong (39/7, not 46/5) and 243 `get_runtime` test refs / 41 files are never sized (O-10). |
| P21 | no | Ships the M1-defective graph as the `langgraph.json` entry point (O-2); leaves `pyproject.toml:39` and `Makefile:100` un-updated (O-1). |
| P22 | no | Deleting shims breaks the CI `product-gate` step and the console script; sized S (O-1). |

**Not shippable alone as written: P7, P11, P12, P20, P21, P22** (6 of 23).

---

## 3. Attacks that failed

1. **"Some `L-NN` is never mentioned or has no phase."** Failed. All 58 ids occur
   in the roadmap; the §0.4 primary table (lines 122–182) contains every one, and
   the ledger set is exactly `L-01…L-58` (58 ids). `comm` diff empty both ways.
2. **"The `Depends on` graph is cyclic or has a forward reference."** Failed. The
   parse yields 23 phases, `non-earlier deps: []`, `cycles: []`; every dependency
   is a strictly lower phase. The topological order is the document's own sequence.
3. **"The baseline test count is wrong."** Failed. `pytest --collect-only -q
   --no-cov` sums to **2011** collected = 2003 passed + 8 skipped; `exit 0`, no
   collection errors. The acceptance gate's 2003/8 is internally consistent at
   `fb85baa`.
4. **"`_services` = 112 refs / 43 files is wrong."** Failed. `grep -rn '_services'
   src/ --include='*.py' | wc -l` = 112 and `grep -rln` = 43, exactly as `:1077`
   says.
5. **"P6 leaves `_AGENT_PROFILE_MAP` and the descriptor both authoritative."**
   Failed. P6 step 2 states the delete and the test correction land *in the same
   commit* (`:570-574`); unlike P11, no coexistence is licensed.
6. **"C2 cannot be closed at P2."** Failed. `03` D3 (`:1404-1406`) and `03` §2.5
   W1 both close C2 by moving `product_gate` above `mcp`; `mcp → app` edges
   without an `app → mcp` edge form no cycle.
7. **"The roadmap clones the storage rewrite's shape."** Failed. Prior art is 7
   phases (`documentation/storage-upgrade-plan.md` §6, P1–P7) with
   "implement → 3 reviews → fix → commit"; the roadmap is 23 phases on a 13-wave
   spine with an exemption ledger and a shim budget. Different shape.
8. **"The plan contradicts the prior art by performing an on-disk migration."**
   Failed. P8 performs no migration (`:675`), and the prior art's owner decision
   removed the migrator entirely (plan P6: "the migration tooling was removed
   entirely — old-layout projects are no longer readable"). The stance matches.
9. **"The `langgraph.json` change is silent."** Failed. It is listed as an
   explicit B7 change in P21 (`:1120-1123`) and `03` §8; the objection is timing,
   not concealment (O-2).
10. **"P0 is not inert."** Failed. `architecture.py` is specified as a declared
    leaf that no runtime path imports (`:246`, `:371-372`), consistent with
    `05` §2.1 rule 3.
11. **"The `--cov-fail-under` gate makes `make ci-check` itself impossible."**
    Failed. `test-cov`/`ci-check` run the whole tree and reach 91.58 %; only
    *subset* runs fail by construction (O-4).

---

## 4. Verdict

**On B5 (independently shippable).** Not met as written. Six phases (P7, P11,
P12, P20, P21, P22) cannot ship alone and green on the document's own terms, and
two of those failures fall at the seal (P22 deletes shims that `ci-check`'s
`product-gate` step and `pyproject.toml`'s console script still target), which
means the program's declared end state is red. The dependency graph is genuinely
acyclic and the ordering is real — the failure is not ordering *between* phases
but mis-scoped products inside them: persisted-representation behavior (P8), an
excluded B7 change inside an acceptance criterion (P12), a named module that does
not exist yet (P11/P16), and an un-measured test-migration surface (P20).

**On B6 (guard tests).** Partially met. The guard catalogue is concrete and the
anti-vacuity canary is the strongest part of the plan. But three guards are
vacuous or self-contradictory in the states they are asked to certify: the
acyclicity sweep cannot see C1/C3/C4/C5 (O-5), `test_registry_and_enum_agree` is
green on a live 8/6 mismatch (O-7), and the mandatory red/green demonstration
cannot be run without an undocumented `--no-cov` (O-4, measured 28 %). B6 says a
guard must fail if ownership regresses; for four of five cycles and for the kind
vocabulary it cannot.

**Could an engineer execute this plan as written?** Not to the end. Through P19
the plan is followable with the caveats named above — the phases are detailed,
the evidence commands are mostly reproducible, and the exemption ledger is a
sound ratchet. From P20 the instructions stop matching the tree: the locator
phase never counts the 41 test files that monkeypatch `get_runtime`, P21 points
the declared entry point at a known Critical import-time defect, and P22 deletes
the shims that keep `make ci-check`'s product gate and the installed CLI
resolvable without ever updating `Makefile:100` or `pyproject.toml:39`. An
engineer would discover this at P22, having already performed twenty-two phases
of migration; the smallest fix set (O-1, O-2, O-3, O-6, O-7) is two weeks of
re-scoping, not a rewrite.

**Objection counts.** Blocking **4**, Major **10**, Minor **5** (19 total).

---

## 5. Tree confirmation

```bash
$ git status --porcelain
(empty)
$ git status --short | wc -l
0
```

Only `docs/modular-architecture/reviews/adversarial-roadmap.md` was created. No
file under `src/`, `tests/`, or the repo root was modified; no `git checkout`,
`git clean`, or `git stash` was run; scratch work stayed in `/tmp`
(`/tmp/roadmap_ids.txt`, `/tmp/ledger_ids.txt`, `/tmp/collect.txt`,
`/tmp/collect.err`). `docs/` is gitignored (`.gitignore:2`), so the new file does
not appear in `git status`.

---

# Revision 2 — re-anchored against the frozen 21-phase roadmap

Revision 1 above is historical. This section re-derives every objection from the
frozen text; no objection is carried forward on the strength of its old anchor.

## R2.1 Pins, what changed, and the phase-id remap

**Frozen document under attack.**

```
$ wc -l docs/modular-architecture/04-extraction-roadmap.md
1381 docs/modular-architecture/04-extraction-roadmap.md
$ shasum -a 256 docs/modular-architecture/04-extraction-roadmap.md
4f5a8db14f1d4189414dfba13dd043b7d2c52ed8d8a9b39e509dfdd39e08c47e
$ stat -f '%N mtime=%Sm' -t '%Y-%m-%dT%H:%M:%S' docs/modular-architecture/04-extraction-roadmap.md
docs/modular-architecture/04-extraction-roadmap.md mtime=2026-09-25T15:39:16
$ git rev-parse HEAD
fb85baa0e6b769b709791a96a89980089304bf13
```

Revision 1 reviewed: 1339 lines, sha256 `e12009b3…`, mtime 15:22:09, phases
`P0`–`P22`. Frozen revision: 1381 lines, sha256 `4f5a8db1…`, mtime 15:39:16,
phases `P0`–`P20` (21). Mechanical parse of the frozen phase table: 21 rows;
`Depends on` graph **acyclic**, `non-earlier deps: []`, `cycles: []`; all 58
`L-NN` ids present. `03:192` now pins the same range: "its `P0`–`P20`".

**Old → new phase-id map** (derived from the frozen table, not assumed):

| Revision 1 | Frozen | Change |
|---|---|---|
| P0–P15 | P0–P15 | ids stable |
| P16 projection/cost | **P16** | merged with old P17 |
| P17 `budget` | **P16** | absorbed (`03` D5) |
| P18 `governance` | **P17** | −1 |
| P19 `projects` | **P18** | −1 |
| P20 `operations` | **P19** | −1 |
| P21 `studio` | **P20** (W11 series) | fused |
| P22 seal | **P20** (W12 series) | fused |

Frozen P20 is stated as "executed as two staged commit series, each independently
green — **W11 commits** … then **W12 commits**" (`:1134-1136`).

**Re-measured facts at `fb85baa`** (all re-run in this revision):
`mcp/tools` = 39 files; `app/services` = 7; `get_runtime` in tests = 243 refs / 41
files; `_services` in tests = 83 refs / 24 files; `"blocking"` = 57 in the six
named packages / 59 repo-wide; `_phase_gate_updates` = 19 calls, 9 with `gate=`;
`kb_context_ref=None` = 0 literals, 15 `ArtifactMetadata(` constructions;
`pytest tests/unit/graph/test_channel_registry.py -q` = 28.00 % → exit 1;
`tests/architecture/` and `tests/unit/filmspec/` still absent;
`graph/graph.py:201` = `graph: CompiledStateGraph = build_graph()`;
`Makefile:100` = `python -m film_pipeline.app.product_gate`;
`pyproject.toml:39` = `film-pipeline-run = "film_pipeline.cli.run:main"`;
`langgraph.json:4` = `./src/film_pipeline/graph/graph.py:graph`.

## R2.2 Re-adjudication of the 19 Revision-1 objections

| # | Rev-1 sev | Rev-2 status | Frozen anchor | Deciding fact (re-derived) |
|---|---|---|---|---|
| O-1 | Blocking | **still-blocking** | `:1138-1147`, `:1161-1163`, `:1172-1174`, `:1181-1187` | P20 deletes `app/product_gate.py` and moves `cli/`→`studio`, but `Makefile` appears only at `:372`/`:418`, `pyproject.toml` only at `:1145` (`59,95-98`); `:39` and `Makefile:100` are never updated. |
| O-2 | Blocking | **resolved-by-rewrite** | `:280`, `:792-803`, `:818-819` | P11 now owns verify-10 M1 with guard `test_bare_graph_import_does_not_poison_storage_root.py` and acceptance "no longer creates `<storage root>/checkpoints/`", before P20's path change. |
| O-3 | Blocking | **still-blocking** | `:842`, `:848-850`, `:852-854` | P12 still lists "mutable save→read preserves the ref" and evidence "today `null`" while its rollback excludes the `meta.json` change. |
| O-4 | Blocking | **still-blocking** | `:445-447`, `:1263-1265` | P1 evidence still says "show `pytest tests/architecture` fails"; `grep -n 'no-cov' 04` → none; measured subset run exits 1 at 28.00 %. |
| O-5 | Major | **still-major** | `:414-419`, `:437-438` | `CONTRACTS` still built from the 17 top-level `__init__.py`; C1/C3/C4/C5 remain intra-package and invisible to the Kahn sweep. |
| O-6 | Major | **still-major** | `:810-811`, `:821-822` | P11 deletions still "`_FALLBACK_PROFILES` or the YAML copy (pick `config`)"; ownership check still written for the coexistence state. |
| O-7 | Major | **still-major** | `:276`, `:644-653` | P7 names `test_registry_and_enum_agree` while acceptance still records "8/6 mismatch recorded as cited exemptions". |
| O-8 | Major | **still-major** | `:686-696`, `:706-707` | P8 still removes the `script` fallback and gates every read while calling the label assumption "the program's one unverified caveat"; no pre-P8 corpus fixture in the test list. |
| O-9 | Major | **still-major** | `:243-246`, `:903-905`, `:1058-1059` | §1.8 still says "three intentional behaviour changes"; P14 fixes the 22/22 zero-width band and P17 "changes operator-visible gating intentionally". |
| O-10 | Major | **still-major** | `:1101-1103`, `:1107`, `:1253` | Operations phase is now P19; Files still "(5 files)" and "(46 files)" (measured 7 / 39) and still no test-migration count (243/41 + 83/24); still sized L. |
| O-11 | Major | **still-major** | `:1209`, `:162`, `:839` | DB-8 trigger is still "separate feature release"; L-19 render half still deferred while L-19 is counted scheduled. |
| O-12 | Major | **still-major** | `:1205`, `:1221-1222` | DB-4 trigger moved "after P18"→"after P17" but is still the governance phase; provider health consumes no gate verdict. |
| O-13 | Major | **still-major** | `:280`, `:285`, `:276-277`, `:727-728` | P11 product `studio.resolve_persistence()`, P16 product `orchestration.project_generation_requests`; `studio` first created P20 (`:289`), rename only in P20's W12 series (`:1161`); `storage/contract.py` still "created" by P7 and P8. |
| O-14 | Major | **still-major** | `:302`, `:276` | `grep -n 'CONSENSUS_REPORT\|COST_ESTIMATE' 04` → none, though §2.1 W4 still requires them; P7 still `Depends on` P3 only. |
| O-15 | Minor | **still-minor** | `:300`, `:518-519`, `:541-542` | "48 severity sites" (measured 57 in those packages) and "19 `_phase_gate_updates(..., gate=...)` literals" (measured 19 calls / 9 with `gate=`). |
| O-16 | Minor | **still-minor** | `:835-836`, `:852-853` | "11 write paths that construct `kb_context_ref=None`"; measured 0 such literals / 15 `ArtifactMetadata(` constructions. |
| O-17 | Minor | **resolved on the count half; still-minor on the suite size** | `:5-7`, `:42-43` (resolved); `:371`, `:416-418` (survives) | `03:192` and the roadmap now agree on 21 / `P0`–`P20`; P0 still adds `test_architecture_manifest.py` before P1's self-described "9-file" suite → 10 files. |
| O-18 | Minor | **still-minor** | `:478-479`, `:495`, `:757-758`, `:1040`, `:1145-1147`, `:1174` | Shim windows now end at P20, not P22, but SHIM(W1)/W2/W5/W9 still span 3–18 phases with no rationale vs the prior art's same-phase deletion lesson. |
| O-19 | Minor | **still-minor** | `:503-504` | P3 Deletions still name the three source edges and not the C1/C4/C5 `CYCLE_EXEMPTIONS` rows that `05` §5.3 rule 2 makes mandatory. |

**Resolved-objection detail (O-2).** The parent's raw fact is correct: the
module-level `build_graph()` is real (`graph/graph.py:201`), it is now
`F-CRP-12` in `audit/10-checkpoints-and-runtime-persistence.md:30` ("`F-CRP-12`
(= M1, Critical"), and the frozen roadmap places the fix in **P11**
(`:280` table row; `:792-803`; acceptance `:280` "a bare `import
film_pipeline.graph.graph` no longer creates `<storage root>/checkpoints/`").
P11 (`P10`→`P11`→…→`P20`) precedes the `langgraph.json` change in P20
(`:1176-1178`). Revision 1's premise — that M41's only home was DB-6, triggered
*after* the entry-point change — is **withdrawn**. One residual is recorded as
new O-20 below.

## R2.3 New objections found in the frozen text

### O-20 — Major — P11's M1 fix removes the module-level `graph` object that the still-current `langgraph.json` entry and `03`'s public contract depend on

**Claim attacked** (`04:799-803`): the P11 guard "imports the graph module in a
subprocess against an empty temp root and asserts no directory is created and
that a subsequent app bootstrap succeeds"; (`03:390` M41): "no import-time side
effect: the compiled graph is built by `studio` (L6/D8) *after* roots resolve".

**Evidence.**

```bash
$ sed -n '4p' langgraph.json
    "film_pipeline": "./src/film_pipeline/graph/graph.py:graph"
$ sed -n '201p' src/film_pipeline/graph/graph.py
graph: CompiledStateGraph = build_graph()
$ grep -n 'langgraph.json' docs/.../04-extraction-roadmap.md   # P20 rows only (119,246,289,309,1145,1176)
$ sed -n '829p' docs/.../03-target-architecture.md
- **Public contract.** `graph` (the `langgraph.json` entry), `build_graph`, ...
```

`03` M41's prescribed fix is to stop building the graph at import and build it in
`studio` after roots resolve — i.e. to remove (or lazify) the module-level `graph`
attribute. But `langgraph.json` continues to name
`graph/graph.py:graph` until P20, and `03` §3 lists `graph` as the module's
public contract. P11's Files (`:774-780`) contain no `langgraph.json` and no
`graph/graph.py` change, and P11's text never mentions the entry object.

**Why it matters.** If P11 implements M41 literally, the LangGraph Platform entry
point stops resolving at P11 and stays broken for nine phases, with no phase
documenting the break (B7) and no `ci-check` step that would notice. If P11
instead keeps a module-level `graph` via lazy `__getattr__`, that mechanism is
neither stated nor tested (the stated guard imports the module, which would still
work).

**Smallest fix.** State the P11 mechanism explicitly (lazy module
`__getattr__("graph")` that builds only when LangGraph requests it), add a
`graph/graph.py:graph` import assertion to P11's guard list, and note the residual
entry-path change in P11's B7 line.

### O-21 — Major — P20 fuses two waves and eight concerns into one L phase, so the seal's acceptance cannot be met incrementally

**Claim attacked** (`04:1130-1136`): P20 "spans two waves … executed as two
staged commit series, each independently green"; (`:289`): P20 retires "L-11,
L-12, L-23, L-43 (bootstrap half), L-44, L-52, L-54 (+L-48 closure)"; (`:1254`):
size **L**; (`:1289-1298`): "P17, P19 and P20 are three L phases in a row".

**Evidence.** The frozen P20's own acceptance (`:289`) is the conjunction of the
split's conditions and the seal's: "cycle ledger empty; one `bootstrap(role)`;
graph compiles + resumes; `grep -rn "SHIM(W" src/` → 0; exemption ledger empty".
Its Deletions (`:1172-1174`) delete both the W11 symbols (`entrypoints.py`) and
the W12 symbols (every `# SHIM(W<n>)`). §6 counts P20 as one **L** (5+
day-equivalents, `:1295-1298`) although Revision 1 carried the same work as two
phases (P21 + P22). `03` §2.5 pins `P0`–`P20`, so the folding is mandated; the
phase's granularity is not.

**Why it matters.** B5 is evaluated per phase. A phase whose acceptance requires
the union of a 7-concern split and a whole-tree rename/shim-removal cannot be
partially accepted: the W12 series is the only place `make ci-check` can fail on
the entry points (O-1), and by then the W11 split is already merged. The §7.11
mitigation ("must not land in the same commit", `:1346-1348`) reduces commit
granularity but not acceptance granularity.

**Smallest fix.** Keep one phase id but split §5 into two rows (P20-W11,
P20-W12) with separate size, acceptance and rollback, so the seal is a separately
revertible, separately verifiable deliverable.

### O-22 — Minor — the Critical seam is traceable only by verifier-section name, not by its audit finding id

**Claim attacked** (`04:110`): "the verifier also found a **missed seam M1
(Critical)**"; (`:797-803`): P11 "owns" M1.

**Evidence.**

```bash
$ grep -n 'F-CRP-12' docs/modular-architecture/04-extraction-roadmap.md
(no output)
$ grep -n 'F-CRP-12' docs/modular-architecture/audit/10-checkpoints-and-runtime-persistence.md | head -1
30:- **Missed seams folded in as new findings (verifier §3):** `F-CRP-12` (= M1, Critical
```

`04` §0.1 says the live corpus is measured from `- **Severity:**` bullets in
`audit/*.md`; `F-CRP-12` is one of those findings but the roadmap never cites its
id, so the phase→finding traceability for the program's highest-severity seam is
by a verifier section label that a later audit edit could rename.

**Smallest fix.** Add `F-CRP-12` to §0.1/§0.2 and to P11's guard line.

## R2.4 The parent's raw facts, checked against the frozen roadmap

| Given fact | Handled by the frozen roadmap? | Anchor / measurement |
|---|---|---|
| `pyproject.toml:80` `--cov-fail-under=90`; subset run exits 1 at 28.00 %, `--no-cov` exits 0; `05` uses `--no-cov`, `04` does not | **No** | `grep -n 'no-cov' 04` → none; P1 evidence `:445-447`; done-rule `:1263-1265` (O-4). |
| `Makefile:100` product-gate target; `pyproject.toml:39` console script | **No** | `grep -n 'Makefile' 04` → `:372`, `:418` only; `pyproject.toml` in P20 Files is `:1145` = `59,95-98` (O-1). |
| `graph/graph.py:201` module-level `build_graph()`; import poisoning; now `F-CRP-12` in `audit/10` | **Yes, in P11** | `:280`, `:792-803`, acceptance `:280`; the module-level object and `langgraph.json` remain unreconciled (O-20); the finding id is not cited (O-22). |
| P2 moves `product_gate` above `mcp` via `entrypoints.py` | **Yes** | `:455-463`, shim at `:477-479`. |
| P20 moves `product_gate` into `studio`, updates `langgraph.json`, deletes every `# SHIM(W<n>)` | **Yes** | `:1138-1147`, `:1149-1163`, `:1172-1174`, `:1176-1178`. |
| Which phase lists the console script and the Makefile target as files to update | **None** | Directly answers O-1: no phase does. |

## R2.5 New severity tally and "not shippable alone" list

**Tally: 3 Blocking, 12 Major, 6 Minor (21 scored objections) + 1 resolved
(O-2).**

- Blocking: **O-1** (P20 entry points), **O-3** (P12 evidence vs rollback), **O-4**
  (P1/done-rule canary vs `--cov-fail-under`).
- Major: O-5, O-6, O-7, O-8, O-9, O-10, O-11, O-12, O-13, O-14, **O-20**, **O-21**.
- Minor: O-15, O-16, O-17, O-18, O-19, **O-22**.
- Resolved-by-rewrite: O-2.

**Not shippable alone as written: P7, P11, P12, P19, P20** (5 of 21).
`P19` is the old `P20` (operations/locator; O-10) and `P20` absorbs the old `P21`
+ `P22` failures (O-1, O-21). `P11` remains non-shippable on O-6 (dual profile
owners at merge) and now also carries O-20; `P12` on O-3; `P7` on O-7.

## R2.6 Revision-2 B5/B6 verdict

- **B5 (independently shippable): NOT MET as written.** The frozen plan fixes the
  two things Revision 1 attacked hardest on ordering — M41 now sits in P11 before
  the entry-point change (O-2), and the phase ids now agree with `03` (O-17 half).
  What remains is the same shape at the tail and at P12: a phase whose acceptance
  requires a change it excludes (O-3), a phase whose acceptance is a whole-tree
  seal fused to a split (O-21), and two declared entry points that no phase
  updates (O-1). The dependency graph itself is acyclic and every dependency is a
  strictly earlier phase (verified), so the failure is internal scoping, not
  ordering.
- **B6 (guard tests): PARTIALLY MET.** The revision did not change the three
  guard-level defects: the acyclicity sweep is blind to C1/C3/C4/C5 because the
  manifest is keyed on 17 top-level packages (O-5); `test_registry_and_enum_agree`
  is green on the live 8/6 mismatch it is named after (O-7); and the mandated
  red/green canary still cannot run because `04` does not say `--no-cov` while
  `pyproject.toml:80` fails any subset at 28.00 % (O-4).

## R2.7 Premises withdrawn in this revision

1. **O-2's premise is withdrawn.** Revision 1 asserted that M41's only fix
   location was DB-6 with trigger "after P19 and P21", so P21 shipped the
   defective path. The frozen text places M1 in **P11** with a dedicated guard and
   an acceptance assertion, earlier than P20's `langgraph.json` change. Recorded
   as resolved; the residual entry-object question is now O-20.
2. **O-17's phase-count premise is withdrawn.** Revision 1 asserted `03` pinned
   `P0`–`P20` while the roadmap had 23 phases. The frozen roadmap is 21 phases and
   `03:192` pins the same range. Only the "9-file suite is 10 files" half survives
   (still Minor).
3. **Revision 1's phase ids `P21`/`P22` and all its line anchors are withdrawn as
   citations against the current file.** Every surviving objection above carries a
   frozen-file anchor and, where needed, a reproduce command.

## R2.8 Revision-2 tree confirmation

```bash
$ git status --porcelain
(empty)
$ git status --short | wc -l
0
```

Only `docs/modular-architecture/reviews/adversarial-roadmap.md` was modified in
this revision (Revision 1 content preserved, Revision 2 appended). No file under
`src/`, `tests/`, or the repo root was modified; no `git checkout`, `git clean`,
or `git stash` was run; `make ci-check` was not run; Python ran via
`UV_CACHE_DIR="$PWD/.uv-cache" uv run`; scratch output stayed in `/tmp`.
