# Reconciliation notes (working)

Cross-source discrepancies found while combining the audits, the two independent
architect proposals, and the enola snapshot. Each entry states the ground truth
and what must be corrected in the synthesis (`01`–`05`). This file is a working
record; its outcomes are folded into the synthesis documents, which are
authoritative.

Commit for every measurement below: `fb85baa` (`modular-app`).

---

## R1 — Artifact-kind counts: two sources disagree; ground truth is 47 / 45 / 39

**Claim A** (`audit/07-artifact-refs-and-schemas.md`, F-ARTIFACT-08): "registry 47
kinds vs `ArtifactType` 45 (8 registry-only / 3 enum-only)".

**Claim B** (`design/proposal-A-boundaries.md`, F-AKIND-01): "`registry.py:126`
registers 54 kinds vs `schemas/_base.py:27` `ArtifactType` with 45 (12
unregistered, 3 unstorable)".

**Ground truth** (measured with the repo venv):

```bash
.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "src")
from film_pipeline.artifacts.registry import REGISTRY
from film_pipeline.schemas._base import ArtifactType
enum = {e.value for e in ArtifactType}
exact = set(REGISTRY._exact)
print(len(exact), len(enum), sorted(exact - enum), sorted(enum - exact))
PY
```

| Measure | Value |
|---|---|
| `REGISTRY._exact` (artifact ids) | **47** |
| `ArtifactType` enum members | **45** |
| Shared | **39** |
| Registry-only | **8**: `consensus_report`, `cost_estimate`, `execution_brief`, `project_profile`, `scope_contract`, `shot_matrix`, `story_bible`, `subtitles` |
| Enum-only | **6**: `checkpoint`, `clip`, `invalidation_report`, `last_frame`, `mid_frame`, `rollback_record` |
| Enum-only covered by a registry **prefix** | `checkpoint_`, `invalidation_report_`, `rollback_record_` (3) |
| Enum-only with **no** registry entry at all | `clip`, `last_frame`, `mid_frame` (3) |

**Verdict.**

- Claim A is directionally right; its registry-only count (8) is exact, but its
  enum-only count (3) is wrong — it is **6** (3 prefix-covered + 3 uncovered).
- Claim B is **wrong in method**: it compared `_by_kind` (kind slugs such as
  `film.studio/script`, 54 of them) against `ArtifactType` snake_case values
  (`script`, 45). Those are different namespaces, so "12 unregistered" is not a
  real set difference. `_by_kind` is 54 rather than 55 because one spec
  (`project_config`) is registered both exactly and as the `project_config_v`
  prefix.
- **Correct statement for the synthesis:** 47 registered ids vs 45 enum values,
  39 shared; 8 registry ids have no enum value, and 6 enum values have no exact
  registry entry (3 are reachable only through prefixes; `clip`, `last_frame`,
  `mid_frame` have no registry entry at all).

**Action:** use the ground-truth numbers in `02-duplication-ledger.md`; note
Claim B's method error in `reviews/adversarial-review.md` as a reconciliation the
design had to correct.

---

## R2 — Cycles: enola finds 5; audit 14 reported 1 (not a contradiction)

`audit/14` checked only top-level package 2-cycles in its own AST scan and
reported `app ↔ mcp`. Enola (module granularity, all cycle lengths) reports 5:

1. `agents/prompt_templates` ↔ `agents/prompt_templates/defaults`
2. `app` ↔ `mcp` and 5 sub-modules (7 members) — the larger form of the audit's finding
3. `graph` ↔ `graph/nodes` ↔ `graph/orchestrator_validators` ↔ `graph/subgraphs`
4. `providers` ↔ `providers/adapters`
5. `schemas` ↔ `schemas/registries`

**Action:** `01-ownership-map.md` records all five; `03-target-architecture.md`
must show how the layer law breaks them. Three (1, 4, 5) are façade-re-export
cycles and are cheap; two (2, 3) are design-level.

---

## R3 — The artifact-contract candidate must not re-own what storage already owns

`audit/07` §6.2 lists what the storage owner already covers: layout, root
resolution, atomic writes, path helpers, the kind catalog, version numbering,
checksum, immutable-schema checks, approve/supersede, renderers. The
`artifacts.contract` candidate (from `audit/07`) and `proposal-A`'s decision to
**not** split the artifact catalog out of `storage` must be reconciled in `03`:
the audit's leaks are about *callers re-deriving* what storage owns, not about
storage owning too much.

**Action:** in `03`, express the artifact-contract candidate as an *enforcement
and derivation* concern (single formatter, store-decided version, enum↔registry
agreement guard), not as a second storage module.

---

## R4 — Verifier verdicts supersede author claims

Where `reviews/verify-*.md` marks a finding DOWNGRADED or REJECTED, that verdict
wins and the finding is corrected in `02`. This file is not updated per finding.
