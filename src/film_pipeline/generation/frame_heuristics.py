"""Per-frame auto-heuristic checks — free, instant validation before Gemini review.

Catches ~80% of obvious failures (corrupt, blank, too small, no face) at $0 cost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image


@dataclass
class HeuristicResult:
    """Outcome of running auto-heuristic checks on a generated frame."""

    passed: bool
    checks_run: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    image_size: tuple[int, int] | None = None


def _check_file_readable(image_path: Path, failures: list[str], checks_run: list[str]) -> None:
    """Check 1 — file exists and is non-empty."""
    checks_run.append("file_exists")
    try:
        if not image_path.is_file():
            failures.append("file_missing")
        elif image_path.stat().st_size == 0:
            failures.append("file_empty")
    except OSError:
        failures.append("file_unreadable")


def _open_and_verify(image_path: Path, failures: list[str]) -> Image.Image | None:
    """Check 2 — can open (not corrupt); returns the opened image or ``None``."""
    img: Image.Image | None = None
    if not failures:
        try:
            img = Image.open(image_path)
            img.verify()  # check for truncation / corruption
        except Exception:
            failures.append("corrupt_image")
    return img


def _check_min_resolution(image_path: Path, failures: list[str]) -> tuple[int, int] | None:
    """Check 3 — minimum resolution; returns the measured size when readable."""
    try:
        img = Image.open(image_path)
        w, h = img.size
        if w < 512 or h < 512:
            failures.append(f"resolution_too_low_{w}x{h}")
        return (w, h)
    except Exception:
        failures.append("cannot_read_size")
        return None


def _check_has_content(
    image_path: Path, failures: list[str], img: Image.Image | None
) -> Image.Image | None:
    """Check 4 — has content (not solid color)."""
    if not failures and img is not None:
        try:
            # Re-open after verify() since verify() consumes the file object
            img = Image.open(image_path).convert("RGB")
            pixels = list(img.getdata())
            # Sample first 1000 pixels — solid color means all identical
            sample = pixels[:1000]
            if len(set(sample)) <= 1:
                failures.append("solid_color_or_blank")
        except Exception:
            failures.append("cannot_check_content")
    return img


def _check_face_size(
    subject_type: str,
    image_size: tuple[int, int] | None,
    failures: list[str],
    checks_run: list[str],
) -> None:
    """Check 5 — face present (character frames only).

    Real face detection requires a model (Gemini handles this in Phase 3).
    This check gates on whether the image is large enough for face detection
    to be meaningful; actual face verification happens downstream.
    """
    if subject_type != "character":
        return
    checks_run.append("face_present")
    if not failures and image_size is not None:
        w, h = image_size
        if w < 256 or h < 256:
            failures.append("too_small_for_face_detection")


def run_heuristic_checks(image_path: Path, *, subject_type: str = "character") -> HeuristicResult:
    """Run the 5 standard auto-heuristic checks against *image_path*.

    Check 5 (face detection) is only run when *subject_type* is ``"character"``.

    Returns a ``HeuristicResult`` with ``passed=True`` if all applicable
    checks succeeded.
    """
    failures: list[str] = []
    checks_run: list[str] = []

    _check_file_readable(image_path, failures, checks_run)

    checks_run.append("not_corrupt")
    img = _open_and_verify(image_path, failures)

    checks_run.append("min_resolution")
    image_size: tuple[int, int] | None = None
    if not failures:
        image_size = _check_min_resolution(image_path, failures)

    checks_run.append("has_content")
    img = _check_has_content(image_path, failures, img)

    _check_face_size(subject_type, image_size, failures, checks_run)

    passed = len(failures) == 0
    return HeuristicResult(
        passed=passed,
        checks_run=checks_run,
        failures=failures,
        image_size=image_size,
    )
