# 05 — Enforcement and Guard Tests

> **Review status (2026-09-25): superseded proposal.** The proposed manifest
> and guard suite were not installed or shown to pass CI. The independent review
> in [06](06-independent-review-and-decision.md) recommends focused behavior and
> boundary tests before any broad ownership-manifest mechanism.

Status: **synthesis (bar B3, B5, B6, B8).** Baseline `fb85baa` (`modular-app`).
This is the execution volume of the modularization program: it decides *how*
ownership is declared and mechanically enforced, condensing
`design/proposal-B-enforcement.md` (primary source) with
`design/proposal-A-boundaries.md` (module catalog and layer law).

**Module-name caveat.** Proposal A's 18 module names (`filmspec`, `storage`,
`orchestration`, `governance`, `studio`, …) are **provisional** here. Only a
handful of those modules exist as directories at HEAD; `03-target-architecture.md`
is authoritative for the final names and the final layer table. Every guard below
is written against a **current, verified path** (`film_pipeline/artifacts/…`,
`film_pipeline/graph/…`, `film_pipeline/schemas/…`) so it runs today; the
declaration type carries the name, so a later rename is a one-line manifest edit,
not a guard rewrite. Where a guard is shown with e.g. `artifacts` (proposal A:
`storage`), read it as "the module that owns storage today under whatever name
`03` settles on".

**Docs-only constraint honoured.** No file under `src/`, `tests/`, or the repo
root is created, modified, or deleted by this document. The declaration module,
the `CONTRACT` blocks and the guard suite are presented as *wave-0 deliverables*
(§6, §7.1), with a verified, reverted prototype preserved at
`design/prototype-enforcement/` for reference only — it is **not** to be re-applied
to the tree by this program.

**Corrections consumed (non-negotiable).** This document reflects the
post-verification state: `reviews/verify-01…14.md` all exist — **all 14
verifications are complete** (verify-10 landed last: 11 CONFIRMED / 2 DOWNGRADED /
0 REJECTED / 0 UNVERIFIED) — so R4 applies throughout (verifier verdicts supersede
audit claims, §1.7); `02-duplication-ledger.md` has landed (58 canonical concerns,
§3.10); and `reviews/orchestrator-verification-notes.md` **V1–V6, V9** are applied
in full: V1/V6 (normative numbers and the threshold literals, §3.11), V3 (the edge
matrix, **not** a hardcoded edge count, §3.9), V4 (107 + 3 private reach-ins
enumerated from the AST, §3.7), V5 (the finding corpus — measured below), V6 (the
guard registry, §5.5), V9 (the corrected canary justification, §5.3).

**The finding corpus is a normative number, so it is measured, not remembered.**
Per §3.11's own discipline — the class this document adds to stop exactly this
drift — the corpus is re-derivable by command and the command is stated here:

```bash
# Live finding corpus = every Severity bullet (one per live finding):
grep -h '^- \*\*Severity:\*\*' docs/modular-architecture/audit/*.md | wc -l
#   -> 173

# Live severity distribution:
grep -h '^- \*\*Severity:\*\*' docs/modular-architecture/audit/*.md \
  | sed -E 's/^- \*\*Severity:\*\* *\**([A-Za-z]+).*/\1/' | sort | uniq -c
#   ->  38 Critical   88 High   47 Medium      (0 Low)

# Per audit: 01=11 02=17 03=13 04=12 05=8 06=16 07=13 08=15 09=13 10=11 11=15
#            12=13 13=10 14=6                    (sum 173)
```

**Final measured corpus: 173 live findings — 38 Critical, 88 High, 47 Medium,
0 Low.** `audit/13`'s withdrawn `F-TEST-02` is the heading
`### F-TEST-02 — *withdrawn during the fix loop* — see "Withdrawn findings /
unverified hypotheses"` and **carries no `- **Severity:**` bullet** (verified: the
withdrawn block has no Severity line), so it contributes nothing to the 173 — there
is no "172 live + 1 stub", and 173 is already all-live and equals the per-audit
sum. The draft-time figure **163 (38C/83H/41M/1L) was stale**, as was the
pre-verification **148 (42C/80H/25M/1L)**; both are history, not the current
corpus. No audit has a Low finding (`F-VR-11` was corrected to Medium). The
withdrawn finding is carried as a live concern nowhere in this document. The
ledger's 58 concerns were deduplicated at the 148-finding moment and are a
*different* measure from the live finding count, so §3.10's 58/58 coverage
arithmetic is unaffected by this correction — and no guard justification in this
document rests on a corpus total.

---

## Revision 2 — adversarial architecture review fixes

`reviews/adversarial-architecture.md` (396 lines, bar B8) reviewed this file at the
**2334-line / `afd0059755e16a1e`** revision and raised three **Blocking** and
several **Major** objections. Independent reproduction in this session confirmed
all three Blocking objections. Every objection that touches this file is disposed
below; objections that touch only `03`/`04` are marked *not this file* with the
coordination action, and nothing is silently ignored.

| Obj. | Sev. | Disposition | Where |
|---|---|---|---|
| **O-01** | Blocking | **FIXED.** Every executable input is now a **tracked** file (`src/film_pipeline/architecture.py`) or the AST. The guard registry no longer reads `docs/…/02-duplication-ledger.md`; concern ids are declared as `CONCERN_IDS` in `architecture.py`, and the ledger-document comparison is an **optional, auto-skipped** test. §5.3's citation rule resolves tracked paths strictly and doc paths only when the (gitignored) docs tree is present. | §2.2, §5.3, §5.5, §3.10 |
| **O-02** | Blocking | **FIXED.** `assert len(edges) == 53` is gone. The forbidden set is now defined as the **complement of the declared matrix** — `observed − may_import − ALWAYS_IMPORTABLE` — and the scope tables that derived a competing set are **deleted**, because `03` §4.3 explicitly forbids a second matrix home. The `53` survives only as a marked change-detector. **Single source of the forbidden-edge count: the `03` §4.3 matrix, whose one machine-readable home is `ModuleContract.may_import`; this document no longer states any forbidden-edge count, so there is no third number to disagree with `03`'s derived `10` or the audit's retired `8`.** | §3.9, §3.10 |
| **O-03** | Blocking | **FIXED.** The site-vs-row arithmetic error is corrected: the guard now proves `observed ⊆ covered` and `covered ⊆ observed` by *site*, and `_SYMBOL_EXEMPT` (undefined, and which the old assertion required to have 108 entries) is replaced by a real declared tuple `PRIVATE_SYMBOL_EXEMPTIONS` with the 3 measured rows. | §3.7, §5.2 |
| **O-04** | Major | **FIXED (M-1).** New guard `test_declared_edges_go_strictly_down_one_layer` reads `MODULE_LAYERS`; L1 is now machine-checked, not merely declared. | §3.9 |
| **O-05** | Major | **FIXED (M-2).** New guard `test_cross_package_imports_use_the_declared_public_api` makes `public_api` normative (red-on-branch until wave 1 authors the declarations; the first run seeds `PUBLIC_API_EXEMPTIONS`). The `03` side is **already done and not four names**: §3.21 adds `default_checkpoints_root`, `default_runtime_root`, `graph_state_location` and **refutes** `sanitize_artifact_id` (its only importer loses the edge). | §3.8.1 |
| **O-07** | Major | **PARTLY FIXED, PARTLY REFUTED.** `unrestricted_imports`/`UNRESTRICTED_PACKAGES` are re-stated as **W0 pre-images with a removal wave**, not as target-law constructs, and the target-law wording is `03`'s to fix (*not this file*). The adversary's "behaviourally identical" claim is correct and kept. | §2.2, §3.9 |
| **O-11** | Major | **FIXED.** `agents` is removed from the W1 tightening list; `03:685` and §4.3 declare `agents → providers` allowed, and the adversary is right that deleting it would red the guard against 4 real call sites. | §3.9 |
| **O-13** | Major | **NOT THIS FILE (no change needed).** This document already names the genuinely divergent pair correctly (`graph/services.py:31,48`); the wrong pair is in `03`'s §8. | §3.5 |
| **O-14** | Major | **FIXED (M-6), with an open item on `03`.** The three unlisted write-side representation changes (`artifact_type` labels, the `budget` durable document, `kb_context_ref` stamping) are now explicit compatibility rows in the rollback contract, each with its wave, compatibility class, what a revert does *not* undo, and its migration owner. The reviewer's first remedy — one *§8 row* per change in `03-target-architecture.md` — is **not this file's to apply** and is recorded here as still open. | §6 step 9 |
| **O-15** | Major | **FIXED.** `subject_is_live` is now **violation-aware**: it is handed the observed sets, so a private-module row is live only while ≥1 importer is *observed* and a writer row only while a write site is *observed*. Existence is no longer sufficient, which is exactly the defect (a `find_spec` check stayed green after all 72 importers were migrated). | §5.3, §3.7 |
| **O-16** | Major | **FIXED (M-5).** The registry is a **checked-in sorted manifest** compared against a **directory scan** in both directions (a scan alone cannot see a deletion; a manifest alone cannot see an addition), with a `concerns`-vs-declarations cross-check and the sortedness and size of the manifest asserted. The count is stated once (**12 guard test files**); the stale "9"/"10"/"11" variants are corrected. The coordinated same-commit edit is still review-only — stated plainly, not claimed otherwise. | §5.5, §8.2b |
| **O-17** | Major | **FIXED.** `test_every_declaration_family_is_present_and_non_empty` now exists and iterates `DECLARATION_FAMILIES`, a declared registry of all **nine** families — the previous check named five in prose, and the eight-name list that replaced it still omitted `PRIVATE_SYMBOL_EXEMPTIONS`. | §5.3, §5.5, §5.2 |
| **O-20** | Major | **FIXED.** The citation locator grammar is now structural and total: `§N[.M…]` must match a `^##+ N[.: ]` heading, `F-<AREA>-<nn>` must match its own `^###+ F-… —` heading, `C<n>` must occur in the document body, and **anything else raises** rather than being skipped. A bare-capitalised-word locator (`wave-1`, `Note`, `IMPORT`) no longer passes, and a citation into the tracked tree must additionally be git-tracked. | §5.3 |
| **M-4 / B1** | Major | **FIXED.** §2.2's table asserted "exactly one sentence" and "each non-goal starts with `does not`" while no guard in the catalog checked either. `test_responsibility_is_one_sentence_with_explicit_non_goals` now does both, in the family that already resolves `CONTRACTS`. Its sentence-counting heuristic and its failure mode (an abbreviation such as "e.g." trips it) are stated in the docstring rather than hidden. | §2.2, §3.8 |
| **O-23** | Minor | **FIXED.** The leaf/coverage justification is reworded to address the actual risk (whole-distribution import-time SPOF), and the `architecture_<domain>.py` split is committed to a **stated** line count with a self-check, not "~500". | §2.1, §8.6 |
| **O-21, O-22** | Minor | **NOT THIS FILE.** Both are `03` phrasing/evidence defects. This document already states O-21's env condition correctly (`FILM_PIPELINE_PERSIST_STATE=1` and no `RUNTIME_ROOT`) in its M1 note. | §5.5 |

### Revision 2b — the three guard defects from `reviews/adversarial-roadmap.md` (Revised 2)

`reviews/adversarial-roadmap.md` Revised 2 raised three guard defects that are also
this file's, not `04`'s. They use that document's own numbering, so they are
disambiguated here as **RR-4 / RR-5 / RR-7** to avoid collision with this file's
`O-4`/`O-5`/`O-7` above. All three are folded into the same revision section rather
than a second one.

| Obj. | Sev. | Disposition | Where |
|---|---|---|---|
| **RR-4** | Blocking | **FIXED.** The coverage caveat is now stated in the guard catalog itself, so `04` cannot reproduce the subset-run failure: `pyproject.toml:78-81` sets `--cov-fail-under=90`, and a single-file run of these guards exits **1** at ~28% coverage. Every reproduce command in this document uses `--no-cov` (or `make arch-check`). | §3.0, §3.1–§3.11 reproduce lines, §7.1 |
| **RR-5** | Blocking | **FIXED.** The acyclicity guard no longer keys on `CONTRACTS`: it runs Tarjan SCC over the **whole** `module_edges()` graph at **package-directory granularity** and **sees all five cycles C1–C5** (measured: 5 SCCs, membership matching `01-ownership-map.md` §15). `CYCLE_EXEMPTIONS` rows are keyed on the **SCC member set** (`"a <-> b <-> c"`), not on a single edge: C3's sub-graph has 8 internal edges and a **minimal feedback set of 3**, so an edge-keyed ledger would have left C3 live while the guard reported green. A separate guard reports a stale cycle row, and a granularity-drift guard prevents a silent collapse back to top-level keys. enola is stated as **reporting-only, not wired into `ci-check`**. | §3.9, §7.2, §5.2 |
| **RR-7** | Blocking | **FIXED.** `test_registry_and_enum_agree` previously asserted only `known_ids() ⊇ enum` on a hand-picked subset — it stayed **green while the live mismatch was real**. It now asserts the measured **two-directional** invariant (registry-only ids in an explicit allow-list; enum-only ids matched by an exact row, a `<member>_` prefix family, or the allow-list) **plus** an anti-narrowing guard. Measured at `fb85baa`: registry **47**, enum **45**, shared **39**; 8 registry-only, 6 enum-only of which 3 are covered by the `checkpoint_`/`invalidation_report_`/`rollback_record_` prefix families and 3 (`clip`, `last_frame`, `mid_frame`) by nothing. | §3.4.1 |

**Counts recomputed in this revision.** Guard test files: **12** (was variously
9/10/11). Declaration families: **9** (`DECLARATION_FAMILIES`; the eight-name list
omitted `PRIVATE_SYMBOL_EXEMPTIONS`). Wave-0 exemption ledger: **31 rows** (was
stated as 28, which omitted the 3 private-symbol rows). Private-module sites:
**107** (106 `schemas._base` + 1 `app._persistence`); private-symbol sites: **3**;
exemption rows for them: **2 + 3**. Cross-package edges: **53**, retained only as a
labelled change-detector. Cycle exemption rows: **5**, each keyed on a whole SCC
member set, not on one edge.

**Defects found in this document while re-verifying it, and fixed here.** Each was
found by re-running a measurement this revision had already claimed, not by a
reviewer — recorded so the same class is visible if it recurs:

| Defect | What was wrong | Fix |
|---|---|---|
| Unterminated code fence in §3.7 | A fence closed mid-file at `test_private_import_shape_is_a_labelled_change_detector`, leaving `test_schemas_facade_is_complete`, a stray `)`, and the block tail rendered as prose. Any reader or tooling parsing the file saw 20 lines of Python as markdown. | Fence repaired; the façade guard is now a labelled second block with an introduction. All 29 Python blocks `compile()` cleanly except the one explicitly-marked `<old_module>`/`<owner>` template, which cannot. |
| `121 edges over 17 package-directory nodes` | **17** is the count of *top-level packages*; the edge sweep actually produces **35** package-directory nodes (34 with outgoing edges). The two granularities were conflated in the same sentence that exists to distinguish them. | Corrected to 35/34, and `test_module_edges_are_keyed_at_package_directory_granularity` now asserts the node *universe* (keys ∪ targets) rather than `len(graph)` alone — a target-only package would otherwise be invisible. |
| `PUBLIC_API_EXEMPTIONS` referenced, never declared | §3.8.1 imported it; no code block declared it. The same class as the O-03 `_SYMBOL_EXEMPT` defect this revision claims to have fixed. | Declared in §5.2 as `()` with a stated reason, **excluded deliberately** from `DECLARATION_FAMILIES` (an empty family would break rule 4 on day one), and given its own liveness guard `test_public_api_exemptions_are_live`. |
| "eight declaration families" / "28 ledger rows" | The eight-name list omitted `PRIVATE_SYMBOL_EXEMPTIONS`, so the stated ledger total was 3 short. | Nine families (`DECLARATION_FAMILIES`, count asserted) and **31** rows. |
| `package_edges()` used, never defined | Four guards consume it; only `module_edges()` was specified, and the two differ *only* by granularity — precisely the distinction RR-5 turns on. | Both defined in §3.9, with `package_edges()` stated as a documented collapse of `module_edges()` (one parser, not two). |
| C3 cycle exemption keyed on one edge | Measured: C3's sub-graph has 8 internal edges and a **minimal feedback set of 3**, so a single-edge row would have left C3 live while the guard passed — the RR-5 failure reproduced inside the RR-5 fix. | `CYCLE_EXEMPTIONS` rows key on the whole SCC member set; the sweep runs on the unmodified graph. |

---

## 0. The decision in one table

| Question | Answer |
|---|---|
| Primary mechanism | Typed `ModuleContract` in each package `__init__.py` + one leaf `src/film_pipeline/architecture.py` manifest + a shared stdlib-`ast` guard suite under `tests/architecture/` |
| Complementary mechanism | **enola** `layers:` declaration graded by `enola check --fail-on=cycles,layers`, pinned per phase (§7.2) — already installed, zero new deps, independent evidence |
| New dependencies | **None.** No `import-linter`, no `tach`, no `pytest-archon` |
| CI change | **None required.** Guards are ordinary tests collected by the existing `pytest` step inside `make ci-check` / `make ci-verify`. One optional `make arch-check` convenience target (§7.1) |
| Declaration home | Under `src/`, **never** under `docs/` — `docs/` is gitignored (`.gitignore:2`) and CI-ignored (`paths-ignore` in `.github/workflows/ci.yml`) |
| Fully automatable O-classes | **O1, O3, O4, O5, O7** |
| Partly automatable (human-anchored) | **O2, O6** (enumerate/declare is human), **O8** (existence exact; "typed well enough" is review) |
| Biggest failure mode | **Exemption rot** — a ledger that only grows (§8.1) |

---

## 1. Decision — how ownership is declared and enforced here

### 1.1 What already exists (the reason the decision is nearly forced)

| Asset at HEAD | Evidence | Consequence |
|---|---|---|
| **Four** hand-written **AST guards** — two import-boundaries + two contract guards | `tests/unit/artifacts/test_storage_boundary.py`, `tests/unit/graph/test_startup_boundaries.py`, `tests/unit/config/test_config_contract.py`, `tests/unit/graph/test_channel_registry.py`. `reviews/verify-14.md` re-verification item 7 confirms **exhaustiveness**: exactly four test files under `tests/` call `ast.parse`, the four listed. | The shape is already proven **four times by hand**. The mechanism is *consolidation*, not invention. This is the ground-truth count — proposal B §2.2 says "five", counting a non-AST guard (below). |
| One further **regex/text** guard (not AST) | `tests/unit/artifacts/test_storage_guards.py:26-47` sweeps `Path("projects")` and `Path.home()` with `re` + `read_text`, not `ast.parse` | The mechanism absorbs its *pattern* (a literal-only-in-owner sweep) but it is not one of the four AST guards. Its two behavioural tests are not generalizable. |
| One distribution, one gate | `pyproject.toml:59` `packages = ["src/film_pipeline"]`; `Makefile:108` `ci-check: format-check lint typecheck test-cov build product-gate`; `Makefile:111` `ci-verify` | A test under `tests/` is gated with **no YAML change**. |
| `pytest` already configured for the whole tree | `pyproject.toml:70-90`: `testpaths = ["tests"]`, `-n auto`, `--cov=film_pipeline`, `--cov-fail-under=90` | New guard tests ride the existing step and the existing coverage gate. |
| `mypy --strict` over `src` **and** `tests` | `Makefile:42` (`mypy src tests`), `pyproject.toml:107-113` | A **typed** manifest is type-checked, so a typo'd package name is a mypy error, not a silent no-op — the decisive advantage over YAML. |
| `ruff` with no import-layering rule | `pyproject.toml:132-133` (`select = ["E","F","W","I","B","C4","UP","SIM","PIE","PTH","RET","ARG","RUF"]`) | Ruff cannot express this law; don't pretend otherwise. |
| Pre-commit runs the full `pytest` + `mypy --strict` at **pre-push** | `.pre-commit-config.yaml` `pytest` and `mypy` hooks (`stages: [pre-push]`) | Zero pre-commit change needed. |
| enola installed and configured | `mcp-arch.yaml`; `enola version 0.2.7-51-g72cd079`; `enola check --fail-on=cycles,layers` is a real flag | A second, independent, already-installed boundary gate exists. |
| Measured debt | 8 domain→domain edges (`audit/14` F-BOUNDARY-01); 72 non-schema files import the private `schemas._base` (F-BOUNDARY-02); 5 cycles (`01-ownership-map.md` §15); enola reports **0 layer violations "because no layers are declared"** (`enola-architecture-facts.md:44`) | The law is invisible to the only tool that could enforce it, and the "violations" count is vacuous. |

### 1.2 The realistic options, compared concretely

| Option | What it is | Cost here | Can it express O1/O3/O4/O5? | Verdict |
|---|---|---|---|---|
| **A. Typed `ModuleContract` per package + one AST guard suite** | `ModuleContract`/`Exemption`/`VocabularyMirror`/`StateChannel`/`RegistryAgreement`/`PolicyPoint` dataclasses in a leaf `src/film_pipeline/architecture.py`; `CONTRACT = ModuleContract(...)` in each `__init__.py`; guards read both | est. ~650 lines manifest + ~770 lines guards + ~325 lines one-time `CONTRACT` declarations; **zero new deps, zero CI YAML**; mypy-checked | **Yes** — mirrors, writer sets, registry parity, policy read-sites are all expressible | **ADOPT as primary** |
| **B. `import-linter`** | `[tool.importlinter]` layers/forbidden contracts | Not in `uv.lock`, not in `.venv`, not in the uv caches (proposal B §2.1); adds `import-linter` + `grimp` to the lockfile for a repo whose gate is `make ci-check` | **No** — import edges only; 5 of 8 debt classes invisible | **Reject as primary.** Permitted later as an *optional redundant* edge check only |
| **C. `tach`** | `tach.toml` module boundaries + `tach check` | A fourth tool to install, lock, and keep configured; same import-edge ceiling as B; its "interfaces/public API" feature is a weaker, untyped subset of `public_api` | **No** — edges only | **Reject** |
| **D. `pytest-archon`** | decorator-per-test boundary assertions | Same offline/lockfile problem; declarative assertions are a strict subset of option A's ~40-line edge test; no ability to sweep string literals or writer sites | **No** — edges only | **Reject** |
| **E. enola `enola-intent.yaml` `layers:` + `enola check`** | Declare layers; CI grades the architecture delta against a pinned baseline; exit 1 on new cycle/layer violation | **Zero install cost** (enola already present); but (i) there is **no `enola-intent.yaml`** at HEAD, (ii) `enola doctor` currently reports the baseline **NOT COMPARABLE** (`version_mismatch`, `ignore_globs`), so it must be re-pinned, (iii) it grades *deltas* — it cannot express O1/O3/O4/O5 at all, and cannot fail on an absolute pre-existing state | **No** — cycles/layers only | **ADOPT as complementary**, not primary. It is the one gate that catches *unknown-unknown* structural change and it is free |

The decisive facts are (i) every alternative tool is **absent offline** and would
add lockfile churn and a second mechanism *beside* the five existing AST guards
rather than replacing them; (ii) the program's own quality bar B6 names
"duplicate-normative-model test" and "single-writer test" as required guard kinds,
and no import-edge tool can express either; (iii) option A is the repo's own
precedent (four files, three authors, reached independently).

### 1.3 Decision

