# Architecture Roadmap Execution — Program Charter

This directory governs the implementation of the accepted architecture review
([`../architecture-review.md`](../architecture-review.md), critic-verified PASS in
[`../reviews/arch-review-critic.md`](../reviews/arch-review-critic.md)). The review is the source of
finding IDs (B-F*, DF-F*, O-F*, Flx-F*, C-*) and of the P0/P1/P2 roadmap; this charter defines the
execution bar, the phase batching, and the mandatory per-phase loop.

## The bar (end-state definition)

The global bar is [`../quality-criteria.md`](../quality-criteria.md) plus the AGENTS.md "Done"
definition. Concretely, the program is done when **all** of the following hold:

1. Every roadmap item (P0 1–9, P1 1–13, P2 1–6) is either implemented or carries a recorded,
   reasoned deferral in this directory. Silence is not a decision.
2. `make ci-check` passes at every phase commit (ruff format + lint, mypy strict, pytest with ≥90%
   coverage, `uv build`).
3. Behavior evidence: every changed behavior has tests that prove it (not merely cover lines);
   JSON/MCP payload shapes stay stable unless an item explicitly changes them; MCP-first contract
   and sub-package boundaries are preserved.
4. Review bar per phase: three independent post-implementation reviews from distinct lenses each
   return PASS with all dimension scores ≥4/5; two independent plan reviews approved the plan before
   implementation. Any REVISE loops until resolved.

## Per-phase loop (mandatory)

1. **Plan** — write `phase-NN-<slug>-plan.md`: scope (roadmap item IDs), current ground truth with
   `file:line`, target design, files to touch, test plan, risks, non-goals.
2. **Two plan reviews** — independent reviewers, one *solid architecture* lens, one *completeness &
   correctness* lens. REVISE findings are folded back into the plan before any code.
3. **Implement** — clean-code principles (AGENTS.md): smallest correct change, Pydantic/frozen
   dataclasses at boundaries, specific exceptions, no speculative abstraction, tests in the same
   change.
4. **Three reviews** — distinct lenses (e.g. correctness & test evidence; architecture, boundaries &
   clean code; behavior preservation & regression risk). Each scores Grounded/Specific/Complete/
   Regression-safety 1–5 and returns PASS or REVISE.
5. **Loop** until every reviewer PASSes and `make ci-check` is green.
6. **Commit** (conventional message naming the roadmap IDs) and update the phase index below.

## Phase index

| Phase | Scope (roadmap items) | Status |
|---|---|---|
| 01 | State-safety guardrails: D1 channel registry + parity test (+DF-F2), D6 resume integrity (+O-F4), B-F4 mock fixtures relocation | **done** — committed; 3/3 reviews PASS (all scores ≥4); ci-check green (2004 passed, cov 92.49%) |
| 02 | Truth defaults: Flx-F10 imagen pricing delegation, Flx-F9 config-contract test, O-F6 truthful `get_blockers`, O-F10 logging bootstrap | planned |
| 03 | Law & docs truth: B-F8 boundary law amendment + CI edge scan (warn mode), C-6 docs truth pass | planned |
| 04 | Generation lifecycle behind `GenerationExecutor` [D2] | planned |
| 05 | Typed event catalog + single audit implementation [D4] | planned |
| 06 | Run correlation + node lifecycle events [P1#3] | planned |
| 07 | Unify QC core [D3] | planned |
| 08 | Approval semantics unification [D5] | planned |
| 09 | Provider catalog [Flx-F1] + registry policy alignment [Flx-F3] | planned |
| 10 | Phase single-source-of-truth + agent-table invariants [Flx matrix, Flx-F2] | planned |
| 11 | Error taxonomy end-to-end + wire-or-delete safety channels [O-F5/O-F8/O-F9, D13/DF-F6] | planned |
| 12 | Artifact-ref chokepoint [D8/C-3.2] | planned |
| 13 | Boundary repairs [D12] + single rollback-record producer [C-1.2/D13] | planned |
| 14+ | P2 bets (ToolContext DI, generic diff_updates, hotspot splits, mode-name unification, schema ratchet, enum follow-through) — batched after P1 lands | planned |

Sequencing follows the review's own principles: guardrails before refactors; characterize before
touching spec-bearing helpers; docs-as-law early; behavior-preserving envelopes around money/QC/gate
paths. Guardrails ("what NOT to do", review §Guardrails) bind every phase.

## Rules of engagement for reviewers

Reviewers are independent agents; they verify claims against source themselves rather than trusting
the author. Findings must cite `file:line`. Scores below 4 on any dimension force REVISE. Review
artifacts are appended to the phase plan file under a "Review record" section.
