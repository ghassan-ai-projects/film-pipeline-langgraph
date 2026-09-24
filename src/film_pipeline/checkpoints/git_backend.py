"""Git backend — commit, tag, restore for checkpoint operations.

Operations run in the project's git repository. For testing, an isolated
temp directory with its own git init is used.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GitBackend:
    """Thin wrapper around git for checkpoint operations."""

    repo_path: Path

    def _spawn_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run git in the repo and return the raw result, unchecked."""
        return subprocess.run(
            ["git", "-C", str(self.repo_path), *args],
            capture_output=True,
            text=True,
        )

    def _run(self, *args: str) -> str:
        result = self._spawn_git(*args)
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def _run_ok(self, *args: str) -> bool:
        return self._spawn_git(*args).returncode == 0

    def commit(self, message: str, files: list[str] | None = None) -> str:
        """Stage and commit. Returns the commit hash."""
        if files:
            self._run("add", "--", *files)
        else:
            self._run("add", "-A")
        self._run("commit", "-m", message, "--allow-empty")
        return self._run("rev-parse", "HEAD")

    def tag(self, name: str, message: str) -> None:
        """Create an annotated tag."""
        self._run("tag", "-a", name, "-m", message)

    def branch(self, name: str, base: str | None = None) -> None:
        """Create a branch."""
        args = ["branch", name]
        if base:
            args.append(base)
        self._run(*args)

    def restore_files(self, commit: str, files: list[str]) -> None:
        """Restore specific files from a commit."""
        self._run("checkout", commit, "--", *files)

    def list_files(self, commit: str) -> list[str]:
        """Return every tracked file path at a commit (unquoted, NUL-delimited)."""
        output = self._run("ls-tree", "-z", "-r", "--name-only", commit)
        return [entry for entry in output.split("\x00") if entry]

    def log(self, max_count: int = 20) -> list[str]:
        """Return recent commit hashes."""
        output = self._run("log", f"--max-count={max_count}", "--format=%H")
        return [h for h in output.split("\n") if h]

    def current_branch(self) -> str:
        return self._run("branch", "--show-current")

    def is_clean(self) -> bool:
        return self._run_ok("diff", "--quiet")

    @classmethod
    def init_temp(cls, path: Path) -> GitBackend:
        """Initialize a temp git repo for testing."""
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-C", str(path), "init", "-b", "main"], capture_output=True)
        subprocess.run(
            ["git", "-C", str(path), "config", "user.email", "test@test"],
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(path), "config", "user.name", "Test"],
            capture_output=True,
        )
        return cls(repo_path=path)
