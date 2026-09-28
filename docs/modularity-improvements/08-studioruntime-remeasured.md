# 16 — `StudioRuntime` re-measured: 392 lines, 29 methods, 8 concerns

**Status: measurement and decision.** Doc 07's row 16 asks for "public methods and
concerns, per `AGENTS.md`'s table" before deciding whether to split. This is that
measurement, re-taken at the review-fix tip after Steps 10–15.

## The measurement

`AGENTS.md` says size alone is not a seam; the discriminating numbers are the *public
surface* and the number of *concerns*:

| Class | Lines | Public methods | Concerns | Verdict |
|---|---:|---:|---:|---|
| `StudioRuntime` (at base `2450616`) | 394 | 29 | 8 | split |
| `StudioRuntime` (now) | **392** | **29** | **8** | split deferred, this program |
| `ArtifactStore` | 605 | 15 | 1 | leave alone |

Exactly one number moved, and it moved during review rather than during Steps 13–14:

- **The class body fell 394 → 392.** Both figures are `ast`
  (`ClassDef.lineno..end_lineno`), so they measure the same object. The two lines are
  a dead `# --- Graph ---` section header and its blank line, which sat above
  `# --- Graph execution ---` with no method under it; the header is deleted. The
  lazy-import work in this file is outside the class (in `_install_graph_builder`) and
  made the module longer, not shorter.
- **Public methods are 29 at both commits**, and the concerns are the same eight.

### Correction: three earlier numbers in this document were never measured

An adversarial review of this branch re-measured the claims below, and they did not
survive. They are recorded rather than silently dropped, because each is a written
claim a later round would otherwise have trusted:

- This document reported **`516 → 393` lines (−24%)** and attributed it to Steps 13
  and 14. `516` is not a measurement of anything at any commit on this branch:
  `studio/runtime.py` is 485 lines at base `2450616`, 514 at `88d773a^`, 536 at
  `330ab8d` and 546 in the reviewed tree. The number was a *file* line count (never
  516 either) conflated with a *class-body* count. The class body was 394 before the
  graph-execution move and 394 after it.
- It reported **27 → 29 public methods**. Both commits measure **29**.
- It reported **5 → 9 concerns**. Both commits measure **8**. The section-heading
  count was 9 in both trees only because a `# --- Graph ---` header sat immediately
  above `# --- Graph execution (see orchestration.execution) ---` with no method under
  it; that dead header has been deleted.

The moves these claims credited were real, but smaller in this file than described:
`studio/_graph_exec.py` (542 lines) did become `orchestration/execution.py`, and that
removed three cross-package private reach-ins. It did not shrink `StudioRuntime`,
because the five graph-execution methods were already three-line delegators before
the move — the module held *functions taking the runtime as an argument*, not method
bodies.

The decision below is unchanged, and now rests on numbers that hold.

## Eight concerns, from the class's own section comments

| Concern | Methods |
|---|---:|
| Provider health | 6 |
| Project management | 5 |
| Graph execution | 5 |
| Provider registry | 4 |
| Checkpoints | 3 |
| Persistence across restarts | 2 |
| Audit | 2 |
| Operator comments | 2 |

Total 29. **Thirteen of the 29 are pure delegators** — a single `return` of a call:

```text
load_persisted_projects  get_project      ensure_graph      run_graph
approve_phase            run_validation   request_revision   get_checkpoint
get_provider             list_providers   get_provider_health
get_all_health           default_video_provider
```

That is 13 of 29 — **nearly half the public surface forwards to something else**. By
target: `orchestration.execution` 5, the runtime's own attributes 6
(`self.projects`, `self.checkpoints`, `self.provider_adapters`, `self.provider_health`,
including the `list(...)` and `dict(...)` wrapping of the last two), `studio._persistence`
1, and `studio._provider_seeds` 1. The six that read the runtime's own attributes are
the runtime acting as a live view of its own state rather than delegating outward.

## Decision

**Do not split `StudioRuntime` in this program.** Three reasons, in order of weight:

1. **It is the composition root, and a composition root is allowed a wide surface.**
   `studio` is where services, providers, checkpoints and the graph are wired together;
   `03-target-architecture.md` §4.6 assigns it that role. Splitting it into eight
   collaborating classes would move the wiring without removing it, and every split
   point would itself need the others — the classic complaint about decomposing a
   facade with no second implementation.

2. **The delegators are the actual defect, and they are cheap to fix separately.**
   `AGENTS.md` already names this pattern: *"A symbol used many times is a symptom, not
   a fix... The repair is to move the concern up to its owner and delete the callers'
   re-derivation."* Here the concern is already *up* — `orchestration.execution` owns
   graph execution. What remains is that callers reach it *through* the runtime. That is
   a decision about the runtime's interface, not about its size, and it should be made
   per-concern with the callers in front of you.

3. **The measurement does not show a maintenance problem.** Concerns like "audit" (2
   methods) and "operator comments" (2) are small and stable. Splitting a 2-method
   concern into its own class adds a collaborator and a wiring line to remove two
   delegators.

## What a split would look like, if taken up later

The concern table is the natural seam list, in this order:

1. **Provider health + registry (10 methods)** — the largest coherent pair, and both
   already delegate to `studio._provider_seeds` and the provider factory. A
   `ProviderRegistry` owning these ten would leave the runtime with 19 methods.
2. **Graph execution (5 delegators)** — delete the delegators and have callers use
   `orchestration.execution` directly, or keep them deliberately as the runtime's
   published interface. This is a design call, not a mechanical move.
3. **Checkpoints (3) and persistence (2)** — both already delegate to `checkpoints`
   and `studio._persistence`.

Doing (1) alone would take 29 → 19 methods and 8 → 6 concerns, and is the single
change with the best ratio. It is **not** done here, and this document does not claim
it is.

## What this does not establish

- That 29 methods is too many. `ArtifactStore` has 15 and one concern; the table in
  `AGENTS.md` gives no threshold, and this measurement does not invent one.
- That the delegators are harmful. They may be a deliberate published interface for a
  composition root; nothing here tests whether callers *should* go through the runtime.
- That Steps 13 and 14 were wrong. Step 13 removed three cross-package private
  reach-ins and Step 14 moved the reference-generation bodies; the program's net
  effect on this file's *surface* is nothing. Its effect on private reach-ins is
  recorded in their own ledger entries, and corrected here: counting private module
  reach-ins and private symbol imports together,
  `tests/unit/architecture/test_boundary_law.py`'s detector measures **7 at base
  `2450616` → 4 at the tip** (module reach-ins 2 → 2, symbol imports 5 → 2). Step 13's
  own delta was **7 → 4**, not the `8 → 2` this document used to cite, and not the
  `8 → 2` its commit message claimed.

## Evidence

- `StudioRuntime`: **392 lines, 29 public methods, 8 concerns**, 13 pure delegators.
- Measured from the class's own `# --- Section ---` comments plus an AST pass counting
  single-`return` bodies and per-section method counts; the base column is the same
  pass over `git show 2450616:src/film_pipeline/studio/runtime.py`.
- Private reach-ins measured with `tests/unit/architecture/test_boundary_law.py`'s own
  `_measure_private_imports()`.
- `make ci-check`, `mypy src tests` and `enola check` are all green on the tip this
  document ships with; this document changes no code.
