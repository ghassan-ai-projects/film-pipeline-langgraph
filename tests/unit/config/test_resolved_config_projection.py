"""`config` owns the projection of a resolved configuration onto graph state.

Three call sites used to build the same five keys by hand — two in `mcp`, one
in `operations` — with small divergences: `["sources"]` vs `.get("sources", [])`
(which raises versus defaults), and an inline cast where another site called a
helper. `resolved_config_state_keys` is now the single producer.
"""

from __future__ import annotations

from film_pipeline.config.profile_resolver import resolved_config_state_keys


def _resolved() -> dict[str, object]:
    return {
        "raw": {"studio": {"require_human_approval": True}},
        "sources": ["base.studio", "quality.festival"],
        "conflicts": [{"code": "c1", "message": "m", "severity": "warning"}],
    }


class TestResolvedConfigStateKeys:
    def test_carries_the_profile_stack(self) -> None:
        keys = resolved_config_state_keys({"quality_profile": "festival"}, _resolved())
        assert keys["profile_stack"] == {"quality_profile": "festival"}

    def test_carries_the_raw_config(self) -> None:
        keys = resolved_config_state_keys({}, _resolved())
        assert keys["resolved_config"] == {"studio": {"require_human_approval": True}}

    def test_sources_are_a_list_of_strings(self) -> None:
        """The schema declares a list; the producer must not coerce it away."""
        keys = resolved_config_state_keys({}, _resolved())
        assert keys["resolved_config_sources"] == ["base.studio", "quality.festival"]

    def test_conflicts_are_carried(self) -> None:
        keys = resolved_config_state_keys({}, _resolved())
        assert keys["config_conflicts"] == [{"code": "c1", "message": "m", "severity": "warning"}]

    def test_missing_sources_defaults_to_empty(self) -> None:
        """A partial resolution must not raise, unlike the old `["sources"]`."""
        keys = resolved_config_state_keys({}, {"raw": {}})
        assert keys["resolved_config_sources"] == []
        assert keys["config_conflicts"] == []

    def test_non_dict_raw_degrades_to_empty(self) -> None:
        keys = resolved_config_state_keys({}, {"raw": "not-a-dict"})
        assert keys["resolved_config"] == {}

    def test_matches_the_declared_schema_types(self) -> None:
        """Every produced key must agree with `StudioGraphState`."""
        from film_pipeline.orchestration.state_schema import StudioGraphState

        declared = StudioGraphState.__annotations__
        keys = resolved_config_state_keys({"quality_profile": "festival"}, _resolved())
        assert set(keys) <= set(declared)
        assert isinstance(keys["resolved_config_sources"], list)
        assert isinstance(keys["profile_stack"], dict)
