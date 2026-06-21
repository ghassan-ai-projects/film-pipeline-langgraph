# Scene & Script Review Pipeline — How We Improve Story, Scenes, and Flow

> **Purpose:** This document captures the complete review architecture from the legacy TPS
> pipeline — the 5-agent writers' room, flow validation between scenes, post-generation
> output quality gates, and iteration protocols — and maps it to what exists and what's
> missing in the new LangGraph project.
>
> Use this as the specification for building review and iteration loops.

---

## TL;DR

The legacy TPS pipeline had a **sophisticated multi-agent review system** that was the
secret to its quality. The LangGraph project has the infrastructure (schemas for
`ValidationReport`, `ConsensusReport`, `ReviewPackage`, 10 human approval gates) and
9 of 15 agent prompt templates, but **zero of the review agents or validation loops are
actually wired into the graph**.

**What's there:** Interrupts at every phase gate, approval/revision schemas, validation
report schema, multi-model consensus, ReviewPackage for human review.

**What's missing:** The actual review agents (Structural Analyst, Character Consistency,
Thematic Evaluator, AI Constraints Verifier, Flow Validator, Output Validator), the
iteration loops (rewrite on fail, retake on bad output, drift detection every 5 shots),
and the validation rubrics (per-scene 140pt, flow 40pt, output 50pt).

---

## 1. The Legacy Review Architecture (TPS)

The legacy pipeline had **4 distinct review stages** at different points in the lifecycle,
each with dedicated agents and rubrics.

### Stage 1: Per-Scene Validation Gate

**When:** After each scene script is written, before prompt generation.

**What it does:** 5 agents review each scene in parallel against a 140-point full-stack rubric.
This is the PRIMARY story improvement mechanism — it's where scripts get fixed before any
generation budget is spent.

**The 5 Review Agents:**

| Agent | Domain | Points | Writes | What It Checks |
|-------|--------|--------|--------|----------------|
| **Structural Analyst** | Narrative Architecture | 30 (M1-20) | `ValidationReport` | Plot causality, 3-act structure, inciting incident, midpoint, climax, scene economy |
| **Character Consistency** | Character Psychology | 30 (M21-40) | `ValidationReport` | Emotional arc integrity, motivation consistency, non-verbal storytelling |
| **Thematic Evaluator** | Theme + World | 50 (M31-40 shared, M61-80) | `ValidationReport` | Symbolic density, cultural authenticity, visual progression, world-building |
| **AI Constraints Verifier** | Technical Feasibility | 30 (M41-60) | `ValidationReport` | Physics debt, identity anchors, temporal drift, continuity, generation feasibility |
| **Orchestrator/Judge** | Production Readiness | 25 (M81-100) + synthesis | `ConsensusReport` | Aggregates all 4, mediates conflicts, delivers PASS/FAIL/DEBATE verdict |

**Total:** 140pts • **Threshold:** ≥133/140 (95%) — deliberately high because scene fixes
cost $0 vs generation fixes costing $0.18/s.

**When threshold isn't met:**
1. Orchestrator synthesizes all 4 agent critiques into concrete rewrite instructions
2. Script Generator rewrites the scene (or adds bridging scenes)
3. Revalidate → pass or repeat (max 5 iterations, then manual flag)

**When threshold is met:**
- Scene N passes → move to Scene N+1
- All scenes in an act pass → move to Flow Validation

**The TPS loop was SEQUENTIAL per scene, not batch.** S001 validates completely → if pass,
S002 validates → if pass, S003 validates → ... No out-of-order. Every scene gets the full
5-agent treatment before the next one starts.

### Stage 2: Flow Validation (Inter-Scene)

**When:** After all scenes in an act/beat pass per-scene validation.

**What it does:** Reviews consecutive scene PAIRS (S{N} → S{N+1}) for what per-scene
validation misses — the cut between them.

**1 agent** (Flow Validator) covering **40 points across 4 domains:**

