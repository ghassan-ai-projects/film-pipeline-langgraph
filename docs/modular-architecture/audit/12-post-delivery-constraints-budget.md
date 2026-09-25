# 12 — Post-production, Delivery, Constraints, and Budget/Cost Accounting

Audited commit: **`fb85baa`** (`fb85baa0e6b769b709791a96a89980089304bf13`),
branch `modular-app` — the baseline recorded in
`docs/modular-architecture/00-methodology-and-quality-bar.md:200-202`.

Conforms to `docs/modular-architecture/00-methodology-and-quality-bar.md` §1.6 (evidence), §1.7 (finding
format), §2 bar A. Every claim below cites a `path:line` anchor with a verbatim
quote read at this commit. Commands are re-runnable from the repo root; `python`
means `.venv/bin/python`.

**Independent verification (A6):** `docs/modular-architecture/reviews/verify-12.md`
re-checked this file at the same commit — **11 CONFIRMED, 1 DOWNGRADED, 0
REJECTED**. The downgrade is **F-POST-06: High (3×4=12) → Medium (2×4=8)**,
because owner B (`src/film_pipeline/post/validators.py`) has zero production callers, so the
duplicated rule is a latent maintenance seam rather than wrong live behavior.
All disputes D1–D8 and the four missed seams in the verifier's §4 have been
resolved in this revision; items added after verification are marked
*(added after verification)*. The fix-loop brief transcribed the downgrade as
"3×3=8"; the verifier's own §2 states impact 2 × drift 4 = 8, and this file
follows §2 (§1.5: the product must equal the score). The `docs/` tree is
untracked (`.gitignore:2`); the sibling audits were revised concurrently during
this program (F-GEN-10 moved `:463` → `:467` → `:518`), so sibling citations
below are by finding id plus a grep command rather than by a frozen line
number.

---

## 1. Coverage

### 1.1 Scope A — post-production and delivery

| File | Disposition |
|---|---|
| `src/film_pipeline/post/__init__.py` (26) | read — re-export façade |
| `src/film_pipeline/post/assembly_agent.py` (144) | read in full — **has findings (F-POST-01/03/05/06)** |
| `src/film_pipeline/post/audio_design_agent.py` (113) | read in full — **F-POST-03**; no invocation path |
| `src/film_pipeline/post/delivery_packaging_agent.py` (209) | read in full — **F-POST-03/04/07** |
| `src/film_pipeline/post/subtitle_agent.py` (118) | read in full — **F-POST-03**; no invocation path |
| `src/film_pipeline/post/transition_agent.py` (79) | read in full — **F-POST-03**; no invocation path; `TRANSITION_TYPES` re-export is clean (§5) |
| `src/film_pipeline/post/validators.py` (55) | read in full — **F-POST-06**; no invocation path |
| `src/film_pipeline/agents/impl/assembly_agent.py` (114) | read in full — **F-POST-01/03** |
| `src/film_pipeline/agents/impl/*` (other 15 files) | enumerated — **no other impl duplicates a post agent**; only `src/film_pipeline/agents/impl/assembly_agent.py` does |
| `src/film_pipeline/agents/impl/registry.py` (36) | read in full — **F-POST-01/02** |
| `src/film_pipeline/agents/impl/__init__.py` (33) | read — re-export façade |
| `src/film_pipeline/mcp/tools/assembly.py` (76) | read in full — **F-POST-01/07** |
| `src/film_pipeline/mcp/tools/registry.py:372-382` (tool group wiring) | read — `assemble_review_cut`, `assemble_final_cut`, `export_delivery_package` registered; `assemble_final_cut` is a stub (`src/film_pipeline/mcp/tools/assembly.py:49-50`) |
| `src/film_pipeline/generation/executor_delivery.py` (148) | read in full — **clean for this cluster**; owns generation-asset delivery into the project tree (manifest + take sidecars), not the delivery *package*. No budget/assembly coupling. |
| `src/film_pipeline/validation/impl/assembly.py` (290) | read in full — **F-POST-06** |
| `src/film_pipeline/validation/impl/delivery_completeness.py` (198) | read in full — **F-POST-04/07** |
| `src/film_pipeline/graph/nodes/wrapup.py` (60) | read in full — **F-POST-02/05/07** |
| `src/film_pipeline/graph/nodes/post*.py` | **absent** — `post_node`/`delivery_node` live in `src/film_pipeline/graph/nodes/wrapup.py` (confirmed by `ls src/film_pipeline/graph/nodes/`) |

Companion maps read because they are on the post invocation path:
`src/film_pipeline/graph/_agent_routing.py` (phase default), `src/film_pipeline/graph/nodes/_agent.py` (agent run
harness), `src/film_pipeline/graph/nodes/_context.py` (`_AGENT_PROFILE_MAP`),
`src/film_pipeline/graph/_action_routing.py` (`APPROVAL_GATES`), `src/film_pipeline/graph/edges.py`
(`_NEXT_PHASE_AFTER_APPROVAL`), `src/film_pipeline/agents/mvp/__init__.py` (agent registrations),
`src/film_pipeline/agents/prompt_templates/defaults/production.py` (post prompt template),
`src/film_pipeline/app/mock_responses.py` (`failure-handling-agent` canned output),
`src/film_pipeline/graph/nodes/qc.py:337-370` (phase→validator runners).

### 1.2 Scope B — constraints and budget/cost

| File | Disposition |
|---|---|
| `src/film_pipeline/constraints/__init__.py` (13) | read — façade |
| `src/film_pipeline/constraints/extractor.py` (342) | read in full — **clean single owner** (§5); one seam noted |
| `src/film_pipeline/constraints/_keywords.py` (191) | read in full — **F-BUD-05** (`_NUMBER_WORDS` duplicated) |
| `src/film_pipeline/schemas/constraints.py` (160) | read in full — **clean contract**; `budget_cap_usd` is an unenforced cap (F-BUD-01) |
| `src/film_pipeline/schemas/budget.py` (48) | read in full — **F-BUD-01/03** |
| `src/film_pipeline/graph/nodes/prep.py` (382) | read in full — constraint extract + merge + scope contract (**§5 clean, one gap**) |
| `src/film_pipeline/graph/nodes/_shared.py:29-82` | read — **F-BUD-05** |
| `src/film_pipeline/graph/nodes/_agent_prompt_context.py` (160) | read the budget/constraint parts (:8-10, :38-53, :70-85, :143) — **F-BUD-04** |
| `src/film_pipeline/graph/nodes/_context.py:410-435` | read — **F-BUD-04** |
| `src/film_pipeline/graph/nodes/_generation_batch_planning.py` (165) | read in full — **F-BUD-02** |
| `src/film_pipeline/generation/ledger.py` (282) | read in full — **F-BUD-01/02/03** |
| `src/film_pipeline/generation/executor.py` | read the ledger/cost regions (:100-150, :300-345) — **F-BUD-02/03** |
| `src/film_pipeline/graph/orchestrator_state.py:40-70,125-165,440-540` | read — **F-BUD-02** |
| `src/film_pipeline/graph/_action_routing.py:18-70,225-270,340-395` | read — **F-BUD-02** |
| `src/film_pipeline/graph/orchestrator_validators/planning_gates.py:60-160` | read — **F-BUD-02** (gate site G6) |
| `src/film_pipeline/graph/context_packets.py:105-130` | read — **F-BUD-06** (plain-key budget reader, added after verification) |
| `src/film_pipeline/graph/state_schema.py:135-200` | read — budget/delivery channels (`:162` `delivery_manifest_ref`, `:177`, `:196`) |
| `src/film_pipeline/mcp/tools/planning.py` (250) | read in full — **F-BUD-01/03** |
| `src/film_pipeline/mcp/tools/generation/planning.py:30-180` | read — **F-BUD-02** |
| `src/film_pipeline/mcp/tools/registry.py:61,79,237,250-252` | read — budget/reconcile tool registration |
| `src/film_pipeline/app/services/_generation_ops.py:1-100` | read — **F-BUD-02** |
| `src/film_pipeline/app/services/operator.py:245-260,350-362` | read — budget snapshot reader + spend delegate |
| `src/film_pipeline/config/validator.py` (81) | read in full — **F-BUD-01/02** (cap source; warning-only gate G7) |
| `src/film_pipeline/providers/pricing.py` (139) | read in full — **clean single owner** (§5) |
| `src/film_pipeline/agents/impl/gen_planner_agent.py` (80) | read in full — **F-BUD-01/04** |
| `src/film_pipeline/agents/impl/intake_agent.py:40-105` | read — `budget_cap_usd` writer (F-BUD-01) |
| `src/film_pipeline/mcp/tools/intake.py:22` | read — `constraints_hints` seeding (no extraction) |
| `src/film_pipeline/schemas/project.py:43` | read — `ProjectProfile.budget_cap_usd`, never read for enforcement |

Not in this cluster (owned by sibling audits, cited where relevant):
`docs/modular-architecture/audit/06-generation-runtime-and-ledger.md` (ledger lifecycle, F-GEN-10),
`docs/modular-architecture/audit/07-artifact-refs-and-schemas.md`, `docs/modular-architecture/audit/08-validation-and-review.md` (validator
dispatch, F-VR-07), `docs/modular-architecture/audit/01-phase-model-and-transitions.md`, `docs/modular-architecture/audit/14-module-boundaries-and-import-law.md`.

---

## 2. Post-agent duplication table

`grep -rn "class \(Assembly\|DeliveryPackaging\|Subtitle\|AudioDesign\|Transition\)Agent" src/`
→ 5 classes in `post/`, 1 in `agents/impl/`.

| Class | Implementations (module:line) | Output model | Invocation paths | Reachable in production? |
|---|---|---|---|---|
| `AssemblyAgent` | **TWO.** `src/film_pipeline/post/assembly_agent.py:38` (plain `@dataclass`, `:37`) and `src/film_pipeline/agents/impl/assembly_agent.py:17` (`class AssemblyAgent(BaseAgent)`) | `post` → `AssemblyPlan` dataclass (`:23-34`) → persisted as `AssemblyPlanArtifact` (`:99`); `impl` → `AssemblyManifest` (`src/film_pipeline/agents/impl/assembly_agent.py:55-63`) | (a) graph: `src/film_pipeline/graph/nodes/wrapup.py:24-29` `_run_agent(agent_id="failure-handling-agent")` → `src/film_pipeline/agents/impl/registry.py:29` → impl class; (b) MCP: `src/film_pipeline/mcp/tools/assembly.py:37,39` direct import + `build_plan`/`validate_plan` (`:40-45`) | (a) yes (graph `post_node`); (b) via MCP tool `assemble_review_cut`. `post/…:persist` is called **only from tests** (`grep -rn "\.persist(" src/` → no caller) |
| `DeliveryPackagingAgent` | ONE: `src/film_pipeline/post/delivery_packaging_agent.py:81` | `DeliveryPackage` dataclass (`:21`) → `schemas.delivery.DeliveryPackage` (`:147,150-165`) | MCP: `src/film_pipeline/mcp/tools/assembly.py:59,61` via `export_delivery_package` (`:53`) | Tool reachable, but it never calls `persist` (`:134`) or `validate` (`:180`) — those are called only from `tests/unit/post/test_post.py:339,362,374` |
| `SubtitleAgent` | ONE: `src/film_pipeline/post/subtitle_agent.py:42` | `SubtitlePlan` (`:21`) → `schemas.subtitle.SubtitleArtifact` (`:86`) | **none** — `grep -rn "SubtitleAgent\|generate_subtitles" src/` returns only the definition | no |
| `AudioDesignAgent` | ONE: `src/film_pipeline/post/audio_design_agent.py:79` | `AudioPlan` dataclass (`:28`); **no** persistence method | **none** — `grep -rn "AudioDesignAgent\|plan_audio" src/` returns only the definition | no |
| `TransitionAgent` | ONE: `src/film_pipeline/post/transition_agent.py:26` | `TransitionPlan` dataclass (`:16`); no persistence method | **none** — `grep -rn "TransitionAgent\|plan_transitions" src/` returns only the definition | no |
| `PostValidator` | ONE: `src/film_pipeline/post/validators.py:13` | validates the `post` dataclasses (`:16,27,38,48`) | **none** — used only by `tests/unit/post/test_post.py` | no |

