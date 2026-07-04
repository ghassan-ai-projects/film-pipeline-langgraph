"""Open files with the system default application."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def open_path(path: str | Path) -> None:
    """Open a file or directory with the OS default handler.

    Raises:
        RuntimeError: when no suitable opener is available or the path does not exist.
    """
    target = Path(path).expanduser()
    if not target.exists():
        raise RuntimeError(f"Path does not exist: {target}")

    system = sys.platform
    if system == "darwin":  # pragma: no cover
        subprocess.run(["open", str(target)], check=False)
    elif system == "win32":  # pragma: no cover
        subprocess.run(["start", "", str(target)], shell=True, check=False)
    else:  # pragma: no cover
        opener = shutil.which("xdg-open")
        if opener is None:
            raise RuntimeError("No xdg-open found; cannot open file externally.")
        subprocess.run([opener, str(target)], check=False)
