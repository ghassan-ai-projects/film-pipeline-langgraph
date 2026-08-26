"""Additional composite templates: expression sheet, scale sheet, style board."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from film_pipeline.generation.compositor._layout import (
    _BG_COLOR,
    _BORDER_COLOR,
    _CHAR_LABELS,
    _LABEL_COLOR,
    _crop_center,
    _load_font,
    _parse_palette,
    _paste_placeholder,
)

# ── Sheet geometry ──────────────────────────────────────────────────────

_EXPRESSION_SHEET_SIZE = (2048, 2048)
_EXPRESSION_TILES: dict[str, tuple[int, int, int, int]] = {
    "expression-neutral": (8, 60, 504, 504),
    "expression-frustrated": (520, 60, 504, 504),
    "expression-tired": (8, 572, 504, 504),
    "expression-peaceful": (520, 572, 504, 504),
}
_EXPRESSION_TILE_LABELS: dict[str, str] = {
    role: label for role, label in _CHAR_LABELS.items() if role.startswith("expression-")
}
_SCALE_SHEET_SIZE = (3840, 2160)
_STYLE_BOARD_SIZE = (3840, 2160)
# Swatch strip on the style board (x, y, w, h)
_STYLE_BOARD_SWATCH_ROW = (8, 60, 3840 - 16, 200)

# ── Additional composite templates ─────────────────────────────────────


def build_expression_sheet(
    subject_id: str,
    character_name: str,
    frames: dict[str, Path],
    output_path: Path,
) -> Path:
    """Build an Expression Sheet grid from expression frame roles."""
    canvas = Image.new("RGB", _EXPRESSION_SHEET_SIZE, _BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    font = _load_font(14)
    title = f"EXPRESSION SHEET — {subject_id.upper()} — {character_name}"
    draw.text((8, 8), title, fill=_LABEL_COLOR, font=font)
    draw.line([(8, 40), (_EXPRESSION_SHEET_SIZE[0] - 8, 40)], fill=_BORDER_COLOR, width=1)

    for role, (x, y, w, h) in _EXPRESSION_TILES.items():
        draw.rectangle([x - 1, y - 1, x + w + 1, y + h + 1], outline=_BORDER_COLOR, width=1)
        _paste_frame_or_placeholder(canvas, frames.get(role), x, y, w, h, role)
        label = _EXPRESSION_TILE_LABELS.get(role, role.upper())
        draw.text((x + 2, y + h + 2), label, fill=_LABEL_COLOR, font=font)

    return _save_sheet(canvas, output_path)


def build_scale_sheet(
    project_id: str,
    frames: dict[str, Path],
    output_path: Path,
) -> Path:
    """Build a Scale Sheet — side-by-side full-body comparison of all characters."""
    canvas = Image.new("RGB", _SCALE_SHEET_SIZE, _BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    font = _load_font(16)
    title = f"SCALE SHEET — {project_id}"
    draw.text((8, 8), title, fill=_LABEL_COLOR, font=font)
    draw.line([(8, 42), (_SCALE_SHEET_SIZE[0] - 8, 42)], fill=_BORDER_COLOR, width=1)

    if not frames:
        _paste_placeholder(
            canvas, 8, 60, _SCALE_SHEET_SIZE[0] - 16, _SCALE_SHEET_SIZE[1] - 68, "no-frames"
        )
        return _save_sheet(canvas, output_path)

    tile_w = (_SCALE_SHEET_SIZE[0] - 16) // max(len(frames), 1)
    tile_h = _SCALE_SHEET_SIZE[1] - 68
    for i, (char_id, fp) in enumerate(sorted(frames.items())):
        x = 8 + i * tile_w
        draw.rectangle([x - 1, 59, x + tile_w + 1, 59 + tile_h + 1], outline=_BORDER_COLOR, width=1)
        _paste_frame_or_placeholder(canvas, fp, x, 60, tile_w, tile_h, char_id)
        draw.text((x + 4, 62), char_id.upper(), fill=_LABEL_COLOR, font=font)

    return _save_sheet(canvas, output_path)


def build_style_board(
    project_id: str,
    palette_colors: list[str],
    texture: str,
    grain: str,
    visual_mood: str,
    output_path: Path,
) -> Path:
    """Build a Style Board — color swatches + texture/grain/mood annotation."""
    canvas = Image.new("RGB", _STYLE_BOARD_SIZE, _BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    font = _load_font(20)
    small_font = _load_font(14)
    title = f"STYLE BOARD — {project_id}"
    draw.text((8, 8), title, fill=_LABEL_COLOR, font=font)
    draw.line([(8, 44), (_STYLE_BOARD_SIZE[0] - 8, 44)], fill=_BORDER_COLOR, width=1)
    _draw_style_board_swatches(canvas, draw, font, palette_colors)
    _draw_style_board_annotations(draw, small_font, texture, grain, visual_mood)

    return _save_sheet(canvas, output_path)


# ── Sheet drawing helpers ───────────────────────────────────────────────


def _paste_frame_or_placeholder(
    canvas: Image.Image,
    frame_path: Path | None,
    x: int,
    y: int,
    w: int,
    h: int,
    label: str,
) -> None:
    """Center-crop *frame_path* into the tile at (x, y), or render a placeholder."""
    if frame_path is None or not frame_path.exists():
        _paste_placeholder(canvas, x, y, w, h, label)
        return
    try:
        tile = Image.open(frame_path).convert("RGB")
        canvas.paste(_crop_center(tile, w, h), (x, y))
    except Exception:
        _paste_placeholder(canvas, x, y, w, h, label)


def _draw_style_board_swatches(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    palette_colors: list[str],
) -> None:
    """Render the color-palette swatch strip, or a placeholder when empty."""
    sx_base, swatch_y, row_w, swatch_h = _STYLE_BOARD_SWATCH_ROW
    if not palette_colors:
        _paste_placeholder(canvas, sx_base, swatch_y, row_w, swatch_h, "color-palette")
        return
    rgb_colors = _parse_palette(palette_colors)
    swatch_w = row_w // len(palette_colors)
    for i, color in enumerate(rgb_colors):
        sx = sx_base + i * swatch_w
        canvas.paste(Image.new("RGB", (swatch_w, swatch_h), color), (sx, swatch_y))
        hex_label = f"#{palette_colors[i].strip().lstrip('#')}"
        luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
        text_color = (255, 255, 255) if luminance < 128 else (30, 30, 30)
        bbox = draw.textbbox((0, 0), hex_label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            (sx + (swatch_w - tw) // 2, swatch_y + (swatch_h - th) // 2),
            hex_label,
            fill=text_color,
            font=font,
        )


def _draw_style_board_annotations(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    texture: str,
    grain: str,
    visual_mood: str,
) -> None:
    """Write the TEXTURE/GRAIN/VISUAL MOOD lines below the swatch strip."""
    y = _STYLE_BOARD_SWATCH_ROW[1] + _STYLE_BOARD_SWATCH_ROW[3] + 20
    for label, value in [("TEXTURE", texture), ("GRAIN", grain), ("VISUAL MOOD", visual_mood)]:
        draw.text((16, y), f"{label}: {value or '(not specified)'}", fill=_LABEL_COLOR, font=font)
        y += 24


def _save_sheet(canvas: Image.Image, output_path: Path) -> Path:
    """Write the finished sheet as PNG, creating parent directories first."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG")
    return output_path