**Only `AssemblyAgent` is duplicated as a class.** The other post classes are
single but three of them (`Subtitle`, `AudioDesign`, `Transition`) plus
`PostValidator` are unreachable from any production entry point — recorded here
as *incompleteness, not distributed ownership* (per §1.3), so they are covered
by the "clean/gap" notes in §5, not by a finding.

Every post class also has a schema twin with the same name (§4, F-POST-03).

---

## 3. Budget writer map

Legend: **W** = writer, **R** = reader, **∅** = no writer.

| Field / state | Writer modules (path:line) | Readers | Single / distributed |
|---|---|---|---|
| `BudgetState.cap_usd` | `src/film_pipeline/mcp/tools/planning.py:35` — only writer in all of `src/` | none (grep — no code loads `artifact_id="budget_state"`) | **Single writer, zero consumers** |
| `BudgetState.spent_usd` | `src/film_pipeline/mcp/tools/planning.py:36` `spent_usd=0.0` — init only, never incremented | `src/film_pipeline/schemas/budget.py:47-48` `remaining_usd`; `src/film_pipeline/mcp/tools/planning.py:55` | **∅ recorder** (O3) |
| `BudgetState.per_phase_spent_usd` | **∅** (`src/film_pipeline/schemas/budget.py:42`) | none | ∅ |
| `BudgetState.per_phase_caps_usd` | `src/film_pipeline/mcp/tools/planning.py:37-41` (visual_dev/generation/post split) | **none** | Single writer, zero consumers |
| `BudgetState.max_auto_approved_cost_usd`, `human_approval_above_usd` | `src/film_pipeline/mcp/tools/planning.py:42-43` | **none** | Single writer, zero consumers |
| `SpendRecord` (whole model) | **∅** (`src/film_pipeline/schemas/budget.py:23-32`) | none | ∅ |
| `GenerationLedgerRow.estimated_cost_usd` | `src/film_pipeline/generation/ledger.py:99` (`plan_batch`); `src/film_pipeline/generation/ledger.py:199-217` (`update_row`, generic — no cost caller) | `src/film_pipeline/generation/ledger.py:123-132`, `:276`; `src/film_pipeline/generation/executor.py:333`; `src/film_pipeline/mcp/tools/generation/status.py:32` | **Single writer, 3 cost-estimate producers feed it** (`src/film_pipeline/generation/executor.py:112-120`, `src/film_pipeline/graph/nodes/_generation_batch_planning.py:146-153`, `src/film_pipeline/mcp/tools/generation/planning.py:93-100`) |
| `GenerationLedgerRow.actual_cost_usd` | **∅** (`src/film_pipeline/schemas/generation.py:68`; grep → declaration + one test string only) | none | ∅ (prior art) |
| `_orchestrator__budget_snapshot` (namespaced) | **∅ in production.** `src/film_pipeline/graph/orchestrator_state.py:449-463` `update_budget_snapshot` has **zero** non-test callers | `src/film_pipeline/graph/orchestrator_state.py:466-479`; `src/film_pipeline/graph/_action_routing.py:240`; `src/film_pipeline/app/services/operator.py:251`; `src/film_pipeline/mcp/tools/state.py:57` | **∅ writer, 4 readers** (O3 + O2) |
| `state["budget_snapshot"]` (plain, un-namespaced) | **∅** — the only writer of this key is `tests/unit/graph/test_context_packets.py:175` `"\"budget_snapshot\": {\"cap_usd\": 42}"` | `src/film_pipeline/graph/context_packets.py:121` | **∅ writer, 1 reader** (F-BUD-06, added after verification) |
| `ProjectConstraints.budget_cap_usd` (cap B) | `src/film_pipeline/constraints/extractor.py:154` ← `_extract_budget` (`:286-294`) | nothing enforces it (grep `budget_cap_usd` → writers only) | Single writer, **zero enforcement** |
| `ProjectProfile.budget_cap_usd` (cap E) | `src/film_pipeline/agents/impl/intake_agent.py:49` ← model output (`data.get("budget_cap_usd")`), field at `src/film_pipeline/schemas/project.py:43` | **none** (`grep -rn "budget_cap_usd" src/` → writers only) | Single writer, zero consumers *(added after verification)* |
| `resolved_config["budget"]["project_cap_usd" / "max_total_usd"]` | config profiles (no schema declared; read by consumers) | `src/film_pipeline/graph/nodes/_context.py:422-427`; `src/film_pipeline/config/validator.py:55` | **Undeclared cap** |
| `max_cost_usd` (transient ceiling) | `src/film_pipeline/graph/nodes/_generation_batch_planning.py:37-47`; `src/film_pipeline/mcp/tools/generation/planning.py:131`; `src/film_pipeline/app/services/_generation_ops.py:73,82` | `src/film_pipeline/generation/ledger.py:108,264-282` | **Distributed policy** (O5/O2) |
| `context_vars["budget_cap"]` | `src/film_pipeline/graph/nodes/_context.py:427` | `src/film_pipeline/agents/prompt_templates/defaults/production.py:198` | Single writer |
| `state["budget_cap"]` | **∅** | `src/film_pipeline/agents/impl/gen_planner_agent.py:53` | ∅ (O8/O5, F-BUD-04) |

**Counts (recomputed after verification; counting rule stated so it is
reproducible).** A *representation* is one persisted artifact, typed model,
namespaced state channel, or transient ceiling that carries a budget or cost
number. **Representations: 8** — `BudgetState` (`cap_usd`/`spent_usd`/
`per_phase_*`/approval knobs), `SpendRecord`, ledger row
`estimated_cost_usd`, ledger row `actual_cost_usd`,
`_orchestrator__budget_snapshot`, plain `state["budget_snapshot"]`,
`ProjectConstraints.budget_cap_usd`, `ProjectProfile.budget_cap_usd` — plus
`resolved_config["budget"]` as a ninth, undeclared representation (no schema in
`src/` declares the block; see U-12-02). *Cap* values that a spend decision can
be measured against: **5** (A artifact `BudgetState.cap_usd`; B
`ProjectConstraints.budget_cap_usd`; C `resolved_config` project cap; D the
per-batch `max_cost_usd` ceiling; E `ProjectProfile.budget_cap_usd`).
**Modules that write budget/cost state or derive a ceiling: 7** —
`src/film_pipeline/mcp/tools/planning.py`, `src/film_pipeline/generation/ledger.py`, `src/film_pipeline/constraints/extractor.py`,
`src/film_pipeline/agents/impl/intake_agent.py`, `src/film_pipeline/graph/nodes/_context.py`,
`src/film_pipeline/graph/nodes/_generation_batch_planning.py`, `src/film_pipeline/app/services/_generation_ops.py` +
`src/film_pipeline/mcp/tools/generation/planning.py` (the last two are the same MCP/operator pair;
counted separately they make **8**), and **9** if the defined-but-uncalled
`src/film_pipeline/graph/orchestrator_state.py:449` `update_budget_snapshot` is counted.
Enforcement/advisory gate sites: **8** (§4, F-BUD-02); budget *readers* on the
namespaced channel: 4 (+1 broken plain-key reader, F-BUD-06).

---

## 4. Findings

### F-POST-01 — `AssemblyAgent` exists twice with disjoint output contracts and two invocation lifecycles

- **Class:** O6 (parallel lifecycle)
- **Severity:** Critical (impact 5 × drift 5 = 25)
- **Concern:** one lifecycle — "turn generated media + shot matrix into the
  review cut" — has two independent implementations, one on the graph/agent
  lifecycle and one on the MCP lifecycle.
- **De-facto owners:**
  - `src/film_pipeline/post/assembly_agent.py:37-38` — the MCP-side lifecycle —
    `"@dataclass"` / `"class AssemblyAgent:"`, whose `build_plan` (`:43-81`)
    matches clips by substring and stamps a placeholder duration:
    `"_SECONDS_PER_CLIP = 5.0"` (`:10`).
  - `src/film_pipeline/agents/impl/assembly_agent.py:17` — the graph-side
    lifecycle — `"class AssemblyAgent(BaseAgent):"`, whose `_build_clip_order`
    (`:73-84`) defaults `out_seconds` to `5.0` and synthesises
    `shot_id=f"shot_{i:04d}"` (`:77`).
  - `src/film_pipeline/agents/impl/registry.py:29` — the id that selects the
    graph-side class — `"\"failure-handling-agent\": AssemblyAgent,"`.
  - `src/film_pipeline/mcp/tools/assembly.py:37-39` — the MCP-side path that
    bypasses the registry entirely —
    `"from film_pipeline.post.assembly_agent import AssemblyAgent"` /
    `"agent = AssemblyAgent()"`.
- **Drift proof:** **existing divergence.** The two classes overlap on five
  field *names* — `clip_order, missing_assets, project_id, transitions` plus the
  inherited `schema_version` — but the semantic payload is divergent.
  Executed field diff:
  `AssemblyManifest`(manifest-only) = `audio_plan, color_plan, cut_id,
  delivery_mode, duration_total_seconds`; `AssemblyPlanArtifact`(plan-only) =
  `clip_count, clips, notes, plan_id, total_duration_seconds`. The overlap is
  name-only for `transitions` (typed `list[TransitionPlan]` in the manifest,
  `list[dict[str, str]]` in the plan artifact — see F-POST-05). Mutation scenario:
  change clip matching in `src/film_pipeline/post/assembly_agent.py:13-15` (substring match) —
  `src/film_pipeline/agents/impl/assembly_agent.py:73-84` keeps its own coercion and no test
  fails, because `tests/unit/post/test_post.py` only exercises the `post` class
  and `tests/unit/agents/test_impl_agents.py:658-760` only the `agents.impl`
  class; no test imports both.
- **Reproduce:**
  ```bash
  grep -rn "class AssemblyAgent" src/
  .venv/bin/python -c "
  from film_pipeline.post.assembly_agent import AssemblyPlan
  from film_pipeline.schemas.assembly import AssemblyManifest, AssemblyPlanArtifact
  print('shared', sorted(set(AssemblyManifest.model_fields) & set(AssemblyPlanArtifact.model_fields)))
  print('manifest-only', sorted(set(AssemblyManifest.model_fields) - set(AssemblyPlanArtifact.model_fields)))"
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/wrapup.py`, `src/film_pipeline/agents/impl/registry.py`,
  `src/film_pipeline/mcp/tools/assembly.py`, `src/film_pipeline/validation/impl/assembly.py` (validates *both*
  shapes through `artifact.get(...)`), `src/film_pipeline/schemas/assembly.py:56,70`. User-visible:
  the MCP review-cut plan and the graph assembly manifest are different objects
  for the same film; an agent that fixes one leaves the other wrong.
- **Candidate owner module:** `post-production` — sole owner of the review-cut
  model and its construction; the graph runs *it*, the MCP tool runs *it*.
- **Extraction sketch:** delete `src/film_pipeline/post/assembly_agent.py:AssemblyAgent` (keep
  `src/film_pipeline/schemas/assembly.py` as the contract), make `assemble_review_cut` call the
  registered agent through the same routing as `post_node`, and add a guard test
  asserting exactly one `AssemblyAgent` class exists in `src/` (import-sweep or
  `grep -c "class AssemblyAgent"` == 1).
- **Prior art:** `documentation/audit-findings.md:100` notes the *mismap*
  (`failure-handling-agent` → `AssemblyAgent`) but not that two `AssemblyAgent`
  classes exist. The duplicate class is **new**; the mismap is still present at
  HEAD and is F-POST-02.

### F-POST-02 — the agent id `failure-handling-agent` is owned by six registries that disagree about what it is

- **Class:** O4 (parallel registries)
- **Severity:** Critical (impact 5 × drift 5 = 25)
- **Concern:** the identity of one agent id — is it the failure triage operator
  or the post-production assembler?
