"""Tests for the InProcessStudioGateway delegations left uncovered by
test_inprocess_gateway.py: runtime mode, validation runs, and generation."""

from __future__ import annotations

from typing import Any

from film_pipeline.app.services.models import (
    GenerationWorkspace,
    ValidationWorkspace,
)
from film_pipeline.tui.gateways.inprocess import InProcessStudioGateway


class RecordingService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def _record(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append((name, args, kwargs))

    def set_runtime_mode(self, mode: str) -> str:
        self._record("set_runtime_mode", mode)
        return "real"

    def run_validation(self, project_id: str | None = None) -> ValidationWorkspace:
        self._record("run_validation", project_id)
        return ValidationWorkspace(
            project_id=project_id or "p1",
            phase="script",
            source="fresh_run",
            reports=[{"validator_id": "structure", "score": 88}],
        )

    def get_generation_workspace(self, project_id: str | None = None) -> GenerationWorkspace:
        self._record("get_generation_workspace", project_id)
        return GenerationWorkspace(
            project_id=project_id or "p1",
            phase="generation",
            provider="mock-video-provider",
            model="mock-fast",
            estimated_cost_usd=0.0,
            rows=[
                {
                    "request_id": "req-1",
                    "shot_id": "shot_SC_001_001",
                    "status": "planned",
                }
            ],
            planned=1,
            next_step="approve_spend",
        )

    def plan_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        self._record("plan_generation", project_id)
        return GenerationWorkspace(
            project_id=project_id or "p1",
            phase="generation",
            provider="mock-video-provider",
            model="mock-fast",
            estimated_cost_usd=3.5,
            rows=[
                {
                    "request_id": "req-1",
                    "shot_id": "shot_SC_001_001",
                    "status": "planned",
                    "estimated_cost_usd": 3.5,
                }
            ],
            planned=1,
            next_step="approve_spend",
        )

    def approve_generation_spend(
        self, project_id: str | None = None, max_cost_usd: float = -1.0
    ) -> GenerationWorkspace:
        self._record("approve_generation_spend", project_id, max_cost_usd)
        return GenerationWorkspace(
            project_id=project_id or "p1",
            phase="generation",
            provider="mock-video-provider",
            model="mock-fast",
            estimated_cost_usd=3.5,
            rows=[
                {
                    "request_id": "req-1",
                    "shot_id": "shot_SC_001_001",
                    "status": "approved",
                    "estimated_cost_usd": 3.5,
                }
            ],
            planned=1,
            next_step="start",
        )

    def start_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        self._record("start_generation", project_id)
        return GenerationWorkspace(
            project_id=project_id or "p1",
            phase="generation",
            provider="mock-video-provider",
            model="mock-fast",
            estimated_cost_usd=3.5,
            rows=[
                {
                    "request_id": "req-1",
                    "shot_id": "shot_SC_001_001",
                    "status": "submitted",
                }
            ],
            planned=1,
            submitted=1,
            next_step="poll",
        )

    def poll_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        self._record("poll_generation", project_id)
        return GenerationWorkspace(
            project_id=project_id or "p1",
            phase="generation",
            provider="mock-video-provider",
            model="mock-fast",
            estimated_cost_usd=3.5,
            rows=[
                {
                    "request_id": "req-1",
                    "shot_id": "shot_SC_001_001",
                    "status": "delivered",
                }
            ],
            planned=1,
            submitted=1,
            completed=1,
            next_step="approve_phase",
        )

    def preview_generation_prompts(self, project_id: str | None = None) -> list[dict[str, object]]:
        self._record("preview_generation_prompts", project_id)
        return [
            {
                "shot_id": "shot_SC_001_001",
                "scene_id": "SC_001",
                "provider": "mock-video-provider",
                "model": "mock-fast",
                "duration_seconds": 8,
                "prompt": "Wide establishing shot.",
            }
        ]


def test_inprocess_gateway_delegates_generation_and_mode_methods() -> None:
    service = RecordingService()
    gateway = InProcessStudioGateway(service)  # type: ignore[arg-type]

    assert gateway.set_runtime_mode("real") == "real"
    refreshed = gateway.run_validation("p1")
    assert refreshed.source == "fresh_run"
    assert refreshed.reports[0]["validator_id"] == "structure"
    assert gateway.get_generation_workspace("p1").next_step == "approve_spend"

    planned = gateway.plan_generation("p1")
    assert planned.rows[0]["status"] == "planned"
    assert planned.estimated_cost_usd == 3.5

    approved = gateway.approve_generation_spend("p1", 12.5)
    assert approved.rows[0]["status"] == "approved"
    assert approved.next_step == "start"

    started = gateway.start_generation("p1")
    assert started.rows[0]["status"] == "submitted"
    assert started.submitted == 1
    assert started.next_step == "poll"

    polled = gateway.poll_generation("p1")
    assert polled.rows[0]["status"] == "delivered"
    assert polled.completed == 1
    assert polled.next_step == "approve_phase"

    previews = gateway.preview_generation_prompts("p1")
    assert len(previews) == 1
    assert previews[0]["shot_id"] == "shot_SC_001_001"
    assert previews[0]["prompt"] == "Wide establishing shot."

    assert [name for name, _args, _kwargs in service.calls] == [
        "set_runtime_mode",
        "run_validation",
        "get_generation_workspace",
        "plan_generation",
        "approve_generation_spend",
        "start_generation",
        "poll_generation",
        "preview_generation_prompts",
    ]


def test_inprocess_gateway_forwards_arguments_to_the_service() -> None:
    service = RecordingService()
    gateway = InProcessStudioGateway(service)  # type: ignore[arg-type]

    gateway.set_runtime_mode("mock")
    gateway.run_validation()
    gateway.get_generation_workspace("p2")
    gateway.plan_generation()
    gateway.approve_generation_spend("p3", 7.25)
    gateway.approve_generation_spend(max_cost_usd=9.0)
    gateway.preview_generation_prompts()

    assert service.calls == [
        ("set_runtime_mode", ("mock",), {}),
        ("run_validation", (None,), {}),
        ("get_generation_workspace", ("p2",), {}),
        ("plan_generation", (None,), {}),
        ("approve_generation_spend", ("p3", 7.25), {}),
        ("approve_generation_spend", (None, 9.0), {}),
        ("preview_generation_prompts", (None,), {}),
    ]
