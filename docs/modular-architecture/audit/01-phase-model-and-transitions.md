# Audit 01 — Phase model and transitions

Audited at `modular-app` = `fb85baa` (`git rev-parse --short HEAD`), clean tree.
Method: full reads of every file in the cluster brief, plus targeted greps for
every literal phase-name occurrence and every phase-keyed constant. All counts
and comparisons below are reproducible with the commands shown; every anchor was
read at this commit. Per §1.6, claims that could not be mechanically verified are
in the final "Unverified" section, not among the findings.

Cluster question answered up front: **`graph/_action_routing.py::PHASE_ORDER` and
`artifacts/paths.py::PHASE_DIR_MAP` share one vocabulary, not two.** Their keys
are byte-identical at HEAD, and both equal `schemas/_base.py::FilmPhase` and the
remaining full literals. The defect is not present divergence but **eleven
independent phase-vocabulary definitions spread across eight modules with no
agreement test** (nine carry the full 11-name set; `_APPROVAL_DESTINATIONS` is
10-of-11 and `_PHASE_DEFAULT_AGENTS` 9-of-11) — plus one *behavioural* divergence
in phase advancement (F-PHASE-01), which is proven.

> **Verification record (round 1).** Independently verified by
> `docs/modular-architecture/reviews/verify-01.md` (209 lines): all ten findings
> CONFIRMED or DOWNGRADED in scope (F-PHASE-10 only), none REJECTED, none with a
> severity change forced; F-PHASE-01 impact recomputed to 4 × drift 4 = 16
> (Critical, score survives); F-PHASE-10 DOWNGRADED to Medium 2 × 3 = 6 (two
> phase-keyed validator tables, not three; prior art found). Final set after this
> fix pass: **11 findings — 2 Critical, 5 High, 4 Medium** (F-PHASE-11 added
> from M3). Every dispute (D1–D10) and
> missed-in-scope item (M1–M3) has been re-verified against HEAD and corrected in
> this file: D1 count (9 full + 1 10-of-11 + 1 9-of-11), D2 sweep count (129
> entries / 16 files; any-position 359), D3 `latest_artifact_phase` mutation
> outcome (returns an *earlier* phase), D4 (the action literal *is* test-pinned;
> only the destination is unguarded), D5 (validator-registry scope +
> `_VALIDATOR_ARTIFACTS` + prior art), D6 (prior-art *content* corrected — **one
> partial disagreement** with the verifier on the line number, recorded in the
> Unverified section), D7 (transition invariant moved to `graph`, not `schemas`),
> D8 (no provider spend on generation entry), D9 (F-PHASE-09 scope narrowed to
> the vocabulary leak), D10 (gate-mode asymmetry direction), M1
> (`_APPROVAL_DESTINATIONS` restates `_PHASE_TO_NODE`), M2
> (`_UPSTREAM_CONTENT_SOURCES`), M3 (KB `applies_to_phases`, now F-PHASE-11).

```bash
.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "src")
from film_pipeline.graph._action_routing import PHASE_ORDER, APPROVAL_GATES
from film_pipeline.artifacts.paths import PHASE_DIR_MAP
from film_pipeline.schemas._base import FilmPhase
from film_pipeline.graph.graph import _PHASE_TO_NODE, _APPROVAL_DESTINATIONS
from film_pipeline.graph.nodes._repair_loop import _PHASE_NODES
from film_pipeline.graph.edges import _NEXT_PHASE_AFTER_APPROVAL
from film_pipeline.constraints._keywords import _PHASE_KEYWORDS
print(PHASE_ORDER == list(PHASE_DIR_MAP) == [p.value for p in FilmPhase]
      == list(_PHASE_KEYWORDS) == list(_PHASE_TO_NODE) == list(_PHASE_NODES))
print(list(APPROVAL_GATES) == PHASE_ORDER)
print(all(_NEXT_PHASE_AFTER_APPROVAL[p] == PHASE_ORDER[i+1]
          for i, p in enumerate(PHASE_ORDER[:-1])))
print(all(_APPROVAL_DESTINATIONS[k] == _PHASE_TO_NODE[k]
          for k in _PHASE_TO_NODE if k in _APPROVAL_DESTINATIONS))  # M1 restatement
import pathlib, re
_gate_literals = {m.group(1) for f in pathlib.Path("src/film_pipeline").rglob("*.py")
                  for m in re.finditer(r'gate="([a-z_]+)"', f.read_text())}
print(_gate_literals == set(APPROVAL_GATES.values()))  # F-PHASE-03: node gate= literals
PY
# -> True / True / True / True / True
```

---

## Coverage

| Scope file | Verdict |
|---|---|
| `graph/_action_routing.py` | audited — defines `PHASE_ORDER`, `APPROVAL_GATES`, the phase-class partition, and the phase-advance rule (F-PHASE-01/02/03/06) |
| `graph/router.py` | audited — pure re-export façade; defines no phase data (`:20-40`) |
| `graph/edges.py` | audited — defines a second successor table `_NEXT_PHASE_AFTER_APPROVAL` (F-PHASE-04) and the action→node transition table (F-PHASE-06) |
| `graph/graph.py` | audited — defines `_PHASE_TO_NODE`; `_APPROVAL_DESTINATIONS` (`:85-99`) is a hand-copied restatement of it for 10 phases (M1); `_route_current_phase` re-derives node names from `PHASE_ORDER` (F-PHASE-02/03) |
| `graph/nodes/approval.py` | audited — gate control plane; re-exports `_PHASE_NODES` (`:21`), defines no phase vocabulary of its own |
| `graph/nodes/_repair_loop.py` | audited — defines `_PHASE_NODES`, the repair phase→callable registry (F-PHASE-02) |
| `graph/nodes/_shared.py` | audited — owns `_phase_gate_updates` (`:147`) and the second gate-mode reader `_require_human_approval` (`:132`); `_CRITICAL_CONTEXT` is a phase-keyed literal (F-PHASE-07/09) |
| `graph/nodes/wrapup.py` | audited — `post`/`delivery` gate literals at `:21`,`:44` (F-PHASE-03) |
| `graph/nodes/prep.py` | audited — `intake`/`constitution`/`development`/`script` gate literals at `:108`,`:191`,`:223`,`:272` (F-PHASE-03) |
| `graph/subgraphs/qc.py` | audited — `reduce_qc_reports` re-implements the gate-parking update inline (`:263-271`); its `_VALIDATOR_MAP` (`:45-52`) / `_WORKER_NODES` (`:210-217`) / `_VALIDATOR_ARTIFACTS` (`:154-160`) are **validator-id** and node-name registries, not phase-keyed (F-PHASE-03/10) |
| `graph/subgraphs/__init__.py` | audited — docstring only, no phase data |
| `artifacts/paths.py` | audited — `PHASE_DIR_MAP` name→directory map + implicit phase order (F-PHASE-02/05) |
| `artifacts/store.py` (phase use) | audited — `:78`,`:357`,`:495` path keying and `:501` ordering derived from `PHASE_DIR_MAP` (F-PHASE-05) |
| `artifacts/project_storage.py` (grepped beyond scope) | audited — `latest_artifact_phase` uses `reversed(PHASE_DIR_MAP.items())` as pipeline order (`:136`) and feeds `current_phase` (F-PHASE-05) |
| `app/_graph_exec.py` | audited — second phase-advance implementation (`:425-445`), reachable from MCP `approve_phase` (F-PHASE-01) |
| `app/_resume.py` | audited — resume progress check compares `PHASE_ORDER` indices (`:31-33`); consumer only, no new definition |
| `app/services/_project_discovery.py` | audited — writes `current_phase` from `latest_artifact_phase`, i.e. from `PHASE_DIR_MAP` order (`:35`,`:54`) (F-PHASE-05) |
| `app/services/models.py` | audited — **irrelevant to this cluster**: `current_phase: str` is a raw DTO field (`:36`,`:52`,`:162`); no phase vocabulary, order, map, or gate |
| `mcp/contract.py` | audited — **irrelevant to this cluster**: `ToolGroup.INTAKE`/`.GENERATION` (`:29`,`:34`) are tool-group labels that reuse the words, not pipeline phases |
| `mcp/tools/*.py` | audited — `review.py` is a `human_gate` consumer (`:115`); `intake.py` has a local phase guard (`:73`); `planning.py` has a phase→budget literal (`:37-40`); `validation.py` has the second genuinely phase-keyed validator table `_live_validator_specs` (`:123-158`, `phases=("post","assembly")` at `:149`) (F-PHASE-06/09/10) |
| `post/*.py` | audited — **clean consumers**: `src/film_pipeline/post/assembly_agent.py:125`, `src/film_pipeline/post/subtitle_agent.py:101`, `src/film_pipeline/post/delivery_packaging_agent.py:170` all construct `FilmPhase("post")`/`FilmPhase("delivery")`; no local phase vocabulary |
| `agents/impl/*.py` | audited — **irrelevant to this cluster**: every phase-word match is an artifact id or a model-output JSON key (`src/film_pipeline/agents/impl/intake_agent.py:35` `model_output.get("intake", …)`, `src/film_pipeline/agents/impl/development_agent.py:76`), not phase vocabulary |
| `checkpoints/rollback.py` | audited — regeneration-phase tuple `("generation", "qc", "post")` at `:68` (F-PHASE-09) |
| `constraints/_keywords.py` | audited — `_PHASE_KEYWORDS` is a fourth full ordered copy (`:153-165`), consumed by `src/film_pipeline/constraints/extractor.py:328` (F-PHASE-02/09) |
| `schemas/_base.py` | audited — `FilmPhase` at `:77-90` is the only canonical *type*; every other site uses raw strings (F-PHASE-02) |
| `graph/_agent_routing.py` (grepped beyond scope) | audited — `_PHASE_DEFAULT_AGENTS` covers 9 of 11 phases (`:35-47`) (F-PHASE-08) |
| `graph/context_packets.py` (grepped beyond scope) | audited — `PHASE_BUILDERS` covers 7 of 11 phases (`:128-136`) (F-PHASE-08) |
| `graph/nodes/qc.py` (grepped beyond scope) | audited — `_VALIDATOR_RUNNERS` phase-membership sets incl. the non-phase `"assembly"` (`:361-368`) (F-PHASE-10) |
| `graph/nodes/_context.py` (added after verification, M2) | audited — `_UPSTREAM_CONTENT_SOURCES` (`:329-338`) holds 8 phase names as tuple **values**, invisible to the line-initial sweep (F-PHASE-02) |
| `kb/manifest.py`, `schemas/kb.py`, `film-knowledge-base/index/kb-manifest.yaml` (added after verification, M3) | audited — `applies_to_phases: list[str]` (`schemas/kb.py:25`) is filtered by raw string (`kb/manifest.py:44`) against manifest data carrying phase lists; nothing validates the tokens (F-PHASE-11) |
| `tests/unit/graph/test_qc_validator_dispatch.py` (guard test) | audited — guards `_VALIDATOR_RUNNERS` membership only; no cross-registry or phase-token validation (F-PHASE-10/11) |
| `tests/unit/kb/test_manifest.py` (guard test) | audited — `test_by_phase_all_match` (`:48-55`) asserts `len(items) >= 8`; a typo'd phase token still passes (F-PHASE-11) |
| `graph/nodes/generation.py`, `visual.py` (grepped beyond scope) | audited — gate literals `generation_batch`/`visual_bible`/`shot_bible`/`generation_spend` (F-PHASE-03); `generation_node` plans a ledger and parks at the gate, it does not dispatch providers (F-PHASE-01 impact) |
| `cli/driver.py` (grepped beyond scope) | audited — `PHASE_ORDER` consumer for `--target-phase` (`:139-214`); no new definition |
| `app/mock_responses.py` (grepped beyond scope) | audited — phase words are mock-payload keys nested under agent ids (`:101`,`:119`,`:218`,`:312`); a fixture, not a phase model |
| `profiles/base.studio.yaml` (grepped beyond scope) | audited — a 12th full ordered phase list at `:4-15`; unread by any code (recorded as a deliberate deferral in `documentation/reviews/hardcoded-values-inventory.md:62`) |
| `scripts/*.py` (grepped beyond scope) | audited — `scripts/e2e-real-auto-approve.py:113` and `scripts/test-full-pipeline-direct.py:59` hard-code partial phase lists; out of the src ownership map but corroborate the vocabulary leak |
| `artifacts/registry.py`, `checkpoints/invalidation.py` (grep false positives) | audited — **irrelevant**: matches are artifact-type keys (`"script"`, `"shot_bible"`), not phases |

