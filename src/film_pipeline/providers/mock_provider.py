"""Mock video provider — implements full adapter contract with zero cost."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from film_pipeline.providers.base import (
    BaseProviderAdapter,
    ProviderJob,
    ProviderJobStatus,
)
from film_pipeline.schemas.registries.provider_registry import ProviderRegistryEntry

_MINIMAL_MP4 = (
    b"\x00\x00\x00\x1c\x66\x74\x79\x70\x6d\x70\x34\x32\x00\x00\x00\x00"
    b"\x6d\x70\x34\x32\x69\x73\x6f\x6d\x00\x00\x00\x08\x6d\x6f\x6f\x76"
)

_MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
    b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


@dataclass(frozen=True)
class ScenarioStep:
    """One step in a mock provider scenario script."""

    shot_id: str
    submit: str = "success"
    polls_before_complete: int = 1
    output: str = "placeholder_video"
    last_frame: str = "generated"
    mid_frame: str = "generated"
    error_code: str = ""
    expected_decision: str = ""


class MockVideoProvider(BaseProviderAdapter):
    """Mock video provider for zero-cost end-to-end testing."""

    def __init__(
        self,
        entry: ProviderRegistryEntry,
        output_base: Path | None = None,
        scenario_steps: list[ScenarioStep] | None = None,
    ) -> None:
        super().__init__(entry)
        self.output_base = output_base or Path("/tmp/mock-provider")
        self.scenario_steps = scenario_steps or []
        self._step_index = 0
        self._jobs: dict[str, ProviderJob] = {}
        self._poll_counts: dict[str, int] = {}

    def _current_step(self) -> ScenarioStep | None:
        if self._step_index < len(self.scenario_steps):
            return self.scenario_steps[self._step_index]
        return None

    def build_payload(
        self,
        prompt: str,
        references: list[str] | None = None,
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        seed: int | None = None,
    ) -> dict[str, Any]:
        return {
            "prompt": prompt,
            "references": references or [],
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "seed": seed,
            "provider": self.entry.provider_id,
            "model": self.entry.models[0] if self.entry.models else "mock",
        }

    def submit(self, payload: dict[str, Any], shot_id: str) -> ProviderJob:
        step = self._current_step()
        if step and step.submit == "error":
            self._step_index += 1
            raise RuntimeError(f"Mock provider submit error: {step.error_code or 'unknown'}")

        job_id = f"mock-job-{uuid4().hex[:12]}"
        job = ProviderJob(
            job_id=job_id,
            shot_id=shot_id,
            provider_id=self.entry.provider_id,
            model=payload.get("model", "mock"),
            payload=payload,
        )
        self._jobs[job_id] = job
        self._poll_counts[job_id] = 0
        return job

    def poll(self, job: ProviderJob) -> ProviderJob:
        self._poll_counts[job.job_id] += 1
        step = self._current_step()
        polls_needed = step.polls_before_complete if step else 1

        if step and step.error_code and self._poll_counts[job.job_id] > polls_needed:
            job.status = ProviderJobStatus.FAILED
            job.metadata = {"error": step.error_code}
            return job

        if self._poll_counts[job.job_id] >= polls_needed:
            job.status = ProviderJobStatus.COMPLETED
        else:
            job.status = ProviderJobStatus.PROCESSING
        return job

    def download(self, job: ProviderJob, output_dir: str) -> str:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        step = self._current_step()
        if step and step.output == "corrupt":
            video_path = self._write_corrupt_video(out, job.shot_id)
        else:
            video_path = self._write_video_with_frames(out, job.shot_id, step)
            job.metadata = self._write_asset_metadata(out, job)

        self._step_index += 1
        return str(video_path)

    def _write_corrupt_video(self, output_dir: Path, shot_id: str) -> Path:
        """Persist a deliberately corrupted video to simulate a damaged download."""
        video_path = output_dir / f"{shot_id}.mp4"
        video_path.write_bytes(b"CORRUPT_DATA")
        return video_path

    def _write_video_with_frames(
        self,
        output_dir: Path,
        shot_id: str,
        step: ScenarioStep | None,
    ) -> Path:
        """Persist the placeholder video plus last/mid frames unless the scenario fails them."""
        video_path = output_dir / f"{shot_id}.mp4"
        video_path.write_bytes(_MINIMAL_MP4)

        if step is None or step.last_frame != "failed":
            (output_dir / f"{shot_id}_last.png").write_bytes(_MINIMAL_PNG)
        if step is None or step.mid_frame != "failed":
            (output_dir / f"{shot_id}_mid.png").write_bytes(_MINIMAL_PNG)
        return video_path

    def _write_asset_metadata(self, output_dir: Path, job: ProviderJob) -> dict[str, Any]:
        """Persist the companion JSON describing the generated asset."""
        metadata = {
            "shot_id": job.shot_id,
            "job_id": job.job_id,
            "provider": job.provider_id,
            "model": job.model,
            "duration_seconds": 5.0,
            "resolution": "1280x720",
            "fps": 24,
            "file_size_bytes": len(_MINIMAL_MP4),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        (output_dir / f"{job.shot_id}_metadata.json").write_text(json.dumps(metadata, indent=2))
        return metadata

    def extract_metadata(self, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"error": "file_not_found", "path": file_path}

        meta_path = path.parent / f"{path.stem}_metadata.json"
        if meta_path.exists():
            raw: Any = json.loads(meta_path.read_text())
            return dict(raw)

        return {"file": file_path, "size_bytes": path.stat().st_size, "placeholder": True}

    def estimate_cost(self, duration: float, model: str | None = None) -> float:
        _ = duration
        _ = model
        return 0.0

    def cancel(self, job: ProviderJob) -> bool:
        job.status = ProviderJobStatus.CANCELLED
        return True