- **De-facto owners:**
  - `src/film_pipeline/agents/mvp/__init__.py:157-168` — the registration says
    failure triage — `"agent_id=\"failure-handling-agent\","` with
    `"capabilities=[\"error_classification\", \"recovery_decision\", \"retry_policy\"],"` (`:160`)
    and `"output_artifacts=[\"failure_decision\"],"` (`:162`).
  - `src/film_pipeline/agents/impl/registry.py:29` — the implementation says
    assembly — `"\"failure-handling-agent\": AssemblyAgent,"`.
  - `src/film_pipeline/agents/prompt_templates/defaults/production.py:302-306` —
    the prompt says assembly — `"template_id=\"assembly-agent-v3\","` /
    `"agent_id=\"failure-handling-agent\","` /
    `"role=\"You are the assembly-agent (Post-Production Assembly). \""`.
  - `src/film_pipeline/graph/nodes/_context.py:49` — the model profile says
    triage — `"\"failure-handling-agent\": \"operations_triage\","`.
  - `src/film_pipeline/graph/_agent_routing.py:45` — the phase default makes it
    the *post* creator — `"\"post\": \"failure-handling-agent\","`.
  - `src/film_pipeline/app/mock_responses.py:398-399` — the canned reply is
    assembly — `"\"failure-handling-agent\": {"` / `"\"assembly\": {"`.
- **Drift proof:** **existing divergence** between `src/film_pipeline/agents/mvp/__init__.py:162`
  (`output_artifacts=["failure_decision"]`) and `src/film_pipeline/agents/impl/assembly_agent.py:64`
  (`return {"assembly_manifest": manifest}`). Support: `FailureDecision`
  (`src/film_pipeline/schemas/failure.py:17`) is **never constructed anywhere in `src/`**
  (`grep -rn "FailureDecision(" src/` → only the class definition), so the
  declared output artifact does not exist in any run. Mutation scenario: rename
  the impl result key to `cut_manifest`; `src/film_pipeline/agents/impl/registry.py:29` still maps the id and
  `src/film_pipeline/agents/mvp/__init__.py:162` still declares `failure_decision`; no test compares
  `AGENT_CLASS_BY_ID` keys against the registered contracts' declared
  `output_artifacts` (`grep -rn "AGENT_CLASS_BY_ID" src/ tests/` → only
  `src/film_pipeline/agents/impl/registry.py:18,36` and `tests/unit/agents/test_impl_registry.py:7,22`;
  `src/film_pipeline/graph/nodes/_agent.py:100` matches `get_agent_class`, not the map, and
  `tests/unit/agents/test_impl_registry.py:22` is the tautology `"assert len(AGENT_CLASS_BY_ID) == len(set(AGENT_CLASS_BY_ID))"`).
- **Reproduce:**
  ```bash
  grep -rn "failure-handling-agent" src/ | grep -v __pycache__
  grep -rn "FailureDecision(" src/
  grep -rn "AGENT_CLASS_BY_ID" src/ tests/
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/_agent.py:100` (`impl=get_agent_class(...)`),
  `src/film_pipeline/graph/nodes/wrapup.py:26`, `src/film_pipeline/graph/_agent_routing.py:45,79-88`,
  `src/film_pipeline/agents/prompt_templates/defaults/production.py`, `src/film_pipeline/app/mock_responses.py`.
  User-visible: any request routed as the failure handler runs the assembler,
  so failure triage cannot happen; and the post phase is documented as "failure
  handling" in every registry that a reviewer would consult.
- **Candidate owner module:** `agent-registry` — one registry keyed by agent id
  that holds implementation, contract, prompt template, and model profile
  together, with an agreement test.
- **Extraction sketch:** split the id: introduce `assembly-agent` for the post
  creator and restore `failure-handling-agent` to a real triage impl (or delete
  it until one exists); assert in one guard test that
  `set(AGENT_CLASS_BY_ID) ⊆ {r.agent_id for r in MVP_AGENTS}` and that each
  impl's produced keys match its contract's `output_artifacts`.
- **Prior art:** `documentation/audit-findings.md:68` and `:100` already record
  the mismap ("contains semantic mismaps (`failure-handling-agent` →
  `AssemblyAgent` …)"). **Still present at HEAD.** New here: the full six-way
  registry enumeration and the executable proof that the declared
  `failure_decision` output is never produced.

### F-POST-03 — every post-production model is defined twice: once in `post/`, once in `schemas/`

- **Class:** O1 (duplicated normative model)
- **Severity:** High (impact 3 × drift 5 = 15)
- **Concern:** the normative shape of a post-production artifact.
- **De-facto owners:**
  - `src/film_pipeline/post/audio_design_agent.py:27-28` — `"@dataclass"` /
    `"class AudioPlan:"` — versus `src/film_pipeline/schemas/assembly.py:34`
    `"class AudioPlan(SchemaBase):"`.
  - `src/film_pipeline/post/transition_agent.py:15-16` — `"@dataclass"` /
    `"class TransitionPlan:"` — versus `src/film_pipeline/schemas/assembly.py:22`
    `"class TransitionPlan(SchemaBase):"`.
  - `src/film_pipeline/post/delivery_packaging_agent.py:20-21` — `"@dataclass"` /
    `"class DeliveryPackage:"` — versus `src/film_pipeline/schemas/delivery.py:27`
    `"class DeliveryPackage(SchemaBase):"`.
  - `src/film_pipeline/post/subtitle_agent.py:10-11` — `"@dataclass"` /
    `"class SubtitleCue:"` — versus `src/film_pipeline/schemas/subtitle.py:10`
    `"class SubtitleCue(SchemaBase):"`.
  - `src/film_pipeline/post/assembly_agent.py:23-24` — `"@dataclass"` /
    `"class AssemblyPlan:"` — versus `src/film_pipeline/schemas/assembly.py:56` `AssemblyManifest`
    and `:70` `AssemblyPlanArtifact`.
  - `src/film_pipeline/agents/prompt_templates/defaults/production.py:351` — the
    prompt declares a *fourth* name for the same thing —
    `"output_schema_ref=\"assembly.AssemblyPlan\","` — which exists in no module
    (`grep -rn "class AssemblyPlan" src/film_pipeline/schemas/` → nothing).
- **Drift proof:** **existing divergence, executed.** `post.AudioPlan` and
  `schemas.assembly.AudioPlan` share **zero** fields: post-only =
  `notes, plan_id, project_id, total_tracks, tracks`; schema-only =
  `cue_points, dialogue_track_refs, music_track_refs, schema_version,
  sfx_track_refs` (`schema_version` is inherited from
  `schemas/_base.SchemaBase:273`, not a domain field). Same for
  `TransitionPlan`: post-only = `plan_id, project_id, total_count, transitions`;
  schema-only = `duration_seconds, from_shot_id, to_shot_id, schema_version,
  transition_type`.
  Mutation scenario: add a `cue_points`-style field to
  `schemas/assembly.AudioPlan:34-43` (the model `src/film_pipeline/agents/impl/assembly_agent.py:100-106`
  builds); `src/film_pipeline/post/audio_design_agent.py:28` keeps the old shape and no test
  fails — the two suites never import the same class under both names.
  `output_schema_ref` is declared at `src/film_pipeline/agents/prompt_templates/registry.py:30`
  and never resolved (grep → assignments only), so the dangling
  `assembly.AssemblyPlan` cannot fail any test.
- **Reproduce:**
  ```bash
  .venv/bin/python -c "
  import dataclasses as dc
  from film_pipeline.post.audio_design_agent import AudioPlan as P
  from film_pipeline.schemas.assembly import AudioPlan as S
  print('post-only', sorted(f.name for f in dc.fields(P)))
  print('schema-only', sorted(S.model_fields))"
  grep -rn "output_schema_ref" src/ | grep -c "assembly.AssemblyPlan"
  ```
- **Blast radius:** `src/film_pipeline/agents/impl/assembly_agent.py:100-114` (consumes the schema
  twin), `src/film_pipeline/post/validators.py:7-9` (consumes the dataclass twins),
  `src/film_pipeline/graph/nodes/qc.py:342` (validates the schema twin). User-visible: the
  structured fields the assembler actually produces (`audio_plan.cue_points`,
  `color_plan.per_scene`) are invisible to every `post/` consumer, and vice
  versa.
- **Candidate owner module:** `schemas` (already the repo's declared contract
  package, `AGENTS.md` "Pydantic v2 for all schemas") — `post/` must import the
  contract, not restate it.
- **Extraction sketch:** delete the five dataclass models, keep
  `src/film_pipeline/schemas/assembly.py` + `src/film_pipeline/schemas/delivery.py` + `src/film_pipeline/schemas/subtitle.py` as the
  only definitions, port `to_srt()` (`src/film_pipeline/post/subtitle_agent.py:30-38`) and the
  `is_complete`/`missing_items` derivations (`src/film_pipeline/post/delivery_packaging_agent.py:37-45`)
  onto the schema models or into the owning module's functions, and add a
  duplicate-normative-model guard test that asserts one class of each name under
  `film_pipeline`.
- **Prior art:** new for the model duplication. `docs/modular-architecture/audit/01-phase-model-and-transitions.md:62`
  records `post/*.py` as clean *phase-vocabulary* consumers, which this finding
  does not contradict.

### F-POST-04 — "what makes a delivery package complete" has two owners that already disagree

- **Class:** O2 (duplicated invariant enforcement)
- **Severity:** Critical (impact 5 × drift 5 = 25)
- **Concern:** the rule that decides whether a delivery package is complete and
  may ship.
- **De-facto owners:**
  - `src/film_pipeline/post/delivery_packaging_agent.py:11-17` — owner A, five
    flags — `"(\"subtitles_included\", \"subtitles\"),"` …
    `"(\"credits_included\", \"credits\"),"`, consumed by `is_complete` (`:37-39`)
    and `missing_items` (`:41-45`). Note: `audio_stems` is required; the final
    video is **not**.
  - `src/film_pipeline/validation/impl/delivery_completeness.py:15-22` — owner B,
    six basenames — `"REQUIRED_DELIVERY_FILES = {"` /
    `"\"final_video.mp4\","` / `"\"review_cut.mp4\","` / … / `"\"cost_report.json\","`,
    enforced at `:134` `"missing_required = REQUIRED_DELIVERY_FILES - basenames"`.
  - `src/film_pipeline/post/delivery_packaging_agent.py:48-77` — the raw-dict
    adapter that bridges them —
    `"Shape a package as the artifact dict DeliveryCompletenessValidator reads."`
    / `"Canonical basenames stand in for real paths because the validator only"`.
- **Drift proof:** **existing divergence, executed.** A package the owner calls
  complete is blocked by the validator the same agent runs:
  ```
  is_complete = True | missing_items = []
  validator status = blocked | score = 0.0
  blocking = [5 × missing_required_asset: cost_report.json, final_video.mp4,
              review_cut.mp4, subtitles.srt, validation_report.json]
  ```
  Mutation scenario: add `"poster.png"` to `_COMPLETION_REQUIREMENTS`
  (`src/film_pipeline/post/delivery_packaging_agent.py:11-17`); `REQUIRED_DELIVERY_FILES`
  (`src/film_pipeline/validation/impl/delivery_completeness.py:15-22`) keeps the old set, and no
  test fails: the only test that runs the validator patches the package by hand
  to satisfy owner B —
  `tests/unit/post/test_post.py:359-360`
  `"# Also add review_cut for completeness"` /
  `"package.files.append({\"path\": \"review_cut.mp4\", \"type\": \"video\"})"`.
  `tests/unit/post/test_post.py:118-130` asserts `is_complete is True` on a
  package (`final.mp4`, `subs.srt`, `cost.json`) that owner B blocks.
- **Reproduce:**
  ```bash
  .venv/bin/python -c "
  from film_pipeline.post.delivery_packaging_agent import DeliveryPackagingAgent as A
  p = A().build_package(project_id='p', video_path='final.mp4', subtitle_path='subs.srt',
      audio_stems_dir='stems/', validation_report_path='report.json',
      cost_report_path='cost.json', credits_path='credits.txt')
  print('is_complete', p.is_complete, p.missing_items)
  r = A().validate(p); print(r['status'], r['score'], r['blocking_issues'])"
  ```
- **Blast radius:** `src/film_pipeline/post/delivery_packaging_agent.py`, `src/film_pipeline/validation/impl/delivery_completeness.py`,
  `src/film_pipeline/graph/nodes/qc.py:353-358`, `src/film_pipeline/mcp/tools/assembly.py:72-76` (`_ok(is_complete=package.is_complete)`
  reports owner A's verdict to the operator while the validator is never run on
  that path), and `src/film_pipeline/post/validators.py:38-46` — a third observable of owner A's
  verdict — `"if not package.is_complete:"` / `"missing = package.missing_items"`
  *(added after verification)*. User-visible: the operator is told "complete" for a package the
  system's own validator blocks — wrong information about a human deliverable.
