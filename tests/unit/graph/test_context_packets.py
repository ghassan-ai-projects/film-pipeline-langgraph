"""Tests for phase-scoped prompt context packet builders."""

from __future__ import annotations

from typing import Any

from film_pipeline.graph import context_packets as cp
from film_pipeline.schemas._base import FilmPhase
from film_pipeline.schemas.artifact import ArtifactRef


class FakeArtifactStore:
    def __init__(self, artifacts: dict[str, dict[str, Any]]) -> None:
        self.artifacts = artifacts
        self.calls: list[tuple[str, FilmPhase, str, int]] = []

    def load(
        self,
        project_id: str,
        phase: FilmPhase,
        artifact_id: str,
        version: int,
    ) -> dict[str, Any]:
        self.calls.append((project_id, phase, artifact_id, version))
        if artifact_id not in self.artifacts:
            raise FileNotFoundError(artifact_id)
        return self.artifacts[artifact_id]

    def load_ref(self, project_id: str, ref: str | ArtifactRef) -> dict[str, Any]:
        parsed = ref if isinstance(ref, ArtifactRef) else ArtifactRef.from_string(ref)
        phase = FilmPhase(parsed.phase) if parsed.phase else FilmPhase("intake")
        return self.load(project_id, phase, parsed.artifact_id, parsed.version)


class FakeServices:
    def __init__(self, artifacts: dict[str, dict[str, Any]]) -> None:
        self.artifact_store = FakeArtifactStore(artifacts)


def test_constitution_context_uses_state_only() -> None:
    rendered = cp.build_constitution_context(
        {
            "project_id": "p1",
            "idea": "A memory film.",
            "film_type": "short_drama",
            "target_runtime_seconds": 300,
        }
    )

    assert rendered == (
        "Film idea: A memory film.\nFilm type: short_drama\nTarget runtime: 300s\nProject ID: p1"
    )


def test_development_context_loads_constitution_summary() -> None:
    services = FakeServices({"constitution": {"theme": "Memory", "tone": "quiet"}})

    rendered = cp.build_development_context(
        {
            "project_id": "p1",
            "constitution_ref": "artifact:constitution:constitution:v1",
            "target_runtime_seconds": 240,
            "film_type": "short",
        },
        services,
    )

    assert "Constitution theme: Memory" in rendered
    assert "Tone: quiet" in rendered
    assert "Target runtime: 240s | Film type: short" in rendered


def test_script_context_summarizes_treatment_and_scene_count() -> None:
    services = FakeServices(
        {
            "treatment": {"themes": ["memory", "loss"], "act_map": {"act_1": "setup"}},
            "scene_list": {"scenes": [{"scene_id": "s1"}, {"scene_id": "s2"}]},
        }
    )

    rendered = cp.build_script_context(
        {
            "project_id": "p1",
            "treatment_ref": "artifact:development:treatment:v1",
            "scene_list_ref": "artifact:development:scene_list:v1",
        },
        services,
    )

    assert "Treatment themes: memory, loss" in rendered
    assert "Act structure: ['act_1']" in rendered
    assert "Scene count: 2" in rendered


def test_visual_dev_context_summarizes_style_and_script_count() -> None:
    services = FakeServices(
        {
            "constitution": {
                "visual_language": "static frames",
                "camera_philosophy": "patient",
            },
            "script": {"scenes": [{}, {}, {}]},
        }
    )

    rendered = cp.build_visual_dev_context(
        {
            "project_id": "p1",
            "constitution_ref": "artifact:constitution:constitution:v1",
            "script_ref": "artifact:script:script:v1",
            "target_runtime_seconds": 180,
            "film_type": "micro",
        },
        services,
    )

    assert "Visual language: static frames" in rendered
    assert "Camera philosophy: patient" in rendered
    assert "Script scenes: 3" in rendered
    assert "Target runtime: 180s | Film type: micro" in rendered


def test_shot_bible_context_summarizes_execution_brief_and_script() -> None:
    services = FakeServices(
        {
            "execution_brief": {
                "target_runtime_seconds": 120,
                "pacing_style": "measured",
                "movements": [
                    {
                        "movement_id": "act_1",
                        "shot_count": 4,
                        "duration_range_seconds": [8, 10],
                    }
                ],
                "mandatory_anchors": ["opening image"],
                "environment_progression": ["room"],
            },
            "script": {"scenes": [{}, {}]},
        }
    )

    rendered = cp.build_shot_bible_context(
        {
            "project_id": "p1",
            "execution_brief_ref": "artifact:shot_bible:execution_brief:v1",
            "script_ref": "artifact:script:script:v1",
        },
        services,
    )

    assert "Execution brief - 120s, measured" in rendered.replace("—", "-")
    assert "act_1: 4 shots ([8, 10])" in rendered
    assert "Mandatory anchors: ['opening image']" in rendered
    assert "Script has 2 scenes across 3 acts" in rendered


def test_gen_planning_context_summarizes_matrix_rows_and_budget() -> None:
    services = FakeServices(
        {
            "shot_matrix": {
                "rows": [
                    {"act_id": "act_2"},
                    {"act_id": "act_1"},
                    {"act_id": "act_2"},
                ]
            }
        }
    )

    rendered = cp.build_gen_planning_context(
        {
            "project_id": "p1",
            "shot_matrix_ref": "artifact:shot_bible:shot_matrix:v1",
            "budget_snapshot": {"cap_usd": 42},
        },
        services,
    )

    assert "Shot matrix: 3 rows across 2 acts" in rendered
    assert "  act_1: 1 rows" in rendered
    assert "  act_2: 2 rows" in rendered
    assert "Budget cap: $42" in rendered


def test_load_ref_returns_none_for_malformed_missing_or_unresolved_refs() -> None:
    services = FakeServices({})
    state = {"project_id": "p1"}

    assert cp._load_ref(state, services, "") is None
    assert cp._load_ref(state, services, "artifact:x:vbad") is None
    assert cp._load_ref(state, services, "artifact:x:v1") is None


def test_phase_builder_registry_contains_expected_builders() -> None:
    assert cp.PHASE_BUILDERS["intake"] is cp.build_constitution_context
    assert cp.PHASE_BUILDERS["constitution"] is cp.build_constitution_context
    assert cp.PHASE_BUILDERS["development"] is cp.build_development_context
    assert cp.PHASE_BUILDERS["script"] is cp.build_script_context
    assert cp.PHASE_BUILDERS["visual_dev"] is cp.build_visual_dev_context
    assert cp.PHASE_BUILDERS["shot_bible"] is cp.build_shot_bible_context
    assert cp.PHASE_BUILDERS["gen_planning"] is cp.build_gen_planning_context
