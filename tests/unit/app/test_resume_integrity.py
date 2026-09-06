"""Resume-integrity contracts [D6/O-F4].

The approval-gate resume may fall back to manual advance *only* when no
checkpoint exists for the thread (empty ``get_state`` snapshot). Any other
failure is audited as ``resume_failed`` and re-raised — gates cannot be
silently bypassed. Also pins the staleness-quartet helpers branch by branch,
and the visible-failure contract of ``auto_checkpoint``.
"""

from __future__ import annotations

import logging
from typing import Any, cast

import pytest

from film_pipeline.app import _graph_exec
from film_pipeline.app._resume import (
    _approval_made_progress,
    _build_resume_payload,
    _has_stale_generation_request_blocker,
    _preserve_external_generation_requests,
    _strip_stale_generation_request_blockers,
)
from film_pipeline.app.runtime import StudioRuntime


class _FakeSnapshot:
    def __init__(
        self,
        values: dict[str, Any] | None,
        nxt: tuple[str, ...] = (),
        tasks: tuple[Any, ...] = (),
    ) -> None:
        self.values = values or {}
        self.next = nxt
        self.tasks = tasks


class _FakeGraph:
    """Records interactions; configurable snapshot and invoke behavior."""

    def __init__(
        self,
        snapshot: _FakeSnapshot | None = None,
        result_state: dict[str, Any] | None = None,
        invoke_error: Exception | None = None,
    ) -> None:
        self.snapshot = snapshot or _FakeSnapshot({})
        self.result_state = result_state or {}
        self.invoke_error = invoke_error
        self.invoke_calls = 0
        self.last_input: Any = None

    def get_state(self, config: dict[str, Any]) -> _FakeSnapshot:
        return self.snapshot

    def invoke(self, command: Any, config: dict[str, Any]) -> dict[str, Any]:
        self.invoke_calls += 1
        self.last_input = command
        if self.invoke_error is not None:
            raise self.invoke_error
        return self.result_state


@pytest.fixture()
def rt(tmp_path: Any) -> StudioRuntime:
    runtime = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
    root = tmp_path / "roots" / "p1"
    root.mkdir(parents=True, exist_ok=True)
    runtime.projects["p1"] = {"project_id": "p1", "current_phase": ""}
    runtime.project_roots["p1"] = root
    return runtime


def _active() -> dict[str, Any]:
    return {"project_id": "p1", "current_phase": ""}


def _audit(rt: StudioRuntime, action: str) -> list[dict[str, Any]]:
    return [e for e in rt.audit_events if e.get("action") == action]


def _patch_graph(monkeypatch: pytest.MonkeyPatch, graph: _FakeGraph) -> None:
    monkeypatch.setattr(_graph_exec, "ensure_graph", lambda _rt: graph)


# --- Resume fallback classification ------------------------------------------