- **Candidate owner module:** `delivery` — one declarative required-artifact
  table from which both `is_complete` and the validator are derived.
- **Extraction sketch:** move `REQUIRED_DELIVERY_FILES` into the delivery
  contract module as the single table, derive `DeliveryPackage.is_complete`
  from it, delete `_completeness_check_artifact` (`:48-77`), and add a guard
  test asserting `is_complete == (validator.status is PASS)` for a fixture
  matrix of packages.
- **Prior art:** `documentation/reviews/arch-lens-boundaries.md:20` already
  states: "`src/film_pipeline/post/delivery_packaging_agent.py:11-17` `_COMPLETION_REQUIREMENTS` +
  `is_complete`/`missing_items` (lines 37-45) duplicate 'what makes delivery
  complete', which is also encoded inside `src/film_pipeline/validation/impl/delivery_completeness.py`.
  Two sources of truth." **Still present at HEAD.** New here: the executed
  divergence (owner A `True` vs owner B `blocked/0.0`) and the test that hides it
  (`tests/unit/post/test_post.py:359-360`); the prior review asserted the duplication but did not
  show the two verdicts differing.

### F-POST-05 — the same artifact id (`assembly_manifest`, phase `post`) has two writers with incompatible schemas

- **Class:** O3 (split state authority)
- **Severity:** Critical (impact 4 × drift 5 = 20)
- **Concern:** the persisted representation of the post phase's assembly output.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/wrapup.py:30-32` — writer 1, the graph —
    `"manifest = result.get(\"assembly_manifest\")"` /
    `"ref = _save_artifact(new_state, manifest, \"assembly_manifest\", \"post\")"`,
    where `manifest` is an `AssemblyManifest` (`src/film_pipeline/agents/impl/assembly_agent.py:55`).
  - `src/film_pipeline/post/assembly_agent.py:98-99,132` — writer 2, the MCP/post
    path — `"artifact_id = \"assembly_manifest\""` /
    `"model = AssemblyPlanArtifact("` / `"ref: ArtifactRef = artifact_store.save(model, meta)"`.
  - `src/film_pipeline/artifacts/registry.py:186` — the single spec both claim —
    `"\"assembly_manifest\": _spec(\"assembly_manifest\"),"`.
- **Drift proof:** **existing divergence, live writer vs test-only writer.**
  Writer 2 (`src/film_pipeline/post/assembly_agent.py:132`) has **no `src/` caller**
  (`grep -rn "\.persist(" src/` → empty); it is exercised only by
  `tests/unit/post/test_post.py:298`, so the divergence is latent in production
  today but is a live hazard for any MCP-driven state that reuses the class.
  The two schemas share only five field *names* (F-POST-01) and disagree on the
  semantic payload: writer 1 emits
  `transitions: list[TransitionPlan]` typed with `transition_type`
  (`src/film_pipeline/schemas/assembly.py:28,62`) and `cut_id` (`:59`); writer 2 emits
  `transitions: list[dict[str, str]]` and no `cut_id`/`audio_plan`/`color_plan`
  (`src/film_pipeline/schemas/assembly.py:70-81`). `src/film_pipeline/validation/impl/assembly.py:223-228` reads both
  through `artifact.get("cut_id", "?")` and `artifact.get("audio_plan", {})`, so
  the validator silently degrades on writer 2's artifact: `_flag_audio_sync_issues`
  returns 0 (`:164-167`) and `_flag_color_plan_issues` emits
  `color_grade_inconsistent` (`:187-193`) for a manifest that simply has no
  color field. Mutation scenario: add a required field to `AssemblyManifest`;
  `src/film_pipeline/post/assembly_agent.py:99` keeps writing `AssemblyPlanArtifact` and no test
  fails — `tests/unit/graph/test_wrapup_nodes.py` only exercises writer 1 and
  `tests/unit/post/test_post.py:303` only writer 2.
- **Reproduce:**
  ```bash
  grep -rn "assembly_manifest" src/film_pipeline/post/assembly_agent.py src/film_pipeline/graph/nodes/wrapup.py
  .venv/bin/python -c "
  from film_pipeline.schemas.assembly import AssemblyManifest, AssemblyPlanArtifact
  print('manifest-only', sorted(set(AssemblyManifest.model_fields)-set(AssemblyPlanArtifact.model_fields)))
  print('plan-only', sorted(set(AssemblyPlanArtifact.model_fields)-set(AssemblyManifest.model_fields)))"
  ```
- **Blast radius:** `src/film_pipeline/validation/impl/assembly.py`, `src/film_pipeline/graph/nodes/qc.py:337-342`,
  `src/film_pipeline/artifacts/registry.py:186`, `src/film_pipeline/graph/state_schema.py:158`
  (`assembly_manifest_ref`). User-visible: whichever path wrote the artifact
  decides whether the assembly validator reports a clean cut or a bogus color
  warning.
- **Candidate owner module:** `post-production` (assembly artifact writer) —
  one writer, one schema per artifact id.
- **Extraction sketch:** make `assembly_manifest` mean exactly one model
  (`AssemblyManifest`); have `post/assembly_agent.build_plan` return it and route
  both the graph and the MCP tool through one save function; guard test
  asserting `src/film_pipeline/artifacts/registry.py` maps each artifact id to exactly one schema
  class and that a `grep` finds one `_save_artifact(..., "assembly_manifest", ...)`
  call site.
- **Prior art:** new. `docs/modular-architecture/audit/07-artifact-refs-and-schemas.md` does not mention
  `assembly_manifest` (grep → 0 hits).

### F-POST-06 — three independent validators of the assembly plan, with divergent rules

- **Class:** O2 (duplicated invariant enforcement)
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** what counts as a structurally valid assembly plan/manifest.
- **De-facto owners:**
  - `src/film_pipeline/post/assembly_agent.py:135-144` — owner A —
    `"def validate_plan(self, plan: AssemblyPlan) -> list[str]:"` with
    `"if plan.clip_count != len(plan.clips):"` / `"issues.append(\"Clip count mismatch.\")"` (`:142-143`).
  - `src/film_pipeline/post/validators.py:16-25` — owner B, a second copy of the
    same checks with a *different* third rule —
    `"if plan.clip_count == 0:"` / `"issues.append(\"Clip count is zero.\")"` (`:23-24`).
  - `src/film_pipeline/validation/impl/assembly.py:197` — owner C, the validator
    the QC phase runs — `"class AssemblyValidator(BaseValidator):"`, whose
    `_validate_rules` (`:216-257`) checks transition referential integrity and
    clip ordering, not clip count.
- **Drift proof:** **existing divergence, executed.** For the same object —
  `AssemblyPlan(plan_id='i', project_id='p', clips=['a','b'], clip_count=1)` —
  owner A returns `['Clip count mismatch.']` and owner B returns `[]`. Mutation
  scenario: change the rule
  in `src/film_pipeline/post/assembly_agent.py:142`; `src/film_pipeline/post/validators.py:23` keeps its own and no
  test fails — `tests/unit/post/test_post.py:47-65` tests A and
  `:171-251` tests B, never against each other.
- **Reproduce:**
  ```bash
  grep -rn "clip_count" src/film_pipeline/post/assembly_agent.py src/film_pipeline/post/validators.py
  .venv/bin/python -c "
  import film_pipeline.post.assembly_agent as m
  from film_pipeline.post.assembly_agent import AssemblyPlan
  from film_pipeline.post.validators import PostValidator
  p = AssemblyPlan(plan_id='i', project_id='p', clips=['a','b'], clip_count=1)
  print('ownerA', m.AssemblyAgent().validate_plan(p))
  print('ownerB', PostValidator().validate_assembly(p))"
  ```
- **Blast radius:** `src/film_pipeline/post/validators.py`, `src/film_pipeline/post/assembly_agent.py`,
  `src/film_pipeline/mcp/tools/assembly.py:45` (calls owner A and returns its issues to the
  operator). User-visible: the MCP review-cut reply can report "no issues" for a
  plan the post-phase validator would reject.
- **Candidate owner module:** `post-production` validation (one rule function
  used by the agent, the façade, and the validator).
- **Extraction sketch:** delete `src/film_pipeline/post/validators.py:PostValidator`'s duplicate
  assembly rules and have `PostValidator.validate_assembly` delegate to the
  owner; guard test asserting the two call sites return identical issue lists for
  a fixture matrix.
- **Prior art:** new.

### F-POST-07 — the delivery manifest seam has two artifact ids, two field grammars, and no in-graph producer

