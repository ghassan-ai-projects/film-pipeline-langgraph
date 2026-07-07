"""Shared layout constants, drawing helpers, and the sheet manifest writer."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Layout constants ─────────────────────────────────────────────────────

_SHEET_SIZE = (2048, 2048)
_BG_COLOR = (248, 248, 250)
_BORDER_COLOR = (51, 51, 51)
_BORDER_WIDTH = 1
_SPACING = 8
_MARGIN = 8
_LABEL_COLOR = (80, 80, 80)
_PLACEHOLDER_COLOR = (200, 200, 210)

# Tile positions for Character Identity Sheet (x, y, w, h)
_CHAR_TILES: dict[str, tuple[int, int, int, int]] = {
    "front-face": (_MARGIN, 60, 640, 640),  # 2x scale, top-left
    "3-4-left": (656, 60, 312, 312),  # column 2
    "3-4-right": (976, 60, 312, 312),  # column 3
    "profile-right": (656, 380, 312, 312),  # column 2, row 2
    "profile-left": (976, 380, 312, 312),  # column 3, row 2
    "full-body": (_MARGIN, 708, 720, 400),  # wide, row 2
    "expression-neutral": (_MARGIN, 1116, 312, 312),  # row 3
    "expression-frustrated": (328, 1116, 312, 312),
    "expression-tired": (656, 1116, 312, 312),
    "expression-peaceful": (976, 1116, 312, 312),
    # Detail insets — right column
    "detail-eyes": (1304, 60, 312, 312),
    "detail-hands": (1304, 380, 312, 312),
    "wardrobe-baseline": (1304, 708, 480, 312),  # after body
}

# Labels shown below/above tiles (in margins)
_CHAR_LABELS: dict[str, str] = {
    "front-face": "FRONT FACE",
    "3-4-left": "3/4 LEFT",
    "3-4-right": "3/4 RIGHT",
    "profile-right": "PROFILE RIGHT",
    "profile-left": "PROFILE LEFT",
    "full-body": "FULL BODY",
    "expression-neutral": "NEUTRAL",
    "expression-frustrated": "FRUSTRATED",
    "expression-tired": "TIRED",
    "expression-peaceful": "PEACEFUL",
    "detail-eyes": "EYES",
    "detail-hands": "HANDS",
    "wardrobe-baseline": "WARDROBE",
}


# ── Helpers ───────────────────────────────────────────────────────────────


def _crop_center(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Center-crop *img* to *target_w* x *target_h*, then resize."""
    iw, ih = img.size
    # Crop to target aspect ratio
    target_aspect = target_w / target_h
    img_aspect = iw / ih

    if img_aspect > target_aspect:
        new_w = int(ih * target_aspect)
        left = (iw - new_w) // 2
        img = img.crop((left, 0, left + new_w, ih))
    else:
        new_h = int(iw / target_aspect)
        top = (ih - new_h) // 2
        img = img.crop((0, top, iw, top + new_h))

    return img.resize((target_w, target_h), Image.Resampling.LANCZOS)


def _paste_placeholder(
    canvas: Image.Image,
    x: int,
    y: int,
    w: int,
    h: int,
    label: str,
) -> None:
    """Render a gray placeholder rectangle with a role label."""
    placeholder = Image.new("RGB", (w, h), _PLACEHOLDER_COLOR)
    canvas.paste(placeholder, (x, y))
    draw = ImageDraw.Draw(canvas)
    font = _load_font(12)
    text = label.upper().replace("-", " ")
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        (x + (w - tw) // 2, y + (h - th) // 2),
        text,
        fill=_LABEL_COLOR,
        font=font,
    )


def _load_font(size: int = 14) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a TrueType font, falling back to default."""
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except OSError:
        pass
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        pass
    return ImageFont.load_default()


def _render_color_palette(
    canvas: Image.Image,
    x: int,
    y: int,
    w: int,
    h: int,
    palette_colors: list[str] | None,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """Render hex color swatches in the palette tile area.

    When *palette_colors* is empty or None, renders a placeholder.
    """
    if not palette_colors:
        _paste_placeholder(canvas, x, y, w, h, "color-palette")
        return

    # Parse hex colors, skip invalid entries
    rgb_colors: list[tuple[int, int, int]] = []
    for c in palette_colors:
        try:
            hex_str = c.strip().lstrip("#")
            if len(hex_str) == 6:
                rgb_colors.append(
                    (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
                )
        except (ValueError, IndexError):
            continue

    if not rgb_colors:
        _paste_placeholder(canvas, x, y, w, h, "color-palette")
        return

    # Render equal-width swatches
    swatch_w = w // len(rgb_colors)
    for i, color in enumerate(rgb_colors):
        sx = x + i * swatch_w
        swatch = Image.new("RGB", (swatch_w, h), color)
        canvas.paste(swatch, (sx, y))
        # Draw hex label centered in swatch (white text on dark, dark on light)
        hex_label = f"#{palette_colors[i].strip().lstrip('#')}"
        luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
        text_color = (255, 255, 255) if luminance < 128 else (30, 30, 30)
        bbox = draw.textbbox((0, 0), hex_label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (sx + (swatch_w - tw) // 2, y + (h - th) // 2),
            hex_label,
            fill=text_color,
            font=font,
        )


def _write_sheet_manifest(
    sheet_path: Path,
    sheet_id: str,
    sheet_type: str,
    dimensions: tuple[int, int],
    frames: dict[str, Path],
    tiles: dict[str, tuple[int, int, int, int]],
) -> None:
    """Write a .sheet.json manifest alongside the composite PNG."""

    from film_pipeline.schemas.reference import CompositeSheetManifest, TileEntry

    tile_entries: list[TileEntry] = []
    placeholders: list[str] = []

    for role, pos in tiles.items():
        fp = frames.get(role)
        if fp and fp.exists():
            tile_entries.append(
                TileEntry(
                    tile_name=role,
                    frame_reference_id=fp.stem,
                    frame_path=str(fp),
                    position=pos,
                )
            )
        else:
            placeholders.append(role)

    manifest = CompositeSheetManifest(
        sheet_id=sheet_id,
        sheet_type=sheet_type,
        sheet_path=str(sheet_path),
        dimensions=dimensions,
        tiles=tile_entries,
        placeholder_tiles=placeholders,
    )
    manifest_path = Path(str(sheet_path) + ".sheet.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json(indent=2))


def _parse_palette(hex_strings: list[str]) -> list[tuple[int, int, int]]:
    """Parse hex strings to RGB tuples, defaulting to gray on failure."""
    result: list[tuple[int, int, int]] = []
    for c in hex_strings:
        try:
            h = c.strip().lstrip("#")
            if len(h) == 6:
                result.append((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)))
                continue
        except (ValueError, IndexError):
            pass
        result.append((180, 180, 190))
    return result
