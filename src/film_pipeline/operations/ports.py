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

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from film_pipeline.orchestration.services import GraphServices
from film_pipeline.schemas.checkpoint import CheckpointMetadata
from film_pipeline.storage.store import ArtifactStore

#: The artifact store is a concrete owner in `storage`, which `operations` may
#: import. A structural stand-in would be narrower than the real class and so
#: could not satisfy Protocol invariance.
ArtifactStorePort = ArtifactStore


#: The services bundle is owned by `graph`, which `operations` may import.
ServicesPort = GraphServices


@runtime_checkable
class RuntimePort(Protocol):
    """The runtime capabilities the operator surface depends on.

    A conforming object is any runtime that can report its services, hold a
    mutable project registry, drive the graph, and manage providers.
    `film_pipeline.studio.runtime.StudioRuntime` satisfies this without
    modification or subclassing.

    The protocol is intentionally the *measured* surface: every member below is
    called by at least one operator use case. Adding speculative members would
    re-create the god object this port exists to avoid.
    """

    # ── identity and configuration ────────────────────────────────────────
    @property
    def server_mode(self) -> str:
        """The active provider mode (``mock`` or ``real``)."""
        ...

    # Read-write: the concrete runtime assigns this during initialization and
    # tests exercise the not-yet-initialized state by clearing it.
    services: ServicesPort | None

    # ── project state ─────────────────────────────────────────────────────
    @property
    def projects(self) -> Any:
        """The mutable registry of live project states, keyed by project id."""
        ...

    def create_project(self, project_id: str, title: str = "", slug: str = "") -> dict[str, Any]:
        """Create and register a new project state."""
        ...

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Return a live project state, or ``None`` when it is unknown."""
        ...

    def set_active(self, project_id: str) -> None:
        """Mark a project as the session's active project."""
        ...

    def get_active(self) -> dict[str, Any] | None:
        """Return the active project state, or ``None`` when none is selected."""
        ...

    @property
    def active_project_id(self) -> str:
        """The id of the session's active project, or an empty string."""
        ...

    @property
    def checkpoint_managers(self) -> Mapping[str, Any]:
        """The checkpoint manager for each project, keyed by project id."""
        ...

    @property
    def project_roots(self) -> Mapping[str, Path]:
        """The on-disk root of each live project, keyed by project id."""
        ...

    def _persist_project_state(self, project_id: str) -> None:
        """Persist a project's in-memory state to durable storage.

        Recorded debt (O7, leaked internals): this is the concrete runtime's
        private name and the operator surface already reaches it. The port
        mirrors the real spelling so the protocol describes the code that
        exists rather than a rename that has not happened; giving it a public
        name is a separate, behavior-adjacent change.
        """
        ...

    # ── orchestration ─────────────────────────────────────────────────────
    def run_graph(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the graph for a phase."""
        ...

    def approve_phase(self, *args: Any, **kwargs: Any) -> Any:
        """Advance past a human approval gate."""
        ...

    def request_revision(self, *args: Any, **kwargs: Any) -> Any:
        """Request a revision at a human gate."""
        ...

    def run_validation(self, *args: Any, **kwargs: Any) -> Any:
        """Run the validation phase."""
        ...

    # ── checkpoints and audit ─────────────────────────────────────────────
    def list_checkpoints(self, *args: Any, **kwargs: Any) -> Any:
        """List checkpoint metadata for a project."""
        ...

    def get_checkpoint(self, checkpoint_id: str) -> CheckpointMetadata | None:
        """Find checkpoint metadata by its globally unique identifier."""
        ...

    def create_checkpoint(self, *args: Any, **kwargs: Any) -> Any:
        """Create a checkpoint for a project."""
        ...

    def get_audit_log(self, *args: Any, **kwargs: Any) -> Any:
        """Return a project's audit events."""
        ...

    def list_operator_comments(self, *args: Any, **kwargs: Any) -> Any:
        """Return operator comments recorded against a project."""
        ...

    def add_operator_comment(self, *args: Any, **kwargs: Any) -> Any:
        """Record an operator comment."""
        ...

    # ── providers ─────────────────────────────────────────────────────────
    @property
    def provider_adapters(self) -> Mapping[str, Any]:
        """The registered provider adapters, keyed by provider id."""
        ...

    def register_provider(self, provider_id: str, adapter: Any) -> None:
        """Register a provider adapter under an id."""
        ...

    def clear_providers(self) -> None:
        """Remove every registered provider adapter."""
        ...

    def set_provider_health(self, provider_id: str, status: str, reason: str = "") -> None:
        """Record a provider's health status."""
        ...

    def get_all_health(self) -> Any:
        """Return health records for every known provider."""
        ...

    def get_provider_health(self, provider_id: str) -> Any:
        """Return one provider's health record."""
        ...

    def list_providers(self) -> list[str]:
        """Return the ids of every registered provider."""
        ...

    def seed_default_provider_health(self) -> None:
        """Seed health records for the default provider set."""
        ...

    def default_video_provider(self) -> tuple[str, str]:
        """Return the ``(provider, model)`` used for video generation."""
        ...


@runtime_checkable
class RuntimeProvider(Protocol):
    """Resolves the active runtime for a surface that does not hold one.

    The operator service may be constructed with an explicit runtime or resolve
    the process singleton lazily. That *resolution policy* is the composition
    root's business, so it is injected rather than imported: `operations` must
    not import `film_pipeline.studio`.
    """

    def current(self) -> RuntimePort:
        """Return the runtime currently in effect."""
        ...

    def switch(self, mode: str) -> RuntimePort:
        """Rebuild and return the runtime in a new provider mode."""
        ...


@runtime_checkable
class ProviderComposition(Protocol):
    """Composes project-profile provider specs onto a runtime.

    `operations` owns the *policy* that a profile stack selects providers and
    that a credential check precedes project creation, but building adapters is
    composition-root work. This port carries that capability across the boundary
    so `operations` never imports `film_pipeline.studio`.
    """

    def register_profile_providers(
        self,
        runtime: RuntimePort,
        profile_stack: dict[str, str],
        resolved_config: dict[str, object],
    ) -> None:
        """Replace the runtime's providers with the profile-selected adapters."""
        ...

    def missing_profile_credentials(
        self,
        profile_stack: dict[str, str],
        resolved_config: dict[str, object],
    ) -> list[Any]:
        """Return the credentials the resolved profile requires but lacks."""
        ...


def artifact_store_of(runtime: RuntimePort) -> ArtifactStorePort | None:
    """The artifact store behind a runtime, or ``None`` when services are absent."""
    services = runtime.services
    if services is None:
        return None
    return services.artifact_store