def test_no_checkpoint_snapshot_advances_without_invoking(
    rt: StudioRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty get_state snapshot → legitimate manual-advance path."""
    graph = _FakeGraph(snapshot=_FakeSnapshot({}))
    _patch_graph(monkeypatch, graph)
    state = _graph_exec._resume_after_approval(rt, _active(), "")
    assert state.get("project_id") == "p1"
    assert graph.invoke_calls == 0
    assert not _audit(rt, "resume_failed")


def test_generic_resume_failure_raises_and_audits(
    rt: StudioRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing resume must never silently bypass the human gate."""
    graph = _FakeGraph(
        snapshot=_FakeSnapshot({"current_phase": "script"}),
        invoke_error=RuntimeError("boom"),
    )
    _patch_graph(monkeypatch, graph)
    with pytest.raises(RuntimeError, match="boom"):
        _graph_exec._resume_after_approval(rt, _active(), "script")
    events = _audit(rt, "resume_failed")
    assert len(events) == 1
    event = events[0]
    assert event["actor"] == "system"
    assert event["details"]["error"] == "RuntimeError"
    assert event["details"]["project_id"] == "p1"
    assert event["details"]["phase"] == "script"


def test_successful_resume_returns_state_without_failure_audit(
    rt: StudioRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    result_state: dict[str, Any] = {"project_id": "p1", "current_phase": "gen_planning"}
    graph = _FakeGraph(
        snapshot=_FakeSnapshot({"current_phase": "gen_planning"}),
        result_state=result_state,
    )
    _patch_graph(monkeypatch, graph)
    state = _graph_exec._resume_after_approval(rt, _active(), "")
    assert state is result_state
    assert not _audit(rt, "resume_failed")
    assert not _audit(rt, "resume_stalled_manual_advance")


def test_revision_reenters_repair_from_failed_start_checkpoint(
    rt: StudioRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A persisted ``__start__`` failure must be recovered with graph input."""
    result_state: dict[str, Any] = {"project_id": "p1", "current_phase": "shot_bible"}
    graph = _FakeGraph(
        snapshot=_FakeSnapshot({"current_phase": "shot_bible"}, ("__start__",)),
        result_state=result_state,
    )
    rt.active_project_id = "p1"
    _patch_graph(monkeypatch, graph)

    state = _graph_exec.request_revision(rt, "Align the shot matrix with the brief.")

    assert state is result_state
    assert graph.invoke_calls == 1
    assert isinstance(graph.last_input, dict)
    assert graph.last_input["_resume_to_repair"] is True
    assert graph.last_input["_revision_note"] == "Align the shot matrix with the brief."
    assert not _audit(rt, "resume_failed")


def test_revision_uses_interrupt_resume_when_approval_is_pending(
    rt: StudioRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A live approval interrupt keeps the normal LangGraph resume path."""
    result_state: dict[str, Any] = {"project_id": "p1", "current_phase": "shot_bible"}
    graph = _FakeGraph(
        snapshot=_FakeSnapshot({"current_phase": "shot_bible"}, ("await_approval",)),
        result_state=result_state,
    )
    rt.active_project_id = "p1"
    _patch_graph(monkeypatch, graph)

    _graph_exec.request_revision(rt, "Please revise the structure.")

    assert graph.invoke_calls == 1
    assert graph.last_input.resume["action"] == "revise"


def test_real_graph_recovers_failed_start_and_reaches_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A poisoned start checkpoint is repaired through the actual graph wiring."""
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.errors import InvalidUpdateError
    from langgraph.types import Command

    from film_pipeline.graph import graph as graph_module

    reached_repair: list[bool] = []

    def fake_repair(state: dict[str, Any]) -> dict[str, Any]:
        reached_repair.append(bool(state.get("_resume_to_repair")))
        return {
            "current_phase": "shot_bible",
            "approved": False,
            "human_approval_required": True,
            "human_approval_phase": "shot_bible",
            "issues": [],
            "_resume_to_repair": False,
        }

    monkeypatch.setattr(graph_module, "repair_phase_node", fake_repair)
    graph = graph_module.build_graph(checkpointer=MemorySaver())
    config: RunnableConfig = {"configurable": {"thread_id": "poisoned-start"}}

    with pytest.raises(InvalidUpdateError, match="Must write to at least one"):
        graph.invoke(Command(resume={"action": "revise"}), config)

    result = graph.invoke(
        {
            "project_id": "poisoned-start",
            "current_phase": "shot_bible",
            "_resume_to_repair": True,
        },
        config,
    )
    snapshot = graph.get_state(config)

    assert reached_repair == [True]
    assert result["current_phase"] == "shot_bible"
    assert snapshot.next == ("await_approval",)


def test_stalled_resume_advances_and_audits(
    rt: StudioRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stall detection still falls back — visibly."""
    graph = _FakeGraph(
        snapshot=_FakeSnapshot({"current_phase": ""}),
        result_state={"project_id": "p1", "current_phase": ""},
    )
    _patch_graph(monkeypatch, graph)
    state = _graph_exec._resume_after_approval(rt, _active(), "")
    assert state.get("project_id") == "p1"
    events = _audit(rt, "resume_stalled_manual_advance")
    assert len(events) == 1
    assert events[0]["actor"] == "system"
    assert events[0]["details"]["project_id"] == "p1"


# --- Auto-checkpoint visibility ------------------------------------------------


class _ExplodingManager:
    def create(self, **_: Any) -> Any:
        raise ValueError("disk full")


def test_auto_checkpoint_failure_is_visible_but_non_fatal(
    rt: StudioRuntime, caplog: pytest.LogCaptureFixture
) -> None:
    rt.projects["p1"] = {"project_id": "p1", "current_phase": "script"}
    # Test double for the checkpoint manager; the real one owns git plumbing.
    rt.checkpoint_managers["p1"] = cast(Any, _ExplodingManager())
    with caplog.at_level(logging.WARNING, logger="film_pipeline.app._graph_exec"):
        _graph_exec.auto_checkpoint(rt, {"project_id": "p1", "current_phase": "script"})
    events = _audit(rt, "auto_checkpoint_failed")
    assert len(events) == 1
    assert events[0]["details"]["error"].startswith("disk full")
    assert any("Auto-checkpoint failed" in rec.message for rec in caplog.records)


# --- Staleness quartet: table-driven branch coverage ----------------------------


@pytest.mark.parametrize(
    ("state", "previous", "expected"),
    [
        ({"completed": True}, "intake", True),
        ({"_approval_blocked_by_issues": True}, "intake", True),
        ({"issues": [{"severity": "blocking"}]}, "intake", True),
        ({"current_phase": "script"}, "script", False),
        ({"current_phase": "script"}, "intake", True),
        ({"current_phase": "intake"}, "script", False),
        ({"current_phase": "custom_phase"}, "unknown_prev", True),
        ({"current_phase": ""}, "unknown_prev", False),
    ],
    ids=[
        "completed",
        "approval-blocked",
        "blocking-issue",
        "same-phase",
        "forward",
        "backward",
        "unknown-prev-nonempty",
        "unknown-prev-empty",
    ],
)
def test_approval_made_progress_branches(
    state: dict[str, Any], previous: str, expected: bool
) -> None:
    assert _approval_made_progress(state, previous) is expected


def test_stale_blocker_requires_generation_phase_with_missing_requests() -> None:
    resumed: dict[str, Any] = {
        "issues": [{"code": "no_generation_requests", "severity": "blocking"}]
    }
    active_gen: dict[str, Any] = {"current_phase": "generation", "generation_requests": [{"x": 1}]}
    assert _has_stale_generation_request_blocker(resumed, active_gen) is True


def test_stale_blocker_false_when_not_applicable() -> None:
    issue = {"code": "no_generation_requests", "severity": "blocking"}
    active_gen: dict[str, Any] = {"current_phase": "generation", "generation_requests": [{}]}
    assert _has_stale_generation_request_blocker({}, active_gen) is False  # wrong phase
    assert (
        _has_stale_generation_request_blocker(
            {"issues": [issue]}, {"current_phase": "script", "generation_requests": [{}]}
        )
        is False
    )  # right issue, wrong phase


def test_stale_blocker_false_when_resumed_already_has_requests() -> None:
    resumed: dict[str, Any] = {
        "generation_requests": [{"id": "r1"}],
        "issues": [{"code": "empty_generation_requests"}],
    }
    active_gen: dict[str, Any] = {"current_phase": "generation", "generation_requests": [{}]}
    assert _has_stale_generation_request_blocker(resumed, active_gen) is False


def test_stale_blocker_false_for_unrelated_issue_codes() -> None:
    resumed: dict[str, Any] = {"issues": [{"code": "something_else"}]}
    active_gen: dict[str, Any] = {"current_phase": "generation", "generation_requests": [{}]}
    assert _has_stale_generation_request_blocker(resumed, active_gen) is False


def test_stale_blocker_guard_branches() -> None:
    """Non-dict-shape guards: empty active requests and non-list issues."""
    active_gen: dict[str, Any] = {"current_phase": "generation"}
    # Active requests empty → never stale, whatever the issues hold.
    assert (
        _has_stale_generation_request_blocker(
            {"issues": [{"code": "no_generation_requests"}]}, active_gen
        )
        is False
    )
    # Resumed issues not a list → treated as absent.
    resumed: dict[str, Any] = {
        "issues": "not-a-list",
        "generation_requests": None,
    }
    active_with_requests: dict[str, Any] = {
        "current_phase": "generation",
        "generation_requests": [{}],
    }
    assert _has_stale_generation_request_blocker(resumed, active_with_requests) is False


def test_strip_ignores_non_list_issues() -> None:
    state: dict[str, Any] = {"generation_requests": [{}], "issues": "not-a-list"}
    _strip_stale_generation_request_blockers(state)
    assert state["issues"] == "not-a-list"


def test_preserve_external_requests_copies_when_resumed_empty() -> None:
    resumed: dict[str, Any] = {}
    active: dict[str, Any] = {"generation_requests": [{"id": "ext"}]}
    _preserve_external_generation_requests(resumed, active)
    assert resumed["generation_requests"] == [{"id": "ext"}]


def test_preserve_external_requests_noop_when_resumed_has_own() -> None:
    resumed: dict[str, Any] = {"generation_requests": [{"id": "own"}]}
    active: dict[str, Any] = {"generation_requests": [{"id": "ext"}]}
    _preserve_external_generation_requests(resumed, active)
    assert resumed["generation_requests"] == [{"id": "own"}]


def test_strip_removes_only_stale_codes_when_requests_restored() -> None:
    state: dict[str, Any] = {
        "generation_requests": [{"id": "r1"}],
        "issues": [
            {"issue_id": "a", "code": "no_generation_requests"},
            {"issue_id": "b", "code": "other"},
            {"issue_id": "c", "code": "empty_generation_requests"},
        ],
    }
    _strip_stale_generation_request_blockers(state)
    assert [i["issue_id"] for i in state["issues"]] == ["b"]


def test_strip_noop_without_requests() -> None:
    issues = [{"code": "no_generation_requests"}]
    state: dict[str, Any] = {"issues": issues}
    _strip_stale_generation_request_blockers(state)
    assert state["issues"] == issues


@pytest.mark.parametrize(
    ("active", "note", "expect_external"),
    [
        ({"generation_requests": [{"b": 2}, {"a": 1}]}, "n", True),
        ({}, "", False),
    ],
    ids=["with-requests", "without-requests"],
)
def test_build_resume_payload(active: dict[str, Any], note: str, expect_external: bool) -> None:
    payload = _build_resume_payload("approve", active, note=note)
    assert payload["action"] == "approve"
    if note:
        assert payload["note"] == note
    if expect_external:
        external = payload["_external_state"]
        assert external["generation_requests"] == [{"b": 2}, {"a": 1}]
        # Sorted remove codes keep the instruction deterministic.
        assert external["remove_issue_codes"] == [
            "empty_generation_requests",
            "no_generation_requests",
        ]
    else:
        assert "_external_state" not in payload
