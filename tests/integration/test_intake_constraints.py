"""Integration test for constraints extraction via MCP submit_idea."""

from __future__ import annotations

import asyncio

import pytest

from film_pipeline.mcp.tools import (
    create_film_project,
    set_active_project,
    submit_idea,
)
from film_pipeline.schemas._base import FilmPhase


@pytest.mark.integration
class TestIntakeConstraints:
    """End-to-end constraints extraction and persistence."""

    def setup_method(self) -> None:
        from film_pipeline.studio.runtime import get_runtime, reset_runtime

        reset_runtime("mock")
        rt = get_runtime()
        rt.projects.clear()
        rt.active_project_id = ""

    def test_submit_idea_with_constraints_creates_artifact(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                create_film_project({"project_id": "constraints-01", "title": "Constraints Test"})
            )
            loop.run_until_complete(set_active_project({"project_ref": "constraints-01"}))
            result = loop.run_until_complete(
                submit_idea(
                    {
                        "idea": (
                            "A dark 3 minute sci-fi short with 6 scenes, "
                            "no violence, themes: isolation."
                        ),
                        "constraints": {
                            "target_audience": "adults",
                            "forbidden_topics": ["profanity"],
                        },
                    }
                )
            )
            assert result["ok"] is True

            rt = __import__("film_pipeline.studio.runtime", fromlist=["get_runtime"]).get_runtime()
            state = rt.get_project("constraints-01")
            assert state is not None
            assert state["constraints_ref"] == "artifact:intake:project_constraints:v1"
            constraints = state["constraints"]
            assert constraints["target_runtime_seconds"] == 180
            assert constraints["target_scene_count"] == 6
            assert constraints["tone"] == "dark"
            assert constraints["genre"] == "sci-fi"
            assert "violence" in constraints["forbidden_topics"]
            assert "profanity" in constraints["forbidden_topics"]
            assert constraints["target_audience"] == "adults"

            # Artifact persisted.
            artifact = rt.services.artifact_store.load(
                "constraints-01", FilmPhase("intake"), "project_constraints", 1
            )
            assert artifact["target_runtime_seconds"] == 180
        finally:
            loop.close()
