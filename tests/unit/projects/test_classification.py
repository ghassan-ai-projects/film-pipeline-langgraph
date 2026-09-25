"""Project classification policy has one owner.

Folder-name classification decides whether a project is real production work or
throwaway test scaffolding, and the title rule decides what a human sees in the
project list. Both were private helpers inside the operator service's discovery
module; they are now owned by `film_pipeline.projects.classification` so every
surface shares one definition.
"""

from __future__ import annotations

import pytest

from film_pipeline.operations.errors import BackendOperationError
from film_pipeline.projects.classification import (
    VALID_PROJECT_KINDS,
    normalize_project_kind,
    project_kind_for_name,
    project_kind_for_state,
    project_title_from_id,
)


class TestProjectKindForName:
    @pytest.mark.parametrize(
        "name", ["my-film", "lighthouse", "the-third-interval", "production-2024"]
    )
    def test_ordinary_names_are_production(self, name: str) -> None:
        assert project_kind_for_name(name) == "production"

    @pytest.mark.parametrize(
        "name",
        ["test-project", "my-fixture", "sample-run", "tmp-scratch", "demo-reel"],
    )
    def test_marker_names_are_test(self, name: str) -> None:
        assert project_kind_for_name(name) == "test"

    def test_matching_is_case_insensitive(self) -> None:
        assert project_kind_for_name("TEST-Project") == "test"

    def test_marker_matches_inside_a_longer_name(self) -> None:
        """The rule is substring-based, so a marker anywhere classifies."""
        assert project_kind_for_name("my-latest-film") == "test"


class TestNormalizeProjectKind:
    @pytest.mark.parametrize("kind", ["production", "test"])
    def test_valid_kinds_pass_through(self, kind: str) -> None:
        assert normalize_project_kind(kind) in VALID_PROJECT_KINDS

    def test_case_and_whitespace_are_canonicalized(self) -> None:
        assert normalize_project_kind("  PRODUCTION  ") == "production"

    def test_unknown_kind_raises_actionable_error(self) -> None:
        with pytest.raises(BackendOperationError, match=r"production.*test"):
            normalize_project_kind("staging")

    def test_error_reports_the_rejected_value(self) -> None:
        with pytest.raises(BackendOperationError, match="staging"):
            normalize_project_kind("staging")


class TestProjectKindForState:
    def test_declared_kind_wins_over_the_name(self) -> None:
        assert project_kind_for_state({"project_kind": "production"}, "test-thing") == "production"

    def test_falls_back_to_the_folder_name(self) -> None:
        assert project_kind_for_state({}, "my-film") == "production"
        assert project_kind_for_state({}, "test-thing") == "test"

    def test_blank_declared_kind_falls_back(self) -> None:
        assert project_kind_for_state({"project_kind": "   "}, "test-thing") == "test"

    def test_invalid_declared_kind_raises(self) -> None:
        with pytest.raises(BackendOperationError):
            project_kind_for_state({"project_kind": "bogus"}, "my-film")


class TestProjectTitleFromId:
    @pytest.mark.parametrize(
        ("project_id", "expected"),
        [
            ("my-film", "My Film"),
            ("my_film", "My Film"),
            ("the-third-interval", "The Third Interval"),
            ("solo", "Solo"),
        ],
    )
    def test_separators_become_spaced_title_case(self, project_id: str, expected: str) -> None:
        assert project_title_from_id(project_id) == expected


def test_discovery_module_reexports_the_owner() -> None:
    """The operator discovery module must not carry its own copies."""
    from film_pipeline.projects import discovery

    assert discovery.project_kind_for_name is project_kind_for_name
    assert discovery.normalize_project_kind is normalize_project_kind
    assert discovery.project_kind_for_state is project_kind_for_state
    assert discovery.project_title_from_id is project_title_from_id
