"""Composite sheet construction — Pillow-based templates for reference sheets.

Builds production-ready composite sheets (Character Identity, Environment Board)
from generated master frames. Pure image processing — no AI involved.
"""

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
        _CHAR_LABELS,
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


# ── Environment Board ─────────────────────────────────────────────────────

_ENV_SHEET_SIZE = (3840, 2160)

_ENV_TILES: dict[str, tuple[int, int, int, int]] = {
    "wide-establishing": (_MARGIN, 60, 1920, 1080),
    "alt-angle-desk": (1944, 60, 960, 540),
    "alt-angle-corner": (1944, 608, 960, 540),
    "lighting-cool-night": (_MARGIN, 1148, 960, 540),
    "lighting-golden-afternoon": (976, 1148, 960, 540),
    "detail-texture": (1944, 1156, 480, 480),
    "detail-prop": (2432, 1156, 480, 480),
    "color-palette": (_MARGIN, 1696, 1880, 100),
}

_ENV_LABELS: dict[str, str] = {
    "wide-establishing": "WIDE ESTABLISHING (CANONICAL)",
    "alt-angle-desk": "ALT — DESK",
    "alt-angle-corner": "ALT — CORNER",
    "lighting-cool-night": "COOL NIGHT",
    "lighting-golden-afternoon": "GOLDEN AFTERNOON",
    "detail-texture": "TEXTURE DETAIL",
    "detail-prop": "PROP DETAIL",
    "color-palette": "COLOR PALETTE",
}


def build_environment_board(
    subject_id: str,
    environment_name: str,
    frames: dict[str, Path],
    output_path: Path,
    *,
    palette_colors: list[str] | None = None,
) -> Path:
    """Build an Environment Board composite.

    Same architecture as Character Identity Sheet — different template dimensions
    and tile layout.

    Args:
        palette_colors: Optional hex color strings (e.g. ``["#1a1a2e", "#e94560"]``)
                        from the EnvironmentBible. Rendered as swatches in the
                        ``color-palette`` tile area.
    """
    canvas = Image.new("RGB", _ENV_SHEET_SIZE, _BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    font = _load_font(16)

    title = f"ENVIRONMENT BOARD — {subject_id.upper()} — {environment_name}"
    draw.text((_MARGIN, 8), title, fill=_LABEL_COLOR, font=font)
    draw.line([(_MARGIN, 42), (_ENV_SHEET_SIZE[0] - _MARGIN, 42)], fill=_BORDER_COLOR, width=1)

    for role, (x, y, w, h) in _ENV_TILES.items():
        draw.rectangle(
            [x - 1, y - 1, x + w + 1, y + h + 1],
            outline=_BORDER_COLOR,
            width=_BORDER_WIDTH,
        )

        if role == "color-palette":
            _render_color_palette(canvas, x, y, w, h, palette_colors, draw, font)
        else:
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

        label = _ENV_LABELS.get(role, role.upper().replace("-", " "))
        label_y = y + h + 2
        if label_y + 16 < _ENV_SHEET_SIZE[1]:
            draw.text((x + 2, label_y), label, fill=_LABEL_COLOR, font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG")
    _write_sheet_manifest(
        output_path,
        subject_id,
        "environment_board",
        _ENV_SHEET_SIZE,
        frames,
        _ENV_TILES,
        _ENV_LABELS,
    )
    return output_path


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
    labels: dict[str, str],  # noqa: ARG001
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
