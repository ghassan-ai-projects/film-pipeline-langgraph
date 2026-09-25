"""The runtime handle the operator surface depends on.

`operations` owns operator use cases but must not import `studio` (the
composition root): `03-target-architecture.md` §4.6.1 records `operations →
studio` as a forbidden edge. The operator nevertheless needs a small set of
runtime capabilities, so this module declares them as a structural protocol.

Everything here is expressed in terms `operations` already owns or may import
(`storage`, `schemas`, `checkpoints`). The concrete `StudioRuntime` satisfies
the protocol structurally, so no import of the composition root is required and
no runtime subclass is introduced.

The protocol is deliberately narrow. It names only what the operator surface
actually calls; a wider protocol would re-import the god object the target
architecture is trying to dissolve.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ArtifactStorePort(Protocol):
    """The subset of the artifact store the operator surface needs."""

    @property
    def root(self) -> Path:
        """The storage root this store writes into."""
        ...


@runtime_checkable
class ServicesPort(Protocol):
    """The graph services bundle, as far as the operator surface sees it."""

    @property
    def artifact_store(self) -> ArtifactStorePort:
        """The artifact store backing this runtime."""
        ...


@runtime_checkable
class RuntimePort(Protocol):
    """The runtime capabilities the operator surface depends on.

    A conforming object is any runtime that can report its services, hold a
    mutable project registry, resolve the active project, and name its default
    video provider. `film_pipeline.app.runtime.StudioRuntime` satisfies this
    without modification.
    """

    @property
    def services(self) -> ServicesPort | None:
        """The runtime's services, or ``None`` before they are built."""
        ...

    @property
    def projects(self) -> Any:
        """The mutable registry of live project states, keyed by project id."""
        ...

    def create_project(self, project_id: str, title: str = "", slug: str = "") -> dict[str, Any]:
        """Create and register a new project state."""
        ...

    def default_video_provider(self) -> tuple[str, str]:
        """Return the ``(provider, model)`` used for video generation."""
        ...


def artifact_store_of(runtime: RuntimePort) -> ArtifactStorePort | None:
    """The artifact store behind a runtime, or ``None`` when services are absent."""
    services = runtime.services
    if services is None:
        return None
    return services.artifact_store