- **Class:** O8 (missing contract)
- **Severity:** Critical (impact 4 × drift 5 = 20)
- **Concern:** the typed interface by which a delivery package is persisted and
  discovered.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/qc.py:356` — discovery probes an id nothing
    writes — `"artifact = _pick_artifact(artifact_data, \"delivery_manifest\", \"delivery_package\")"`,
    and the runner is only reachable at phase `delivery` (`:367`
    `"({"delivery"}, _run_delivery_validators),"`).
  - `src/film_pipeline/post/delivery_packaging_agent.py:149` — the only writer
    uses the *other* id — `"artifact_id = \"delivery_package\""`.
  - `src/film_pipeline/schemas/delivery.py:10-24` — `"class DeliveryManifest(SchemaBase):"`
    with `"description=\"List of {'path': str, 'kind': str} entries.\""` (`:17`) —
    **no writer anywhere** (`grep -rn "DeliveryManifest" src/` → the schema and
    its re-export only).
  - `src/film_pipeline/schemas/delivery.py:27-35` — `"class DeliveryPackage(SchemaBase):"`
    with `"description=\"List of {'path': str, 'type': str} entries.\""` (`:34`) —
    the grammar the writer uses. No `model_fields` set comparison is offered for
    this pair, deliberately: both models are `SchemaBase` subclasses, so both
    inherit `schema_version` and it discriminates nothing; the divergence here is
    the *entry grammar* (`kind` vs `type`) and the artifact id, not the field-name
    set. (Contrast F-POST-01 and F-POST-03, where the field-name sets do differ
    and `schema_version` is called out as the shared inherited member.)
  - `src/film_pipeline/graph/nodes/wrapup.py:43-44` — `delivery_node` writes no
    artifact at all — `"def delivery_node(state: dict[str, Any]) -> dict[str, Any]:"`
    / `"return _phase_gate_updates(state, phase=\"delivery\", gate=\"final_delivery\")"`.
  - `src/film_pipeline/graph/state_schema.py:162` — the state channel uses the
    *writerless* id — `"delivery_manifest_ref: str"` — while the only writer
    emits `delivery_package` (`src/film_pipeline/post/delivery_packaging_agent.py:149`) and
    `src/film_pipeline/graph/nodes/qc.py:356` probes both. *(Added after verification.)*
- **Drift proof:** **existing divergence.** `src/film_pipeline/graph/nodes/qc.py:356` probes
  `delivery_manifest` first; the only writer produces `delivery_package`; the
  graph's `delivery_node` produces neither. So at phase `delivery` the
  `DeliveryCompletenessValidator` has no artifact to read and
  `_run_delivery_validators` (`src/film_pipeline/graph/nodes/qc.py:345-358`) is a no-op. Mutation scenario:
  delete `src/film_pipeline/schemas/delivery.py:DeliveryManifest` entirely (it has zero writers);
  nothing fails — `_pick_artifact` is string-keyed by design, so no type check
  or test binds the discovery name to the writer name.
- **Reproduce:**
  ```bash
  grep -rn "delivery_manifest" src/ | grep -v __pycache__
  grep -rn "DeliveryManifest" src/ | grep -v __pycache__
  grep -rn "delivery_manifest_ref" src/film_pipeline/graph/state_schema.py
  grep -rn "artifact_id = \"delivery" src/film_pipeline/post/delivery_packaging_agent.py
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/wrapup.py:43`, `src/film_pipeline/graph/nodes/qc.py:345-358`,
  `src/film_pipeline/mcp/tools/assembly.py:53-76`, `src/film_pipeline/validation/impl/delivery_completeness.py`,
  `src/film_pipeline/post/delivery_packaging_agent.py:134-178`. User-visible: no delivery package
  is ever persisted or validated by the pipeline, so the delivery gate
  (`src/film_pipeline/graph/_action_routing.py:60` `"\"delivery\": \"final_delivery\","`) can be approved
  with no delivery artifact in existence.
- **Candidate owner module:** `delivery` — one artifact id, one schema, one
  writer; the phase node calls it.
- **Extraction sketch:** make `delivery_node` produce the package via the
  delivery owner, delete `DeliveryManifest` (unused) or make it the single
  schema, and add a guard test asserting every artifact id probed by
  `qc._VALIDATOR_RUNNERS` has at least one `save` call site in `src/`
  (a "no orphan artifact id" sweep).
- **Prior art:** `docs/modular-architecture/audit/14-module-boundaries-and-import-law.md` **F-BOUNDARY-01**
  records the `post → validation.impl` edge ("reaching an **implementation**
  module, not a registry"; locate with
  `grep -n "reaching an \*\*implementation\*\* module" docs/modular-architecture/audit/14-module-boundaries-and-import-law.md`). `docs/modular-architecture/audit/08-validation-and-review.md` F-VR-07 (title:
  "the delivery validator is absent from both QC paths") records that
  `DeliveryCompletenessValidator` is absent from `_WORKER_NODES`
  (`src/film_pipeline/graph/subgraphs/qc.py:210-217`) and from every `qc`-phase runner set
  (`src/film_pipeline/graph/nodes/qc.py:362-366`) while being present for `phase == "delivery"`
  (`src/film_pipeline/graph/nodes/qc.py:367`) — i.e. the *dispatch* gap, not the writer gap. **Still
  present at HEAD.** New here: the orphan `delivery_manifest` id, the writerless
  `DeliveryManifest` schema, and the `delivery_manifest_ref` state channel that
  make the seam untyped rather than merely mis-dispatched.

### F-BUD-01 — five independent budget caps, no single budget state

- **Class:** O3 (split state authority)
- **Severity:** Critical (impact 5 × drift 5 = 25)
- **Concern:** "what is this project's spend cap?" — the value every spend
  decision must agree on.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/planning.py:33-35` — cap A, the artifact —
    `"budget = BudgetState("` / `"project_id=project_id,"` / `"cap_usd=cap,"`
    (input `"cap = float(cast(float, args.get(\"cap_usd\", 100.0)))"`, `:22`).
  - `src/film_pipeline/constraints/extractor.py:286-293` — cap B, from the idea
    text — `"match = re.search("` / `r"(?:budget|spend|cost|under|max)\s*(?:of|is|up\s*to)?\s*[$]?\s*(\d+(?:\.\d+)?)",`
    written into `ProjectConstraints.budget_cap_usd` (`src/film_pipeline/schemas/constraints.py:93-97`).
  - `src/film_pipeline/graph/nodes/_context.py:422-427` — cap C, from resolved
    config — `"budget = resolved_config.get(\"budget\", {})"` /
    `"for key in (\"project_cap_usd\", \"max_total_usd\"):"` /
    `"context_vars[\"budget_cap\"] = str(value)"`.
  - `src/film_pipeline/generation/ledger.py:108,264-282` — cap D, a per-batch
    ceiling computed elsewhere — `"def approve_spend(self, project_id: str, max_cost_usd: float = -1.0) -> GenerationLedger:"`
    / `"def _raise_if_over_budget("` / `"if total_cost > max_cost_usd:"`.
  - `src/film_pipeline/agents/impl/intake_agent.py:49` — cap E, the intake
    agent's own model-reported cap —
    `"budget_cap_usd=_coerce_budget_cap(data.get(\"budget_cap_usd\")),"`,
    landing on `ProjectProfile.budget_cap_usd` (`src/film_pipeline/schemas/project.py:43`
    `"budget_cap_usd: float | None = Field(default=None, ge=0, description=\"Hard spend cap.\")"`)
    and read by nothing. *(Added after verification.)*
  - Cap A's readers: **none.** `grep -rn "budget_state" src/` → the writer, the
    artifact registry spec (`src/film_pipeline/artifacts/registry.py:165`), a checkpoint field
    (`src/film_pipeline/checkpoints/manager.py:33`), and a declared agent input
    (`src/film_pipeline/agents/mvp/__init__.py:161`). No code loads the artifact to read `cap_usd`.
- **Drift proof:** **existing divergence.** Set `cap_usd=100` via MCP
  `initialize_budget`, and state an idea containing "budget of $50"; the artifact
  says 100, `ProjectConstraints.budget_cap_usd` says 50.0 (`src/film_pipeline/constraints/extractor.py:293`),
  the config-derived prompt variable says whatever profile config holds
  (`src/film_pipeline/graph/nodes/_context.py:427`), `ProjectProfile.budget_cap_usd` holds whatever the intake
  model returned (`src/film_pipeline/agents/impl/intake_agent.py:49`), and the ledger ceiling is
  `cost_estimate.estimated_cost_usd * 1.1` (`src/film_pipeline/graph/nodes/_generation_batch_planning.py:42-45`) —
  none reads another. Mutation scenario: change `_extract_budget`'s regex
  (`src/film_pipeline/constraints/extractor.py:287-291`); the MCP cap, the prompt cap, and the
  ledger ceiling are unchanged and no test fails —
  `tests/unit/constraints/test_extractor.py:92` pins only the extractor's own
  output (`"assert result.budget_cap_usd == 500"`), and
  `tests/unit/mcp/tools/test_planning.py` pins only cap A.
- **Reproduce:**
  ```bash
  grep -rn "cap_usd\b" --include=*.py src/ | grep -v __pycache__
  grep -rn "budget_cap_usd" --include=*.py src/
  grep -rn "budget_state" --include=*.py src/ tests/ | grep -v __pycache__
  .venv/bin/python -c "
  from film_pipeline.constraints import extract_constraints
  print(extract_constraints('A short film with a budget of \$50', project_id='p').budget_cap_usd)"
  ```
- **Blast radius:** `src/film_pipeline/mcp/tools/planning.py`, `src/film_pipeline/constraints/extractor.py`,
  `src/film_pipeline/graph/nodes/_context.py`, `src/film_pipeline/config/validator.py:51-63`,
  `src/film_pipeline/graph/nodes/_generation_batch_planning.py:37-47`, `src/film_pipeline/generation/ledger.py`. User-visible:
  the project's stated cap is enforced by whichever cap the calling surface
  happens to compute; a user who sets a cap through one surface is not capped on
  another.
- **Candidate owner module:** `budget` — one `BudgetState` document with one
  writer and one `cap_for(project_id)` accessor; every cap source (A–E) is read
  through it.
- **Extraction sketch:** move cap resolution behind a single
  `budget.cap_for(project_id)` that reads the `budget_state` artifact (falling
  back to `ProjectConstraints.budget_cap_usd` and then config, in a documented
  order); delete `context_vars["budget_cap"]` derivation
  (`src/film_pipeline/graph/nodes/_context.py:422-427`) and have the ceiling in
  `src/film_pipeline/graph/nodes/_generation_batch_planning.py:37-47` come from that accessor; guard test
  asserting every cap source (A–E) returns the same number for one fixture.
- **Prior art:** `docs/modular-architecture/audit/06-generation-runtime-and-ledger.md` **F-GEN-10** already owns
  the *two cost models compared by the gate* and the shot-duration default
  re-derivation; its writer-table row — locate it with
  `grep -n "Single writer, but the \*ceiling\*" docs/modular-architecture/audit/06-generation-runtime-and-ledger.md` —
  records `estimated_cost_usd` as a single writer with a divergent ceiling.
  **That claim is not re-filed here.** New in F-BUD-01: the five *caps*
  (artifact / constraints / project profile / config / ceiling) as an inventory,
  and the proof that cap A has zero readers.
  *Anchor discipline: `docs/` is untracked (`.gitignore:2`) and the sibling
  audits were revised concurrently during this program — F-GEN-10's heading sat
  at `:463` when this audit was written, `:467` at verification, and `:518` at
  this revision — so sibling references below are by finding id plus a grep,
  never by a frozen line number.*

### F-BUD-02 — budget refusal is re-derived at eight sites; only one can refuse, and the graph's gate is inert

- **Class:** O2 (duplicated invariant enforcement)
- **Severity:** Critical (impact 4 × drift 5 = 20)
- **Concern:** the policy that blocks or refuses generation spend when it would
  exceed a cap.
- **De-facto owners:**
  - `src/film_pipeline/generation/ledger.py:264-277` — **G1, the only site that
    refuses** — `"def _raise_if_over_budget("` /
    `"total_cost = sum(r.estimated_cost_usd for r in rows if r.status == GenerationStatus.SUBMITTED)"` /
    `"if total_cost > max_cost_usd:"` → `raise ValueError(...)` (`:278-282`).
  - `src/film_pipeline/graph/nodes/_generation_batch_planning.py:30-55` — **G2,
    derives the ceiling** — `"max_cost_usd = float(raw_cost) * 1.1"` (`:45`),
    converts `ValueError` into a blocking issue —
    `"\"code\": \"generation_budget_exceeded\","` (`:52`).
  - `src/film_pipeline/mcp/tools/generation/planning.py:146-165` — **G3, defaults
    to no cap** — `"# Budget gate: the manager rejects the batch when estimated cost exceeds it."`
    / `"max_cost = _parse_max_cost_usd(args)"` (`:159-160`), where
    `"max_cost_raw = args.get(\"max_cost_usd\", -1)"` (`:48`) and `-1.0` means
    "no limit" (`src/film_pipeline/generation/ledger.py:274-275`).
  - `src/film_pipeline/app/services/_generation_ops.py:70-84` — **G4, also
    defaults to no cap** — `"max_cost_usd: float = -1.0,"` (`:73`) /
    `"executor.approve_spend(project_id_value, max_cost_usd=max_cost_usd)"` (`:82`),
    reached from `src/film_pipeline/app/services/operator.py:354-360`.
  - `src/film_pipeline/graph/_action_routing.py:238-252` — **G5, inert** —
    `"def _budget_blocked_result(state: dict[str, Any]) -> RouterResult | None:"` /
    `"if not ostate.is_budget_blocked(state):"` / `"\"reason\": \"budget threshold exceeded\","`,
    consuming `src/film_pipeline/graph/orchestrator_state.py:477-479`
    `"return cast(bool, get_budget_snapshot(state).get(\"threshold_exceeded\", False))"`.
  - `src/film_pipeline/graph/orchestrator_validators/planning_gates.py:99-127` —
    **G6, a placeholder test, not a cap check** —
    `"def _cost_gate_issues(cost_estimate: Any) -> list[dict[str, Any]]:"` /
    `"if total_cost == 0.0 and clip_count > 0:"` (`:119`).
  - `src/film_pipeline/config/validator.py:51-62` — **G7, warning only** —
    `"cap: float = float(budget.get(\"project_cap_usd\", 0))"` /
    `"if cap < 10 and shot_count > 20:"` / `"severity=\"warning\","`.
  - `src/film_pipeline/agents/prompt_templates/defaults/production.py:198` —
    **G8, advisory text** — `"\"Budget cap: {budget_cap}\\n\""` fed by
    `src/film_pipeline/graph/nodes/_context.py:427`.
- **Drift proof:** **existing divergence between the two spend surfaces.** The
  graph surface (G2) always passes a ceiling derived from the planner's own
  `cost_estimate` artifact; the MCP surface (G3) and the operator surface (G4)
  pass `-1.0` unless the caller supplies `max_cost_usd`, so
  `_raise_if_over_budget` returns immediately (`"if max_cost_usd < 0:"` /
  `"return"`, `src/film_pipeline/generation/ledger.py:274-275`). Two surfaces of the same "approve spend"
  operation therefore enforce different policies. G5 is unreachable in
  production: `update_budget_snapshot` (`src/film_pipeline/graph/orchestrator_state.py:449`) has **zero**
  non-test callers, the channel's own registry entry says so —
  `src/film_pipeline/graph/orchestrator_state.py:137` `"\"dormant writer; wiring decided in D13/P1 (budget recording)\","` —
  and `ensure_orchestrator_state` seeds `"threshold_exceeded": False`
  (`src/film_pipeline/graph/orchestrator_state.py:529-535`), so `is_budget_blocked` is always `False`.
  Mutation scenario: delete `_budget_blocked_result` and its dispatch
  (`src/film_pipeline/graph/_action_routing.py:378`); only its own unit test fails
  (`tests/unit/graph/test_router_blockers.py:43` calls
  `update_budget_snapshot` directly to manufacture the flag), and no production
  test changes behaviour.
