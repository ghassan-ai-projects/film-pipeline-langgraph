# 06 — Independent review and architecture decision

Date: 2026-09-25. Source revision: `fb85baa0e6b769b709791a96a89980089304bf13` (`modular-app`). Scope: review the modular architecture package and verify its decisive claims against repository source. **This document decides a direction; it does not claim that the refactor has shipped.**

## 1. Decision

**Do not execute `03`–`05` as written.** Keep the existing packages as the starting architecture, repair the proven runtime defects first, and enforce a few narrow ownership boundaries where a test can name the observable contract. This preserves the source of truth in `documentation/architecture-blueprint.md`: MCP is the operator boundary, LangGraph owns orchestration, artifacts are typed and versioned, and humans approve major phases. It also respects `documentation/product-completion/00-product-standard.md`: docs and structural elegance cannot substitute for working MCP and recovery behavior.

The original program's audit has substantial value. It discovered real drift in phase policy, validation paths, persistence, and entry points. Its strongest evidence is a reproduction against code or a behavior test. Its weakest step is the jump from that evidence to **20 target modules, one `ModuleContract` per package, and a 21-phase migration**. The review record itself shows that the proposed enforcement and roadmap have unclosed contradictions. More module boundaries would add coordination work while the present user-visible defects remain.

This decision **supersedes the recommendations** in `03-target-architecture.md`, `04-extraction-roadmap.md`, and `05-enforcement-and-guard-tests.md`. Those files remain as reviewed proposals and evidence of rejected tradeoffs. Findings in `audit/` are triage inputs, not a backlog whose 189 rows must all become modules or guard tests.

## 2. What was checked directly

| Observation | Source evidence at the pinned revision | Consequence |
|---|---|---|
| Phase identity has several owners | `schemas/_base.py:77-90` declares `FilmPhase`; `graph/_action_routing.py:18` declares `PHASE_ORDER`; `graph/graph.py:55-68` declares `_PHASE_TO_NODE`; `artifacts/paths.py:14-26` declares directory names, and `:34` accepts an unknown phase as a path segment. | One phase catalog or a small parity guard is justified. A new cross-cutting package is not yet required. |
| Validation has two execution shapes | `graph/nodes/qc.py:417-430` writes `_pending_row_updates`; `:68-80` consumes it to emit a matrix patch. `app/_graph_exec.py:332-345` clears it before `_run_validators` and persists only issues, reports, and consensus ref. | Test and unify the operator-visible validation result before reorganizing packages. The missing matrix patch is a behavior problem. |
| Graph import can perform I/O | `graph/graph.py:201` constructs `graph` on import; `:180-181` requests a default checkpointer; `:40-51` creates a SQLite directory when persistence is enabled. `artifacts/storage.py:72-74` places it under the storage root. | Defer checkpointer creation until explicit bootstrap, preserving the declared `langgraph.json` graph entry or changing it in the same shippable step. `verify-15.md` downgraded the original worst-case severity: do not repeat its unqualified Critical claim. |
| Config is coupled to provider runtime | `config/profile_resolver.py:173-196` builds and registers provider adapters; `:199-215` reads provider credential policy. | Put the side-effecting registration in the composition layer; keep profile normalization in `config`. This requires moving two sites, not only the credential check. |
| MCP is the actual safety boundary | `mcp/server.py:46-67` resolves project and checks confirmation before dispatch; `:164-176` reaches into `app.runtime`; `:234-257` sets persistence and logging policy during server startup. | Keep `MCPServer.call` as the contract under test and inject its runtime dependencies. Avoid wholesale package moves until tool behavior is frozen by tests. |
| The proposed guard can fail its own gate | `pyproject.toml:70-83` sets `--cov-fail-under=90`; `Makefile:47-50` explicitly uses `--no-cov` for subset tests; `Makefile:108` requires the full suite. | Use `--no-cov` for mutation or red/green subset checks, then `make ci-check` for the deliverable. The old roadmap omitted this and its reviewer marked B6 partial. |
| The source package is already substantial | `src/film_pipeline/` contains 281 Python files at this revision, but the existing `artifacts` package already owns the storage layout (`artifacts/storage.py`, `project_storage.py`). | Do not rename `artifacts` to `storage` solely to satisfy a layer diagram. Prove a specific consumer needs a narrower API first. |

The old ledger reports `F-ARTIFACT-13` as a live ownership finding. `reviews/verify-19.md:346-438` **rejects** its drift proof. The old 58-concern and 189-finding totals therefore cannot be used as a verified scope or priority score. `reviews/verify-15.md`–`verify-20.md` also correct severities and mechanisms that the ledger and roadmap have not reconciled. This is a provenance problem, not a reason to silently edit an old snapshot into an invented current total.

## 3. Root cause analysis

**Why did a large module migration appear necessary?** Because several policies are independently repeated. **Why are they repeated?** The system grew by implementation phase: schema, graph, app, MCP, and artifact paths each restated rules they needed. **Why did the repeats survive?** Tests mostly cover local behavior; few check agreement across entry points or persistent representations. **Why did the proposed plan overshoot?** It equated every repeated value or import with a new target-module boundary, then designed a general manifest to police all such boundaries. **Why is that risky here?** The contract surface is still moving, and the proposed manifest/phase sequence has unresolved self-contradictions. The smallest reliable repair is to make a single owner for a concrete rule and prove agreement at the consumer boundary.

The original audit's O1–O8 taxonomy is a discovery vocabulary. It is not a module-count formula. A dead field, a missing feature, and an independently writable invariant need different fixes. A static import guard cannot prove human review, checkpoint restoration, or MCP refusal behavior.

## 4. Target shape