| Domain | Points | What It Checks |
|--------|--------|----------------|
| F1: Prop & Physical Continuity | 10 | Hand state, body marks, clothing, geography, prop timelines carry across cut |
| F2: Lighting & Environment | 10 | Color temp, light direction, location geometry, transitions, atmosphere |
| F3: Character State | 10 | Emotional arc, posture, breath/fatigue, attention focus, knowledge state |
| F4: Transition Technical | 10 | Cut type, match-cut feasibility, dissolve, audio bridge, hard cut energy |

**Threshold:** ≥34/40 (85%) — slightly lower because some flow issues are fixable in prompt.

**When threshold isn't met:**
- Log specific failed metrics → propose prompt-level fix → optionally revalidate

### Stage 3: Prompt Readiness Validation

**When:** After flow validation passes, before sending to generation provider.

**What it does:** Validates the actual JSON prompt file, not the narrative.

**1 agent** (Prompt Readiness Validator) covering **40 points across 4 domains:**

| Domain | Points | What It Checks |
|--------|--------|----------------|
| R1: Structure | 10 | JSON validity, all 7 blocks present (ENVIRONMENT, ATMOSPHERE, ACTION, CAMERA, CHARACTER, CONSISTENCY, NEGATIVE) |
| R2: Identity | 10 | CHAR_DESC verbatim from locked block, IDENTITY_REINFORCE present |
| R3: Environment | 10 | ENV_BASE verbatim from locked block, ENVIRONMENT_REINFORCE present |
| R4: Parameters | 10 | Duration ≤12s standard / ≤15s max, seed set, ratio match, audio toggle |

**Threshold:** ≥34/40 (85%) — structural, not subjective.

### Stage 4: Output Validation (Post-Generation)

**When:** After each clip comes back from the generation provider.

**What it does:** Validates the actual generated video against what was requested.

**1 agent** (Output Validator) covering **50 points across 5 domains:**

| Domain | Points | What It Checks |
|--------|--------|----------------|
| O1: Duration & Timing | 10 | Duration ±10%, frame count, first/last frame valid |
| O2: Identity Preservation | 10 | Face consistent, no warping, no double faces, outfit persistent |
| O3: Artifact Detection | 10 | No deformed hands, extra limbs, floating elements, texture crawl, ghosting |
| O4: Environment & Lighting | 10 | Key light, color temp, background stability, prop persistence, weather |
| O5: Technical Quality | 10 | Resolution, macroblocking, flicker, audio sync, watermarks |

**Threshold:** ≥43/50 (85%) to accept, <38/50 to reject outright.

**Retake protocol:**
1. First retake: same prompt, fallback provider
2. Second retake: simplified prompt (shorter duration, simpler action, stronger negatives)
3. Both fail: mark as high-risk, use static plate + Ken Burns effect

**Drift detection (every 5 shots):**
Compare the 5th clip's last frame to the master reference. On drift detected, inject the
master reference into the next generation as a reference frame.

---

## 2. The Complete Review Lifecycle