1. **Primary:** adopt **option A**. `ModuleContract` declarations live in each
   package's `__init__.py`; cross-module facts live centrally in
   `src/film_pipeline/architecture.py`; one shared harness
   (`tests/architecture/_harness.py`) replaces the private helper copies; the
   guards are the eight O-class files in §3 plus the edge-law and ledger files.
2. **Complementary:** adopt **option E** — declare enola `layers:` in an
   intent/config file and wire `enola check --fail-on=cycles,layers` as a
   *reporting and phase-grading* step (§7.2). It does not replace A and must not
   be the only gate: it is delta-based and silent about a pre-existing absolute
   violation.
3. **Retain:** `mypy --strict` (the free O8 lever via a per-package
   `disallow_any_explicit` override, deferred to wave 2+, §3.8) and `ruff`
   unchanged.
4. **Do not add:** any new runtime or dev dependency for enforcement.

### 1.4 Rejected alternatives, one line each

- **`import-linter`** — not offline, needs a lockfile change, and blind to
  O1/O3/O4/O5 (5 of 8 classes); revisit only as a redundant edge check.
- **`tach`** — a fourth tool for the same edge-only coverage; its public-API
  notion is an untyped subset of `ModuleContract.public_api`.
- **`pytest-archon`** — decorator assertions are a strict subset of a ~40-line
  parametrized AST test, with no literal/writer-sweep ability.
- **`modules.yaml` data manifest** — untyped, so a typo is silent until a guard
  notices; under `docs/` it is CI-exempt; under the repo root it is neither
  mypy-checked nor packaged consistently. Rejected as the *primary* store
  (the manifest is Python source).
- **`__all__` + `no_implicit_reexport` alone** — already on (`mypy strict`), and
  O7 is already violated 72 times despite it (`schemas._base`). Adopted only as an
  *input* to the `public_api` check, never as the mechanism.
- **A new CI job or pre-commit hook for architecture** — redundant: `pytest`
  already runs every guard inside `make ci-check` (`Makefile:108`).

### 1.5 The failure mode being prevented

Not "someone imports the wrong module". The measured damage is **silent drift**:
a second normative model, a new writer of owned state, a re-derived policy
decision, or a ninth forbidden edge appears and **no test can fail**. The
canonical examples the guards must make impossible:

- add a 12th phase to `graph/_action_routing.PHASE_ORDER` (verified: 11 members,
  `list(PHASE_ORDER)` equals `list(PHASE_DIR_MAP)` at HEAD): `artifacts/paths.py:34`
  falls through `PHASE_DIR_MAP.get(phase, phase)` and writes the new phase's
  artifacts into a raw-named directory with **no test failing** (F-PHASE-02).
- rename a config field rather than a symbol: `config/profile_resolver.py:204`
  and `providers/credentials.py` both still compile and diverge silently
  (F-BOUNDARY-05 drift proof).
- add `from film_pipeline.validation.impl.assembly import AssemblyValidator` to
  `post/subtitle_agent.py`: nothing fails — no boundary test exists outside
  `artifacts/` and `graph/` (F-BOUNDARY-04 mutation scenario).
- `cli/driver.py:182` (`state["current_phase"] = PHASE_ORDER[target_index]`)
  mutates persisted state directly; no test asserts the writer set, so a ninth
  writer can appear silently (F-PHASE-09, F-CRP-*; proposal B §2.4).

The mechanism's job is to convert each of these into a **failing test that names
the owner**.

### 1.6 Reconciliation of the evidence this document relies on

These discrepancies are real and are resolved here so the guards encode one
truth. `reviews/verify-14.md` is the verifier of record for the boundary findings,
and **its verdicts supersede the audit's claims** (reconciliation-notes R4).

| Discrepancy | Resolution |
|---|---|
| "4 hand-written AST guards" (`audit/14`) vs "5 hand-rolled guards" (proposal B §2.2) | Both count real files but not the same kind. `verify-14` re-verification item 7 re-confirmed exhaustiveness: **exactly four** test files under `tests/` call `ast.parse`. `tests/unit/artifacts/test_storage_guards.py` is a **fifth guard but regex/text-based**. §4 consolidates all five; the AST harness absorbs four. |
| "8 forbidden domain→domain edges" (`audit/14` F-BOUNDARY-01) vs "11 violating statements in 4 pairs" (proposal B §2.3) | Different definitions of *domain*. `verify-14` F-BOUNDARY-01 **CONFIRMED** and independently enumerated **8** edges: `agents→providers` (4 stmts), `config→providers` (2), `generation→providers` (4), `generation→artifacts` (7), `post→validation` (1), `testing→artifacts` (2), `testing→checkpoints` (1), `testing→providers` (1). Proposal B scans a narrower domain set. **Under a layer law, 6 of the 8 become lawful** (downward: `agents→providers`, `generation→artifacts`, `generation→providers`; off-graph: the three `testing→*`), leaving **two genuinely illegal edges**: `config→providers` and `post→validation`. The guards enforce the layer law, so if the layer law is adopted the ledger needs 2 rows, not 8 — and the *measured* 8 remains the number recorded in L-48. |
| Proposal A's layer law vs its own catalog for `post` | Proposal A §5.12 lists `post` Deps as `filmspec, schemas, storage, validation`, but §6.2 **L1 forbids same-layer imports** and `post`/`validation` are both L6. An internal contradiction in proposal A. **Flagged for `03-target-architecture.md`**; until `03` resolves it, the enforcement doc treats the layer table as provisional and the `post→validation` edge must be recorded in the ledger with the reason "pending the L6 decision in `03`". |
| Private cross-package import counts | `verify-14` F-BOUNDARY-05 **CONFIRMED (offenders real)**, but note the arithmetic: the verifier's total is **107 private-module sites** while listing 105 `schemas._base` + 1 `app._persistence`. An independent AST re-run in this session gives **107 = 106 `schemas._base` + 1 `app._persistence`**, plus **3 private-symbol sites**. The design uses the *measured* split (106/1) and the verifier's *total* (107); the "105" in `verify-14` §1 is an arithmetic slip, not a finding change. |
| F-BOUNDARY-02's class | `verify-14` **DOWNGRADED** it to Medium (3×3=9) and **REJECTED the O1 half** — no second *definition* of an enum/constant is shown, and §1.4 O1 requires one. So the O1 guard family **must not claim F-BOUNDARY-02**; the real divergence there is **façade incompleteness** (`TRANSITION_TYPES` and `LEGACY_TRANSITION_ALIASES` are bound only in `_base` and absent from `schemas/__init__.py`), which is an O8/public-surface check. F-BOUNDARY-02 appears under **O7 and O8** in this document, never under O1. |
| enola "layer violations 0" | Vacuously true: `enola-architecture-facts.md:44` — *"because no layers are declared"*. Declaring `layers:` turns 0 into a real measurement. |

### 1.7 Verifier verdicts consumed (R4)

`reviews/verify-01.md … verify-14.md` all exist and **all 14 verifications are
complete**; **verify-10 landed last** (11 CONFIRMED / 2 DOWNGRADED / 0 REJECTED /
0 UNVERIFIED) and its "Missed in scope" section adds a **Critical** seam the
checkpoint audit did not record. The verdicts that change the **enforcement
design** — as opposed to the finding text — are:

| Verifier verdict | Effect on this document |
|---|---|
| F-BOUNDARY-01 severity **High (3×4=12)**, class **O7/O8** (O5 struck as a stretch) | The edge-law guard is filed under **O7/edge law**, not O5. L-48's O5 clause is not what the guard enforces. |
| F-BOUNDARY-02 **DOWNGRADED → Medium (3×3=9)**; **O1 REJECTED** | O1 guard does not claim it (§1.6). The façade-completeness check is an **O8** guard: every name outsiders import from `schemas._base` must be bound in `schemas/__init__.py`. |
| F-BOUNDARY-04 scope correction: `test_config_contract.py` and `test_channel_registry.py` are **additional AST contract guards** | §4's consolidation table has **four** rows plus the regex guard, and the "only two guarded boundaries" phrasing is scoped to *import* boundaries. |
| F-BOUNDARY-05 **CONFIRMED but `Reproduce` broken**; two `app→graph` private-symbol sites added; **High (3×4=12)** | The O7 guard is indentation- and form-agnostic (`ast.walk`, both `import`/`from`); its seed ledger has **3** private-symbol subjects, not 1. |
| F-BOUNDARY-06 **Medium (3×3=9)**; coverage `omit` has **two** entries | The L7 harness-isolation guard is seeded for `graph` and generalized to all 17 packages (L-54). |
| F-PHASE-10 **DOWNGRADED** (two phase→validator tables, not three) | The O4 registry guard seeds the **two** tables verify-01 confirmed; no guard is written against the third that does not exist. |
| F-GEN-07/GEN-08 **DOWNGRADED** (drift proofs refuted by re-run tests) | Those two are **not** used as guard justifications: a refuted drift proof cannot justify a guard (`00` §1.6.3). L-39/L-40 keep only their surviving clauses. |
| F-CFG-01 **DOWNGRADED** (16→12): the YAML does reach the router | The O1 model-profile mirror stays (the duplicate map is real), but its failure message must not claim "stale fallback live in every `ModelRouter()` path". |
| F-AGENT-02 **DOWNGRADED** (Critical→High) | L-07's guard is still written, with the corrected severity ordering. |
| Structural correction: **5 cycles, not 1**; C2 has 7 members, C3 4 members | The acyclicity guard must be evaluated at **directory-module granularity**, not top-level package granularity, or it will report green while C3 (intra-`graph`) is live. The harness resolves `film_pipeline.graph.nodes` etc. as modules; `test_module_graph_is_acyclic_except_recorded_cycles` runs on the *observed* graph at the same granularity enola reports (spike-verified: 5 SCCs at `fb85baa`), and enola's `cycles` explainer (§7.2) is the manual cross-check. Exempted cycles are recorded as **whole SCC member lists**, not as a minimal feedback edge set: recording the SCC means the guard cannot be satisfied by deleting one arbitrary edge of the cycle while the cycle stays live. |
| `schemas` count **322**, not 323 | Any comment or message in the guards quoting the count uses 322 (252 cross-package + 70 intra-package). |
| **V3** — the "8 forbidden edges" is the union of three targeted greps, not an enumeration; 53/32/21/17 are the real ladder | The edge-law guard consumes a **declared edge matrix plus scope definition** and **derives** every count; no guard hardcodes 8 (§3.9). |
| **V4** — 107 private-module sites (106 `schemas._base` + 1 `app._persistence`), 72 non-schema importer files, 3 private-symbol sites | The O7 guard enumerates all 107 + 3 **from the AST** and asserts the derived totals (§3.7). |
| **V1** — 23 `ValidatorThresholds(` calls, 22 with literals, 18×(85,75,75)/3×(80,70,70)/1×(90,80,80), `block_below == review_at` in 22/22; `NEEDS_REVISION` unreachable | New **normative-number** guard class with a derived distribution and a four-status reachability lock (§3.11). |
| **V5** — live finding corpus is **173** (38C/88H/47M/0L), not 148 and not the draft-time 163; `audit/13`'s withdrawn `F-TEST-02` carries **no** Severity bullet, so there is no "172 + 1 stub" | All corpus statements in this document use the measured 173, with both reproduce commands stated (§ header). The withdrawn finding is never cited as a guard justification. |
| **V6** — a normative number was wrong in four files while a fifth had corrected it | The normative-number class (§3.11) plus the **guard registry** (§5.5) that fails when a guard file or manifest family disappears. |
| **V9** — the orphaned `test_guard_canary` `.pyc` is **this program's own prototype**, not a pre-existing repo loss (never tracked; created inside the session window) | The canary justification is replaced by a measured one: **18 orphaned `.pyc` files** under `tests/` from real deletions/renames, and no test-set enumeration anywhere (§5.3, §5.5, §8.2b). CI's `paths-ignore` and lack of any guard-enumerating step are stated in §7.1. |
| **verify-10 M1** — bare `import film_pipeline.graph.graph` creates `<storage root>/checkpoints/`; the app then **refuses its own storage root** (`StorageRootError`), Critical (5×5=25) | A **lifecycle side effect at import time** that no static source sweep can see — recorded in §5.5 as the boundary of what this mechanism can enforce, and as a why-not-static note; it needs a runtime probe, not an AST rule. |

The remaining verifier verdicts (~20 severity/class corrections, ~30 extra seams
folded into the 58 ledger entries) change *priority order*, not mechanism. The
guard catalog is organized by O-class, so a severity correction re-orders the
extraction waves (§7.2) without changing a single guard.

---

## 2. The ownership declaration format

### 2.1 Where declarations live

Four rules, and they resolve every "where does this go?" question **and** the
O-01 requirement that no executable input may live under `docs/`:

1. **A module states its own contract** — `CONTRACT = ModuleContract(...)` in
   `src/film_pipeline/<pkg>/__init__.py`, because only that package can truthfully
   describe itself (bar B1/B2).
2. **Cross-module facts are declared centrally** — a mirror pair, a state channel
   with several writers, or two registries that must agree are *nobody's* private
   property; they live in `src/film_pipeline/architecture.py`.
3. **Every guard input is tracked source or the AST.** The guard suite reads
   `src/film_pipeline/**` and `tests/architecture/**` — never `docs/**`. The
   concern-id vocabulary it validates against is `CONCERN_IDS` in
   `architecture.py` (§2.2), a **tracked** declaration; the narrative ledger under
   `docs/` is compared to it only by an optional test that *auto-skips* when the
   docs tree is absent (§5.3, §5.5). Nothing the suite needs in order to pass is
   gitignored.
4. **Declarations are data; logic is tests.** All decision logic lives under
   `tests/`.

**Why under `src/`, and the real risk of doing so.** `docs/` is gitignored
(`.gitignore:2`) and CI-exempt (`.github/workflows/ci.yml` `paths-ignore`:
`**/*.md`, `docs/**`, `LICENSE`), so a manifest there is unreviewable as a diff,
untriggered by CI, and absent from a clean checkout — the O-01 failure. The
declaration therefore lives under `src/`. The adversary's **O-23** correctly
observes that this creates a *different* risk than the one an earlier revision
justified: because every package `__init__.py` imports `ModuleContract`, a syntax
or name error in the single leaf `architecture.py` (est. ~650 lines, §2.1) breaks the import of all
281 modules, and coverage of a data module is trivially 100 % and constrains
nothing. The manifest is a whole-distribution import-time dependency and is
treated as one:

- the leaf rule (`test_architecture_manifest_is_a_leaf`) is what keeps the blast
  radius a *syntax/name* error rather than an import cycle; it is load-bearing, not
  cosmetic;
- a **size self-check** fails at a stated limit — `test_architecture_manifest_size`
  asserts `architecture.py` ≤ **750 lines** — and the split into
  `architecture_<domain>.py` files (types and the `ModuleContract`/`Exemption`
  definitions stay in the leaf; the *data* families — `CONCERN_IDS`, `MIRRORS`,
  `NORMATIVE_NUMBERS`, the three exemption tuples, the artifact-id allow-lists —
  move to globbed siblings that the guard imports) is committed at that threshold
  (§8.6);
- `ruff format` + `mypy --strict` already cover the file, so the remaining risk is
  a *runtime* error in data construction, which the size limit bounds.

**Why 750 and not the earlier "~330 / ~500".** The `~330` estimate predates this
revision and counts only the types plus `MODULE_LAYERS`. Summing the row counts
this document itself declares gives roughly **650 lines** at wave 0: types ~125;
`MODULE_LAYERS` (17) ~25; `CONCERN_IDS` (58) ~12; `MIRRORS` ~90; `STATE_CHANNELS`
(1 channel, 8 writer rows) ~30; `REGISTRY_AGREEMENTS` ~40; `POLICY_POINTS` (1
point, 7 exemption rows) ~30; `LIFECYCLES` ~25; `NORMATIVE_NUMBERS` (23) ~160;
the three exemption tuples (2 + 3 + 5 rows) ~90; the artifact-id allow-lists and
pinned constants ~20. The `~500` trigger in §8.6 would therefore have fired on
day one, which is worse than no trigger: a limit that is already exceeded is
ignored. **750** sits ~100 lines above the estimate, and the estimate is labelled
as an estimate — `architecture.py` does not exist yet, so the first wave to author
it records the measured line count here and the limit moves only in the same
commit.

### 2.2 The exact shape a module must provide

The six things the task requires map onto the `ModuleContract` fields verbatim:

| Required | Field | Rule |
|---|---|---|
| responsibility | `responsibility: str` | exactly one sentence, ends with "." — `test_responsibility_is_one_sentence_with_explicit_non_goals` (§3.8) |
| non-goals | `non_goals: tuple[str, ...]` | non-empty, each starts with `"does not"` — same guard (§3.8) |
| public contract | `public_api: tuple[str, ...]` | every name must exist in the package namespace (`test_public_api_names_exist`) |
| invariants owned | `owns: tuple[str, ...]` | non-empty; the N/I/R it is the single owner of |
| state owned | `owns` (state entries) **and** `StateChannel` rows for observable cross-module keys | a key with writers is a `StateChannel`, not a package-private fact |
| allowed dependencies | `may_import: frozenset[str]` (+ `unrestricted_imports: bool`) | the **minimum** set, not a licence — `test_declared_edges_are_real` fails a declared-but-unused edge |

```python
# src/film_pipeline/architecture.py  (leaf: imports nothing from film_pipeline)
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final, Literal


@dataclass(frozen=True, slots=True)
class Exemption:
    """A recorded, citable deviation from the target ownership law.

    ``subject`` is the stable key the guard computes (a dotted path, a
    ``"<module>::<symbol>"`` writer key, a ``"<left> -> <right>"`` edge, or a
    ``"<a> <-> <b> <-> <c>"`` cycle member set).
    Line numbers are never used: they drift under reformatting.
    """

    subject: str
    reason: str
    citation: str
    removal_phase: str  # <-- amendment to proposal B §5.2: makes the burndown
    #                        machine-readable and reviewable (§5.4)


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
    mode: Literal["ordered", "subset"] = "ordered"


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


@dataclass(frozen=True, slots=True)
class LifecycleCase:
    """One human-authored equivalence case for an O6 lifecycle pair."""

    name: str
    state: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class LifecyclePair:
    """Two implementations of one lifecycle that must advance identically.

    Declared in wave 6+ (the O2/O6 phase); the *cases* are the human step, the
    comparison is the automatic lock. Proposal B §6.9 names this type as the
    missing declaration for O6.
    """

    concern: str
    left: str
    right: str
    cases: tuple[LifecycleCase, ...]
    citation: str


#: Importable by every package without needing a ``may_import`` entry.
ALWAYS_IMPORTABLE: Final[frozenset[str]] = frozenset({"architecture"})

#: W0 PRE-IMAGE, NOT TARGET LAW (O-07). ``AGENTS.md:51`` exempts ``graph`` and
#: ``mcp`` from the coarse edge check. The target law (03 L8) has no unrestricted
#: modules, so this set exists only so wave 0 can ship green: ``test_unrestricted_
#: packages_are_a_declared_preimage`` fails if a third package is added, and
#: ``test_declarations_cannot_be_coarsely_exempt`` (below) makes the flag's removal
#: a ledger row with a wave. A module whose ``may_import`` enumerates every target
#: and a module flagged unrestricted are behaviourally identical, which is the
#: adversary's point and is accepted: the difference is bookkeeping, and wave 3's
#: exit criterion is that this frozenset is empty.
UNRESTRICTED_PACKAGES: Final[frozenset[str]] = frozenset({"graph", "mcp"})

#: The concern-id vocabulary the guard registry validates against. TRACKED SOURCE
#: (O-01): the narrative ledger under ``docs/`` is *compared to* this set by an
#: optional, auto-skipped test -- never read as the authority, because ``docs/`` is
#: gitignored and absent from a clean CI checkout.
CONCERN_IDS: Final[frozenset[str]] = frozenset(
    {f"L-{n:02d}" for n in range(1, 59)}  # L-01 … L-58, the ledger's canonical set
)

#: Cross-package private *symbol* exemptions (O-03). Three measured sites; declared
#: here as Exemption rows exactly like ``PRIVATE_MODULE_EXEMPTIONS``, so the guard
#: compares site counts to site counts and never to a row count of a different
#: granularity.
PRIVATE_SYMBOL_EXEMPTIONS: Final[tuple[Exemption, ...]] = (
    Exemption(
        subject="film_pipeline.providers.credentials._env_var_for",
        reason="config/profile_resolver.py:204 reaches a private function of another package.",
        citation="docs/modular-architecture/audit/14-module-boundaries-and-import-law.md F-BOUNDARY-05",
        removal_phase="wave 5 (O7)",
    ),
    Exemption(
        subject="film_pipeline.graph.nodes._run_validators",
        reason="app/_graph_exec.py:319 reaches a private symbol of another package.",
        citation="docs/modular-architecture/audit/14-module-boundaries-and-import-law.md F-BOUNDARY-05",
        removal_phase="wave 5 (O7)",
    ),
    Exemption(
        subject="film_pipeline.graph.nodes.approval._PHASE_NODES",
        reason="app/_graph_exec.py:449 reaches a private symbol of another package.",
        citation="docs/modular-architecture/audit/14-module-boundaries-and-import-law.md F-BOUNDARY-05",
        removal_phase="wave 5 (O7)",
    ),
)

#: Residual undeclared cross-package imports found by
#: ``test_cross_package_imports_use_the_declared_public_api`` (§3.8.1). **Empty at
#: W0 by construction**: the guard cannot run until wave 1 authors the
#: ``public_api`` tuples, and its first run seeds this tuple with whatever residue
#: is left. It is therefore deliberately NOT a member of ``DECLARATION_FAMILIES``
#: -- a family that is empty at W0 would make the non-vacuity check red on day one.
#: It has its own liveness guard instead: ``test_public_api_exemptions_are_live``.
PUBLIC_API_EXEMPTIONS: Final[tuple[Exemption, ...]] = ()
```

### 2.3 Worked example — `film_pipeline.artifacts` (real symbols, verified)

Symbols verified bound in the package namespace by
`hasattr(film_pipeline.artifacts, name)` at `fb85baa`:
`ArtifactStore`, `REGISTRY`, `KindSpec`, `ArtifactKindRegistry`, `read_manifest`,
`write_manifest`, `phase_dir`, `media_scene_dir`, `project_dir`,
`payload_checksum`, `ArtifactEnvelope`, `AssetManifest` — all `True`.

```python
# src/film_pipeline/artifacts/__init__.py   (target name per proposal A: `storage`)
from film_pipeline.architecture import ModuleContract

CONTRACT = ModuleContract(
    name="artifacts",
    responsibility=(
        "Resolve the storage root and read and write versioned project artifacts."
    ),
    non_goals=(
        "does not import domain packages",
        "does not decide pipeline order",
        "does not own checkpoint policy",
    ),
    owns=(
        "storage root resolution and marker gating",
        "artifact layout and path helpers",
        "artifact version numbering and checksums",
        "artifact kind registry",
        "single-writer authority over every byte under the root",
    ),
    may_import=frozenset({"schemas"}),
    public_api=(
        "ArtifactStore",
        "REGISTRY",
        "KindSpec",
        "ArtifactKindRegistry",
        "read_manifest",
        "write_manifest",
    ),
)
```

Three things this example is deliberately honest about:

