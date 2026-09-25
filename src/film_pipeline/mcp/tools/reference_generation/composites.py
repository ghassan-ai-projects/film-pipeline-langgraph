"""Composite sheet building and Gemini validation (non-blocking)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from film_pipeline.artifacts.store import ArtifactStore

_logger = logging.getLogger(__name__)


def _palette_from_bible(bible: object) -> list[str] | None:
    """Extract a non-empty color palette list from an EnvironmentBible."""
    if not isinstance(bible, dict):
        return None
    palette = bible.get("color_palette", [])
    if isinstance(palette, list) and palette:
        return [str(c) for c in palette]
    return None


def _load_environment_palette(
    artifact_store: ArtifactStore,
    project_id: str,
) -> list[str] | None:
    """Load the visual-dev EnvironmentBible palette (None when unavailable)."""
    from film_pipeline.schemas.base import FilmPhase

    try:
        version = max(
            1, artifact_store.latest_version(project_id, "visual_dev", "environment_bible")
        )
        bible = artifact_store.load(
            project_id, FilmPhase("visual_dev"), "environment_bible", version
        )
        return _palette_from_bible(bible)
    except (FileNotFoundError, ValueError):
        return None


def _collect_environment_palettes(
    artifact_store: ArtifactStore,
    project_id: str,
    entries: list[dict[str, object]],
) -> dict[str, list[str]]:
    """Resolve color palettes from EnvironmentBible artifacts."""
    palette = _load_environment_palette(artifact_store, project_id)
    if not palette:
        return {}
    env_palettes: dict[str, list[str]] = {}
    for entry in entries:
        if str(entry.get("subject_type", "")) != "environment":
            continue
        subject_id = str(entry.get("subject_id", "")).strip()
        if subject_id and subject_id not in env_palettes:
            env_palettes[subject_id] = palette
    return env_palettes


def _collect_subject_frames(
    project_root: Path,
    entries: list[dict[str, object]],
    subject_type: str,
) -> dict[str, dict[str, Path]]:
    """Group existing generated frame files by subject id and frame role."""
    frames_by_subject: dict[str, dict[str, Path]] = {}
    for entry in entries:
        if str(entry.get("subject_type", "")) != subject_type:
            continue
        if entry.get("generation_status") not in ("validated", "generated"):
            continue
        subject_id = str(entry.get("subject_id", "")).strip()
        role = str(entry.get("frame_role", "")).strip()
        asset = str(entry.get("asset_path", "")).strip()
        if not subject_id or not role or not asset:
            continue
        frame_path = project_root / asset
        if frame_path.exists():
            frames_by_subject.setdefault(subject_id, {})[role] = frame_path
    return frames_by_subject


def _collect_full_body_frames(char_frames: dict[str, dict[str, Path]]) -> dict[str, Path]:
    """Map each character to its existing full-body frame."""
    full_body_frames: dict[str, Path] = {}
    for subject_id, frames in char_frames.items():
        frame = frames.get("full-body")
        if frame and frame.exists():
            full_body_frames[subject_id] = frame
    return full_body_frames


def _build_identity_sheets(project_root: Path, char_frames: dict[str, dict[str, Path]]) -> None:
    """Build one identity sheet per character (Phase 7 + validation Phase 8)."""
    from film_pipeline.generation.compositor import build_character_identity_sheet

    for subject_id, frames in char_frames.items():
        sheet_path = project_root / "references" / "characters" / subject_id / "identity-sheet.png"
        try:
            build_character_identity_sheet(subject_id, subject_id, frames, sheet_path)
            # Phase 8 — Composite validation
            _validate_composite(sheet_path, "character_identity_sheet", subject_id)
        except Exception as exc:
            _logger.warning("Identity sheet build failed for %s: %s", subject_id, exc)


def _build_environment_boards(
    project_root: Path,
    env_frames: dict[str, dict[str, Path]],
    env_palettes: dict[str, list[str]],
) -> None:
    """Build one environment board per environment (Phase 7 + validation Phase 8)."""
    from film_pipeline.generation.compositor import build_environment_board

    for subject_id, frames in env_frames.items():
        sheet_path = (
            project_root / "references" / "environments" / subject_id / "environment-board.png"
        )
        try:
            build_environment_board(
                subject_id,
                subject_id,
                frames,
                sheet_path,
                palette_colors=env_palettes.get(subject_id),
            )
            # Phase 8 — Composite validation
            _validate_composite(sheet_path, "environment_board", subject_id)
        except Exception as exc:
            _logger.warning("Environment board build failed for %s: %s", subject_id, exc)


def _build_composites(
    project_root: Path,
    project_id: str,
    entries: list[dict[str, object]],
    artifact_store: ArtifactStore,
) -> None:
    """Build composite sheets from generated frames (Phase 7)."""
    env_palettes = _collect_environment_palettes(artifact_store, project_id, entries)
    char_frames = _collect_subject_frames(project_root, entries, "character")
    _build_identity_sheets(project_root, char_frames)

    env_frames = _collect_subject_frames(project_root, entries, "environment")
    _build_environment_boards(project_root, env_frames, env_palettes)

    # Phase 05 — Additional composite templates
    _build_optional_sheets(project_root, project_id, char_frames, env_palettes)


def _build_optional_sheets(
    project_root: Path,
    project_id: str,
    char_frames: dict[str, dict[str, Path]],
    env_palettes: dict[str, list[str]],
) -> None:
    """Build expression sheets, scale sheet, and style board (non-blocking)."""
    _build_expression_sheets(project_root, char_frames)
    _build_scale_sheet(project_root, project_id, char_frames)
    _build_style_board(project_root, project_id, env_palettes)


def _build_expression_sheets(project_root: Path, char_frames: dict[str, dict[str, Path]]) -> None:
    """Build one expression sheet per character (non-blocking)."""
    from film_pipeline.generation.compositor import build_expression_sheet

    for subject_id, frames in char_frames.items():
        try:
            sheet_path = (
                project_root / "references" / "characters" / subject_id / "expression-sheet.png"
            )
            build_expression_sheet(subject_id, subject_id, frames, sheet_path)
        except Exception as exc:
            _logger.warning("Expression sheet build failed for %s: %s", subject_id, exc)


def _build_scale_sheet(
    project_root: Path,
    project_id: str,
    char_frames: dict[str, dict[str, Path]],
) -> None:
    """Build the combined scale sheet from characters' full-body frames."""
    from film_pipeline.generation.compositor import build_scale_sheet

    full_body_frames = _collect_full_body_frames(char_frames)
    if not full_body_frames:
        return
    try:
        sheet_path = project_root / "references" / "scale" / "scale-sheet.png"
        build_scale_sheet(project_id, full_body_frames, sheet_path)
    except Exception as exc:
        _logger.warning("Scale sheet build failed for %s: %s", project_id, exc)


