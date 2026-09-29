"""What one state-changing MCP action must do at the server boundary.

Source of the invariants: ``docs/modularity-improvements/10-boundary-audit.md``
finding B4, whose "next checks" ask for exactly this — characterize *one*
state-changing action at ``MCPServer.call`` and check refusal, persisted state,
audit, and restart behaviour, to learn whether the live-mapping reach-in removes a
real failure path.

The action is ``create_film_project`` with an accompanying idea, because it is the
one handler that both creates a project and runs the graph, so it exercises
creation, intake, state replacement and persistence in a single call.

The reach-in this pins: ``StudioRuntime.projects`` is a public mutable mapping and
``get_project`` returns its members rather than copies, so a handler writing
``rt.projects[project_id] = state`` replaces live runtime state with no operation
boundary and no required persistence. Measured before the repair: four such writes
outside ``studio``, all of them redundant — the handler had already mutated the
live mapping, so the assignment was a self-assignment whose only real content was
the following ``persist_project_state`` call. ``apply_project_state`` is that pair
as one named operation, and these tests assert the observable effects the reach-in
made optional.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest

from film_pipeline.mcp.server import MCPServer
from film_pipeline.studio.runtime import StudioRuntime, get_runtime

PROJECT_ID = "boundary-b4"


def _server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> StudioRuntime:
    """Install an isolated runtime as the process runtime, and return it."""
    from film_pipeline.studio.runtime import install_runtime

    runtime = StudioRuntime(runtime_root=tmp_path / "runtime")
    runtime.seed_default_provider_adapters()
    install_runtime(runtime, mode="mock")
    return runtime


def _call(server: MCPServer, tool: str, args: dict[str, object]) -> dict[str, Any]:
    response = asyncio.run(server.call(tool, args))
    assert response.success is True, response.error
    return cast(dict[str, Any], response.data)


def test_a_state_changing_action_persists_what_it_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The state the call reports is the state on disk, not only in memory.

    This is the contract the direct mapping write did not enforce: a handler could
    replace the live mapping and return the new state without ever persisting it,
    and every other guard would stay green because the fields are public.
    """
    runtime = _server(tmp_path, monkeypatch)
    server = MCPServer()

    data = _call(
        server,
        "create_film_project",
        {"project_id": PROJECT_ID, "title": "Boundary B4", "idea": "A lantern in fog."},
    )

    in_memory = runtime.get_project(PROJECT_ID)
    assert in_memory is not None, "the call must leave the project loaded"
    assert data["project_id"] == PROJECT_ID

    # The durable record `persist_project_state` writes.
    from film_pipeline.storage import _layout

    record_path = tmp_path / "runtime" / "projects" / PROJECT_ID / _layout.PROJECT_FILENAME
    if not record_path.exists():
        # The runtime root may nest storage differently; find the record.
        candidates = sorted(tmp_path.rglob(_layout.PROJECT_FILENAME))
        assert candidates, (
            "the action reported new state but no project record reached disk — "
            "`apply_project_state` persists in the same call for this reason"
        )
        record_path = candidates[0]
    assert record_path.exists()
    assert PROJECT_ID in record_path.read_text()


def test_the_live_mapping_is_shared_and_the_operation_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`get_project` returns the live mapping; the operation is the declared write.

    Stated as a test because it is the fact that decides B4's repair shape: making
    the accessor return a copy would change every caller, while naming the write
    operation costs nothing and is what handlers now use. If a future change makes
    the accessor copy, this test fails and the decision gets remade deliberately.
    """
    runtime = _server(tmp_path, monkeypatch)
    runtime.create_project(PROJECT_ID, "Shared Mapping")

    assert runtime.get_project(PROJECT_ID) is runtime.projects[PROJECT_ID], (
        "get_project now returns a copy. That is a legitimate change, but it "
        "invalidates the comment in `apply_project_state` — update both together."
    )


def test_apply_project_state_refuses_an_unknown_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replacing the state of a project the runtime does not have must fail."""
    runtime = _server(tmp_path, monkeypatch)

    with pytest.raises(KeyError, match="not loaded"):
        runtime.apply_project_state("no-such-project", {"project_id": "no-such-project"})


def test_apply_project_state_is_visible_to_the_process_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The write lands on the runtime the server reads, through the installed runtime."""
    runtime = _server(tmp_path, monkeypatch)
    runtime.create_project(PROJECT_ID, "Visible")
    state = runtime.get_project(PROJECT_ID)
    assert state is not None
    state["current_phase"] = "script"

    runtime.apply_project_state(PROJECT_ID, state)

    assert get_runtime().get_project(PROJECT_ID)["current_phase"] == "script"  # type: ignore[index]


def test_a_refused_action_leaves_project_state_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mutating action without confirmation must not reach the state write.

    The refusal half of the audit's check list. `create_film_project` is not
    confirmation-gated, so `approve_phase` is used: it mutates, and it requires
    `confirmed`.
    """
    runtime = _server(tmp_path, monkeypatch)
    runtime.create_project(PROJECT_ID, "Refusal")
    runtime.set_active(PROJECT_ID)
    before = dict(cast(dict[str, Any], runtime.get_project(PROJECT_ID)))
    server = MCPServer()

    response = asyncio.run(server.call("approve_phase", {}))

    assert response.success is False
    assert response.error is not None
    after = cast(dict[str, Any], runtime.get_project(PROJECT_ID))
    assert after == before, "a refused action changed project state"
