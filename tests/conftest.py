"""Root test configuration — keeps production data safe from test runs."""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_runtime_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Give every test its own persistent runtime root.

    ``StudioRuntime`` restores persisted project state from its runtime root
    at construction; without per-test isolation, projects created by one
    test would reappear in the next. The global runtime singleton is also
    reset so tests that exercise MCP tools share no in-memory state.
    """
    monkeypatch.setenv("FILM_PIPELINE_RUNTIME_ROOT", str(tmp_path / "runtime-root"))
    monkeypatch.delenv("FILM_PIPELINE_PERSIST_STATE", raising=False)
    # Production code writes FILM_PIPELINE_MCP_MODE directly (operator backend
    # mode switch). Without this, a leaking test leaves
    # the mode in the worker's os.environ and every later get_runtime() on the
    # same xdist worker recreates the singleton in the leaked mode — tests then
    # fail order-dependently ("No active project", mock/real mismatches).
    monkeypatch.delenv("FILM_PIPELINE_MCP_MODE", raising=False)
    from film_pipeline.app.runtime import reset_runtime
    from film_pipeline.testing.in_memory_git import reset_in_memory_git

    # Each test starts with an empty in-memory checkpoint history (see the
    # ``_fast_checkpoint_backend`` session fixture for why real git is bypassed).
    reset_in_memory_git()
    reset_runtime()


@pytest.fixture(scope="session", autouse=True)
def _fast_checkpoint_backend() -> Iterator[None]:
    """Back runtime checkpoints with an in-process git double for the whole suite.

    Real git shells out ~9 subprocesses per project and writes a ``.git`` tree
    that teardown must delete — pure overhead for the ~50 modules that create
    projects without asserting git semantics. The genuine ``GitBackend``
    contract tests construct ``GitBackend`` directly and are unaffected.
    """
    from film_pipeline.app._persistence import reset_git_backend_type, set_git_backend_type
    from film_pipeline.testing.in_memory_git import InMemoryGitBackend

    set_git_backend_type(InMemoryGitBackend)
    try:
        yield
    finally:
        reset_git_backend_type()


@pytest.fixture(scope="session", autouse=True)
def _clean_production_state_stores(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[None]:
    """Keep tests isolated from production runtime/checkpoint/artifact stores.

    Tests never write to the user's real ``~/.film-pipeline`` directory or to
    the legacy ``projects/`` / ``.film-pipeline-run`` folders.  The session is
    pointed at a temp directory and only that directory is cleaned.
    """
    os.environ["FILM_PIPELINE_NO_PERSIST"] = "1"
    persist_root = tmp_path_factory.mktemp("film-pipeline")
    os.environ["FILM_PIPELINE_PERSIST_ROOT"] = str(persist_root)

    home_root = Path.home() / ".film-pipeline"
    cwd_root = Path(".film-pipeline-run").resolve()
    for path in (persist_root, home_root, cwd_root):
        assert not _is_under(path, home_root) or path == home_root, (
            f"Session persist root {path} would overlap the production root"
        )

    try:
        yield
    finally:
        if persist_root.exists():
            shutil.rmtree(persist_root, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def _redirect_default_projects_root(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[None]:
    """Redirect the default artifact store root to a temp directory.

    In addition, the production code now defaults artifact storage to the
    configured persistence root, which is already redirected to a temp dir by
    ``_clean_production_state_stores``.  This monkeypatch catches any code
    paths that still instantiate ``ArtifactStore(root=Path(\"projects\"))``.
    """
    from film_pipeline.artifacts.store import ArtifactStore

    default_root = Path("projects")
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


def _is_under(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve()
        resolved_root = root.resolve()
    except OSError:
        return False
    return resolved == resolved_root or resolved_root in resolved.parents
