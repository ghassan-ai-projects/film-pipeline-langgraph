"""Point film-pipeline storage at ``.scratch/`` for one-off developer scripts.

Dev scripts run from the repo root; without this they would create real
projects inside the repository or in ``~/.film-pipeline``. Call
``use_scratch_roots()`` after ``os.chdir`` and before creating a runtime.
Artifacts land under ``.scratch/runtime/artifacts``. ``make scratch-clean``
removes the whole directory.
"""

from __future__ import annotations

import os
from pathlib import Path


def use_scratch_roots() -> Path:
    """Redirect runtime and storage roots to the repo's ``.scratch/`` tree.

    Returns the scratch artifacts directory (the runtime root's ``artifacts``
    subtree) so scripts clean up the same location they write to.
    """
    scratch = Path(".scratch").resolve()
    os.environ.setdefault("FILM_PIPELINE_STORAGE_ROOT", str(scratch / "storage"))
    os.environ.setdefault("FILM_PIPELINE_RUNTIME_ROOT", str(scratch / "runtime"))
    return scratch / "runtime" / "artifacts"