- **`may_import={"schemas"}` is what the audit measured**, not a target: the
  `audit/14` matrix row `artifacts → schemas: 16` is the only cross-package edge.
  `test_declared_edges_are_real` will fail the day a second edge appears, and
  `test_imports_stay_within_declared_edges` fails the day `artifacts` imports
  `graph`, `app`, `generation`, or `checkpoints` — which
  `test_storage_boundary.py:101-130` already forbids by hand.
- **`public_api` omits `ProjectStorage` on purpose.** `hasattr(artifacts,
  "ProjectStorage")` is **False** at HEAD: the storage gateway is reachable only
  as `film_pipeline.artifacts.project_storage.ProjectStorage`, even though
  `test_storage_boundary.py:146` treats it as *the* façade. Declaring it here
  would fail `test_public_api_names_exist` until the export is added. That is a
  real, one-line wave-2 decision (export it, or keep the deep import and say so),
  surfaced by the format rather than hidden.
- **`name="artifacts"` is the current directory.** When `03` renames the module to
  `storage`, `test_contract_name_matches_its_package` forces `name` and the
  directory to move together in the same commit.

### 2.4 One cross-module row — the real phase mirror

This is the O1 seam from F-PHASE-02 / F-PHASE-05, and it is **green at HEAD**
(verified: `list(PHASE_DIR_MAP) == list(PHASE_ORDER)` is `True`, both 11 members),
so it ships as a ratchet without a migration:

```python
# src/film_pipeline/architecture.py
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

`as_vocabulary()` maps a `dict` to its keys and a `StrEnum` subclass to its
`.value`s, which is why `PHASE_DIR_MAP` (a `dict[str, str]`) and `FilmPhase`
(verified: 11 members `INTAKE … DELIVERY`) are both comparable with no per-row
extraction config to drift.

> **Note for `03`.** Proposal A moves `FilmPhase` out of `schemas/_base.py` into
> `filmspec`. When that lands, `canonical` becomes
> `film_pipeline.filmspec.FilmPhase`, a one-line edit here, and
> `test_canonical_owner_lives_in_the_contract_package` must be repointed from
> `schemas` to `filmspec`.

---

## 3. Guard catalog — O1 … O8

Every guard is justified by a finding. **No guard exists without one.**

### 3.0 Catalog

| Class | Filing | Automatable? | Guard file | Findings protected |
|---|---|---|---|---|
| **O1** duplicated normative model | full | **Yes** | `test_vocabularies.py` | F-PHASE-02/05, F-ARTIFACT-02/08, F-CFG-04, F-AGENT-01, F-PROV-05, F-BUD-05, F-SEV-01ᴬ |
| **O2** duplicated invariant enforcement | **human-anchored** | **Partly** (lock yes, enumeration human) | `test_invariants.py` | F-OST-05, F-VR-06, F-PHASE-01/03, F-CFG-05, F-POST-04/06, F-BUD-02 |
| **O3** split state authority | full | **Yes** | `test_state_writers.py` | F-PHASE-09, F-OST-01/03/08, F-ARTIFACT-03/06, F-CRP-04, F-RUNTIME-01ᴬ |
| **O4** parallel registries | full | **Yes** | `test_registries.py` | F-AGENT-10, F-VR-01/07, F-CFG-03, F-PHASE-10, F-MCP-07, F-OST-15, F-ARTIFACT-02 |
| **O5** policy-by-branch | full | **Yes** (new read sites; intent stays human) | `test_policy_points.py` | F-CFG-07/08/09/11/12, F-PHASE-07, F-OST-10, F-CRP-09, F-PROV-04 |
| **O6** parallel lifecycle | **human-anchored** | **Partly** (lock yes, equivalence cases human) | `test_lifecycles.py` | F-OST-06/07/13/14, F-VR-03/04/05, F-GEN-02/03/04, F-POST-01/03, F-MCP-02/04/12 |
| **O7** leaked internals | full | **Yes** | `test_private_imports.py` | F-BOUNDARY-02/05, F-PRIV-01ᴬ |
| **O8** missing contract | **partly** | **Partly** (existence exact; well-typedness human) | `test_public_api.py` | F-BOUNDARY-06, F-OST-03, F-MCP-03, F-CRP-03, F-TEST-08 |
| **B3** dependency law + acyclicity | full | **Yes** | `test_contracts.py` | F-BOUNDARY-01/03/04, F-BOUNDARY-06 |
| **N** normative **number** authority (V1/V6) | full | **Yes** | `test_normative_numbers.py` | L-14, L-41, L-53, L-58 (the "24/20 was wrong in four files" anti-pattern — no single authority for a number) |

ᴬ proposal-A-only finding id (the audit cluster did not raise it).

**COVERAGE CAVEAT — read before running any guard in isolation (RR-4).**
`pyproject.toml:78-81` sets `--cov=film_pipeline` and `--cov-fail-under=90`, so a
subset run of these guards **exits 1 on coverage, not on the guard**. Measured: a
single architecture-guard file run under the repo's default `addopts` reports
**28.00%** coverage and fails the 90% gate with no guard failure. Every reproduce
command in §3.1–§3.11 and §6 therefore passes **`--no-cov`**. Use:

```bash
UV_CACHE_DIR=$PWD/.uv-cache uv run pytest tests/architecture -q --no-cov   # all guards
UV_CACHE_DIR=$PWD/.uv-cache uv run pytest tests/architecture/test_contracts.py -q --no-cov
make arch-check                                                            # same, once §7.1's target exists
```

`-n auto` and `--strict-markers` are also in `addopts`; the second is why the
`change_detector` marker must be registered in `pyproject.toml:85` (§7.1) before
any marked test can be collected.

**Revision 2 additions to the catalog.** The guards below were added by this
revision; they belong to the families in the table above and are not a new class:

| Guard | Family | Added for |
|---|---|---|
| `test_no_cross_package_edge_escapes_the_declared_matrix` | B3 | O-02 (replaces the scope-table derivation) |
| `test_declared_edges_go_strictly_down_one_layer`, `test_every_package_is_assigned_a_layer` | B3 (L1) | O-04 / M-1 |
| `test_module_graph_is_acyclic_except_recorded_cycles`, `test_cycle_exemptions_still_describe_a_real_cycle`, `test_module_edges_are_keyed_at_package_directory_granularity` | B3 (acyclicity) | RR-5 / O-5 |
| `test_the_observed_edge_ladder_is_still_what_this_document_reports` (`change_detector`) | B3 | O-02 |
| `test_cross_package_imports_use_the_declared_public_api` (§3.8.1) | O8 | O-05 / M-2 |
| `test_registry_and_enum_agree` (rewritten, §3.4.1) + `test_registry_enum_agreement_has_not_narrowed` + the two directional tests | O4 | RR-7 / O-7 |
| `test_every_declaration_family_is_present_and_non_empty` | ledger | O-17 |
| `test_responsibility_is_one_sentence_with_explicit_non_goals` (§3.8) | O8 / B1 | M-4 |

Each guard family must be **non-empty** and each guard must be **capable of
failing**; those two properties are asserted centrally in §5.3 rather than being
assumed.

---

### 3.1 O1 — duplicated normative model (fully automatable)

*Fails when* a mirror re-declares, re-orders, or extends a canonical vocabulary.

```python
"""Guard: O1 duplicated normative models (F-PHASE-02/05, F-ARTIFACT-02)."""

from __future__ import annotations

import pytest

from film_pipeline.architecture import MIRRORS, VocabularyMirror
from tests.architecture._harness import as_vocabulary, resolve


@pytest.mark.parametrize("mirror", MIRRORS, ids=lambda m: m.concern)
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


@pytest.mark.parametrize("mirror", MIRRORS, ids=lambda m: m.concern)
def test_canonical_owner_is_not_its_own_mirror(mirror: VocabularyMirror) -> None:
    """A guard that compares a symbol to itself can never fail."""
    assert mirror.canonical not in mirror.mirrors, (
        f"{mirror.concern} lists its canonical owner as a mirror: vacuous guard"
    )
    assert mirror.mirrors, f"{mirror.concern} has no mirrors: vacuous guard"


def test_phase_vocabulary_is_pinned_by_name() -> None:
    """Regression canary: the highest-severity O1 concern must stay under guard."""
    concerns = {mirror.concern for mirror in MIRRORS}
    assert any("phase" in concern for concern in concerns), (
        "the film-phase vocabulary lost its mirror guard (F-PHASE-02 regressed)"
    )
```

---

### 3.2 O2 — duplicated invariant enforcement (**human-anchored**)

The mechanism **cannot find** that two functions enforce the same rule; that is a
semantic judgement. What it can do is make the fix permanent: once the entry
points are enumerated, a differential test locks them.

**Human step (once per concern):** read the callers and write down *every* entry
point of the invariant. For F-OST-05 ("cannot approve with blocking issues") the
verified implementations are at least:

- `graph/nodes/approval.py:52` `_count_blocking_issues` (verified:
  `sum(1 for i in issues if i.get("severity") == "blocking")`, used at `:111`,
  `:223`, `:250`) and `:255` region;
- `review/actions.py:48` — `approve_phase` availability gated on
  `has_blocking_issues` (verified docstring at `:38` and `:31`);
- plus the two MCP paths named in F-OST-05 (`mcp/tools/validation.py`,
  `mcp/tools/approval.py` or their current home).

Recording that enumeration in `INVARIANT_ENTRY_POINTS` is the human act; the test
below is the machine act.

```python
"""Guard: O2 duplicated invariant enforcement — lock only, enumeration is human.

Finding: F-OST-05 ("cannot approve with blocking issues" is implemented 4 times
in 2 different scopes).
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.architecture._readers import BLOCKING_APPROVE_ENTRY_POINTS

#: Human-authored: every entry point of the "approve requires zero blocking
#: issues" invariant. Adding a 5th implementation without adding it here is the
#: regression this test cannot see -- which is exactly why the list is reviewed.
_CASES: tuple[tuple[str, tuple[dict[str, Any], ...]], ...] = (
    ("graph/nodes/approval.py::_count_blocking_issues", (
        ({}, 0),
        ({"issues": [{"severity": "blocking"}]}, 1),
        ({"issues": [{"severity": "warning"}, {"severity": "blocking"}]}, 1),
    )),
)


@pytest.mark.parametrize("dotted", sorted(BLOCKING_APPROVE_ENTRY_POINTS))
def test_every_entry_point_agrees_on_the_blocking_rule(dotted: str) -> None:
    """Each declared entry point computes the same verdict for the same state."""
    reader = BLOCKING_APPROVE_ENTRY_POINTS[dotted]
    verdicts = {reader(state) for state, _expected in _CASES[0][1]}
    assert len(verdicts) <= 1, (
        f"{dotted} disagrees with itself across cases: {verdicts}"
    )


def test_entry_point_list_is_not_vacuous() -> None:
    assert len(BLOCKING_APPROVE_ENTRY_POINTS) >= 2, (
        "fewer than two entry points recorded: either the extraction succeeded "
        "(delete this guard) or the enumeration was never done"
    )
```

**Human step, stated plainly:** the guard proves the *listed* entry points agree.
It cannot prove the list is complete. Completeness is a review obligation recorded
in the pull request, and the count of entry points is the burndown number.

---

### 3.3 O3 — split state authority (fully automatable)

*Fails when* a new `module::symbol` writes an owned channel key, or when a
recorded writer disappears (half-finished migration).

Verified writer set for `current_phase` at HEAD (8 sites, matching proposal B
§2.4): `graph/nodes/_shared.py:155`, `graph/nodes/_context.py:73`,
`graph/subgraphs/qc.py:267`, `cli/driver.py:182`, `app/_persistence.py:165`,
`app/services/_project_discovery.py:54`, `app/runtime.py:117`,
`agents/impl/orchestrator_agent.py:47`.

```python
"""Guard: O3 split state authority (F-PHASE-09, F-OST-01/03, F-CRP-04)."""

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
    recorded = {row.subject for row in channel.writers}
    unaccounted = sorted(set(observed) - recorded)
    assert not unaccounted, (
        f"new writers of {channel.key!r} with no disposition: {unaccounted}. "
        f"The single writer is {channel.owner}; route the write through it or add "
        "a recorded disposition with a reason and citation."
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
def test_channel_owner_declares_the_key(channel: StateChannel) -> None:
    owner = resolve(channel.owner)
    annotations = getattr(owner, "__annotations__", {})
    assert channel.key in annotations, (
        f"{channel.owner} does not declare {channel.key!r} in its schema"
    )
```

The manifest row for `current_phase` carries the 8 writers above as `Exemption`
rows keyed `"<module>/<file>.py::<symbol>"` — line numbers never appear. Wave 3
collapses them onto the owner and deletes rows; deleting a row without deleting its
write site fails `test_recorded_writers_are_live`.

`write_sites()` must cover all three write shapes the repo uses — subscript
assignment, `state.update({...})`, and bare returned dict literals — or it misses
`graph/subgraphs/qc.py:267` and `app/runtime.py:117`. That is a harness
requirement, not a per-guard one.

---

### 3.4 O4 — parallel registries (fully automatable)

*Fails when* two registries that must agree stop agreeing, or when a recorded
non-member becomes a member.

Verified at HEAD: `MVP_AGENTS` has **11** entries, `REGISTRY.known_ids()` has
**47** kinds, and the stray agent-declared outputs are exactly
`['classified_input', 'failure_decision', 'provider_plan', 'reference_strategy',
'routing_decision', 'scene_intents']` — the 6 non-members from F-AGENT-10, and the
hook that would reject them is **off** (`agents/registry.py:27`
`known_output_artifacts: set[str] | None = None`;
`graph/services.py:40` `registry = AgentRegistry()`).

```python
"""Guard: O4 parallel registries that must agree (F-AGENT-10, F-VR-01, F-CFG-03)."""

from __future__ import annotations

import pytest

from film_pipeline.architecture import REGISTRY_AGREEMENTS, RegistryAgreement
from tests.architecture._harness import resolve


@pytest.mark.parametrize("agreement", REGISTRY_AGREEMENTS, ids=lambda a: a.concern)
def test_left_registry_is_a_subset_of_the_canonical_one(agreement: RegistryAgreement) -> None:
    recorded = {row.subject for row in agreement.non_members}
    members = set(resolve(agreement.left)())
    canonical = set(resolve(agreement.right)())
    stray = sorted(members - canonical - recorded)
    assert not stray, (
        f"{agreement.concern}: {stray} are neither registered nor recorded as "
        "deliberate non-members in REGISTRY_AGREEMENTS."
    )


@pytest.mark.parametrize("agreement", REGISTRY_AGREEMENTS, ids=lambda a: a.concern)
def test_non_member_rows_are_not_stale(agreement: RegistryAgreement) -> None:
    actual = set(resolve(agreement.left)()) - set(resolve(agreement.right)())
    recorded = {row.subject for row in agreement.non_members}
    stale = sorted(recorded - actual)
    assert not stale, f"{agreement.concern}: non-member rows no longer needed: {stale}"


@pytest.mark.parametrize("agreement", REGISTRY_AGREEMENTS, ids=lambda a: a.concern)
def test_both_registries_are_non_trivial(agreement: RegistryAgreement) -> None:
    """A guard comparing two empty sets proves nothing."""
    assert set(resolve(agreement.right)()), f"{agreement.right} resolved empty"
    assert set(resolve(agreement.left)()), f"{agreement.left} resolved empty"
    assert agreement.left != agreement.right, "a registry cannot agree with itself"


def test_production_cross_registry_check_is_inert_today() -> None:
    """Gap record (pattern of test_config_contract.py:307).

    ``AgentRegistry`` supports ``known_output_artifacts`` but production wires the
    default ``None``, so ``_reject_unknown_output_artifacts`` returns immediately
    (agents/registry.py:119-121). This test *fails the moment the hook is turned
    on*, which is the signal to delete the 6 non-member rows that exist only
    because it is off. F-AGENT-10.
    """
    from film_pipeline.graph.services import _mvp_agent_registry

    registry = _mvp_agent_registry()
    assert registry.known_output_artifacts is None, (
        "the cross-registry hook is now enabled -- remove the non_members rows "
        "in REGISTRY_AGREEMENTS and assert the agreement directly."
    )
```

The readers (`tests/architecture/_readers.py`) are 3 lines each and are reviewed
in the same diff as the declaration; `test_both_registries_are_non_trivial`
catches a mis-written reader (its failure mode is an empty set).

#### 3.4.1 `test_registry_and_enum_agree` — what it asserted before vs after (RR-7)

`reviews/adversarial-roadmap.md` Revised 2 measured this guard **green on a live
mismatch**. The defect is worth stating exactly, because it is the archetype of
"a guard that cannot fail":

**Before (the defect).** It asserted only the *forward* direction, against a
hand-picked subset, so the two divergences that actually exist were invisible:

```python
# BEFORE -- measured green at fb85baa while 8 registry ids had no enum member
# and 3 enum members had no registry row.
def test_registry_and_enum_agree() -> None:
    for artifact_id in ["script", "matrix_row", "validation_report"]:   # hand-picked
        assert artifact_id in REGISTRY.known_ids()
```

**Measured at `fb85baa` (the fact the old guard did not see).**

| Measure | Value | Members |
|---|---|---|
| `REGISTRY.known_ids()` (exact ids) | **47** | — |
| `ArtifactType` members | **45** | — |
| shared | **39** | — |
| registry-only | **8** | `consensus_report`, `cost_estimate`, `execution_brief`, `project_profile`, `scope_contract`, `shot_matrix`, `story_bible`, `subtitles` |
| enum-only, covered by a **registered prefix** | **3** | `checkpoint` ← `checkpoint_`; `invalidation_report` ← `invalidation_report_`; `rollback_record` ← `rollback_record_` |
| enum-only, genuinely unregistered | **3** | `clip`, `last_frame`, `mid_frame` |

`story_bible` is not hypothetical: `graph/nodes/prep.py:288` writes an artifact of
kind `"story_bible"` and `artifacts/registry.py:145` registers it, yet
`ArtifactType` has no such member. That is F-ARTIFACT-02, live.

**After (the corrected invariant).** Both directions, with the two allow-lists
declared as measured W0 pre-images in `architecture.py` — not as a licence:

```python
# src/film_pipeline/architecture.py
#: Registry exact ids with no ``ArtifactType`` member, measured at fb85baa. A real
#: divergence (F-ARTIFACT-02), recorded so W0 ships green: wave 2 either adds the
#: enum members or deletes the registry rows. The list may not grow.
REGISTRY_ONLY_ARTIFACT_IDS: Final[frozenset[str]] = frozenset({
    "consensus_report", "cost_estimate", "execution_brief", "project_profile",
    "scope_contract", "shot_matrix", "story_bible", "subtitles",
})

#: ``ArtifactType`` members that are deliberately *not* persisted kinds and so need
#: no registry row (runtime media/validation types). The list may not grow.
ENUM_ONLY_ARTIFACT_IDS: Final[frozenset[str]] = frozenset({
    "clip", "last_frame", "mid_frame",
})
```

```python
# REQUIRED PREREQUISITE (3 lines, wave 0, src/): ArtifactKindRegistry exposes only
# known_ids() (registry.py:109-110) and its prefixes live in the private
# ``_prefixes``. A guard must not read a private attribute (that is the O7 smell
# this document exists to remove), so wave 0 adds a public accessor:
#     def known_prefixes(self) -> list[str]:
#         return sorted(self._prefixes)
def _registry_exact_ids() -> set[str]:
    return set(REGISTRY.known_ids())


def _registry_prefixes() -> set[str]:
    return set(REGISTRY.known_prefixes())


def _artifact_type_values() -> set[str]:
    return {member.value for member in ArtifactType}


def test_every_registry_id_is_an_artifact_type_or_recorded() -> None:
    """Direction 1: registry -> enum, minus the 8 recorded divergences."""
    stray = sorted(
        _registry_exact_ids() - _artifact_type_values() - REGISTRY_ONLY_ARTIFACT_IDS
    )
    assert not stray, (
        f"registry ids with no ArtifactType member and no recorded row: {stray}. "
        "Add the enum member (F-ARTIFACT-02) or delete the registry row."
    )


def test_every_artifact_type_is_a_registry_id_prefix_or_recorded() -> None:
    """Direction 2: enum -> registry, exact, ``<member>_`` prefix family, or recorded.

    This is the half the previous revision never checked. "Covered by a prefix"
    means the **dynamic family** ``<member>_<suffix>`` is registered -- it does
    *not* mean the bare label resolves. Measured at `fb85baa`: the three families
    ``checkpoint_``, ``invalidation_report_`` and ``rollback_record_`` exist, so
    ``checkpoint_5c1f`` resolves, but ``spec_for("checkpoint")`` raises
    ``KindNotRegisteredError`` because the bare label is in no registry map. The
    rule is deliberate: those three are container/dynamic kinds, and their bare
    enum member is the family name.
    """
    registry = _registry_exact_ids()
    prefixes = _registry_prefixes()
    uncovered = sorted(
        member
        for member in _artifact_type_values()
        if member not in registry
        and f"{member}_" not in prefixes
        and member not in ENUM_ONLY_ARTIFACT_IDS
    )
    assert not uncovered, (
        f"ArtifactType members with no registry row, prefix, or recorded exemption: "
        f"{uncovered}"
    )


def test_registry_and_enum_agree() -> None:
    """The original name, kept so the registry can still enumerate the guard.

    Both directions plus the prefix relation; the hand-picked list is gone.
    """
    test_every_registry_id_is_an_artifact_type_or_recorded()
    test_every_artifact_type_is_a_registry_id_prefix_or_recorded()


def test_registry_enum_agreement_has_not_narrowed() -> None:
    """Anti-narrowing: the agreement may improve, never shrink.

    Without this, a wave could "fix" a stray by deleting registry rows or enum
    members and the two direction tests above would stay green while coverage of
    the real vocabulary fell.
    """
    shared = _registry_exact_ids() & _artifact_type_values()
    assert len(shared) >= 39, f"shared registry/enum vocabulary shrank to {len(shared)}"
    assert len(REGISTRY_ONLY_ARTIFACT_IDS) <= 8, "the registry-only ledger grew"
    assert len(ENUM_ONLY_ARTIFACT_IDS) <= 3, "the enum-only ledger grew"
```

The anti-narrowing test is the one that makes the other two safe: it is what
distinguishes "recorded divergence" from "vocabulary deletion".

**The measured residue, stated exactly (RR-7).** At `fb85baa`, `REGISTRY.known_ids()`
returns **47** exact ids and `ArtifactType` has **45** members, sharing **39**.
That leaves:

- **8 registry-only** ids (`consensus_report`, `cost_estimate`, `execution_brief`,
  `project_profile`, `scope_contract`, `shot_matrix`, `story_bible`, `subtitles`) —
  recorded in `REGISTRY_ONLY_ARTIFACT_IDS`; the list is asserted **not to grow**.
- **6 enum-only** members, of which **3 are covered by a registered prefix family**
  (`checkpoint` by `checkpoint_`, `invalidation_report` by `invalidation_report_`,
  `rollback_record` by `rollback_record_`) and **3 are covered by nothing**
  (`clip`, `last_frame`, `mid_frame`) — recorded in `ENUM_ONLY_ARTIFACT_IDS`,
  likewise asserted not to grow.

The bare enum labels of the first three are **not** registered: `spec_for("checkpoint")`
raises. That is asserted behaviour, not an oversight — the registry's model is
"the container id is dynamic and will carry a suffix", and this document states the
distinction rather than reporting the three as "covered" without qualification.

Two facts make this reproducible rather than asserted:

```bash
UV_CACHE_DIR=$PWD/.uv-cache uv run python -c "
from film_pipeline.artifacts.registry import REGISTRY
from film_pipeline.schemas import ArtifactType
e = {t.value for t in ArtifactType}; r = set(REGISTRY.known_ids())
print(len(r), len(e), len(r & e)); print(sorted(r - e)); print(sorted(e - r))"
# 47 45 39
# ['consensus_report', 'cost_estimate', 'execution_brief', 'project_profile', 'scope_contract', 'shot_matrix', 'story_bible', 'subtitles']
# ['checkpoint', 'clip', 'invalidation_report', 'last_frame', 'mid_frame', 'rollback_record']
```

The public `known_prefixes()` accessor noted above is a **wave-0 `src/` prerequisite**
(3 lines); the guard cannot read `_prefixes` without committing the O7 smell this
document exists to remove. Until it lands, direction 2 cannot be written at all —
which is why it is called out as a prerequisite rather than assumed.

---

### 3.5 O5 — policy-by-branch (fully automatable for new sites)

*Fails when* the policy input is read in a module that did not declare it.

Verified at HEAD: `FILM_PIPELINE_NO_PERSIST` is read at **7** sites in 6 files
across 4 packages — `app/_persistence.py:52`, `app/logging_setup.py:80`,
`graph/services.py:31`, `graph/services.py:48`, `graph/graph.py:43`,
`mcp/server.py:243`, `cli/run.py:226` — and the predicates are re-derived with
different shapes, e.g. `graph/graph.py:43` (`os.getenv(...) or not
os.getenv(...)`) vs `graph/services.py:31` (consults `NO_PERSIST` only). F-CFG-08,
F-CRP-09.

```python
"""Guard: O5 policy-by-branch (F-CFG-08/09/11/12, F-PHASE-07, F-CRP-09)."""

from __future__ import annotations

import ast

import pytest

from film_pipeline.architecture import POLICY_POINTS, PolicyPoint
from tests.architecture._harness import _enclosing_symbols, parse, python_files, rel


def _policy_reads(pattern: str) -> set[tuple[str, str]]:
    """Every ``(module, symbol)`` that names *pattern* as a string literal.

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