```
┌──────────────────────────────────────────────────┐
│                  SCRIPT                          │
│          (Screenwriter Agent)                    │
│                  │                               │
│                  ▼                               │
│          PER-SCENE VALIDATION                    │
│   5 agents in parallel:                          │
│   ├── Structural Analyst         (140pt total)   │
│   ├── Character Consistency      (95% threshold) │
│   ├── Thematic Evaluator                         │
│   ├── AI Constraints Verifier                   │
│   └── Orchestrator (synthesis + verdict)         │
│                  │                               │
│           ┌──────┴──────┐                        │
│           ▼              ▼                       │
│       FAIL (≤133)    PASS (≥134)                 │
│           │              │                       │
│           ▼              ▼                       │
│     Script Generator   FLOW VALIDATION           │
│     rewrites scene     1 agent, scene pairs      │
│           │            40pt, 85% threshold       │
│           ▼              │                       │
│     Revalidate     ┌─────┴─────┐                 │
│     (max 5 iters)  ▼           ▼                 │
│                  FAIL        PASS                 │
│                  (fix)         │                  │
│                                ▼                  │
│                     PROMPT READINESS              │
│                     1 agent, 40pt, 85%            │
│                                │                  │
│                     ┌──────────┴──────────┐       │
│                     ▼                     ▼       │
│                  PASS                   FAIL      │
│                     │                 (fix JSON)  │
│                     ▼                             │
│              GENERATION                           │
│              (clip-by-clip)                       │
│                     │                             │
│                     ▼                             │
│              OUTPUT VALIDATION                    │
│              After every clip                     │
│              50pt, 85%/75% thresholds            │
│                     │                             │
│             ┌───────┴────────┐                    │
│             ▼                ▼                    │
│         ACCEPT            REJECT                  │
│             │            (retake ×2 max)          │
│             ▼                                     │
│      DRIFT CHECK (every 5 shots)                  │
│             │                                     │
│             ▼                                     │
│      ASSEMBLY + DELIVERY                          │
└──────────────────────────────────────────────────┘
```

---

## 3. What the LangGraph Project Already Has

### ✅ Existing schemas (complete)

| Schema | File | Use |
|--------|------|-----|
| `ValidationReport` | `validation.py` | One validator's structured output — scores, status, blocking issues, warnings, recommended_actions, requires_human_review |
| `ValidationIssue` | `validation.py` | Individual issue: code, message, severity |
| `ConsensusReport` | `validation.py` | Multi-model aggregation: reviewer scores, agreement_level, shared_findings, disagreements, orchestrator_recommendation |
| `ReviewerScore` | `validation.py` | Model_id + validator_id + score + status |
| `ValidationLedgerEntry` | `validation.py` | Stored record: report + project_id + phase + consensus |
| `ReviewPackage` | `approval.py` | Human review package: summary, artifacts, diffs, validation_results, open_issues, risks, cost_impact, orchestrator_recommendation, available/blocked_actions |
| `ApprovalRecord` | `approval.py` | approve/request_revision/reject/escalate at phase gates |
| `RevisionRequest` | `approval.py` | Link old → new version, notes |
| `ReviewStrategy` | `_base.py` | Enum: SINGLE, PARALLEL_INDEPENDENT, SPECIALIST_PANEL, DEBATE_SYNTHESIS, HUMAN_ARBITRATED |
| `ValidationScope` | `_base.py` | ARTIFACT, CLIP, SCENE, SEQUENCE, ACT, FULL_MOVIE, DELIVERY |
| `ValidationModality` | `_base.py` | TEXT, IMAGE, CAMERA, CONTINUITY, FLOW, VIDEO, ASSEMBLY |

### ✅ Existing infrastructure

| Component | Location | Status |
|-----------|----------|--------|
| 10 human approval gates | `graph/interrupts.py` | ✅ Every phase has an interrupt point |
| Approval edge routing | `graph/edges.py` | ✅ `after_approval` routes to next phase |
| `QCSynthesisAgent` | `agents/impl/qc_synthesis_agent.py` | ✅ Produces `ConsensusReport` from multiple validator reports |
| `ValidationStatus` | `_base.py` | PASS, PASS_WITH_NOTES, NEEDS_REVISION, BLOCKED, ERROR |
| `ArtifactType` includes: | `_base.py` | `VALIDATION_REPORT`, `REVIEW_PACKAGE`, `APPROVAL_RECORD`, `REVISION_REQUEST`, `ISSUE_RECORD` |
| Prompt templates for critical agents | `agents/prompt_templates/defaults.py` | ✅ 9 agent templates registered (including screenwriter, development) |
| No review-specific templates | `agents/prompt_templates/defaults.py` | ❌ Missing: structural-analyst, character-consistency, thematic-evaluator, ai-constraints-verifier, orchestrator-judge, flow-validator, output-validator, prompt-readiness-validator |
| `HandoffManager` | `agents/handoff.py` | ✅ Tracks agent-to-agent handoffs with task + validation_required |
| `AgentRegistration` | `handoff.py` | ✅ Has `reviewed_by` field, `input_artifacts`, `output_artifacts` |

