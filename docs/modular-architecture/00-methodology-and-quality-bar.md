# 00 — Methodology, Ownership Model, and Quality Bars

Status: **authoritative spec for this program.** Every audit and architecture
artifact in `docs/modular-architecture/` must conform to the definitions and
bars below. Where this file and an individual document disagree, this file wins
until it is amended here.

Program: **modularization of `film-pipeline-langgraph`** — converting a
17-sub-package Python codebase (~281 source files, ~40k LOC source, ~180 test
files) from implicit, spread-out ownership into explicit modules with one owner
per concern and mechanically enforced boundaries.

This is a **first-principles audit**. The prior storage rewrite
(`documentation/storage-upgrade-plan.md`) is treated as *one resolved data point
and a source of guard-test precedent* — it is **not** the template, and its
choices are not assumed correct for other concerns.

---

## 1. Definitions (normative)

### 1.1 Concern

A **concern** is one rule, one piece of state, one policy, or one lifecycle that
the system must get right. Examples: "the ordered set of pipeline phases and
their transitions", "how a storage root is resolved", "which agent may execute a
phase", "what makes a validation report blocked vs passed", "how a generation
job's lifecycle advances".

### 1.2 Owner

A module **owns** a concern when it is the *single* place that satisfies all
three of:

- **N — Normative model:** defines the types, enums, constants, and grammar of
  the concern.
- **I — Invariant enforcement:** validates and enforces the concern's rules
  (transitions, checks, refusal paths).
- **R — Representation authority:** is the only writer of the concern's
  persisted or observable representation.

All other modules **consume** the concern through the owner's declared public
contract. A consumer must not re-derive N, re-implement I, or write R.

### 1.3 Distributed ownership (a.k.a. an ownership seam)

A concern has **distributed ownership** when two or more modules independently
satisfy part of N, I, or R, such that:

- changing the concern requires coordinated edits in more than one module, **and**
- a partial edit can pass every existing test while producing divergent
  behavior.

Distributed ownership is not the same as *incompleteness* (a feature that is
unfinished) or *duplication of convenience* (a trivial local helper with no
normative content). Findings must be one of these, not the others.

### 1.4 Ownership debt taxonomy (classify every finding)

| Class | Name | Meaning |
|---|---|---|
| **O1** | Duplicated normative model | The same enum/map/constant/grammar is defined in 2+ modules. |
| **O2** | Duplicated invariant enforcement | The same validation/refusal/transition is implemented in 2+ paths. |
| **O3** | Split state authority | One logical state is written by 2+ modules with no single writer. |
| **O4** | Parallel registries | 2+ registries must agree but nothing enforces agreement. |
| **O5** | Policy-by-branch | One policy decision is re-derived at N call sites (env flag, `if`, default). |
| **O6** | Parallel lifecycle | One lifecycle has two implementations (e.g. graph path vs MCP path). |
| **O7** | Leaked internals | A module reaches into another's private state, so ownership is nominal. |
| **O8** | Missing contract | A seam has no typed interface; callers pass raw dicts/strings and re-parse. |

### 1.5 Severity rubric (apply uniformly)

- **Impact (1–5):** 5 = wrong behavior reaches a human deliverable or corrupts
  durable data; 3 = wrong internal behavior, recoverable; 1 = cosmetic.
- **Drift likelihood (1–5):** 5 = no test can fail when one site changes;
  1 = a test already pins the agreement.
- **Score = Impact × Drift likelihood.** Critical ≥ 16, High 9–15, Medium 4–8,
  Low 1–3.
- **The band is a function of the score — arithmetic wins over a band word.**
  A finding whose recorded band disagrees with its recorded score is a
  self-contradiction, not a judgement call. A verifier who disagrees with a band
  changes the *axes* (impact, drift) and the recomputed score determines the band;
  it does not relabel the band while leaving a score that says otherwise. This rule
  was added in round 3, when a mechanical check over all 189 findings
  (`band == band(impact × drift)`) found exactly five violations —
  `F-CRP-05` (3×3=9 recorded Medium), `F-CRP-13` (4×4=16 recorded High),
  `F-BOUNDARY-02/03/06` (3×3=9 recorded Medium) — all of them a verifier's band
  word disagreeing with its own recomputed score. A conforming corpus makes this
  invariant checkable by a guard test, which is the point.
- **Extraction cost:** S (≤1 day-equivalent), M (2–4), L (5+). Cost never
  lowers severity; it only orders the roadmap.

### 1.6 Evidence rules (non-negotiable)

1. Every claim cites `path:line` anchors. `line` must point at the defining or
   enforcing line, not the file in general.
2. Every anchor is backed by a short verbatim quote (≤ 3 lines). Do not
   paraphrase code as if it were a quote.
3. Every finding states a **drift proof**: either (a) an *existing* divergence
   between two owners, with both sites cited, or (b) a *mutation scenario* —
   "change X at `A:l`; `B:l` keeps the old value and no test fails because Z".
   A finding without a drift proof is a hypothesis, not a finding.
