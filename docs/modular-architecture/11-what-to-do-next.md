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

## 5. Why I am not recommending more analysis

Four design documents have been written on this (`07`–`10`). The last three
rounds produced more value per unit of effort than all of them, because they
changed code and let the tests measure. The pattern to keep is: make the
narrowest change that a test can falsify, and let the failures enumerate the
work.

The `extra="forbid"` experiment is the model — 96 failures became a work list.
Analysis without a falsifiable check has been, in this session, the less
productive half.
