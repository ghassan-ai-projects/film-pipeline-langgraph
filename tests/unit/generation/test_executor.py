"""Tests for GenerationExecutor."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from film_pipeline.generation.executor import GenerationExecutor, GenerationStepResult
from film_pipeline.providers.base import BaseProviderAdapter, ProviderJob, ProviderJobStatus
from film_pipeline.providers.mock_provider import MockVideoProvider
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.schemas.base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.schemas.registries.provider_registry import (
    CostProfile,
    ProviderCapabilities,
    ProviderRegistryEntry,
)
from film_pipeline.storage.store import ArtifactStore


class ShotMatrix(BaseModel):
    rows: list[dict[str, Any]]


class PromptPackage(BaseModel):
    entries: list[dict[str, Any]]


class ShotBible(BaseModel):
    shots: list[dict[str, Any]]


@pytest.fixture
def entry() -> ProviderRegistryEntry:
    return ProviderRegistryEntry(
        provider_id="mock-video-provider",
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


def _save_shot_matrix(store: ArtifactStore, project_id: str) -> None:
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
                    "characters": ["Wanderer"],
                    "environment": "forest clearing",
                },
                {
                    "shot_id": "S002",
                    "scene_id": "SC01",
                    "duration_seconds": 3,
                    "story_function": "Footsteps crunch on dry leaves.",
                    "camera_profile": "detail-texture",
                    "lighting_state": "overcast-morning",
                    "environment_state": "forest path",
                    "characters": [],
                    "environment": "forest path",
                },
            ]
        ),
        ArtifactMetadata(
            artifact_id="shot_matrix",
            artifact_type=ArtifactType.SHOT_BIBLE,
            project_id=project_id,
            phase=FilmPhase.SHOT_BIBLE,
            version=1,
            status=ArtifactStatus.APPROVED,
            created_by="test",
            created_at=datetime.now(UTC),
        ),
    )


def _save_prompt_package(store: ArtifactStore, project_id: str) -> None:
    store.save(
        PromptPackage(
            entries=[
                {
                    "shot_id": "S001",
                    "rendered_prompt": "Rendered lantern prompt.",
                }
            ]
        ),
        ArtifactMetadata(
            artifact_id="prompt_package",
            artifact_type=ArtifactType.PROMPT_PACKAGE,
            project_id=project_id,
            phase=FilmPhase.GEN_PLANNING,
            version=1,
            status=ArtifactStatus.APPROVED,
            created_by="test",
            created_at=datetime.now(UTC),
        ),
    )


class TestGenerationExecutor:
    def test_plan_raises_when_no_shots(self, store: ArtifactStore) -> None:
        executor = GenerationExecutor(store, providers={})
        with pytest.raises(ValueError, match="No shots to plan"):
            executor.plan("proj", provider="mock-video-provider", model="mock-fast")

    def test_plan_from_shot_matrix(self, store: ArtifactStore) -> None:
        _save_shot_matrix(store, "proj")
        executor = GenerationExecutor(store, providers={})
        result = executor.plan("proj", provider="mock-video-provider", model="mock-fast")
        assert result.processed == 2
        assert result.details[0]["shot_id"] == "S001"
        assert executor.shot_ids("proj") == ["S001", "S002"]

    def test_plan_idempotent(self, store: ArtifactStore) -> None:
        _save_shot_matrix(store, "proj")
        executor = GenerationExecutor(store, providers={})
        executor.plan("proj", provider="mock-video-provider", model="mock-fast")
        result = executor.plan("proj", provider="mock-video-provider", model="mock-fast")
        assert result.processed == 2
        assert len(executor.status_rows("proj")) == 2

    def test_plan_with_explicit_shot_ids(self, store: ArtifactStore) -> None:
        _save_shot_matrix(store, "proj")
        executor = GenerationExecutor(store, providers={})
        result = executor.plan(
            "proj",
            provider="mock-video-provider",
            model="mock-fast",
            shot_ids=["S001"],
        )
        assert result.processed == 1

    def test_approve_spend_transitions_rows(self, store: ArtifactStore) -> None:
        _save_shot_matrix(store, "proj")
        executor = GenerationExecutor(store, providers={})
        executor.plan("proj", provider="mock-video-provider", model="mock-fast")
        result = executor.approve_spend("proj")
        assert result.processed == 2
        assert result.running == 2
        statuses = {r["status"] for r in executor.status_rows("proj")}
        assert statuses == {"submitted"}

    def test_start_submits_jobs(self, store: ArtifactStore, entry: ProviderRegistryEntry) -> None:
        _save_shot_matrix(store, "proj")
        executor = GenerationExecutor(
            store, providers={"mock-video-provider": MockVideoProvider(entry=entry)}
        )
        executor.plan("proj", provider="mock-video-provider", model="mock-fast")
        executor.approve_spend("proj")
        result = executor.start("proj")
        assert result.processed == 2
        assert result.running == 2
        assert all(d["provider_job_id"] for d in result.details)

    def test_start_skips_already_running(
        self, store: ArtifactStore, entry: ProviderRegistryEntry
    ) -> None:
        _save_shot_matrix(store, "proj")
        executor = GenerationExecutor(
            store, providers={"mock-video-provider": MockVideoProvider(entry=entry)}
        )
        executor.plan("proj", provider="mock-video-provider", model="mock-fast")
        executor.approve_spend("proj")
        executor.start("proj")
        result = executor.start("proj")
        # All rows are already RUNNING, so there is nothing left to submit.
        assert result.processed == 0
        assert result.running == 0
        assert result.failed == 0

    def test_start_unknown_provider_fails(self, store: ArtifactStore) -> None:
        _save_shot_matrix(store, "proj")
        executor = GenerationExecutor(store, providers={})
        executor.plan("proj", provider="unknown", model="m")
        executor.approve_spend("proj")
        result = executor.start("proj")
        assert result.processed == 2
        assert result.failed == 2
        assert result.running == 0

    def test_poll_once_completes(self, store: ArtifactStore, entry: ProviderRegistryEntry) -> None:
        _save_shot_matrix(store, "proj")
        executor = GenerationExecutor(
            store, providers={"mock-video-provider": MockVideoProvider(entry=entry)}
        )
        executor.plan("proj", provider="mock-video-provider", model="mock-fast")
        executor.approve_spend("proj")
        executor.start("proj")
        result = executor.poll_once("proj")
        assert result.processed == 2
        assert result.completed == 2
        assert result.running == 0
        rows = executor.status_rows("proj")
        assert all(r["status"] == "completed" for r in rows)
        assert all(r["output"] for r in rows)

    def test_poll_once_failed_status(
        self, store: ArtifactStore, entry: ProviderRegistryEntry
    ) -> None:
        _save_shot_matrix(store, "proj")
        reg_entry = entry

        class FailAdapter(BaseProviderAdapter):
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
                    job_id="fail-1",
                    shot_id=shot_id,
                    provider_id="fail-provider",
                    model="m",
                )

            def poll(self, job: ProviderJob) -> ProviderJob:
                job.status = ProviderJobStatus.FAILED
                job.metadata = {"error": "mock_failure"}
                return job

            def download(self, job: ProviderJob, output_dir: str) -> str:
                return ""

            def extract_metadata(self, file_path: str) -> dict[str, Any]:
                return {}

            def estimate_cost(self, duration: float, model: str | None = None) -> float:
                return 0.0

        executor = GenerationExecutor(
            store,
            providers={"fail-provider": FailAdapter(entry=reg_entry)},
        )
        executor.plan("proj", provider="fail-provider", model="m")
        executor.approve_spend("proj")
        executor.start("proj")
        result = executor.poll_once("proj")
        assert result.processed == 2
        assert result.failed == 2
        assert executor.status_rows("proj")[0]["status"] == "failed"

    def test_status_rows_and_ledger_absent(self, store: ArtifactStore) -> None:
        executor = GenerationExecutor(store, providers={})
        assert executor.status_rows("proj") == []
        assert not executor.has_ledger("proj")

    def test_dispatchable_requests(self, store: ArtifactStore) -> None:
        _save_shot_matrix(store, "proj")
        executor = GenerationExecutor(store, providers={})
        executor.plan(
            "proj",
            provider="mock-video-provider",
            model="mock-fast",
            shot_ids=["S001"],
        )
        requests = executor.dispatchable_requests("proj")
        assert len(requests) == 1
        assert requests[0]["shot_id"] == "S001"
        assert requests[0]["status"] == "prepared"

    def test_resolve_prompt_rendered(self, store: ArtifactStore) -> None:
        _save_shot_matrix(store, "proj")
        _save_prompt_package(store, "proj")
        executor = GenerationExecutor(store, providers={})
        prompt = executor.resolve_prompt("proj", "S001", {}, "prompt_package")
        assert prompt == "Rendered lantern prompt."

    def test_resolve_prompt_structured(self, store: ArtifactStore) -> None:
        _save_shot_matrix(store, "proj")
        executor = GenerationExecutor(store, providers={})
        shot_row = executor.load_shot_rows("proj")[0]
        prompt = executor.resolve_prompt("proj", "S001", shot_row)
        assert "lantern" in prompt.lower()

    def test_resolve_prompt_fallback(self, store: ArtifactStore) -> None:
        executor = GenerationExecutor(store, providers={})
        prompt = executor.resolve_prompt("proj", "S001", {})
        assert "S001" in prompt
        assert "proj" in prompt

    def test_result_done_property(self) -> None:
        assert GenerationStepResult(running=0).done is True
        assert GenerationStepResult(running=2).done is False

    def test_start_submit_exception(
        self, store: ArtifactStore, entry: ProviderRegistryEntry
    ) -> None:
        _save_shot_matrix(store, "proj")
        reg_entry = entry

        class SubmitErrorAdapter(BaseProviderAdapter):
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
                raise RuntimeError("submit exploded")

            def poll(self, job: ProviderJob) -> ProviderJob:
                return job

            def download(self, job: ProviderJob, output_dir: str) -> str:
                return ""

            def extract_metadata(self, file_path: str) -> dict[str, Any]:
                return {}

            def estimate_cost(self, duration: float, model: str | None = None) -> float:
                return 0.0

        executor = GenerationExecutor(
            store,
            providers={"error-provider": SubmitErrorAdapter(entry=reg_entry)},
        )
        executor.plan("proj", provider="error-provider", model="m")
        executor.approve_spend("proj")
        result = executor.start("proj")
        assert result.processed == 2
        assert result.failed == 2
        assert "submit exploded" in result.details[0]["error"]

    def test_poll_once_poll_exception(
        self, store: ArtifactStore, entry: ProviderRegistryEntry
    ) -> None:
        _save_shot_matrix(store, "proj")
        reg_entry = entry

        class PollErrorAdapter(BaseProviderAdapter):
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
                    job_id="poll-err-1",
                    shot_id=shot_id,
                    provider_id="poll-error-provider",
                    model="m",
                )

            def poll(self, job: ProviderJob) -> ProviderJob:
                raise RuntimeError("poll exploded")

            def download(self, job: ProviderJob, output_dir: str) -> str:
                return ""

            def extract_metadata(self, file_path: str) -> dict[str, Any]:
                return {}

            def estimate_cost(self, duration: float, model: str | None = None) -> float:
                return 0.0

        executor = GenerationExecutor(
            store,
            providers={"poll-error-provider": PollErrorAdapter(entry=reg_entry)},
        )
        executor.plan("proj", provider="poll-error-provider", model="m")
        executor.approve_spend("proj")
        executor.start("proj")
        result = executor.poll_once("proj")
        assert result.processed == 2
        assert result.failed == 2
        assert "poll exploded" in result.details[0]["error"]

    def test_load_shot_bible_legacy(self, store: ArtifactStore) -> None:
        store.save(
            ShotBible(shots=[{"shot_id": "SB01", "scene_id": "SC01"}]),
            ArtifactMetadata(
                artifact_id="shot_bible",
                artifact_type=ArtifactType.SHOT_BIBLE,
                project_id="proj",
                phase=FilmPhase.SHOT_BIBLE,
                version=1,
                status=ArtifactStatus.APPROVED,
                created_by="test",
                created_at=datetime.now(UTC),
            ),
        )
        executor = GenerationExecutor(store, providers={})
        rows = executor.load_shot_rows("proj")
        assert len(rows) == 1
        assert rows[0]["shot_id"] == "SB01"
