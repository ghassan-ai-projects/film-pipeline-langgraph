"""Unit tests for shared MCP tool helpers."""

from __future__ import annotations

from typing import Any

import pytest

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.mcp.envelope import RequestEnvelope
from film_pipeline.mcp.tools.helpers import (
    _active_project_state,
    _active_project_with_state,
    _store_project_state,
)


class _Runtime:
    def __init__(
        self,
        projects: dict[str, dict[str, Any]],
        active_project_id: str = "",
        missing_project_id: str | None = None,
    ) -> None:
        self.projects = projects
        self.active_project_id = active_project_id
        self.missing_project_id = missing_project_id

    def get_active(self) -> dict[str, Any] | None:
        if not self.active_project_id:
            return None
        return self.projects.get(self.active_project_id)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        if project_id == self.missing_project_id:
            return None
        return self.projects.get(project_id)


class _PersistingRuntime:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}
        self.persisted: list[tuple[str, dict[str, Any]]] = []

    def _persist_project_state(self, project_id: str) -> None:
        self.persisted.append((project_id, self.projects[project_id]))


class _FailingPersistRuntime(_PersistingRuntime):
    def _persist_project_state(self, project_id: str) -> None:
        raise RuntimeError(f"persist failed for {project_id}")


def test_active_project_with_state_uses_active_project() -> None:
    state = {"project_id": "active"}
    runtime = _Runtime({"active": state}, active_project_id="active")

    result = _active_project_with_state({}, runtime)

    assert result is not None
    assert result[0] == "active"
    assert result[1] is state


def test_active_project_with_state_prefers_resolved_envelope_project() -> None:
    active_state = {"project_id": "active"}
    envelope_state = {"project_id": "envelope"}
    runtime = _Runtime(
        {"active": active_state, "envelope": envelope_state}, active_project_id="active"
    )

    result = _active_project_with_state(
        {"_envelope": RequestEnvelope("request-1", resolved_project_id="envelope")}, runtime
    )

    assert result == ("envelope", envelope_state)
    assert result[1] is envelope_state


def test_active_project_with_state_returns_none_without_project() -> None:
    runtime = _Runtime({}, active_project_id="")

    assert _active_project_with_state({}, runtime) is None


def test_active_project_with_state_returns_none_for_missing_state() -> None:
    state = {"project_id": "active"}
    runtime = _Runtime({"active": state}, active_project_id="active", missing_project_id="active")

    assert _active_project_with_state({}, runtime) is None


def test_active_project_state_keeps_state_only_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {"project_id": "state-only"}
    runtime = _Runtime({"state-only": state}, active_project_id="state-only")
    monkeypatch.setattr(tools_pkg, "get_runtime", lambda: runtime)

    result = _active_project_state({})

    assert result is state


def test_store_project_state_preserves_identity_and_persistence_order() -> None:
    runtime = _PersistingRuntime()
    state = {"project_id": "stored"}

    _store_project_state(runtime, "stored", state)

    assert runtime.projects["stored"] is state
    assert runtime.persisted == [("stored", state)]
    assert runtime.persisted[0][1] is state


def test_store_project_state_propagates_persistence_errors() -> None:
    runtime = _FailingPersistRuntime()
    state = {"project_id": "failed"}

    with pytest.raises(RuntimeError, match="persist failed for failed"):
        _store_project_state(runtime, "failed", state)

    assert runtime.projects["failed"] is state
