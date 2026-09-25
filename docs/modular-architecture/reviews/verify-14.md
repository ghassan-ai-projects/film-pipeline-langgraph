# Verify 14 — adversarial verification of `audit/14-module-boundaries-and-import-law.md`

- Verifier: independent agent (A6), did not write the audit.
- Verified at: `modular-app` = `fb85baa0e6b769b709791a96a89980089304bf13`, clean tree.
- Method: independent `ast`-based package/module graph (own script, not the file's numbers),
  `grep` re-runs of every stated `Reproduce` command, source reads of every cited anchor,
  independent Tarjan SCC at package **and** directory-module granularity, and a prior-art
  sweep of `documentation/reviews/`, `documentation/architecture-review.md`,
  `documentation/roadmap-execution/` and `docs/modular-architecture/enola-architecture-facts.md`.

## 0. Import matrix — reproduced independently

My AST scan (one count per `ImportFrom` statement, `Import` statements counted separately,
relative imports resolved to absolute; the audit's matrix is `ImportFrom`-only) reproduces
the audit's §2 matrix **exactly** on every one of the 16 rows and 17 columns:

- `agents` {schemas 27, providers 4}; `app` {schemas 7, graph 16, agents 1, mcp 1, providers 4,
  generation 2, artifacts 8, validation 1, config 2, kb 3, checkpoints 4}; `artifacts` {schemas 16};
  `checkpoints` {schemas 5}; `cli` {graph 4, app 4, artifacts 1}; `config` {providers 2};
  `constraints` {schemas 6}; `generation` {schemas 8, providers 4, artifacts 7};
  `graph` {schemas 50, agents 9, providers 2, generation 4, artifacts 3, validation 14, kb 2,
  constraints 2}; `kb` {schemas 7}; `mcp` {schemas 73, graph 7, agents 7, providers 6,
  generation 23, artifacts 7, validation 7, app 7, config 6, kb 5, checkpoints 3, post 2, review 1};
  `post` {schemas 10, validation 1}; `providers` {schemas 8}; `review` {schemas 3};
  `testing` {artifacts 2, checkpoints 1, providers 1}; `validation` {schemas 32}.
- **No disagreeing row.** The `graph` 131, `agents` 86, `providers` 52, `generation` 52,
  `artifacts` 51, `validation` 43, `app` 40 column totals also reproduce exactly once `ast.Import`
  nodes are excluded (which is what the audit did — including them inflates `graph` to 134 and
  `app` to 41).
- Two cosmetic matrix defects: the row set has **16** rows, not 17 — the `schemas` source row
  (all dots) is omitted — and the file's §2 table has no self-row, which §1.6.4 does not forbid.

**Count defect (confirmed):** the prose total "`schemas` **323** imports" is **322** under any
consistent AST convention. The extra hit is a *docstring line*:
`src/film_pipeline/schemas/__init__.py:5` — ``so callers can ``from film_pipeline.schemas import ProjectProfile``.``
reproduces the grep number but is not an import:
```
python3 -c "import ast,os;print(sum(1 for dp,_,fs in os.walk('src/film_pipeline') for f in fs if f.endswith('.py') for n in ast.walk(ast.parse(open(os.path.join(dp,f)).read())) if isinstance(n,ast.ImportFrom) and 'schemas' in (n.module or '')))"
# 322   (grep -ro 'from film_pipeline\.schemas[._a-zA-Z]* import' src/film_pipeline --include='*.py' | wc -l  ->  323)
```
`323` is the figure propagated into `enola-architecture-facts.md:79` as "the manual count of 323
cross-package imports" — the same doc computes `schemas` fan-in as 509, so the two numbers are not
the same measure. Correct prose: **322 import statements (252 cross-package + 70 intra-package)**.

## 1. Per-finding verdicts

### F-BOUNDARY-01 — declared domain-isolation law violated / unenforced / partly wrong
- **Verdict: CONFIRMED (substance), with two numeric corrections.**
- Counter-evidence run: all three `Reproduce` greps return the claimed edges. I independently
  enumerate **8** forbidden domain→domain edges, not 7:
  `agents→providers` (4), `config→providers` (2), `generation→providers` (4),
  `generation→artifacts` (7), `post→validation` (1), `testing→artifacts` (2),
  `testing→checkpoints` (1), `testing→providers` (1).
  The finding's own parenthetical lists **eight** items while the sentence says "seven distinct
  forbidden edges"; consequently "a contributor adding an eighth forbidden edge" should be "a
  ninth". (The prior art `documentation/architecture-review.md:73-76` enumerated only five.)
- Anchors all resolve with exact quotes (`AGENTS.md:51`, `agents/runner.py:17`,
  `config/profile_resolver.py:204`, `generation/executor.py:29`, `generation/ledger.py:14`,
  `post/delivery_packaging_agent.py:190`, `testing/storage.py:11-12`, `graph/nodes/qc.py:265,352`;
  `graph→validation` = 14 confirmed).
- §1 claims confirmed: 17 packages, not 12 (`ls src/film_pipeline`); no import check in
  `pyproject.toml`, `Makefile`, `.pre-commit-config.yaml`, or any repo YAML/TOML/INI
  (`grep -rniE "import-linter|importlinter|pytest-arch|archon|tach|grimp"` → empty).
- Class: **O7/O8 supported; O5 is a stretch** — no policy is "re-derived at N call sites"; the
  policy is declared once and ignored (O8/missing contract fits).
- **Recomputed severity:** the printed "High (4 × 4 = **16**)" is internally inconsistent — §1.5
  makes 16 **Critical**. No wrong deliverable/durable-data behavior is demonstrated (latent
  architectural risk), so impact 3, drift 4 (nothing pins it) → **High (3 × 4 = 12)**.

### F-BOUNDARY-02 — `schemas._base` private module used by 72 non-schema files
- **Verdict: DOWNGRADED.**
- Both stated counts reproduce **exactly** and match AST truth:
  `grep -rl "schemas._base" ... | wc -l` → **109**; `| grep -vc '^src/film_pipeline/schemas/'` → **72**
  (37 inside + 72 outside = 109).
- O7 **confirmed** — but the listed "O1 (duplicated normative model)" is **REJECTED**: no second
  definition of any enum/constant is shown, and §1.4 O1 requires one.
- The finding understates the real evidence it does have. I found a genuine **existing divergence**
  (§1.6.2a): of the 16 distinct names outsiders import from `schemas._base`, **two are not bound in
  `schemas/__init__.py` at all** — `TRANSITION_TYPES` and `LEGACY_TRANSITION_ALIASES`
  (e.g. `post/transition_agent.py:8`). The declared façade is genuinely incomplete, not merely
  at risk. This should replace the hedge "duplicated normative model risk".
- The drift claim "a symbol removed from `_base` breaks 72 files that no façade check would have
  flagged" is **wrong as a silent-failure argument**: mypy strict + normal import resolution make a
  rename/removal loud immediately. Only *façade completeness* drifts silently.
- **Recomputed severity:** claimed "High (4 × 4 = 16)" (again Critical by §1.5, not High).
  With O1 rejected and no user-visible impact: impact 3 × drift 3 = **Medium (9)**.
  Count correction: 323 → 322 as above; §3's "29 imports" for `schemas/__init__.py` is defensible
  (29 `ImportFrom` nodes incl. `from __future__`, of which 28 target `schemas.*`).

### F-BOUNDARY-03 — `app` ↔ `mcp` import cycle
- **Verdict: CONFIRMED at package granularity; scope materially understated (see §2).**
- All anchors resolve exactly (`app/product_gate.py:17`; `mcp/server.py:164,241,248`;
  `mcp/tools/__init__.py:22`). Both `Reproduce` greps run; `grep -rn "from film_pipeline.app" src/film_pipeline/mcp`
  returns **7** sites — the finding lists 5 and omits `mcp/server.py:249`
  (`app.logging_setup.configure_logging`) and `mcp/tools/generation/planning.py:136-137`
  (`app.services.errors`, `app.services.operator`).
- Independent package-level Tarjan SCC = `[['app','mcp']]`, so "one 2-cycle" is correct **only at
  package granularity** — which the Coverage row does not say.
- Lazy imports: confirmed function-body, so mypy/pytest do not flag the cycle.
- **Recomputed severity:** Medium (3 × 3 = 9) stands; matches prior art B-F7
  (`documentation/architecture-review.md:110`).
- A7: prior art is **mischaracterized** — see §3.

### F-BOUNDARY-04 — enforcement is two bespoke AST suites; no global law
- **Verdict: CONFIRMED (core), with severity/scope corrections.**
- `ls tests/unit/*/test_*boundar*.py tests/unit/*/test_*architect*.py` returns exactly the two
  files named; the five named storage tests exist at lines 56/72/84/101/132. No `import-linter`,
  `tach`, `archon`, `pytest-arch` or `grimp` section appears anywhere in the repo
  (`mcp-arch.yaml` at repo root is only the enola ignore config, not a boundary tool).
- The mutation scenario is sound: `tests/unit/post/` has no boundary test and ruff has no
  import-rule selection (`select = ["E","F","W","I","B","C4","UP","SIM","PIE","PTH","RET","ARG","RUF"]`).
- Scope correction: "No other package has a boundary test" is true for **import** boundaries, but
  `tests/unit/config/test_config_contract.py` and `tests/unit/graph/test_channel_registry.py` are
  additional hand-written **AST contract guards** (config-leaf reads; orchestrator↔registry
  parity) — so the general phrase "the only two mechanically guarded boundaries" is overbroad.
- **Recomputed severity:** printed "High (4 × 4 = **16**)" is Critical by §1.5; recompute
  impact 3 × drift 4 = **High (3 × 4 = 12)**.

### F-BOUNDARY-05 — cross-package private-module / private-symbol imports
- **Verdict: CONFIRMED (offenders real) but the stated `Reproduce` command is BROKEN and the
  offender list is incomplete.**
- The command:
  ```
  grep -rn "^from film_pipeline\.[a-z_]*\._" src/film_pipeline --include='*.py' \
    | grep -vE "^src/film_pipeline/([a-z_]+)/.*from film_pipeline\.\1\."
  ```
  is anchored at `^from`, so it only sees **column-0** imports. It returns 42 lines, **all of them
  `schemas._base`** — it finds **neither** of the two offenders the finding cites, because both are
  indented (`mcp/server.py:248`, `config/profile_resolver.py:204`). §1.6.4 fails: a verifier cannot
  reproduce the finding with the stated command.
- Correct AST enumeration (any indentation, `import` and `from` forms), cross-package only:
  - private **modules**: 107 sites — 105 are `schemas._base` (the F-BOUNDARY-02 systemic case) and
    only **one** non-schema site, `mcp/server.py:248 → app._persistence`;
  - private **symbols**: **3** sites — `config/profile_resolver.py:204` (`_env_var_for`, cited),
    plus **two the finding misses**: `app/_graph_exec.py:319` (`_run_validators`) and
    `app/_graph_exec.py:449` (`_PHASE_NODES`), both reaching into `graph` internals.
- A7: "Prior art: new" is **false** — `documentation/reviews/arch-lens-boundaries.md:43` already
  records `config/profile_resolver.py:204` importing `_env_var_for` as Finding 2 (severity medium),
  with a target design that makes the symbol public.
- **Recomputed severity:** Medium (3 × 3 = 9) for the cited anchors; including the two missed
  `app→graph` private-symbol reach-ins raises drift to 4 → High (12) once corrected.

### F-BOUNDARY-06 — `film_pipeline.testing` ships and is a cross-domain consumer
- **Verdict: CONFIRMED, with two citation corrections.**
- Anchors resolve (`testing/storage.py:11-12`, `testing/in_memory_git.py:29`,
  `testing/scenarios.py:5`, `app/mock_responses.py:1`); the `Reproduce` mock-class grep returns 4
  classes across `providers/` and `testing/`, confirming three homes for test doubles.
  The guard test's docstring confirms the historical leak; `packages = ["src/film_pipeline"]` is at
  `pyproject.toml:59`.
- Correction 1: the quoted `[tool.coverage.run] omit = ["*/testing/*"]` is **truncated** — the real
  list has two entries (`pyproject.toml:95-98`): `*/testing/*` **and**
  `src/film_pipeline/mcp/tools/__init__.py`. "Only `src` *package* excluded" is true; the quote as
  written is not the config.
- Correction 2: the referenced `docs/modular-architecture/04-extraction-roadmap.md` **does not
  exist** at HEAD (only `design/proposal-{A,B}-*.md` and `reconciliation-notes.md`).
- **Recomputed severity:** Medium (3 × 3 = 9) stands.

## 2. Missed in scope

1. **Cycle detection is materially incomplete — the headline omission.** The audit reports one
   2-cycle. The deterministic sibling snapshot at the *same commit* (`enola-out/receipt.json`:
   `commit fb85baa…, dirty:false`) reports **5** cycles, and my independent directory-module Tarjan
   reproduces exactly the same 5 with the same members:
   - C1 `agents/prompt_templates ↔ agents/prompt_templates/defaults`
   - C2 `app → app/services → mcp → mcp/tools → mcp/tools/bibles → mcp/tools/generation →
     mcp/tools/reference_generation → app` (**7 modules**)
   - C3 `graph ↔ graph/nodes ↔ graph/orchestrator_validators ↔ graph/subgraphs` (**4 modules**)
   - C4 `providers ↔ providers/adapters`
   - C5 `schemas ↔ schemas/registries`
   The audit's own sibling `enola-architecture-facts.md:51-63` states C2 "corroborates `audit/14`
   F-BOUNDARY-03, and it is larger than the 2-package view", and calls C2/C3 the design-level cycles
   the target architecture must resolve. Because the audit presents only the 2-package view, its
   proposed fix (split `app.product_gate` / add `app.contracts`) is not shown to break the actual
   7-module cycle, and C3 (graph-internal, design-level) is absent entirely. C1/C4/C5 are cheap
   façade-re-export cycles and belong in scope for a boundary audit. **Worth recording: yes —
   material ×4 (three unrecorded cycles plus an understated root cycle).**
2. **Two O7 offenders omitted** from F-BOUNDARY-05: `app/_graph_exec.py:319` (`_run_validators`)
   and `:449` (`_PHASE_NODES`).
3. **Adjacent mechanical contract guards** not mentioned in "Clean concerns":
   `tests/unit/config/test_config_contract.py` and `tests/unit/graph/test_channel_registry.py`.
4. **Dangling reference** to a non-existent `04-extraction-roadmap.md` (F-BOUNDARY-06).

## 3. Disputes requiring the author to fix

1. **F-BOUNDARY-05 `Reproduce` command does not reproduce its own anchors** (§1.6.4). Replace the
   `^from`-anchored grep with an AST or indentation-agnostic scan, and add the two missed
   `app→graph` private-symbol sites.
2. **A7 prior-art violations (three findings claim novelty that prior art already records):**
   - F-BOUNDARY-03: "the concrete 2-cycle is new" — false. `arch-lens-boundaries.md:215-226`
     (Finding 7) and `documentation/architecture-review.md:78,110` (B-F7) already state
     "exactly one package-level cycle `{app ↔ mcp}`, held together by lazy imports".
   - F-BOUNDARY-05: "Prior art: new" — false; `config/profile_resolver.py:204 → _env_var_for` is
     `arch-lens-boundaries.md:43`.
   - F-BOUNDARY-04: "The *global* absence is new" — false; `arch-lens-boundaries.md:269` and
     `roadmap-execution/phase-03-law-and-docs-truth-plan.md:28` already propose the CI edge scan
     (`scripts/check_boundaries.py`) that F-BOUNDARY-04 nominates.
   - F-BOUNDARY-01: prior art "does not measure the matrix or the violations" is inaccurate —
     `architecture-review.md:73-76` enumerates five of the violating edges and Finding 8 measures
     the 12-vs-19 package miscount. What is genuinely new is the full 17×17 matrix.
3. **Arithmetic vs §1.5:** F-BOUNDARY-01, -02 and -04 each print "(impact 4 × drift 4 = 16)" beside
   the label **High**; §1.5 makes 16 **Critical**. Either the inputs or the label is wrong on all
   three; they cannot both stand.
4. **Numeric corrections:** "seven distinct forbidden edges" → **eight** (and "adding an eighth" →
   "a ninth"); "`schemas` 323 imports" → **322**.
5. **F-BOUNDARY-02 class:** drop O1 (no duplicated definition is shown); keep O7/O8 and replace the
   hedge with the real existing divergence (`TRANSITION_TYPES`, `LEGACY_TRANSITION_ALIASES` bound
   only in `_base`, absent from `schemas/__init__.py`).
6. **Cycle section:** state the granularity ("package-level") in the Coverage row, and add the five
   module-level cycles (or explicitly defer them to the design phase with a pointer to
   `enola-architecture-facts.md`).
7. **F-BOUNDARY-06:** quote the full coverage `omit` list and fix the dangling
   `04-extraction-roadmap.md` reference.

## 4. "Clean concerns" check

- The two guard suites are the only **import-boundary** guards; their descriptions are accurate
  (storage: 5 AST rules at lines 56/72/84/101/132 plus a façade-API assertion at line 144, plus two
  behavioral tests the table does not mention; graph: AST sweep incl. lazy imports + fresh-interpreter
  subprocess check, `test_startup_boundaries.py:26,45,68`).
- The sentence "These are the **only** two mechanically guarded boundaries in the repo" is
  **overbroad** as written; scope it to import/module boundaries, or add the two adjacent AST
  contract guards named in §2.3.

## Overall verdict

Substantively sound and mechanically re-runnable for the import matrix (reproduced exactly) and the
`schemas._base` counts (109/72), but it under-reports cycles by 4, fails §1.6.4 on F-BOUNDARY-05's
own reproduce command, misstates the forbidden-edge count (7 vs 8) and the schemas total (323 vs
322), mislabels three 16-scores as High when §1.5 makes them Critical, and claims novelty for three
findings already recorded in prior art — fix those seven disputes and the file meets bar A.

---

# Re-verification (post-fix)

Re-verified against the updated `audit/14-module-boundaries-and-import-law.md` (411 lines) at the
same commit `fb85baa`. Method identical to above: source reads of every changed anchor, re-runs of
every changed `Reproduce` command, and re-checks of each disputed claim.

## Per-item verdicts

1. **F-BOUNDARY-01 — RESOLVED.** Line 128 now says **eight** and lists exactly the eight edges I
   enumerated; line 132-133 says "the ninth"; severity is now "High (impact 3 × drift 4 = 12)"
   (line 115) with the §1.5 rationale; prior art (line 153-157) credits
   `documentation/architecture-review.md:73-76` (verified: those lines enumerate five of the
   edges) and states what is new (the full 17×17 matrix + 8-edge count).
2. **F-BOUNDARY-02 — PARTIALLY RESOLVED.** O1 is removed/rejected (line 160-161); severity is
   Medium (3×3=9) (line 162); the withdrawn silent-rename argument is replaced by the real
   existing divergence — `TRANSITION_TYPES` and `LEGACY_TRANSITION_ALIASES` bound in `_base` but
   not in `schemas/__init__.py` (line 177-184) — which I independently confirmed. **Unresolved
   residual:** the correction was applied only in §2 (line 64). §1 **line 34 still says
   `schemas` (323 imports)**, contradicting line 64's 322 in the same file.
3. **F-BOUNDARY-03 — RESOLVED.** `mcp/server.py:249` and `mcp/tools/generation/planning.py:136-137`
   added (lines 212-213, both verified to exist); the 7-member directory-module view is stated
   (lines 215-217) and tabled in §2a; prior art (line 236-239) now credits
   `arch-lens-boundaries.md:215-226` and `architecture-review.md:78,110`.
4. **F-BOUNDARY-04 — RESOLVED.** Severity now High (3×4=12) (line 244); the two extra AST contract
   guards are acknowledged and correctly scoped as non-import boundaries (lines 255-259); prior art
   (line 282-286) now credits `arch-lens-boundaries.md:269` and
   `roadmap-execution/phase-03-law-and-docs-truth-plan.md:28`. Minor overstatement: "(verify-14
   confirmed both.)" (line 243) — my earlier pass confirmed this finding's substance but never
   examined its O5 half.
5. **F-BOUNDARY-05 — RESOLVED.** The new indentation-agnostic AST script (lines 314-331)
   **re-runs to exactly 107 private-module and 3 private-symbol sites** (matches my independent
   enumeration; the 3 sites are `config/profile_resolver.py:204`, `app/_graph_exec.py:319` `:449`
   — both previously-missed sites are now cited at lines 299-302); severity raised to High (3×4=12)
   (line 290); prior art corrected (lines 341-344). Residual nit: Blast radius (line 335) still
   reads "`schemas`, `app`→`mcp`, `providers`→`config`" and was not updated to include the new
   `app`→`graph` reach-ins.
6. **F-BOUNDARY-06 — PARTIALLY RESOLVED.** The two-entry coverage omit list is now correct —
   `*/testing/*` **and** `src/film_pipeline/mcp/tools/__init__.py` (`pyproject.toml:95-98`), lines
   362-365. **Unresolved residual:** my dispute 7 also asked for the dangling
   `04-extraction-roadmap.md` reference to be fixed; line 377 still cites it, and the file remains
   absent at HEAD.
7. **"Clean concerns" four guards — RESOLVED.** The table now lists four rows (lines 389-392) and
   scopes the claim correctly: two import boundaries (`artifacts`, `graph`) + two contract guards
   (`config`, `graph`). I re-confirmed exhaustiveness: exactly four test files under `tests/` call
   `ast.parse` — the four listed.
8. **New §2a (five cycles + fix caveat) — RESOLVED.** C1–C5 match enola and my independent Tarjan
   at `fb85baa`; the consequence paragraph (lines 89-92) correctly states that splitting
   `app.product_gate` / adding `app.contracts` is not shown to break the 7-module C2 cycle and does
   not address C3. **New defect introduced:** line 92 also points at
   `03-target-architecture.md` §"cycle-breaking", which **does not exist** at HEAD (the
   `reconciliation-notes.md` R2 pointer is valid and does cover the 5 cycles).

## Still inconsistent (not blocking)

- **Line 34 vs line 64:** `323` vs `322` in the same document.
- **Coverage row line 15** still says "measured — one 2-cycle" with no package-granularity
  qualifier and no pointer to §2a; row 17 still says "two bespoke suites only" while the Clean
  concerns table now says four guards (defensible if read as *import* boundaries, but unqualified).
- **Two dangling doc references:** `04-extraction-roadmap.md` (line 377) and
  `03-target-architecture.md` (line 92).
- **Two stale Blast-radius lines:** F-BOUNDARY-02 line 190-192 still reasons about "two definitions
  drift" (the rejected O1 framing); F-BOUNDARY-05 line 335 omits `app`→`graph`.
- **One overstated attribution:** F-BOUNDARY-04 line 243 "(verify-14 confirmed both.)".

## Bar A status for audit 14

- **A2 (evidence):** holds for every finding's anchors and reproduce commands as re-run, with one
  residual: the stale `323` at line 34 is a wrong count still printed in the file (line 64 is the
  correct 322). Fix that one number to clear A2 fully.
- **A3 (drift proof):** **holds** — F-BOUNDARY-02 now cites an existing divergence and F-BOUNDARY-05
  a mutation scenario; both verified.
- **A7 (prior art):** **now holds** — all four prior-art claims (F-01, F-03, F-04, F-05) are
  correctly attributed to `architecture-review.md` and `arch-lens-boundaries.md`, with what is new
  stated.

**Bottom line:** 6 of 8 disputed items RESOLVED, 2 PARTIALLY RESOLVED (F-02: line-34 `323`;
F-06: dangling `04-extraction-roadmap.md`), none NOT RESOLVED; remaining issues are editorial
(one stale count, two dangling references, two stale blast-radius lines), not evidence or
classification failures.
