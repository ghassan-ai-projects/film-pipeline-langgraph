"""Shot bible generation tool and continuity ledger."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import _error, _latest_artifact_version, _ok, _services
from ._shared import _extract_script_text

if TYPE_CHECKING:
    from film_pipeline.agents.impl.shot_bible_agent import ShotBibleAgent
    from film_pipeline.schemas._base import ArtifactType

from film_pipeline.schemas.continuity import (
    ContinuityLedger,
    ContinuityLedgerEntry,
    StateRecord,
)


def _character_state(chars: list[str]) -> StateRecord:
    """Build the characters StateRecord shared by state_in/state_out."""
    return StateRecord(
        label="characters",
        description=", ".join(chars) if chars else "none",
        refs=chars,
    )


def _environment_state(env: str) -> StateRecord:
    """Build the environment StateRecord shared by state_in/state_out."""
    return StateRecord(label="environment", description=env, refs=[env] if env else [])


def _continuity_entries(matrix: Any) -> list[ContinuityLedgerEntry]:
    """Walk the matrix rows, pairing each shot's state_in with prior state_out."""
    entries: list[ContinuityLedgerEntry] = []
    prev_chars: list[str] = []
    prev_env = ""
    for row in matrix.rows:
        current_chars = [str(c) for c in row.characters]
        current_env = str(row.environment)
        entries.append(
            ContinuityLedgerEntry(
                shot_id=row.shot_id,
                state_in=[_character_state(prev_chars), _environment_state(prev_env)],
                action="",
                state_out=[_character_state(current_chars), _environment_state(current_env)],
            )
        )
        prev_chars = current_chars
        prev_env = current_env
    return entries


def _save_next_candidate_version(
    store: Any,
    project_id: str,
    artifact_id: str,
    artifact_type: ArtifactType,
    payload: Any,
) -> str:
    """Save payload as the next CANDIDATE version of an artifact in the shot_bible phase."""
    from datetime import UTC, datetime

    from film_pipeline.schemas._base import ArtifactStatus, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef

    next_version = (
        _latest_artifact_version(store, project_id, FilmPhase("shot_bible"), artifact_id) + 1
    )
    meta = ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        project_id=project_id,
        phase=FilmPhase("shot_bible"),
        version=next_version,
        status=ArtifactStatus.CANDIDATE,
        parents=[],
        created_by="mcp.generate_shot_bible",
        created_at=datetime.now(UTC),
    )
    ref: ArtifactRef = store.save(payload, meta)
    return ref.to_string()


def _persist_continuity_ledger(store: Any, project_id: str, ledger: ContinuityLedger) -> str:
    """Save the ledger as a new continuity_ledger artifact version."""
    from film_pipeline.schemas._base import ArtifactType

    return _save_next_candidate_version(
        store, project_id, "continuity_ledger", ArtifactType.CONTINUITY_LEDGER, ledger
    )


def _generate_continuity_ledger(store: Any, project_id: str, matrix: Any) -> str | None:
    """Generate a basic continuity ledger from the shot matrix."""
    try:
        ledger = ContinuityLedger(project_id=project_id, entries=_continuity_entries(matrix))
        return _persist_continuity_ledger(store, project_id, ledger)
    except Exception:
        return None


def _load_matrix_inputs(store: Any, project_id: str) -> tuple[Any, Any]:
    """Load the Script and reference_index artifacts the matrix is built from."""
    from film_pipeline.schemas._base import FilmPhase

    script_version = max(1, store.latest_version(project_id, "script", "script"))
    script_data = store.load(project_id, FilmPhase("script"), "script", script_version)
    ref_version = max(1, store.latest_version(project_id, "visual_dev", "reference_index"))
    ref_data = store.load(project_id, FilmPhase("visual_dev"), "reference_index", ref_version)
    return script_data, ref_data


def _reference_summary(ref_data: Any) -> str:
    """Summarize the first visual-reference entries for the agent prompt."""
    if not isinstance(ref_data, dict):
        return ""
    entries = ref_data.get("entries", [])
    return ", ".join(
        f"{e.get('subject_type', '')}/{e.get('subject_id', '')}({e.get('frame_role', '')})"
        for e in entries[:20]
        if isinstance(e, dict)
    )


def _register_shot_agent() -> ShotBibleAgent:
    """Create the shot-design agent with its handoff registration."""
    from film_pipeline.agents.impl.shot_bible_agent import ShotBibleAgent
    from film_pipeline.schemas._base import AgentFamily, AgentRole
    from film_pipeline.schemas.handoff import AgentRegistration

    return ShotBibleAgent(
        AgentRegistration(
            agent_id="shot-design-agent",
            family=AgentFamily.DEVELOPMENT,
            role=AgentRole.CREATOR,
            capabilities=["shot_design", "matrix_planning"],
            input_artifacts=["script", "visual_refs", "character_bible"],
            output_artifacts=["master_film_matrix"],
        )
    )


def _fallback_matrix_output(project_id: str) -> dict[str, Any]:
    """Deterministic mock output used when no model adapter is configured."""
    return {
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


def _request_matrix_output(
    runner: Any,
    project_id: str,
    script_text: str,
    ref_summary: str,
) -> dict[str, Any]:
    """Ask the model for a MasterFilmMatrix, falling back to mock output."""
    if runner.model_adapter is None:
        return _fallback_matrix_output(project_id)

    raw = runner.model_adapter.chat(
        f"Create a MasterFilmMatrix from the script and visual references.\n\n"
        f"Script:\n{script_text[:6000]}\n\n"
        f"Visual references available:\n{ref_summary}\n\n"
        "Return JSON with 'shot_matrix' containing 'rows' array of shot rows "
        "(shot_id, act_id, scene_id, duration_seconds, characters, environment, "
        "camera_profile, priority, risk_level) and 'coverage_groups' array.",
        model=runner.model_router.resolve("creative_writer"),
    )
    return raw if isinstance(raw, dict) else {}


def _persist_shot_matrix(store: Any, project_id: str, matrix: Any) -> str:
    """Save the matrix as a new master_film_matrix artifact version."""
    from film_pipeline.schemas._base import ArtifactType

    return _save_next_candidate_version(
        store, project_id, "master_film_matrix", ArtifactType.MASTER_FILM_MATRIX, matrix
    )


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
        script_data, ref_data = _load_matrix_inputs(store, project_id)
    except (FileNotFoundError, ValueError) as e:
        return _error(f"Required artifacts not found: {e}")

    script_text = _extract_script_text(script_data)
    ref_summary = _reference_summary(ref_data)

    try:
        agent = _register_shot_agent()
        runner = _services(rt).prompt_runner
        model_output = _request_matrix_output(runner, project_id, script_text, ref_summary)

        result = agent.execute(model_output)
        if not agent.validate(result):
            return _error("ShotBible agent produced invalid output.")
        matrix = result["shot_matrix"]

        ref = _persist_shot_matrix(store, project_id, matrix)
        active["shot_matrix_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)

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
