# Implementation Progress

**Last updated:** 2026-06-19
**Branch:** main (4 commits)
**Tests:** 130 passing, CI green

## Completed Phases

| Phase | Name | Commit | Tests | Coverage | Status |
|-------|------|--------|-------|----------|--------|
| 00 | Scaffolding | `d473712` | 3 | 100% | ✅ |
| 01 | Schemas & Registries | `d473712` | 52 | 99% | ✅ |
| 02 | MCP Tool Contracts | `d473712` | 30 | — | ✅ |
| 03 | Config & Profile System | `527ac6a` | 25 | 95% | ✅ |
| 04 | Artifact Store | `3db9fa3` | 20 | 94% | ✅ |
| 05 | LangGraph Skeleton | NOT YET COMMITTED | — | — | 🟡 (graph module exists, tests need fixing) |

## Phase 05 Status (In Progress — DO NOT RESTART)

Files created:
- `src/film_pipeline/graph/state.py` — FilmStudioState dataclass
- `src/film_pipeline/graph/router.py` — action router with 11 phases + gates
- `src/film_pipeline/graph/nodes.py` — 13 node functions (11 phases + approve + revision)
- `src/film_pipeline/graph/edges.py` — conditional edge routing
- `src/film_pipeline/graph/graph.py` — build_graph() StateGraph builder
- `src/film_pipeline/graph/__init__.py` — re-exports
- `tests/unit/test_graph.py` — needs fixing (old version deleted)

What works:
- Router logic fully tested (earlier version had 4 passing tests)
- Graph compiles without error after node renaming fix (StateGraph reserves phase names → nodes named `*_node`)

What broke:
- `tests/unit/test_graph.py` had import errors after node rename. File was deleted. Need to recreate tests.
- Coverage dropped to ~83% without graph tests.

**Fix plan:** Run these commands in the new session:
```bash
cd /Users/ghassan/my-projects/film-pipeline-langgraph
cat > tests/unit/test_graph.py << 'EOF'
"""Tests for LangGraph graph module."""
from __future__ import annotations
from typing import Any
from film_pipeline.graph.edges import after_approval, after_phase
from film_pipeline.graph.graph import build_graph
from film_pipeline.graph.nodes import approve_phase_node, intake_node, request_revision_node
from film_pipeline.graph.router import APPROVAL_GATES, PHASE_ORDER, compute_actions

class TestRouter:
    def test_intake_needs_approval(self) -> None:
        r = compute_actions({"current_phase": "intake", "approved": False, "issues": []})
        assert "approve_phase" in r.eligible

    def test_approved_advances(self) -> None:
        r = compute_actions({"current_phase": "intake", "approved": True, "human_approval_required": False, "issues": []})
        assert "advance_to_constitution" in r.eligible

    def test_blocking_stops(self) -> None:
        r = compute_actions({"current_phase": "script", "approved": True, "human_approval_required": False, "issues": [{"severity": "blocking"}]})
        assert len(r.blocked) == 1

    def test_human_gate_priority(self) -> None:
        r = compute_actions({"current_phase": "script", "approved": False, "human_approval_required": True, "issues": []})
        assert r.next_action == "wait_for_human"

    def test_phases_count(self) -> None:
        assert len(PHASE_ORDER) == 11

    def test_gates_mapped(self) -> None:
        for p in PHASE_ORDER:
            assert p in APPROVAL_GATES

class TestNodes:
    def test_intake_node(self) -> None:
        o = intake_node({})
        assert o["current_phase"] == "intake"

    def test_approve_node(self) -> None:
        o = approve_phase_node({"approved": False})
        assert o["approved"] is True

    def test_revision_node(self) -> None:
        o = request_revision_node({"issues": []})
        assert len(o["issues"]) == 1

class TestEdges:
    def test_after_phase_to_gate(self) -> None:
        assert after_phase({"current_phase": "script", "approved": False, "human_approval_required": True, "issues": []}) == "await_approval"

    def test_after_approval_next(self) -> None:
        assert after_approval({"current_phase": "intake", "approved": True}) == "constitution"

class TestGraph:
    def test_compiles(self) -> None:
        assert build_graph() is not None
EOF
make ci-check
```

Then `git add -A && git commit -m "feat: Phase 05 — LangGraph state machine"` and continue with **Phase 06**.

## Pending Phases (06–15)

Continue from Phase 06. Each has a plan file in `docs/implementation-plan/`. Build order:
- 06: KB Context Packet Builder
- 07: Agent Registry & Prompt Runner
- 08: Review Package Generator
- 09: Validation Registry
- 10: Mock Provider & Test Harness
- 11: Checkpoint/Resume & Rollback
- 12: E2E Mock Mini-Film
- 13: Real Provider Adapter
- 14: Post-Production Assembly
- 15: Production Hardening

## Key Conventions
- All code in `src/film_pipeline/`
- Tests in `tests/unit/`, `tests/integration/`, `tests/e2e/`
- `make ci-check` = format-check + lint + mypy strict + pytest (90% cov) + build
- Commit style: `feat: implement Phase XX — description`
- Node names in StateGraph must not conflict with state field names (use `*_node` suffix)
