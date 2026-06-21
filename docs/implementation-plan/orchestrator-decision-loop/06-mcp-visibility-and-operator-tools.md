# Phase 06 — MCP Visibility And Operator Tools

**Depends on:** `05-human-gates-and-review-packages.md`, Phase 02 (MCP Tool Contracts)
**Blocks:** Phase 07 in this folder

---

## Goal

Expose orchestrator reasoning and review lifecycle state through MCP so an operator can
understand what the graph is doing and why.

---

## Scope

Improve operator-facing inspection for:

- current selected action
- eligible and blocked actions
- latest routing decision
- active review cycle
- pending revision requests
- candidate vs approved artifact baselines
- escalation reasons

This phase should focus on visibility, not on redesigning the MCP surface from scratch.

---

## Files To Touch

- `src/film_pipeline/mcp/tools/__init__.py`
- `src/film_pipeline/app/runtime.py`
- `tests/unit/mcp/`
- `tests/integration/mcp/`
- docs under `docs/mcp-openclaw/` only if behavior changes materially

---

## Checklist

- [ ] Expand orchestrator summary to include selected action and route reason
- [ ] Expose current review-cycle state
- [ ] Expose pending revision requests
- [ ] Expose candidate refs and approved refs separately
- [ ] Expose why approval is blocked when it is blocked
- [ ] Add MCP tests for the new state surfaces

---

## Acceptance Criteria

- [ ] An operator can see what the orchestrator wants to do next
- [ ] An operator can see why the orchestrator chose that path
- [ ] An operator can distinguish candidate artifacts from approved baselines
- [ ] An operator can inspect pending revision state and blockers
- [ ] MCP state surfaces remain backward compatible where possible

---

## Risks

| Risk | Mitigation |
|------|------------|
| Too much internal state leaks through MCP | Expose stable summaries and refs, not raw internal implementation details |
| Tool responses become noisy | Keep summaries concise and use refs for drill-down |
