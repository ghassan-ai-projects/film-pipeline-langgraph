# 04 — Extraction Roadmap (sequencing and execution plan)

> **Review status (2026-09-25): superseded proposal.** Do not execute P0–P20 as
> a delivery plan. The latest roadmap review finds five phases not shippable on
> their own (`reviews/adversarial-roadmap.md` R2.5–R2.6). The smaller sequence in
> [06](06-independent-review-and-decision.md) is the current recommendation.

Status: **synthesis, execution plan.** This document decomposes the modularization
program into dependency-ordered, independently shippable phases. Per
`03-target-architecture.md` §2.5, **this document is authoritative for phase ids,
ordering and per-phase acceptance — its phase ids are `P0`–`P20` (21 phases)** —
and `03`'s `W0`–`W12` is the design's internal wave spine, which this document
decomposes against. `03` owns the module catalog, the dependency law (v2), the
allowed-edge matrix and its single declaration home; `05-enforcement-and-guard-tests.md`
owns the enforcement mechanism.

Baseline for every number below: `fb85baa` (`modular-app`), `make ci-check`
verified green — **2003 passed / 8 skipped, 91.58 % coverage**, ruff format +
lint, mypy strict, `uv build` and the product gate OK, run with
`UV_CACHE_DIR=$PWD/.uv-cache` (`01-ownership-map.md:9-11`, `README.md:11`). enola
0.2.7-51-g72cd079 at the same commit: 5 cycles, 25 god classes, 63 modules,
0 declared layers (`enola-architecture-facts.md:14-18`).

## Revision 2 — adversarial roadmap review fixes

This section answers Revision 2 of `reviews/adversarial-roadmap.md` (Revision 2
begins at `:818`), which pinned an earlier text at 1381 lines, and it also
incorporates **`03`'s own Revision 2**, which published **§4.6.1 (FES)** as the
normative forbidden-edge scope and superseded the old count. The phase count
(`P0`–`P20`), the `Depends on` graph (acyclic, every dependency strictly earlier),
the wave mapping rows, the 58-id coverage and the `P0`–`P15` block are unchanged;
none of them was faulted. Every number below was re-measured at `fb85baa`, and
every command printed in this document now runs as written.

