"""Root test configuration — keeps production data safe from test runs.

Storage roots are separated from production by construction (see
``film_pipeline.storage.storage``): every test runs with
``FILM_PIPELINE_STORAGE_ROOT`` pointed at a per-test temp directory, and a
session guard asserts the run leaves the user's real roots untouched.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast

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
    from film_pipeline.devharness.in_memory_git import reset_in_memory_git
    from film_pipeline.studio.runtime import reset_runtime

    # Each test starts with an empty in-memory checkpoint history (see the
    # ``_fast_checkpoint_backend`` session fixture for why real git is bypassed).
    reset_in_memory_git()
    reset_runtime()

    # Defensively rebind the tool->runtime function to the genuine one: a
    # stale MagicMock must never survive into the next test regardless of
    # how it got there.
    import film_pipeline.mcp.tools as tools_pkg

    tools_pkg.get_runtime = reset_runtime.__globals__["get_runtime"]


@pytest.fixture
def store_root(tmp_path: Path) -> Path:
    """A marked sandbox storage root for direct store construction."""
    from film_pipeline.devharness.storage import sandbox_store_root

    return sandbox_store_root(tmp_path / "storage-root")


@pytest.fixture(scope="session", autouse=True)
def _fast_checkpoint_backend() -> Iterator[None]:
    """Back runtime checkpoints with an in-process git double for the whole suite.

    Real git shells out ~9 subprocesses per project and writes a ``.git`` tree
    that teardown must delete — pure overhead for the ~50 modules that create
    projects without asserting git semantics. The genuine ``GitBackend``
    contract tests construct ``GitBackend`` directly and are unaffected.
    """
    from film_pipeline.devharness.in_memory_git import InMemoryGitBackend
    from film_pipeline.storage.project_storage import (
        get_git_backend_type,
        set_git_backend_type,
    )

    previous = get_git_backend_type()
    set_git_backend_type(InMemoryGitBackend)
    try:
        yield
    finally:
        if previous is not None:
            set_git_backend_type(previous)


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


@pytest.fixture
def call_tool() -> Iterator[Callable[..., Any]]:
    """Call a tool handler the way dispatch does, without the global singleton.

    Doc 01's slice 2 replaces "handler fetches its own runtime via
    ``tools_pkg.get_runtime()``" with "dispatch passes a `ToolContext`". This
    fixture builds that context from a real `StudioRuntime` the test owns, so a
    migrated handler is exercised through its real calling convention rather than
    by patching a package global. The 61 monkeypatch sites this replaces were the
    symptom: every test had to know *how* the handler looked its runtime up.

    The context is rebuilt per call, so a handler that mutates runtime state is
    observed on the same runtime the assertions read.
    """

    def _call(
        handler: Callable[..., Any],
        args: dict[str, Any] | None = None,
        *,
        project_id: str | None = None,
        runtime: Any = None,
    ) -> Any:
        import film_pipeline.mcp.tools as tools_pkg
        from film_pipeline.mcp.envelope import new_envelope
        from film_pipeline.mcp.tools.context import ToolContext

        # `runtime=` is for a test that built its own runtime and wants the
        # handler to see it. Otherwise honour whichever runtime the test made
        # visible by patching `film_pipeline.mcp.tools.get_runtime` — which is
        # the accessor dispatch itself reads, so a test that patched nothing gets
        # the process runtime, exactly as production would.
        rt = runtime if runtime is not None else tools_pkg.get_runtime()

        envelope = new_envelope(project_ref=project_id)
        # A tool that needs a project gets the runtime's active project, which is
        # what dispatch's resolution step produces.
        resolved = project_id if project_id is not None else _active_project_id(rt)
        context = ToolContext(runtime=rt, project_id=resolved, envelope=envelope)
        # Both handler shapes are legal while doc 01's migration is in flight;
        # the same signature check dispatch uses picks which call this is. A
        # legacy handler still gets `"_envelope"`, exactly as dispatch passes it.
        from film_pipeline.mcp.server import _accepts_context

        any_handler = cast("Any", handler)
        if _accepts_context(handler):
            result = any_handler(context, args or {})
        else:
            result = any_handler({**(args or {}), "_envelope": envelope})
        if inspect.isawaitable(result):
            awaited: Any = asyncio.run(cast("Any", result))
            return awaited
        return result

    yield _call


def _active_project_id(runtime: Any) -> str | None:
    """The runtime's active project id, matching dispatch's resolution step."""
    active = runtime.get_active()
    if active is None:
        return None
    return str(active.get("project_id", "")) or None
