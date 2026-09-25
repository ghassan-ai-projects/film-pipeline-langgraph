"""The operator runtime port keeps `operations` independent of the runtime.

`03-target-architecture.md` §4.6.1 records `operations → studio` as a forbidden
edge. The operator surface still needs runtime capabilities, so `operations`
declares them structurally and the concrete `StudioRuntime` satisfies the
protocol without either side importing the other.

These tests pin both halves: that a real runtime conforms to the port, and that
nothing under `operations` imports the composition root.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from film_pipeline.operations.ports import (
    ArtifactStorePort,
    RuntimePort,
    ServicesPort,
    artifact_store_of,
)

_OPERATIONS_DIR = Path(__file__).resolve().parents[3] / "src" / "film_pipeline" / "operations"
_FORBIDDEN_ROOT = "film_pipeline.app"


class _FakeStore:
    def __init__(self, root: Path) -> None:
        self.root = root


class _FakeServices:
    def __init__(self, store: Any) -> None:
        self.artifact_store = store


class _FakeRuntime:
    """A minimal object satisfying ``RuntimePort`` without any real runtime."""

    def __init__(self, services: Any) -> None:
        self.services = services
        self.projects: dict[str, Any] = {}

    def create_project(self, project_id: str, title: str = "", slug: str = "") -> dict[str, Any]:
        state = {"project_id": project_id, "title": title, "slug": slug}
        self.projects[project_id] = state
        return state

    def default_video_provider(self) -> tuple[str, str]:
        return ("mock", "mock-video")


class TestProtocolConformance:
    def test_fake_runtime_satisfies_the_port(self, tmp_path: Path) -> None:
        runtime = _FakeRuntime(_FakeServices(_FakeStore(tmp_path)))
        assert isinstance(runtime, RuntimePort)

    def test_store_and_services_satisfy_their_ports(self, tmp_path: Path) -> None:
        store = _FakeStore(tmp_path)
        assert isinstance(store, ArtifactStorePort)
        assert isinstance(_FakeServices(store), ServicesPort)

    def test_real_runtime_satisfies_the_port(self, tmp_path: Path) -> None:
        """The production runtime conforms structurally, with no subclass."""
        from film_pipeline.app.runtime import StudioRuntime

        runtime = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
        assert isinstance(runtime, RuntimePort)


class TestArtifactStoreOf:
    def test_returns_the_store_when_services_exist(self, tmp_path: Path) -> None:
        store = _FakeStore(tmp_path)
        runtime = _FakeRuntime(_FakeServices(store))
        assert artifact_store_of(runtime) is store

    def test_returns_none_without_services(self) -> None:
        assert artifact_store_of(_FakeRuntime(None)) is None

    def test_persistence_helpers_accept_the_port(self, tmp_path: Path) -> None:
        """`storage_for` and `artifact_root` take the port, not the runtime."""
        from film_pipeline.app._persistence import artifact_root, storage_for

        runtime = _FakeRuntime(_FakeServices(_FakeStore(tmp_path)))
        assert artifact_root(runtime) == tmp_path
        storage = storage_for(runtime)
        assert storage is not None
        assert storage.root == tmp_path

    def test_persistence_helpers_tolerate_absent_services(self) -> None:
        from film_pipeline.app._persistence import artifact_root, storage_for

        runtime = _FakeRuntime(None)
        assert artifact_root(runtime) is None
        assert storage_for(runtime) is None


class TestOperationsDoesNotImportTheCompositionRoot:
    def test_no_operations_module_imports_app(self) -> None:
        """FES #3 (`operations → studio`) must not be introduced."""
        offenders: list[str] = []
        for path in sorted(_OPERATIONS_DIR.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                targets: list[str] = []
                if isinstance(node, ast.Import):
                    targets = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    targets = [node.module or ""]
                for target in targets:
                    if target == _FORBIDDEN_ROOT or target.startswith(f"{_FORBIDDEN_ROOT}."):
                        offenders.append(f"{path.name}: {target}")
        assert offenders == [], f"operations imports the composition root: {offenders}"

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            ("import film_pipeline.app.runtime", True),
            ("from film_pipeline.app import runtime", True),
            ("from film_pipeline.app.runtime import StudioRuntime", True),
            ("from film_pipeline.storage import store", False),
            ("from film_pipeline.schemas import artifact", False),
        ],
    )
    def test_guard_detects_the_forms_it_claims(self, source: str, expected: bool) -> None:
        tree = ast.parse(source)
        found = False
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                targets = [node.module or ""]
            found = found or any(
                t == _FORBIDDEN_ROOT or t.startswith(f"{_FORBIDDEN_ROOT}.") for t in targets
            )
        assert found is expected