### ✅ Existing agents ready to be wired

| Agent | File | Status | Missing |
|-------|------|--------|---------|
| `IntakeAgent` | `agents/impl/intake_agent.py` | ✅ Complete | None |
| `ConstitutionAgent` | `agents/impl/constitution_agent.py` | ✅ Complete | None |
| `DevelopmentAgent` | `agents/impl/development_agent.py` | ✅ Complete | None |
| `ScreenwriterAgent` | `agents/impl/screenwriter_agent.py` | ✅ Complete | None |
| `VisualDevAgent` | `agents/impl/visual_dev_agent.py` | ✅ Complete | Reference image binary store |
| `CharacterBibleAgent` | `agents/impl/character_bible_agent.py` | ✅ Complete | Not wired in graph |
| `EnvironmentBibleAgent` | `agents/impl/environment_bible_agent.py` | ✅ Complete | Not wired in graph |
| `CameraBibleAgent` | `agents/impl/camera_bible_agent.py` | ✅ Complete | Not wired in graph |
| `StyleBibleAgent` | `agents/impl/style_bible_agent.py` | ✅ Complete | Not wired in graph |
| `ShotBibleAgent` | `agents/impl/shot_bible_agent.py` | ✅ Complete | Not wired in graph |
| `GenPlannerAgent` | `agents/impl/gen_planner_agent.py` | ✅ Complete | Not wired |
| `QCSynthesisAgent` | `agents/impl/qc_synthesis_agent.py` | ✅ Complete | No data to synthesize |
| `AssemblyAgent` | `agents/impl/assembly_agent.py` | ✅ Complete | Not wired |

---

## 4. What's Missing (Needs Building)

### Gap 1: Review agent implementations

**Need 6 new review agents** (or prompt templates that feed into existing `BaseAgent`):

| Agent ID | Domain | Points | Threshold | Prompt template exists? |
|----------|--------|--------|-----------|------------------------|
| `structural-analyst-agent` | Narrative architecture | 30 (M1-20) | 95% | ✅ From TPS legacy — needs porting |
| `character-consistency-agent` | Character psychology | 30 (M21-40) | 95% | ✅ From TPS legacy — needs porting |
| `thematic-evaluator-agent` | Theme + world-building | 50 (M31-40, M61-80) | 95% | ✅ From TPS legacy — needs porting |
| `ai-constraints-verifier-agent` | Technical feasibility | 30 (M41-60) | 95% | ✅ From TPS legacy — needs porting |
| `orchestrator-judge-agent` | Synthesis + verdict | 25 (M81-100) | — | ✅ From TPS legacy — needs porting |
| `flow-validator-agent` | Inter-scene continuity | 40 (F1-F4) | 85% | ✅ From TPS legacy — needs porting |
| `prompt-readiness-validator-agent` | Prompt structure | 40 (R1-R4) | 85% | ✅ From TPS legacy — needs porting |
| `output-validator-agent` | Generated clip QA | 50 (O1-O5) | 85% | ✅ From TPS legacy — needs porting |

**Each needs:**
- An `AgentRegistration` entry in `MVP_AGENTS`
- A `PromptTemplate` in `agents/prompt_templates/defaults.py`
- A `BaseAgent` subclass with `prepare`, `execute`, `validate`
- Registered in `nodes.py` agent_map

### Gap 2: Validation rubrics as KB artifacts

The rubrics (140pt, 40pt, 40pt, 50pt) should be stored as KB items, not hardcoded in
prompt templates. This allows versioning and iterative improvement.

### Gap 3: No per-scene loop in the graph

