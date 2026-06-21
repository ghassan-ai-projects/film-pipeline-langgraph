"""Mock image provider — placeholder PNG generation for reference images."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from film_pipeline.providers.base import BaseProviderAdapter, ProviderJob
from film_pipeline.schemas.registries.provider_registry import ProviderRegistryEntry

_MOCK_SIZE = 1024


def _mock_png(path: Path, shot_id: str, prompt: str) -> None:
    """Write a 1024x1024 varied PNG so heuristic checks pass."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (_MOCK_SIZE, _MOCK_SIZE), (180, 180, 190))
    draw = ImageDraw.Draw(img)
    # Add color variation so it's not flagged as solid color
    for i in range(0, _MOCK_SIZE, 128):
        for j in range(0, _MOCK_SIZE, 128):
            draw.rectangle(
                [i, j, i + 64, j + 64],
                fill=((i * 3) % 256, (j * 5) % 256, ((i + j) * 7) % 256),
            )
    # Draw reference info in top-left corner
    draw.text((16, 16), f"MOCK IMAGE\n{shot_id}", fill=(255, 255, 255))
    draw.text((16, 56), prompt[:120], fill=(200, 200, 200))
    img.save(path, "PNG")


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
        prompt = str(job.payload.get("prompt", "")) if job.payload else ""
        _mock_png(path, job.shot_id, prompt)
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
