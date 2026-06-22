# Orchestrator-Led Generation Fix

This directory defines the fix strategy for the Camino-style film generation gap:

- the shot bible under-specifies movement structure
- runtime drifts below the target film duration
- shot rows miss generation-critical references
- generation planning and dispatch do not reliably reach provider execution

The core decision is simple:

> The orchestrator owns the film-level outcome. Specialist agents support it, but the orchestrator is responsible for enforcing structure, validating completeness, and refusing to advance weak artifacts.

## Documents

- [01-root-cause.md](./01-root-cause.md) — evidence-based diagnosis
- [02-orchestrator-design.md](./02-orchestrator-design.md) — orchestrator responsibilities and agent contracts
- [03-acceptance-criteria.md](./03-acceptance-criteria.md) — done criteria for the improved flow

## Scope

This is a design and implementation-planning package. It does not change runtime behavior by itself.