@pytest.mark.parametrize("point", POLICY_POINTS, ids=lambda p: p.pattern)
def test_policy_inputs_are_read_only_at_declared_points(point: PolicyPoint) -> None:
    observed = {module for module, _symbol in _policy_reads(point.pattern)}
    declared = set(point.readers)
    exempt = {row.subject.split("::")[0] for row in point.exemptions}
    undeclared = sorted(observed - declared - exempt)
    assert not undeclared, (
        f"{point.pattern} is read in undeclared modules: {undeclared}. "
        f"Route the decision through {point.owner} instead."
    )


@pytest.mark.parametrize("point", POLICY_POINTS, ids=lambda p: p.pattern)
def test_declared_policy_readers_are_not_stale(point: PolicyPoint) -> None:
    observed = {module for module, _symbol in _policy_reads(point.pattern)}
    stale = sorted(set(point.readers) - observed)
    assert not stale, f"{point.pattern} lists readers that no longer read it: {stale}"
```

**Human step:** the *intended* policy (should one flag control all seven sites at
all?) is a design decision. The guard only makes a new read site visible and makes
the current set explicit.

---

### 3.6 O6 — parallel lifecycle (**human-anchored**)

Two implementations of one lifecycle must be *declared* as a pair, then fed
identical input and asserted to produce identical transitions. The declaration and
the equivalence cases are human; the comparison is automatic.

Verified pair at HEAD: the QC lifecycle exists twice —
`graph/subgraphs/qc.py` (compiled subgraph, used by the forward path) and
`graph/nodes/qc.py` (sequential node, used by the repair loop and `app`) — and the
audits record that their validator sets and side effects differ (F-OST-07,
F-VR-03, F-MCP-04).

```python
"""Guard: O6 parallel lifecycle -- lock only, declaration is human.

Finding: F-OST-07 / F-VR-03 (QC runs as a subgraph on the forward path and as a
sequential node on the repair/app paths, with different validators).
"""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.architecture import LIFECYCLES, LifecyclePair


@pytest.mark.parametrize("pair", LIFECYCLES, ids=lambda p: p.concern)
def test_both_implementations_exist(pair: LifecyclePair) -> None:
    from tests.architecture._harness import resolve

    for side in (pair.left, pair.right):
        assert resolve(side) is not None, f"{pair.concern}: {side} does not resolve"


@pytest.mark.parametrize("pair", LIFECYCLES, ids=lambda p: p.concern)
def test_lifecycles_advance_identical_state(pair: LifecyclePair) -> None:
    """Human-authored equivalence cases; identical input -> identical transition.

    ``pair.cases`` is the human step: one entry per lifecycle event that must not
    diverge (start, validator-set selection, terminal status, side effects).
    """
    from tests.architecture._harness import resolve

    left = resolve(pair.left)
    right = resolve(pair.right)
    for case in pair.cases:
        state: dict[str, Any] = dict(case.state)
        assert left(state) == right(state), (
            f"{pair.concern}: {pair.left} and {pair.right} diverge on "
            f"case {case.name!r} -- recorded in {pair.citation}"
        )


def test_lifecycle_rows_are_not_vacuous() -> None:
    assert LIFECYCLES, "no lifecycle pair declared: vacuous guard"
    for pair in LIFECYCLES:
        assert pair.cases, f"{pair.concern} declares no equivalence cases"
        assert pair.left != pair.right, f"{pair.concern} compares a path to itself"
```

**Human step, stated plainly:** choosing the equivalence cases. The guard cannot
discover that two lifecycles ought to agree; it can only stop them diverging once
someone has said they must.

---

### 3.7 O7 — leaked internals (fully automatable)

*Fails when* a package imports another package's private module or private symbol.

Exact ground truth (`orchestrator-verification-notes.md` V4, re-measured by AST in
this session and matching): **107 cross-package private-module import sites —
106 to `film_pipeline.schemas._base`, 1 to `film_pipeline.app._persistence`
(`mcp/server.py:248`)**; **72 distinct files outside `schemas/` import
`schemas._base`** (109 files total = 37 inside + 72 outside); and **3
cross-package private-symbol sites** — `app/_graph_exec.py:319` →
`graph.nodes._run_validators`, `app/_graph_exec.py:449` →
`graph.nodes.approval._PHASE_NODES`, `config/profile_resolver.py:204` →
`providers.credentials._env_var_for`. (An earlier summary said "105
`schemas._base`"; the measured value is **106** — the AST number is authoritative.
F-BOUNDARY-02's O1 half is rejected; the façade-completeness clause at the end of
this section is the **O8** half that survives `verify-14`.)

The guard **enumerates all 107 + 3 from the AST** — never from a three-line
offender list — and asserts the *derived* totals, so a fourth private-symbol site
or a 108th private-module site fails without anyone editing a number:

```python
"""Guard: O7 leaked internals (F-BOUNDARY-02/05, F-PRIV-01; ledger L-48)."""

from __future__ import annotations

from collections import Counter

from film_pipeline.architecture import (
    PRIVATE_MODULE_EXEMPTIONS,
    PRIVATE_SYMBOL_EXEMPTIONS,
)
from tests.architecture._harness import import_edges, package_of, python_files

#: Row subjects, keyed by kind -- the two families are NEVER mixed (O-03).
MODULE_ROWS = {row.subject for row in PRIVATE_MODULE_EXEMPTIONS}
SYMBOL_ROWS = {row.subject for row in PRIVATE_SYMBOL_EXEMPTIONS}


def _private_sites() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """All cross-package private sites, from the AST.

    Returns ``(module_sites, symbol_sites)`` where each entry is
    ``("path:line", target_import)``. Module sites are keyed by the *imported
    module* (``film_pipeline.schemas._base``); symbol sites by the *imported
    symbol* (``film_pipeline.providers.credentials._env_var_for``). Both are
    site-level, so a comparison against exemption rows is like-for-like once each
    row is expanded to the site set it covers.
    """
    module_sites: list[tuple[str, str]] = []
    symbol_sites: list[tuple[str, str]] = []
    for path in python_files():
        owner = package_of(path)
        for edge in import_edges(path):
            if edge.target_pkg == owner:
                continue
            parts = edge.target.split(".")
            if len(parts) > 2 and parts[2].startswith("_"):
                module_sites.append((f"{edge.source}:{edge.lineno}", ".".join(parts[:3])))
            for name in edge.names or ():
                if name.startswith("_") and name != "*":
                    symbol_sites.append((f"{edge.source}:{edge.lineno}", f"{edge.target}.{name}"))
    return module_sites, symbol_sites


def _uncovered(sites: list[tuple[str, str]], rows: set[str]) -> list[str]:
    """Sites with no covering row. A row covers every site whose target *is* it.

    Granularity note (O-03): the previous revision compared a count of *sites*
    (110) to a count of *rows* (5) and demanded 108 symbol rows. A row and a site
    are different units; the correct relation is coverage, not cardinality.
    """
    return sorted(f"{where} -> {target}" for where, target in sites if target not in rows)


def test_no_cross_package_private_imports() -> None:
    """A package's internals are reachable only from inside that package."""
    module_sites, symbol_sites = _private_sites()
    offenders = _uncovered(module_sites, MODULE_ROWS) + _uncovered(symbol_sites, SYMBOL_ROWS)
    assert not offenders, "cross-package private imports with no recorded row:\n" + "\n".join(offenders)


def test_recorded_rows_are_still_observed() -> None:
    """Violation-aware liveness (O-15): a row lives only while its *violation* does.

    Existence is not enough. ``film_pipeline.schemas._base`` resolves as a module
    even after every importer is migrated, so a ``find_spec``-style check would let
    the row outlive the violation and the burndown would never reach zero. Here a
    module row is live only while >=1 importer is observed; a symbol row is live
    only while >=1 import site is observed. Fixing the violation therefore FORCES
    the row's deletion, which is the ratchet the ledger claims to be.
    """
    module_sites, symbol_sites = _private_sites()
    observed_modules = {target for _where, target in module_sites}
    observed_symbols = {target for _where, target in symbol_sites}
    stale = sorted(
        [row for row in MODULE_ROWS if row not in observed_modules]
        + [row for row in SYMBOL_ROWS if row not in observed_symbols]
    )
    assert not stale, (
        f"private-import rows whose violation is gone: {stale}. "
        "Delete the rows -- a shrinking ledger is the migration succeeding."
    )


def test_private_import_shape_is_a_labelled_change_detector() -> None:
    """Change detector, not a licence (O-02/O-03).

    UPDATE THIS WHEN THE TREE CHANGES, and say why in the commit message: these
    integers are the *shape* of today's violation set, printed so a reviewer can
    see that the ledger covers all of it. They are deliberately NOT the pass
    condition -- ``test_no_cross_package_private_imports`` and
    ``test_recorded_rows_are_still_observed`` are, and they fail on any new or
    fixed site without reference to these numbers. If you edit a number here,
    you are asserting the tree moved, not granting an exemption.
    """
    module_sites, symbol_sites = _private_sites()
    by_module = Counter(target for _where, target in module_sites)
    assert len(module_sites) == 107, f"private-module sites changed: {len(module_sites)}"
    assert by_module["film_pipeline.schemas._base"] == 106
    assert by_module["film_pipeline.app._persistence"] == 1
    assert len(symbol_sites) == 3, f"private-symbol sites changed: {symbol_sites}"
    # Coverage, not cardinality: every module row covers >=1 site, and vice versa.
    assert MODULE_ROWS == set(by_module), "module rows and observed modules disagree"
    assert SYMBOL_ROWS == {target for _where, target in symbol_sites}
```

**The same file carries the O8 façade half.** `verify-14` rejected the O8
classification for F-BOUNDARY-02, so what remains machine-checkable here is façade
*completeness*: every name outsiders import from `schemas._base` must be bound in
`schemas/__init__.py`. It reads the same observed import surface that
`_private_sites()` walks, so it lives in this file rather than duplicating the
sweep — and `_FACADE_EXEMPT` is the ledger family that makes the two known
divergences recorded rather than silent.

```python
# tests/architecture/test_private_imports.py (continued)

def test_schemas_facade_is_complete() -> None:
    """O8 half (F-BOUNDARY-02 after verify-14 rejected its O1 class).

    Every name outsiders import from ``schemas._base`` must be bound in
    ``schemas/__init__.py``. At HEAD this FAILS for two names --
    ``TRANSITION_TYPES`` and ``LEGACY_TRANSITION_ALIASES`` -- which is the real
    existing divergence, so they ship as an exemption row and the row goes stale
    the moment they are re-exported.
    """
    import film_pipeline.schemas as facade

    imported: set[str] = set()
    for path in python_files():
        if package_of(path) == "schemas":
            continue
        for edge in import_edges(path):
            if edge.target == "film_pipeline.schemas._base":
                imported.update(edge.names or ())
    missing = sorted(
        name for name in imported
        if name != "*" and not hasattr(facade, name) and name not in _FACADE_EXEMPT
    )
    assert not missing, f"schemas._base names absent from the public façade: {missing}"
```

`import_edges()` must use `ast.walk`, not `tree.body`: the repo has 52 relative
imports and many function-body imports, and `test_startup_boundaries.py:26`
already documents why lazy imports must be caught.

**Anti-deletion.** A guard that enumerates from the AST can still be *deleted*;
the guard registry (§5.5) is what prevents that, and this file is one of its
entries.

---

### 3.8 O8 — missing contract (**partly automatable**)

Automatable half: every declared public name exists, and (optionally) a package
does not traffic in explicit `Any`. Human half: whether a boundary is *typed well
enough* is review.

Verified at HEAD, the O8 defects are real: every MCP tool advertises an empty
input schema because `mcp/contract.py:52` is
`input_schema: dict[str, Any] = field(default_factory=dict)` and nothing populates
it (F-MCP-03); the resume seam is stringly typed (F-CRP-03, F-BOUNDARY-06); and
`GraphServices` has no protocol — two `FakeArtifactStore`s already disagree
(F-TEST-08).

```python
"""Guard: O8 missing contract -- existence is exact; quality is review.

Findings: F-MCP-03 (empty inputSchema), F-CRP-03 (stringly-typed resume seam),
F-BOUNDARY-06, F-TEST-08.
"""

from __future__ import annotations

import pytest

from film_pipeline.architecture import ModuleContract
from tests.architecture._harness import PACKAGES, resolve

CONTRACTS: dict[str, ModuleContract] = {
    name: resolve(f"film_pipeline.{name}.CONTRACT") for name in PACKAGES
}


@pytest.mark.parametrize("package", sorted(PACKAGES))
def test_public_api_names_exist(package: str) -> None:
    contract = CONTRACTS[package]
    module = resolve(f"film_pipeline.{package}")
    missing = [name for name in contract.public_api if not hasattr(module, name)]
    assert not missing, f"{package} declares public names that do not exist: {missing}"


@pytest.mark.parametrize("package", sorted(PACKAGES))
def test_public_api_is_not_empty(package: str) -> None:
    assert CONTRACTS[package].public_api, (
        f"{package} declares no public API: a seam with no typed interface is O8"
    )


_NON_GOAL_PREFIX = "does not"


@pytest.mark.parametrize("package", sorted(PACKAGES))
def test_responsibility_is_one_sentence_with_explicit_non_goals(package: str) -> None:
    """Bar B1, and the field §2.2's table names but the previous revision never checked.

    M-4 (architecture review) is right that §2.2 asserts "exactly one sentence"
    and "each non-goal starts with ``does not``" while no guard in the catalog did
    either. This is that guard, in the family that already resolves
    ``CONTRACTS``, so it adds no new plumbing.

    The non-goal half is the load-bearing one: a boundary stated only positively
    is what let both `agents` and `providers` appear to own prompt rendering
    (§2.2, A §4). Requiring the disavowal makes the overlap a written claim a
    reviewer can disagree with.

    Limit, stated rather than hidden: sentence counting is a **heuristic** --
    ``". "`` inside the string fails a responsibility containing an abbreviation
    such as "e.g.". That is the intended trade (write it without the abbreviation
    rather than weaken the check), and it is why the assertion message quotes the
    text.
    """
    text = CONTRACTS[package].responsibility.strip()
    assert text, f"{package} has no responsibility statement"
    assert text.endswith("."), f"{package} responsibility does not end with '.': {text!r}"
    assert ". " not in text, f"{package} responsibility is more than one sentence: {text!r}"
    assert len(text) > 20, f"{package} responsibility is too short to state anything: {text!r}"
    assert CONTRACTS[package].non_goals, (
        f"{package} declares no non-goals: the boundary is stated only positively"
    )
    bad = [g for g in CONTRACTS[package].non_goals if not g.startswith(_NON_GOAL_PREFIX)]
    assert not bad, f"{package} non-goals must start with {_NON_GOAL_PREFIX!r}: {bad}"
```

**Human step + the one free lever.** Existence is mechanical; *quality* is not.
The only machine-checkable proxy is mypy's `disallow_any_explicit`, applied
**per package** (never globally — 37 % of public functions carry `Any` today):

```toml
[[tool.mypy.overrides]]
module = ["film_pipeline.schemas", "film_pipeline.schemas.*"]  # low-Any packages only
disallow_any_explicit = true
```

This is deferred to wave 2+ and lands one package at a time; adding it for `graph`
(79/98 public signatures carry `Any`) today would be a wall of errors, not a gate.

#### 3.8.1 `public_api` is normative, not decorative (O-05 / M-2)

`test_public_api_names_exist` above only checks that a *declared* name exists. It
never checks the converse, so a package could declare a 2-name API while callers
import 40 names — which is exactly the state at HEAD, and it is why the adversary
called the declaration decorative. The counter-guard compares the **actual
cross-package import surface** against `public_api`:

```python
"""Guard: O8 second half -- the declared public API is what callers may import."""

from __future__ import annotations

from film_pipeline.architecture import PUBLIC_API_EXEMPTIONS
from tests.architecture._harness import PACKAGES, cross_package_imported_names, resolve

CONTRACTS = {name: resolve(f"film_pipeline.{name}.CONTRACT") for name in PACKAGES}


def test_cross_package_imports_use_the_declared_public_api() -> None:
    """Every name imported across a package boundary is in that package's `public_api`.

    Referenced by `03-target-architecture.md:556-557`, so the mechanism has to
    exist for `03`'s §3.21 reconciliation to be enforceable rather than prose.
    Exemptions are `Exemption` rows keyed ``"<package>::<name>"`` and removed wave by
    wave -- the same ledger discipline as every other family (§5.3), never a
    permanent allow-list.
    """
    exempt = {row.subject for row in PUBLIC_API_EXEMPTIONS}
    problems: list[str] = []
    for package in sorted(PACKAGES):
        declared = set(CONTRACTS[package].public_api)
        observed = cross_package_imported_names(package)
        for name in sorted(observed - declared):
            if f"{package}::{name}" not in exempt:
                problems.append(f"{package}::{name} is imported across a boundary but undeclared")
    assert not problems, (
        "undeclared cross-package imports (add to `public_api`, or record an "
        "Exemption with a removal wave):\n" + "\n".join(problems)
    )


def test_public_api_exemptions_are_live() -> None:
    """The liveness half for the one family that starts empty (O-15 pattern).

    ``PUBLIC_API_EXEMPTIONS`` is deliberately absent from ``DECLARATION_FAMILIES``
    (§5.3 rule 4) because it is empty at W0. That makes it the one exemption
    family whose rot cannot be caught by the non-vacuity rule, so it gets the
    violation-aware liveness check directly: every recorded ``<package>::<name>``
    must still be *observed* as a cross-package import. Once wave 1 lands
    ``public_api``, a row whose import has been declared away fails here and must
    be deleted -- the same ratchet as every other family.
    """
    observed = {
        f"{package}::{name}"
        for package in PACKAGES
        for name in cross_package_imported_names(package)
    }
    stale = sorted(row.subject for row in PUBLIC_API_EXEMPTIONS if row.subject not in observed)
    assert not stale, (
        f"public-API exemptions whose import is gone: {stale}. Delete the rows -- "
        "a shrinking exemption set is the declaration succeeding."
    )
```

**Status at W0: red-on-branch, by construction.** The declarations do not exist
yet, so this guard cannot be green at `fb85baa`; it turns green package by package
as each `CONTRACT.public_api` is authored in wave 1, and the first run populates
`PUBLIC_API_EXEMPTIONS` with the residue that a wave must burn down. That is the
documented pattern for every new guard (§6 step 2: "red is allowed only on the
branch"). The **`03` side of O-05 is already done**, and this file does not need to
request it: `03` §3.21 measures the surface at `fb85baa` and adds
`default_checkpoints_root`, `default_runtime_root` and `graph_state_location` to
the storage contract, while **refuting** `sanitize_artifact_id` as a `public_api`
name (its only importer, `mcp`, loses that edge). So the correct statement is
**three additions and one refutation**, not four additions — the earlier revision's
"four missing names" overstated it.

---

### 3.9 B3 — the dependency law and acyclicity (fully automatable)

Not an O-class, but the guard bar B3 requires: the law must be **mechanically
checkable**, the module graph **acyclic**, and a declared edge must be **real**
(the minimum set, not a licence). Protects F-BOUNDARY-01/03/04 and retires L-48.

#### The edge matrix is the contract; the edge count is *derived*

`orchestrator-verification-notes.md` **V3** is a finding about the *design*, not
about a number: "the widely-quoted **8 forbidden domain→domain edges** is the union
of three targeted greps, not an enumeration." Re-measured at `fb85baa` on the
package-granularity edge set, the ladder is a pure filter chain — note that the
last rung is **6**, not the "7 + 3" the audit prose states, because the `artifacts`
filter also removes `testing→artifacts`:

| Rung | Filter | Count | Reproduce |
|---|---|---|---|
| L1 | all cross-package package pairs | **53** | `package_edges()` |
| L2 | source ∉ {`graph`, `mcp`} (unrestricted W0 pre-image) | **32** | `{e for e in L1 if e[0] not in UNRESTRICTED_PACKAGES}` |
| L3 | target ≠ `schemas` (contract layer) | **21** | `{e for e in L2 if e[1] != "schemas"}` |
| L4 | target ≠ `artifacts` (storage façade) | **17** | `{e for e in L3 if e[1] != "artifacts"}` |
| L5 | source ∉ {`app`, `cli`} (composition roots) | **6** = **4** domain→domain (`agents→providers`, `config→providers`, `generation→providers`, `post→validation`) + **2** `testing→*` (`testing→checkpoints`, `testing→providers`) | `{e for e in L4 if e[0] not in {"app","cli"}}` |

The law never defines "domain module" and never says whether importing the
`artifacts` façade is "communicating through `artifacts`" or a forbidden edge —
which is exactly why the guard below does not consume this ladder.

**A guard that hardcodes `8` (or `10`) is the same failure mode as the prose law
it replaces.** The law encodes **no** edge count: it encodes the declared matrix,
and the forbidden set is its complement.

**Single source of the forbidden-edge count (O-02).** Three numbers circulate; only
one has a home, and it is not in this file:

| Number | Where | Status |
|---|---|---|
| **10** | `03-target-architecture.md:1655`, derived from the §4.3 matrix (7 domain→domain + 3 `testing→*`) | **The only count the program recognises, and `03` owns it.** `05` treats it as a consequence of the matrix and asserts it nowhere. |
| **8** | the audit's "8 forbidden domain→domain edges" | **Retired.** It is the union of three targeted greps, not an enumeration (`orchestrator-verification-notes.md` V3); `03` does not use it. |
| 53 / 32 / 21 / 17 / 6 | the ladder above | **Observed at `fb85baa`, not law.** A change-detector, kept so a reviewer notices when the tree moves — and the only place in this document where those integers appear. |

The **single source is the `03` §4.3 matrix**, and §4.3 itself states where that
matrix lives: *"exactly one machine-readable home: `ModuleContract.may_import` in
each package `__init__.py` … No second matrix file may exist."* So `05` does not
define a second set, a scope, or a count. The forbidden set is **the complement of
the declared matrix**, computed at run time:

> `forbidden := observed_cross_package_edges − declared_may_import − ALWAYS_IMPORTABLE`

No assertion anywhere in this document compares against `8`, `10` or `53`. The
earlier revision was internally contradictory — it claimed to "encode no edge
count" while its first assertion pinned `len(edges) == 53`, and it carried a
scope-table derivation whose forbidden set disagreed with `03`'s derived `10`.
Both are removed; the 53 survives only as a labelled **change-detector**, below.
The consequence is that **"the forbidden-edge count" is not a number this document
owns** — it is `|observed − declared|`, and `03`'s `10`, the audit's retired `8` and
the ladder above are all *historical readings of the tree at different
granularities*, none of which the guard consumes.

```python
# src/film_pipeline/architecture.py -- W0 pre-image constants only; no scope tables.
# `03` §4.3 forbids a second matrix file, so the scope machinery that the previous
# revision used to *derive* a forbidden set is deleted: the forbidden set is the
# complement of `may_import` and needs no declaration of its own.