4. Counts must be mechanically reproducible. "N sites" means a grep/command that
   a verifier can re-run; record the exact command in the finding.
5. Never claim a file's contents without reading it in this program. Line
   numbers drift; verify at HEAD and record the commit.
6. If a claim cannot be verified, delete it or downgrade it to an explicitly
   labeled "unverified hypothesis" section — never leave it among findings.
7. **Every printed command reproduces its stated output at the revision the file
   is written against.** A `Reproduce:` block whose real output differs from the
   number in the finding text is a defect, not a rounding difference. This rule
   was added after an adversarial evidence replay found reproduce blocks whose
   own commands printed 323 where the finding claimed 359, and 6 where the
   finding claimed 3.
   *Convention for indented fences:* a ```` ``` ```` block nested inside a list
   item is indented with it. Before running one, de-indent the body to the
   fence's own indentation — that is what a markdown renderer does, and running
   the raw text produces a spurious `IndentationError`. 12 of the 14 audit files
   indent at least one fence this way; the replay handled it and so should a
   reader.
8. **Pin the revision.** Any document that depends on another states the revision
   it read (line count plus sha256, or the commit). Line numbers drift; a claim
   about "the current file" with no pin is unverifiable. When the object changes,
   the dependent document is re-derived, not hand-patched — and the revision
   history stays in the file rather than being overwritten.

### 1.8 Adversarial review protocol (added after round 3)

Independent verification of individual findings (A6) is not the same as
independent attack on the *whole* deliverable. The program therefore requires a
second, adversarial pass, and it must be structured so that a pass cannot quietly
agree with the thing it is reviewing:

1. **Four independent passes, each briefed to falsify**: coverage (does the audit
   actually cover the normative surface?), evidence (do the reproduce commands
   reproduce?), architecture (is the target law and its enforcement mechanism
   buildable?), and roadmap (is each phase independently shippable?).
2. **Each pass works from its own enumeration**, not from the deliverable's
   claims. A coverage pass that reads the audit's own file list has already
   inherited its blind spots. The successful round-3 coverage pass built its own
   AST inventory of normative *values* — enums, `Literal`s, string-keyed
   registries, numeric policy constants, path and URL literals — and compared
   that against the deliverable's text. Enumerating symbols is insufficient:
   the seams that were missed were bare `str` fields and second alias tables,
   which no symbol grep surfaces.
3. **A finding of the pass is a hypothesis until it is reproduced by the
   orchestrator or a verifier.** Passes are expected to get some things wrong;
   round 3's passes each had claims corrected or refuted by the authors, and that
   is a healthy result rather than a failure.
4. **Each pass pins the revision of every file it cites**, and is re-run when its
   object changes. Round 3's roadmap pass spent its first revision on a roadmap
   that had already been rewritten; the re-run is kept alongside the original.
5. **A capstone verdict** (`reviews/bar-conformance.md`) states, per bar item,
   whether the bar is met, by whom it was demonstrated, and what remains. It runs
   last, over the closed deliverable, and its author must not have written any of
   the documents it judges.

### 1.7 Finding record format (one block per finding)

```markdown
### F-<DOMAIN>-<NN> — <title>
- **Class:** O<1..8>
- **Severity:** <Critical|High|Medium|Low> (impact <1-5> × drift <1-5> = <score>)
- **Concern:** <one sentence>
- **De-facto owners:**
  - `path:line` — <what it defines/enforces> — `"quote"`
  - `path:line` — <...> — `"quote"`
