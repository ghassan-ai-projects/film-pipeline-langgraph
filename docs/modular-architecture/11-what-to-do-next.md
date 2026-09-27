# Recommendation: what to do next, and what to leave alone

Date: 2026-09-26. Revision: `e18c1a5`. This is the answer to "what do you
recommend now", written after measuring the remaining shared keys rather than
reasoning from the earlier framing.

## 1. The remaining keys are not the problem I said they were

`09` §2 listed seven keys written by MCP and owned by nodes, and implied
distributed ownership. Measuring them changes that reading:

| Key | Writer files | Guard agreement |
|---|---:|---|
| `target_runtime_seconds` | 5 | **All agree** on `> 0` |
| `target_scene_count` | 3 | All agree |
| `idea` | 3 | All agree |
| `shot_matrix_ref` | 2 | — |
| `visual_refs` | 2 | — |

The operator-intent keys are **duplication of convenience**, not distributed
ownership: independent writers that happen to implement the same rule the same
way. Per `00` §1.3 that is explicitly *not* an ownership seam, because a partial
edit would not produce divergent behaviour — it would produce an obvious bug.

So marking these as violations would be wrong. They are **inputs** to the graph,
and inputs legitimately originate outside it.

## 2. One key is genuinely different

`issues` is the exception, and it is the opposite problem from the one I
described. It has a reducer built precisely for it:

```python
def merge_issues(left, right):
    """Reducer for the ``issues`` channel: append, dedupe, and allow removal."""
```

Yet **13 files assign the key wholesale** rather than going through it:

```python
state["issues"] = [...]        # studio/_resume.py:73
raw["issues"] = []             # mcp/tools/reference_generation/outcomes.py:79
active["issues"] = [...]       # mcp/tools/generation/_text_only.py:32
```

The reducer's own docstring says why that matters: "a plain `operator.add`
reducer makes issues immortal — once a blocking issue is recorded it can never
be removed." These sites are outside the graph, so they bypass the reducer on
the way in and depend on being re-merged correctly on the way out.

**That is a real defect class**, and it is a *narrower* and more actionable one
than the seven-key census.

It is sharper still: the reducer already implements the exact operation two of
these sites need. It honors a ``{"__remove_codes__": [...]}`` sentinel entry
that removes previously recorded issues by code — described in its own docstring
as "used when an external actor — e.g. the operator planning a generation batch
— has resolved the underlying condition." Two sites reimplement precisely that
as an inline list comprehension:

```python
# studio/_resume.py:73 and mcp/tools/generation/_text_only.py:32
state["issues"] = [
    issue for issue in issues
    if not (isinstance(issue, dict) and issue.get("code") in STALE_CODES)
]
```

So the sentinel is not a hypothetical: a documented, purpose-built mechanism for
external issue removal exists, and its intended callers bypass it.

## 3. Recommendation

**Do this: make `issues` writes go through its reducer.**

One helper that applies `merge_issues` semantics for out-of-graph writers, used
by the sites that currently assign wholesale. Cheap, mechanical, and it converts
a class of silent-clobber into a single code path. It is also testable in
isolation, unlike the seven-key question.

**Do not do this: declare authority for all 78 keys.**

That was my earlier proposal and it is not justified by the measurements. Of the
keys I flagged:

- The five operator-intent keys are agreed-upon duplication. A guard would fail
  on correct code.
- The graph channels (`artifact_refs`, `generation_requests`,
  `validation_report_refs`) already have reducers and a declared shape, now
  enforced at the snapshot boundary by `d079a5e`.
- The private `_`-prefixed keys are graph bookkeeping and are now confined to
  graph state rather than leaking into `project.json`, by `7845834`.

The boundary work already done removed most of what the census was for.

**And do not revisit `StudioRuntime` yet.** Its size is still real, but the
honest position is unchanged from `08`: the consumer set has to move before the
structure can, and I have not established which of its 39 methods are studio's
versus other modules' concerns. Guessing cost time once already.

## 4. Sequencing if more is wanted after that

1. **`issues` through its reducer** — the defect above.
2. **Then re-measure.** Several `09` claims are now stale; a fresh census against
   the post-boundary tree is cheap and would tell us whether anything is left.
3. **Then, and only then, `StudioRuntime`** — with the 16 state-only handlers
   identified in `08` §7 as the first concrete slice, since they need a
   project-state accessor rather than the runtime.

## 5b. Re-measured after the boundary rounds

The `issues` consolidation landed (`dcb4914`), so the recommendations above are
partly spent. Re-measuring rather than trusting the earlier notes:

| Claim | Status |
|---|---|
| `issues` writers | 13 -> 11; the two removed were the duplicated removal sites. The remaining three non-graph writes are a manifest entry (`outcomes.py`) and validator freshness replacement (`_graph_exec.py`) — both correct as-is. |
| State-only MCP handlers (`08` §7) | **Still 16**, unchanged. |
| Capability-needing handlers | Still 25. |

So the next concrete slice is the one `08` §7 identified and the boundary work
has since made cheaper. Measured on the current tree:

- **25 handlers inline `rt.get_active()`; 12 already call the existing
  `helpers._active_project_state`.**
- The "no active project" error string appears **48 times**, in three variants:
  45 x `"No active project."`, 1 x `"No active project. Create one first with
  create_film_project."`, 1 x `"No active project set"`.

