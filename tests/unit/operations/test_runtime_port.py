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

from film_pipeline.operations.ports import (
    ArtifactStorePort,
    ProviderComposition,
    RuntimePort,
    RuntimeProvider,
    ServicesPort,
    artifact_store_of,
)
from film_pipeline.orchestration.services import GraphServices
from film_pipeline.storage.store import ArtifactStore

_OPERATIONS_DIR = Path(__file__).resolve().parents[3] / "src" / "film_pipeline" / "operations"
_FORBIDDEN_ROOT = "film_pipeline.studio"


class _NoServicesRuntime:
    """The only runtime shape the port must tolerate besides the real one."""

    def __init__(self) -> None:
        self.services: Any = None


class TestProtocolConformance:
    def test_real_runtime_satisfies_the_port(self, tmp_path: Path) -> None:
        """The production runtime conforms structurally, with no subclass."""
        from film_pipeline.studio.runtime import StudioRuntime

        runtime = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
        assert isinstance(runtime, RuntimePort)

    def test_runtime_provider_is_satisfied_by_the_studio_binding(self, tmp_path: Path) -> None:
        from film_pipeline.studio._operator_runtime import StudioRuntimeProvider

        assert isinstance(StudioRuntimeProvider(), RuntimeProvider)

    def test_provider_composition_is_satisfied_by_the_studio_binding(self) -> None:
        from film_pipeline.studio._operator_runtime import profile_provider_composition

        assert isinstance(profile_provider_composition(), ProviderComposition)

    def test_store_and_services_ports_are_the_concrete_owners(self) -> None:
        """`operations` may import these, so no structural stand-in is needed."""
        assert ArtifactStorePort is ArtifactStore
        assert ServicesPort is GraphServices


class TestArtifactStoreOf:
    def test_returns_the_store_when_services_exist(self, tmp_path: Path) -> None:
        from film_pipeline.studio.runtime import StudioRuntime

        runtime = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
        assert runtime.services is not None
        assert artifact_store_of(runtime) is runtime.services.artifact_store

    def test_returns_none_without_services(self) -> None:
        assert artifact_store_of(_NoServicesRuntime()) is None  # type: ignore[arg-type]

    def test_persistence_helpers_accept_the_real_runtime(self, tmp_path: Path) -> None:
        """`storage_for` and `artifact_root` take the port, not a runtime import."""
        from film_pipeline.studio._persistence import artifact_root, storage_for
        from film_pipeline.studio.runtime import StudioRuntime

        runtime = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
        storage = storage_for(runtime)
        if storage is None:
            assert artifact_root(runtime) is None
        else:
            assert storage.root == artifact_root(runtime)

    def test_persistence_helpers_tolerate_absent_services(self) -> None:
        from film_pipeline.studio._persistence import artifact_root, storage_for

        runtime = _NoServicesRuntime()
        assert artifact_root(runtime) is None  # type: ignore[arg-type]
        assert storage_for(runtime) is None  # type: ignore[arg-type]


class TestOperationsDoesNotImportTheCompositionRoot:
    def test_no_operations_module_imports_app_at_module_level(self) -> None:
        """FES #3 (`operations → studio`) must not be introduced.

        Module-level imports only: a *nested* import of
        `film_pipeline.studio._operator_runtime` is the deliberate lazy default
        that keeps zero-arg `OperatorService()` working, and it is asserted
        separately below.
        """
        offenders: list[str] = []
        for path in sorted(_OPERATIONS_DIR.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                targets: list[str] = []
                if isinstance(node, ast.Import):
                    targets = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    targets = [node.module or ""]
                for target in targets:
                    if target == _FORBIDDEN_ROOT or target.startswith(f"{_FORBIDDEN_ROOT}."):
                        offenders.append(f"{path.name}: {target}")
        assert offenders == [], f"operations imports the composition root: {offenders}"

    def test_no_operations_module_imports_studio_at_any_level(self) -> None:
        """Not even a nested import: that edge is what created a real cycle.

        An earlier revision allowed one function-local import of
        `film_pipeline.studio._operator_runtime` to keep zero-arg
        `OperatorService()` working. `studio` already imports `operations`, so
        the pair formed an `operations <-> studio` cycle that Enola reported as
        a gating failure. Every production call site passes a runtime
        explicitly, so the default bought nothing and is gone.
        """
        offenders: list[str] = []
        for path in sorted(_OPERATIONS_DIR.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            top_level = {id(node) for node in tree.body}
            for node in ast.walk(tree):
                targets: list[str] = []
                if isinstance(node, ast.Import):
                    targets = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    targets = [node.module or ""]
                where = "module level" if id(node) in top_level else "nested"
                offenders.extend(
                    f"{path.name} ({where}): {t}"
                    for t in targets
                    if t == _FORBIDDEN_ROOT or t.startswith(f"{_FORBIDDEN_ROOT}.")
                )
        assert offenders == [], f"operations imports the composition root: {offenders}"

    def test_service_requires_its_collaborators(self, tmp_path: Path) -> None:
        """A bare service fails actionably rather than reaching into studio."""
        from film_pipeline.operations.errors import BackendOperationError
        from film_pipeline.operations.operator import OperatorService

        service = OperatorService()
        with pytest.raises(BackendOperationError, match="RuntimeProvider"):
            _ = service.runtime
        with pytest.raises(BackendOperationError, match="ProviderComposition"):
            service.register_profile_providers({}, {})

    def test_service_accepts_an_injected_runtime(self, tmp_path: Path) -> None:
        """Passing a runtime directly keeps working without any studio import."""
        from film_pipeline.operations.operator import OperatorService
        from film_pipeline.studio.runtime import StudioRuntime

        runtime = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
        assert OperatorService(runtime).runtime is runtime

    def test_studio_factory_returns_a_wired_service(self, tmp_path: Path) -> None:
        """The composition root supplies the collaborators operations requires."""
        from film_pipeline.operations.operator import OperatorService
        from film_pipeline.studio._operator_runtime import operator_service
        from film_pipeline.studio.runtime import StudioRuntime

        runtime = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
        service = operator_service(runtime)
        assert isinstance(service, OperatorService)
        assert service.runtime is runtime

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            ("import film_pipeline.studio.runtime", True),
            ("from film_pipeline.studio import runtime", True),
            ("from film_pipeline.studio.runtime import StudioRuntime", True),
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
