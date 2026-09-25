# Module decomposition analysis

Date: 2026-09-26. Revision: `e207714`. Method: measured LOC, file counts,
internal import edges, and concentration of symbols. No file in `src/` was
modified to produce this document.

This answers a specific question: **which modules are too big, and which of them
should actually be broken up?** Size alone is not the criterion — a large module
whose parts are independent is cheap to live with, while a smaller module that
concentrates many concerns is expensive. Every recommendation below is tied to a
measurement.

## 1. Measured sizes

| Module | LOC | Files | Verdict |
|---|---:|---:|---|
| `mcp` | 7,288 | 46 | Large but already decomposed into `tools/<domain>/` |
| `orchestration` | 6,033 | 29 | Large and **cohesive** — see §3 |
| `agents` | 4,735 | 36 | Large; one real seam in `model_adapter` — see §4 |
| `generation` | 2,879 | 18 | Fine |
| `studio` | 2,838 | 17 | Small file count, **but one god object** — see §2 |
| `schemas` | 2,811 | 40 | Large file count, **zero internal coupling** — see §5 |
| `validation` | 2,549 | 14 | Fine |
| `storage` | 2,548 | 14 | One oversized file (`store.py`, 832) |
| `operations` | 1,861 | 9 | Fine |
| `governance` | 1,698 | 14 | Fine |

Largest single files: `storage/store.py` (832), `orchestration/nodes/visual.py`
(637), `operations/operator.py` (582), `orchestration/orchestrator_state.py`
(551).

## 2. The real finding: `StudioRuntime` is the concentration

`studio/runtime.py` is not the largest file, but `StudioRuntime` is **370 lines,
39 methods, and 12 fields** spanning five unrelated concerns. Enola's `god-class`
explainer independently reports it as the most-depended-on symbol family in the
repository:

| Symbol | Dependents |
|---|---:|
| `StudioRuntime.create_project` | 106 |
| `StudioRuntime.set_active` | 98 |
| `get_runtime` | 95 |
| `StudioRuntime.get_active` | 80 |
| `StudioRuntime._run_phase_node` | 33 |
| `StudioRuntime._persist_project_state` | (private, reached by name) |

Clustering its own methods by the state they touch gives five groups:

| Concern | Methods | Examples |
|---|---:|---|
| Project lifecycle | 14 | `create_project`, `get_project`, `delete_project`, `set_active`, `get_active`, `add_operator_comment` |
| Checkpoints + audit | 9 | `create_checkpoint`, `list_checkpoints`, `_auto_checkpoint`, `get_audit_log` |
| Graph execution | 6 | `ensure_graph`, `run_graph`, `approve_phase`, `run_validation`, `request_revision` |
| Providers | 10 | `register_provider`, `get_provider_health`, `seed_default_provider_adapters` |

