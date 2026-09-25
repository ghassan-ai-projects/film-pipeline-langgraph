# 04 — Agent Registry, Capabilities, and Prompts

- **Repo:** `${REPO_ROOT}`
- **Branch:** `modular-app`
- **Audited commit:** `fb85baa0e6b769b709791a96a89980089304bf13` (the `fb85baa` merge of the storage upgrade)
- **Methodology:** `docs/modular-architecture/00-methodology-and-quality-bar.md` (bar A, §1.6 evidence rules, §1.7 finding format)
- **Reading rule applied:** every anchor in this document was read at HEAD. **The working tree was dirty while this audit was first written** (17 uncommitted `__init__.py` edits by a concurrent sibling task adding `ModuleContract` blocks, plus untracked `src/film_pipeline/architecture.py` and `tests/architecture/`). Those are *not* part of HEAD and no finding below rests on them. All quotes were taken from files that are unmodified at HEAD, or verified against `git show HEAD:<path>`.
- **Post-verification revision (fix loop).** Independently verified by `docs/modular-architecture/reviews/verify-04.md` (bar A6): **8 CONFIRMED, 1 DOWNGRADED, 1 CONFIRMED-with-dispute, 0 REJECTED**, and the working tree is now clean (`git status --porcelain` empty). This revision applies every required correction:
  - **F-AGENT-02 downgraded Critical 20 → High (3×5=15);** its `Reproduce` block was rewritten to `inspect.getfile` (the version the verifier read resolved `cls.__module__` against CWD and raised `FileNotFoundError` — verified now to run from any CWD), its comparison is now stated as set equality vs. overlap (1 exact / 3 partial / 7 disjoint, 4 with any overlap), and the severity was recomputed because the declared field it hinges on has **zero** production readers and therefore no deliverable impact.
  - **F-AGENT-06 drift-proof item 3 removed** — the `schemas/prompt.py` classes *are* schema-tested (`tests/unit/test_schemas.py:393,408,1032`), so "dead" was false; the other two items (4 divergent renderers, dead `prompt_runner.build` branch) stand. Marked **CONFIRMED (dispute)**.
  - **F-AGENT-04**, **F-AGENT-08**, **F-AGENT-09**, **F-AGENT-10**: two anchors, one count and the `.resolve(` grep corrected; `§2.4`'s undefined `S10` replaced with a defined vocabulary.
  - **F-AGENT-11 and F-AGENT-12 added** (seams the verifier found that this audit had tagged as covered but never analysed), and the §4 attribution of the `_FALLBACK_PROFILES` row corrected to audit `03`'s F-CFG-01. Both additions are labelled as post-verification in §3.
  - **Added post-verification (PENDING VERIFICATION):** F-AGENT-13 — the `graph` capability-classification sets (`_REVIEW_CAPABILITIES`/`_REPAIR_CAPABILITIES`) share zero tokens with the 30 capabilities `MVP_AGENTS` declares and are reachable from no caller in `src/` or `tests/`; added from the adversarial coverage pass (`reviews/adversarial-coverage.md` §H4) after independent re-verification.
  - **Finding count is now 13** (10 original + 3 added after verification): **2 Critical, 10 High, 1 Medium**. No finding was rejected; the only severity change is the F-AGENT-02 downgrade.
  - **The mix is mechanically checkable.** Run from the repo root; it parses every `- **Severity:**` bullet, recomputes `impact × drift`, maps the score to the §1.5 band and flags any label that disagrees with it:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run python - <<'PY'
import pathlib, re
doc = pathlib.Path("docs/modular-architecture/audit/04-agent-registry-and-prompts.md").read_text()
BANDS = [(16, "Critical"), (9, "High"), (4, "Medium"), (1, "Low")]
mix: dict[str, int] = {}
mismatch = 0
for m in re.finditer(
    r"- \*\*Severity:\*\* \*\*(\w+)\*\* \(impact (\d) × drift (\d) = (\d+)\)", doc
):
    band, impact, drift, score = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    assert impact * drift == score, (impact, drift, score)
    expected = next(b for t, b in BANDS if score >= t)
    flag = "" if band == expected else "   <-- MISMATCH"
    mismatch += band != expected
    print(f"impact {impact} × drift {drift} = {score:>2}  ->  {expected:<8} (recorded {band}){flag}")
    mix[expected] = mix.get(expected, 0) + 1