The current graph runs a single `script_node` that produces all scenes at once. The
legacy pipeline validated **one scene at a time** with an iteration loop.

**Need:** Either:
- A subgraph that loops per-scene: write → validate → rewrite → validate → ... → next scene
- Or a validation-only parallel pass that generates `ValidationReport` per scene, then
  feeds back to a rewrite step

The loop needs: max_iterations (5), convergence detection (score oscillation), and manual
flag on exhaustion.

### Gap 4: No flow validation between scenes

`MasterFilmMatrixRow` has `chaining: ChainingConfig` but there's no cross-scene continuity
check. The `ContinuityLedger` schema exists but nothing writes or validates it.

### Gap 5: No output validation after generation

`generation_node` exists as a flag-only skeleton. After a clip is generated, nothing checks
it for face warping, artifacts, duration mismatch, or identity drift.

### Gap 6: No drift detection every 5 shots

The legacy pipeline compared the last frame of every 5th clip to the master reference. This
was the safety net for long films. Nothing equivalent exists in the LangGraph project.

### Gap 7: No iteration/convergence tracking

| Missing | Why |
|---------|-----|
| Score history per artifact | Detecting oscillation (up-down-up) across iterations |
| Max-iterations enforcement (5) | Preventing infinite loops |
| Manual flag on exhaustion | Escalating to human when AI convergence fails |
| Delta-only revalidation | Re-validating only what changed, not the full scene |

### Gap 8: No review agent prompt templates in registry

9 complete RCTCO prompt templates exist in TPS legacy files
(`~/ai-movies/the-primordial-stroke/pipeline-docs/agents/*.md`) but none have been ported
to `agents/prompt_templates/defaults.py`. Currently only 9 creation-agent templates are
registered (screenwriter, development, constitution, etc.) — zero review templates.

---

## 5. Comparison: TPS Legacy vs LangGraph Project

| Feature | Legacy TPS | LangGraph |
|---------|-----------|-----------|
| 5-agent per-scene validation | ✅ Firing in parallel every scene | ❌ No review agents exist |
| 140pt rubric per scene | ✅ Full metric table | ❌ No rubric stored |
| Sequential scene processing | ✅ S001 → validate → S002 → validate | ❌ All scenes in one batch |
| Iteration loop (max 5) | ✅ Re-write → re-validate | ❌ No loop |
| Orchestrator synthesis | ✅ Mediates agent disagreements | ❌ No orchestrator agent |
| Flow validation (40pt pairs) | ✅ Between scene pairs | ❌ No flow validator |
| Prompt readiness (40pt) | ✅ Before generation | ❌ No prompt validator |
| Output validation (50pt) | ✅ After each clip | ❌ No output validator |
| Retake protocol (×2 max) | ✅ Fallback provider → simplified prompt | ❌ No retake logic |
| Drift detection (every 5) | ✅ Last-frame comparison | ❌ No drift detection |
| Score oscillation detection | ✅ Up-down-up = convergence failure | ❌ No score history |
| Human interrupt gates | ❌ (no human-in-loop) | ✅ 10 phase gate interrupts |
| ValidationReport schema | ❌ | ✅ Complete |
| ConsensusReport schema | ❌ | ✅ Complete |
| ReviewPackage for humans | ❌ | ✅ Complete |
| ApprovalRecord/RevisionRequest | ❌ | ✅ Complete |
| HandoffManager | ❌ | ✅ Complete |
| Agent registry | ❌ | ✅ 19 MVP agents registered |
| Prompt template registry | ❌ | ✅ 9 creation agents registered |

**The pattern is clear:** The LangGraph project has superior **infrastructure** (schemas,
registries, interrupts, handoff tracking) but zero **review execution**. The legacy pipeline
had the opposite — great review execution with zero infrastructure.

---

## 6. Implementation Order

### Phase 1 — Core Review Agents (Priority: Critical)

