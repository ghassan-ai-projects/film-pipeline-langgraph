# Reference migration 01: phase sequence

**Status:** implemented and validated; commit pending. This is a deliberately small example of moving one rule to one owner while preserving the existing public and persisted contracts. It is not the whole phase-policy migration.

## Problem and root cause

Before this change, `schemas.FilmPhase` listed 11 serialized phase names, `graph._action_routing.PHASE_ORDER` listed them again, `graph.edges._NEXT_PHASE_AFTER_APPROVAL` separately encoded the successor relation, and `graph.graph` independently spelled phase-to-node and approval-destination tables. The lists happened to agree. A partial edit could change routing, graph wiring, or resume order without changing the others. The root cause was **multiple editable statements of one sequence**, not a lack of a 20-module package structure.

## Ownership decision

| Item | Owner and contract |
|---|---|
| Serialized phase vocabulary | `schemas.FilmPhase` remains the type accepted by persisted artifacts and state. Its declaration order now defines execution order. |
| Ordered sequence and successor | `graph.phase_sequence.PHASE_SEQUENCE` is the immutable sequence derived from `FilmPhase`; `next_phase(phase)` is the sole successor rule. `PHASE_ORDER` remains a list-shaped compatibility view. `next_phase` returns `None` for delivery and unknown input; it never decides whether progression is allowed. |
| Graph node-name projection | `graph.phase_sequence.PHASE_NODES` derives node names from the sequence. `graph.graph` registers actual callables and owns gate/terminal wiring; `graph.nodes._repair_loop._PHASE_NODES` owns repair/app callable dispatch and has a parity test against the sequence. |
| Approval and provider policy | `graph._action_routing` and the operator workflow still own refusal decisions. This example does **not** repair the known app-path provider-gate bypass. |

The module imports only `schemas.FilmPhase`. No new package, dependency, service locator, registry, or runtime manifest was added. A small function and a read-only node-name mapping are sufficient.

## Migration boundary

- `graph.router.PHASE_ORDER` remains the stable public import and remains a **list** for compatibility. Internal consumers use immutable `PHASE_SEQUENCE`, so mutating the compatibility list cannot change runtime progression.
- `graph._action_routing` uses `next_phase` for approved-phase progression. Its provider check stays in place.
- `graph.edges.after_approval` uses the same successor instead of its private 11-row table.
- `graph.graph` derives both phase-node dispatch and approval destinations. Gate and terminal nodes remain explicit because they are different concepts.
- `app._graph_exec.advance_to_next_phase` uses the same successor. It still has its separate approval policy; this change does not claim to unify that policy.
- `app._resume` and `cli.driver` use the immutable sequence for phase-order comparisons and target selection.
- Artifact directory names and persisted phase strings are unchanged. The storage directory projection belongs to `artifacts` and is outside this small extraction.

## Proof and limits

`tests/unit/graph/test_phase_sequence.py` pins the serialized order, checks every successor and approval edge, verifies graph and repair/app phase registries agree with the sequence, checks phase-node registration and entry dispatch, and exercises the app consumer's next and terminal behavior. Existing router and graph tests still run. The exact order assertion is a compatibility guard: a future enum reorder must be reviewed as a workflow and resume change, not accepted through an incidental edit.

The full delivery gate is `make ci-check`. A focused run uses `pytest --no-cov -n 0` because project-wide 90% coverage is enforced in `pyproject.toml`; a subset run without `--no-cov` is not a valid red/green proof. This slice passed formatting, lint, strict mypy, 2,008 tests / 8 skips, 91.62% coverage, source and wheel builds, and the product gate. The docs-local Enola check reported no cycle delta. See the [implementation progress tracker](../implementation-progress.md) for exact commands and reviewer evidence; historical baseline results are not used as proof for this change.

## Pattern for the next migration

1. Name **one behavior or invariant** and show its competing definitions in source.
2. Choose an existing package as owner unless a concrete dependency conflict requires a new package.
3. Define the smallest public contract and state its unknown/terminal behavior.
4. Move all direct consumers of that rule in one shippable change. Preserve stable imports and serialized data.
5. Test behavior at the owner and at at least one real consumer boundary. Pin compatibility-sensitive representations explicitly.
6. Record adjacent concerns left open; do not claim this extraction solves them.
7. Run the full repository gate and inspect the diff for new cycles, unrelated changes, and accidental contract breaks.

**Follow-up:** the provider-blocked-generation mismatch between graph routing and the app approval path needs its own behavior test and fix. It should not be hidden inside this sequence extraction.
