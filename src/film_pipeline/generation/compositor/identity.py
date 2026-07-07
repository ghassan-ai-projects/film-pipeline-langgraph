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
    _crop_center,
    _load_font,
    _paste_placeholder,
    _write_sheet_manifest,
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

    # Try to load a font; fall back to default
    font = _load_font(14)

    # Title
    title = f"CHARACTER IDENTITY SHEET — {subject_id.upper()} — {character_name}"
    draw.text((_MARGIN, 8), title, fill=_LABEL_COLOR, font=font)

    # Divider line below title
    draw.line([(_MARGIN, 40), (_SHEET_SIZE[0] - _MARGIN, 40)], fill=_BORDER_COLOR, width=1)

    # Paste each frame tile
    for role, (x, y, w, h) in _CHAR_TILES.items():
        # Draw border
        draw.rectangle(
            [x - 1, y - 1, x + w + 1, y + h + 1], outline=_BORDER_COLOR, width=_BORDER_WIDTH
        )

        frame_path = frames.get(role)
        if frame_path and frame_path.exists():
            try:
                tile = Image.open(frame_path).convert("RGB")
                tile = _crop_center(tile, w, h)
                canvas.paste(tile, (x, y))
            except Exception:
                _paste_placeholder(canvas, x, y, w, h, role)
        else:
            _paste_placeholder(canvas, x, y, w, h, role)

        # Label in margin area (below tile)
        label = _CHAR_LABELS.get(role, role.upper().replace("-", " "))
        label_y = y + h + 2
        if label_y + 14 < _SHEET_SIZE[1]:
            draw.text((x + 2, label_y), label, fill=_LABEL_COLOR, font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG")
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

    if new_frame_path.exists():
        try:
            tile = Image.open(new_frame_path).convert("RGB")
            tile = _crop_center(tile, w, h)
            canvas.paste(tile, (x, y))
        except Exception:
            _paste_placeholder(canvas, x, y, w, h, tile_name)
    else:
        _paste_placeholder(canvas, x, y, w, h, tile_name)

    canvas.save(target, "PNG")
    return target
