"""Tests for constraints propagation through graph nodes."""

from __future__ import annotations

from typing import Any

from pytest import MonkeyPatch

from film_pipeline.app.mock_responses import default_mock_responses
from film_pipeline.graph.nodes import _run_agent, intake_node
from film_pipeline.graph.services import SERVICES_KEY, GraphServices
from film_pipeline.schemas._base import FilmPhase


def test_intake_node_extracts_constraints_and_persists_artifact(
    tmp_path: Any,
) -> None:
    services = GraphServices.for_mock_runtime(
        artifacts_root=str(tmp_path / "artifacts"), mock_responses=default_mock_responses()
    )
    state: dict[str, Any] = {
        "project_id": "p1",
        "idea": (
            "A dark 4 minute sci-fi thriller with 8 scenes, no violence, "
            "themes: isolation, technology."
        ),
        "constraints_hints": {"target_audience": "adults"},
        SERVICES_KEY: services,
    }

    updates = intake_node(state)

    assert updates["constraints_ref"].startswith("artifact:intake:project_constraints:")
    constraints = updates["constraints"]
    assert constraints["target_runtime_seconds"] == 240
    assert constraints["target_scene_count"] == 8
    assert constraints["tone"] == "dark"
    assert constraints["genre"] == "sci-fi"
    assert constraints["themes"] == ["isolation", "technology"]
    assert "violence" in constraints["forbidden_topics"]
    assert constraints["target_audience"] == "adults"

    # Artifact is loadable.
    artifact = services.artifact_store.load("p1", FilmPhase("intake"), "project_constraints", 1)
    assert artifact["target_runtime_seconds"] == 240


def test_intake_node_constraints_seed_scene_count_for_scope_contract(
    tmp_path: Any,
) -> None:
    services = GraphServices.for_mock_runtime(
        artifacts_root=str(tmp_path / "artifacts"), mock_responses=default_mock_responses()
    )
    state: dict[str, Any] = {
        "project_id": "p1",
        "idea": "A short film with exactly 5 scenes.",
        SERVICES_KEY: services,
    }

    updates = intake_node(state)

    assert updates["target_scene_count"] == 5
    assert updates["min_scene_count"] == 5


def test_run_agent_includes_constraints_in_context_vars(
    tmp_path: Any,
    monkeypatch: MonkeyPatch,
) -> None:
    services = GraphServices.for_mock_runtime(
        artifacts_root=str(tmp_path / "artifacts"), mock_responses=default_mock_responses()
    )
    captured: dict[str, Any] = {}

    original_run_from_template = services.prompt_runner.run_from_template

    def fake_run_from_template(
        template: Any,
        kb: Any,
        task: str,
        *,
        context_vars: dict[str, str],
        model_profile: str,
        agent_id: str,
        model_overrides: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], str, str]:
        captured["context_vars"] = context_vars
        return original_run_from_template(
            template,
            kb,
            task,
            context_vars=context_vars,
            model_profile=model_profile,
            agent_id=agent_id,
            model_overrides=model_overrides,
        )

    monkeypatch.setattr(services.prompt_runner, "run_from_template", fake_run_from_template)

    state: dict[str, Any] = {
        "project_id": "p1",
        "idea": "A hopeful 90 second film.",
        "constraints": {
            "project_id": "p1",
            "target_runtime_seconds": 90,
            "tone": "hopeful",
            "themes": ["friendship"],
        },
        SERVICES_KEY: services,
    }

    _run_agent(
        state,
        agent_id="film-constitution-agent",
        phase="constitution",
        task="Write the constitution.",
    )

    assert "constraints" in captured["context_vars"]
    rendered = captured["context_vars"]["constraints"]
    assert "Target Runtime Seconds: 90" in rendered
    assert "Tone: hopeful" in rendered
    assert "Themes: friendship" in rendered


def test_run_agent_constraints_default_empty_when_absent(
    tmp_path: Any,
    monkeypatch: MonkeyPatch,
) -> None:
    services = GraphServices.for_mock_runtime(
        artifacts_root=str(tmp_path / "artifacts"), mock_responses=default_mock_responses()
    )
    captured: dict[str, Any] = {}

    def fake_run_from_template(
        template: Any,
        kb: Any,
        task: str,
        *,
        context_vars: dict[str, str],
        model_profile: str,
        agent_id: str,
        model_overrides: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], str, str]:
        captured["context_vars"] = context_vars
        return (
            {
                "constitution": {
                    "project_id": "p1",
                    "theme": "identity",
                    "tone": "melancholic",
                    "emotional_promise": "hope",
                    "visual_language": "minimalist",
                    "camera_philosophy": "static",
                    "quality_bar": "studio",
                }
            },
            "template-id",
            model_profile,
        )

    monkeypatch.setattr(services.prompt_runner, "run_from_template", fake_run_from_template)

    state: dict[str, Any] = {
        "project_id": "p1",
        "idea": "A short film.",
        SERVICES_KEY: services,
    }

    _run_agent(
        state,
        agent_id="film-constitution-agent",
        phase="constitution",
        task="Write the constitution.",
    )

    assert captured["context_vars"].get("constraints") == ""