| Objection | Sev | Disposition | Change |
|---|---|---|---|
| **R2-O-1** — `Makefile` product-gate target and the console script belong to no phase | Blocking | **Fixed** | P20 now owns `Makefile:98-100` (`product-gate` → the relocated gate module), `pyproject.toml:39` (`film-pipeline-run = "film_pipeline.cli.run:main"` → the `studio` path) and every caller; Files, Steps, Evidence and the §5 rows carry them. |
| **R2-O-3** — P12's acceptance needs the change its rollback excludes | Blocking | **Fixed** | P12's scope is **extended** to include the `meta.json` provenance write; its B7 line now documents that as P12's own compatibility release rather than excluding it. Acceptance and evidence are unchanged. |
| **R2-O-4** — the red/green canary cannot run | Blocking | **Fixed** | Every subset command in this document now passes `--no-cov` and says why: `pyproject.toml:80` puts `--cov-fail-under=90` in `addopts`, so a subset run exits 1 on coverage rather than on the guard (`pytest tests/unit/graph/test_channel_registry.py -q` → 28.00 %, exit 1; exit 0 with `--no-cov`), and `05` uses `--no-cov` on all its guard commands. |
| **R2-O-20** — the M1 fix and the `langgraph.json` entry object | Major | **Fixed** | P11 states the mechanism: a lazy module `__getattr__("graph")` keeps `graph/graph.py:graph` resolvable while making import side-effect-free; P11 adds an entry-object assertion and a B7 line. `langgraph.json` itself changes only in P20 (W11) — the dependency edge is stated in P11. |
| **R2-O-21** — P20 fuses W11+W12 into one L phase | Major | **Fixed without changing the phase count** | P20 keeps one id but is two independently shippable, independently revertible series — **P20-W11** (split) and **P20-W12** (seal) — each with its own size, acceptance and rollback in §3 and its own row in §5. B5 therefore holds at series granularity, and §2/§3/§5 say so. |
| **R2-O-19** (= R1 O-10) — P19's surface is unmeasured, counts wrong | Major | **Fixed, with the review's counts corrected** | P19 now enumerates its surface with reproduce commands: `app/services` = **7** `.py` files, `mcp/tools` = **39**, `get_runtime` = **325** refs / **123** test files, `_services` = **131** refs / **72** test files. The review's 243/41 and 83/24 were not reproducible under any scope I tried (§ below) and are superseded by measurement. |
| **R2-O-22** — the Critical seam is untraceable by finding id | Minor | **Fixed** | `F-CRP-12` (= M1, **Critical 5×5=25**) is now cited in §0.1, §0.2, P11's §2 acceptance row and P11's §3 guard line. |
| **O-5** — the acyclicity sweep is blind to C1/C3/C4/C5 | Major | **Refuted; the document is clarified** | `05:1422-1426`: "the node set is every package and sub-package directory plus every module file, so a `graph -> graph.nodes` edge has two distinct endpoints. `CYCLE_EXEMPTIONS` rows are keyed at this same granularity"; `05:1433-1435` asserts over `strongly_connected_components(effective)`. The guard `05` specifies is **module**-granular, so it does see all five cycles. P1 now names it as such. |
| **O-6** — P11 leaves two profile owners at merge | Major | **Fixed** | P11 now **deletes `_FALLBACK_PROFILES`** outright, keeping the YAML authoritative; the coexistence note is gone. |
| **O-7** — `test_registry_and_enum_agree` is green on the mismatch it is named after | Major | **Fixed** | P7 now states the guard's anti-vacuity: it asserts the recorded difference is *exactly* the 8 registry-only / 6 enum-only set, so it is red the moment either side changes silently. |
| **O-8** — P8 gates every read with no pre-P8 corpus fixture | Major | **Fixed** | P8's test list gains a fixture built in the pre-P8 on-disk format and read back through the new reader; the label assumption is asserted by that fixture rather than carried as an open caveat. |
| **O-9** — "three intentional behaviour changes" | Major | **Fixed** | §1.8 now separates `03` §8's three B7 compatibility changes from P14's band correction and P17's gate reconvergence, which are defect fixes with before/after tests, not B7 releases. |
| **O-11** — DB-8 trigger; L-19 counted scheduled while half-deferred | Major | **Fixed** | DB-8's trigger is now "after P12", and §0.4's L-19 row names both halves: construction/wiring scheduled in P12, prompt rendering deferred to DB-8. |
| **O-12** — DB-4 trigger names the governance phase | Major | **Fixed** | DB-4's trigger is now "after P9" (provider policy home + P5 state model), decoupled from P17. |
| **O-13** — products named in modules that do not exist yet | Major | **Fixed** | P11's product is named at its pre-rename path (the module P20 renames to `studio`), P16's is `graph.project_generation_requests` (renamed `orchestration` in P20), and `storage/contract.py` is **created in P7, extended in P8** — no double ownership. |
| **O-14** — `CONSENSUS_REPORT`/`COST_ESTIMATE` absent while W4 requires them | Major | **Fixed** | P7 now declares those two kind names, per `03` §2.5 W4 (`03:208`), as declared vocabulary mirrors. No dependency is added: the names already exist in the registry at HEAD, so P7 declares them from data. |
| **O-15 / O-16** — literal counts | Minor | **Fixed** | Severity literals: **57** in the six packages, **59** repo-wide. `_phase_gate_updates`: **19** source occurrences, **12** call sites, **9** with an explicit `gate=`. `kb_context_ref=None`: **0** literals, with **15** `ArtifactMetadata(` constructions. Commands printed. |
| **O-17** — suite size | Minor | **Fixed** | P0's `test_architecture_manifest.py` is listed alongside the `tests/architecture/` suite files `05` §2.1 enumerates; the count is `05`'s and is cited, not restated. |
| **O-18** — shim windows span 3–18 phases with no rationale | Minor | **Fixed** | §1.9 states the rationale: a shim *is* the B7 guarantee that an old internal import path keeps working while its consumers migrate across phases, and `03` D9/§8 remove them only in W12, when the target names exist. |
| **O-19** — P3 does not delete the C1/C4/C5 exemption rows | Minor | **Fixed** | P3's Deletions now name the three `CYCLE_EXEMPTIONS` rows it must remove, per `05` §5.3 rule 2. |
| **R2/O-02 — forbidden-edge count and scope** | Blocking (raised in `03`'s own Revision 2) | **Fixed by citation** | `03` §4.6.1 (FES) is now the single normative definition and the sole home of the count and of the FES #1..#13 enumeration. Every place `04` restated, narrowed or recomputed it is replaced by a citation of §4.6.1; P0's acceptance states no number. Because `03` §2.5's W1 row now deletes the edge it numbers FES #1, **P2 owns that deletion** and P9 no longer claims it. |

**Where I judge the reviewer wrong (two points, both evidenced).**

1. **O-5's premise is incorrect for the guard `05` actually specifies.** The
   claim is that C1/C3/C4/C5 are "intra-package and invisible to the Kahn sweep".
   `05` §5.3's acyclicity guard is not package-keyed: its node set is every
   package *and sub-package directory and every module file*
   (`05:1422-1426`), `CYCLE_EXEMPTIONS` rows are keyed at that granularity, and it
   asserts on `strongly_connected_components(effective)` (`05:1433-1435`). All
   five cycles are intra-*package* but inter-*module*, which is exactly the
   granularity the guard uses. The document was at fault only for not naming the
   granularity; P1 now does.
2. **O-19's test-surface counts are not reproducible.** The review states 243
   `get_runtime` refs / 41 files and 83 `_services` refs / 24 files. Measured at
   `fb85baa`:

   ```
   $ grep -rn 'get_runtime' tests/ | wc -l ; grep -rln 'get_runtime' tests/ | wc -l
   325
   123
   $ grep -rn '_services' tests/ | wc -l ; grep -rln '_services' tests/ | wc -l
   131
   72
   ```

   Narrowing to `tests/unit` gives 295/102 and 79/42; narrowing further to
   `tests/unit/mcp` gives 168/55 and 0/0 — none of which is 243/41 or 83/24. The
   measured whole-suite upper bounds are what P19 now states.

The two counts the review supplied that **do** reproduce are kept: `app/services`
= 7 `.py` files and `mcp/tools` = 39 `.py` files (P19's old "5 files" / "46
files" were wrong and are corrected).

## 0. Authority, provenance and ordering authority

| Source | Role in this document | Conflict rule |
|---|---|---|
| `00-methodology-and-quality-bar.md` | Bars B5 (independently shippable) and B6 (guard tests); O1–O8 taxonomy; severity rubric §1.5 | Wins |
| `03-target-architecture.md` | **Authoritative** for the module catalog (§3), law v2 (§4.1), layers (§4.2), the allowed-edge matrix and its **single declaration home** (§4.3), the normative forbidden-edge scope **§4.6.1 (FES)**, the decisions record (D1–D12), the compatibility table (§8), and the wave spine (§2.5) | **Wins for module names, the law, the matrix and its home, and the FES scope and count.** Its §2.5 delegates **phase ids, ordering and per-phase acceptance to this document** |
| `05-enforcement-and-guard-tests.md` | **Authoritative** for the enforcement mechanism: the `tests/architecture/` suite it enumerates, the `CONTRACT`/`Exemption`/`VocabularyMirror`/`StateChannel`/`RegistryAgreement`/`PolicyPoint` shapes, the guard catalog, `make arch-check`, the CI wiring and the enola second gate | **Wins for mechanism**; P0/P1 consume it, they do not restate it |
| `02-duplication-ledger.md` | **The scope driver.** 58 deduplicated ownership concerns, `L-01`…`L-58`, each with O-class, evidence and candidate owner | Its `L-NN` ids own phase scope |
| `reviews/orchestrator-verification-notes.md` | The orchestrator's own reproductions at `fb85baa`: V1–V10 (V5 owns the corpus count). Corrects cross-cutting numbers the syntheses had duplicated | Applied in §0.2 |
| `reviews/verify-01.md` … `verify-14.md` | Independent verdicts; R4 — verifier verdicts win over audit and ledger claims. **All 14 have landed**; zero findings rejected | Applied in §0.2 |
| `audit/*.md` (corrected in the fix loop) | The corrected ground truth; the live count is measured in §0.1, not taken from any synthesis | Referenced through `02` and §0.2 |
| `01-ownership-map.md` | Current-state concern map and the five cycles | Ground truth for "who owns what today" |
| `design/proposal-A-boundaries.md` | The A-phase labels retained in the phase names | Subordinate to `03` |
| `design/proposal-B-enforcement.md` | The wave labels and playbook retained in P0/P1 | Subordinate to `03`/`05` |
| `enola-architecture-facts.md` | Measured coupling and cycles; the grading baseline | Structural evidence |
| `reconciliation-notes.md` | R1 kind counts (47/45/39), R2 cycles, R3 artifact contract is enforcement not a second storage module, R4 verifier verdicts win | Wins where the audit and proposal A disagree |

### 0.0 Ordering authority

Two documents constrain order, and they do not conflict:

- **`03` §2.5 owns the wave spine `W0`–`W12`** — the design's internal
  decomposition. It states that `04` is authoritative for **phase ids, ordering and
  per-phase acceptance**, and pins the id range to **`P0`–`P20`** (21 phases). This
  document therefore keeps exactly 21 phases and decomposes the `03` §2.5 spine
  onto them
  (§2.1), with two phases spanning two adjacent waves (`P8` spans W4/W5, `P20`
  spans W11/W12) where `03` itself puts one deliverable across the seam.
- **This document owns the P ordering and what is inside a phase** — scope, files,
  migration steps, guard tests, acceptance, rollback.

Where a P-level dependency would contradict the wave spine, **`03` wins and this
document is corrected**. The current order is checked against the spine in §2.1 and
has no cross-wave inversion.

### 0.1 The live finding count (measured, reproduce commands stated)

The live corpus is **173 findings — 38 Critical, 88 High, 47 Medium, 0 Low**.
Reproduce:

```
grep -h '^- \*\*Severity:\*\*' audit/*.md | wc -l                              # 173
grep -h '^- \*\*Severity:\*\*' audit/*.md \
  | sed -E 's/^- \*\*Severity:\*\* *\**([A-Za-z]+).*/\1/' | sort | uniq -c      # 38 Critical / 88 High / 47 Medium
```

The per-audit sum equals 173 exactly. **`audit/13`'s withdrawn `F-TEST-02` carries
no `- **Severity:**` bullet**, so it neither adds to nor subtracts from 173, and
there is no "172 live + 1 stub"; its heading survives only as a stub and it is
never cited as a guard justification.

The program's highest-severity single finding is `audit/10`'s **`F-CRP-12`**
(= verifier verify-10's **M1**, **Critical 5×5 = 25**): the module-level
`graph: CompiledStateGraph = build_graph()` at `graph/graph.py:201` runs
`default_checkpoints_root()` at import time and, under `PERSIST_STATE=1`, writes an
unmarked `checkpoints/` directory *inside* the storage root, after which the app
refuses its own root (`StorageRootError`). It is one of audit 10's eleven live
findings, and it is cited by id at every phase anchor in this document (§0.2, P11).

| Audit | Live | Audit | Live |
|---|---|---|---|
| 01 phase model | 11 | 08 validation / review | 15 |
| 02 orchestration state | 17 | 09 KB / provenance | 13 |
| 03 config / profiles | 13 | 10 checkpoints | 11 |
| 04 agents / prompts | 12 | 11 MCP / safety | 15 |
| 05 providers | 8 | 12 post / budget | 13 |
| 06 generation | 16 | 13 test doubles | 10 live + 1 withdrawn stub |
| 07 artifacts / refs | 13 | 14 module boundaries | 6 |
| | | **Total** | **173** |

`02`'s own appendix maps the **pre-fix 148-finding set** onto the 58 `L-NN`
concerns; `148` is history, not the current measure. `05` §3.11 records its own
draft-time figures — **163 (38C/83H/41M/1L)** and an earlier pre-verification
**148 (42C/80H/25M/1L)** — and marks both as stale; those are the only places this
document cites them, and only as draft-time history. `03-target-architecture.md:14`
already carries the corrected **173 — 38/88/47/0** and the same per-audit table.

The additions relative to the pre-fix 148 fold into existing concerns rather than
creating new ones, so the `L-NN` scope is unchanged:

| Added findings | Fold into | Effect on this plan |
|---|---|---|
| `F-AGENT-11` (prompt policy by identity branch), `F-AGENT-12` (validator-id rows in the profile map) | L-37/L-51, L-02 | P6 scope grows; V2 confirms L-02 is **O4** |
| `F-ARTIFACT-10` (QC artifact-version resolution), `-11` (`AssetEntry.kind` fourth kind vocabulary), `-12` (read paths never validate `artifact_id`), `-13` (`_UPSTREAM_CONTENT_SOURCES` fifth ref→phase map) | L-38, L-18, L-15 | P7/P8 scope grows; F-ARTIFACT-12 is read-path Critical under L-38 |
| `F-KBCTX-11/12/13` (matrix identity, producer-less kind, second type model) | L-18, L-19 | P7/P12 scope grows; no new concern |
| `F-MCP-13` (transport erases the typed code; no actor), `-14` (`MCPServer.active_project_id` write-only second state), `-15` (dead idempotency field) | L-52, L-45, L-23 | P18/P20 scope grows |
| `F-BUD-06` (sixth cap vocabulary in `context_packets`) | L-01 | P16 scope (budget, no longer deferred — §4) |
| `F-TEST-09/10/11` | L-47, L-09 | L-33 stands on F-TEST-01/07 and is deferred (DB-7); no scheduled phase depends on the withdrawn finding |

### 0.2 Corrections applied from the verifiers and the orchestrator

| # | Correction | Supersedes | Effect on this plan |
|---|---|---|---|
| V1 | Validator thresholds: **22** call-site literals carrying all three values (**18** at `85/75/75`, 3 at `80/70/70`, 1 at `90/80/80`); `block_below == review_at` in 22/22. The 23rd `ValidatorThresholds(` call is the bare default construct | `02` L-14, `audit/03`, `01` | P14 tests the band invariant (`block_below < review_at`), per `03` §2.7.2 |
| V2 | `_AGENT_PROFILE_MAP` has **21** entries against an **11**-agent roster; **10** orphan keys; two shared keys diverge. L-02 is **O4** as well as O1+O5. The cited test path does not exist; `tests/unit/graph/test_agent_profile_routing.py:21,25` pin the wrong values | `02` L-02 | P6 replaces those assertions; `AgentDescriptor.default_model_profile` is the single authority (`03` M6) |
| V3 | "8 forbidden edges" is not an enumeration. The earlier package-granularity counts could not see the `graph` split (`governance → orchestration`) or the `app` split (`operations → studio`), and omitted the `mcp → studio` edge | `02` L-48, `audit/14`, `01` | Superseded by **`03` §4.6.1 (FES)**, now the single normative definition of the scope and the count; `04` cites it and never restates, narrows or recomputes the number. See §2.2 |
| V4 | Private reach-ins: **107** cross-package private-module sites (**106** `schemas._base` + **1** `app._persistence`) plus **3** private-symbol sites; **72** files outside `schemas` import `_base`; `schemas` has **322** `ImportFrom` = **252** cross + **70** intra | proposal A's "383", `01`, enola §3 | P0's ledger seed and P10's evidence use 107 + 3 and 322 = 252 + 70 |
| V5 | Live corpus is **173 (38C/88H/47M/0L)**, measured by the two commands in §0.1; the draft-time 163 (38/83/41/1) and pre-verification 148 (42/80/25/1) are history; audit 13's withdrawn `F-TEST-02` carries no Severity bullet, so there is no "172 + 1 stub" | README/`01`/`02` "148"; the draft-time sizes in `03` §2.7 / `05` §3.11 | §0.1; no scheduled phase is justified by a withdrawn finding |
| V6 | Verification complete for audits 01–14; **zero findings rejected** | — | R4 remains the conflict rule |
| V7–V9 | Cross-cutting reconciliations the orchestrator recorded before the V10 close-out | `02` misc | No phase reorder; already folded into §0.1–§0.3 |
| **V10** | **`reviews/verify-10.md` has landed** (audit 10, checkpoints/persistence): **11 CONFIRMED / 2 DOWNGRADED / 0 REJECTED**; the two recomputed severities are `F-CRP-05` (High→Medium, 4×3 → 3×3) and `F-CRP-10` (High→Medium, 3×3 → 2×3). The verifier also found a **missed seam `F-CRP-12` (= M1, Critical 5×5=25, `audit/10:30`)**: a bare `import film_pipeline.graph.graph` creates `<storage root>/checkpoints/`, after which the app refuses its own storage root | the previous `PENDING VERIFY-10` marker | **No marker remains.** P11 (persistence policy) absorbs `F-CRP-12` and the F-CRP-09 truth-table correction; DB-6 carries the rest |
| — | L-38 read-path half **Critical** (F-ARTIFACT-05, reproduced) | `02` L-38 | P8's read-path step precedes kind declaration |
| — | F-VR-02 corrected: `NEEDS_REVISION` **is** reachable on the LLM path; the real defect is the zero-width band for all 22 explicit literals | `audit/08` | P14 guard is the band invariant, per `03` §2.7.2 |
| — | L-24 → High; L-10/F-VR-05 → High (F-VR-04 still Critical); F-VR-06 → **seven** gate sites; F-VR-09 drift proof falsified | `02`/audit | P11/P14/P17 scope wording; no reorder |
| — | `03` D4: no top-level `artifacts.contract`; the contract is **`storage.contract`** | proposal A §5, audit 07 §6 | P7/P8 module attribution |
| — | `03` D5/W8: budget/spend is a **`budget` module at L5**, scheduled in W8 | my previous "DB-1 deferral" | **L-01 is scheduled inside P16** (the W8 projection/cost phase); DB-1 retired (§4) |
| — | `03` D6: `app/mock_responses.py` **stays in `studio`**; only `testing` → `devharness` leaves the wheel | proposal A §7, my previous studio phase | P20 no longer moves `mock_responses.py` |
| — | `03` D9/D10: shims are `# SHIM(W<n>)`, removed by guard in W12; the target law has **no unrestricted modules** | proposal B §5.3, my previous `SHIM(P<n>)`/`UNRESTRICTED_PACKAGES` | P1 declares observed edges (incl. temporary `graph`/`mcp` unrestricted) and each wave tightens toward §4.3; P20 removes shims |
| — | `03` D11: the **47 registered ids are canonical**; the 8 registry-only names join `filmspec`; `clip`/`last_frame`/`mid_frame` are declared **non-storable media kinds**; the 3 prefix-covered names stay prefix-reachable | my previous "register the 3 media kinds" recommendation | P7/P8 adopt D11 (declaration, not registration) |
| — | `03` §8: the only intentional behaviour changes are the W8 ceiling, the W6 persistence precedence and the W11 `langgraph.json` path | my previous P11/P20 | P11, P16 and P20 carry them |

### 0.3 Numbers this plan uses

```
artifact kinds:      47 registered (canonical) / 45 enum / 39 shared; 8 registry-only (added to filmspec);
                     3 prefix-covered; clip/last_frame/mid_frame declared non-storable (03 D11)
validator thresholds: 22 literal calls (18x 85/75/75) + 1 bare default construct
private reach-ins:   107 private-module sites (106 schemas._base + 1 app._persistence) + 3 private-symbol sites
schemas imports:     322 ImportFrom = 252 cross-package + 70 intra-package
forbidden edges:     scope and count are owned by `03` §4.6.1 (FES) — the normative definition and
                     the enumeration of FES #1..#13 live only there. The guard derives the count
                     from the manifest; `04` cites §4.6.1 and never restates the number
live findings:       173 (38 Critical / 88 High / 47 Medium / 0 Low); F-TEST-02 withdrawn stub, no Severity bullet
baseline:            2003 passed / 8 skipped, 91.58 % coverage, UV_CACHE_DIR=$PWD/.uv-cache
```

### 0.4 `L-NN` → phase map (58 / 58)

"Primary phase" is where the concern's authority is created and its guard added;
residual halves are named. Deferred concerns are in §4 with the trigger that
unblocks them; **49 concerns are scheduled and 9 deferred**. Module attribution
follows `03` §2.7.1.

| L | Concern | Sev (02) | Corrections (§0.2) | 03 module | Primary phase | Note |
|---|---|---|---|---|---|---|
| L-01 | Budget state, caps, refusal gates, spend recording | Critical | CONFIRMED; F-BUD-06 added | `budget` | **P16** (W8) | Scheduled by 03 D5; shares the W8 phase with projection/cost |
| L-02 | Agent→model-profile map duplicated and divergent | Critical | CONFIRMED (25→16); **O4** (V2) | `agents` (+`config`) | **P6** (W4) | Two tests encode the wrong values |
| L-03 | Agent execution lifecycle: graph vs MCP bible | Critical | CONFIRMED (live `AttributeError`) | `agents` | **P6** (W4) | Lifecycle half deferred to DB-9 (after P19) |
| L-04 | Post models, `AssemblyAgent`, `assembly_manifest` | Critical | CONFIRMED | `post` | **deferred DB-2** | After P17 |
| L-05 | "Delivery complete" and the delivery-manifest seam | Critical | CONFIRMED (F-POST-06 → Medium) | `post` | **deferred DB-3** | After P17 |
| L-06 | Phase advancement / successor; app skips provider gate | Critical | CONFIRMED (reproduced) | `governance` + `filmspec` | **P17** (W9) | Successor dedup in P4 |
| L-07 | Agent declared contract vs registered implementation | Critical | CONFIRMED | `agents` | **P6** (W4) | |
| L-08 | Generation job lifecycle: submit → poll → complete | Critical | CONFIRMED | `generation` | **P15** (W8) | |
| L-09 | Provider health: four representations; routing reads dormant | Critical | CONFIRMED | `providers` (+`orchestration`) | **deferred DB-4** | After P17 |
| L-10 | Consensus construction and consensus report state | Critical | CONFIRMED (F-VR-05 → High) | `validation` | **P14** (W7) | Router-key half in P5 |
| L-11 | Run / runtime / storage / checkpoint roots resolved five ways | Critical | CONFIRMED | `studio` (+`storage`,`checkpoints`) | **P20** (W11) | |
| L-12 | MCP invocation lifecycle and the `app`↔`mcp` cycle | Critical | MIXED (C2 = 7 modules) | `mcp` + `studio`/`operations` | **P20** (W11) | Early edge move in P2 (W1) |
| L-13 | Validator registry and phase→validator dispatch | Critical | CONFIRMED (F-MCP-04 20→16) | `validation` | **P13** (W7) | Two phase-keyed tables, not three |
| L-14 | Score→status thresholds; `NEEDS_REVISION` band | Critical | CONFIRMED; V1: 22/18; F-VR-02 corrected | `validation` | **P14** (W7) | Guard is the band invariant |
| L-15 | Phase vocabulary, order and phase-keyed policy literals | Critical | CONFIRMED; F-ARTIFACT-13 added | `filmspec` | **P3** (W2) | Literal sweeps in P4 |
| L-16 | Ledger state machine and generation-status grammar | Critical | CONFIRMED | `generation` | **P15** (W8) | |
| L-17 | Two live QC lifecycles (subgraph vs sequential node) | Critical | CONFIRMED | `validation` (+`orchestration`) | **deferred DB-5** | After P14 |
| L-18 | Artifact kind ↔ `ArtifactType` vocabulary (R1) | Critical | CONFIRMED; F-ARTIFACT-11/12 added | `filmspec` + `storage.contract` | **P8** (W4) | Guard added in P7; 03 D11 resolution |
| L-19 | KB packet construction and delivery to prompts | Critical | CONFIRMED | `kb` (+`orchestration`) | **P12** (W6) | Scheduled in P12: construction + wiring; deferred to DB-8: prompt rendering |
| L-20 | KB provenance stamping and `kbctx:` id grammar | Critical | CONFIRMED (04..07 downgraded) | `kb` (+`storage`) | **P12** (W6) | `meta.json` change is a separate B7 release |
| L-21 | Checkpoint metadata registries and `artifact_versions` | Critical | CONFIRMED (verify-10: 11/2/0) | `checkpoints` | **deferred DB-6** | After P18/P20 |
| L-22 | Resume seam and duplicate resume implementations | Critical | CONFIRMED (verify-10: 11/2/0) | `checkpoints` (+`operations`) | **deferred DB-6** | Drift risk; shares DB-6 |
| L-23 | MCP tool argument contracts declared, never populated | Critical | CONFIRMED (0/77); F-MCP-15 added | `mcp` | **P20** (W11) | |
| L-24 | Model-profile defaults in YAML and in code | Critical | DOWNGRADED (16→12) | `config` | **P11** (W6) | |
| L-25 | Provider-lineup parsing understands one profile shape | Critical | CONFIRMED | `config` (+`providers`) | **P11** (W6) | |
| L-26 | "Stalled phase": two representations, three thresholds | High | DOWNGRADED (proof false) | `orchestration` | **P5** (W3) | |
| L-27 | Failure decisions and provider failure classification | High | CONFIRMED | `providers` (+`orchestration`) | **P5** (W3) | Classifier ownership in DB-4 |
| L-28 | Provider registry and catalog/capabilities | High | CONFIRMED | `providers` | **deferred DB-4** | After P17 |
| L-29 | Credential resolution policy re-derived at 14 sites | High | CONFIRMED | `providers` | **P9** (W5) | Freshness half in DB-12 |
| L-30 | Agent naming drifts into the KB manifest/defaults | High | CONFIRMED | `agents` (+`kb`) | **P6** (W4) | Manifest-load validation |
| L-31 | Gate decision and the human-gate review package | High | CONFIRMED | `governance` | **P17** (W9) | Seven gate-decision sites |
| L-32 | Number-word and scene-count grammar defined twice | High | (not separately verified) | `constraints` | **P4** (W2) | |
| L-33 | Canned payloads, mock model, mock provider entries | High | F-TEST-02 **withdrawn stub**; L-33 stands on F-TEST-01/07 | `devharness` (+`studio`) | **deferred DB-7** | After P20 |
| L-34 | Phase→approval-gate map and gate mode | High | CONFIRMED | `filmspec` + `governance` | **P4** (W2) | Gate-mode half in P17 |
| L-35 | `issues` contract, blocking predicate, approve veto | High | CONFIRMED | `orchestration` (+`governance`) | **P5** (W3) | Predicate half in P4 |
| L-36 | `app` re-implements the graph's channel reducers | High | CONFIRMED (proof overstated) | `orchestration` | **P19** (W10) | `_graph_exec` dismantled there |
| L-37 | Prompt registry keyed from two id spaces | High | CONFIRMED; F-AGENT-11 added | `agents` | **P6** (W4) | |
| L-38 | Artifact version / `schema_version` / status law | High | **UPGRADED** (F-ARTIFACT-05 → Critical) | `storage.contract` | **P8** (W4/W5) | Read gate is the Critical half |
| L-39 | Media paths, reference-asset catalog, generated-media policy | High | DOWNGRADED (F-GEN-07/08) | `generation` (+`storage`) | **P8** (W4) | Inventory half in P15 |
| L-40 | Generation-request identity and stale-code sets | High | CONFIRMED | `generation` (+`orchestration`) | **P16** (W8) | |
| L-41 | Cost model: pricing vs planner artifact ceiling | High | CONFIRMED (F-PROV-07 partly downgraded) | `budget` (+`providers.pricing`) | **P16** (W8) | Ceiling fed to the budget comparison |
| L-42 | Rollback/invalidation/audit/discovered projects | High | CONFIRMED (verify-10 F-CRP-11) | `checkpoints` (+`storage`) | **P18** (W10) | Audit half; rest in DB-6 |
| L-43 | Persistence flags and entry-point bootstrap | High | CONFIRMED (verify-10 F-CRP-09/`F-CRP-12`) | `studio` | **P11** (W6) | Bootstrap half in P20-W11 |
| L-44 | MCP confirmation enforcement and dangerous-mutation policy | High | CONFIRMED | `mcp` | **P20** (W11) | |
| L-45 | `OperatorService` vs MCP and the two project registries | High | DOWNGRADED (F-MCP-06 → Medium); F-MCP-14 added | `operations` + `projects` | **P18** (W10) | Operator half in P19 |
| L-46 | Profile-stack keys, writers, `resolved_review_strategy` | High | CONFIRMED | `config` | **P11** (W6) | |
| L-47 | Test harness: store factory, fixtures, git double, protocols | High | CONFIRMED; F-TEST-09 added | `devharness` | **deferred DB-7** | After P20 |
| L-48 | Module dependency law, enforcement, private reach-ins | High | VERIFIED; V3/`03` §4.6.1 scope fixed | `architecture.py` + guards | **P0** (W0) matrix, **P1** (W0) enforcement | Reach-ins P9, façade P10, closure P20 |
| L-49 | Router action vocabulary vs the edge transition table | High | CONFIRMED | `governance` | **P4** (W2) | |
| L-50 | Orchestrator key grammar and `_orchestrator__` literals | High | CONFIRMED | `orchestration` | **P5** (W3) | |
| L-51 | Four prompt renderers and two JSON-recovery strategies | High | CONFIRMED | `agents` | **P6** (W4) | |
| L-52 | MCP error taxonomy bypassed; dead envelope field | High | CONFIRMED; F-MCP-13 added | `mcp` | **P20** (W11) | |
| L-53 | `profiles/` location and hardcoded numeric defaults | High | CONFIRMED | `config` | **P11** (W6) | |
| L-54 | `film_pipeline.testing` ships and is a cross-domain consumer | High | VERIFIED (confirmed) | `devharness` | **P20** (W11) | Wheel exclusion + boundary guard |
| L-55 | `next_action` prose and routing-decision channels | Medium | CONFIRMED | `governance` (+`orchestration`) | **P5** (W3) | Prose ownership in P17 |
| L-56 | Ledger read path creates the ledger (write-on-read) | Medium | CONFIRMED | `generation` | **P15** (W8) | |
| L-57 | Ref-string formatter duplicated | Medium | CONFIRMED | `storage.contract` | **P7** (W4) | |
| L-58 | "Requires human review" derived twice | Medium | CONFIRMED (band corrected) | `validation` (+`governance`) | **P14** (W7) | |

**Counts.** 58 concerns: **49 scheduled** across 21 phases; **9 deferred** with a
trigger (L-04, L-05, L-09, L-17, L-21, L-22, L-28, L-33, L-47). Of the ledger's
47 defects, **39 scheduled and 8 deferred**; of its 11 drift-risk items, **10
scheduled and 1 deferred** (L-22).

## 1. Sequencing principles

1. **The wave spine is the order; phases are its decomposition.** `03` §2.5's
   W0–W12 is the design's spine and this document owns the 21 phase ids that
   decompose it. A phase may span two adjacent waves (P8 spans W4/W5, P20 spans
   W11/W12) but no phase may be scheduled in a wave whose inputs do not yet exist.
   §2.1 is the checking table.
2. **The law is declared before it is enforced (V3).** A guard that hardcodes a
   number nobody defined freezes a wrong fact. The allowed-edge matrix and its
   scope definition are declaration *data* in `src/film_pipeline/architecture.py`
   (`03` §4.3/§4.6, `05` §2.1); the guard computes counts from the manifest and
   never reads them from prose.
3. **Defects before drift risk — except where the drift risk is a prerequisite.**
   `02` separates executed defects from latency seams. Defects whose fix is local
   and whose authority exists go early (P6 agent contracts, P15 generation
   lifecycle, P14 thresholds/consensus, P8 read path). Drift-risk concerns go
   early only when everything depends on their authority: L-15 and L-34/L-49 are
   O1 duplicates whose single owner must exist before state or advancement is
   unified.
4. **Leaves before hubs, by measured in-degree.** `schemas` is imported across 16
   packages (252 cross-package imports); `checkpoints`, `kb`, `constraints` by
   1–3; `providers` by 5; `storage` by 8; `orchestration` and `mcp` are the
   highest non-composition modules. Extract the zero-import vocabulary leaf first,
   and change `schemas` only by relocation with re-exports.
5. **Normative model first, enforcement second.** Most recorded debt is O1/O5, not
   corrupted state. `filmspec` (P3) exists before any predicate is centralized
   (P4), and the state model (P5) exists before advancement is unified (P17).
6. **Every concern gets exactly one primary phase**, with residual halves named in
   §0.4. This prevents the prohibited end state where two owners of one concern
   both look authoritative.
7. **Smallest independently shippable step.** Every phase ends with
   `make ci-check` green on its own. Where `03`'s wave bundles work, this document
   splits it while keeping the 21-phase id range (W0 → P0/P1, W4 → P6/P7/P8,
   W8 → P15/P16, W10 → P18/P19), and folds where a split would exceed the range
   (W11+W12 → P20; `budget` → P16).
8. **Blast-radius containment by construction.** A phase may not change a
   persisted representation. `03` §8 ships exactly three B7 compatibility changes:
   the W8 MCP spend-ceiling default (P16), the W6 persistence precedence (P11) and
   the W11 `langgraph.json` path (P20); each is documented in its phase note and
   asserted by a test. Two further phases change observable outputs while fixing
   defects — P14 makes `NEEDS_REVISION` reachable by widening the zero-width band,
   and P17 reconverges the app/MCP gate decision onto the graph's — and those
   carry before/after evidence in the phase note, not a B7 compatibility release.
   Anything else that changes a persisted representation is a separate B7 PR.
9. **No long-lived divergent branch, no feature flags.** The exemption ledger
   makes un-migrated seams *recorded* rather than forbidden; each phase is a short
   branch off `modular-app`. No runtime toggle — if one seems necessary, the phase
   is too large. Shims are `# SHIM(W<n>)`. A shim *is* the B7 guarantee that an
   existing internal import path keeps resolving while that path's consumers
   migrate, so its lifetime is bounded by its slowest consumer, not by the phase
   that created it: `schemas._base` has 72 importers spanning W2–W5, and
   `graph._action_routing` / `app/product_gate` are only renamed by the W12 seal.
   `03` D9/§8 removes every shim in W12, when the target names exist and `# SHIM`
   can be asserted absent; P20 enforces that.
10. **The ledger is the burndown chart.** Every phase deletes its exemption rows;
    P20 asserts the ledger is empty. P1 is the high-water mark and no wave may
    grow it (`03` L8).

## 2. Phase table

Legend: **W** = the `03` §2.5 wave this phase belongs to; **A** = the proposal-A
phase it derives from. **L** = the concerns whose authority this phase creates.
Sizes: S ≤1 day-equivalent, M 2–4, L 5+. Acceptance is uniform: `make ci-check`
green (ruff format + lint, mypy strict, pytest ≥90 % coverage, `uv build`, product
gate) with 2003 passed / 8 skipped and 91.58 % coverage as the floor; "CI@90 %" is
shorthand for that plus the §5 done-rule. Every phase additionally passes the
**ownership-uniqueness check**: at every intermediate commit, no concern it
touches has two authoritative owners, and the exemption ledger names the single
remaining owner for any un-migrated site.

| Phase | W (A) | Name | Concerns retired (L) | Module created / owned | Depends on | Guard test(s) added | MCP / LangGraph compat | Acceptance |
|---|---|---|---|---|---|---|---|---|
| **P0** | W0 (A:P0) | Pin baseline; declare matrix + scope in `architecture.py` | L-48 (matrix/scope) | `architecture.py` (declared leaf) | — | `test_architecture_manifest_is_a_leaf`; `test_matrix_matches_03_4_3`; `test_scope_classes_cover_all_packages` | None — no production change | CI@90 %; `enola baseline pin`; matrix rows = `03` §4.3; the forbidden count derived by `03` §4.6.1 (FES), computed by the guard and not restated here |
| **P1** | W0 (A:P0, B:W0) | Law on: `CONTRACT`s + `tests/architecture/` suite + exemption ledger | L-48 (enforcement) | 17 `__init__.py` contracts; the `tests/architecture/` suite enumerated in `05` §2.1, plus P0's `test_architecture_manifest.py` | P0 | `test_exemptions.py` (hygiene + anti-vacuity canary); `test_contracts.py::test_declared_edges_are_real`; `::test_declared_module_graph_is_acyclic` (**module**-granular SCC, `05` §5.3 — sees C1/C3/C4/C5) | None — no production change | CI@90 % (`--no-cov` on subset runs); every observed edge declared; a synthetic violation makes a guard fail (demonstrated) |
| **P2** | W1 (A:P9, pulled early) | Make the cycle true; delete FES #1 | L-12 (early edge) | top-level `entrypoints.py` pre-image of `studio`; `config/profile_resolver.py` | P1 | `test_declared_module_graph_is_acyclic` with empty `CYCLE_EXEMPTIONS`; `test_forbidden_edges_are_derived_from_the_declared_scope` (FES #1 gone); mutation canary | `product_gate` moves above `mcp` (internal path only); the three `register_project_providers` callers re-point to the `operations` pre-image | CI@90 %; cycle C2 edge gone; no new cycle; FES #1 no longer derived |
| **P3** | W2 (A:P1) | Extract `filmspec` vocabulary | L-15 | `filmspec` (L0, zero outbound imports) | P1 | `tests/unit/filmspec/test_no_duplicate_literals.py::test_phase_order_is_derived_not_redeclared`; `::test_filmspec_has_zero_outbound_imports` | LangGraph state unchanged; import shims `# SHIM(W2)` | CI@90 %; old paths resolve to identical objects; C1/C4/C5 source edges removed |
| **P4** | W2 (A:P2) | Literal/table burndown | L-32, L-34, L-49 (+L-15, L-35 residual) | `filmspec` predicates; `constraints` number-word table | P3 | `test_no_duplicate_literals.py::{test_severity_literal_never_reappears,test_phase_gate_map_single_source}`; `test_router_action_vocabulary_matches_edges`; `test_scene_count_grammar_single_source` | None external | CI@90 %; any-position literal sweeps go to owner-only; mutation drives every gate site |
| **P5** | W3 (B:W3) | Orchestration state single writer + routing inputs | L-26, L-27, L-35, L-50, L-55 | `orchestration` state | P4 | `tests/unit/graph/test_channel_registry.py` extended (writers == 1, Name-subscript writes); `test_orchestrator_key_sets_are_identical` (both ways); `test_stall_predicate_single_source.py` | Channels added/rerouted, never removed; `consensus_report_ref` typed, additively | CI@90 %; one writer per `STATE_CHANNELS` row; `route_reason` non-empty |
| **P6** | W4 (A §5.8) | Agents: catalog, prompts, model routing | L-02, L-03 (defect), L-07, L-30, L-37, L-51 | `agents` catalog + prompt registry | P5 | `test_catalog_parity.py` (set equality both ways, `produces ∈ execute()`); `::test_profile_map_matches_declared_contract` (replaces the two wrong-value tests); `test_prompt_coverage.py`; `test_renderers_single_grammar.py` | MCP bible path stops raising `AttributeError` (documented) | CI@90 %; 21↔11 map resolved; KB manifest tokens resolve |
| **P7** | W4 (A §5.9/R1) | Artifact kind set + ref grammar | L-57 (+L-18 guard) | `filmspec` kind vocabulary (**incl. `CONSENSUS_REPORT`/`COST_ESTIMATE`**, `03` §2.5 W4); `storage/contract.py` (created) | P3 | `tests/unit/filmspec/test_artifact_kind_parity.py::test_registry_and_enum_agree` (asserts the recorded difference is *exactly* 8 registry-only / 6 enum-only, so it is red on any silent change); `tests/unit/artifacts/test_single_ref_formatter.py` | No persisted change; the 8/6 mismatch is a cited ledger row with an exact-set assertion | CI@90 %; R1 script output recorded; formatter count 2 → 1 |
| **P8** | W4/W5 (A §5.5, R3) | Storage single-writer authority + read gate | L-18, L-38, L-39 (media grammar) | `storage` + `storage/contract.py` | P7, P6 | `test_storage_boundary.py` extended: `test_storage_never_imports_above_l1`, `test_all_reads_use_checked_envelope`, `test_version_assigned_only_by_store`; `test_kind_declaration.py`; `test_artifact_id_validated_on_read.py` | **B7 (additive):** 8 names join `filmspec`; 3 media kinds declared non-storable; stored `artifact_type=script` labels not migrated (03 D11) | CI@90 %; 47 registered kinds round-trip; checksum/schema/traversal checks fire on every read entry |
| **P9** | W5 (A:P3) | Private reach-ins + credential policy | L-29 (+L-48 residual) | `providers` public credentials API | P8 | `test_boundaries.py` private-import sweep (107 + 3 baseline); `tests/unit/providers/test_adapter_port.py`; `tests/unit/config/test_config_contract.py::test_config_does_not_import_providers`; façade identity canaries | None external | CI@90 %; credential policy has one home; FES #1 (`config → providers`, both sites) is already removed in P2 (W1), so P9 adds no new forbidden edge |
| **P10** | W5 (B:W5) | `schemas` public surface | L-48 (façade half) | `schemas` façade; `_base.py`→`base.py` | P9 | `tests/unit/schemas/test_public_surface.py::test_no_private_base_import_outside_schemas`; `::test_facade_reexports_all_public_names` | Import shim `# SHIM(W5)` only | CI@90 %; 72 → 0 importers; façade completeness enumerated |
| **P11** | W6 (B:W1.5/6) | Resolution policy: persistence + config (**absorbs verify-10 `F-CRP-12`**) | L-24, L-25, L-43 (persistence half), L-46, L-53 | `config`; `resolve_persistence()` (pre-rename `app/_persistence.py`) | P10 | `test_config_contract.py` extended: `::test_provider_lineup_normalizes_all_shapes`, `::test_profile_stack_slots_single_source`, `::test_no_hardcoded_profile_defaults`; `test_persistence_truth_table.py` (four rows, incl. F-CRP-09's corrected row-4 label); `test_bare_graph_import_does_not_poison_storage_root.py` and `test_graph_entry_object_resolves.py` (**`F-CRP-12`**) | **B7 (documented):** one persistence precedence truth table; `langgraph.json` entry path changes only in P20-W11 | CI@90 %; every consumer reports the same persistence mode; festival-stack conflict fires for the all-mock profile; a bare `import film_pipeline.graph.graph` no longer creates `<storage root>/checkpoints/`; the `graph` entry object still resolves |
| **P12** | W6 (audit 09) | KB root, id grammar, packet wiring, provenance (**incl. the `meta.json` write**) | L-19, L-20 | `kb` | P10, P6 | `tests/unit/kb/test_kb_root.py::test_kb_path_literal_only_in_kb`; `test_single_kbctx_minter.py`; `test_wired_packet_builder.py`; `test_manifest_phase_tokens_valid.py` (03 M3) | **B7:** P12 ships the `meta.json` `kb_context_ref` write as its own documented compatibility change (R2-O-3) | CI@90 %; root resolves under a changed CWD; one minter; both factories build a real packet; a mutable save→read preserves the ref |
| **P13** | W7 (A §5.9) | Validator registry + dispatch | L-13 | `validation` registry + `PHASE_VALIDATORS` | P12 | `tests/unit/validation/test_registry_agreement.py` (values, not just keys — 03 M9); `test_dispatch_tables_agree.py` | MCP `run_validation` set becomes the union; every declared phase reachable (03 M24) | CI@90 %; set equality both ways; unknown validator fails loudly |
| **P14** | W7 (A:P4) | Report writer, status band, consensus | L-10, L-14, L-58 | `validation` report writer | P13 | `test_single_report_writer.py` (AST sweep); `test_score_to_status_bands.py` (22 literals; `block_below < review_at`); `test_consensus_receives_typed_objects.py` | Report payload unchanged; `consensus_report_ref` typed channel declared (additive, old checkpoints resume) | CI@90 %; band invariant holds for all 22; consensus non-`None`; typed `ReviewPackage` asserted on both paths (03 M17) |
| **P15** | W8 (A:P5 part) | Generation ledger lifecycle | L-08, L-16, L-56 (+L-39 inventory) | `generation` ledger | P14 | `tests/unit/generation/test_ledger_single_writer.py`; `test_ledger_transition_law.py`; `test_read_does_not_create_ledger.py` | Ledger payload preserved; MCP poll records media/manifest (documented) | CI@90 %; provider call carries resolved prompt; poll test asserts media + manifest |
| **P16** | W8 (A:P5, 03 D5) | Generation projection, cost/ceiling, and the `budget` module | L-40, L-41, L-01 | `graph.project_generation_requests` (renamed `orchestration` in P20); `budget` (L5) | P15 | `test_generation_requests_projection_single_writer.py`; `test_cost_model_single_source.py`; `test_budget_single_source.py`; `test_spend_recorded.py`; `test_ceiling_agreement.py` | **B7:** MCP `approve_generation_spend` default becomes the estimate-derived ceiling, not unlimited | CI@90 %; reducer/filter agree on every id subset; mock cost equals `pricing`; graph and MCP approve at the same ceiling; `spent_usd` is a real sum |
| **P17** | W9 (A:P6) | Extract `governance` / advancement | L-06, L-31 | `governance` (stateless, L8) | P16 | `test_gate_decision_is_single_source.py`; `test_governance_imports_nothing_above_l8.py` (anti-cycle); `test_review_package_shape.py` | Graph human gate builds the typed package; MCP shape frozen | CI@90 %; F-PHASE-01 divergence reconverges; graph SCC C3 broken |
| **P18** | W10 (A:P7) | Extract `projects` | L-42 (audit half), L-45 (registry half) | `projects` (L4) | P17 | `test_single_active_project_authority.py` (incl. `MCPServer.active_project_id`); `test_inmemory_matches_disk.py`; `test_delete_audit_persisted.py` | `resolved_project_id` semantics unchanged | CI@90 %; memory ≡ disk; both creation paths equal |
| **P19** | W10 (A:P8) | Extract `operations`; kill the locator | L-36 (+L-45 operator half, L-03 lifecycle half) | `operations` (L10) | P18 | `test_mcp_does_not_touch_domain_modules.py`; `test_operator_backend_is_constructor_injected.py`; `test_reducers_shared_with_schema.py` | MCP names/schemas frozen; `_services` **state channel kept** | CI@90 %; locator grep 112 → 0; full integration suite green |
| **P20** | W11/W12 (A:P9+P10) | Split `studio`; close `app`↔`mcp`; then seal — **two independently shippable series** | L-11, L-12, L-23, L-43 (bootstrap half), L-44, L-52, L-54 (+L-48 closure) | `studio` (L12); `Makefile:98-100`; `pyproject.toml:39` | P19 | W11: `test_composition_root_singularity.py`, acyclicity with empty `CYCLE_EXEMPTIONS`, `test_tool_input_schemas_populated.py`, `test_devharness_not_imported_by_production.py`, confirmation + roots + wheel + entry-point tests. W12: `test_no_shim_tokens.py`, `test_contracts_cover_tree.py`, per-module guards (`03` §3) | **B7 (W11):** `langgraph.json` → `orchestration/graph.py:graph`; `devharness` leaves the wheel; console script re-pointed | **W11 series green:** cycle ledger empty; one `bootstrap(role)`; graph compiles + resumes; both entry points resolve. **W12 series green:** `grep -rn "SHIM(W" src/` → 0; exemption ledger empty; the forbidden-edge set derived under `03` §4.6.1 (FES) is empty |

### 2.1 P↔W mapping (every wave of `03` §2.5 × the 21 phases)

`03` §2.5 delegates phase ids and ordering to this document while keeping `W0`–`W12`
as the design's internal spine; the mapping is therefore maintained **here**.

| Wave (`03` §2.5) | Phases | Wave exit condition (from `03`) | Satisfied by |
|---|---|---|---|
| **W0 — law with a ledger** | P0, P1 | law exists, green, cannot drift; baseline = high-water mark | P0 declares matrix/scope in `architecture.py` + pins enola; P1 adds `CONTRACT`s, the `tests/architecture/` suite `05` §2.1 enumerates (plus P0's manifest test) and the seeded ledger |
| **W1 — make the cycle true** | P2 | `CYCLE_EXEMPTIONS` empty; FES #1 deleted; mutation canary | P2 moves `product_gate` above `mcp` via `film_pipeline/entrypoints.py` and deletes FES #1 (`config → providers`, both sites) per `03` §2.5 W1 |
| **W2 — `filmspec` (O1)** | P3, P4 | mirrors real; duplicate-literal sweeps added | P3 moves the vocabulary; P4 burns down the 57 severity literals in the six carrying packages, the gate map and the action table |
| **W3 — `current_phase` single writer (O3)** | P5 | `STATE_CHANNELS.writers` → 1 | P5 collapses the eight writers and the routing-input channels |
| **W4 — registry agreement (O4)** | P6, P7, P8 (part) | `AgentRegistry(known_output_artifacts=…)` enabled; kinds declared | P6 enables the catalog agreement; P7 declares the kind set — including `CONSENSUS_REPORT`/`COST_ESTIMATE` per `03:208` — and creates `storage/contract.py`; P8 applies `03` D11 |
| **W5 — private imports (O7)** | P8 (part), P9, P10 | private-module ledger empty; `_base` renamed | P8 adds the read-time gate; P9 removes the 107+3 reach-ins; P10 completes the façade and renames |
| **W6 — persistence policy (O5)** | P11, P12 | −7 policy rows; one truth table | P11 unifies persistence precedence (and absorbs verify-10 `F-CRP-12`) and config resolution; P12 resolves KB root/id/provenance |
| **W7 — validation** | P13, P14 | single report writer; one dispatch table; band law | P13 reconciles registry+dispatch; P14 lands the writer, band and typed consensus |
| **W8 — generation + `budget`** | P15, P16 | spend ceiling derived once; projection moves up; budget extracted | P15 fixes the ledger; P16 moves the projection and creates `budget` with the derived ceiling |
| **W9 — `governance`** | P17 | C3 broken; `evaluate_phase` single source | P17 moves gate law + validators + `review/` |
| **W10 — `projects` + `operations`** | P18, P19 | −locator; two registries agree | P18 creates `projects`; P19 creates `operations` and deletes `_services` |
| **W11 — `studio` split** | P20-W11 | C2 closed; `langgraph.json` updated | P20-W11 splits `studio`, populates schemas, closes the cycle, re-points both entry points, drops `devharness` from the wheel |
| **W12 — renames + seal** | P20-W12 | target names; shim tokens 0; baseline empty | P20-W12 renames to the catalog, removes shims and asserts the empty ledger |

**Coverage: every wave of `03` §2.5 and all 21 phases P0–P20 appear exactly once** (P8 spans
W4/W5, P20 spans W11/W12 — the two seams `03` itself places one deliverable
across). Wave order is respected with no inversion: every phase's `Depends on` is
either an earlier phase in the same wave or a phase in a lower-numbered wave. P11
and P12 are independent of each other inside W6; P18 and P19 are ordered because
the operations split consumes the project registry.

### 2.2 The matrix home (reconciliation, not a fork)

The previous revision put the edge matrix in `scripts/architecture/edges.yaml`.
**That was wrong and is withdrawn.** `03` §4.3 now carries a **"Single declaration
home"** paragraph, and it is decisive:

> The matrix below has exactly **one** machine-readable home:
> `ModuleContract.may_import` in each package `__init__.py`, with the cross-module
> rows in the leaf `src/film_pipeline/architecture.py` (§2.6). **No second matrix
> file may exist — no `scripts/architecture/edges.yaml`, no `layers.yaml`, no
> JSON/YAML edge list** — because a second home is the same distributed-ownership
> failure this law exists to prevent (a typo'd YAML entry silently declares
> nothing, and the two homes drift with no test able to fail).

This document therefore **consumes that single root and creates no matrix file**:

- **P0** writes the `03` §4.3 matrix rows (as cross-module rows) and the scope
  classes of `03` §4.6.1 (FES) into `src/film_pipeline/architecture.py`
  (declaration data only, no `CONTRACT`s yet), plus
  `test_architecture_manifest_is_a_leaf`, `test_matrix_matches_03_4_3` and
  `test_scope_classes_cover_all_packages`. The forbidden-edge scope and the count
  are **owned by `03` §4.6.1 (FES)**, which `04` cites verbatim and never restates,
  narrows or recomputes: the guard derives the count from the manifest, never from
  prose (`03` D12).
- **P1** appends the per-package `ModuleContract` blocks (`may_import`, the
  observed edges at HEAD), the `tests/architecture/` suite `05` §2.1 enumerates
  (plus P0's manifest test), the seeded `Exemption` ledger and `make arch-check`,
  exactly as `05` §2.1–§5 specify.
- `scripts/architecture/*.py` survives only as **generated reproduce/report
  tooling** (`import_matrix.py`, `cycles.py`, `private.py`, `diff_norm.py`, enola
  wrappers). It is not authority, it is never hand-edited to change a rule, it
  emits no edge list, and its output is regenerated from the manifest.
- **No decision request is needed.** `03` §4.3 and `05` §2.1 agree on the home;
  the data-file alternative is rejected on their stated grounds (typed
  declaration, citation check, liveness, and a single authority).

## 3. Detailed phases

Execution follows `05` §6's playbook: Step 0 confirm the `L-NN` seam still exists
at the branch point and record the base commit; Step 1 inventory every site
mechanically; Step 2 declare the contract (red allowed only on the branch);
Step 3 create the module; Step 4 migrate writers **one at a time**, each commit
green; Step 5 delete the duplicates and prove it by re-running Step 1's command;
Step 6 pin it with a guard and delete the in-flight exemption rows; Step 7 update
docs; Step 8 run `make ci-check`; Step 9 roll back by reverting the merge commit.
Each phase records its `enola baseline pin` at the branch point and its
`enola check --fail-on=cycles,layers` delta (`05` §7.2). Each section ends with the
ownership-uniqueness check required at every intermediate commit.

### P0 — W0: pin baseline, declare matrix + scope in `architecture.py`

**Files.** New `src/film_pipeline/architecture.py` (leaf: the `Exemption`,
`ModuleContract`, `VocabularyMirror`, `StateChannel`, `RegistryAgreement`,
`PolicyPoint` types from `05` §2.2, plus the `03` §4.3 cross-module matrix rows and
§4.6.1 scope classes); new `tests/architecture/test_architecture_manifest.py`;
`Makefile` (`UV_CACHE_DIR` pin); `scripts/architecture/` reproduce tooling
(generated).

**Steps.**
1. `enola baseline pin .` at the branch point (`05` §7.2; the checked-in `.enola/`
   is stale — `main@4f802b1`, still containing the deleted `tui/` package). Phase-0
   posture is deliberately non-blocking: `enola check --warn-only .` until the
   mechanism is trusted.
2. Encode `03` §4.3's allowed-edge matrix as cross-module rows in
   `architecture.py` and the scope classes of **`03` §4.6.1 (FES)** — the normative
   definition, cited verbatim and not narrowed or recomputed here. **Do not**
   re-author a scope definition and do not restate the forbidden count; `03` owns
   both, and **do not create any second matrix file** (§2.2). Record the count the
   FES guard derives from the manifest as its *output* only.
3. Relocate proposal A's scratch analyses from `/tmp` into
   `scripts/architecture/` as generated report tooling (a concern whose reproduce
   command lives in `/tmp` is not reproducible, A:1347-1350). These scripts read
   the manifest; they never define it.
4. Pin `UV_CACHE_DIR=$PWD/.uv-cache` so test counts and coverage are comparable
   across phases, and record 2003 / 8 / 91.58 % in the PR template.

**Tests.** `test_architecture_manifest_is_a_leaf` (imports nothing from
`film_pipeline`); `test_matrix_matches_03_4_3` (every manifest row agrees with the
matrix, both directions); `test_scope_classes_cover_all_packages` (every package
in exactly one class); `test_forbidden_edges_are_derived_from_the_declared_scope`
(the count is computed by the FES guard and no prose constant for it exists
anywhere in `src/`); plus P0's manifest test alongside the `tests/architecture/`
suite files enumerated in `05` §2.1 (R2-O-17; the authoritative file list is
`05`'s, so it is cited and not counted here).

**Deletions.** `scripts/architecture/edges.yaml` is **not created** (withdrawn,
§2.2).

**Rollback.** Revert; `architecture.py` is inert data that no production module
imports.

**Evidence.** `enola baseline show`; the FES guard's derived forbidden-edge output
(the number is `03` §4.6.1's, printed by the guard, never written into `04`'s
prose); the `03` §4.3 matrix diff, empty.

**Ownership check.** One declaration root only: `docs/` is gitignored and
CI-exempt (`05` §2.1), so no second matrix can live beside it; the reproduce
scripts are marked generated-not-authoritative in the phase note.

### P1 — W0: law on — `CONTRACT`s, guard suite, exemption ledger

**Files.** All 17 current `src/film_pipeline/*/__init__.py` (append
`CONTRACT = ModuleContract(...)`, `may_import` = the observed edges at HEAD, per
`03` §2.6.2); `tests/architecture/{__init__,_harness,_readers,test_contracts,
test_boundaries,test_vocabularies,test_state_writers,test_registries,
test_exemptions}.py` (`05` §2.1/§5 — the authoritative suite file list is `05`'s,
plus P0's `test_architecture_manifest.py`); `Makefile` (`arch-check`); seed rows in
`architecture.py`.

**Steps.** Wire `05` §2.1–§5. Declare each package's observed edges; `graph` and
`mcp` keep `unrestricted_imports=True` **as the W0 observed-edge declaration
only** — the target law has no unrestricted modules (`03` D10) and each wave
tightens toward §4.3. Seed the `Exemption` ledger from the measured numbers
(§0.3), each row carrying `reason`, `citation` (pointing at `03`, not proposal B)
and `removal_phase: "W<n>"` (`05` §2.2's amendment makes the burndown
machine-readable): 107 private-module + 3 private-symbol sites (V4); the 10
forbidden edges under §4.6; the eight `current_phase` writers (L-35/L-50); the six
registry non-members and the 8/6 kind mismatch (L-18, recorded, not reconciled,
§4 DB-11); seven policy read sites (L-43); the 112 `_services` references (L-12);
the 57 severity literals in the six carrying packages (59 repo-wide) and 11
phase-order definitions (L-15/L-35); 64 direct `ArtifactStore` constructions
(L-47).

**Tests.** `test_exemptions.py` — non-empty `reason`/`citation`; citations resolve
to `03`; every subject is live; every guard family non-empty; source tree >200
files; the mutation canary (`05` §5.3). Plus
`test_contracts.py::{test_declared_edges_are_real,
test_declared_module_graph_is_acyclic}` — the latter is the **module**-granular SCC
check of `05` §5.3 (`module_edges()`), whose node set includes sub-package
directories, so it sees C1/C3/C4/C5 and not only the 17 package nodes (R2-O-5).
Subset runs pass `--no-cov` (see Evidence).

**Deletions.** None. The five existing bespoke guards are folded into the suite
where `05` §4 says so; otherwise they stay until P20.

**Rollback.** Revert the merge commit; no production behaviour changed.

**Evidence.** The red/green canary: add one synthetic private import on a scratch
branch, show `pytest tests/architecture --no-cov -q` fails naming the offender,
remove it and show it green. **`--no-cov` is required, not cosmetic:**
`pyproject.toml:80` puts `--cov-fail-under=90` in `addopts`, so any subset run
exits 1 on coverage rather than on the guard (`pytest
tests/unit/graph/test_channel_registry.py -q` → 28.00 %, exit 1; the same command
with `--no-cov` → exit 0). Every subset command in this document carries it, as
`05`'s guard commands do. `enola check --warn-only` report attached to the phase
note.

**Ownership check.** Every un-migrated site is named in the ledger with exactly one
owning wave; the guard fails on a new site, so nothing is simultaneously "allowed"
and "owned elsewhere".

### P2 — W1: make the cycle true; delete FES #1

**Files.** `app/product_gate.py:17`; new top-level `src/film_pipeline/entrypoints.py`
(the pre-image of `studio`, `03` C2 row); `config/profile_resolver.py:179` and
`:204` (FES #1's two sites); `CYCLE_EXEMPTIONS` in `architecture.py`.

**Steps.** Move `product_gate` above `mcp` into `entrypoints.py` so the edge
becomes legal `studio → mcp`; delete the `app → mcp` `CYCLE_EXEMPTIONS` row.
**Delete FES #1 (`config → providers`) in this wave**, as `03` §2.5's W1 row
prescribes: `:204`'s credential check moves to `providers.required_credentials`
called by the W1 `studio` pre-image, and `:179`'s `build_provider_adapter` inside
`register_project_providers` moves to the `operations` pre-image, re-pointing its
three call paths (`app/services/operator.py:147`, `mcp/tools/_profile_change.py:129`,
`mcp/tools/projects.py:192`). FES #1's definition and its membership in the count
are owned by `03` §4.6.1 and are not restated here. Then run the mutation canary.
This is the deliberate early pull-forward of A:P9's `product_gate` move (`03` §2.5
W1); the full `studio` split and the closing of C2 remain P20, and P9 consolidates
the credential *policy* (L-29) on the home this phase creates.

**Tests.** `test_declared_module_graph_is_acyclic` with an empty
`CYCLE_EXEMPTIONS`; `test_forbidden_edges_are_derived_from_the_declared_scope`
asserting FES #1 is no longer derived; the canary that a re-introduced `app → mcp`
import fails. Subset runs use `--no-cov`.

**Deletions.** The temporary top-level file is itself deleted in P20-W11 when
`studio` exists; the `app → mcp` `CYCLE_EXEMPTIONS` row and FES #1's two import
sites are deleted now.

**Rollback.** Revert; the move is an import relocation plus a new module whose only
caller is the gate, and FES #1's two sites revert with it.

**Evidence.** `enola check` reports one fewer cycle; the acyclicity guard is green
with no exceptions; `config` no longer imports `providers` at either site.

**Ownership check.** During P2 the cycle edge has exactly one home (the new
`entrypoints.py`); the old `app/product_gate.py` path is left as a `# SHIM(W1)`
re-export removed in P20-W12, so no consumer sees two live modules. The credential
*check* has one home (`providers.required_credentials`) from this commit; P9 then
owns the credential *policy* (env-var map, `.env` fallback, freshness), so the two
are never both authoritative.

### P3 — W2: extract `filmspec` vocabulary (A:P1) — L-15

**Files.** `schemas/_base.py` (280 lines: every enum moves); new `filmspec/`;
`graph/_action_routing.py`, `artifacts/paths.py`, `graph/graph.py`,
`graph/edges.py`, `graph/nodes/_repair_loop.py`, `constraints/_keywords.py`,
`graph/_agent_routing.py`; `agents/prompt_templates/registry.py` and the C1/C4/C5
source edges.

**Migration steps.** Pure relocation behind re-exports. Move `FilmPhase`,
`AgentRole`, `AgentFamily`, `ArtifactType`, `ArtifactStatus`, `IssueSeverity`,
`ValidationStatus`, `GenerationStatus` and the transition vocabulary; per `03` D7
and D11 `filmspec` also owns `PHASE_ORDER`, `PHASE_GATES`, `next_phase`,
`successor`, `gate_for`, the agnostic/generation-dependent sets, the phase-keyed
policy name sets and all 47 kind names. `schemas/_base.py` keeps `SchemaBase` and
gains `from film_pipeline.filmspec import *  # SHIM(W2)`. Delete the C1
(`prompt_templates/registry.py:100 → defaults`), C4 (`providers/__init__.py:9-13 →
adapters.*`) and C5 (`schemas/__init__.py:120 → registries`) source edges
(`03` §4.4).

**Tests.** `test_phase_order_is_derived_not_redeclared`; identity canaries
`schemas._base.X is filmspec.X`; the zero-outbound-import test.

**Deletions.** The enum definitions in `schemas/_base.py`; the duplicated phase
class sets; the three cycle-forming re-export edges **and their three
`CYCLE_EXEMPTIONS` rows**, which `05` §5.3 rule 2 makes mandatory — C1
(`agents.prompt_templates -> agents.prompt_templates.defaults`), C4
(`providers -> providers.adapters`) and C5 (`schemas -> schemas.registries`);
`test_cycle_exemptions_target_real_edges` reports a row whose edge is gone, so
deleting the edge and keeping the row fails (R2-O-19). C3's row is deleted by P17,
which breaks that cycle.

**Rollback.** Revert; the tree returns exactly to baseline.

**Evidence.** The L-15 mutation (add a 12th phase to `FilmPhase` only:
`_advance_result` computes `idx = -1` and returns `"wrap"`, ending the run early)
now fails a test; `enola check` shows C1/C4/C5 gone.

**Ownership check.** After P3, `filmspec` is the only module defining phase/kind
literals; every other table is a derived view or a declared partial index with
named omissions (`03` D7).

### P4 — W2: literal and table burndown (A:P2) — L-32, L-34, L-49

**Files.** The **57** severity sites across `graph`, `app`, `mcp`, `cli`,
`validation`, `config` (**59** repo-wide; `grep -rn --include='*.py' '"blocking"'
src/ | wc -l`); the **19** `_phase_gate_updates` source occurrences — **12** call
sites, **9** of them carrying an explicit `gate=` literal; the inline gate copy in
`graph/subgraphs/qc.py`; the router action vocabulary (`graph/_action_routing.py`)
vs `graph/edges.py`; `_NUMBER_WORDS` in `constraints/_keywords.py` and
`graph/nodes/_shared.py`.

**Migration steps (one commit per module).** Replace every severity literal with
`filmspec.is_blocking`/`blocking_issue`; replace `gate=` literals with
`gate_for(phase)` and derive `PHASE_GATES`; declare the router's
`ACTION → destination` table (the undefined `escalate_to_failure_handler`
currently falls through to `consistency_check`); collapse the two number-word
tables onto `constraints`. Per `03` §2.7.3 M2 the duplicate-literal sweep must
scan **every string constant (any position)**, not line-initial entries only.

**Tests.** The any-position duplicate-literal sweep and gate-map single-source
test; `test_router_action_vocabulary_matches_edges`; the scene-count agreement
table.

**Deletions.** The comparisons; the gate/agnostic literals; the inline qc gate
map; `_NUMBER_WORDS` in `graph/nodes/_shared.py`.

**Rollback.** Revert; per-module commits are independently green.

**Evidence.** The severity mutation as a permanent test; **57 → 0** outside
`filmspec/`; `escalate_to_failure_handler` resolves to one declared action.

**Ownership check.** Each module commit removes exactly one module's literals while
the ledger still lists the others; no commit leaves a literal site and the
predicate both authoritative in the same module.

### P5 — W3: orchestration state single writer + routing inputs (B:W3) — L-26, L-27, L-35, L-50, L-55

**Files.** `graph/state_schema.py`, `graph/orchestrator_state.py` (537 lines;
38/38 public surface), `graph/router.py`, `graph/edges.py`, `graph/nodes/_shared.py`,
`graph/nodes/prep.py:333`, `graph/nodes/wrapup.py:30-35`,
`graph/nodes/_repair_loop.py:72`, `mcp/tools/review.py:120`,
`app/services/operator.py` (`_recommendation`).

**Migration steps (writer-by-writer).** Collapse the eight `current_phase` writers
onto `orchestration`; register `consensus_report_ref`/`qc_patch_ref` in
`ORCH_CHANNELS` (they currently bypass the registry via `updates[key]`, `03` M21)
and finish or delete `_orchestrator__active_review_cycles` (M4); give `issues` one
model and one `is_blocking` plus one `may_approve` replacing four veto sites;
collapse `stalled_phase` to one state and one cap; make `FailureDecision` a typed
channel the failure-handling agent's output reaches; two-directional orchestrator
key parity with published accessors; one routing-decision channel and one
`describe_action(next_action)`.

**Tests.** `test_channel_registry.py` extended so every `STATE_CHANNELS` row has
one writer and the sweep sees **Name-subscript** writes (M21);
`test_orchestrator_key_sets_are_identical` (both ways); a stall-predicate table
test; a routing-decision round-trip test.

**Deletions.** Duplicate writers; `_stalled_phase`; the prefix minter copies; the
empty routing channel. `app/_graph_exec.py`'s reducers (L-36) are **not** deleted
here — P19.

**Rollback.** One revert. Channels are added or rerouted, never removed, so
LangGraph checkpoint/resume stays loadable.

**Evidence.** Writer sweep before/after; a shadow-assertion window for channels no
existing test covers; a blocked-consensus state makes `compute_actions` return
`handle_blockers`.

**Ownership check.** The commit that starts writing through the owner also removes
the old writer; the liveness check fails on a row whose site stopped writing, so a
half-migrated channel cannot look done.

### P6 — W4: agents catalog, prompts, model routing (A §5.8) — L-02, L-03, L-07, L-30, L-37, L-51

**Files.** `agents/mvp/__init__.py` (11 agents), `agents/impl/registry.py` (12
class keys, orphan `visual-dev-agent`), `agents/registry.py`,
`schemas/registries/agent_registry.py`, `graph/nodes/_context.py:27`
(`_AGENT_PROFILE_MAP`, 21 entries vs 11 agents, 10 orphan keys — V2/M6),
`agents/prompt_templates/registry.py`, `validation/validators/__init__.py`,
`agents/runner.py:43`, `schemas/prompt.py`, `validation/base.py:231-234`,
`agents/_json_extraction.py`, `mcp/tools/bibles/_shared.py:101-107`,
`kb/retrieval.py:51` + `film-knowledge-base/index/kb-manifest.yaml`.

**Migration steps (writer-by-writer).**
1. One descriptor table (`agent_id`, class, contract, `produces`) as the
   registration source; validate total and surjective; remove the orphan alias and
   reconcile `failure-handling-agent` (L-07).
2. **Resolve L-02 as O4 (V2/M6).** `AgentDescriptor.default_model_profile` becomes
   the **single profile authority**; delete `_AGENT_PROFILE_MAP`, delete the
   `ModelRouter().list_profiles()` + `"orchestrator"` alias authority, and correct
   the two tests (`tests/unit/graph/test_agent_profile_routing.py:21,25`) in the
   same commit.
3. Fix `ModelRouter.resolve` (or route through `select`) so the MCP bible path
   stops raising `AttributeError`; assert no MCP module imports
   `ModelAdapter.chat` directly. The lifecycle unification stays DB-9 (L-03).
4. One `TemplateKey` id space and a coverage invariant; fold `F-AGENT-11`'s
   identity branches into `AgentDescriptor` (M8); make the registry-agreement
   guard compare **values**, not only key sets (M9).
5. One RCTCO renderer grammar and one JSON-recovery strategy list (L-51).
6. Validate `applies_to_agents` at KB manifest load (L-30).

**Tests.** `test_catalog_parity.py` (`produces ∈ execute()`, set equality both
ways); `test_profile_map_matches_declared_contract` (replaces the wrong-value
assertions); `test_prompt_coverage.py`; `test_renderers_single_grammar.py`;
manifest-token validation.

**Deletions.** The orphan class key; the profile map; the dead renderer branch;
the second JSON-recovery implementation; the identity branches.

**Rollback.** Revert. The `resolve` fix repairs a path that currently raises, so it
cannot regress a working flow.

**Evidence.** L-02's map test fails today on two rows and passes after, with all
orphan keys gone; `set(AGENT_CLASS_BY_ID) == set(MVP_AGENTS)` was false (12 vs 11);
the real-model bible tool completes.

**Ownership check.** The map and the descriptor are never both authoritative: the
derivation/delete commit lands with the canonical declaration, or the ledger row
stays.

### P7 — W4: artifact kind set and ref grammar (R1/R3, 03 D4/D11) — L-57

**Files.** `artifacts/registry.py` (`_register_defaults`, `_spec`),
`schemas/_base.py`/`filmspec` (`ArtifactType`),
`graph/nodes/_context.py:300-319` (`_ARTIFACT_TYPE_BY_CLASS`),
`review/diff.py:70` (`_id_stem`), `schemas/artifact.py`, new
`src/film_pipeline/storage/contract.py` (six public names, `03` §3.6.1),
`artifacts/manifest.py` (`AssetManifest.kind`, `03` M19),
`graph/nodes/_shared.py` (`_UPSTREAM_CONTENT_SOURCES`, M2).

**Migration steps.** Declare the kind set once in `filmspec` — including
`CONSENSUS_REPORT` and `COST_ESTIMATE`, which `03` §2.5 W4 (`03:208`) requires in
the kind vocabulary; both names already exist in the registry at HEAD, so this is
declaration from data, not a new dependency (R2-O-14). Keep the kind catalog/specs
in `storage`, and **create** `src/film_pipeline/storage/contract.py` (six public
names, `03` §3.6.1) here; P8 extends it, it is not created twice (R2-O-13).
Replace `review/diff._id_stem` with the canonical formatter (L-57). Make
`_ARTIFACT_TYPE_BY_CLASS` a `storage.contract` lookup, but keep values until P8
removes the silent `SCRIPT` fallback. Per `03` D11, prepare the declaration of the
8 registry-only names and the three media kinds — the mechanical parity guard lands
here, the declaration lands in P8.

**Tests.** Registry↔kind parity, asserting the recorded difference is **exactly**
the 8 registry-only / 6 enum-only set (`test_registry_and_enum_agree`) — so the
test is red on any silent change to either side, not green on the mismatch it is
named after (R2-O-7); a second-formatter sweep; a construction test asserting no
map value the enum rejects; a test that `AssetManifest.kind` values are declared
kinds; a test that `CONSENSUS_REPORT` and `COST_ESTIMATE` resolve from `filmspec`
(the W4 vocabulary requirement).

**Deletions.** The second formatter; duplicate declarations of the second type
table (behaviour-preserving only).

**Rollback.** Revert; no persisted change.

**Evidence.** The R1 script before/after; `from_string(to_string(ref)) == ref`;
`grep -rn 'f"artifact:' src/` returns one site.

**Ownership check.** The kind **vocabulary** is in `filmspec` and the kind
**specs** in `storage`; the phase note states the split so neither looks like a
second authority for the same rows.

### P8 — W4/W5: storage single-writer authority + read gate (A §5.5, R3) — L-18, L-38, L-39

**Files.** `artifacts/store.py` (834 lines), `artifacts/registry.py`,
`artifacts/manifest.py`, `artifacts/project_storage.py`, `artifacts/paths.py`,
`storage/contract.py` (**created by P7, extended here** — R2-O-13),
`generation/ledger.py`, `graph/nodes/_context.py`, the
callers with `version=1` (`grep -rnE 'version\s*=\s*1\b' src/film_pipeline
--include='*.py'` → 6) and the four "latest + 1" re-derivations,
`generation/compositor/*` (03 M16: media bytes must go through `storage`).

**Migration steps (writer-by-writer).**
1. Route every `save` caller through store-assigned versions; delete the `version=`
   arguments (L-38/F-ARTIFACT-03; nine caller-side derivations, `03` D4).
2. `save_mutable` expresses `APPROVED` or documents the restriction; give
   `REJECTED`/`ARCHIVED` a reachable path (L-38/F-ARTIFACT-06).
3. **Read gate (Critical).** Route `load_mutable`, `load_metadata` and
   `list_artifacts` through the checked reader so `SchemaTooNewError` and the
   checksum apply everywhere, and validate `artifact_id` on read
   (F-ARTIFACT-05/12; `03` §2.7.2 moves this to W5). Ban the compositor's direct
   disk writes (M16).
4. **Kind declaration, not registration (`03` D11).** `filmspec` declares all 47
   registered names; the 8 registry-only names join the enum; `clip`,
   `last_frame`, `mid_frame` are declared **non-storable media kinds**;
   `checkpoint`, `invalidation_report`, `rollback_record` stay prefix-reachable.
   `storage.contract`'s guard asserts every `REGISTRY._exact` id is in `filmspec`
   and every `filmspec` kind is exact-registered, prefix-registered, or one of the
   three media kinds. Stored `artifact_type=script` labels are **not migrated**
   (D11: no reader keys on them). That assumption is not left as a caveat — it is
   **asserted** by the pre-P8 corpus fixture in Tests, which reads a corpus written
   in the old format through the new reader and requires identical results
   (R2-O-8).
5. Replace the `script` fallback with a loud refusal; one media/sidecar grammar
   (L-39; the reference-asset inventory is P15).

**Tests.** `test_storage_boundary.py` extended (L1-only imports, version rule);
`test_kind_declaration.py` (the D11 assertion); `test_artifact_id_validated_on_read.py`;
a corruption test for every read entry; a compositor-write-surface test; and the
**pre-P8 corpus fixture** (R2-O-8): a corpus written in the pre-P8 on-disk format
is read back through the new checked reader, asserting byte-identical artifact
bytes and that no stored `artifact_type=script` label is reinterpreted. Subset
runs use `--no-cov`.

**Deletions.** Hardcoded version arguments; duplicate "latest + 1" derivations; the
fabricated kind spec on read; the dead media-path helper; the denylist; the
`script` fallback.

**Rollback.** One revert. No on-disk migration is performed, so the property
holds; if a publisher later demands label migration it is a separate B7 PR.

**Evidence.** The 47 registered kinds round-trip; a `schema_version=2` mutable load
raises where it silently passed; checksum corruption fails on all read entries; a
traversal-shaped id is refused on read; the D11 guard's derived sets.

**Ownership check.** Steps 1–3 and 5 are inside `storage`; step 4 is additive
declaration, so no reader ever has two valid interpretations of a stored type.

### P9 — W5: private reach-ins and credential policy (A:P3) — L-29

**Files.** `providers/credentials.py` (`_env_var_for` → public `env_var_for`),
`config/profile_resolver.py:204` (move the credential check to
`providers.required_credentials`), `graph/services.py`, `graph/nodes/_shared.py`,
`app/_graph_exec.py:319,449` (the two private-symbol sites), `cli/driver.py:80-81`,
`agents/model_adapter.py:36`, `agents/_http_transport.py:18`,
`providers/__init__.py`, `schemas/registries/__init__.py`.

**Migration steps.** Publish `env_var_for`; move `config`'s credential predicate
into `providers` so L-29's id→env-var map, `.env` fallback and caching policy have
one home and one freshness rule; publish a `studio` runtime accessor so
`cli/driver.py` stops assigning module state; drop the concrete-adapter import;
promote the two `app/_graph_exec.py` private symbols or leave them on the ledger
for P19 — never both; complete the C1/C4/C5 edge removal begun in P3.

**Tests.** The private-import sweep with its ledger shrunk from the 107 + 3
baseline; the adapter-port guard; the config-does-not-import-providers guard;
identity canaries.

**Deletions.** The private alias `_env_var_for`; `config`'s credential predicate;
the concrete-adapter import; the cycle-forming re-export edges.

**Rollback.** Revert; no persisted representation touched.

**Evidence.** `enola check` shows no cycle and the private ledger shrinks by the
removed sites; L-29's rotation test — rotate a key between two lookups and assert
both adapters observe the new value (they disagree today).

**Ownership check.** The credential policy has one home from the commit that
publishes it; the two `app/_graph_exec` private symbols are on the ledger, not
silently re-exported in two places.

### P10 — W5: `schemas` public surface (B:W5) — L-48 (façade half)

**Files.** `schemas/__init__.py`; the 72 non-schema files importing
`schemas._base`; `schemas/_base.py` → `base.py`.

**Migration steps.** Add every public name to the façade, including
`TRANSITION_TYPES` and `LEGACY_TRANSITION_ALIASES` (the two names outsiders already
import that the façade omits, `03` §2.7.2); migrate the 72 importers one package
per commit; rename the module and leave `schemas/_base.py` as a `# SHIM(W5)`
removed in P20.

**Tests.** `test_no_private_base_import_outside_schemas`; façade completeness
enumerating `schemas.base`'s public names.

**Deletions.** The private import edges; at P20 the shim module.

**Rollback.** Revert; import-path-only.

**Evidence.** V4's count 72 → 0; mypy strict green after the rename.

**Ownership check.** Mid-migration, each commit moves one package while the shim
resolves to the same object; the façade and `base` never both define a name.

### P11 — W6: resolution policy — persistence + config (B:W1.5/6) — L-24, L-25, L-43 (persistence half), L-46, L-53

**Files.** `app/_persistence.py:41-42,51-53`, `graph/graph.py:43`,
`graph/services.py:31,48`, `app/logging_setup.py:80`, `mcp/server.py:243`,
`cli/run.py:226` (`NO_PERSIST`/`PERSIST_STATE`); `profiles/base.studio.yaml:43`
and `agents/model_routing/__init__.py` (`_FALLBACK_PROFILES`),
`config/validator.py:26`, `config/profile_resolver.py`, `app/services/operator.py:143`,
`mcp/tools/projects.py:107-113`, `graph/_agent_routing.py:204-211`,
`config/loader.py:30` + `config/bootstrap.py:34`, `KNOWN_DEAD_GROUPS`.

**Migration steps.** `resolve_persistence()` is the one truth table (six readers,
two formulas today; `03` §8 lists this as an **intentional documented behaviour
change**). It lands in the module that P20 renames to `studio` — today
`app/_persistence.py` — and P20's rename moves it without changing its body
(R2-O-13); this document names the pre-rename path so the product exists at the
commit that claims it. Make `ModelRouter.profiles` a required argument fed from
resolved config so the YAML is authoritative (L-24 — the verifier downgrade means
the remaining defect is the copy, not a live wrong model); one provider-lineup
normalizer so a festival stack against an all-mock profile produces the blocking
conflict it exists to produce (L-25); one `PROFILE_STACK_SLOTS` tuple and a writer
or deletion for `resolved_review_strategy` (L-46); one absolute `profiles/` root
and either proof or deletion for each numeric default (L-53).

**`F-CRP-12` and the `langgraph.json` entry object (R2-O-20).** `03` M41
(`03:390`) prescribes "no import-time side effect: the compiled graph is built by
`studio` *after* roots resolve", and `langgraph.json:4` currently names
`./src/film_pipeline/graph/graph.py:graph` while `graph: CompiledStateGraph =
build_graph()` sits at `graph/graph.py:201` (`03:829` lists `graph` as the module's
public contract). Removing the module-level attribute outright would break that
entry for nine phases with no phase documenting it, and no `ci-check` step would
notice. **P11 therefore keeps the attribute, lazily:** `graph/graph.py` gains a
module `__getattr__("graph")` that builds (and caches) the compiled graph only when
LangGraph asks for it, so importing the module performs no filesystem write while
`from film_pipeline.graph.graph import graph` still resolves. The guard asserts
both halves — no write on import, and the entry object resolves — and P11's B7 line
records that the *entry path* changes only in P20 (W11), the phase that edits
`langgraph.json`.

**verify-10 corrections absorbed here (`reviews/verify-10.md`, landed).**
`F-CRP-09`'s truth table reproduces byte-for-byte on the four required rows **but
its row-4 label `NO_PERSIST=0` is false under a presence test**, and its
storage-root sentence conflates "public default" with "effective root" — the phase
note states the corrected labels and the test asserts the corrected semantics.
The verifier's **missed seam `F-CRP-12`** (= `M1`, **Critical 5×5=25**,
`audit/10:30`) is owned here: **a bare `import film_pipeline.graph.graph` creates
`<storage root>/checkpoints/`, after which the app refuses its own storage root**
(`StorageRootError`). The guard
`test_bare_graph_import_does_not_poison_storage_root.py` imports the graph module
in a subprocess against an empty temp root and asserts no directory is created and
that a subsequent app bootstrap succeeds. This is the *fourth* storage-root
poisoning path, and it is why P11 — not P20 — owns the persistence truth table.

**Tests.** `test_persistence_truth_table.py` (all four flag combinations with
corrected row-4 labels, every consumer agrees);
`test_bare_graph_import_does_not_poison_storage_root.py` (**`F-CRP-12`**);
`test_graph_entry_object_resolves.py` (`from film_pipeline.graph.graph import
graph` succeeds and the import performs no filesystem write — the lazy
`__getattr__` half of R2-O-20); the config tests listed in §2; a subdirectory-CWD
corpus test. Subset runs use `--no-cov`.

**Deletions.** `_FALLBACK_PROFILES` — **deleted outright, not "or the YAML copy"**:
the YAML is authoritative and the code copy goes (R2-O-6); dead `KNOWN_DEAD_GROUPS`
entries; the duplicate `Path("profiles")`.

**Rollback.** Revert. The persistence precedence is the one behaviour change;
publish the truth table in the phase note.

**Evidence.** L-25 reproduced (no conflict) and then firing; the persistence mode
is identical in every entry point for the same env (today it differs); a bare
graph import leaves the temp root empty and a following bootstrap succeeds (today
it raises `StorageRootError`); the entry object still imports, so `langgraph.json`
stays valid until P20 (R2-O-20).

**Ownership check.** `_FALLBACK_PROFILES` is deleted in the same commit that makes
the YAML authoritative, so there is no merge state with two profile owners
(R2-O-6). The persistence truth table has exactly one home from that commit; the
six readers convert one at a time and the ledger row closes with the last.

### P12 — W6: KB root, id grammar, packet wiring, provenance — L-19, L-20

**Files.** `kb/paths.py:10-16`, `kb/packets.py:108`,
`graph/services.py:119,128-134`, `agents/runner.py:400,415`,
`graph/context_packets.py`, `graph/_agent_routing.py:196-201`,
`graph/nodes/_agent_artifacts.py:86`, `artifacts/store.py:279-289,536-553`
(`meta.json`), `app/bootstrap.py:42`, `app/smoke.py:55`,
`film-knowledge-base/index/kb-manifest.yaml` (phase tokens, `03` M3).

**Migration steps.** One `resolve_kb_root()` with env → explicit → repo-layout
precedence; delete the two `app` literals. One `KBContextId.for_packet(...)` so
`parse(ref)` round-trips; delete the two other minters. One provenance stamping
point so the **15** `ArtifactMetadata(` constructions route through it
(`grep -rn --include='*.py' 'ArtifactMetadata(' src/ | wc -l` → **15**; measured
literal `kb_context_ref=None` constructions: **0** — the seam is the constructor
default, not a literal, which corrects O-16). Wire `kb_builder` into both
`GraphServices` factories so the packet is real (L-19); delete the dead context
system; validate manifest phase tokens against `FilmPhase` at load.

**Scope includes the `meta.json` provenance write (R2-O-3).** The stamping point is
only observable if the ref is persisted, so P12 owns serialising `kb_context_ref`
into `meta.json` — the same phase that introduces the stamping point, not a later
one. This makes the acceptance below reachable by P12's own commits instead of
requiring a change its rollback excluded. Prompt rendering of packet content
remains DB-8 and is unrelated to this write.

**Tests.** `test_kb_path_literal_only_in_kb`; a changed-CWD root test; id
round-trip; mutable save→read preserves the ref; both factories build a non-empty
packet; unknown manifest token fails load. Subset runs use `--no-cov`.

**Deletions.** The two `app` path literals; two of three id minters; the dead
context system.

**Rollback.** One revert. **B7:** serialising `kb_context_ref` into `meta.json`
changes persisted representation; it ships in **this** phase as the program's
documented compatibility change — the phase note carries the before/after and the
reader tolerance for `null` refs written before it — rather than being excluded
from P12's scope and left unowned (R2-O-3).

**Evidence.** Root resolves identically from repo root and a temp CWD; every
`ArtifactMetadata` construction stamps through one function; a mutable artifact
saved with a ref reads it back (today `null`).

**Ownership check.** The stamping point is single from the commit that introduces
it; the 15 construction sites are never fixed individually before the owner
exists.

### P13 — W7: validator registry and dispatch (A §5.9) — L-13

**Files.** `validation/validators/__init__.py` (15 declared, never executed),
`validation/impl/*`, `validation/registry.py`, `graph/nodes/qc.py:361-368`,
`graph/subgraphs/qc.py:45-52,210-217`, `mcp/tools/validation.py:123-158`,
`agents/*` validator contracts, `config/validator.py`.

**Migration steps.** One declaration of validator identity, executed set derived;
agreement guard both directions and on **values** (the `scene-continuity-validator`
profile disagreement, `03` M9); one `PHASE_VALIDATORS` table consumed by both QC
paths — per `03` §2.7.2 there are **two** phase-keyed tables, not three, and
`_VALIDATOR_MAP`/`_WORKER_NODES` are not phase-keyed; make every declared phase
reachable through the tool (`03` M24); the delivery validator absent from both QC
paths is the first row fixed. Every `blocking_conditions` token is produced by the
validator that declares it.

**Tests.** `test_registry_agreement.py` (symmetric difference empty, values
compared); `test_dispatch_tables_agree.py`; unknown validator fails loudly.

**Deletions.** The three dead validator-contract definitions; the duplicate
dispatch tables.

**Rollback.** One revert; MCP `run_validation` responses keep their shape, though
the validator set becomes the union — document it.

**Evidence.** Declared-vs-executed difference before (non-empty on six ids) and
after (empty); a phase previously unreachable through `run_validation` now runs.

**Ownership check.** The registry declaration lands before the dispatch tables are
derived, in separate commits, with the guard asserting agreement between whichever
pair currently exists.

### P14 — W7: report writer, status band, consensus (A:P4) — L-10, L-14, L-58

**Files.** `graph/nodes/qc.py:166-182,392`, `mcp/tools/validation.py:187`,
`validation/base.py:245-290`, `validation/thresholds.py:25,32-40`,
`validation/consensus.py:66-71`, `graph/_action_routing.py:108-115` (read half
moves to P5), `post/delivery_packaging_agent.py:14`,
`graph/subgraphs/qc.py` + `graph/nodes/qc.py` (two QC artifact-resolution rules,
`03` M17).

**Migration steps.** `validation.run(...) -> ValidationReport` produces the
artifact once; `save_report`/`load_latest_report` are the only writer/reader; the
`qc` node stores `validation_report_ref`; the MCP path calls the same function.
**Per F-VR-02 (V1/`03` §2.7.2)** `NEEDS_REVISION` is reachable on the LLM path;
the defect is the zero-width `[block_below, review_at)` band in all 22 explicit
literals, so the guard asserts `block_below < review_at` and the four statuses are
reachable per registration. Fix the consensus defect — `ConsensusBuilder` receives
serialized dicts and the `AttributeError` is swallowed; pass typed objects and let
it surface; assert a typed `ReviewPackage` on **both** paths (`03` M17/F-VR-09).
Derive `requires_human_review` once (L-58). One artifact-resolution rule (M17).

**Tests.** AST sweep: exactly one `VALIDATION_REPORT` save outside `validation/`;
band invariant over the 22 literals; non-`None` consensus for a disagreement
fixture; `requires_human_review` agreement.

**Deletions.** The raw-dict report representation; duplicate writers; the
`except AttributeError: pass`; the second resolution rule.

**Rollback.** One revert. The report payload is unchanged; the typed
`consensus_report_ref` channel is additive, so old checkpoints resume (`03` §8).

**Evidence.** The band invariant holds for all 22 registrations (baseline: 22/22
have `block_below == review_at`); consensus is produced; both paths yield the
typed package.

**Ownership check.** The writer is single; the router-key read stays on the ledger
until P5 closes it, so it is never half-owned.

### P15 — W8: generation ledger lifecycle (A:P5 part) — L-08, L-16, L-56

**Files.** `generation/ledger.py` (282), `generation/executor.py`,
`generation/executor_delivery.py`, `mcp/tools/generation/{dispatch,planning}.py`,
`graph/nodes/generation.py:44`, `graph/nodes/_generation_batch_planning.py`,
`app/services/_generation_ops.py`, `artifacts/manifest.py`,
`mcp/tools/reference_generation/entries.py`.

**Migration steps (writer-by-writer).** One transition API rejecting illegal
`(from, to)` pairs (10 sites in 2 modules; `CANCELLED` after `COMPLETED` persists
today); fix the MCP submit path to send resolved prompt text, not `prompt_ref`;
fix the MCP poll path to call the delivery that downloads media and records the
manifest; collapse the untyped reference status onto `GenerationStatus`; stop
marking shot-matrix rows `generated` at planning time; expose
`load_or_none`/`ensure` so reading does not create a ledger (L-56); register
reference assets in `AssetManifest` (L-39 inventory); use the enum for provider
status (M14) and one scene-id default (M15).

**Tests.** Provider-call capture asserting the resolved prompt; poll test asserting
media + manifest; exhaustive `(from,to)` matrix; read-leaves-directory-unchanged;
every emitted status is an enum member.

**Deletions.** The second status writer; ad-hoc status literals; the
ledger-creating read path; the second reference-asset catalog.

**Rollback.** One revert; ledger payload and revision semantics preserved.

**Evidence.** The three named defects each get a before/after test; an
`IN_PROGRESS → COMPLETED` transition without evidence is refused.

**Ownership check.** The ledger manager is the only row mutator at every commit;
until a caller migrates, the ledger names the caller and the manager never writes
on its behalf.

### P16 — W8: generation projection, cost/ceiling, and the `budget` module (A:P5, 03 D5) — L-40, L-41, L-01

This phase carries the W8 tail: the ledger→state projection moves up, the cost
model gets one source, and the `budget` module `03` D5 places at L5 is created. It
is one phase because the ceiling the planner derives (L-41) is exactly the value
the spend gate compares (L-01); splitting them would leave the ceiling
authoritative in two places for a phase.

**Files.** `mcp/tools/generation/planning.py`
(`_sync_generation_requests_from_ledger`), `graph/state_schema.py:44`,
`graph/nodes/_shared.py:163-188`, `mcp/tools/generation/_text_only.py:9`,
`app/_resume.py:14`, `providers/pricing.py:36`, `generation/ledger.py:99,276`,
`graph/nodes/_generation_batch_planning.py:42-45`, `app/mock_responses.py`;
new `src/film_pipeline/budget/` (`BudgetState`, `cap_for`, `authorize_spend`,
`record_spend`, `SpendRecord`); the cap derivations in
`mcp/tools/planning.py:33`, `constraints/extractor.py:286-293`,
`graph/nodes/_context.py:422-427`, `generation/ledger.py:264-277`,
`graph/orchestrator_state.py:59`; the eight refusal gate sites
(`generation/ledger.py:264-277`, graph/router/operator gates); the sixth cap
vocabulary in `graph/context_packets.py:121-123` (F-BUD-06/`03` M33); the MCP
`approve_generation_spend` default `-1.0`; `ProjectProfile.budget_cap_usd`
(`03` M34).

**Migration steps (writer-by-writer).**
1. Move the ledger→state projection up into
   `graph.project_generation_requests` — the module P20 renames to
   `orchestration` — named here at its pre-rename path so the product exists at
   the commit that claims it (R2-O-13); delete the MCP copy. One
   generation-request identity and one stale-code set shared by both consumers,
   parameterised over every id-key subset (L-40).
2. One cost estimate and one shot-duration constant; mock response cost derives
   from `pricing`; the ceiling is derived in one place (L-41). `providers.pricing`
   stays the rate authority.
3. Create `budget` at L5 with one `BudgetState` document, one `cap_for`, one
   `authorize_spend` and one `record_spend`; durable through `storage`.
   `generation` calls `authorize_spend` before dispatch and `record_spend` after
   completion; `governance` consumes the verdict as a value and keeps zero state
   (03 D5). Collapse the cap readers to one and the refusal path to one.
4. **The MCP `approve_generation_spend` default changes from unlimited to the
   estimate-derived ceiling — the program's documented intentional behaviour
   change** (`03` §8, D5; a test asserts both paths agree).

**Tests.** Projection single-writer sweep; reducer/filter agreement over every id
subset; mock cost equals `pricing`; `test_budget_single_source.py` (one cap reader,
one refusal path); `test_spend_recorded.py` (`remaining_usd = cap - spent`,
currently always equal to the cap); `test_ceiling_agreement.py` (graph ≡ MCP); a
test that no second cost model exists; `test_budget_gate_matrix.py` over every
phase × `(cap, spent)` pair.

**Deletions.** `_sync_generation_requests_from_ledger` from `mcp`; the second
dedup key; the three stale-code copies; the duplicate duration constants; the four
independent cap derivations and the sixth vocabulary; the seven inert refusal
sites; the `-1.0` default.

**Rollback.** One revert per concern (projection, cost, budget); the ledger
artifact shape is unchanged.

**Evidence.** L-41's mutation (rate 0.18→0.36) fails a single-source test after the
phase; a shot-id-only request is deduped identically by filter and reducer; at
baseline `spent_usd` is always 0 and `remaining_usd` always equals the cap, and
after P16 a mock batch records a real sum; L-01's executed divergence (cap 100 via
MCP vs "$50" in the idea) yields one verdict.

**Ownership check.** The projection moves in one commit that deletes the MCP
writer in the same commit — there is no window in which both project
`generation_requests`. The cap/refusal/spend authority moves in one commit that
deletes the previous readers in the same commit, and `governance` never receives
state, only a verdict value (03 D5).

### P17 — W9: extract `governance` / advancement (A:P6) — L-06, L-31

**Files.** `graph/_action_routing.py:325` (`_advance_result`; `compute_actions`
stays in orchestration), `graph/orchestrator_validators/` (5 files),
`graph/consistency.py`, `graph/scope_contract.py`, `review/*` (4 files),
`graph/edges.py:40-54`, `graph/nodes/approval.py:113-190,221-249`,
`app/_graph_exec.py:425-445`, `mcp/tools/review.py`, `app/services/operator.py`,
`schemas/approval.py:12`.

**Migration steps.** Introduce `advance_decision(...)`/`evaluate_phase(...)` as the
only producer of a phase decision; move the gate law, the orchestrator validators
and `review/*` into `governance`; keep `graph._action_routing` as a `# SHIM(W9)`
re-export; make `graph.edges`, `graph.nodes.approval`, `review`, `app` and `mcp`
call it. **This is where L-06 is fixed:** the graph refuses to enter `generation`
while providers are blocked, while the app/MCP `approve_phase` path indexes
`PHASE_ORDER` with no provider check (executed divergence:
`continue_unrelated_work` vs `generation`); the two successor implementations
collapse onto `filmspec.successor`. L-31's **seven** gate-decision sites, the
ad-hoc review package on the LangGraph path and the `ApprovalAction` vocabulary
gap all route through it. `governance` is stateless and may not import
`orchestration` — that is what breaks C3.

**Tests.** `test_gate_decision_is_single_source.py` (matrix over phase, reports,
issues, config); `test_governance_imports_nothing_above_l8.py` (anti-cycle); a
typed `ReviewPackage` on both paths; every `ApprovalAction` member has a handler.

**Deletions.** The app/MCP duplicate advances; the second blocking filters; the
ad-hoc review-package dict; the test that replicates the production predicate.

**Rollback.** One revert; the shim reverts with it. The divergence fix changes
operator-visible gating intentionally — record it.

**Evidence.** L-06's reproduced divergence returns one decision on both paths;
`enola check` shows C3 gone.

**Ownership check.** Until the last caller migrates, the shim delegates rather than
re-derives; the guard asserts the legacy entry point and the owner agree over a
matrix of states.

### P18 — W10: extract `projects` (A:P7) — L-42 (audit half), L-45 (registry half)

**Files.** `app/runtime.py:36-52`, `mcp/tools/helpers.py:34-47`,
`mcp/server.py:142-177` and the write-only `MCPServer.active_project_id`
(F-MCP-14/`03` M30), `app/safety.py:131-132`, `app/_persistence.py`.

**Migration steps.** Create `ProjectRegistry`/`ProjectCatalog`
(`create/get/list/resolve/set_active/active`) that always writes `project_kind`,
read by `mcp`; `StudioRuntime.projects`/`active_project_id` delegate; delete the
server's write-only active pointer (M30); the two registries agree with no lazy
fallback. Reconcile the in-memory map with the on-disk record on every mutation.
Stop keying audit persistence on live registry membership so deletion reaches disk
(L-42 audit half; verify-10's `F-CRP-11` reproduced exactly this: archived audit
log `['create_project']` vs in-memory `['create_project', 'delete_project']`).
Persistence roots remain P20 (L-11); checkpoint history is DB-6.

**Tests.** `test_single_active_project_authority.py` (AST sweep including the
server attribute); memory ≡ disk; both creation paths equal; delete writes both
audit events.

**Deletions.** The second registry in `mcp/tools/helpers.py`; the server field.

**Rollback.** One revert; `resolved_project_id` semantics unchanged.

**Evidence.** L-45's executed divergence (deletable via MCP, protected via the
operator) yields one classification; the archived audit log contains
`delete_project`.

**Ownership check.** The write-only server state is deleted in the same commit the
registry becomes the pointer writer.

### P19 — W10: extract `operations`; kill the locator (A:P8) — L-36 (+halves)

**Files.** `app/services/` (**7** `.py` files — `ls src/film_pipeline/app/services/*.py
| wc -l`) → `operations/`; `mcp/tools/**` (**39** `.py` files — `find
src/film_pipeline/mcp/tools -name '*.py' | wc -l`); `mcp/tools/helpers.py:70-73`;
`mcp/tools/__init__.py:15-22`; `app/_graph_exec.py:455-484` (reducers),
`graph/state_schema.py` (`REDUCERS`).

**Migration surface, enumerated (R2-O-19).** The review is right that this phase is
a mechanical migration whose size was unstated. Measured at `fb85baa`:

| Surface | Count | Reproduce |
|---|---|---|
| `app/services/*.py` | **7** | `ls src/film_pipeline/app/services/*.py \| wc -l` |
| `mcp/tools/**/*.py` | **39** | `find src/film_pipeline/mcp/tools -name '*.py' \| wc -l` |
| test references to `get_runtime` | **325** refs / **123** files | `grep -rn 'get_runtime' tests/ \| wc -l` ; `grep -rln 'get_runtime' tests/ \| wc -l` |
| test references to `_services` | **131** refs / **72** files | `grep -rn '_services' tests/ \| wc -l` ; `grep -rln '_services' tests/ \| wc -l` |
| files importing `film_pipeline.cli` | **7** | `grep -rlE '^[[:space:]]*(from\|import)[[:space:]]+film_pipeline\.cli' tests/ \| wc -l` |
| files importing `film_pipeline.app` | **69** | `grep -rlE '^[[:space:]]*(from\|import)[[:space:]]+film_pipeline\.app' tests/ \| wc -l` |

The review's 243 refs / 41 files (`get_runtime`) and 83 / 24 (`_services`) are not
reproducible under the whole-suite scope or the narrower `tests/unit` scope
(295/102 and 79/42); the measured whole-suite numbers above are used. The migration
is one tool group per commit precisely because the test surface is ~two orders of
magnitude larger than the production surface, which is why this phase stays sized
**L** on the measured counts, not on the review's smaller ones.

**Migration steps.** One **tool group per commit** (bibles, generation, review,
planning, validation, artifacts, projects); each handler becomes a call on a
constructor-injected `OperatorBackend`; tests migrate from monkeypatching the
package `get_runtime` to injection; the locator is deleted last. Export the
`REDUCERS` map and have `_graph_exec` consume it (L-36). Route the MCP
bible/assembly tools through the agent catalog (L-03 lifecycle half). Give
`OperatorService` mutators the registry's confirmation contract (L-45 operator
half).

**Tests.** `test_mcp_does_not_touch_domain_modules.py`; constructor-injection
guard; `test_reducers_shared_with_schema.py`; the MCP contract-freeze snapshot.
Subset runs use `--no-cov`.

**Deletions.** `_services`; the `get_runtime` package attribute; the monkeypatch
indirection; the re-implemented reducers; the duplicate `next_action` prose.

**Rollback.** One revert per tool group; the locator deletion is independently
revertible. The `_services` **graph state channel stays** (`03` §8).

**Evidence.** `grep -rn "_services" src/` 112 → 0 while `_services` remains
declared in `state_schema`; the `get_runtime` test-reference count (325) falls to
0 across the same commits; contract freeze green; the full integration suite — not
coverage — is this phase's acceptance evidence.

**Ownership check.** Each group converts every handler before deleting the group's
locator calls; the locator reference count is reported per commit.

### P20 — W11/W12: split `studio`; close `app`↔`mcp`; seal (A:P9+P10) — L-11, L-12, L-23, L-43 (bootstrap half), L-44, L-52, L-54, L-48 (closure)

This phase carries two wave deliverables in one id — the split (**W11**) and the
seal (**W12**). Because `03` §2.5 pins the id range to `P0`–`P20`, the *id* is not
split; **the phase is**, into two commit series that are each independently
shippable, independently green and independently revertible (R2-O-21). B5 is
evaluated at series granularity and holds for both; a reader must not read "P20" as
one acceptance gate.

#### P20-W11 (W11) — split `studio`, close `app`↔`mcp`, move the entry points

**Files.** `app/product_gate.py`/`entrypoints.py` → `studio`; `app/runtime.py`
(reduced to wiring); `app/{bootstrap,health,logging_setup,safety,smoke,version,
_persistence,_provider_seeds,_resume}.py`; `cli/{run,driver,io}.py`;
`mcp/server.py`, `mcp/_stdio_transport.py` (F-MCP-13), `mcp/contract.py:52` +
`mcp/tools/registry.py:110-117`, `mcp/errors.py:15`, `mcp/tools/helpers.py:33-35`,
`mcp/envelope.py:28`; the five roots (`artifacts/storage.py:79`, `cli/driver.py:69`,
`app/runtime.py:75-77`, `graph/graph.py:46`, `app/_persistence.py:41-42`);
**`Makefile` (`:98-100`)**; **`pyproject.toml` (`:39`, plus the existing
`:59,95-98`)**; `langgraph.json`.

**The two entry points no earlier phase updates (R2-O-1).** Both are real gates:

- `Makefile:98-100` runs `$(UV_RUN) python -m film_pipeline.app.product_gate`, and
  `product-gate` is a prerequisite of both `ci-check` (`Makefile:108`) and
  `ci-verify` (`Makefile:111`, the GitHub Actions target). Moving `product_gate`
  into `studio` must re-point this target **in this series**, or `ci-verify` fails
  on a moved module.
- `pyproject.toml:39` declares
  `film-pipeline-run = "film_pipeline.cli.run:main"`. Moving `cli/*` to `studio`
  must re-point the console script in the same series.

The test files that import the moved packages — **69** importing
`film_pipeline.app` and **7** importing `film_pipeline.cli` (`grep -rlE
'^[[:space:]]*(from|import)[[:space:]]+film_pipeline\.app' tests/ | wc -l`, and the
same for `.cli`; full surface in P19) — migrate with their module; any that cannot
is named in the phase note.

**Migration steps.** Move `product_gate` into `studio` (above `mcp`) and re-point
`Makefile:98-100`; delete the `get_runtime` indirection and the temporary
`entrypoints.py`; move `cli/*` to `studio` and re-point `pyproject.toml:39`; reduce
`StudioRuntime` to services scope + graph handle + logging. One
`invoke_tool(name, args, *, actor)` used by the stdio transport, the CLI driver and
the scripts, with confirmation and project resolution on all four paths, actor
attribution and the typed code carried through the transport (F-MCP-13; L-44,
L-52). One `bootstrap(role) -> Runtime` for all entry points (L-43 bootstrap half,
building on P11's truth table). One `RootLayout(storage_root, runtime_root,
checkpoint_root, run_root)` resolved once (L-11). Populate tool argument models and
JSON Schema before the gate (L-23); one `authorize(...)` and danger-from-behaviour
(L-44); one typed `MCPError` (L-52, M28/M29). `testing` → `devharness` leaves the
wheel (L-54; `03` D6) while **`app/mock_responses.py` stays in `studio`** (D6 — do
not move it).

**Tests (W11).** `test_composition_root_singularity.py`; acyclicity with empty
`CYCLE_EXEMPTIONS`; `test_tool_input_schemas_populated.py`;
`test_devharness_not_imported_by_production.py`; one confirmation contract for the
10 gated tools; `test_roots_resolve_identically.py`; `test_bootstrap_single_role`;
a wheel-contents test; an invocation test that all four entry points refuse an
unconfirmed destructive tool; and an **entry-point test** asserting
`python -m <studio>.product_gate` and `film-pipeline-run --help` both resolve from
the installed wheel. Subset runs use `--no-cov`.

**Deletions (W11).** The dead `requires_confirmation` and `idempotency_key_field`
fields; the `testing` wheel inclusion; two of three bootstrap re-derivations; four
of five root resolutions; `entrypoints.py`.

**Acceptance (W11 — independently green).** `make ci-check` passes with the moved
entry points and the re-pointed `Makefile`/`pyproject` targets, coverage ≥90 %,
`enola check` reports zero cycles and zero layer violations, all four entry points
bootstrap identically, a checkpoint written before this series resumes, a CLI run
leaves the storage root openable by the app, and the wheel contains `devharness`
but not `testing`. **B7 (W11):** `langgraph.json` →
`./src/film_pipeline/orchestration/graph.py:graph` (object name and graph id
unchanged); the console script re-points to the `studio` path; `devharness` leaves
the wheel.

**Rollback (W11).** One revert per module group plus one for the entry-point
commits. No shim is removed in this series, so the pre-W11 tree is fully
restorable.

#### P20-W12 (W12) — seal: rename to the catalog, remove shims, empty the ledger

**Files.** Every `# SHIM(W<n>)` re-export (`schemas/_base.py`,
`graph/_action_routing.py`, `app/services/operator.py`, `app/product_gate.py`, …);
the final module renames to the `03` catalog; the per-module guards of `03` §3.

**Steps.** Rename modules to the target catalog; delete every shim; empty the
exemption ledger; add the per-module guard tests not already present; make the
checker fail if any `SHIM(` token remains (`03` D9).

**Tests (W12).** `test_no_shim_tokens.py`; `test_contracts_cover_tree.py`; the
anti-vacuity canary still proves each guard can fail. Subset runs use `--no-cov`.

**Acceptance (W12 — independently green, the seal last).** `make ci-check` passes
with the target names; `grep -rn "SHIM(W" src/` → 0; the exemption ledger is empty
with every guard family still non-empty; the matrix is re-derived at HEAD and its
forbidden-edge set derived under `03` §4.6.1 (FES) is empty; W11's entry-point
test still passes against the renamed modules.

**Rollback (W12).** One revert. Internal only: external contracts are frozen and
`03` D9 makes the shim set a recorded burndown rather than a runtime mechanism, so
reverting restores the shims without touching on-disk state. **W12 is the last
series and can be deferred indefinitely without leaving the tree in a broken
state**, because every shim it removes is a working import path until it does.

**Ownership check (both series).** The cycle break, the invocation unification, the
root layout, the entry-point re-pointing and the rename/shim removal are separate
commits, each independently green; the P0 matrix guard is re-run after each and
must show no new forbidden edge.

## 4. Deferred backlog — do not start here

`03`'s wave spine (W0–W12) carries the program's critical correctness work; nine
ledger concerns sit outside every wave in `03` and remain deferred here with a
named trigger. **DB-1 (budget) is retired as a deferral**: `03` D5 and W8 schedule
the `budget` module, and this roadmap executes it inside **P16**.

| # | Deferred work | L | Why not now | Trigger / earliest phase |
|---|---|---|---|---|
| ~~DB-1~~ | ~~Full budget/spend authority~~ | L-01 | **Scheduled by `03` D5/W8** | **P16** (this document) |
| **DB-2** | Post-production models, `AssemblyAgent`, `assembly_manifest` | L-04 | Two `AssemblyAgent` classes with disjoint fields, every post model defined twice, one artifact id written by two incompatible schemas. Needs gate authority before a writer can be chosen. | after P17 |
| **DB-3** | Delivery-completeness and delivery-manifest seam | L-05 | Two owners already disagree (`is_complete=True` beside a `blocked` validator with five findings); QC probes `delivery_manifest` while post writes `delivery_package` (`03` M35/M36 add two more names). | after P17 |
| **DB-4** | Provider health, registry, failure classification | L-09, L-28 (+L-27 classifier half) | Four health representations (two graph channels, `03` M12), the checkpointed one routing reads has **no producer**; two same-named registries, neither production; `FailureClassifier` has zero production callers. Consumes the state model and the provider policy, **not** a gate verdict, so it is decoupled from the governance phase (R2-O-12). | after P9 |
| **DB-5** | QC lifecycle unification | L-17 | Two *live* lifecycles with different state keys, validator sets and findings→issues mappings; removing one needs an equivalence harness. | after P14 |
| **DB-6** | Checkpoint metadata + resume/rollback lifecycle | L-21, L-22, L-42 (residual) | Two in-memory registries (rollback validates against one, executes against the other), two resume implementations plus a write-only snapshot, a hand-maintained invalidation graph. **`reviews/verify-10.md` has landed** — 11 CONFIRMED / 2 DOWNGRADED (`F-CRP-05` High→Medium, `F-CRP-10` High→Medium) / 0 REJECTED — so L-21/L-22 are verified, and the verifier's **missed seam `F-CRP-12` (= M1, Critical 5×5=25)** is carried by **P11** (bare `import film_pipeline.graph.graph` poisons `<storage root>`), not here. This entry keeps the remaining checkpoint/resume/rollback machinery (F-CRP-02/04/06/07/08). | after P18 and P20-W11 |
| **DB-7** | Test doubles → one harness | L-33, L-47 | 64 direct `ArtifactStore` constructions, an unguarded production-separation invariant, an unparity-tested git double, canned payloads bound to no schema, mock-provider entries that disagree. L-33 stands on F-TEST-01/07; **`F-TEST-02` is a withdrawn stub carrying no Severity bullet and is not a justification**. `03` D6 binds the canned payloads in W4 and keeps `mock_responses.py` in `studio`. | after P20-W11 |
| **DB-8** | KB packet content rendered into prompts | L-19 (render half) | The graph runs on a synthetic packet and the template path discards the packet, rendering only its id — **feature completion**, not ownership extraction. P12 lands construction and wiring; this is the remaining render half and is deliberately outside P12's acceptance (R2-O-11). | after P12 |
| **DB-9** | Agent lifecycle unification (MCP bible path) | L-03 (lifecycle half) | Four MCP-only agents invisible to the roster; reconciling the two lifecycles requires the operations split first. | after P19 |
| **DB-10** | Storage layout / on-disk v2 format changes | — | The storage subsystem is the one properly owned, guarded subsystem; `03` D4 extends its guards and never rewrites it. | never in this program |
| **DB-11** | Artifact-kind reconciliation by naive set-difference | L-18 | Resolved differently: `03` D11 declares the 47 registered names canonical, adds the 8 registry-only names to `filmspec`, and declares the 3 media kinds non-storable; stored `script` labels are not migrated. A naive diff is still forbidden as an approach. | P7 guard → P8 declaration |
| **DB-12** | Credential policy freshness across all sites | L-29 (residual) | P9 publishes one `env_var_for` and one policy home; unifying the `.env`-vs-process-env split for config knobs also touches P11 and P20. | after P20 |

Rejected outright: renaming MCP tools; adding a runtime feature flag
(`if os.getenv("MODULAR_V2")`) — if a toggle seems necessary, the phase must be
split (`05` §6 step 9).

**Why the deferred set is safe.** Eight of the nine deferred concerns are defects,
but each sits downstream of an authority a scheduled phase creates (L-04/L-05 need
L-31's gate decision; L-09/L-28 need the state model from P5 and the gate from
P17). The one drift-risk concern, L-22, is entangled with L-21's two registries,
both verified by the landed verify-10 with zero rejections. Deferring them keeps
their exemption rows visible rather than shipping another representation of a
state no phase can yet own.

## 5. Progress tracking

One row per deliverable: 21 phase ids, with **P20 carried as two series rows**
(`P20-W11` and `P20-W12`) because each series is independently shippable and has
its own green state (R2-O-21). All statuses start **Not started**. Update in place;
this table is the program's single progress record.

| Phase | W | Name | L retired | Size | Status |
|---|---|---|---|---|---|
| P0 | W0 | Pin baseline; declare matrix + scope | L-48 (matrix) | M | Not started |
| P1 | W0 | Law on: `CONTRACT`s + guards + ledger | L-48 (enforcement) | M | Not started |
| P2 | W1 | Make the cycle true; delete FES #1 | L-12 (early edge) | M | Not started |
| P3 | W2 | Extract `filmspec` vocabulary | L-15 | S | Not started |
| P4 | W2 | Literal/table burndown | L-32, L-34, L-49 | S | Not started |
| P5 | W3 | Orchestration state single writer | L-26, L-27, L-35, L-50, L-55 | L | Not started |
| P6 | W4 | Agents: catalog, prompts, routing | L-02, L-03, L-07, L-30, L-37, L-51 | L | Not started |
| P7 | W4 | Artifact kind set + ref grammar | L-57 | S | Not started |
| P8 | W4/W5 | Storage single-writer authority + read gate | L-18, L-38, L-39 | L | Not started |
| P9 | W5 | Private reach-ins + credential policy | L-29 | M | Not started |
| P10 | W5 | `schemas` public surface | L-48 (façade) | M | Not started |
| P11 | W6 | Resolution policy: persistence + config (verify-10 `F-CRP-12`) | L-24, L-25, L-43, L-46, L-53 | M | Not started |
| P12 | W6 | KB root, ids, packet wiring, provenance | L-19, L-20 | M | Not started |
| P13 | W7 | Validator registry + dispatch | L-13 | M | Not started |
| P14 | W7 | Report writer, status band, consensus | L-10, L-14, L-58 | M | Not started |
| P15 | W8 | Generation ledger lifecycle | L-08, L-16, L-56 | L | Not started |
| P16 | W8 | Projection, cost/ceiling, `budget` | L-40, L-41, L-01 | L | Not started |
| P17 | W9 | Extract `governance` / advancement | L-06, L-31 | L | Not started |
| P18 | W10 | Extract `projects` | L-42, L-45 | M | Not started |
| P19 | W10 | Extract `operations`; kill the locator | L-36 (+halves) | L | Not started |
| P20-W11 | W11 | Split `studio`; close `app`↔`mcp`; move entry points | L-11, L-12, L-23, L-43, L-44, L-52, L-54 | L | Not started |
| P20-W12 | W12 | Seal: rename to the catalog, remove shims, empty the ledger | L-48 (closure) | S | Not started |

**Rule for marking a phase done.** All five must hold, each demonstrated rather
than asserted:

1. **Scope complete.** Every `L-NN` the phase retires has its Step-1 inventory
   command re-run and now returns the owner only, or the residue is carried
   forward as a recorded exemption naming the wave that closes it. The phase leaves
   no concern with two authoritative owners.
2. **Guard fails on regression, demonstrated.** The phase's guard test is shown red
   against a synthetic re-introduction of the seam, then green with it removed. A
   guard that cannot fail is guard theatre (`05` §8.1). Subset runs must pass
   `--no-cov`, because `pyproject.toml:80`'s `--cov-fail-under=90` makes any subset
   exit 1 on coverage rather than on the guard (R2-O-4; the reasoning and the
   measured 28.00 % run are in P1).
3. **`make ci-check` green** with coverage ≥90 %, test count ≥ the baseline's 2003
   passed / 8 skipped, and coverage not below the recorded per-phase floor
   (baseline 91.58 %). The phase also attaches its `enola check
   --fail-on=cycles,layers` delta, which must be non-regressing (`05` §7.2). **For
   P20 only, “the phase” means the series being landed:** `P20-W11` and `P20-W12`
   each satisfy rules 1–5 on their own commit series, so B5 is met at series
   granularity rather than as the union of split and seal (R2-O-21).
4. **Docs updated.** `AGENTS.md`'s sub-package roster and ownership one-liner when
   a module moves, plus the phase note recording the `L-NN` ids, the wave, the
   guard file, any B7 change and the enola delta.
5. **No new exemptions beyond the declared ones.** The ledger never grows past the
   P1 high-water mark except for rows declared in this roadmap and cited (03 L8).

## 6. Estimated size and critical path

Sizes use the §1.5 rubric: **S** ≤1 day-equivalent, **M** 2–4, **L** 5+.

Critical path (following the wave spine; longest chain within it):

```
P0 → P1 → P2 → P3 → P4 → P5 → P6 → P8 → P9 → P10 → P11/P12 → P13 → P14
   → P15 → P16 → P17 → P18/P19 → P20-W11 → P20-W12
```

Off the critical path after their wave opens: P7 (parallel with P6 inside W4), P12
(parallel with P11 inside W6), P18 (parallel with P19's first tool groups inside
W10). The risk concentration is the tail: P17, P19 and P20-W11 are three L
deliverables in a row, and P19 carries the 112-reference locator removal (with the
325 `get_runtime` test references measured in §3) while P20-W11 closes the cycle and
re-points both entry points. P8 is the phase that spans two waves (W4 declaration +
W5 read gate) because `03` D11 and §2.7.2 place its two halves there; P20 spans
W11/W12 because the seal removes exactly what the split introduces, and its two
series are separately sized and separately accepted (R2-O-21).

Totals: **8 L** (P5, P6, P8, P15, P16, P17, P19, P20-W11), **10 M** (P0, P1, P2,
P9, P10, P11, P12, P13, P14, P18), **4 S** (P3, P4, P7, P20-W12). If one engineer
executes serially at the rubric's day-equivalents the path is roughly 60–75
day-equivalents before buffer. P2's size rose from S to M when `03` §2.5's W1 row
took on FES #1's two sites.

## 7. What could invalidate this plan

1. **`03` revises its wave spine or edge matrix.** This document's P↔W mapping
   (§2.1) is checked against `03` §2.5; a moved wave forces a re-map (the phase id
   range stays `P0`–`P20` because `03` §2.5 pins it). *Signal:* `03` §2.5 changes,
   or `03` §4.3/§4.6.1 changes the forbidden-edge scope (its count is owned by
   `03` §4.6.1 and never restated here).
2. **The declaration root moves.** P0/P1 assume the `03` §4.3 "Single declaration
   home": `ModuleContract.may_import` plus the leaf
   `src/film_pipeline/architecture.py` (`05` §2.1). If `03`/`05` revise it, P0/P1
   follow; **in no case does a second matrix file appear** (§2.2).
3. **Another cross-cutting number is wrong (the V1–V10 class).** Three files stated
   the same threshold count and all three were wrong while a fourth had corrected
   it (`reviews/orchestrator-verification-notes.md:214-218`, V5). Any number this
   plan repeats in a guard is suspect until its Step-1 command runs at the branch
   point. *Signal:* a phase's Step-1 disagrees with §0.3 — trust the command,
   update §0.3, and re-check the `L` row. This already happened twice: the live
   corpus is **173 (38/88/47/0)** as measured here, and the draft-time **163
   (38/83/41/1)** and pre-verification **148 (42/80/25/1)** in `03` §2.7 /
   `05` §3.11 are history.
4. **A verifier correction re-bands a concern across a wave.** L-38's read-path
   half moving to Critical *reinforces* P8 and is already applied; verify-10's
   landed verdict moved `F-CRP-05` and `F-CRP-10` High→Medium and surfaced
   **`F-CRP-12` (= M1, Critical 5×5=25)**, already placed in P11. A promotion of a
   deferred concern above a scheduled one forces a re-rank. *Signal:* a new or
   edited verifier file contradicting §0.2.
5. **The 90 % coverage floor.** The baseline's 91.58 % leaves 1.58 points of
   headroom. *Signal:* a phase PR whose coverage delta is negative and whose new
   guards do not offset it — split the module move or add behaviour tests first.
6. **Baseline drift.** If `modular-app` advances past `fb85baa` before P0, the
   enola baseline, the matrix, the ledger and the 2003/8/91.58 numbers are stale.
   *Signal:* `git log` shows a merge after `fb85baa`. `05` §7.2 already requires a
   `baseline pin` at each phase's branch point.
7. **Feature work on un-migrated seams.** *Signal:* the exemption ledger grows
   after P1 — split the phase or land the vocabulary guard first.
8. **A phase cannot avoid a persisted-representation change.** P8's kind
   declaration is deliberately label-preserving; P12's `meta.json` provenance
   **is** a persisted-representation change and is now inside P12's scope as that
   phase's documented B7 release (R2-O-3), with reader tolerance for `null` refs
   written before it. *Signal:* an extraction PR contains a migration that is not
   named as a B7 change in its phase note, or a test that reads pre-existing
   on-disk data differently.
9. **C2 is larger than the two-package view.** `03` reports it as 7 modules, and
   the invocation unification (P19) plus the P20-W11 split are both required.
   *Signal:* the acyclicity guard still reports an SCC after the P20-W11 series.
10. **P19's locator removal breaks the monkeypatch contract.** 112 `_services`
    references across 43 source files (`grep -rn --include='*.py' '_services'
    src/film_pipeline | wc -l` = 112; `grep -rln … | wc -l` = 43) plus 325
    `get_runtime` references across 123 test files are load-bearing. *Signal:* a
    tool group cannot be converted without keeping a locator shim — split the
    group rather than preserving the shim.
11. **P20's two series are executed as one merge.** `P20-W11` (split, entry-point
    re-pointing) and `P20-W12` (rename/shim removal) must land as separate series
    with separate green states; the W12 rename must not land in the same commit as
    the W11 split. *Signal:* a single PR touching both the module moves and
    `grep -rn "SHIM(W" src/`, or a `ci-check` that only goes green after both.
12. **A moved entry point is missed.** `Makefile:98-100`'s `product-gate` target and
    `pyproject.toml:39`'s console script are the two declared entry points that
    point at modules P20-W11 moves; `ci-verify` (`Makefile:111`) runs the first.
    *Signal:* `ci-verify` fails on a moved module, or the installed console script
    fails to resolve — both are acceptance conditions of P20-W11 (R2-O-1).
13. **`enola` version or snapshot drift.** Structural grades assume
    0.2.7-51-g72cd079; the checked-in `.enola/` is stale and cites a deleted `tui/`
    package, and `enola check` exit code `3` means "baseline not comparable", not
    success (`05` §7.2). *Signal:* `enola baseline show` reports another commit, or
    a CI wrapper treats `3` as green.
14. **The sandbox cannot run the gate as verified.** *Signal:* `make ci-check`
    fails on cache or network setup rather than on code (the `UV_CACHE_DIR` pin in
    P0 exists to prevent exactly this).

---

### One-paragraph summary

Twenty-one phases (P0–P20, the id range `03` §2.5 delegates to this document)
decompose every wave of `03` §2.5's spine and retire 49 of the ledger's 58
concerns; the other 9 are deferred with named triggers, and budget (L-01) is
scheduled inside P16 per `03` D5 rather than deferred. P0 pins the enola baseline
and declares the allowed-edge matrix and the FES scope classes as data in
`src/film_pipeline/architecture.py` — the single declaration home `03` §4.3 and
`05` §2.1 own, with the scope and the forbidden count owned solely by `03` §4.6.1
and never restated here — and P1 turns on the law with the `CONTRACT`s, the
`tests/architecture/` suite `05` §2.1 enumerates, and the exemption ledger. P2 makes
the cycle true and deletes FES #1; P3–P4 install `filmspec` and burn down the 57
severity literals;
P5–P8 give the state model, agents, the artifact contract and the storage read path
single owners; P9–P12 clean the private reach-ins, the `schemas` façade, the
resolution policy (including `F-CRP-12` = verify-10 M1, which keeps the
`langgraph.json` entry object via a lazy module `__getattr__`) and the KB provenance
path; P13–P14 fix validation; P15–P16 fix the generation ledger, the projection and
the cost/ceiling and create `budget`; and the tail does the hard work — `governance`
(P17), `projects` (P18), the operations split with the 112-reference locator removal
and its 325 test references (P19), then the studio split that closes `app`↔`mcp` and
re-points both declared entry points (**P20-W11**), followed by the renames and shim
removal that seal the program (**P20-W12**). Every phase — and each of P20's two
series — is independently shippable, leaves one authoritative owner per concern it
touches at every intermediate commit, respects the W0→W12 spine, and ends with
`make ci-check` green at ≥90 % coverage against the verified baseline of 2003
passed / 8 skipped at 91.58 %, with the live finding corpus measured at 173 — 38
Critical, 88 High, 47 Medium, 0 Low.
