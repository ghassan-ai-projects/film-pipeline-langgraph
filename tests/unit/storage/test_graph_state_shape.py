"""The graph state snapshot enforces the state schema's declared shape.

`StudioGraphState` declares every graph-state key with a type, but nothing
checked a persisted snapshot against it: `GraphStateSnapshot.state` was a bare
``dict[str, Any]``, so an undeclared key could reach disk and be read back
silently. These tests pin the check and record that real graph state conforms.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from film_pipeline.schemas.runtime_state import GraphStateSnapshot
from film_pipeline.studio.runtime import StudioRuntime


class TestCheckStateKeys:
    def test_declared_keys_pass(self) -> None:
        assert GraphStateSnapshot.check_state_keys({"project_id": "p1", "issues": []}) == []

    def test_undeclared_key_is_reported(self) -> None:
        found = GraphStateSnapshot.check_state_keys({"project_id": "p1", "not_a_real_key": 1})
        assert found == ["not_a_real_key"]

    def test_reports_every_undeclared_key_sorted(self) -> None:
        found = GraphStateSnapshot.check_state_keys({"zeta": 1, "alpha": 2})
        assert found == ["alpha", "zeta"]

    def test_empty_state_is_clean(self) -> None:
        assert GraphStateSnapshot.check_state_keys({}) == []


class TestRealGraphStateConforms:
    def test_fresh_project_state_is_declared(self) -> None:
        root = Path(tempfile.mkdtemp()) / "runtime"
        rt = StudioRuntime(server_mode="mock", runtime_root=root)
        state = rt.create_project("p1", "T", "p1")
        assert GraphStateSnapshot.check_state_keys(state) == []

    def test_state_after_a_graph_run_is_declared(self) -> None:
        """The schema must cover what the graph actually produces.

        This is the measurement that says the contract is real rather than
        aspirational: a full intake run adds ~18 keys, and every one is
        declared.
        """
        root = Path(tempfile.mkdtemp()) / "runtime"
        rt = StudioRuntime(server_mode="mock", runtime_root=root)
        state = rt.create_project("p1", "T", "p1")
        state["idea"] = "a lighthouse keeper"
        result = rt.run_graph(state)
        assert len(result) > len(state), "expected the graph to add state"
        assert GraphStateSnapshot.check_state_keys(result) == []

    def test_persisted_snapshot_round_trips(self) -> None:
        root = Path(tempfile.mkdtemp()) / "runtime"
        rt = StudioRuntime(server_mode="mock", runtime_root=root)
        state = rt.create_project("p1", "T", "p1")
        state["idea"] = "a lighthouse keeper"
        result = rt.run_graph(state)
        rt.projects["p1"] = result
        rt._persist_project_state("p1")
        snapshot_path = rt.project_roots["p1"] / "state" / "graph-state.json"
        assert snapshot_path.exists()
        snapshot = GraphStateSnapshot.model_validate_json(snapshot_path.read_text())
        assert GraphStateSnapshot.check_state_keys(snapshot.state) == []
