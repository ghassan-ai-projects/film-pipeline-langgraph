# 08 — Audit: Validation, Review, Scoring, and Human Gates

- **Repo:** `${REPO_ROOT}`
- **Branch:** `modular-app`
- **Commit audited (HEAD):** `fb85baa0e6b769b709791a96a89980089304bf13` (`git rev-parse HEAD`)
- **Working tree at audit time:** clean (`git status --porcelain` → empty)
- **Conforms to:** `docs/modular-architecture/00-methodology-and-quality-bar.md` (§1.6 evidence,
  §1.7 finding format, §2 bar A)
- **Cluster:** validators score and produce statuses; review builds packages, diffs, and consensus;
  the graph decides revision loops and human gates.
- **Verification (bar A6):** independently verified in
  `docs/modular-architecture/reviews/verify-08.md` at the same HEAD — **7 CONFIRMED,
  4 CONFIRMED-with-correction, 0 REJECTED** (187 anchors re-resolved, 101 quotes checked).
  Corrections applied to this file: (1) F-VR-02's absolute "not reachable end-to-end" verdict is
  replaced with the exact statement (no *validator* can emit `NEEDS_REVISION`; the LLM consensus
  path *can*, and it reaches a human-viewable artifact; the router's `revise` tier is dead);
  (2) F-VR-05 severity recomputed Critical 16 → **High 12** (writer A cannot succeed, so the race is
  latent); (3) F-VR-09's drift proof no longer claims the MCP path "fails loudly" (it degrades
  silently); (4) F-VR-11 severity relabelled Low → **Medium (2×3=6)**; (5) §1.2 counts corrected;
  (6) F-VR-06 "six" → **seven** enumerated sites (six production derivations + one test replica);
  (7) the `src/film_pipeline/graph/orchestrator_state.py:156-159` quote in F-VR-05 split into three verbatim quotes (§1.6.2);
  (8) F-VR-07's delivery claim qualified to the `get_validation_report` fallback; (9)
  F-VR-03/F-VR-07 "no test fails" softened in light of
  `tests/unit/graph/test_qc_validator_dispatch.py`. One verifier sub-claim is **not** adopted and is
  corrected here: verify-08's M3 says the registered `consensus_report` spec/renderer "can never
  fire" — false, because the artifact registry is keyed by *artifact id* (`src/film_pipeline/artifacts/registry.py:100-107`)
  and `src/film_pipeline/graph/nodes/qc.py:109` saves under the id `consensus_report`, so the renderer does fire; the
  real defect is the wrong `artifact_type` metadata (F-VR-12). Five seams missed by the first pass are
  added as **§3.2 (added after verification)**: F-VR-12..F-VR-15 plus a coverage correction (M5).

Every anchor below was read at the recorded commit. Quotes are verbatim, ≤3 lines.

---

## 1. Coverage

### 1.1 In-scope paths read in full or in the cited line range

| Path | Lines | Read | Verdict |
|---|---|---|---|
| `src/film_pipeline/validation/__init__.py` | 27 | full | consumer/re-export only |
| `src/film_pipeline/validation/base.py` | 321 | full | **has findings** (F-VR-02, F-VR-08, F-VR-11) |
| `src/film_pipeline/validation/thresholds.py` | 40 | full | **has findings** (F-VR-02, F-VR-11) |
| `src/film_pipeline/validation/registry.py` | 46 | full | **has findings** (F-VR-01) — dataclass registry, never populated |
| `src/film_pipeline/validation/consensus.py` | 138 | full | **has findings** (F-VR-02, F-VR-04, F-VR-05) |
| `src/film_pipeline/validation/validators/__init__.py` | 167 | full | **has findings** (F-VR-01, F-VR-02) — 15-entry `MVP_VALIDATORS` |
| `src/film_pipeline/validation/impl/__init__.py` | 19 | full | consumer/re-export only |
| `src/film_pipeline/validation/impl/assembly.py` | 290 | full | **has findings** (F-VR-01, F-VR-07) |
| `src/film_pipeline/validation/impl/script_structure.py` | 240 | entry block 120-160 + grep | **has findings** (F-VR-01 — confirmed drift) |
| `src/film_pipeline/validation/impl/dialogue_voice.py` | 250 | entry 167-183 + score 210-250 | clean locally (entry agrees with MVP) |
| `src/film_pipeline/validation/impl/prompt_readiness.py` | 244 | entry 152-167 + grep | clean locally (entry agrees with MVP) |
| `src/film_pipeline/validation/impl/reference_usability.py` | 273 | entry 185-200 + grep | clean locally (entry agrees with MVP) |
| `src/film_pipeline/validation/impl/scene_continuity.py` | 297 | entry 205-222 | clean locally (entry agrees with MVP) |
| `src/film_pipeline/validation/impl/delivery_completeness.py` | 198 | entry 100-118 | **has findings** (F-VR-01, F-VR-07) — absent from `MVP_VALIDATORS` |
| `src/film_pipeline/review/__init__.py` | 21 | full | consumer/re-export only |
| `src/film_pipeline/review/actions.py` | 73 | full | **has findings** (F-VR-06) |
| `src/film_pipeline/review/diff.py` | 70 | full | single-owner, guard-tested (Clean concern C4) |
| `src/film_pipeline/review/generator.py` | 92 | full | **has findings** (F-VR-09) |
| `src/film_pipeline/graph/orchestrator_validators/__init__.py` | 40 | full | second validator family (F-VR-07 blast radius) |
| `src/film_pipeline/graph/orchestrator_validators/_shared.py` | 66 | full | second validator family (F-VR-07 blast radius) |
| `src/film_pipeline/graph/orchestrator_validators/brief.py` | 238 | full | second validator family (F-VR-07 blast radius) |
| `src/film_pipeline/graph/orchestrator_validators/planning_gates.py` | 268 | full | second validator family (F-VR-07 blast radius) |
| `src/film_pipeline/graph/orchestrator_validators/prep_gates.py` | 155 | full | second validator family (F-VR-07 blast radius) |
| `src/film_pipeline/graph/nodes/qc.py` | 435 | full | **has findings** (F-VR-03, F-VR-04, F-VR-05, F-VR-07, F-VR-12, F-VR-13) |
| `src/film_pipeline/graph/subgraphs/qc.py` | 311 | full | **has findings** (F-VR-03, F-VR-05, F-VR-07) |
| `src/film_pipeline/graph/_action_routing.py` | 394 | full | **has findings** (F-VR-02, F-VR-05, F-VR-06) |
| `src/film_pipeline/graph/router.py` | 103 | grepped | thin re-export of `_action_routing` (Clean concern C1) |
| `src/film_pipeline/graph/edges.py` | grepped | **has findings** (F-VR-06 context; phase-map note §5) |
| `src/film_pipeline/graph/nodes/approval.py` | 294 | full | **has findings** (F-VR-06, F-VR-10) |
| `src/film_pipeline/graph/nodes/_shared.py` | 210 | 100-179 | gate-flag writer (`_phase_gate_updates`) |
| `src/film_pipeline/graph/nodes/_agent_handoff.py` | 143 | full | channel propagation (F-VR-05) |
| `src/film_pipeline/graph/nodes/_agent.py` | 238 | full | no validation logic; F-VR-05 evidence |
| `src/film_pipeline/graph/orchestrator_state.py` | 537 | 60-165 | `ORCH_CHANNELS` (F-VR-05, F-VR-13 candidate owner, F-VR-14) |
| `src/film_pipeline/graph/state_schema.py` | — | 150-180 | `GraphState` ref fields (F-VR-13, F-VR-14) |
| `src/film_pipeline/graph/services.py` | ~120 | 55-80 | `validator_registry: Any = None` (F-VR-01) |
| `src/film_pipeline/schemas/_base.py` | 280 | 27-75, 122-142, 192-198 | `ArtifactType` (F-VR-12), `ValidationStatus`, `IssueSeverity` (Clean concern C2) |
| `src/film_pipeline/graph/nodes/_agent_artifacts.py` | 150 | 25-60 | `_resolve_artifact_type` coercion (F-VR-12) |
| `src/film_pipeline/graph/nodes/_context.py` | 465 | 300-321 | `_ARTIFACT_TYPE_BY_CLASS` / `_infer_artifact_type` (F-VR-12) |
| `src/film_pipeline/artifacts/registry.py` | 253 | 95-125, 165-200 | id-keyed `spec_for`/`renderer_for` (F-VR-12) |
| `src/film_pipeline/artifacts/store.py` | 834 | 120-200, 750-775 | `spec_for(artifact_id)` → rendered `- type:` header (F-VR-12) |
| `src/film_pipeline/artifacts/rendering.py` | — | 160-175 | `render_consensus_report` (F-VR-12 — confirms it does fire) |
| `src/film_pipeline/graph/nodes/_repair_loop.py` | — | 40-55, 205-240 | repair-path QC dispatch (F-VR-03) |
| `src/film_pipeline/schemas/validation.py` | 76 | full | `ValidationReport`/`ConsensusReport` contracts (F-VR-04, F-VR-05) |
| `src/film_pipeline/schemas/registries/validator_registry.py` | 40 | full | **has findings** (F-VR-01) — two classes named `ValidatorRegistry` |
| `src/film_pipeline/schemas/approval.py` | ~60 | full | **has findings** (F-VR-10) |
| `src/film_pipeline/mcp/tools/validation.py` | 374 | full | **has findings** (F-VR-07, F-VR-14, F-VR-15) |
| `src/film_pipeline/mcp/tools/registry.py` | — | 236-244 | `run_validation` registration (F-VR-15) |
| `src/film_pipeline/mcp/tools/review.py` | 165 | full | **has findings** (F-VR-06, F-VR-09) |
| `src/film_pipeline/mcp/tools/helpers.py` | ~230 | 214-223 | `_report_summary` projection (F-VR-04 blast radius) |
| `src/film_pipeline/agents/impl/qc_synthesis_agent.py` | 77 | full | **has findings** (F-VR-05) |
| `src/film_pipeline/agents/impl/registry.py` | — | grepped | `"clip-validator": QCSynthesisAgent` (`src/film_pipeline/agents/impl/registry.py:28`) |
| `src/film_pipeline/agents/impl/*validator*` | — | glob | **no such files exist**; QC synthesis is the only consensus agent |
| `src/film_pipeline/app/_graph_exec.py` | 484 | 240-345, 425-484 | third live caller of the sequential QC path (F-VR-03) |
| `src/film_pipeline/app/smoke.py` | — | 35-44 | counts `MVP_VALIDATORS` (F-VR-01) |
| `src/film_pipeline/post/delivery_packaging_agent.py` | — | 188-196 | 5th direct validator instantiation (F-VR-07) |
| `tests/unit/validation/*` | 7 files | read | **no** registry-agreement test (F-VR-01) |
| `tests/unit/graph/test_router_validation_status.py` | 94 | full | pins router branch with hand-built state (F-VR-02) |
| `tests/unit/graph/test_qc_validator_dispatch.py` | 107 | full | pins `_VALIDATOR_RUNNERS` per phase (**m5 — added after verification**; qualifies F-VR-03/F-VR-07) |
| `tests/unit/graph/test_channel_registry.py` | 371 | 30-40, 60-95, 196-300 | channel parity + writer sweep; sweep scope excludes F-VR-13's keys |
| `tests/unit/mcp/tools/test_validation.py` | 394 | 16-100 | pins the "No validators found" refusal as correct (F-VR-15) |
| `tests/unit/graph/test_real_human_gates.py` | 402 | 140-210 | replicates gate policy (F-VR-06) |
| `tests/unit/review/*` | 3 files, 30 tests | read | pins `review/` in isolation (Clean concern C4) |
| `tests/integration/test_validation_runtime.py` | — | 1-60 | drives `rt._run_phase_node(..., "qc")` (F-VR-03) |
| `tests/e2e/conftest.py` | — | 30-65 | registers `MVP_VALIDATORS` into a fixture nobody consumes (F-VR-01) |

### 1.2 Greps run beyond the listed scope

```
grep -rn "score_to_status" --include=*.py .                  # 1 definition, 1 production call site
grep -rn "def score_to_status" --include=*.py . | wc -l      # 1
grep -rn "review_at" --include=*.py . | wc -l                 # 26 = 22 entry literals + schema default
                                                              #   + read site thresholds.py:25 + 2 test tuples
grep -rn "NEEDS_REVISION" --include=*.py src | wc -l          # 11: 3 producers-ish (thresholds.py:28,
                                                              #   consensus.py:93,98), 8 read/compare sites
grep -rn "consensus" --include=*.py src                      # 2 builders, 4 readers
grep -rn "ValidatorRegistry" --include=*.py src tests        # 2 distinct classes, same name
grep -rn "register_validator" --include=*.py .               # 0 hits — this name does not exist
grep -rn "ValidatorRegistryEntry(" --include=*.py src | wc -l # 23 = 22 literals + 1 class declaration
grep -rn "blocking_conditions\|warning_conditions" --include=*.py src   # 46 hits; 0 read sites
grep -rn '"blocking"' --include=*.py src | wc -l              # 59 raw-string severity comparisons
grep -rn "ApprovalRecord" --include=*.py src                 # definition + exports only, 0 constructions
grep -rn "validation_report_refs" --include=*.py src | wc -l # 5 hits, 0 writers (F-VR-14)
grep -rn "consensus_report_ref\|qc_patch_ref" --include=*.py src/film_pipeline/graph/orchestrator_state.py  # 0 rows (F-VR-13)
grep -rn "consensus_report" --include=*.py src/film_pipeline/schemas/_base.py   # 0 members (F-VR-12)
```

### 1.3 Adjacent concerns deliberately not claimed here

- **Phase order / phase advance.** `PHASE_ORDER` (`src/film_pipeline/graph/_action_routing.py:18-30`) is imported by
  `src/film_pipeline/app/_graph_exec.py:24` and `src/film_pipeline/app/_resume.py:12` (single source), but a second literal table exists
  at `src/film_pipeline/graph/edges.py:40-54` (`_NEXT_PHASE_AFTER_APPROVAL`). That is the graph-transition cluster's
  concern, not this one; recorded here as an unclaimed cross-reference, not a finding.
- **`graph/orchestrator_validators/*` (Gates S/A/B/C)** are a second *validator family* that never
  touches `BaseValidator`/`ValidationReport`/`ValidationStatus`; they return raw issue dicts via
  `_blocking` (`src/film_pipeline/graph/orchestrator_validators/_shared.py:10-11`) and are consumed by phase nodes
  (`src/film_pipeline/graph/nodes/prep.py:257`, `src/film_pipeline/graph/nodes/visual.py:126,465,576,588`, `src/film_pipeline/graph/nodes/generation.py:32`). This is used as
  **blast-radius evidence** for F-VR-07, not as a separate finding (no score/status contract is
  duplicated; the family is a distinct, self-consistent mechanism).

---

## 2. Validator registry reconciliation

### 2.1 How many registries / registration paths exist

**Four independent definition/registration paths** for validator identity+thresholds, plus
**four independent dispatch tables** (the tables are `F-VR-07`'s subject, listed here for the
reconciliation picture):