Reproduce the scope-wide literal sweeps (D2/M2):

```bash
# line-initial phase-name entries (what this audit's inventory counts):
grep -rcE '^\s*"(intake|constitution|development|script|visual_dev|shot_bible|gen_planning|generation|qc|post|delivery)"' \
  -r src/film_pipeline --include='*.py' | awk -F: '{s+=$2; if($2>0) f++} END {print "entries="s" files="f}'
# -> entries=129 files=16

# every phase-name string anywhere in src/ (a lower bound on the vocabulary leak; M2):
grep -roE '"(intake|constitution|development|script|visual_dev|shot_bible|gen_planning|generation|qc|post|delivery)"' \
  -r src/film_pipeline --include='*.py' | wc -l
# -> 359
```

---

## Phase-vocabulary inventory (measured)

Eleven independent phase-vocabulary definitions live in **eight** modules (D1):
**9** carry the full 11-name set, `_APPROVAL_DESTINATIONS` is 10-of-11 (omits
`intake`), and `_PHASE_DEFAULT_AGENTS` is 9-of-11. `+` marks a derived view
(computed from another table), not an independent copy. This set is a **lower
bound** on the leak: phase names also appear as non-line-initial literals
(`_UPSTREAM_CONTENT_SOURCES`, KB applicability, `_CRITICAL_CONTEXT`, …), and the
mechanically measured sweep finds **129 line-initial entries across 16 files**
(D2).

