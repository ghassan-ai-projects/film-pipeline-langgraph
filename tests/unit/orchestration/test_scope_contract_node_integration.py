"""Integration coverage for the new node-level scope-contract wiring.

Exercises the real intake_node / development_node / script_node through mock
GraphServices so the integration glue (not just the pure derivation function)
is covered: contract attachment, the dev-scene-count helper, and the auto-mode
approval-withholding path end to end.
"""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.orchestration import nodes
from film_pipeline.orchestration.nodes import _attach_scope_contract, _development_scene_count
from film_pipeline.orchestration.services import _SERVICES_CTX, SERVICES_KEY, GraphServices
from film_pipeline.orchestration.state_schema import StudioGraphState
from film_pipeline.studio.mock_responses import default_mock_responses

_AUTO_CFG: dict[str, object] = {"studio": {"require_human_approval": False}}


@pytest.fixture(autouse=True)
def _reset_services_contextvar() -> Any:
    """Ensure the module-level services ContextVar never leaks between tests.

    ``_mock_state`` sets it as a fallback path for nested lazy-imported helpers;
    without an explicit reset, ``ContextVar.set()`` persists for the rest of the
    test process (same thread), breaking unrelated "no services" tests.
    """
    token = _SERVICES_CTX.set(None)
    yield
    _SERVICES_CTX.reset(token)


def _mock_state(**extra: Any) -> StudioGraphState:
    """Build the probe state as the typed graph-state contract.

    ``SERVICES_KEY`` is a module constant, and a TypedDict literal only accepts
    the literal key, so the services handle is written under its literal name.
    ``**extra`` cannot be merged by ``update`` for the same reason (a computed
    key), so the one key these tests pass is applied explicitly.
    """
    svc = GraphServices.for_mock_runtime(mock_responses=default_mock_responses())
    _SERVICES_CTX.set(svc)
    state: StudioGraphState = {
        "project_id": "probe",
        "idea": "a short film",
        "current_phase": "intake",
        "_services": svc,
        "resolved_config": _AUTO_CFG,
    }
    runtime_seconds = extra.get("target_runtime_seconds")
    if isinstance(runtime_seconds, int):
        state["target_runtime_seconds"] = runtime_seconds
    return state


def _set_str_key(state: StudioGraphState, key: str, value: str) -> None:
    """Write one string-valued contract key by name (a loop cannot be literal-typed)."""
    if key == "current_phase":
        state["current_phase"] = value
    elif key == "idea":
        state["idea"] = value
    elif key == "profile_ref":
        state["profile_ref"] = value
    elif key == "constraints_ref":
        state["constraints_ref"] = value
    elif key == "scope_contract_ref":
        state["scope_contract_ref"] = value


def _set_int_key(state: StudioGraphState, key: str, value: int) -> None:
    """Write one int-valued contract key by name (a loop cannot be literal-typed)."""
    if key == "target_runtime_seconds":
        state["target_runtime_seconds"] = value
    elif key == "target_scene_count":
        state["target_scene_count"] = value
    elif key == "min_scene_count":
        state["min_scene_count"] = value
    elif key == "target_shot_count":
        state["target_shot_count"] = value


def _merge_updates(state: StudioGraphState, updates: dict[str, Any]) -> None:
    """Apply a node's returned updates to the accumulated state, LangGraph-style.

    A node returns an opaque ``dict[str, Any]`` accumulator (it carries
    registry-driven channel keys a TypedDict cannot name), so it cannot be
    splatted into the typed state. Only the contract keys these tests drive are
    carried, and ``artifact_refs`` keeps its append semantics: the node returns
    just the refs it created.
    """
    for key in (
        "current_phase",
        "idea",
        "profile_ref",
        "constraints_ref",
        "scope_contract_ref",
    ):
        value = updates.get(key)
        if isinstance(value, str):
            _set_str_key(state, key, value)
    int_keys = (
        "target_runtime_seconds",
        "target_scene_count",
        "min_scene_count",
        "target_shot_count",
    )
    for key in int_keys:
        value = updates.get(key)
        if isinstance(value, int):
            _set_int_key(state, key, value)
    new_refs = updates.get("artifact_refs")
    if isinstance(new_refs, list):
        state["artifact_refs"] = [
            *(state.get("artifact_refs") or []),
            *(ref for ref in new_refs if isinstance(ref, str)),
        ]


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
    svc = GraphServices.for_mock_runtime(mock_responses=default_mock_responses())
    assert _development_scene_count({SERVICES_KEY: svc}) == 0


def test_development_scene_count_bad_ref_returns_zero() -> None:
    svc = GraphServices.for_mock_runtime(mock_responses=default_mock_responses())
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
    _merge_updates(state, intake_updates)

    dev_updates = nodes.development_node(state)
    blocking = [i for i in dev_updates.get("issues", []) if i.get("severity") == "blocking"]
    assert blocking == [], f"unexpected Gate S block on consistent mock fixture: {blocking}"
    assert dev_updates.get("approved") is True

    _merge_updates(state, dev_updates)

    script_updates = nodes.script_node(state)
    blocking = [i for i in script_updates.get("issues", []) if i.get("severity") == "blocking"]
    assert blocking == [], f"unexpected Gate S block on script phase: {blocking}"
    assert script_updates.get("approved") is True
