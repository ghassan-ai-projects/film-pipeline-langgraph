"""Integration coverage for the new node-level scope-contract wiring.

Exercises the real intake_node / development_node / script_node through mock
GraphServices so the integration glue (not just the pure derivation function)
is covered: contract attachment, the dev-scene-count helper, and the auto-mode
approval-withholding path end to end.
"""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.graph import nodes
from film_pipeline.graph.nodes import _attach_scope_contract, _development_scene_count
from film_pipeline.graph.services import SERVICES_KEY, GraphServices

_AUTO_CFG = {"studio": {"require_human_approval": False}}


@pytest.fixture(autouse=True)
def _reset_services_contextvar() -> Any:
    """Ensure the module-level services ContextVar never leaks between tests.

    ``_mock_state`` sets it as a fallback path for nested lazy-imported helpers;
    without an explicit reset, ``ContextVar.set()`` persists for the rest of the
    test process (same thread), breaking unrelated "no services" tests.
    """
    token = nodes._SERVICES_CTX.set(None)
    yield
    nodes._SERVICES_CTX.reset(token)


def _mock_state(**extra: Any) -> dict[str, Any]:
    svc = GraphServices.for_mock_runtime()
    nodes._SERVICES_CTX.set(svc)
    state: dict[str, Any] = {
        "project_id": "probe",
        "idea": "a short film",
        "current_phase": "intake",
        SERVICES_KEY: svc,
        "resolved_config": _AUTO_CFG,
    }
    state.update(extra)
    return state


class TestAttachScopeContractDirect:
    def test_noop_when_runtime_is_zero(self) -> None:
        updates: dict[str, Any] = {"target_runtime_seconds": 0}
        new_refs: list[str] = []
        _attach_scope_contract({"project_id": "p"}, updates, new_refs)
        assert "scope_contract_ref" not in updates
        assert new_refs == []

    def test_noop_when_runtime_missing(self) -> None:
        updates: dict[str, Any] = {}
        new_refs: list[str] = []
        _attach_scope_contract({"project_id": "p"}, updates, new_refs)
        assert "scope_contract_ref" not in updates


def test_intake_node_attaches_scope_contract() -> None:
    state = _mock_state(target_runtime_seconds=300)
    updates = nodes.intake_node(state)
    assert updates.get("target_runtime_seconds") == 300
    assert updates.get("target_scene_count", 0) >= 1
    assert updates.get("min_scene_count", 0) >= 1
    assert updates.get("target_shot_count", 0) >= 1
    assert updates.get("scope_contract_ref")


def test_development_scene_count_no_services() -> None:
    assert _development_scene_count({"scene_list_ref": "artifact:x:v1"}) == 0


def test_development_scene_count_no_ref() -> None:
    svc = GraphServices.for_mock_runtime()
    assert _development_scene_count({SERVICES_KEY: svc}) == 0


def test_development_scene_count_bad_ref_returns_zero() -> None:
    svc = GraphServices.for_mock_runtime()
    state = {SERVICES_KEY: svc, "project_id": "probe", "scene_list_ref": "artifact:nope:v1"}
    assert _development_scene_count(state) == 0


def test_development_then_script_node_full_mock_flow() -> None:
    """Drives intake -> development -> script through mock services.

    Confirms the auto-mode Gate S withholding doesn't fire for the (now
    runtime-consistent) mock fixture, and that the dev-scene-count gate reads a
    real persisted artifact rather than failing closed.
    """
    state = _mock_state()
    intake_updates = nodes.intake_node(state)
    state.update(intake_updates)
    state.setdefault("artifact_refs", [])
    state["artifact_refs"].extend(intake_updates.get("artifact_refs", []) or [])

    dev_updates = nodes.development_node(state)
    blocking = [i for i in dev_updates.get("issues", []) if i.get("severity") == "blocking"]
    assert blocking == [], f"unexpected Gate S block on consistent mock fixture: {blocking}"
    assert dev_updates.get("approved") is True

    state.update(dev_updates)
    state["artifact_refs"].extend(dev_updates.get("artifact_refs", []) or [])

    script_updates = nodes.script_node(state)
    blocking = [i for i in script_updates.get("issues", []) if i.get("severity") == "blocking"]
    assert blocking == [], f"unexpected Gate S block on script phase: {blocking}"
    assert script_updates.get("approved") is True