| # | Path | Artifact | Populated in production? |
|---|---|---|---|
| R1 | `src/film_pipeline/validation/validators/__init__.py:11-167` | `MVP_VALIDATORS` — 15 `ValidatorRegistryEntry` literals | **No** (only `src/film_pipeline/app/smoke.py:38-40` counts it; `tests/e2e/conftest.py:61-64` registers a fixture nothing consumes) |
| R2 | `validation/impl/*.py` `__init__` | 7 per-class `ValidatorRegistryEntry` literals | **Yes** — this is the entry every runtime `run()` reads |
| R3 | `src/film_pipeline/validation/registry.py:15-46` | runtime `ValidatorRegistry` dataclass, `register`/`register_many` | **No** (`GraphServices.validator_registry` is `None` forever — `src/film_pipeline/graph/services.py:65`) |
| R4 | `src/film_pipeline/schemas/registries/validator_registry.py:37-40` | Pydantic `ValidatorRegistry` aggregate | **No** (only `tests/unit/test_schemas.py:1071` constructs it) |

There is **no `register_validator` function and no `validator_registry` binding**: the grep
`grep -rn "register_validator" --include=*.py .` returns zero hits, and
`grep -rn "validator_registry" --include=*.py src` returns only the dead field
(`src/film_pipeline/graph/services.py:65`) plus `src/film_pipeline/app/smoke.py`'s count check. Dispatch is by hardcoded import.

### 2.2 Does anything prove the registries agree? — No

No test imports both `MVP_VALIDATORS` and any `validation.impl` class:

```
grep -rln "MVP_VALIDATORS" tests/   → tests/unit/validation/test_registry.py, tests/e2e/conftest.py
grep -rln "validation\.impl" tests/ → tests/unit/validation/test_impl_validators.py, …(5 files, disjoint)
```

`tests/unit/validation/test_registry.py:74-79` only asserts each MVP entry has `pass_at > 0` and
`block_below > 0`:

> `assert entry.thresholds.pass_at > 0`

A registry-agreement invariant test does not exist. §1.5 drift-likelihood 5 applies.

### 2.3 Reconciliation table (mechanically produced at HEAD)

Produced by instantiating every impl class and diffing `cls().entry` against the `MVP_VALIDATORS`
entry of the same `validator_id` (see the reproduce command on F-VR-01):

| `validator_id` | In `MVP_VALIDATORS` | Impl class | Entry agreement | Thresholds (pass/review/block) | NEEDS_REVISION band |
|---|---|---|---|---|---|
| `scene-writing-validator` | `src/film_pipeline/validation/validators/__init__.py:33-42` | `src/film_pipeline/validation/impl/script_structure.py:122` | **DIFFERS** — impl has `"scene_count_under_min"` (`src/film_pipeline/validation/impl/script_structure.py:139`); MVP does not (`src/film_pipeline/validation/validators/__init__.py:40`) | 85/75/75 | **empty** |
| `dialogue-voice-validator` | `:43-52` | `src/film_pipeline/validation/impl/dialogue_voice.py:167` | agrees | 85/75/75 | **empty** |
| `reference-usability-validator` | `:73-82` | `src/film_pipeline/validation/impl/reference_usability.py:185` | agrees | 85/75/75 | **empty** |
| `prompt-readiness-validator` | `:94-103` | `src/film_pipeline/validation/impl/prompt_readiness.py:152` | agrees | 85/75/75 | **empty** |
| `scene-continuity-validator` | `:126-135` | `src/film_pipeline/validation/impl/scene_continuity.py:205` | agrees | 85/75/75 | **empty** |
| `assembly-validator` | `:157-166` | `src/film_pipeline/validation/impl/assembly.py:197` | agrees | 85/75/75 | **empty** |
| `delivery-completeness-validator` | **ABSENT** | `src/film_pipeline/validation/impl/delivery_completeness.py:107-117` | n/a — impl-only | 90/80/80 | **empty** |
| `logline-validator` | `:13-22` | none | n/a — declared, unimplemented | 85/75/75 | **empty** |
| `treatment-validator` | `:23-32` | none | n/a — declared, unimplemented | 85/75/75 | **empty** |
| `character-dossier-validator` | `:53-62` | none | n/a | 80/70/70 | **empty** |
| `environment-bible-validator` | `:63-72` | none | n/a | 80/70/70 | **empty** |
| `shot-design-validator` | `:84-93` | none | n/a | 85/75/75 | **empty** |
| `clip-quality-validator` | `:105-114` | none | n/a | 85/75/75 | **empty** |
| `prompt-adherence-validator` | `:115-124` | none | n/a | 85/75/75 | **empty** |
| `act-structure-validator` | `:136-145` | none | n/a | 80/70/70 | **empty** |
| `full-movie-flow-validator` | `:146-155` | none | n/a | 85/75/75 | **empty** |

**Single-registry finding:** there is **no** single registry. Two live-and-divergent entry
populations exist (R1 declared contract vs R2 executed contract), one is already divergent in
content, one validator exists only in R2, and nine declared validators have no implementation.
R3/R4 are dead code. **Nothing enforces agreement.**

### 2.4 Score→status mapping and `review_at` reachability at HEAD

The mapping itself **is single-owned** (good): one definition, one call site.

- `src/film_pipeline/validation/thresholds.py:9-29` — `def score_to_status(score, thresholds=None)` →
  `PASS` / `PASS_WITH_NOTES` / `NEEDS_REVISION` / `BLOCKED`.
- `grep -rn "def score_to_status" --include=*.py . | wc -l` → `1`.
- Sole production caller: `src/film_pipeline/validation/base.py:263` — `status = score_to_status(score, self.entry.thresholds)`.

But `review_at` at HEAD maps to `PASS_WITH_NOTES`, and `NEEDS_REVISION` occupies
`[block_below, review_at)`. Because **every one of the 22 entry literals sets
`block_below == review_at`** (`85/75/75`, `80/70/70`, `90/80/80`), that band is empty everywhere:

- `src/film_pipeline/validation/validators/__init__.py:19` — `thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),`
- `src/film_pipeline/validation/impl/assembly.py:210` — same literal for the executed entry.
- Range probe over all 15 MVP entries at 0.5-point resolution: **zero** scores produce
  `NEEDS_REVISION` (see F-VR-02 reproduce).

`ValidationStatus.NEEDS_REVISION` has **one live producer that is not a validator**: the LLM
consensus path. `src/film_pipeline/agents/impl/qc_synthesis_agent.py:66`
(`consensus_status=ValidationStatus(str(data.get("consensus_status", "pass")))`, and per-reviewer
`:56`) mints whatever status the model returns, and that `ConsensusReport` is persisted as the
`consensus_report` artifact (`src/film_pipeline/graph/nodes/qc.py:109`). The artifact-kind registry is keyed by
**artifact id**, not by `artifact_type` (`src/film_pipeline/artifacts/registry.py:1,100-107`), so
`render_consensus_report` (`src/film_pipeline/artifacts/rendering.py:164-170`) prints the status verbatim — i.e.
`needs_revision` **can reach a human-viewable artifact**. (The artifact's *metadata* type is
nevertheless wrong — coerced to `script` — see F-VR-12; renderer selection is unaffected.)
What cannot happen is routing on it:
`src/film_pipeline/graph/_action_routing.py:110` reads `state["consensus_report"]`, a key no production module writes and
which has no `ORCH_CHANNELS` row, so rule 6's `revise` tier is unreachable.
`src/film_pipeline/validation/consensus.py:92-93,98` are pass-throughs gated on an input status no validator can emit, and
`src/film_pipeline/graph/_action_routing.py:287` is read-side.

**Verdict at HEAD:** no *validator* can emit `NEEDS_REVISION` (the band is empty in all 22 entry
literals), and the router's consensus/`revise` tier is dead; the status itself is reachable only via
LLM-supplied consensus JSON, which is stored and rendered but never routed on.

---

## 3. Findings

§3.1 lists the eleven findings from the first pass (all re-verified; the four corrections the
verifier required are applied in place and marked). §3.2 lists four findings added after verification
for seams the first pass missed, plus one verifier consequence that is corrected rather than adopted.
The finding inventory is therefore **15 findings**: F-VR-01..F-VR-15.

**3.1 Findings from the first pass (corrected where verification required).**

### F-VR-01 — Parallel validator registries: the declared 15-validator contract and the executed per-class entries disagree

- **Class:** O4 (parallel registries)
- **Severity:** High (impact 3 × drift 5 = 15)
- **Concern:** One validator identity/threshold contract is declared twice — once as the
  `MVP_VALIDATORS` table and once inside each implementation's `__init__` — and only the second is
  ever executed, so the "registry" that names, scopes, and threshold-configures validators is a
  fiction.
- **De-facto owners:**
  - `src/film_pipeline/validation/validators/__init__.py:40` — declared blocking contract for
    `scene-writing-validator` — `"blocking_conditions=["missing_scene_intent", "no_conflict"],"`
  - `src/film_pipeline/validation/impl/script_structure.py:139` — executed contract, different
    content — `"blocking_conditions=["missing_scene_intent", "no_conflict", "scene_count_under_min"],"`
  - `src/film_pipeline/validation/validators/__init__.py:157-163` — declares
    `assembly-validator` / `pass_at=85, review_at=75, block_below=75` — the same literal is
    re-declared at `src/film_pipeline/validation/impl/assembly.py:204-210`
  - `src/film_pipeline/validation/impl/delivery_completeness.py:109` — a validator that exists only
    in the executed population — `validator_id="delivery-completeness-validator",`
  - `src/film_pipeline/validation/validators/__init__.py:1` — the declared population's own scope
    claim — `"""MVP validator contracts — all 15 validators from the validation matrix."""`
  - `src/film_pipeline/graph/services.py:65` — the wiring point that was never wired —
    `validator_registry: Any = None  # ValidatorRegistry`
- **Drift proof:** **existing divergence.** For `scene-writing-validator`, the executed validator
  can report `scene_count_under_min` as blocking (`src/film_pipeline/validation/impl/script_structure.py:45-46`:
  `"code": "scene_count_under_min", "severity": "blocking"`) while the declared contract in
  `MVP_VALIDATORS` does not list it (`src/film_pipeline/validation/validators/__init__.py:40`). Symmetrically,
  `delivery-completeness-validator` is absent from `MVP_VALIDATORS` entirely, so
  `ValidatorRegistry.lookup_by_scope(ValidationScope.DELIVERY)` (`src/film_pipeline/validation/registry.py:33-34`)
  cannot return it — even though the runtime executes it
  (`src/film_pipeline/mcp/tools/validation.py:110-114`, `src/film_pipeline/post/delivery_packaging_agent.py:190-196`). Mutation scenario:
  change `MVP_VALIDATORS`'s threshold for `assembly-validator` from `75` to `65`; `src/film_pipeline/validation/impl/assembly.py:210`
  keeps `75`, every runtime report is unchanged, and no test fails because no test imports both
  modules (`grep -rln` sets are disjoint).
- **Reproduce:**
  ```bash
  ./.venv/bin/python - <<'PY'
  from film_pipeline.validation.validators import MVP_VALIDATORS
  from film_pipeline.validation.impl import (AssemblyValidator, DeliveryCompletenessValidator,
      DialogueVoiceValidator, PromptReadinessValidator, ReferenceUsabilityValidator,
      SceneContinuityValidator, ScriptStructureValidator)
  mvp = {e.validator_id: e for e in MVP_VALIDATORS}
  for cls in (ScriptStructureValidator, DialogueVoiceValidator, ReferenceUsabilityValidator,
              PromptReadinessValidator, SceneContinuityValidator, AssemblyValidator,
              DeliveryCompletenessValidator):
      e = cls().entry; m = mvp.get(e.validator_id)
      if m is None: print(e.validator_id, "ABSENT from MVP_VALIDATORS"); continue
      diff = [f for f in ("scope","modalities","input_schema","model_profile","thresholds",
                          "blocking_conditions","warning_conditions")
              if getattr(e,f) != getattr(m,f)]
      print(e.validator_id, "AGREES" if not diff else f"DIFFERS {diff}")
  PY
  # → scene-writing-validator DIFFERS ['blocking_conditions']
  # → delivery-completeness-validator ABSENT from MVP_VALIDATORS
  # → the other 5: AGREES
  ./.venv/bin/python - <<'PY'
  from film_pipeline.validation.validators import MVP_VALIDATORS
  from film_pipeline.validation.impl import (AssemblyValidator, DeliveryCompletenessValidator,
      DialogueVoiceValidator, PromptReadinessValidator, ReferenceUsabilityValidator,
      SceneContinuityValidator, ScriptStructureValidator)
  impls = (ScriptStructureValidator, DialogueVoiceValidator, ReferenceUsabilityValidator,
           PromptReadinessValidator, SceneContinuityValidator, AssemblyValidator,
           DeliveryCompletenessValidator)
  ids = {e.validator_id for e in MVP_VALIDATORS}
  impl_ids = {c().entry.validator_id for c in impls}
  print("MVP_VALIDATORS entries:", len(MVP_VALIDATORS))          # → 15
  print("implemented classes:", len(impls))                      # → 7
  print("declared but unimplemented:", len(ids - impl_ids))      # → 9
  PY
  ```
