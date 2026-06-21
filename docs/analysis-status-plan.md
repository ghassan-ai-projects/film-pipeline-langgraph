# Film Pipeline LangGraph — Analysis, Status & Plan

**Author:** OpenClaw-orch
**Date:** 2026-06-19
**Project:** `~/my-projects/film-pipeline-langgraph/`

---

## 1. Summary

The project is in **pre-implementation planning phase**. All planning docs are written (15 docs, ~50KB total) but zero code exists beyond the repo scaffolding. The vision is ambitious: a LangGraph-based film studio operating system with MCP-first control, specialist agent teams, human review gates, and typed state throughout.

---

## 2. What Already Exists

### Repository Layout
```
film-pipeline-langgraph/
├── README.md                     ← Project overview (this doc)
├── docs/                         ← 15 planning documents
│   ├── vision-and-direction.md   ← North star vision
│   ├── architecture-blueprint.md ← Full architecture (biggest doc)
│   ├── fresh-review.md           ← Fresh-eyes review of existing KB
│   ├── agent-architecture.md     ← Agent roles and relationships
│   ├── kb-operating-model.md     ← KB authority layers + retrieval
│   ├── remaining-needs.md        ← Gap analysis + build order
│   ├── e2e-test-scenarios.md     ← Test scenarios
│   ├── project-intake.md         ← Intake workflow
│   ├── clip-generation-execution.md  ← Safe generation ops
│   ├── multi-angle-coverage.md   ← Multi-angle scene planning
│   ├── reference-image-flow.md   ← Reference image lifecycle
│   ├── environment-consistency.md ← Location consistency
│   ├── versioning-and-checkpoints.md  ← Version model
│   └── analysis-status-plan.md   ← ← THIS FILE
└── film-knowledge-base/          ← Existing research, skills, scripts
```

### Existing Knowledge Base (film-knowledge-base/)
- **Skills:** Film production pipeline, reference-image pipeline, seedance skill
- **Research:** 00-COMPREHENSIVE-KNOWLEDGE.md, lang-graph-movie-pipeline.md, prompt-framework.md
- **Projects:** Davinci post-production, film production protocol, movie production (Primordial Stroke)
- **Lessons learned:** Cost optimization, film production protocol
- **Published article:** ART-029 film pipeline postmortem (with LinkedIn carousels)
- **Scripts:** generate-chain.py, providers.py, primordial-film-pipeline.py, composer-prompt.py
- **Reference templates:** Shot cards, camera blocks, character blocks, environment blocks, anchor prompts

### External Repositories Reviewed
- `agentic-drama-pipeline` — good typed workflow contracts
- `ai-drama-engine-demo` — good QC reports and reference handling
- `VEO.IO` — platform/product framing

---

## 3. Current Status

| Aspect | Status | Details |
|--------|--------|---------|
| **Vision** | ✅ Complete | Full north star documented |
| **Architecture** | ✅ Complete | Layers, state domains, schemas, registries, profiles |
| **Agent design** | ✅ Complete | Agent families, contracts, routing, collaboration patterns |
| **KB model** | ✅ Complete | Authority layers, retrieval, context packets |
| **MCP contracts** | ⚠️ Spec-defined | 15+ tool groups identified, no formal schemas yet |
| **Schemas** | ❌ Not started | Highest-priority gap — needed before any code |
| **LangGraph state machine** | ❌ Not started | Nodes, edges, subgraphs, interrupts only described in prose |
| **Code** | ❌ Not started | Zero Python/TypeScript. Only README + docs |
| **Mock provider** | ❌ Not started | Needed before real provider integration |
| **Test harness** | ❌ Not started | No E2E tests, no mock human actor |
| **Profiles** | ❌ Not started | Profile system described but not implemented |
| **Artifact storage** | ❌ Not started | No manifest system, no asset model |
| **Post-production** | ❌ Not started | Conceptual only |

---

## 4. Architecture Highlights

### Core Design Decisions
1. **MCP-first** — the LangGraph runtime is behind an MCP surface. OpenClaw controls everything through MCP tools. No direct UI, no wrapper model.
2. **Many small experts** — ~50+ specialist agents listed, each with narrow responsibility, typed contracts, separate reviewers.
3. **Human-in-the-loop** — 10 mandatory approval gates from concept through final delivery. LangGraph interrupts persist state and artifacts.
4. **Supervisor graph** — orchestrator agent routes work, not a single linear chain.
5. **Provider-agnostic** — registry adapter pattern. Mock provider first, real providers later.
6. **RCTCO prompts** — every agent gets structured Role-Core Task-Context-Constraints-Output prompts.
7. **Multi-model review** — parallel independent review by different models, debate/synthesis for disagreements.

