"""P5 readability tests: renderers, README, deliverables-on-approve (D9)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from film_pipeline.devharness.storage import make_store
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.storage.rendering import (
    render_bible,
    render_scene_list,
    render_script,
    render_validation_report,
)


def _meta(artifact_id: str, artifact_type: Any, phase: Any) -> ArtifactMetadata:

    return ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        project_id="p1",
        phase=phase,
        version=1,
        created_by="test",
        created_at=datetime.now(UTC),
    )


class TestRenderers:
    def test_script_renders_screenplay_style(self) -> None:
        markdown = render_script(
            {
                "title": "The Test",
                "scenes": [
                    {
                        "scene_id": "SC_001",
                        "scene_heading": "INT. LAB — NIGHT",
                        "action_lines": ["She stares at the tank."],
                        "dialogue": [
                            {
                                "character_id": "MARA",
                                "direction": "whispering",
                                "line": "It came early.",
                            }
                        ],
                    }
                ],
            }
        )
        assert "**Title:** The Test" in markdown
        assert "### INT. LAB — NIGHT" in markdown
        assert "She stares at the tank." in markdown
        assert "**MARA** (whispering): It came early." in markdown

    def test_scene_list_renders_table(self) -> None:
        markdown = render_scene_list(
            {
                "scene_list": {
                    "scenes": [
                        {
                            "scene_id": "SC_001",
                            "dramatic_function": "setup",
                            "story_function": "plant the message",
                            "outcome": "note found",
                        }
                    ]
                }
            }
        )
        assert "## Scenes" in markdown
        assert "| SC_001 | setup | plant the message | note found |" in markdown

    def test_validation_report_renders_real_fields(self) -> None:
        markdown = render_validation_report(
            {
                "validator_id": "clip-validator",
                "score": 40.0,
                "status": "needs_revision",
                "blocking_issues": [{"severity": "blocking", "message": "clip drifts from brief"}],
                "warnings": [{"severity": "warning", "message": "audio low"}],
                "recommended_actions": ["regenerate shot_0001"],
            }
        )
        assert "## Blocking Issues" in markdown
        assert "- [blocking] clip drifts from brief" in markdown
        assert "## Warnings" in markdown
        assert "## Recommended Actions" in markdown
        assert "- regenerate shot_0001" in markdown

    def test_bible_renders_sections(self) -> None:
        markdown = render_bible(
            {
                "project_id": "p1",
                "name": "Mara",
                "want": "To be seen",
                "signature_props": ["the note"],
            }
        )
        assert "**Name:** Mara" in markdown
        assert "**Want:** To be seen" in markdown
        assert "- the note" in markdown
        assert "schema_version" not in markdown


class TestReadmeContent:
    def test_readme_lists_phase_and_links(self, tmp_path: Path) -> None:
        from film_pipeline.schemas._base import ArtifactType, FilmPhase
        from film_pipeline.schemas.script import Script

        root = tmp_path / "store"
        store = make_store(root)
        store.save(
            Script(project_id="p1", title="T", scenes=[]),
            _meta("script", ArtifactType.SCRIPT, FilmPhase.SCRIPT),
        )
        readme = (root / "p1" / "README.md").read_text()
        assert "## Artifacts (current versions)" in readme
        assert "[script](artifacts/03-script/script/current.md)" in readme
        assert "v1" in readme

    def test_readme_regen_records_deliverables_on_approve(self, tmp_path: Path) -> None:
        from film_pipeline.schemas._base import ArtifactType, FilmPhase
        from film_pipeline.schemas.script import Script

        root = tmp_path / "store"
        store = make_store(root)
        store.save(
            Script(project_id="p1", title="T", scenes=[]),
            _meta("script", ArtifactType.SCRIPT, FilmPhase.SCRIPT),
        )
        store.approve("p1", "script", "script", 1, approval_ref="approval:x")
        deliverables = root / "p1" / "deliverables"
        assert (deliverables / "script-script.md").exists()
        assert "## Deliverables" in (root / "p1" / "README.md").read_text()
        # The human view copied into deliverables matches the artifact view.
        assert (deliverables / "script-script.md").read_text() == (
            root / "p1/artifacts/03-script/script/current.md"
        ).read_text()


class TestDeliverablesOnApprove:
    def test_approve_phase_marks_artifacts_approved_and_fills_deliverables(
        self, tmp_path: Path
    ) -> None:
        """D9's named test: the human gate fills deliverables/ and approves."""
        from film_pipeline.app.runtime import StudioRuntime
        from film_pipeline.orchestration.services import GraphServices
        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
        from film_pipeline.schemas.artifact import ArtifactMetadata
        from film_pipeline.schemas.script import Script
        from film_pipeline.storage.store import ArtifactStore

        projects_root = tmp_path / "projects"
        rt = StudioRuntime(
            server_mode="mock",
            runtime_root=tmp_path / "runtime",
            services=GraphServices(artifact_store=ArtifactStore(root=projects_root)),
        )
        rt.create_project("p1", title="Deliver")
        rt.set_active("p1")
        assert rt.services is not None
        rt.services.artifact_store.save(
            Script(project_id="p1", title="T", scenes=[]),
            ArtifactMetadata(
                artifact_id="script",
                artifact_type=ArtifactType.SCRIPT,
                project_id="p1",
                phase=FilmPhase.SCRIPT,
                version=1,
                created_by="test",
                created_at=datetime.now(UTC),
            ),
        )
        state = rt.get_active()
        assert state is not None
        state["current_phase"] = "script"
        rt.projects["p1"] = state

        from film_pipeline.app._graph_exec import _approve_phase_artifacts

        _approve_phase_artifacts(rt, "p1", "script")

        listed = rt.services.artifact_store.list_artifacts("p1", FilmPhase.SCRIPT)
        assert listed
        assert all(m.status == ArtifactStatus.APPROVED for m in listed)
        assert all(m.approval_ref for m in listed)

        deliverables = sorted(p.name for p in (projects_root / "p1" / "deliverables").glob("*"))
        assert "README.md" in deliverables
        assert "script-script.md" in deliverables
