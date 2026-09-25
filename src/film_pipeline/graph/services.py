"""Compatibility aliases for :mod:`film_pipeline.orchestration.services`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.orchestration.services import _SERVICES_CTX as _SERVICES_CTX
from film_pipeline.orchestration.services import SERVICES_KEY as SERVICES_KEY
from film_pipeline.orchestration.services import AgentRegistry as AgentRegistry
from film_pipeline.orchestration.services import ArtifactStore as ArtifactStore
from film_pipeline.orchestration.services import GraphServices as GraphServices
from film_pipeline.orchestration.services import KBContextPacket as KBContextPacket
from film_pipeline.orchestration.services import ModelAdapter as ModelAdapter
from film_pipeline.orchestration.services import ModelRouter as ModelRouter
from film_pipeline.orchestration.services import PromptRunner as PromptRunner
from film_pipeline.orchestration.services import _artifact_store as _artifact_store
from film_pipeline.orchestration.services import _default_artifact_root as _default_artifact_root
from film_pipeline.orchestration.services import _get_services as _get_services
from film_pipeline.orchestration.services import _mvp_agent_registry as _mvp_agent_registry
from film_pipeline.orchestration.services import ensure_storage_root as ensure_storage_root
from film_pipeline.orchestration.services import resolve_storage_root as resolve_storage_root

__all__ = [
    "SERVICES_KEY",
    "AgentRegistry",
    "ArtifactStore",
    "GraphServices",
    "KBContextPacket",
    "ModelAdapter",
    "ModelRouter",
    "PromptRunner",
    "ensure_storage_root",
    "resolve_storage_root",
]
