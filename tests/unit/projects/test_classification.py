"""Project classification policy has one owner.

Folder-name classification decides whether a project is real production work or
throwaway test scaffolding, and the title rule decides what a human sees in the
project list. Both were private helpers inside the operator service's discovery
module; they are now owned by `film_pipeline.projects.classification` so every
surface shares one definition.
"""

from __future__ import annotations

import pytest

from film_pipeline.projects.classification import (
    VALID_PROJECT_KINDS,
    InvalidProjectKindError,
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
        with pytest.raises(InvalidProjectKindError, match=r"production.*test"):
            normalize_project_kind("staging")

    def test_error_reports_the_rejected_value(self) -> None:
        with pytest.raises(InvalidProjectKindError, match="staging"):
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
        with pytest.raises(InvalidProjectKindError):
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


def test_discovery_lives_in_the_operator_layer() -> None:
    """Discovery is operator-surface code, not a `projects` concern.

    `projects` sits at L4 and may import only `filmspec`, `schemas`, and
    `storage`. Discovery takes an `OperatorService` and produces operator view
    models, so it belongs to `operations`; keeping it in `projects` created an
    `operations <-> projects` import cycle.
    """
    from film_pipeline.operations import project_discovery

    assert callable(project_discovery.discover_project_folders)
    assert callable(project_discovery.load_discovered_project)
    assert not hasattr(project_discovery, "normalize_project_kind")


def test_projects_package_imports_no_higher_layer() -> None:
    """No module under `projects` may import `operations` or `studio`."""
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[3] / "src" / "film_pipeline" / "projects"
    forbidden = ("film_pipeline.operations", "film_pipeline.studio")
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                targets = [node.module or ""]
            offenders.extend(f"{path.name}: {t}" for t in targets if t.startswith(forbidden))
    assert offenders == [], f"projects imports a higher layer: {offenders}"
