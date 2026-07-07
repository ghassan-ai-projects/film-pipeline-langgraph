"""Shot bible generation tool and continuity ledger."""

from __future__ import annotations

from typing import Any, cast

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import _error, _latest_artifact_version, _ok, _services
from ._shared import _extract_script_text


def _generate_continuity_ledger(store: Any, project_id: str, matrix: Any) -> str | None:
    """Generate a basic continuity ledger from the shot matrix."""
    try:
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
        from film_pipeline.schemas.artifact import ArtifactMetadata
        from film_pipeline.schemas.continuity import (
            ContinuityLedger,
            ContinuityLedgerEntry,
            StateRecord,
        )

        entries: list[ContinuityLedgerEntry] = []
        prev_chars: list[str] = []
        prev_env = ""

        for _i, row in enumerate(matrix.rows):
            current_chars = [str(c) for c in row.characters]
            current_env = str(row.environment)
            entries.append(
                ContinuityLedgerEntry(
                    shot_id=row.shot_id,
                    state_in=[
                        StateRecord(
                            label="characters",
                            description=", ".join(prev_chars) if prev_chars else "none",
                            refs=prev_chars,
                        ),
                        StateRecord(
                            label="environment",
                            description=prev_env,
                            refs=[prev_env] if prev_env else [],
                        ),
                    ],
                    action="",
                    state_out=[
                        StateRecord(
                            label="characters",
                            description=", ".join(current_chars) if current_chars else "none",
                            refs=current_chars,
                        ),
                        StateRecord(
                            label="environment",
                            description=current_env,
                            refs=[current_env] if current_env else [],
                        ),
                    ],
                )
            )
            prev_chars = current_chars
            prev_env = current_env

        ledger = ContinuityLedger(
            project_id=project_id,
            entries=entries,
        )
        next_version = (
            _latest_artifact_version(
                store, project_id, FilmPhase("shot_bible"), "continuity_ledger"
            )
            + 1
        )
        meta = ArtifactMetadata(
            artifact_id="continuity_ledger",
            artifact_type=ArtifactType.CONTINUITY_LEDGER,
            project_id=project_id,
            phase=FilmPhase("shot_bible"),
            version=next_version,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_shot_bible",
            created_at=datetime.now(UTC),
        )
        return cast(str, store.save(ledger, meta))
    except Exception:
        return None


async def generate_shot_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate MasterFilmMatrix + ContinuityLedger from Script + visual refs.

    Produces the shot-by-shot production matrix (every clip as a row with
    scene, characters, env, camera, chaining) and a continuity ledger
    tracking state_in/state_out per shot.
    """
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import FilmPhase

        script_data = store.load(project_id, FilmPhase("script"), "script", 1)
        ref_data = store.load(project_id, FilmPhase("visual_dev"), "reference_index", 1)
    except (FileNotFoundError, ValueError) as e:
        return _error(f"Required artifacts not found: {e}")

    script_text = _extract_script_text(script_data)
    ref_summary = ""
    if isinstance(ref_data, dict):
        entries = ref_data.get("entries", [])
        ref_summary = ", ".join(
            f"{e.get('subject_type', '')}/{e.get('subject_id', '')}({e.get('frame_role', '')})"
            for e in entries[:20]
            if isinstance(e, dict)
        )

    try:
        from film_pipeline.agents.impl.shot_bible_agent import ShotBibleAgent
        from film_pipeline.schemas._base import AgentFamily, AgentRole, ArtifactStatus, ArtifactType
        from film_pipeline.schemas.handoff import AgentRegistration

        agent = ShotBibleAgent(
            AgentRegistration(
                agent_id="shot-design-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["shot_design", "matrix_planning"],
                input_artifacts=["script", "visual_refs", "character_bible"],
                output_artifacts=["master_film_matrix"],
            )
        )
        runner = _services(rt).prompt_runner
        model_output: dict[str, Any]
        if runner.model_adapter is not None:
            raw = runner.model_adapter.chat(
                f"Create a MasterFilmMatrix from the script and visual references.\n\n"
                f"Script:\n{script_text[:6000]}\n\n"
                f"Visual references available:\n{ref_summary}\n\n"
                "Return JSON with 'shot_matrix' containing 'rows' array of shot rows "
                "(shot_id, act_id, scene_id, duration_seconds, characters, environment, "
                "camera_profile, priority, risk_level) and 'coverage_groups' array.",
                model=runner.model_router.resolve("creative_writer"),
            )
            model_output = raw if isinstance(raw, dict) else {}
        else:
            model_output = {
                "shot_matrix": {
                    "project_id": project_id,
                    "rows": [
                        {
                            "shot_id": "S001",
                            "act_id": "act1",
                            "scene_id": "scene_01",
                            "duration_seconds": 5,
                            "characters": ["leo"],
                            "environment": "studio",
                            "camera_profile": "default",
                            "priority": "standard",
                            "risk_level": "low",
                            "generation_order": 1,
                        }
                    ],
                    "coverage_groups": [],
                }
            }

        result = agent.execute(model_output)
        if not agent.validate(result):
            return _error("ShotBible agent produced invalid output.")
        matrix = result["shot_matrix"]

        from datetime import UTC, datetime

        from film_pipeline.schemas.artifact import ArtifactMetadata

        next_version = (
            _latest_artifact_version(
                store, project_id, FilmPhase("shot_bible"), "master_film_matrix"
            )
            + 1
        )
        meta = ArtifactMetadata(
            artifact_id="master_film_matrix",
            artifact_type=ArtifactType.MASTER_FILM_MATRIX,
            project_id=project_id,
            phase=FilmPhase("shot_bible"),
            version=next_version,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_shot_bible",
            created_at=datetime.now(UTC),
        )
        ref = store.save(matrix, meta)
        active["shot_matrix_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)

        # Generate a basic continuity ledger from the matrix
        ledger_ref = _generate_continuity_ledger(store, project_id, matrix)

        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(
            shot_matrix_ref=ref,
            shot_count=len(matrix.rows),
            continuity_ledger_ref=ledger_ref,
        )
    except Exception as exc:
        return _error(f"Shot bible generation failed: {exc}")