1. Port 4 review agent prompts from TPS → `agents/prompt_templates/defaults.py`:
   - `structural-analyst` (port from `structural-analyst-prompt.md`)
   - `character-consistency` (port from `character-consistency-prompt.md`)
   - `thematic-evaluator` (port from `thematic-evaluator-prompt.md`)
   - `ai-constraints-verifier` (port from `ai-constraints-verifier-prompt.md`)

2. Port `orchestrator-judge` prompt + implement:
   - Collects 4 reports → computes weighted aggregate → produces `ConsensusReport`
   - Handles score disagreements → synthesis → PASS/FAIL/DEBATE verdict
   - Detects score oscillation across iterations

3. Register all 5 as `BaseAgent` subclasses + `AgentRegistration` entries

4. Build per-scene validation subgraph:
   - Input: single `ScriptScene` + `SceneIntent`
   - Run 4 agents in parallel → collect `ValidationReport[]`
   - Orchestrator produces `ConsensusReport`
   - If PASS → save `ValidationReport` + advance to next scene
   - If FAIL → produce `RevisionRequest` + loop back to rewrite

### Phase 2 — Flow + Prompt Validation (Priority: High)

5. Port `flow-validator` prompt from TPS
6. Build flow validation subgraph: reads consecutive `MasterFilmMatrixRow` pairs → validates F1-F4
7. Port `prompt-readiness-validator` prompt from TPS
8. Build prompt validation step: reads generated prompt JSON → validates R1-R4

### Phase 3 — Output Validation (Priority: High)

9. Port `output-validator` prompt from TPS
10. Build output validation step in `generation` subgraph:
    - After each clip download, validate O1-O5
    - Implement retake protocol (fallback provider → simplified prompt → static plate)
    - Log all retakes in `GenerationLedgerRow`

### Phase 4 — Drift + Convergence (Priority: Medium)

11. Build drift detection: every 5th clip, compare last frame to master reference
    - Face structure, environment geometry, color temperature
    - On drift: inject master reference into next generation
12. Build iteration tracking:
    - Score history per artifact (list of scores across iterations)
    - Max 5 iterations enforcement
    - Oscillation detection (up-down-up = convergence failure → manual)
    - Delta-only revalidation

### Phase 5 — Iteration Loop (Priority: Medium)

13. Wire the full validation loop in the graph:
    - `ScreenwriterAgent` writes `Script`
    - For each scene: validate → loop back on fail → max 5 iterations
    - After all scenes pass: `flow-validator` on scene pairs
    - After flow passes: `prompt-readiness-validator` on generated JSON
    - After generation: `output-validator` on each clip
    - Every 5 clips: drift detection
14. Store `ValidationReport` + `ConsensusReport` via `ArtifactStore`

---

## 7. Key Design Decisions to Replicate

### Decision 1: Sequential per-scene, not batch

**Legacy choice:** S001 validates completely → if pass, S002 → if pass, S003 → ...

**Why:** Early scenes define the world, character, and tone. If S001's character voice is wrong,
it cascades through every subsequent scene. Fixing S001 before writing S002 prevents waste.

**Our approach:** Each scene is a subgraph iteration. The graph stays at `scene_processing`
until the current scene passes, then advances.

### Decision 2: 95% per-scene threshold, not 80%

**Legacy choice:** ≥133/140 (95%) for per-scene, ≥34/40 (85%) for flow/output.