- **Drift proof:** <existing divergence | mutation scenario with expected silent failure>
- **Reproduce:** `<exact grep/command>`
- **Blast radius:** <modules affected; user-visible consequence>
- **Candidate owner module:** <name> — <one-line responsibility>
- **Extraction sketch:** <moves/renames, public contract, guard test>
- **Prior art:** <existing doc that already noted it | "new">
```

---

## 2. Quality bar A — the audit

The audit is **done** only when all of the following hold and are demonstrated,
not asserted:

- **A1 Coverage.** Every source package (`agents`, `app`, `artifacts`,
  `checkpoints`, `cli`, `config`, `constraints`, `generation`, `graph`, `kb`,
  `mcp`, `post`, `providers`, `review`, `schemas`, `testing`, `validation`),
  plus `profiles/`, `scripts/`, `tests/`, and every entry point (`cli.run.main`,
  `mcp.server.main`, `app.product_gate.main`, `langgraph.json`) is mapped to at
  least one concern and explicitly marked either "has findings" or "clean, no
  distributed ownership found". No package may be silently omitted.
- **A2 Evidence.** Every finding satisfies §1.6; zero unsourced claims.
- **A3 Drift proof.** Every finding has one (§1.6.3), including the "clean"
  claims where the proof is a guard test that already pins the concern.
- **A4 Classification.** Every finding names its O-class, affected modules, and
  de-facto owners.
- **A5 If a concern is single-owner already**, it is recorded in the ownership
  map as such, with the guard test that pins it (or the absence noted as a gap).
- **A6 Independent verification.** Every finding block is re-checked by a second
  agent that did not write it, against §1.6. The verifier records
  CONFIRMED / DOWNGRADED / REJECTED per finding with its own evidence. No
  finding ships on the author's word alone.
- **A7 No silent duplication of prior audits.** Findings already present in
  `documentation/audit-findings.md`, `documentation/reviews/*.md`, or
  `docs/clean-code-refactor/*.md` must cite that prior art and state what is new
  (still present at HEAD? worsened? already fixed?).
- **A8 Actionability.** Every finding nominates a candidate owner module and a
  guard test that would fail if the seam regressed.
- **A9 Adversarial coverage, not just verification.** The audit has survived an
  independent pass (§1.8) that enumerated the normative surface *itself* — values,
  vocabularies, registries and numeric policy, not the audit's own file list — and
  that pass's surviving holes have been closed as findings. Verification (A6) shows
  a finding is real; A9 is what shows the *set* of findings is complete. Added after
  round 3, where A1–A8 were all arguably met and 13 real seams were still missing.

## 3. Quality bar B — the target architecture

- **B1 One responsibility per module**, stated in one sentence, with explicit
  non-goals ("does not …").
- **B2 Declared contract.** Each module states its public API surface, the
  invariants it owns, and the state it owns.
- **B3 Dependency law.** Allowed and forbidden edges are written down; the
  resulting module graph is acyclic; the law is mechanically checkable (import
  test or linter), not merely documented.
- **B4 Conformance map.** Every existing source file is assigned to a target
  module, or explicitly marked "stays where it is" / "deleted". No orphan files.
- **B5 Independently shippable phases.** The extraction roadmap is ordered by
  real dependency, and each phase leaves `make ci-check` green on its own.
- **B6 Guard tests.** Each extracted module gets at least one test that fails if
  its ownership regresses (duplicate-normative-model test, single-writer test,
  registry-agreement invariant, or boundary/import test).
- **B7 Contract compatibility.** MCP response shapes, the LangGraph state
  schema, and the checkpoint/resume protocol are either preserved or the
  breaking change is listed and documented in the phase that ships it.
- **B8 Adversarial validation.** A senior architect adversary attacks the design
  (over-modularization, cycle risk, contract leakage, migration risk, cost vs
  benefit). All blocking objections are resolved or the design is amended.
- **B9 Concreteness.** Every module is justified by ≥1 audit finding or an
  existing contract. No "future flexibility" layers, no speculative
  abstractions.

---

## 4. Program process

1. **Recon (this session).** Establish repo facts, ownership taxonomy, cluster
   map.
2. **Audit fan-out.** One auditor per domain cluster, writing
   `docs/modular-architecture/audit/<NN>-<cluster>.md` under bar A.
3. **Independent architecture.** Senior-architect subagents design a target
   architecture from first principles without reading the audit, so the design
   is not anchored by the findings.
4. **Verification fan-out.** A different agent per audit file re-checks every
   finding under §1.6; results in
   `docs/modular-architecture/reviews/verify-<NN>.md`.
5. **Fix loop.** Rejected/downgraded findings are corrected in the audit files
   until a verification pass returns zero unresolved disputes.
6. **Reconciliation.** Audit findings + independent architecture proposals are
   merged into `01`–`05` with explicit reconciliation of disagreements.
7. **Adversarial review.** Architect adversary + evidence adversary review the
   whole deliverable; blocking findings fixed; review record written.
8. **Loop ends** only when bars A and B are demonstrably met and no reviewer
   returns a blocking finding.

## 5. Recorded baseline facts

- Repo: `${REPO_ROOT}`, branch
  `modular-app`, starting commit `fb85baa` (merge of the storage upgrade).
- Source: 281 `.py` files / 40,369 lines under `src/film_pipeline/`.
- Tests: 180 `.py` files / 32,183 lines under `tests/`.
- Largest source files: `artifacts/store.py` (834), `graph/nodes/visual.py`
  (632), `graph/orchestrator_state.py` (537), `app/_graph_exec.py` (484),
  `app/services/operator.py` (483).
- Gates: `make ci-check` = ruff format + lint, mypy strict, pytest ≥90% coverage
  (`--cov-fail-under=90`), `uv build`.
- Entry points: `film_pipeline.cli.run:main`, `film_pipeline.mcp.server:main`,
  `film_pipeline.app.product_gate:main`, `langgraph.json →
  graph/graph.py:graph`.
- Cross-package imports at HEAD (top): `schemas` 323, `graph` 131, `agents` 86,
  `mcp` 66, `providers` 52, `generation` 52, `artifacts` 51, `validation` 43,
  `app` 40.
- `AGENTS.md` declares: "`graph` and `mcp` may import across all sub-packages;
  domain modules must not import each other directly — they communicate through
  `artifacts`." **Whether that law is actually enforced or true is itself an
  audit question.**
