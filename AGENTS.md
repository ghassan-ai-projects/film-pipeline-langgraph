# AGENTS.md — Film Pipeline LangGraph

Canonical instructions for coding agents in this repository. Read this file first, then load only the context files needed for the task.

## Purpose

This repository implements the **LangGraph Film Studio** described in `documentation/`. It is an MCP-first, LangGraph-orchestrated, multi-agent system that drives a film from idea through delivery with mandatory human review gates.

The architectural source of truth is `documentation/architecture-blueprint.md`. Hard acceptance and product-completion standards are in `documentation/product-completion/` and `documentation/product-completion-plan/`. Read those before writing code.

## Engineering Priorities

1. Correctness and safety.
2. Simplicity of design and implementation.
3. Test evidence for changed behavior.
4. Consistency with the docs and existing patterns.
5. Speed of implementation.

If two options both work, choose the one that is easier to read, easier to test, and easier for the next agent to extend.

## Plan First

Before editing code, plan: files to touch, why each is needed, validation commands, risks.

A plan is a starting point, not a deliverable — see
[Run the command; do not narrate it](#run-the-command-do-not-narrate-it). State the
next action and take it in the same turn.

## Build, Test, and Lint

Primary commands:

```bash
make setup          # uv sync --group dev
make hooks          # install pre-commit hooks
make ci-check       # format-check + lint + typecheck + test + build
make test-unit      # unit tests only
make test-integration
make test-e2e
```

The full pipeline runs `make ci-check`: ruff format, ruff lint, mypy strict, pytest with 90% coverage, and `uv build`.

**Type-check `src` and `tests` together.** The pre-push hook runs mypy over both
(505 files), while `mypy src` alone checks 297. The narrower command cannot see a
break confined to test imports: a test that imports a name a package stopped
re-exporting still *passes at runtime* (Python resolves the attribute), and only
`attr-defined` over `tests` reports it. This cost a rejected push — run
`uv run mypy src tests` before pushing, not `mypy src`.

### Architecture gate (Enola)

`make ci-check` does **not** grade architecture. Enola is a second, required gate,
and it must stay at exit 0 with no new *blocking* finding:

```bash
enola check --baseline=docs/modular-architecture/enola-out \
            docs/modular-architecture/enola-config.yaml
```

Rules for using it:

- **Run it before every commit, and again on the committed tree.** A clean
  `make ci-check` says nothing about structure.
- **Use the docs-local baseline.** `docs/modular-architecture/enola-out` plus
  `docs/modular-architecture/enola-config.yaml` is the comparable pair. The root
  `.enola` baseline is stale; a check against it is not a pass.
- **Check the baseline's age before believing a FAIL.** `enola check` grades the
  working tree against a *pinned snapshot*, so a snapshot older than the branch it
  grades reports the branch's own renames as regressions. This actually happened:
  a 2026-09-25 baseline still held 703 facts for `src/film_pipeline/app`, 935 for
  `graph`, and 396 for `artifacts` — packages renamed away on this branch — and it
  promoted a pre-existing `agents <-> agents/prompt_templates` cycle to
  "regression" the moment an unrelated back-edge was removed. Regenerate from
  **clean** HEAD (`enola --generate`, then `enola baseline clear` + `baseline pin`)
  and confirm the fresh snapshot holds 0 facts for packages that no longer exist.
  Never fix a FAIL by editing a filter or threshold; fix the baseline's currency.
- **A freshly pinned baseline cannot catch new cycles.** It grades against a
  snapshot, not the working tree: with the baseline regenerated from the current
  commit, an injected `schemas -> orchestration` back-edge still exits 0. That check
  lives in `tests/unit/architecture/test_package_acyclicity.py` — keep it, and keep
  it scoped to cycles. It is not a duplicate of this gate.
- **Exit codes:** `0` clean, `1` regression (policy violated), `2` error
  (gate could not run — no baseline, bad flag), `3` declined (baseline not
  comparable). Anything but `0` must be resolved or explained, not ignored.
- **`cycles` is the failure policy** (`--fail-on` defaults to it). Heuristic
  explainers — `god-class`, `hotspots`, `complexity-outliers`, `dependency-depth`,
  `exported-surface` — report as *advisory* and do not fail the gate. Treat them
  as claims to verify against the source, not as verdicts.
- **Never lower the count by changing an Enola filter or threshold.** The count is
  evidence, not a target.
- A refactor is expected to *change* coupling, so "new coupling" output is normal.
  What must not appear is a new cycle or a violated policy.

Record the Enola result next to `make ci-check` for every migration slice.

### Dependency boundaries — what is enforced, and what is not

`tests/unit/architecture/test_boundary_law.py` guards the boundaries this project
has **adopted**:

- **No cross-package private reach-in** — importing another package's
  underscore-prefixed module. Guarded, with existing debt in
  `KNOWN_PRIVATE_REACH_INS`, ratcheted down.
- **No external call to the runtime's private persist/audit methods.**
  `StudioRuntime` exposes `persist_project_state` and `record_audit`; the
  underscore spellings survive only as in-package aliases for the 24 call sites
  inside `studio`, where a private name is legitimate. `RuntimePort` declares the
  public names. `KNOWN_MIRRORED_PRIVATE_CALLS` is now **empty** — all 8 outside
  call sites were routed — and the guard counts the *private* spellings only, so
  it does not flag the correct public usage. If an external private call
  reappears, record it in that table rather than allowing it silently.

**What is deliberately NOT enforced.** `docs/modular-architecture/03-target-architecture.md`
declares a per-package "Allowed outbound" set, but its own header calls it a
**superseded proposal**, and `06-independent-review-and-decision.md` §4 decided:

> This is an ownership map, **not a prohibition on ordinary package imports**.
> Tighten a dependency only when it removes a proven cycle or unsafe reach-in.

Do **not** treat `03`'s layer law as a burndown target, and do not contort code to
satisfy it. The guard reports that law's census as an observation only.

An earlier round of this program did exactly the wrong thing here: it graded every
import against `03` and froze 73 edges as debt to eliminate, which is enforcing a
rejected proposal. That was re-scoped. **Read `06` before `03`** — which
`docs/modular-architecture/README.md` already instructs.

## Python Standards

- Add type hints to public functions, methods, and module-level constants.
- Prefer `pathlib.Path` over stringly-typed filesystem paths.
- Use Pydantic v2 for all schemas (never raw dicts across boundaries).
- Use `dataclass(frozen=True)` for internal value objects when Pydantic is overkill.
- Raise specific exceptions with actionable messages.
- Keep modules focused and side effects minimal.

## Sub-Package Boundaries

The packages under `src/film_pipeline/` map to implementation phases and to the
ownership map in `06-independent-review-and-decision.md` §4. That review decided
the package layout is an **ownership map, not an import prohibition** — see
"Dependency boundaries" above for what is actually enforced.

The migration is complete: every package under `src/film_pipeline/` is a target
module that owns its concern. The pre-migration names — `artifacts`, `graph`,
`review`, `testing`, and `app` — have been removed along with their
compatibility shims, and all consumers import the owners directly.

| Sub-package | Phase | Notes |
|-------------|-------|-------|
| `filmspec` | — | Pure vocabulary: phases, enums, transitions, generation-request codes |
| `config` | 03 — Profile loading, merging | |
| `schemas` | 01 — Pydantic contracts | |
| `storage` | 04 — Artifact identity, layout, versioning | Owner of `ProjectStorage`, `ArtifactStore`, `KindSpec` |
| `orchestration` | 05 — LangGraph state machine | Formerly `graph` |
| `kb` | 06 — Knowledge base | |
| `agents` | 07 — Agent registry, prompts | |
| `governance` | 08 — Review packages, gate law | Formerly `review` plus the graph gate modules |
| `validation` | 09 — Validator registry | |
| `providers` | 10, 13 — Provider adapters | |
| `checkpoints` | 11 — Checkpoints, resume | |
| `mcp` | 02 — MCP tool surface | |
| `post` | 14 — Post-production | |
| `operations` | — | Operator use cases, view models, runtime ports |
| `projects` | — | Project identity, classification, resolution |
| `studio` | — | Composition root; formerly `app` |
| `devharness` | — | Test doubles and scenarios; formerly `testing` |

The former owners map to their replacements as follows: `artifacts` ->
`storage`, `graph` -> `orchestration` (with the gate law and validators in
`governance`), `review` -> `governance`, `testing` -> `devharness`, and `app` ->
`studio` (with the operator surface in `operations`). Import the new names.

## Decomposition Rules

These are the working conclusions of the modularization program
(`docs/modular-architecture/`), learned by measurement rather than by taste.
Apply them before proposing a new module or a new abstraction.

**Size alone is not a seam.** The discriminating number is the *public surface*
and the number of *concerns*, not the line count:

| Class | Lines | Public methods | Concerns | Verdict |
|---|---:|---:|---:|---|
| `StudioRuntime` | 370 | 27 | 5 | split |
| `ArtifactStore` | 605 | 15 | 1 | leave alone |

Judge a file by "how many reasons does it have to change", not by how long it is.

**A symbol used many times is a symptom, not a fix.** High fan-in on one method
means consumers are reaching past the abstraction to something that belongs at a
higher level. The repair is to move the concern *up* to its owner and delete the
callers' re-derivation — not to add a wrapper that keeps every call site.

**One policy reimplemented at N sites is the real defect.** When the same rule,
guard, or message appears at many call sites, the fix is to find the owner that
should already express it and route every site through it. Precedents: the
`issues` reducer (13 wholesale writes reduced to one code path) and the
active-project precondition (46 handler-level guards deleted in favour of one
check at dispatch). Look for the existing mechanism before inventing a new one —
a purpose-built API that its own intended callers bypass is a common finding.

**Delete dead branches and divergent duplicates; do not preserve them.**
Guards that no production path can reach, tables whose rows name ids that do not
exist, and second implementations of one lifecycle should be removed. Deleting
them is part of the change, not a follow-up.

**Distinguish duplication of convenience from distributed ownership.** Two
modules happening to write the same value the same way is *not* an ownership
seam; a partial edit there produces an obvious bug, not divergent behaviour.
Under `docs/modular-architecture/00-methodology-and-quality-bar.md` §1.3, only
the latter justifies a boundary.

### Verify claims against the tree, not against the log or a docstring

Two failures in the cost-removal round came from trusting a written claim:

- A commit titled "remove provider pricing" never touched `providers/pricing.py`.
  `git show --name-status` on it lists no such path; the module was still present
  and still imported by five modules. **A commit message is a claim, not
  evidence.** Before building on a prior slice, `grep` the working tree.
- A docstring asserted a state channel was "always the default" because its only
  writer had been deleted. It had a second, dormant writer (`state.setdefault` in
  `ensure_orchestrator_state`, plus a registered `OrchChannelSpec` noted "dormant
  writer"). **"Nothing writes it" is a claim about every writer, including dormant
  ones.** A dormant writer is still a writer.
- A guard's commit message claimed it "recovers 77 silently-skipped names" and
  blamed an AST parser limitation. The real cause was **scan scope**: the helper
  walked top-level directories only, so the package in question was never read at
  all by either the old or the new parser. **Name the mechanism you measured, not
  the one you assumed** — two of this program's commit messages have now asserted
  what their own diffs did not deliver.

**A guard must be audited as adversarially as the code it guards.** The surface
ratchet above passed every gate and still had three defects: a *newly added* package
escaped the count guards entirely (they `continue` on a missing baseline row), the
comparisons used `>` so a shrinking or renamed public surface passed silently, and
the guard-the-guard asserted container sizes rather than set equality. Ask of every
guard: what change would make this pass while being wrong? Then inject it.

**A green suite is evidence about the paths it covers, and silence about the rest.**
When you change a function's contract, `grep` its callers and ask which of them
exercise the branch you changed. A refactor once made `configured_runtime_root()`
return `Path | None`; one call site still passed the result to `configure_logging`,
which silently installs **no** file handler when given `None` — so the persistent MCP
server lost its log. **Every gate stayed green**, because the single test covering
that path set the environment variable explicitly and therefore took a different
branch. One call site, and it was the one no test reached.

Corollary, learned the hard way in both directions: when a deletion removes an
item from a rule set, a test asserting `count(...) == N` was derived from that set
and must be re-measured, not edited to match. And when a sweep finds a suspicious
name — `FailureClass.BUDGET` looked like a cost leftover — check the owner before
deleting it; it was a live member of the failure taxonomy.

### How to run a decomposition slice

1. Make the **narrowest change a test can falsify**, then let the failures
   enumerate the work. The `extra="forbid"` experiment is the model: 96 failures
   became the work list.
2. Prefer moves that **preserve behaviour and public signatures** over redesigns;
   move *consumers* before moving *structure*.
3. Keep the change **shippable on its own** — one slice, one commit, green gates.
4. **Record the measurement, not the argument.** A count you can re-run beats a
   design document. Four documents were written on state ownership before one
   round of code plus tests produced more than all of them.
5. State what the slice does **not** establish. Analysis that is not backed by a
   falsifiable check is the less productive half.

### Run the command; do not narrate it

A plan is not progress. The state-typing migration is the cautionary example: it
was estimated at roughly four rounds and took twelve, because several rounds
ended with a description of the next step instead of its result — "let me look at
`repair_phase_node`", "I'll extract the offender list", "I'll build the exemption
table" — each followed by no tool call. The code that eventually landed was the
same code the earlier rounds had already scoped; only the clock changed.

The cost is not the wasted tokens. A narrated step cannot fail, so it cannot
correct you, and the plan silently outranks the tree. Twice in that program the
narration was *wrong* and only execution revealed it: the assumption that the
graph state was untyped (it was `StudioGraphState` already, wired to
`StateGraph`, with 0 of 47 functions naming it), and an AST classifier asserted
to find mutators that missed nested, transitive and accumulator mutation three
separate times. Both errors survived exactly as long as they went unexecuted.

So:

- **If the next step is a command, run it in the same turn you describe it.**
  Reading a file, grepping, running mypy — these are cheap and they are the
  evidence. Prose about them is not.
- **A claim you have not re-measured is a memory, not a fact.** Re-read the
  tree before acting on an earlier round's summary, including your own: a
  subagent's "the baseline is 67 errors" was stale within the hour, and a
  `grep -c "^PASSED"` under `pytest-xdist` interleaves output and miscounts —
  both cost a round.
- **Prefer the smallest command that could prove you wrong.** `pytest -rA` on
  the one failing test beats reasoning about which test fails.
- **When a step stalls twice, change the step, not the wording.** Two rounds
  spent restating the same plan is the signal that the plan is the problem —
  usually it is too large, or it is waiting on a decision that should have been
  made already.

## Operating Rules

- Keep changes scoped to a single phase unless the change spans phases deliberately.
- Do not overwrite user changes. Prefer straightforward solutions over clever ones.
- Do not add abstractions, helpers, or dependencies unless they remove repeated or proven complexity.
- For production-code changes, add or update tests in the same change.
- Keep repo facts in files, not in chat history.

## Forbidden Changes

- No secrets, credentials, or machine-specific private data.
- No network calls in unit tests (mark them `integration` or `e2e`).
- No abstraction layers "for future flexibility" without a current concrete need.
- No bypassing the MCP-first contract to expose internal APIs.
- No paid providers before Phase 12 E2E baseline passes.

## Done

A task is done when: scope is complete with no unrelated refactors, the simplest correct change fits requirements, production changes have tests (90% coverage), `make ci-check` passes, **Enola passes at exit 0**, docs are updated when behavior changes, and secrets are not added.

Before handoff: re-read changed files for vague guidance, confirm tests prove behavior (not just coverage), run both gates, and summarize remaining risks.
