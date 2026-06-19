"""Mock image provider — placeholder PNG generation for reference images."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from film_pipeline.providers.base import BaseProviderAdapter, ProviderJob
from film_pipeline.schemas.registries.provider_registry import ProviderRegistryEntry

_MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
    b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


class MockImageProvider(BaseProviderAdapter):
    """Mock image provider for zero-cost reference image generation."""

    def __init__(
        self,
        entry: ProviderRegistryEntry,
        output_base: Path | None = None,
    ) -> None:
        super().__init__(entry)
        self.output_base = output_base or Path("/tmp/mock-provider")

    def build_payload(
        self,
        prompt: str,
        references: list[str] | None = None,
        duration: float = 0.0,
        aspect_ratio: str = "16:9",
        seed: int | None = None,
    ) -> dict[str, Any]:
        _ = references
        _ = duration
        return {"prompt": prompt, "aspect_ratio": aspect_ratio, "seed": seed}

    def submit(self, payload: dict[str, Any], shot_id: str) -> ProviderJob:
        job_id = f"mock-img-{uuid4().hex[:12]}"
        return ProviderJob(
            job_id=job_id,
            shot_id=shot_id,
            provider_id=self.entry.provider_id,
            model=self.entry.models[0] if self.entry.models else "mock",
            payload=payload,
            status="completed",
        )

    def poll(self, job: ProviderJob) -> ProviderJob:
        job.status = "completed"
        return job

    def download(self, job: ProviderJob, output_dir: str) -> str:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{job.shot_id}.png"
        path.write_bytes(_MINIMAL_PNG)
        return str(path)

    def extract_metadata(self, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        return {
            "file": file_path,
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "placeholder": True,
        }

    def estimate_cost(self, duration: float, model: str | None = None) -> float:
        _ = duration
        _ = model
        return 0.0
