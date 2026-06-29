"""Root test configuration — keeps the real projects/ folder clear."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _redirect_default_projects_root(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[None]:
    """Redirect the default artifact store root and clean up after the session.

    Most tests rely on the default ``projects/`` directory. Redirecting the
    default ``ArtifactStore`` root to a session-scoped temp directory keeps
    the workspace folder clear for the in-process tests that pick up the
    monkeypatch. After the session any directories created in the real
    ``projects/`` folder (e.g. by MCP server subprocess tests that cannot be
    redirected) are removed.

    Tests that explicitly pass a custom ``root`` to ``ArtifactStore`` are
    not affected.
    """
    from film_pipeline.artifacts.store import ArtifactStore

    default_root = Path("projects")
    existing_dirs = _project_dir_names(default_root)
    session_root = tmp_path_factory.mktemp("projects")
    original_init = ArtifactStore.__init__

    def _init_with_redirect(self: ArtifactStore, root: Path = default_root) -> None:
        if root == default_root:
            root = session_root
        original_init(self, root)

    ArtifactStore.__init__ = _init_with_redirect  # type: ignore[method-assign]
    try:
        yield
    finally:
        ArtifactStore.__init__ = original_init  # type: ignore[method-assign]
        _cleanup_new_project_dirs(default_root, existing_dirs)


def _cleanup_new_project_dirs(projects_root: Path, existing_dirs: set[str]) -> None:
    if not projects_root.exists():
        return
    for project_dir in projects_root.iterdir():
        if project_dir.is_dir() and project_dir.name not in existing_dirs:
            shutil.rmtree(project_dir, ignore_errors=True)


def _project_dir_names(projects_root: Path) -> set[str]:
    if not projects_root.exists():
        return set()
    return {p.name for p in projects_root.iterdir() if p.is_dir()}
