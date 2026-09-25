"""Resolve the storage gateway from a runtime handle.

These helpers answer "where does this runtime store artifacts?" without
depending on the concrete runtime, so a caller that holds only a structural
runtime handle (the operator surface) can reach storage without importing the
composition root.

The accepted shape mirrors :class:`film_pipeline.operations.ports.RuntimePort`
but is declared locally so `storage` keeps no dependency on `operations`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from film_pipeline.storage.project_storage import ProjectStorage


class _StoreLike(Protocol):
    @property
    def root(self) -> Path:
        """The storage root this store writes into."""
        ...


class _ServicesLike(Protocol):
    @property
    def artifact_store(self) -> _StoreLike:
        """The artifact store backing the runtime."""
        ...


class RuntimeLike(Protocol):
    """The runtime shape these helpers need: services that expose a store."""

    @property
    def services(self) -> _ServicesLike | None:
        """The runtime's services, or ``None`` before they are built."""
        ...


def artifact_store_root(runtime: RuntimeLike) -> Path | None:
    """Return the runtime's artifact root, or ``None`` when services are absent."""
    services = runtime.services
    if services is None:
        return None
    return services.artifact_store.root


def project_storage_for(runtime: RuntimeLike) -> ProjectStorage | None:
    """Return a project-storage gateway over the runtime's artifact root."""
    root = artifact_store_root(runtime)
    return None if root is None else ProjectStorage.for_root(root)
