# Progress ledger — modularity improvements

One row per committed slice from [07 — sequencing and guards](07-sequencing-and-guards.md).
The "check" column is a command whose output is the evidence, not an argument.

Tooling note: `enola` 0.4.25 is the installed build. A `DECLINED` (exit 3) means the
pinned baseline is not comparable — regenerating is the fix, never a filter change.

| Step | Slice | Commit | Check | Enola |
|---:|---|---|---|---|
| 0 | Regenerate baseline; ignore `.pre-commit-cache/**`; `make enola` | `ba193d0` | `enola check` exits 0; 0 facts for `app`/`graph`/`artifacts`/`review`/`testing` | 0 |
| 1 | Delete the `nodes.approval` re-export shim | `_pending_` | module-level SCCs 2 → 1 (`measure.py`) | 0 |

## Step 0 — Enola gate restored (2026-09-28)

Before: `enola check` exited **3 (DECLINED)** — baseline pinned by
`0.2.7-51-g72cd079` at `df97c47`; installed `0.4.25`; ignore globs differed.

What changed:

- `.pre-commit-cache/**` added to `ignore` in `enola-config.yaml`. This is a scope
  correction of the same kind as `.uv-cache/**`, not a threshold change: the dir is
  gitignored vendored hook code, and it contributed 963 facts that surfaced as
  "new coupling" on every run.
- Baseline cleared and re-pinned with `0.4.25` from the tree at `74490e2`.
- `make enola` added: runs the check **without a pipe** and propagates the exit code,
  so a later run cannot read `tail`'s status as the gate's.

After: `enola check` exits **0 (PASS — no architectural change)**; snapshot
`sha256:8783d71d…`, 8497 facts, 0 facts for the five removed packages
(`app`, `graph`, `artifacts`, `review`, `testing`).

Note, per AGENTS.md: a freshly pinned baseline grades against a snapshot, so it
cannot catch a *new* cycle. That check stays in
`tests/unit/architecture/test_package_acyclicity.py`.

The baseline artifacts are gitignored (`/docs/modular-architecture/enola-out/`), so
this slice's committed content is the config ignore entry and the `make enola` target.

## Step 1 — one fewer module cycle (2026-09-28)

`orchestration/nodes/approval.py` re-exported `_PHASE_NODES` and `repair_phase_node`
from `_repair_loop` "to keep the historical `graph.nodes.approval` import paths
working" — but the `graph` package no longer exists. That eager back-import was one
half of the `approval <-> _repair_loop` module cycle.

Pointed the two consumers (`studio/_graph_exec.run_phase_node` and
`orchestration/nodes/__init__`) at the owner, `nodes._repair_loop`, and deleted the
re-export plus its now-empty `__all__`.

Evidence: `measure.py` module-level SCCs **2 → 1** (only `mcp.contract <-> registry`
remains). `enola check` exit 0. Full `make ci-check` green on the committed tree.
