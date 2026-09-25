"""CI guards: the storage rules are enforced by tests, not by discipline.

These tests fail the suite when library code re-acquires an implicit storage
default or when runtime startup silently adopts legacy roots.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest

from film_pipeline.storage.storage import STORAGE_ROOT_ENV, resolve_storage_root

SRC_ROOT = Path(__file__).parents[3] / "src" / "film_pipeline"
_STORAGE_MODULE = SRC_ROOT / "storage" / "storage.py"


def _python_sources() -> list[Path]:
    return sorted(SRC_ROOT.rglob("*.py"))


class TestNoImplicitRootDefaults:
    def test_no_cwd_relative_projects_default_outside_storage_module(self) -> None:
        pattern = re.compile(r"Path\([\"']projects[\"']\)")
        offenders = [
            path
            for path in _python_sources()
            if path != _STORAGE_MODULE and pattern.search(path.read_text())
        ]
        assert offenders == [], (
            "CWD-relative storage default re-introduced outside the storage "
            f"module: {[str(p.relative_to(SRC_ROOT)) for p in offenders]}"
        )

    def test_no_path_home_outside_storage_module(self) -> None:
        offenders = [
            path
            for path in _python_sources()
            if path != _STORAGE_MODULE and "Path.home()" in path.read_text()
        ]
        assert offenders == [], (
            "Path.home() default re-introduced outside the storage module: "
            f"{[str(p.relative_to(SRC_ROOT)) for p in offenders]}"
        )


class TestNoSilentAdoption:
    def test_runtime_ignores_legacy_cwd_projects(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A legacy ``projects/`` tree in the CWD is never adopted at startup."""
        legacy = tmp_path / "projects" / "legacy-a" / "intake" / "idea"
        legacy.mkdir(parents=True)
        (legacy / "current.meta.json").write_text("{}\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv(STORAGE_ROOT_ENV, str(tmp_path / "real-storage"))
        monkeypatch.delenv("FILM_PIPELINE_RUNTIME_ROOT", raising=False)
        monkeypatch.delenv("FILM_PIPELINE_PERSIST_STATE", raising=False)

        from film_pipeline.studio.runtime import StudioRuntime

        runtime = StudioRuntime()

        assert runtime.projects == {}
        assert resolve_storage_root() == tmp_path / "real-storage"
        # Non-persistent invocation: the runtime lives in the system temp tree,
        # never in the user's home or the (legacy-populated) CWD.
        assert runtime.runtime_root is not None
        assert runtime.runtime_root.is_relative_to(tempfile.gettempdir())