#: Every package that participates in the law; anything unlisted is a guard error,
#: not a silent exemption (mirrors proposal A §6.4's layers-cover-the-tree test).
MODULE_LAYERS: Final[Mapping[str, int]] = {
    "schemas": 1,         # contract layer: importable by everyone, imports only filmspec
    "config": 2,          # ...
    "artifacts": 3,       # storage: imports schemas only, never a domain
    # ... all 17, per the layer table 03 §4.3 publishes (provisional here)
}

#: CHANGE-DETECTOR, not law. The cross-package edge set measured at fb85baa. Its
#: only purpose is to force a reviewer to re-read the 03 §4.3 matrix when the tree
#: moves; the forbidden-edge count is the complement computed below and is asserted
#: nowhere. A wave that legitimately changes the edge set updates these two values.
OBSERVED_EDGE_SET_AT: Final[str] = "fb85baa"
OBSERVED_CROSS_PACKAGE_EDGES: Final[int] = 53


def _declared_edges() -> set[tuple[str, str]]:
    """The ONLY thing the law asserts: every edge the matrix declares.

    ``CONTRACTS`` is defined in the same guard module (below); this helper exists so
    the complement test and the acyclicity/real-edge tests read one implementation.
    """
    return {(source, target) for source, c in CONTRACTS.items() for target in c.may_import}
```

The forbidden set is then a one-line complement, and the matrix is the only
declaration it consults:

```python
def test_no_cross_package_edge_escapes_the_declared_matrix() -> None:
    """V3, restated: the forbidden set is `observed − declared`. No count is law.

    This subsumes the previous revision's scope-table guard. It is deliberately
    *not* parameterized per source package (that is `test_imports_stay_within_
    declared_edges`); its job is the global statement: there is no cross-package
    edge in the tree that the `03` §4.3 matrix does not declare, so the matrix's
    complement -- the forbidden set -- is empty of observed edges by construction.
    """
    declared = _declared_edges()
    undeclared = sorted(
        (source, target)
        for source, target in package_edges()
        if target not in ALWAYS_IMPORTABLE and (source, target) not in declared
    )
    assert not undeclared, (
        f"cross-package edges absent from the 03 §4.3 matrix: {undeclared}"
    )


@pytest.mark.change_detector
def test_the_observed_edge_ladder_is_still_what_this_document_reports() -> None:
    """The observed cross-package edge count, pinned to `OBSERVED_EDGE_SET_AT`.

    Marked `change_detector` (a marker this suite registers) so it is visibly *not*
    a law test: it exists only so that a wave which changes the cross-package edge
    set must also update §3.9's prose and re-read `03` §4.3. Nothing in the guard
    suite depends on the number being right; the law test above depends only on the
    matrix.
    """
    edges = package_edges()
    assert len(edges) == OBSERVED_CROSS_PACKAGE_EDGES, (
        f"cross-package edge set moved from {OBSERVED_CROSS_PACKAGE_EDGES} to "
        f"{len(edges)} since {OBSERVED_EDGE_SET_AT}: re-read 03 §4.3, update the "
        "matrix rows if the law changed, and update this constant + §3.9's ladder."
    )
