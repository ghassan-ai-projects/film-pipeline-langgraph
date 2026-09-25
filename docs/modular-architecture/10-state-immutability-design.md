# Can project state be lifted and made immutable?

Date: 2026-09-26. Revision: `3da5f55`. This answers a design question directly:
*why not move the state up an abstraction layer, make it immutable, and give it
its own module?*

Short answer: **yes to the module, yes to lifting it, and mostly-yes to
immutability — but not the way it looks.** The graph state is already immutable
by construction; the mutability lives outside it. And there is a hard constraint
that a naive immutable type would break.

## 1. The graph state is already immutable — that is the surprise

LangGraph does not ask nodes to mutate. A node returns a **partial update**, and
reducers merge it:

```python
artifact_refs:      Annotated[list[str], merge_unique]
issues:             Annotated[list[dict[str, object]], merge_issues]
generation_requests: Annotated[list[dict[str, object]], merge_generation_requests]
```

Nodes still `deepcopy(state)` internally, which is defensive but not the
mechanism. The framework's contract is already "return what changed".

So the graph half of the system is fine. **The mutation problem is entirely in
the layers around it**, and it takes a specific and worse form:

```python
# mcp/tools/intake.py:27
active = rt.get_active()      # aliases the runtime's live dict
active["idea"] = idea         # mutates it in place
state = rt.run_graph(active)  # passes the same object in
rt.projects[pid] = state      # writes it back
```

`get_active()` hands out a reference to the runtime's own dict. Callers mutate it
directly, which is why there is no single writer and no way to observe a change.
An immutable value type would turn a silent in-place write into a loud error —
which is precisely the value here.

## 2. The hard constraint: LangGraph needs a mutable mapping

This is the part that must be designed around, not wished away. LangGraph's
`StateGraph` accumulates state through reducers over a plain mapping. Passing a
frozen `Mapping` breaks the framework contract.

The way through is to stop conflating two roles that are currently one object:

| Role | Lifetime | Correct type |
|---|---|---|
| **Graph channel state** | one graph invocation | mutable dict, LangGraph's business |
| **Project record** | the session, persisted to disk | immutable value, owned by `projects` |

Today `rt.projects[pid]` is simultaneously both. It is the graph's input, the
graph's output, the persisted record, and the thing 25 `get_active()` call sites
mutate. That conflation is the defect — not the absence of an immutable type.

## 3. What "its own module" should own

`projects` (L4) is already declared for exactly this, and `03` §3.8 says so:

> **State.** the in-memory project map and active id — one place, replacing
> `StudioRuntime.projects` + `active_project_id` and
> `mcp/tools/helpers._active_project_id`.

So the target already exists in the design; the migration never delivered it.

A `ProjectRecord` value type there should be:

- **Immutable** — `frozen=True`. A field change produces a new record.
- **The single persisted representation** — `storage` writes it, nothing else.
- **The only thing `get_active()` can return** — so an in-place write is a
  `TypeError`, not a silent corruption.

The mutable dict then exists *only* inside a graph invocation, created from the
record and folded back into a new record on completion. That is the boundary
that currently does not exist.

## 4. Does this shrink `StudioRuntime`? Yes — as a consequence

This is the part my earlier attempts got backwards. With a `ProjectRecord`:

- The **16 handlers that only read project state** stop needing the runtime at
  all. They need the active record, which they can get without a god object.
- The runtime stops being the persistence owner for project state; `projects`
  owns it and `storage` writes it.
- The runtime keeps what is genuinely its own: graph handle, services, session
  wiring. That is a bijection with its name.

The shrinkage follows from the ownership change rather than being pursued
directly. No delegating methods, no facade.

## 5. Where immutability is the wrong tool

Two places to not force it:

**Operator intent keys** (`idea`, `target_runtime_seconds`, `constraints_hints`).
These are *requests*, not state. `submit_idea` mutating `active["idea"]` is wrong
not because the dict is mutable but because a request should be an **argument**.
The fix is a function that takes the request and returns a new record — not an
immutable dict the caller still assigns into.

**Derived config** (`resolved_config`). §2 of `09` records that no node writes
it; `config` produces it and the transport layer smuggles it in. Immutability
does not help here either — the fix is that `config` computes it and the record
*contains* it, rather than three layers assigning the same key.

In both cases the real fix is **moving the write to its owner**, and
immutability is the enforcement mechanism, not the solution.

## 6. Recommended shape, in order

1. **`projects.ProjectRecord`** — immutable value type; the persisted and active
   representation. Replaces `rt.projects` + `active_project_id`.
2. **`projects.ProjectRegistry`** — owns the map and the active pointer, returns
   records, exposes `update(record)` rather than handing out aliases.
3. **Retarget `get_active()`** to return a record. Every in-place write becomes a
   type error, which is the migration checklist generated by the type system
   rather than by my judgement.
4. **Then** reassess `StudioRuntime` with the 16 state-only handlers already
   detached.

## 6b. The experiment: what actually happened

I ran the prototype rather than leaving it as a design argument. Three steps,
each measured.

**Step 1 — `frozen=True` on `ProjectRecord`.** Passed everything: mypy clean,
2,184 tests green, CI exit 0, Enola exit 0. Verified directly that mutation is
now rejected (`ValidationError`) and that `extra` keys still round-trip.

That is the honest result: **the record was already immutable in practice.**
Nothing in the codebase mutates a validated `ProjectRecord`. The immutability
half of the idea was already true and is now enforced rather than assumed.

