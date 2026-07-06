"""Delta regeneration — tile-level fixes after composite validation failure.

When composite validation returns failing tiles, regenerate only those tiles
instead of the entire batch. Saves 30-40% cost. Max 3 iterations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from film_pipeline.generation.compositor import replace_tile
from film_pipeline.generation.sheet_reviewer import SheetReviewResult, review_composite_sheet


def regenerate_failing_tiles(
    sheet_review: SheetReviewResult,
    entries: list[dict[str, Any]],
    sheet_path: Path,
    *,
    regenerate_fn: Any,
    max_iterations: int = 3,
    model: str = "",
) -> tuple[float, int, list[str]]:
    """Regenerate failing tiles from a composite validation review.

    Args:
        sheet_review: Composite validation result with failing_tiles.
        entries: Reference index entries (to find source frames by role).
        sheet_path: Path to the composite sheet to fix.
        regenerate_fn: Callable(entry, prompt_feedback) -> Path that regenerates
                       a single frame and returns the new file path.
        max_iterations: Max delta iterations (default 3).
        model: Model ID for sheet review (required, resolved via ModelRouter).

    Returns:
        (best_score, iterations_used, failing_tiles_history)
    """
    best_score = sheet_review.total
    best_iteration = 0
    all_failing: list[str] = list(sheet_review.failing_tiles)

    for iteration in range(1, max_iterations + 1):
        if not sheet_review.failing_tiles:
            break

        # Regenerate each failing tile
        for tile_name in sheet_review.failing_tiles:
            entry = _find_entry_by_role(entries, tile_name)
            if entry is None:
                continue
            asset_path = str(entry.get("asset_path", ""))
            if not asset_path:
                continue
            feedback = sheet_review.actionable_feedback or f"Fix {tile_name}"
            try:
                new_path = regenerate_fn(entry, feedback)
                if new_path and new_path.exists():
                    replace_tile(sheet_path, tile_name, new_path)
                    if tile_name not in all_failing:
                        all_failing.append(tile_name)
            except Exception:
                continue

        # Re-validate the sheet
        sheet_type = sheet_review.sheet_type
        subject_id = sheet_review.sheet_id
        sheet_review = review_composite_sheet(sheet_path, sheet_type, subject_id, model=model)

        if sheet_review.total > best_score:
            best_score = sheet_review.total
            best_iteration = iteration

        if sheet_review.passed:
            break

    return best_score, best_iteration, all_failing


def _find_entry_by_role(
    entries: list[dict[str, Any]],
    role: str,
) -> dict[str, Any] | None:
    for entry in entries:
        if str(entry.get("frame_role", "")) == role:
            return entry
    return None