def _first_environment_palette(env_palettes: dict[str, list[str]]) -> list[str]:
    """Return the first environment's palette, or empty for compositor defaults."""
    return next(iter(env_palettes.values()), [])


def _build_style_board(
    project_root: Path,
    project_id: str,
    env_palettes: dict[str, list[str]],
) -> None:
    """Build the style board from the first environment palette (non-blocking)."""
    from film_pipeline.generation.compositor import build_style_board

    try:
        sheet_path = project_root / "references" / "style" / "style-board.png"
        build_style_board(
            project_id,
            _first_environment_palette(env_palettes),
            "",
            "",
            "",
            sheet_path,
        )
    except Exception as exc:
        _logger.warning("Style board build failed for %s: %s", project_id, exc)


def _validate_composite(sheet_path: Path, sheet_type: str, subject_id: str) -> None:
    """Run Gemini composite validation on a sheet (Phase 8). Non-blocking."""
    try:
        from film_pipeline.agents.model_routing import ModelRouter
        from film_pipeline.generation.sheet_reviewer import review_composite_sheet

        router = ModelRouter()
        review_composite_sheet(
            sheet_path,
            sheet_type,
            subject_id,
            model=router.resolve_or_raise("visual_reasoner"),
        )
    except Exception:
        pass  # validation failure doesn't block
