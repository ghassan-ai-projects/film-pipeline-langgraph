# 02 — Graph execution has a second executor, and QC has two implementations

**Priority: 1 (divergent duplicates of the core lifecycle).** Size: S–M.

AGENTS.md: *"Delete dead branches and divergent duplicates … second implementations of
one lifecycle should be removed."* This finding is two of those, nested.

## Finding A — `studio` hand-rolls a graph executor

`StudioGraphState` declares how each accumulating channel merges
([state_schema.py:215–263](../../src/film_pipeline/orchestration/state_schema.py)).
LangGraph applies those annotations when the compiled graph runs.

`studio/_graph_exec.run_phase_node`
([_graph_exec.py:507](../../src/film_pipeline/studio/_graph_exec.py)) runs a phase node
**outside** the graph: it looks the node up in `_PHASE_NODES`, calls it, and merges the
result with **its own hand-written reducer table**. The two tables disagree:

| Channel | Graph (`StudioGraphState`) | `run_phase_node` |
|---|---|---|
| `artifact_refs` | `merge_unique` | `merge_unique` |
| `issues` | `merge_issues` | `merge_issues` |
| `validation_report_refs` | `merge_unique` | `merge_unique` |
| `generation_requests` | `merge_generation_requests` | `merge_generation_requests` |
| `_routing_decisions` | last write | **dedupe-append** |
| `_validation_reports` | last write | **dedupe-append** |
| `_qc_reports` | `operator.add` | **last write** |
| `_qc_raw_reports` | `operator.add` | **last write** |

It is reachable in production: `approve_phase` falls back to
`advance_to_next_phase -> run_phase_node` when there is no graph checkpoint for the
thread, and **also when a resume "stalls"** (audited as
`resume_stalled_manual_advance`,
[_graph_exec.py:235](../../src/film_pipeline/studio/_graph_exec.py)).

**How much of the disagreement is observable today** (read, not executed):
`_routing_decisions` is benign because `_agent_handoff` returns the full list, so
append-dedupe and last-write converge. `_qc_*` is written only inside the QC subgraph,
which the manual path never runs. `_validation_reports` is the live one: the QC
subgraph returns it as a *replacement* (`reduce_qc_reports`), which the manual path
would append instead. The defect class is the hand-maintained copy itself — a new
annotated channel is silently mis-merged by the manual path, and no test ties the two.

Supporting evidence that this belongs to `orchestration`, not `studio`: to do its job,
`_graph_exec` imports three private orchestration names — `services._SERVICES_CTX`,
`nodes._run_validators`, `nodes.approval._PHASE_NODES` — i.e. 3 of the 5 remaining
cross-package private-symbol imports in the tree.

## Finding B — QC runs one implementation first, another on repair

The graph wires QC as the parallel subgraph:
`builder.add_node("qc_node", build_qc_subgraph())`
([graph_factory.py:92](../../src/film_pipeline/studio/graph_factory.py)).

`_PHASE_NODES["qc"]` is the **sequential** `orchestration.nodes.qc.qc_node`
([_repair_loop.py:41](../../src/film_pipeline/orchestration/nodes/_repair_loop.py)).
`_PHASE_NODES` is what `repair_phase_node` re-runs on a revision round
([_repair_loop.py:215](../../src/film_pipeline/orchestration/nodes/_repair_loop.py)),
and what the manual executor above runs.

So a film's **first** QC pass and its **repair** QC pass run different code:

| Step | Subgraph (first pass) | `nodes.qc.qc_node` (repair, manual) |
|---|---|---|
| Validator set | 6 hard-coded workers, classes imported by name | registry-driven `_execute_phase_validators` |
| Phase-gate updates | sets `current_phase` / approval flags inline | `_phase_gate_updates(..., gate="qc")` |
| Matrix patch from findings | **no** | `_emit_matrix_patch_from_findings` |
| Consensus report | **no** (its docstring says it builds one) | `_synthesize_consensus_report` |
| Side-effect propagation | **no** | `_propagate_side_effects` |

Whichever behaviour is intended, one of the two paths is wrong.

Reproduced — identity of each graph-wired node vs `_PHASE_NODES`:

```python
g = build_graph(runtime_root=tmp)
for phase, fn in _PHASE_NODES.items():
    spec = g.builder.nodes[f"{phase}_node"]
    print(phase, getattr(spec.runnable, "func", spec.runnable) is fn)
```

```text
intake True · constitution True · development True · script True · visual_dev True
shot_bible True · gen_planning True · generation True · qc False · post True · delivery True
```

## Recommendation

### Slice 1 — one reducer source (small, do first)

Delete the literal reducer table in `run_phase_node` and derive it from
`typing.get_type_hints(StudioGraphState, include_extras=True)`: every
`Annotated[..., reducer]` field uses its reducer, every other key is last-write —
exactly LangGraph's rule. Move the function to `orchestration` as a public
`apply_node_update(state, update)` so `studio` stops importing `_PHASE_NODES`.

**Falsifiable check:** a parametrized test over every annotated channel that runs a
stub node through both the compiled graph and `apply_node_update` and asserts equal
state. It fails today on 4 channels.

### Slice 2 — one QC implementation

Decide which QC is canonical (the parallel subgraph is the documented Phase-7 design;
the sequential node carries the matrix-patch and consensus steps). Make the other a
thin caller of it, or delete it, and point `_PHASE_NODES["qc"]` at the same object the
graph wires. This is a behaviour decision — record it in `documentation/` before
changing code.

**Falsifiable check:** a test asserting `_PHASE_NODES[phase]` is the same callable the
graph builder registers for every phase. It fails today on `qc` only; the other ten
phases already agree.

### Slice 3 — graph execution lives with the graph

Move `studio/_graph_exec.py` + `studio/_resume.py` into `orchestration` (e.g.
`orchestration/execution.py`) behind a small public API (`run`, `resume_after_approval`,
`advance_manually`), taking the runtime's persist/audit through `RuntimePort`. `studio`
keeps the composition (`graph_factory` wiring services and checkpointer). This removes
the three private reach-ins above without adding a port — `RuntimePort` already exists.

Re-measure `StudioRuntime` after this; `08`'s 27-method count should drop by the
graph-execution delegates.

## What this does not establish

Whether the QC divergence has produced a wrong result in a real run. It requires a
revision round at QC; no existing test drives one through both paths. Slice 2's test
is the cheapest way to find out.
