"""Tests for production-data safety guards."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.app.safety import (
    ProductionDataError,
    can_delete_project,
    is_safe_to_delete,
    move_to_trash,
    persist_root,
    require_safe_to_delete,
    safe_rmtree,
)


def test_persist_root_defaults_to_home_dot_film_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FILM_PIPELINE_PERSIST_ROOT", raising=False)
    monkeypatch.delenv("FILM_PIPELINE_STORAGE_ROOT", raising=False)
    assert persist_root() == Path.home() / ".film-pipeline"


def test_persist_root_derives_from_storage_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FILM_PIPELINE_STORAGE_ROOT", "/tmp/film-pipeline-test/projects")
    expected = Path("/tmp/film-pipeline-test/projects").resolve().parent
    assert persist_root() == expected


def test_temp_path_is_safe_to_delete(tmp_path: Path) -> None:
    subdir = tmp_path / "delete-me"
    subdir.mkdir()
    assert is_safe_to_delete(subdir) is True


def test_persist_root_path_is_safe_to_delete(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("FILM_PIPELINE_STORAGE_ROOT", str(tmp_path / "projects"))
    subdir = tmp_path / "runs" / "default"
    subdir.mkdir(parents=True)
    assert is_safe_to_delete(subdir) is True


def test_home_directory_is_not_safe_to_delete() -> None:
    assert is_safe_to_delete(Path.home()) is False


def test_marker_file_makes_path_safe(tmp_path: Path) -> None:
    subdir = tmp_path / "marked"
    subdir.mkdir()
    (subdir / ".film-pipeline-allow-delete").touch()
    assert is_safe_to_delete(subdir) is True


def test_require_safe_to_delete_raises_for_unsafe_path() -> None:
    unsafe = Path.cwd()
    with pytest.raises(ProductionDataError):
        require_safe_to_delete(unsafe)


def test_require_safe_to_delete_message_offers_working_remedies() -> None:
    with pytest.raises(ProductionDataError) as excinfo:
        require_safe_to_delete(Path.cwd())
    message = str(excinfo.value)
    assert "FILM_PIPELINE_STORAGE_ROOT" in message
    assert ".film-pipeline-allow-delete" in message


def test_require_safe_to_delete_message_does_not_advertise_allow_delete_env() -> None:
    """R-102: the guard must not recommend an override it does not honor."""
    with pytest.raises(ProductionDataError) as excinfo:
        require_safe_to_delete(Path.cwd())
    assert "FILM_PIPELINE_ALLOW_DELETE" not in str(excinfo.value)


def test_allow_delete_env_var_does_not_override_path_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FILM_PIPELINE_ALLOW_DELETE=1 gates project-level deletes only.

    The physical path guards ignore it, so an ambient leftover export can
    never disable deletion protection for arbitrary locations.
    """
    monkeypatch.setenv("FILM_PIPELINE_ALLOW_DELETE", "1")
    assert is_safe_to_delete(Path.cwd()) is False
    with pytest.raises(ProductionDataError):
        safe_rmtree(Path.cwd())


def test_safe_rmtree_refuses_unsafe_path() -> None:
    with pytest.raises(ProductionDataError):
        safe_rmtree(Path.cwd())


def test_safe_rmtree_deletes_safe_path(tmp_path: Path) -> None:
    subdir = tmp_path / "to-delete"
    subdir.mkdir()
    (subdir / "file.txt").touch()
    safe_rmtree(subdir)
    assert not subdir.exists()


def test_move_to_trash_archives_under_persist_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("FILM_PIPELINE_PERSIST_ROOT", str(tmp_path))
    source = tmp_path / "runs" / "project-1"
    source.mkdir(parents=True)
    (source / "state.json").touch()

    trashed = move_to_trash(source, prefix="test-")

    assert not source.exists()
    assert trashed.exists()
    assert (trashed / "state.json").exists()
    assert "trash" in str(trashed)


def test_can_delete_project_allows_test_projects() -> None:
    assert can_delete_project({"project_kind": "test"}) is True


def test_can_delete_project_allows_unknown_kind() -> None:
    assert can_delete_project({"project_kind": ""}) is True


def test_can_delete_project_blocks_production_by_default() -> None:
    assert can_delete_project({"project_kind": "production"}) is False


def test_can_delete_project_allows_production_with_force() -> None:
    assert can_delete_project({"project_kind": "production"}, force=True) is True


def test_can_delete_project_allows_production_with_env_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FILM_PIPELINE_ALLOW_DELETE", "1")
    assert can_delete_project({"project_kind": "production"}) is True
