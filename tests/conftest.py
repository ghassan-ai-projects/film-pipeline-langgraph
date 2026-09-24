"""Root test configuration — keeps production data safe from test runs.

Storage roots are separated from production by construction (see
``film_pipeline.artifacts.storage``): every test runs with
``FILM_PIPELINE_STORAGE_ROOT`` pointed at a per-test temp directory, and a
session guard asserts the run leaves the user's real roots untouched.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_runtime_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Give every test its own persistent runtime and storage roots.

    ``StudioRuntime`` restores persisted project state from its runtime root
    at construction; without per-test isolation, projects created by one
    test would reappear in the next. The global runtime singleton is also
    reset so tests that exercise MCP tools share no in-memory state.
    """
    monkeypatch.setenv("FILM_PIPELINE_RUNTIME_ROOT", str(tmp_path / "runtime-root"))
    monkeypatch.setenv("FILM_PIPELINE_STORAGE_ROOT", str(tmp_path / "storage-root"))
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


@pytest.fixture
def store_root(tmp_path: Path) -> Path:
    """A marked sandbox storage root for direct store construction."""
    from film_pipeline.testing.storage import sandbox_store_root

    return sandbox_store_root(tmp_path / "storage-root")


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
    import os

    os.environ["FILM_PIPELINE_NO_PERSIST"] = "1"
    session_root = tmp_path_factory.mktemp("film-pipeline")
    # The canonical storage variable carries the session; the deprecated
    # FILM_PIPELINE_PERSIST_ROOT alias is exercised only by its own test.
    os.environ["FILM_PIPELINE_STORAGE_ROOT"] = str(session_root / "storage")

    try:
        yield
    finally:
        import shutil

        if session_root.exists():
            shutil.rmtree(session_root, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def _production_roots_untouched() -> Iterator[None]:
    """Fail the suite if any test wrote into a real production storage root.

    Snapshots file path sets and sizes (not mtimes) for the user's
    ``~/.film-pipeline`` tree and the repo's legacy ``projects/`` /
    ``.film-pipeline-run`` directories, and asserts nothing was added,
    removed, or resized. Log files are ignored: a live server on this machine
    may legitimately append to its own logs while tests run.
    """
    watched = {
        "home-film-pipeline": Path.home() / ".film-pipeline",
        "cwd-projects": Path("projects").resolve(),
        "cwd-film-pipeline-run": Path(".film-pipeline-run").resolve(),
    }
    before = {name: _snapshot_tree(path) for name, path in watched.items()}
    yield
    failures = []
    for name, path in watched.items():
        before_tree = before.get(name)
        after_tree = _snapshot_tree(path)
        if after_tree == before_tree:
            continue
        old = before_tree or {}
        new = after_tree or {}
        added = sorted(set(new) - set(old))[:10]
        removed = sorted(set(old) - set(new))[:10]
        resized = sorted(key for key in set(old) & set(new) if old[key] != new[key])[:10]
        failures.append(f"{name} ({path}): added={added} removed={removed} resized={resized}")
    assert not failures, "Test run touched production storage roots:\n" + "\n".join(failures)


def _snapshot_tree(root: Path) -> dict[str, int] | None:
    """Snapshot ``relative path -> size`` for files and dirs under ``root``.

    Directories are recorded with size 0 so pure directory creation (writing
    nothing) is still caught. Unreadable subtrees are skipped rather than
    failing the snapshot itself; the comparison covers everything readable.
    """
    if not root.exists():
        return None
    snapshot: dict[str, int] = {}
    try:
        paths = sorted(root.rglob("*"))
    except OSError:
        return snapshot
    for path in paths:
        relative = path.relative_to(root).as_posix()
        parts = relative.split("/")
        if "logs" in parts or relative.endswith(".log"):
            continue
        try:
            snapshot[relative] = path.stat().st_size if path.is_file() else 0
        except OSError:
            continue
    return snapshot
