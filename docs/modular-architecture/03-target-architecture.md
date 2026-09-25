# 03 — Target Architecture (Reconciled)

> **Review status (2026-09-25): superseded proposal.** The independent review
> in [06](06-independent-review-and-decision.md) does not adopt the 20-module
> catalog or its dependency law as an implementation mandate. This document is
> retained as design evidence. Its bar-B self-assessment predates unresolved
> adversarial and second-round findings; see [the capstone](reviews/bar-conformance.md).

Status: **authoritative target design.** This is the synthesis required by
`00-methodology-and-quality-bar.md` §4 step 6. It satisfies **quality bar B**
(§3 of that file) and supersedes `design/proposal-A-boundaries.md` and
`design/proposal-B-enforcement.md` wherever it decides between them. Where it
disagrees with `01-ownership-map.md`, the disagreement is stated explicitly
(§2.4 and the per-module entries in §3). **Revision 2** (see the section below)
records the fixes made in response to `reviews/adversarial-architecture.md`.

| Field | Value |
|---|---|
| Repo | `${REPO_ROOT}` |
| Baseline | `fb85baa` (`modular-app`, merge of the storage upgrade) |
| Evidence base | 14 audits (`audit/01`–`audit/14`, **corrected after their fix loops**: **173 live findings — 38 Critical, 88 High, 47 Medium, 0 Low**; audit 13's `F-TEST-02` is **WITHDRAWN** as unprovable and is not a live concern; its heading survives as a stub carrying no Severity bullet). Measured: `grep -h '^- \*\*Severity:\*\*' audit/*.md | wc -l` = **173**, which equals the per-audit sum below; distribution `grep -h '^- \*\*Severity:\*\*' audit/*.md \| sed -E 's/^- \*\*Severity:\*\* *\**([A-Za-z]+).*/\1/' \| sort \| uniq -c` → 38 Critical / 88 High / 47 Medium / 0 Low. Per audit: 01 = 11, 02 = 17, 03 = 13, 04 = 12, 05 = 8, 06 = 16, 07 = 13, 08 = 15, 09 = 13, 10 = 11, 11 = 15, 12 = 13, 13 = 10 live + 1 withdrawn, 14 = 6. **`02-duplication-ledger.md` (58 deduplicated concerns, L-01…L-58; its 148-finding appendix is the pre-fix set and is being corrected in parallel)**; **`reviews/verify-01.md`…`verify-14.md` + `reviews/orchestrator-verification-notes.md` (V1–V10; R4 — verifier verdicts supersede audit claims)**; `01-ownership-map.md`; `enola-architecture-facts.md`; `reconciliation-notes.md` (R1–R4); `04-extraction-roadmap.md`; `design/proposal-A-boundaries.md` (1,392 lines); `design/proposal-B-enforcement.md` (1,819 lines) |
| Verification status | `verify-01`…`verify-14` **all exist — verification is complete for all 14 audits**. Aggregate: **0 findings rejected**; ~20 severity/class corrections; ~30 ownership seams the audits missed (each dispositioned in §2.7.3). Orchestrator corrections V1–V10 are applied: **22** threshold literals (**18** at 85/75/75; `block_below == review_at` in 22/22), **107** cross-package private-module sites (**106** `schemas._base` + **1** `app._persistence`), **3** private-symbol sites, **322** `schemas` `ImportFrom` (**252** cross + **70** intra), the FES forbidden-edge count of §4.6.1 (**13**), and the measured rejection of the middleware alternative (D13). The persistence concerns L-11/L-21/L-22/L-42/L-43 are **no longer pending** — verify-10 lands 11/11 CONFIRMED with two severity recomputations (F-CRP-05 → Medium 9, F-CRP-10 → Medium 6) and four missed seams now folded in as M41–M44 (§2.7.3). |
| Revision 2 | **`reviews/adversarial-architecture.md`** (396 lines, `fb85baa`) is answered objection-by-objection at the top of this file. 14 of its objections landed here and are fixed: the FES scope and count corrected **10 → 13** (O-02), **53 `public_api` additions** measured (O-05), the §8 persistence row re-anchored (O-13), three persisted-representation rows added (O-14), plus O-06/O-07/O-08/O-09/O-10/O-12/O-18/O-19/O-21/O-22. Three of its confirmations (FA-1 acyclicity, FA-2 package count, FA-3 281/281) are recorded as reproduced results. Its mechanism objections (O-01/O-03/O-04/O-11/O-15/O-16/O-17/O-20/O-23) are `05`'s; §4.5 names the law they must satisfy. |
| Reference-only artifact | `design/prototype-enforcement/` — a 9-file, 793-line guard suite and a 327-line manifest that were executed against the real tree and then reverted. **Never merged; never to be merged as-is.** Cited as verified evidence; re-created under `src/`+`tests/` in wave 0 (§2.6). |
| Counts | 281 source `.py` files / 40,369 lines; 180 test files; 17 source packages. Target: **20 modules**. |

Every module below is justified by at least one audit finding or an enola
measurement (B9). Counts in this document were re-measured at `fb85baa`; the
commands are in the appendix.

---

## Revision 2 — adversarial architecture review fixes

`reviews/adversarial-architecture.md` (396 lines, HEAD `fb85baa`) attacks this file
and `05-enforcement-and-guard-tests.md`. This section records every change **this
file** made in response, keyed by the adversary's objection id, plus what the
adversary got wrong. Each row was re-measured here; the reproduction commands are in
the appendix. The objections whose subject is the *mechanism* (O-01, O-03, O-15,
O-16, O-17, O-20, O-23 — plus the mechanism half of O-04 and O-11) are `05`'s to fix;
this file states the law they must satisfy and, where the objection named a claim in
this file, corrects the claim.

### R2.1 Objections that landed on this file

| Objection | Verdict | Change in this file |
|---|---|---|
| **O-02** — 03/04/05 specify three forbidden-edge sets (10 / 10 / 4) and 05 hardcodes the edge total | **Upheld, and worse than stated** | §4.6 is rewritten as the **normative** definition, named **§4.6.1 (FES)**, with one keyable sentence, an explicit statement that `mcp → *` edges are **inside** the count, and the derived count corrected from **10 → 13**. The two extra edges are exactly the ones a package-granularity mapping cannot see: the `graph` split (`governance → orchestration`) and the `app` split (`operations → studio`); a third, `mcp → studio`, was missing from the old enumeration. `05` must cite §4.6.1 verbatim; `04`'s P0 acceptance "derived forbidden count = 10" and `05`'s scope are superseded (see §4.6.2). |
| **O-05** — declared `public_api` omits names callers really import | **Upheld on three of the four named, plus fifty more** | New **§3.21** measures all 126 non-`schemas` cross-module names at `fb85baa` and marks each *declared* / *add* / *via `operations`* / *renamed* / *deleted*; **53 additions** in total, concentrated in `governance` (12), `storage` (10), `providers` (8) and `validation` (8). §3.6, §3.8, §3.10, §3.13, §3.15, §3.17, §3.18, §3.6.1 and the module preamble are corrected inline. Of the adversary's four: `default_checkpoints_root`, `default_runtime_root` and `graph_state_location` are added; `sanitize_artifact_id` is **refuted** as a `storage.public_api` name (its only importer, `mcp`, loses that edge — it moves to `storage.contract` reached via `operations`). |
| **O-13** — the §8 persistence row names a non-divergence | **Upheld** | The adversary is right that `graph/graph.py:43` and `app/_persistence.py:51` are the same formula (`PERSIST_STATE ∧ ¬NO_PERSIST`). §8 now cites the real divergence — `graph/graph.py:43` vs `graph/services.py:31,48` (+ the `cli/run.py:226` override) — quotes both formulas side by side, and gives the input that distinguishes them. |
| **O-14** — three persisted-representation changes have no §8 row | **Upheld (exactly three)** | §8 gains three rows: `artifact_type` labels (W4, D11), the `budget` durable document (W8), and `kb_context_ref` stamping (`1/12 → 12/12`). All three are **additive and read-compatible**; each row names the wave, the migration owner and what a `git revert` does and does not undo. |
| **O-06** — §5 names `orchestration`/`projects` as checkpoint consumers that §4.3 forbids | **Upheld** | §5's checkpoint row is corrected: the read-only consumers are `operations`, `studio`, `devharness`; `orchestration` and `projects` are removed. §5 and §8 now state explicitly that the **LangGraph SQLite checkpointer is `orchestration`'s concern, not the `checkpoints` module's**, and that `orchestration` takes `default_checkpoints_root` from `storage` (which §3.6 now declares). |
| **O-07** — "no unrestricted modules" is true only by redefinition | **Upheld as to wording** | L8 and D10 are restated: the target law has no *coarsely* exempt module — every module's outbound set is finite and declared — while `studio` is a **composition root** whose 18-target set is enumerated in §4.3 and whose only inbound edge is none. §4.6.1 makes `studio` an ordinary scope member rather than an exemption. The `unrestricted_imports` flag is a W0-only pre-image (`05`'s removal wave). |
| **O-08** — `budget`'s abandon trigger is half-unsatisfiable | **Upheld** | §9.1's trigger is rewritten to the measurable disjunct (`authorize_spend` called from ≥2 modules **or** the cap gates ≥2 domains) and the impossible `post/assembly` parenthetical is deleted. |
| **O-09** — `projects`' merge trigger cannot be executed (`merge into studio` violates L6) | **Upheld** | §9.1 now says **merge into `operations`** — the layer that writes the pointer — or keep `projects` on the two-writer measurement. |
| **O-10** — `budget → config` is forbidden but the cap lives in `config` | **Upheld; resolved by declaring the source** | §3.10 and D5 now name the cap's single source: the **project record's** `budget_cap_usd`, read by `budget` through `storage` (no `budget → config` edge exists or is needed) and produced once at project creation by `config` from the profile. `budget` keeps N+I over the cap *policy* and loses the "N+I+R over the cap value" claim; the three rival cap representations are named and collapsed onto the record field. "One cap derivation" becomes "one cap value, one refusal path". |
| **O-12** — the `config → providers` migration covers one of two live sites | **Upheld** | §2.5's W1 row, the §6.1 `config/` rule and §4.6.1's FES #1 now list **both** `config/profile_resolver.py:179` (`build_provider_adapter` in `register_project_providers`) and `:204` (the credential check); the adapter factory call relocates to `operations` (3 call paths named), and `:179` is named as the second site of the edge. |
| **O-18** — the "N+I+R" earning rule fails for five modules by their own declarations | **Upheld** | §9.1 restates the rule as *owns N+I, or owns R, or is a declared composition root / harness*, and each of `filmspec`, `config`, `constraints`, `governance`, `devharness` now names which exemption it claims. |
| **O-19** — the declared source of truth (`documentation/architecture-blueprint.md`) is never cited | **Upheld** | New **§2.8** reads the blueprint's six System Layers and its `:15-16` design rule, and records explicitly that L0–L12 is a refinement that supersedes the blueprint's layer *listing* while preserving its MCP-boundary rule. |
| **O-21** — the "bare import" claim omits the env condition | **Upheld** | §5's import-time row now says "on `import` **with `FILM_PIPELINE_PERSIST_STATE` set**", the condition `05` already states correctly. The defect and its Critical 5×5=25 severity are unchanged. |
| **O-22** — the B7 MCP freeze is asserted in the present tense although the test does not exist at HEAD | **Upheld** | §8's MCP row is re-phrased "**will be frozen by**" and the freeze test moves to **W0** (it is a snapshot and needs no refactor). |
| **O-04** — L1 layer direction is declared but read by no guard | **Upheld as to §4.5's mapping** | §4.5's single row that bundled L1 with L2's three guards is split: L1 now names the guard the law **requires** — `test_declared_edges_go_strictly_down_one_layer`, iterating `may_import` against §4.2 — and states that it was missing, because acyclicity alone permits a same-layer or upward `may_import`. The matrix itself is not at fault (FA-1). `05` owns writing it. |
| **O-11** — `05`'s W1 plan deletes an edge this file declares allowed | **Upheld as to `05`** | No change to the law, which is stated as the correction: `agents → providers` is **allowed** by §4.3 (4 measured sites), so `05`'s W1 tightening list must drop `agents` and keep only `config` dropping `providers`. Recorded in D12's consequences; the edge stays in `agents`' `may_import`. |

### R2.2 What the adversary got wrong

- **"03 and 04 use 10" is not an error in 03's arithmetic, only in its scope.** The
  adversary's own FA-2 reproduces 10 at *current-package* granularity. §4.6.1 now
  says why that mapping is the wrong granularity (it cannot see the `graph`/`app`
  splits) and publishes the target-module count, 13. FA-2 is therefore *confirmed
  and absorbed*, not refuted.
- **`sanitize_artifact_id` is not a `storage.public_api` omission.** The only HEAD
  importer is `mcp/tools/_profile_change.py`, and §4.3 deletes `mcp → storage`. The
  name survives as `storage.contract`'s id grammar, reached from `mcp` through
  `operations`; putting it in `storage.public_api` would declare a surface no legal
  target module may call. The other three names the adversary named (`default_checkpoints_root`,
  `default_runtime_root`, `graph_state_location`) **are** omissions and are fixed.
- **The "three write-side changes" count is right; the framing that they are
  unlisted *representation* breaks is partly wrong.** Two of the three are **new**
  representations (the budget document) or **additive fields** (`kb_context_ref`),
  not changes to existing bytes. The §8 rows added in R2.1 say which is which, so
  B5's single-`git revert` claim is now demonstrated per change rather than asserted.
- **O-23's premise about the leaf is correct but its conclusion is not a defect in
  this file:** `architecture.py` being a manifest that every package imports is the
  D2 design, and the fragility it names is a `05`/D2 sizing concern (D2's
  "~500 lines" revisit trigger), not a false claim here.

### R2.3 Confirmed results (recorded, not asserted)

The adversary independently re-derived three of this file's structural claims and
they hold; they are recorded here as **confirmed at `fb85baa`** so a later reader does
not have to re-run the attack:

- **FA-1 — the §4.3 matrix is internally consistent and acyclic.** Parsed
  programmatically: **0 self-edges**, **0 non-lower edges** across all 20 rows, and
  Kahn closure completes with a full topological order. §4.1's "acyclic by
  construction" is confirmed. (The adversary separately found L1 is *unread by any
  guard* — O-04, a `05` mechanism gap, not a matrix defect; §4.5's mapping is
  corrected in R2.1 only where it over-claimed.)
- **FA-2 — the package-granularity forbidden count reproduces.** The AST sweep
  reproduces exactly **53** distinct cross-package edges and the doc's list at that
  granularity. §4.6.1 supersedes the *scope*, not the arithmetic.
- **FA-3 — the conformance map is exact.** All **281** files assign to exactly one
  target module with **0 orphans**, every one of the 18 per-package counts
  reproduces, and a 20-file random sample (seed 7) assigns correctly including the
  split cases `app/services/__init__.py → operations` and
  `graph/_action_routing.py → governance`. §6.4 is confirmed, not merely claimed.

Objections whose subject is **only** the mechanism are `05`'s to fix, and this file
records the law they must satisfy rather than a change: O-01 (guard inputs under
gitignored `docs/`), O-03 (the `107+3 == 2+n` assertion), O-15 (existence-based
liveness), O-16 (the anti-deletion registry), O-17 (declaration-family
non-emptiness), O-20 (the citation regex), O-23 (`architecture.py` fragility). For
O-04 and O-11 the *objection* landed here and the correction is in R2.1/§4.5/D12;
only the mechanism is `05`'s.

---

## 1. Executive summary

**Module count: 20** (17 current packages → 20 modules): `filmspec`, `schemas`,
`config`, `kb`, `constraints`, `storage`, `providers`, `projects`,
`checkpoints`, `agents`, `budget`, `validation`, `generation`, `post`,
`governance`, `orchestration`, `operations`, `mcp`, `studio`, `devharness`.
Two of the 20 (`filmspec`, `budget`) are new; four current packages are renamed
or split (`graph` → `orchestration` + `governance`; `app` → `studio` +
`operations` + `projects`; `artifacts` → `storage`; `testing` → `devharness`).

**The dependency law in one sentence.** Every module declares a layer 0–12; a
module may import only modules in strictly lower layers, no module may import a
private name or submodule of another module, no module may write another
module's state, and the resulting import graph is acyclic — `filmspec` at L0 has
zero imports, and every allowed edge points strictly downward.

**The three decisions that matter most.**

1. **D1 — one Python distribution, many enforced modules.** The repo keeps
   shipping a single distribution (`film-pipeline`) and does *not* become a `uv`
   workspace of distributions. A Python *distribution* is the gem analogue; the
   repo's import packages are Ruby-`module` analogues. The program gets its
   boundaries from D2, not from packaging. Revisit trigger in D1.
2. **D2 — enforcement is a typed, in-tree contract manifest plus one shared
   AST guard suite; enola corroborates and does not gate.** `ModuleContract` in
   each package `__init__.py` + cross-module invariants in the leaf
   `src/film_pipeline/architecture.py` + `tests/architecture/`, with a
   citation-checked, liveness-checked `Exemption` ledger. No `import-linter`,
   no `tach`, no new dependency, no new CI job. This is proposal B's mechanism;
   proposal A's untyped YAML baseline is rejected.
3. **D5 — `budget` is its own module, and `governance` stays stateless.**
   Budget/spend is currently 4 caps, 7 representations, 6 writer modules and 8
   gate sites (F-BUD-01/02/03/04); `governance` must hold no state or it becomes
   a second cycle site, so the cap and the spend ledger live in a small L5
   `budget` module that `governance`, `generation` and `operations` consume.

The single structural cut that makes the law true is **D3**: `app ↔ mcp` (the
only package-level cycle, enola C2, F-BOUNDARY-03) disappears by splitting
`app` into `studio` (above `mcp`) and `operations` (below it). The most-debated
cosmetic question is **D4**: `artifacts.contract` does not become a module; its
derivation/enforcement content lives in the `storage` module as
`storage.contract`, per reconciliation note R3.

---

## 2. Reconciliation of proposal A and proposal B

Both proposals were written independently. They agree on more than they
disagree. §2.1 states the agreements once; §2.2 is the decision table; §2.3
records the corrections each proposal needs; §2.4 lists the places this document
contradicts `01-ownership-map.md`; §2.5 fixes the phase sequencing; §2.6 states
how the enforcement layer is declared.

### 2.1 Where A and B agree (stated once, adopted)

| Agreement | Evidence both used |
|---|---|
| The baseline facts: 281 source files, 17 packages, `make ci-check` green at `fb85baa`, storage is the one well-owned subsystem | `00` §5, A §1, B §2.2 |
| `artifacts` storage (layout, root, atomic writes, paths, kind catalog, version numbering, checksum, approve/supersede) stays single-owner and is not re-cut | `01` §7, `audit/07` §6.1, A §5.5/§10.1, R3 |
| Boundaries must be enforced by **source-level tests that can fail**, not by docstrings; the storage guard is the precedent | `tests/unit/artifacts/test_storage_boundary.py:1-10`, A §1, B §2.2 |
| Enforcement must ship **first**, with a recorded debt baseline so wave 0 is green; the baseline is the burndown | A §6.4/§8 P0, B §5.3/§8.2 |
| Extraction order is the topological order of the law: leaves first, `schemas` early but carefully, `graph`/`mcp`/composition root last | A §8, B §8.1 |
| No runtime feature flags; no extraction PR may change a persisted representation; compatibility changes are separate PRs | A §11, B §7 step 9 |
| `app ↔ mcp` is the only *package-level* cycle; the file-level tangle in `graph/nodes` + `graph/orchestrator_validators` is the second real cycle | `01` §15, `enola` §2, A §2.2, B §2.3 |
| The `_services` service locator (112 refs / 43 files, deliberate monkeypatch contract) is the largest and riskiest seam | `enola` §4, A §2.4/§10.9, B §6 |
| O2 (duplicated enforcement) and O6 (parallel lifecycle) cannot be fully automated; they get human-declared pairs plus differential locks | A §6 (implicit), B §6.9 |

### 2.2 Decision table (who won, and why)

| # | Question | Proposal A | Proposal B | Decision (winner) | Rejected alternative, and why |
|---|---|---|---|---|---|
| R-1 | Module names | 18 new target names (`storage`, `orchestration`, `studio`, `operations`, `devharness`, `filmspec`, `governance`) | Keep the 17 current package names; add `architecture.py` | **A wins on the catalog.** Target modules use A's names. Renames are staged last, behind shims, with the manifest re-pointed each wave. | B's keep-the-names: `app` and `artifacts` and `graph` are names that *lie* about ownership (`app` = composition root **and** operator use cases **and** project registry). B never proposed a catalog, so it cannot win a naming question it did not answer. |
| R-2 | `artifacts.contract` | Does **not** create it; kind set → `filmspec`, `KindSpec`/`REGISTRY` stay in `storage` (A §5.5, §10.1) | Silent — B's `artifacts` contract lists `ArtifactStore`, `REGISTRY`, `KindSpec` with `may_import={schemas}` | **Neither, exactly: `storage.contract` is a submodule of `storage`** (D4). Audit 07's content (ref `stem()`, `type_for`, `kind_spec_for`, `check_readable`, status/GenerationStatus transition tables, `read_meta`) becomes `storage/contract.py`; there is no top-level `artifacts.contract` module. | A top-level `artifacts.contract` (audit 07 §6) is rejected: R3 says the leaks are *callers re-deriving*, not storage owning too much; a same-layer module beside `storage` creates a `storage ↔ contract` cycle risk and a second storage-shaped module. A's position is also corrected: the *kind vocabulary* (`ArtifactType`) moves to `filmspec`, not the whole kind catalog. |
| R-3 | Is `graph` split? | Yes: `orchestration` + `governance` + `filmspec`; `nodes/` stays together (A §10.2) | No: `graph` stays and is `unrestricted_imports=True` | **A wins.** `governance` is extracted; `nodes/` + `subgraphs/` + topology/module state stay in one `orchestration` module. | Per-phase `nodes/` split: rejected by A §10.2 and by `tests/unit/graph/test_channel_registry.py:1-10` (the D-009 dropped-channel bug class). B's `UNRESTRICTED_PACKAGES = {graph, mcp}` (B §5.3): rejected for the target law — B itself concedes in §9.3 that it makes B3 vacuous for the two most-coupled packages. B's mechanism is kept; its waiver is not. |
| R-4 | Where does `governance` sit? | Its own stateless L7 module; `review/` folds into it; imports `filmspec`, `schemas`, `storage`, `validation` (A §5.10, §10.6) | Keeps `review` as a package; `graph` unrestricted, so the question is not posed | **A wins.** `governance` is a module between `validation`/`budget` and `orchestration`; it owns the gate decision, available actions and review-package assembly; it holds no state and never imports `orchestration`. | `audit/08` §4.3 (validation owns the human gate): rejected — validation would own report *production* **and** the phase *decision*, breaking B1, and `review` would depend on the module that produces the reports it reviews. `audit/02` §5 (the orchestrator-state owner owns `may_approve`/`resolve_action`): rejected — that placement is exactly today's smear (the decision is re-derived in 5–6 places around the state owner, F-OST-05/F-VR-06). |
| R-5 | How is the enforcement layer declared? | `scripts/architecture/layers.yaml` + `import_matrix.py` + free-text `violations-baseline.txt` + `tests/unit/architecture/test_module_law.py` (A §6.4) | Typed `ModuleContract` per `__init__.py` + `src/film_pipeline/architecture.py` + `tests/architecture/` (9 files) + `Exemption(subject, reason, citation)` (B §5) | **B wins (D2).** Typed, mypy-strict-checked declarations; one citation-checked, liveness-checked exemption type; the mechanism was executed against the real 281-file tree (B §11). | A's YAML + free-text baseline: untyped (a typo'd package silently does nothing), no citation resolving, no liveness (a fixed violation's row rots green). A's *layers as data* idea survives as `ModuleContract.may_import`, which is data in a Python file that mypy checks. |
| R-6 | Phase sequencing | P0–P10 (11 phases), enforcement first, vocabulary second, locator at P8/P9 | Wave 0–6+ (mechanism first, topological order by in-degree, ledger high-water mark) | **B wins the spine; A's content is merged in.** The wave table is §2.5. | A's `P0` baseline numbers are rejected as measurements (below, C-4). A's ordering instinct (locator last) is kept verbatim — it is A's own §10.9 warning. |
| R-7 | How many modules? | 18 | 17 packages + `architecture.py` (no catalog) | **20.** A's 18, corrected: `constraints` standalone (+1), `budget` new (+1), `artifacts.contract` not a module (0). | 18 with `constraints` folded into `agents` (A §7): rejected — `constraints` is a clean single-owner leaf (`01` §12, `audit/12` §6.3) and folding it makes `agents` own extraction grammar plus prompts plus model invocation. |
| R-8 | Artifact-kind counts | A's F-AKIND-01: "registry 54 kinds vs `ArtifactType` 45 (12 unregistered, 3 unstorable)" | Not addressed numerically | **Neither; R1 ground truth wins: 47 registered ids, 45 enum values, 39 shared; 8 registry-only, 6 enum-only (3 prefix-covered, 3 uncovered: `clip`, `last_frame`, `mid_frame`).** | A's method error is recorded: it compared `_by_kind` (54 kind slugs in a different namespace) against `ArtifactType` values. Re-measured at HEAD: `REGISTRY._exact` = 47, `ArtifactType` = 45 (`reconciliation-notes.md` R1; appendix command 6). |
| R-9 | `film_pipeline.testing` | Rename `devharness`, move `app/mock_responses.py` into it | Keeps `testing`, gives it a contract (B §5.4) | **A wins the rename; A loses the `mock_responses` move** (D6). `devharness` is dev-only and leaves the wheel; `app/mock_responses.py` **stays** in `studio` because 4 production modules import it and the product gate runs mock mode in CI. | Moving `mock_responses` (A §7): rejected by measurement — `grep -rln mock_responses src` → `app/runtime.py`, `graph/services.py`, `agents/runner.py`, `cli/driver.py`; the shipped `product-gate` target exercises it (`Makefile:108`). |
| R-10 | `agents → providers` and `post → validation` | Both allowed (`agents` uses only the provider *port*; A §10.8) | Wave-1 target drops both | **A wins.** Allowed edges are `agents → providers` (public port/taxonomy only; never a concrete adapter) and `post → validation` (public). The edge B wanted gone is `post → validation.impl`, a **private submodule**, which L3 forbids — not the module edge. | B's wave-1 tightening to `schemas` only: rejected — it would force the model-adapter and validator *types* to be injected as `Any`, which B's own O8 section says is the thing to avoid. The correct instrument is L3 (no private submodules), not an over-broad edge ban. |
| R-11 | `_agent_routing.py` placement | Ambiguous in A (`agents` or `orchestration`) | n/a | **`orchestration`.** It is a phase-keyed partial map consumed by routing; `audit/01` §"Candidate module boundary" explicitly keeps `_PHASE_DEFAULT_AGENTS`/partial maps in `graph`, keyed/validated against `filmspec.PHASE_ORDER`. | Putting it in `agents` (A §7's parenthetical) would make `agents` import the phase vocabulary for a routing concern, compensating a routing module for an agent concern. |

### 2.3 Corrections each proposal needs (recorded per `reconciliation-notes.md` R4)

- **C-1 (A):** the conformance map's per-package counts sum to **280**; the tree
  has **281** `.py` files. The missing file is `src/film_pipeline/__init__.py`
  (`__version__`, `project_name()`), which A never assigned. It is assigned to
  `studio` (§6).
- **C-2 (A):** A says `app/services/` is "5 files → operations". It is **7**
  (`__init__`, `operator`, `errors`, `models`, `_browse_ops`, `_generation_ops`,
  `_project_discovery`).
- **C-3 (A):** A's graph split reads "`orchestration` 24 + `governance` 12" and
  says "`nodes/` (19 files)". The real tree is `nodes/` **17**, `subgraphs/` 2,
  `orchestrator_validators/` 5, `graph/*.py` 12. The corrected split is
  `orchestration` **28**, `governance` **12** (8 graph files + 4 `review/`
  files); see §6.
- **C-4 (A):** A's P0 baseline says "383 private reach-ins, **1 cycle**, 52
  outbound edges". These are three different measurements at three different
  granularities: 383 is *all* private reach-ins including intra-package (A
  §2.3); enola finds **5** package/sub-package cycles (C1–C5); A's own SCC sweep
  finds 7 file-level SCCs; the *package-level* cycle count is **1**. The
  enforcement ledger (D2) keys on the guard-computed sets, not on a prose total —
  B's measured sets: 8 `current_phase` writers, 7 `NO_PERSIST` readers, 6
  registry non-members, 2 private modules, 1 cycle edge.
- **C-5 (B):** B says "71 files import `schemas._base`" (§2.4, §6.4); `audit/14`
  F-BOUNDARY-02 and a HEAD re-measure say **72** non-`schemas` files (V4). The
  precise AST counts to use are **107 cross-package private-module import
  sites** = **106** to `schemas._base` (in those 72 files) + **1** to
  `app._persistence`, plus **3** private-*symbol* sites
  (`app/_graph_exec.py:319,449`, `config/profile_resolver.py:204`). B's
  `_readers.py`-based prototype is otherwise taken as verified.
- **C-6 (both):** `schemas` inbound is **322** `ImportFrom` statements under a
  consistent AST convention, not 323 — split **252 cross-package + 70
  intra-package** (V4) — and the extra hit in the old count is a docstring line
  in `schemas/__init__.py:5`. enola's *fan-in* 509 is a different measure (all
  edges, including intra-package); the two numbers are not interchangeable.
- **C-7 (B):** B's `UNRESTRICTED_PACKAGES = {graph, mcp}` is not carried into
  the target law (R-3). It is carried into **wave 0 only**, as the observed-edge
  declaration, and is deleted as the split lands.
- **C-8 (B):** B's `CYCLE_EXEMPTIONS` cites `app -> mcp` as the cycle. Correct,
  but B's rename plan does not exist, so the exemption is keyed to the *target*
  edge `studio -> mcp` after wave 1 (§4.4).
- **C-9 (A):** A §7 says `artifacts/registry.py` "splits: the kind set →
  `filmspec`". Only the **kind vocabulary** (`ArtifactType` values) moves;
  `registry.py` (with `KindSpec`, `MIGRATIONS`, renderers, `validate_artifact_id`,
  `REGISTRY`) stays whole in `storage`. R3.
- **C-10 (A):** A's `filmspec` contract lists `ArtifactKind` as "the 54-value
  catalog". Corrected: the canonical vocabulary is the **47 registered ids**,
  plus 3 explicitly declared non-storable media names, with the 3
  prefix-covered names reachable through their prefixes (R1).

### 2.4 Explicit contradictions of `01-ownership-map.md`

`01-ownership-map.md` is evidence, not law, but its candidate owners are the
default. This document departs from it in four places, deliberately:

1. **§1 candidate owner `phase-model` vs this document's `filmspec`.** `01` §1
   and `audit/01` propose a `phase-model` module (home `schemas/phase.py`). This
   document folds the phase vocabulary into `filmspec` together with the other
   normative vocabularies (severities, kinds, statuses, roles). Reason: a
   standalone `phase-model` fragments the O1 vocabulary across two modules and
   leaves severities/kinds homeless, which is the O1 disease at module scale.
   D7.
2. **§7 candidate owner `artifacts.contract` vs this document's
   `storage.contract` submodule.** `01` §7 and `audit/07` §6 propose a top-level
   module. R3 and D4 reject it. The derivation/enforcement content is kept; the
   module is not created.
3. **§12 candidate owner for the budget law is `governance` vs this document's
   `budget` module.** `01` §12 writes "`governance` owns the budget law";
   `audit/12` §6.4 proposes a `budget` module. This document follows
   `audit/12`, because `governance`'s acyclicity argument depends on it being
   **stateless** (A §10.6) and budget owns a spend ledger. D5.
4. **`audit/10` §6 proposes a `runtime_persistence` module vs this document's
   three-way split** (`studio` = policy, `checkpoints` = lifecycle,
   `storage` = bytes). Reason: `audit/10`'s own N/I/R list shows the three
   concerns have three different correct owners, and a fourth module whose only
   job is to hold a `RootLayout` would sit between `studio` and `storage` for no
   ownership gain. D8.

`01`'s single-owner classifications (storage layout, constraint extraction, KB
conflicts, multi-model review package shape, MCP contract flags, ref parsing)
are adopted unchanged.

