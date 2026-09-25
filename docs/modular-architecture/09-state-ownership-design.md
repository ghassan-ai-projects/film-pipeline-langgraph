# The design problem behind `StudioRuntime`

Date: 2026-09-26. Revision: `77bfcf2`. This supersedes the counting in
`08-why-studioruntime-is-large.md`: the numbers there are evidence, but the
problem is not a number.

## 1. What the size actually is a symptom of

`StudioRuntime` has 39 methods and `orchestration` has a 78-key state dict. Those
are the same problem seen from two ends.

The graph's state is a **mutable dict with no owner**. Every layer reads and
writes it directly:

| Layer | Direct writes | Direct reads |
|---|---:|---:|
| `orchestration` | 23 | 118 |
| `studio` | 11 | 37 |
| `operations` | 20 | 34 |
| `mcp` | 26 | 51 |

`StudioRuntime` is the thing that hands that dict around and persists it. It is
large because it is the de-facto owner of a structure nobody owns on purpose.

## 2. The concrete defect

`resolved_config` is the clearest case:

- `config` (L2) is the **declared producer**: `03` §3.3 — "produces the
  resolved-config value consumed by the graph and runtime."
- `prep.py` **reads** `state.get("resolved_config")` as though a node produced it.
- But the actual writer is an **MCP tool**:
  `mcp/tools/projects.py:121` does `state["resolved_config"] = ...`, and
  `mcp/tools/_profile_change.py:279` does the same.

So a profile-resolution policy is executed in the transport layer and smuggled
into the graph through a shared dict. Neither the graph nor `config` controls it.
That is what "distributed ownership" means in practice, and it is exactly the
class of defect the audit's O1–O8 taxonomy was written to name.

Sharper still: **no node ever writes `resolved_config`.** The schema declares it
as a graph channel, `prep.py` reads it as though a node produced it, and every
actual writer is outside the graph — two MCP tools and one operator service. The
channel exists in the schema for a producer that does not exist.

It is not isolated. Of the keys MCP tools write directly, most are also
node-owned:

| Key written by MCP | Also used in `orchestration/nodes` |
|---|---:|
| `issues` | 32× |
| `generation_requests` | 12× |
| `shot_matrix_ref` | 12× |
| `target_runtime_seconds` | 12× |
| `target_scene_count` | 6× |
| `visual_refs` | 5× |
| `resolved_config` | 4× |
| `idea` | 3× |
| `_validation_reports` | 2× |

## 3. Why extraction did not help

Extracting a collaborator from `StudioRuntime` changes where *state lives* while
every consumer still asks the runtime for it. Observable behaviour is identical,
so nothing gets smaller — the 10 delegating methods I added made it measurably
bigger.

The same trap applies to the state dict. Moving `resolved_config` into a typed
object without changing who writes it just relocates the violation.

**The consumer set has to move before the structure can.** That is the design
lesson from the failed attempt.

## 4. The design principle that is missing

The system has no answer to a basic question: **who may write a given piece of
state?**

Three different things are conflated in the same dict:

1. **Graph channels** — values nodes produce and reducers merge
   (`issues`, `generation_requests`, `artifact_refs`). Owned by `orchestration`.
2. **Session/operator intent** — what the human asked for (`idea`,
   `target_runtime_seconds`, `constraints_hints`, `profile_stack`). Owned by
   whoever accepts the request, i.e. `operations`.
3. **Derived configuration** — `resolved_config`, produced by `config` from (2).

Right now all three are the same dict, written by whoever finds it convenient.
The graph reads `resolved_config` expecting (1); MCP writes it as (3). The
schema declares the keys but not the *authority*.

## 5. What an improvement looks like

Not a file split. Three changes, in dependency order:

**Step 1 — name the authority.** For each of the ~78 state keys, record one
owner: `orchestration` (node-produced channel), `operations` (operator intent),
or `config`/`studio` (derived). This is a declaration, not a refactor, and it is
the thing whose absence caused the defect. It can be a table in the schema module
plus a test that fails when a layer writes a key it does not own — the same shape
as the AST guards already in the repo, and cheap.

**Step 2 — make the writers honest.** With authority declared, the violations
become mechanical: an MCP tool writing `resolved_config` is wrong, and the fix is
to route it through the owner (operator intent in, resolved config out) rather
than assigning into the dict. A handful of keys, each a small change.

**Step 3 — only then reconsider structure.** Once `resolved_config` and the
operator-intent keys have real owners, `StudioRuntime`'s surface shrinks on its
own, because the 16 handlers that only want project state no longer need it, and
the keys it persists are the ones it actually owns. Decomposition becomes a
consequence of correct ownership rather than a goal pursued directly.

## 6. Why this ordering matters

Every failed attempt so far — my `ProviderRegistry` extraction, and to a lesser
extent the whole `StudioRuntime`-as-god-object framing — tried to fix the shape
before fixing the ownership. The shape is downstream.

There is also a measurement consequence: the repo currently has no way to detect
a layer writing state it does not own. That is why ten cross-layer violations
sit in the tree unnoticed, and why a guard is the highest-value first step — it
is what makes the rest verifiable rather than a matter of my judgement.

## 7. What I am not claiming

- I have not verified all ~78 keys. The table in §2 covers the keys MCP writes;
  the full set needs the same treatment.
- I do not know whether some of the ten shared keys are *legitimately* shared
  (e.g. `idea` may be operator intent that a node then refines). That is exactly
  what step 1 decides, and it should be decided per key rather than in bulk.
- Step 1's guard is not designed. Whether it is an AST check, a runtime
  assertion, or a schema-level declaration is open.
