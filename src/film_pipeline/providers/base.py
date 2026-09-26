"""Base provider adapter — standard contract every provider must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from film_pipeline.schemas.registries.provider_registry import (
    ProviderRegistryEntry,
)


class ProviderJobStatus(StrEnum):
    """Lifecycle status of a provider job as reported by its adapter."""

    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProviderJob:
    """A submitted generation job tracked by the provider."""

    job_id: str
    shot_id: str
    provider_id: str
    model: str
    status: ProviderJobStatus = ProviderJobStatus.SUBMITTED
    polls: int = 0
    payload: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class BaseProviderAdapter(ABC):
    """Standard contract for every video/image/audio provider.

    Every provider — mock or real — implements:
    - build_payload → submit → poll → download → extract_metadata
    - cancel (when supported)
    """

    entry: ProviderRegistryEntry

    def __init__(self, entry: ProviderRegistryEntry) -> None:
        self.entry = entry

    @abstractmethod
    def build_payload(
        self,
        prompt: str,
        references: list[str] | None = None,
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        seed: int | None = None,
    ) -> dict[str, Any]:
        """Build a provider-specific request payload."""
        ...

    @abstractmethod
    def submit(self, payload: dict[str, Any], shot_id: str) -> ProviderJob:
        """Submit a generation job and return a job handle."""
        ...

    @abstractmethod
    def poll(self, job: ProviderJob) -> ProviderJob:
        """Check job status. Updates job in place."""
        ...

    @abstractmethod
    def download(self, job: ProviderJob, output_dir: str) -> str:
        """Download result to output_dir. Returns the output file path."""
        ...

    @abstractmethod
    def extract_metadata(self, file_path: str) -> dict[str, Any]:
        """Extract duration, resolution, frame count, etc. from output."""
        ...

    def cancel(self, job: ProviderJob) -> bool:
        """Cancel a job. Returns True if successful, False if not supported."""
        _ = job
        return False
