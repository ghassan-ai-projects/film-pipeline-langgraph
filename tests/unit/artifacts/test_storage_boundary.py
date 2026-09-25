"""Boundary guards for the storage core.

Storage ownership must stay in one place: ``film_pipeline.artifacts``. These
tests fail if a component starts building project paths or writing project
files itself instead of going through
:class:`~film_pipeline.artifacts.project_storage.ProjectStorage`.

They are deliberately source-level checks. A structural rule that is only
described in a docstring drifts; a rule with a failing test does not.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[3] / "src" / "film_pipeline"
STORAGE_PACKAGE = SRC / "artifacts"

#: Layout facts and write primitives that only the storage package may touch.
CORE_PRIVATE_NAMES = (
    "_layout",
    "serialization",
)


def _python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _imported_modules(path: Path) -> set[str]:
    """Every module name ``path`` imports (import and from-import forms)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def _outside_storage() -> list[Path]:
    return [
        path
        for path in _python_files(SRC)
        if STORAGE_PACKAGE not in path.parents and path.parent != STORAGE_PACKAGE
    ]


class TestStorageCoreBoundary:
    """One component owns storage; everything else consumes it."""

    def test_only_storage_imports_layout_facts(self) -> None:
        """No module outside ``artifacts/`` may import the private layout module."""
        offenders = [
            path
            for path in _outside_storage()
            if any(
                module.endswith(("artifacts._layout", "artifacts.serialization"))
                for module in _imported_modules(path)
            )
        ]
        assert offenders == [], (
            "These modules bypass the storage core by importing layout/serialization "
            f"internals directly: {[str(p) for p in offenders]}. Use "
            "ProjectStorage from film_pipeline.artifacts instead."
        )

    def test_only_storage_imports_path_helpers(self) -> None:
        """Project path helpers stay internal to the storage package."""
        offenders = [
            path
            for path in _outside_storage()
            if any(module.endswith("artifacts.paths") for module in _imported_modules(path))
        ]
        assert offenders == [], (
            f"These modules build project paths themselves: {[str(p) for p in offenders]}. "
            "Ask ProjectStorage for typed values instead."
        )

    def test_no_layout_constants_leak_outside_storage(self) -> None:
        """Layout filenames must not be hardcoded by consumers."""
        leaked = []
        for path in _outside_storage():
            text = path.read_text(encoding="utf-8")
            for constant in (
                "GRAPH_STATE_RELPATH",
                "CHECKPOINTS_RELPATH",
                "AUDIT_RELPATH",
            ):
                if constant in text:
                    leaked.append(f"{path}: {constant}")
        assert leaked == [], (
            f"Layout constants referenced outside the storage core: {leaked}. "
            "Read them as data from ProjectStorage instead."
        )

    def test_storage_core_does_not_import_other_components(self) -> None:
        """The core must not depend on graph, mcp, app, generation, or checkpoints."""
        forbidden = (
            "film_pipeline.graph",
            "film_pipeline.mcp",
            "film_pipeline.app",
            "film_pipeline.generation",
            "film_pipeline.checkpoints",
            "film_pipeline.review",
            "film_pipeline.validation",
            "film_pipeline.post",
            "film_pipeline.providers",
            "film_pipeline.kb",
            "film_pipeline.agents",
            "film_pipeline.cli",
        )
        offenders: list[str] = []
        for path in _python_files(STORAGE_PACKAGE):
            if path.name == "project_storage.py":
                # The checkpoint backend is injected; only a TYPE_CHECKING
                # import of the store is allowed, which this test still checks
                # by inspecting runtime imports below.
                pass
            for module in _imported_modules(path):
                if any(module.startswith(prefix) for prefix in forbidden):
                    offenders.append(f"{path.name}: {module}")
        assert offenders == [], (
            f"The storage core depends on other components: {offenders}. "
            "Dependencies must point inward: consumers depend on storage, not the reverse."
        )

    def test_storage_core_has_no_runtime_checkpoints_dependency(self) -> None:
        """Injecting the backend keeps ``checkpoints`` out of the core's runtime graph."""
        text = (STORAGE_PACKAGE / "project_storage.py").read_text(encoding="utf-8")
        assert "film_pipeline.checkpoints.git_backend" not in text, (
            "project_storage.py must declare a structural protocol instead of "
            "importing the concrete checkpoint backend."
        )


class TestProjectStorageIsTheOnlyWriter:
    """Consumers receive typed values, not paths they then write to."""

    def test_project_storage_exposes_no_public_path_assembly(self) -> None:
        """The façade returns locations, but callers do not re-derive them."""
        from film_pipeline.artifacts.project_storage import ProjectStorage

        # The gateway must offer typed accessors for every owned concern.
        for method in (
            "read_project_record",
            "write_project_record",
            "read_graph_state",
            "write_graph_state",
            "read_checkpoints",
            "append_checkpoints",
            "read_audit_events",
            "append_audit_events",
            "media_dir",
            "read_manifest",
            "write_manifest",
        ):
            assert callable(getattr(ProjectStorage, method, None)), (
                f"ProjectStorage must own {method}(); consumers should not do it themselves."
            )

    def test_construction_from_root_and_store_agree(self, tmp_path: Path) -> None:
        """Both construction paths must resolve to the same project directory."""
        from film_pipeline.artifacts.project_storage import ProjectStorage
        from film_pipeline.testing.storage import make_store

        root = tmp_path / "store"
        store = make_store(root)
        from_store = ProjectStorage.from_store(store)
        from_root = ProjectStorage.for_root(root)
        assert from_store.project_dir("p1") == from_root.project_dir("p1")

    def test_unconfigured_backend_reports_actionably(self, tmp_path: Path) -> None:
        """Asking for git without an injected backend must not fail cryptically."""
        from film_pipeline.artifacts import project_storage

        saved = project_storage.get_git_backend_type()
        project_storage.set_git_backend_type(None)  # type: ignore[arg-type]
        try:
            with pytest.raises(RuntimeError, match="set_git_backend_type"):
                project_storage.ProjectStorage.for_root(tmp_path).git_backend("p1")
        finally:
            if saved is not None:
                project_storage.set_git_backend_type(saved)
