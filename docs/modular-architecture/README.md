# Modular architecture: review and decision

**Status (2026-09-25): migration in progress by user direction.** The user chose to pursue the 20-module target despite [the earlier independent decision](06-independent-review-and-decision.md). That review remains evidence of risks and inconsistencies, not the current stop decision. The 21-phase roadmap is a source of candidates, not a literal checklist: each move must preserve behavior and reduce a measured Enola finding or a verified ownership violation. [The progress ledger](implementation-progress.md) records the live order and results.

This is an **audit and design package with one small implementation example**, not a completed architecture migration. The independent review changed no source behavior; the later phase-sequence example migrates one internal rule. The baseline studied by the original program is commit `fb85baa0e6b769b709791a96a89980089304bf13`; the same commit was checked for the original decision. Recheck source anchors and counts against the current working tree before using them.

Absolute workstation paths in the historical records were normalized to
`${REPO_ROOT}`. Before replaying a command that uses it, run
`export REPO_ROOT="$(git rev-parse --show-toplevel)"` from this repository.
Printed output in those records is historical; re-run the command for current
output.

## Decision in brief

Migrate toward the target modules in small, behavior-preserving rounds. Prioritize measured cycles and duplicate ownership. Preserve the MCP operator boundary, typed artifacts, human gates, and checkpoint recovery required by [the architecture blueprint](../../documentation/architecture-blueprint.md) and [the product standard](../../documentation/product-completion/00-product-standard.md). Defer behavior repairs until the migration is complete.

The independent review found that the proposed design adds 20 target modules, a custom `ModuleContract` declaration in each package, a large AST guard suite, and 21 migration phases before the critical runtime seams are resolved. Its own adversarial reviews report unsatisfied roadmap and evidence gates. Those are reasons to revise the plan, not reasons to discard the evidence.

## Read order

The first implemented example is [reference migration 01: phase sequence](examples/01-phase-sequence.md). It is a small ownership extraction with migrated consumers and tests; it does not approve the old 20-module program.

Use the [implementation progress tracker](implementation-progress.md) for per-slice scope, reviews, validation, Enola verdicts, coverage, and commits.

1. [06 — independent review and decision](06-independent-review-and-decision.md): current recommendation, direct code checks, priorities, and delivery gates.
2. [Bar conformance](reviews/bar-conformance.md): honest A1–A9/B1–B9 assessment of the original program.
3. [00 — methodology](00-methodology-and-quality-bar.md): the original audit's definitions and desired quality bar. Its historical process requirements do not turn unverified claims into facts.
4. [01 — ownership map](01-ownership-map.md) and [02 — duplication ledger](02-duplication-ledger.md): discovery evidence. Their snapshots and totals are historical and internally out of sync with the current audit corpus. Resolve a finding against the source and its verifier before using it.
5. [03 — target architecture](03-target-architecture.md), [04 — extraction roadmap](04-extraction-roadmap.md), and [05 — enforcement](05-enforcement-and-guard-tests.md): the requested migration target and historical sequencing proposals. Apply each boundary against current source and the live quality gates; their stale counts and behavior-changing clauses are not automatic instructions. **`05` is a design that was never implemented** — `tests/architecture/` and `src/film_pipeline/architecture.py` do not exist, `ModuleContract` has no occurrences under `src/`, and 15 of the 16 guards it enumerates are absent. Its edge law is documentation-only, so nothing mechanically blocks a forbidden import.

## Evidence inventory

- `audit/01`–`audit/14`: domain-specific finding records. The files currently contain 191 `F-` headings and 189 live `Severity` bullets. A heading is not a verified finding; at least one later verdict rejects a previously counted finding.
- `reviews/verify-01`–`verify-20`: two rounds of finding-level review. There is no `verify-21.md` despite the old README's reference to it.
- `reviews/adversarial-{coverage,evidence,architecture,roadmap}.md`: independent attacks on coverage, reproducibility, target design, and phase shippability. Read the revision-2 addendum at the end of `adversarial-roadmap.md`.
- `design/proposal-A-boundaries.md` and `design/proposal-B-enforcement.md`: independent input proposals, not adopted contracts.
- `design/prototype-enforcement/`: ignored local prototype and backup material, retained only for reference in this workspace. It is not part of the deliverable and does not prove the guard suite can pass the repository gate.
- `enola-architecture-facts.md` and `reconciliation-notes.md`: baseline measurements and corrections. `enola-out/` is generated local data and remains ignored by Git.

## How to use a finding

For an implementation change, identify the behavior and source anchor, read the relevant audit finding and its latest `verify-*` verdict, reproduce the problem on the target commit, and write a behavior test before changing the owner. The original finding's severity, class, and suggested module are hypotheses until checked. Keep a change shippable with `make ci-check` and explicit persisted-data compatibility checks where applicable.

## Reproducible package checks

From the repository root:

```bash
git rev-parse HEAD
rg -n '^### F-' docs/modular-architecture/audit/*.md | wc -l
rg -n '^- \*\*Severity:\*\*' docs/modular-architecture/audit/*.md | wc -l
rg --files docs/modular-architecture/reviews | rg '/verify-[0-9]+\.md$' | wc -l
git check-ignore -v docs/modular-architecture/enola-out/facts.jsonl
```

The counts above inventory text; they do not establish audit correctness or implementation readiness.