print("\nmix:", ", ".join(f"{mix.get(b, 0)} {b}" for _, b in BANDS))
print("mismatches:", mismatch)
PY
```

  Output at HEAD: thirteen `impact …` lines, then `mix: 2 Critical, 10 High, 1 Medium, 0 Low` and `mismatches: 0`.

---

## 1. Coverage

Every file in the assigned scope, plus the greps that widened it, followed by the entry points that consume the agent roster.

### 1.1 `src/film_pipeline/agents/**` (35 files)

| Area | Files | Status |
|---|---|---|
| Roster | `mvp/__init__.py` (170 L) | **has findings** (F-AGENT-01, 02, 03, 10) |
| Registry | `registry.py` (132 L) | **has findings** (F-AGENT-03, 10) |
| Implementation registry | `impl/registry.py` (36 L) | **has findings** (F-AGENT-02, 10) |
| Impl classes | `impl/{intake,constitution,development,screenwriter,structure_extractor,shot_bible,visual_dev,gen_planner,qc_synthesis,assembly,orchestrator}_agent.py`, `impl/{camera,character,environment,style}_bible_agent.py` (15 classes) | **has findings** (F-AGENT-02, 04) |
| Shared output parsing | `impl/_model_output.py` (41 L) | clean — see §5 |
| Prompt templates | `prompt_templates/registry.py` (103 L), `defaults/{__init__,spine,production,validators,_quality}.py` | **has findings** (F-AGENT-05, 06) |
| Runner | `runner.py` (471 L) | **has findings** (F-AGENT-06, 07) |
| Model routing | `model_routing/__init__.py` (161 L) | **has findings** (F-AGENT-01 supporting) |
| Model adapter | `model_adapter.py` (382 L) | **has findings** (F-AGENT-07) |
| JSON recovery | `_json_extraction.py` (86 L) | **has findings** (F-AGENT-07) |
| HTTP transport | `_http_transport.py` (93 L) | clean, no agent-roster content |
| Lifecycle/handoff | `base.py` (60 L), `handoff.py` (51 L) | **has findings** (F-AGENT-02 supporting: `HandoffManager` is unreachable from production) |
| Package surface | `__init__.py` (22 L at HEAD) | clean |

### 1.2 `schemas/registries/*.py` (agent-related)

- `schemas/registries/agent_registry.py` (28 L) — `AgentRegistryEntry`: **has findings** (F-AGENT-10: duplicate of `AgentRegistration`, dead).
- `schemas/registries/model_registry.py`, `provider_registry.py` — read; no agent-roster content.
- `schemas/registries/validator_registry.py` — **has findings** (F-AGENT-08, in scope via validator prompt templates).
- `schemas/registries/__init__.py` (30 L) — exports only.

### 1.3 `graph`

| File | Status |
|---|---|
| `graph/_agent_routing.py` (211 L) | **has findings** (F-AGENT-10 supporting: `_PHASE_DEFAULT_AGENTS`, 2 phases silently fall back) |
| `graph/nodes/_agent_artifacts.py` (150 L) | **clean** — persists artifacts; reads no agent contract (see §5) |
| `graph/nodes/_context.py` (465 L) | **has findings** (F-AGENT-01: `_AGENT_PROFILE_MAP`; F-AGENT-05: `_get_template_registry`) |
| `graph/nodes/_agent.py` (238 L) | **has findings** (F-AGENT-01, 02) |
| `graph/nodes/_agent_handoff.py` (143 L) | clean w.r.t. roster; records `template_id`/`model_profile` |
| `graph/nodes/_agent_prompt_context.py` (149 L) | **has findings** (F-AGENT-11: hardcoded `"orchestrator-agent"` / `"structure-extractor-agent"` branches) |
| `graph/nodes/{prep,visual,qc,wrapup,approval}.py` | **has findings** (F-AGENT-02: consumers read impl keys, not declared `output_artifacts`) |
| `graph/services.py` (137 L) | **has findings** (F-AGENT-08: `validator_registry: Any = None`) |
| `graph/router.py`, `graph/subgraphs/qc.py` | **has findings** (F-AGENT-08) |

### 1.4 `mcp`

| File | Status |
|---|---|
| `mcp/tools/bibles/{camera,character,environment,style,shot}.py` + `_shared.py` | **has findings** (F-AGENT-04) |
| `mcp/tools/registry.py` (387 L) | **clean** — registers *tools*, not agents; no agent id appears in it |
| `mcp/tools/kb.py` | **has findings** (F-AGENT-09: `agent_id` default `"orchestrator"`) |
| `mcp/tools/audit.py` | clean — projects `_routing_decisions`, defines no agent id |
| `mcp/tools/reference_generation/retry_loop.py` | **has findings** (F-AGENT-04: second, *correct* model-resolution idiom — `resolve_or_raise`) |

### 1.5 `app` and other entry points

- `app/mock_responses.py` (435 L) — **has findings** (F-AGENT-04 supporting: second mock-response authority for bibles).
- `app/smoke.py:22-45` — `check_agent_registry` / `check_validator_registry` count rows only; no agreement check.
- `tests/` (180 files) — searched for roster/registry agreement tests; results in §2.4 and §5.
- Entry points `cli.run.main`, `mcp.server.main`, `app.product_gate.main`, `langgraph.json` — reached through `graph/services.py` `_mvp_agent_registry()`; covered by §1.3/§1.5.

### 1.6 Grep widening (exact commands)

```
grep -rln "AGENT\|agent_id\|capabilit\|ROSTER\|_AGENT_PROFILE_MAP\|MVP" src/film_pipeline/ --include=*.py
grep -rn "agent_id=\|AgentRegistration\|get_agent_class\|prompt_templates\|_AGENT_PROFILE_MAP\|agent_registry\|MVP_AGENTS" src/film_pipeline/mcp/
grep -rn "template_id" src/ --include=*.py
grep -rn "default_model_profile" src/ --include=*.py
grep -rn "output_artifacts" src/ --include=*.py
grep -rn "known_kb_domains\|known_output_artifacts\|known_model_profiles" src/ tests/ --include=*.py
grep -rn "applies_to_agents" film-knowledge-base/index/kb-manifest.yaml
```

Beyond the assigned scope these reached: `kb/{manifest,packets,retrieval}.py`, `film-knowledge-base/index/kb-manifest.yaml` (F-AGENT-09), `validation/base.py`, `validation/impl/*`, `validation/validators/__init__.py` (F-AGENT-05/06/07/08), and `schemas/prompt.py` (F-AGENT-06). Each is a place that independently decides which agent exists or which prompt that agent gets, so each belongs to this cluster.

---

## 2. Roster reconciliation

### 2.1 The nine sources of truth

| Id | Source | Location | Rows |
|---|---|---|---|
| **S1** | `MVP_AGENTS` roster | `src/film_pipeline/agents/mvp/__init__.py:15` | 11 |
| **S2** | `AGENT_CLASS_BY_ID` impl registry | `src/film_pipeline/agents/impl/registry.py:18` | 12 |
| **S3** | prompt-template `agent_id`s (one registry, two id spaces) | `agents/prompt_templates/defaults/{spine,production,validators}.py` | 18 = 11 agent + 7 validator |
| **S4** | `_AGENT_PROFILE_MAP` model-profile map | `src/film_pipeline/graph/nodes/_context.py:27` | 21 |
| **S5** | `default_mock_responses()` keys | `src/film_pipeline/app/mock_responses.py:99` | 11 |
| **S6** | `_PHASE_DEFAULT_AGENTS` values | `src/film_pipeline/graph/_agent_routing.py:35` | 9 |
| **S7** | `_run_agent(agent_id=...)` call-site literals | `graph/nodes/{prep,visual,qc,wrapup,approval}.py` | 11 distinct |
| **S8** | MCP bible `AgentRegistration(agent_id=...)` literals | `mcp/tools/bibles/{camera,character,environment,style,shot}.py` | 5 |
| **S9** | KB manifest `applies_to_agents` tokens | `film-knowledge-base/index/kb-manifest.yaml` | 6 (excl. `all`) |

The mechanical source (`reproduced in §2.4`):

```bash
.venv/bin/python -c "
from film_pipeline.agents.mvp import MVP_AGENTS
from film_pipeline.agents.impl.registry import AGENT_CLASS_BY_ID
from film_pipeline.agents.prompt_templates.registry import get_registry
from film_pipeline.app.mock_responses import default_mock_responses
from film_pipeline.graph.nodes._context import _AGENT_PROFILE_MAP
print(len(MVP_AGENTS), len(AGENT_CLASS_BY_ID), len(get_registry().templates),
      len(default_mock_responses()), len(_AGENT_PROFILE_MAP))
"
# -> 11 12 18 11 21
```

### 2.2 Membership matrix

`Y` = name is declared in that source; `.` = absent. `S3 tpl` counts the 11 agent templates only (the 7 validator templates are reconciled separately in §2.3).

| declared name | S1 MVP | S2 class | S3 tpl | S4 profile | S5 mock | S6 phase | S7 call | S8 mcp | S9 kb |
|---|---|---|---|---|---|---|---|---|---|
| `camera-bible-agent` | . | . | . | . | . | . | . | Y | . |
| `character-bible-agent` | . | . | . | . | . | . | . | Y | . |
| `character-dossier-agent` | . | . | . | Y | . | . | . | . | . |
| `clip-validator` | Y | Y | Y | Y | Y | Y | Y | . | . |
| `config-inference-agent` | . | . | . | Y | . | . | . | . | . |
| `continuity-ledger-agent` | . | . | . | Y | . | . | . | . | . |
| `environment-bible-agent` | . | . | . | Y | . | . | . | Y | . |
| `failure-handling-agent` | Y | Y | Y | Y | Y | Y | Y | . | Y |
| `film-constitution-agent` | Y | Y | Y | Y | Y | Y | Y | . | . |
| `full-movie-flow-validator` | . | . | . | Y | . | . | . | . | . |
| `generation-agent` | . | . | . | . | . | . | . | . | Y |
| `generation-scheduler-agent` | . | . | . | Y | . | . | . | . | . |
| `intake-classifier-agent` | Y | Y | Y | Y | Y | Y | Y | . | . |
| `kb-curator-agent` | . | . | . | Y | . | . | . | . | . |
| `orchestrator` | . | . | . | . | . | . | . | . | Y |
| `orchestrator-agent` | Y | Y | Y | Y | Y | .* | Y | . | . |
| `prompt-composition-agent` | . | . | . | Y | . | . | . | . | Y |
| `provider-agent` | . | . | . | . | . | . | . | . | Y |
| `provider-planning-agent` | Y | Y | Y | Y | Y | Y | Y | . | . |
| `qc-agent` | . | . | . | . | . | . | . | . | Y |
| `reference-strategy-planner` | Y | Y | Y | Y | Y | Y | Y | . | . |
| `scene-continuity-validator` | . | . | . | Y | . | . | . | . | . |
| `screenwriter-agent` | Y | Y | Y | Y | Y | Y | Y | . | . |
| `shot-design-agent` | Y | Y | Y | Y | Y | Y | Y | **Y** | . |
| `structure-extractor-agent` | Y | Y | Y | Y | Y | . | Y | . | . |
| `style-bible-agent` | . | . | . | . | . | . | . | Y | . |
| `treatment-agent` | Y | Y | Y | Y | Y | Y | Y | . | . |
| `visual-dev-agent` | . | **Y** | . | Y | . | . | . | . | . |

\* `orchestrator-agent` is S6's *fallback literal* (`_default_agent_for` returns it, `graph/_agent_routing.py:52`) but is not a value in the phase table itself.

**Names declared nowhere but `S4`** (7): `character-dossier-agent`, `config-inference-agent`, `continuity-ledger-agent`, `full-movie-flow-validator`, `generation-scheduler-agent`, `kb-curator-agent`, `scene-continuity-validator`.
**Names declared only in `S8`** (3): `camera-bible-agent`, `character-bible-agent`, `style-bible-agent`.
**Names declared only in `S9`** (4): `generation-agent`, `orchestrator`, `provider-agent`, `qc-agent`.

### 2.3 Concrete drift proofs

**(a) `_AGENT_PROFILE_MAP` disagrees with the contract it is supposed to mirror — 2 of 11 rows.**

| agent | contract `default_model_profile` | `_AGENT_PROFILE_MAP` | runtime wins |
|---|---|---|---|
| `intake-classifier-agent` | `"creative_writer"` (`mvp/__init__.py:40`) | `"operations_triage"` (`_context.py:44`) | the map (`_agent.py:152`) |
| `structure-extractor-agent` | `"schema_enforcer"` (`mvp/__init__.py:96`) | `"strict_validator"` (`_context.py:39`) | the map (`_agent.py:152`) |

```bash
.venv/bin/python -c "
from film_pipeline.agents.mvp import MVP_AGENTS
from film_pipeline.graph.nodes._context import _AGENT_PROFILE_MAP as M
print([(a.agent_id,a.default_model_profile,M.get(a.agent_id)) for a in MVP_AGENTS
       if a.default_model_profile!=M.get(a.agent_id)])"
# -> [('intake-classifier-agent', 'creative_writer', 'operations_triage'),
#     ('structure-extractor-agent', 'schema_enforcer', 'strict_validator')]
```

The disagreement is not cosmetic: `creative_writer` is `max_tokens: 8192, temperature: 0.7` while `operations_triage` is `max_tokens: 4096, temperature: 0.2` (`agents/model_routing/__init__.py:19-26,51-56`), and `schema_enforcer` is `temperature: 0.0` while `strict_validator` is `0.1` (`:27-44`).

**(b) `AGENT_CLASS_BY_ID` declares `visual-dev-agent`, which no roster registers.** `impl/registry.py:26` `"visual-dev-agent": VisualDevAgent,`. Routing to it yields `contract=None` and the `agent_not_found` early return (`graph/nodes/_agent.py:211-212`).

**(c) `S4` carries 10 ids with no registered contract** — the 7 S4-only names plus `visual-dev-agent`, `environment-bible-agent`, `prompt-composition-agent`.

**(d) `shot-design-agent` is declared twice with two *different* contracts.** MVP (`mvp/__init__.py:114-127`) declares `capabilities=["shot_design","matrix_assembly","coverage_planning"]`, `input_artifacts=["script","scene_intents","character_bible","environment_bible"]`, `output_artifacts=["shot_bible","master_film_matrix"]`, plus KB domains and failure modes. MCP (`mcp/tools/bibles/shot.py:136-145`) declares `capabilities=["shot_design","matrix_planning"]`, `input_artifacts=["script","visual_refs","character_bible"]`, `output_artifacts=["master_film_matrix"]`, and omits `prompt_framework`, `default_model_profile`, `allowed_kb_domains`, and `failure_modes`.

**(e) `environment-bible-agent` exists in `S4` (a profile row) and `S8` (a live MCP contract) but in neither `S1` nor `S2`** — so it has a model profile and an executable prompt path but no registry entry and no implementation class mapping.

**(f) Validator space: three sources, one live divergence.** `MVP_VALIDATORS` (15 rows, `validation/validators/__init__.py:11-167`) vs the `ValidatorRegistryEntry` each impl hardcodes in `__init__` (7 rows) vs the 7 validator prompt templates (`prompt_templates/defaults/validators.py`):

- `scene-writing-validator.blocking_conditions`: `["missing_scene_intent", "no_conflict", "scene_count_under_min"]` (`validation/impl/script_structure.py:139`) vs `["missing_scene_intent", "no_conflict"]` (`validation/validators/__init__.py:40`).
- `delivery-completeness-validator` exists as an impl entry (`validation/impl/delivery_completeness.py:109`) and a prompt template (`validators.py:319`) but **not** in `MVP_VALIDATORS`.
- 9 `MVP_VALIDATORS` ids have no prompt template: `act-structure-validator`, `character-dossier-validator`, `clip-quality-validator`, `environment-bible-validator`, `full-movie-flow-validator`, `logline-validator`, `prompt-adherence-validator`, `shot-design-validator`, `treatment-validator`.

### 2.4 Does any test prove these agree?

**Independent reconciliation (post-verification).** `reviews/verify-04.md` recomputed all nine sources with a script that imports the real objects rather than regexing, from a clean HEAD. It reproduced every membership claim in §2.2 and **refuted none**; the only wording correction it raised is now applied (S8 contributes 4 roster-absent ids, 3 of which are S8-only — see the table below).

**Yes, but only forward and only for S1.** `tests/unit/agents/test_mvp_invariants.py:38-69` parametrizes over `MVP_AGENTS` and asserts, per row, that an implementation class, a dedicated prompt template, a resolvable model profile, and a mock response all exist. `tests/unit/graph/test_agent_profile_routing.py:35-40` adds `agent_id in _AGENT_PROFILE_MAP` for every MVP agent.

What is **not** pinned:

| invariant | test? | consequence today |
|---|---|---|
| S1 ⊆ S2 | `test_mvp_invariants.py:39-42` | holds |
| S1 ⊆ S3 | `test_mvp_invariants.py:44-48` | holds |
| S1 ⊆ S4 (membership only) | `test_agent_profile_routing.py:35-40` | holds |
| S1 ⊆ S5 | `test_mvp_invariants.py:61-69` | holds |
| **S1 `default_model_profile` == S4 value** | **none** | **2 rows already disagree (§2.3a)** |
| **S2 ⊆ S1 ∪ documented aliases** | **none** | `visual-dev-agent` orphan |
| **S4 ⊆ S1 ∪ documented aliases** | **none** | 10 orphan rows |
| **S3 ⊆ S1 ∪ V (validator ids)** | **none** | no test fails if a template names a nonexistent agent or validator |
| **S8 ⊆ S1 ∪ aliases** | **none** | 4 MCP bible ids are absent from the roster (3 of them S8-only: `camera-bible-agent`, `character-bible-agent`, `style-bible-agent`; plus `environment-bible-agent`, which otherwise lives only in S4) |
| **S9 ⊆ S1 ∪ aliases** | **none** | 4 KB tokens never match a real agent |
| **S4 values ∈ `ModelRouter.list_profiles()`** | none | 21/21 happen to be valid today |
| **`_PHASE_DEFAULT_AGENTS` keys == `PHASE_ORDER`** | none | 2 phases silently fall back (`generation`, `delivery`) |

`V` = the validator-id vocabulary: the 15 `MVP_VALIDATORS` ids (`validation/validators/__init__.py:11-167`) plus `delivery-completeness-validator`, which exists only as an impl entry and a template (§2.3f). `S3` is one registry holding both id spaces; §2.1's row splits its 18 entries into the 11 agent space and the 7 validator space.

`tests/unit/agents/test_impl_registry.py:21-23` asserts `len(AGENT_CLASS_BY_ID) == len(set(AGENT_CLASS_BY_ID))` — a dict cannot contain duplicate keys, so the assertion is vacuous.

---

## 3. Findings

### F-AGENT-01 — Two model-profile authorities per agent; the runtime ignores the contract and the two already disagree
- **Class:** O1 (duplicated normative model) + O5 (policy re-derived per call site)
- **Severity:** **Critical** (impact 4 × drift 5 = 20)
- **Concern:** Which model profile (and therefore which model, token budget, and temperature) an agent runs with.
- **De-facto owners:**
  - `src/film_pipeline/agents/mvp/__init__.py:40` — contract declares the profile — `default_model_profile="creative_writer",`
  - `src/film_pipeline/agents/mvp/__init__.py:96` — second divergent declaration — `default_model_profile="schema_enforcer",`
  - `src/film_pipeline/graph/nodes/_context.py:44` — the map that actually decides — `"intake-classifier-agent": "operations_triage",`
  - `src/film_pipeline/graph/nodes/_context.py:39` — `"structure-extractor-agent": "strict_validator",`
  - `src/film_pipeline/graph/nodes/_agent.py:152` — the only runtime read — `resolved_profile = _AGENT_PROFILE_MAP.get(agent_id, "operations_triage")`
  - `src/film_pipeline/agents/registry.py:78` — the contract field is only ever *validated*, never read — `if contract.default_model_profile not in self.known_model_profiles:`
  - `src/film_pipeline/agents/registry.py:17` — a third, unguarded profile id-space — `return {*ModelRouter().list_profiles(), "orchestrator"}`. The legacy alias `"orchestrator"` is injected into the set of *known profiles* although no `default_model_profile` anywhere uses it (`grep -rn 'default_model_profile="orchestrator"' src/ tests/` → no match) and `_AGENT_PROFILE_MAP` has no such key (`_context.py` has `"orchestrator-agent"` at `:50`, not `"orchestrator"`); the only other `"orchestrator"` literal is an unrelated *agent_id* default at `mcp/tools/kb.py:99`.
- **Drift proof:** Existing divergence, both sites cited: `intake-classifier-agent` declares `creative_writer` (`mvp/__init__.py:40`) but runs `operations_triage` (`_context.py:44`); `structure-extractor-agent` declares `schema_enforcer` (`:96`) but runs `strict_validator` (`:39`). **The divergence is not merely unpinned — it is pinned on the wrong side:** `tests/unit/graph/test_agent_profile_routing.py:21` asserts `_AGENT_PROFILE_MAP["structure-extractor-agent"] == "strict_validator"`, locking in the value that contradicts the contract, and `:11-27` hardcode 10 map values in total. **Mutation scenario:** change `mvp/__init__.py:40` to any other valid profile; the run still uses `operations_triage` because `_agent.py:152` never consults the contract, and no test fails — `test_mvp_invariants.py:50-59` only checks that the declared profile is *resolvable*, never that it equals the map value. Verified: `grep -rn "default_model_profile" src/ --include=*.py` shows the only non-definition reads are `registry.py:74` and `:78`, both validation.
- **Reproduce:** `.venv/bin/python -c "from film_pipeline.agents.mvp import MVP_AGENTS; from film_pipeline.graph.nodes._context import _AGENT_PROFILE_MAP as M; print([(a.agent_id,a.default_model_profile,M.get(a.agent_id)) for a in MVP_AGENTS if a.default_model_profile!=M.get(a.agent_id)])"`
- **Blast radius:** `graph/nodes/_agent.py:152` (every critical-agent model call), `graph/nodes/_context.py:400-414` (`_model_overrides_for` selects overrides by the *map's* profile name, so a profile override in `quality.festival.yaml` lands on a different profile than the contract advertises), `agents/model_routing/__init__.py:19-68`. User-visible: the intake classifier runs at temperature 0.2/4096 tokens instead of 0.7/8192, and the structure extractor at 0.1 instead of 0.0.
- **Candidate owner module:** `agents.registry` — one `AgentDescriptor` per agent carrying `model_profile` as the single normative value, with `_AGENT_PROFILE_MAP` reduced to (or derived from) that field.
- **Extraction sketch:** add a reverse-agreement guard test first (`for a in MVP_AGENTS: assert _AGENT_PROFILE_MAP[a.agent_id] == a.default_model_profile`) — it fails today on 2 rows; then either delete the divergent map rows and read `contract.default_model_profile` at `_agent.py:152`, or delete `default_model_profile` from the contract and treat the map as the sole owner. Public contract unchanged either way; guard test is the new invariant.
- **Prior art:** `documentation/reviews/arch-lens-flexibility.md:16` ("three parallel per-agent tables (contract list, class dict, profile map) must stay aligned by hand") and `:40` ("derive `_AGENT_PROFILE_MAP` default from contract's `default_model_profile` … already validated against `ModelRouter` at register time"). **New at HEAD:** the prior review proposed the derivation but did not report that the two authorities *already disagree on 2 of 11 rows*, and did not connect the disagreement to the different token/temperature budgets. Still present, unresolved.

### F-AGENT-02 — The registered implementation's role and outputs contradict the agent's declared contract
- **Class:** O1 (duplicated normative model: the contract's identity vs the class's identity) + O8 (missing contract: consumers re-derive the artifact key)
- **Severity:** **High** (impact 3 × drift 5 = 15) — **downgraded from Critical (4×5=20) after verification** (`reviews/verify-04.md`): the divergence is real and unguarded, but the field it hinges on (`output_artifacts`) has **zero** production readers, so no wrong behaviour reaches a deliverable. Impact 3 = wrong/latent internal model, fully recoverable; drift 5 = no test.
- **Concern:** Which artifact an agent actually produces, and what kind of agent it is.
- **De-facto owners:**
  - `src/film_pipeline/agents/mvp/__init__.py:158-162` — declares a failure-handling operator — `role=AgentRole.OPERATOR,` / `capabilities=["error_classification", "recovery_decision", "retry_policy"],` / `output_artifacts=["failure_decision"],`
  - `src/film_pipeline/agents/impl/registry.py:29` — binds that id to the assembly implementation — `"failure-handling-agent": AssemblyAgent,`
  - `src/film_pipeline/agents/impl/assembly_agent.py:64` — what it actually returns — `return {"assembly_manifest": manifest}`
  - `src/film_pipeline/graph/nodes/wrapup.py:30` — the consumer reads the impl key — `manifest = result.get("assembly_manifest")`
- **Drift proof:** Existing divergence, all 11 rows reconcilable. Comparison basis: **set equality** (declared set == returned set), not mere overlap — under **non-empty overlap** the two sides agree for **4 of 11** agents (`intake-classifier-agent`, `treatment-agent`, `screenwriter-agent`, `structure-extractor-agent`) and under **set equality** for exactly **1 of 11** (`structure-extractor-agent`). `execute()` return keys (AST-extracted, `§Reproduce`) vs declared `output_artifacts`: exactly one agent matches exactly (`structure-extractor-agent` → `execution_brief`), three overlap partially (`intake-classifier-agent` contains `classified_input` but also returns an undeclared `profile`; `treatment-agent` loses `act_map`; `screenwriter-agent` loses `scene_intents` and gains `story_bible`), and **seven share no key at all** (one of those, `orchestrator-agent`, is an extraction artifact, not a second divergence — its `execute` returns `decision.model_dump()`, see §7) — e.g. `clip-validator` declares `validation_report` (`mvp/__init__.py:148`) but `QCSynthesisAgent.execute` returns `consensus_report` (`impl/qc_synthesis_agent.py:71`), and the graph consumer reads `result.get("consensus_report")` (`graph/nodes/qc.py:107`); `failure-handling-agent` declares `failure_decision` (`mvp/__init__.py:162`) but returns `assembly_manifest` (`impl/assembly_agent.py:64`) which `graph/nodes/wrapup.py:30` consumes. **Mutation scenario:** add `"assembly_manifest"` to `failure-handling-agent`'s `output_artifacts`; nothing observable changes. The only production read of the field is `agents/registry.py:118-122`, and it is inert because `known_output_artifacts` defaults to `None` (`agents/registry.py:27`) — `if self.known_output_artifacts is None: return`. The two other sites, `agents/runner.py:468` and `agents/handoff.py:37`, are inside `HandoffManager`/`create_handoff`, which nothing in production calls (`grep -rn "create_handoff\|HandoffManager" src/` returns only the definitions plus the re-export at `agents/__init__.py:10`).
- **Reproduce:** (runs from any CWD — the module file is located with `inspect.getfile`, not by joining `cls.__module__` against the CWD, which raised `FileNotFoundError` in the version the verifier read)
  ```bash
  .venv/bin/python - <<'EOF'
  import ast, pathlib, inspect
  from film_pipeline.agents.mvp import MVP_AGENTS
  from film_pipeline.agents.impl.registry import AGENT_CLASS_BY_ID
  for a in MVP_AGENTS:
      cls=AGENT_CLASS_BY_ID[a.agent_id]; keys=set()
      for n in ast.parse(pathlib.Path(inspect.getfile(cls)).read_text()).body:
          if isinstance(n,ast.ClassDef):
              for m in n.body:
                  if isinstance(m,ast.FunctionDef) and m.name=='execute':
                      for r in ast.walk(m):
                          if isinstance(r,ast.Return) and isinstance(r.value,ast.Dict):
                              keys|={k.value for k in r.value.keys if isinstance(k,ast.Constant)}
      print(f"{a.agent_id:28} declared={a.output_artifacts} actual={sorted(keys)}")
  EOF
  ```
  Verified output at HEAD (`11` rows): `orchestrator-agent declared=['routing_decision'] actual=[]` (its `execute` returns `decision.model_dump()`, `impl/orchestrator_agent.py:69`, i.e. `action`/`feedback`/`preserve`/`reasoning`/`quality_score`/`critical_issues` — the dict-literal scan cannot see it, so the divergence is understated, not absent); `film-constitution-agent declared=['film_constitution'] actual=['constitution']`; `treatment-agent declared=['treatment','act_map','scene_list'] actual=['scene_list','treatment']`; `screenwriter-agent declared=['script','scene_intents'] actual=['script','story_bible']`; `reference-strategy-planner declared=['reference_strategy'] actual=['reference_index']`; `shot-design-agent declared=['shot_bible','master_film_matrix'] actual=['shot_matrix']`; `provider-planning-agent declared=['provider_plan'] actual=['cost_estimate','generation_requests','total_cost_usd','total_shots']`; `clip-validator declared=['validation_report'] actual=['consensus_report']`; `failure-handling-agent declared=['failure_decision'] actual=['assembly_manifest']`. Only `structure-extractor-agent` matches its declared set exactly; `intake-classifier-agent`, `treatment-agent` and `screenwriter-agent` each retain at least one declared key; the remaining seven share none.
- **Blast radius:** Every graph node that consumes an agent result (`prep.py:205,236,285-286`, `visual.py:50,115,438,495`, `qc.py:107`, `wrapup.py:30`), the MCP bible tools (`bibles/*.py`), and `_save_artifact` calls that pass `artifact_id` by hand. User-visible: the contract is not a contract — a reader of `MVP_AGENTS` is systematically misled about what each agent produces, and `requires_human_review`/handoff metadata built from it is empty in production.
- **Candidate owner module:** `agents.registry` — the descriptor row must carry the produced artifact key that the consumer asserts, and `BaseAgent`/`AgentDescriptor` should expose it so nodes stop hardcoding string keys.
- **Extraction sketch:** make the produced-artifact key a declared field (`produces: str`), assert `produces in result` inside `BaseAgent.run`, and replace `result.get("consensus_report")`-style literals with `result[descriptor.produces]`. Guard test: `for a in AGENTS: assert a.produces in get_agent_class(a.agent_id)(a).execute({...})` — or, minimally, a table test asserting `declared output_artifacts[0] == produces`.
- **Prior art:** `documentation/audit-findings.md:68` — "`agents/impl/registry.py` covers only 12 of 20 MVP agents and contains semantic mismaps (`failure-handling-agent` → `AssemblyAgent`, `clip-validator` → `QCSynthesisAgent`)". **New at HEAD:** the mismap survives into the *declared contract* ("failure_decision" / "validation_report"), the roster is now 11 not 20, and the prior note did not show that the contract field has **zero** production readers. Prior art confirmed still present.

### F-AGENT-03 — Registry agreement checks for KB domains and output artifacts are dead in production, and turning them on would reject 7 of 11 agents
- **Class:** O2 (duplicated invariant enforcement — declared but unexecuted)
- **Severity:** **High** (impact 3 × drift 4 = 12)
- **Concern:** Whether an agent's declared KB domains and output artifacts are drawn from the system's real vocabularies.
- **De-facto owners:**
  - `src/film_pipeline/agents/registry.py:118-122` — the check that never fires — `def _reject_unknown_output_artifacts(...)` / `if self.known_output_artifacts is None:` / `return`
  - `src/film_pipeline/agents/registry.py:104-106` — the warn path that never fires — `if self.known_kb_domains is None:` / `return`
  - `src/film_pipeline/agents/registry.py:26-27` — the allowlists default to `None` — `known_kb_domains: set[str] | None = None` / `known_output_artifacts: set[str] | None = None`
  - `src/film_pipeline/graph/services.py:40-41` — production construction passes neither — `registry = AgentRegistry()` / `registry.register_many(MVP_AGENTS)`
- **Drift proof:** Existing divergence, both vocabularies measured. `grep -rn "known_kb_domains\|known_output_artifacts" src/ tests/` shows assignments only in `tests/unit/agents/test_registry.py:96,113` (synthetic values `{"ops"}`, `{"script"}`) — production never sets them, so both guards are unreachable. Populating `known_output_artifacts` with the real `ArtifactType` vocabulary would **raise** for 7/11 MVP agents: `orchestrator-agent`→`routing_decision`, `intake-classifier-agent`→`classified_input`, `screenwriter-agent`→`scene_intents`, `structure-extractor-agent`→`execution_brief`, `reference-strategy-planner`→`reference_strategy`, `provider-planning-agent`→`provider_plan`, `failure-handling-agent`→`failure_decision` are all absent from `ArtifactType` (`schemas/_base.py`). Likewise 8 agent KB domains are absent from the manifest vocabulary: `camera`, `character`, `cost`, `creative-writing`, `dialogue`, `directing`, `tone`, `visual-design`. **Mutation scenario:** replace the first agent's `allowed_kb_domains=["operations", "governance"],` (`mvp/__init__.py:23`) with `allowed_kb_domains=["totally-made-up-domain"],`. Verified in a pristine `git archive HEAD` copy: `pytest tests/unit/agents tests/unit/graph` exits **0** (513 tests, 2 skipped) — nothing fails. No production construction passes an allowlist (`graph/services.py:40-41`), so `registry.py:104-106` returns before the check, and the only test that exercises the guard does so with a synthetic value (`tests/unit/agents/test_registry.py:96`: `AgentRegistry(known_kb_domains={"ops"})`).
- **Reproduce:** `.venv/bin/python -c "from film_pipeline.agents.mvp import MVP_AGENTS; from film_pipeline.schemas._base import ArtifactType; v={a.value for a in ArtifactType}; print({a.agent_id:[o for o in a.output_artifacts if o not in v] for a in MVP_AGENTS if [o for o in a.output_artifacts if o not in v]})"`
- **Blast radius:** `agents/registry.py` (its advertised invariants), `graph/services.py:36-42`, and every consumer that trusts `output_artifacts`/`allowed_kb_domains` — `agents/runner.py:127` renders `Allowed KB domains` into the prompt from these unchecked values, and `graph/_agent_routing.py:196-201` builds the KB context ref from them (`f"kbctx:{agent.agent_id}:{'+'.join(sorted(allowed))}"`). User-visible: prompts advertise KB domains that the KB manifest does not contain, and the `kbctx:` ref in artifact provenance names domains that resolve to nothing.
- **Candidate owner module:** `agents.registry` — own the two vocabularies by injecting the real domain set (from `KBManifest`) and the real artifact-type set (from `ArtifactType`) at construction, so registration fails fast.
- **Extraction sketch:** make `known_kb_domains` / `known_output_artifacts` **required** constructor arguments with no `None` default, populate them in `graph/services.py:36-42` from `KBManifest`/`ArtifactType`, and rename the 7 agent output keys + 8 KB domains to canonical values. Guard test: `AgentRegistry(known_kb_domains=..., known_output_artifacts=...).register_many(MVP_AGENTS)` must not raise.
- **Prior art:** `documentation/reviews/arch-lens-flexibility.md:21` notes for validators that "the 'registry' advertised by the design is fiction". **New at HEAD:** nobody has recorded that the *agent* registry has the same condition and that the real vocabularies would reject 7/11 rows.

### F-AGENT-04 — MCP bible generation is a second agent lifecycle: locally built contracts, inline prompts, and a real-model path that cannot work
- **Class:** O6 (parallel lifecycle — graph path vs MCP path) + O1 (duplicate contracts/prompts) + O5 (model profile re-hardcoded)
- **Severity:** **Critical** (impact 5 × drift 5 = 25)
- **Concern:** How an agent is constructed, prompted, and model-routed when invoked through MCP rather than the graph.
- **De-facto owners (graph path):**
  - `src/film_pipeline/graph/nodes/_agent.py:144` — graph path resolves a dedicated template — `template = prompt_registry.get_required(agent_id)`
  - `src/film_pipeline/graph/nodes/_agent.py:154-162` — and routes through the runner — `services.prompt_runner.run_from_template(`
  - `src/film_pipeline/agents/prompt_templates/defaults/production.py:85-87` — the same agent's registry template — `template_id="shot-bible-creator-v5",` / `agent_id="shot-design-agent",`
- **De-facto owners (MCP path):**
  - `src/film_pipeline/mcp/tools/bibles/shot.py:136-145` — a second, divergent contract for the same agent — `AgentRegistration(` / `agent_id="shot-design-agent",` / `capabilities=["shot_design", "matrix_planning"],`
  - `src/film_pipeline/mcp/tools/bibles/shot.py:182-190` — a hand-written prompt that bypasses the template registry — `raw = runner.model_adapter.chat(` … `model=runner.model_router.resolve("creative_writer"),`
  - `src/film_pipeline/mcp/tools/bibles/_shared.py:106` — the same bypass for camera/character/environment/style — `raw = runner.model_adapter.chat(prompt, model=runner.model_router.resolve("creative_writer"))`
  - `src/film_pipeline/mcp/tools/bibles/_shared.py:107` — a string reply can never satisfy this — `return raw if isinstance(raw, dict) else {}`
  - `src/film_pipeline/mcp/tools/bibles/camera.py:68-77` — the registration no roster knows about — `agent_id="camera-bible-agent",`
  - `src/film_pipeline/mcp/tools/bibles/camera.py:30`, `character.py:116`, `environment.py:111`, `style.py:39`, `shot.py:148` — a second mock-response authority alongside `app/mock_responses.py`
- **Drift proof:** Existing divergence plus two live defects.
  1. `ModelRouter` has no `resolve` method — its public methods are `select`, `resolve_or_raise`, `fallback`, `cost_ranked`, `list_profiles`, `resolve_model_params` (`agents/model_routing/__init__.py:86,98,112,122,133,136`). `grep -rn "\.resolve(" src/ --include=*.py` returns **16 lines / 17 occurrences**, nearly all of them `pathlib.Path.resolve` or unrelated resolvers (`app/safety.py:32,41,42,51,52,67,110`, `app/logging_setup.py:93,102`, `config/profile_resolver.py:68`, `mcp/resolution.py:81`, `reference_generation/context.py:131`, `reference_generation/outcomes.py:166` ×2, `testing/in_memory_git.py:74`). Filtering to the router is decisive: `grep -rn "model_router\.resolve(" src/` returns **exactly two** calls — `bibles/_shared.py:106` and `bibles/shot.py:189` — against the *correct* idiom at `mcp/tools/reference_generation/retry_loop.py:119` (`resolve_or_raise`). Under the **real** runtime the runner holds a `ModelAdapter` (`graph/services.py:102` `model_adapter=ModelAdapter(),`), not `None`, so the mock short-circuit at `_shared.py:104` does not apply and MCP bible real-model mode raises `AttributeError` before the request is made.
  2. Even if it did not, `ModelAdapter.chat` is annotated `-> str` (`agents/model_adapter.py:169,179`) and returns `str(msg.get("content") or "")` (`:206`), so `isinstance(raw, dict)` at `_shared.py:107` is always `False` and the function returns `{}` — every bible would be empty.
  3. `shot-design-agent` has two prompt sources (registry template v5 vs the inline f-string at `shot.py:183-189`) and two different capability/IO contracts (`mvp/__init__.py:114-127` vs `shot.py:136-145`).
  **Mutation scenario:** change `shot-bible-creator-v5`'s core task; the graph path changes, the MCP `generate_shot_bible` tool does not, and no test fails — the only bible tests (`tests/unit/mcp/tools/test_bibles.py`) run in mock mode, where `runner.model_adapter is None` short-circuits at `_shared.py:104`.
- **Reproduce:** `grep -rn "model_router.resolve(" src/film_pipeline/mcp/` and `grep -n "llm_enabled\|model_adapter" tests/unit/mcp/tools/test_bibles.py` (no `model_adapter` fixture appears in that file).
- **Blast radius:** five MCP tools (`generate_camera_bible`, `generate_character_bible`, `generate_environment_bible`, `generate_style_bible`, `generate_shot_bible`) registered at `mcp/tools/registry.py:203-236`; four `BaseAgent` subclasses (`CameraBibleAgent`, `CharacterBibleAgent`, `EnvironmentBibleAgent`, `StyleBibleAgent`) that no registry maps; artifact provenance stamped `created_by="mcp.generate_*"` — the four visual-dev tools pass the literal positionally into `_save_visual_dev_candidate` (`_shared.py:110-117`, param `created_by: str` at `:115`): `camera.py:95` `"mcp.generate_camera_bible"`, `character.py:199`, `environment.py:178`, `style.py:90`; `shot.py:82` passes it by keyword (`created_by="mcp.generate_shot_bible"`); `_shared.py:135` is the forwarding call `created_by=created_by,` — so MCP-produced bibles are distinguishable from graph-produced ones. User-visible: real-model bible generation is dead code that raises; in mock mode it silently produces hardcoded payloads from a second authority.
- **Candidate owner module:** `agents.registry` (+ `agents.prompt_templates`) — one descriptor per agent (id, class, contract, template, mock) consumed by both `graph/nodes/_agent.py` and `mcp/tools/bibles/*`, so the MCP tools call `PromptRunner.run_from_template` instead of building prompts by hand.
- **Extraction sketch:** register `camera-bible-agent`, `character-bible-agent`, `environment-bible-agent`, `style-bible-agent` in the roster with classes and templates; replace `_chat_json_or_mock` and `_request_matrix_output` with `run_from_template(..., model_profile=<descriptor profile>)`; delete the five local mock payload functions in favour of `default_mock_responses()`; add a guard test asserting every MCP bible tool resolves its agent through the registry and that no module under `mcp/` calls `model_adapter.chat(` directly.
- **Prior art:** `documentation/audit-findings.md:74` — "MCP bible real-mode calls `ModelRouter.resolve()`, which does not exist." **Still present at HEAD, unfixed, with no test added.** **New at HEAD:** the second defect at `_shared.py:107` (`chat` returns `str`), the divergent duplicate `AgentRegistration` for `shot-design-agent`, the four roster-invisible MCP-only agents, and the parallel mock authority.

### F-AGENT-05 — One prompt registry is keyed from two different id spaces, and 6 of 7 validator templates are unreachable
- **Class:** O4 (parallel registries must agree but nothing enforces agreement)
- **Severity:** **High** (impact 3 × drift 4 = 12)
- **Concern:** Which prompt template an agent or validator gets, and by what id.
- **De-facto owners:**
  - `src/film_pipeline/agents/prompt_templates/registry.py:69-71` — lookup keyed by **agent_id** — `def get(self, agent_id: str) -> PromptTemplate | None:` / `return self.templates.get(agent_id)`
  - `src/film_pipeline/validation/base.py:115` — the same dict, keyed by **validator_id** — `template = self._template_registry.get(agent_id=self.entry.validator_id)`
  - `src/film_pipeline/agents/prompt_templates/defaults/__init__.py:61-84` — two loaders into one dict — `reg.register(_intake_classifier())` … `reg.register(_script_structure_validator())`
  - `src/film_pipeline/agents/prompt_templates/registry.py:66-67` — collisions silently overwrite — `"""Register a template. Overwrites existing for same agent_id."""` / `self.templates[template.agent_id] = template`
  - `src/film_pipeline/graph/nodes/_context.py:20-24` vs `src/film_pipeline/graph/nodes/_agent.py:141` — two access paths to the same singleton (`_get_template_registry()` vs a direct `get_registry()` import)
- **Drift proof:** Existing divergence. `MVP_VALIDATORS` has 15 rows (`validation/validators/__init__.py:11-167`) but only 6 have templates (`scene-writing-validator`, `dialogue-voice-validator`, `prompt-readiness-validator`, `reference-usability-validator`, `scene-continuity-validator`, `assembly-validator`); `delivery-completeness-validator` has a template and an impl but no registry row. Independently, `llm_enabled = True` is set on exactly one class (`validation/impl/script_structure.py:129`); every other impl inherits `llm_enabled: bool = False` (`validation/base.py:36`), so even the 6 matching templates are only reachable for one validator. `PromptTemplate.template_id` (e.g. `"shot-bible-creator-v5"`) is never a lookup key anywhere — `grep -rn "template_id" src/` shows it is only returned for audit (`agents/runner.py:423`) and stored in `_routing_decisions` (`graph/nodes/_agent_handoff.py:140`). **Mutation scenario:** rename `_delivery_completeness_validator()`'s `agent_id` to `"delivery-validator"`; nothing fails — `grep -rn "delivery-completeness-validator" src/ tests/` matches only its own two definitions.
- **Reproduce:** `.venv/bin/python -c "from film_pipeline.validation.validators import MVP_VALIDATORS; from film_pipeline.agents.prompt_templates.registry import get_registry; t={x.agent_id for x in get_registry().templates.values()}; v={e.validator_id for e in MVP_VALIDATORS}; print('tpl-only',sorted(t-v-{'clip-validator','failure-handling-agent','film-constitution-agent','intake-classifier-agent','orchestrator-agent','provider-planning-agent','reference-strategy-planner','screenwriter-agent','shot-design-agent','structure-extractor-agent','treatment-agent'})); print('registry-only',sorted(v-t))"`
- **Blast radius:** `validation/base.py:108-153` (the only LLM validation path), `graph/nodes/qc.py:227` (injects the registry), `graph/subgraphs/qc.py:139-149` (injects services *without* the registry, so `_has_llm_services()` is `False` there). User-visible: a validator can be declared, implemented, and still silently run rule-only, or fail with `RuntimeError: No prompt template found for validator '…'` (`validation/base.py:117-119`) — caught and downgraded to the rule-based result by the bare `except Exception` at `:90-94`.
- **Candidate owner module:** `agents.prompt_templates` — one registry with an explicit, single `TemplateKey` (either agent_id or validator_id, not both) and a declared coverage invariant.
- **Extraction sketch:** give the registry two named accessors (`for_agent(agent_id)` / `for_validator(validator_id)`) backed by one dict with keys typed by the id space; assert at load time that every `MVP_VALIDATORS` id with a corresponding `llm_enabled` impl has a template and every template names a known id. Guard test: `test_mvp_invariants.py` style, parametrized over `MVP_VALIDATORS`.
- **Prior art:** `documentation/audit-findings.md:69` — "Dedicated prompt templates are missing for ~9 declared agents." **Still present at HEAD, now 9 of 15 validators.** **New at HEAD:** the dual-id-space keying and the `llm_enabled` gate that makes 6 of the 7 templates unreachable.

### F-AGENT-06 — Four RCTCO prompt renderers; the live validator renderer duplicates the template renderer and the runner branch is dead code
- **Class:** O2 (duplicated invariant enforcement — the prompt grammar)
- **Severity:** **High** (impact 3 × drift 3 = 9) — verdict **CONFIRMED with one dispute, now resolved**: drift-proof item 3 ("`schemas/prompt.py` is dead") was **false** and has been replaced with the accurate characterisation; the four divergent renderers (items 1–2) and the dead `prompt_runner.build` branch stand as verified.
- **Concern:** The RCTCO prompt grammar — which sections exist, in what order, and how placeholders are substituted.
- **De-facto owners:**
  - `src/film_pipeline/agents/runner.py:43-52` — renderer 1, the live graph path — `self.rendered = "\n\n".join([ f"# Role\n{self.role}", f"# Runtime Context\nCurrent date: {current_date}", …`
  - `src/film_pipeline/agents/prompt_templates/registry.py:43-55` — renderer 2, live template path — `parts = [ f"# Role\n{self.role}", … ]` … `text = text.replace(f"{{{key}}}", value)`
  - `src/film_pipeline/validation/base.py:161-173` — renderer 3, the live validator path — `if self._prompt_runner is not None:` / `return str(self._prompt_runner.build(template=template, context=context))` / … `parts.append(template.context_template.format_map(_SafeDict(context)))`
  - `src/film_pipeline/schemas/prompt.py:24-35` — renderer 4, dead — `def render(self) -> str:` with `f"Role: {self.r}\n\n"` … `f"Output Schema: {self.o_schema_ref or '(unspecified)'}"`
- **Drift proof:** Existing divergence plus a dead broken branch.
  1. Renderers 1 and 2 emit the same six `#`-prefixed sections but substitute differently (`replace` vs `format_map`); renderer 3 emits **four** sections with no `# Role` heading, in a different order, and drops `quality_instructions`; renderer 4 emits a fifth label format (`Role: …`, not `# Role`). Four grammars, one documented framework (`agents/prompt_templates/registry.py:1-10` names `film-knowledge-base/promt.md` the manual reference).
  2. `PromptRunner` has no `build` method — its builder is `build_rctco` (`agents/runner.py:86`). `grep -rn "\.build(" src/film_pipeline/agents/ src/film_pipeline/validation/` returns only `validation/base.py:162` (plus `validation/consensus.py:21`, an unrelated `ConsensusBuilder.build`). The branch is reachable only if a caller passes `prompt_runner=` to `set_services`; no production caller does (`grep -rn "set_services" src/` → `graph/nodes/qc.py:228` and `graph/subgraphs/qc.py:145`, neither passes `prompt_runner=`), so it would raise `AttributeError` if ever wired. `tests/unit/validation/test_base.py:319-327` exercises only the fallback arm (`_prompt_runner` stays `None`).
  3. `schemas/prompt.py:RCTCOPrompt`/`PromptRegistry`/`PromptRegistryEntry` are **not** production-wired: the only `src/` reference is the re-export at `schemas/__init__.py:108` (`"PromptRegistry"`/`"PromptRegistryEntry"`/`"RCTCOPrompt"` at `:223-231`), and nothing constructs them outside `schemas/prompt.py`. **Corrected after verification:** they are *not* unused — they are **schema-tested**, so deleting them is not free: `tests/unit/test_schemas.py:393-403` calls `RCTCOPrompt.render()`, `:408`/`:412` build `PromptRegistryEntry`, and `:1032-1037` build `PromptRegistry`. The correct characterisation is "dead in `src/` outside the `schemas` re-export, but pinned by `tests/unit/test_schemas.py`", not "dead".
  **Mutation scenario:** add a section to `PromptTemplate.render`; the validator LLM prompt (`validation/base.py:163-173`) and the generic `RCTCOPrompt` (`runner.py:43-52`) keep the old shape and no test compares them.
- **Reproduce:** `grep -rn "def build\b\|def build_rctco\|def render" src/film_pipeline/agents/ src/film_pipeline/validation/ src/film_pipeline/schemas/prompt.py`. Note this surfaces only renderers 2–4: **renderer 1 is `runner.py:43-52` inside `RCTCOPrompt.__post_init__`**, so it has no `def render` and must be read directly (verified: `runner.py:31 class RCTCOPrompt:`, `:43 self.rendered = "\n\n".join([...])`).
- **Blast radius:** every critical agent prompt (`graph/nodes/_agent.py:154`), every LLM validator prompt (`validation/base.py:129`), any future consumer of `schemas.prompt`. User-visible: prompt shape depends on which of four code paths renders it, and the validator prompt omits the Role heading and quality instructions that the agent prompt includes.
- **Candidate owner module:** `agents.prompt_templates` — one `render()` and one section grammar, consumed by the runner, the validator base, and any schema.
- **Extraction sketch:** retire `schemas/prompt.py:RCTCOPrompt.render` and `PromptRegistry*` (production-dead, but **schema-tested** — see drift-proof item 3 — so the move must also update `tests/unit/test_schemas.py:393,408,1032-1037` and the `schemas/__init__.py:108` re-export), make `RCTCOPrompt` wrap a `PromptTemplate` instead of re-assembling, and have `validation/base.py` call `template.render(**context)` rather than its local `format_map` fallback; delete the `self._prompt_runner.build(...)` branch. Guard test: a golden-render test asserting the template renderer and the validator prompt builder produce byte-identical output for a fixture template.
- **Prior art:** `documentation/reviews/arch-lens-flexibility.md:122` (prompt prose drift) is adjacent but does not cover the renderers. **New.**

### F-AGENT-07 — Model-output JSON recovery is implemented twice, with different strategy sets
- **Class:** O2 (duplicated invariant enforcement)
- **Severity:** **Medium** (impact 2 × drift 3 = 6)
- **Concern:** How a raw model reply is turned into a mapping.
- **De-facto owners:**
  - `src/film_pipeline/agents/_json_extraction.py:15-26` — four strategies — `for extract in (_parse_direct_json, _parse_fenced_json, _parse_braced_json, _parse_bracketed_json):`
  - `src/film_pipeline/agents/model_adapter.py:328` — agent path uses them — `extracted = extract_json_object(text)`
  - `src/film_pipeline/validation/base.py:206-234` — validator path re-implements three of them — `direct = _parse_json_dict_or_none(text)` … `for fence in ("```json", "```JSON", "```"):` … `brace_start = text.find("{")`
  - `src/film_pipeline/agents/impl/_model_output.py:16-29` — a third, independent unwrap for the bible agents — `for key in (artifact_key, "data", "output"):`
- **Drift proof:** Existing divergence. `_json_extraction` has a fourth strategy (`_parse_bracketed_json`, `:75-86`) that recovers array-wrapped responses via `dict(json.loads(candidate))`; `validation/base._parse_validation_response` has no equivalent and raises `ValueError` (`:231-234`) on the same input. Conversely the validator path tries three fence spellings in one loop (`:213`), while `_json_extraction` tries them in order with "last opening fence" semantics (`:39-51`). **Mutation scenario:** add a fifth recovery strategy to `_json_extraction.py`; validator LLM parsing is unaffected and no test fails, because `grep -rn "_parse_validation_response\|extract_json_object" tests/` shows they are tested independently.
- **Reproduce:** `grep -rn "extract_json_object\|_parse_validation_response\|normalize_model_output" src/ tests/ --include=*.py`
- **Blast radius:** `agents/model_adapter.py:300-335` (all agent JSON), `validation/base.py:206-234` (all validator JSON), `agents/impl/_model_output.py` (four bible agents). User-visible: the same malformed reply is accepted by one path and rejected by the other.
- **Candidate owner module:** `agents` (json recovery) — one recovery function with an injectable strategy list.
- **Extraction sketch:** move `_parse_validation_response` onto `extract_json_object` (the validator path already raises a good error at `:231`), and let `normalize_model_output` delegate its string branch to the same function. Guard test: table-driven test asserting every recovery strategy is reachable from both call sites.
- **Prior art:** new.

### F-AGENT-08 — Validator contracts live in three places; the runtime validator registry is never populated
- **Class:** O3 (split state authority) + O4 (parallel registries)
- **Severity:** **High** (impact 3 × drift 4 = 12)
- **Concern:** Which validators exist and with what thresholds, scopes, and model profiles.
- **De-facto owners:**
  - `src/film_pipeline/validation/validators/__init__.py:11` — declared roster, 15 rows — `MVP_VALIDATORS: list[ValidatorRegistryEntry] = [`
  - `src/film_pipeline/validation/impl/script_structure.py:131-141` — each impl hardcodes its own entry — `def __init__(self) -> None:` / `entry = ValidatorRegistryEntry(` / `blocking_conditions=["missing_scene_intent", "no_conflict", "scene_count_under_min"],`
  - `src/film_pipeline/validation/registry.py:16-24` — the runtime registry that would hold them — `class ValidatorRegistry:` / `self.entries[entry.validator_id] = entry`
  - `src/film_pipeline/graph/services.py:65` — never populated in production — `validator_registry: Any = None  # ValidatorRegistry`
  - `src/film_pipeline/graph/subgraphs/qc.py:45-52` — a fourth naming space for the same validators — `_VALIDATOR_MAP: dict[str, str] = { "script-structure": "ScriptStructureValidator", … }`
- **Drift proof:** Existing divergence, both sites cited: `scene-writing-validator.blocking_conditions` is `["missing_scene_intent","no_conflict","scene_count_under_min"]` in the implementation (`impl/script_structure.py:139`) and `["missing_scene_intent","no_conflict"]` in the declared roster (`validators/__init__.py:40`). `delivery-completeness-validator` has an impl entry (`impl/delivery_completeness.py:109`) but no roster row. Because `graph/services.py:65` is `None`, the runtime registry is populated only by tests — construction at `tests/unit/validation/test_registry.py:40` (`reg = ValidatorRegistry()`, with `register_many` on `:41`) and `tests/e2e/conftest.py:62` (`reg = ValidatorRegistry()`, with `register_many` on `:63`). **Mutation scenario:** delete a validator from `MVP_VALIDATORS`; the graph still runs its impl because `graph/subgraphs/qc.py` dispatches by the `_VALIDATOR_MAP` short key into a class map (`:125-136`), not through the registry, and no test fails.
- **Reproduce:** `.venv/bin/python -c "from film_pipeline.validation.validators import MVP_VALIDATORS; from film_pipeline.validation.impl import ScriptStructureValidator; m={e.validator_id:e for e in MVP_VALIDATORS}; e=ScriptStructureValidator().entry; print(e.blocking_conditions, m[e.validator_id].blocking_conditions)"`
- **Blast radius:** `validation/base.py` (`self.entry.thresholds` drives `score_to_status` at `:263`), `graph/subgraphs/qc.py:125-149`, `graph/nodes/qc.py:205-230`, `app/smoke.py:35-45` (which asserts `len(MVP_VALIDATORS) == 15` on a registry nothing reads). User-visible: a validator's blocking conditions can differ between the declared matrix and the code that enforces them, with no error.
- **Candidate owner module:** `validation.registry` — and the same pattern as F-AGENT-01/02: one descriptor per validator, injected into the impl rather than rebuilt in `__init__`.
- **Extraction sketch:** make `graph/services.py:36-42` build and store a `ValidatorRegistry` from `MVP_VALIDATORS`; have each impl accept its `ValidatorRegistryEntry` from that registry instead of constructing one; add a guard test that every `MVP_VALIDATORS` row has exactly one impl and that the impl's entry equals the row field-for-field.
- **Prior art:** `documentation/reviews/arch-lens-flexibility.md:21` ("each impl constructs its own `ValidatorRegistryEntry` inline") and the same row's "runtime `ValidatorRegistry` class exists but is **never populated**". **Still present at HEAD.** **New at HEAD:** the concrete field-level divergence (`scene_count_under_min`) and the fourth naming space (`_VALIDATOR_MAP` short keys).

### F-AGENT-09 — Agent naming drifts into the KB manifest and KB defaults, silently starving agents of KB items
- **Class:** O4 (parallel registries must agree)
- **Severity:** **High** (impact 3 × drift 5 = 15)
- **Concern:** The set of agent names the KB layer recognizes as matching a real agent.
- **De-facto owners:**
  - `film-knowledge-base/index/kb-manifest.yaml:162-163` — names no roster agent — `applies_to_agents: [generation-agent, qc-agent]` (also `:62` `applies_to_agents: [generation-agent, provider-agent]`, `:178` `orchestrator`; note `:30` is `[prompt-composition-agent, generation-agent]`, which an earlier draft mis-cited as the `provider-agent` anchor)
  - `src/film_pipeline/kb/retrieval.py:51-54` — the filter that drops them — `if agent_id is not None:` / `items = [ i for i in items if "all" in i.applies_to_agents or agent_id in i.applies_to_agents ]`
  - `src/film_pipeline/kb/packets.py:87-90` — the filter is on the live path — `retrieved = retrieval.for_task(phase=phase, agent_id=agent_id,)`
  - `src/film_pipeline/kb/retrieval.py:20` — a phantom default in the docstring example — `items = retrieval.for_task(phase="generation", agent_id="generation-agent")`
  - `src/film_pipeline/mcp/tools/kb.py:99` — a near-miss default — `agent_id=str(args.get("agent_id", "orchestrator")),`
- **Drift proof:** Existing divergence, measured. The canonical agent for generation planning is `provider-planning-agent` (`mvp/__init__.py:129`), but the manifest tags generation items with `generation-agent` / `provider-agent`, which no source declares. `.venv/bin/python -c "from pathlib import Path; from film_pipeline.kb.manifest import KBManifest; m=KBManifest.from_yaml(Path('film-knowledge-base/index/kb-manifest.yaml')); print(len(m.by_agent('provider-planning-agent')), len(m.by_agent('generation-agent')), len(m.by_agent('clip-validator')), len(m.by_agent('qc-agent')))"` → `4 11 4 5`. **Mutation scenario:** rename `qc-agent` → `clip-validator` in the manifest; nothing tests the rename and no test fails today either way, because the KB tests never assert that a manifest agent token resolves to a registered agent id.
- **Reproduce:** `grep -rn "applies_to_agents" film-knowledge-base/index/kb-manifest.yaml` and `grep -rn "\"orchestrator\"\|generation-agent\|qc-agent\|provider-agent" src/`
- **Blast radius:** `kb/retrieval.py`, `kb/packets.py`, `graph/services.py:111-134` (`kb_for`), `graph/nodes/_agent.py:105-121` (`_open_kb_session` passes the canonical `routing.agent_id`), `mcp/tools/kb.py:95-102`. User-visible: up to 7 of 11 generation-tagged KB items never reach the agent that plans generation, and `kb_get_context_packet`'s default `"orchestrator"` matches 5 items that the canonical `"orchestrator-agent"` does not (`m.by_agent('orchestrator')` = 5 vs `m.by_agent('orchestrator-agent')` = 4).
- **Candidate owner module:** `agents.registry` — export the canonical agent-id set; `kb` validates `applies_to_agents` against it at manifest load.
- **Extraction sketch:** add a manifest-load assertion (or a guard test) that every non-`all` token in `applies_to_agents` is a registered agent id, fix the manifest tokens to canonical ids, and delete the `"generation-agent"` docstring example. Depends on F-AGENT-03 making the id set authoritative.
- **Prior art:** `docs/modular-architecture/audit/09-kb-context-and-provenance.md` owns the KB side of this seam. **New here:** the agent-name half — the manifest's `applies_to_agents` vocabulary has no relationship to any roster, and the item counts prove the loss.

### F-AGENT-10 — No reverse-direction roster guard, so orphan ids and a duplicate schema survive
- **Class:** O4 (parallel registries) + O1 (duplicated normative model)
- **Severity:** **High** (impact 2 × drift 5 = 10)
- **Concern:** Whether every declared agent id corresponds to a real agent, and whether there is one schema for an agent registration.
- **De-facto owners:**
  - `src/film_pipeline/agents/impl/registry.py:26` — orphan alias — `"visual-dev-agent": VisualDevAgent,`
  - `src/film_pipeline/graph/nodes/_context.py:35-51` — orphan profile rows — `"character-dossier-agent": "creative_writer",` … `"kb-curator-agent": "operations_triage",`
  - `src/film_pipeline/graph/_agent_routing.py:52` — silent fallback for unknown phases — `return _PHASE_DEFAULT_AGENTS.get(phase, "orchestrator-agent")`
  - `src/film_pipeline/schemas/registries/agent_registry.py:10-28` — a second registration schema for the same concept — `class AgentRegistryEntry(SchemaBase):` sharing **12** fields with `AgentRegistration` (`schemas/handoff.py:39-53`: `agent_id`, `family`, `role`, `capabilities`, `input_artifacts`, `output_artifacts`, `allowed_kb_domains`, `blocked_kb_domains`, `prompt_framework`, `default_model_profile`, `reviewed_by`, `failure_modes`) and adding a 13th, `enabled: bool = True`
  - `tests/unit/agents/test_mvp_invariants.py:38-69` — the only roster guard, forward only — `@pytest.mark.parametrize("agent", MVP_AGENTS, ids=lambda a: a.agent_id)`
- **Drift proof:** Existing divergence: `AGENT_CLASS_BY_ID` has 12 keys while `MVP_AGENTS` has 11, and the extra one (`visual-dev-agent`) is unreachable through normal routing, returning `{"status": "agent_not_found"}` (`graph/nodes/_agent.py:211-212`). `_AGENT_PROFILE_MAP` has 21 keys, 10 of which name no registered contract. `_PHASE_DEFAULT_AGENTS` covers 9 of the 11 `PHASE_ORDER` phases (`graph/_action_routing.py:18` lists `… 'generation', 'qc', 'post', 'delivery'`), so `generation` and `delivery` silently route to `orchestrator-agent`. `schemas/registries/agent_registry.py:AgentRegistryEntry` is referenced only by `schemas/registries/__init__.py:5`, `schemas/__init__.py:121` and `tests/unit/test_schemas.py:110,985` — no production consumer. **Mutation scenario:** delete `"reference-strategy-planner": VisualDevAgent` from `AGENT_CLASS_BY_ID`; `test_mvp_invariants.py:39-42` fails (good), but deleting `"visual-dev-agent"` from the same dict fails nothing, and adding a 22nd orphan to `_AGENT_PROFILE_MAP` fails nothing — both directions are unguarded.
- **Reproduce:** `.venv/bin/python -c "from film_pipeline.agents.mvp import MVP_AGENTS; from film_pipeline.agents.impl.registry import AGENT_CLASS_BY_ID; from film_pipeline.graph.nodes._context import _AGENT_PROFILE_MAP as M; from film_pipeline.schemas.registries.agent_registry import AgentRegistryEntry; m={a.agent_id for a in MVP_AGENTS}; print('class-only',sorted(set(AGENT_CLASS_BY_ID)-m)); print('profile-only',sorted(set(M)-m))"` and `.venv/bin/python -c "from film_pipeline.graph._action_routing import PHASE_ORDER; from film_pipeline.graph._agent_routing import _PHASE_DEFAULT_AGENTS as D; print([p for p in PHASE_ORDER if p not in D])"`
- **Blast radius:** `graph/nodes/_agent.py:96-102` (`contract=None` / `impl=None` early returns), `graph/_agent_routing.py:50-52`, `schemas/__init__.py`. User-visible: two registrations of the same concept can diverge (one carries `enabled`, one does not), and a dormant profile row looks load-bearing to the next reader.
- **Candidate owner module:** `agents.registry` — one `AGENTS` descriptor table plus a reverse-direction guard test; `schemas` keeps exactly one registration model.
- **Extraction sketch:** add reverse guards first (`set(AGENT_CLASS_BY_ID) - mvp_ids ⊆ {documented aliases}` and likewise for `_AGENT_PROFILE_MAP`, `_PHASE_DEFAULT_AGENTS` keys ⊇ `PHASE_ORDER`), delete the orphans, and delete `AgentRegistryEntry` in favour of `AgentRegistration`. Guard test file: `tests/unit/agents/test_registry_agreement.py` (new).
- **Prior art:** `documentation/reviews/arch-lens-flexibility.md:37` documents the `visual-dev-agent` alias, the 21-id profile map with ≥9 orphans, the forward-only guard, and the vacuous uniqueness assertion. **Still present at HEAD, unchanged** (the counts are now exactly 12 / 21 / 10 orphans). **New at HEAD:** the duplicate `AgentRegistryEntry` schema, the `PHASE_ORDER` → `_PHASE_DEFAULT_AGENTS` gap, and the measured orphan count.

### F-AGENT-11 — Per-agent prompt policy is re-derived by hardcoded identity branches at the call site *(added after verification — `reviews/verify-04.md` §Missed in scope 1)*
- **Class:** O5 (policy-by-branch)
- **Severity:** **High** (impact 2 × drift 5 = 10)
- **Concern:** Whether an agent gets the extra prompt context it needs — phase context, script scene count — and who owns that per-agent decision.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/_agent_prompt_context.py:94` — branch 1 — `if agent_id == "orchestrator-agent":` / `context_vars.update(_build_phase_context(state))`
  - `src/film_pipeline/graph/nodes/_agent_prompt_context.py:148` — branch 2 — `if agent_id == "structure-extractor-agent" and context_vars.get("script_content"):` / `_set_script_scene_count(context_vars)`
  - `src/film_pipeline/graph/nodes/_agent_prompt_context.py:136-149` — the layering function that hardcodes both — `_render_constraint_block(...)` / `_maybe_add_orchestrator_context(context_vars, state, agent_id)` / `_attach_scoped_packet(...)` / `_attach_validator_issues(...)`
  - `src/film_pipeline/graph/nodes/_agent.py:146,150` — the only caller — `context_vars = _build_template_context(state, kb)` / `_augment_phase_context(context_vars, state, services, phase, agent_id)`
  - `src/film_pipeline/agents/prompt_templates/defaults/spine.py:12-15,40,59` — the template that *declares* it needs the variable — `def _structure_extractor() -> PromptTemplate:` / `agent_id="structure-extractor-agent",` / `"   - The script has {script_scene_count} scenes; the total must be "` — i.e. `{script_scene_count}` is a template variable wired to a branch, not a contract field
- **Drift proof:** Mutation scenario, verified by absence of coverage: `grep -rn -e "_agent_prompt_context" -e "_maybe_add_orchestrator_context" tests/ --include=*.py` returns **nothing** — the module is not referenced by any test. So adding a third identity branch (or deleting either existing one) fails no test; and a new roster agent whose template declares `script_scene_count` silently renders the placeholder unfilled, because nothing connects a template's required variables to a branch list. The branch is also invisible to `AGENTS`: neither `MVP_AGENTS` nor `_AGENT_PROFILE_MAP` records "this agent needs phase context".
- **Reproduce:** `grep -rn -e "_maybe_add_orchestrator_context" -e "_set_script_scene_count" src/ tests/ --include=*.py`
- **Blast radius:** `graph/nodes/_agent.py:146-150` (every graph agent prompt), and indirectly every prompt built for `orchestrator-agent` / `structure-extractor-agent`. User-visible: prompt context is assembled by an if-chain that a descriptor table cannot express and no test constrains — a re-named or new agent silently loses its augmentation, degrading prompt quality with no error.
- **Candidate owner module:** `agents.registry` — make augmentation a declarative field on the descriptor (`context_augmenters: tuple[str, ...]`, e.g. `("phase_context",)`, `("script_scene_count",)`), so `_augment_phase_context` iterates the descriptor instead of naming ids.
- **Extraction sketch:** replace the two `if agent_id == ...` branches with a lookup `for augmenter in AGENTS[agent_id].context_augmenters: _AUGMENTERS[augmenter](context_vars, state, services, phase)`; add a guard test asserting every `{placeholder}` a template requires is either a base context var or supplied by a declared augmenter.
- **Prior art:** none found. **New; the verifier's independent pass found it — this audit's §1.3 coverage table had tagged the file as "F-AGENT-05 supporting", but F-AGENT-05 never cites it, so the seam was claimed as covered without being analysed. Corrected above.**

### F-AGENT-12 — `_AGENT_PROFILE_MAP` carries validator ids with contradicting model profiles (2 of 2 rows disagree with the validator roster) *(added after verification — `reviews/verify-04.md` §Missed in scope 2)*
- **Class:** O1 (duplicated normative model) + O3 (split state authority)
- **Severity:** **High** (impact 3 × drift 4 = 12)
- **Concern:** Which model profile a validator actually runs with when the same validator id is declared in both the agent-profile map and the validator roster — with different values.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/_context.py:41` — the agent-side map says text — `"scene-continuity-validator": "strict_validator",`
  - `src/film_pipeline/graph/nodes/_context.py:42` — same, second row — `"full-movie-flow-validator": "strict_validator",`
  - `src/film_pipeline/validation/validators/__init__.py:131` — the declared validator roster says multimodal — `model_profile="multimodal_reviewer",`
  - `src/film_pipeline/validation/validators/__init__.py:151` — likewise for the other id — `model_profile="multimodal_reviewer",`
  - `src/film_pipeline/validation/impl/scene_continuity.py:217` — the implementation's own entry, the one actually read, says multimodal — `model_profile="multimodal_reviewer",`
  - `src/film_pipeline/validation/base.py:122-125` — the runtime consumer of whichever entry wins — `profile = self.entry.model_profile` / `model = self._router.resolve_or_raise(profile)`
- **Drift proof:** Existing divergence, both rows measured: the two validator ids present in `_AGENT_PROFILE_MAP` (`scene-continuity-validator`, `full-movie-flow-validator`) are declared `strict_validator` there and `multimodal_reviewer` in the validator roster, and nothing compares them. The profile definitions differ materially (`agents/model_routing/__init__.py:27,57`). Today the implementation's self-built entry wins only because `graph/services.py:65` leaves the runtime validator registry `None` (F-AGENT-08) — so **fixing F-AGENT-08 by populating the registry would flip these validators' profiles to whichever authority the fix chooses**, with no test failing either way. `grep -rn "_AGENT_PROFILE_MAP" tests/ --include=*.py` shows the map is pinned only for *agent* ids (`tests/unit/graph/test_agent_profile_routing.py:11-27`) plus the membership guard at `:35-40` — never for a validator row. Mutation scenario: change `_context.py:41` or `:42` to `"text_validator"`; no test fails.
- **Reproduce:** `grep -rn "scene-continuity-validator\|full-movie-flow-validator" src/ --include=*.py` and `.venv/bin/python -c "from film_pipeline.graph.nodes._context import _AGENT_PROFILE_MAP as M; from film_pipeline.validation.validators import MVP_VALIDATORS; v={e.validator_id:e.model_profile for e in MVP_VALIDATORS}; print({k:(M[k],v[k]) for k in set(M)&set(v)})"` → `{'full-movie-flow-validator': ('strict_validator','multimodal_reviewer'), 'scene-continuity-validator': ('strict_validator','multimodal_reviewer')}`
- **Blast radius:** `validation/base.py:122-125` (the model actually used for scene-continuity and full-movie-flow LLM validation), `graph/nodes/_context.py:27-52` (a 21-row map containing validator ids that the graph path never routes, one of which — `full-movie-flow-validator` — has neither an impl entry nor a prompt template, §2.3f). User-visible: a validator's model/temperature depends on which of three tables is consulted; the map rows are a latent trap that an F-AGENT-08 fix would trip.
- **Candidate owner module:** `agents.registry` (profile authority) + `validation.registry` (validator entry) — the validator's profile must come from its registered entry, and `_AGENT_PROFILE_MAP` must contain agent ids only.
- **Extraction sketch:** drop validator ids from `_AGENT_PROFILE_MAP` (they belong to `MVP_VALIDATORS`/the entry), add a guard test asserting the map's keys are exactly the agent ids, and assert `impl.entry == registry_row` for every validator (already proposed as F-AGENT-08's guard).
- **Prior art:** `documentation/reviews/arch-lens-flexibility.md:16` names the three parallel per-agent tables; this is the first recorded *value* divergence for a validator id. **New.**

### F-AGENT-13 — The router's capability-classification sets share zero tokens with the roster, and the only argument that reads them is supplied by no caller in `src/` or `tests/` *(added after verification — `reviews/adversarial-coverage.md` §H4)*
- **Class:** O4 (parallel registries) + O5 (policy-by-branch)
- **Severity:** **High** (impact 2 × drift 5 = 10). The coverage pass scored the hole qualitatively (O4 + O5) without arithmetic; this is the §1.5 rubric applied: the branch is unreachable today (no deliverable impact → impact 2), but no test can fail when either vocabulary changes (drift 5).
- **Concern:** Which declared agent capability counts as "review" or "repair" work, and whether that classification is ever consulted.
- **De-facto owners:**
  - `src/film_pipeline/graph/_agent_routing.py:31` — the router's private review vocabulary — `_REVIEW_CAPABILITIES = {"review", "validation", "qc", "inspecting"}`
  - `src/film_pipeline/graph/_agent_routing.py:32` — the router's private repair vocabulary — `_REPAIR_CAPABILITIES = {"repair", "revision", "replan", "correcting"}`
  - `src/film_pipeline/agents/mvp/__init__.py:15` — the roster whose `capabilities` these sets are meant to classify — `MVP_AGENTS: list[AgentRegistration] = [`
  - `src/film_pipeline/agents/mvp/__init__.py:20` — the vocabulary an agent actually declares — `capabilities=["flow_routing", "arbitration", "phase_transition"],`
  - `src/film_pipeline/graph/_agent_routing.py:57,59` — the only reads of the sets — `if preferred_capability in _REPAIR_CAPABILITIES:` / `if preferred_capability in _REVIEW_CAPABILITIES:`
  - `src/film_pipeline/graph/_agent_routing.py:175,177` — the branches they decide — `if task_type == "repair" or preferred_capability in _REPAIR_CAPABILITIES:` / `if task_type == "review" or preferred_capability in _REVIEW_CAPABILITIES:`
  - `src/film_pipeline/graph/nodes/_agent.py:86` — the sole production caller — `route_result = route_agent(`
  - `src/film_pipeline/graph/nodes/_agent.py:91` — it passes an agent id, never a capability — `preferred_agent_id=agent_id if task_type == "create" else None,`
  - `src/film_pipeline/graph/nodes/_agent.py:193` — and it inherits `task_type`'s create default — `task_type: str = "create",`
  - `src/film_pipeline/agents/registry.py:43` — the accessor the dead sets shadow and duplicate — `def lookup_by_capability(self, capability: str) -> list[AgentRegistration]:`
  - `tests/unit/graph/test_create_path_routing.py:63` — a test that reaches the review arm only by supplying `task_type` itself — `task_type="review",`
  - `tests/unit/graph/test_services.py:126` — likewise for the review/`no_impl` path — `result = _run_agent(state, "custom-review-agent", "script", "task", task_type="review")`
- **Drift proof:** Existing divergence: the roster declares **30** distinct capabilities, the union of the router's two sets is **8** tokens, and the intersection is **empty** — all 8 routing tokens are declared by no agent and all 30 declared capabilities are unclassified (first command in `Reproduce`). The eight tokens are a redundant *synonym* layer, not a broken lookup: `_normalized_task_type` (`:55-61`) rewrites `task_type` before the branch checks, so `preferred_capability="review"` does reach the reviewer (`clip-validator`) and `"repair"` the operator (`failure-handling-agent`). The residual harm is the vocabulary's invisibility — nothing compares the 8 router tokens with the 30 declared capabilities, so a token taken from either vocabulary silently does nothing in the other — together with the decision-dead disjuncts and the `task_type` override recorded in `Blast radius`. **Mutation scenario (silent):** replacing `_REVIEW_CAPABILITIES` with `{"no_such_capability"}` and `_REPAIR_CAPABILITIES` with `{"also_fake"}` in a pristine `git archive fb85baa` copy and running `PYTHONPATH=<copy>/src pytest tests/unit -o addopts=""` exits **0** — `1866 passed, 3 skipped`. Nothing fails because `preferred_capability` has **zero** callers anywhere: `grep -rn "preferred_capability" src/ tests/ --include=*.py` returns 11 lines, all inside `_agent_routing.py` (the parameter, its docstring, its two membership tests, the two `route_agent` branches). **The tests pin behaviour production cannot reach.** The review/repair arms *are* genuinely constrained — deleting the `task_type` disjuncts at `_agent_routing.py:175,177` fails `test_review_and_repair_paths_ignore_preferred_agent` (`tests/unit/graph/test_create_path_routing.py:67`) — but only because tests pass `task_type="review"`/`"repair"` by hand (`test_create_path_routing.py:59-76`, `test_services.py:126`). No production `_run_agent(...)` call site passes `task_type` (all 11 omit it; the only `task_type=` in `src/` is the forwarding site `graph/nodes/_agent.py:89`), so every production routing decision is `"create"` and the arms never run. The suite therefore certifies routing paths the shipped system never executes, while the capability disjunct it also depends on is asserted by no test at all.
- **Reproduce:**
  ```bash
  cd ${REPO_ROOT}
  UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
  from film_pipeline.agents.mvp import MVP_AGENTS
  from film_pipeline.graph._agent_routing import _REVIEW_CAPABILITIES as R, _REPAIR_CAPABILITIES as P
  caps = set().union(*[set(a.capabilities) for a in MVP_AGENTS])
  print('roster caps', len(caps), '| routing tokens', len(R|P), '| intersection', sorted((R|P)&caps))
  print('routing tokens in no agent:', sorted((R|P)-caps))
  "
  grep -rn "preferred_capability=" src/ tests/ --include=*.py | grep -v _agent_routing.py || echo "no caller passes preferred_capability"
  grep -rn "task_type=" src/film_pipeline/graph/nodes/ --include=*.py
  UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
  from film_pipeline.agents.mvp import MVP_AGENTS
  from film_pipeline.agents.registry import AgentRegistry
  from film_pipeline.graph._agent_routing import route_agent
  reg = AgentRegistry(); reg.register_many(MVP_AGENTS)
  s = {'project_id': 'p', 'current_phase': 'script'}
  for c in ['review', 'repair', 'qc', 'validation', 'arbitration', 'no_such']:
      r = route_agent(s, phase='script', registry=reg, preferred_capability=c)
      print(f'{c:12} -> {r.agent_id:22} {r.routing_reason}')
  r = route_agent(s, phase='script', task_type='repair', registry=reg, preferred_capability='review')
  print('repair+review ->', r.agent_id, '|', r.routing_reason)
  "
  ```
  Output at `fb85baa`:
  ```
  roster caps 30 | routing tokens 8 | intersection []
  routing tokens in no agent: ['correcting', 'inspecting', 'qc', 'repair', 'replan', 'review', 'revision', 'validation']
  no caller passes preferred_capability
  src/film_pipeline/graph/nodes/_agent.py:89:        task_type=task_type,
  review       -> clip-validator         review path for phase 'script'
  repair       -> failure-handling-agent repair path for phase 'script' after validation failure
  qc           -> clip-validator         review path for phase 'script'
  validation   -> clip-validator         review path for phase 'script'
  arbitration  -> orchestrator-agent     selected by capability 'arbitration' for phase 'script'
  no_such      -> screenwriter-agent     create path for phase 'script' — using default agent
  repair+review -> clip-validator | review path for phase 'script'
  ```
- **Blast radius:** `graph/_agent_routing.py:55-61,170-186` (both membership tests, `_normalized_task_type`, `_capability_route`), `graph/nodes/_agent.py:84-92,187-210` (the only `route_agent` caller and all 11 `_run_agent` call sites), `agents/registry.py:40-56` (`lookup_by_capability`). User-visible: **none today** — and the three residual harms are all latent, which is why impact is 2, not 3:
  1. **A parallel 8-token capability vocabulary that intersects the 30 registry capabilities in the empty set.** `_REVIEW_CAPABILITIES`/`_REPAIR_CAPABILITIES` act as a private synonym layer for the task-type strings, so the router's notion of a review/repair capability is decoupled from the roster; a future author who writes a token from the roster's vocabulary (e.g. `clip_quality`, `identity_consistency`) into these sets, or one of these tokens into a contract's `capabilities`, gets no error and no effect — because nothing compares the two vocabularies.
  2. **The `preferred_capability in …` disjuncts at `_agent_routing.py:175,177` are decision-dead for every production call.** `_normalized_task_type` (`:170`) rewrites `task_type` before the branch is read, and no production call supplies either argument: all 11 `_run_agent(...)` call sites omit `task_type` (the only `task_type=` in `src/` is the forwarding site `graph/nodes/_agent.py:89`) and `preferred_capability` has no caller in `src/` or `tests/`.
  3. **`preferred_capability` silently overrides an explicit `task_type`** — the combination a future caller is most likely to write. `_normalized_task_type` (`:55-61`) tests `preferred_capability` before `task_type`, so `task_type="repair"` + `preferred_capability="review"` yields the *review* path (`clip-validator`, reason `"review path for phase 'script'"`) and `task_type="review"` + `preferred_capability="repair"` yields the *repair* path (`failure-handling-agent`) — the caller's explicit intent is discarded without a warning. What is **not** a harm: the eight tokens resolve correctly — `"review"`/`"qc"`/`"validation"`/`"inspecting"` select `clip-validator`, `"repair"`/`"revision"`/`"replan"`/`"correcting"` select `failure-handling-agent` — and a genuine roster capability such as `"arbitration"` reaches `_capability_route` and selects `orchestrator-agent`; only a token in neither vocabulary falls through to the phase default.
- **Candidate owner module:** `agents.registry` — own one closed `Capability` vocabulary on the descriptor table and validate it at registration (mirroring the existing `model_profile` check at `agents/registry.py:78`); `graph/_agent_routing.py` classifies by the declared `role`/`capabilities`, not by a private synonym set.
- **Extraction sketch:** delete `_REVIEW_CAPABILITIES`/`_REPAIR_CAPABILITIES`; express the two documented task types as `AgentRole` selectors (the `AgentRole` enum has `REVIEWER`/`VALIDATOR`/`OPERATOR`; the roster already claims `VALIDATOR` via `clip-validator` and `OPERATOR` via `failure-handling-agent` — §5 records that `REVIEWER` is unclaimed — and `lookup_by_role` already implements this at `_agent_routing.py:79-113`) or as members of a `Capability` enum exported by `agents.registry`; add the register-time vocabulary check and a guard test asserting every routing token is a capability some `MVP_AGENTS` row declares. Because the seam is dormant, pair it with prior art Finding 8's dormancy guard (`documentation/reviews/arch-lens-flexibility.md:93-94`) — fail the build when a `route_agent` arm has no non-test caller and no declared activation — before any caller starts trusting it.
- **Prior art:** `documentation/reviews/arch-lens-flexibility.md:121` (extension-cost matrix row 4, "Agent capability tokens") already names both sets and the "typo'd capability routes nowhere … no vocabulary check at register time" risk; `:88-97` (Finding 8, "Dormant capability is unmarked and rotting invisibly") already records that all production `_run_agent` call sites omit `task_type`, so the review/repair/capability arms execute only from tests — Finding 8 says **12** sites, but the count at `fb85baa` is **11** (`wrapup.py:24`, `qc.py:97`, `prep.py:58,195,226,275`, `approval.py:34`, `visual.py:39,105,426,600`), and this finding uses the measured 11 rather than repeating the prior art's 12. **New at HEAD:** (i) the mismatch is not typo-proneness but a measured **empty** intersection — 0 of 8 routing tokens are declared by any of the 30 roster capabilities; (ii) `preferred_capability` has zero callers in `src/` *and* `tests/`, so Finding 8's "execute only from `tests/integration/test_dynamic_routing.py`" is stale — that file exercises `compute_actions`/`after_phase`, not `route_agent`; (iii) the tests that do pin the arms hand-supply `task_type`, certifying paths production cannot reach. **Within audit 04 this is a distinct seam, not an extension:** F-AGENT-02/03/10 cover output-artifact, KB-domain and model-profile agreement, while `_REVIEW_CAPABILITIES`/`_REPAIR_CAPABILITIES` appear in **zero** audit files (§2.4 and §5 record only the absence of an agreement guard).
- **Provenance:** uncovered by the adversarial coverage pass (`reviews/adversarial-coverage.md` §H4); added post-verification.


---

## 4. Ownership map

| Concern | De-facto owners | Single / distributed |
|---|---|---|
| Which agents exist (the roster) | `agents/mvp/__init__.py:15`; `agents/impl/registry.py:18`; `graph/_agent_routing.py:35`; `mcp/tools/bibles/{camera,character,environment,style,shot}.py`; `film-knowledge-base/index/kb-manifest.yaml` | **Distributed (5+ owners)** — F-AGENT-04, 10 |
| What an agent can do (`capabilities`) | `agents/mvp/__init__.py`; duplicated per-`AgentRegistration` in `mcp/tools/bibles/*.py` | **Distributed (2)** — F-AGENT-04 |
| What an agent produces | `agents/mvp/__init__.py:22-162` (declared, unread); each `impl/*.py` `execute()` (actual); each `graph/nodes/*.py` consumer (hardcoded key) | **Distributed (3)** — F-AGENT-02 |
| Which model profile an agent uses | `agents/mvp/__init__.py` `default_model_profile` (validated, unread); `graph/nodes/_context.py:27` `_AGENT_PROFILE_MAP` (authoritative) | **Distributed (2), with an existing value divergence** — F-AGENT-01 |
| Which prompt an agent gets | `agents/prompt_templates/defaults/*.py` (registry); inline f-strings in `mcp/tools/bibles/{camera,style,shot}.py` | **Distributed (2)** — F-AGENT-04 |
| Prompt template lookup key | `prompt_templates/registry.py:69` (agent_id); `validation/base.py:115` (validator_id) into the same dict | **Distributed (2 id spaces)** — F-AGENT-05 |
| Actual model id / sampling params | `agents/model_routing/__init__.py:18` `_FALLBACK_PROFILES`; `profiles/base.studio.yaml:43` `model_profiles` | **Distributed (2) — not this cluster.** Attributed to `audit/03-config-profile-and-defaults.md` **F-CFG-01** (corrected after verification); this document records it only as the target reached by the profile *name* an agent picks (F-AGENT-01) |
| Model name hardcoded in the MCP bible path | `mcp/tools/bibles/_shared.py:106` and `shot.py:189` — the literal `"creative_writer"` | **Single literal, two sites, bypasses the profile table** — F-AGENT-04 |
| Mock/canned responses | `app/mock_responses.py:97`; `mcp/tools/bibles/*_mock_payload` / `_fallback_matrix_output` | **Distributed (2)** — F-AGENT-04 |
| Agent-registration schema | `schemas/handoff.py:39` `AgentRegistration` (live); `schemas/registries/agent_registry.py:10` `AgentRegistryEntry` (dead) | **Distributed (2)** — F-AGENT-10 |
| Which validators exist and their thresholds | `validation/validators/__init__.py:11`; per-impl `__init__` entries; `graph/subgraphs/qc.py:45` `_VALIDATOR_MAP`; `validation/registry.py` (unpopulated) | **Distributed (4)** — F-AGENT-08 |
| Model-output parsing (JSON recovery) | `agents/_json_extraction.py:15`; `validation/base.py:206`; `agents/impl/_model_output.py:16` | **Distributed (3)** — F-AGENT-07 |
| RCTCO prompt grammar | `agents/runner.py:41`; `prompt_templates/registry.py:33`; `validation/base.py:155`; `schemas/prompt.py:24` (production-dead, schema-tested) | **Distributed (4)** — F-AGENT-06 |
| Agent roles / families enum | `schemas/_base.py:93-120` | **Single owner, no guard for coverage** — see §5 |
| Routing by role/capability | `graph/_agent_routing.py:79-141` | **Single owner**; `REVIEWER` role never claimed, falls back to `VALIDATOR` (`:108-113`) |
| Handoff record creation | `graph/nodes/_agent_handoff.py:109` (live); `agents/handoff.py:18` + `agents/runner.py:449` (unreachable) | **Distributed (2), one dead** — F-AGENT-02 |
| Artifact persistence for agents | `graph/nodes/_agent_artifacts.py:112` `_save_artifact` | **Single owner, clean** — §5 |
| Extra prompt context an agent gets (phase context, scene count) | `graph/nodes/_agent_prompt_context.py:94,148` (identity branches); `prompt_templates/defaults/spine.py:40` (the template variable they satisfy) | **Distributed (2)** — F-AGENT-11 |
| A validator's model profile | `graph/nodes/_context.py:41-42` (agent-side map, 2 validator rows); `validation/validators/__init__.py:131,151` (declared roster); `validation/impl/scene_continuity.py:217` (impl entry — wins at `validation/base.py:122`) | **Distributed (3), with 2 of 2 rows diverging** — F-AGENT-12 |
| The set of *known* profile ids | `agents/model_routing/__init__.py` (`list_profiles()`); `agents/registry.py:17` adds the legacy alias `"orchestrator"` | **Distributed (2), unguarded** — F-AGENT-01 |

---

## 5. Clean concerns and their guard tests

| Concern | Owner | Guard test | Notes |
|---|---|---|---|
| Prompt-template registration mechanics (register/get/get_required, overwrite-by-agent_id) | `agents/prompt_templates/registry.py:59-81` | `tests/unit/agents/test_prompt_template_registry.py:27-48` (`test_returns_registered_template`, `test_raises_keyerror_when_unregistered`) | Mechanics are single-owner and pinned. The *coverage* invariant (F-AGENT-05) is not. |
| Profile resolution and fallback semantics | `agents/model_routing/__init__.py:86-134` | `tests/unit/agents/model_routing/test_routing.py` | `select` / `resolve_or_raise` / `fallback` / `resolve_model_params` have one owner. The profile *name set* is duplicated (F-AGENT-01). |
| Model JSON extraction strategies | `agents/_json_extraction.py:15-86` | `tests/unit/agents/test_model_adapter.py` | Single owner; duplicated by `validation/base.py` (F-AGENT-07), but the module itself is clean. |
| `AgentRole` / `AgentFamily` enums | `schemas/_base.py:93-120` | `tests/unit/test_schemas.py` | Single owner. No test asserts every enum member is reachable by some registration — `VISUAL_DEV`, `GENERATION`, `POST`, `MEMORY` and `REVIEWER`, `SYNTHESIZER`, `CURATOR` have no MVP claimant. Recorded as a gap, not a finding. |
| Artifact persistence and candidate-ref publication for an agent run | `graph/nodes/_agent_artifacts.py:43-150` | `tests/unit/graph/test_candidate_ref_propagation.py` | Reads no agent contract; `created_by="graph_node"` (`:85`). Clean w.r.t. this cluster. |
| Handoff/side-channel propagation | `graph/nodes/_agent_handoff.py:45-96` | `tests/unit/graph/test_channel_registry.py` | Channel keys owned by `orchestrator_state.ORCH_CHANNELS`; the module contributes none. Clean. |
| Mock-response ↔ MVP roster coverage | `app/mock_responses.py:97` | `tests/unit/agents/test_mvp_invariants.py:61-69` | Pinned in the forward direction. MCP bible mocks are a separate, unguarded authority (F-AGENT-04). |
| **Explicit absence:** a guard test proving any two roster sources agree | — | **none** | `test_mvp_invariants.py` + `test_agent_profile_routing.py:35-40` are forward-only and never compare *values*. §2.4 is the absence record. |
| **Explicit absence:** a guard test for the KB manifest's agent vocabulary | — | **none** | No test loads `kb-manifest.yaml` and asserts `applies_to_agents ⊆ registered agent ids` (F-AGENT-09). |
| **Explicit absence:** a guard test that the declared `output_artifacts` match `execute()` | — | **none** | F-AGENT-02. |
| **Explicit absence:** any test at all for per-agent prompt-context augmentation | — | **none** | `grep -rn -e "_agent_prompt_context" -e "_maybe_add_orchestrator_context" tests/ --include=*.py` matches nothing (F-AGENT-11). |
| **Explicit absence:** a guard that a validator id has one agreed `model_profile` | — | **none** | No test compares `_AGENT_PROFILE_MAP`'s 2 validator rows to `MVP_VALIDATORS` or to an impl entry; both rows disagree today (F-AGENT-12). |
| **Explicit absence:** a guard that the set of known profile ids has one owner | — | **none** | `agents/registry.py:17`'s legacy alias is asserted by no test (F-AGENT-01). |

---

## 6. Candidate module boundary: `agents.registry` (agent descriptor + prompt owner)

One responsibility: **own the normative catalog of agents — identity, capabilities, I/O contract, prompt, model profile, and mock — and expose it as a single immutable table that every consumer reads.**

**Non-goals (does not):** does not execute agents; does not persist artifacts; does not decide routing *policy* (task-type/phase selection stays in `graph/_agent_routing.py`); does not call models; does not own the RCTCO section grammar beyond exposing one `render()`.

**Ownership reconciliation (post-verification).** `reviews/verify-04.md` dispute 8 notes that invariant 3 below adds a `_PHASE_DEFAULT_AGENTS.keys() ⊇ PHASE_ORDER` guard under `agents.registry`, while `audit/02` nominates a single `phases.py` catalog owning "order + gate + default agent + node". Resolution kept here: **the phase→default-agent table itself stays owned by `audit/02`'s `phases.py`; `agents.registry` owns only the invariant that every *value* in that table is a member of `AGENTS`.** The guard is split accordingly — `phases.py`/`audit/02` asserts `keys ⊇ PHASE_ORDER`, `agents.registry` asserts `set(_PHASE_DEFAULT_AGENTS.values()) ⊆ AGENTS`. Reading the table *from* `agents.registry` is explicitly not proposed.

**Owned state / normative model**

- `AGENTS: Mapping[str, AgentDescriptor]` — one row per real agent: `agent_id`, `aliases`, `family`, `role`, `capabilities`, `input_artifacts`, `produces` (the exact result key consumers read), `allowed_kb_domains`, `blocked_kb_domains`, `model_profile`, `prompt: PromptTemplate`, `mock_key`, `impl: type[BaseAgent]`.
- `PROMPT_TEMPLATES: Mapping[str, PromptTemplate]` — the single prompt registry with named accessors `for_agent()` / `for_validator()` (F-AGENT-05).
- The two vocabularies that registration validates against: `KB_DOMAINS` (supplied by `kb`) and `ArtifactType` (supplied by `schemas`).

**Invariants it enforces (must fail fast at import/registration)**

1. `descriptor.model_profile == _AGENT_PROFILE_MAP.get(agent_id, descriptor.model_profile)` — kills F-AGENT-01 by removing the second table.
2. Every `descriptor.produces` is an `ArtifactType` value and `descriptor.produces in impl(contract).execute(fixture)` — kills F-AGENT-02/03.
3. Every `AGENT_CLASS_BY_ID` key is `AGENTS` member or a documented alias; and `set(_PHASE_DEFAULT_AGENTS.values()) ⊆ AGENTS` (the table itself stays in `graph/_agent_routing.py`, per the reconciliation above) — kills F-AGENT-10.
4. Every non-`all` token in the KB manifest's `applies_to_agents` is an `AGENTS` member — kills F-AGENT-09.
5. Every `MVP_VALIDATORS` id with an `llm_enabled` impl has a validator template — kills F-AGENT-05/08.
6. Every agent's `prompt` comes from `PROMPT_TEMPLATES`; no module outside this package builds a prompt string for a known agent — kills F-AGENT-04/06.
7. Every `{placeholder}` a descriptor's template requires is either a base context var or supplied by one of the descriptor's declared `context_augmenters` (`("phase_context",)`, `("script_scene_count",)`) — kills F-AGENT-11.
8. `_AGENT_PROFILE_MAP` keys are exactly the `AGENTS` ids (no validator ids — today 2 validator rows sit there, `_context.py:41-42`), and every validator's `entry.model_profile` comes from its `MVP_VALIDATORS` row — kills F-AGENT-12.
9. Every profile id in `AGENTS` is a `ModelRouter.list_profiles()` member and no ad-hoc alias set is unioned in (`agents/registry.py:17`'s `"orchestrator"` is deleted) — kills F-AGENT-01's unguarded profile id-space.

**Consumers to move (conformance map)**

| Current site | Change |
|---|---|
| `agents/mvp/__init__.py:15-170` | becomes the `AGENTS` table (or is derived from it) |
| `agents/impl/registry.py:18-31` | folded into `AGENTS` (`impl` field) |
| `agents/prompt_templates/**` | folded in; `load_all`/`load_validator_templates` become table rows |
| `graph/nodes/_context.py:27-52` | deleted; `_AGENT_PROFILE_MAP` reads `AGENTS[id].model_profile` |
| `graph/nodes/_agent.py:141-162` | `descriptor = AGENTS[agent_id]`; uses `descriptor.prompt` and `descriptor.model_profile` |
| `graph/nodes/_agent_prompt_context.py:136-149` | the two `if agent_id == …` identity branches become `descriptor.context_augmenters` (invariant 7) |
| `graph/nodes/_context.py:41` (validator row) | removed from the map; the validator's profile comes from its `MVP_VALIDATORS` row (invariant 8) |
| `agents/registry.py:17` | legacy `"orchestrator"` profile alias deleted (invariant 9) |
| `mcp/tools/bibles/*.py` | delete local `AgentRegistration(...)` blocks and inline prompts; call `PromptRunner.run_from_template(AGENTS[id].prompt, …)` |
| `app/mock_responses.py` + five `*_mock_payload` functions | one mock per `descriptor.mock_key` |
| `schemas/registries/agent_registry.py` | deleted in favour of `schemas/handoff.py:AgentRegistration` |

**Public contract (for consumers):** `AGENTS`, `AgentDescriptor`, `PROMPT_TEMPLATES`, `for_agent()`, `for_validator()`, and the existing `AgentRegistry` lookup methods (`agents/registry.py:40-56`) preserved unchanged.

**Guard tests (bar B6)** — new file `tests/unit/agents/test_registry_agreement.py`:
- `test_every_descriptor_field_matches_its_contract` (invariant 1)
- `test_every_declared_output_is_produced` (invariant 2)
- `test_no_orphan_class_or_profile_ids` (invariant 3)
- `test_kb_manifest_agents_are_registered` (invariant 4)
- `test_every_llm_validator_has_a_template` (invariant 5)
- `test_no_module_outside_agents_builds_agent_prompts` — a grep/import test over `mcp/` and `graph/` for `model_adapter.chat(` and `PromptTemplate(` (invariant 6)
- `test_no_per_agent_identity_branches_in_prompt_context` — asserts `graph/nodes/_agent_prompt_context.py` contains no `agent_id ==` literal (invariant 7)
- `test_validator_profile_agrees_across_sources` — for each `MVP_VALIDATORS` id, the impl entry's `model_profile` equals the roster row's, and the id is absent from `_AGENT_PROFILE_MAP` (invariant 8)
- `test_known_profile_ids_have_one_owner` — `AgentRegistry().known_model_profiles == {*ModelRouter().list_profiles(), "orchestrator"}` is replaced by an exact-equality guard on `list_profiles()` (invariant 9)

**Extraction cost:** M (whole-table move, no logic change) for the table; S each for the profile-map and orphan deletions. **Order:** invariant 1 test → profile unification (S) → invariant 3 + orphan deletion (S) → MCP bible unification (M) → the full descriptor table (M). **Post-verification additions (F-AGENT-11/12/01-alias) are all S** and each can ship independently with its guard test.

---

## 7. Unverified hypotheses (not findings)

1. **Sibling-agent interference (resolved after verification).** The working tree *at first-audit time* contained 17 uncommitted `__init__.py` edits adding `ModuleContract(...)` blocks, an untracked `src/film_pipeline/architecture.py`, an untracked `tests/architecture/` tree, and a syntactically broken `src/film_pipeline/providers/__init__.py:42` (`public_api=(,),`) that made **every** `film_pipeline.agents.*` import fail. All evidence above was taken from HEAD; I did not modify, stash, or revert the sibling's work. **Update (`reviews/verify-04.md`):** the tree is now clean — `git status --porcelain` is empty at `fb85baa`, and every reproduce command in this document was re-run against a pristine `git archive HEAD` copy (`PYTHONPATH=<copy>/src`) from an unrelated CWD, all producing the stated output.
2. `src/film_pipeline/architecture.py:215` (untracked, not at HEAD) references `tests.architecture._readers.mvp_agent_output_artifacts`. If the concurrent task is building a declarative module-contract checker, it may overlap with this document's `output_artifacts` vocabulary finding (F-AGENT-03/F-AGENT-02). Unverified — the file is not at HEAD and I did not audit it.
3. `PromptTemplate.output_schema_ref` (e.g. `"matrix.ShotMatrix"`, `production.py:172`) is assigned by all 18 templates and **never read** by any source file — verified at HEAD: `grep -rn "output_schema_ref" src/ --include=*.py` returns exactly 18 assignment lines plus the dataclass field, with **zero** non-assignment references. A declared-but-unvalidated output schema belongs to the same family as F-AGENT-03, but I did not verify whether any external consumer (documentation generator, eval harness) reads it, so it is not promoted to a finding.
4. **Test suite (partially resolved after verification).** At first-audit time the dirty tree's `providers/__init__.py` import failure prevented `make ci-check`, so test names and line numbers were read, not run. With the tree clean, the full **`tests/unit` suite now exits 0 at HEAD** (1869 tests collected, 3 skipped, run from a pristine `git archive HEAD` copy). `make ci-check` as a whole (ruff format/lint, mypy strict, coverage gate, `uv build`) was still **not** run in this session, and the suite passing is exactly what makes F-AGENT-02's "no test can fail" claims load-bearing rather than incidental.

---

## 8. Coverage completeness against bar A1

- `agents`, `graph`, `mcp`, `schemas`, `app`, `validation`, `kb` (agent-related), `profiles/`, `tests/`, and all four entry points are mapped above.
- Not found to contain agent-roster decisions (read or grepped, no finding): `artifacts/*` (only `created_by` strings), `checkpoints/*`, `cli/*`, `config/*` (owns `model_profiles` YAML, consumed via F-AGENT-01's map), `constraints/*`, `generation/*`, `post/*`, `providers/*` (provider ids, a different registry), `review/*`, `testing/*` (`mock_model.py` keys by the caller's id, owns no roster).
- Packages omitted here with a pointer: `config` and `providers` profile/registry tables are owned by their own cluster audits; this document records only the agent-facing edge (F-AGENT-01, F-AGENT-04).
