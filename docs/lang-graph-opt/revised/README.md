# LangGraph Optimization Review - Revised

Date: 2026-06-22

This folder is a revised, codebase-grounded version of the notes in `docs/lang-graph-opt/`.
The original files are left untouched.

## Why This Revision Exists

The original analysis is directionally useful. It correctly identifies missing LangGraph
interrupts, untyped graph state, stub subgraphs, full-state copies, context truncation, and
weak matrix write-back.

The main correction is architectural:

**The Master Film Matrix should not replace the artifact system as an in-memory source of
truth.** This product is MCP-first and audit-first. Durable typed artifacts, metadata,
review packages, approval records, and checkpoints are the product contract. Graph state
should coordinate work and hold resumable execution context. Artifacts should remain the
durable source of truth.

The target design is therefore:

- LangGraph state is typed, resumable, and small enough to checkpoint.
- ArtifactStore remains authoritative for durable outputs.
- The Master Film Matrix becomes living by versioned patches, row status transitions, and
  row-level provenance.
- Human gates use real LangGraph interrupts with a checkpointer.
- MCP tools drive graph resume, inspection, approval, revision, rollback, and generation.
- Subgraphs are introduced where they reduce real complexity, starting with approval and QC.

## Files

- `01-corrected-findings.md` - what the original analysis got right, what it overreached on,
  and the current root causes.
- `02-target-architecture.md` - the desired graph, state, artifact, matrix, interrupt, and
  subgraph design.
- `03-implementation-roadmap.md` - phased implementation plan with tests and risks.

## Primary Conclusion

The next high-leverage change is not "move everything into LangGraph state."

The next high-leverage change is:

1. Compile the graph with a checkpointer and replace recursion-limit gates with `interrupt()`.
2. Add a typed state contract with reducers for append-only channels.
3. Add artifact version allocation and dependency metadata.
4. Treat matrix updates as versioned row patches, not whole-artifact rewrites.
5. Make MCP approval and revision tools resume the graph instead of manually mutating runtime
   state.

This keeps the product vision intact while using LangGraph for what it is strongest at:
durable execution, human-in-the-loop workflow, streaming, routing, and recoverable state.