That is the same shape as the `issues` finding: one policy, many
reimplementations, small divergences. It needs no new abstraction — the helper
already exists and does exactly what the inline sites re-derive. Retargeting the
16 state-only handlers to it is mechanical and testable, and it is the safest
possible first step toward the `StudioRuntime` question, because it moves
*consumers* rather than structure.

**Not recommended:** inventing a new accessor type first. The helper already
returns what they need; a new type would be the facade mistake again.

## 6. Why I am not recommending more analysis

Four design documents have been written on this (`07`–`10`). The last three
rounds produced more value per unit of effort than all of them, because they
changed code and let the tests measure. The pattern to keep is: make the
narrowest change that a test can falsify, and let the failures enumerate the
work.

The `extra="forbid"` experiment is the model — 96 failures became a work list.
Analysis without a falsifiable check has been, in this session, the less
productive half.

## 7. Measured and rejected: flattening the orchestrator key constants

**Decision: leave `orchestrator_state.py` lines 77–114 alone. Do not flatten the
nine `f"{_ORCH_NS}__..."` constants to literals, and do not delete
`_COMPUTED_KEY_WRITERS`.** Measured on `11a0f99`, clean tree.

The proposal was: replace the nine computed module-constant state keys with
literal-typed values, which would let the nine computed-key writers take
`StudioGraphState` and let the guard's `_COMPUTED_KEY_WRITERS` table be deleted.

It fails on two independent counts. Either one is sufficient.

### 7.1 It breaks the channel-registry guard, as predicted

`tests/unit/orchestration/test_channel_registry.py::_ast_orchestrator_keys`
discovers the key set by matching `ast.JoinedStr` values containing a
`FormattedValue` whose `Name.id == "_ORCH_NS"`. Flattening removes every such
node. Reproduced by executing the guard's own discovery function against a
flattened tree:

| | constants discovered | registry rows | assertion |
|---|---:|---:|---|
| committed tree | 9 | 9 | passes |
| flattened | **0** | 9 | `AssertionError: registry rows without orchestrator constant:` + all 9 |

`test_every_orchestrator_constant_has_a_registry_row` fails on its **`unknown`**
branch, not `missing` — the direction that reads as "the registry has rows for
constants that no longer exist". The guard's discovery mechanism is the thing
being broken, not the tree it grades. Note the guard would still *pass* if it
had only the `missing` assertion, so this is a case of a guard whose two
branches have different sensitivity: the failure surfaces on the weaker-tested
one.

### 7.2 It does not actually unlock the writers — this is the real blocker

The premise is that a TypedDict rejects a computed key because the key is
*computed*. It rejects it because the key is **a name**. Moving the string into
the constant's value changes nothing: mypy resolves the name at the write site,
not the value at the definition. Probed directly (`mypy --strict`):

```python
_CANDIDATE_REFS: str = "_orchestrator__candidate_refs"   # flattened literal

def writer(state: StudioGraphState) -> None:
    state[_CANDIDATE_REFS] = {}                  # error: [literal-required]
    state.setdefault(_CANDIDATE_REFS, {})        # error: [misc]
```

`Final` does not rescue it either — `_X: Final = "_orchestrator__convergence"`
still yields `Expected TypedDict key to be string literal [misc]`. Only the
**literal spelled inline at the write site** type-checks:

```python
def writer_ok(state: StudioGraphState) -> None:
    state["_orchestrator__candidate_refs"] = {}          # clean
    state.setdefault("_orchestrator__convergence", {})   # clean
```

So the change that would delete `_COMPUTED_KEY_WRITERS` is not "flatten the
constants" — it is "inline the literal spelling at all ~10 write sites and lose
the single-definition constant", which is the opposite of the ownership
direction this program has been moving in. The constants have 53 references in
their own module; nine of them are the write sites, the rest are reads that
currently work *because* the read path goes through `Mapping`.

### 7.3 The exemption table is not what blocks the callers anyway

The nine `_COMPUTED_KEY_WRITERS` rows are one row per writer function, and the
boundary copies they sit behind are **deliberate, and not caused by the
constants**:

- `_agent_artifacts._publish_candidate_ref` *already takes* `StudioGraphState`,
  then takes `dict(state)` explicitly to hand a dict to the helpers, then writes
  the one changed key back by literal name. Its docstring states the reason.
- `approval._orchestrator_working_state` builds a `_orchestrator__*`-filtered
  **slice**, not a copy of state — the writers must not see non-orchestrator
  keys, and `ensure_orchestrator_state` seeds defaults into it.

Retyping the writers would not delete either copy, so the exemption rows would
have to move rather than disappear.

### 7.4 What this does *not* establish

It does not establish that `_COMPUTED_KEY_WRITERS` is permanent, only that
*this* step does not remove it. The table holds eleven rows: the nine writer
functions named above, plus `compute_actions` and `remove_issues_by_code`,
whose recorded reasons (transitive mutation through the fact port; plain-dict
callers in `mcp`/`operations`) are unrelated to these constants and would
outlive any flattening. Even in the best case the table would shrink by nine
rows only under the inline-literal spelling, which trades a checkable exemption
table for nine unstated copies of the same key strings. That is not a better
trade.

The scope of the proposed step was also overstated in its own framing: it is
**nine** constants (lines 77–114), not ten, and nine writers, not ten.

If this is ever revisited, the falsifiable check is the one used here, and it is
cheap: run `_ast_orchestrator_keys()` against the modified module and assert it
still returns the registered key set. That single command would have caught the
guard break before any edit was committed.
