# Phase 07 — Generation Plan + Budget

> **Status:** 🟡 Blocked by 06 | **Depends on:** Shot Bible Writers (06)

## Problem

Two artifacts are missing for the generation phase:

1. **GenerationPlan** — no schema exists. Need ordered shot list with provider
   routing, priority, estimated duration, and cost per shot.

2. **BudgetState** — schema exists in `budget.py`. No writer. Need running
   spend tracker: cap, spent, per-phase caps, approval thresholds.

`gen_planning_node` is flag-only. These artifacts are prerequisites for
`approve_generation_spend` and `start_generation_batch` (which already exist
as MCP tools).

## What to Build

### Part A: GenerationPlan Schema

New Pydantic model in `src/film_pipeline/schemas/generation.py`:

```python
class ShotPlan(SchemaBase):
    shot_id: str
    priority: int           # 1-5, lower = higher priority
    risk: str               # low / medium / high
    provider_id: str        # which provider to use
    model_id: str           # which model variant
    tier: str               # fast / standard / ultra
    estimated_duration: float  # seconds
    estimated_cost: float
    prompt_ref: str         # ref to prompt in PromptRegistry
    generation_order: int   # sequential order
    dependencies: list[str]  # shot_ids that must complete first

class GenerationPlan(SchemaBase):
    project_id: str
    shots: list[ShotPlan]
    total_estimated_cost: float
    provider_utilization: dict[str, int]  # provider_id → shot count
    created_at: str
```

### Part B: GenerationPlan Writer

**MCP tool:** `generate_plan` — reads `MasterFilmMatrix` + `PromptRegistry` +
`BudgetState` (or budget profile) and produces the ordered plan.

**Storage:** `ArtifactStore.save()` → `06-generation-plan/generation_plan.v1.json`

### Part C: BudgetState Writer

**MCP tool:** `initialize_budget` — creates the initial `BudgetState` from the
project's budget profile (cap, per-phase allocations).

**Storage:** `ArtifactStore.save()` → `06-generation-plan/budget_state.v1.json`

**State ref:** `budget_state_ref`

### Part D: Wire Existing Generation Tools

The generation MCP tools (`plan_generation_batch`, `approve_generation_spend`,
`start_generation_batch`) already use `GenerationLedgerManager`. Update them to:

1. `plan_generation_batch` → reads `GenerationPlan` instead of ad-hoc shot list
2. `approve_generation_spend` → checks against `BudgetState.cap`
3. `start_generation_batch` → follows `GenerationPlan.generation_order`

## Files to Create

- `src/film_pipeline/schemas/generation_plan.py` — GenerationPlan + ShotPlan schemas
- `src/film_pipeline/agents/impl/gen_planner_agent.py` — Implement existing stub
- `tests/unit/schemas/test_generation_plan.py`
- `tests/unit/agents/test_gen_planner_agent.py`

## Files to Modify

- `src/film_pipeline/schemas/__init__.py` — Export GenerationPlan
- `src/film_pipeline/schemas/generation.py` — May move ShotPlan here or keep separate
- `src/film_pipeline/mcp/tools/__init__.py` — Add `generate_plan`, `initialize_budget`; update gen tools
- `src/film_pipeline/graph/nodes.py` — Wire `gen_planning_node`
- `src/film_pipeline/mcp/contract.py` — Register new tools

## Acceptance Criteria

1. `GenerationPlan` schema passes mypy strict + round-trip JSON test
2. `generate_plan` produces valid plan from shot matrix + prompt registry
3. `initialize_budget` writes BudgetState with cap and per-phase allocations
4. `approve_generation_spend` rejects when estimated cost > remaining budget
5. `start_generation_batch` follows generation_order
6. Unit + integration + MCP tests

## Risks

- **Cost estimation accuracy**: Estimated cost is based on tier × duration.
  Actual cost may vary. Mitigation: track actual vs estimated in ledger.
- **Provider availability**: The plan may route to a provider that's unhealthy.
  Mitigation: check provider health in `generate_plan`.
- **Budget enforcement**: Budget is currently not enforced at generation time.
  This phase adds enforcement — may break existing generation tests.
