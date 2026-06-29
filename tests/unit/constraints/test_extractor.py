"""Unit tests for deterministic constraint extraction."""

from __future__ import annotations

from film_pipeline.constraints.extractor import extract_constraints
from film_pipeline.schemas._base import FilmType


def test_extract_runtime_minutes() -> None:
    idea = "A 4 minute short film about a robot learning to paint."
    result = extract_constraints(idea, project_id="p1")
    assert result.target_runtime_seconds == 240


def test_extract_runtime_seconds() -> None:
    idea = "A 90 second commercial for a coffee brand."
    result = extract_constraints(idea, project_id="p1")
    assert result.target_runtime_seconds == 90


def test_extract_runtime_timestamp() -> None:
    idea = "A 2:30 experimental film about light."
    result = extract_constraints(idea, project_id="p1")
    assert result.target_runtime_seconds == 150


def test_extract_scene_count() -> None:
    idea = "A narrative short with 8 scenes set in Paris."
    result = extract_constraints(idea, project_id="p1")
    assert result.target_scene_count == 8


def test_extract_scene_count_words() -> None:
    idea = "A drama told in twelve scenes."
    result = extract_constraints(idea, project_id="p1")
    assert result.target_scene_count == 12


def test_extract_shot_count() -> None:
    idea = "A dynamic action trailer with 24 shots."
    result = extract_constraints(idea, project_id="p1")
    assert result.target_shot_count == 24


def test_extract_film_type() -> None:
    idea = "A visual poetry piece about autumn."
    result = extract_constraints(idea, project_id="p1")
    assert result.film_type == FilmType.VISUAL_POETRY


def test_extract_pacing() -> None:
    idea = "A slow cinema meditation on grief."
    result = extract_constraints(idea, project_id="p1")
    assert result.pacing_style == "slow_cinema"


def test_extract_tone_and_genre() -> None:
    idea = "A dark sci-fi thriller for adults."
    result = extract_constraints(idea, project_id="p1")
    assert result.tone == "dark"
    assert result.genre == "sci-fi"
    assert result.target_audience == "adults"


def test_extract_visual_style() -> None:
    idea = "A noir mystery with grainy black-and-white cinematography."
    result = extract_constraints(idea, project_id="p1")
    assert result.visual_style == "noir"


def test_extract_rating() -> None:
    idea = "A family-friendly PG animated short."
    result = extract_constraints(idea, project_id="p1")
    assert result.rating == "PG"


def test_extract_themes() -> None:
    idea = "Themes: love, betrayal, redemption. A story about two friends."
    result = extract_constraints(idea, project_id="p1")
    assert result.themes == ["love", "betrayal", "redemption"]


def test_extract_language() -> None:
    idea = "A French dialogue short set in Lyon."
    result = extract_constraints(idea, project_id="p1")
    assert result.dialogue_language == "French"


def test_extract_budget() -> None:
    idea = "Keep the budget under $500 for this social clip."
    result = extract_constraints(idea, project_id="p1")
    assert result.budget_cap_usd == 500


def test_extract_delivery_modes() -> None:
    idea = "Deliver as mp4 and mov for the festival."
    result = extract_constraints(idea, project_id="p1")
    assert sorted(result.delivery_modes) == ["mov", "mp4"]


def test_extract_forbidden_topics() -> None:
    idea = "A hopeful story with no violence or profanity."
    result = extract_constraints(idea, project_id="p1")
    assert "violence" in result.forbidden_topics
    assert "profanity" in result.forbidden_topics


def test_extract_required_elements() -> None:
    idea = "Must include a red balloon and a piano solo."
    result = extract_constraints(idea, project_id="p1")
    assert "a red balloon" in result.required_elements
    assert "a piano solo" in result.required_elements


def test_extract_locations() -> None:
    idea = "A comedy set in a small bookstore in Tokyo."
    result = extract_constraints(idea, project_id="p1")
    assert "a small bookstore in Tokyo" in result.locations


def test_extract_character_constraints() -> None:
    idea = "The protagonist must be a child under 10."
    result = extract_constraints(idea, project_id="p1")
    assert "be a child under 10" in result.character_constraints


def test_extract_target_phase() -> None:
    idea = "Run up to shot_bible for now."
    result = extract_constraints(idea, project_id="p1")
    assert result.target_phase == "shot_bible"


def test_hints_override_extraction() -> None:
    idea = "A 2 minute film."
    result = extract_constraints(
        idea,
        project_id="p1",
        hints={"target_runtime_seconds": 300, "tone": "melancholic"},
    )
    assert result.target_runtime_seconds == 300
    assert result.tone == "melancholic"


def test_hints_merge_lists() -> None:
    idea = "Themes: friendship."
    result = extract_constraints(
        idea,
        project_id="p1",
        hints={"themes": ["adventure"]},
    )
    assert result.themes == ["friendship", "adventure"]


def test_project_id_is_preserved() -> None:
    result = extract_constraints("A short film.", project_id="my-project")
    assert result.project_id == "my-project"