- **Reproduce:**
  ```bash
  grep -rn "max_cost_usd" --include=*.py src/ | grep -v __pycache__
  grep -rn "update_budget_snapshot" --include=*.py src/ tests/
  grep -rn "_budget_blocked_result\|is_budget_blocked" --include=*.py src/
  .venv/bin/python -c "
  from film_pipeline.graph import orchestrator_state as o
  s={}; o.ensure_orchestrator_state(s); print(o.is_budget_blocked(s))"
  ```
- **Blast radius:** `src/film_pipeline/generation/ledger.py`,
  `src/film_pipeline/graph/nodes/_generation_batch_planning.py`,
  `src/film_pipeline/mcp/tools/generation/planning.py`, `src/film_pipeline/app/services/_generation_ops.py`,
  `src/film_pipeline/app/services/operator.py`, `src/film_pipeline/graph/_action_routing.py`,
  `src/film_pipeline/graph/orchestrator_state.py`, `src/film_pipeline/config/validator.py`. User-visible: spend can
  be approved through MCP/operator with no cap at all; the router's
  "budget exceeded → escalate to human" rule can never fire.
- **Candidate owner module:** `budget` — one `authorize_spend(project_id, batch)`
  that resolves the cap and raises a typed `BudgetExceeded`; every surface calls
  it and no surface takes a raw `max_cost_usd=-1.0`.
- **Extraction sketch:** move the G1 check behind the budget owner, make
  `max_cost_usd` non-optional (delete the `-1.0` default from
  `src/film_pipeline/mcp/tools/generation/planning.py:48`, `src/film_pipeline/app/services/_generation_ops.py:73`,
  `src/film_pipeline/generation/ledger.py:108`), wire `update_budget_snapshot` from the ledger's
  approve/poll transitions or delete G5 and its channel, and add a single guard
  test that drives both the graph and MCP approve paths against the same fixture
  and asserts identical outcomes.
- **Prior art:** `documentation/reviews/arch-lens-dataflow.md:32` records
  `budget_snapshot` as having "none (tests only)" writers and "feeds dead router
  rules (F-6)"; `documentation/reviews/arch-review-critic.md:36` confirms the
  observation. `docs/modular-architecture/audit/06-generation-runtime-and-ledger.md` F-GEN-10 covers the two cost
  *models*. **Still present at HEAD.** New here: the eight-site inventory with
  which sites can actually refuse, and the G2-vs-G3/G4 policy divergence between
  the graph and MCP surfaces of the same operation.

### F-BUD-03 — no spend is ever recorded; every "cost" the system reports is an estimate and `remaining_usd` always equals the cap

- **Class:** O3 (split state authority)
- **Severity:** Critical (impact 4 × drift 5 = 20)
- **Concern:** the authoritative record of money actually spent.
- **De-facto owners:**
  - `src/film_pipeline/schemas/budget.py:40-42` — the fields meant to hold it —
    `"spent_usd: float = Field(default=0.0, ge=0)"` /
    `"per_phase_spent_usd: dict[str, float] = Field(default_factory=dict)"`.
  - `src/film_pipeline/mcp/tools/planning.py:36` — the only write, at
    initialization — `"spent_usd=0.0,"`.
  - `src/film_pipeline/schemas/budget.py:23-32` — the unused ledger of spends —
    `"class SpendRecord(MutableSchemaBase):"` with
    `"amount_usd: float = Field(ge=0)"` (`:30`); **zero writers**
    (`grep -rn "SpendRecord(" src/` → nothing).
  - `src/film_pipeline/schemas/generation.py:68` — the unused actual-cost field —
    `"actual_cost_usd: float | None = None"`; grep finds only the declaration and
    one test string.
  - `src/film_pipeline/generation/executor.py:333` — the estimate presented under
    a spend label — `"\"cost_usd\": row.estimated_cost_usd,"`, and
    `src/film_pipeline/generation/executor.py:340-344` aggregates the same estimates as
    `"def estimated_cost(self, project_id: str) -> float:"`.
- **Drift proof:** **existing divergence.** `BudgetState.remaining_usd`
  (`src/film_pipeline/schemas/budget.py:46-48` `"return max(0.0, self.cap_usd - self.spent_usd)"`)
  is returned to the operator as a live budget figure by
  `src/film_pipeline/mcp/tools/planning.py:55` `"return _ok(budget_state_ref=ref, cap_usd=cap, remaining_usd=budget.remaining_usd)"`,
  but `spent_usd` is never incremented, so `remaining_usd == cap_usd` forever.
  Meanwhile `src/film_pipeline/mcp/tools/state.py:57` exposes the (also never-written)
  orchestrator snapshot, and the operator UI sees `"cost_usd"` from
  `src/film_pipeline/generation/executor.py:333`. Mutation scenario: complete 100 generation rows through
  `executor.poll` (`:257,293,399` all call `update_row` with lifecycle fields
  only — no cost key); `spent_usd`, `per_phase_spent_usd`, `SpendRecord`, and the
  orchestrator snapshot are all unchanged and no test fails — grep for a writer
  of any of the four finds only the `0.0` initializer.
- **Reproduce:**
  ```bash
  grep -rn "spent_usd" --include=*.py src/
  grep -rn "SpendRecord(" --include=*.py src/ tests/
  grep -rn "actual_cost_usd" --include=*.py src/ tests/
  .venv/bin/python -c "
  from film_pipeline.schemas.budget import BudgetState
  b = BudgetState(project_id='p', cap_usd=100.0); print('remaining', b.remaining_usd)"
  ```
- **Blast radius:** `src/film_pipeline/schemas/budget.py`, `src/film_pipeline/mcp/tools/planning.py`,
  `src/film_pipeline/mcp/tools/state.py:57`, `src/film_pipeline/app/services/operator.py:251`,
  `src/film_pipeline/generation/executor.py`, `src/film_pipeline/graph/orchestrator_state.py`. User-visible: every
  spend figure the operator sees is a pre-flight estimate; the project cap is
  never consumed, and a resumed project reports full headroom after spending it.
- **Candidate owner module:** `budget` — a `record_spend(project_id, phase, usd,
  source)` writer that updates `spent_usd`, `per_phase_spent_usd`, and appends a
  `SpendRecord` in one transaction, called from the delivered/failed ledger
  transitions.
- **Extraction sketch:** add the single `record_spend` writer, call it from
  `src/film_pipeline/generation/executor.py` where a row reaches a terminal state
  (`:257,293,399`), rename `status_rows`'s `"cost_usd"` label to
  `"estimated_cost_usd"` (`src/film_pipeline/generation/executor.py:333`), and add a property test asserting
  `spent_usd == sum(SpendRecord.amount_usd)` and
  `remaining_usd == cap_usd - spent_usd`.
- **Prior art:** `documentation/reviews/arch-lens-observability.md:161,164`
  already states: "`BudgetState.spent_usd` is initialized to `0.0`
  (`src/film_pipeline/mcp/tools/planning.py:29`) and **never incremented** anywhere" and proposes
  the `record_cost(...)` seam; `documentation/reviews/arch-review-critic.md:36`
  marks it verified ✅; `tests/unit/config/test_config_contract.py:85` even
  encodes the fact in a test name ("actual_cost_usd is never …"). **Still present
  at HEAD.** New here: the `per_phase_spent_usd`/`SpendRecord` zero-writer proof
  (the prior reviews name only `spent_usd` and `actual_cost_usd`) and the
  `remaining_usd == cap_usd` consequence as an executed repro.

### F-BUD-04 — `budget_cap` is derived twice and the planner reads a state key that is never written

- **Class:** O8 (missing contract). Re-classed from O5 after verification: the
  operative defect is a writerless state key with no declared contract, not a
  branch that re-derives a policy (the two derivations are on different sides of
  the prompt seam).
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** which cap value reaches the generation-planning prompt and the
  planner's reasoning.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/_context.py:422-427` — derivation 1, prompt
    template context — `"budget = resolved_config.get(\"budget\", {})"` /
    `"for key in (\"project_cap_usd\", \"max_total_usd\"):"` /
    `"context_vars[\"budget_cap\"] = str(value)"`.
  - `src/film_pipeline/agents/impl/gen_planner_agent.py:53-58` — derivation 2,
    the agent's own `prepare` — `"budget_cap = str(state.get(\"budget_cap\", \"unlimited\"))"`
    / `"\"budget_cap\": budget_cap,"`.
  - `src/film_pipeline/agents/base.py:54-56` — why derivation 2 is dead —
    `"# prepare() runs as the lifecycle step; the graph node layer assembles"`
    / `"# the actual prompt context, so its inputs are not consumed here."` /
    `"self.prepare(state, kb_context, task)"`.
  - `src/film_pipeline/agents/prompt_templates/defaults/production.py:198` — the
    only consumer of derivation 1 — `"\"Budget cap: {budget_cap}\\n\""`.
- **Drift proof:** **existing divergence.** `state["budget_cap"]` is never
  written by any module (`grep -rn "budget_cap" src/` → writers are
  `src/film_pipeline/constraints/extractor.py:154` for the *different* key `budget_cap_usd`,
  `src/film_pipeline/graph/nodes/_context.py:427` for the *context var* `budget_cap`, and
  `src/film_pipeline/agents/impl/gen_planner_agent.py:53,58` which only reads it), so the planner's branch
  always takes the default `"unlimited"`. The test that covers it manufactures
  the key: `tests/unit/agents/test_gen_planner_agent.py:140`
  `"\"budget_cap\": \"25.0\","` and `:149` asserts it round-trips. Mutation
  scenario: change the config key list at `src/film_pipeline/graph/nodes/_context.py:424` from
  `("project_cap_usd", "max_total_usd")` to a new name; the prompt silently loses
  the cap (the placeholder default is `""`, `src/film_pipeline/graph/nodes/_agent_prompt_context.py:46`) while
  `src/film_pipeline/config/validator.py:55` keeps reading `project_cap_usd`, and no test fails —
  `tests/unit/config/test_config_contract.py:394-401` pins the `src/film_pipeline/graph/nodes/_context.py`
  behaviour, and no test asserts the rendered planning prompt contains a cap.
- **Reproduce:**
  ```bash
  grep -rn "budget_cap\b" --include=*.py src/ tests/ profiles/ 2>/dev/null
  grep -rn "budget_cap" -A 3 src/film_pipeline/agents/impl/gen_planner_agent.py
  ```
- **Blast radius:** `src/film_pipeline/graph/nodes/_context.py`, `src/film_pipeline/agents/impl/gen_planner_agent.py`,
  `src/film_pipeline/agents/prompt_templates/defaults/production.py`, `src/film_pipeline/config/validator.py:55`.
  User-visible: a user who writes "budget of $50" into the idea gets a planner
  prompt that says "Budget cap: " (empty) while
  `ProjectConstraints.budget_cap_usd` holds 50.0 and is never shown to the model.
- **Candidate owner module:** `budget` (owns the accessor; the prompt builder
  consumes it) — no second `budget_cap` vocabulary.
- **Extraction sketch:** delete `src/film_pipeline/agents/impl/gen_planner_agent.py:53,58` (dead read) and
  route the template variable through the same `budget.cap_for(project_id)`
  accessor as F-BUD-01; add a guard test that renders the `provider-planning-agent`
  prompt for a project with a known cap and asserts the number appears.
- **Prior art:** `docs/modular-architecture/audit/06-generation-runtime-and-ledger.md` notes
  `src/film_pipeline/mcp/tools/planning.py` as "a third plan/cost builder" (find it with
  `grep -n "third plan/cost builder" docs/modular-architecture/audit/06-generation-runtime-and-ledger.md`). The dead
  `state["budget_cap"]` read and the empty prompt cap are **new**;
  `documentation/audit-findings.md:73`
  ("`BaseAgent.run` ignores the output of `prepare`") is the enabling condition
  and is still present at HEAD.

