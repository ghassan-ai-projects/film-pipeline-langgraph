"""Tests for storage root resolution and marker gating."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from film_pipeline.storage.paths import phase_dir, project_dir
from film_pipeline.storage.storage import (
    LAYOUT_VERSION,
    MARKER_FILENAME,
    STORAGE_ROOT_ENV,
    StorageRootError,
    default_checkpoints_root,
    default_run_root,
    default_runtime_root,
    default_storage_root,
    ensure_storage_root,
    init_storage_root,
    read_marker,
    resolve_storage_root,
)


class TestResolveStorageRoot:
    def test_explicit_argument_wins(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(STORAGE_ROOT_ENV, str(tmp_path / "from-env"))
        assert resolve_storage_root(tmp_path / "explicit") == tmp_path / "explicit"

    def test_env_variable_is_honored(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(STORAGE_ROOT_ENV, str(tmp_path / "env-root"))
        assert resolve_storage_root() == tmp_path / "env-root"

    def test_unmarked_legacy_tree_is_refused(self, tmp_path: Path) -> None:
        """Pre-upgrade project trees are refused, not adopted."""
        from film_pipeline.storage.storage import ensure_storage_root

        root = tmp_path / "legacy"
        project = root / "01-vision" / "film_constitution"
        project.mkdir(parents=True)
        (project / "current.meta.json").write_text("{}\n")
        with pytest.raises(StorageRootError):
            ensure_storage_root(root)

    def test_blank_env_falls_through(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(STORAGE_ROOT_ENV, "   ")
        assert resolve_storage_root() == default_storage_root()

    def test_default_is_under_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(STORAGE_ROOT_ENV, raising=False)
        assert resolve_storage_root() == Path.home() / ".film-pipeline" / "projects"

    def test_derived_defaults_cohere(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Runtime root IS the storage root so a project is one folder (§1/D3).

        Checkpoints and runs stay outside the per-project tree, under the same
        root, because they are machine-global rather than per-project.
        """
        root = tmp_path / "base" / "projects"
        monkeypatch.setenv(STORAGE_ROOT_ENV, str(root))
        assert default_runtime_root() == root
        assert default_checkpoints_root() == root / "checkpoints"
        assert default_run_root() == root / "runs" / "default"

    def test_runtime_and_artifact_roots_coincide(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A project's record, state, audit, and artifacts share one directory.

        This is the §1 end-goal guard: if the runtime tree and the artifact tree
        ever drift apart again, a human can no longer read a project folder as a
        single document set.
        """
        from film_pipeline.studio.runtime import StudioRuntime

        monkeypatch.setenv(STORAGE_ROOT_ENV, str(tmp_path / "store"))
        rt = StudioRuntime(server_mode="mock")
        rt.create_project("p1")
        assert rt.services is not None
        assert rt.project_roots["p1"] == rt.services.artifact_store.root / "p1"


class TestMarker:
    def test_init_writes_readable_marker(self, tmp_path: Path) -> None:
        root = init_storage_root(tmp_path / "store")
        marker = read_marker(root)
        assert marker is not None
        assert marker.layout_version == LAYOUT_VERSION
        assert marker.profile == "production"
        raw = json.loads((root / MARKER_FILENAME).read_text())
        assert raw["layout_version"] == LAYOUT_VERSION
        assert raw["profile"] == "production"
        assert read_marker(root) == marker

    def test_ensure_initializes_missing_root(self, tmp_path: Path) -> None:
        root = tmp_path / "fresh"
        assert ensure_storage_root(root) == root
        assert read_marker(root) is not None

    def test_ensure_accepts_marked_root(self, tmp_path: Path) -> None:
        root = init_storage_root(tmp_path / "marked")
        assert ensure_storage_root(root) == root

    def test_ensure_refuses_newer_layout(self, tmp_path: Path) -> None:
        root = tmp_path / "from-future"
        root.mkdir()
        (root / MARKER_FILENAME).write_text(
            json.dumps(
                {
                    "layout_version": LAYOUT_VERSION + 5,
                    "schema_version": 1,
                    "profile": "production",
                    "created_at": "2026-01-01T00:00:00Z",
                }
            )
        )
        with pytest.raises(StorageRootError, match="newer layout"):
            ensure_storage_root(root)

    def test_ensure_refuses_unmarked_foreign_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "junk"
        root.mkdir()
        (root / "random.txt").write_text("not a film-pipeline store\n")
        with pytest.raises(StorageRootError, match=r"without a storage\.json marker"):
            ensure_storage_root(root)

    def test_ensure_refuses_corrupt_marker(self, tmp_path: Path) -> None:
        root = tmp_path / "corrupt-marker"
        root.mkdir()
        (root / MARKER_FILENAME).write_text("{not valid json")
        with pytest.raises(StorageRootError, match="corrupt"):
            ensure_storage_root(root)

    def test_ensure_refuses_file(self, tmp_path: Path) -> None:
        hostage = tmp_path / "a-file"
        hostage.write_text("data\n")
        with pytest.raises(StorageRootError, match="not a directory"):
            ensure_storage_root(hostage)


class TestRequiredRoots:
    def test_store_requires_root(self) -> None:
        from film_pipeline.storage.store import ArtifactStore

        with pytest.raises(TypeError):
            ArtifactStore()  # type: ignore[call-arg]

    def test_paths_require_root(self) -> None:
        with pytest.raises(TypeError):
            project_dir("slug")  # type: ignore[call-arg]
        with pytest.raises(TypeError):
            phase_dir("slug", "script")  # type: ignore[call-arg]

    def test_store_exposes_root(self, store_root: Path) -> None:
        from film_pipeline.storage.store import ArtifactStore

        assert ArtifactStore(root=store_root).root == store_root


class TestSandboxHelper:
    def test_sandbox_store_root_marks_profile(self, tmp_path: Path) -> None:
        from film_pipeline.devharness.storage import sandbox_store_root

        root = sandbox_store_root(tmp_path / "sandbox")
        marker = read_marker(root)
        assert marker is not None
        assert marker.profile == "sandbox"