### Key Data Structures
- **Master Film Matrix** — central production table connecting story, characters, environments, prompts, references, validation
- **Continuity Ledger** — per-shot state tracking (props, wardrobe, emotional state, location)
- **Prompt Registry** — stored RCTCO package per agent/shot
- **Generation Ledger** — provider execution records with cost tracking
- **Validation Ledger** — structured validation results per scope/modality

### Phase Map (0-10)
| Phase | Name | Human Gate |
|-------|------|------------|
| 0 | Project Intake | Yes |
| 1 | Film Constitution | Yes |
| 2 | Development | Yes |
| 3 | Screenwriting | Yes |
| 4 | Visual Development | Yes |
| 5 | Shot Bible | Yes |
| 6 | Generation Planning | Yes |
| 7 | Clip Generation | Yes |
| 8 | Multi-Level QC | Yes |
| 9 | Post-Production | Yes |
| 10 | Wrap | Yes |

---

## 5. Gap Analysis (Detailed)

### Critical Gaps (Must Fix Before Coding)

1. **Formal Schemas** — no JSON/YAML schemas for project config, artifacts, validation reports, matrix rows, MCP responses. Prose descriptions only.
2. **MCP Tool Contracts** — tool names identified but no input/output schemas, no idempotency rules, no error documentation.
3. **LangGraph State Machine** — phase names exist but no graph nodes, edges, interrupt points, conditional routing, subgraph structure.
4. **Artifact Storage Model** — no decision on git vs LFS vs external storage, no asset manifest schema.
5. **Test Harness** — mock provider described but not built. No mock human actor. No E2E scenarios executed.

### High Priority Gaps

6. **Observability** — no audit log design, no explainability tools, no blocking-reason reporting.
7. **Cost/Budget Policy** — spend approval thresholds described but not formalized into config schema.
8. **Security/Secrets** — no credential management strategy for provider API keys.
9. **Model Routing Policy** — model profiles named but no routing rules, fallback chains, cost-aware selection.
10. **Validation Registry** — validators listed but no formal registry with thresholds, blocking conditions.

### Medium Priority Gaps

11. **Project Templates** — no reusable config profiles for film types (narrative, poetry, experimental).
12. **Delivery Strategy** — delivery packages described but no export workflow.
13. **Invalidation Engine** — dependency tracking for artifact invalidation described but not formalized.
14. **UI/Review Package Shape** — review package contents described but no actual templates.

---

## 6. Recommended Build Order

Taken from `remaining-needs.md` — validated as correct:

```
Phase     Focus                              Depends On
─────     ─────                              ──────────
1.        Schemas & registries               Nothing
2.        MCP tool contracts                 Schemas
3.        Project config/profile system      Schemas
4.        Artifact store & manifests         Schemas
5.        LangGraph state machine skeleton   All above
6.        KB context packet builder          LangGraph skeleton
7.        Agent registry & prompt runner     KB builder
8.        Review package generator           Artifact store
9.        Validation registry                Schemas
10.       Mock provider & test harness       Generator
11.       Checkpoint/resume & rollback       Test harness
12.       End-to-end mock mini-film          All above
13.       Real provider adapter              Mock passes E2E
14.       Post-production assembly           Real provider
15.       Production hardening               All above
```

### First Implementation Slice (Smallest Useful Build)
```
MCP:  create_project, resolve_active_project, submit_idea
Graph: idea → config → constitution → treatment → review gate
Storage: artifact persistence, checkpoint
MCP:  inspect_state, approve_phase, request_revision
```

---

## 7. Key Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Scope creep** — massive agent roster, 50+ agents | High | MVP insists on 19 agents minimum. Add more after proving the spine. |
| **Overengineering** — building a "studio OS" instead of a working pipeline | Medium | Mock provider + E2E test forces real execution. If the studio is too abstract, the mock will expose it. |
| **KB dependency** — pipeline depends on structured, governed KB | Medium | KB already exists but needs formal layers. MVP KB slices are small. |
| **MCP-first is novel** — no reference implementation for this pattern | Medium | Treat MCP as a standard tool surface. LangGraph is standard. The risk is in the integration, not the components. |
| **Real provider cost** — expensive generation before proving the system | Low | Mitigated by: mock provider first, budget caps, approval gates. |
| **Agent prompt quality** — 50 agents with RCTCO prompts may drift | Low | Agent contracts + validators per agent keep quality bounded. |
| **Low momentum** — planning phase already has 15 docs, zero code | Medium | This analysis document is the signal to move from planning to building. First slice is well-scoped. |

---

## 8. Next Actions

1. **Move to Phase 1 (Schemas)** — define the core JSON/YAML schemas for project config, artifacts, master film matrix, validation reports, and MCP responses.
2. **Define MCP tool contracts** — create a spec doc with input/output schemas for the first 10-15 tools.
3. **Build LangGraph skeleton** — implement the top-level supervisor graph with phase routing and interrupt points.
4. **Run the first slice** — intake → constitution → treatment → review gate through MCP.

The planning is done. The docs are written. The next commit should be **code**.