- **Blast radius:** `src/film_pipeline/validation/validators/__init__.py`, all `validation/impl/*`, `src/film_pipeline/validation/registry.py`,
  `src/film_pipeline/graph/services.py`, `src/film_pipeline/app/smoke.py`, `src/film_pipeline/mcp/tools/validation.py`, `src/film_pipeline/post/delivery_packaging_agent.py`.
  User-visible consequence: a registry-driven lookup (the fix already mandated by
  `documentation/refactoring-plan.md:194-196`, "Replace direct validator imports with registry-driven
  dispatch") would silently drop the delivery validator and mis-declare scene blocking conditions,
  so a human deliverable could ship with a validator that never ran.
- **Candidate owner module:** `src/film_pipeline/validation/registry.py` — owns validator identity, scope/modality
  indexes, thresholds, and the enabled flag; classes become consumers of an entry passed in
  (the `BaseValidator(entry)` constructor already supports this).
- **Extraction sketch:** (1) move each impl's `ValidatorRegistryEntry` literal into the single
  `validation/validators/` table keyed by class; (2) `BaseValidator.__init__` requires an injected
  entry (remove every `entry = ValidatorRegistryEntry(...)` block from `impl/*`); (3) add a
  registry-agreement guard test that builds the registry and asserts
  `registry.lookup_by_id(cls().entry_id) is not None` and that every impl class appears exactly once;
  (4) delete or implement the nine unimplemented entries. Public contract:
  `PHASE_VALIDATORS: dict[str, tuple[type[BaseValidator], ...]]` plus the `ValidatorRegistry` index.
- **Prior art:** `documentation/audit-findings.md:97` ("`ValidatorRegistry` exists but
  `GraphServices.validator_registry` is `None`; validators are imported directly");
  `documentation/reviews/arch-lens-flexibility.md:64-67` (thresholds hardcoded in four places).
  **What is new at HEAD:** the profile-level `validation.thresholds` block that prior art cited was
  removed (`profiles/base.studio.yaml:103-107`), so the residual duplication is exactly the
  22 entry literals; and the registry drift is now proven by an *existing content divergence*
  (`scene_count_under_min`) plus a *membership divergence* (`delivery-completeness-validator`),
  not merely by an unused class. Prior art's `documentation/reviews/arch-lens-boundaries.md:161` claim is confirmed at HEAD.

### F-VR-02 — No validator can emit `NEEDS_REVISION` (empty threshold band), and the router's consensus/`revise` tier is dead

- **Class:** O1 (duplicated normative model — the same policy is encoded in 22 independently
  maintained threshold triples and one documented intent)
- **Severity:** Critical (impact 4 × drift 5 = 20)
- **Concern:** The four-status validation contract is only satisfiable if `block_below < review_at`;
  every registered validator sets `block_below == review_at`, so no validator can ever emit the
  repair-label status, and the router branch that would act on it is unreachable because it reads a
  state key nothing writes. The status itself is still mintable by the LLM consensus path, so the
  defect is a collapsed contract plus dead routing, not a globally impossible value.
- **De-facto owners:**
  - `src/film_pipeline/validation/thresholds.py:25-28` — the normative band arithmetic —
    `"if score >= t.review_at:\n        return ValidationStatus.PASS_WITH_NOTES\n    if score >= t.block_below:\n        return ValidationStatus.NEEDS_REVISION"`
  - `src/film_pipeline/schemas/registries/validator_registry.py:17-19` — schema defaults that *do*
    leave a band — `block_below: float = Field(default=65.0, ge=0, le=100)`
  - `src/film_pipeline/validation/validators/__init__.py:19` — every entry overrides the band away —
    `thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),`
  - `src/film_pipeline/validation/impl/assembly.py:210` — the executed entry repeats it —
    `thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),`
  - `src/film_pipeline/agents/impl/qc_synthesis_agent.py:66` — the non-validator producer —
    `consensus_status=ValidationStatus(str(data.get("consensus_status", "pass"))),`
  - `src/film_pipeline/graph/_action_routing.py:110` — the routing reader with no writer —
    `consensus = state.get("consensus_report")`
  - `documentation/refactoring-plan.md:192` — the documented intent contradicts the code —
    ``"- `score_to_status` must use `review_at` so `[review_at, pass_at)` returns `NEEDS_REVISION`."``
- **Drift proof:** **two existing divergences.** (a) Code vs documented intent:
  `documentation/refactoring-plan.md:192` assigns `NEEDS_REVISION` to `[review_at, pass_at)`, but
  `src/film_pipeline/validation/thresholds.py:25-26` assigns that band to `PASS_WITH_NOTES` and gives `NEEDS_REVISION`
  `[block_below, review_at)` — which the 22 literals make empty. (b) Code vs code: the schema
  default `85/75/65` (`src/film_pipeline/schemas/registries/validator_registry.py:17-19`) leaves a 10-point `NEEDS_REVISION` band, while
  every actual entry uses `85/75/75` or `80/70/70` or `90/80/80`. Mutation scenario: change
  `src/film_pipeline/validation/validators/__init__.py:19` `block_below=75` → `65`; nothing in production changes (impl entries
  are the executed ones), and no test fails — `tests/unit/validation/test_thresholds.py:14-36`
  exercises only the default triple and a custom `90/80/70` tuple, never a registered entry.
  **Counter-evidence (verified by the verifier and re-verified here):** the value is *not*
  globally unreachable. `src/film_pipeline/agents/impl/qc_synthesis_agent.py:56,66` mints `needs_revision` from LLM JSON; the
  resulting `ConsensusReport` is saved under artifact id `consensus_report`
  (`src/film_pipeline/graph/nodes/qc.py:109`), and the kind registry is keyed by artifact id
  (`src/film_pipeline/artifacts/registry.py:1,100-107`), so `render_consensus_report`
  (`src/film_pipeline/artifacts/rendering.py:164-170`, `for key in ("consensus_status", …)`) prints it into a
  human-viewable artifact. It simply never enters `state["consensus_report"]`
  (`grep -rn "consensus_report" src/film_pipeline/graph/orchestrator_state.py` → only
  `validation_report_refs`), so rule 6 cannot see it. What *is* true: no **validator** can emit the
  status, and the `revise` tier is dead. Repair is still reached for low scores via `BLOCKED`
  → rule 5 → `handle_blockers` with `eligible=["repair", …]` (`src/film_pipeline/graph/_action_routing.py:283-286`).
- **Reproduce:**
  ```bash
  ./.venv/bin/python - <<'PY'
  from film_pipeline.validation.validators import MVP_VALIDATORS
  from film_pipeline.validation.thresholds import score_to_status
  from film_pipeline.validation.impl.delivery_completeness import DeliveryCompletenessValidator
  from film_pipeline.schemas.registries.validator_registry import ValidatorRegistryEntry
  from film_pipeline.schemas._base import ValidationScope, ValidationStatus
  entries = list(MVP_VALIDATORS) + [DeliveryCompletenessValidator().entry]
  hits = [e.validator_id for e in entries
          if any(score_to_status(s/2, e.thresholds) == ValidationStatus.NEEDS_REVISION
                 for s in range(201))]
  print("entries that can emit NEEDS_REVISION:", hits)                 # → []
  triples = sorted({(e.thresholds.pass_at, e.thresholds.review_at, e.thresholds.block_below)
                    for e in entries})
  print("distinct entry triples:", len(triples), triples)
  # → 3 [(80.0, 70.0, 70.0), (85.0, 75.0, 75.0), (90.0, 80.0, 80.0)]
  print("entries with block_below == review_at:",
        sum(1 for e in entries if e.thresholds.block_below == e.thresholds.review_at),
        "of", len(entries))                                            # → 16 of 16
  defaults = ValidatorRegistryEntry(validator_id="probe",
      scope=ValidationScope.SCENE).thresholds
  print("schema default triple:", defaults.pass_at, defaults.review_at, defaults.block_below,
        "-> NEEDS_REVISION band", defaults.review_at - defaults.block_below)
  # → 85.0 75.0 65.0 -> NEEDS_REVISION band 10.0
  PY
  grep -rn "review_at=" --include=*.py src | grep -c "block_below=review\|block_below=75\|block_below=70\|block_below=80"
  # → 22 entry literals (the count F-VR-02's Class line and §2.4 rely on)
  # Counter-evidence: the non-validator producer
  grep -n "consensus_status" src/film_pipeline/agents/impl/qc_synthesis_agent.py
  grep -n "consensus_report" src/film_pipeline/graph/orchestrator_state.py   # → 0 rows for the key
  ```
- **Blast radius:** `src/film_pipeline/validation/thresholds.py`, `src/film_pipeline/validation/base.py:263,286-290`,
  `src/film_pipeline/validation/consensus.py:92-93`, `src/film_pipeline/graph/_action_routing.py:287-293` (the dead `revise` route),
  `src/film_pipeline/graph/nodes/approval.py` (repair loop entry), `src/film_pipeline/mcp/tools/validation.py` (report statuses),
  `src/film_pipeline/schemas/validation.py:41` (`ValidationReport.status`). User-visible consequence: the *label* and
  the *routing tier* are missing — a repairable artifact is reported `BLOCKED`, so repair still
  happens, but always through the blocking-issue path; `NEEDS_REVISION` never appears on a
  `ValidationReport`, and rule 6's `revise` eligibility never fires. The acceptance line
  "Repairable findings route to repair behavior"
  (`documentation/product-completion-plan/acceptance-checklist.md:54`) is met only incidentally via
  `BLOCKED`, not through the status the contract defines for it.
- **Candidate owner module:** `src/film_pipeline/validation/thresholds.py` — owns the score→status function *and* the
  four-status band invariant (`block_below < review_at`).
- **Extraction sketch:** keep `score_to_status` as the only mapping; add a model-level invariant
  (`ValidatorThresholds` validator requiring `pass_at > review_at >= block_below`, or explicitly
  `block_below < review_at`); migrate every entry literal to a single table (F-VR-01); add a guard
  test asserting that *for every registry entry* there exists a score emitting each of the four
  statuses — the test that would have caught this.
- **Prior art:** `documentation/audit-findings.md:29,96,171` — "`score_to_status` ignores `review_at`,
  making `NEEDS_REVISION` unreachable"; `documentation/product-completion-plan/acceptance-checklist.md:54,63`.
  **What is new at HEAD:** the prior mechanism is **fixed** — `src/film_pipeline/validation/thresholds.py:25` now reads
  `review_at` — but the prior *conclusion still holds through a different mechanism*: the band
  `[block_below, review_at)` is empty in all 22 entry literals. The prior fix (using `review_at`)
  and the current four-status semantics are mutually inconsistent for any dataset with
  `block_below == review_at`, and no test covers a registered entry.

### F-VR-03 — Two live QC lifecycles: forward graph uses the parallel subgraph, repair/app paths use the sequential node, and they diverge in coverage and side effects

- **Class:** O6 (parallel lifecycle)
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** The `qc` phase has two independent implementations — a Send fan-out subgraph on the
  forward path and a sequential validator loop used by the repair loop and the app — which load
  different artifacts, run different validator sets, and produce different side effects, so the QC
  verdict for one phase depends on how the phase was entered.
- **De-facto owners:**
  - `src/film_pipeline/graph/graph.py:115` — forward path — `builder.add_node("qc_node", build_qc_subgraph())  # Phase 7: parallel subgraph`
  - `src/film_pipeline/graph/nodes/_repair_loop.py:47` — repair path uses the *other* implementation —
    `"qc": qc_node,`
  - `src/film_pipeline/graph/nodes/_repair_loop.py:234` — the other implementation is invoked —
    `result = cast(dict[str, Any], phase_fn(state))`
  - `src/film_pipeline/app/_graph_exec.py:337` — app/headless path calls the sequential loop directly —
    `_run_validators(working)`
  - `src/film_pipeline/app/_graph_exec.py:449` — and `run_phase_node` resolves through `_PHASE_NODES` —
    `from film_pipeline.graph.nodes.approval import _PHASE_NODES`
  - `src/film_pipeline/graph/subgraphs/qc.py:266` — forward path writes reports into state itself —
    `"_validation_reports": raw,`
- **Drift proof:** covering-set divergence is structural and testable. The forward subgraph has six
  workers (`src/film_pipeline/graph/subgraphs/qc.py:210-217`, `_WORKER_NODES`) with no delivery validator; the sequential
  node has six runners (`src/film_pipeline/graph/nodes/qc.py:361-368`, `_VALIDATOR_RUNNERS`), where the delivery runner is
  gated on `{"delivery"}` only (`src/film_pipeline/graph/nodes/qc.py:367`), so at `phase == "qc"` the delivery validator
  never runs on either QC path. Side-effect divergence: the sequential node emits a
  `MatrixPatch` (`src/film_pipeline/graph/nodes/qc.py:68-92`) and attempts a consensus artifact
  (`src/film_pipeline/graph/nodes/qc.py:137,164-183`); the subgraph's reduce node does neither (`src/film_pipeline/graph/subgraphs/qc.py:249-277`).
  Mutation scenario: add a seventh validator to `_WORKER_NODES` only; the repair path
  (`_PHASE_NODES["qc"]` → `src/film_pipeline/graph/nodes/qc.py`) keeps the old set and no test compares the two sets —
  `tests/unit/graph/test_qc_subgraph.py` never imports `graph.nodes.qc`, and
  `tests/integration/test_validation_runtime.py:38` drives only `rt._run_phase_node`, i.e. only one
  path. **Qualification (from verification):** `tests/unit/graph/test_qc_validator_dispatch.py`
  (107 lines) *does* pin the sequential table's per-phase membership — its docstring says a typo
  "would ship green because every runner still runs successfully wherever it fires", and it fixes
  the `qc` set as `id="qc-covers-upstream-but-not-delivery"` (`:85-90`). So a partial edit to
  `_VALIDATOR_RUNNERS` alone is caught; what remains unguarded is **cross-path agreement**
  (sequential vs subgraph vs MCP) and any edit made to the subgraph table alone.
- **Reproduce:**
  ```bash
  grep -rn "build_qc_subgraph\|_PHASE_NODES\[" --include=*.py src | grep -v test
  grep -n "_VALIDATOR_RUNNERS" -A 8 src/film_pipeline/graph/nodes/qc.py
  grep -n "_WORKER_NODES" -A 9 src/film_pipeline/graph/subgraphs/qc.py
  grep -rn "_PHASE_NODES" src/film_pipeline/app/_graph_exec.py src/film_pipeline/graph/nodes/_repair_loop.py
  wc -l tests/unit/graph/test_qc_validator_dispatch.py        # → 107 lines
  ```
- **Blast radius:** `src/film_pipeline/graph/graph.py`, `src/film_pipeline/graph/subgraphs/qc.py`, `src/film_pipeline/graph/nodes/qc.py`,
  `src/film_pipeline/graph/nodes/_repair_loop.py`, `src/film_pipeline/app/_graph_exec.py`, `src/film_pipeline/mcp/tools/validation.py` (reads
  `_validation_reports` produced by either path). User-visible consequence: an artifact rejected at
  QC can be re-validated with a different validator set and different artifact versions after a
  revision round, producing non-reproducible QC verdicts and missing matrix patches exactly when a
  human has requested a fix.
- **Candidate owner module:** `src/film_pipeline/validation/runtime.py` — one pure core
  `run_validators(services, project_id, artifact_resolver, validators) -> list[ValidationReport]`
  with an injected resolver, plus one `PHASE_VALIDATORS` table; the subgraph workers and the
  sequential loop become thin adapters over it.
- **Extraction sketch:** move `_collect_artifacts`/`_pick_artifact`/`_VALIDATOR_RUNNERS`
  (`src/film_pipeline/graph/nodes/qc.py:140-201,361-368`) and `_VALIDATOR_ARTIFACTS`/`_resolve_validator_instance`
  (`src/film_pipeline/graph/subgraphs/qc.py:113-203`) into the shared core; keep `Send` fan-out and sequential invocation as
  the only differences; move consensus/MatrixPatch side effects into an explicitly shared post-step
  invoked by both callers. Guard test: run both entry paths over the same fixture and assert equal
  validator-id sets, equal statuses, and equal side-effect keys.
- **Prior art:** `documentation/reviews/arch-lens-dataflow.md:110` and its failure scenario at
  `:117` ("Pass/fail decisions differ depending on which entry point ran — unreproducible QC
  verdicts"). **What is new at HEAD:** the exact live call sites are now confirmed
  (`src/film_pipeline/graph/graph.py:115` vs `src/film_pipeline/graph/nodes/_repair_loop.py:47` and `src/film_pipeline/app/_graph_exec.py:337`), and the coverage delta is
  quantified: the delivery validator is absent from *both* QC paths while `src/film_pipeline/mcp/tools/validation.py:153-157`
  runs it at `delivery`, and the subgraph's reduce node produces no consensus artifact at all.
  **Distinct from F-VR-07 (double-counting check):** F-VR-03 and F-VR-07 share the
  `_WORKER_NODES`/`_VALIDATOR_RUNNERS` evidence but assert different invariants and are not
  mergeable. F-VR-03's invariant is *behavioural equivalence of two live entry paths for the same
  phase* (same artifacts loaded, same validator set, same side effects: consensus + `MatrixPatch`) —
  two implementations that both exist and disagree. F-VR-07's invariant is *declarative agreement of
  the phase→validator tables themselves* (registry scopes vs runner tuples vs worker/map pairs vs MCP
  `_PhaseSpec`), including the MCP table, which F-VR-03 does not cover. Consequently the candidate
  owners differ: F-VR-03 extracts a shared **execution core** (`src/film_pipeline/validation/runtime.py`), whereas
  F-VR-07 extracts a shared **dispatch table** (`src/film_pipeline/validation/dispatch.py`); extracting either one
  alone would not fix the other.

### F-VR-04 — `ConsensusBuilder` is called with serialized dicts and its `AttributeError` is swallowed, so the algorithmic consensus never runs

- **Class:** O8 (missing contract — an untyped list crosses the seam and is re-parsed by attribute access)
- **Severity:** Critical (impact 4 × drift 5 = 20)
- **Concern:** The QC node stores `ValidationReport.model_dump()` dicts in `_validation_reports` and
  then hands that list to `ConsensusBuilder.build`, which only accepts typed `ValidationReport`
  objects; the resulting `AttributeError` is caught by a bare `except Exception: return`, so the
  algorithmic consensus silently never exists.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/qc.py:392-393` — writer stores dicts —
    `reports = state.setdefault("_validation_reports", [])` / `reports.append(report.model_dump())`
  - `src/film_pipeline/graph/nodes/qc.py:166,174-177` — reader passes them straight through and
    swallows the failure —
    `"reports = state.get("_validation_reports", [])"` … `"try:\n        consensus = ConsensusBuilder().build(reports, artifact_refs)\n    except Exception:\n        return"`
  - `src/film_pipeline/validation/consensus.py:66-71` — the typed contract —
    `model_id=r.validator_id,` / `validator_id=r.validator_id,` / `score=r.score,`
  - `src/film_pipeline/schemas/validation.py:32` — the declared element type —
    `class ValidationReport(SchemaBase):`
- **Drift proof:** **existing divergence, executable.** Feeding the builder the exact runtime
  payload raises `AttributeError: 'dict' object has no attribute 'validator_id'`, caught at
  `src/film_pipeline/graph/nodes/qc.py:176-177`; feeding it `ValidationReport` objects succeeds. Both callers are live
  (`_run_validators` is invoked by `src/film_pipeline/graph/nodes/qc.py:38` on the repair path and by
  `src/film_pipeline/app/_graph_exec.py:337`). No test calls `_build_consensus_if_needed`
  (`grep -rn "_build_consensus_if_needed" tests` → 0 hits) and
  `grep -rn "consensus_report_ref" tests` → 0 hits, so the silent failure is unpinned.
- **Reproduce:**
  ```bash
  ./.venv/bin/python - <<'PY'
  from film_pipeline.validation.consensus import ConsensusBuilder
  from film_pipeline.schemas.validation import ValidationReport
  from film_pipeline.schemas._base import ValidationModality, ValidationScope, ValidationStatus
  r = ValidationReport(validation_id="v1", validator_id="scene-writing-validator",
      scope=ValidationScope.SCENE, modalities=[ValidationModality.TEXT], score=90,
      status=ValidationStatus.PASS)
  try: ConsensusBuilder().build([r.model_dump(), r.model_dump()], [])
  except Exception as e: print("dict input FAILS ->", type(e).__name__, e)
  print("model input OK ->", ConsensusBuilder().build([r, r], []).consensus_status)
  PY
  grep -rn "_build_consensus_if_needed\|consensus_report_ref" tests
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/qc.py`, `src/film_pipeline/validation/consensus.py`, `src/film_pipeline/app/_graph_exec.py`,
  `src/film_pipeline/mcp/tools/helpers.py:214-223` (`_report_summary` is what the MCP surface shows instead of a
  consensus), `src/film_pipeline/artifacts/registry.py:171-174` (`consensus_report` artifact type that is then never
  produced on this path). User-visible consequence: no algorithmic consensus artifact at QC;
  agreement level, disagreements, and `orchestrator_recommendation` are never computed for the
  sequential path, and nothing surfaces the failure.
- **Candidate owner module:** `src/film_pipeline/validation/consensus.py` — owns consensus construction and its
  input contract; the graph must hand it typed reports (or the builder must accept a typed
  `list[ValidationReport]` only, with the node responsible for deserialization).
- **Extraction sketch:** store typed `ValidationReport` objects in an internal channel and
  `model_dump()` only at the persistence boundary (or re-validate with
  `ValidationReport.model_validate` inside `ConsensusBuilder.build`); replace
  `except Exception: return` with a logged, typed refusal so the failure cannot be silent; guard
  test: run `_run_validators` on a state with two validator reports and assert
  `state["consensus_report_ref"]` is set.
- **Prior art:** new (no prior doc cites the dict/typed mismatch; `documentation/reviews/arch-lens-dataflow.md:110`
  describes the consensus path as if it worked, and `docs/clean-code-refactor/BASELINE.md:261`
  scores `src/film_pipeline/validation/consensus.py` as `PASS` coverage). This finding corrects that record.

### F-VR-05 — Split consensus state authority: two writers of `consensus_report_ref` in one node run, and the router reads a `consensus_report` key nothing writes

- **Class:** O3 (split state authority)
- **Severity:** High (impact 3 × drift 4 = 12) — recomputed during verification: writer A cannot
  succeed at HEAD (F-VR-04), so the last-writer-wins race is latent, not live; the live defect is
  the unwritten router key (wrong internal routing, recoverable)
- **Concern:** Within a single `qc_node` run, two independent consensus producers are coded to write
  the same `consensus_report_ref`/artifact-id pair (today only the second one can succeed), while
  the router's authoritative consensus reader targets a differently-named state key
  (`consensus_report`) that no production module writes and that is not a registered channel.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/qc.py:180-182` — writer A (algorithmic; unreachable at HEAD per
    F-VR-04) — `ref = _save_artifact(state, consensus, "consensus_report", phase)` / `state["consensus_report_ref"] = ref`
  - `src/film_pipeline/graph/nodes/qc.py:107-111` — writer B (LLM agent), the effective writer —
    `report = result.get("consensus_report")` / `ref = _save_artifact(state, report, "consensus_report", "qc")`
  - `src/film_pipeline/agents/impl/qc_synthesis_agent.py:61-71` — the second implementation's
    normative model — `report = ConsensusReport(` … `return {"consensus_report": report}`
  - `src/film_pipeline/graph/_action_routing.py:110` — the reader that can never fire —
    `consensus = state.get("consensus_report")`
  - `src/film_pipeline/graph/orchestrator_state.py:156-159` — the channel registry omits the key —
    `"_validation_reports",` / `"full",` / `"validator reports accumulated within the node run",`
- **Drift proof:** **existing divergence.** `grep -rn '"consensus_report":' src` returns exactly one
  producer (`src/film_pipeline/agents/impl/qc_synthesis_agent.py:71`, an agent *result* key) and
  `src/film_pipeline/graph/nodes/qc.py:107` is its only consumer — which persists it as a ref, never as state. So
  `_action_routing._consensus_status` always returns `None` and rule 6 always falls back to
  `_most_severe_report(reports)` (`src/film_pipeline/graph/_action_routing.py:139-140`). The unit test that pins the
  consensus-precedence behaviour hand-injects the key
  (`tests/unit/graph/test_router_validation_status.py:77-80`, `"consensus_report": {`), i.e. it pins
  a state shape production never produces. Mutation scenario: change `QCSynthesisAgent`'s default
  `consensus_status` from `"pass"` to `"blocked"`
  (`src/film_pipeline/agents/impl/qc_synthesis_agent.py:66`) — no routing decision anywhere changes, because the router reads a
  different key, and no test fails. **Latency caveat:** because writer A raises before writing
  (F-VR-04), there is no live "which consensus did the human see" race today; the two-writer hazard
  becomes live the moment F-VR-04 is fixed, which is why the pair must be fixed together.
- **Reproduce:**
  ```bash
  grep -rn "consensus_report" --include=*.py src
  grep -rn "consensus_report" src/film_pipeline/graph/orchestrator_state.py    # → no channel row
  grep -rn "consensus_report" tests/unit/graph/test_router_validation_status.py
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/qc.py`, `src/film_pipeline/agents/impl/qc_synthesis_agent.py`,
  `src/film_pipeline/validation/consensus.py`, `src/film_pipeline/graph/_action_routing.py`, `src/film_pipeline/app/_graph_exec.py:342-344`
  (persists only `consensus_report_ref`), `src/film_pipeline/artifacts/registry.py:171`. User-visible consequence: the
  orchestrator's consensus-based gate rule never sees the consensus report (the ref is persisted and
  human-renderable — see §2.4 — but not routed on), and fixing F-VR-04 without F-VR-05 would
  immediately reintroduce a silent last-writer-wins overwrite between the two producers
  (`_synthesize_consensus_report` at `src/film_pipeline/graph/nodes/qc.py:40` runs after `_build_consensus_if_needed` at
  `:39`).
- **Candidate owner module:** `src/film_pipeline/validation/consensus.py` — owns `ConsensusReport` construction and
  the single state projection (`consensus_report` payload + `consensus_report_ref`), with the agent
  and the builder as two *inputs* to one writer.
- **Extraction sketch:** pick one producer (or explicitly merge: algorithmic agreement metrics +
  LLM narrative) and one writer; register `consensus_report` in `ORCH_CHANNELS`
  (`src/film_pipeline/graph/orchestrator_state.py:93-159`) **or** change `_action_routing._consensus_status` to load the
  ref (`consensus_report_ref`) from the artifact store; delete the other producer. Guard test: after
  `qc_node`, assert `state["consensus_report"]` (or the ref-resolved report) is what
  `compute_actions` reads; assert a non-`pass` consensus status changes `next_action`.
- **Prior art:** `documentation/reviews/arch-lens-dataflow.md:110` notes that consensus appears only
  on the repair path. **What is new at HEAD:** the router's reader key (`state["consensus_report"]`)
  has no writer and no channel registration, which makes the router's consensus precedence branch
  (`src/film_pipeline/graph/_action_routing.py:108-115`) unreachable in production — a second, independent reason
  `NEEDS_REVISION` cannot reach rule 6 (F-VR-02).

### F-VR-06 — The approve-vs-request-revision gate decision is re-derived at seven sites, including a test that replicates the production logic

- **Class:** O5 (policy-by-branch)
- **Severity:** High (impact 3 × drift 5 = 15)
- **Concern:** "May this gate approve?" is computed from the same blocking-issue count in seven
  enumerated sites spanning three packages (six production derivations plus a test-side replica),
  with only one of them enforcing anything, and the behaviour test asserts against a copy of the
  policy rather than the policy itself.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/approval.py:249-251` — the only *enforcement* —
    `if _count_blocking_issues(state):` / `return {"approved": False, "_approval_blocked_by_issues": True}`
  - `src/film_pipeline/graph/nodes/approval.py:113-115` — the interrupt payload's advisory copy —
    `allowed_actions: list[str] = []` / `if blocking_count == 0:` / `allowed_actions.append("approve_phase")`
  - `src/film_pipeline/graph/nodes/approval.py:221-224` — headless copy —
    `approve_phase_node(state) if _count_blocking_issues(state) == 0 else {"approved": False, ...}`
  - `src/film_pipeline/graph/_action_routing.py:154-159` — router copy —
    `if blocking_count == 0:\n        result.eligible.append("approve_phase")` … `result.eligible.append("request_revision")`
  - `src/film_pipeline/review/actions.py:49-55` — review-package copy —
    `if has_blocking_issues:\n        result.blocked.append("approve_phase")`
  - `src/film_pipeline/mcp/tools/review.py:63-65` — the MCP caller's own count that feeds it —
    `return [i for i in state.get("issues", []) if i.get("severity") == "blocking"]`
  - `tests/unit/graph/test_real_human_gates.py:153-174` — the policy is *copied into the test* —
    `"""Replicate the payload-building logic from await_approval_node for testing."""` … `if blocking_count == 0:\n        allowed_actions.append("approve_phase")`
- **Drift proof:** mutation scenario with silent failure. Change the enforcement predicate
  `_count_blocking_issues` (`src/film_pipeline/graph/nodes/approval.py:52-55`) to also treat `"info"` as blocking; the gate payload
  (`src/film_pipeline/graph/nodes/approval.py:111`), the headless path (`:223`), and the router (`src/film_pipeline/graph/_action_routing.py:95-97`, its own
  `_blocking_issue_count`) each have their own copy, and `src/film_pipeline/mcp/tools/review.py:65` computes the count
  independently before handing it to `src/film_pipeline/review/actions.py:49-55`, which branches on it a fifth and
  sixth time — so
  `src/film_pipeline/review/actions.py:49-55` would still advertise `approve_phase` as available in the review package
  while `approve_phase_node` refuses it. No test fails: the gate tests call the replicated
  `_build_payload` (`tests/unit/graph/test_real_human_gates.py:29,48,70,86`) and `tests/unit/review/test_actions.py`
  tests `compute_available_actions` in isolation; nothing asserts agreement between the payload,
  the router, and the review package.
- **Reproduce:**
  ```bash
  grep -rn "severity.*== \"blocking\"\|_count_blocking_issues\|_blocking_issue_count\|has_blocking_issues" \
    --include=*.py src | grep -v 'severity": "blocking"'
  grep -rn "_build_payload(" tests/unit/graph/test_real_human_gates.py
  grep -rn "compute_available_actions" tests
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/approval.py`, `src/film_pipeline/graph/_action_routing.py`, `src/film_pipeline/review/actions.py`,
  `src/film_pipeline/mcp/tools/review.py`, `src/film_pipeline/app/_graph_exec.py` (`run_validation` preserves non-validator issues at
  `:327-334`), `src/film_pipeline/cli/run.py:280`, `src/film_pipeline/cli/driver.py:221`, `src/film_pipeline/app/_resume.py:25`. User-visible consequence:
  the human can be shown "approve" as an available action in one surface and have it refused in
  another (or the converse), with no reconciliation.
- **Candidate owner module:** `src/film_pipeline/validation/gate_policy.py` (or `src/film_pipeline/review/actions.py` promoted to own
  it) — one function `available_gate_actions(issues) -> AvailableActions` consumed by the interrupt
  payload, the router, `approve_phase_node`'s guard, and the review package.
- **Extraction sketch:** introduce `is_blocking_issue(issue) -> bool` and
  `gate_decision(issues) -> GateDecision` next to `IssueSeverity`; delete the six local production
  copies (leaving the seventh site — the test replica — replaced by an assertion against the real
  payload); have
  `_build_gate_payload` call the review-package builder (see F-VR-09) instead of assembling its own
  dict. Guard test: assert `available_gate_actions(issues)` equals the allowed set in the real
  interrupt payload and in the `ReviewPackage.available_actions` for the same state — replacing the
  replicated `_build_payload` helper.
- **Prior art:** `documentation/reviews/arch-lens-boundaries.md:196` notes three parallel operator
  surfaces with "two implementations of 'what should the operator do next'". **What is new at HEAD:**
  the gate-policy duplication is now counted inside the graph too (payload / headless / router /
  guard), and the strongest drift proof is the test-side replica at
  `tests/unit/graph/test_real_human_gates.py:153`.

### F-VR-07 — Four independent phase→validator dispatch tables; nothing proves they agree, and the delivery validator is absent from both QC paths

- **Class:** O4 (parallel registries — dispatch tables that must agree)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** Which validator runs at which phase is declared four times (registry scopes, the
  sequential node's runner tuples, the subgraph's worker/map pairs, and the MCP tool's phase specs),
  and the four sets already disagree.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/qc.py:361-368` — table 1 —
    `_VALIDATOR_RUNNERS: tuple[tuple[set[str], _ValidatorRunner], ...]` with `({"delivery"}, _run_delivery_validators)`
  - `src/film_pipeline/graph/subgraphs/qc.py:45-52` and `:210-217` — table 2 (ids and worker order) —
    `_VALIDATOR_MAP: dict[str, str] = {` … `_WORKER_NODES: tuple[str, ...] = (`
  - `src/film_pipeline/graph/subgraphs/qc.py:153-160` — table 3, artifact routing —
    `_VALIDATOR_ARTIFACTS: dict[str, tuple[str, ...]] = {`
  - `src/film_pipeline/mcp/tools/validation.py:123-158` — table 4, `_PhaseSpec` arms —
    `_PhaseSpec(phases=("delivery",), ... validators=_delivery_validators)`
  - `src/film_pipeline/validation/validators/__init__.py:11-167` — the declared scope/modality
    contract that tables 1-4 never consult
- **Drift proof:** **existing divergence.** `DeliveryCompletenessValidator` is declared for the
  `delivery` phase in the MCP table (`src/film_pipeline/mcp/tools/validation.py:152-157`,
  `_PhaseSpec(\n            phases=("delivery",),` / `validators=_delivery_validators,`) and runs
  through the *sequential* QC node only when `phase == "delivery"` (`src/film_pipeline/graph/nodes/qc.py:367`), but it is
  absent from `_WORKER_NODES` (`src/film_pipeline/graph/subgraphs/qc.py:210-217`) and from every `qc`-phase runner set
  (`src/film_pipeline/graph/nodes/qc.py:362-366`), so the forward QC subgraph never validates delivery completeness. The MCP
  arm is narrower still than its table implies: the *registered* `run_validation` tool
  (`src/film_pipeline/mcp/tools/registry.py:240`, `_register(registry, "run_validation", ToolGroup.VALIDATION,
  run_validation, mutates=True)`) dispatches only two phases — `src/film_pipeline/mcp/tools/validation.py:298-301`
  (`if phase_str == "visual_dev":` / `elif phase_str == "script":`) — and otherwise returns the
  success-shaped `if not reports:` / `        return _ok(message="No validators found for this
  phase.")` (`:305-306`), so its `delivery` `_PhaseSpec` is unreachable through that tool. The
  delivery spec is reachable only through `get_validation_report`'s live fallback —
  `src/film_pipeline/mcp/tools/validation.py:343-347` (`reports=_run_live_validators(rt, store, project_id, fp,
  phase_str),` / `source="live",`), which filters `if phase_str not in spec.phases:` at `:167` — and
  only when no stored QC reports exist, since `:325-332` returns those first. **Correction recorded
  after verification:** the earlier claim that delivery runs "through the MCP table" is qualified
  above — the registered tool cannot reach it at all. Coverage consequence: on the forward path no
  delivery-completeness check runs, and on the MCP path it runs only as an unrequested side effect
  of asking for a report. Mutation scenario: add a validator class to `_VALIDATOR_MAP`
  (`src/film_pipeline/graph/subgraphs/qc.py:45-52`) and its `cls_map` without adding it to `src/film_pipeline/graph/nodes/qc.py`'s
  `_VALIDATOR_RUNNERS`; the repair path silently skips it. **Qualification recorded after
  verification:** the sequential table's *own* membership is pinned —
  `tests/unit/graph/test_qc_validator_dispatch.py:65-107` asserts each runner registers exactly once
  and fires for exactly the expected phase set, including the `qc-covers-upstream-but-not-delivery`
  case at `:85-89` — but *nothing asserts agreement between the tables*: that test imports only
  `film_pipeline.graph.nodes.qc` (`:15`), never `src/film_pipeline/graph/subgraphs/qc.py` or `src/film_pipeline/mcp/tools/validation.py`, so a
  validator present in one table and absent from another ships green. Table 3 also hardcodes artifact-id
  preferences that table 1 expresses only as "load all `artifact_refs`" — a second divergence in
  *what* is validated, not only *whether*.
- **Reproduce:**
  ```bash
  grep -n "_VALIDATOR_RUNNERS" -A 8 src/film_pipeline/graph/nodes/qc.py
  grep -n "_WORKER_NODES" -A 9 src/film_pipeline/graph/subgraphs/qc.py
  grep -n "_live_validator_specs" -A 36 src/film_pipeline/mcp/tools/validation.py
  grep -rn "DeliveryCompletenessValidator" --include=*.py src
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/qc.py`, `src/film_pipeline/graph/subgraphs/qc.py`, `src/film_pipeline/mcp/tools/validation.py`,
  `validation/impl/*`, `src/film_pipeline/post/delivery_packaging_agent.py:190-196` (a fifth instantiation site),
  `graph/orchestrator_validators/*` (a parallel validator family with its own phase wiring at
  `src/film_pipeline/graph/nodes/prep.py:257`, `src/film_pipeline/graph/nodes/visual.py:126,465,576,588`, `src/film_pipeline/graph/nodes/generation.py:32`). User-visible
  consequence: "validation theater" — the MCP validation report and the graph QC verdict can list
  different validators for the same phase, with the delivery validator never firing on the forward
  path.
- **Candidate owner module:** `src/film_pipeline/validation/dispatch.py` — owns `PHASE_VALIDATORS:
  dict[FilmPhase, tuple[type[BaseValidator], ...]]` and `VALIDATOR_ARTIFACTS`, consumed by the
  subgraph workers, the sequential runner, and the MCP tool.
- **Extraction sketch:** collapse tables 1-3 into one table keyed by `FilmPhase` (the MCP `_PhaseSpec`
  becomes a projection of it); keep table 4's loader lambdas but source the validator tuples from
  the shared table; guard test: for every `FilmPhase`, assert the subgraph worker set, the sequential
  runner set, and the MCP spec set are equal.
- **Prior art:** `documentation/reviews/arch-lens-boundaries.md:161,173` ("Adding a validator
  requires editing both hardcoded tables or QC and the MCP surface disagree"; recommendation of a
  single `PHASE_VALIDATORS` table) and `documentation/reviews/arch-lens-flexibility.md:17`. **What is new at HEAD:** the
  disagreement is now proven to have *concrete coverage consequences* (delivery validator absent
  from both QC paths; artifact-selection tables differ), not only a maintenance cost.
  **Distinct from F-VR-03 (double-counting check):** this finding owns the *table-level* invariant —
  four declarations of phase→validator membership must agree, MCP `_PhaseSpec` included — while
  F-VR-03 owns the *path-level* invariant that the two live QC entry points behave identically.
  Different candidate owners (`src/film_pipeline/validation/dispatch.py` here vs `src/film_pipeline/validation/runtime.py` there); see
  the full differentiation at F-VR-03.

### F-VR-08 — `blocking_conditions`/`warning_conditions` are inert; "which finding blocks" is re-derived inline in every validator

- **Class:** O1 (duplicated normative model)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** Both registries declare which finding codes block and which warn, but nothing in
  `src/` ever reads those lists — the real severity model is hardcoded per finding beside each
  rule implementation — so the declared contract can drift arbitrarily from behaviour.
- **De-facto owners:**
  - `src/film_pipeline/schemas/registries/validator_registry.py:32-33` — the declared model, read by
    no one — `blocking_conditions: list[str] = Field(default_factory=list)` / `warning_conditions: …`
  - `src/film_pipeline/validation/impl/script_structure.py:139 vs :45-46` — declaration vs the
    enforcement that actually decides — `"code": "scene_count_under_min",` / `"severity": "blocking",`
  - `src/film_pipeline/validation/base.py:261-262` — the only place severity is read, and only for
    partitioning into report fields — `blocking = [i for i in issues if i.severity == "blocking"]`
  - `src/film_pipeline/graph/nodes/qc.py:395-401` — same partition re-derived for state issues —
    `severities = (("blocking", report.blocking_issues), ("warning", report.warnings))`
  - `src/film_pipeline/graph/subgraphs/qc.py:233` — a third identical partition —
    `for severity, key in (("blocking", "blocking_issues"), ("warning", "warnings")):`
- **Drift proof:** mutation scenario with silent failure. Delete every `blocking_conditions`/
  `warning_conditions` argument from all 22 entry literals (`src/film_pipeline/validation/validators/__init__.py`, `impl/*.py`);
  every validator behaves identically because no code path reads them
  (`grep -rn "blocking_conditions\|warning_conditions" --include=*.py src | grep -v "src/film_pipeline/validation/validators/__init__.py\|impl/"` → only the two schema field definitions), and no test fails —
  `tests/unit/validation/test_impl_validators.py` asserts on emitted severities, never on the entry
  lists. Conversely, the `scene_count_under_min` divergence in F-VR-01 is invisible precisely because
  the declared list has no enforcement role.
- **Reproduce:**
  ```bash
  grep -rn "blocking_conditions\|warning_conditions" --include=*.py src | grep -v "src/film_pipeline/validation/validators/__init__.py\|src/film_pipeline/validation/impl/"
  grep -rn "blocking_count = sum\|severity.*== \"blocking\"" --include=*.py src/film_pipeline/validation
  grep -rn "ValidatorRegistryEntry(" --include=*.py src | wc -l   # → 23 = 22 entry literals + the class declaration
  ```
- **Blast radius:** all `validation/impl/*.py`, `src/film_pipeline/validation/validators/__init__.py`,
  `src/film_pipeline/validation/base.py`, `src/film_pipeline/graph/nodes/qc.py`, `src/film_pipeline/graph/subgraphs/qc.py`, `src/film_pipeline/schemas/validation.py:25`.
  User-visible consequence: the published validator contract (what a validator blocks on, used by
  `MVP_VALIDATORS` consumers and shown in `list_validation_issues`) is not the behaviour a reviewer
  gets.
- **Candidate owner module:** `src/film_pipeline/validation/registry.py` — owns the entry lists *and* provides
  `severity_for_code(entry, code) -> IssueSeverity`, so implementations classify findings through
  the contract instead of beside it.
- **Extraction sketch:** have `BaseValidator.run` (`src/film_pipeline/validation/base.py:250-291`) map each raw finding's
  severity through `entry.blocking_conditions`/`warning_conditions` (with an explicit default for
  undeclared codes) — or delete both fields and make the impl-local severities normative, then
  remove `blocking_conditions`/`warning_conditions` from all 22 literals. Guard test: for each
  impl validator, assert `set(emitted_blocking_codes) == set(entry.blocking_conditions)`.
- **Prior art:** new (prior art covers the registry/threshold duplication, not the inert condition
  lists).

### F-VR-09 — The typed review package exists only on the MCP path; the LangGraph human gate shows an ad-hoc dict

- **Class:** O6 (parallel lifecycle)
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** The human-gate representation is built twice — once as a typed `ReviewPackage` with
  diff, validation results, and available/blocked actions, and once as an inline dict inside the
  interrupt payload — and the graph path never uses the typed contract.
- **De-facto owners:**
  - `src/film_pipeline/review/generator.py:65-80` — the typed builder's only construction site —
    `return ReviewPackage(` … `available_actions=actions.available,` / `blocked_actions=actions.blocked,`
  - `src/film_pipeline/mcp/tools/review.py:42-46` — its only consumer —
    `from film_pipeline.review.generator import ReviewPackageGenerator` / `generator = ReviewPackageGenerator()`
  - `src/film_pipeline/graph/nodes/approval.py:121-129` — the graph's parallel representation —
    `return {\n        "project_id": state.get("project_id", ""),` … `"allowed_actions": allowed_actions,`
  - `src/film_pipeline/schemas/approval.py:44-47` — the contract the graph never emits —
    `class ReviewPackage(SchemaBase):` / `"""The package a human reviewer sees at an approval gate."""`
- **Drift proof:** mutation scenario with silent failure *on both paths*. Add a required field to
  `ReviewPackage` (e.g. `risks_summary`): `src/film_pipeline/review/generator.py:65-80` raises while constructing it,
  but the MCP caller swallows the failure — `src/film_pipeline/mcp/tools/review.py:58-59` is
  `except Exception:` / `        return None` under the docstring `"""Build the structured review
  package; None when generation fails."""` (`:41`) — and `review_phase_artifacts` degrades to its
  fallback at `:104-106` (`if pkg is None:` / `# Fallback to simple artifact list if generator fails`
  / `return _ok(artifacts=artifact_list, phase=phase)`), i.e. a *successful* tool response with the
  typed package quietly absent. `src/film_pipeline/graph/nodes/approval.py:121-130` is untouched, so the real human
  gate keeps rendering its ad-hoc dict without the new field. No test fails: no code path builds a
  `ReviewPackage` from graph state (`grep -rn "ReviewPackageGenerator" src` → `src/film_pipeline/mcp/tools/review.py:42`
  only), no test asserts the interrupt payload contains diff/validation/risks fields, and no test
  asserts the MCP tool errors (rather than degrading) when the generator fails. Correction recorded
  after verification: the earlier claim that the MCP path "fails loudly" is false — it degrades
  silently, which makes the seam *harder* to detect, not easier.
- **Reproduce:**
  ```bash
  grep -rn "ReviewPackageGenerator\|ReviewPackage(" --include=*.py src
  grep -rn "interrupt(payload)\|_build_gate_payload" src/film_pipeline/graph/nodes/approval.py
  grep -rn "review_package" src/film_pipeline/graph
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/approval.py`, `src/film_pipeline/review/generator.py`, `src/film_pipeline/review/actions.py`,
  `src/film_pipeline/review/diff.py`, `src/film_pipeline/mcp/tools/review.py`, `src/film_pipeline/schemas/approval.py`, `src/film_pipeline/graph/edges.py:31`
  (`present_review_package` routes to the human gate). User-visible consequence: a reviewer reached
  through the LangGraph interrupt sees fewer facts (no diff-from-approved, no validation results, no
  risks/cost, no blocked-action reasons) than a reviewer reached through the MCP
  `review_phase_artifacts` tool.
- **Candidate owner module:** `src/film_pipeline/review/generator.py` — owns the human-gate representation
  (`ReviewPackage`); the graph's `_build_gate_payload` becomes a thin projection of it.
- **Extraction sketch:** make `await_approval_node` build the payload from
  `ReviewPackageGenerator.build(...)` (passing `has_blocking_issues` from the shared gate policy of
  F-VR-06); keep the interrupt payload a `ReviewPackage` plus `stalled`/`recommendation`. Guard
  test: assert the interrupt payload equals the MCP review package for the same state.
- **Prior art:** `documentation/reviews/arch-lens-boundaries.md:196` ("Three parallel operator
  surfaces … Same state, three shapes"). **What is new at HEAD:** the graph-side gap is
  localized to `_build_gate_payload` (the MCP and `OperatorService` shapes were already noted); the
  typed `ReviewPackage` is confirmed to have exactly one construction site.

### F-VR-10 — The gate action vocabulary bypasses its own typed contract; approval/revision records are defined but never written

- **Class:** O8 (missing contract)
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** The declared approval vocabulary and record schemas are not used by the human gate:
  the graph accepts two spellings per action and persists free-form dicts, so a gate decision cannot
  be reconstructed from the typed records the schema advertises.
- **De-facto owners:**
  - `src/film_pipeline/schemas/approval.py:12` — the declared vocabulary —
    `ApprovalAction = Literal["approve", "request_revision", "reject", "escalate"]`
  - `src/film_pipeline/graph/nodes/approval.py:180-189` — the accepted vocabulary (superset, with
    synonyms the Literal rejects) — `if action in ("approve", "approve_phase"):` … `if action in ("revise", "request_revision"):`
  - `src/film_pipeline/graph/nodes/approval.py:133-148` — untyped normalization of arbitrary resume
    values — `str(decision.get("action", "")),` … `return "await", "", {}`
  - `src/film_pipeline/schemas/approval.py:16-28` — never constructed anywhere in `src/` —
    `class ApprovalRecord(SchemaBase):` … `action: ApprovalAction`
  - `src/film_pipeline/schemas/approval.py:30-40` — likewise unused —
    `class RevisionRequest(SchemaBase):`
- **Drift proof:** **existing divergence.** `_normalize_decision`/`_route_decision` accept
  `"approve_phase"` and `"revise"`, which `ApprovalAction` (`src/film_pipeline/schemas/approval.py:12`) does not
  contain; conversely `ApprovalAction`'s `"reject"` has no handler in `_route_decision`
  (`src/film_pipeline/graph/nodes/approval.py:180-190`, falling through to bare updates). `grep -rn "ApprovalRecord" --include=*.py src`
  returns only the class definition and package exports — zero construction sites — while the
  revision outcome is instead written as an issue dict (`src/film_pipeline/graph/nodes/approval.py:285-292`,
  `"code": "REVISION_REQUESTED"`). Mutation scenario: add `"reject"` to the router's branches; no
  schema, test, or persisted record changes, and no test fails.
- **Reproduce:**
  ```bash
  grep -rn "ApprovalRecord\|RevisionRequest" --include=*.py src
  grep -rn "ApprovalAction" --include=*.py src tests
  sed -n '173,190p' src/film_pipeline/graph/nodes/approval.py
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/approval.py`, `src/film_pipeline/schemas/approval.py`, `src/film_pipeline/schemas/__init__.py:159,243`,
  `src/film_pipeline/app/_graph_exec.py` (audit trail written as free-form `_record_audit` args), `src/film_pipeline/testing/mock_human.py:36-50`
  (returns the same untyped strings). User-visible consequence: the typed contract is not the
  representation authority for approvals; any consumer that expects `ApprovalRecord`/`RevisionRequest`
  has no data source.
- **Candidate owner module:** `src/film_pipeline/schemas/approval.py` + `src/film_pipeline/graph/nodes/approval.py` — the schema owns the
  vocabulary; the gate owns constructing `ApprovalRecord`/`RevisionRequest` as the persisted
  representation.
- **Extraction sketch:** route every gate decision through a single `ApprovalDecision` value
  (`ApprovalAction` + note + external state), have `_route_decision` reject unknown actions with a
  typed error, and persist `ApprovalRecord`/`RevisionRequest` at the gate and in
  `app/_graph_exec.approve_phase`/`request_revision`. Guard test: for each `ApprovalAction` member,
  assert a handler exists and that a typed record is persisted.
- **Prior art:** new.

### F-VR-11 — "Requires human review" is derived twice; the report field and both helper predicates have no consumer

- **Class:** O1 (duplicated normative model)
- **Severity:** Medium (impact 2 × drift 3 = 6) — recomputed after verification; previously
  mislabelled Low, but 2 × 3 = 6 falls in the audit's Medium band (4-8).
- **Concern:** The set of statuses that require human review is encoded both inside
  `BaseValidator.run` and in a package-level helper that production never calls, and the resulting
  report field is read by no one.
- **De-facto owners:**
  - `src/film_pipeline/validation/base.py:286-290` — inline derivation, written into the report —
    `requires_human_review=status\n            in (\n                ValidationStatus.NEEDS_REVISION,\n                ValidationStatus.BLOCKED,\n            ),`
  - `src/film_pipeline/validation/thresholds.py:37-40` — the same predicate as an exported helper —
    `def needs_human_review(score, thresholds=None) -> bool:` … `return status in (ValidationStatus.NEEDS_REVISION, ValidationStatus.BLOCKED)`
  - `src/film_pipeline/validation/thresholds.py:32-34` — `is_blocking`, likewise uncalled in
    production — `return score_to_status(score, thresholds) == ValidationStatus.BLOCKED`
  - `src/film_pipeline/schemas/validation.py:45` — the field nobody reads —
    `requires_human_review: bool = False`
- **Drift proof:** mutation scenario with silent failure. Change
  `thresholds.needs_human_review` to include `PASS_WITH_NOTES`;
  `src/film_pipeline/validation/base.py:286-290` keeps the old rule, `ValidationReport.requires_human_review` keeps its old value,
  and nothing consumes it anyway (`grep -rn "requires_human_review" --include=*.py src` → schema
  fields plus the single writer at `src/film_pipeline/validation/base.py:286`). `grep -rn "is_blocking\|needs_human_review"
  --include=*.py src tests` shows the only callers are `tests/unit/validation/test_thresholds.py`
  and the package re-export in `src/film_pipeline/validation/__init__.py:13-14`.
- **Reproduce:**
  ```bash
  grep -rn "requires_human_review" --include=*.py src
  grep -rn "is_blocking\|needs_human_review" --include=*.py src tests
  ```
- **Blast radius:** `src/film_pipeline/validation/thresholds.py`, `src/film_pipeline/validation/base.py`, `src/film_pipeline/validation/__init__.py`,
  `src/film_pipeline/schemas/validation.py`. User-visible consequence: limited today (the helpers are dead), but the
  duplicated predicate is the natural place a future gate-policy change (F-VR-06) will be applied
  to only one of two sites.
- **Candidate owner module:** `src/film_pipeline/validation/thresholds.py` — owns both the mapping and the predicates
  derived from it.
- **Extraction sketch:** delete `is_blocking`/`needs_human_review` (or make `src/film_pipeline/validation/base.py:286` call
  `needs_human_review`), and either consume `requires_human_review` in the gate/router or remove the
  field. Guard test: assert `report.requires_human_review == needs_human_review(report.score, entry.thresholds)`.
- **Prior art:** new.

**3.2 Findings added after verification.**

The independent verifier (`docs/modular-architecture/reviews/verify-08.md`, section "Missed in scope", seams M1-M5) identified
five seams inside this cluster that the first pass did not file. Four are recorded below as findings
in the §1.7 format. The fifth (M5 — `tests/unit/graph/test_qc_validator_dispatch.py` was omitted from
the §1.1 table and from the "no test fails" reasoning of F-VR-03/F-VR-07) is a coverage defect rather
than an ownership defect, so it is folded into the updated §1.1 table and into the qualifications now
carried by F-VR-03 and F-VR-07. One verifier consequence is explicitly **not** adopted: the M3 claim
that the `consensus_report` spec/renderer "can never fire" is falsified in F-VR-12 below.

### F-VR-12 — Consensus artifacts are persisted with `artifact_type = script`, and a `MatrixPatch` is declared as `consensus_report`

- **Class:** O8 (missing contract — an unregistered type string crosses the save seam and is
  silently coerced) compounded by O1 (duplicated normative model — the id→kind registry and the
  class→`ArtifactType` map disagree)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** `ArtifactType` has no `consensus_report` member, yet two call sites pass or infer
  that exact string when saving, and the shared coercion helper swallows the `ValueError` and
  substitutes `SCRIPT`, so every QC consensus artifact and the QC matrix patch carry the wrong
  `artifact_type` while their registry kind is right.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/qc.py:83-89` — the patch is *declared* a consensus report —
    `patch_ref = _save_artifact(` / `            patch,` / `            "matrix_patch_qc",` /
    `            "qc",` / `            artifact_type="consensus_report",`
  - `src/film_pipeline/graph/nodes/qc.py:109` — the report relies on class-name inference instead —
    `ref = _save_artifact(state, report, "consensus_report", "qc")`
  - `src/film_pipeline/graph/nodes/_agent_artifacts.py:35-39` — the silent substitution —
    `if artifact_type is not None:` / `        try:` / `            return _ArtifactType(artifact_type)` /
    `        except ValueError:` / `            return _ArtifactType.SCRIPT`
  - `src/film_pipeline/graph/nodes/_context.py:310,318-321` — the same bad string, as a class map —
    `"ConsensusReport": "consensus_report",` … `return _ArtifactType(_ARTIFACT_TYPE_BY_CLASS.get(class_name, "script"))` / `except ValueError:` / `        return _ArtifactType.SCRIPT`
  - `src/film_pipeline/schemas/_base.py:27-75` — the contract that lacks the member; `grep -rn "consensus_report" src/film_pipeline/schemas/_base.py` returns nothing
  - `src/film_pipeline/artifacts/store.py:754-758` — where the wrong value becomes human-visible —
    `details = [` / `        f"- phase: {meta.phase.value}",` / `        f"- type: {meta.artifact_type.value}",`
- **Drift proof:** **existing divergence, reproduced at HEAD.** The artifact registry is keyed by *artifact id*, not by `artifact_type` (`src/film_pipeline/artifacts/registry.py:100-107`, `def spec_for(self, artifact_id: str)` … `spec = self._exact.get(artifact_id)`), and `src/film_pipeline/artifacts/store.py:128,194` calls `_render_markdown(spec.kind, meta, payload)`. So the *registered* `consensus_report` spec and its renderer **do** fire for `src/film_pipeline/graph/nodes/qc.py:109` — the verifier's M3 consequence ("the registered `consensus_report` artifact spec/renderer can never fire") is **false and is not adopted here**; the renderer prints the status verbatim (`src/film_pipeline/artifacts/rendering.py:164-170`, `for key in ("consensus_status", "agreement_level", "orchestrator_recommendation")`). What is broken is the *metadata*, verified by direct call at HEAD:

  ```
  infer ConsensusReport -> script
  resolve consensus_report+MatrixPatch -> script
  spec_for(consensus_report).kind = film.studio/consensus-report | renderer = render_consensus_report
  spec_for(matrix_patch_qc).kind = film.studio/matrix-patch | payload_model = MatrixPatch
  consensus_report in ArtifactType? False
  ```

  Consequence: the consensus report renders the correct body under a wrong header (`- type: script`),
  and the QC `MatrixPatch` is stored as `script` while its own registered spec declares
  `payload_model=MatrixPatch` (`src/film_pipeline/artifacts/registry.py:199`). Nothing consumes `artifact_type` for selection
  today (`grep -rn "artifact_type =="` / `artifact_type in` over `src` returns 0 comparisons; the field
  is only surfaced by `src/film_pipeline/artifacts/store.py:758`, `src/film_pipeline/mcp/tools/review.py:24`, `src/film_pipeline/mcp/tools/artifacts.py:40`,
  `src/film_pipeline/mcp/tools/projects.py:260`, `src/film_pipeline/app/services/_browse_ops.py:74`), so the drift is currently
  cosmetic-but-wrong metadata plus a live trap for the first type-based filter. Mutation scenario:
  rename or add an `ArtifactType` member; nothing fails, because nothing compares `_ARTIFACT_TYPE_BY_CLASS`
  or the two literal `"consensus_report"` save arguments against the enum.
- **Reproduce:**
  ```bash
  ./.venv/bin/python - <<'PY'
  from film_pipeline.graph.nodes._context import _infer_artifact_type
  from film_pipeline.graph.nodes._agent_artifacts import _resolve_artifact_type
  from film_pipeline.schemas.validation import ConsensusReport
  from film_pipeline.schemas.matrix_patch import MatrixPatch
  from film_pipeline.artifacts.registry import REGISTRY
  r = ConsensusReport(review_id="r1", agreement_level="high", consensus_status="pass")
  p = MatrixPatch(patch_id="qc_p1", matrix_ref="artifact:shot_bible:master_film_matrix:v1", phase="qc")
  print("infer ConsensusReport ->", _infer_artifact_type(r).value)
  print("resolve consensus_report+MatrixPatch ->", _resolve_artifact_type("consensus_report", p).value)
  print("spec_for(consensus_report).kind =", REGISTRY.spec_for("consensus_report").kind)
  print("spec_for(matrix_patch_qc).kind =", REGISTRY.spec_for("matrix_patch_qc").kind)
  PY
  grep -rn "consensus_report" src/film_pipeline/schemas/_base.py
  grep -rn "artifact_type ==\|artifact_type in" --include=*.py src | wc -l   # → 0 comparisons
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/qc.py`, `src/film_pipeline/graph/nodes/_agent_artifacts.py`, `src/film_pipeline/graph/nodes/_context.py`,
  `src/film_pipeline/artifacts/store.py`, `src/film_pipeline/schemas/_base.py`, `src/film_pipeline/artifacts/registry.py`. User-visible consequence: rescue
  and audit surfaces that print the artifact header (`- type: …`) label the QC consensus report and the
  QC matrix patch as `script`, and any future inventory or routing keyed on `artifact_type` would
  silently mis-classify them; the markdown *body* is still correct, which is precisely why this has
  gone unnoticed.
- **Candidate owner module:** `src/film_pipeline/schemas/_base.py` (the `ArtifactType` catalogue) plus
  `src/film_pipeline/artifacts/registry.py` — one place that owns "payload class → artifact type → registry kind", so
  the save path can never pass a string the enum does not contain.
- **Extraction sketch:** add `CONSENSUS_REPORT = "consensus_report"` to `ArtifactType` (and a
  `MATRIX_PATCH` member, since `"matrix_patch"` is also only a registry prefix), then replace
  `_ARTIFACT_TYPE_BY_CLASS`'s string map with `ArtifactType` members and make
  `_resolve_artifact_type` raise instead of defaulting to `SCRIPT` when an explicit `artifact_type` is
  unrecognised. Guard test: assert every value in `_ARTIFACT_TYPE_BY_CLASS` is an `ArtifactType`
  member, and that `_resolve_artifact_type(None, ConsensusReport(...))` returns
  `ArtifactType.CONSENSUS_REPORT`.
- **Prior art:** `docs/clean-code-refactor/BASELINE.md:261` (stringly-typed artifact typing noted);
  the specific id-keyed-registry vs class-map mismatch and the `MatrixPatch`-as-`consensus_report`
  save argument are **new at HEAD** and come from verifier seam M3 (with the "renderer can never fire"
  consequence corrected).

### F-VR-13 — `consensus_report_ref`/`qc_patch_ref` cross the node boundary through a private key tuple that `ORCH_CHANNELS` does not own and the parity sweep cannot see

- **Class:** O5 (policy-by-branch — a node declares its own boundary key set instead of the registry)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** `qc_node` copies two ref keys into its state update through a module-private tuple,
  neither key has an `ORCH_CHANNELS` row, and both the registry parity test and the AST writer sweep
  are scoped so that neither can observe them — contradicting the documented single owner of
  boundary keys.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/qc.py:29-30` — the private policy —
    `# Ref-valued state keys qc_node copies into its update once validators set them.` /
    `_QC_REF_KEYS: tuple[str, ...] = ("consensus_report_ref", "qc_patch_ref")`
  - `src/film_pipeline/graph/nodes/qc.py:42` — passed as the whole boundary rule —
    `updates = _collect_updates(gate_updates, new_state, state, _QC_REF_KEYS)`
  - `src/film_pipeline/graph/nodes/qc.py:61-64` — applied by hand, with a non-constant subscript —
    `for key in ref_keys:` / `        val = new_state.get(key)` / `        if val:` / `            updates[key] = val`
  - `src/film_pipeline/graph/nodes/_agent_handoff.py:9-12` — the ownership claim they contradict —
    "Which keys cross the node boundary — and how each is copied — is owned by" /
    "``graph.orchestrator_state.ORCH_CHANNELS``. This module contributes no key" /
    "names of its own; adding a channel means adding a registry row, which the" /
    "channel-registry parity tests enforce."
  - `src/film_pipeline/graph/orchestrator_state.py:93-165` — the registry, which has no row for
    either key (`grep -rn "consensus_report_ref\|qc_patch_ref" src/film_pipeline/graph/orchestrator_state.py` → 0)
  - `src/film_pipeline/graph/state_schema.py:157` and `:167` — both *are* GraphState fields —
    `consensus_report_ref: str` / `qc_patch_ref: str`
  - `tests/unit/graph/test_channel_registry.py:35-37` — the sweep scope that omits them —
    `_EXTRA_SWEEP_KEYS = frozenset(` / `    {"artifact_refs", "generation_requests", "_qc_reports", "_qc_raw_reports"}`
  - `tests/unit/graph/test_channel_registry.py:71-72` — the parity test only covers one namespace —
    `registered = {spec.key for spec in ORCH_CHANNELS if spec.key.startswith("_orchestrator")}`
  - `tests/unit/graph/test_channel_registry.py:292-293` — and the writer sweep inherits that scope —
    `return frozenset(spec.key for spec in ORCH_CHANNELS) | _EXTRA_SWEEP_KEYS`
  - `tests/unit/graph/test_channel_registry.py:200-205` — the "no hidden local key lists" claim that
    does not detect this one — `"""No hidden local key lists: anything unregistered stays behind."""`
    followed by `_propagate_side_effects({"_services": object(), "unknown_channel": [1]}, dest)`
- **Drift proof:** **existing divergence, reproduced by the verifier at HEAD** (`/tmp/sweep.py`):

  ```
  'consensus_report_ref': in ORCH_CHANNELS=False in sweep_scope=False in GraphState=True
  'qc_patch_ref':         in ORCH_CHANNELS=False in sweep_scope=False in GraphState=True
  ```

  Two structural blindnesses make the guard unable to catch it: (a) the parity tests filter to
  `startswith("_orchestrator")` (`tests/unit/graph/test_channel_registry.py:72,80-82`), so a plain GraphState field is
  checked by nothing; (b) the AST writer sweep records only `ast.Constant` string subscripts in scope
  (`:277-288`, `isinstance(target.slice, ast.Constant)` … `target.slice.value in scope`), so
  `updates[key]` at `src/film_pipeline/graph/nodes/qc.py:64` is invisible even if the keys were in scope. `_propagate_side_effects`
  compounds this: it iterates `ORCH_CHANNELS` only (`src/film_pipeline/graph/nodes/_agent_handoff.py:62-73`), so these two keys
  survive the node boundary *only* because `_collect_updates` copies them by hand — a second,
  unregistered propagation policy. Mutation scenario: rename the fields at `src/film_pipeline/graph/state_schema.py:157,167`;
  `src/film_pipeline/graph/nodes/qc.py:30,91,111` keep writing the old names, no unit test fails (the sweep excludes them, and
  `test_unregistered_keys_are_never_copied` never exercises `_collect_updates`), and the mismatch
  surfaces only at compiled-graph reduce time or as a silently dropped ref.
- **Reproduce:**
  ```bash
  grep -rn "consensus_report_ref\|qc_patch_ref" src/film_pipeline/graph/orchestrator_state.py
  grep -rn "_QC_REF_KEYS\|ref_keys" src/film_pipeline/graph/nodes/qc.py
  grep -n "_EXTRA_SWEEP_KEYS" -A 3 tests/unit/graph/test_channel_registry.py
  grep -n "startswith(\"_orchestrator\")" tests/unit/graph/test_channel_registry.py
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/qc.py`, `src/film_pipeline/graph/orchestrator_state.py`, `src/film_pipeline/graph/state_schema.py`,
  `src/film_pipeline/graph/nodes/_agent_handoff.py`, `tests/unit/graph/test_channel_registry.py`,
  `src/film_pipeline/graph/subgraphs/qc.py:266` (the subgraph writes the same conceptual value through the registered
  `_validation_reports` path instead). User-visible consequence: the QC verdict refs are the *one* pair
  of boundary keys outside the documented contract, so the contract's guarantee ("adding a channel
  means adding a registry row") does not hold for the phase that decides whether a human is asked to
  approve; a future channel-policy change silently skips them.
- **Candidate owner module:** `src/film_pipeline/graph/orchestrator_state.py` — `ORCH_CHANNELS` as the only boundary-key
  owner, with the sweep scope derived from `StudioGraphState` rather than from a hand-maintained extra
  set.
- **Extraction sketch:** delete `_QC_REF_KEYS` and add two `ORCH_CHANNELS` rows
  (`consensus_report_ref`, `qc_patch_ref`, propagation `full_truthy`); widen the parity test to every
  `StudioGraphState` field that any node writes, and teach `_sweep_boundary_writes` to resolve
  `updates[key]` when `key` is a loop variable bound to a literal tuple. Guard test: assert every
  `StudioGraphState` scalar field either has an `ORCH_CHANNELS` row or appears in a documented
  exclusion list, and that `set(_sweep_scope()) ⊇ {f for f in StudioGraphState.__annotations__}` for
  ref-valued fields.
- **Prior art:** the docstring claim it violates is at `src/film_pipeline/graph/nodes/_agent_handoff.py:9-12` (new at HEAD); the
  broader "state keys are declared in more than one place" theme is
  `documentation/reviews/arch-lens-dataflow.md:119`. **What is new at HEAD:** the specific
  unregistered pair and the proof that both guards are structurally blind to it (verifier seam M1 —
  the registration half of the `consensus_report_ref` concern that F-VR-05 owns; F-VR-05 covers the
  *two writers*, this finding covers the *unregistered channel*).

### F-VR-14 — The MCP validation tool writes an undeclared `validation_refs` project-state key while the registered `validation_report_refs` channel has no writer

- **Class:** O3 (split state authority — one registered channel with no writer, one writer with no registration)
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** The append-only channel `validation_report_refs` is declared in the schema,
  registered in `ORCH_CHANNELS`, documented, and wired to a reducer — and written by nobody — while
  `run_validation` persists its saved report refs under a differently-named key that no schema,
  registry row, or reducer map declares.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/validation.py:274-276` — the real writer, to an unregistered name —
    `active["_validation_reports"] = reports` / `    active.setdefault("validation_refs", []).extend(saved_refs)` /
    `    rt.projects[project_id] = active`
  - `src/film_pipeline/graph/state_schema.py:173` — the declared name — `validation_report_refs: Annotated[list[str], merge_unique]`
  - `src/film_pipeline/graph/orchestrator_state.py:163` — its registry row —
    `"validation_report_refs", "append_only", "append-only report-ref reducer channel"`
  - `src/film_pipeline/graph/nodes/_agent_handoff.py:31` — documentation that treats it as live —
    "``issues`` and ``validation_report_refs`` are append-only reducer channels;"
  - `src/film_pipeline/app/_graph_exec.py:470` — the reducer map it is wired into —
    `"validation_report_refs": merge_unique,`
- **Drift proof:** **existing divergence.** `grep -rn "validation_report_refs" --include=*.py src`
  returns exactly five hits — the schema field, the `ORCH_CHANNELS` row, the handoff docstring, the
  `_graph_exec` reducer map, and an unrelated `src/film_pipeline/schemas/repair.py:53` field — and **no writer**: the
  grep for an assignment is empty. Conversely `grep -rn "validation_refs" --include=*.py src tests`
  shows the project-state key written only at `src/film_pipeline/mcp/tools/validation.py:275`, read nowhere (the other
  hits are a different, per-artifact `validation_refs` on `ArtifactEnvelope`
  (`src/film_pipeline/artifacts/envelope.py:109,145`), `MatrixRow` (`src/film_pipeline/schemas/matrix.py:72`), `ArtifactMetadata`
  (`src/film_pipeline/schemas/artifact.py:66,91`), `checkpoint` (`src/film_pipeline/schemas/checkpoint.py:42`), and the row patch at
  `src/film_pipeline/graph/nodes/qc.py:428`). The asymmetry is specifically about the *refs*: the sibling channel
  `_validation_reports` **is** registered (`src/film_pipeline/graph/orchestrator_state.py:156-160`) and **is** written by the
  same function (`src/film_pipeline/mcp/tools/validation.py:274`, `active["_validation_reports"] = reports`), so one
  write was split across two keys — report bodies to a registered key, refs to an unregistered one.
  So one name covers three different concepts and the *registered* refs name covers
  none of the live writes. Mutation scenario: delete the `validation_report_refs` row from
  `ORCH_CHANNELS`; nothing fails, because the parity tests assert only that registered keys exist for
  declared constants — not that every row has a writer or reader. Note also that the store-backed QC
  path deliberately does not use this channel: `src/film_pipeline/graph/subgraphs/qc.py:266` puts the raw reports in
  `_validation_reports` and refs go to the generic `artifact_refs`.
- **Reproduce:**
  ```bash
  grep -rn "validation_refs\|validation_report_refs" --include=*.py src
  grep -rn "validation_report_refs" --include=*.py src | wc -l   # 5, none a writer
  ```
- **Blast radius:** `src/film_pipeline/mcp/tools/validation.py`, `src/film_pipeline/graph/state_schema.py`, `src/film_pipeline/graph/orchestrator_state.py`,
  `src/film_pipeline/app/_graph_exec.py`, `src/film_pipeline/schemas/repair.py`. User-visible consequence: the relation "this artifact was
  validated by these reports" is not reconstructible from graph state for MCP-run validations —
  `validation_refs` is propagated by no `ORCH_CHANNELS` row (`src/film_pipeline/graph/nodes/_agent_handoff.py:62-73` copies
  registered keys only), so it survives only inside the MCP runtime's own `rt.projects` dict, while the
  channel that was designed to carry it stays permanently empty.
- **Candidate owner module:** `src/film_pipeline/graph/orchestrator_state.py` — one registered ref channel per artifact
  family, with every writer targeting the declared name.
- **Extraction sketch:** point `_record_validation_results` at `validation_report_refs` (keeping
  `_validation_reports` for the report bodies), or delete the registered row and document
  `validation_refs` as an MCP-local cache with a name that does not collide with the three
  `validation_refs` schema fields. Guard test: after `run_validation` on a phase with validators,
  assert the saved refs appear under the `ORCH_CHANNELS`-declared name and survive a
  `_propagate_side_effects` round trip; assert the project-state key set is a subset of
  `StudioGraphState.__annotations__` plus a documented allow-list.
- **Prior art:** the audit's own §4.3 already listed `validation_refs` as owned state without filing a
  finding for it (noted by the verifier); otherwise **new at HEAD** (verifier seam M2).

### F-VR-15 — The registered `run_validation` tool cannot reach four of the six declared phase arms (five of the seven phases), and reports the refusal as success

- **Class:** O4 (parallel registries — the spec table and the tool's dispatch disagree) with O5
  (policy-by-branch)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** `_live_validator_specs` declares six phase arms, but `run_validation` — the
  *registered* mutating validation tool — dispatches only `visual_dev` and `script` and answers every
  other declared phase with a success-shaped `"No validators found for this phase."`, so four of
  those arms (five phases together, since the `post`/`assembly` arm covers two) are unreachable
  through the tool that is supposed to run them.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/validation.py:297-306` — the narrow dispatch and its success-shaped refusal —
    `try:` / `        if phase_str == "visual_dev":` / `        elif phase_str == "script":` … /
    `    if not reports:` / `        return _ok(message="No validators found for this phase.")`
  - `src/film_pipeline/mcp/tools/validation.py:138-157` — the four arms this cannot reach —
    `_PhaseSpec(` / `            phases=("gen_planning",),` … `            phases=("delivery",),`
  - `src/film_pipeline/mcp/tools/registry.py:240` — its registration as the mutating tool —
    `_register(registry, "run_validation", ToolGroup.VALIDATION, run_validation, mutates=True)`
  - `src/film_pipeline/mcp/tools/validation.py:343-347` — the only path that runs those arms —
    `reports=_run_live_validators(rt, store, project_id, fp, phase_str),` / `        source="live",`
  - `tests/unit/mcp/tools/test_validation.py:45-58` — the test that pins the refusal as *correct* —
    `active["current_phase"] = "intake"` … `assert result["ok"] is True` /
    `    assert result["message"] == "No validators found for this phase."`
- **Drift proof:** **existing divergence.** `_live_validator_specs` (`:127-158`) has exactly one
  consumer, `_run_live_validators` (`:166`), which is called from exactly one place,
  `get_validation_report` (`:345`) — the *read-only* tool. The registered mutating tool's phase test is
  a two-branch `if/elif` with no `else`, so `gen_planning`, `shot_bible`, `post`, `assembly`, and
  `delivery` all fall through to the empty-`reports` early return. The covering test for that return
  uses `"intake"` (`tests/unit/mcp/tools/test_validation.py:45-58`), a phase that has no arm in
  `_live_validator_specs` at all, and the only other two tests that assert the same message
  (`:227-240` at `visual_dev`, `:243-256` at `script`) use phases that *are* dispatched and merely
  have no artifact loaded — so none of the three can distinguish "phase legitimately has no
  validators" from "this tool never implemented the phase".
  Mutation scenario: add a phase arm to `_live_validator_specs`; the registered tool still refuses it
  and no test fails. This is also why F-VR-07's "delivery runs through the MCP table" needed
  qualification — see the corrected drift proof there.
- **Reproduce:**
  ```bash
  grep -n "def run_validation" -A 30 src/film_pipeline/mcp/tools/validation.py
  grep -n "_live_validator_specs" -A 36 src/film_pipeline/mcp/tools/validation.py
  # → six `phases=(...)` arms: script, visual_dev, gen_planning, shot_bible, post/assembly, delivery
  grep -rn '"run_validation"' src/film_pipeline/mcp/tools/registry.py
  grep -n "No validators found for this phase" -r src tests
  ```
- **Blast radius:** `src/film_pipeline/mcp/tools/validation.py`, `src/film_pipeline/mcp/tools/registry.py`, `src/film_pipeline/mcp/tools/__init__.py`
  (tool exports), `src/film_pipeline/app/services/operator.py:310` (its own `run_validation` wrapper),
  `src/film_pipeline/graph/nodes/qc.py`. User-visible consequence: an operator or agent asking the MCP surface to
  validate `gen_planning`, `shot_bible`, `post`, `assembly`, or `delivery` gets `ok: true` with no
  reports and no indication that the phase was never wired — while `get_validation_report` on the same
  phase would silently run validators and return them with `source="live"`, so the two MCP tools
  disagree about whether the phase is validatable at all.
- **Candidate owner module:** `src/film_pipeline/validation/dispatch.py` — the same shared phase→validator table
  nominated by F-VR-07; the MCP tool becomes a projection that cannot name fewer phases than the table
  declares.
- **Extraction sketch:** replace the `if phase_str == "visual_dev" / elif "script"` dispatch with a
  lookup into the shared table, and make "no validators for this phase" an explicit error (or an
  `_ok` carrying `"validators": []` plus a `wired: false` marker) rather than an indistinguishable
  success. Guard test: for every `phases` tuple in the shared table, assert the registered
  `run_validation` tool produces at least one report when the loader returns data, or a distinguishable
  "not wired" response.
- **Prior art:** `documentation/reviews/arch-lens-boundaries.md:161` (hardcoded validator tables across
  QC and the MCP surface). **What is new at HEAD:** the divergence is now shown to exist *inside* the
  MCP module — its own spec table versus its own dispatch — and to be codified by a test that asserts
  the refusal is correct (verifier seam M4).

---

## 4. Ownership map, clean concerns, and candidate module boundary

### 4.1 Ownership map (concern → current de-facto owners → finding)

| Concern | Current owners | Status |
|---|---|---|
| Validator identity/scope/modality/thresholds | `src/film_pipeline/validation/validators/__init__.py:11-167` (declared), `impl/*.py` (executed), `src/film_pipeline/validation/registry.py:15-46` (unused), `src/film_pipeline/schemas/registries/validator_registry.py:37-40` (unused) | **distributed — F-VR-01** |
| Which phase runs which validator | `src/film_pipeline/graph/nodes/qc.py:361-368`, `src/film_pipeline/graph/subgraphs/qc.py:45-52,210-217`, `src/film_pipeline/mcp/tools/validation.py:123-158`, `src/film_pipeline/validation/validators/__init__.py` scopes | **distributed — F-VR-07** |
| Score → status mapping | `src/film_pipeline/validation/thresholds.py:9-29` (single definition), inputs declared in 22 places | **single function, duplicated inputs — F-VR-02** |
| Which finding code blocks/warns | 22 entry literals (inert) + inline `"severity": "blocking"` in each impl | **distributed — F-VR-08** |
| Multi-reviewer consensus construction | `src/film_pipeline/validation/consensus.py:17-138` + `src/film_pipeline/agents/impl/qc_synthesis_agent.py:26-77` | **two implementations — F-VR-04, F-VR-05** |
| Consensus representation in state | `src/film_pipeline/graph/nodes/qc.py:180-182`, `src/film_pipeline/graph/nodes/qc.py:107-111` (both write `consensus_report_ref`) | **no single writer — F-VR-05** |
| Human-gate approve vs revision decision | `src/film_pipeline/graph/nodes/approval.py:52-55,113-119,221-224,249-251`, `src/film_pipeline/graph/_action_routing.py:90-97,143-170`, `src/film_pipeline/review/actions.py:30-55`, `src/film_pipeline/mcp/tools/review.py:63-65` (+ test replica `tests/unit/graph/test_real_human_gates.py:153-174`) | **seven derivations (six production + one test replica) — F-VR-06** |
| Human-gate representation | `src/film_pipeline/review/generator.py:38-80` (MCP only), `src/film_pipeline/graph/nodes/approval.py:103-130` (graph) | **two shapes — F-VR-09** |
| Approval/revision record | `src/film_pipeline/schemas/approval.py:12,16,30` (unused), raw dicts at `src/film_pipeline/graph/nodes/approval.py:281-293` | **contract unused — F-VR-10** |
| `requires_human_review` | `src/film_pipeline/validation/base.py:286-290`, `src/film_pipeline/validation/thresholds.py:37-40`, field at `src/film_pipeline/schemas/validation.py:45` | **duplicated + unread — F-VR-11** |
| Validator-driven repair routing (`revise`, rule 6) | `src/film_pipeline/graph/_action_routing.py:273-301` | **present but unreachable — F-VR-02, F-VR-05** |
| Artifact typing for consensus/QC outputs | `src/film_pipeline/graph/nodes/qc.py:88,109` (literal `"consensus_report"`), `src/film_pipeline/graph/nodes/_agent_artifacts.py:35-39` (coercion), `src/film_pipeline/graph/nodes/_context.py:310` (class map), `src/film_pipeline/schemas/_base.py:27-75` (enum without the member) | **silently coerced — F-VR-12** |
| QC boundary ref keys (`consensus_report_ref`, `qc_patch_ref`) | `src/film_pipeline/graph/nodes/qc.py:29-30,42,61-64` (private tuple) vs `src/film_pipeline/graph/orchestrator_state.py:93-165` (no row) | **unregistered policy — F-VR-13** |
| Saved-validation refs | `src/film_pipeline/mcp/tools/validation.py:275` (`validation_refs`) vs `src/film_pipeline/graph/state_schema.py:173` + `src/film_pipeline/graph/orchestrator_state.py:163` (`validation_report_refs`, no writer) | **split authority — F-VR-14** |
| Which phases the registered MCP validation tool can run | `src/film_pipeline/mcp/tools/validation.py:297-306` (two branches) vs `:138-157` (six declared arms) | **disagree — F-VR-15** |

### 4.2 Clean concerns (single-owner at HEAD, with the guard test that pins them)

| # | Concern | Single owner | Guard test / proof |
|---|---|---|---|
| C1 | Score→status **function** | `src/film_pipeline/validation/thresholds.py:9-29` — one definition; `grep -rn "def score_to_status" → 1`; `src/film_pipeline/graph/router.py:22-36` re-exports rather than re-implements | `tests/unit/validation/test_thresholds.py:14-36` pins all four statuses for default and custom thresholds |
| C2 | `ValidationStatus` / `IssueSeverity` enums | `src/film_pipeline/schemas/_base.py:122-129` and `:192-197`; every other module imports them (`grep` for local redefinitions → none) | `tests/unit/test_schemas.py:471,507,532-542,1002` round-trips the values through report/consensus schemas |
| C3 | `ValidationReport` / `ConsensusReport` shapes | `src/film_pipeline/schemas/validation.py:32-67`; the MCP projection adds no fields (`src/film_pipeline/mcp/tools/helpers.py:214-223`) | `tests/unit/validation/test_consensus.py` (16 tests) + `tests/unit/validation/test_base.py` (13 tests) build and assert these models |
| C4 | Artifact diff + review-package assembly (MCP path) | `src/film_pipeline/review/diff.py:27-58` (+ `src/film_pipeline/review/generator.py:83-92`) and `src/film_pipeline/review/generator.py:38-80`; `compute_artifact_diff` has one definition | `tests/unit/review/test_diff.py` (11 tests) and `tests/unit/review/test_generator.py` (10 tests) |
| C5 | Artifact-scope validator *scoring* rules | each `impl/*` owns its own `extract_score` (e.g. `src/film_pipeline/validation/impl/dialogue_voice.py:215-236`); no scoring logic is duplicated across validators | `tests/unit/validation/test_impl_validators.py` asserts per-validator scores/thresholds behaviour |
| C6 | Gate-flag writer (`approved` / `human_approval_required` / `human_approval_phase`) | `src/film_pipeline/graph/nodes/_shared.py:147-159` (`_phase_gate_updates`), called by every phase node | `tests/unit/graph/test_real_human_gates.py:195+` asserts the real `interrupt` fires with gates ON |
| C7 | Failure-class/gate escalation for provider/budget/failure states | `src/film_pipeline/graph/_action_routing.py:173-251` (rules 2-4) with state predicates in `src/film_pipeline/graph/orchestrator_state.py` (`has_blocking_failure`, `is_budget_blocked`) | `tests/integration/test_dynamic_routing.py:138-165` |

The numeric cells above (C3, C4) are produced by:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest \
  tests/unit/validation/test_consensus.py tests/unit/validation/test_base.py \
  tests/unit/review/test_diff.py tests/unit/review/test_generator.py \
  --collect-only -q --no-cov
# → test_consensus.py: 16 | test_base.py: 13 | test_diff.py: 11 | test_generator.py: 10
```

`--no-cov` is required: `pyproject.toml` `addopts` carries `--cov-fail-under=90`, so a subset run
without it exits 1 on the coverage gate rather than on the counts being demonstrated. The remaining
rows cite line ranges, not counts.

### 4.3 Candidate module boundary — **validation/review owner**

**Module name:** `film_pipeline.validation` (absorbing `review/` as a submodule for the
human-gate package, or keeping `review/` with `validation` owning the gate policy it depends on).

**One-sentence responsibility:** decides whether an artifact or phase satisfies its contract —
running validators, mapping scores and finding codes to the four-status contract, synthesizing
consensus, and computing the human gate's available actions — and is the only writer of the
resulting `ValidationReport`, `ConsensusReport`, and `ReviewPackage` representations.

**Explicit non-goals:** does not decide phase order or phase advancement
(`src/film_pipeline/graph/_action_routing.py:18-30`, `src/film_pipeline/graph/edges.py:40-54`); does not persist artifacts
(`artifacts/`); does not dispatch generation, budget, or provider-health policy
(`src/film_pipeline/graph/_action_routing.py:173-251`); does not own agent routing or prompts (`agents/`).

**Declared public contract（target）:** three of the modules named in this section are targets, not
files at HEAD — `src/film_pipeline/validation/registry.py` exists, while
`src/film_pipeline/validation/dispatch.py` (F-VR-07, F-VR-15),
`src/film_pipeline/validation/gate_policy.py` (F-VR-06), and
`src/film_pipeline/validation/runtime.py` (F-VR-03) are where those findings propose the code should
live.

- `ValidatorRegistry` (one class, from `src/film_pipeline/validation/registry.py`) — `register`, `lookup_by_id`,
  `lookup_by_scope`, `lookup_by_modality`, `enabled_only`, populated once at services build
  (`src/film_pipeline/graph/services.py:65`) from the single entry table.
- `ValidatorThresholds` with an enforced band invariant (`pass_at > review_at >= block_below`,
  and `block_below < review_at` for `NEEDS_REVISION` to exist).
- `score_to_status(score, thresholds) -> ValidationStatus` (`src/film_pipeline/validation/thresholds.py:9`),
  `severity_for_code(entry, code) -> IssueSeverity`.
- `BaseValidator.run(...) -> ValidationReport` — the only producer of `ValidationReport`.
- `ConsensusBuilder.build(list[ValidationReport], refs) -> ConsensusReport` — the only producer of
  `ConsensusReport`; `QCSynthesisAgent` contributes a narrative input, not a second writer.
- `dispatch.PHASE_VALIDATORS: dict[FilmPhase, tuple[type[BaseValidator], ...]]` and
  `VALIDATOR_ARTIFACTS` — the only phase→validator table.
- `gate.available_gate_actions(issues) -> AvailableActions` and
  `ReviewPackageGenerator.build(...) -> ReviewPackage` — the only human-gate representation.

**State owned:** `_validation_reports`, `consensus_report` + `consensus_report_ref`,
`validation_refs`/`validation_report_refs` (one name, chosen here — kills F-VR-14);
`ValidationReport.status/requires_human_review`;
`ReviewPackage.available_actions/blocked_actions`. All other modules read these through the
contract. Boundary keys owned elsewhere but *consumed* here: `consensus_report_ref`, `qc_patch_ref`
(must become `ORCH_CHANNELS` rows — F-VR-13).

**Invariants (each with a guard test):**

1. Registry agreement: every impl class is registered exactly once; every registry entry maps to an
   implemented class or is explicitly marked unimplemented (kills F-VR-01).
2. Status reachability: for every registry entry there exists a score producing each of the four
   statuses; `block_below < review_at` (kills F-VR-02).
3. Single representation writer: `ConsensusBuilder` input is typed; `consensus_report` has exactly
   one writer and one channel row (kills F-VR-04, F-VR-05).
4. Dispatch agreement: subgraph, sequential runner, and MCP specs produce identical validator sets
   per phase (kills F-VR-07), **and** the registered MCP tool can reach every phase its table
   declares (kills F-VR-15).
5. Gate-policy agreement: payload allowed-actions, router eligibility, `approve_phase_node`
   guard, and `ReviewPackage.available_actions` agree for the same state (kills F-VR-06, F-VR-09).
6. Condition-list coherence: emitted blocking codes equal `entry.blocking_conditions` (kills F-VR-08).
7. Gate vocabulary: every `ApprovalAction` has a handler and produces a typed record (kills F-VR-10).
8. Artifact typing: every saved artifact's `artifact_type` is an `ArtifactType` member, and the
   payload-class → enum map is total (kills F-VR-12).
9. Boundary-key registration: every ref key a node copies has an `ORCH_CHANNELS` row and is inside
   the writer-sweep scope (kills F-VR-13).

**Allowed dependencies:** `schemas`, `artifacts` (read/write reports only), `providers`/`agents`
(LLM calls through injected services). **Forbidden:** `graph`, `mcp`, `app` must consume the
registry/policy, not re-declare it; `validation` must not import `graph` (today it does not).

**Extraction order (each step keeps `make ci-check` green):**
(1) collapse the 22 entry literals into one table + inject entries into `BaseValidator` (F-VR-01,
F-VR-08); (2) enforce and test the status band (F-VR-02); (3) type the `ConsensusBuilder` seam and
collapse to one consensus writer (F-VR-04, F-VR-05); (4) extract one validator core + one dispatch
table and re-point subgraph/sequential/MCP (F-VR-03, F-VR-07, F-VR-15); (5) add the
`consensus_report`/`matrix_patch` artifact types and make the save path total (F-VR-12); (6) register
`consensus_report_ref`/`qc_patch_ref` and widen the channel sweep to plain `GraphState` fields
(F-VR-13); (7) collapse `validation_refs`/`validation_report_refs` to one name (F-VR-14);
(8) extract `gate.available_gate_actions` and make the interrupt payload a `ReviewPackage` (F-VR-06,
F-VR-09, F-VR-10, F-VR-11). Steps 5-7 are independent of 1-4 and can land first, since each is a
small, locally verifiable change with an existing guard-test home.

---

## 5. Unverified hypotheses and open gaps

Explicitly **not** findings (§1.6.6):

- **H1.** The nine implemented-in-registry-only validators (`logline-validator` … `full-movie-flow-validator`)
  may be intended future work rather than debt; no doc at HEAD states the intent.
  Verified only that no implementation exists (`grep -rln "validation.impl" src` → 5 files, none
  containing those ids).
- **H2.** The prompts/templates for validator LLM calls (`src/film_pipeline/agents/prompt_templates/defaults/production.py:248`,
  `src/film_pipeline/graph/nodes/_context.py:40` `"clip-validator": "strict_validator"`) are out of this cluster; whether
  every validator id has a prompt template is unverified here.
- **H3.** `src/film_pipeline/graph/_action_routing.py:348-361`'s documented priority order lists rule 6 as "Pending
  revision" and rule 7 as "Not approved", while the code runs validation-status (6) before
  pending-revision (7) and uses "Not approved → present review package" (8). The docstring is stale
  relative to `compute_actions`' body; classified as documentation drift, not ownership debt.
- **H4.** `__pycache__` artifacts under `tests/` were excluded from all `grep -rln` counts above
  (`--include=*.py` with the `*.pyc` paths filtered where they appeared).

**Verification follow-up (no open gaps left):** every dispute in `docs/modular-architecture/reviews/verify-08.md` is resolved in
place, and its five missed seams are accounted for — M1 → F-VR-13, M2 → F-VR-14, M3 → F-VR-12 (with
the verifier's "renderer can never fire" consequence falsified and replaced by the metadata-coercion
defect), M4 → F-VR-15, M5 → the `tests/unit/graph/test_qc_validator_dispatch.py` row in §1.1 plus the
qualifications on F-VR-03 and F-VR-07. One item is deliberately *not* promoted to a finding: the
`src/film_pipeline/validation/consensus.py:92-93,98` pass-throughs remain described as gated pass-throughs (F-VR-02), not
independent producers, because no validator can emit their input status.

Audited and reported at commit `fb85baa0e6b769b709791a96a89980089304bf13`, branch `modular-app`.
