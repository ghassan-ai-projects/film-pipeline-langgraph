"""The runtime handle the surviving operator use cases depend on.

`operations` owns operator use cases but must not import `studio` (the
composition root): `03-target-architecture.md` §4.6.1 records `operations →
studio` as a forbidden edge. The use cases nevertheless need a small set of
runtime capabilities, so this module declares them as a structural protocol.

Everything here is expressed in terms `operations` already owns or may import
(`storage`, `schemas`, `checkpoints`). The concrete `StudioRuntime` satisfies the
protocol structurally, so no import of the composition root is required and no
runtime subclass is introduced.

## Why this shrank

The protocol used to declare ~30 members under a claim its own docstring made —
"every member below is called by at least one operator use case". That was true
when `OperatorService` had 31 public methods; after the orphaned 25 were deleted
(`docs/modularity-improvements/03-one-use-case-layer.md`), it was false for about
twenty of them. A protocol declaring members nothing calls is a speculative
surface, and this file's own docstring says a wider protocol "re-imports the god
object the target architecture is trying to dissolve".

The members below are the ones the surviving use cases actually reach:

    _checkpoint_ops      services, checkpoint_managers, get_checkpoint,
                         list_checkpoints
    _operator_runtime    clear_providers, register_provider, set_provider_health

`RuntimeProvider` and `ProviderComposition` are deleted with the service that
consumed them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from film_pipeline.orchestration.services import GraphServices
from film_pipeline.schemas.checkpoint import CheckpointMetadata
from film_pipeline.storage.store import ArtifactStore

#: The artifact store is a concrete owner in `storage`, which `operations` may
#: import. A structural stand-in would be narrower than the real class and so
#: could not satisfy Protocol invariance.
ArtifactStorePort = ArtifactStore


#: The services bundle is owned by `orchestration`, which `operations` may import.
ServicesPort = GraphServices


@runtime_checkable
class RuntimePort(Protocol):
    """The runtime capabilities the surviving operator use cases depend on.

    A conforming object is any runtime that can report its services, expose its
    checkpoint managers, and manage providers.
    `film_pipeline.studio.runtime.StudioRuntime` satisfies this without
    modification or subclassing.
    """

    # Read-write: the concrete runtime assigns this during initialization and
    # tests exercise the not-yet-initialized state by clearing it.
    services: ServicesPort | None

    @property
    def checkpoint_managers(self) -> Mapping[str, Any]:
        """Per-project checkpoint managers, keyed by project id."""
        ...

    def get_checkpoint(self, checkpoint_id: str) -> CheckpointMetadata | None:
        """Return checkpoint metadata by its globally unique identifier."""
        ...

    def list_checkpoints(self, *args: Any, **kwargs: Any) -> Any:
        """List a project's checkpoints, newest first."""
        ...

    # ── provider registration ─────────────────────────────────────────────
    def clear_providers(self) -> None:
        """Remove every registered provider adapter."""
        ...

    def register_provider(self, provider_id: str, adapter: Any) -> None:
        """Register one provider adapter under its provider id."""
        ...

    def set_provider_health(self, provider_id: str, status: str, reason: str = "") -> None:
        """Record a provider's health status."""
        ...


def artifact_store_of(runtime: RuntimePort) -> ArtifactStorePort | None:
    """The artifact store behind a runtime, or ``None`` when services are absent."""
    services = runtime.services
    if services is None:
        return None
    return services.artifact_store


__all__ = [
    "ArtifactStorePort",
    "RuntimePort",
    "ServicesPort",
    "artifact_store_of",
]
