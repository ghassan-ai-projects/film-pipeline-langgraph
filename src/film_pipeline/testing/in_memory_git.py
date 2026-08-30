"""In-memory git backend — a fast, subprocess-free stand-in for tests.

The real :class:`~film_pipeline.checkpoints.git_backend.GitBackend` shells out
to ``git`` for every commit/tag/branch and materializes a ``.git`` directory
full of objects. In the test suite this dominates runtime: creating a single
project spawns ~9 ``git`` subprocesses and writes dozens of files that teardown
must then delete. Multiplied across the ~50 test modules that create projects,
it added minutes of pure overhead without exercising any git semantics those
tests care about.

:class:`InMemoryGitBackend` mirrors the observable behaviour the checkpoint and
rollback managers depend on — commit hashes, working-tree snapshots, file
restore, tags, branches — using an in-process store keyed by repo path. State
survives runtime reloads within the same process (matching how a real ``.git``
survives), so rollback and resume tests stay meaningful while running in
microseconds instead of seconds.

The genuine ``GitBackend`` contract tests (``tests/unit/checkpoints``) still use
real git; this double is injected only through the runtime's
``project_git_backend`` seam.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from film_pipeline.checkpoints.git_backend import GitBackend


@dataclass
class _Commit:
    hash: str
    message: str
    # Full working-tree snapshot at commit time: relative path -> file bytes.
    tree: dict[str, bytes]


@dataclass
class _RepoState:
    commits: list[_Commit] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)
    branches: set[str] = field(default_factory=lambda: {"main"})
    current_branch: str = "main"
    _counter: int = 0


# Process-global store keyed by resolved repo path. Persisting here (rather than
# on the instance) means a fresh backend created during a runtime reload sees the
# same history a real ``.git`` directory would have retained on disk.
_REPOS: dict[Path, _RepoState] = {}


def reset_in_memory_git() -> None:
    """Drop all in-memory repo state (call between tests for isolation)."""
    _REPOS.clear()


class InMemoryGitBackend(GitBackend):
    """Subprocess-free ``GitBackend`` used by the test runtime."""

    # --- construction -------------------------------------------------------

    @classmethod
    def init_temp(cls, path: Path) -> InMemoryGitBackend:
        path.mkdir(parents=True, exist_ok=True)
        backend = cls(repo_path=path)
        _REPOS.setdefault(backend._key, _RepoState())
        return backend

    @property
    def _key(self) -> Path:
        return self.repo_path.resolve()

    @property
    def _state(self) -> _RepoState:
        return _REPOS.setdefault(self._key, _RepoState())

    # --- working-tree helpers ----------------------------------------------

    def _snapshot_tree(self) -> dict[str, bytes]:
        """Read every tracked file currently on disk under the repo root."""
        tree: dict[str, bytes] = {}
        for file in self.repo_path.rglob("*"):
            if file.is_dir() or self._is_ignored(file):
                continue
            tree[file.relative_to(self.repo_path).as_posix()] = file.read_bytes()
        return tree

    @staticmethod
    def _is_ignored(file: Path) -> bool:
        return ".git" in file.parts

    def _latest_tree(self) -> dict[str, bytes]:
        commits = self._state.commits
        return dict(commits[-1].tree) if commits else {}

    def _write_tree(self, tree: dict[str, bytes], only: list[str] | None = None) -> None:
        selected = tree if only is None else {p: tree[p] for p in only if p in tree}
        for rel, data in selected.items():
            target = self.repo_path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    def _find_commit(self, ref: str) -> _Commit | None:
        for commit in reversed(self._state.commits):
            if commit.hash == ref or commit.hash.startswith(ref):
                return commit
        return None

    # --- GitBackend API -----------------------------------------------------

    def commit(self, message: str, files: list[str] | None = None) -> str:
        state = self._state
        tree = self._latest_tree()
        current = self._snapshot_tree()
        if files:
            # ``git add -- <files>``: stage only the named paths over the prior tree.
            for rel in files:
                if rel in current:
                    tree[rel] = current[rel]
                else:
                    tree.pop(rel, None)
        else:
            # ``git add -A``: the working tree becomes the new snapshot.
            tree = current
        state._counter += 1
        parent = state.commits[-1].hash if state.commits else ""
        digest = hashlib.sha1(
            f"{parent}:{state._counter}:{message}".encode(), usedforsecurity=False
        ).hexdigest()
        state.commits.append(_Commit(hash=digest, message=message, tree=tree))
        return digest

    def tag(self, name: str, message: str) -> None:  # noqa: ARG002 — mirror GitBackend.tag
        state = self._state
        if not state.commits:
            raise RuntimeError("git tag failed: no commits yet")
        state.tags[name] = state.commits[-1].hash

    def branch(self, name: str, base: str | None = None) -> None:  # noqa: ARG002 — mirror signature
        self._state.branches.add(name)

    def restore_files(self, commit: str, files: list[str]) -> None:
        target = self._find_commit(commit)
        if target is None:
            raise RuntimeError(f"git checkout {commit} failed: unknown commit")
        if files == ["."]:
            self._write_tree(target.tree)
        else:
            self._write_tree(target.tree, only=files)

    def log(self, max_count: int = 20) -> list[str]:
        hashes = [c.hash for c in reversed(self._state.commits)]
        return hashes[:max_count]

    def current_branch(self) -> str:
        return self._state.current_branch

    def is_clean(self) -> bool:
        return self._snapshot_tree() == self._latest_tree()
