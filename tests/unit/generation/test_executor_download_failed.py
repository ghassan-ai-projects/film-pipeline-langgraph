"""Pin the executor's ``download_failed`` arm of the completion flow."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from film_pipeline.generation.executor import GenerationExecutor
from film_pipeline.generation.ledger import GenerationLedgerManager
from film_pipeline.providers.base import BaseProviderAdapter, ProviderJob, ProviderJobStatus
from film_pipeline.schemas._base import (
    ArtifactStatus,
    ArtifactType,
    FilmPhase,
    GenerationStatus,
)
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.schemas.registries.provider_registry import (
    CostProfile,
    ProviderCapabilities,
    ProviderRegistryEntry,
)
from film_pipeline.storage.store import ArtifactStore


class ShotMatrix(BaseModel):
    rows: list[dict[str, Any]]


@pytest.fixture
def entry() -> ProviderRegistryEntry:
    return ProviderRegistryEntry(
        provider_id="download-error-provider",
        provider_type="video",
        models=["mock-fast"],
        capabilities=ProviderCapabilities(
            text_to_video=True,
            image_to_video=True,
            return_last_frame=True,
            max_duration_seconds=30,
            aspect_ratios=["16:9"],
            supports_audio=True,
            supports_seed=True,
        ),
        cost_profile=CostProfile(unit="second", estimated_rate_usd=0.0),
    )


@pytest.fixture
def store(tmp_path: Path) -> ArtifactStore:
    return ArtifactStore(root=tmp_path / "projects")


class DownloadErrorAdapter(BaseProviderAdapter):
    """Submits and polls cleanly, then explodes when downloading output."""

    def build_payload(
        self,
        prompt: str,
        references: list[str] | None = None,
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        seed: int | None = None,
    ) -> dict[str, Any]:
        return {}

    def submit(self, payload: dict[str, Any], shot_id: str) -> ProviderJob:
        return ProviderJob(
            job_id="dl-err-1",
            shot_id=shot_id,
            provider_id="download-error-provider",
            model="m",
        )

    def poll(self, job: ProviderJob) -> ProviderJob:
        job.status = ProviderJobStatus.COMPLETED
        return job

    def download(self, job: ProviderJob, output_dir: str) -> str:
        raise RuntimeError("download exploded")

    def extract_metadata(self, file_path: str) -> dict[str, Any]:
        return {}

    def estimate_cost(self, duration: float, model: str | None = None) -> float:
        return 0.0


def test_download_failed_marks_row_failed(
    store: ArtifactStore, entry: ProviderRegistryEntry
) -> None:
    store.save(
        ShotMatrix(
            rows=[
                {
                    "shot_id": "S001",
                    "scene_id": "SC01",
                    "duration_seconds": 5,
                    "story_function": "A lantern flickers in the dark.",
                    "camera_profile": "wide-establishing",
                    "lighting_state": "cool-night",
                    "environment_state": "forest clearing",
                    "characters": [],
                    "environment": "forest clearing",
                }
            ]
        ),
        ArtifactMetadata(
            artifact_id="shot_matrix",
            artifact_type=ArtifactType.SHOT_BIBLE,
            project_id="proj",
            phase=FilmPhase.SHOT_BIBLE,
            version=1,
            status=ArtifactStatus.APPROVED,
            created_by="test",
            created_at=datetime.now(UTC),
        ),
    )
    executor = GenerationExecutor(
        store, providers={"download-error-provider": DownloadErrorAdapter(entry=entry)}
    )
    executor.plan("proj", provider="download-error-provider", model="m")
    executor.approve_spend("proj")
    executor.start("proj")

    result = executor.poll_once("proj")

    assert result.processed == 1
    assert result.completed == 0
    assert result.failed == 1
    assert result.running == 0
    assert result.done is True
    assert result.details == [{"shot_id": "S001", "error": "download exploded"}]

    rows = GenerationLedgerManager(store).list_rows("proj")
    assert len(rows) == 1
    row = rows[0]
    assert row.status is GenerationStatus.FAILED
    assert row.error_code == "download_failed"
    assert row.blocking_reason == "download exploded"
    assert row.next_action == "wait_human"
    assert row.output_refs == []