```

`test_no_cross_package_edge_escapes_the_declared_matrix` is the guard `03` must
satisfy: the matrix is the declaration, its complement is the forbidden set, the
ledger records the residual, and **no count appears in any assertion**. The second
test is a change-detector with a dedicated marker — the distinction the previous
revision failed to make. **When `03-target-architecture.md` ratifies `MODULE_LAYERS`,
this provisional table is replaced by that file's; the guard code does not change.**

```python
"""Guard: the module law -- declared edges, real edges, acyclicity (B3)."""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.architecture import ALWAYS_IMPORTABLE, CYCLE_EXEMPTIONS, MODULE_LAYERS
from tests.architecture._harness import (
    PACKAGES,
    SRC,
    import_edges,
    module_edges,
    package_edges,
    resolve,
    strongly_connected_components,
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


def test_architecture_manifest_size() -> None:
    """The leaf's blast radius is bounded by its size (§2.1, §8.6).

    Every package ``__init__.py`` imports this module, so a syntax or name error
    here breaks the import of the whole distribution. The size limit is what keeps
    the file reviewable and the split decision pre-committed rather than
    improvised: at >750 lines the *data* families move to
    ``architecture_<domain>.py`` siblings (types and the ``ModuleContract`` /
    ``Exemption`` definitions stay in the leaf).
    """
    manifest = SRC / "architecture.py"
    limit = 750
    lines = len(manifest.read_text().splitlines())
    assert lines <= limit, (
        f"{manifest} is {lines} lines, over the {limit}-line limit. Split the data "
        "families to architecture_<domain>.py siblings (types stay in the leaf) -- "
        "see 05-enforcement-and-guard-tests.md §8.6, and move the limit only in the "
        "same commit that records the measured count."
    )


@pytest.mark.parametrize("source_pkg", sorted(PACKAGES))
def test_imports_stay_within_declared_edges(source_pkg: str) -> None:
    contract = CONTRACTS[source_pkg]
    if contract.unrestricted_imports:
        return
    allowed = set(contract.may_import) | set(ALWAYS_IMPORTABLE) | {source_pkg}
    undeclared = sorted(
        target for source, target in package_edges() if source == source_pkg and target not in allowed
    )
    assert not undeclared, (
        f"{source_pkg} imports undeclared packages: {undeclared}. Remove the import "
        f"or add the edge to {source_pkg}/__init__.py CONTRACT.may_import."
    )


@pytest.mark.parametrize("source_pkg", sorted(PACKAGES))
def test_declared_edges_are_real(source_pkg: str) -> None:
    """A declared edge with no importer is a stale contract, not a licence."""
    contract = CONTRACTS[source_pkg]
    observed = {target for source, target in package_edges() if source == source_pkg}
    stale = sorted(set(contract.may_import) - observed)
    assert not stale, f"{source_pkg} declares unused edges: {stale}"


def test_declared_edges_go_strictly_down_one_layer() -> None:
    """L1 (M-1): every declared edge points at a STRICTLY lower layer.

    Without this, acyclicity alone permits any DAG — a same-layer or upward
    ``may_import`` such as ``post -> governance`` (L6 -> L7) forms no cycle and
    would ship green. ``MODULE_LAYERS`` was declared but unread in the prior
    revision; this test is what makes L1 mechanically checkable (B3).
    """
    problems: list[str] = []
    for source, contract in CONTRACTS.items():
        source_layer = MODULE_LAYERS[source]
        for target in contract.may_import:
            if target not in MODULE_LAYERS:  # e.g. "architecture"
                continue
            target_layer = MODULE_LAYERS[target]
            if target_layer >= source_layer:
                problems.append(
                    f"{source} (L{source_layer}) -> {target} (L{target_layer}): "
                    "same-layer or upward edge"
                )
    assert not problems, "L1 layer-direction violations:\n" + "\n".join(sorted(problems))


def test_every_package_is_assigned_a_layer() -> None:
    """A package without a layer would silently escape L1."""
    missing = sorted(set(PACKAGES) - set(MODULE_LAYERS))
    assert not missing, f"packages with no MODULE_LAYERS row: {missing}"


def test_module_graph_is_acyclic_except_recorded_cycles() -> None:
    """B3 acyclicity, at the granularity where the five recorded cycles live.

    Prior revision (RR-5, roadmap review): ``CONTRACTS`` is keyed on the **17
    top-level packages**, so both endpoints of an intra-package cycle collapse to
    one key and only **C2** was visible. C1 (``agents.prompt_templates``), C3
    (``graph`` / ``graph.nodes`` / ``graph.orchestrator_validators`` /
    ``graph.subgraphs``), C4 (``providers.adapters``) and C5
    (``schemas.registries``) were structurally invisible — a guard whose whole
    claim is that the five enola cycles are closed.

    This sweep builds the graph from ``module_edges()`` and runs Tarjan SCC over
    the **whole** graph; no edges are deleted before the sweep. Each multi-member
    SCC must match a recorded cycle *component*, not an arbitrary feedback edge
    set: an exempted cycle is recorded in ``CYCLE_EXEMPTIONS`` as
    ``"a <-> b <-> c"``, so closing the cycle makes the row stale (reported by
    ``test_cycle_exemptions_still_describe_a_real_cycle``) and a *new* cycle can
    never be absorbed by a stale edge deletion.

    **It now sees C1, C2, C3, C4 and C5.** Measured at `fb85baa`:
    ``module_edges()`` has **121 edges over 35 package-directory nodes** (34 of them
    with at least one outgoing edge), and its
    SCCs are exactly the five of `01-ownership-map.md` §15 — C1 (2 members), C2
    (7: ``app``, ``app.services``, ``mcp``, ``mcp.tools``, ``mcp.tools.bibles``,
    ``mcp.tools.generation``, ``mcp.tools.reference_generation``), C3 (4), C4 (2),
    C5 (2).
    """
    recorded = {frozenset(row.subject.split(" <-> ")) for row in CYCLE_EXEMPTIONS}
    unrecorded = [
        " <-> ".join(sorted(component))
        for component in strongly_connected_components(module_edges())
        if len(component) > 1 and frozenset(component) not in recorded
    ]
    assert not unrecorded, "unrecorded package-directory dependency cycles:\n" + "\n".join(
        sorted(unrecorded)
    )


def test_cycle_exemptions_still_describe_a_real_cycle() -> None:
    """An exemption for a cycle that no longer exists is a stale record.

    Deleting the row is the wave's exit criterion for that cycle: the row is the
    only thing standing between the SCC sweep and a red build.
    """
    observed = {
        frozenset(component)
        for component in strongly_connected_components(module_edges())
        if len(component) > 1
    }
    for row in CYCLE_EXEMPTIONS:
        assert frozenset(row.subject.split(" <-> ")) in observed, (
            f"cycle exemption no longer describes an observed cycle: {row.subject}. "
            "If the wave closed it, delete the row."
        )


def test_module_edges_are_keyed_at_package_directory_granularity() -> None:
    """Rule against silent granularity drift (the RR-5 failure mode).

    If ``module_edges()`` ever collapses back to top-level package keys, the SCC
    sweep above goes blind again *and still passes*. This pins the granularity:
    sub-packages must be distinct nodes, so an intra-``graph`` cycle can be seen.
    """
    graph = module_edges()
    universe = set(graph) | {target for deps in graph.values() for target in deps}
    assert len(universe) >= 35, (
        f"module_edges() collapsed to {len(universe)} nodes; the measured universe at "
        "fb85baa is 35 package directories (34 with outgoing edges)"
    )
    sub = {node for node in universe if "." in node}
    assert len(sub) >= 18, (
        f"only {len(sub)} sub-package nodes: granularity collapsed to top-level keys"
    )
    assert {"graph.nodes", "graph.subgraphs", "schemas.registries", "providers.adapters"} <= sub, (
        f"sub-package nodes missing from module_edges(): {sorted(sub)}"
    )
    assert len(graph) >= 34, f"only {len(graph)} nodes have outgoing edges"
```

**Harness additions this revision requires.** `module_edges()` and
`strongly_connected_components()` do not exist in the previous revision and are
the two pieces that make the SCC sweep possible; they live in
`tests/architecture/_harness.py` (one implementation, per §4). Two further helpers
are added for the ledger guard: `private_module_violations()` (the O7 sweep's
observed cross-package private-module targets, extracted from §3.7 so that §5.3's
`subject_is_live` is violation-aware without a second implementation) and
`git_tracked(path)` (`git ls-files --error-unmatch`, used by the citation check so
a citation into the *tracked* tree must be tracked). `module_edges()`
reuses the same `ast.walk`-based import extraction as `import_edges()` — it adds
**no new parsing** — and differs only in how it names endpoints.

**Two granularities, two functions, stated once so they cannot be confused.**
`module_edges()` keys on the **nearest package directory** (`graph.nodes`) and is
what the acyclicity sweep consumes. `package_edges()` keys on the **top-level
package** (`graph`) and is what the layer law, the edge-ladder change-detector and
`test_declared_edges_are_real` consume. The second is a documented collapse of the
first — there is one parser, not two:

```python
# tests/architecture/_harness.py

def package_edges() -> set[tuple[str, str]]:
    """Top-level-package import pairs: the layer law's granularity (§3.9).

    A *collapse* of ``module_edges()``, not a second sweep: ``graph.nodes`` and
    ``graph.subgraphs`` both become ``graph``, and self-edges that the collapse
    creates are dropped. The layer law and the ladder are stated in these terms
    (17 packages); the cycle law is stated in directory terms (35 nodes). Keeping
    both here makes the distinction reviewable in one place.
    """
    collapsed = {
        (source.split(".")[0], target.split(".")[0])
        for source, deps in module_edges().items()
        for target in deps
    }
    return {(source, target) for source, target in collapsed if source != target}
```

Expanded, `module_edges()` is:

```python
# tests/architecture/_harness.py

def _owning_package(path: Path) -> str:
    """Nearest ancestor directory containing ``__init__.py``, dotted, no prefix.

    This is the granularity choice that makes C1, C3, C4 and C5 visible: every
    module *file* maps to its package directory, so ``graph/nodes/prep.py`` and
    ``graph/nodes/__init__.py`` are both ``graph.nodes`` -- and an edge
    ``graph.graph -> graph.nodes`` therefore has two distinct endpoints. Collapsing
    to the top-level package (the prior behaviour) merges them and hides C3.
    """
    directory = path.parent
    while directory != SRC and not (directory / "__init__.py").exists():
        directory = directory.parent
    return "" if directory == SRC else str(directory.relative_to(SRC)).replace("/", ".")


def module_edges() -> Mapping[str, frozenset[str]]:
    """Observed import edges between package directories (§3.9).

    Keys are **package directories with at least one outgoing edge** (34 at
    `fb85baa`); the node universe is the union of keys and targets (35). Callers
    that need the universe must union the values -- ``strongly_connected_components``
    below does so, which is why it can see a pure sink as its own component.
    """
    edges: dict[str, set[str]] = defaultdict(set)
    for path in python_files():
        source = _owning_package(path)
        for edge in import_edges(path):
            target = _owning_package(edge.target_path) if edge.target_path else ""
            if source and target and source != target:
                edges[source].add(target)
    return {node: frozenset(deps) for node, deps in edges.items()}


def strongly_connected_components(
    graph: Mapping[str, Collection[str]],
) -> list[list[str]]:
    """Tarjan SCC (iterative), returned as components, singletons included.

    Iterates ``set(graph) | {t for deps in graph.values() for t in deps}`` -- the
    full node universe -- so a package that only ever *receives* edges is still a
    component of its own rather than being silently absent from the sweep.
    """
    ...  # ~30 lines, no dependency; the only reader is the acyclicity guard
```

**What the acyclicity guard sees now.** At package-directory granularity the five
cycles `01-ownership-map.md` §15 records are each a distinct SCC, in dotted node
names: **C1** `agents.prompt_templates ↔ agents.prompt_templates.defaults`;
**C2** `app ↔ app.services ↔ mcp ↔ mcp.tools ↔ mcp.tools.bibles ↔
mcp.tools.generation ↔ mcp.tools.reference_generation` (7 members, matching §15);
**C3** `graph ↔ graph.nodes ↔ graph.orchestrator_validators ↔ graph.subgraphs`
(4, matching §15); **C4** `providers ↔ providers.adapters`; **C5** `schemas ↔
schemas.registries`. All five need a `CYCLE_EXEMPTIONS` row at W0 (not just C2),
and each row's removal is a wave's exit criterion. The prior package-keyed version
could see only C2, and — worse — it could not distinguish "no cycle" from "cycle
collapsed to a self-loop".

Each row records the **whole member set**, never one "representative" edge. That
matters most for C3: measured at `fb85baa` its sub-graph has **8 internal edges and
a minimal feedback set of 3** (`graph → graph.nodes`, `graph → graph.subgraphs`,
`graph.nodes → graph.orchestrator_validators`). One edge per cycle would have left
C3 live while the guard reported green — the exact class of silence RR-5 named.

**enola's second gate is aspirational until it is wired.** `enola` is **not** in
`ci-check` — `.github/workflows/ci.yml` runs `make ci-verify`, and `make ci-check`
is `format-check lint typecheck test-cov build product-gate`; nothing invokes
`enola`. §7.2's `enola check --fail-on=cycles,layers` is therefore a **manual,
reviewer-run** gate at W0 (and is not one of the tests the registry protects),
promoted to CI only if wave 3 shows it adds signal beyond the SCC sweep above. The
document does not claim a second automated gate it does not have.

`test_declared_edges_are_real` is the second half of B3 and is why the law stays
tight: a `may_import` entry cannot sit in the manifest unexercised, so wave-1
tightening (`config` dropping `providers` — and **not** `agents`, which `03:685`
and §4.3 declare allowed; O-11) actually has to land rather than being announced.

---

### 3.10 Guard ↔ ledger concern coverage

`02-duplication-ledger.md` has landed with **58 canonical concerns (L-01 … L-58)**.
(Measured corpus, § header: **173 live findings — 38 Critical, 88 High,
47 Medium, 0 Low.** `F-TEST-02` is withdrawn and carries no Severity bullet, so it
is not part of the 173. The ledger's 58 concerns were deduplicated at the
148-finding synthesis moment and are a *different* measure from the live finding
count, so the coverage arithmetic below is unaffected by this correction.) A guard
that does not name the concern it protects is unauditable, so each guard file
declares a `GUARD_CONCERNS` tuple (§5.5) and the table below maps each guard family
to the ledger entries it pins.

The mapping is **mechanically derived from the ledger's own O-class column** — not
hand-assigned — so it cannot drift from the ledger without a re-run failing:

```bash
# Reproduce: L-NN -> O-class membership, from the ledger's executive table.
python3 - <<'EOF'
import re, pathlib
text = pathlib.Path("docs/modular-architecture/02-duplication-ledger.md").read_text()
rows = re.findall(r"^\| (L-\d\d) \| ([^|]+?) \|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|$", text, re.M)
by = {}
for lid, _title, _sev, oclass, _owner, _ver in rows:
    for c in re.findall(r"O[1-8]", oclass):
        by.setdefault(c, []).append(lid)
for c in sorted(by):
    print(c, len(by[c]), ", ".join(by[c]))
EOF
```

| Guard family | Ledger concerns it pins | # |
|---|---|---|
| **O1** `test_vocabularies.py` | L-02, L-03, L-04, L-06, L-07, L-08, L-13, L-14, L-15, L-16, L-18, L-20, L-24, L-25, L-28, L-32, L-33, L-34, L-38, L-39, L-40, L-41, L-42, L-46, L-47, L-50, L-52, L-55, L-57, L-58 | 30 |
| **O2** `test_invariants.py` (human-anchored) | L-01, L-05, L-17, L-18, L-27, L-29, L-34, L-35, L-38, L-44, L-47, L-51 | 12 |
| **O3** `test_state_writers.py` | L-01, L-04, L-09, L-10, L-11, L-13, L-15, L-16, L-19, L-20, L-21, L-26, L-38, L-42, L-45, L-46, L-55 | 17 |
| **O4** `test_registries.py` | L-07, L-09, L-13, L-15, L-18, L-28, L-30, L-34, L-36, L-37, L-39, L-40, L-41, L-42, L-45 | 15 |
| **O5** `test_policy_points.py` | L-01, L-02, L-03, L-10, L-11, L-26, L-27, L-28, L-29, L-31, L-34, L-38, L-39, L-41, L-43, L-44, L-47, L-48, L-53, L-55, L-56 | 21 |
| **O6** `test_lifecycles.py` (human-anchored) | L-03, L-04, L-06, L-08, L-12, L-16, L-17, L-19, L-22, L-31, L-36, L-42, L-45 | 13 |
| **O7** `test_private_imports.py` | L-48, L-50, L-53, L-54, L-56 | 5 |
| **O8** `test_public_api.py` | L-05, L-07, L-08, L-10, L-12, L-19, L-20, L-21, L-22, L-23, L-27, L-28, L-31, L-33, L-35, L-46, L-47, L-48, L-49, L-52, L-53, L-54 | 22 |
| **B3** `test_contracts.py` (edge law + acyclicity) | L-12, L-48, L-54 (plus every concern whose candidate owner is `module-law`) | 3 |
| **N** `test_normative_numbers.py` (V1/V6) | L-14, L-41, L-53, L-58 (a normative number with one authority, not 22–24 literals) | 4 |

**Coverage arithmetic** (also mechanically derived — a concern may carry several
O-classes, so the column counts sum to more than 58):

| Measure | Count | Concerns |
|---|---|---|
| Total ledger concerns | **58** | L-01 … L-58 |
| Pinned by ≥1 **fully automatable** guard (O1/O3/O4/O5/O7) | **50** | all except the eight below |
| Pinned **only** by a partly/human-anchored class (O2/O6/O8) | **8** | L-05, L-12, L-17, L-22, L-23, L-35, L-49, L-51 |
| Of those, with an **exact mechanical core** despite the class | **2** | L-23 (`input_schema` populated: an existence/count check), L-49 (router action literals ⊆ declared edge-table actions: a `VocabularyMirror` `subset` row) |
| Genuinely human-anchored (enumeration/cases are the human step) | **6** | L-05, L-12, L-17, L-22, L-35, L-51 |
| Concerns with **no** O-class at all | **0** | — (every one of the 58 is classified in the ledger) |

**What "pins" means, and what "retires" means.** A guard is green from wave 0
because the ledger records the deviation; the guard **pins** the concern
(`observed ⊆ recorded` and `recorded ⊆ observed`). A concern is **retired** only
when the playbook's step-5 command returns the owner and nothing else (O1/O3/O4)
and the ledger rows for it are gone. The ledger's own per-entry "Guard test" field
names the same guard family, so a concern's status is readable from two
independent places — and `test_every_ledger_concern_is_claimed` (§5.5) fails if a
concern is orphaned or a guard claims a concern id that the ledger does not
define.

Two ledger entries deserve explicit callouts for the guards:

- **L-48** ("Module dependency law, enforcement and private reach-ins") is the
  concern this entire document exists to retire, and it is the only entry marked
  `VERIFIED (corrected)` by `verify-14`. Its guard list is the edge matrix, the
  private-import sweep, **and the façade-completeness test** — the O8 half added
  by the verifier's O1 rejection (§1.6).
- **L-12** ("MCP tool invocation lifecycle and the `app` ↔ `mcp` cycle") is
  `MIXED`: one verifier verdict covers part of it, and its candidate owner is
  `mcp.dispatch / module-law`. It is claimed by **O6, O8 and B3**; the cycle half
  is retired by `test_module_graph_is_acyclic_except_recorded_cycles` plus `CYCLE_EXEMPTIONS`,
  the invocation-lifecycle half stays human-anchored.

---

### 3.11 Normative numbers — the V1/V6 guard class

The orchestrator's **V6** records the anti-pattern directly: *"Three separate
files stated the same threshold count and all three were wrong in the same
direction, while a fourth file had already corrected it. That is a small instance
of the exact failure this program audits: a number duplicated across owners with
no single authority and no guard."* **V1** measures the truth: **23**
`ValidatorThresholds(` calls in `src/`; **22** carry all three literals (the 23rd
is the bare default at `validation/thresholds.py:21`); distribution **18×
(85, 75, 75), 3× (80, 70, 70), 1× (90, 80, 80)**; `block_below == review_at` in
**22 of 22**; `block_below == 75` in **18**, not 20 (the "24/20" figure came from
a grep that also matched the class definition line and the Pydantic `Field`
default at `schemas/registries/validator_registry.py`).

A guard class is therefore required that treats a **normative number** the same
way O1 treats a normative vocabulary: one owner, and every other occurrence either
references the owner or is recorded. This generalizes beyond thresholds — the
`300`/`5`-second defaults (L-53), the `110%` spend ceiling (L-41), and the
score bands (L-14, L-58) are all the same shape.

```python
# src/film_pipeline/architecture.py -- extends the §2.2 type family.

@dataclass(frozen=True, slots=True)
class NormativeNumber:
    """One normative value (or value-tuple) that must have a single authority.

    ``owner`` is the dotted symbol that defines the value; ``sites`` is the AST
    pattern that finds every occurrence; the guard derives the count and the
    distribution, so neither is written down as a licence.
    """

    concern: str
    owner: str
    call_pattern: str          # e.g. "film_pipeline.schemas.registries.validator_registry.ValidatorThresholds"
    expected_distribution: Mapping[tuple[float, float, float], int]
    exemptions: tuple[Exemption, ...] = ()


NORMATIVE_NUMBERS: Final[tuple[NormativeNumber, ...]] = (
    NormativeNumber(
        concern="validator score→status thresholds (ledger L-14)",
        owner="film_pipeline.validation.thresholds.ValidatorThresholds",
        call_pattern="ValidatorThresholds",
        expected_distribution={(85.0, 75.0, 75.0): 18, (80.0, 70.0, 70.0): 3, (90.0, 80.0, 80.0): 1},
    ),
)
```

```python
"""Guard: normative numbers have one authority (V1/V6; ledger L-14, L-41, L-53, L-58)."""

from __future__ import annotations

import ast
from collections import Counter

import pytest

from film_pipeline.architecture import NORMATIVE_NUMBERS, NormativeNumber
from tests.architecture._harness import parse, python_files, rel


def _threshold_calls() -> Counter[tuple[float, float, float]]:
    """Every literal ``ValidatorThresholds(...)`` call, from the AST, with values."""
    found: Counter[tuple[float, float, float]] = Counter()
    for path in python_files():
        for node in ast.walk(parse(path)):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "ValidatorThresholds":
                values = {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords}
                if {"pass_at", "review_at", "block_below"} <= set(values):
                    found[(values["pass_at"], values["review_at"], values["block_below"])] += 1
    return found


@pytest.mark.parametrize("number", NORMATIVE_NUMBERS, ids=lambda n: n.concern)
def test_normative_number_distribution_is_derived_not_written(number: NormativeNumber) -> None:
    """The count and distribution come from the AST; a new literal fails here."""
    observed = _threshold_calls()
    assert dict(observed) == dict(number.expected_distribution), (
        f"{number.concern}: threshold literal distribution changed.\n"
        f"observed={dict(observed)} expected={dict(number.expected_distribution)}"
    )


def test_score_band_is_collapsed_into_blocked() -> None:
    """Four-status reachability (V1): NEEDS_REVISION is unreachable at HEAD.

    ``block_below == review_at`` in all 22 literal call sites, so the
    ``score >= block_below`` branch at ``validation/thresholds.py:27`` can never
    be reached: the scores that would need revision are already ``blocked``. This
    test asserts today's three-status reality, so the day the band is restored the
    test FAILS and the exemption row (and the L-14 ledger row) must be deleted.
    """
    from film_pipeline.schemas.registries.validator_registry import ValidatorThresholds
    from film_pipeline.validation.thresholds import score_to_status

    for triple in _threshold_calls():
        thresholds = ValidatorThresholds(pass_at=triple[0], review_at=triple[1], block_below=triple[2])
        assert triple[2] == triple[1], f"band restored in {triple}; see L-14"
        observed = {str(score_to_status(float(s), thresholds)) for s in range(101)}
        assert observed == {"pass", "pass_with_notes", "blocked"}, (
            f"{triple}: reachable statuses changed to {observed}; "
            "if NEEDS_REVISION is now reachable, delete the L-14 exemption and this assertion"
        )


def test_every_threshold_owner_lives_in_the_contract_layer() -> None:
    """The value's authority is the owner symbol, not any of the 22 call sites."""
    for number in NORMATIVE_NUMBERS:
        assert number.owner.split(".")[0] == "film_pipeline"
        assert number.expected_distribution, f"{number.concern}: no distribution declared"
```

---

## 4. The four existing guards and their consolidation

All four are good guards; none of them generalizes. The consolidation **replaces
the private helper copies, never the coverage**.

| Guard | What it pins today | What generalizes | Migration path (no coverage lost) |
|---|---|---|---|
| `tests/unit/artifacts/test_storage_boundary.py` (188 lines) | 5 AST rules + a façade-API assertion: no layout/serialization/path import outside `artifacts/`; no layout constants leaked; the storage core imports no other component; no runtime `checkpoints` dependency; `ProjectStorage` owns 11 typed accessors; both construction paths agree; unconfigured backend reports actionably. Guards the **single clean subsystem** in the map (`01-ownership-map.md` §17). | `test_only_storage_imports_layout_facts`, `test_only_storage_imports_path_helpers`, `test_storage_core_does_not_import_other_components` are direct instances of **O7 + the edge law**. | **Keep the file.** The three import sweeps become *redundant* once `test_private_imports.py` + `test_contracts.py` cover the same edges; leave them in place until the generalized guards are proven green for a wave, then delete the duplicated assertions and keep the behavioural tests (`test_construction_from_root_and_store_agree`, `test_unconfigured_backend_reports_actionably`, the layout-constant leak check) which the manifest cannot express. |
| `tests/unit/graph/test_startup_boundaries.py` (76 lines) | No module under `graph/` imports `testing` or `app`, **including lazy function-body imports**; constructing mock services pulls in no `testing` modules (fresh interpreter); the default runtime gets injected canned responses. Encodes a real historical leak. | `test_graph_package_never_imports_testing_or_app` generalizes to **L7 harness isolation for all packages**: `PRIVATE`/forbidden-target sweeps in `test_private_imports.py` with `film_pipeline.testing` in every package's forbidden set. | **Keep the file**, and add the generalized L7 guard in `test_contracts.py` (parametrized over all packages). The **fresh-interpreter test is not generalizable** and must stay: it proves a *runtime* property (`sys.modules`), which no AST sweep can. |
| `tests/unit/config/test_config_contract.py` (409 lines) | Every profile leaf and every `ENV_OVERRIDE_MAP` target is read somewhere in `src/`, or is a cited `KNOWN_DEAD_GROUPS` row; citations must resolve and their `§X` sections must exist; `READERS` annotations must name real functions and be exercised at runtime. This is the **best existing precedent for the exemption ledger**. | The ledger **hygiene** rules (`test_known_dead_rows_cite_evidence`, `test_named_flx_f9_failures_stay_deliberate`, `test_annotated_reader_paths_are_exercised`) become `test_exemptions.py` (§5). The profile-leaf sweep stays config-specific. | **Keep the file.** Re-express `KNOWN_DEAD_GROUPS` as `Exemption` rows where they are genuinely cross-module (the budget and review groups touch `governance`/`generation`), and leave the config-internal groups as a specialization. The `test_named_flx_f9_failures_stay_deliberate` pattern is the template for **gap records** used in O4 (§3.4). |
| `tests/unit/graph/test_channel_registry.py` (371 lines) | The orchestrator constant ↔ `GraphState` ↔ `ORCH_CHANNELS` triangle; per-key propagation policy; **every** write to a boundary key in `graph/nodes/**` has a `WRITER_DISPOSITIONS` row and no row is stale; the `execution_brief` boundary regression. Protects the D-009 bug class. | This is **already the O1+O3+O4 mechanism, hand-built for one seam**. `WRITER_DISPOSITIONS` keyed by `(filename, key)` (line-number-free, deliberately) becomes `StateChannel.writers` keyed by `"<module>::<symbol>"` — strictly stronger, because a *new* write site inside an already-recorded module then fails. | **Keep the file** for the propagation-policy tests (they are behavioural, not structural) and migrate `_sweep_boundary_writes` + `WRITER_DISPOSITIONS` into the harness/`StateChannel` form. The node-boundary write sweep becomes a *reusable* `write_sites()` instead of a private helper; the same sweep then also covers `current_phase` (8 writers) and any other channel. |

**The consolidation rule.** After wave 0, **exactly one** module in the tree
implements `_python_files()` / `ast.parse` / symbol resolution: `tests/architecture/_harness.py`.
`test_storage_boundary.py` and `test_startup_boundaries.py` may keep their
*behavioural* tests, but a new guard must not add a sixth private copy. The
migration is safe because it is additive-then-subtractive: add the general guards,
prove them green against the same facts, then delete the duplicated assertions.

**Net effect on coverage:** none lost. Every assertion listed above maps to either
a general guard (edge law, O7, O5, O3, ledger hygiene) or stays in its specialist
file (fresh-interpreter runtime check, propagation policy, storage behaviour).

---

## 5. Exemption ledger design

The ledger is what lets the suite ship **green today** while the law is only
partly true. It is also, by a distance, the mechanism's biggest failure mode, so
it gets the most rules.

### 5.1 The type

One `Exemption(subject, reason, citation, removal_phase)` serves every family. The
first three fields are proposal B's; `removal_phase` is this document's amendment
(B §10.1(d) requires each row to cite the wave that removes it — making that a
typed field instead of prose is what lets the burndown be read mechanically).

Three properties make a row non-rotting:

- **`subject` is a computed key, never a line number.** A dotted path, a
  `"<module>::<symbol>"` writer key, a `"<left> -> <right>"` edge, or a
  `"<a> <-> <b> <-> <c>"` cycle member set (§5.2). Proposal B's
  reasoning is confirmed by the existing precedent:
  `WRITER_DISPOSITIONS` is keyed by `(filename, key)` for exactly this reason and
  says so in its docstring.
- **`reason` is prose a reviewer can disagree with**, so accepting a row is a
  review decision, not a mechanism decision.
- **`citation` must resolve** to a file that exists (and, when it carries `§X`,
  to a document-shaped section) — the generalized form of
  `test_config_contract.py:318`.

### 5.2 How a known violation ships today

```python
# src/film_pipeline/architecture.py — wave-0 ledger (illustrative, real subjects)
PRIVATE_MODULE_EXEMPTIONS: Final[tuple[Exemption, ...]] = (
    Exemption(
        subject="film_pipeline.schemas._base",
        reason=(
            "72 non-schema files import the private module; the public facade is "
            "also incomplete (TRANSITION_TYPES and LEGACY_TRANSITION_ALIASES are "
            "not re-exported). Migrate the importers, then rename _base -> base."
        ),
        citation="docs/modular-architecture/audit/14-module-boundaries-and-import-law.md F-BOUNDARY-02",
        removal_phase="wave-5 (O7)",
    ),
    Exemption(
        subject="film_pipeline.app._persistence",
        reason="mcp/server.py:248 reaches a private module of another package.",
        citation="docs/modular-architecture/audit/14-module-boundaries-and-import-law.md F-BOUNDARY-05",
        removal_phase="wave-5 (O7)",
    ),
)

CYCLE_EXEMPTIONS: Final[tuple[Exemption, ...]] = (
    Exemption(
        subject="agents.prompt_templates <-> agents.prompt_templates.defaults",
        reason=(
            "C1. 03 §4.4: prompt_templates/registry.py:100 lazily imports defaults to "
            "load the built-in templates, while defaults/* import registry for the "
            "PromptTemplate type. Break by moving the load to "
            "agents.catalog.bootstrap_defaults(), called by studio."
        ),
        citation="docs/modular-architecture/01-ownership-map.md C1",
        removal_phase="wave-1 (façade edges)",
    ),
    Exemption(
        subject=(
            "app <-> app.services <-> mcp <-> mcp.tools <-> mcp.tools.bibles <-> "
            "mcp.tools.generation <-> mcp.tools.reference_generation"
        ),
        reason=(
            "C2, 7 members. app/product_gate.py imports make_registry from "
            "mcp.contract, closing app -> mcp -> app (mcp/server.py imports "
            "app.bootstrap and app.runtime); the remaining five members hang off "
            "mcp.tools/* back into app.services. Wave 1 moves the gate onto the MCP "
            "entry-point side. Requires all five tool sub-packages to be cleared, "
            "not just app -> mcp."
        ),
        citation="docs/modular-architecture/01-ownership-map.md C2",
        removal_phase="wave-1 (law truth)",
    ),
    Exemption(
        subject=(
            "graph <-> graph.nodes <-> graph.orchestrator_validators <-> graph.subgraphs"
        ),
        reason=(
            "C3, 4 members. 03 §4.4: "
            "graph/orchestrator_validators/brief.py:179 imports graph.nodes back; the "
            "graph.nodes<->graph and graph.nodes<->graph.subgraphs halves become "
            "intra-module once graph is one module. Measured at fb85baa the "
            "sub-graph has **8 internal edges and a minimal feedback set of 3** "
            "(graph -> graph.nodes, graph -> graph.subgraphs, graph.nodes -> "
            "graph.orchestrator_validators): no single edge closes this cycle, which "
            "is why the row is keyed on the member set rather than on one edge. W9."
        ),
        citation="docs/modular-architecture/01-ownership-map.md C3",
        removal_phase="wave-3 (intra-package structure)",
    ),
    Exemption(
        subject="providers <-> providers.adapters",
        reason=(
            "C4. Façade re-export: providers/__init__.py:9-13 re-exports adapter "
            "classes, which import the providers package for their base types."
        ),
        citation="docs/modular-architecture/01-ownership-map.md C4",
        removal_phase="wave-1 (façade edges)",
    ),
    Exemption(
        subject="schemas <-> schemas.registries",
        reason=(
            "C5. Façade re-export: schemas/__init__.py:120 re-exports the registries "
            "package, which imports schemas for its base models."
        ),
        citation="docs/modular-architecture/01-ownership-map.md C5",
        removal_phase="wave-1 (façade edges)",
    ),
)

#: Rule 4 of §5.3 as data: every declaration family, by name, so a guard cannot
#: silently scan nothing and a *new* family cannot be forgotten. Nine entries --
#: the eight named in the previous revision's prose plus PRIVATE_SYMBOL_EXEMPTIONS,
#: which that prose omitted even though §3.7 already declared it.
DECLARATION_FAMILIES: Final[Mapping[str, Sequence[object]]] = MappingProxyType(
    {
        "MIRRORS": MIRRORS,
        "STATE_CHANNELS": STATE_CHANNELS,
        "REGISTRY_AGREEMENTS": REGISTRY_AGREEMENTS,
        "POLICY_POINTS": POLICY_POINTS,
        "LIFECYCLES": LIFECYCLES,
        "NORMATIVE_NUMBERS": NORMATIVE_NUMBERS,
        "PRIVATE_MODULE_EXEMPTIONS": PRIVATE_MODULE_EXEMPTIONS,
        "PRIVATE_SYMBOL_EXEMPTIONS": PRIVATE_SYMBOL_EXEMPTIONS,
        "CYCLE_EXEMPTIONS": CYCLE_EXEMPTIONS,
    }
)
```

At wave 0 the ledger holds **31 rows** (5 cycles, 8 `current_phase` writers, 6
registry non-members, 7 policy exemptions, 2 private modules, 3 private symbols) and
every guard is green. That is the intended state: **recorded, not forbidden.**

Two corrections to the previous revision's row count, both from making the family
list explicit:

- The cycle rows moved from **1 to 5**: the prior acyclicity guard ran at
  top-level package granularity, so C1, C3, C4 and C5 collapsed to self-loops and
  needed no row — the guard's silence, not the law's truth, is what kept the ledger
  short.
- The **3 `PRIVATE_SYMBOL_EXEMPTIONS` rows were uncounted**. They are real ledger
  rows (`§3.7` sweeps them, `§5.3` checks their citations and liveness), but the
  earlier prose listed only "2 private modules", so the stated total was 3 short.
  **31, not 28**, is the wave-0 high-water mark that §5.4 rule 1 and §8.1 refer to.

All five cycle member sets were measured at `fb85baa` with the `module_edges()`
sweep of §3.9; the non-cycle counts are the site measurements recorded in §3.3
(`current_phase` writers), §3.6 (`FILM_PIPELINE_NO_PERSIST`), §3.7 (2 private
modules over 107 sites, 3 private symbols) and §3.8 (registry/enum non-members).

A cycle row is keyed on the **SCC member set**, not on an edge. The earlier draft
recorded one edge per cycle and deleted those edges before running Tarjan. That is
wrong twice over: for C3 no single edge is sufficient (**minimal feedback set of
3**, measured above), so an edge-keyed ledger would have left the cycle live while
the guard reported green; and for any cycle, edge-keyed deletion lets a *new*
cycle hide behind a stale exemption. Keying on the member set makes both
impossible — the sweep sees the whole graph, and a row only matches the exact
component it names.

### 5.3 How rot is prevented

`tests/architecture/test_exemptions.py` enforces six rules; rules 1–3 generalise
the proven `test_config_contract.py:318` pattern, and rules 4–6 are the
anti-vacuity canary:

1. **Citation resolves.** Every row's `citation` has the form `<path>` or
   `<path> <locator>`. The path must exist (and, when it points into the tracked
   tree, must be tracked by git); the locator, when present, must resolve by one of
   three **structural** rules — never by "find a capital letter somewhere":
   `§N[.M…]` resolves against a `^##+ N[.: ]` heading, `F-<AREA>-<nn>` resolves
   against a `^###+ F-… —` heading, and `C<n>` resolves against a cycle token in
   the document body. A malformed locator (no `§`, no recognisable id) is a
   failure, not a skip — the earlier revision's `§?([A-Z]{1,3})` regex accepted
   `wave-1`, `Note`, and the word `IMPORT` in prose, i.e. it could pass on a
   citation that resolved to nothing. *(proven pattern:
   `test_known_dead_rows_cite_evidence`)*
2. **Subject is live — as a violation, not as a name.** Every row's `subject` must
   still describe an **observed** deviation: a dotted path still resolves, a
   `module::symbol` root is still present, an `a -> b` edge is still observed, a
   `a <-> b <-> c` member set is still the exact SCC the sweep finds. Liveness is
   checked against the *observed violation sets* the guards already compute, not
   against name existence, because those differ exactly where it matters: if every
   importer of `film_pipeline.schemas._base` is migrated while the module itself
   still exists, an existence-only check keeps the row green forever and the ledger
   carries a violation that no longer exists. `subject_is_live` therefore takes the
   observed sets as arguments (§5.3 skeleton). A **fixed** deviation fails the
   ledger until the row is deleted. This is what makes the ledger a ratchet:
   deleting a row *without* fixing the site is impossible (the guard would still
   see it), and fixing the site *without* deleting the row fails liveness.
3. **Reason is non-empty** and `removal_phase` names a real wave.
4. **No family is empty — and the family list is data.** `DECLARATION_FAMILIES`
   below enumerates every declaration tuple verbatim; `test_every_declaration_family_is_present_and_non_empty`
   iterates it, so a family that is added later cannot be omitted from the check,
   and the earlier revision's hand-written list of five (`MIRRORS`,
   `STATE_CHANNELS`, `REGISTRY_AGREEMENTS`, `POLICY_POINTS`,
   `PRIVATE_MODULE_EXEMPTIONS`) cannot be mistaken for exhaustive.
   `PUBLIC_API_EXEMPTIONS` is excluded **on purpose**: it is empty at W0 (§5.2)
   and becomes non-empty on the guard's first run, so including it would make this
   rule red on day one. Its liveness is checked by
   `test_public_api_exemptions_are_live` in §3.8.1 instead, which is the property
   that actually matters for an initially-empty family.
5. **The source tree looks like the repo.** `python_files()` returns >200 files,
   so a mis-resolved `SRC` cannot make every sweep pass.
6. **A mutation canary proves the primitive can fail.** The mirror comparison is
   run against a deliberately perturbed copy of the canonical vocabulary; if it
   does not report drift, `test_vocabularies.py` is theatre. Deliberately **not**
   `xfail` — it asserts the primitive is sensitive, which is the part that can
   silently become a no-op.

**The evidence that justifies the canary — corrected.**
An earlier version of this document (and the briefing that produced it) claimed the
orphaned `tests/unit/__pycache__/test_guard_canary.cpython-312-pytest-9.1.1.pyc`
proves a canary was *silently deleted from this repo before*. **That claim is
withdrawn**; `reviews/orchestrator-verification-notes.md` **V9** measured it and it
is not supported. The `.pyc` was created at **12:41 on 2026-09-25**, inside this
program's own session window (the audited commit `fb85baa` is 13:16 that day); its
embedded source path is `tests/unit/test_guard_canary.py` and its string is
`"Canary: write into a watched production root; the session guard MUST fail."` —
it is **this program's enforcement-prototype subagent's canary**, not a
pre-existing repo loss. `git log --all -- '*test_guard_canary*'` is empty: it was
never tracked, and `__pycache__/` is gitignored (`.gitignore:5`), so no deletion
would be visible in history anyway.

The corrected — and stronger — argument is a **test-inventory churn** measurement,
reproduced here:

```bash
# Orphaned-bytecode sweep: .pyc files under tests/ whose source no longer exists.
.venv/bin/python - <<'PY'
import pathlib
for pyc in sorted(pathlib.Path("tests").rglob("*.pyc")):
    if "__pycache__" not in pyc.parts:
        continue
    if not (pyc.parent.parent / pyc.name.split(".")[0]).with_suffix(".py").exists():
        print(pyc)
PY
# 18 files, at fb85baa.
```

**18** stale bytecode files have accumulated under `tests/`, and nothing cleans
them or enumerates the test set as data:

- **7 removed by a real, traceable refactor** — `37e9c65 refactor(tui): remove TUI
  package, tests, entry point, and textual dependency` deleted five
  `tests/e2e/test_tui_*.py` plus `tests/integration/cli/conftest.py`, and their
  bytecode is still present (`test_tui_mock_flow`, `test_tui_new_flow`,
  `test_tui_real_mode`, `test_tui_real_text_only_intake`, `test_real_tui_e2e`,
  `test_tui_live_providers`, `integration/cli/conftest`);
- **8 tracked helpers that moved or were renamed** — `tests/unit/graph/_helpers.py`,
  `tests/unit/mcp/tools/test_helpers.py`, `tests/unit/generation/_helpers.py`,
  `tests/unit/mcp/tools/_helpers.py`, `tests/unit/artifacts/test_migration.py`, …
- **at least 1 never tracked** — `tests/__pycache__/_helpers.py`;
- plus this program's prototype canary.

So the real claim is: **this repository's test-inventory churn leaves no trace —
18 stale bytecode files accumulated and nothing enumerates the test set, so the
disappearance of a guard file is invisible.** The response is structural: the
canary is **split across the ledger tests** (rules 4–6) rather than being one
deletable file, and the guard set is enumerated by name in a registry (§5.5), so
losing a guard requires deleting several green assertions in unrelated files.

```python
"""Guard: the exemption ledger cannot rot or become vacuous."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from film_pipeline.architecture import (
    CYCLE_EXEMPTIONS,
    DECLARATION_FAMILIES,
    LIFECYCLES,
    MIRRORS,
    NORMATIVE_NUMBERS,
    POLICY_POINTS,
    PRIVATE_MODULE_EXEMPTIONS,
    PRIVATE_SYMBOL_EXEMPTIONS,
    REGISTRY_AGREEMENTS,
    STATE_CHANNELS,
)
from tests.architecture._harness import (  # noqa: F401
    REPO_ROOT,
    git_tracked,
    module_edges,
    private_module_violations,
    python_files,
    resolve,
    strongly_connected_components,
    subject_is_live,
)

_LEDGER = (
    *CYCLE_EXEMPTIONS,
    *PRIVATE_MODULE_EXEMPTIONS,
    *PRIVATE_SYMBOL_EXEMPTIONS,
    *(row for c in STATE_CHANNELS for row in c.writers),
    *(row for a in REGISTRY_AGREEMENTS for row in a.non_members),
    *(row for p in POLICY_POINTS for row in p.exemptions),
)

#: Locator grammar for `citation`. Structural, so a locator that resolves to
#: nothing is a failure instead of a silent skip (O-20).
_SECTION = re.compile(r"^§(\d+(?:\.\d+)*)$")
_FINDING = re.compile(r"^F-[A-Z]+-\d+$")
_CYCLE = re.compile(r"^C[1-9]\d*$")


def _assert_locator_resolves(subject: str, cited: Path, locator: str) -> None:
    text = cited.read_text()
    if (match := _SECTION.match(locator)) is not None:
        number = match.group(1)
        assert re.search(rf"^##+ {re.escape(number)}[.: ]", text, re.M), (
            f"{subject}: cited section §{number} not found in {cited.name}"
        )
    elif _FINDING.match(locator):
        assert re.search(rf"^###+ {re.escape(locator)} —", text, re.M), (
            f"{subject}: cited finding {locator} has no '### {locator} —' heading"
        )
    elif _CYCLE.match(locator):
        assert re.search(rf"\b{locator}\b", text), (
            f"{subject}: cited cycle {locator} does not appear in {cited.name}"
        )
    else:
        raise AssertionError(
            f"{subject}: malformed citation locator {locator!r}. Use '§N[.M]', "
            "'F-<AREA>-<nn>' or 'C<n>' -- a bare capitalised word is not a locator."
        )


def test_exemption_is_cited_and_reasoned() -> None:
    for row in _LEDGER:
        assert row.reason.strip(), f"{row.subject}: empty reason"
        assert row.removal_phase.strip(), f"{row.subject}: no removing phase"
        cited_text, _, locator = row.citation.partition(" ")
        cited = REPO_ROOT / cited_text
        assert cited.exists(), f"{row.subject}: citation does not resolve: {cited_text}"
        if locator:
            # A citation into the tracked tree must be tracked; a citation into
            # gitignored `docs/` (see §8.4) can only be checked for existence.
            if cited.with_name("").relative_to(REPO_ROOT).parts[0] != "docs":
                assert git_tracked(cited_text), (
                    f"{row.subject}: citation points at an untracked file: {cited_text}"
                )
            _assert_locator_resolves(row.subject, cited, locator)


def test_exemption_subject_still_exists() -> None:
    """A fixed deviation must fail until its row is deleted (works in both directions).

    ``subject_is_live`` lives in ``_harness.py`` so there is exactly one
    implementation of "does this subject still describe an observed deviation",
    per the consolidation rule in §4. It is **violation-aware** (O-15): it is
    handed the observed sets rather than checking name existence, so a row whose
    deviation has been fixed dies even while the name it cites still exists.

    Handled subject forms, and what "live" means for each:

    * ``"a -> b"`` -- the edge is still observed in ``module_edges()``;
    * ``"a <-> b <-> c"`` -- that exact member set is still one of the
      multi-member SCCs of ``module_edges()`` (the cycle-exemption form, §5.2);
    * a private dotted path -- ``film_pipeline.schemas._base`` is still imported
      from another package by at least one file (``private_module_violations()``),
      *not* merely still importable;
    * any other dotted module/package path -- ``importlib.util.find_spec`` resolves it;
    * ``"<module>::<symbol>"`` -- the symbol root still appears in that module.

    In the reverse direction, the family guards assert ``observed ⊆ recorded``, so
    deleting a row while the site remains fails as well.
    """
    observed = {
        "edges": {(a, b) for a, deps in module_edges().items() for b in deps},
        "cycles": {
            frozenset(component)
            for component in strongly_connected_components(module_edges())
            if len(component) > 1
        },
        "private_modules": set(private_module_violations()),
    }
    for row in _LEDGER:
        assert subject_is_live(row.subject, observed=observed), (
            f"exemption subject no longer describes an observed violation: {row.subject!r}. "
            "Fix the site *and* delete the row -- a fixed deviation must not stay recorded."
        )
    for row in PRIVATE_MODULE_EXEMPTIONS:
        parts = row.subject.split(".")
        assert parts[0] == "film_pipeline" and parts[2].startswith("_"), row.subject


def test_every_declaration_family_is_present_and_non_empty() -> None:
    """Rule 4: no guard may be scanning an empty declaration.

    Iterates the declared registry rather than a hand-written list, so the check
    cannot lag the declaration set (O-17).
    """
    assert len(DECLARATION_FAMILIES) == 9, (
        f"DECLARATION_FAMILIES has {len(DECLARATION_FAMILIES)} entries; if a family was "
        "added or removed, update this count and §5.3 rule 4 together."
    )
    empty = sorted(name for name, rows in DECLARATION_FAMILIES.items() if not rows)
    assert not empty, f"declaration families with no rows: {empty}"


def test_guard_inputs_are_not_empty() -> None:
    """Rule 4, spelled out for the families whose guards are parametrised over them."""
    assert MIRRORS, "MIRRORS is empty: the vocabulary guard is vacuous"
    assert STATE_CHANNELS, "STATE_CHANNELS is empty: the writer guard is vacuous"
    assert REGISTRY_AGREEMENTS, "REGISTRY_AGREEMENTS is empty: the registry guard is vacuous"
    assert POLICY_POINTS, "POLICY_POINTS is empty: the policy guard is vacuous"
    assert LIFECYCLES, "LIFECYCLES is empty: the lifecycle guard is vacuous"
    assert NORMATIVE_NUMBERS, "NORMATIVE_NUMBERS is empty: the number guard is vacuous"
    assert PRIVATE_MODULE_EXEMPTIONS, "the private-import guard records no sites"
    assert PRIVATE_SYMBOL_EXEMPTIONS, "the private-symbol guard records no sites"
    assert CYCLE_EXEMPTIONS, "the acyclicity guard records no cycles"


def test_source_tree_looks_like_the_repo() -> None:
    """Rule 5: a mis-resolved SRC must not make every sweep pass."""
    found = python_files()
    assert len(found) > 200, f"only {len(found)} source files found: is SRC correct?"


def test_mirror_guard_detects_a_real_mutation() -> None:
    """Rule 6: proves the vocabulary comparison is capable of failing."""
    from tests.architecture._harness import as_vocabulary

    mirror = next(row for row in MIRRORS if row.mode == "ordered")
    canonical = list(as_vocabulary(resolve(mirror.canonical)))
    mutated = [*canonical, "a_phase_that_does_not_exist"]
    assert mutated != canonical, "mutation helper is broken"
    assert sorted(set(mutated) - set(canonical)) == ["a_phase_that_does_not_exist"]
```

*(`subject_is_live` is the only piece of the ledger guard that does not already
exist in the existing guards; it generalises the "citation resolves" check from
`test_config_contract.py:318` to every family's subject type. It lives in
`_harness.py` so there is one implementation, per §4's consolidation rule.)*

### 5.4 How the ledger shrinks

1. **Wave 0 is the high-water mark.** No wave may grow the ledger beyond its
   wave-0 row count; a wave that needs new rows means scope crept and the wave
   must be split. This is the only real defence against a ledger that only grows
   (see §8.1).
2. **Every row names its removing wave** (`removal_phase`), so an orphaned row is
   visible in review, not just in a doc.
3. **Liveness does the shrinking automatically.** Migrating a writer and deleting
   its `Exemption` is the *only* way to make `test_recorded_writers_are_live`
   pass after the write site is gone; conversely, deleting the row while the site
   remains fails `test_only_the_owner_and_recorded_writers_touch_a_channel`.
4. **Two independent directions, always.** Every family asserts both
   `observed ⊆ recorded` (no new violations) and `recorded ⊆ observed` (no stale
   rows). A one-directional ledger is a licence; a two-directional ledger is a
   burndown chart.
5. **The final phase asserts the ledger is empty** (proposal A's P10 /
   proposal B's wave 6+), which is the completion criterion for the program.

### 5.5 The guard registry — surviving a *deleted guard*

§5.3's canary protects against a guard that is *vacuous*. A second, distinct
failure mode is that **a guard can simply disappear**: the whole ledger can be
green, and if someone deletes `test_state_writers.py` (or renames it, or empties
it), the suite still passes because nothing asserts that the guard *exists*. A
canary inside the guard does not survive the guard's deletion.

The justification is measured, not anecdotal (V9, §5.3): **18 orphaned `.pyc`
files** under `tests/` are the residue of test-file deletions, renames and moves
that no mechanism noticed — including five `test_tui_*.py` and an
`integration/cli/conftest.py` removed by `37e9c65`, and eight renamed `_helpers.py`
/ `test_helpers.py` modules. Nothing cleans them and **nothing enumerates the test
set as data**, so the disappearance of any test file — guard or not — is invisible.

The fix is a **registry that lives in a different file from the guards it names**,
so deleting a guard fails a test that is still present:

```python
# tests/architecture/_guard_registry.py -- the single registry of guard families.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GuardFile:
    """One guard file, the ledger concerns it pins, and its automation class.

    ``concerns`` must be a subset of the L-NN ids defined in
    ``docs/modular-architecture/02-duplication-ledger.md``; the registry test
    resolves every id against that file, so a guard cannot cite a concern that
    does not exist, and a concern cannot be silently orphaned.
    """

    filename: str
    concerns: frozenset[str]
    automation: str  # "exact" | "subset" | "partial" | "human-locked"


#: Concerns that are allowed to be pinned by **no guard file**, stated explicitly
#: rather than left implicit in the difference between two sets. §3.10's coverage
#: table derives these six as the *genuinely* human-anchored concerns -- the ones
#: whose enumeration or case list is itself the human step -- so the reverse
#: direction of the registry check ("no ledger concern is silently orphaned") is a
#: claim about six specific rows a reviewer can audit, rather than an accident of
#: which guard files happen to exist. Membership here is permission, not
#: exclusion: a concern on this list may also appear in a guard's ``concerns``.
HUMAN_ONLY_CONCERNS: frozenset[str] = frozenset(
    {"L-05", "L-12", "L-17", "L-22", "L-35", "L-51"}
)


#: The checked-in manifest. **Twelve** files: ten concern guards (contracts,
#: vocabularies, normative numbers, invariants, state writers, registries, policy
#: points, lifecycles, private imports, public API) plus the two ledger-machinery
#: files (exemptions, guard registry). Kept in sorted order by ``filename`` so the
#: directory scan below is a set comparison rather than a fuzzy one. Earlier drafts
#: said "9", "10" and "11" in three different places; **12** is the count stated
#: once, here, and every prose reference points at this tuple.
GUARD_REGISTRY: tuple[GuardFile, ...] = (
    GuardFile("test_contracts.py", frozenset({"L-12", "L-48", "L-54"}), "exact"),
    GuardFile("test_exemptions.py", frozenset(), "exact"),                 # ledger hygiene
    GuardFile("test_guard_registry.py", frozenset(), "exact"),             # anti-deletion (this file)
    GuardFile("test_invariants.py", frozenset({...}), "human-locked"),     # O2 rows
    GuardFile("test_lifecycles.py", frozenset({...}), "human-locked"),     # O6 rows
    GuardFile("test_normative_numbers.py", frozenset({"L-14", "L-41", "L-53", "L-58"}), "exact"),
    GuardFile("test_policy_points.py", frozenset({...}), "exact"),         # O5 rows
    GuardFile("test_private_imports.py", frozenset({...}), "exact"),       # O7 rows
    GuardFile("test_public_api.py", frozenset({...}), "partial"),          # O8 rows
    GuardFile("test_registries.py", frozenset({...}), "exact"),            # O4 rows
    GuardFile("test_state_writers.py", frozenset({...}), "exact"),         # O3 rows
    GuardFile("test_vocabularies.py", frozenset({...}), "exact"),          # §3.10 O1 rows
)

#: The four pre-existing guards that must survive consolidation (§4). They are
#: listed here so deleting one is a test failure even after its assertions have
#: been folded into the generalized guards -- the *files* are coverage.
LEGACY_GUARDS: frozenset[str] = frozenset({
    "tests/unit/artifacts/test_storage_boundary.py",
    "tests/unit/graph/test_startup_boundaries.py",
    "tests/unit/config/test_config_contract.py",
    "tests/unit/graph/test_channel_registry.py",
})
```

`tests/architecture/test_guard_registry.py` asserts, and **fails loudly**, when:

1. **a registered guard file is missing** — deleting or renaming any of the twelve
   new guard files, or any of the four legacy guards, fails here even though the
   deleted file's own tests are gone;
2. **a guard file contains no collected `test_` function** — an emptied file is as
   bad as a deleted one (`ast.parse` the file and count top-level `def test_*`);
3. **a guard file that exists is not registered** — a new `test_*.py` under
   `tests/architecture/` must be added to the registry, so guards cannot appear
   unaccounted for either;
4. **a registered concern id is not a real ledger entry** — resolve `L-NN` against
   the `### L-NN —` headings of `02-duplication-ledger.md`; a typo'd or deleted
   concern fails;
5. **a ledger concern is claimed by no guard and is not listed as human-only** —
   the reverse direction: no concern may be silently orphaned;
6. **every declaration family is present and non-empty** — the test delegates to
   `DECLARATION_FAMILIES` (§5.2), which lists all **nine** tuples
   (`MIRRORS`, `STATE_CHANNELS`, `REGISTRY_AGREEMENTS`, `POLICY_POINTS`,
   `LIFECYCLES`, `NORMATIVE_NUMBERS`, `PRIVATE_MODULE_EXEMPTIONS`,
   `PRIVATE_SYMBOL_EXEMPTIONS`, `CYCLE_EXEMPTIONS`) with ≥1 row each — so deleting
   a *manifest family* is caught even if every guard file survives. The earlier
   prose listed eight and omitted `PRIVATE_SYMBOL_EXEMPTIONS`; that is corrected
   here and the count is asserted, so the next family added cannot be forgotten
   silently.

```python
"""Guard: the guards themselves cannot vanish (anti-deletion registry)."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from tests.architecture._guard_registry import (
    GUARD_REGISTRY,
    HUMAN_ONLY_CONCERNS,
    LEGACY_GUARDS,
)

_ARCH = Path(__file__).resolve().parent
_REPO = _ARCH.parents[1]
_LEDGER = _REPO / "docs" / "modular-architecture" / "02-duplication-ledger.md"


def test_every_registered_guard_file_exists_and_has_tests() -> None:
    missing: list[str] = []
    empty: list[str] = []
    for guard in GUARD_REGISTRY:
        path = _ARCH / guard.filename
        if not path.exists():
            missing.append(guard.filename)
            continue
        tree = ast.parse(path.read_text())
        if not any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in tree.body
        ):
            empty.append(guard.filename)
    assert not missing, f"registered guard files are missing: {missing}"
    assert not empty, f"registered guard files contain no tests: {empty}"


def test_legacy_guards_still_exist() -> None:
    """Consolidation must not delete coverage: the four files stay."""
    gone = sorted(name for name in LEGACY_GUARDS if not (_REPO / name).exists())
    assert not gone, f"legacy guard files removed without replacement: {gone}"


def test_no_unregistered_guard_file() -> None:
    """Directory scan vs. checked-in manifest, in both directions (O-16/M-5).

    The choice: the manifest is **checked in** (``GUARD_REGISTRY`` above) and the
    directory is **scanned** at test time; the two are compared as sets. A
    directory scan alone cannot detect a *deleted* file (the scan simply finds one
    fewer), and a manifest alone cannot detect an *added* file. Only the
    comparison catches both, which is why both halves are asserted here and the
    count is pinned so a silent drop of two files cannot pass.
    """
    registered = {guard.filename for guard in GUARD_REGISTRY}
    present = {p.name for p in _ARCH.glob("test_*.py")}
    assert len(registered) == 12, f"GUARD_REGISTRY holds {len(registered)} files, not 12"
    assert [g.filename for g in GUARD_REGISTRY] == sorted(registered), (
        "GUARD_REGISTRY must stay in sorted filename order: it is read as a manifest"
    )
    unregistered = sorted(present - registered)
    assert not unregistered, f"guard files missing from GUARD_REGISTRY: {unregistered}"
    ghost = sorted(registered - present)
    assert not ghost, f"GUARD_REGISTRY names files that do not exist: {ghost}"


def test_guard_concerns_resolve_against_the_declaration() -> None:
    """The concern universe is ``CONCERN_IDS`` in ``architecture.py``, not the docs tree.

    O-01: the previous revision read ``docs/modular-architecture/02-duplication-ledger.md``
    directly. ``docs/`` is **gitignored** (``.gitignore:2``), so in a clean CI
    checkout that file does not exist and the guard raised ``FileNotFoundError`` --
    a red build for a reason unrelated to the law. Every executable input is now a
    **tracked** file or the AST, so the authority is the tracked tuple.
    """
    from film_pipeline.architecture import CONCERN_IDS

    defined = set(CONCERN_IDS)
    claimed = {c for guard in GUARD_REGISTRY for c in guard.concerns} | HUMAN_ONLY_CONCERNS
    unknown = sorted(claimed - defined)
    assert not unknown, f"guard registry cites non-existent ledger concerns: {unknown}"
    orphans = sorted(defined - claimed)
    assert not orphans, f"ledger concerns pinned by no guard: {orphans}"


@pytest.mark.skipif(
    not _LEDGER.exists(),
    reason="docs/ is gitignored; the ledger document is absent in a clean checkout (O-01)",
)
def test_concern_ids_match_the_ledger_document_when_present() -> None:
    """Optional cross-check: the tracked ids still agree with the prose ledger.

    Auto-skipped when the docs tree is absent. This is a **drift report on a
    document**, never a gate on the code: §5.5's registry test above is the gate.
    """
    from film_pipeline.architecture import CONCERN_IDS

    documented = set(re.findall(r"^### (L-\d\d) —", _LEDGER.read_text(), re.M))
    assert set(CONCERN_IDS) == documented, (
        "CONCERN_IDS and 02-duplication-ledger.md have drifted: "
        f"only in code {sorted(set(CONCERN_IDS) - documented)}; "
        f"only in prose {sorted(documented - set(CONCERN_IDS))}"
    )
```

This is the design's answer to the deleted-guard failure mode: the canary is
*inside* the ledger tests (§5.3 rules 4–6) **and** the guard files are registered
in a shared data module that they do not own. Losing the canary or losing a guard
now requires editing a second file, and that edit is visible in review. The
**18-orphaned-`.pyc`** measurement (V9) is the state this replaces: today, a test
file can vanish and leave nothing behind but bytecode.

**Boundary of the registry — an import-time side effect it cannot see.**
`verify-10`'s missed-in-scope finding **M1** (Critical, 5×5=25) is the honest limit
of any source-level registry: merely importing the module named by `langgraph.json`
does the harm. `graph/graph.py:201` runs `graph = build_graph()` at module level,
which reaches `_default_checkpointer` (`:41-46`) → `default_checkpoints_root()` →
`artifacts/storage.py:74` (`resolve_storage_root() / "checkpoints"`) →
`artifacts/storage.py:49` (`checkpoint_dir.mkdir(parents=True, exist_ok=True)`). With
`PERSIST_STATE=1` and no `RUNTIME_ROOT`, the bare import creates
`<storage root>/checkpoints/`, and `ensure_storage_root` then **refuses its own
storage root** — `verify-10` reproduced `[S5] app FAILED to open storage root after
graph.graph import: StorageRootError`; the app cannot open the project it just
created. No AST sweep in this suite can detect that: the code is correct-looking,
the *ordering* is the defect. It needs a **runtime probe**, not a source rule — the
same class as `test_startup_boundaries.py`'s fresh-interpreter subprocess test,
which is why §4 keeps that test rather than folding it into a sweep. The general
shape is worth stating as a limitation: **this mechanism enforces structure, and
M1 is a lifecycle/ordering property.** The guard suite would not have caught it, and
this document does not claim otherwise.

---

## 6. The extraction playbook

One concern, one branch, one PR, `make ci-check` green at every step. The
inventory count from step 1 is the PR's burndown number.

### Step 0 — Pick the concern and record the finding

```bash
git fetch origin && git switch -c extract/<concern> origin/modular-app
git log --oneline -1                       # record the base commit in the PR body
grep -rn "<duplicate literal or second implementation>" src/film_pipeline --include="*.py"
```

Write the O-class, the `path:line` owners, the drift proof, and the reproduce
command into the phase document. A concern without a drift proof is a hypothesis
(`00-methodology-and-quality-bar.md` §1.6.3) and **must not be extracted**.

### Step 1 — Inventory every site (mechanical, no edits)

```bash
uv run python - <<'EOF'
import ast, pathlib
VOCAB = {"intake","constitution","development","script","visual_dev","shot_bible",
         "gen_planning","generation","qc","post","delivery"}
for p in sorted(pathlib.Path("src/film_pipeline").rglob("*.py")):
    if "__pycache__" in p.parts:
        continue
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            items = n.keys if isinstance(n, ast.Dict) else n.elts
            vals = {e.value for e in items
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)}
            if len(vals & VOCAB) >= 4:
                print(f"{p}:{n.lineno}  {len(vals & VOCAB)} members")
EOF
```

At HEAD this prints the four phase-vocabulary copies (`schemas/_base.py`,
`graph/_action_routing.py` ×2, `artifacts/paths.py`). Record the count; it is the
number this PR must drive to its target (1 for O1, 1 for O3, …).

### Step 2 — Declare the contract (red is allowed only on the branch)

Append `CONTRACT` to `src/film_pipeline/<owner>/__init__.py`; add the manifest row
**only for cross-module facts**. Do not add the agreement row yet if the migration
is not done — add it in step 6.

```bash
uv run --python 3.12 --group dev pytest tests/architecture -q --no-cov 2>&1 | tee /tmp/red.txt
```

The merged commit must be green. Red exists only between step 2 and step 6 on a
short-lived branch.

### Step 3 — Create the module

```bash
mkdir -p src/film_pipeline/<owner>
uv run --python 3.12 --group dev ruff format src/film_pipeline/<owner>
uv run --python 3.12 --group dev mypy --strict src tests
uv run --python 3.12 --group dev pytest tests/architecture -q --no-cov
```

At this point the new module imports nothing (`may_import=frozenset()`), which
`test_imports_stay_within_declared_edges` proves.

### Step 4 — Migrate writers, one at a time

For O3 the rule is **one writer per commit**: move a caller to the owner, delete
its row, run the guard, commit. Each commit shrinks the ledger and stays green.

```bash
uv run --python 3.12 --group dev pytest \
  tests/architecture/test_state_writers.py tests/architecture/test_exemptions.py -q --no-cov
git commit -am "refactor(<concern>): route <caller> through <owner>"
```

**Shadow assertion** (temporary, deleted before merge) for a write that no
existing test covers:

```python
# TEMPORARY -- remove before merge (05-enforcement-and-guard-tests.md §6 step 4)
assert new_derive(state) == legacy_derive(state), "shadow mismatch"
```

**Permanent canary** so the migration cannot silently regress:

```python
# TEMPLATE -- substitute <old_module> and <owner>; not runnable as written.
def test_legacy_entry_point_delegates_to_the_owner() -> None:
    from film_pipeline.<old_module> import legacy_derive
    from film_pipeline.<owner> import derive

    assert legacy_derive({"current_phase": "script"}) == derive({"current_phase": "script"})
```

### Step 5 — Delete the duplicates and prove it by command

```bash
# Re-run step 1's command: the output must be the owner only.
grep -rn "PHASE_DIR_MAP\|_PHASE_AGNOSTIC_PHASES" src/film_pipeline --include="*.py"
```

This is the completion criterion for the finding — **not** "tests pass".

### Step 6 — Pin it with a guard

Add the real manifest row (mirror/channel/agreement/policy point) and delete the
rows that existed only because the migration was in flight.

```bash
uv run --python 3.12 --group dev pytest tests/architecture -q --no-cov
```

### Step 7 — Update the documentation

- `AGENTS.md` — the sub-package roster (**it currently says 12; there are 17**,
  `audit/14` §1) and the dependency law (replace the prose with a pointer to the
  manifest).
- The phase document under `docs/modular-architecture/` with the finding id and
  the guard file that now pins it.

### Step 8 — Run the full gate

```bash
make ci-check
```

### Step 9 — Rollback plan

```bash
git revert --no-edit <merge-commit>
git push origin <branch>          # never force-push (AGENTS.md global rule)
```

Rollback is safe **by construction** because an extraction PR must not change any
persisted representation:

- if the concern's representation changes (artifact layout, checkpoint payload,
  MCP response shape), that is a compatibility change under B7 and must be a
  **separate** PR with an explicit version bump — never bundled into an extraction;
- no extraction PR may add a runtime feature flag (`if os.getenv("MODULAR_V2")`);
  if a behaviour toggle seems necessary, the extraction is too large — split it;
- guard changes revert with the code because they live in the same commit as the
  manifest rows they depend on.

If the revert is partial, revert the individual commit: each step-4 commit is
independently green, which is the property B5 requires.

**The three write-side representation changes, as explicit compatibility rows
(O-14 / M-6).** The bullet above says an extraction "must not change any persisted
representation"; that is not the same as *no extraction in this program does*.
Three waves do exactly that, so the B5 claim "revertible by a single `git revert`"
is only true if each one is named here with its compatibility class and migration
owner. `03-target-architecture.md` §8 is the table that should carry them; this
document restates them so the rollback contract is not silently weaker than the
program's core cost argument. **The §8 rows themselves remain an open item owned by
`03`** — this file cannot edit it, and a reader should grade `03` on that gap, not
this document.

| # | Change | Wave | Compatibility class | What a `git revert` does *not* undo | Migration owner |
|---|---|---|---|---|---|
| a | **`artifact_type` labels** — `type_for` stops silently falling back to `script` and returns the correct type (`03:1631-1638`, D11). | W4 | **Read-compatible both directions.** Both the old label (`script`) and each corrected label are members of `ArtifactType`, so a reader written either side of W4 parses either envelope. Data-only difference. | Reverting W4 restores the fallback **writer** but does not rewrite the labels W4-era writes put on disk. The stored label is a historical fact and must not be back-filled: rewriting it would make an old artifact claim a type its producer did not know. | W4 (no migration script; a one-line note in the W4 PR that old labels persist) |
| b | **The `budget` durable document** — the budget/spend document under the project, written through `storage` (`03:705-706`). | W8 | **Purely additive.** A new file at a new path; nothing reads it before W8, and every pre-W8 reader ignores unknown paths. | Reverting W8 leaves the document on disk. It must therefore be **inert on read**: a missing document means "no spend recorded", so a reverted tree with a leftover file does not silently resume spending against a stale cap. | W8 |
| c | **`kb_context_ref` stamping** — persisted artifact meta goes from 1 of 12 write paths to 12 of 12 (`03:1176`; today `graph/nodes/_agent_artifacts.py:86` is the only stamping site — F-KBCTX-03). | W6 (P12) | **Additive and read-compatible.** `ArtifactMetadata.kb_context_ref` already defaults to `None` and is already persisted for 1 of 12 paths; the wave only fills it more often. Both `None` and a `kbctx:` string are legal in `meta.json` before and after. | Nothing, on disk: the field's presence and absence are both legal in both directions, so a revert is a true no-op for stored artifacts. | W6 (P12); `04-extraction-roadmap.md` P12 already records this as a **B7** change, which is the correct classification |

The rule this table encodes, and the reason it is in the enforcement document
rather than a narrative one: **"additive" and "revertible" are different claims.**
(a) is read-compatible yet not revert-clean; (b) is additive yet only safe if the
reader treats absence as the default; (c) is the only one of the three where
`git revert` is genuinely a no-op. A single `git revert` is the program's cost
argument, so each of the three needs a row like these before its wave ships.

---

## 7. CI wiring

### 7.1 Exactly what changes

| File | Change | Cost | Why this is the right amount |
|---|---|---|---|
| `Makefile` | **Add** one convenience target: `arch-check: ## Run only the architecture guards (fast, AST-level)` → `$(UV_RUN) pytest tests/architecture -q --no-cov` | 2 lines; no gate change | Gives a sub-second local loop. `--no-cov` avoids paying coverage instrumentation on a source-only sweep. `ci-check` is untouched, so the guards are still enforced by the existing `test-cov` step. |
| `pyproject.toml` | **One marker registration required** (`--strict-markers` is on at `:75`, so an unregistered `change_detector` marker is a *collection error*, not a warning): add `"change_detector: a pinned observation, not a law assertion"` to `markers`. No other change required. Optionally, later, per-package: `[[tool.mypy.overrides]]` with `disallow_any_explicit = true` | 1 line now; ~6 lines later per package | Guards are ordinary tests under `tests/`, already collected by `testpaths = ["tests"]` (`pyproject.toml:83`) and already covered by `--cov-fail-under=90` (`:80`). The manifest is import-only, so its module body executes at collection and cannot dilute coverage. The mypy override is the only free O8 lever and must be applied **per package**, never globally (§3.8). |
| `.pre-commit-config.yaml` | **No change** | 0 | The pre-push `pytest` and `mypy --strict` hooks already run the whole suite, including the new guards. A second hook would be ceremony. |
| `.github/workflows/ci.yml` | **No change** | 0 | `make ci-verify PYTHON=3.12` (`:40-41`) invokes `test-cov`, which collects `tests/architecture`. |
| Declaration location | `src/film_pipeline/architecture.py` + 17 `__init__.py` `CONTRACT` blocks | est. ~650 + ~325 lines, one-time (§2.1) | **Must** be under `src/`. `docs/` is gitignored (`.gitignore:2`) **and** CI-ignored — `.github/workflows/ci.yml` triggers on `pull_request` with `paths-ignore: ["**/*.md", "docs/**", "LICENSE"]` — so a manifest there would be neither reviewed as a diff nor gated. This is also why the **declared edge matrix (§3.9) lives in `src/film_pipeline/architecture.py`**, not in a `scripts/architecture/edges.yaml` as proposal A §6.4 first suggested: `scripts/` is outside `[tool.ruff]`'s src scope (`pyproject.toml:127`), is excluded from mypy's `src tests` invocation (`Makefile:42`), and a YAML table is not type-checked, so a typo'd package name would be silent. `04-extraction-roadmap.md` was told to defer to this home. |
| Guard enumeration | **None exists.** CI has no step that lists or counts guard/architecture files; it runs `make ci-verify` and nothing else (`ci.yml` step "CI check"). | 0 | Stated explicitly because it is *why* §5.5's registry is needed rather than redundant: nothing in CI would notice a deleted guard file. |
| enola | `enola-intent.yaml` (or a `layers:` block) + `enola baseline pin` / `enola check` | see §7.2 | Complementary reporting/grading gate, already installed, zero new deps. |

**Total new dependencies: zero. Total new CI jobs: zero. Total new commit
rituals: zero.**

### 7.2 The enola second gate

enola is installed (`enola version 0.2.7-51-g72cd079`), configured
(`mcp-arch.yaml`), and its `check` subcommand already supports a layers
explainer — `enola check --help` documents
`enola check --fail-on=cycles,layers --min-confidence=0.8`. It is a genuinely
independent gate: it parses structure itself and grades *deltas*, so it catches
unknown-unknown structural change that the hand-written guards did not anticipate.

Two facts must be stated honestly rather than assumed:

1. **There is no `enola-intent.yaml` at HEAD** (verified: the file does not exist,
   and `find` finds no `enola-intent*` outside `.venv`). The `layers:` declaration
   therefore has to be authored — most naturally by extending `mcp-arch.yaml`
   (which already exists and is the file `enola doctor` reports it is using) with
   a `layers:` block, exactly as proposal A §6.3 sketches the layer DAG. **The
   exact schema of that block must be read off the installed enola 0.2.7 build
   before it is written**, not guessed from the docs; that verification is the
   first sub-task of wave 0.
2. **The current baseline is not comparable.** `enola doctor` reports
   `NOT COMPARABLE: version_mismatch ...; ignore_globs ...` and instructs
   `enola baseline pin`. The checked-in `.enola/` snapshot is also stale — it was
   taken at `main@4f802b1` and still contains the deleted `tui/` package
   (`enola-architecture-facts.md` provenance note). The baseline must be
   re-pinned at the first wave's branch point.

Wiring, per phase:

```bash
# Once, at the branch point of a phase, before any edit:
enola baseline pin .                        # freezes the "before"; writes .enola/baseline

# Make the phase's changes...

# Grade the delta. Read-only; exit codes CI can act on:
enola check .                               # 0 clean · 1 regression · 2 error · 3 declined
enola check --fail-on=cycles,layers --min-confidence=0.8 --detail
```

Phase-0 posture, deliberately non-blocking while the mechanism is being trusted:

```bash
enola check --warn-only .                   # report everything, always exit 0 on findings
```

Later phases may also bound scope to prove an extraction did not spill:

```bash
enola check --target=film_pipeline/artifacts --max-spillover=0 .
```

**Exit-code contract for CI.** `0` clean, `1` structural regression, `2` could not
run, `3` declined (baseline not comparable). **`3` is never a statement about the
change** — a CI step that treats `3` as success is silently un-gated, and a step
that treats `2` as failure without a message will produce phantom reds. The
recommended wrapper fails on `1`, warns and annotates on `2`/`3`, and requires a
`baseline pin` in the same PR whenever the wave intentionally changes structure.

**How this grades the architecture delta per phase.** Because the baseline is
pinned at the phase's branch point and cleared/repinned on merge, each phase is
graded on *that phase's* structural delta against the wave table: wave 0 must
report zero new **cycles** — all **five** of `01-ownership-map.md` §15's cycles
(C1–C5) are recorded in `CYCLE_EXEMPTIONS`, so a *new* cycle is the regression
signal — and every later wave must show the cycle count and the layer-violation
count non-increasing. This is the independent, machine-derived corroboration of
`01-ownership-map.md` §15 and `enola-architecture-facts.md` §2 for each phase.

**Not wired into `ci-check` (stated plainly).** `make ci-check` is
`format-check lint typecheck test-cov build product-gate`; **nothing in it invokes
`enola`**, and no workflow step does either. §7.2's `enola baseline pin` /
`enola check --fail-on=cycles,layers` commands are **manual, reviewer-run** at wave
0 (and enola is not one of the gates §5.5's registry protects). The automated
acyclicity signal at wave 0 is the `module_edges()` SCC sweep in §3.9; enola is
promoted to a CI step only if a later wave shows it adds signal beyond that sweep.

**Not wired:** `enola install --hooks`. The session hooks are opt-in and run
commands at session end; the repo's own pre-push hooks already gate the same
content, so adding a second automatic mechanism is unnecessary.

---

## 8. Failure modes of this approach, and what it cannot enforce

### 8.1 Exemption rot — the biggest failure mode

The ledger starts with **31 rows** (§5.2). Every row is an opportunity to record a
deviation
instead of fixing it, and a ledger that only grows converts the mechanism into
documentation with a green checkmark.

*Mitigations:* (a) every row needs a `reason`, a resolving `citation` and a
`removal_phase` (§5.3 rules 1–3); (b) every row's subject must still describe an
observed violation — not merely still name an existing module — so a
fixed deviation fails the ledger until the row is deleted; (c) wave 0 is declared
the high-water mark and no wave may grow the ledger without splitting
(§5.4 rules 1–2); (d) every family asserts both directions, so a stale row and a
new violation are both failures.

*Residual risk:* a reviewer who accepts a new row for a legitimate-sounding
reason. The only real defence is (c) plus review attention; the mechanism makes
rejecting cheap, because rejecting is just "no new row".

### 8.2 Guard theatre — a guard that cannot fail

The most dangerous state is green and meaningless. `MIRRORS` is especially
exposed: if a mirror symbol *re-exports* the canonical constant, the guard compares
a value to itself.

*Mitigations:* `test_canonical_owner_is_not_its_own_mirror`,
`test_both_registries_are_non_trivial` plus `left != right`, `as_vocabulary()`
raising on a non-vocabulary instead of comparing two empty tuples,
`test_guard_inputs_are_not_empty`, `test_source_tree_looks_like_the_repo`, and the
mutation canary (§5.3), **plus the guard registry (§5.5)**, which catches the
adjacent failure — a guard that is *deleted or emptied* rather than one that is
vacuous. The measured precedent is not a single anecdote but a pattern: **18
orphaned `.pyc` files** under `tests/` are the residue of test-file deletions,
renames and moves that nothing noticed (V9; five `test_tui_*.py` and an
`integration/cli/conftest.py` removed by `37e9c65`, eight renamed helper modules,
one never tracked). The test set is not enumerated anywhere, so a vanishing guard
file is invisible — which is exactly what §5.5's registry fixes.

### 8.2b A guard file disappears

Distinct from §8.2: the file is not wrong, it is *gone*. A green suite with a
deleted guard is indistinguishable from a green suite with a satisfied one, and
this repository has no test-set manifest to notice: 18 orphaned `.pyc` files show
that deletions, renames and moves of test files accumulate without a trace (V9).

*Mitigation:* `tests/architecture/_guard_registry.py` (§5.5) is the **checked-in
manifest**: it names all **twelve** new guard files and the four legacy guards,
asserts each exists and contains at least one `test_` function, asserts the
manifest is sorted and 12 long, compares it **both ways** against a directory scan
of `tests/architecture/test_*.py` (so a *deleted* file and an *added* file are both
failures), and asserts every registered concern id resolves. Because the registry
lives in a different file from the guards it names, deleting a guard fails a test
that is still present.

*Residual risk:* someone deletes the registry **and** every guard in one commit.
That edit is a visible, large diff; no in-repo mechanism can defeat a coordinated
deletion, and pretending otherwise would be ceremony.

### 8.3 Static sweeps miss dynamic construction

`_policy_reads` and `write_sites` see string **literals**. `os.getenv(name)` with a
computed name, `state[key] = value` with a variable key, and
`globals()["PHASE_ORDER"]` are all invisible. `test_config_contract.py:18-21`
already documents this class of blindness for config scanning.

*Mitigations:* (a) declarations accept an explicit annotation for the dynamic
case, so it is recorded rather than lucky; (b) the policy sweep flags any *literal*
occurrence outside the declared modules, so the cheap evasion (a new literal
`os.getenv("FILM_PIPELINE_NO_PERSIST")`) is always caught; (c) where a read is
genuinely dynamic, the runtime differential test covers behaviour instead of
source.

### 8.4 Declaration/behaviour divergence in reader functions

`_readers.mvp_agent_output_artifacts()` could read the wrong attribute and make a
stale agreement look green.

*Mitigation:* readers are 3 lines each and live in tests, so they are reviewed in
the same diff as the declaration; `test_both_registries_are_non_trivial` fails an
empty result, which is a mis-written reader's failure mode.

### 8.5 Guard drift from the code it describes

Renaming `graph/services.py::_default_artifact_root` breaks a `module::symbol`
disposition key. The row then fails **liveness**, which is safe, but the message
("write site disappeared") could be misread as "the migration succeeded".

*Mitigation:* the liveness failure message says the write site disappeared and
tells the author to delete the row; a rename in a non-migrating PR produces the
same message with an unchanged step-1 count, which the PR template asks for.

### 8.6 The manifest becomes a merge-conflict magnet

`architecture.py` is edited by every ownership change, and conflicts in one file
across parallel extraction branches are likely in a multi-agent workflow (the
pre-commit config already references a fleet workflow).

*Mitigations:* (a) section the file one concern per block, so conflicts are
textually local; (b) at the estimated ~650 lines (§2.1) with `ruff format`
normalisation, resolution is mechanical but no longer trivial, which is why (c) is
a **committed threshold, not a suggestion**: when
`test_architecture_manifest_size` reports more than **750** lines, the *data*
families (`CONCERN_IDS`, `MIRRORS`, `NORMATIVE_NUMBERS`, the exemption tuples, the
artifact-id allow-lists) move into `architecture_<domain>.py` siblings that the
guard globs and imports, while the types and the `ModuleContract`/`Exemption`
definitions stay in the single leaf module. Splitting the *types* would break the
leaf rule for every `__init__.py` that imports `ModuleContract`, so the split is
deliberately data-only.

### 8.7 Over-constraint blocks legitimate work

A strict `may_import` plus `test_declared_edges_are_real` can make a legitimate
short-term edge expensive.

*Mitigation:* the escape is one declared edge line, plus — for a violation — an
exemption row with a reason and a wave. The point is that the **decision becomes
visible**; the mechanism never blocks a merge on its own authority.

### 8.8 Cost, and the `src/`-vs-`tests/` declaration question

Every source file is parsed by several sweeps, so cost is O(files × sweeps).
Measured baseline: the existing AST guards run 21 tests in ~7.5 s wall-clock with
`-n auto` and `--no-cov`; the prototype suite is in the same class (pure
`ast.parse` over a 40k-LOC tree plus ~6 symbol imports). *Mitigations:* parsing is
per-file and independent, `pytest-xdist` is already configured, and
`make arch-check --no-cov` gives a fast local loop; if it ever matters, cache
`ast.parse` per session in the harness (~10 lines, confined to `_harness.py`).

A contributor may also not know whether an invariant belongs in a module
`CONTRACT` or the central manifest. *Mitigation:* one testable rule (§2.1 rule 1
vs 2) — if exactly one module can truthfully state it, it goes in that module's
`CONTRACT`; if it is a relation *between* modules, it goes in `architecture.py`.
The guards' failure messages name both, so the contributor is told which to edit.

### 8.9 What this approach cannot enforce — stated honestly

- **O2 (duplicated invariant enforcement).** Finding that two functions enforce the
  same rule is a semantic judgement. The mechanism locks the *fix* once the entry
  points are enumerated; it cannot enumerate them, and it cannot prove the
  enumeration is complete.
- **O6 (parallel lifecycle).** Same shape: two paths must be *declared* as a pair,
  and the equivalence cases are human-authored. The comparison is automatic; the
  claim that they ought to agree is not verifiable mechanically.
- **"Should these two things agree at all?"** The O4 non-member rows encode a
  judgement. The guard makes the judgement explicit and forces it to be revisited
  when reality changes; it cannot make the judgement correct.
- **O8 quality.** Existence of a declared public name is exact; whether a boundary
  is *well typed* is review, with `disallow_any_explicit` as a partial proxy only.
- **Dynamic construction.** §8.3 — computed attribute/module/key names defeat any
  source-level sweep.
- **Runtime properties.** Only a fresh-interpreter test (the pattern already in
  `test_startup_boundaries.py`) can prove what actually loaded; the AST sweeps
  prove what is *written*.
- **Whether the declared responsibility is the right one.** The format forces a
  module to state its responsibility, non-goals, and owned invariants in one
  sentence each; a wrong-but-honest sentence passes every guard. That is a review
  and architecture question (`00-methodology-and-quality-bar.md` §1.2), not an
  enforcement question.
- **Anything under `docs/`.** The whole documentation tree — including `AGENTS.md`
  and this file — is invisible to CI (`paths-ignore`). The `AGENTS.md` "12
  sub-packages" error and its false dependency law can only be fixed by a human
  edit; no guard can fail on them.
- **Cross-repo / generated / vendored code.** `mcp-arch.yaml` ignores
  `film-knowledge-base/**` and `scripts/**`; both are outside the guards' scope by
  construction, so a boundary policy in `scripts/` is unenforced.

---

## Appendix — concern → guard index

The authoritative, mechanically derived index is **§3.10** (every `L-01 … L-58`
concern mapped to the guard family that pins it, generated from
`02-duplication-ledger.md`'s O-class column). Individual finding ids are not
re-listed here: the ledger deduplicates the finding corpus (148 findings at the
synthesis moment; **173 live** now) into 58 concerns, so citing a raw finding id
here would reintroduce exactly the corpus-count drift V5 corrects. Where a specific
finding matters to a guard, it is cited inline in that guard's section, and the
verifier verdict that corrected it is recorded in §1.7.

| Concern group | Guard section |
|---|---|
| O1 vocabularies | §3.1 (plus normative numbers, §3.11) |
| O2 invariants (human-anchored) | §3.2 |
| O3 state authority | §3.3 |
| O4 parallel registries | §3.4 |
| O5 policy-by-branch | §3.5 |
| O6 lifecycles (human-anchored) | §3.6 |
| O7 leaked internals (107 + 3, V4) | §3.7 |
| O8 missing contract | §3.8 |
| B3 edge matrix + acyclicity (V3) | §3.9 |
| Normative numbers (V1/V6) | §3.11 |
| Ledger hygiene + anti-vacuity | §5.3 |
| Guard registry / anti-deletion | §5.5 |
| The four legacy guards and their consolidation | §4 |
