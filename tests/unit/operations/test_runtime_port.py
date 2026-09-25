"""The operator runtime port keeps `operations` independent of the runtime.

`03-target-architecture.md` §4.6.1 records `operations → studio` as a forbidden
edge. The operator surface still needs runtime capabilities, so `operations`
declares them structurally and the composition root supplies the concrete
bindings.

The port deliberately describes the *real* surface (`ArtifactStorePort` and
`ServicesPort` are the concrete `storage`/`graph` owners, which `operations` may
import), so conformance is checked against the production runtime rather than a
toy double. These tests pin three things: that the real runtime conforms, that
the injected collaborators conform, and that nothing under `operations` imports
the composition root.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from film_pipeline.graph.services import GraphServices
from film_pipeline.operations.ports import (
    ArtifactStorePort,
    ProviderComposition,
    RuntimePort,
    RuntimeProvider,
    ServicesPort,
    artifact_store_of,
)
from film_pipeline.storage.store import ArtifactStore

_OPERATIONS_DIR = Path(__file__).resolve().parents[3] / "src" / "film_pipeline" / "operations"
_FORBIDDEN_ROOT = "film_pipeline.app"


class _NoServicesRuntime:
    """The only runtime shape the port must tolerate besides the real one."""

    def __init__(self) -> None:
        self.services: Any = None


class TestProtocolConformance:
    def test_real_runtime_satisfies_the_port(self, tmp_path: Path) -> None:
        """The production runtime conforms structurally, with no subclass."""
        from film_pipeline.app.runtime import StudioRuntime

        runtime = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
        assert isinstance(runtime, RuntimePort)

    def test_runtime_provider_is_satisfied_by_the_studio_binding(self, tmp_path: Path) -> None:
        from film_pipeline.app._operator_runtime import StudioRuntimeProvider

        assert isinstance(StudioRuntimeProvider(), RuntimeProvider)

    def test_provider_composition_is_satisfied_by_the_studio_binding(self) -> None:
        from film_pipeline.app._operator_runtime import profile_provider_composition

        assert isinstance(profile_provider_composition(), ProviderComposition)

    def test_store_and_services_ports_are_the_concrete_owners(self) -> None:
        """`operations` may import these, so no structural stand-in is needed."""
        assert ArtifactStorePort is ArtifactStore
        assert ServicesPort is GraphServices


class TestArtifactStoreOf:
    def test_returns_the_store_when_services_exist(self, tmp_path: Path) -> None:
        from film_pipeline.app.runtime import StudioRuntime

        runtime = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
        assert runtime.services is not None
        assert artifact_store_of(runtime) is runtime.services.artifact_store

    def test_returns_none_without_services(self) -> None:
        assert artifact_store_of(_NoServicesRuntime()) is None  # type: ignore[arg-type]

    def test_persistence_helpers_accept_the_real_runtime(self, tmp_path: Path) -> None:
        """`storage_for` and `artifact_root` take the port, not a runtime import."""
        from film_pipeline.app._persistence import artifact_root, storage_for
        from film_pipeline.app.runtime import StudioRuntime

        runtime = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
        storage = storage_for(runtime)
        if storage is None:
            assert artifact_root(runtime) is None
        else:
            assert storage.root == artifact_root(runtime)

    def test_persistence_helpers_tolerate_absent_services(self) -> None:
        from film_pipeline.app._persistence import artifact_root, storage_for

        runtime = _NoServicesRuntime()
        assert artifact_root(runtime) is None  # type: ignore[arg-type]
        assert storage_for(runtime) is None  # type: ignore[arg-type]


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

    def test_operator_service_module_has_no_module_level_app_import(self) -> None:
        """The service resolves the runtime through injected ports only.

        Same-package imports (`app.services.*`) remain until the physical file
        move; those are intra-module and constrained by neither the layer law
        nor the port. What must not exist is a module-level import of the
        runtime, the provider composition, or the persistence helpers.
        """
        source = (_OPERATIONS_DIR / ".." / "app" / "services" / "operator.py").resolve()
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        forbidden = (
            "film_pipeline.app.runtime",
            "film_pipeline.app._provider_profiles",
            "film_pipeline.app._persistence",
        )
        offenders: list[str] = []
        for node in tree.body:
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                targets = [node.module or ""]
            offenders.extend(t for t in targets if t in forbidden)
        assert offenders == [], f"module-level composition-root imports: {offenders}"

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
