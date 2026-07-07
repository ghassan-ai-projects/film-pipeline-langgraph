"""Environment board construction."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from film_pipeline.generation.compositor._layout import (
    _BG_COLOR,
    _BORDER_COLOR,
    _BORDER_WIDTH,
    _LABEL_COLOR,
    _MARGIN,
    _crop_center,
    _load_font,
    _paste_placeholder,
    _render_color_palette,
    _write_sheet_manifest,
)

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
    )
    return output_path
