"""Unit tests for the ProjectConstraints schema and renderer."""

from __future__ import annotations

import pytest

from film_pipeline.schemas.base import FilmType
from film_pipeline.schemas.constraints import ProjectConstraints, render_constraints


def test_empty_constraints_omits_none_values() -> None:
    pc = ProjectConstraints(project_id="p1")
    data = pc.model_dump(mode="json", exclude_none=True, exclude_defaults=True)
    assert data.get("project_id") == "p1"
    assert "target_runtime_seconds" not in data
    assert "themes" not in data


def test_constraints_round_trip() -> None:
    pc = ProjectConstraints(
        project_id="p1",
        target_runtime_seconds=240,
        target_scene_count=12,
        film_type=FilmType.NARRATIVE,
        pacing_style="standard",
        tone="dark",
        themes=["loss", "redemption"],
        forbidden_topics=["violence"],
    )
    loaded = ProjectConstraints(**pc.model_dump(mode="json"))
    assert loaded.target_runtime_seconds == 240
    assert loaded.target_scene_count == 12
    assert loaded.film_type == FilmType.NARRATIVE
    assert loaded.themes == ["loss", "redemption"]


def test_render_constraints_skips_empty_values() -> None:
    pc = ProjectConstraints(
        project_id="p1",
        target_runtime_seconds=120,
        tone="hopeful",
    )
    rendered = render_constraints(pc)
    assert "=== PROJECT CONSTRAINTS ===" in rendered
    assert "Target Runtime Seconds: 120" in rendered
    assert "Tone: hopeful" in rendered
    assert "Target Scene Count" not in rendered


def test_render_constraints_lists() -> None:
    pc = ProjectConstraints(
        project_id="p1",
        themes=["love", "loss"],
        forbidden_topics=["violence", "profanity"],
    )
    rendered = render_constraints(pc)
    assert "Themes: love, loss" in rendered
    assert "Forbidden Topics: violence, profanity" in rendered


def test_render_constraints_empty() -> None:
    assert render_constraints(None) == ""
    assert render_constraints(ProjectConstraints(project_id="p1")) == ""


def test_render_constraints_accepts_dict() -> None:
    rendered = render_constraints({"target_runtime_seconds": 60, "tone": "comedic"})
    assert "Target Runtime Seconds: 60" in rendered
    assert "Tone: comedic" in rendered


def test_invalid_runtime_rejected() -> None:
    with pytest.raises(ValueError):
        ProjectConstraints(project_id="p1", target_runtime_seconds=0)