### 2.5 Phase sequencing (B's wave spine, A's content)

**Ownership of phase identity:** `04-extraction-roadmap.md` is authoritative for
**phase ids, ordering and per-phase acceptance** (its `P0`–`P20`); the `W0`–`W12`
names below are this design's **internal wave spine** — the ordering argument
that explains *why* the modules can be extracted in that sequence. A reader
executing the program follows `04`; a reader auditing the design follows §2.5.
The two must agree, and `04` carries the full P↔W mapping plus this document's
module names.

Each wave is one short branch off `modular-app`, ends green in `make ci-check`,
and shrinks the exemption ledger. `L0-L12` are the layers of §4.

| Wave | Content | Target modules touched | Ledger effect | Source |
|---|---|---|---|---|
| **W0 — Law with a ledger** | `src/film_pipeline/architecture.py` (leaf), `CONTRACT` in each package `__init__.py`, `tests/architecture/` (9 files), `make arch-check`, citations re-pointed at this document | none (no runtime path reads the manifest) | baseline created: 1 cycle edge, 8 `current_phase` writers, 6 registry non-members, 7 policy readers, 2 private modules; **high-water mark** | B §5.8/§8.2; A §8 P0 |
| **W1 — Make the cycle true** | move `app/product_gate.py` above `mcp` (temporary top-level module `film_pipeline/entrypoints.py`); delete the `config → providers` edge — **both** of its live sites, `config/profile_resolver.py:204` (credential check → `providers.required_credentials`, called by `studio`) and `:179` (`build_provider_adapter` inside `register_project_providers` → `operations`, whose 3 call paths are `app/services/operator.py:147`, `mcp/tools/_profile_change.py:129`, `mcp/tools/projects.py:192`); delete `CYCLE_EXEMPTIONS`; add the mutation canary | `studio` (pre-image), `operations` (pre-image), `mcp`, `config`, `providers` | −1 cycle edge; −1 forbidden edge (FES #1); −0 policy rows | B wave 1; A P9's `product_gate` move, pulled early; O-12 |
| **W2 — `filmspec` (O1)** | enums out of `schemas/_base.py`; `PHASE_ORDER`, `PHASE_GATES`, `successor`, `is_blocking`; replace 48 `"blocking"` literals and 9 inline `gate=` literals; re-point `MIRRORS.canonical` to `filmspec` | `filmspec`, `schemas` | MIRRORS rows become real; duplicate-literal sweeps added | A P1/P2; B wave 2 |
| **W3 — `current_phase` single writer (O3)** | collapse 8 writers onto `orchestration`; `STATE_CHANNELS.writers` → 1 | `orchestration`, `operations`, `checkpoints`, `agents` | −7 writer rows | B wave 3 |
| **W4 — registry agreement (O4)** | enable `AgentRegistry(known_output_artifacts=…)`; add `CONSENSUS_REPORT`/`COST_ESTIMATE` etc. to the kind vocabulary; declare the 3 media kinds non-storable | `agents`, `storage`, `filmspec` | −6 non-member rows | B wave 4; R1 |
| **W5 — private imports (O7)** | 72 `schemas._base` importers migrate to the public surface; rename `_base.py` → `schemas/base.py` | `schemas` + all consumers | −1 private-module row | B wave 5 |
| **W6 — persistence policy (O5)** | one `studio.resolve_persistence()`; unify `NO_PERSIST`/`PERSIST_STATE` precedence (documented behaviour change) | `studio`, `checkpoints`, `storage` | −7 policy rows | B wave 1.5/6; A P3 |
| **W7 — validation** | single `ValidationReport` writer; one dispatch table; status-band law; typed consensus | `validation`, `governance` | O2/O6 locks | A P4; `audit/08` |
| **W8 — generation + `budget`** | spend ceiling derived once; ledger→state projection moves up into `orchestration`; `budget` extracted | `generation`, `budget`, `orchestration`, `operations` | O2/O6 locks | A P5; `audit/12` §6.4 |
| **W9 — `governance`** | gate law + `orchestrator_validators/` + `review/` → `governance`; `evaluate_phase`; **C3 broken** | `governance`, `orchestration` | −graph SCC | A P6 |
| **W10 — `projects` + `operations`** | `ProjectRegistry`; `app/services/` → `operations`; kill `_services` (112 refs / 43 files) | `projects`, `operations` | −locator | A P7/P8 |
| **W11 — `studio` split** | `product_gate` returns above `mcp`; `cli/` → `studio`; `mcp` loses `get_runtime`; **C2 closed**; `langgraph.json` path updated | `studio`, `mcp`, `cli` | −cycle, −locators | A P9 |
| **W12 — renames + seal** | target names, shim removal (`# SHIM(...)` tokens → 0), per-module guards, baseline empty | all | baseline must be **empty** | A P10; B §8.4 |

Rules carried verbatim from B §8.4: no wave may grow the ledger beyond the W0
high-water mark; every ledger row cites this document and the wave that deletes
it; an extraction PR never changes a persisted representation (if it must, it is
a separate B7 PR).

### 2.6 How the enforcement layer is declared (D2, concretely)

Adopt B §5 as written, with three target-specific edits:

1. **Manifest:** `src/film_pipeline/architecture.py` stays a **leaf** (imports
   nothing from `film_pipeline`); it is *not* one of the 20 modules — it is the
   law's declaration root and is `ALWAYS_IMPORTABLE`. It defines `Exemption`,
   `ModuleContract`, `VocabularyMirror`, `StateChannel`, `RegistryAgreement`,
   `PolicyPoint`, and the cross-module rows.
2. **Per-package contract:** a `CONTRACT = ModuleContract(...)` appended to each
   of the current 17 `__init__.py` files in W0 (B's verified
   `package-init-contract-diff.patch`, 325 lines). W0 `may_import` = the edges
   observed at HEAD, so the edge guard ships green; each wave tightens its own
   package's set and `test_declared_edges_are_real` fails if a tightened-away
   edge is still imported. The target sets are the §4 matrix.
3. **Guards:** `tests/architecture/` with B's nine files
   (`_harness.py`, `_readers.py`, `test_contracts.py`, `test_boundaries.py`,
   `test_vocabularies.py`, `test_state_writers.py`, `test_registries.py`,
   `test_exemptions.py`, `__init__.py`). All prototype citations are re-pointed
   from `proposal-B-enforcement.md` to **this document**; B §11 records that the
   citation test was the only failing guard in the prototype precisely because
   the cited file was still being written. That failure is resolved by this file
   existing.

**enola's role (D2, second half).** enola 0.2.7 is installed at
`~/.local/bin/enola` (a user binary, not a project dependency), `mcp-arch.yaml`
is checked in, `.enola/` is **stale** (taken at `main@4f802b1`, still contains
the deleted `tui/` package), and there is **no** `enola-intent.yaml`, which is
why the facts doc reports "0 layer violations — because no layers are
declared". Decision: enola is **corroboration and impact analysis**, not the
gate. It stays wired as the docs-local snapshot
(`docs/modular-architecture/enola-config.yaml`) and gets a derived
`enola-intent.yaml` generated from the `CONTRACT` manifest once W2 lands, so
`enola --explain` and the guard suite cannot disagree. The gate is the pytest
guard suite, because enola's module granularity collapses submodules to their
parent package (C1/C4/C5) and therefore cannot express L3, L5, L6 or the O1/O3
state sweeps.

### 2.7 Ledger reconciliation (L-01…L-58) and the verifier verdicts

`02-duplication-ledger.md` is the program's concern inventory: 58 canonical
concern entries (the ledger's own `148/148` appendix is the **pre-fix** finding
set; the corrected audit files now hold **173 live findings** — 38 Critical, 88
High, 47 Medium, 0 Low, measured as 173 severity bullets, none of which belongs
to the withdrawn `F-TEST-02` stub, so it is not a live concern and is not carried anywhere in this
document). Concern ids are used here and are **not** re-derived; the verifier
corrections that supersede audit claims are applied in §2.7.2 and the seams the
audits missed in §2.7.3. Under R4, where a verifier verdict contradicts an audit
claim, the verdict wins and this document follows it. All 14 verifier files have
landed, so **nothing here is pending verification**.

#### 2.7.1 Every ledger concern has exactly one target module

| Ledger | Concern (short) | Target module | Ledger | Concern (short) | Target module |
|---|---|---|---|---|---|
| L-01 | Budget caps/refusal/spend | `budget` (D5) | L-30 | Agent naming → KB manifest | `agents` (+`kb`) |
| L-02 | Agent→model-profile map | `agents` (+`config`) | L-31 | Gate decision + review package | `governance` (R-4) |
| L-03 | Agent execution lifecycle | `agents` | L-32 | Number-word / scene-count | `constraints` |
| L-04 | Post models/`AssemblyAgent` | `post` | L-33 | Canned payloads / mocks | `devharness` (+`studio`) |
| L-05 | "Delivery complete" + manifest | `post` | L-34 | Phase→gate map + gate mode | `filmspec` + `governance` |
| L-06 | Phase advancement / successor | `governance` + `filmspec` (D7) | L-35 | `issues` contract / approve veto | `orchestration` (+`governance`) |
| L-07 | Agent contract vs implementation | `agents` | L-36 | `app` re-implements reducers | `orchestration` (D3) |
| L-08 | Generation job lifecycle | `generation` | L-37 | Prompt registry id spaces | `agents` |
| L-09 | Provider health representations | `providers` (+`orchestration`) | L-38 | Version / `schema_version` / status | `storage.contract` (D4) |
| L-10 | Consensus construction/state | `validation` | L-39 | Media paths / reference catalog | `generation` (+`storage`) |
| L-11 | Roots resolved five ways | `studio` (+`storage`, `checkpoints`) — VERIFIED (verify-10: CONFIRMED, framing disputed) | L-40 | Generation-request identity | `generation` (+`orchestration`) |
| L-12 | MCP invocation + `app↔mcp` | `mcp` + `studio`/`operations` (D3) | L-41 | Cost model vs planner ceiling | `budget` (+`providers.pricing`) |
| L-13 | Validator registry + dispatch | `validation` | L-42 | Rollback/invalidation/audit | `checkpoints` (+`storage`) — VERIFIED (verify-10: F-CRP-07 CONFIRMED; F-CRP-05→Medium 9) |
| L-14 | Score→status / `NEEDS_REVISION` | `validation` | L-43 | Persistence flags / bootstrap | `studio` — VERIFIED (verify-10: F-CRP-09 CONFIRMED, 2 sub-claims corrected; +M42) |
| L-15 | Phase vocabulary/order/keyed literals | `filmspec` (+derived in `orchestration`) | L-44 | Confirmation / dangerous mutation | `mcp` |
| L-16 | Ledger state machine / status grammar | `generation` | L-45 | OperatorService vs MCP + registries | `operations` + `projects` |
| L-17 | Two QC lifecycles | `validation` (+`orchestration`) | L-46 | Profile-stack keys/writers | `config` |
| L-18 | Kind ↔ `ArtifactType` (R1) | `filmspec` + `storage.contract` | L-47 | Harness factory/fixtures/git double | `devharness` |
| L-19 | KB packet construction/delivery | `kb` (+`orchestration`) | L-48 | Dependency law / private reach-ins | `architecture.py` + guards (D2) |
| L-20 | KB provenance / `kbctx:` ids | `kb` (+`storage` bytes) | L-49 | Router actions vs edge table | `governance` |
| L-21 | Checkpoint registries / `artifact_versions` | `checkpoints` — VERIFIED (verify-10: F-CRP-02/04/06 CONFIRMED; +M41) | L-50 | `_orchestrator__` key grammar | `orchestration` |
| L-22 | Resume seam / duplicate resume | `checkpoints` (+`operations`) — VERIFIED (verify-10: F-CRP-03 confirmed; F-CRP-05→Medium 9, F-CRP-10→Medium 6) | L-51 | Prompt renderers / JSON recovery | `agents` |
| L-23 | MCP tool argument contracts | `mcp` | L-52 | Error taxonomy / dead envelope field | `mcp` |
| L-24 | Model-profile defaults YAML vs code | `config` | L-53 | `profiles/` location / hardcoded defaults | `config` |
| L-25 | Provider-lineup parsing shapes | `config` (+`providers.required_credentials`) | L-54 | `testing` ships / cross-domain | `devharness` (D6) |
| L-26 | "Stalled phase" representations | `orchestration` | L-55 | `next_action` → prose / channels | `governance` (+`orchestration`) |
| L-27 | Failure decisions / classification | `providers` (+`orchestration`) | L-56 | Ledger write-on-read | `generation` |
| L-28 | Provider registry / capabilities | `providers` | L-57 | Ref-string formatter | `storage.contract` |
| L-29 | Credential resolution at 14 sites | `providers` | L-58 | "Requires human review" twice | `validation` (+`governance`) |

Two ledger candidate owners differ from this catalog and are resolved
explicitly, extending §2.4: **L-06/L-15/L-34/L-49 name `phase-model`** → this
document's `filmspec` + `governance` (D7); **L-31 names
`validation/gate_policy.py`** → this document's `governance` (R-4). Both
downgrades are deliberate and justified in those decisions; the ledger's
`runtime_persistence*` owners (L-11/L-21/L-22/L-42/L-43) are dissolved into
`studio`/`checkpoints`/`storage` by D8. Every other ledger candidate owner maps
1:1 to a module in §3, which is independent corroboration of the catalog.

#### 2.7.2 Verifier corrections that change this design (R4)

| Finding | Verdict | Effect here |
|---|---|---|
| F-ARTIFACT-05 | **UPGRADED** High 12 → **Critical 16** (verify-07) | `storage.contract.check_readable` (D4) is a **Critical-priority** fix, not a tidiness fix; the read-time schema gate moves to W5. |
| F-VR-02 | CORRECTED (verify-08) | `NEEDS_REVISION` **is** reachable on the LLM path; the real defect is the zero-width `[block_below, review_at)` band for 22/22 explicit literals. `validation`'s guard tests the **band invariant** (`block_below < review_at`), not "unreachable end-to-end". |
| F-GEN-07 | DOWNGRADED High 12 → Medium 6 (verify-06) | Media-path construction is **not** a silent partial-edit seam. This strengthens A §10.4 (do not extract a `media` module) — but the compositor's direct disk writes are a separate **L4** violation (§2.7.3 M16). |
| F-BOUNDARY-02 | DOWNGRADED; its **O1 class REJECTED**, O7 confirmed (verify-14) | The 72-importer `schemas._base` migration is a **public-surface** fix (W5), not a vocabulary fix; it does not justify moving enums for this reason (D7 does that for its own reason). |
| F-CFG-01 / F-AGENT-02 | DOWNGRADED to High (verify-03, verify-04) | Priority ordering only; both remain in W2/W4. F-AGENT-02's declared profile field has **zero** production readers, so the `agents` catalog must become the reader, not just the declaration. |
| F-PHASE-10 | DOWNGRADED: **two** phase→validator tables, not three (verify-01) | `validation.PHASE_VALIDATORS` stays the one table; `_VALIDATOR_MAP`/`_WORKER_NODES` are not phase-keyed and need no ownership claim. |
| F-VR-05 | DOWNGRADED Critical 16 → High 12 (verify-08) | Consensus single-writer stays `validation`; priority High. |
| F-VR-06 | CORRECTED: **seven** gate-decision sites, not six (verify-08) | Strengthens `governance.evaluate_phase` as the single decision (R-4). |
| F-VR-09 | Drift proof **falsified** (verify-08) | The typed review package is real but the MCP path *swallows* the failure; the guard must assert a typed `ReviewPackage` on **both** paths, not "fails loudly". |
| F-VR-11 | Class corrected Low → **Medium** (verify-08; ledger L-58) | `validation` owns `requires_human_review` once. |
| F-PROV-07 | DOWNGRADED in part: O3 quota clause struck (verify-05) | The **cost** half stands and is strengthened by verify-05 M2: the real-mode ceiling comes from the planner's LLM number, not `providers.pricing`. `budget` owns the comparison; `providers.pricing` owns the number. |
| F-GEN-08 | DOWNGRADED High 12 → 9 (verify-06) | Reference-asset catalog → `generation`/`storage` (L-39). |
| F-GEN-10 | CONFIRMED (verify-06) | Cost-model duplication is real: `budget` derives the ceiling from `providers.pricing`, never from the planner artefact. |
| F-ARTIFACT-03 | DOWNGRADED High 12 → **Medium 8** (verify-07) | Version re-derivation is Medium; `storage.contract` still owns the one rule. |
| F-BOUNDARY-01 / schemas count | CONFIRMED with corrections: the "eight domain→domain edges" is the union of three targeted greps, **not** an enumeration (V3); **322** schemas imports (not 323), split 252 cross + 70 intra (V4) | The law's justification is unchanged. The scope is fixed in **§4.6.1 (the FES)**, which settles the HEAD forbidden-edge count at **13** under an explicit target-module-granularity definition (the former 10 was a package-granularity result); the phrase "domain module" is not used by the target law at all. |
| F-BOUNDARY-05 | CONFIRMED but its `Reproduce` was broken (verify-14); two `app→graph` private sites missed (`app/_graph_exec.py:319,449`) | The L3 sweep must be **AST-based and indentation-agnostic** (B's `_harness` already is), and those two sites join the W5 offender set. |
| F-PHASE-05 / F-PHASE-06 | CONFIRMED, but one drift proof is inverted and one mutation clause false (verify-01) | The second order authority is real; `filmspec` owns the order. No catalog change. |
| F-OST-02 | DOWNGRADED High 15 → 12 (verify-02) | `orchestration` stall representation; priority only. |
| All findings | **0 REJECTED** across verify-01…09, 11…14 | No concern in §3 is removed by a verifier verdict. |

#### 2.7.3 The ~30 seams the audits missed, and the invariant/guard each one adds

Every row was found by a verifier, not by an audit, so it is new evidence for a
module already in the catalog (no new module is justified by these). Each is
folded into the named module's contract or guard list; the wave is the wave that
already owns that module.

| # | Missed seam (source) | Module | Invariant / guard to add |
|---|---|---|---|
| M1 | `_APPROVAL_DESTINATIONS` hand-copies `_PHASE_TO_NODE` (verify-01 M1) | `governance`/`orchestration` | derive both from `filmspec.PHASE_ORDER`; guard: no hand-written phase→node map |
| M2 | `_UPSTREAM_CONTENT_SOURCES` + **359** any-position phase strings vs the audit's 129 line-initial ones (verify-01 M2) | `filmspec` | the duplicate-literal sweep must scan **every** string constant, not line-initial entries (correction to W2's guard) |
| M3 | KB `applies_to_phases` is an unvalidated free-string phase registry (verify-01 M3) | `kb` | validate every manifest phase token against `filmspec.FilmPhase` at load; guard fails on an unknown token |
| M4 | `_orchestrator__active_review_cycles` is a dead channel with a live MCP reader (verify-02 M1) | `orchestration` | finish or delete the review-cycle lifecycle; it joins the `STATE_CHANNELS` writer sweep |
| M5 | `_resume_to_repair` is written by `app` and read inside `graph` (verify-02 M3) | `orchestration` | one writer; `operations` passes a value, never `state[...]` |
| M6 | Third model-profile vocabulary gates agent registration (`agents/registry.py:15-17`); **L-02 is O4 as well as O1+O5** — the map has **21** entries against an **11**-agent roster, 10 keys with no roster entry, and two tests pin the divergent values as correct (`tests/unit/graph/test_agent_profile_routing.py:21,:25`) (verify-03.1; V2) | `agents` | `AgentDescriptor.default_model_profile` is the **single profile authority**; delete the map, delete the `ModelRouter().list_profiles()` + `"orchestrator"` alias authority, and the two tests that encode the wrong values change with it |
| M7 | `runtime_overrides` hardcodes `creative_writer` (verify-03.4) | `config` | the env-override table is keyed by the profile vocabulary owner, not a literal |
| M8 | Agent-identity branches in prompt-context assembly (verify-04.1) | `agents` | per-agent prompt policy lives in `AgentDescriptor`; guard: no `if agent_id == …` outside `agents` |
| M9 | `scene-continuity-validator` has two contradictory `model_profile` values (verify-04.2) | `agents`/`validation` | the registry-agreement guard compares **values** (model profile), not only key sets |
| M10 | Provider API base URLs declared 3× (verify-05 M1) | `providers` | one endpoint vocabulary; guard: no `generativelanguage.googleapis.com` or OpenRouter URL outside `providers` |
| M11 | Real-mode spend ceiling from the planner's **LLM** number, not `pricing` (verify-05 M2) | `budget`/`providers` | `cap_for`/`authorize_spend` compare the `providers.pricing` number; guard asserts LLM estimate and pricing agree within tolerance |
| M12 | Two provider-health graph channels, one with accessors (verify-05 M3) | `providers`/`orchestration` | one representation, one channel; delete the accessor-less duplicate |
| M13 | Provider registry consumed as raw `Mapping[str, Any]` at 4 sites (verify-05 M4) | `providers`/`generation` | typed port; no `Mapping[str, Any]` provider argument |
| M14 | Provider-status string literals in the executor vs `ProviderJobStatus` (verify-06.1) | `generation` | use the enum; guard: no `"completed"`/`"failed"` job-status literals outside `providers` |
| M15 | `scene_id` is `"unassigned"` in the path and `""` in the sidecar/manifest (verify-06.2) | `generation`/`storage` | one scene-id default; media path is rebuildable from `(scene_id, shot_id)` |
| M16 | **The compositor writes image bytes straight to disk**, bypassing `ProjectStorage` (verify-06.3) | `generation`/`storage` | **L4 violation**: media writes go through `storage`; the storage-boundary guard bans the write surface, not just the imports |
| M17 | Two QC artifact-resolution rules: latest-on-disk vs pinned refs (verify-07 M1) | `validation`/`orchestration` | one resolution rule (pinned refs); the subgraph calls the same helper |
| M18 | Second and third "latest version" rules (`store.latest_version`, `mcp.tools.helpers`) (verify-07 M2) | `storage.contract` | one latest-version rule used by store, helpers, and `list_artifacts` |
| M19 | Fourth kind vocabulary (`AssetManifest.kind`) with live drift `generated_clip` vs `clip` (verify-07 M3) | `filmspec`/`storage` | `AssetKind` is declared in `filmspec`; the manifest validates against it (the ledger's clean row was wrong) |
| M20 | Read-side `artifact_id` never charset-validated (verify-07 M4) | `storage.contract` | `read`/`load` paths call `validate_artifact_id`; guard: a traversal id is refused on read |
| M21 | `consensus_report_ref`/`qc_patch_ref` bypass the channel registry via `updates[key]` (verify-08 M1) | `orchestration` | register both in `ORCH_CHANNELS`; the writer sweep must see **Name-subscript** writes too (a structural gap in the prototype sweep) |
| M22 | `validation_refs` (unregistered, MCP-written) vs `validation_report_refs` (registered, unwritten) (verify-08 M2) | `validation`/`orchestration` | one channel name, one writer |
| M23 | Consensus artefacts are stored with `artifact_type=script` (verify-08 M3) | `storage.contract`/`filmspec` | `type_for` refuses to fall back to `SCRIPT`; the kind exists in `filmspec` |
| M24 | `run_validation` cannot reach the phases its own dispatch table declares (verify-08 M4) | `validation` | one dispatch table that the tool actually uses; guard: every declared phase is reachable |
| M25 | Two artifact identities for one matrix: `shot_matrix` vs `master_film_matrix` (verify-09.1) | `filmspec`/`storage` | one id; the registry/kind agreement guard covers it |
| M26 | `kb_context_packet` is a registered kind with **no producer** (verify-09.2) | `kb`/`storage` | either produce it (so `kb_context_ref` resolves) or delete the row; guard: every registered kind has a producer **or** a declared no-producer disposition |
| M27 | `_ARTIFACT_TYPE_BY_CLASS` disagrees with the writers it serves (verify-09.3) | `storage.contract` | `type_for` is the one map; `MasterFilmMatrix → master_film_matrix`, `ExecutionBrief` present |
| M28 | The stdio transport erases `MCPErrorCode` (every failure → `-32000`) (verify-11.1) | `mcp` | the JSON-RPC error carries the typed code; guard: a confirmation refusal is distinguishable over the wire |
| M29 | `idempotency_key_field` is dead normative state (verify-11.2) | `mcp` | delete or populate; the contract guard covers every flag, not just `requires_confirmation` |
| M30 | `MCPServer.active_project_id` is a write-only second active project (verify-11.3) | `projects` | one active pointer; delete the server field (D-decisions in §3.8) |
| M31 | `actor_id`/`actor_type` never populated and never read (verify-11.4) | `studio`/`mcp` | the transport passes the actor; every mutation writes one audit event with it |
| M32 | `set_active_project` is an ungated process-global mutation (verify-11.5) | `mcp` | add to the danger classification; guard: every process-global mutation is confirm-gated |
| M33 | A fourth budget-cap vocabulary in `graph/context_packets.py:121-123` (verify-12.1) | `budget` | one cap reader; delete the plain-key read against the namespaced channel |
| M34 | `ProjectProfile.budget_cap_usd` is a distinct cap representation, read by nothing (verify-12.2) | `budget` | include it in the cap inventory or delete it |
| M35 | `delivery_manifest_ref` is a third name in the delivery seam (verify-12.3) | `post` | one artifact id, one state ref name |
| M36 | `post/validators.validate_delivery` is a third observer of the completeness rule (verify-12.4) | `post` | `REQUIRED_DELIVERY_ARTIFACTS` is read, not re-derived |
| M37 | `mcp.tools.get_runtime` is rebound by 2 conftests + 6 test-local patches (verify-13.1) | `devharness` | one runtime-injection mechanism; the harness factory is the only seam |
| M38 | Tests write `provider_health` as a raw dict **and** as a `ProviderHealthState` (verify-13.2) | `providers`/`devharness` | one value type; the harness seeds through the owner setter |
| M39 | A third agent-output wrapper is unbound to its template (`screenwriter_agent.py:54`) (verify-13.3) | `agents` | every canned payload is schema-bound to its template's declared wrapper |
| M40 | e2e builds a real `GitBackend` while the session fixture installs an in-memory one (verify-13.4) | `devharness` | one backend per tier; the parity test covers the pair |
| **M41** | **`import film_pipeline.graph.graph` alone poisons the storage root** — the module-level `graph = build_graph()` (`graph/graph.py:201`) runs `default_checkpoints_root()` inside the storage root while `PERSIST_STATE=1`, and the app then fails to open it (`StorageRootError`). **Critical (5×5=25)** — the highest-severity missed seam in the program (verify-10 M1) | `studio`/`orchestration`/`checkpoints` | no import-time side effect: the compiled graph is built by `studio` (L6/D8) *after* roots resolve, and a guard asserts importing any production module performs no filesystem write; state-ownership row in §5 |
| **M42** | **`NO_PERSIST` does not gate the root when `RUNTIME_ROOT` is set** — a runtime whose policy reports "not persistent" still writes `storage.json`, the marker and `project.json` durably (verify-10 M2; High 4×4=16) | `studio`/`storage` | one `resolve_roots()` whose policy is authoritative for **every** root; guard: the "non-persistent invocations never write home or CWD" bar holds for every flag combination |
| **M43** | `SafetyService.persist_root()` ignores the root in use, so delete archives cross-root (verify-10 M3; High 4×3=12) | `studio`/`storage` | actions use the resolved `RootLayout`, never a re-derived root |
| **M44** | `request_revision` ignores `_has_pending_human_interrupt`'s negative branch twice (verify-10 M5; Low, recorded not scored) | `governance`/`operations` | the pending-interrupt predicate is consulted once, at the decision point |

#### 2.7.4 Verification is complete; the verify-10 result

`verify-10.md` (checkpoints and runtime persistence) has landed: **11/11 findings
CONFIRMED, 0 rejected**, with two severity recomputations (F-CRP-05 High 12 →
**Medium 9**; F-CRP-10 High 9 → **Medium 6**) and four seams the audit missed.
The five affected ledger concerns — **L-11, L-21, L-22, L-42, L-43** — are
therefore `VERIFIED` in §2.7.1. Two verifier corrections bear directly on this
design:

- **F-CRP-01's framing is disputed, not its substance** (verify-10 §2.3):
  `resolve_storage_root()` has one reader path today and is already single-owned
  by `storage` (`audit/03` records it clean, guarded by
  `tests/unit/artifacts/test_storage_guards.py`). What is unowned is the
  **composition** of the root paths, not the storage root itself. This confirms
  **D8**: `studio` owns the *policy and composition* (`resolve_persistence()` /
  `resolve_roots()`), `storage` keeps `resolve_storage_root()` and its existing
  guard tests, `checkpoints` owns the checkpoint lifecycle. No owner moves.
- **The four missed seams (M41–M44, §2.7.3)** add a **Critical** entry:
  importing `film_pipeline.graph.graph` alone poisons the storage root via the
  module-level `graph = build_graph()` (`graph/graph.py:201`), and with
  `RUNTIME_ROOT` set a runtime whose policy says "not persistent" still writes
  durable state (`app/runtime.py:59-77`). Both are `studio`/`storage` seams and
  both join **W6** (persistence policy), which is now the highest-value wave
  after W0/W2 rather than a routine one.

Nothing in this document is pending verification.

### 2.8 Prior art: what `documentation/architecture-blueprint.md` already fixes, and what this design supersedes (adversarial O-19)

`AGENTS.md:8` names `documentation/architecture-blueprint.md` as the architectural
source of truth, and `AGENTS.md:51` states the `artifacts`-only law this document
deletes. The `AGENTS.md:51` contradiction is declared (§4.1's "Deleted" paragraph);
the blueprint was previously cited **0 times** in `00`–`05`, which is B9's "existing
contract" half unmet. Recorded explicitly:

- **What the blueprint fixes and this design keeps.** Its six System Layers
  (`:19-118`) are *subject-matter* layers, in this order: **1 MCP Operator Surface**,
  2 Orchestration, 3 Agent, 4 Knowledge, 5 Artifact, 6 Extension. Its design rule
  (`:15-16`) is: *"do not treat MCP as a late wrapper around an internal app. The MCP
  contract is the product boundary. LangGraph is the execution engine behind that
  boundary."* Both are preserved: `mcp` (L11) owns the `ToolContract`, the JSON
  shapes and the error taxonomy, **nothing imports `mcp` except the composition
  root** (§4.3, §8's freeze row), and the blueprint's layer 2 already assigns
  "execution behind MCP tool calls" to LangGraph — which is exactly the target's
  `orchestration` (L9) sitting below `operations` (L10) and `mcp` (L11).
- **What this design supersedes.** The blueprint's layer list is an ordered
  *inventory*, not an import lattice: it has no cycle rule, no notion of a private
  reach, no allowed-edge matrix, and it does not say which layer may import which
  (its Artifact layer 5 sits *below* Extension layer 6, while the target puts
  `storage` at L3 and the extension surfaces `providers`/`agents` above it). L0–L12
  is a **refinement that makes the blueprint's order total, acyclic and mechanically
  checkable**, and it must not be read as demoting MCP: the blueprint's rule is about
  who owns the *contract*, and the contract still belongs to `mcp`.
- **The one genuine divergence, and its resolution.** The blueprint's phrase "MCP
  owns … generation planning, provider health checks, checkpoint creation, rollback
  requests" (`:26-40`) reads as MCP *implementing* those capabilities. The target
  keeps MCP owning all of them **as contract** while `operations` (L10) implements
  them and `mcp` calls it (§4.3; FES #4–#13 are precisely the HEAD edges that
  conflated contract with implementation, and W11 removes them). This is the only
  place where the target narrows a blueprint sentence, and it is F-MCP-04/05's
  parallel-lifecycle finding that forces it.
- **Not superseded:** `documentation/architecture-blueprint.md` remains the product
  description; this document is the module/import law. Where they differ on module
  identity, this document wins for the reason above, and the divergence is listed
  here rather than left silent.

---

## 3. Module catalog

Twenty modules, each with a one-sentence responsibility, explicit non-goals, the
public contract, the invariants it owns (N/I/R per `00` §1.2), the state it owns,
and its allowed outbound/inbound edges. **L** is the layer (§4). "Evidence" cites
the audit finding(s) or measurement that justify the module existing at all — no
module here is a "future flexibility" layer (B9).

**The `public_api` declared in each entry is binding, and §3.21 corrects it against
measurement.** A declaration that omits a name another module actually imports
cannot be enforced (adversarial O-05): `ModuleContract.public_api` is what
`test_cross_package_imports_use_the_declared_public_api` will compare imports
against, so every name with a *legal* target importer must appear here and every
name that moves or disappears must say so. §3.21 is the measured, per-module
reconciliation, re-run at `fb85baa`; where an entry below and §3.21 differ, **§3.21
is the correction and the entry's measured-additions clause is authoritative**.

### 3.1 `filmspec` — L0

- **Responsibility.** Defines the normative vocabulary of the studio and the
  pure laws over it: film phases and their order, phase→gate, issue severities
  and the blocking predicate, validation statuses, generation statuses, agent
  roles/families, and the artifact-kind vocabulary.
- **Non-goals.** does not import anything (`film_pipeline` or third-party
  runtime); does not define payload *shapes* (that is `schemas`); does not decide
  whether a phase advances at runtime (that is `governance`); does not own the
  persistence spec per kind (that is `storage`); does not hold state.
- **Public contract.** `FilmPhase` (+ `order()`, `next_phase()`, `gate_for()`,
  `is_agnostic()`, `generation_dependent()`), `PHASE_ORDER`, `PHASE_GATES`,
  `ArtifactType`/`ArtifactKind` (47 storable ids + 3 declared non-storable media
  names), `AssetKind` (the `AssetManifest.kind` vocabulary — verify-07 M19),
  `IssueSeverity`, `blocking_issue(...)`, `is_blocking(issue)`,
  `ValidationStatus`, `GenerationStatus`, `AgentRole`, `AgentFamily`.
- **Owns.** N for every vocabulary above; I for the pure predicates
  (`is_blocking`, `next_phase`, `gate_for`).
- **State.** None. Module constants only.
- **Allowed outbound.** **none** — the only module with zero imports.
- **Allowed inbound.** every module (it is `ALWAYS_IMPORTABLE`-like; no
  `may_import` entry is needed to import L0).
- **Evidence.** F-PHASE-02 (11 independent phase definitions in 8 modules),
  F-PHASE-05 (order encoded in `PHASE_DIR_MAP` insertion order), F-PHASE-09,
  F-SEV-01/`48` blocking literals, F-ARTIFACT-02/-08 (47/45/39), F-OST-15,
  `enola` §5 (`orchestrator_state` 38/38 exported with no boundary); **verify-01
  M2** — the sweep must count **all** phase-string constants (359 at HEAD), not
  only line-initial ones (129), and **verify-07 M3** — the `AssetKind` vocabulary
  already diverges (`generated_clip` vs `clip`).

### 3.2 `schemas` — L1

- **Responsibility.** Defines every typed Pydantic payload exchanged or
  persisted: artifact payloads, MCP request/response envelopes, graph state
  snapshots, registry entry records.
- **Non-goals.** does not define enums/constants that `filmspec` owns (it
  imports them); does not perform I/O; does not enforce cross-object policy
  (only field-level schema validity); does not re-export its private
  `schemas/base.py` through a façade that creates C5.
- **Public contract.** the existing 40 `schemas/*.py` public models plus
  `SchemaBase` (currently `schemas/_base.py:265`); `schemas/registries/*` stay
  here as payload records but are **not** re-exported through
  `schemas/__init__.py` (C5).
- **Owns.** N+R of payload shape only. It never writes artifacts.
- **State.** None.
- **Allowed outbound.** `filmspec`.
- **Allowed inbound.** every module.
- **Evidence.** `enola` §3 (`schemas` fan-in 509, the shared kernel by
  measurement); F-BOUNDARY-02 (72 files reach the private `_base`); C5.

### 3.3 `config` — L2

- **Responsibility.** Loads profile stacks from `profiles/`, merges them in
  declared order, validates the merged result's *shape*, and produces the
  resolved-config value consumed by the graph and runtime.
- **Non-goals.** does not resolve provider credentials (that is
  `providers.required_credentials`, called by `studio`); does not read project
  storage; does not resolve roots or persistence mode; does not decide phase or
  gate mode.
- **Public contract.** `load_profile_flex`, `ProfileStack`, `merge_profiles`,
  `validate_resolved_config`, `apply_runtime_overrides`. **Measured additions
  (§3.21, adversarial O-05)** — two names with a legal importer that the
  declaration omitted: `ProfileLoader` (`studio`) and the `profile_resolver`
  module surface (`operations`). **Via `operations`:** `canonicalize_profile_stack`,
  `missing_provider_credentials`, `provider_specs_from_raw`, `resolve_project_config`
  and `register_project_providers` are imported only by `mcp` at HEAD; their edges
  are deleted, and `register_project_providers` additionally leaves `config`
  entirely (FES #1).
- **Owns.** N+I for profile merge order and config validity.
- **State.** None (parsed YAML cache keyed by path+mtime only).
- **Allowed outbound.** `filmspec`, `schemas`.
- **Allowed inbound.** `orchestration`, `operations`, `studio`.
- **Evidence.** F-CFG-01/02/05/06/07/09/10/12/13; `01` §3; R-10 (the
  `config → providers` private-credential edge disappears).

### 3.4 `kb` — L2

- **Responsibility.** Resolves the knowledge-base root, reads the manifest,
  retrieves and compresses entries, detects conflicts, builds
  `KBContextPacket`s, and mints/stamps `kb_context_ref` provenance.
- **Non-goals.** does not decide which agent gets which KB domains (agent
  contracts declare that; `orchestration` calls this module); does not write
  project storage (it passes the ref to the writer, which is `storage`); does not
  own the KB *content* (data).
- **Public contract.** `resolve_kb_root`, `load_manifest`, `search`,
  `build_packet`, `compress`, `detect_conflicts`, `KBContextRef`,
  `new_kb_context_ref`. **Measured additions (§3.21, adversarial O-05)** — five
  names with a legal importer that the declaration omitted:
  `DEFAULT_MAX_CONTEXT_CHARS`, `compact_json_context` (`orchestration`),
  `KBContextPacketBuilder` (`orchestration`), `KBManifest`, `kb_manifest_path`
  (`studio`). `KBRetrieval` is imported only by `mcp`, whose edge §4.3 deletes, so
  it moves behind `operations` rather than into `public_api`.
- **Owns.** N+I+R for the KB root, the manifest format, and the provenance id;
  R of the ref's bytes is delegated to `storage`.
- **State.** KB root resolution (env → explicit → repo layout); no project
  state.
- **Allowed outbound.** `filmspec`, `schemas`.
- **Allowed inbound.** `orchestration`, `operations`, `studio`, `devharness`.
- **Evidence.** F-KBPATH-01 (3 CWD-relative resolvers), F-KBCTX-01/02/03/04/05/06
  (4 context systems, 3 id grammars, 1-of-12 write paths stamps provenance),
  F-KBCTX-09; `01` §17 (conflict detection already single-owner, kept).

### 3.5 `constraints` — L2

- **Responsibility.** Turns user intent (idea text + explicit hints) into one
  validated `ProjectConstraints`, including the number-word/scene-count grammar.
- **Non-goals.** does not own the scope contract (`orchestration` consumes the
  scene count); does not render prompts; does not define agent behaviour or
  invoke models; does not store state.
- **Public contract.** `extract_constraints(text, project_id, hints)`,
  `render_constraints`, `ProjectConstraints`, `ConstraintExtractor`,
  `_NUMBER_WORDS`/`first_number_for_unit` (absorbed from
  `graph/nodes/_shared.py:29-82`).
- **Owns.** N+I for the extraction grammar and keyword tables (single owner
  today, `01` §17).
- **State.** None.
- **Allowed outbound.** `filmspec`, `schemas`.
- **Allowed inbound.** `orchestration`, `operations`, `studio`, `devharness`.
- **Evidence.** `audit/12` §6.3 and §5 (SINGLE/clean today), F-BUD-05 (duplicate
  number-word grammar); R-7 (kept standalone rather than folded into `agents`).

### 3.6 `storage` — L3 (today's `artifacts`)

- **Responsibility.** Is the only module that reads or writes the studio storage
  root: root marker gating, project layout, the versioned artifact store
  (envelopes, checksums, migrations), the derived index, manifest, and the
  on-disk project record / graph-state / checkpoint / audit files.
- **Non-goals.** does not import any module above L1 (this exact prohibition is
  already enforced by `tests/unit/artifacts/test_storage_boundary.py:101-130`);
  does not own checkpoint *policy* (`checkpoints`); does not own KB or runtime
  roots (`kb`, `studio`); does not own the phase order (`filmspec`).
- **Public contract.** `ProjectStorage` (project record, graph state,
  checkpoints JSONL, audit-log JSONL, `media_dir`, manifest, git backend),
  `ArtifactStore` (`save`, `save_mutable`, `load`, `load_latest`,
  `list_artifacts`, `envelope`), `ArtifactKindRegistry`/`REGISTRY`/`KindSpec`
  (with `MIGRATIONS`, renderers, `validate_artifact_id`), `resolve_storage_root`,
  `ensure_storage_root`, `PROFILE_PRODUCTION`, `PROFILE_SANDBOX`, and the
  `storage.contract` submodule (§3.6.1). **Measured additions (§3.21, adversarial
  O-05)** — ten names other target modules import today and the target still needs,
  every one with a legal importer: `AssetManifest`, `AssetEntry`, `read_manifest`,
  `write_manifest` (`generation`, `operations`), `default_checkpoints_root`
  (`orchestration`), `default_runtime_root`, `default_run_root`,
  `graph_state_location`, `set_git_backend_type` (`studio`), `init_storage_root`
  (`devharness`). `ArtifactStore`, `ProjectStorage`, `resolve_storage_root`,
  `ensure_storage_root`, `PROFILE_PRODUCTION`/`PROFILE_SANDBOX`, the registry names
  and `storage.contract` were already declared.
  `sanitize_artifact_id` is **not** added: its only importer is `mcp`, whose edge
  §4.3 deletes, so it stays `storage.contract`'s id grammar reached through
  `operations`.
- **Owns.** N (persistence spec per kind: payload model, version, mutability,
  migration, renderer) + I (marker gating, checksum verification, kind
  registration on save, schema-generation gate) + R (every byte under the root).
- **State.** the storage root on disk; the in-process kind registry.
- **Allowed outbound.** `filmspec`, `schemas`. **Nothing else, ever.**
- **Allowed inbound.** `projects`, `checkpoints`, `budget`, `validation`,
  `generation`, `post`, `governance`, `orchestration`, `operations`, `studio`,
  `devharness`.
- **Evidence.** `01` §7 and §17 (the one properly owned subsystem, guarded by
  `tests/unit/artifacts/test_storage_boundary.py`); `audit/07` §6.1 (the ten
  things storage already owns single-handedly); R3.

#### 3.6.1 `storage.contract` — the derivation/enforcement submodule (D4)

- **Responsibility.** Owns the artifact contract's *derivation and enforcement*:
  the ref's derived form, kind→type derivation, kind resolution that refuses
  instead of fabricating, the read-time schema gate, and the artifact /
  generation status transition tables.
- **Non-goals.** does **not** own layout, does **not** write files, does **not**
  own payload models, is **not** a second storage module (R3), and is not a
  top-level catalog entry.
- **Public contract (seven names, no more).** `ArtifactRef` + `stem()`;
  `type_for(artifact_id, payload) -> ArtifactType` (no silent `SCRIPT`);
  `kind_spec_for(artifact_id) -> KindSpec` (raising, used by read **and** write);
  `check_readable(spec, found_version, path) -> None`;
  `ArtifactStatusPolicy.assert_transition(current, next)` +
  `GenerationStatusPolicy.assert_transition(current, next)`;
  `read_meta(path) -> ArtifactCurrentMeta`. **Plus `sanitize_artifact_id(raw_id) -> str`**
  (`artifacts/registry.py:56`), the formatter counterpart of `ArtifactRef` and the
  other half of the formatting/parsing symmetry this submodule owns (F-ARTIFACT-01):
  it is added here — *not* to `storage.public_api`, because its only HEAD importer
  is `mcp`, whose edge §4.3 deletes — and `operations` publishes the one operation
  that uses it (adversarial O-05). Backing these: the **one**
  latest-version rule (used by `next_version`, `latest_version`, the MCP helper
  and `list_artifacts` — verify-07 M2/V4) and **read-side** `validate_artifact_id`
  on every `load` path (verify-07 M4), which today only runs on write.
- **Owns.** I for ref formatting/parsing symmetry, kind resolvability, the one
  version rule, read-side id validation, and the two transition laws. N of the
  kind *vocabulary* is `filmspec`'s; N of the per-kind persistence spec is
  `storage`'s.
- **State.** None (derives from `REGISTRY` and `filmspec`).
- **Evidence.** F-ARTIFACT-01 (second formatter `review/diff._id_stem`),
  F-ARTIFACT-02/-08 (triple-defined kind↔type), F-ARTIFACT-03 (9 caller-side
  version derivations), F-ARTIFACT-04/-05 (8 schema axes, per-path read
  enforcement), F-ARTIFACT-06/-07 (status + `GenerationStatus` transition
  law), F-ARTIFACT-09 (fabricated spec on read); `audit/07` §6.2/§6.3; R3.

### 3.7 `providers` — L3

- **Responsibility.** Declares the provider adapter port, implements the
  concrete model/image/video adapters, resolves credentials, prices requests,
  classifies failures, and reports provider health.
- **Non-goals.** does not know about agents, prompts or generation ledgers; does
  not decide which provider to use (the model router and the generation planner
  do); does not re-export concrete adapters through its package façade (C4).
- **Public contract.** `BaseProviderAdapter`, `ProviderRegistry`, `ProviderEntry`,
  `credentials.lookup/env_or_dotenv/redact/env_var_for` (the private
  `_env_var_for` is published), `required_credentials(provider_ids)`,
  `estimate_cost_for_duration`, `classify_failure`, `health.check`,
  `build_provider_adapter` (factory); concrete adapters are imported by `studio`.
  **Measured additions (§3.21, adversarial O-05)** — eight names with a legal target
  importer that the declaration omitted: `ProviderJob`, `ProviderJobStatus`
  (`generation`), `credentials` as a module (`studio`), `compress_prompt_for_retry`,
  `is_token_limit_exceeded` (`agents` — these two plus `classify_failure` are one
  surface; the declared `classify_failure` is the target name for the predicate they
  implement), `pricing_prompt_block` (`orchestration`), `OPENROUTER_API` (`agents`,
  from the concrete adapter — the one adapter-level constant that must stay public),
  and `ScenarioStep` (`devharness`). `PROVIDER_PRICING`, `tier_for` and
  `is_configured` are **not** added: their importers (`mcp`, and `config` whose edge
  FES #1 deletes) lose those edges, so the reads move behind `operations` /
  `required_credentials`.
- **Owns.** N+I for provider identity, credential naming, pricing, failure
  taxonomy, and **provider health** (§5).
- **State.** credential cache; adapter instances built by `studio` (never a
  module-level singleton — L6).
- **Allowed outbound.** `filmspec`, `schemas`.
- **Allowed inbound.** `agents`, `generation`, `orchestration`, `operations`,
  `studio`, `devharness`.
- **Evidence.** F-PROV-01/02/03/04/05/06, F-CFG-05/11 (credential resolution
  policy), F-OST-13 (provider health representations); C4.

### 3.8 `projects` — L4

- **Responsibility.** Owns the project registry: creation (id, slug, root),
  durable record binding, lookup/list/resolve, and the single active-project
  pointer for a session.
- **Non-goals.** does not run the graph; does not expose MCP shapes; does not
  write storage files directly (uses `storage.ProjectStorage`); does not resolve
  roots or persistence mode.
- **Public contract.** `ProjectRegistry` (`create`, `get`, `list`, `resolve`,
  `set_active`, `active`), `ProjectRecord`, `new_project_id`.
- **Owns.** N+I for project identity; R for the active pointer.
- **State.** the in-memory project map and active id — one place, replacing
  `StudioRuntime.projects` + `active_project_id` (`app/runtime.py:43-44`) and
  `mcp/tools/helpers._active_project_id`.
- **Allowed outbound.** `filmspec`, `schemas`, `storage`.
- **Allowed inbound.** `operations`, `mcp`, `studio`.
- **Evidence.** F-RUNTIME-01 (`StudioRuntime` is 3 responsibilities, 15 fields),
  F-MCP-07 (two project registries with no agreement check), F-CRP-01/-08
  (roots and discovered projects); A §5.13.

### 3.9 `checkpoints` — L4

- **Responsibility.** Owns the checkpoint lifecycle: create at phase boundaries,
  branch, invalidation propagation, resume payload selection, and rollback.
- **Non-goals.** does not write project files itself (goes through
  `storage.ProjectStorage`); does not import `orchestration` (the composition
  root injects the graph handle and the storage backend); does not own the
  persistence *policy* (`studio`).
- **Public contract.** `CheckpointManager`, `GitBackend` (structural protocol),
  `create_checkpoint`, `invalidate`, `resume_from`, `rollback`, `branches`,
  `ResumePayload`, `RollbackRecord`. **Via `operations` (§3.21):**
  `InvalidationEngine` and `RollbackManager` are imported only by `mcp` at HEAD;
  both fold into `CheckpointManager` (§6.1) and the `mcp` tools reach them through
  `operations`, so neither is a `checkpoints.public_api` name. The LangGraph SQLite
  saver is explicitly *not* this module's contract (§5, §8).
- **Owns.** N+I for checkpoint semantics, invalidation rules and the rollback
  record factory; R is delegated to `storage`.
- **State.** one checkpoint metadata registry; git repository per project (via
  the injected backend).
- **Allowed outbound.** `filmspec`, `schemas`, `storage`.
- **Allowed inbound.** `operations`, `studio`, `devharness`.
- **Evidence.** F-CRP-02 (two in-memory registries), F-CRP-04 (two writers of
  `artifact_versions`), F-CRP-05 (two resume implementations), F-CRP-06 (two
  rollback authorities, no audit event), F-CRP-07 (hand-maintained invalidation
  map vs real parentage); `audit/10` §3, §6.

### 3.10 `agents` — L5

- **Responsibility.** Declares the agent roster and its contracts, holds the
  versioned prompt framework and templates, routes a task to (agent, model
  profile, prompt), and executes the model call with retry and failure
  classification.
- **Non-goals.** does not import concrete provider adapters (only the
  `providers` port, credentials, pricing, failure taxonomy — R-10); does not
  know about graph state or phases (receives a task and context); does not write
  artifacts (`orchestration` saves agent outputs through `storage`); does not own
  constraint extraction.
- **Public contract.** `AgentCatalog` (one declaration replacing
  `agents/registry.py` + `agents/impl/registry.py` + `mvp/__init__.py`),
  `AgentRegistration`, `MVP_AGENTS`, `capabilities_for`, `implementation_for`,
  `PromptTemplateRegistry`, `get_registry`, `PromptRunner.run`,
  `ModelRouter.select`, `ModelAdapter` (concrete-adapter import removed),
  `BaseAgent`. **Rename reconciliation (§3.21):** `AgentRegistry`
  (`agents/registry.py`, imported by `orchestration`) becomes `AgentCatalog`; the
  HEAD name stays in `public_api` as the W0–W10 pre-image. **Deleted:**
  `get_agent_class` (`agents/impl/registry.py`) is *not* carried — the
  three-registry collapse replaces it with `AgentCatalog.implementation_for`, and
  its one legal importer (`orchestration`) migrates. The bible agents
  (`CameraBibleAgent`, `CharacterBibleAgent`, `EnvironmentBibleAgent`,
  `ShotBibleAgent`, `StyleBibleAgent`) are imported only by `mcp` and are reached
  through `operations`.
- **Owns.** N+I for the agent catalog, prompt templates, model routing, and
  response parsing.
- **State.** in-process catalog + prompt registry, built by `studio`.
- **Allowed outbound.** `filmspec`, `schemas`, `providers`.
- **Allowed inbound.** `orchestration`, `operations`, `studio`, `devharness`.
- **Evidence.** F-AGENT-01…10, F-AGENTREG-01/`proposal-A` (3 registries + a
  fourth serializable shape, 12 impl keys vs 11 MVP agents), F-POST-02
  (`failure-handling-agent` in 5 registries); `enola` §4
  (`ModelAdapter.chat` 25 dependents).

### 3.11 `budget` — L5

- **Responsibility.** Owns one `BudgetState`: resolves the project cap once,
  authorizes spend, and records actual spend.
- **Non-goals.** does not estimate provider costs (`providers.pricing`); does not
  own generation ledger rows (`generation`); does not route the graph (returns a
  verdict; `orchestration`/`operations` react); does not hold the phase decision
  (`governance`).
- **Public contract.** `cap_for(project_id) -> float`;
  `authorize_spend(project_id, batch) -> None` (raises `BudgetExceeded`);
  `record_spend(project_id, phase, usd, source)`; `BudgetState`, `SpendRecord`.
- **Owns.** N+I for the **cap policy** — what the cap gates, the refusal semantics,
  and the spend record (F-BUD-01/02/03) — and N for the `budget_cap` prompt
  variable (F-BUD-04). **The cap's *value* has one source and it is not `budget`,
  `config` or `generation`:** `ProjectRecord.budget_cap_usd` (`schemas/project.py:43`),
  the single persisted field created once at project creation from the resolved
  profile. N for that field's shape is `projects`'; `config` produces its *initial*
  value from `profiles/*.yaml` only at creation time and is never consulted at gate
  time; `budget` reads it through `storage` (its outbound set is `filmspec`,
  `schemas`, `storage`, so **no `budget → config` edge exists or is needed**) and
  caches nothing. This is the adversarial O-10 correction: the former text claimed
  N+I+R over "the cap value", which the matrix made unreachable — `budget → config`
  was forbidden and the profile cap is unreachable without it, while
  `schemas/constraints.py:93` and the `max_total_usd` key carried *other* caps. The
  three other cap representations (`BudgetState.cap_usd`, `constraints.budget_cap_usd`,
  the `mcp/tools/planning.py:22` `100.0` default) are collapsed onto this one field:
  `BudgetState.cap_usd` becomes a *projection* of it, `constraints.budget_cap_usd`
  keeps only its constraint-parsing meaning, and the MCP default becomes a
  `cap_for` read.
- **State.** the durable budget/spend document under the project (written
  through `storage`) — **a new representation, listed in §8**. The cap value itself
  is not this module's state; it is read from the project record.
- **Allowed outbound.** `filmspec`, `schemas`, `storage`.
- **Allowed inbound.** `generation`, `governance`, `orchestration`,
  `operations`, `studio`.
- **Evidence.** F-BUD-01 (4 caps), F-BUD-02 (8 gate sites, only 1 can refuse),
  F-BUD-03 (`spent_usd` always 0; `SpendRecord` zero writers — a defect),
  F-BUD-04 (`budget_cap` derived twice; prompt reads the unwritten key),
  F-CFG-06; `audit/12` §3/§6.4. **This contradicts `01` §12's `governance`
  candidate — see §2.4.3.**

### 3.12 `validation` — L6

- **Responsibility.** Owns the validator registry and threshold policy, runs
  validators against artifacts, and is the single writer of `ValidationReport`
  and `ConsensusReport`.
- **Non-goals.** does not decide whether a phase may advance (that is
  `governance`, which consumes reports); does not import `orchestration`; does
  not own the review package or the human-gate action set (that is
  `governance`); does not import a concrete model adapter (prompt/model calls
  are injected).
- **Public contract.** `ValidatorRegistry`, `ValidatorRegistryEntry`,
  `BaseValidator`, `run_validators(...) -> ValidationReport`,
  `save_report(report, store, ...) -> ArtifactRef`, `load_latest_report(...)`,
  `score_to_status`, `thresholds`, `ConsensusBuilder.build(...)`,
  `PHASE_VALIDATORS` (one dispatch table). **Measured additions (§3.21, adversarial
  O-05)** — eight names with a legal importer that the declaration omitted:
  `MVP_VALIDATORS` (`studio`; the target's renamed dispatch table, declared here as
  `PHASE_VALIDATORS`), and the seven concrete validators
  `AssemblyValidator`, `DeliveryCompletenessValidator`, `DialogueVoiceValidator`,
  `PromptReadinessValidator`, `ReferenceUsabilityValidator`,
  `SceneContinuityValidator`, `ScriptStructureValidator` (`orchestration`, `post`,
  and `mcp` — `mcp → validation` is one of `mcp`'s six legal edges, so these stay
  public rather than moving behind `operations`).
- **Owns.** N+I+R for validation/consensus reports and the four-status law
  (`validation/base.py:265`); N for score→status bands.
- **State.** the validator registry; `validation_report_ref` /
  `consensus_report_ref` (published as channels, §5).
- **Allowed outbound.** `filmspec`, `schemas`, `storage`.
- **Allowed inbound.** `post`, `governance`, `orchestration`, `operations`,
  `mcp`, `studio`, `devharness`.
- **Evidence.** F-VR-01/02/03/04/05/06/07/08/09/10/11, F-VAL-01 (two report
  representations and two writers), F-PHASE-10/F-MCP-04 (4 dispatch tables);
  `audit/08` §2/§4.3 (adopted except its gate-policy ownership, R-4).

### 3.13 `generation` — L6

- **Responsibility.** Owns the generation ledger lifecycle (plan → approve spend
  → start → poll → deliver/fail → retry/delta), prompt preparation for provider
  calls, provider dispatch, frame/sheet review, and the reference-sheet
  compositor.
- **Non-goals.** does not write graph state channels (returns deltas); does not
  import `orchestration`; does not import `agents` (prompts come from matrix rows
  via `prompt_builder`); does not own the project cap (`budget`).
- **Public contract.** `GenerationLedgerManager`, `LEDGER_ARTIFACT_ID`,
  `GenerationExecutor`, `plan`, `approve_spend` (ceiling derived here, **not**
  at call sites), `start`, `poll_once`, `delta_regenerate`, `build_prompt`,
  `compositor`, `frame_reviewer`. **Measured additions (§3.21):**
  `build_structured_prompt` (`orchestration`). **Via `operations`:** the compositor
  builders (`build_character_identity_sheet`, `build_environment_board`,
  `build_expression_sheet`, `build_scale_sheet`, `build_style_board`), the frame
  reviewers (`review_frame`, `should_review_frame`, `review_composite_sheet`,
  `run_heuristic_checks`) and `write_frame_sidecar` are imported only by `mcp` at
  HEAD, so they stay internal and `mcp` reaches them through `operations`.
- **Owns.** N+I+R for the generation ledger and its transitions; I for the spend
  ceiling; I for prompt assembly for a shot.
- **State.** the `generation_ledger` artifact (mutable, revision-counted) and
  in-flight provider job ids.
- **Allowed outbound.** `filmspec`, `schemas`, `storage`, `providers`, `budget`.
- **Allowed inbound.** `orchestration`, `operations`, `studio`.
- **Evidence.** F-GEN-01…12, F-GEN-01/`proposal-A` (MCP ceiling `-1.0` vs graph
  `× 1.1`), F-BUD-03/04, F-ARTIFACT-07; A §5.11, A §10.4 (compositor stays).

### 3.14 `post` — L7

- **Responsibility.** Owns the assembly, subtitle, transition, audio-design and
  delivery-packaging agents' behaviour, the delivery-completeness rule, and the
  post-phase validators.
- **Non-goals.** does not implement the MCP stubs that call it; does not own
  the assembly *policy* (the operator decides; this module builds the plan and
  package); does not import `validation.impl` private modules (L3).
- **Public contract.** `AssemblyAgent.build(state) -> AssemblyManifest`,
  `SubtitleAgent`, `TransitionAgent`, `AudioDesignAgent`,
  `DeliveryPackagingAgent.build_package`, `REQUIRED_DELIVERY_ARTIFACTS`,
  `post.validators`.
- **Owns.** N+I for the delivery package structure and the completeness rule
  (single source, F-POST-04); R for `assembly_manifest` and the delivery
  package.
- **State.** None (produces artifacts through `storage`).
- **Allowed outbound.** `filmspec`, `schemas`, `storage`, `validation`.
- **Allowed inbound.** `orchestration`, `operations`, `studio`.
- **Evidence.** F-POST-01…07, F-POST-04 (`post` and `validation.impl` already
  disagree on the same package); `audit/12` §6.1/§6.2; R-10.

### 3.15 `governance` — L8

- **Responsibility.** Decides, from a phase, its validation reports, its issues,
  the budget verdict and the resolved config, whether work may advance, must be
  repaired, must escalate, or must await a human — and owns the gate names,
  repair-loop bounds, review-package assembly, diffing, and the human-facing
  available/blocked action set.
- **Non-goals.** does not run validators (consumes `validation` reports); does
  not import `orchestration`, ever (this is the invariant that keeps the graph
  acyclic); does not execute agents; does not write checkpoints; **holds no
  state** — a stateless decision module cannot join a cycle (A §10.6).
- **Public contract.** `PhaseDecision`
  (`advance|repair|escalate|await_human`),
  `evaluate_phase(phase, reports, issues, budget_verdict, resolved_config) ->
  PhaseDecision`, `advance_decision(...)` (the one transition invariant,
  including the provider-blocked-generation refusal of F-PHASE-01),
  `RepairPolicy`, `compute_available_actions`, `build_review_package`,
  `diff_versions`, `blocking_issues(issues)`, `ACTION_DESTINATIONS` (one
  action→edge table). **Measured additions (§3.21, adversarial O-05)** — twelve
  names with a legal importer that the declaration omitted, and the single largest
  omission in this catalog: `ReviewPackageGenerator` (`mcp`), `check_phase_consistency`,
  `derive_scope_contract`, `pacing_from_config`, `load_execution_brief`,
  `validate_dispatch_readiness`, `validate_execution_brief`,
  `validate_planning_completeness`, `validate_scene_count`,
  `validate_script_scene_preservation`, `validate_shot_scene_references`,
  `validate_shot_structure` (all `orchestration`, L9→L8). These are the moved
  `graph/consistency.py`, `graph/scope_contract.py` and
  `graph/orchestrator_validators/*` surfaces; without them in `public_api`, the
  entire governance half of the `graph` split would be unenforceable.
- **Owns.** N+I for advancement policy, gate identity, repair bounds,
  review-package content, and the gate action vocabulary.
- **State.** none.
- **Allowed outbound.** `filmspec`, `schemas`, `storage`, `budget`, `validation`.
- **Allowed inbound.** `orchestration`, `operations`, `mcp`, `studio`.
- **Evidence.** F-GATE-01/`proposal-A` (phase-advance policy in 5 packages),
  F-PHASE-01/-03/-04/-06/-07 (two advances; app path skips the
  provider-blocked gate), F-OST-04/-05/-09/-11 (gate label, 4 vetoes, action
  prose), F-VR-06 (approve-vs-revise at 6 sites), F-VR-09/-10, `review/actions.py`
  and `review/generator.py`; `01` §1/§8.

### 3.16 `orchestration` — L9 (today's `graph`)

- **Responsibility.** Owns the pipeline graph: the typed state schema and its
  reducers, the phase topology and edges, node implementations that run agents
  and persist phase artifacts, interrupts and resume, the orchestrator working
  state and its channel registry, and the projections that turn domain deltas
  (generation ledger rows, KB packets, issue lists) into graph state.
- **Non-goals.** does not decide gate policy (calls `governance`); does not run
  validators (calls `validation`); does not drive the generation lifecycle
  (calls `generation`); does not write the storage root (calls `storage`); does
  not import `mcp`, `studio`, `operations`, `projects` or `devharness` (the
  last two are already enforced by
  `tests/unit/graph/test_startup_boundaries.py:30`); does not split `nodes/`
  per phase (A §10.2, the D-009 channel-loss class).
- **Public contract.** `graph` (the `langgraph.json` entry), `build_graph`,
  `StudioGraphState`, `ORCH_CHANNELS`, all reducers (`merge_unique`,
  `merge_generation_requests`, `merge_issues`), `GraphServices`/`ServicesScope`,
  `services_scope(...)` (public replacement for `_SERVICES_CTX`), `PHASE_ORDER`
  re-exported from `filmspec` under a shim, `project_generation_requests(...)`,
  `_PHASE_DEFAULT_AGENTS` (validated against `filmspec.PHASE_ORDER`). **Measured
  additions (§3.21, adversarial O-05)** — seven names with a legal importer that the
  declaration omitted: `RouterResult`, `compute_actions`, `get_blockers_for_state`,
  `public_blocked_actions` (`operations`; note `compute_actions` **moves here from
  governance**, which is why `governance` declares `compute_available_actions`
  instead), `orchestrator_state` as a module (`operations`), `SERVICES_KEY`
  (`studio`; superseded by the declared `services_scope(...)`, kept for the shim
  window), `get_candidate_refs` (`studio`). **Removed from the surface:** the
  declaration does *not* add `get_approved_refs` or `get_execution_brief` — their
  only importer is `governance`, and `governance → orchestration` is FES #2, so
  `orchestration` passes the brief down as a value instead.
- **Owns.** N+I+R for graph state shape, channel write policy, phase topology,
  and checkpoint-visible state; I for the channel-merge policy.
- **State.** the LangGraph checkpointed state per thread; the services scope.
- **Allowed outbound.** `filmspec`, `schemas`, `config`, `kb`, `constraints`,
  `storage`, `providers`, `agents`, `budget`, `validation`, `generation`,
  `post`, `governance`.
- **Allowed inbound.** `operations`, `studio`.
- **Evidence.** F-OST-01…16, F-PHASE-01/04/08, F-SVC-01 (4 service locators),
  F-STATE-01/`audit/02` §5, `enola` §3 (`graph` depth 10, 148 fan-in) and §5
  (`orchestrator_state` 38/38 public); C3.

### 3.17 `operations` — L10 (today's `app/services`)

- **Responsibility.** Exposes the studio's operations as typed use cases
  (create/inspect project, run/resume/advance pipeline, plan/approve/poll
  generation, run validation, assemble, checkpoint/rollback, read audit) that
  both the MCP tool handlers and the local CLI driver call.
- **Non-goals.** does not construct the object graph (`studio`); does not know
  JSON tool schemas (`mcp`); does not talk to providers directly (uses
  `generation`/`providers`); does not hold the runtime singleton.
- **Public contract.** `OperatorBackend` with one method per operation; typed
  `BackendOperationError`; `GenerationWorkspace`, `ReviewWorkspace`.
  **Rename reconciliation (§3.21):** at HEAD these are `OperatorService` and
  `ServiceError` (`app/services/operator.py`, `app/services/errors.py`), both
  imported by `mcp`; the target names are the declared ones and the HEAD names are
  the W0–W10 pre-image, so `public_api` must carry both until W12. **Measured
  additions:** `BackendOperationError` must also cover `ProjectNotFoundError`, and
  `OperatorService`'s id-sanitizing helper (today `mcp`'s
  `artifacts.registry.sanitize_artifact_id` reach) is published here as one
  operation (§3.21).
- **Owns.** I for operation-level preconditions (project must exist, phase must
  be at gate); R for the operator-facing read models.
- **State.** none beyond injected handles.
- **Allowed outbound.** every module at L0–L9 (`filmspec`, `schemas`, `config`,
  `kb`, `constraints`, `storage`, `providers`, `projects`, `checkpoints`,
  `agents`, `budget`, `validation`, `generation`, `post`, `governance`,
  `orchestration`).
- **Allowed inbound.** `mcp`, `studio`.
- **Evidence.** F-MCP-04/05/06 (parallel lifecycle, mutations bypass
  confirmation, real-money spend path), F-MCP-12 (bibles instantiate agents and
  version artifacts outside the graph), F-OST-08 (`run_phase_node` re-implements
  and diverges from the reducers), `enola` §4 (`OperatorService._state_for_project`
  21 dependents); A §5.15.

### 3.18 `mcp` — L11

- **Responsibility.** Defines the external tool contract (names, JSON schemas,
  flags, idempotency), the request envelope and project resolution, error
  mapping, the registry, and the stdio transport — and adapts each tool call to
  exactly one `operations` use case.
- **Non-goals.** does not import `orchestration` internals, `storage`,
  `generation`, `checkpoints`, `agents`, `providers`, `kb`, `config`, `post` or
  `studio`; does not hold a runtime singleton; does not re-derive project
  resolution (uses `projects.resolve`); no tool handler contains policy.
- **Public contract.** `ToolContract`, `ToolGroup`, `ToolRegistry`,
  `make_registry`, `register_all_tools`, `RequestEnvelope`, `new_envelope`,
  `resolve_request`, the ~90 tool functions (names and JSON shapes **frozen**,
  B7), and the transport. The `mcp.server:main` *entry point* moves to `studio`
  in W11; `mcp` keeps the server object that receives an injected
  `OperatorBackend`.
- **Owns.** N+I for the external contract; R for MCP response shapes; N for the
  error taxonomy (`MCPErrorCode`).
- **State.** the tool registry (built once).
- **Allowed outbound.** `filmspec`, `schemas`, `projects`, `governance`,
  `validation`, `operations`. **Nothing else.**
- **Allowed inbound.** `studio`.
- **Evidence.** F-MCP-01/02/03/07/08/09/10/11, `01` §17 (contract flags already
  single-owner), `enola` §3 (`mcp/tools` fan-out 104 — the widest consumer);
  C2.

### 3.19 `studio` — L12 (today's `app` minus `services`, plus `cli`)

- **Responsibility.** Builds the object graph (services scope, storage, registries,
  provider adapters, graph handle), owns process/session lifecycle (bootstrap,
  mode, persistence policy and root resolution, logging, health, safety,
  version, smoke), and hosts the entry points (`cli.run:main`,
  `mcp.server:main`, `app.product_gate:main`, the `langgraph.json` target).
- **Non-goals.** no domain rules; no MCP JSON shapes; nothing may import
  `studio`; does not own the project registry (`projects`), checkpoint state
  (`checkpoints`) or audit bytes (`storage`).
- **Public contract.** `StudioRuntime` (services scope + graph handle + logging
  only), `build_runtime`, `bootstrap(role)`, `resolve_persistence()`,
  `resolve_roots()`, `configure_logging`, `product_gate.main`,
  `cli.run.main`, `cli.driver.Driver`, `cli.io`, `default_mock_responses`
  (production mock mode, schema-bound per W4), `__version__`/`project_name`.
  **Relocations (§3.21, FES #3):** three HEAD names are imported from `studio`'s
  pre-image by modules that may not import `studio` — `get_runtime` (deleted, C2),
  `validate_environment` (`mcp`; the bootstrap moves behind `operations`),
  `reset_runtime` (`operations`; moves to `operations`). None of the three enters
  `studio.public_api`; `StudioRuntime` itself becomes an `operations`-owned port so
  `operations` no longer imports it (FES #3).
- **Owns.** I for wiring correctness (exactly one services scope, exactly one
  storage root per process); N for the persistence policy and root layout;
  R for the process lifecycle.
- **State.** process lifecycle state only; the one services scope.
- **Allowed outbound.** every module L0–L11.
- **Allowed inbound.** `mcp`? **No** — `mcp.server:main`'s bootstrap is invoked
  from the process entry point that `studio` owns; nothing imports `studio`.
- **Evidence.** F-MCP-09 (3 mains + `langgraph.json` re-derive bootstrap),
  F-CRP-01 (5 root-resolution paths), F-CRP-09/F-CFG-08 (`NO_PERSIST` at 7
  symbols / 6 files / 4 packages, 2 formulas), F-SVC-01, F-RUNTIME-01,
  `enola` §4 (`StudioRuntime` 103/95/78 dependents — the largest concentration
  of authority); C2.

### 3.20 `devharness` — off-graph (today's `testing`)

- **Responsibility.** Provides the mock human actor, mock model adapter,
  in-memory git backend, storage factories and scenario scripts that tests and
  explicit mock-mode runs use.
- **Non-goals.** must not be importable from any production module (already
  enforced for `graph` by `tests/unit/graph/test_startup_boundaries.py:30`);
  does not own the real contracts it doubles; does not import `_private`
  modules of any package; **not shipped in the wheel** (D6).
- **Public contract.** `MockHumanActor`, `DecisionProfile`, `MockModelAdapter`,
  `ALL_SCENARIOS`, `make_store`, `InMemoryGit`, and one
  `GraphServices`/`OperatorBackend` fake factory (F-TEST-08).
- **Owns.** nothing normative; it is a test-double library with a declared
  contract.
- **State.** in-memory doubles.
- **Allowed outbound.** `filmspec`, `schemas`, `storage`, `providers`,
  `checkpoints`, `agents`. (L0–L5; nothing above L5, and never `studio`.)
- **Allowed inbound.** none in production; `tests/**` only.
- **Evidence.** F-TEST-01…08, F-BOUNDARY-06 (ships in the wheel, excluded from
  coverage, imports 3 domains), `enola` §4 (`app/mock_responses` 22 dependents
  proves test doubles are load-bearing); D6.

---

### 3.21 Declared `public_api` vs the measured cross-module import surface (adversarial O-05)

**Method.** AST sweep over all 281 files at `fb85baa`: for every `ImportFrom`/
`Import` whose target resolves to a *different* §6 target module, record the
imported names, excluding private submodules (leading `_`) and private symbols. Then
keep only names whose importer is a **legal** target importer under §4.3 — a name
imported *only* by `mcp` from a module `mcp` may not import is not a target
cross-module import at all. Reproduction: appendix.

The result: **126** public names cross a target-module boundary at HEAD across the 15
modules other than `schemas` (`schemas`' **97** are covered by that module's
whole-package declaration, so 223 `(module, name)` pairs in total); `filmspec`,
`projects` and `budget` have **zero** importers at HEAD because they do not exist
yet, so their `public_api` is enforced from W0 forward once callers exist. Of the
126, **53** were missing from the declared contract and are added below; the
remainder are already declared, reachable only through `operations`, or deleted /
renamed and recorded as such.

| Module | Measured importers' names | Disposition |
|---|---|---|
| `agents` | `BaseAgent`, `MVP_AGENTS`, `ModelAdapter`, `ModelRouter`, `PromptRunner`, `get_registry`, `AgentRegistry`, `get_agent_class`, 5 `*BibleAgent` | `AgentRegistry` → **renamed** `AgentCatalog` (HEAD name kept as pre-image); `get_agent_class` → **deleted** (3-registry collapse, replaced by `AgentCatalog.implementation_for`); 5 `*BibleAgent` → **via `operations`** (mcp-only); rest already declared. **0 additions.** |
| `checkpoints` | `CheckpointManager`, `GitBackend`, `InvalidationEngine`, `RollbackManager` | First two declared; last two fold into `CheckpointManager` and are **via `operations`**. **0 additions.** |
| `config` | `ProfileLoader`, `profile_resolver` (module), `canonicalize_profile_stack`, `load_profile_flex`, `missing_provider_credentials`, `provider_specs_from_raw`, `register_project_providers`, `resolve_project_config` | **2 additions**: `ProfileLoader` (`studio`), `profile_resolver` (`operations`). The other five are mcp-only → **via `operations`**; `register_project_providers` additionally leaves `config` (FES #1). |
| `constraints` | `extract_constraints`, `render_constraints` | Both declared. **0 additions.** |
| `generation` | `GenerationExecutor`, `GenerationLedgerManager`, `build_structured_prompt`, 5 compositor builders, 4 frame/sheet reviewers, `run_heuristic_checks`, `write_frame_sidecar` | **1 addition**: `build_structured_prompt` (`orchestration`). The other ten are mcp-only → **via `operations`**. |
| `governance` | `ReviewPackageGenerator`, `check_phase_consistency`, `derive_scope_contract`, `pacing_from_config`, `load_execution_brief`, 8 `validate_*` | **12 additions** — the entire moved `consistency`/`scope_contract`/`orchestrator_validators` surface plus `ReviewPackageGenerator`. This was the largest omission; without it the `graph` split is unenforceable. |
| `kb` | `DEFAULT_MAX_CONTEXT_CHARS`, `compact_json_context`, `KBContextPacketBuilder`, `KBManifest`, `kb_manifest_path`, `KBRetrieval` | **5 additions** (first five); `KBRetrieval` is mcp-only → **via `operations`**. |
| `mcp` | `make_registry` | Declared. **0 additions.** |
| `operations` | `OperatorService`, `ServiceError` | **Rename reconciliation**: `OperatorBackend` / `BackendOperationError` are the target names; both HEAD names stay in `public_api` until W12. **0 additions.** |
| `orchestration` | `GraphServices`, `PHASE_ORDER`, `RouterResult`, `SERVICES_KEY`, `build_graph`, `compute_actions`, `get_blockers_for_state`, `get_candidate_refs`, `merge_*` (3), `orchestrator_state` (module), `public_blocked_actions`, `get_approved_refs`, `get_execution_brief` | **7 additions**: `RouterResult`, `compute_actions`, `get_blockers_for_state`, `public_blocked_actions`, `orchestrator_state`, `get_candidate_refs`, `SERVICES_KEY` (shim). `get_approved_refs`/`get_execution_brief` **removed**: their only importer is `governance` and FES #2 forbids that edge, so the brief is passed down as a value. |
| `post` | `AssemblyAgent`, `DeliveryPackagingAgent` | Both declared; both reached **via `operations`** (mcp-only). **0 additions.** |
| `providers` | `BaseProviderAdapter`, `ProviderJob`, `ProviderJobStatus`, `credentials` (module), `lookup`, `env_or_dotenv`, `redact`, `compress_prompt_for_retry`, `is_token_limit_exceeded`, `pricing_prompt_block`, `OPENROUTER_API`, `ScenarioStep`, `build_provider_adapter`, `estimate_cost_for_duration`, `PROVIDER_PRICING`, `tier_for`, `is_configured` | **8 additions**: `ProviderJob`, `ProviderJobStatus`, `credentials`, `compress_prompt_for_retry`, `is_token_limit_exceeded`, `pricing_prompt_block`, `OPENROUTER_API`, `ScenarioStep`. `PROVIDER_PRICING`, `tier_for`, `is_configured` → **via `operations`** / `required_credentials`. |
| `schemas` | 97 names across 27 submodules | **0 additions** — the declaration names the 40 whole modules rather than a list, so it is a superset by construction. Confirmed, not merely asserted. |
| `storage` | `ArtifactStore`, `ProjectStorage`, `AssetEntry`, `AssetManifest`, `read_manifest`, `write_manifest`, `PROFILE_PRODUCTION`, `PROFILE_SANDBOX`, `default_checkpoints_root`, `default_runtime_root`, `default_run_root`, `ensure_storage_root`, `graph_state_location`, `init_storage_root`, `resolve_storage_root`, `set_git_backend_type`, `sanitize_artifact_id` | **10 additions**: `AssetEntry`, `AssetManifest`, `read_manifest`, `write_manifest`, `default_checkpoints_root`, `default_runtime_root`, `default_run_root`, `graph_state_location`, `init_storage_root`, `set_git_backend_type`. `sanitize_artifact_id` → **`storage.contract`**, reached via `operations` (see below). |
| `studio` | `StudioRuntime`, `configure_logging`, `get_runtime`, `reset_runtime`, `validate_environment` | **0 additions.** `get_runtime` is **deleted** (C2); `validate_environment` and `reset_runtime` **relocate behind/to `operations`**; `StudioRuntime` becomes an `operations`-owned port (FES #3). Every importer of these is illegal in the target, which is exactly why none may be a `public_api` name. |
| `validation` | `ConsensusBuilder`, `MVP_VALIDATORS`, `AssemblyValidator`, `DeliveryCompletenessValidator`, `DialogueVoiceValidator`, `PromptReadinessValidator`, `ReferenceUsabilityValidator`, `SceneContinuityValidator`, `ScriptStructureValidator` | **8 additions**: the seven concrete validators plus `MVP_VALIDATORS` (the target's `PHASE_VALIDATORS`). All have legal importers (`orchestration`, `post`, and `mcp` — `mcp → validation` is one of its six legal edges). |
| `filmspec`, `projects`, `budget` | *(none)* | **0 measured names** — all three are new or extracted modules with no HEAD importers. Their declared surfaces are enforced from W0 by `test_cross_package_imports_use_the_declared_public_api` as soon as a caller appears. |

**The `sanitize_artifact_id` refutation, stated so it can be checked.** The adversary
listed it among four `storage` omissions. It is not one: at `fb85baa` its **only**
importer is `mcp/tools/_profile_change.py:20`, and `mcp`'s `may_import` set in §4.3
excludes `storage`, so under the FES it is not a target cross-module import. Putting
it in `storage.public_api` would declare a surface that no legal target module may
call — the opposite of what B2 needs. It therefore lives in `storage.contract`
(where ref formatting belongs, §3.6.1) and `operations` publishes the one operation
that uses it. The other three names the adversary named —
`default_checkpoints_root`, `default_runtime_root`, `graph_state_location` — **are**
real omissions and are added above.

**What this means for the guard (05's job, stated so the law is unambiguous).** The
matrix §4.3 already fixes the allowed edges; `public_api` adds a second, finer gate:
an import that is *edge-legal* but names something not in the target's declared
surface is still an L3 violation. `05` owns
`test_cross_package_imports_use_the_declared_public_api`; this section is the
authoritative list of what it must find declared, including the W0 pre-image rows
(`AgentRegistry`, `OperatorService`, `ServiceError`, `SERVICES_KEY`) that exist only
until W12.

---

## 4. The dependency law

### 4.1 The law (normative, numbered)

> **Film Pipeline Modularity Law (v2).** Supersedes `AGENTS.md:51`.
>
> **L1 — Direction.** Every module declares a layer (§4.2). A module may import
> only modules in **strictly lower** layers. Same-layer imports are forbidden.
> Imports within one module's own subpackages are unconstrained.
>
> **L2 — Acyclicity.** The module import graph is acyclic, including
> function-body imports, `__init__` re-exports and `TYPE_CHECKING` blocks. No
> SCC may contain two modules.
>
> **L3 — Public surfaces only.** No module may import a private name
> (`from other import _x`), a private submodule (`other._pkg`), or assign to
> another module's module-level state. If a consumer needs a private thing, the
> owner publishes it or the design is wrong.
>
> **L4 — Persistence exclusivity.** Only `storage` reads or writes the storage
> root or builds project paths. (Existing law, generalized.)
>
> **L5 — Model and invariant exclusivity.** A concern's normative model is
> declared in exactly one module and its invariant enforced in exactly one
> place. Consumers import the model; they never re-declare a literal, a phase
> list, a gate name, a severity string or a kind list, and never re-implement
> the owner's predicate.
>
> **L6 — Composition-root singularity.** Only `studio` constructs the object
> graph. No module holds a mutable module-level singleton of a domain object;
> no module reads another's context variable or global.
>
> **L7 — Harness isolation.** Production modules (L0–L12) never import
> `devharness`.
>
> **L8 — Ledger monotonicity.** No module is **coarsely** exempt: every module's
> outbound set is finite and declared, and **every** module — `studio` and `mcp`
> included — is an ordinary member of the FES (§4.6.1) whose edges are counted.
> "Unrestricted" is not a property any target module has; `studio` being a
> composition root means its set is the *enumerated 18* of §4.3, not that it is
> unbounded. Deviations are recorded as `Exemption` rows in
> `architecture.py` with a reason, a citation and the wave that removes them;
> the row set may never grow after W0 and must be empty by W12.

**Deleted:** *"domain modules must not import each other directly — they
communicate through `artifacts`."* It is false at HEAD (11 violating statements
under the audit's own targeted greps; the count is not definable until the scope
is fixed — see §4.6.1 and V3), it forbids legitimate and necessary edges
(`generation → storage`, `validation → storage`, `agents → providers`), and its
literal enforcement would force typed data through the filesystem, breaking the
single-writer guarantee the storage guards exist to protect. Its replacement:
*modules communicate through declared public contracts; artifacts are the
durable medium for concerns that must survive a process, and only `storage`
writes them.*

### 4.2 Layers

| Layer | Modules |
|---|---|
| **L0** | `filmspec` |
| **L1** | `schemas` |
| **L2** | `config`, `kb`, `constraints` |
| **L3** | `storage`, `providers` |
| **L4** | `projects`, `checkpoints` |
| **L5** | `agents`, `budget` |
| **L6** | `validation`, `generation` |
| **L7** | `post` |
| **L8** | `governance` |
| **L9** | `orchestration` |
| **L10** | `operations` |
| **L11** | `mcp` |
| **L12** | `studio` |
| **off-graph** | `devharness` (imported by `tests/**` only) |

`src/film_pipeline/architecture.py` is **not** a module in this table: it is the
law's declaration root, is importable by every module (`ALWAYS_IMPORTABLE`), and
itself imports nothing from `film_pipeline` (guarded by
`test_architecture_manifest_is_a_leaf`).

### 4.3 Allowed-edge matrix

**Single declaration home.** The matrix below has exactly **one** machine-readable
home: `ModuleContract.may_import` in each package `__init__.py`, with the
cross-module rows in the leaf `src/film_pipeline/architecture.py` (§2.6). **No
second matrix file may exist — no `scripts/architecture/edges.yaml`, no
`layers.yaml`, no JSON/YAML edge list** — because a second home is the same
distributed-ownership failure this law exists to prevent (a typo'd YAML entry
silently declares nothing, and the two homes drift with no test able to fail).
`04-extraction-roadmap.md`'s proposed `scripts/architecture/edges.yaml` (its P0)
must defer to this: the guard reads the manifest, and the matrix below is the
human-readable projection of it.

Rows are source modules; columns are targets in layer order. `•` = allowed;
blank = forbidden (including same-layer and self, except a module's own
submodules, which are unconstrained by L1).

| from \ to | fs | sc | cf | kb | cn | st | pv | pj | cp | ag | bd | va | ge | po | gv | or | op | mc | su |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **filmspec** L0 | · | | | | | | | | | | | | | | | | | | |
| **schemas** L1 | • | · | | | | | | | | | | | | | | | | | |
| **config** L2 | • | • | · | | | | | | | | | | | | | | | | |
| **kb** L2 | • | • | | · | | | | | | | | | | | | | | | |
| **constraints** L2 | • | • | | | · | | | | | | | | | | | | | | |
| **storage** L3 | • | • | | | | · | | | | | | | | | | | | | |
| **providers** L3 | • | • | | | | | · | | | | | | | | | | | | |
| **projects** L4 | • | • | | | | • | | · | | | | | | | | | | | |
| **checkpoints** L4 | • | • | | | | • | | | · | | | | | | | | | | |
| **agents** L5 | • | • | | | | | • | | | · | | | | | | | | | |
| **budget** L5 | • | • | | | | • | | | | | · | | | | | | | | |
| **validation** L6 | • | • | | | | • | | | | | | · | | | | | | | |
| **generation** L6 | • | • | | | | • | • | | | | • | | · | | | | | | |
| **post** L7 | • | • | | | | • | | | | | | • | | · | | | | | |
| **governance** L8 | • | • | | | | • | | | | | • | • | | | · | | | | |
| **orchestration** L9 | • | • | • | • | • | • | • | | | • | • | • | • | • | • | · | | | |
| **operations** L10 | • | • | • | • | • | • | • | • | • | • | • | • | • | • | • | • | · | | |
| **mcp** L11 | • | • | | | | | | • | | | | • | | | • | | • | · | |
| **studio** L12 | • | • | • | • | • | • | • | • | • | • | • | • | • | • | • | • | • | • | · |
| **devharness** off | • | • | | | | • | • | | • | • | | | | | | | | | |

Reading aids: `filmspec` is the only source row with no allowed target.
`orchestration` is the highest non-composition module with a broad downward set;
it still may **not** import `projects`, `checkpoints`, `mcp`, `operations` or
`studio`. `mcp` may import only six modules. `devharness` (last row) is
off-graph: nothing in L0–L12 may import it (L7), so its row is a capability list,
not a licence.

### 4.4 Why this graph is acyclic, and how C1–C5 break

**Acyclic by construction:** every allowed edge in §4.3 points to a strictly
lower layer (the matrix is lower-triangular once rows are ordered by layer), and
`devharness` sits outside the production graph. A directed cycle requires an
edge that does not decrease the layer index; none exists. Same-layer imports are
forbidden precisely so that `post → validation` (L7→L6), `generation → budget`
(L6→L5) and `validation → storage` (L6→L3) stay downward.

| Cycle (enola) | Members at HEAD | Why it exists at HEAD | Edge that disappears | Where |
|---|---|---|---|---|
| **C1** | `agents/prompt_templates` ↔ `agents/prompt_templates/defaults` | `registry.py` lazily imports `defaults` to load the built-in templates, and `defaults/*` import `registry` for the `PromptTemplate` type | `agents/prompt_templates/registry.py:100 → agents/prompt_templates.defaults` (deleted; loading moves to `agents.catalog.bootstrap_defaults()`, called by `studio`). Both members become the single module `agents`, so the enola edge `prompt_templates → prompt_templates.defaults` also disappears. | W2 |
| **C2** | `app` ↔ `mcp` + 5 sub-modules (7 members) | `app/product_gate.py:17` imports `mcp.contract.make_registry` while `mcp/server.py:164,241,248,249` and `mcp/tools/__init__.py:22` import `app.runtime`, `app.bootstrap`, `app._persistence`, `app.logging_setup` | `mcp/tools/__init__.py:22 → app.runtime.get_runtime` (and the three `mcp/server.py` app imports). `mcp` receives an injected `operations` backend; the bootstrap moves to `studio`, which is **above** `mcp`; `app → mcp` becomes the legal `studio → mcp`. | W1 (early move of `product_gate`), W11 (close) |
| **C3** | `graph` ↔ `graph/nodes` ↔ `graph/orchestrator_validators` ↔ `graph/subgraphs` | node modules import gate/validator helpers (`_repair_loop.py:199 → approval`, `approval` re-imports `_repair_loop`) and `orchestrator_validators/brief.py:179` imports `graph.nodes` back | `graph/orchestrator_validators/brief.py:179 → graph.nodes` (deleted). `orchestration → governance` remains (L9→L8); `governance` becomes a pure function over values and may not import `orchestration`. The `nodes/↔subgraphs/` half becomes intra-module. | W9 |
| **C4** | `providers` ↔ `providers/adapters` | `providers/__init__.py:9` re-exports `Imagen4GeminiProvider`, while `adapters/imagen4_gemini.py:13`, `seedance_openrouter.py:19`, `veo_fast.py:13` import `providers.base` (and `credentials`, `pricing`) | `providers/__init__.py:9 → providers.adapters.imagen4_gemini` (deleted; `studio` imports concrete adapters and injects them). Both members become the module `providers`. | W2/W11 |
| **C5** | `schemas` ↔ `schemas/registries` | `schemas/__init__.py:120` re-exports the four registry entry records, while `registries/*.py` import `schemas._base` (`agent_registry.py:7`) | `schemas/__init__.py:120 → schemas.registries` (deleted; consumers import `film_pipeline.schemas.registries` directly) **and** `registries/*.py:7 → schemas._base` becomes an import of the L0 `filmspec` enums plus `schemas.base`. Both members become the module `schemas`. | W2/W5 |

#### C4 source evidence correction (2026-09-25)

The C4 row above understates the provider-to-adapter side of the measured
cycle. The pinned source also has three direct adapter imports in
`src/film_pipeline/providers/factory.py:5-7`; removing only the listed
`providers/__init__.py` re-export would leave those edges and would not clear
C4. The approved migration direction in
[`06-independent-review-and-decision.md`](06-independent-review-and-decision.md)
governs execution: C-02 moves adapter construction to the existing app
composition layer, removes the root concrete Imagen alias, and keeps
`providers.adapters` as the concrete-adapter export surface. The old
`film_pipeline.providers.factory` and
`film_pipeline.providers.Imagen4GeminiProvider` import paths are therefore
removed as part of the migration; the builder behavior remains covered by the
current progress ledger. This correction records the complete measured edge;
it does not revive the superseded 20-module proposal.

#### C4 implementation status correction (2026-09-25)

C-02 is implemented. The builder now lives in
`src/film_pipeline/app/_provider_factory.py`; the profile and default-seed
composition paths import it from `app`, and `providers/__init__.py` no longer
imports a concrete adapter. `providers.adapters` remains the adapter export
surface, while the removed `providers.factory` and root Imagen paths have no
in-repository callers. This is the selected existing-app composition route
recorded in the implementation ledger, rather than the provisional `studio`
wording in the target row above. The factory builder body and signature are
preserved, with the behavior characterized by the C-02 test matrix.

The committed-tree Enola check at 21:08 UTC was clean and reduced the current
cycle count from four to three; no cycle was added. The pinned baseline remains
unchanged. See `implementation-progress.md` for review and validation evidence.

#### C5 implementation status correction (2026-09-25)

C-03 is implemented. The root `schemas` package no longer imports or
re-exports the ten agent, model, provider, and validator registry schemas;
`schemas.registries` remains their canonical export surface. The registry
modules continue to import `schemas._base`, leaving a one-way dependency from
the nested registry package into its owning schema package. The target row's
additional move away from `_base` was unnecessary to remove the measured
cycle and was not included. The `PromptRegistry` and `PromptRegistryEntry`
exports remain at the root. No in-repository consumer used the removed root
aliases.

The committed-tree Enola check at 21:26 UTC was clean and reduced the current
cycle count from three to two; no cycle was added. One dependency-depth
advisory also resolved. See `implementation-progress.md` for review and
validation evidence.

C1, C4, C5 are cheap: each member pair maps to one target module, so the enola
cycle vanishes as soon as the module catalog is applied; the concrete source
edge is additionally deleted to keep the file-level import graph clean.

### 4.5 Mechanical checkability (B3)

The law is checked by `tests/architecture/` (D2, §2.6), not by review:

| Law | Guard |
|---|---|
| L1 direction | **Required: `test_declared_edges_go_strictly_down_one_layer`** — iterate `ModuleContract.may_import` against the §4.2 layer table and assert every target is strictly lower. This guard is **named here because it did not exist** in `05`'s printed suite (adversarial O-04): acyclicity alone permits a same-layer or upward `may_import` (e.g. `post → governance`, L7→L8) that forms no cycle, so §4.1's "acyclic by construction" was sound but its *machine check* was missing. `05` owns the mechanism; the law requires this assertion. |
| L2 acyclicity | `test_imports_stay_within_declared_edges`, `test_declared_edges_are_real`, `test_declared_module_graph_is_acyclic` (Kahn over `ModuleContract.may_import`, minus `CYCLE_EXEMPTIONS`) |
| L3 public surfaces | `test_no_cross_package_private_imports` (AST sweep; W0 ledger: **107** private-module sites = **106** `schemas._base` across **72** files + **1** `app._persistence`, plus **3** private-symbol sites: `app/_graph_exec.py:319,449` and `config/profile_resolver.py:204` — V4) |
| L4 persistence | existing `tests/unit/artifacts/test_storage_boundary.py`, extended to the L0–L1 lattice **and to the media-write surface** (§2.7.3 M16) |
| L5 model/invariant exclusivity | `test_vocabularies.py` (`VocabularyMirror` agreement), per-module duplicate-literal sweeps (§3 guards); the phase sweep must be **any-position** (V/M2), the agent-profile authority is a **single field, not a map** (V2), and the threshold band guard tests `block_below < review_at` over the **22** literals (V1) |
| L6 composition root | `test_no_module_level_domain_singleton`, `test_architecture_manifest_is_a_leaf` |
| L7 harness isolation | `test_devharness_not_imported_by_production` (generalizes `tests/unit/graph/test_startup_boundaries.py:30`) |
| L8 ledger | `test_exemptions.py` (citation resolves, subject is live, families non-empty, source tree >200 files, mutation canary) |

The three debt classes that stay human-anchored are O2 (duplicated enforcement)
and O6 (parallel lifecycle) — declared pairs plus a differential lock, with the
entry-point enumeration done by hand (B §6.9) — and the O4 non-member judgement
(B §6.9). That is stated, not hidden.

### 4.6 The forbidden-edge scope (normative): the FES

This section is **the** definition of what "forbidden edge" means for this program.
`04-extraction-roadmap.md` and `05-enforcement-and-guard-tests.md` must **cite
§4.6.1 verbatim** and may not restate, narrow or recompute the scope; `05` owns the
*mechanism* that enumerates edges, this section owns the *law* that decides which of
them are forbidden. Four numbers were previously in circulation for one tree: the
audit's **eight** (a union of three targeted greps, not an enumeration), **53**
cross-package edges (a package count, ambiguous because `graph` and `app` split),
`05`'s **4** (a scope that excludes every `mcp → *` edge and counts edges §4.3
declares allowed), and this file's former **10**. They are replaced by one number
below.

The ambiguity `reviews/orchestrator-verification-notes.md` V3 identified is that the
`AGENTS.md:51` law never defined "domain module". It is resolved by not using the
phrase at all. A module is a member of the graph, its outbound set is exactly its
`ModuleContract.may_import`, and an edge is forbidden iff it is not in that set:

| Scope class | Modules | Treatment under the FES |
|---|---|---|
| **Contract layers** | `filmspec` (L0), `schemas` (L1) | May be imported by every module; never a forbidden target. The bottom of the lattice, not an exemption. |
| **Persistence medium** | `storage` (L3) | Allowed **only** where §4.3 says so. `AGENTS.md`'s blanket "communicate through `artifacts`" is **deleted**; importing `storage` is an ordinary declared edge. |
| **Composition root** | `studio` (L12); HEAD pre-images `app` + `cli` | **Inside the FES, as an ordinary member**: its outbound set is the enumerated 18 of §4.3 and its inbound set is empty (L6). It is not "outside the count"; it simply has no forbidden edges of its own. This is the O-07 correction — the target law has no *coarsely* exempt module. |
| **Use-case layer** | `operations` (L10) | Inside the FES; outbound is the enumerated L0–L9 set of §4.3. |
| **Harness** | `devharness` (off-graph; HEAD `testing`) | Inside the FES; a production module importing it violates L7. |
| **Everything else** | the other 16 modules, `mcp` included | Governed entirely by §4.3. There is no special "domain isolation" rule, and `mcp` is not a privileged consumer. |

#### 4.6.1 FES — the sentence a guard keys on

> **Forbidden-edge scope (FES).** Over the tree at `fb85baa`, assign every one of the
> 281 source files to its §6 target module, take every distinct
> `(source target module → destination target module)` import pair, and count it
> **forbidden** iff the destination target module is absent from the source target
> module's `ModuleContract.may_import`; `mcp` is an ordinary L11 module with the
> six-module `may_import` set of §4.3, so **all `mcp → *` edges are inside this
> scope**; the derived count is **13**.

Applying that sentence to the tree gives the complete forbidden set — **13 distinct
edges**, not 10 and not 4:

| # | Edge | HEAD sites | Why forbidden | Removed by |
|---|---|---|---|---|
| 1 | `config → providers` | **2** — `config/profile_resolver.py:179` (`build_provider_adapter`, inside `register_project_providers`, live on 3 call paths) and `:204` (the credential check) | `config`'s outbound is `filmspec`, `schemas` only | W1: `:204` moves to `providers.required_credentials` called by `studio`; `:179`'s `register_project_providers` moves to `operations` (O-12) |
| 2 | `governance → orchestration` | **5** — `graph/_action_routing.py:15`, `graph/consistency.py:65`, `graph/orchestrator_validators/brief.py:21`, `:38`, `:179` | `governance` (L8) may not import `orchestration` (L9); governance must be a pure function over values | W9: `:179` is C3's deleted edge; the other four become typed values passed down by `orchestration` |
| 3 | `operations → studio` | **4** — `app/services/_browse_ops.py:8` and `_generation_ops.py:11` (`app._persistence.artifact_root`), `_project_discovery.py:8` (`storage_for`), `operator.py:15` (`StudioRuntime`, `get_runtime`, `reset_runtime`) | `operations` (L10) may not import `studio` (L12); L6 makes `studio` inbound-empty | W1/W10: `artifact_root`/`storage_for` re-home into `operations`; `StudioRuntime` becomes an `operations`-owned port; `get_runtime` is deleted (C2); `reset_runtime` is deleted |
| 4 | `mcp → agents` | **7** — `mcp/tools/bibles/*` | `mcp`'s outbound is `filmspec`, `schemas`, `projects`, `governance`, `validation`, `operations` | W11: collapses to the single legal `mcp → operations` |
| 5 | `mcp → checkpoints` | **3** — `mcp/tools/checkpoints.py:13,14`, `mcp/tools/_profile_change.py:458` | as above | W11 |
| 6 | `mcp → config` | **6** — `mcp/tools/config.py:12,28`, `mcp/tools/_profile_change.py:21`, `mcp/tools/helpers.py:14`, … | as above | W11 |
| 7 | `mcp → generation` | **23** — `mcp/tools/generation/*`, `_text_only.py:78,104` | as above | W11 |
| 8 | `mcp → kb` | **5** — `mcp/tools/kb.py:10,20,21,33` | as above | W11 |
| 9 | `mcp → orchestration` | **7** — `mcp/tools/projects.py:278`, `review.py:94,95`, `state.py:33`, … | as above | W11 |
| 10 | `mcp → post` | **2** — `mcp/tools/assembly.py:37,59` | as above | W11 |
| 11 | `mcp → providers` | **6** — `mcp/tools/generation/dispatch.py:16,184,212,284`, … | as above | W11 |
| 12 | `mcp → storage` | **7** — `mcp/tools/artifacts.py:8`, `checkpoints.py:12`, `_profile_change.py:20`, … | as above | W11 |
| 13 | `mcp → studio` | **5** — `mcp/server.py:164,241,248,249` | as above; `studio` is inbound-empty (L6) | W11: `mcp.server:main` moves to `studio`, the bootstrap is injected |

Edges #1–#3 are the three the *package-granularity* count could not see: `config`
and `providers` are different packages, but `governance`/`orchestration` are both
HEAD `graph` and `operations`/`studio` are both HEAD `app`, so a package-level sweep
reports them as intra-package. That is exactly why the scope is defined at
target-module granularity (O-02): a guard that counts packages cannot enforce a law
that splits them. Edge #13 (`mcp → studio`) is a `mcp → app` package edge that the
former enumeration omitted.

Two edges often mistaken for members are **outside** the count: `app → mcp` is a
*cycle* edge (C2) that becomes the legal `studio → mcp`, and `testing → *` is legal
for a dev-only module. Equally, `agents → providers`, `generation → providers`,
`generation → storage` and `post → validation` are **allowed** by §4.3 (R-10, D6) —
the audit's "eight" over-counted those and under-counted the `mcp` family.

#### 4.6.2 How this reconciles with `04` and `05`

The FES fixes one authority and two derived facts:

- **The count is derived, and it is 13 — not hardcoded.** The guard enumerates the edge
  set from the AST + the manifest and compares it to the sets implied by
  `may_import`, so the *number* is never written into a test. `05`'s
  `assert len(edges) == 53` and its `UNRESTRICTED_PACKAGES`/`ARTIFACTS_FACADE_IS_CONTRACT`
  scope are **superseded**: they produce 4 where the FES produces 13, because that
  scope excludes `mcp → *` (which the FES places inside) and because it evaluates at
  package granularity.
- **W0 is green because the 13 are declared exemptions, not because they are out of
  scope.** `architecture.py` ships one `Exemption(subject=edge, reason=…, citation=…)`
  row per edge above, each naming its removal wave from the last column. The W0
  assertion is therefore *equality with this table*, and the ratchet (L8) is that the
  unexempted forbidden set may only shrink: W1 removes #1 and part of #3, W9 removes
  #2, W11 removes #4–#13. By W12 the table is empty. `04`'s P0 acceptance text
  ("derived forbidden count = **10**") is a stale consequence of the old scope and is
  corrected to the FES count; that correction belongs in `04`, not here.

This count is a **result**, never a source: the guard recomputes it from the manifest
and the AST, and the only hand-maintained object is the exemption table whose
liveness the guard checks (B3, D2, D12).

---

## 5. State ownership table

One owner per logical state; every other module is a read-only consumer. "R" is
the representation authority (`00` §1.2) when it differs from the N/I owner.

| Logical state | Owner module (N/I/R) | Representation | Read-only consumers | Guard that keeps it single-writer |
|---|---|---|---|---|
| **Orchestrator state** (LangGraph channels, `_orchestrator__*`, `issues`, `current_phase`, `approved`, `human_approval_*`, routing inputs) | `orchestration` (N+I+R) | `StudioGraphState` TypedDict + reducers; runtime-only `_services` channel stays declared and is stripped before persistence | `governance` (values only), `operations`, `mcp` (DTOs), `agents` (task context) | `tests/unit/graph/test_channel_registry.py` (constant↔schema↔channels triangle) + `STATE_CHANNELS['current_phase']` writer sweep (8 recorded → 1; F-OST-01/02/03, F-PHASE-03/04) |
| **Budget / spend** | `budget` (N+I+R) | `BudgetState` + `SpendRecord` document persisted through `storage` | `generation` (authorize before dispatch), `governance` (verdict input), `orchestration` (channel projection), `operations`/`mcp` (read models) | one `cap_for`; `authorize_spend` is the only refusal path (8 sites → 1); `spent_usd == Σ SpendRecord.amount_usd` (F-BUD-01/02/03/04, F-CFG-06) |
| **Provider health** | `providers` (N+I+R) | `providers.health` record (payload `schemas/provider_health`) | `orchestration` projects a snapshot into the `provider_health` channel at invoke time and routing reads that snapshot; `operations`/`mcp` read it | one writer; the dormant `graph/orchestrator_state.update_provider_health` is deleted or wired (F-PROV-01, F-OST-13) |
| **Checkpoint metadata** | `checkpoints` (N+I; R via `storage`) | `CheckpointMetadata` in one registry; `checkpoints/checkpoints.jsonl` bytes written by `storage` | `operations`, `studio`, `devharness` — **not** `orchestration` or `projects` (adversarial O-06: both edges are forbidden by §4.3, and `projects → checkpoints` would be same-layer L4→L4, so L1 bars it too) | one registry (F-CRP-02); `artifact_versions` always derived (F-CRP-04); roots resolved once (F-CRP-01). **Two checkpoint mechanisms exist and only one is this module's:** the `checkpoints` module owns the JSONL lifecycle/metadata registry; the **LangGraph SQLite saver** (`graph/graph.py:41-51`, `checkpoints.sqlite`) is `orchestration`'s own concern and is *not* part of this module's contract. `orchestration` obtains `default_checkpoints_root` from `storage` (declared in §3.6); there is deliberately no `orchestration → checkpoints` edge. §8 carries this as a compatibility row. |
| **Artifact status** | `storage` (N+I+R), enforced through `storage.contract.ArtifactStatusPolicy` | `ArtifactStatus` on the envelope + current-meta; `approve`/`supersede` side effects | `operations`, `mcp`, `post`, `generation`, `governance` (read status only) | one transition table; `save_mutable` cannot express APPROVED; `REJECTED`/`ARCHIVED` reachable (F-ARTIFACT-06, F-VR-10) |
| **Generation ledger** | `generation` (N+I+R) | `generation_ledger` mutable artifact (revision-counted) via `storage` | `orchestration` (projects rows into `generation_requests` — the projection moves **up** here, F-GEN-01), `operations`, `mcp` | one ledger state machine (2 writers → 1, F-GEN-04/F-ARTIFACT-07); spend ceiling derived only here (F-GEN-01) |
| **KB provenance (`kb_context_ref`)** | `kb` (N+I; R of the ref's bytes via `storage`) | `KBContextRef` stamped into artifact meta by the single write helper that owns the artifact | `orchestration`, `generation` (pass the ref through), `operations`/`mcp` (read) | every `storage` artifact-write path passes a ref (1 of 12 today → 12 of 12); one `kbctx:` minter (F-KBCTX-02/03/04/05) |

Two states worth naming although the task did not list them: **project identity /
active pointer** → `projects` (F-RUNTIME-01, F-MCP-07), and **persistence policy
+ roots** → `studio` (F-CRP-01, F-CRP-09), with `storage` owning the marker gate
and the bytes.

**Three states verify-10 added that the task's list did not name** (M41–M43,
Critical/High; §2.7.3). They are separate states because each has a different
correct owner, and the current *absence* of an owner is the defect:

| Logical state | Owner module (N/I/R) | Representation | Read-only consumers | Guard that keeps it single-writer |
|---|---|---|---|---|
| **Import-time filesystem effects** (the module-level `graph = build_graph()` at `graph/graph.py:201` that creates `<storage root>/checkpoints/` on `import` **when `FILM_PIPELINE_PERSIST_STATE` is set and `FILM_PIPELINE_NO_PERSIST` is not** — the condition `graph/graph.py:43` tests before returning `SqliteSaver` instead of `MemorySaver`, stated correctly in `05` and added here per adversarial O-21) | `studio` (I): only the composition root may build the object graph, and only at process start | none — importing a production module must be side-effect-free | every module (none may trigger a root write at import) | importing any production module performs **no** filesystem write; the compiled graph is built by `studio` after roots resolve. Today the app then refuses its own root with `StorageRootError` — **Critical 5×5=25**, the highest-severity missed seam in the program (verify-10 M1) |
| **The resolved root layout** (which root is *in use*: storage / runtime / checkpoint / run) | `studio` (N+I+R) via `resolve_roots() -> RootLayout`; `storage` keeps `resolve_storage_root()` and its existing guard tests (verify-10 §4 confirms that one is already single-owned, guarded by `test_storage_guards.py`) | the `RootLayout` value resolved once per process | `storage`, `checkpoints`, `safety`, `operations`, `mcp` | one layout per process; setting `FILM_PIPELINE_RUNTIME_ROOT` must **not** bypass the `use_persistent_runtime()` gate — today a non-persistent runtime still writes durable `project.json` + `storage.json` (verify-10 M2, High 4×4=16); F-CRP-01/-09 |
| **Safety/archival actions** (deletion archives, project removal) | `operations` (I) acting through `studio`'s resolved layout; `safety` is a pure function of the layout it is given | the archive location derived from the resolved root | `mcp`, `cli` | actions use the resolved `RootLayout`, never a re-derived root — today `SafetyService.persist_root()` ignores `rt.runtime_root`, so deletion archives land cross-root (verify-10 M3, High 4×3=12) |

---

## 6. Conformance map (all 281 source files)

Rules are exhaustive; the split packages are enumerated file by file. Proposal A
produced this map; it is reused with the corrections C-1…C-4, C-9 and is
**verified** by the spot-check table in §6.4.

### 6.1 Package-level rules

| Current package | Files (measured) | Target module(s) | Rule |
|---|---|---|---|
| `schemas/` | 40 | `schemas` 39 whole + `_base.py` split + `filmspec` | `_base.py` **splits**: `SchemaBase` (`:265`) stays in `schemas/base.py`; every enum (`ArtifactType` `:27`, `FilmPhase` `:77`, `AgentRole` `:93`, `AgentFamily` `:105`, `IssueSeverity` `:192`, `ArtifactStatus`, `ValidationStatus`, `GenerationStatus`) → `filmspec`. Other 39 files move 1:1. `registries/` (5 files) stay in `schemas` as payload records and stop being re-exported by `schemas/__init__.py` (C5). |
| `artifacts/` | 12 | `storage` 12 | All 12 whole. `registry.py` keeps `KindSpec`/`MIGRATIONS`/renderers/`REGISTRY`; the **kind vocabulary** (`ArtifactType`) was extracted to `filmspec` in W2, not the file. |
| `graph/` | 36 | `orchestration` 28 + `governance` 8 | → `governance`: `_action_routing.py` (gate law; `compute_actions` moves to `orchestration`), `consistency.py`, `scope_contract.py`, `orchestrator_validators/` (5). → `orchestration`: `__init__`, `graph.py`, `edges.py`, `router.py`, `state_schema.py`, `services.py`, `orchestrator_state.py`, `context_packets.py`, `_agent_routing.py`, `nodes/` (17), `subgraphs/` (2) = 28. `router.py` re-exports `PHASE_ORDER` under a shim until W12. |
| `review/` | 4 | `governance` 4 | `actions.py`, `diff.py`, `generator.py`, `__init__.py`. `diff._id_stem` is deleted in favour of `storage.contract.ArtifactRef.stem()` (F-ARTIFACT-01). |
| `validation/` | 14 | `validation` 14 | 1:1. |
| `agents/` | 35 | `agents` 35 | 1:1 with three internal fixes: `registry.py` + `impl/registry.py` + `mvp/__init__.py` collapse into one `AgentCatalog`; `model_adapter.py:36` drops the concrete-adapter import; `_http_transport.py:18` uses public `providers.credentials.redact`. |
| `providers/` | 14 | `providers` 14 | 1:1. `credentials._env_var_for` → public `env_var_for`; concrete adapters are imported only by `studio`. |
| `generation/` | 17 | `generation` 17 | 1:1; `compositor/` (5 files) stays inside `generation` (A §10.4). |
| `checkpoints/` | 7 | `checkpoints` 7 | 1:1. `resume.py`/`branches.py` fold into `CheckpointManager` in W7 (audit 10 §6.5). |
| `post/` | 7 | `post` 7 | 1:1; `validators.py` becomes the single post-validation rule set. |
| `kb/` | 7 | `kb` 7 | 1:1; `paths.py` becomes the only KB-root resolver. |
| `config/` | 7 | `config` 7 | 1:1; **both** `config → providers` sites leave the package (FES #1): the credential check at `profile_resolver.py:202-206` moves to `providers.required_credentials`, called by `studio`; `register_project_providers` (which calls `build_provider_adapter` at `:179`) moves to `operations`. The edge does not disappear from one site alone (O-12). |
| `constraints/` | 3 | `constraints` 3 | 1:1 (R-7). Absorbs `graph/nodes/_shared.py:29-82`'s number-word grammar. |
| `app/` | 21 | `studio` 14 + `operations` 7 | → `operations`: `services/` (7 files). → `studio`: `__init__`, `runtime.py`, `_graph_exec.py`, `_persistence.py`, `_provider_seeds.py`, `_resume.py`, `bootstrap.py`, `health.py`, `logging_setup.py`, `mock_responses.py`, `product_gate.py`, `safety.py`, `smoke.py`, `version.py` (14). |
| `mcp/` | 46 | `mcp` 46 | 1:1 structurally. Tool handlers lose all direct domain imports and call `operations`; `helpers._services(rt)` and the `get_runtime` package attribute are deleted. `server:main` moves to `studio` in W11. |
| `cli/` | 4 | `studio` 4 | `run.py`, `driver.py`, `io.py`, `__init__.py`; `driver.py:80-81` writes to `_RUNTIME`/`_RUNTIME_MODE_OVERRIDE` become public `studio` calls. |
| `testing/` | 6 | `devharness` 6 | 1:1, renamed, **removed from the wheel** (D6). |
| `src/film_pipeline/__init__.py` | 1 | `studio` | Package metadata (`__version__`, `project_name`); C-1. |

Sum: 39 (`schemas` whole) + 1 (`_base`) + 12 + 28 + 8 + 4 + 14 + 35 + 14 + 17 +
7 + 7 + 7 + 7 + 3 + 14 (`studio`) + 7 (`operations`) + 46 + 4 + 6 + 1 =
**281**. New modules `filmspec`, `budget`, `projects` receive extracted content
or new code, not whole files; `governance` receives 8 graph files + 4 review
files. No orphan files.

### 6.2 File-level enumeration for the split packages

**`schemas/_base.py` (one file, two owners).** `SchemaBase` (`:265`) and any
base-only helpers → `schemas/base.py`. Every `StrEnum` → `filmspec`
(`ArtifactType` `:27`, `FilmPhase` `:77`, `AgentRole` `:93`, `AgentFamily`
`:105`, `IssueSeverity` `:192`, `ArtifactStatus`, `ValidationStatus`,
`GenerationStatus`, plus the phase-class sets folded into `PHASE_GATES`/
`PHASE_ORDER`). `schemas/__init__.py` re-exports both for one program release.

**`artifacts/registry.py` (one file, one owner, one extraction).** The file
stays in `storage`. Only the kind *vocabulary* (`ArtifactType` values) moves to
`filmspec`; `_register_defaults()` becomes guarded so
`set(REGISTRY._exact) == set(ArtifactType) - {clip, last_frame, mid_frame}` plus
the 3 prefix-covered names. `clip`/`last_frame`/`mid_frame` are declared
non-storable media kinds in `filmspec` (R1).

**`graph/` (36 files).** `governance` ← `_action_routing.py`, `consistency.py`,
`scope_contract.py`, `orchestrator_validators/{__init__,_shared,brief,planning_gates,prep_gates}.py`.
`orchestration` ← `__init__.py`, `_agent_routing.py`, `context_packets.py`,
`edges.py`, `graph.py`, `orchestrator_state.py`, `router.py`, `services.py`,
`state_schema.py`, `nodes/{__init__,_agent,_agent_artifacts,_agent_handoff,_agent_prompt_context,_context,_generation_batch_planning,_generation_prompts,_repair_loop,_shared,_visual_matrix_coverage,approval,generation,prep,qc,visual,wrapup}.py`,
`subgraphs/{__init__,qc}.py`. (8 + 28 = 36.)

**`app/` (21 files).** `operations` ← `services/{__init__,operator,errors,models,_browse_ops,_generation_ops,_project_discovery}.py`
(7). `studio` ← `__init__.py`, `runtime.py`, `_graph_exec.py`, `_persistence.py`,
`_provider_seeds.py`, `_resume.py`, `bootstrap.py`, `health.py`,
`logging_setup.py`, `mock_responses.py`, `product_gate.py`, `safety.py`,
`smoke.py`, `version.py` (14). (7 + 14 = 21.)

### 6.3 Non-source artifacts

| Path | Disposition |
|---|---|
| `profiles/` (10 yaml, repo root) | **stays** at the repo root; owned by `config` as its input contract |
| `film-knowledge-base/` (data) | **stays**; root resolution owned by `kb` |
| `scripts/` (9 `.py`) | **stays**; developer tooling, must not be importable from `src/` |
| `langgraph.json` | **stays** at the repo root; its `graphs` target changes to `./src/film_pipeline/orchestration/graph.py:graph` in W11 (the one externally visible path change; B7) |
| `tests/` (180 `.py`) | mirror per target module (`tests/unit/<module>/`), plus new `tests/architecture/`; `tests/unit/testing/` → `tests/unit/devharness/` |
| `docs/` | not a module; not in the wheel; CI-exempt |

### 6.4 Spot-checks against the real tree (20 mappings checked)

Proposal A's map is reused, not re-derived. These 20 mappings were independently
re-checked at `fb85baa` with `find`/`grep`/venv imports; every one resolved, and
the four numeric corrections found are C-1…C-4.

| # | Mapping asserted | Check | Result |
|---|---|---|---|
| 1 | `schemas/_base.py` splits: `SchemaBase`→`schemas`, enums→`filmspec` | `grep -n "^class SchemaBase\|^class FilmPhase\|^class ArtifactType\|^class IssueSeverity"` | `SchemaBase:265`, `ArtifactType:27`, `FilmPhase:77`, `IssueSeverity:192` — split confirmed |
| 2 | `schemas/` = 40 files | `find … /schemas -name '*.py' \| wc -l` | 40 ✓ |
| 3 | `artifacts/registry.py` keeps `KindSpec` → `storage` | `grep -c "class KindSpec"` | 1 ✓ |
| 4 | `artifacts/paths.py` keeps `PHASE_DIR_MAP` → `storage` | `grep -c PHASE_DIR_MAP` | 2 ✓ |
| 5 | `artifacts/` = 12 files → `storage` | `find` | 12 ✓ |
| 6 | `graph/_action_routing.py` → `governance` | `grep -c APPROVAL_GATES` | 4 ✓ |
| 7 | `graph/nodes/_shared.py` `_SERVICES_CTX` → `orchestration` | `grep -c _SERVICES_CTX` | 2 ✓ |
| 8 | `graph/nodes/` = 17 files (A said 19) | `ls graph/nodes/*.py \| wc -l` | 17 → **C-3** |
| 9 | `graph/` = 36 files → 28 + 8 | `find` | 12 top + 17 nodes + 5 ov + 2 subgraphs = 36 ✓ |
| 10 | `review/actions.py` → `governance` | `grep -c "def compute_available_actions"` | 1 ✓ |
| 11 | `review/diff.py` `_id_stem` leak → fix via `storage.contract` | `grep -c _id_stem` | 3 ✓ |
| 12 | `app/services/` = 7 files → `operations` (A said 5) | `ls app/services/*.py \| wc -l` | 7 → **C-2** |
| 13 | `app/` = 21 files → 14 + 7 | `find` | 21 ✓ |
| 14 | `app/product_gate.py` is the C2 edge | `grep -c "from film_pipeline.mcp.contract"` | 1 ✓ |
| 15 | `cli/driver.py` writes `_RUNTIME_MODE_OVERRIDE` → `studio` | `grep -c _RUNTIME_MODE_OVERRIDE` | 1 ✓ |
| 16 | `mcp/tools/helpers.py` `_active_project_id` → `projects` | `grep -c "def _active_project_id"` | 1 ✓ |
| 17 | `testing/in_memory_git.py` imports `checkpoints.git_backend` → `devharness` | `grep -c "from film_pipeline.checkpoints.git_backend"` | 1 ✓ |
| 18 | `constraints/extractor.py` clean leaf → `constraints` | `grep -c "def extract_constraints"` | 1 ✓ |
| 19 | `generation/compositor/` = 5 files (A said 4) → stays in `generation` | `ls generation/compositor/*.py \| wc -l` | 5 → **C-4 note** |
| 20 | `agents/impl/registry.py` `AGENT_CLASS_BY_ID` (3-registry fix) | `grep -c AGENT_CLASS_BY_ID` | 2 ✓ |
| 21 | Artifact kinds: R1 ground truth | venv: `len(REGISTRY._exact)`, `len(ArtifactType)`, set diffs | 47 / 45 / 39 shared; 8 registry-only, 6 enum-only → **C-9/C-10** |
| 22 | `src/film_pipeline/__init__.py` unassigned by A | `ls src/film_pipeline/*.py` | 1 file → **C-1** |

Additional structural confirmations: `mcp` = 46 files (7 top + 39 tools);
`agents` = 35 (10 top + 18 impl + 1 model_routing + 1 mvp + 5 prompt_templates);
`providers` = 14 (10 top + 4 adapters); `validation` = 14 (5 top + 8 impl + 1
validators); `_services` = 112 refs / 43 files; `FILM_PIPELINE_NO_PERSIST` = 7
literal sites; `"blocking"` comparisons/emissions = 48; `schemas._base`
importers outside `schemas/` = 72.

---

## 7. Decisions record

### D1 — One distribution, not a `uv` workspace of distributions

- **Context.** The owner asked directly whether Python has a gem-like unit. It
  does not, exactly: in Ruby, a *gem* is the distribution and a *module* is the
  namespace/unit of encapsulation. In Python the analogous pair is a
  **distribution** (the thing `uv build`/PyPI ships, named in
  `[project].name`) and an **import package** (the thing `import` names). This
  repo already ships **one** distribution, `film-pipeline`, with `packages =
  ["src/film_pipeline"]` (`pyproject.toml:59`), containing 17 import packages.
  The modularization problem the audit found is *not* a packaging problem: the
  corrected **173 live findings** are duplicated normative models, split state
  authority and parallel registries, all of which exist **inside** one
  distribution.
- **Decision.** Keep **one** distribution. Enforce boundaries between the 20
  import packages with D2's contract manifest and guard suite. Do **not**
  create a `uv` workspace with one distribution per module.
- **Alternatives.** (a) One distribution per module (a `uv` workspace): rejected
  — it converts every import-boundary question into a versioned dependency
  question, forces a lockfile/publish cycle per extraction wave, and buys
  nothing for the actual findings; it would also break the single entry point
  (`langgraph.json`, `mcp.server:main`) that product users depend on. (b) Publish
  nothing and rely on `AGENTS.md` prose: rejected — measured false (11 violating
  statements under its own targeted greps; §4.6.1 settles the scope and the count).
  (c) A separate `film-pipeline-core`
  distribution for `filmspec`/`schemas`/`storage` only: rejected as premature;
  it is a plausible *future* step, not a current need (B9).
- **Consequences.** `uv build` keeps producing one wheel; `make ci-check` is
  unchanged; the boundary artifact is a test suite, not a packaging layout. The
  program's "gem analogue" vocabulary is recorded here so it is not re-litigated:
  **a Python distribution is the gem analogue; the repo's import packages are
  Ruby-`module` analogues, enforced by D2.**
- **Revisit trigger.** Split into a workspace only if two conditions hold
  together: (i) a module is asked to ship on an independent release cadence
  (a real external consumer of, say, `filmspec` or `storage` alone), **and**
  (ii) that module's public contract has been stable across two consecutive
  extraction waves with an empty exemption ledger. Absent (i), one distribution.

### D2 — Enforcement: typed `ModuleContract` + shared AST guard suite; enola corroborates

- **Context.** The repo has two hand-rolled AST guard suites
  (`tests/unit/artifacts/test_storage_boundary.py`,
  `tests/unit/graph/test_startup_boundaries.py`) plus three more bespoke guards
  (storage guards, config contract, channel registry). `AGENTS.md:51` states a
  law that 11 import statements violate and nothing checks. Enola is installed
  (`~/.local/bin/enola`, a user binary, not a dependency), `mcp-arch.yaml` is
  checked in, `.enola/` is stale, and there is **no** `enola-intent.yaml` — hence
  "0 layer violations because no layers are declared". `import-linter`, `grimp`,
  `tach` and `pytest-archon` are absent offline (`grep` over
  `uv.lock`/`pyproject.toml` returns nothing; B §2.1).
- **Decision.** Adopt proposal B §5: `src/film_pipeline/architecture.py` (typed
  leaf: `Exemption`, `ModuleContract`, `VocabularyMirror`, `StateChannel`,
  `RegistryAgreement`, `PolicyPoint`, plus cross-module rows), a `CONTRACT`
  block in each package `__init__.py`, and `tests/architecture/` (9 files) riding
  the existing `pytest` gate. `tests/unit/architecture/` is not created. enola
  remains a corroboration/impact tool and gets a **derived** `enola-intent.yaml`
  generated from the manifest once W2 lands, so it grades against the same law
  the guards enforce.
- **Alternatives.** (a) `import-linter` (+`grimp`): rejected — absent offline,
  lockfile churn, and it sees import edges only, so O1 (48 severity literals, 11
  phase definitions), O3 (8 `current_phase` writers), O4 (registry agreement),
  O5 (7 policy read sites) and half of O7 are invisible; A's own AST guard could
  express them but A chose a YAML declaration instead. (b) `tach`: rejected —
  same absence, same import-edge-only limit, and it introduces a second
  configuration format beside the manifest. (c) enola layers as the gate:
  rejected — enola collapses submodules to their parent package (that is the
  cause of C1/C4/C5) and cannot express L3/L5/L6 or the state sweeps; it also
  needs a hand-written intent file that would duplicate the manifest. (d) A's
  `layers.yaml` + free-text baseline: rejected — untyped, no citation check, no
  liveness, so a fixed violation's row stays green (allowlist rot, B §10.1).
- **Consequences.** Zero new dependencies, zero CI-YAML changes; ~1,418 lines
  of mechanism for 281 files; W0 is green and every later wave deletes ledger
  rows. The prototype's only failing guard was the citation check, because
  proposal B's document did not yet exist; citations are re-pointed at **this
  document**, which resolves it. Cost is bounded: the five existing guards run
  21 tests in 7.5 s wall-clock; the new sweeps are the same class (B §6.7).
- **Revisit trigger.** If the manifest exceeds ~500 lines, split invariant data
  into `architecture_<domain>.py` files that the guard globs (types stay in the
  leaf). If `tach`/`import-linter` ever ships as a locked dev dependency,
  re-evaluate it as a redundant edge check only — never as the primary gate.

### D3 — `app ↔ mcp` (C2) is broken by splitting `app` into `studio` and `operations`

- **Context.** C2 is the only package-level cycle (7 modules; `enola` §2,
  F-BOUNDARY-03). `app/product_gate.py:17` imports `mcp.contract.make_registry`
  (1 edge up), while `mcp/server.py:164,241,248,249` and
  `mcp/tools/__init__.py:22` import `app.runtime`, `app.bootstrap`,
  `app._persistence`, `app.logging_setup` (7 edges down). `app` is a dependency
  hub (enola: 214 fan-in / 40 fan-out), not a leaf composition root.
- **Decision.** Split `app` at the *role* boundary, not the file boundary:
  `studio` (L12) hosts the entry points and the object graph and may import
  `mcp`; `operations` (L10) holds `app/services/` and is imported **by** `mcp`.
  The bootstrap/entry-point half of `mcp/server.py:main` moves to `studio`
  (`bootstrap(role)`), and `mcp` receives an injected `OperatorBackend`. W1 moves
  `product_gate.py` above `mcp` early (temporary `film_pipeline/entrypoints.py`)
  so the cycle is closed before the big split.
- **Alternatives.** (a) Delete `app → mcp` by having `product_gate` import the
  registry differently: rejected — `make_registry` is the MCP contract's own
  builder; the defect is that an entry point lives inside the package `mcp`
  depends on, not that the import exists. (b) Keep `app` whole and make it
  `unrestricted_imports` (B's wave-0 view): rejected for the target law (R-3);
  it is retained in W0 as the observed-edge declaration only. (c) Move all of
  `app` above `mcp`: rejected — `app/services/OperatorService` would then be
  above the surface that calls it, which is the mirror-image cycle; the use-case
  façade must be below.
- **Consequences.** `mcp → app` (7 edges) and `mcp → generation/artifacts/graph/
  checkpoints` (40 edges) all disappear; `mcp` calls `operations` only.
  `_services` (112 refs / 43 files) dies in W10. The entry-point bootstrap
  becomes one function with one persistence policy (also fixes F-MCP-09).
  `langgraph.json` changes in W11 and internal import paths change with shims
  (B7).

### D4 — `artifacts.contract` does not become a module; `storage.contract` does

- **Context.** `audit/07` §6 proposes a top-level `artifacts.contract` module
  owning "the artifact reference/kind/status/version contract and its
  enforcement". `01` §7 lists it as the candidate owner. R3 constrains it:
  "express the artifact-contract candidate as an *enforcement and derivation*
  concern (single formatter, store-decided version, enum↔registry agreement
  guard), not as a second storage module". `audit/07` §6.1 lists ten things
  storage already owns single-handedly (layout, root, atomic writes, paths, kind
  catalog, versioning, checksum, schema/migration, approve/supersede, renderer
  lookup).
- **Decision.** No top-level `artifacts.contract`. The derivation/enforcement
  concern becomes `storage/contract.py` (seven public names, §3.6.1), importing
  `filmspec` (kind vocabulary) and `storage.registry`. The kind **vocabulary**
  moves to `filmspec`; the kind **catalog/specs** stay in `storage`.
- **Alternatives.** (a) Top-level `artifacts.contract` module (audit 07): rejected
  — R3; it would sit at L3 beside `storage`, creating a `storage ↔ contract`
  cycle candidate and a module whose only distinct content is derived from
  `storage`'s own registry. (b) Split `storage` into `catalog` + `store`
  (proposal A §10.1's rejected option): rejected — `registry.py` is imported by
  the store's write path in four names; the split adds a hop per save for
  nothing the parity guard does not buy. (c) Leave the contract inside
  `registry.py`/`store.py` with no named submodule: rejected — the leak inventory
  (F-ARTIFACT-01…09) needs one named public surface to point at and guard.
- **Consequences.** `review/diff._id_stem` is deleted; nine caller-side version
  derivations are replaced by store-decided versioning; unknown kinds refuse on
  read; two transition tables exist once. The `storage` module's public contract
  grows by one submodule, and the storage boundary guard is extended so
  `storage.contract` may not import above L1 (`test_storage_never_imports_above_l1`).

### D5 — Budget/spend lives in a `budget` module; `governance` stays stateless

- **Context.** Today: 4 independent caps, 7 representations, 6 writer modules,
  8 gate sites of which exactly 1 can refuse, `spent_usd` always 0 and
  `SpendRecord`/`actual_cost_usd` have zero writers (F-BUD-01/02/03/04,
  F-CFG-06; `audit/12` §3, §6.4). `01` §12 nominates `governance` for the budget
  law; `audit/12` §6.4 proposes a `budget` module. Proposal A has no budget
  module: it puts the spend ceiling in `generation` and the "budget law" in
  `governance`.
- **Decision.** Create `budget` at L5: `BudgetState`, `cap_for`,
  `authorize_spend`, `record_spend`, `SpendRecord`; durable through `storage`.
  `generation` calls `authorize_spend` before dispatch and `record_spend` after
  completion; `governance` consumes the verdict as an input value and keeps zero
  state. `providers.pricing` still estimates; `budget` only compares.
- **Alternatives.** (a) Fold into `governance` (`01` §12): rejected — `governance`
  is the one module whose anti-cycle argument is "it is a pure function over
  values" (A §10.6); a spend ledger makes it stateful and a cycle candidate, and
  it would then own both the phase decision and the money record. (b) Fold into
  `generation` (A's implicit placement): rejected — the cap is project-level and
  gates spend beyond video generation (F-BUD-02's 8 sites include graph, router
  and operator gates), so `generation` would own jobs **and** project money; and
  the ceiling policy would still be re-derived at the MCP/operator path
  (F-GEN-01). (c) Keep the cap in `config` as a resolved value only: rejected —
  `config` is stateless and would still leave the spend *record* ownerless
  (F-BUD-03).
- **Consequences.** One cap **value** (the project record's `budget_cap_usd`, read
  through `storage` — not re-derived from the profile at any gate); one refusal
  path; `spent_usd` becomes a real sum; the MCP `approve_generation_spend` default
  changes from unlimited
  (`-1.0`) to the estimate-derived ceiling — a **deliberate behaviour change**,
  listed in W8's phase note (B7). Module count becomes 20.

### D6 — `film_pipeline.testing` → `devharness`, removed from the wheel

- **Context.** `testing` ships in the wheel (`packages = ["src/film_pipeline"]`)
  and is the only `src` package excluded from coverage
  (`pyproject.toml:95-98`, `:103-105`), importing three domains
  (F-BOUNDARY-06). At HEAD, **no production module imports
  `film_pipeline.testing`** (`grep` over `src/film_pipeline` excluding
  `testing/` returns nothing), while `app/mock_responses.py` *is* imported by
  `app/runtime.py`, `graph/services.py`, `agents/runner.py` and `cli/driver.py`.
- **Decision.** Rename to `devharness`, declare its contract (B1/B2), give it one
  fake factory for the `GraphServices`/`OperatorBackend` seams (F-TEST-08), a
  `GitBackend` parity test (F-TEST-03), a production-separation guard with a
  self-test (F-TEST-06), and **remove it from the shipped wheel** (narrow the
  build config / relocate under `tests/`). `app/mock_responses.py` **stays in
  `studio`** as the production mock-mode payload source, bound to output schemas
  in W4 (F-TEST-01). Mock provider adapters (`providers/mock_provider.py`,
  `mock_image_provider.py`) stay in `providers`, where they implement the real
  port.
- **Alternatives.** (a) Proposal A's move of `mock_responses.py` into
  `devharness`: rejected by the import measurement above and because the shipped
  `product-gate` target runs mock mode in CI. (b) Keep `testing` shipped and
  declare it a dev-support distribution package (audit 13's open option):
  acceptable as a fallback only if wheel exclusion is rejected; then it needs the
  parity + separation guards unconditionally. (c) Delete `testing` and
  regenerate doubles per test: rejected — it re-creates the per-tier fixture
  duplication F-TEST-05 found.
- **Consequences.** The wheel shrinks; `tests/unit/testing/` renames; the
  coverage omit can be dropped once the package is dev-only (or kept as a
  belt-and-braces rule). `devharness` is off-graph, so L7 stays simple.

### D7 — The phase model becomes first-class, inside `filmspec`

- **Context.** Phase vocabulary/order/gate is defined in 11 places across 8
  modules (F-PHASE-02), phase advancement has two implementations and the app
  path skips the provider-blocked gate (F-PHASE-01, DIVERGENT), the successor
  function is duplicated (F-PHASE-04), and the router action vocabulary has no
  declared edge table (F-PHASE-06). `audit/01` proposes a `phase-model` module
  (home `schemas/phase.py`); proposal A folds phases into `filmspec` and the
  transition *decision* into `governance`; `audit/02` folds the phase catalog
  into the orchestrator-state owner.
- **Decision.** Yes, the phase model is first-class — but as part of `filmspec`,
  not a separate module. `filmspec` owns `FilmPhase`, `PHASE_ORDER`,
  `PHASE_GATES`, `next_phase`, `successor`, `gate_for`, the agnostic/generation-
  dependent sets, and the phase-keyed policy name sets. `governance` owns
  `advance_decision(...)`, the one transition invariant (including the
  provider-blocked refusal), taking provider health/budget as values.
  `orchestration` derives `_PHASE_TO_NODE`, `_PHASE_NODES`,
  `_NEXT_PHASE_AFTER_APPROVAL` and `_PHASE_DEFAULT_AGENTS` from `PHASE_ORDER`;
  `storage` keeps `PHASE_DIR_MAP` keyed by `FilmPhase` and asserted to cover
  `PHASE_ORDER` in order (`audit/01` §"Candidate module boundary").
- **Alternatives.** (a) Standalone `phase-model` (audit 01): rejected — it
  fragments the normative vocabulary (`IssueSeverity`/`ArtifactType`/statuses
  would live elsewhere), and a second zero-import leaf that only two modules use
  is exactly the over-modularization §9 warns about. (b) Stay in `schemas` (B's
  wave-2 canonical owner): rejected for the target — `schemas` is the payload
  kernel and must not also be the vocabulary *law*; keeping them together is
  where F-BOUNDARY-02's 72 private importers come from. (c) Phase catalog in the
  orchestrator-state owner (`audit/02`): rejected — the catalog is consumed by
  `storage` (paths), `constraints` (keywords) and `governance`, all **below**
  `orchestration`; putting it there inverts those edges.
- **Consequences.** W2 replaces the 48 `"blocking"` literals, the 11 phase
  orderings and the 9 inline gate literals; `MIRRORS.canonical` re-points from
  `film_pipeline.schemas.FilmPhase` to `film_pipeline.filmspec.FilmPhase`
  (a one-line manifest edit); the app-path gate skip (F-PHASE-01) is fixed by
  routing `operations.advance_to_next_phase` through `governance.advance_decision`.

### D8 — Runtime persistence does not become a module

- **Context.** `audit/10` §6 proposes a `runtime_persistence` module owning the
  persistence policy, root layout, checkpoint registry, audit trail and resume
  coordinator. Proposal A assigns roots/policy to `studio`, checkpoint state to
  `checkpoints`, and the on-disk files to `storage`.
- **Decision.** No `runtime_persistence` module. `studio` owns
  `resolve_persistence()`/`resolve_roots()` (one policy, one root layout);
  `checkpoints` owns checkpoint/rollback/resume **lifecycle**; `storage` owns
  every byte (`project.json`, `state/graph-state.json`,
  `checkpoints/checkpoints.jsonl`, `audit/audit-log.jsonl`) and exposes
  `AuditTrail`; `schemas/audit.py` holds the event model.
- **Alternatives.** A `runtime_persistence` module (audit 10 §6): rejected — its
  N/I/R list already names three owners, and a module whose job is to hold a
  `RootLayout` between `studio` and `storage` adds a hop and a cycle risk
  (`runtime_persistence ↔ checkpoints`) for no ownership gain. Keeping policy in
  `app/runtime.py` (status quo): rejected — F-CRP-01's five root paths and
  F-CRP-09's two persistence formulas are the finding.
- **Consequences.** F-CRP-01/-02/-03/-04/-05/-06/-09 are addressed in W6/W7;
  the `ResumePayload` becomes typed; `app/_resume.py` and `checkpoints/resume.py`
  collapse to one coordinator in `checkpoints` (or `operations` for the
  operator-facing entry).

### D9 — Renames are scheduled last, behind shims, and shims are self-deleting

- **Context.** A's target names are adopted (R-1), but renaming packages touches
  every internal import path and the test tree; the repo has a precedent for
  permanent shims (`graph._action_routing.PHASE_ORDER`,
  `schemas._base`, `app.services.operator`) A §10.7 warns about.
- **Decision.** Extraction moves *content* under existing package names first
  (W1–W10); the target-name rename is W12, mechanical, one commit per package,
  with a `# SHIM(<phase>)` token on every re-export. The final guard fails if any
  `SHIM(` token remains.
- **Alternatives.** Rename first (A's per-phase re-exports imply this):
  rejected — it maximizes churn while the code is still moving and makes
  reviews unreadable. No renames at all (B): rejected — the names encode
  ownership and the law is expressed over them.
- **Consequences.** `langgraph.json` changes in W11 (not W12) because the graph
  module path moves with the `governance` split; that is the one external path
  change and is listed in B7.

### D10 — No module is coarsely exempt; the FES counts every module

- **Context.** B §5.3 declares `UNRESTRICTED_PACKAGES = {graph, mcp}`, encoding
  `AGENTS.md:51`; B §9.3 concedes this makes B3 vacuous for the two
  most-coupled packages; A §10.8 argues against the `AGENTS.md` domain-isolation
  sentence in the opposite direction (it forbids necessary downward edges).
  Adversarial O-07 then observed that `studio` imports 18 of the other 19 target
  modules, so "no unrestricted modules" was true only by renaming the exempt set.
- **Decision.** Encode **no coarse exemption** in the **target** law (L1/L8).
  The precise statement is: every module's outbound set is finite and declared,
  and `studio` is a composition root whose set is the enumerated 18 of §4.3 with
  an empty inbound set (L6). `studio` and `mcp` are inside the FES like every
  other module (§4.6.1), and `mcp`'s ten forbidden edges are counted, not
  excluded. W0 keeps B's `unrestricted_imports=True` for `graph`/`mcp` **only as
  a pre-image**: it declares the observed edge set so the suite can run green
  before migration, and each wave replaces it with the §4.3 `may_import` set
  (W11 for `mcp`); `test_declared_edges_are_real` prevents a stale entry from
  re-licensing a removed edge. The flag must not exist by W12.
- **Alternatives.** Permanent unrestricted imports (B): rejected by B's own
  objection. Restoring `AGENTS.md:51` verbatim (A §10.8's rejected reading):
  rejected — it forbids `generation → storage`, `validation → storage` and
  `agents → providers`, which are correct and necessary, and would push typed
  data through the filesystem. Declaring `studio` outside the FES ("composition
  roots are not counted"): rejected — that is the redefinition O-07 names, and it
  would make `operations → studio` and `mcp → studio` uncountable.
- **Consequences.** O7, O1, O3, O4 and O5 guards apply to `graph`/`mcp` from W0
  even while their coarse edge set is still the observed one; the coarse check
  tightens by W11, and the FES count of 13 is the number that must reach 0.

### D11 — Artifact-kind ground truth is 47 / 45 / 39; the disagreement is resolved by declaration

- **Context.** R1: 47 registered ids (`REGISTRY._exact`) vs 45 `ArtifactType`
  values, 39 shared; 8 registry-only, 6 enum-only (3 prefix-covered, 3
  uncovered). Proposal A's F-AKIND-01 method error (kind slugs vs enum values)
  is recorded in `reconciliation-notes.md` R1 and in §2.2 R-8.
- **Decision.** The registered id set is the canonical storable vocabulary.
  `filmspec` declares all 47 names; the 8 registry-only names are added to the
  enum or given first-class status; `clip`, `last_frame`, `mid_frame` are
  declared **non-storable media kinds** explicitly (they have no registry entry
  by design); `checkpoint`, `invalidation_report`, `rollback_record` are
  reachable through their registered prefixes. `storage.contract`'s guard
  asserts, mechanically: every `REGISTRY._exact` id is in `filmspec`, and every
  `filmspec` kind is either exact-registered, prefix-registered, or one of the
  three declared media kinds.
- **Alternatives.** Derive `ArtifactType` from `REGISTRY` (A's F-AKIND-01
  sketch): rejected — it inverts the dependency (`filmspec` would import
  `storage`, L0→L3) and makes the L0 vocabulary depend on the L3 catalog.
  Delete `ArtifactType` and expose `filmspec.artifact_kinds()`: equivalent, but
  it breaks the 45-value enum surface many modules import; keep the enum and
  add the missing names.
- **Consequences.** W4 adds the 8 names, declares the 3 media kinds, adds
  `CONSENSUS_REPORT`/`COST_ESTIMATE`-style fixes to
  `graph/nodes/_context._ARTIFACT_TYPE_BY_CLASS` (which today silently falls back
  to `script`), and turns the registry-agreement guard on. Data already written
  with `artifact_type=script` (F-ARTIFACT-02) is read-compatible because the
  payload model is unchanged; the wrong stored *type label* is not migrated (no
  reader keys on it — the one unverified hypothesis in `audit/07` §7 is retained
  as a caveat).

### D12 — The scope definition behind every forbidden-edge count (V3)

- **Context.** `audit/14` and ledger `L-48` state "eight distinct forbidden
  edge" as an enumeration; `review/orchestrator-verification-notes.md` V3 shows
  it is the union of three **targeted** greps (`agents|config|generation →
  providers`, `post → validation`, `testing → artifacts|checkpoints|providers`)
  that cannot see any other pairing. A full AST sweep finds **53** cross-package
  edges, and the answer is anywhere between 6 and 32 depending on whether
  `schemas`, `artifacts`, `app`/`cli` and `testing` are in scope. The law as
  written does not define "domain module", so "eight" and "32" are both
  defensible and neither is a fact.
- **Decision.** The target law does **not** use the phrase "domain module". It
  fixes a scope at **target-module granularity** — the §4.6.1 **FES**, whose
  normative sentence is quoted there and which `04` and `05` must cite verbatim.
  Under it the HEAD forbidden-edge count is **13** (not 10, not 4): three
  non-`mcp` edges (`config → providers`, `governance → orchestration`,
  `operations → studio`) plus ten `mcp → *` edges, with `mcp` inside the scope
  because it is an ordinary L11 module. The count is **derived** by the guard
  from `ModuleContract.may_import` and the observed edge set — never written into
  a document. The former 10 came from a *package-granularity* mapping that cannot
  see the `graph` or `app` splits and omitted `mcp → studio`.
- **Alternatives.** (a) Keep "eight" with a caveat (V3's fallback for `L-48`):
  rejected — a count with an undefined scope is exactly the O5
  policy-by-branch pattern this program exists to remove. (b) Declare `artifacts`
  a blanket allowed target as `AGENTS.md` implies: rejected — it would legalize
  `mcp → artifacts` and re-open the parallel-lifecycle seam (F-MCP-04/05). (c)
  Put `mcp` (or `studio`) outside the count as `05` did: rejected — that is the
  redefinition D10/O-07 refuses, and it hides ten real edges. (d) Keep the
  package granularity: rejected — a law that splits `graph` into `orchestration`
  and `governance` cannot be enforced by a package-level sweep (O-02). (e)
  Enumerate forbidden edges as a hand-maintained list (A's
  `violations-baseline.txt` style): rejected — the list would drift from the
  manifest with nothing forcing agreement; the FES count is a *result*, not a
  source.
- **Consequences.** `05-enforcement-and-guard-tests.md` must consume the §4.3
  matrix (or the manifest that produces it) rather than a hand-maintained list,
  and must cite §4.6.1 rather than restate a scope; its `UNRESTRICTED_PACKAGES`
  exclusion and its `assert len(edges) == 53` are superseded, and its
  `agents → providers` W1 item is dropped because §4.3 declares that edge
  allowed (adversarial O-11). W0's ledger still records the observed edges
  exactly (all 53 package edges are declared then tightened); the 13 forbidden
  edges carry `Exemption` rows and become legal-or-deleted by W11–W12.

### D13 — A single "middleware" module is rejected; the 20 modules are extracted instead (V10)

- **Context.** The alternative shape a reviewer will raise: instead of extracting
  20 modules, add **one middleware module** owning the cross-cutting mechanisms
  (the `SchemaBase` contract, state channels and the writer law, tool dispatch,
  the generation ledger, the delivery manifest) and let every caller reach it.
  §9.8 rejects `common`/`utils`, but that is a different shape — a shared helper
  bag — so this one needs its own rejection.
- **Measured refutation** (V10; `reviews/orchestrator-verification-notes.md`):
  - `src/` carries **442 cross-package import statements across 144 of 281
    files**, with **145 distinct deep import targets** — middleware would have
    144 captive consumers on day one.
  - Fan-in it would own: `schemas._base` **143** sites (107 of them private
    reach-ins, 72 files outside `schemas`); `mcp.tools` imported **72** times
    from outside `mcp`; `graph.nodes` **58**; `agents.impl` **36**;
    `validation.impl` **28**.
  - The layer law pins it to the bottom of the DAG (L0/L1), where it can hold no
    behaviour and no state without becoming a second `graph` — i.e. the
    god-object the audit already found (`StudioRuntime`, 103/95/78 dependents).
  - "Let the tests wire it up themselves" is refuted too: of **180** test
    modules, **all 180** import production packages, for **856** production-import
    statements (`schemas` 206, `app` 175, `graph` 121, `mcp` 80, `artifacts` 64).
    The four existing guards are themselves consumers — `test_channel_registry.py`
    imports `graph.state_schema`, `graph.orchestrator_state`, `graph.services`,
    `graph.nodes` and `app.mock_responses`; `test_config_contract.py` imports
    `config.profile_resolver`, `config.runtime_overrides`, `graph.nodes` and
    `mcp.tools`; `test_storage_boundary.py` imports `artifacts.project_storage`.
- **Decision.** Reject middleware / inversion-of-control. Extract the 20 modules
  of §3 with the §4.3 matrix and the D2 guard suite.
- **Alternatives.** (a) One middleware module: rejected on the three measurements
  above — 442 imports across 144 files to migrate, a forced L0/L1 position that
  cannot own behaviour or state, and all 180 test modules needing rewrite, which
  is **strictly more churn** than extracting the modules while keeping every
  current import path working behind shims. (b) Middleware as a *thin* façade
  over `filmspec`/`schemas` only: rejected — that is already `filmspec` + L1
  `schemas`, whose 322-statement surface is deliberately the smallest possible
  one; adding a façade over it multiplies the surface without moving ownership.
- **Consequences.** The module count stays 20; nothing in §3 or §4 changes. This
  row exists so the rejected shape is on the record with numbers a reader can
  re-run (V10's commands), satisfying B8.

---

## 8. Compatibility (bar B7)

Three externally visible contracts, one on-disk contract, and **three persisted
representations that change**. Per module, what is preserved and what is explicitly
broken. **Nothing breaks silently**: every "broken" row names the wave that ships it
and the phase note that documents it, and every row that changes persisted bytes
states whether it is additive/read-compatible and what a single `git revert`
does and does not undo (adversarial O-14, B5).

| Contract | Owner module(s) | Disposition | Where |
|---|---|---|---|
| **MCP tool names, JSON input/output shapes, `mutates_state` / `requires_confirmation` / `creates_checkpoint` flags** | `mcp` (R), with `operations` supplying values | **Preserved, and frozen from W0.** Names and shapes **will be frozen by** `tests/unit/mcp/test_contract_freeze.py::test_tool_names_and_schemas_unchanged` (a `make_registry()` name + schema-key snapshot). The test does **not exist at HEAD** (adversarial O-22), so the row is phrased as a plan and the freeze test moves to **W0** — it is a snapshot and needs no refactor, so it can gate every later wave rather than only W11. `mcp` losing its direct domain imports changes *who computes* the values, not the response envelope: every handler still returns the `_ok`/`_error` dicts it returns today. | freeze test W0; shapes all waves |
| MCP `inputSchema` | `mcp` | **Preserved, then improved.** Today every tool advertises `inputSchema: {}` (F-MCP-03). Populating it is additive; no client can depend on an empty schema. | W11 |
| MCP `approve_generation_spend` default ceiling | `generation` now, `budget` after W8 | **Explicitly broken (behaviour).** Today the MCP path defaults `max_cost_usd` to unlimited (`-1.0`) while the graph path derives estimate × 1.1 (F-GEN-01). Target: both derive the ceiling in `generation`/`budget`. This is the **only intentional behaviour change** in the program; W8's phase note carries it, and a test asserts both paths agree. | W8 |
| MCP `project_kind` / project resolution | `projects` (R), `mcp` consumes `projects.resolve` | **Preserved.** `RequestEnvelope.resolved_project_id` semantics unchanged; F-MCP-06's path-dependent `project_kind` becomes one registry read. | W10 |
| **LangGraph state schema (channels + reducers)** | `orchestration` (N+I+R) | **Preserved with two declarations.** (1) The `_services` channel stays declared (`graph/state_schema.py:102,112`) and runtime-only — it is already stripped before persistence; removing it is rejected. (2) `consensus_report`: routing currently reads an **undeclared, unwritten** key (F-OST-06/F-VR-05); the target declares a typed `consensus_report_ref` channel owned by `validation` with a default, so old checkpoints resume. **Additive and read-compatible**: a missing channel takes its default, old checkpoints load, and a revert removes the reader without invalidating existing files. | W7 |
| `current_phase` | `orchestration` | **Preserved** (same key, same type); only the *writer set* shrinks from 8 to 1 (F-PHASE-01/`audit/02`). No persisted value changes meaning. | W3 |
| `_orchestrator__*` key grammar | `orchestration` | **Preserved.** Prefix grammar and key names unchanged; the three consumer modules stop re-deriving the prefix (F-OST-11). | W3/W9 |
| **Checkpoint / resume / rollback protocol** | `checkpoints` (N+I), `storage` (R) | **Preserved.** On-disk layout v2 is untouched (`LAYOUT_VERSION = 2`, marker gating, envelope, JSONL logs); `ProjectStorage` method set is already guarded. `ResumePayload` gains a **type** (F-CRP-03) but the same fields and the same `Command(resume=...)` payload; `checkpoints/resume.py`/`branches.py` fold into one coordinator without changing the persisted format. | W6/W7 |
| **LangGraph SQLite checkpointer** (`<checkpoints root>/checkpoints.sqlite`) | `orchestration` (N+I+R) | **Preserved, and declared as *not* `checkpoints`' concern.** Two checkpoint mechanisms coexist: the `checkpoints` module's JSONL metadata/lifecycle registry, and `orchestration`'s LangGraph SQLite saver built in `graph/graph.py:41-51`. The target keeps both, adds **no** `orchestration → checkpoints` edge (§5, adversarial O-06), and `orchestration` reads its root from `storage.default_checkpoints_root` (declared in §3.6). The file path and the saver's on-disk format are unchanged. | W6 (root resolution only) |
| Persistence-mode precedence (`FILM_PIPELINE_NO_PERSIST` / `PERSIST_STATE`) | `studio` (one `resolve_persistence()`) | **Explicitly broken (behaviour), documented.** The genuinely divergent sites are **`graph/graph.py:43`** on one side and **`graph/services.py:31,48`** plus the `cli/run.py:226` override on the other; `app/_persistence.py:51` is *not* a divergence (adversarial O-13). The two formulas, side by side: <br>`graph/graph.py:43` — `if os.getenv("NO_PERSIST") or not os.getenv("PERSIST_STATE"): return MemorySaver()` ⇔ `PERSIST_STATE ∧ ¬NO_PERSIST` <br>`app/_persistence.py:51` — `return bool(os.getenv("PERSIST_STATE")) and not bool(os.getenv("NO_PERSIST"))` ⇔ `PERSIST_STATE ∧ ¬NO_PERSIST` <br>These are **logically identical** (`¬(A ∨ ¬B) ≡ B ∧ ¬A`), so the former citation of this pair was wrong. The divergent pair is `graph/graph.py:43` vs `graph/services.py:31` (`tempdir if NO_PERSIST else resolve_storage_root()`) and `:48` (`PROFILE_SANDBOX if NO_PERSIST else PROFILE_PRODUCTION`), both of which test **`¬NO_PERSIST` only**. Distinguishing input: `PERSIST_STATE` unset **and** `NO_PERSIST` unset → `graph.py` returns `MemorySaver` (ephemeral graph) while `services.py` resolves the real `<storage root>` under `PROFILE_PRODUCTION` and `cli/run.py:226` passes `persist_enabled=True`, so a CLI run writes a log file and durable artifacts while graph state is not crash-resumable (F-CRP-09's truth-table row 1). `mcp/server.py:243-244` masks this on the MCP path by forcing `PERSIST_STATE=1`. The target has one truth table; the W6 phase note publishes it and a test asserts every consumer reports the same mode. | W6 |
| **On-disk storage layout v2** | `storage` | **Preserved.** No extraction PR may change it; any change is a separate B7 PR with a version bump. The three rows below are the *only* write-side changes in the program; each is additive and is called out here rather than left to the generic shim row. | — |
| **Stored `artifact_type` labels** | `storage` (writer), `filmspec` (vocabulary) | **Changed once, additively (D11).** W4 fixes `graph/nodes/_context._ARTIFACT_TYPE_BY_CLASS`, which today silently falls back to `script`, and adds the 8 missing `ArtifactType` names. New writes carry the correct label; **data already written with `artifact_type=script` is not migrated** — the payload model is unchanged and no reader keys on the label (the one unverified hypothesis of `audit/07` §7, retained as a caveat). A `git revert` of W4 restores the old writer and leaves already-corrected labels on disk, which old readers accept because the field is a `str`-valued enum member. | W4, owner `storage` |
| **`budget` durable document** (spend/ledger document under the project) | `budget` (N+I), `storage` (R) | **New representation (additive).** Today `BudgetState` is constructed in `mcp/tools/planning.py:33` and never persisted, and `SpendRecord` has **zero writers** (F-BUD-03). W8 introduces one durable document written through `storage`. Nothing reads it before W8, so it is not a migration; a `git revert` of W8 stops the writer and leaves an orphaned document that no pre-W8 code path reads. | W8, owner `budget` |
| **`kb_context_ref` in artifact meta** | `kb` (N+I), `storage` (R of the bytes) | **Changed from 1/12 to 12/12 write paths (additive field).** Today only 1 of 12 artifact-write paths stamps the ref (F-KBCTX-02/03); the target makes every `storage` write path pass one. Artifacts written before the wave simply lack the key, and every reader already tolerates absence (`artifacts/store.py:538` reads it with a default), so this is read-compatible in both directions; a `git revert` restores 11 non-stamping paths without invalidating the stamped artifacts. | W5/W8, owner `storage` with `kb` supplying the ref |
| `langgraph.json` graph path | `studio` (entry), `orchestration` (target) | **Explicitly broken (path only).** `./src/film_pipeline/graph/graph.py:graph` → `./src/film_pipeline/orchestration/graph.py:graph`. One-line config edit; the graph *object* name (`graph`) and the `film_pipeline` graph id are unchanged. | W11 |
| Internal Python import paths | all | **Broken with one-program shims** (`# SHIM(W<n>)`), removed under guard in W12. Not externally visible: the distribution name, entry points and module public contracts are unchanged. | W1–W12 |
| `devharness` packaging | `devharness` | **Explicitly broken (wheel contents).** The package leaves the shipped wheel; `import film_pipeline.testing` (dev-only usage) becomes `import film_pipeline.devharness` for source checkouts. No product code path imports it (measured). | W12 (or W0 if relocation is chosen) |

**Per-module compatibility summary.** `mcp`: preserves shapes, changes who
computes them. `orchestration`: preserves channels/reducers; adds one typed
channel; unifies writers; keeps its own SQLite checkpointer outside the
`checkpoints` contract. `checkpoints`: preserves the protocol, types the
payload. `storage`: preserves the layout and the public store API; adds
`storage.contract`; and is the writer for the three additive write-side changes
(`artifact_type` labels, the budget document, `kb_context_ref`), each of which a
single `git revert` reverses in the *reader* direction because every one is
additive or has a tolerant default. `generation`/`budget`: preserves ledger
payloads; changes one
default ceiling. `governance`/`validation`/`post`: internal only. `studio`:
changes persistence precedence deliberately. `devharness`: changes wheel
membership and import name. `filmspec`/`schemas`/`kb`/`config`/`constraints`/
`providers`/`projects`/`operations`: internal only, with public re-exports during
the shim window.

---

## 9. Where the design could be wrong

An honest attack on this specific design, with the trigger that would make me
change it. This section is B8; the blocking objections below are resolved or the
design is amended.

**9.1 Over-modularization is the most likely failure.** 20 modules for ~40k LOC
is +3 against 17 packages, but three of the 20 are small: `budget` (a cap and a
spend list), `projects` (a map and an active id), `constraints` (3 files). A
module earns its place by **owning N+I, or owning R, or being a declared
composition root / harness** (`00` §1.2 defines ownership as all three of N, I and
R; adversarial O-18 correctly observed that five modules cannot satisfy that
literally, so the rule is stated in the form the design actually uses, and each
exemption is named rather than left implicit):

| Module | What it claims | Exemption it uses |
|---|---|---|
| `filmspec` | N for every vocabulary + I for the pure predicates (`is_blocking`, `next_phase`, `gate_for`) | **no R** — a vocabulary module deliberately holds no state |
| `config` | N+I for profile merge order and config validity | **no R** — resolves values into other modules' records |
| `constraints` | N+I for the extraction grammar and keyword tables | **no R** — produces a `schemas` payload consumed by `orchestration` |
| `governance` | N+I for advancement policy, gate identity and the action vocabulary | **no R** — its statelessness is the anti-cycle argument (A §10.6) |
| `devharness` | a declared contract of test doubles | **owns nothing normative** — a harness, exempt by D6 |

A module must also be consumed by more than one module; if its only consumer is one
module, it should be merged (proposal A's own rule, and the reason it rejected a
`media` module in §10.4). Concrete abandon triggers, each written as a
**measurable** condition — the two former triggers that named a measurement nobody
can take or an action the law forbids are corrected per adversarial O-08/O-09:
- `budget` — survives iff `authorize_spend` is called from ≥2 target modules
  (`generation` authorizes before dispatch; `governance` consumes the verdict)
  **or** the cap gates ≥2 domains (F-BUD-02's 8 HEAD sites span graph, router and
  operator gates). The former second disjunct, "`record_spend` has ≥2 call sites
  (generation + post/assembly)", is deleted: `record_spend` has **0** call sites at
  HEAD (F-BUD-03 is exactly that defect) and `post → budget` is forbidden by §4.3,
  so the condition could never be evaluated and its named second caller was
  architecturally impossible. If neither disjunct holds after W8, merge into
  `generation` and keep `cap_for` as a pure function over the project record.
- `projects` — if after W10 the active pointer has exactly one writer and no
  second consumer beyond `mcp.resolve`, merge into **`operations`**, not `studio`
  (adversarial O-09: the pointer's writer is `operations` at L10 and L6/§4.3 make
  `studio` inbound-empty, so "merge into `studio`" prescribed an impossible edit).
  Today the pointer has multiple writing call paths (70 `active_project|set_active`
  hits), so the trigger is not met.
- `governance` — if after W9 `evaluate_phase` has exactly one caller
  (`orchestration`) and `operations` reads decisions only through the graph, the
  separate module is still justified by the review-package/actions surface, but
  if that surface also collapses, `governance` merges into `validation`
  (audit 08's position becomes right, and I would say so).
- `constraints` — the reverse risk: merging a **clean** module into a
  debt-laden one (`agents`) to save a module is not a simplification.

**9.2 Migration cost is real and concentrated in one place.** The service
locator is 112 references across 43 files with a deliberate monkeypatch contract
(`mcp/tools/__init__.py:15-21`); the private-import migration is 72 files;
`tests/` is another 180 files. If W10 is attempted first or as one commit, it
will either red the suite for a week or leave a permanent shim that preserves the
locator — which is why W0–W9 exist and why the renames are W12. **Biggest single
risk of the whole program: W10.** The mitigation is ordering, not cleverness. If
W10 cannot be split into ≤1-day green commits, the correct move is to split it
again (per tool group), not to add a flag.

**9.3 Contract leakage can reappear in three specific places.** (a) `governance`
returning a `PhaseDecision` that `mcp` reads directly would let tool handlers
start reproducing gate logic; the guard is that `mcp` imports `governance` for
*types* only and all evaluation goes through `operations`. (b)
`storage.contract` growing past its six declared names into a second store; the
guard is the six-name public contract plus the L0–L1 import rule. (c) `filmspec`
becoming a dumping ground for anything constant-shaped; the guard is the
`owns` declaration in its `CONTRACT` plus the duplicate-literal sweeps. If any of
these holds after two waves, the module boundary is nominal and must be re-cut.

**9.4 The law could be green and meaningless (guard theatre).** O1's mirror
guard compares a symbol to itself if a mirror re-exports the canonical constant;
O4's agreement passes vacuously if a reader returns an empty set. Mitigations are
B's anti-vacuity set (canonical ≠ mirror, both registries non-trivial, source
tree >200 files, manifest is a leaf, `as_vocabulary()` raising on
non-vocabularies) plus the mutation canary. The cautionary precedent is real:
`tests/unit/__pycache__/test_guard_canary.cpython-312-pytest-9.1.1.pyc` exists
with no source — a guard canary was written, deleted, and left no trace but its
bytecode.

**9.5 Static sweeps miss dynamic construction.** `write_sites()` and
`_policy_reads()` see string literals; `state[key] = value` with a computed key,
`os.getenv(name)` with a built name, or `globals()["PHASE_ORDER"]` are invisible.
The mitigation is to declare the dynamic case as a reader annotation (B §10.3);
the residual risk is a contributor who evades the sweep *and* does not annotate.
I accept this risk because the alternative (runtime instrumentation of every
channel write) is far more expensive and would not cover O1/O4.

**9.6 The design assumes the MCP surface must not be re-implemented above
`operations`.** If a future product requirement genuinely needs a tool whose
logic does not belong in a use case (e.g. a pure read that must bypass the use
case layer for latency), the `mcp → operations` law will be inconvenient. The
escape is a declared edge plus an exemption row — visible, named and removable —
not a new unrestricted module. If that happens more than twice, the boundary
between `mcp` and `operations` is wrong and should be re-cut, not waived.

**9.7 What would make me abandon a module split entirely.** Any one of: (i) the
extracted module cannot declare a public contract that its consumers can use
without an upward import; (ii) after extraction the module's guard test passes
when the ownership content is deleted (the guard is theatre); (iii) the
extraction changes a persisted representation and therefore cannot be reverted
by a single `git revert`; (iv) the module has one caller and no independent
invariant. For `budget`, `projects`, and `governance` these triggers are written
as concrete observations in §9.1, not as principles.

**9.8 What this design deliberately does not do.** No `common`/`utils` module; **no
single "middleware" module owning the cross-cutting mechanisms** (the strongest
alternative shape a reviewer will raise — refuted with measurements in **D13**:
442 cross-package imports across 144 of 281 files, a forced L0/L1 position where
it can own no behaviour or state, and all 180 test modules needing rewrite — more
churn than extracting the modules); no
per-phase `graph/nodes` split; no `media`/`compositor` extraction (single caller,
shared private layout constants — A §10.4); no per-layer DTO mapping (three
shapes with mappers between would triple maintenance and make the B7 freeze
harder to read); no runtime feature flags; no new dependency.

---

## 10. Conformance to bar B

| Bar | Requirement | Where satisfied |
|---|---|---|
| **B1** | One responsibility per module, one sentence, explicit non-goals | §3 — every module has a "Responsibility" sentence and a "Non-goals" list; enforced for the 17 current packages by `test_responsibility_is_one_sentence_with_explicit_non_goals` (D2) |
| **B2** | Declared contract: public API, owned invariants, owned state | §3 — every module states "Public contract", "Owns (N/I/R)", "State"; **§3.21** corrects every `public_api` against the measured cross-module import set (adversarial O-05: 126 names measured, 53 additions); `ModuleContract.public_api`/`.owns` + `test_public_api_names_exist` + `STATE_CHANNELS` (D2) |
| **B3** | Allowed/forbidden edges written down, acyclic, mechanically checkable | §4 — L1–L8, the layer table, the full allowed-edge matrix (§4.3), the **normative FES scope definition and its derived count of 13** (§4.6, §4.6.1), the acyclicity proof (§4.4, confirmed at `fb85baa` by adversarial FA-1), and the guard mapping (§4.5, with the missing L1-direction guard named); the count is guard-derived, not hand-maintained (D2, D12) |
| **B4** | Every source file assigned, or "stays"/"deleted"; no orphans | §6 — package rules for all 17 packages with measured counts, file-level enumeration for the split packages, non-source dispositions, 22 spot-checks; the corrected total is exactly 281, independently reproduced with 0 orphans by adversarial FA-3 |
| **B5** | Independently shippable phases ordered by real dependency; each leaves `make ci-check` green | §2.5 — W0–W12, each one branch, each green, each shrinking the ledger; ordering is the topological order of §4.3; extraction PRs never change a persisted representation, **and §8 now carries a row for each of the three additive write-side changes, stating what a single `git revert` does and does not undo** (adversarial O-14) |
| **B6** | At least one regression guard per extracted module | §3 module entries plus the guard column in §5 and the per-module guard plan in §2.2 (A §9's table adopted, re-pointed at target module names) |
| **B7** | MCP response shapes, LangGraph state schema, checkpoint/resume protocol preserved or the break listed and documented | §8 — a row per contract and per module, with the wave that ships each deliberate break; the persistence-precedence row now cites the **real** divergent sites (adversarial O-13), the MCP freeze test is a W0 plan rather than an existing guarantee (O-22), the two checkpoint mechanisms are separated (O-06), and the three persisted-representation changes each have a row (O-14) |
| **B8** | Adversarial validation of the design | §9 — over-modularization, migration cost, contract leakage, guard theatre, dynamic-sweep blindness, module-abandon triggers; §2 records the rejected alternative for every reconciliation call; **`reviews/adversarial-architecture.md` is answered objection-by-objection in "Revision 2"**, and the verifier-surfaced scope ambiguity (V3) is resolved by an explicit definition rather than a number (§4.6.1, D12) |
| **B9** | Every module justified by ≥1 audit finding or existing contract; no speculative abstraction | §3 "Evidence" line per module, citing F-ids and enola measurements; **§2.8 now consults the declared source of truth (`documentation/architecture-blueprint.md`) and records what L0–L12 supersedes** (adversarial O-19); §9.8 lists what was deliberately *not* abstracted |

---

## Appendix — reproduce commands

All at `fb85baa`; the venv is `.venv/`.

```bash
# 1. File counts (281 total; 17 packages + 1 top-level __init__.py)
find src/film_pipeline -name '*.py' -not -path '*__pycache__*' | wc -l        # 281
for d in src/film_pipeline/*/; do find "$d" -name '*.py' -not -path '*__pycache__*' | wc -l; done

# 2. Split-package structure
ls src/film_pipeline/graph/nodes/*.py | wc -l            # 17
ls src/film_pipeline/graph/*.py | wc -l                  # 12
ls src/film_pipeline/graph/orchestrator_validators/*.py | wc -l  # 5
ls src/film_pipeline/app/services/*.py | wc -l           # 7
ls src/film_pipeline/generation/compositor/*.py | wc -l  # 5

# 3. Artifact-kind ground truth (R1): prints 47 45 39
.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "src")
from film_pipeline.artifacts.registry import REGISTRY
from film_pipeline.schemas._base import ArtifactType
enum = {e.value for e in ArtifactType}; exact = set(REGISTRY._exact)
print(len(exact), len(enum), len(exact & enum))
print("registry-only", sorted(exact - enum)); print("enum-only", sorted(enum - exact))
PY

# 4. Service locator footprint (112 / 43)
grep -rn "_services" src/film_pipeline --include=*.py | wc -l
grep -rln "_services" src/film_pipeline --include=*.py | wc -l

# 5. Policy and literal duplication
grep -rn 'FILM_PIPELINE_NO_PERSIST' src/film_pipeline --include=*.py | wc -l   # 7
grep -rn 'severity") == "blocking"\|"severity": "blocking"' src/film_pipeline --include=*.py | wc -l  # 48

# 6. Private imports (72 non-schemas files reach schemas._base)
grep -rln 'schemas._base' src/film_pipeline --include=*.py | grep -v '/schemas/' | wc -l

# 7. C2 edges
grep -rn 'from film_pipeline.mcp' src/film_pipeline/app --include=*.py
grep -rn 'from film_pipeline.app' src/film_pipeline/mcp --include=*.py

# 8. Cycles (independent of this document)
enola --generate docs/modular-architecture/enola-config.yaml
enola --explain  mcp-arch.yaml

# 9. Revision 2 (adversarial review) — the FES count of 13
#    Maps every file to its §6 target module (so the graph/ and app/ splits are
#    visible), collects cross-target-module import pairs, and prints the pairs whose
#    destination is absent from the source's §4.3 may_import set.
#    Expected: 58 distinct edges, 13 forbidden:
#      config->providers (2), governance->orchestration (5), operations->studio (4),
#      mcp->{agents 7, checkpoints 3, config 6, generation 23, kb 5, orchestration 7,
#            post 2, providers 6, storage 7, studio 5}
UV_CACHE_DIR="$PWD/.uv-cache" uv run python - <<'PY'
import ast, pathlib
from collections import defaultdict
SRC = pathlib.Path("src/film_pipeline")
GOV = {"_action_routing", "consistency", "scope_contract"}          # files that move to `governance`
ALLOWED = {  # §4.3, transposed to "what may this module import" for the 20 target modules
 "filmspec": set(), "schemas": {"filmspec"},
 "config": {"filmspec","schemas"}, "kb": {"filmspec","schemas"}, "constraints": {"filmspec","schemas"},
 "storage": {"filmspec","schemas"}, "providers": {"filmspec","schemas"},
 "projects": {"filmspec","schemas","storage"}, "checkpoints": {"filmspec","schemas","storage"},
 "agents": {"filmspec","schemas","providers"}, "budget": {"filmspec","schemas","storage"},
 "validation": {"filmspec","schemas","storage"},
 "generation": {"filmspec","schemas","storage","providers","budget"},
 "post": {"filmspec","schemas","storage","validation"},
 "governance": {"filmspec","schemas","storage","budget","validation"},
 "orchestration": {"filmspec","schemas","config","kb","constraints","storage","providers","agents",
                   "budget","validation","generation","post","governance"},
 "operations": {"filmspec","schemas","config","kb","constraints","storage","providers","projects",
                "checkpoints","agents","budget","validation","generation","post","governance","orchestration"},
 "mcp": {"filmspec","schemas","projects","governance","validation","operations"},
 "studio": {"filmspec","schemas","config","kb","constraints","storage","providers","projects","checkpoints",
            "agents","budget","validation","generation","post","governance","orchestration","operations","mcp"},
 "devharness": {"filmspec","schemas","storage","providers","checkpoints","agents"}}
PKG = {"validation":"validation","agents":"agents","providers":"providers","generation":"generation",
       "checkpoints":"checkpoints","post":"post","kb":"kb","config":"config","constraints":"constraints","mcp":"mcp"}
def ftarget(rel):
    p = rel.parts[0] if len(rel.parts) > 1 else "studio"
    if p == "schemas": return "schemas"
    if p == "artifacts": return "storage"
    if p == "graph": return "governance" if (len(rel.parts)>1 and (rel.parts[1].removesuffix(".py") in GOV
                      or rel.parts[1]=="orchestrator_validators")) else "orchestration"
    if p == "review": return "governance"
    if p == "app": return "operations" if len(rel.parts)>1 and rel.parts[1]=="services" else "studio"
    if p in ("cli",): return "studio"
    if p == "testing": return "devharness"
    return PKG.get(p, "??"+p)
def dtarget(dotted):
    rest = dotted.split(".")[1:]
    if not rest: return "studio"
    q = rest[0]
    if q == "schemas": return "schemas"
    if q == "artifacts": return "storage"
    if q == "graph": return "governance" if len(rest)>1 and (rest[1] in GOV or rest[1]=="orchestrator_validators") else "orchestration"
    if q == "review": return "governance"
    if q == "app": return "operations" if len(rest)>1 and rest[1]=="services" else "studio"
    if q == "cli": return "studio"
    if q == "testing": return "devharness"
    return PKG.get(q, "??"+q)
def resolve(rel, level, module):
    parts = ["film_pipeline", *rel.parts[:-1]]
    if level > 1: parts = parts[: -(level-1)]
    if module: parts += module.split(".")
    return ".".join(parts)
edges = defaultdict(set)
for f in sorted(SRC.rglob("*.py")):
    rel = f.relative_to(SRC); src = ftarget(rel)
    for n in ast.walk(ast.parse(f.read_text(), filename=str(f))):
        if isinstance(n, ast.ImportFrom):
            if n.level: dotted = resolve(rel, n.level, n.module)
            elif n.module and n.module.startswith("film_pipeline"): dotted = n.module
            else: continue
            dst = dtarget(dotted)
            if dst != src: edges[(src, dst)].add(f"{rel}:{n.lineno}")
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name.startswith("film_pipeline"):
                    dst = dtarget(a.name)
                    if dst != src: edges[(src, dst)].add(f"{rel}:{n.lineno}")
forb = sorted((s,t,v) for (s,t),v in edges.items() if t not in ALLOWED[s])
print("edges", len(edges), "forbidden", len(forb))
for s,t,v in forb: print(f"  {s} -> {t}  [{len(v)} sites]")
PY

# 10. Revision 2 — the measured public_api surface (§3.21)
#     Reproduce from item 9's script with three edits, all of which matter to the count:
#       (a) inside the `ast.ImportFrom` branch, replace the edge update with a name update —
#             if any(p.startswith("_") for p in dotted.split(".")[2:]): continue
#             for a in n.names:
#                 if not a.name.startswith("_"): names[(dst, a.name)].add(src)
#           the first line is what excludes `schemas._base` and `app._persistence`;
#       (b) drop the bare `ast.Import` branch entirely (module-level imports carry no name);
#       (c) `names` is a dict keyed by (dst_module, name).
#     Expected: len(names) == 223 (module,name) pairs; 126 outside `schemas`, 97 for it;
#     per-module: agents 13, checkpoints 4, config 8, constraints 2, generation 13,
#     governance 12, kb 6, mcp 1, operations 2, orchestration 15, post 2, providers 17,
#     schemas 97, storage 17, studio 5, validation 9. Verified: the modified script prints
#     `names 223 non-schemas 126` and exactly that per-module histogram.
#     The §3.21 disposition of each name (declared / add / via-operations / renamed /
#     deleted) is the 53 additions listed in the §3.21 table; each is a one-line diff
#     against the module entry it corrects.

# 11. Revision 2 — the persistence divergence (O-13): the cited pair is identical
sed -n '43p'      src/film_pipeline/graph/graph.py        # PERSIST_STATE AND NOT NO_PERSIST
sed -n '51,52p'   src/film_pipeline/app/_persistence.py   # same formula  -> not a divergence
sed -n '31p;48p'  src/film_pipeline/graph/services.py     # NOT NO_PERSIST only -> real divergence
sed -n '226p'     src/film_pipeline/cli/run.py            # NOT NO_PERSIST -> real divergence
grep -rn 'FILM_PIPELINE_NO_PERSIST\|FILM_PIPELINE_PERSIST_STATE' src/film_pipeline --include=*.py

# 12. The law, once W0 exists
uv run --python 3.12 --group dev pytest tests/architecture -q --no-cov
make arch-check
make ci-check
```

**Not verified in this document** (stated, per `00` §1.6.6): the W1–W12
migrations were not executed; the wave table is derived from the observed edge
graph and the audit findings. The `enola-intent.yaml` derivation is planned, not
built. The optional per-package mypy `disallow_any_explicit` tightening (B §5.7)
was not applied. `tach`/`import-linter` availability was not re-checked
(proposal B's §2.1 measured them absent offline).