Retain the current package names. Assign **specific authorities**, then change only the consumers that demonstrably duplicate them:

| Concern | Preferred owner within current structure | Required contract | Guard or behavior proof |
|---|---|---|---|
| Phase vocabulary, order, gate and successor policy | `graph` for routing; `schemas.FilmPhase` remains the serialized type | One ordered phase definition consumed by graph routing and validated against `FilmPhase`; storage directory mapping is an explicit projection with no fallback for unknown phases. | A parity test and an MCP approval transition test, including provider-blocked generation. |
| Artifact identity and storage layout | `artifacts` | Typed ref parsing, kind validation, canonical on-disk path and version semantics. | Existing storage boundary tests plus a persisted corpus read/write compatibility test before changing metadata. |
| Resolved profiles | `config` | Pure validated profile data. Provider adapter creation is called by app/runtime composition after resolution. | Profile-stack regression tests and a fake-provider integration test. |
| Graph state and validation handoff | `graph` | Typed or explicitly registered channels for every cross-node value; one QC validation result including matrix patches. | Test graph and MCP `run_validation` produce equivalent issues, refs, and row patches. |
| Runtime, persistence, and checkpoint lifecycle | `app` with `checkpoints` and `artifacts` as explicit dependencies | One startup path and explicit checkpointer construction; root selection and marker checks before writes. | Import-side-effect test, restart/resume test, rollback/version test, and all entry points exercised. |
| Operator contract | `mcp` | Stable tool schemas, confirmation refusal, typed errors, project resolution; implementation delegated to app services. | Transport-level and `MCPServer.call` tests for the same action. |

This is an ownership map, **not a prohibition on ordinary package imports**. Tighten a dependency only when it removes a proven cycle or unsafe reach-in. Package-renaming, `filmspec`, `budget`, `governance`, `operations`, `studio`, and `devharness` are not required as up-front products. They may be justified later by measured coupling after the behavior fixes. Do not add `ModuleContract` to every `__init__.py`: it makes architecture metadata a runtime import dependency, while the most serious current seams require behavior tests. A small AST test is appropriate for a stable, concrete boundary such as prohibiting imports of `schemas._base` from outside `schemas`; it must allow existing debt explicitly and ratchet it down.

## 5. Delivery sequence

Each step is a separate change with its own tests and `make ci-check`. Do not begin a later step merely because a document names a wave. Recheck the target commit and any user changes before editing.

### Step 1 — Prove the operator paths

Freeze response shapes for `approve_phase`, `run_validation`, `request_revision`, and checkpoint rollback at `MCPServer.call` and stdio transport. Exercise the same project through graph and MCP where both paths exist. Record the current divergence as a failing test, including QC row patches and the blocked-generation gate. **Exit:** tests demonstrate current behavior and fail under a targeted mutation; no production change yet.

### Step 2 — Repair state and persistence defects

Make QC patch emission part of the shared validation result, rather than a private scratch key discarded on one path. Resolve the checkpointer only during explicit runtime bootstrap. Keep `langgraph.json` loadable in the same change. Unify persistence-mode and root selection before moving entry-point code. **Exit:** mock MCP workflow, import-side-effect, restart/resume, rollback, and storage-marker tests pass. Audit any on-disk format change with old-data read and rollback fixtures.

### Step 3 — Consolidate high-value vocabularies

Remove the independently writable phase order and unknown-phase path fallback. Reconcile artifact-kind registry, `ArtifactType`, and persisted metadata with an explicit mapping or a documented intentional difference. Move provider registration side effects out of `config` after its pure resolved-profile API is tested. **Exit:** parity tests fail if a consumer invents a phase/kind, and existing project data still opens.

### Step 4 — Tighten boundaries where the payoff is measured

Rerun the import graph after steps 1–3. Break cycles that remain by dependency injection or narrow interfaces; add a guard for each changed edge. Choose new packages only when a current package still has two incompatible owners after the behavior changes. **Exit:** the import graph is acyclic at the granularity used by the guard, and the guards name exact allowed exceptions. The test suite, build, and product gate pass.

### Step 5 — Update product documentation

Align the blueprint and operator runbooks with behavior actually exercised by the MCP tests. Record intentionally deferred seams with a trigger and owner. **Exit:** a fresh checkout can run the documented mock operator workflow and `make ci-check`; no documentation claims an untested feature is complete.

## 6. Gate and risk rules

- **No paid-provider execution** as architecture evidence. Use mocks and isolated temporary roots.
- **No bulk renames before compatibility proof.** The package is a single distribution; moving many import paths at once raises risk without proving behavior.
- **Persisted representation is a contract.** If a step changes artifact metadata, checkpoint data, or state keys, test old-write/new-read, new-write/new-read, and rollback/restore before calling that step shippable.
- **A green guard is not enough.** Mutate the owner or a consumer and show a focused test fails with `pytest --no-cov -n 0`; then run the full `make ci-check` gate.
- **No invented audit total.** The 191 headings / 189 severity bullets are a text inventory, not 189 verified defects. The exact actionable set is decided per change against current code and the latest verifier.

## 7. Remaining uncertainty

This review inspected decisive source paths and adversarial outcomes; it did not replay all 189 audit reproducers or run a full end-to-end migration. Apart from the small reference extraction below, the repository remains at its pre-migration architecture. The central unresolved design choice is whether a future package split is useful **after** the operator and persistence paths are repaired. Measure that coupling then; do not commit to the 20-module diagram now. Step 1's operator-path behavior proof remains to be done.

**Subsequent reference example:** at the user's request, [the phase-sequence extraction](examples/01-phase-sequence.md) was implemented as a small model for future migrations. It consolidates sequence lookup only; it does not close Step 1 or the provider-blocked approval defect described above.
