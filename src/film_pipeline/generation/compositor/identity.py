"""Character identity sheet construction and tile replacement."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from film_pipeline.generation.compositor._layout import (
    _BG_COLOR,
    _BORDER_COLOR,
    _BORDER_WIDTH,
    _CHAR_LABELS,
    _CHAR_TILES,
    _LABEL_COLOR,
    _MARGIN,
    _SHEET_SIZE,
    _load_font,
    _write_sheet_manifest,
)
from film_pipeline.generation.compositor.extras import (
    _paste_frame_or_placeholder,
    _save_sheet,
)

# ── Public API ────────────────────────────────────────────────────────────


def build_character_identity_sheet(
    subject_id: str,
    character_name: str,
    frames: dict[str, Path],
    output_path: Path,
) -> Path:
    """Build a Character Identity Sheet composite from master frames.

    Args:
        subject_id: e.g. ``"leo"``.
        character_name: Display name for the sheet header.
        frames: Map of ``frame_role`` → ``Path`` to frame PNG.
                Missing roles render as gray placeholders.
        output_path: Where to save the composite PNG.

    Returns:
        ``output_path``.
    """
    canvas = Image.new("RGB", _SHEET_SIZE, _BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    font = _load_font(14)

    title = f"CHARACTER IDENTITY SHEET — {subject_id.upper()} — {character_name}"
    draw.text((_MARGIN, 8), title, fill=_LABEL_COLOR, font=font)
    draw.line([(_MARGIN, 40), (_SHEET_SIZE[0] - _MARGIN, 40)], fill=_BORDER_COLOR, width=1)

    for role, (x, y, w, h) in _CHAR_TILES.items():
        draw.rectangle(
            [x - 1, y - 1, x + w + 1, y + h + 1], outline=_BORDER_COLOR, width=_BORDER_WIDTH
        )
        _paste_frame_or_placeholder(canvas, frames.get(role), x, y, w, h, role)
        label = _CHAR_LABELS.get(role, role.upper().replace("-", " "))
        label_y = y + h + 2
        if label_y + 14 < _SHEET_SIZE[1]:
            draw.text((x + 2, label_y), label, fill=_LABEL_COLOR, font=font)

    _save_sheet(canvas, output_path)
    _write_sheet_manifest(
        output_path,
        subject_id,
        "character_identity_sheet",
        _SHEET_SIZE,
        frames,
        _CHAR_TILES,
    )
    return output_path


def replace_tile(
    sheet_path: Path,
    tile_name: str,
    new_frame_path: Path,
    output_path: Path | None = None,
) -> Path:
    """Replace a single tile in an existing composite sheet.

    Args:
        sheet_path: Existing composite PNG.
        tile_name: Frame role name matching a key in ``_CHAR_TILES``.
        new_frame_path: Path to the replacement frame.
        output_path: Where to save (defaults to overwriting *sheet_path*).

    Returns:
        Path to the saved composite.
    """
    target = output_path or sheet_path
    canvas = Image.open(sheet_path).convert("RGB")

    if tile_name not in _CHAR_TILES:
        raise ValueError(f"Unknown tile: {tile_name}")

    x, y, w, h = _CHAR_TILES[tile_name]
    _paste_frame_or_placeholder(canvas, new_frame_path, x, y, w, h, tile_name)

    return _save_sheet(canvas, target)
