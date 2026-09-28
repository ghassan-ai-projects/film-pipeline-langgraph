# QC has one implementation: the parallel subgraph

Status: **decided 2026-09-28.** This document records the behaviour decision
required by `docs/modularity-improvements/02-graph-execution-has-two-executors.md`
before that slice changed any code.

## The finding

`build_graph` wires the `qc` phase to the **parallel subgraph**
(`orchestration/subgraphs/qc.py::build_qc_subgraph`). The repair loop's
`_PHASE_NODES["qc"]` pointed at the **sequential** `orchestration/nodes/qc.py::qc_node`.
`_PHASE_NODES` is what `repair_phase_node` re-runs on a revision round, and what
`studio/_graph_exec.run_phase_node` runs on a stalled resume.

So a film's **first** QC pass and its **repair** QC pass ran different code, and
the two differed on five steps:

| Step | Subgraph (first pass) | `nodes.qc.qc_node` (repair, manual) |
|---|---|---|
| Validator set | 6 hard-coded workers, classes imported by name | registry-driven `_execute_phase_validators` |
| Phase-gate updates | sets `current_phase` / approval flags in `reduce_qc_reports` | `_phase_gate_updates(..., gate="qc")` |
| Matrix patch from findings | **no** | `_emit_matrix_patch_from_findings` |
| Consensus report | **no** (its docstring claimed one) | `_synthesize_consensus_report` |
| Issues from findings | **yes** — `_findings_to_issues` | **yes** — `_append_validator_report` |

Neither was a superset of the other, so "whichever behaviour is intended, one of
the two paths is wrong" was the correct reading.

## Decision

**The parallel subgraph is canonical.** `_PHASE_NODES["qc"]` is
`build_qc_subgraph()` — the same object `build_graph` registers.

Reasons, in order of weight:

1. **It is the wired production path.** Every film's first QC pass runs it, and
   that is the pass whose result the human gate reviews. Making the rarely-taken
   path canonical would change what the common path does.
2. **It is the documented design.** `documentation/architecture-blueprint.md`
   Phase 8 defines QC as multi-level validation (clip, scene, act, movie); the
   subgraph is the LangGraph `Send` fan-out built for it, and it runs the six
   validators concurrently.
3. **It keeps the fan-out channel contract honest.** `_qc_reports` and
   `_qc_raw_reports` are `Annotated[..., operator.add]` specifically because the
   QC workers write them concurrently. That declaration is only meaningful on a
   path that actually fans out. A sequential node writing a concurrent channel
   makes the reducer look arbitrary.

## The three capabilities the sequential node had, and where each went

The decision is not "delete the other one and lose its steps". Each had to be
placed deliberately:

1. **Matrix patch from per-row findings.** Kept. `reduce_qc_reports` now calls
   `_emit_matrix_patch_from_findings`, which is imported from `nodes.qc` — the
   module that owns the `MatrixPatch` construction and `_track_matrix_row_updates`.
   The subgraph's workers do not currently populate `_pending_row_updates`, so this
   is a no-op today; it is wired so the capability is not silently absent if a
   worker gains per-row findings, and the wiring is asserted by a test rather than
   left as an aspiration.
2. **Consensus report synthesis.** Kept, and the *defect* is fixed rather than
   the step. `nodes.qc._synthesize_consensus_report` ran the clip-validator agent
   for a free-text synthesis; its docstring in the subgraph claimed the same
   result while building nothing. The subgraph now produces the consensus through
   `nodes.qc._build_consensus_if_needed`, which is the *deterministic* builder
   (`validation.consensus.ConsensusBuilder`) over the reports the workers actually
   collected. That is the stronger of the two: it cannot disagree with the reports
   it summarises. The agent-based synthesis is dropped, and dropping it is part of
   the decision — two consensus producers was the defect.
3. **Registry-driven validator dispatch.** Not kept as a second runner. The
   subgraph's six workers are the validator set for QC; `nodes.qc._VALIDATOR_RUNNERS`
   keeps its non-QC members (`script`, `visual_dev`, `gen_planning`, `shot_bible`,
   `post`, `assembly`, `delivery`) for the phases that still call `_run_validators`
   directly. Its `"qc"` membership is removed, because a phase with two runners is
   the finding this document exists to close.

## What this does not establish

- **That the divergence produced a wrong artifact in a real run.** 02 says the
  same. Finding it required a revision round at QC, and no test drove one through
  both paths. The decision closes the *duplication*; it does not date the defect.
- **That the subgraph's validator set is the right six.** `_VALIDATOR_MAP` names
  six validators against `validation/validators/__init__.py`'s 15-entry
  `MVP_VALIDATORS` matrix. Which nine are missing from QC is a product question,
  not a modularity one; changing the set here would be a behaviour change this
  slice has no evidence for.
- **That the first pass and the repair pass now share a checkpoint.** They share
  a callable. Whether a *resumed* thread re-enters QC with `_qc_raw_reports`
  already populated is a separate question about checkpoint replay, and it is
  unchanged by this decision.

## Implementation note: the package cycle this decision created, and what it cost

Making the subgraph the QC phase node gave `nodes` a dependency on `subgraphs`
(`_repair_loop._PHASE_NODES["qc"]`) while `subgraphs.qc` already depended on
`nodes` (for the shared matrix-patch/consensus steps). Three attempts were needed,
and the failures are worth recording because two of them were *invisible to the
test suite*:

1. **The shared steps moved to `nodes/qc_steps.py`.** `nodes -> subgraphs` and
   `subgraphs -> nodes` then closed a two-module cycle. `measure.py` caught it.
2. **The compiled accessor moved to `orchestration/qc_phase_node.py`.** Worse: it
   produced a real `ImportError: cannot import name 'qc_phase_node' from partially
   initialized module` whenever `subgraphs.qc` was imported first. The whole test
   suite was green; only importing that module directly, or reading Enola, showed
   it. `_PHASE_NODES` compiling the subgraph at import time was the cause, so the
   table now holds a deferred `_LazyQcPhaseNode` and consumers call
   `resolved_phase_node(phase)`.
3. **Final shape.** `orchestration/qc_steps.py` (root, leaf-only) owns the shared
   consensus builder; `subgraphs.qc` owns the matrix-patch emitter (it is QC's own
   output); every cross-module import among these is function-level with a
   `# lazy:` reason. `measure.py` reports the module-level SCC count back at 1
   (`mcp.contract <-> mcp.registry`), and every import order of the four modules
   involved succeeds.

**What Enola still reports, and why it is not a defect.** Enola's `cycles`
explainer collapses every module directly under `orchestration/` into a single
`orchestration` node. With `qc_steps` at the root, `subgraphs -> orchestration` and
`orchestration -> subgraphs` look like a cycle even though `subgraphs.qc` loads no
`nodes` module at runtime. The measured evidence that it is a modelling artifact
rather than a defect:

- `measure.py` module-level SCCs: **1** (only `mcp.contract <-> mcp.registry`).
- `tests/unit/architecture/test_package_acyclicity.py`: passes.
- Every import order of `orchestration.qc_steps`, `nodes.qc`, `subgraphs.qc`, and
  `nodes` succeeds in a fresh interpreter.

The alternative shapes were tried and are worse: putting `qc_steps` under `nodes`
or `subgraphs` recreates a real cycle, and deleting the shared builder means two
consensus implementations, which is the defect this document exists to close.
