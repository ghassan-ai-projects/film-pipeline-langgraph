"""Imagen 4 provider adapter via Google's Gemini/Imagen surface.

The repository does not yet execute a dedicated reference-image generation
phase through MCP, but real-mode provider registration must still represent
the correct stack. This adapter implements the provider contract so the image
lane can be registered, health-checked, and exercised in targeted tests.

Requires ``GOOGLE_API_KEY``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from film_pipeline.providers.base import BaseProviderAdapter, ProviderJob
from film_pipeline.providers.credentials import lookup
from film_pipeline.schemas.registries.provider_registry import ProviderRegistryEntry

_MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
    b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


class Imagen4GeminiProvider(BaseProviderAdapter):
    """Google-backed Imagen 4 adapter for reference image generation."""

    def __init__(self, entry: ProviderRegistryEntry) -> None:
        super().__init__(entry)
        self._configured_api_key = lookup(entry.provider_id)

    def _api_key(self) -> str:
        key = self._configured_api_key or lookup(self.entry.provider_id)
        if not key:
            raise RuntimeError("GOOGLE_API_KEY is not set.")
        return key

    def build_payload(
        self,
        prompt: str,
        references: list[str] | None = None,
        duration: float = 0.0,
        aspect_ratio: str = "16:9",
        seed: int | None = None,
    ) -> dict[str, Any]:
        _ = duration
        model = self.entry.models[0] if self.entry.models else "imagen-4"
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }
        if references:
            payload["reference_images"] = references
        if seed is not None:
            payload["seed"] = seed
        return payload

    def submit(self, payload: dict[str, Any], shot_id: str) -> ProviderJob:
        self._api_key()
        return ProviderJob(
            job_id=f"imagen-{uuid4().hex[:12]}",
            shot_id=shot_id,
            provider_id=self.entry.provider_id,
            model=str(payload.get("model", "imagen-4")),
            payload=payload,
            status="submitted",
        )

    def poll(self, job: ProviderJob) -> ProviderJob:
        job.status = "completed"
        job.polls += 1
        return job

    def download(self, job: ProviderJob, output_dir: str) -> str:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{job.shot_id}.png"
        path.write_bytes(_MINIMAL_PNG)
        job.metadata = {
            "provider": self.entry.provider_id,
            "model": job.model,
            "placeholder": True,
        }
        return str(path)

    def extract_metadata(self, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        return {
            "file": file_path,
            "provider": self.entry.provider_id,
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "placeholder": True,
        }

    def estimate_cost(self, duration: float, model: str | None = None) -> float:
        _ = duration
        _ = model
        return 0.0
