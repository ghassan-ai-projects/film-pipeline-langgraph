"""Shot bible generation tool and continuity ledger."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import (
    _error,
    _latest_artifact_version,
    _ok,
    _services,
    require_project_state,
)
from ._shared import InvalidBibleOutput, _extract_script_text, _run_bible_agent

if TYPE_CHECKING:
    from film_pipeline.schemas.base import ArtifactType

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

    from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef
    from film_pipeline.schemas.base import ArtifactStatus, FilmPhase

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
    from film_pipeline.schemas.base import ArtifactType

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
    from film_pipeline.schemas.base import FilmPhase

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


def _persist_shot_matrix(store: Any, project_id: str, matrix: Any) -> str:
    """Save the matrix as a new master_film_matrix artifact version."""
    from film_pipeline.schemas.base import ArtifactType

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
    active = require_project_state(args)
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    try:
        script_data, ref_data = _load_matrix_inputs(store, project_id)
    except (FileNotFoundError, ValueError) as e:
        return _error(f"Required artifacts not found: {e}")

    script_text = _extract_script_text(script_data)
    ref_summary = _reference_summary(ref_data)

    try:
        result = _run_bible_agent(
            rt,
            "shot-design-agent",
            "Design the shot matrix for the film.",
            {
                "script_content": script_text,
                "reference_summary": ref_summary,
                "project_id": project_id,
            },
        )
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
    except InvalidBibleOutput:
        return _error("ShotBible agent produced invalid output.")
    except Exception as exc:
        return _error(f"Shot bible generation failed: {exc}")
