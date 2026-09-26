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

## Python Standards

- Add type hints to public functions, methods, and module-level constants.
- Prefer `pathlib.Path` over stringly-typed filesystem paths.
- Use Pydantic v2 for all schemas (never raw dicts across boundaries).
- Use `dataclass(frozen=True)` for internal value objects when Pydantic is overkill.
- Raise specific exceptions with actionable messages.
- Keep modules focused and side effects minimal.

## Sub-Package Boundaries

The packages under `src/film_pipeline/` map to implementation phases and to the
ownership boundaries in `docs/modular-architecture/03-target-architecture.md`.
`orchestration` and `mcp` may import across all sub-packages; domain modules must
not import each other directly — they communicate through `storage` (the owner
of artifact identity and layout).

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
| `budget` | — | Spend cap policy and refusal |
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