| # | Definition | Site | Phase keys | Independent? |
|---|---|---|---|---|
| 1 | `FilmPhase` StrEnum | `schemas/_base.py:77` | 11 | yes |
| 2 | `PHASE_ORDER` list | `graph/_action_routing.py:18` | 11 | yes |
| 3 | `_PHASE_AGNOSTIC_PHASES` + `_GENERATION_DEPENDENT_PHASES` | `src/film_pipeline/graph/_action_routing.py:33`,`:47` | 10 + 1 = 11 | yes |
| 4 | `APPROVAL_GATES` keys | `src/film_pipeline/graph/_action_routing.py:49` | 11 | yes (values: gates) |
| 5 | `_PHASE_TO_NODE` | `graph/graph.py:55` | 11 | yes |
| 6 | `_APPROVAL_DESTINATIONS` | `graph/graph.py:85` | **10** (+`end`/`repair`/`await_approval`; restates #5, M1) | yes |
| 7 | `_PHASE_NODES` | `graph/nodes/_repair_loop.py:38` | 11 | yes |
| 8 | `_NEXT_PHASE_AFTER_APPROVAL` | `graph/edges.py:40` | 11 | yes |
| 9 | `PHASE_DIR_MAP` keys | `artifacts/paths.py:14` | 11 | yes |
| 10 | `_PHASE_KEYWORDS` | `constraints/_keywords.py:153` | 11 | yes |
| 11 | `_PHASE_DEFAULT_AGENTS` | `graph/_agent_routing.py:35` | **9** | yes |
| — | `PHASE_BUILDERS` | `graph/context_packets.py:128` | 7 | yes (partial index) |
| — | `_VALIDATOR_RUNNERS` phase sets | `graph/nodes/qc.py:361` | 6 sets | yes (partial) |
| — | `_PhaseSpec.phases` (`_live_validator_specs`) | `mcp/tools/validation.py:123-158` | 6 rows | yes (partial) |
| — | per-phase budget `per_phase_caps_usd` | `mcp/tools/planning.py:37` | 3 | yes (partial) |
| — | `_CRITICAL_CONTEXT` | `graph/nodes/_shared.py:85` | 2 | yes (partial) |
| — | `_UPSTREAM_CONTENT_SOURCES` (M2) | `graph/nodes/_context.py:329` | 8 entries (5 distinct phases) | yes (partial) |
| — | `applies_to_phases` (free-string KB registry, M3 → F-PHASE-11) | `schemas/kb.py:25`, `kb/manifest.py:44`, `film-knowledge-base/index/kb-manifest.yaml` | 5 phases + `all` | yes (partial) |
| — | `phases:` profile list | `profiles/base.studio.yaml:4` | 11 | yes (unread) |
| + | `_AFTER_PHASE_DESTINATIONS` | `graph/graph.py:70` | 11 | derived (`**_PHASE_TO_NODE`) |
| + | `_ROUTER_DESTINATIONS` | `graph/graph.py:79` | 11 | derived |
| + | node-name f-string | `graph/graph.py:197` | — | derived from `PHASE_ORDER` |

---

## Findings

### F-PHASE-01 — Phase advancement has two implementations, and the app path skips the provider-blocked-generation gate
- **Class:** O6 (parallel lifecycle)
- **Severity:** Critical (impact 4 × drift 4 = 16). Impact is 4, not 5: `generation_node` does not itself call a provider — it plans a batch ledger and parks at the `generation_batch` gate — so the bypass spends a state entry and writes a plan before the gate rather than buying a render immediately. The safety invariant is still defeated (the provider-block refusal is skipped), so it stays Critical.
- **Concern:** the rule that decides which phase runs next after approval.
- **De-facto owners:**
  - `src/film_pipeline/graph/_action_routing.py:325` — the graph rule: next = successor in `PHASE_ORDER`, but refuse to enter generation while providers are blocked — `"if next_phase == \"generation\" and blocked_providers:"` … `"result.next_action = \"continue_unrelated_work\""` (`:337-339`)
  - `src/film_pipeline/app/_graph_exec.py:425` — the app rule: next = successor in `PHASE_ORDER` with no provider check — `"next_phase = PHASE_ORDER[current_index + 1]"` (`:441`) then `"advanced_state = run_phase_node(rt, state, next_phase)"` (`:442`)
  - `src/film_pipeline/app/_graph_exec.py:210` and `:240` — the two call sites that reach the app rule (no-checkpoint fallback, and stalled-resume fallback), both under `approve_phase` (`:286`)
- **Drift proof (existing divergence, executed):** with `current_phase="gen_planning"`, `approved=True`, and provider `seedance` blocked, the graph rule returns `continue_unrelated_work` while the app rule enters `generation`. Reproduced output:
  ```
  GRAPH continue_unrelated_work
  APP generation
  ```
  The two tests on this path, `tests/unit/app/test_resume_integrity.py:91-100` and `:224` (`test_stalled_resume_advances_and_audits`), assert `project_id`/`invoke_calls == 0` and that the stalled resume advances; neither inspects the target phase or provider health.
- **Reproduce:**
```bash
.venv/bin/python - <<'PY'
import sys, tempfile, pathlib; sys.path.insert(0, "src")
from film_pipeline.app import _graph_exec
from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.graph.router import compute_actions
from film_pipeline.graph import orchestrator_state as ostate
class S:
    def __init__(s, v): s.values=v; s.next=(); s.tasks=()
class G:
    def __init__(s): s.snapshot=S({})
    def get_state(s, c): return s.snapshot
    def invoke(s, c, cfg): raise AssertionError
st={"project_id":"p1","current_phase":"gen_planning","approved":True,"human_approval_required":False}
ostate.ensure_orchestrator_state(st); ostate.update_provider_health(st,"seedance",{"status":"blocked_quota"})
print("GRAPH", compute_actions(dict(st)).next_action)
tmp=pathlib.Path(tempfile.mkdtemp()); rt=StudioRuntime(server_mode="mock", runtime_root=tmp/"r")
(tmp/"roots"/"p1").mkdir(parents=True); rt.projects["p1"]=dict(st); rt.project_roots["p1"]=tmp/"roots"/"p1"
_graph_exec.run_phase_node=lambda rt_,s,p:{**s,"current_phase":p}
_graph_exec.ensure_graph=lambda rt_:G()
print("APP", _graph_exec._resume_after_approval(rt, dict(st), "gen_planning")["current_phase"])
PY
```
- **Blast radius:** `app/_graph_exec.py`, `app/runtime.py:230`, `mcp/tools/review.py:149` (MCP `approve_phase` tool), `cli/driver.py`. A human approval while a provider is blocked enters and plans the generation phase (the node itself parks at the `generation_batch` gate without spending) instead of refusing — the exact transition the graph rule exists to prevent. `app/_graph_exec.py:70` still says `"# 10 phases x ~3 steps each"` although there are 11 phases.
- **Candidate owner module:** `phase-model` — `schemas/phase.py` owns `PHASE_ORDER`; the single `successor(phase)` / `advance_decision(state, *, blocked_providers)` transition law lives in `graph/phase_transitions.py` (it returns `RouterResult`, so it must stay in `graph` — see D7 in the Candidate module boundary). `app` calls that instead of re-deriving.
- **Extraction sketch:** move `_advance_result`'s decision into `graph.phase_transitions.advance_decision` returning the same `RouterResult`, have `app/_graph_exec.advance_to_next_phase` call it (or the equivalent `compute_actions` decision) rather than indexing `PHASE_ORDER`; guard test: for every phase × blocked-provider state, the app advance result must equal `compute_actions().next_action`.
- **Prior art:** `documentation/reviews/arch-lens-dataflow.md:131` notes resume progress is a `PHASE_ORDER`-index heuristic; the *second advance implementation and its provider-gate bypass* are new.

### F-PHASE-02 — The phase vocabulary and order are defined independently in eleven places across eight modules, and nothing pins agreement
- **Class:** O1 (duplicated normative model)
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** the set and order of pipeline phases.
- **De-facto owners (9 full 11-name definitions; 2 partial):**
  - `src/film_pipeline/graph/_action_routing.py:18` — `"PHASE_ORDER = ["` … `"\"delivery\","` (`:18-30`) — full
  - `src/film_pipeline/artifacts/paths.py:14` — `"PHASE_DIR_MAP: dict[str, str] = {"` … `"\"delivery\": \"10-delivery\","` (`:14-26`) — full
  - `src/film_pipeline/schemas/_base.py:77` — `"class FilmPhase(StrEnum):"` … `"DELIVERY = \"delivery\""` (`:77-90`) — full
  - `src/film_pipeline/constraints/_keywords.py:153` — `"_PHASE_KEYWORDS: tuple[str, ...] = ("` (`:153-165`) — full
  - `src/film_pipeline/graph/graph.py:55` — `"_PHASE_TO_NODE: dict[str, str] = {"` (`:55-67`) — full
  - `src/film_pipeline/graph/graph.py:85` — `"_APPROVAL_DESTINATIONS: dict[Hashable, str] = {"` (`:85-99`) — **10 of 11** (omits `intake`) and **restates `_PHASE_TO_NODE`**: 10 shared keys with byte-identical values, `intake` only in `_PHASE_TO_NODE`, plus `end`/`repair`/`await_approval`. So phase→node has two definitions, not one (M1).
  - `src/film_pipeline/graph/nodes/_repair_loop.py:38` — `"_PHASE_NODES: dict[str, Any] = {"` (`:38-50`) — full
  - `src/film_pipeline/graph/edges.py:40` — `"_NEXT_PHASE_AFTER_APPROVAL: Mapping[str, str]"` (`:40-54`) — full
  - `src/film_pipeline/graph/_agent_routing.py:35` — `"_PHASE_DEFAULT_AGENTS"` — **9 of 11**
  - `src/film_pipeline/graph/_action_routing.py:33`/`:47` — `"_PHASE_AGNOSTIC_PHASES"` (10) + `"_GENERATION_DEPENDENT_PHASES = {\"generation\"}"` — full (10 + 1)
  - `profiles/base.studio.yaml:4` — a 12th copy (unread: `documentation/reviews/hardcoded-values-inventory.md:62`)
- **Also phase-keyed but not line-initial (lower bound only, M2):** `graph/nodes/_context.py:329` `_UPSTREAM_CONTENT_SOURCES` names a phase as the first element of each of its 8 tuple values (5 distinct phases; `{{"constitution_ref": ("constitution", …), …}}`); `graph/nodes/_shared.py:85` `_CRITICAL_CONTEXT` keys 2; `schemas/kb.py:25`/`kb/manifest.py:44`/`film-knowledge-base/index/kb-manifest.yaml` use free-string `applies_to_phases` values (5 phase names + `"all"`, F-PHASE-11). None is counted among the eleven.
- **Drift proof (mutation scenario):** add a 12th phase `"assembly"` to `FilmPhase` and `PHASE_DIR_MAP` only (the minimum needed to store its artifacts). Storage works (`artifacts/paths.py:34` falls back to `PHASE_DIR_MAP.get(phase, phase)`), but `PHASE_ORDER` still has 11 entries, so `_advance_result` computes `idx = -1` (`:327`) and returns `"wrap"` — the run ends early with the phase never executed. **No test fails:** `tests/unit/test_graph.py:69-74` only asserts `len(PHASE_ORDER) == 11` and that each `PHASE_ORDER` entry has a gate; no test references `PHASE_DIR_MAP` (`grep -rn PHASE_DIR_MAP tests/ --include='*.py'` → no matches) and none pins `FilmPhase` membership.
- **Reproduce:**
  ```bash
  grep -rn "PHASE_DIR_MAP" tests/ --include='*.py'          # no matches
  grep -rn "list(FilmPhase)\|len(FilmPhase)" tests/ --include='*.py'   # no matches
  grep -rcE '^\s*"(intake|constitution|development|script|visual_dev|shot_bible|gen_planning|generation|qc|post|delivery)"' \
    src/film_pipeline --include='*.py' | awk -F: '{s+=$2; if($2>0) f++} END {print "entries="s" files="f}'   # entries=129 files=16
  grep -roE '"(intake|constitution|development|script|visual_dev|shot_bible|gen_planning|generation|qc|post|delivery)"' \
    src/film_pipeline --include='*.py' | wc -l              # 359 any-position occurrences (-roE counts occurrences; -rnE would count 323 lines)
  ```
  The 129 line-initial entries cover 16 files; the eleven tables above are the ones with a full or near-full ordered name list, so "eleven definitions" is a curated count over a larger literal population, and 129/359 are the measured lower bounds.
- **Blast radius:** routing, artifact layout, gates, KB context, repair dispatch, CLI target phase, MCP validation — the full vocabulary alone spans eight modules in four packages (`schemas`, `graph`, `artifacts`, `constraints`), plus partial registries in `mcp`, `checkpoints`, and `app` and an unread list in `profiles/`. A partial edit silently wraps, mis-routes, or writes to a raw-named directory.
- **Candidate owner module:** `phase-model` — one ordered `PHASE_ORDER: tuple[FilmPhase, ...]`; every other table becomes a derived view or a `FilmPhase`-keyed partial index.
- **Extraction sketch:** put `FilmPhase` + `PHASE_ORDER` in one module (e.g. `schemas/phase.py`), derive `_PHASE_TO_NODE`/`_PHASE_NODES`/`_NEXT_PHASE_AFTER_APPROVAL` from it (`{p: f"{p}_node" for p in PHASE_ORDER}` + a successor function), and make `PHASE_DIR_MAP` a validated `dict[FilmPhase, str]`. Guard test: assert `set(PHASE_DIR_MAP) == set(PHASE_ORDER) == set(FilmPhase)` and `list(PHASE_DIR_MAP) == [p.value for p in PHASE_ORDER]`, plus one AST test banning new line-initial phase-name literal blocks outside the owner.
- **Prior art:** `documentation/reviews/arch-lens-flexibility.md:19` records "five hand-maintained parallel phase tables with no single source"; `:120` is the "Phase keys" inventory row naming some of the sites. New here: the count is now **eleven independent definitions in eight modules** (the prior list omits `FilmPhase`, `PHASE_DIR_MAP`, `_PHASE_KEYWORDS`, `APPROVAL_GATES`, `_PHASE_NODES`); the values are still identical at HEAD; and the specific silent failure mode (`_advance_result` → `"wrap"`) is demonstrated.

### F-PHASE-03 — The phase→approval-gate map is written twice, and the QC subgraph writes the gate update inline
- **Class:** O1 (duplicated normative model) + O2 (duplicated invariant enforcement)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** which approval gate each phase parks at, and how a completed phase records it.
- **De-facto owners:**
  - `src/film_pipeline/graph/_action_routing.py:49` — the normative map — `"\"shot_bible\": \"shot_bible\","` … `"\"delivery\": \"final_delivery\","` (`:49-61`)
  - `src/film_pipeline/graph/nodes/_shared.py:147` — the parking update — `"\"human_approval_phase\": gate,"` (`:158`), called with a *second* literal per node: `src/film_pipeline/graph/nodes/prep.py:108` `gate="config"`, `:191` `gate="constitution"`, `:223` `gate="treatment"`, `:272` `gate="script"`, `src/film_pipeline/graph/nodes/visual.py:35` `gate="visual_bible"`, `:472` `gate="shot_bible"`, `:597` `gate="generation_spend"`, `src/film_pipeline/graph/nodes/generation.py:108` `gate="generation_batch"`, `src/film_pipeline/graph/nodes/qc.py:35` `gate="qc"`, `src/film_pipeline/graph/nodes/wrapup.py:21` `gate="assembly"`, `:44` `gate="final_delivery"`
  - `src/film_pipeline/graph/subgraphs/qc.py:263` — a hand-inlined third copy of `_phase_gate_updates` for QC — `"\"current_phase\": \"qc\","` / `"\"human_approval_phase\": \"qc\","` (`:267`,`:270`)
- **Drift proof (mutation scenario):** rename one gate in `APPROVAL_GATES` (e.g. `"shot_bible": "shot_matrix"`) without touching `src/film_pipeline/graph/nodes/visual.py:472`. `compute_actions().human_gate` becomes `"shot_matrix"` (`src/film_pipeline/graph/_action_routing.py:321`, surfaced to MCP at `mcp/tools/review.py:115` and in the recommendation text `:124`), while the interrupt payload keeps `"shot_bible"` (`src/film_pipeline/graph/nodes/approval.py:110` reads `state["human_approval_phase"]`). **No test fails:** `tests/unit/test_graph.py:72-74` checks only key presence, and `tests/unit/graph/test_wrapup_nodes.py:126`, `tests/unit/graph/test_qc_subgraph.py:85` assert the *node* literals, not `APPROVAL_GATES`. A mechanical comparison currently shows all 11 gate values agree.
- **Reproduce:**
  ```bash
  grep -rnE 'gate="[a-z_]+"' src/film_pipeline --include='*.py'
  grep -rn "human_approval_phase" src/ --include='*.py' | grep -v tests
  # all 11 values equal APPROVAL_GATES at HEAD; verified by the inventory script above
  ```
- **Blast radius:** `graph/nodes/*`, `graph/subgraphs/qc.py`, `graph/_action_routing.py`, MCP review package. Operator-facing gate identity can disagree between the router and the interrupt payload with no failing test.
- **Candidate owner module:** `phase-model` owns `APPROVAL_GATES`; `_phase_gate_updates` becomes the only writer of `human_approval_phase`, taking the gate from that map.
- **Extraction sketch:** delete the per-node `gate=` argument; `_phase_gate_updates(state, phase=...)` looks up `PHASE_GATES[phase]`. Replace `src/film_pipeline/graph/subgraphs/qc.py:263-271` with a call to `_phase_gate_updates`. Guard test: for every phase, `_phase_gate_updates(...)["human_approval_phase"] == APPROVAL_GATES[phase]`.
- **Prior art:** none for the gate map. The nearest row is the "Phase keys" inventory at `documentation/reviews/arch-lens-flexibility.md:120`, which lists several of the same *files* (`graph.py`, `src/film_pipeline/graph/edges.py:40-54`, `_agent_routing.py`, `base.studio.yaml`) but mentions neither `APPROVAL_GATES` nor the per-node `gate=` literals; the `APPROVAL_GATES` ↔ node-literal ↔ QC-inline triple is new.

### F-PHASE-04 — The "successor phase" function is implemented twice inside the graph
- **Class:** O1 (duplicated normative model) + O4 (parallel registries)
- **Severity:** High (impact 4 × drift 3 = 12)
- **Concern:** what the next phase is after a phase completes.
- **De-facto owners:**
  - `src/film_pipeline/graph/_action_routing.py:325` — successor by `PHASE_ORDER` index — `"next_phase = PHASE_ORDER[idx + 1]"` (`:333`); consumed by the phase-node edges (`edges.after_phase` strips the `advance_to_` prefix, `src/film_pipeline/graph/edges.py:75-76`)
  - `src/film_pipeline/graph/edges.py:40` — a hand-written successor table for the approval edge — `"\"generation\": \"qc\","` … `"\"delivery\": \"end\","` (`:49-52`); consumed by `after_approval` (`:119`)
- **Drift proof (mutation scenario):** swap `qc` and `post` in `_NEXT_PHASE_AFTER_APPROVAL` only. The approval path (`await_approval` → `after_approval`) sends `generation → post`, while the non-approval path (`after_phase` → `advance_to_<successor>`) sends `generation → qc`. `PHASE_ORDER` still reads `…, generation, qc, post, delivery`. The Reproduce grep (`grep -rn "after_approval\b" tests/ --include='*.py' | wc -l`) returns 28 refs to `after_approval` in `tests/` (imports, per-edge assertions such as `tests/unit/test_graph.py:228`, `tests/unit/graph/test_real_human_gates.py:103`, `tests/integration/test_dynamic_routing.py:177,203`, and 4 `_resume_after_approval` refs); none compares the table against `PHASE_ORDER`, so a `qc`-skipping swap passes.
- **Reproduce:**
  ```bash
  grep -rn "after_approval\b" tests/ --include='*.py' | wc -l      # 28 refs (imports + per-edge assertions; no table-vs-PHASE_ORDER check)
  grep -rn "_NEXT_PHASE_AFTER_APPROVAL" src/ tests/ --include='*.py'
  # inventory script above: all successors currently match PHASE_ORDER
  ```
- **Blast radius:** `graph/edges.py`, `graph/_action_routing.py`, `graph/graph.py` (`_APPROVAL_DESTINATIONS`). A divergence can skip `qc` or run a phase twice depending on whether the phase was reached via the approval gate or the direct edge — i.e. the two live routes through the same graph disagree.
- **Candidate owner module:** `phase-model` — `graph/phase_transitions.py` owns `successor(phase) -> FilmPhase | None`; `_NEXT_PHASE_AFTER_APPROVAL` and `_advance_result` both call it (D7).
- **Extraction sketch:** derive `_NEXT_PHASE_AFTER_APPROVAL = {p.value: successor(p) for p in PHASE_ORDER}`; guard test asserting every `PHASE_ORDER[i]` maps to `PHASE_ORDER[i+1]` and `delivery → end`.
- **Prior art:** `documentation/reviews/arch-lens-flexibility.md:19` lists both tables; the *duplicated successor invariant* and its skip-a-phase failure mode are new.

### F-PHASE-05 — Phase *order* is also encoded in `PHASE_DIR_MAP` insertion order and used as pipeline order by the artifact layer
- **Class:** O1 + O3 (split state authority)
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** which phase is "latest"/current when derived from storage.
- **De-facto owners:**
  - `src/film_pipeline/graph/_action_routing.py:18` — `PHASE_ORDER` — the graph's order authority
  - `src/film_pipeline/artifacts/store.py:501` — storage order authority — `"phase_order = {name: index for index, name in enumerate(paths.PHASE_DIR_MAP)}"` (`:501`), used to sort `list_artifacts`
  - `src/film_pipeline/artifacts/project_storage.py:136` — `"for phase, dirname in reversed(PHASE_DIR_MAP.items()):"` (`:136`), the storage-side "latest phase" rule
  - `src/film_pipeline/app/services/_project_discovery.py:35` — writes that value back into live state — `"current_phase=storage.latest_artifact_phase(project_id),"` (also `:54`)
- **Drift proof (mutation scenario, executed):** move `"post"` above `"qc"` in `PHASE_DIR_MAP` (a directory-naming edit that looks harmless). `src/film_pipeline/artifacts/project_storage.py:136` walks `reversed(PHASE_DIR_MAP.items())`, so the "latest phase with artifacts" it finds changes from the last-inserted backwards. At HEAD the tail is `[qc, post, delivery]` and a project holding both re-runs `latest_artifact_phase -> post`; after the reorder the tail is `[post, qc, delivery]` and the same project returns `qc` — the *earlier* phase. `src/film_pipeline/app/services/_project_discovery.py:35` writes that value straight into live `current_phase`, so the operator/MCP resume point moves **backwards** while `PHASE_ORDER` is unchanged. Reproduced:
  ```
  HEAD    tail ['qc', 'post', 'delivery'] -> post
  MUTATED tail ['post', 'qc', 'delivery'] -> qc
  ```
  `tests/unit/artifacts/test_store_v2.py:392-419` pins only `constitution < script`; no test compares `PHASE_DIR_MAP` order to `PHASE_ORDER`.
- **Reproduce:**
  ```bash
  grep -rn "PHASE_DIR_MAP" src/film_pipeline --include='*.py'
  grep -rn "PHASE_DIR_MAP" tests/ --include='*.py'   # no matches
  grep -n "reversed(PHASE_DIR_MAP" src/film_pipeline/artifacts/project_storage.py
  ```
- **Blast radius:** `artifacts/store.py` ordering, project discovery, the operator dashboard's `current_phase`, and MCP resume. The storage layer is a second, independent authority for the pipeline order.
- **Candidate owner module:** `phase-model` owns the order; `PHASE_DIR_MAP` stays in `artifacts` (it is a layout concern) but must be keyed by `FilmPhase` and validated to cover `PHASE_ORDER` in order.
- **Extraction sketch:** `PHASE_DIR_MAP` becomes `dict[FilmPhase, str]` with a module-import assertion that its key order equals `PHASE_ORDER`; `src/film_pipeline/artifacts/store.py:501` and `src/film_pipeline/artifacts/project_storage.py:136` iterate `PHASE_ORDER` and look up the dirname. Guard test: `list(PHASE_DIR_MAP) == [p.value for p in PHASE_ORDER]`.
- **Prior art:** none for `PHASE_DIR_MAP` as an ordering authority. The "Phase keys" row at `documentation/reviews/arch-lens-flexibility.md:120` does not name `PHASE_DIR_MAP` at all; its role as a **second ordering authority** feeding `current_phase` is new.

### F-PHASE-06 — The router's action vocabulary and the edge transition table disagree on `escalate_to_failure_handler`; coverage is by fallback, not declaration
- **Class:** O8 (missing contract) between two registries
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** the mapping from a computed next-action to a graph destination.
- **De-facto owners:**
  - `src/film_pipeline/graph/_action_routing.py:220` — the router emits the action — `"eligible=[\"escalate_to_failure_handler\", \"escalate_to_human\"],"` / `"next_action=\"escalate_to_failure_handler\","` (`:220-221`)
  - `src/film_pipeline/graph/edges.py:29` — the declared transition table lists four human-gate actions — `"_HUMAN_GATE_ACTIONS = ("` … `"\"continue_unrelated_work\","` (`:29-34`) — and `:37` `"_REPAIR_ACTIONS = (\"handle_blockers\",)"`; neither contains `escalate_to_failure_handler`
  - `src/film_pipeline/graph/edges.py:86` — the action is handled only by the catch-all — `"# Fallback: treat as human gate"` / `"return \"consistency_check\""` (`:86-87`)
- **Drift proof (existing gap):** the router's *documented* contract says rule 2 routes to a failure handler (`src/film_pipeline/graph/_action_routing.py:354`), and three suites assert the action *string* is produced (`tests/unit/test_graph.py:138`, `tests/integration/test_dynamic_routing.py:48`, `tests/e2e/test_orchestrator_decision_loop.py:134`), but no graph node for it exists (`src/film_pipeline/graph/graph.py:102-125`) and no test asserts where it *goes*. `after_phase` therefore silently converts a failure-handler escalation into a human gate via the `"# Fallback: treat as human gate"` branch. The action literal itself is pinned by those three tests, so the unguarded surface is the **destination**: adding `escalate_to_failure_handler` to `_HUMAN_GATE_ACTIONS` (or deleting it) changes routing with no test failure, and the fallback makes the omission invisible today. Executed: `after_phase({})` with `compute_actions` patched to return `escalate_to_failure_handler` → `consistency_check`.
- **Reproduce:**
  ```bash
  grep -nE 'next_action\s*=|next_action=f' src/film_pipeline/graph/_action_routing.py
  grep -rn "escalate_to_failure_handler" src/ tests/ --include='*.py'   # never asserted in graph/edges tests
  .venv/bin/python -c "import sys;sys.path.insert(0,'src');from unittest import mock;from film_pipeline.graph.edges import after_phase;from film_pipeline.graph.router import RouterResult;m=mock.patch('film_pipeline.graph.edges.compute_actions',return_value=RouterResult(next_action='escalate_to_failure_handler'));m.start();print(after_phase({}))"   # -> consistency_check
  ```
- **Blast radius:** `graph/edges.py`, `graph/graph.py`, `graph/_action_routing.py`. Failure escalation in headless mode terminates at an approval gate (auto-mode path, `src/film_pipeline/graph/edges.py:127-129`) instead of being triaged by an agent.
- **Candidate owner module:** `phase-model` transition law (`graph/phase_transitions.py`, D7) — one declared `ACTION → destination` table covering every action `compute_actions` can emit.
- **Extraction sketch:** make the action vocabulary a closed enum owned with the phase model; add a guard test that the set of `next_action` literals emitted by `_action_routing.py` is a subset of the edge table's declared actions (not the fallback).
- **Prior art:** new.

### F-PHASE-07 — Gate mode (human vs auto) is re-derived in two modules from the same config key
- **Class:** O2 (duplicated invariant enforcement) + O5 (policy-by-branch)
- **Severity:** Medium (impact 3 × drift 2 = 6)
- **Concern:** whether a phase pauses at a human gate or auto-approves.
- **De-facto owners:**
  - `src/film_pipeline/graph/edges.py:18` — `"def _is_auto_mode(state: dict[str, Any]) -> bool:"` reading `"studio.get(\"require_human_approval\", True)"` (`:24`); used at `:127`
  - `src/film_pipeline/graph/nodes/_shared.py:132` — `"def _require_human_approval(state: dict[str, Any]) -> bool:"` reading the same key (`:143`); used at `src/film_pipeline/graph/nodes/_shared.py:153`, `src/film_pipeline/graph/nodes/approval.py:217`, `src/film_pipeline/graph/subgraphs/qc.py:262`
- **Drift proof (mutation scenario):** add a second policy source to `_require_human_approval` (e.g. honour `studio.mode == "headless"`) without touching `_is_auto_mode`. The two predicates now disagree in **both** directions, and each direction fails differently:
  - `_is_auto_mode` says **auto** while `_require_human_approval` says **human**: a stalled, non-approved run takes `src/film_pipeline/graph/edges.py:127-129`, sets `completed = True` and returns `"end"` — the run silently terminates even though the node layer believes a human must answer the gate.
  - `_is_auto_mode` says **human** while `_require_human_approval` says **auto**: `await_approval` treats a stalled phase with blocking issues as headless and returns `{"approved": False}` (`src/film_pipeline/graph/nodes/approval.py:220-225`), then `after_approval` sees `_is_auto_mode` False and returns `"await_approval"` (`src/film_pipeline/graph/edges.py:130`) — the run re-enters the gate until the recursion limit.
  No test fails: `_is_auto_mode` is pinned only for the `require_human_approval` key (`tests/unit/graph/test_prep_gates.py:106-113`) and `_require_human_approval` only for the same key (`tests/unit/graph/test_real_human_gates.py:237-264`); nothing asserts the two agree.
- **Reproduce:**
  ```bash
  grep -rn "require_human_approval" src/film_pipeline --include='*.py'
  grep -rn "_is_auto_mode\|_require_human_approval" tests/ --include='*.py'
  ```
- **Blast radius:** `graph/edges.py`, `graph/nodes/_shared.py`, `graph/nodes/approval.py`, `graph/subgraphs/qc.py`. A disagreement either ends a stalled run that still needed a human (`completed = True`) or loops the gate to the recursion limit — not the "safe" behaviour either predicate documents alone.
- **Candidate owner module:** `phase-model` owns the gate-mode predicate; both call sites import it.
- **Extraction sketch:** keep `_require_human_approval` as the single predicate and have `edges._is_auto_mode` delegate (`return not _require_human_approval(state)`); guard test parameterized over both entry points.
- **Prior art:** new.

### F-PHASE-08 — Partial phase registries fall back silently for the phases they omit
- **Class:** O1 (duplicated normative model) + O8
- **Severity:** Medium (impact 2 × drift 3 = 6)
- **Concern:** per-phase defaults that must stay keyed to the phase vocabulary.
- **De-facto owners:**
  - `src/film_pipeline/graph/_agent_routing.py:35` — `_PHASE_DEFAULT_AGENTS` lists 9 phases (no `generation`, no `delivery`); the fallback is `"orchestrator-agent"` (`:52`)
  - `src/film_pipeline/graph/context_packets.py:128` — `PHASE_BUILDERS` lists 7 phases (no `generation`, `qc`, `post`, `delivery`); the fallback is no scoped context (`src/film_pipeline/graph/nodes/_agent_prompt_context.py:111-116`)
- **Drift proof (mutation scenario):** call the public `route_agent(state, phase="generation", task_type="create")` (`graph/router.py:39` exports it) with a registry and no `preferred_agent_id`: it returns `"orchestrator-agent"` instead of a generation agent, with `routing_reason` "using default agent" — no error, no test (`tests/unit/graph/test_create_path_routing.py` covers only `shot_bible`/`qc`/`script`). Adding `generation` to `_PHASE_DEFAULT_AGENTS` likewise changes nothing that any test observes.
- **Reproduce:**
  ```bash
  grep -rn "_PHASE_DEFAULT_AGENTS\|PHASE_BUILDERS" src/ tests/ --include='*.py'
  ```
- **Blast radius:** `graph/_agent_routing.py`, `graph/context_packets.py`, `graph/nodes/_agent_prompt_context.py`. A new/renamed phase silently loses its default agent or its scoped context instead of failing fast.
- **Candidate owner module:** `phase-model` — one `.get(phase)` index whose key set is checked to be `⊆ PHASE_ORDER`, with omitted phases declared explicitly as "no default".
- **Extraction sketch:** re-key both maps by `FilmPhase`; add a guard test asserting every key is in `PHASE_ORDER` and that intentional omissions are listed (`_PHASES_WITHOUT_DEFAULT_AGENT`).
- **Prior art:** `documentation/reviews/arch-lens-flexibility.md:19` notes `_PHASE_DEFAULT_AGENTS` as one of the parallel tables; its 9/11 coverage gap is new.

### F-PHASE-09 — The phase vocabulary leaks into five unrelated policy modules as raw strings
- **Class:** O1 (duplicated normative model)
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** the *vocabulary leak*, not the policies themselves. Five distinct policies each need to name phases, and each re-encodes phase names as bare strings with no link back to the phase model. The policies are legitimately owned by their modules (`checkpoints`, `constraints`, `mcp`, `graph`) and this finding does **not** propose moving them into `phase-model`; it proposes that their phase *keys* come from the one vocabulary so that a rename or a new phase cannot silently stop matching.
- **De-facto owners (raw-string phase keys, no shared source):**
  - `src/film_pipeline/checkpoints/rollback.py:68` — regeneration policy by phase — `"requires_regeneration=checkpoint.phase.value in (\"generation\", \"qc\", \"post\"),"`
  - `src/film_pipeline/constraints/_keywords.py:153` — `_PHASE_KEYWORDS` (full ordered copy), consumed by `constraints/extractor.py:328` to recognize `"stop at shot_bible"` (`:330`)
  - `src/film_pipeline/mcp/tools/planning.py:37` — budget caps by phase — `"\"visual_dev\": cap * 0.3,"` / `"\"generation\": cap * 0.6,"` / `"\"post\": cap * 0.1,"` (`:38-40`)
  - `src/film_pipeline/graph/nodes/_shared.py:85` — required upstream context by phase — `"_CRITICAL_CONTEXT: dict[str, list[str]] = {"` / `"\"development\": [\"constitution_ref\"],"` (`:85-88`)
  - `src/film_pipeline/mcp/tools/intake.py:73` — a local phase guard — `"if current_phase not in (\"intake\", \"\"):"`
- **Drift proof (mutation scenario):** narrow the regeneration set to `("generation", "qc")` (e.g. someone decides post is cheap to redo). Nothing fails: the `True` branch is untested — `tests/unit/checkpoints/test_checkpoints.py:159-173` rolls back a `FilmPhase.SCRIPT` checkpoint and asserts only `will_revert == ["script"]`. A rollback from a post checkpoint then reuses stale assembly/delivery artifacts without requiring regeneration. The same shape applies to the other four: mutate any set and only that module's own tests (or none) can notice.
- **Reproduce:**
  ```bash
  grep -rn "requires_regeneration" src/ tests/ --include='*.py'
  grep -rn "_PHASE_KEYWORDS" src/ --include='*.py'
  grep -rn "per_phase_caps_usd" -A 5 src/film_pipeline/mcp/tools/planning.py
  .venv/bin/python -c "import sys;sys.path.insert(0,'src');from film_pipeline.schemas._base import FilmPhase;print([s for s in ('generation','qc','post') if s not in [x.value for x in FilmPhase]])"   # []
  ```
- **Blast radius:** `checkpoints/rollback.py`, `constraints/`, `mcp/tools/planning.py`, `graph/nodes/_shared.py`, `mcp/tools/intake.py`. A renamed/added phase silently stops matching a policy in a module that never imports the vocabulary; no error, no test.
- **Candidate owner module:** `phase-model` owns **only the vocabulary**; each policy keeps its own map and its current owning module, but re-keyed to `FilmPhase` with an explicit completeness/complement declaration (e.g. `PHASE_REGENERATION_REQUIRED: frozenset[FilmPhase]`). The extraction is a keying change, not a relocation.
- **Extraction sketch:** convert each tuple/dict key to `FilmPhase`, have each module import `FilmPhase`/`PHASE_ORDER` from `phase-model`, and assert its keys are a subset (or an explicit complement) of `PHASE_ORDER`. `constraints/_keywords.py` is the one case that should *delete* its copy and import `PHASE_ORDER`.
- **Prior art:** `documentation/reviews/hardcoded-values-inventory.md:62` records the profile `phases` list as an unread declaration; the five src-side raw-string phase-keyed policies are new.

### F-PHASE-10 — Two phase→validator tables disagree on the token `"assembly"`, which is a phase alias in one and a *gate* name in the phase model
- **Class:** O4 (parallel registries) + O1
- **Severity:** Medium (impact 2 × drift 3 = 6)
- **Concern:** which validators belong to which phase.
- **De-facto owners — exactly two tables are genuinely phase-keyed:**
  - `src/film_pipeline/graph/nodes/qc.py:366` — the graph's live-phase table row — `({"post", "assembly", "qc"}, _run_assembly_validators),` (the `_VALIDATOR_RUNNERS` tuple spans `:361-368`); consumed by `"if phase in phases:"` (`:382`)
  - `src/film_pipeline/mcp/tools/validation.py:123` — the MCP live-validation table `_live_validator_specs`, six `_PhaseSpec(phases=...)` rows — `phases=("post", "assembly"),` (`:149`), `phases=("script",),` (`:129`), `phases=("visual_dev",),` (`:134`), `phases=("gen_planning",),` (`:139`), `phases=("shot_bible",),` (`:144`), `phases=("delivery",),` (`:154`)
  - `src/film_pipeline/graph/_action_routing.py:49` — the phase model that supplies the *other* meaning of the token — `"post": "assembly",` (`:59`), i.e. `"assembly"` is the **gate** for `post`
- **Adjacent but NOT phase-keyed (corrected):** `graph/subgraphs/qc.py:45-52` `_VALIDATOR_MAP` is keyed by validator **id** (`"script-structure"`, `"assembly"`, …) and `:210-217` `_WORKER_NODES` is keyed by node name; neither keys on a phase. `graph/subgraphs/qc.py:153` `_VALIDATOR_ARTIFACTS` (validator id → artifact-type tuple, e.g. `"assembly": ("assembly_manifest", "review_cut", "final_cut")`) is a third validator-id table the earlier draft omitted; it shares the id vocabulary but not the phase vocabulary.
- **Drift proof (existing vocabulary conflation):** the token `"assembly"` is a phase alias in `src/film_pipeline/graph/nodes/qc.py:366` and `mcp/tools/validation.py:149` but a gate name in `src/film_pipeline/graph/_action_routing.py:59`. `FilmPhase("assembly")` raises `ValueError`, so those two memberships are unreachable from `run_validation` (`src/film_pipeline/mcp/tools/validation.py:290` parses via `FilmPhase`) and from `_execute_phase_validators` (`src/film_pipeline/graph/nodes/qc.py:380` reads `current_phase`) — dead branches a reader must still maintain. The two live tables also drift independently: adding a validator to one does not update the other, and no test compares them. Mutation: delete `"assembly"` from `src/film_pipeline/graph/nodes/qc.py:366`; the graph and MCP tables now disagree, and only the dispatch test below notices (it asserts the graph set, not parity with MCP).
- **Reproduce:**
  ```bash
  grep -rn '"assembly"' src/film_pipeline --include='*.py'
  grep -rn "_VALIDATOR_MAP\|_VALIDATOR_RUNNERS\|_VALIDATOR_ARTIFACTS\|_live_validator_specs" src/ tests/ --include='*.py'
  .venv/bin/python -c "import sys;sys.path.insert(0,'src');from film_pipeline.schemas._base import FilmPhase;print([p for p in ('post','assembly') if p not in [x.value for x in FilmPhase]])"   # ['assembly']
  ```
- **Blast radius:** `graph/nodes/qc.py`, `mcp/tools/validation.py`, `graph/subgraphs/qc.py`. A phase's validator set can differ between the graph QC run and the MCP `run_validation` tool — the parallel-registry failure class O4 describes — and the `"assembly"` alias silently makes two table entries unreachable.
- **Candidate owner module:** `phase-model` owns the phase vocabulary; the two phase-keyed tables become `FilmPhase`-keyed registries (validator selection itself stays a `validation`/`mcp` concern). `_VALIDATOR_MAP`/`_VALIDATOR_ARTIFACTS`/`_WORKER_NODES` are validator-id/node-name tables and are out of scope for the phase model.
- **Extraction sketch:** key both phase tables by `FilmPhase`, drop the `"assembly"` alias (use the `post` phase), and add a guard test asserting each table's phase keys are valid `FilmPhase` members and that the graph and MCP phase sets agree.
- **Prior art:** `documentation/reviews/arch-lens-flexibility.md:17` (the "New validator" row) already names both registration sites — "`graph/subgraphs/qc.py` name→class map (:46-51) or `mcp/tools/validation.py` per-phase tuple fns (:73-115)" — and notes the runtime `ValidatorRegistry` "is never populated". New here: the `"assembly"` phase-vs-gate conflation and the two live phase tables' divergence.
- **Guard test:** `tests/unit/graph/test_qc_validator_dispatch.py:57-67` pins `_VALIDATOR_RUNNERS` membership (`{"post","assembly","qc"}`); it does not check `_live_validator_specs` or parity between the two.

### F-PHASE-11 — The knowledge base keys items by unvalidated free-string phase names
- **Class:** O8 (missing contract) + O4 (parallel registry)
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** a second, data-side phase registry that no code validates against the phase model.
- **De-facto owners:**
  - `src/film_pipeline/schemas/kb.py:25` — the field is free strings — `"applies_to_phases: list[str] = Field(default_factory=list)"`
  - `src/film_pipeline/kb/manifest.py:40-45` — the only reader matches raw tokens — `"if \"all\" in i.applies_to_phases or phase in i.applies_to_phases"`
  - `film-knowledge-base/index/kb-manifest.yaml:13,29,45,61,77,93,111,127,143,161,177,193` — 12 items carrying `applies_to_phases`; the distinct tokens are `all` plus the 5 phase names `gen_planning`, `generation`, `post`, `qc`, `visual_dev` (e.g. `:111` `"[visual_dev, gen_planning]"`, `:93` `"[qc, post]"`)
- **Drift proof (mutation scenario):** at HEAD every token is a valid phase name (or the `"all"` wildcard), so the leak is latent. Rename one token — e.g. `visual_dev` → `visualdev` at `film-knowledge-base/index/kb-manifest.yaml:111` — or add a phase to `FilmPhase` without touching the manifest. `by_phase("visual_dev")` silently returns fewer items; nothing raises and nothing fails: `tests/unit/kb/test_manifest.py:48-55` calls `by_phase("generation")` and asserts only `"len(items) >= 8"`, a cardinality lower bound that a typo'd token cannot break. There is no reverse check either (a phase with no KB item is legal and invisible).
- **Reproduce:**
  ```bash
  grep -h "applies_to_phases" film-knowledge-base/index/kb-manifest.yaml | grep -oE '\[[^]]*\]' | tr -d '[]' | tr ',' '\n' | tr -d ' ' | sort -u
  # all gen_planning generation post qc visual_dev   <- 5 phase names + "all", none validated
  grep -rn "applies_to_phases\|by_phase" src/film_pipeline tests/ --include='*.py'
  .venv/bin/python -c "import sys;sys.path.insert(0,'src');from film_pipeline.schemas._base import FilmPhase;print([t for t in ('gen_planning','generation','post','qc','visual_dev') if t not in [x.value for x in FilmPhase]])"   # []
  ```
- **Blast radius:** `kb/manifest.py::by_phase`, the agent/context packet builders that consume KB items, and the manifest YAML. A phase rename or addition shrinks (or silently fails to grow) the knowledge an agent receives, with no error at load time.
- **Candidate owner module:** `phase-model` owns the vocabulary; `kb` keeps `by_phase` and the manifest but types the field as `list[FilmPhase] | Literal["all"]` (or validates tokens against `FilmPhase` at manifest load).
- **Extraction sketch:** change `applies_to_phases: list[str]` to a validated phase-token type, or add a manifest-load assertion that every token is `"all"` or a `FilmPhase` member; guard test parameterized over the real manifest (fails on a typo'd token, unlike today's `>= 8`).
- **Prior art:** new (no `documentation/reviews/*` entry mentions `applies_to_phases` or `by_phase`).

---

## Ownership map

| Concern | De-facto owner(s) | Single or distributed |
|---|---|---|
| Phase name set & order | `graph/_action_routing.py:18`, `artifacts/paths.py:14`, `schemas/_base.py:77`, `constraints/_keywords.py:153`, `graph/graph.py:55`/`:85`, `graph/nodes/_repair_loop.py:38`, `graph/edges.py:40`, `graph/_agent_routing.py:35`, `src/film_pipeline/graph/_action_routing.py:33/47`, `profiles/base.studio.yaml:4`; partial: `graph/nodes/_context.py:329`, `graph/nodes/_shared.py:85`, `schemas/kb.py:25` + manifest YAML | **distributed** — **9** full 11-name definitions + `_APPROVAL_DESTINATIONS` (10-of-11) + `_PHASE_DEFAULT_AGENTS` (9-of-11) = the eleven, plus **7 further partial indices/policies** (`PHASE_BUILDERS`, `_VALIDATOR_RUNNERS`, `_live_validator_specs`, `per_phase_caps_usd`, `_CRITICAL_CONTEXT`, `_UPSTREAM_CONTENT_SOURCES`, KB `applies_to_phases`) and 1 unread config list |
| Canonical phase *type* | `schemas/_base.py:77` (`FilmPhase`) | single definition, **bypassed** by raw strings everywhere (F-PHASE-02) |
| Successor phase | `graph/_action_routing.py:333` and `graph/edges.py:40-54` | **distributed** (F-PHASE-04) |
| Phase advance / transition execution | `graph/_action_routing.py:325-345` (graph), `app/_graph_exec.py:425-445` (app/MCP) | **distributed** — proven behavioral divergence (F-PHASE-01) |
| Phase → approval gate | `src/film_pipeline/graph/_action_routing.py:49` vs 11 node call-site literals vs `src/film_pipeline/graph/subgraphs/qc.py:270` | **distributed** (F-PHASE-03) |
| Gate mode (human/auto) | `src/film_pipeline/graph/edges.py:18` and `src/film_pipeline/graph/nodes/_shared.py:132` | **distributed** (F-PHASE-07) |
| Gate-parking state update | `src/film_pipeline/graph/nodes/_shared.py:147` (`_phase_gate_updates`) + `src/film_pipeline/graph/subgraphs/qc.py:263` inline | mostly single, one bypass (F-PHASE-03) |
| Phase → directory name | `artifacts/paths.py:14` (`PHASE_DIR_MAP`) | single owner for dirnames; also a second **order** authority (F-PHASE-05) |
| Phase execution order from storage | `artifacts/store.py:501`, `artifacts/project_storage.py:136` | single implementation, wrong key source (F-PHASE-05) |
| Phase → node name | `graph/graph.py:55` (`_PHASE_TO_NODE`) **and** `graph/graph.py:85` (`_APPROVAL_DESTINATIONS`, 10 of the same 11 keys, identical values) | **distributed** — two definitions, not one (M1) |
| Phase → repair callable | `graph/nodes/_repair_loop.py:38` (`_PHASE_NODES`) | single definition (also consumed by `app/_graph_exec.py:452`) |
| Phase → default agent | `graph/_agent_routing.py:35` | single definition, 9/11 coverage (F-PHASE-08) |
| Phase → context builder | `graph/context_packets.py:128` | single definition, 7/11 coverage (F-PHASE-08) |
| Phase → required upstream context | `graph/nodes/_context.py:329` (`_UPSTREAM_CONTENT_SOURCES`, phase names as tuple values), `graph/nodes/_shared.py:85` (`_CRITICAL_CONTEXT`) | single definitions each, no key-set guard (F-PHASE-02/F-PHASE-09) |
| Phase → validator set (genuinely phase-keyed) | `graph/nodes/qc.py:361`, `mcp/tools/validation.py:123` | **distributed** (F-PHASE-10); validator-id tables `src/film_pipeline/graph/subgraphs/qc.py:45/153/210` are not phase-keyed |
| Phase → KB items | `schemas/kb.py:25` + `kb/manifest.py:40` + manifest YAML | single data-side registry, unvalidated tokens (F-PHASE-11) |
| Action → graph destination | `graph/edges.py:29-87`, `graph/graph.py:70-99` | single table with an undeclared fallback (F-PHASE-06) |
| Resume phase-progress comparison | `app/_resume.py:31-33` (reads `PHASE_ORDER`) | consumer — no new definition |

---

## Clean concerns (single-owner)

| Concern | Owner | Guard test |
|---|---|---|
| `FilmPhase` enum membership | `schemas/_base.py:77-90` | **no guard test** — no test references `len(FilmPhase)`/`list(FilmPhase)`; the gap is what makes F-PHASE-02 silent. |
| Phase → directory name (`PHASE_DIR_MAP` values) | `artifacts/paths.py:14-26` | **partial**: `tests/unit/artifacts/test_store_v2.py:392-419` pins `constitution` before `script` in `list_artifacts`; no test references `PHASE_DIR_MAP` or asserts its key set. |
| Approval-gate identity per phase (`APPROVAL_GATES` values) | `graph/_action_routing.py:49-61` | **partial**: `tests/unit/test_graph.py:72-74` and `tests/integration/test_dynamic_routing.py:210-212` assert every `PHASE_ORDER` entry *has* a gate; no test asserts the gate *value* equals the node's `gate=` literal. |
| Result of the router's advance rule (`advance_to_<successor>` / `wrap`) | `graph/_action_routing.py:325-345` | `tests/e2e/test_graph_execution.py:101` (`zip(nodes, PHASE_ORDER, strict=True)`) pins node order against `PHASE_ORDER`; `tests/unit/test_graph.py:78-104` pins the provider-blocked cases. |
| Graph node registration + entry dispatch | `graph/graph.py:55-99`, `:192-198` | `tests/e2e/test_graph_execution.py:85-104` exercises every node and phase name; `tests/unit/test_graph.py:227-228` pins `intake → constitution`. The two phase→node tables (`_PHASE_TO_NODE`, `_APPROVAL_DESTINATIONS`) are **not** asserted equal (M1). |
| Gate-parking update shape | `graph/nodes/_shared.py:147-159` (`_phase_gate_updates`) | `tests/unit/graph/test_wrapup_nodes.py:126,256` and `tests/unit/graph/test_real_human_gates.py` pin the returned keys for several phases — but per-phase gate *values* are pinned only for `post`/`delivery`/`qc`. |
| Repair re-dispatch by phase | `graph/nodes/_repair_loop.py:38-50` (`_PHASE_NODES`) | **no guard test** asserting its key set equals `PHASE_ORDER`; `tests/unit/graph/test_repair_loop*.py` exercise repair for selected phases only. |
| Required upstream context by phase | `graph/nodes/_context.py:329-338` (`_UPSTREAM_CONTENT_SOURCES`) | **no guard test** — `grep -rn "_UPSTREAM_CONTENT_SOURCES" tests/` has no matches (0); its 8 tuple values naming a phase can drift from `PHASE_ORDER` silently (M2). |
| KB items by phase | `schemas/kb.py:25`, `kb/manifest.py:40-45`, manifest YAML | **weak**: `tests/unit/kb/test_manifest.py:48-55` asserts `len(items) >= 8` for one phase; a typo'd phase token still passes (F-PHASE-11). |
| MCP approval/revision entry points | `mcp/tools/review.py:146-164` → `app/runtime.py:230-240` → `app/_graph_exec.py:272-307` | `tests/unit/mcp/tools/test_review.py`; the *target phase* of the advance is unguarded (F-PHASE-01). |
| `post/` agents consuming `FilmPhase` | `post/assembly_agent.py:125`, `src/film_pipeline/post/subtitle_agent.py:101`, `src/film_pipeline/post/delivery_packaging_agent.py:170` | no phase vocabulary of their own; covered indirectly by `tests/unit/post/**`. |

---

## Candidate module boundary

A single **`phase-model`** concern, split across two files so that no new package
cycle is created:

- **`schemas/phase.py` — the vocabulary kernel.** Proposed home is `schemas`,
  because `schemas` is the one package every module already imports (see audit
  14's import matrix). It holds *data only* — no `RouterResult`, no state, no
  provider knowledge.
- **`graph/phase_transitions.py` — the transition law. It must live in `graph`,
  not `schemas`.** The one transition invariant (`advance_decision`) returns or
  consumes `RouterResult`, which is defined at
  `graph/_action_routing.py:65`; putting it in `schemas/phase.py` would make
  `schemas` import `graph` while `graph` already imports `schemas`, creating a
  new `schemas ↔ graph` cycle — which is **not** among the five cycles recorded at
  `docs/modular-architecture/enola-architecture-facts.md:57-59` (C5 there is `schemas ↔ schemas/registries`)
  and would break the shared-kernel role measured at `:69` (`schemas` fan-in 509).
  `app` already imports `graph` (`PHASE_ORDER`, `compute_actions`),
  so `app/_graph_exec.py` calling `graph.phase_transitions` adds no new edge.

**`schemas/phase.py` — public contract (N, normative model):**
- `FilmPhase` (moved from `schemas/_base.py:77`).
- `PHASE_ORDER: tuple[FilmPhase, ...]` — the one ordered vocabulary.
- `PHASE_GATES: Mapping[FilmPhase, str]` (from `APPROVAL_GATES`).
- Named policy sets keyed by `FilmPhase`: `PHASE_AGNOSTIC_PHASES`,
  `GENERATION_DEPENDENT_PHASES`, `PHASE_KEYWORDS` (promoted from
  `_PHASE_KEYWORDS`). Policy sets that belong to another module
  (`PHASE_REGENERATION_REQUIRED` in `checkpoints`, budget caps in `mcp`) stay
  there and only *import* `FilmPhase` — see F-PHASE-09.

**`graph/phase_transitions.py` — transition law:**
- `successor(phase: FilmPhase) -> FilmPhase | None` — the one successor function.
- `advance_decision(state) -> RouterResult` — the one transition invariant,
  including the provider-blocked-generation refusal (`src/film_pipeline/graph/_action_routing.py:337`),
  callable from both `graph` and `app`.

**Invariant enforcement (I):** guards for `successor`/`advance_decision`, the
"every phase has exactly one gate" check, and the "phase-keyed map keys ⊆
PHASE_ORDER" check.

**Representation authority (R):** `phase-model` is the only place the vocabulary and
order are written. It does **not** own the directory names (`artifacts` keeps
`PHASE_DIR_MAP`, keyed by `FilmPhase` and asserted to cover `PHASE_ORDER` in
order), the node names (`graph` derives `_PHASE_TO_NODE`/`_APPROVAL_DESTINATIONS`/
`_PHASE_NODES` from `PHASE_ORDER`), the validator sets (`validation`/`mcp` keep
their registries but must key them by `FilmPhase`), or per-phase agent/context
maps (`graph` keeps `_PHASE_DEFAULT_AGENTS`/`PHASE_BUILDERS`/`_UPSTREAM_CONTENT_SOURCES`
as declared partial `FilmPhase` maps).

**Definitions that become imports from it:**

| Current definition | Becomes |
|---|---|
| `schemas/_base.py:77` `FilmPhase` | moved into `schemas/phase.py`; `_base` re-exports for one release |
| `graph/_action_routing.py:18` `PHASE_ORDER` | `schemas.phase.PHASE_ORDER` (router re-export deleted) |
| `graph/_action_routing.py:49` `APPROVAL_GATES` | `schemas.phase.PHASE_GATES`; node `gate=` literals deleted (F-PHASE-03) |
| `graph/_action_routing.py:33,47` phase-class sets | `schemas.phase` constants |
| `graph/edges.py:40` `_NEXT_PHASE_AFTER_APPROVAL` | derived in `graph.phase_transitions`: `{p: successor(p) for p in PHASE_ORDER}` |
| `graph/_action_routing.py:325-345` `_advance_result` | `graph.phase_transitions.advance_decision` (returns `RouterResult`) |
| `graph/graph.py:55/85` `_PHASE_TO_NODE`/`_APPROVAL_DESTINATIONS` | derived from `PHASE_ORDER` (+ `.value`) — one table, not two (M1) |
| `graph/nodes/_repair_loop.py:38` `_PHASE_NODES` | keyed/validated against `PHASE_ORDER` (naturally derived from the node module) |
| `constraints/_keywords.py:153` `_PHASE_KEYWORDS` | import `PHASE_ORDER` |
| `app/_graph_exec.py:425-445` `advance_to_next_phase` | calls `graph.phase_transitions.advance_decision`; keeps only the "run the chosen node and persist" mechanics |
| `artifacts/paths.py:14` `PHASE_DIR_MAP` | stays in `artifacts`, re-keyed to `FilmPhase`, coverage-asserted against `PHASE_ORDER` |
| `graph/_agent_routing.py:35`, `graph/context_packets.py:128`, `graph/nodes/qc.py:361`, `graph/nodes/_context.py:329`, `mcp/tools/validation.py:123`, `graph/nodes/_shared.py:85` | partial/policy maps re-keyed to `FilmPhase` with explicit completeness declarations |
| `checkpoints/rollback.py:68`, `mcp/tools/planning.py:37`, `schemas/kb.py:25` + `kb/manifest.py:40` | re-key/validate against `FilmPhase` **in place**; these modules keep ownership (F-PHASE-09, F-PHASE-11) |

**Guard tests that must ship with the extraction (B6):**
1. `test_phase_vocabulary_is_single_source` — `set(PHASE_ORDER) == set(FilmPhase)`,
   `list(PHASE_DIR_MAP) == [p.value for p in PHASE_ORDER]`.
2. `test_successor_matches_order` — every `PHASE_ORDER[i]` successor is
   `PHASE_ORDER[i+1]`; `delivery` has none.
3. `test_app_advance_equals_router_advance` — for every phase and
   blocked/healthy provider state, `advance_to_next_phase` picks the same phase
   `compute_actions()` names (fails on today's code, F-PHASE-01).
4. `test_every_phase_has_gate` extended to assert the *value* equals the gate the
   node writes into `human_approval_phase`.
5. `test_no_phase_literals_outside_phase_model` — AST scan for line-initial
   phase-name string entries outside the owner (extends the storage-boundary test
   precedent noted in audit 14).
6. `test_every_router_action_has_a_declared_edge` — the emitted `next_action`
   set ⊆ `edges` declared actions (fails on `escalate_to_failure_handler` today,
   F-PHASE-06).
7. `test_phase_keyed_maps_are_valid` — every `FilmPhase`-keyed map's keys ⊆
   `PHASE_ORDER`, and each intentionally partial map declares its omissions
   (covers `_PHASE_DEFAULT_AGENTS`, `PHASE_BUILDERS`, `_UPSTREAM_CONTENT_SOURCES`,
   `_CRITICAL_CONTEXT`, budget caps).
8. `test_kb_phase_tokens_are_valid` — every `applies_to_phases` token in the real
   manifest is `"all"` or a `FilmPhase` member (fails on a typo today, F-PHASE-11).

---

## Unverified hypotheses and coverage gaps (not findings)

- **`_APPROVAL_DESTINATIONS` (`src/film_pipeline/graph/graph.py:85-99`) omits `"intake"`.** I verified the
  literal does not contain `"intake"` and that `after_approval` never returns
  `"intake"` (it returns the *next* phase), so this is consistent today. I did
  **not** verify whether LangGraph would reject an `intake` key if a future
  successor function returned it; not claimed as a finding.
- **`profiles/base.studio.yaml:4-15` is unread.** I confirmed no `config`/`schemas`
  code reads a `phases` profile key, and `documentation/reviews/hardcoded-values-inventory.md:62`
  records it as a deliberate deferral. I did not trace generic profile
  passthrough (`resolved_config`) to prove the key is never echoed into state, so
  "dead" is bounded to "no code reads it as a phase list".
- **`scripts/*.py` phase lists** (`scripts/e2e-real-auto-approve.py:113`,
  `scripts/test-full-pipeline-direct.py:59`) are outside the `src` ownership map;
  I read the lists but did not audit script behavior.
- **Prior-art sweep scope.** I searched `documentation/audit-findings.md`,
  `documentation/reviews/*`, and `docs/clean-code-refactor/*` for
  `PHASE_ORDER|PHASE_DIR_MAP|phase vocabulary|phase order|APPROVAL_GATES` and
  found only `documentation/reviews/arch-lens-flexibility.md:17,19,120`, `documentation/reviews/arch-lens-dataflow.md:131`, and
  `documentation/reviews/hardcoded-values-inventory.md:62`. Other audits in this program may have
  reached different anchors; no claim is made about them.
- **Partial disagreement with verify-01 (D6).** The verifier's substantive point
  is accepted and applied: the row at `documentation/reviews/arch-lens-flexibility.md:120` mentions
  neither gate tables nor `PHASE_DIR_MAP`, so the F-PHASE-03/F-PHASE-05 prior-art
  sentences were rewritten. I disagree only with its off-by-one claim that the
  phase-vocabulary row is at `:119`: `grep -n` at HEAD shows line 120 =
  `| 3 | Phase keys "intake"…"delivery" | str repeated in 5 parallel tables | …`
  and line 121 = the Agent-capability-token row. The line number `:120` is
  therefore correct; only its *content* was misdescribed in the first draft.
- **Reproduction environment.** Commands use `.venv/bin/python` (repo venv,
  Python 3.12). System `python3` has no `pydantic`; the import-based comparisons
  will not run under it.