**Why:** Scene fixes cost nothing (it's just a text edit). Generation fixes cost $0.18/s.
95% on text is the cheap gate before expensive gates. The lower output threshold (85%)
reflects reality: you can accept minor artifacts and fix them in post, but a broken script
can't be fixed in post.

**Our approach:** Same thresholds. Hard-code as defaults, allow project-level override.

### Decision 3: Orchestrator synthesizes, not just averages

**Legacy choice:** Orchestrator reads all 4 agent reports, detects scoring disagreements,
mediates them, and produces a nuanced verdict — not just an average.

**Why:** Two agents might disagree (one gives 12/20, another gives 18/20). The orchestrator
reads both justifications and decides who's right, or flags the tension for human review.
A simple average would mask the disagreement.

**Our approach:** `OrchestratorJudgeAgent` produces `ConsensusReport` with
`agreement_level`, `disagreements: list[str]`, and `shared_findings`. The `ReviewPackage`
preserves disagreements so humans can see the tension.

### Decision 4: Output validation is automatic, not AI

**Legacy choice:** O1 (Duration & Timing) was auto-checked. O2-O5 required AI review.

**Why:** Duration, frame count, and file existence are trivial to check programmatically.
Face warping and artifacts need a vision model. Split the costs: free checks first, AI
checks only if auto-checks pass.

**Our approach:** Auto-heuristics (`os.path.getsize`, `ffprobe` duration) → if pass, run
AI validator → if fail, reject immediately without spending AI budget.

### Decision 5: Drift detection is periodic, not per-shot

**Legacy choice:** Every 5th clip only.

**Why:** Running face comparison after every shot costs $0.001 each. Every 5th is enough —
identity drift accumulates slowly; a single bad shot is caught by output validation;
periodic drift detection catches slow degradation across 20+ shots.

**Our approach:** Counter in `GenerationLedgerRow`: `polls_completed % 5 == 0` triggers
drift check. On drift: inject master reference into next generation.

---

## 8. File Locations — What Goes Where

| Artifact | Schema | Location | When |
|----------|--------|----------|------|
| Per-scene `ValidationReport` (×4 per scene) | `ValidationReport` | `08-validation/scene_{id}_{agent}.v{n}.json` | After each scene validation pass |
| `ConsensusReport` (per scene) | `ConsensusReport` | `08-validation/consensus_scene_{id}.v{n}.json` | After orchestrator synthesis |
| Flow `ValidationReport` (per pair) | `ValidationReport` | `08-validation/flow_{from}_{to}.v{n}.json` | After flow validation |
| Prompt readiness `ValidationReport` | `ValidationReport` | `08-validation/prompt_readiness_{shot_id}.v{n}.json` | After prompt validation |
| Output `ValidationReport` (per clip) | `ValidationReport` | `08-validation/output_{shot_id}.v{n}.json` | After each clip generation |
| Drift report (every 5 clips) | `ValidationReport` | `08-validation/drift_check_{shot_id}.v{n}.json` | After drift detection |
| `ReviewPackage` (per phase gate) | `ReviewPackage` | `{phase}/review_package.{phase}.v{n}.json` | At each human approval gate |
| Score history | (inline dict) | `08-validation/score_history_scene_{id}.json` | Runtime tracking for oscillation detection |

---

## 9. Summary: What's Ported vs What's Missing

### ✅ Ported to LangGraph
- `ValidationReport`, `ConsensusReport`, `ReviewPackage`, `ApprovalRecord`, `RevisionRequest` schemas
- 10 human approval interrupt gates
- `QCSynthesisAgent` (produces `ConsensusReport`)
- `HandoffManager` with agent routing
- 19 MVP agent registrations
- Prompt template registry
- 9 creation agent prompt templates (intake → assembly)

### ❌ Not Ported
- 5 per-scene review agent implementations (structural, character, thematic, constraints, orchestrator)
- 4 review prompt templates (need porting from TPS `pipeline-docs/agents/*.md`)
- Per-scene validation loop (sequential, max 5 iterations)
- Flow validation (40pt rubric, scene pairs)
- Prompt readiness validation (40pt rubric, JSON structure)
- Output validation (50pt rubric, generated clips)
- Retake protocol (fallback provider → simplified → static plate)
- Drift detection (every 5 shots)
- Score oscillation detection
- Validation rubrics as KB artifacts
- Review agent registrations in `MVP_AGENTS`
- Review agent prompt templates in `defaults.py`
