"""Veo 3.1 Fast provider adapter via Google Cloud.

Implements the full BaseProviderAdapter contract. Requires ``GOOGLE_API_KEY``.
Cost model TBD — insert actual rate when available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from film_pipeline.providers.base import BaseProviderAdapter, ProviderJob
from film_pipeline.providers.credentials import lookup
from film_pipeline.schemas.registries.provider_registry import ProviderRegistryEntry


class VeoFastProvider(BaseProviderAdapter):
    """Veo 3.1 Fast provider adapter. Stub pending API integration."""

    def __init__(self, entry: ProviderRegistryEntry) -> None:
        super().__init__(entry)

    def _api_key(self) -> str:
        key = lookup("veo-fast")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY is not set.")
        return key

    def build_payload(
        self,
        prompt: str,
        references: list[str] | None = None,
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        seed: int | None = None,
    ) -> dict[str, Any]:
        _ = references
        _ = seed
        return {"prompt": prompt, "duration": duration, "aspect_ratio": aspect_ratio}

    def submit(self, payload: dict[str, Any], shot_id: str) -> ProviderJob:
        return ProviderJob(
            job_id=f"veo-{uuid4().hex[:12]}",
            shot_id=shot_id,
            provider_id=self.entry.provider_id,
            model=self.entry.models[0] if self.entry.models else "veo-3.1-fast",
            payload=payload,
            status="submitted",
        )

    def poll(self, job: ProviderJob) -> ProviderJob:
        job.status = "completed"
        return job

    def download(self, job: ProviderJob, output_dir: str) -> str:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{job.shot_id}.mp4"
        path.write_bytes(b"PLACEHOLDER")
        return str(path)

    def extract_metadata(self, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        return {"file": file_path, "size_bytes": path.stat().st_size if path.exists() else 0}

    def estimate_cost(self, duration: float, model: str | None = None) -> float:
        _ = model
        return duration * 0.10  # placeholder rate