**Step 2 — declare the three leaked keys** (`idea`, `constraints_hints`,
`issues`). Also clean. Declaring them closes the field set without changing the
on-disk format.

**Step 3 — `extra="forbid"`.** **96 tests failed**, and the failure is the
measurement I wanted. Pydantic reported up to 27 extra inputs per record. After
a graph run, a live project state carries **28 keys** of which **17 are
undeclared**:

```
_orchestrator__candidate_refs   _qc_raw_reports      _qc_reports
_routing_decisions              artifact_refs        constraints
constraints_ref                 film_type            generation_requests
min_scene_count                 pacing_style         profile_ref
scope_contract_ref              target_runtime_seconds
target_scene_count              target_shot_count    validation_report_refs
```

That list is not incidental. It is almost exactly the split §5 predicted:

| Kind | Keys | Should live in |
|---|---|---|
| Graph channels with reducers | `artifact_refs`, `generation_requests`, `validation_report_refs` | `orchestration` |
| Private graph bookkeeping | `_orchestrator__candidate_refs`, `_qc_reports`, `_qc_raw_reports`, `_routing_decisions` | `orchestration` |
| Derived values | `constraints`, `constraints_ref`, `film_type`, `min_scene_count`, `pacing_style`, `profile_ref`, `scope_contract_ref`, `target_*` | derived, not stored on the record |

**All 17 are graph concerns leaking into the persisted project record.** None is
operator intent; none is project identity.

## 6c. What the experiment establishes

The design question is answered, and not in the direction the original idea
pointed:

1. **Immutability was never the problem.** Applying it changed nothing because
   the mutation was never happening on the validated record. It is still worth
   keeping — it converts an unstated assumption into an enforced invariant — but
   it is not the fix.

2. **The leak is real, measured, and large.** 17 of 28 live keys are undeclared
   graph state flowing into a project record. `extra="allow"` is what permits it.

3. **The fix is a boundary, not a type.** The record must regain a closed field
   set, and the 17 keys must be routed to their owners. That is precisely the
   "name the authority, then make the writers honest" sequence proposed in `09`,
   now backed by an empirical list instead of a census.

4. **`extra="forbid"` is the acceptance test.** It fails 96 tests today. Each
   failure is a key in the wrong place, so the count going to zero *is* the
   migration's progress bar — and it cannot be gamed, because pydantic enforces
   it.

## 7. Checked: the typed record already exists, and it is load-bearing

The risk in §6 is smaller than it looked, because the work is partly done. I ran
the check rather than leaving it as a hypothesis.

`_persistence.py:272` **already** validates the live dict into a typed record
before writing:

```python
record = ProjectRecord.model_validate(rt.projects[project_id])
storage.write_project_record(project_id, record)
```

And `schemas/runtime_state.py` already defines `ProjectRecord` as a Pydantic
model. So there is a typed, persisted representation today. Measured against a
real runtime, a persisted `project.json` carries **14 keys**:

```
approved, constraints_hints, current_phase, discovered, human_approval_phase,
human_approval_required, idea, issues, project_id, project_kind,
schema_version, server_mode, slug, title
```

`ProjectRecord` **declares 11** of them. Three are undeclared and survive only
because the model sets `extra="allow"`:

- `constraints_hints`
- `idea`
- `issues`

### What this changes

1. **Immutability is a one-line change with a real blast radius.** Adding
   `frozen=True` to `ProjectRecord` is trivial; finding every site that mutates a
   validated record is the work. That is exactly the migration checklist we want
   the type system to generate.

2. **`extra="allow"` is the actual defect**, not the missing module. A record
   with a closed field set would have rejected `idea`/`issues`/`constraints_hints`
   at the boundary, and the three-way split in §5 would have had to be decided
   then. `extra="allow"` let three concerns leak into the persisted representation
   without anyone choosing it.

3. **The persisted format is already narrow.** Only 14 of ~78 live keys reach
   disk, so the compatibility surface (`03` §8) is far smaller than the live
   state suggests. A closed, frozen `ProjectRecord` is therefore achievable
   without a data migration — provided those 14 keep their names and types.

4. **`issues` is the interesting one.** It is persisted, and it is also a graph
   channel with a `merge_issues` reducer used 32× in `orchestration/nodes`. A
   frozen record forces the question the current design avoids: is `issues` part
   of the *project record*, or only of *graph state*? One of those is wrong
   today, and `extra="allow"` is what hides it.

### A naming collision this exposes

There are **two classes called `ProjectRecord`**:

| Location | Shape | Role |
|---|---|---|
| `schemas/runtime_state.py:25` | Pydantic, 11 declared fields, `extra="allow"` | The persisted record (`project.json`) |
| `projects/resolution.py:14` | plain dataclass, 4 fields (`project_id`, `slug`, `title`, `aliases`) | In-memory stand-in for reference resolution |

Both are re-exported from `projects`. The resolution one is a *different thing*
wearing the same name — it has `aliases`, which the persisted record does not,
and lacks `current_phase`, which it does.

Any move of project state into `projects` has to resolve this first, because the
"immutable record with one owner" design cannot have two types claiming the name.
The likely resolution is that the resolution type is a *projection* of the record
(used for fuzzy matching) and should be named for that, e.g. `ProjectMatch`.

### Remaining unknown

Whether closing `extra="allow"` breaks anything outside the repo. The persisted
format is read back by `read_project_record`; an existing `project.json` with an
unexpected key would now fail validation rather than being silently accepted.
That tolerance may be deliberate for forward compatibility, and the §8
compatibility table should be consulted before closing it.