### F-BUD-05 — the number-word vocabulary and the scene-count grammar are defined twice

- **Class:** O1 (duplicated normative model)
- **Severity:** High (impact 3 × drift 5 = 15)
- **Concern:** how a user's spoken number ("twelve scenes") becomes a constraint
  value.
- **De-facto owners:**
  - `src/film_pipeline/constraints/_keywords.py:13-34` — the constraint
    extractor's table — `"_NUMBER_WORDS: dict[str, int] = {"` … `"\"twenty\": 20,"`.
  - `src/film_pipeline/graph/nodes/_shared.py:29-50` — the graph's table —
    `"_NUMBER_WORDS: dict[str, int] = {"` … `"\"twenty\": 20,"` (byte-identical:
    `A == B` → `True`, 20 entries each).
  - `src/film_pipeline/constraints/extractor.py:167-185` — grammar 1 —
    `"def _extract_number(self, text: str, unit_words: tuple[str, ...]) -> int | None:"`
    with `"digit_match = re.search(rf\"(\\d+)\\s*[-]?\\s*(?:{unit_pattern})\\b\", text, re.IGNORECASE)"`
    (`:172`) and the word loop (`:180-183`).
  - `src/film_pipeline/graph/nodes/_shared.py:69-80` — grammar 2 —
    `"digit_match = re.search(r\"(\\d+)\\s*[-]?\\s*(?:scene|scenes)\\b\", idea, re.IGNORECASE)"`
    (`:69`) and `"pattern = rf\"\\b{word}\\b\\s*[-]?\\s*(?:scene|scenes)\\b\""` (`:78`).
- **Drift proof:** mutation scenario — add `"thirty": 30` to
  `src/film_pipeline/constraints/_keywords.py:33` (the table the extractor iterates at
  `src/film_pipeline/constraints/extractor.py:180`); `src/film_pipeline/graph/nodes/_shared.py:49` keeps the 20-word table, so
  `_extract_target_scene_count({"idea": "thirty scenes"})` returns `None` while
  `extract_constraints("thirty scenes", ...).target_scene_count` returns 30. No
  test fails: `tests/unit/constraints/test_extractor.py` pins only the
  extractor, and `tests/unit/graph/test_extract_target_scene_count.py:19-20`
  covers only `"Twelve scenes"` / `"five scenes"` (words already in both tables).
  Executed equality check today: `A == B` is `True` — the duplication is latent,
  which is exactly the drift condition (two sites, no test binding them).
- **Reproduce:**
  ```bash
  grep -rn "_NUMBER_WORDS" src/ | grep -v __pycache__
  .venv/bin/python -c "
  from film_pipeline.constraints._keywords import _NUMBER_WORDS as A
  from film_pipeline.graph.nodes._shared import _NUMBER_WORDS as B
  print('equal', A == B, len(A), len(B))"
  .venv/bin/python -c "
  from film_pipeline.constraints import extract_constraints
  from film_pipeline.graph.nodes._shared import _extract_target_scene_count
  print('extractor', extract_constraints('twelve scenes', project_id='p').target_scene_count,
        '| graph', _extract_target_scene_count({'idea': 'twelve scenes'}))"
  ```
- **Blast radius:** `src/film_pipeline/constraints/_keywords.py`, `src/film_pipeline/graph/nodes/_shared.py`,
  `src/film_pipeline/graph/nodes/prep.py:166` (`"user_scene_count = _extract_target_scene_count(state) or _extract_target_scene_count(updates)"`),
  `src/film_pipeline/graph/scope_contract.py:90-93` (which honours `user_scene_count`).
  User-visible: the Story Scope Contract's scene floor can silently differ
  depending on which grammar ran, changing `min_scene_count` and therefore the
  development/script gates.
- **Candidate owner module:** `constraints` — the numeric vocabulary and the
  number/unit grammar are constraint-extraction concerns; `graph` consumes them.
- **Extraction sketch:** export `_NUMBER_WORDS` and a
  `first_number_for_unit(text, units)` helper from `constraints`, delete
  `src/film_pipeline/graph/nodes/_shared.py:29-82`, and add a duplicate-normative-model guard test
  asserting `grep -c "_NUMBER_WORDS: dict" src/ == 1` plus a parity test over a
  word list that includes at least one value beyond the shared prefix.
- **Prior art:** new.

### F-BUD-06 — a sixth budget-cap vocabulary: `context_packets` reads a plain `budget_snapshot` key the owner never writes *(added after verification)*

- **Class:** O7 (leaked internals) — a non-owning module reaches for
  orchestrator-owned budget state by an un-namespaced key, and reaches for the
  wrong key; the O8/O5 readings (missing contract / re-derived cap string) also
  apply.
- **Severity:** High (impact 2 × drift 5 = 10)
- **Concern:** which state key carries the cached budget snapshot to readers.
- **De-facto owners:**
  - `src/film_pipeline/graph/orchestrator_state.py:59` — the owner's key —
    `"_BUDGET_SNAPSHOT = f\"{_ORCH_NS}__budget_snapshot\""`, i.e.
    `_orchestrator__budget_snapshot` (declared `src/film_pipeline/graph/state_schema.py:196`
    `"_orchestrator__budget_snapshot: dict[str, Any]"`).
  - `src/film_pipeline/graph/context_packets.py:121-123` — the reader's key —
    `"budget = state.get(\"budget_snapshot\", {})"` /
    `"cap = budget.get(\"cap_usd\", 0) if isinstance(budget, dict) else 0"` /
    `"parts.append(f\"Budget cap: ${cap}\")"`.
  - `src/film_pipeline/graph/state_schema.py:177` — a second, *declared but
    unused* plain channel — `"budget_snapshot: dict[str, object]"` — filled on
    the operator path from the namespaced accessor
    (`src/film_pipeline/app/services/operator.py:251` `"budget_snapshot=dict(ostate.get_budget_snapshot(state)),"`
    into `src/film_pipeline/app/services/models.py:64`), never from graph state.
  - `tests/unit/graph/test_context_packets.py:175` — the only writer of the key
    the reader looks for — `"\"budget_snapshot\": {\"cap_usd\": 42},"`.
- **Drift proof:** **existing divergence.** The reader's key is never written
  (`grep -rn '"budget_snapshot"' src/ tests/` → the read at
  `src/film_pipeline/graph/context_packets.py:121` and the test fabrication at `tests/unit/graph/test_context_packets.py:175`
  only), so `cap` is always `0` and the packet renders `Budget cap: $0` — a
  sixth cap string that agrees with none of caps A–E. Reachability is live:
  `src/film_pipeline/graph/nodes/_agent_prompt_context.py:109-116` runs
  `"builder = PHASE_BUILDERS.get(phase)"` then
  `"context_vars[\"scoped_context\"] = builder(state, services)"`, and
  `PHASE_BUILDERS["gen_planning"] = build_gen_planning_context`
  (`src/film_pipeline/graph/context_packets.py:135`). Mutation scenario: rename the channel at
  `src/film_pipeline/graph/orchestrator_state.py:59` (or delete the plain field at `src/film_pipeline/graph/state_schema.py:177`);
  `src/film_pipeline/graph/context_packets.py:121` keeps reading the plain key and no test fails — the
  one covering test supplies the key itself, so it passes either way.
- **Reproduce:**
  ```bash
  grep -rn '"budget_snapshot"' src/ tests/ | grep -v __pycache__
  sed -n '59p' src/film_pipeline/graph/orchestrator_state.py
  sed -n '177p;196p' src/film_pipeline/graph/state_schema.py
  grep -rn "scoped_context" src/
  grep -n "budget_snapshot" src/film_pipeline/graph/context_packets.py
  ```
- **Blast radius:** `src/film_pipeline/graph/context_packets.py`, `src/film_pipeline/graph/nodes/_agent_prompt_context.py`,
  `src/film_pipeline/graph/orchestrator_state.py`, `src/film_pipeline/graph/state_schema.py:177`. **Impact is
  bounded today:** no prompt template contains `{scoped_context}`
  (`grep -rn "scoped_context" src/` → only the assignment at
  `src/film_pipeline/graph/nodes/_agent_prompt_context.py:116`), so the wrong string is computed and dropped.
  The consequence is latent, not cosmetic-by-accident: the moment any template
  consumes `{scoped_context}`, every gen-planning prompt advertises a $0 cap.
- **Candidate owner module:** `budget` — publish the snapshot under one declared
  key and expose an accessor; `context_packets` consumes that accessor, and the
  plain `src/film_pipeline/graph/state_schema.py:177` field is deleted or namespaced with it.
- **Extraction sketch:** replace `src/film_pipeline/graph/context_packets.py:121-123` with
  `ostate.get_budget_snapshot(state)` from the owning module, delete the plain
  `budget_snapshot` TypedDict field (`src/film_pipeline/graph/state_schema.py:177`), and add a guard test
  that builds the gen-planning packet from real orchestrator state (no fabricated
  key) and asserts the cap matches `cap_for(project_id)`.
