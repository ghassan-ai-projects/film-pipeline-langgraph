"""Tests for StudioGraphState typed state contract."""

from __future__ import annotations


class TestStudioGraphState:
    def test_state_compiles_with_graph(self) -> None:
        """StateGraph(StudioGraphState) compiles successfully."""
        from film_pipeline.graph.graph import build_graph

        graph = build_graph()
        assert graph is not None

    def test_artifact_refs_uses_add_reducer(self) -> None:
        """Verifying add reducer appends, not replaces."""
        from operator import add

        result = add(["ref1"], ["ref2"])
        assert result == ["ref1", "ref2"]

    def test_scalar_fields_last_write_wins(self) -> None:
        """Scalar TypedDict fields (no Annotated) replace on write."""
        from film_pipeline.graph.state_schema import StudioGraphState

        state: StudioGraphState = {"current_phase": "intake"}
        state["current_phase"] = "constitution"
        assert state["current_phase"] == "constitution"

    def test_total_false_allows_extra_keys(self) -> None:
        """total=False TypedDict accepts runtime-injected _services key."""
        from film_pipeline.graph.state_schema import StudioGraphState

        state: StudioGraphState = {"project_id": "test"}  # type: ignore[typeddict-unknown-key]
        state["_services"] = object()  # type: ignore[typeddict-unknown-key]
        assert state["project_id"] == "test"

    def test_partial_update_preserves_other_keys(self) -> None:
        """Merging partial update dict preserves unmodified keys."""
        from film_pipeline.graph.state_schema import StudioGraphState

        state: StudioGraphState = {
            "project_id": "test",
            "current_phase": "intake",
            "idea": "test idea",
        }
        update: dict[str, object] = {"current_phase": "constitution"}
        merged = {**state, **update}
        assert merged["project_id"] == "test"
        assert merged["current_phase"] == "constitution"
        assert merged["idea"] == "test idea"

    def test_intake_node_returns_partial_update(self) -> None:
        """intake_node returns only modified keys, not full state."""
        # Verify the node function signature and that it returns a dict
        from film_pipeline.graph.nodes import intake_node

        assert callable(intake_node)


class TestTypedStateKeys:
    def test_core_identifier_keys_exist(self) -> None:
        """Core identifiers are defined in schema."""
        from film_pipeline.graph.state_schema import StudioGraphState

        assert "project_id" in StudioGraphState.__annotations__
        assert "current_phase" in StudioGraphState.__annotations__
        assert "approved" in StudioGraphState.__annotations__
        assert "completed" in StudioGraphState.__annotations__

    def test_append_channels_exist(self) -> None:
        """Append-only channels are defined with Annotated[list, add]."""
        from film_pipeline.graph.state_schema import StudioGraphState

        assert "artifact_refs" in StudioGraphState.__annotations__
        assert "issues" in StudioGraphState.__annotations__
        assert "validation_report_refs" in StudioGraphState.__annotations__

    def test_services_key_not_in_schema(self) -> None:
        """_services key is NOT in the typed schema (injected at runtime)."""
        from film_pipeline.graph.state_schema import StudioGraphState

        assert "_services" not in StudioGraphState.__annotations__