This is the same measurement `03` §3.8 recorded as F-RUNTIME-01 ("`StudioRuntime`
is 3 responsibilities, 15 fields"). The migration left it intact because moving
it is behaviour-adjacent, not because it is fine.

**Recommendation.** Decompose by *delegation*, not by moving code out of the
class: `StudioRuntime` becomes a thin facade holding the five collaborators
(`ProjectStore`, `CheckpointService`, `AuditLog`, `GraphRunner`,
`ProviderRegistry`), each owning its own state. This preserves all 106 dependents
and the `get_runtime()` seam, which is why it is safer than the file-move rounds.
`operations.ports.RuntimePort` already declares the narrowed surface, so the port
is the specification for the facade.

## 3. `orchestration` should NOT be split

The node files look separable by phase, but the coupling says otherwise. Of 43
node-to-node edges, the dominant pattern is shared infrastructure, not pairwise
dependency:

- `_shared`, `_agent`, and `_context` are imported by most phase nodes.
- `_repair_loop` imports **six of the seven** node modules (`generation`, `prep`,
  `qc`, `visual`, `wrapup`, `approval`) plus the shared `_agent` — it is the
  repair cycle that spans phases.
- No cluster is internally dense and externally sparse.

Splitting by phase would produce subpackages that each import the shared trio and
that `_repair_loop` must reach across anyway. That is churn without a boundary.

**Recommendation.** Leave `orchestration` as one module. If anything is worth
extracting, it is `orchestrator_state.py` (551 lines, 97% public surface, 39
public symbols) — but that is a *surface* problem, not a size problem: the fix is
to narrow what it exports, not to split the file.

## 4. `agents`: one genuine seam

`agents/model_adapter.py` is 382 lines. `ModelAdapter` alone is 264 lines and
carries six provider-specific methods across three transports:

- `_gemini_api_key`, `_call_gemini_api`, `_gemini_url`
- `_zai_api_key`, `_zai_base_url`, `_zai_request`
- plus the generic `_request` / `_chat_completions_payload` path

`03` §3.10 already records the intended fix: "`model_adapter.py:36` drops the
concrete-adapter import". The seam is real and the target architecture names it.

**Recommendation.** Extract per-provider transports into
`agents/transports/{gemini,zai,chat_completions}.py` behind the existing
`_ChatRequest` / `_GeminiRequest` value objects, leaving `ModelAdapter` as
dispatch. This is a contained change with a clear interface, and it is the
highest-confidence split in this document.

`agents/runner.py` (471) is large but cohesive: one class with a retry ladder
(`_attempt_normal_call` → `_attempt_structured_retry` → `_all_retries_exhausted` →
`_attempt_fallback_model`). Splitting the ladder would obscure it.

## 5. `schemas` should NOT be split

`schemas` has 40 files and 2,811 LOC, which looks like a candidate. The coupling
measurement says it is not:

- 69 internal import edges (37 to `base`, 32 elsewhere).
- Of those 32 "elsewhere" edges, **30 originate in `__init__.py`** — they are the
  facade re-exporting its own modules, not modules depending on each other.
- Excluding the facade, there are exactly **two** real cross-file edges:
  `reference -> validation` and `constraints -> project`.
- Total external dependencies: 102 stdlib/external, 9 `filmspec`. It is a leaf.

It is a flat namespace of independent record definitions. Grouping it into
subpackages (`schemas/script/`, `schemas/visual/`, …) would add a directory level
and change every import path in the repository while removing no coupling,
because there is almost no coupling to remove. The one real defect — the
97%-public `base.py` surface with 99 dependents — is a surface question, not a
size one.

**Recommendation.** Leave the layout alone. If `schemas/base.py` needs work,
narrow its public surface rather than relocating its files.

> **Correction.** A first draft of this section claimed "62 of 69 edges go to
> `base`". That was wrong — it was an inference from the most-common list rather
> than a count. The measured split is 37 to `base` and 32 elsewhere, and
> resolving the elsewhere group changed the conclusion from "weakly coupled" to
> "almost entirely uncoupled", which strengthens the recommendation rather than
> weakening it. The false number is recorded here because the mistake is exactly
> the kind this document exists to prevent.

## 6. Ranked recommendations

Ordered by value per unit of risk, which is what the migration has consistently
optimised for:

1. **`StudioRuntime` delegation split** (§2). Highest measured concentration —
   106/98/95/80 dependents on individual methods. Behaviour-preserving by
   construction if the facade keeps its signatures. Highest value, medium risk.
2. **`agents/model_adapter` transport split** (§4). Real seam, already named in
   the target architecture, contained interface. Medium value, low risk.
3. **`storage/store.py`** (832 lines). Largest file. Not yet analysed in depth
   here; a candidate for a follow-up measurement before any split.
4. **Narrow `orchestrator_state`'s 97% public surface** (§3) and
   **`schemas/base.py`'s** (§5). Surface reductions, no file moves.
5. **Do not split** `schemas` (§5) or `orchestration` (§3).

## 7. What this analysis does not establish

- `mcp` (7,288 LOC, the largest module) is not analysed in depth here. It already
  decomposes into `tools/<domain>/`, so its size is breadth rather than
  concentration, but that is an impression from the file listing, not a
  measurement of its internal coupling.
- `storage/store.py`'s 832 lines were counted, not read for seams.
- The method clustering in §2 is a heuristic over field references, not a
  dependency analysis; the four groups are indicative, and a decomposition plan
  should re-derive them.
- No attempt was made to estimate effort for any recommendation.
