# 16 — `StudioRuntime` re-measured: 393 lines, 29 methods, 9 concerns

**Status: measurement and decision.** Doc 07's row 16 asks for "public methods and
concerns, per `AGENTS.md`'s table" before deciding whether to split. This is that
measurement, taken 2026-09-28 at commit `485a7cc` after Steps 10–15.

## The measurement

`AGENTS.md` says size alone is not a seam; the discriminating numbers are the *public
surface* and the number of *concerns*:

| Class | Lines | Public methods | Concerns | Verdict |
|---|---:|---:|---:|---|
| `StudioRuntime` (before this program) | 516 | 27 | 5 | split |
| `StudioRuntime` (now) | **393** | **29** | **9** | split |
| `ArtifactStore` | 605 | 15 | 1 | leave alone |

Two things moved in opposite directions, and both matter:

- **Lines fell 516 → 393** (−24%), because Steps 13 and 14 moved the graph-execution
  and reference-generation *bodies* out to their owners.
- **Public methods rose 27 → 29**, and **concerns rose 5 → 9**. Doc 02 predicted the
  method count would drop; it did not. Six graph-execution methods survive as one-line
  delegators, and the operator-surface deletion added no methods but the measurement
  became precise about what was always there.

The concern count is the more useful number and it went the wrong way — which is why
it is worth measuring rather than asserting.

## Nine concerns, from the class's own section comments

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

That is 13 of 29 — **nearly half the public surface forwards to something else**,
mostly to
`orchestration.execution` (5) and `studio._persistence` (1). Seven more forward to the
runtime's own attributes (`self.projects`, `self.checkpoints`, `self.provider_adapters`,
`self.provider_health`), which is the runtime acting as a live view of its own state
rather than delegating outward.

## Decision

**Do not split `StudioRuntime` in this program.** Three reasons, in order of weight:

1. **It is the composition root, and a composition root is allowed a wide surface.**
   `studio` is where services, providers, checkpoints and the graph are wired together;
   `03-target-architecture.md` §4.6 assigns it that role. Splitting it into nine
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

Doing (1) alone would take 29 → 19 methods and 9 → 7 concerns, and is the single
change with the best ratio. It is **not** done here, and this document does not claim
it is.

## What this does not establish

- That 29 methods is too many. `ArtifactStore` has 15 and one concern; the table in
  `AGENTS.md` gives no threshold, and this measurement does not invent one.
- That the delegators are harmful. They may be a deliberate published interface for a
  composition root; nothing here tests whether callers *should* go through the runtime.
- That Step 13's or 14's moves were wrong. They reduced lines and coupling (private
  reach-ins 8 → 2) while leaving the surface; that trade is recorded in their own
  ledger entries rather than revisited here.

## Evidence

- `StudioRuntime`: **393 lines, 29 public methods, 9 concerns**, 13 pure delegators.
- Measured at `485a7cc`, from the class's own `# --- Section ---` comments plus an AST
  pass counting single-`return` bodies.
- `make ci-check`, `mypy src tests` and `enola check` are all green at that commit; this
  document changes no code.