- **Prior art:** new. Not covered by F-BUD-01/02 (which own the caps and the
  enforcement sites) or by `documentation/reviews/arch-lens-dataflow.md:32` (which records the
  namespaced channel's missing writer, not this mis-keyed reader).

### 4.1 Unverified hypotheses (not findings)

- **U-12-01.** `src/film_pipeline/post/audio_design_agent.py`, `src/film_pipeline/post/subtitle_agent.py`,
  `src/film_pipeline/post/transition_agent.py`, `src/film_pipeline/post/validators.py` appear to be dead code
  (no production caller). This is *incompleteness*, which §1.3 explicitly
  excludes from distributed-ownership findings; recorded only so the ownership
  map can mark them. Evidence: `grep -rn "AudioDesignAgent\|SubtitleAgent\|TransitionAgent\|PostValidator" src/`
  returns only their own definitions, `src/film_pipeline/post/__init__.py`, and
  `src/film_pipeline/post/validators.py`.
- **U-12-02.** `src/film_pipeline/config/validator.py:55` reads `resolved["budget"]["project_cap_usd"]`
  and `src/film_pipeline/graph/nodes/_context.py:424` reads `("project_cap_usd", "max_total_usd")`, but no
  schema in `src/` declares a `budget` block for the resolved config. I did not
  find the profile defaults that define it; the field names may be unregistered
  config (a config-cluster question, not this cluster's).

---

## 5. Clean concerns (with the guard test or the noted gap)

| Concern | Single owner | Evidence | Guard test / gap |
|---|---|---|---|
| Phase vocabulary inside `post/` | `schemas._base.FilmPhase` | `src/film_pipeline/post/assembly_agent.py:125` `"phase=FilmPhase(\"post\"),"`, `src/film_pipeline/post/subtitle_agent.py:101`, `src/film_pipeline/post/delivery_packaging_agent.py:170` `"phase=FilmPhase(\"delivery\"),"` — all values come from the enum; no local phase literals | `docs/modular-architecture/audit/01-phase-model-and-transitions.md:62` records the same; `tests/unit/post/**` covers it indirectly. Gate green. |
| Transition vocabulary | `src/film_pipeline/schemas/_base.py:253` `"TRANSITION_TYPES: tuple[str, ...] = (\"cut\", \"dissolve\", \"fade_in\", \"fade_out\", \"crossfade\")"` | `src/film_pipeline/post/transition_agent.py:8` `"from film_pipeline.schemas._base import TRANSITION_TYPES as TRANSITION_TYPES"` with the explanatory comment at `:10-12` | **Explicit guard test:** `tests/unit/post/test_post.py:86-91` `"def test_transition_types_matches_canonical_home(self) -> None:"` asserts equality with the canonical home; `tests/unit/validation/test_assembly_transition_vocabulary.py` pins the value set and `LEGACY_TRANSITION_ALIASES` end-to-end through `AssemblyValidator.run`. |
| Constraint extraction (text → `ProjectConstraints`) | `src/film_pipeline/constraints/extractor.py` (`ConstraintExtractor.extract`, `:112-135`) | Only one call site in all of `src/`: `src/film_pipeline/graph/nodes/prep.py:49-53` `"return extract_constraints("` / `"text=idea_text,"` / `"hints=constraints_hints if isinstance(constraints_hints, dict) else {},"`. No MCP tool extracts: `src/film_pipeline/mcp/tools/intake.py:22` stores raw data only — `"active[\"constraints_hints\"] = user_constraints"`. `grep -rn "ProjectConstraints(" src/` → extractor + the prep re-validation only. | `tests/unit/constraints/test_extractor.py` (191 lines of facet coverage, e.g. `:92`), `tests/unit/graph/test_nodes_constraints.py` pins the hints→state path. |
| Constraint merge order (hints > extracted > profile) | `src/film_pipeline/constraints/extractor.py:87-103` (`_merge_hints`) + `src/film_pipeline/graph/nodes/prep.py:91-102` + `:130` | The two merges implement *different* rules (explicit-hint overlay; profile backfill), and `src/film_pipeline/graph/nodes/prep.py:130` `"final_constraints = ProjectConstraints(**merged_constraints)"` re-validates through the typed model before persisting (`:131`). One artifact writer: `"constraints_ref"`. | **Gap:** the `constraints` state channel is untyped — `src/film_pipeline/graph/state_schema.py:145` `"constraints: dict[str, Any] | None"` — so the seam relies on `model_dump`/re-validate rather than a declared type. No boundary test. Recorded as a gap, not a finding (no divergent behaviour found). |
| Provider pricing | `src/film_pipeline/providers/pricing.py:36` `"PROVIDER_PRICING: dict[str, _PricingEntry] = {"` | Every adapter delegates rather than restating rates: `src/film_pipeline/providers/adapters/veo_fast.py:69-71` `"from film_pipeline.providers.pricing import rate_for"` / `"return duration * rate_for(\"veo-3.1-fast\")"`; `src/film_pipeline/providers/adapters/seedance_openrouter.py:166-168`; `src/film_pipeline/providers/adapters/imagen4_gemini.py:165-168`; the planner prompt is generated from the same table (`src/film_pipeline/providers/pricing.py:116-139`, consumed at `src/film_pipeline/graph/nodes/_agent_prompt_context.py:51-53`). | `src/film_pipeline/providers/pricing.py:1-8` documents the prior divergence it fixed; `docs/modular-architecture/audit/06-generation-runtime-and-ledger.md` F-GEN-10 pins the remaining ceiling mismatch (not re-filed here). |
| Generation asset delivery (media → project tree) | `src/film_pipeline/generation/executor_delivery.py` (`deliver_completed_job`, `:25-41`) | Path ownership delegated to storage: `:53-55` `"Path ownership belongs to the storage core; this only asks it where to put"` / `"the media."` / `"return ProjectStorage.for_root(root).media_dir(project_id, scene_id, shot_id)"`; one manifest writer (`:118-119`). | `tests/unit/generation/**`; no budget/assembly coupling in this module (`grep` clean). |

**Post/delivery lifecycle ownership (the scope-A question).** The post-production
phase lifecycle is owned **de facto by `graph`, not by `post/`**:
`src/film_pipeline/graph/_action_routing.py:59` sets the gate (`"\"post\": \"assembly\","`),
`src/film_pipeline/graph/edges.py:50-51` sets the successors (`"\"qc\": \"post\","` / `"\"post\": \"delivery\","`),
`src/film_pipeline/graph/graph.py:65,94,116` binds the node, and `src/film_pipeline/graph/nodes/wrapup.py:19-40`
executes it. `post/` is reached from exactly two places, both in `mcp/`
(`src/film_pipeline/mcp/tools/assembly.py:37,59`). The delivery artifact set is owned **nowhere**:
`src/film_pipeline/graph/nodes/wrapup.py:43-44` writes no artifact, the MCP export path never persists, and the
validator's discovery id matches no writer (F-POST-07).

---

## 6. Candidate module boundaries

### 6.1 `post-production` (assembly + post artifacts)

- **Responsibility (one sentence):** given the shot matrix and delivered media,
  produce the single review-cut/assembly artifact that downstream validation and
  delivery consume. **Does not:** own the phase lifecycle, own phase gates, own
  the transition vocabulary (consumes `schemas._base`), or run validators
  directly.
- **Public contract:** one `AssemblyAgent` class; `build(state) -> AssemblyManifest`;
  persists `assembly_manifest` through one save function. Contract types live in
  `src/film_pipeline/schemas/assembly.py` only.
- **Owns:** the assembly manifest artifact id and its only writer (F-POST-01/05);
  the clip-order/transition construction rules.
- **Deletes:** `src/film_pipeline/post/assembly_agent.py`'s dataclass model and duplicate class
  (F-POST-01/03); `src/film_pipeline/post/validators.py`'s duplicate assembly rules (F-POST-06).
- **Guard tests:** exactly one `class AssemblyAgent` in `src/`; the
  `assembly_manifest` artifact id has exactly one `save` call site; every
  `post/` model name resolves to a `schemas/` model.

### 6.2 `delivery` (package + completeness policy)

- **Responsibility:** define what a delivery package must contain, assemble it,
  persist it under one artifact id, and answer "is it complete?" once. **Does
  not:** validate its own output (that is `validation`, consuming the same
  table), own the `delivery` phase node, or fabricate validator input dicts.
- **Public contract:** `REQUIRED_DELIVERY_ARTIFACTS` (one declarative table);
  `DeliveryPackage` (one schema in `src/film_pipeline/schemas/delivery.py`);
  `build_package(...) -> DeliveryPackage`; `persist(package) -> ref`;
  `is_complete` derived from the table.
- **Owns:** the completeness rule (F-POST-04), the artifact id and its writer
  (F-POST-07), the required-artifact grammar.
- **Deletes:** `DeliveryManifest` (writerless, F-POST-07);
  `_completeness_check_artifact` (F-POST-04);
  `src/film_pipeline/validation/impl/delivery_completeness.py`'s private `REQUIRED_DELIVERY_FILES`
  (reads the owner's table). The `post → validation.impl` import
  (F-BOUNDARY-01 in `docs/modular-architecture/audit/14-module-boundaries-and-import-law.md`) disappears with it.
- **Guard tests:** `is_complete` agrees with `DeliveryCompletenessValidator` on a
  fixture matrix; every artifact id probed by `src/film_pipeline/graph/nodes/qc.py` has a writer in
  `src/`.

### 6.3 `constraints`

- **Responsibility:** turn user intent (idea text + explicit hints) into one
  validated `ProjectConstraints`. **Does not:** own the scope contract
  (`graph.scope_contract` consumes the scene count), render prompts
  (`graph.nodes._agent_prompt_context` consumes `render_constraints`), or store
  state.
- **Public contract:** `extract_constraints(text, project_id, hints)`,
  `render_constraints`, `ProjectConstraints`, `ConstraintExtractor`, and (new)
  the numeric vocabulary + `first_number_for_unit` helper (F-BUD-05).
- **Owns:** the extraction grammar and keyword tables (single owner today, §5).
- **Absorbs:** `src/film_pipeline/graph/nodes/_shared.py:29-82` (`_NUMBER_WORDS`,
  `_extract_target_scene_count`) — F-BUD-05.
- **Budget-cap boundary (resolves the `constraints` ↔ `budget` collision raised
  in `docs/modular-architecture/reviews/verify-12.md` §6):** `constraints` *extracts and types* the user-stated cap
  — it is the only writer of `ProjectConstraints.budget_cap_usd`
  (`src/film_pipeline/schemas/constraints.py:93-97`; `src/film_pipeline/constraints/extractor.py:154`) — and **does
  not** own cap precedence, `BudgetState`, or enforcement. `budget` owns
  resolution/precedence and is the only writer of `BudgetState`;
  `ProjectConstraints.budget_cap_usd` is one *input* to that resolution
  (F-BUD-01 cap B), never a second authority. The split in one line:
  `constraints` answers "what did the user say?", `budget` answers "what cap
  applies, and may this spend proceed?".
- **Guard tests:** one `_NUMBER_WORDS` table in `src/`; extractor and
  scope-contract scene counts agree on a shared fixture corpus; the extracted
  `budget_cap_usd` is read only through `budget.cap_for(project_id)` (no direct
  consumer of the constraint field).

### 6.4 `budget` (cap resolution + spend authorization + spend ledger)

- **Responsibility:** own one `BudgetState`, resolve the cap once, authorize
  spend, and record actual spend. **Does not:** estimate provider costs
  (`providers.pricing`), own generation ledger rows (`generation.ledger`), or
  route the graph (it raises/returns a verdict; `graph` reacts).
- **Public contract:** `cap_for(project_id) -> float`;
  `authorize_spend(project_id, batch) -> None` (raises `BudgetExceeded`);
  `record_spend(project_id, phase, usd, source)`; `BudgetState`, `SpendRecord`.
- **Owns:** cap resolution and precedence across caps A–E (F-BUD-01) — with
  `ProjectConstraints.budget_cap_usd` consumed as an input, not a rival authority
  (§6.3) — the refusal policy (F-BUD-02), the spend record (F-BUD-03), the
  `budget_cap` prompt variable (F-BUD-04), and the snapshot key/accessor
  (F-BUD-06).
- **Consumes, does not own:** `GenerationLedgerRow.estimated_cost_usd` and the
  ledger rows themselves stay with `generation` (`src/film_pipeline/generation/ledger.py:99`, per
  `docs/modular-architecture/audit/06-generation-runtime-and-ledger.md`). The proposed extraction therefore
  schedules **`generation`-consumer edits** in the same phase: drop the `-1.0`
  no-cap default at `src/film_pipeline/generation/ledger.py:108` and call the owner's
  `record_spend(...)` from the terminal ledger transitions at
  `src/film_pipeline/generation/executor.py:257,293,399` — otherwise ownership reads as shared.
- **Absorbs:** the cap derivation in `src/film_pipeline/graph/nodes/_context.py:422-427`,
  `src/film_pipeline/graph/nodes/prep.py`'s profile backfill of `budget_cap_usd`, the
  `max_cost_usd` default plumbing in `src/film_pipeline/mcp/tools/generation/planning.py:48`,
  `src/film_pipeline/app/services/_generation_ops.py:73`, and `src/film_pipeline/generation/ledger.py:108`;
  either wires or deletes `src/film_pipeline/graph/orchestrator_state.py:449-479` and
  `src/film_pipeline/graph/_action_routing.py:238-253` (F-BUD-02).
- **Non-goal:** cost *estimation* stays in `providers.pricing`; `budget` compares
  numbers, it does not compute them.
- **Guard tests:** graph and MCP approve paths produce identical outcomes for one
  fixture (F-BUD-02); `spent_usd == sum(SpendRecord.amount_usd)` and
  `remaining_usd == cap_usd - spent_usd` (F-BUD-03); one `budget_cap` derivation
  in `src/` (F-BUD-04).

### 6.5 Reconciliation with sibling audits

`docs/modular-architecture/audit/06-generation-runtime-and-ledger.md` owns ledger lifecycle (its F-GEN-01..10);
F-BUD-01/02 cite its F-GEN-10 rather than restating the two-cost-model claim, and
add only the cap inventory and the eight-site enforcement map.
`docs/modular-architecture/audit/08-validation-and-review.md` F-VR-07 owns validator dispatch; F-POST-07 adds the
orphan `delivery_manifest` id and the writerless `DeliveryManifest` schema.
`docs/modular-architecture/audit/14-module-boundaries-and-import-law.md` F-BOUNDARY-01/04 own the
`post → validation.impl` edge and boundary-test absence (cite by finding id: the
anchor line in that untracked, concurrently-revised file moved `:99` → `:125`
during this program); F-POST-04/07 supply the behavioral divergence that
justifies deleting the edge.
Budget ownership is **split deliberately** with `06`: `generation` owns the
ledger and the row-cost fields, `budget` owns cap resolution, refusal, and the
spend record. F-BUD-01 defers the two-cost-model claim (06's F-GEN-10) and adds
only the cap inventory; F-BUD-02/03 name the `generation`-side edits their
extraction requires (§6.4) so the roadmap can sequence them in one phase.
`docs/modular-architecture/audit/08-validation-and-review.md` F-VR-07's dispatch gap (delivery validator absent
from `_WORKER_NODES` and the `qc`-phase runner sets, present at
`src/film_pipeline/graph/nodes/qc.py:367`) is orthogonal to F-POST-07's writer gap and is not re-filed.
