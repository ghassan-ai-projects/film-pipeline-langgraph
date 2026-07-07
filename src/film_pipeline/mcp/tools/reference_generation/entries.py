"""Reference-index entry helpers: grouping, prompts, output paths."""

from __future__ import annotations

import logging
from pathlib import Path

_logger = logging.getLogger(__name__)


def _group_key(entry: dict[str, object]) -> str:
    """Deterministic group key for identity/geometry consistency."""
    subject_type = str(entry.get("subject_type", "")).strip().lower()
    subject_id = str(entry.get("subject_id", "")).strip().lower()
    return f"{subject_type}:{subject_id}"


def _group_and_sort_entries(
    entries: list[object],
    requested_ids: set[str],
    force: bool,
    project_root: Path,
) -> list[dict[str, object]]:
    """Filter, group, and sort entries — anchor frame first per group.

    Character anchors: 'front-face'. Environment anchors: 'wide-establishing'.
    Entries already generated (asset_path present, not force) are tagged _skip.
    """
    ANCHOR_PRIORITY = {"front-face": 0, "wide-establishing": 0}

    filtered: list[dict[str, object]] = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        ref_id = str(raw.get("reference_id", "")).strip()
        if not ref_id:
            continue
        if requested_ids and ref_id not in requested_ids:
            continue
        r = dict(raw)
        r["_reference_id"] = ref_id
        if r.get("asset_path") and not force:
            existing_path = project_root / str(r.get("asset_path", ""))
            if existing_path.exists():
                r["_skip"] = True
        filtered.append(r)

    # Sort: group by key, anchor first within each group
    def sort_key(r: dict[str, object]) -> tuple[str, int, str]:
        gk = _group_key(r)
        role = str(r.get("frame_role", "")).strip().lower()
        anchor_prio = ANCHOR_PRIORITY.get(role, 50)
        return (gk, anchor_prio, str(r.get("reference_id", "")))

    filtered.sort(key=sort_key)
    return filtered


def _reference_output_dir(entry: dict[str, object], project_root: Path) -> Path:
    """Compute organized output directory for a reference entry.

    Produces paths like:
        references/characters/leo/master-frames/
        references/environments/studio/master-frames/
        references/props/paintbrush/
        references/style/
        references/scale/
    """
    subject_type = str(entry.get("subject_type", "misc")).strip().lower()
    subject_id = str(entry.get("subject_id", "unknown")).strip().lower()

    if subject_type in ("character", "environment", "prop"):
        return project_root / "references" / f"{subject_type}s" / subject_id / "master-frames"
    return project_root / "references" / subject_type


def _reference_prompt(
    entry: dict[str, object],
    *,
    character_bible: dict[str, object] | None = None,
    constitution: dict[str, object] | None = None,
    identity_state: dict[str, object] | None = None,
) -> str:
    """Build a structured generation prompt from domain data blocks.

    Delegates to ``build_structured_prompt()`` which assembles character or
    environment prompts from locked blocks (CharacterBible, FilmConstitution).
    Falls back to the entry's ``prompt_text`` when no structured sources exist.
    """
    from film_pipeline.generation.prompt_builder import build_structured_prompt

    return build_structured_prompt(
        dict(entry),
        character_bible=dict(character_bible) if character_bible else None,
        constitution=dict(constitution) if constitution else None,
        identity_state=dict(identity_state) if identity_state else None,
    )


def _reference_aspect_ratio(entry: dict[str, object]) -> str:
    asset_type = str(entry.get("asset_type", ""))
    subject_type = str(entry.get("subject_type", ""))
    if "environment" in asset_type or subject_type == "environment":
        return "16:9"
    if "style" in asset_type or "camera" in asset_type or "scale" in asset_type:
        return "16:9"
    return "3:4"


def _reference_job_id(reference_id: str) -> str:
    return reference_id.replace(":", "-").replace("/", "-")
