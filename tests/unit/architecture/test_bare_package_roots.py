"""The three deliberately-bare package roots must stay import-light.

## Why these three declare no ``__all__``

`test_public_surface.py` enforces that a cross-package consumer cannot import a
name a package did not declare. It skips packages with no `__all__` — and three
packages have none on purpose:

- `cli` — a command-line entry package; consumers invoke commands, not symbols.
- `orchestration` — the LangGraph engine. A root `__all__` naming its nine
  submodules would make `import film_pipeline.orchestration` eagerly load the
  graph, and `langgraph` with it.
- `studio` — the composition root; it wires, it does not export.

`test_public_surface.py` records that reasoning in prose. Prose cannot fail, so
this file turns it into a property: **importing one of these roots must load no
submodule of it and must not import `langgraph`.** That is the concrete cost an
accidental `__all__` would impose, and it is what the prose is protecting.

## Scope, stated honestly

This checks *import weight*, not surface. It says nothing about whether these
packages should have a surface — only that adding one must not make the import
eager. If a future change genuinely needs a root `__all__` here, it can: make the
members lazily available (module `__getattr__`) and this guard still passes; or
accept the eager import and record why in the allow-list below, which is a
deliberate edit rather than a silent regression.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]

#: Package roots with no ``__all__`` whose lightness is deliberate.
BARE_PACKAGE_ROOTS = ("cli", "orchestration", "studio")

#: Modules a bare root must not pull in when imported. `langgraph` is the heavy
#: one; the graph engine lives under `orchestration`, so an eager root import
#: would load the whole engine to import a constant.
_FORBIDDEN_ON_IMPORT = ("langgraph",)

_PROBE = """
import sys

before = set(sys.modules)
import film_pipeline.{package}  # noqa: F401
after = set(sys.modules)

new_submodules = sorted(
    name for name in after - before
    if name.startswith("film_pipeline.{package}.")
)
heavy = sorted(
    name for name in after - before
    if any(part in name for part in {forbidden!r})
)
print("SUBMODULES:" + ",".join(new_submodules))
print("HEAVY:" + ",".join(heavy))
"""


def _probe(package: str) -> tuple[list[str], list[str]]:
    """Import *package* in a fresh interpreter; return (submodules, heavy deps)."""
    result = subprocess.run(
        [sys.executable, "-c", _PROBE.format(package=package, forbidden=_FORBIDDEN_ON_IMPORT)],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
    )
    assert result.returncode == 0, f"importing film_pipeline.{package} failed:\n{result.stderr}"
    submodules: list[str] = []
    heavy: list[str] = []
    for line in result.stdout.splitlines():
        if line.startswith("SUBMODULES:"):
            submodules = [n for n in line.removeprefix("SUBMODULES:").split(",") if n]
        elif line.startswith("HEAVY:"):
            heavy = [n for n in line.removeprefix("HEAVY:").split(",") if n]
    return submodules, heavy


@pytest.mark.parametrize("package", BARE_PACKAGE_ROOTS)
def test_bare_root_loads_no_submodule(package: str) -> None:
    """Importing the root must not drag in its submodules.

    This is what makes the missing `__all__` a deliberate design rather than an
    oversight: the root binds nothing, so nothing is loaded.
    """
    submodules, _ = _probe(package)
    assert submodules == [], (
        f"importing film_pipeline.{package} loaded {submodules}. This root is "
        f"deliberately bare (see this module's docstring); if it must now export "
        f"names, keep the import lazy with a module-level __getattr__, or record "
        f"the eager import here with a reason."
    )


@pytest.mark.parametrize("package", BARE_PACKAGE_ROOTS)
def test_bare_root_does_not_import_langgraph(package: str) -> None:
    """The graph engine must not load just because a root was imported."""
    _, heavy = _probe(package)
    assert heavy == [], (
        f"importing film_pipeline.{package} pulled in {heavy}. A bare root exists "
        f"partly to keep this off the import path."
    )


def test_the_bare_roots_are_still_bare() -> None:
    """If one of these gains an ``__all__``, this file should be revisited.

    Not a failure in itself — but the guard above only means something while the
    package really is bare, so the assumption is asserted rather than assumed.
    """
    for package in BARE_PACKAGE_ROOTS:
        init = _REPO_ROOT / "src" / "film_pipeline" / package / "__init__.py"
        assert init.exists(), f"{package} has no __init__.py"
        source = init.read_text()
        assert "__all__" not in source, (
            f"film_pipeline.{package} now declares __all__; either remove it or "
            f"move {package} out of BARE_PACKAGE_ROOTS so the surface guard grades it."
        )
