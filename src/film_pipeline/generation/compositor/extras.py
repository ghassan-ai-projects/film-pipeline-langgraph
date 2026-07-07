"""Additional composite templates: expression sheet, scale sheet, style board."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

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

# ── Additional composite templates ─────────────────────────────────────


def build_expression_sheet(
    subject_id: str,
    character_name: str,
    frames: dict[str, Path],
    output_path: Path,
) -> Path:
    """Build an Expression Sheet grid from expression frame roles."""
    _EXPR_SIZE = (2048, 2048)
    _EXPR_TILES = {
        "expression-neutral": (8, 60, 504, 504),
        "expression-frustrated": (520, 60, 504, 504),
        "expression-tired": (8, 572, 504, 504),
        "expression-peaceful": (520, 572, 504, 504),
    }
    _EXPR_LABELS = {k: v for k, v in _CHAR_LABELS.items() if k.startswith("expression-")}

    canvas = Image.new("RGB", _EXPR_SIZE, _BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    font = _load_font(14)
    title = f"EXPRESSION SHEET — {subject_id.upper()} — {character_name}"
    draw.text((8, 8), title, fill=_LABEL_COLOR, font=font)
    draw.line([(8, 40), (_EXPR_SIZE[0] - 8, 40)], fill=_BORDER_COLOR, width=1)

    for role, (x, y, w, h) in _EXPR_TILES.items():
        draw.rectangle([x - 1, y - 1, x + w + 1, y + h + 1], outline=_BORDER_COLOR, width=1)
        fp = frames.get(role)
        if fp and fp.exists():
            try:
                tile = Image.open(fp).convert("RGB")
                tile = _crop_center(tile, w, h)
                canvas.paste(tile, (x, y))
            except Exception:
                _paste_placeholder(canvas, x, y, w, h, role)
        else:
            _paste_placeholder(canvas, x, y, w, h, role)
        label = _EXPR_LABELS.get(role, role.upper())
        draw.text((x + 2, y + h + 2), label, fill=_LABEL_COLOR, font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG")
    return output_path


def build_scale_sheet(
    project_id: str,
    frames: dict[str, Path],
    output_path: Path,
) -> Path:
    """Build a Scale Sheet — side-by-side full-body comparison of all characters."""
    _SCALE_SIZE = (3840, 2160)
    canvas = Image.new("RGB", _SCALE_SIZE, _BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    font = _load_font(16)
    title = f"SCALE SHEET — {project_id}"
    draw.text((8, 8), title, fill=_LABEL_COLOR, font=font)
    draw.line([(8, 42), (_SCALE_SIZE[0] - 8, 42)], fill=_BORDER_COLOR, width=1)

    if not frames:
        _paste_placeholder(canvas, 8, 60, _SCALE_SIZE[0] - 16, _SCALE_SIZE[1] - 68, "no-frames")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, "PNG")
        return output_path

    tile_w = (_SCALE_SIZE[0] - 16) // max(len(frames), 1)
    tile_h = _SCALE_SIZE[1] - 68
    for i, (char_id, fp) in enumerate(sorted(frames.items())):
        x = 8 + i * tile_w
        draw.rectangle([x - 1, 59, x + tile_w + 1, 59 + tile_h + 1], outline=_BORDER_COLOR, width=1)
        if fp.exists():
            try:
                tile = Image.open(fp).convert("RGB")
                tile = _crop_center(tile, tile_w, tile_h)
                canvas.paste(tile, (x, 60))
            except Exception:
                _paste_placeholder(canvas, x, 60, tile_w, tile_h, char_id)
        else:
            _paste_placeholder(canvas, x, 60, tile_w, tile_h, char_id)
        draw.text((x + 4, 62), char_id.upper(), fill=_LABEL_COLOR, font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG")
    return output_path


def build_style_board(
    project_id: str,
    palette_colors: list[str],
    texture: str,
    grain: str,
    visual_mood: str,
    output_path: Path,
) -> Path:
    """Build a Style Board — color swatches + texture/grain/mood annotation."""
    _STYLE_SIZE = (3840, 2160)
    canvas = Image.new("RGB", _STYLE_SIZE, _BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    font = _load_font(20)
    small_font = _load_font(14)
    title = f"STYLE BOARD — {project_id}"
    draw.text((8, 8), title, fill=_LABEL_COLOR, font=font)
    draw.line([(8, 44), (_STYLE_SIZE[0] - 8, 44)], fill=_BORDER_COLOR, width=1)

    # Color palette swatches
    palette_y = 60
    palette_h = 200
    if palette_colors:
        swatch_w = (_STYLE_SIZE[0] - 16) // len(palette_colors)
        rgb_colors = _parse_palette(palette_colors)
        for i, color in enumerate(rgb_colors):
            sx = 8 + i * swatch_w
            swatch = Image.new("RGB", (swatch_w, palette_h), color)
            canvas.paste(swatch, (sx, palette_y))
            hex_label = f"#{palette_colors[i].strip().lstrip('#')}"
            luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
            tc = (255, 255, 255) if luminance < 128 else (30, 30, 30)
            bbox = draw.textbbox((0, 0), hex_label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(
                (sx + (swatch_w - tw) // 2, palette_y + (palette_h - th) // 2),
                hex_label,
                fill=tc,
                font=font,
            )
    else:
        _paste_placeholder(canvas, 8, palette_y, _STYLE_SIZE[0] - 16, palette_h, "color-palette")

    # Texture / grain / mood annotation
    y = palette_y + palette_h + 20
    for label, value in [("TEXTURE", texture), ("GRAIN", grain), ("VISUAL MOOD", visual_mood)]:
        draw.text(
            (16, y), f"{label}: {value or '(not specified)'}", fill=_LABEL_COLOR, font=small_font
        )
        y += 24

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG")
    return output_path
