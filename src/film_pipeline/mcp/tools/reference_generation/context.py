"""Per-entry generation context: batch state, bibles, prompts, routing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from film_pipeline.mcp.tools.reference_generation.entries import (
    _group_key,
    _reference_aspect_ratio,
    _reference_job_id,
    _reference_output_dir,
    _reference_prompt,
)


@dataclass(frozen=True)
class _GenerationBatch:
    """Shared services and accumulators for one generation batch."""

    rt: Any
    provider: Any
    project_root: Path
    identity_states: dict[str, dict[str, object]]
    char_bibles: dict[str, dict[str, object]]
    results: list[dict[str, object]]


@dataclass(frozen=True)
class _EntryContext:
    """Per-entry generation inputs shared by the retry and metadata steps."""

    reference_id: str
    shot_id: str
    output_dir: str
    prompt_text: str
    aspect_ratio: str
    tier: str
    provider_kwargs: dict[str, object]


def _requested_reference_ids(args: dict[str, object]) -> set[str]:
    """Normalized set of explicitly requested reference ids."""
    return {
        str(item)
        for item in cast(list[Any], args.get("reference_ids", []))
        if isinstance(item, str) and str(item).strip()
    }


def _copied_entries(grouped_entries: list[dict[str, object]]) -> list[dict[str, object]]:
    """Shallow-copy every entry so persisted state keeps the pre-run values."""
    return [dict(r) for r in grouped_entries]  # use modified copies


def _maybe_cache_character_bible(
    store: Any,
    project_id: str,
    raw: dict[str, object],
    char_bibles: dict[str, dict[str, object]],
) -> None:
    """Cache the CharacterBible for a character entry when one exists."""
    subject_type = str(raw.get("subject_type", ""))
    subject_id = str(raw.get("subject_id", "")).strip()
    if subject_type != "character" or not subject_id or subject_id in char_bibles:
        return
    try:
        from film_pipeline.schemas._base import FilmPhase

        bible = store.load(project_id, FilmPhase("visual_dev"), "character_bible", 1)
        if isinstance(bible, dict) and bible.get("character_id") == subject_id:
            char_bibles[subject_id] = bible
    except (FileNotFoundError, ValueError):
        pass  # CharacterBible not yet generated — fall back to prompt_text


def _load_character_bibles(
    store: Any,
    project_id: str,
    grouped_entries: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Pre-load CharacterBibles from the artifact store for structured prompts."""
    char_bibles: dict[str, dict[str, object]] = {}
    for raw in grouped_entries:
        if raw.get("_skip"):
            continue
        _maybe_cache_character_bible(store, project_id, raw, char_bibles)
    return char_bibles


# Identity consistency is enforced via the ID_REINFORCE prompt block
# (the Imagen API does not support reference-image conditioning).
# anchor_frame_path and i2i_active in identity_states are consumed by
# _reference_prompt() → build_structured_prompt() to strengthen the
# ID_REINFORCE instruction when Gemini detects subject drift.


def _seed_from_identity_state(
    identity_states: dict[str, dict[str, object]],
    group_key: str,
    shot_id: str,
    provider_kwargs: dict[str, object],
) -> None:
    """Reuse the group's anchor seed, or mint one on the anchor entry."""
    identity_state = identity_states.get(group_key, {})
    anchor_seed = identity_state.get("anchor_seed")
    if anchor_seed is not None:
        provider_kwargs["seed"] = anchor_seed
    else:
        provider_kwargs["seed"] = hash(shot_id) % (2**31)
        identity_states.setdefault(group_key, {})["anchor_seed"] = provider_kwargs["seed"]


def _prepare_entry_context(
    raw: dict[str, object],
    reference_id: str,
    char_bibles: dict[str, dict[str, object]],
    identity_states: dict[str, dict[str, object]],
    project_root: Path,
) -> _EntryContext:
    """Build prompt, output, and provider-routing context for one entry."""
    prompt_text = _reference_prompt(
        raw,
        character_bible=char_bibles.get(str(raw.get("subject_id", "")).strip()),
        identity_state=identity_states.get(_group_key(raw)),
    )
    aspect_ratio = _reference_aspect_ratio(raw)
    shot_id = _reference_job_id(reference_id)
    output_dir = str(_reference_output_dir(raw, project_root).resolve())
    # Ensure the directory tree exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Provider tier routing (Phase 6) + Identity consistency (Phase 4)
    tier = str(raw.get("tier", "fast"))
    provider_kwargs: dict[str, object] = {"duration": 0.0, "aspect_ratio": aspect_ratio}
    if tier in ("standard", "ultra"):
        _seed_from_identity_state(identity_states, _group_key(raw), shot_id, provider_kwargs)

    return _EntryContext(
        reference_id=reference_id,
        shot_id=shot_id,
        output_dir=output_dir,
        prompt_text=prompt_text,
        aspect_ratio=aspect_ratio,
        tier=tier,
        provider_kwargs=provider_kwargs,
    )
