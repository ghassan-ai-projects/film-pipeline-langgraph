"""The public-surface ratchet: a package's reachable surface may not grow silently.

## What this enforces, and why it is a ratchet rather than a rule

The user's request was "make sure we have public interfaces for the modules, and
nothing outside those interfaces is accessible, enforced by tool or script."

Measured reality, which shapes what is honest to enforce:

- **The package roots are already closed.** Across the 17 packages that declare
  `__all__`, there are **zero** public names reachable off the root that the
  package does not declare — checked, not assumed. Every declared name resolves.
  So "nothing outside the interface is reachable *at the root*" already holds.
- **Submodule paths are the real surface.** 454 cross-package imports go through
  a submodule (`from film_pipeline.schemas.base import FilmPhase`) against 66
  through a package root. For a 38-file package, the submodules *are* the API; a
  107-name root `__all__` is a convenience facade, not the whole contract.
- **Cross-package private reach-in is 2 sites**, both already recorded debt.

Python cannot make a submodule unimportable without an import hook, and the
alternative — rewriting all 454 imports and expanding every `__all__` to match —
is the `03`/`05` program that `06` §4 rejected and an earlier round reverted.

So this guard enforces the property that is both real and falsifiable: **the
surface cannot grow by accident.** A new exported name, a new public module, or a
new cross-package reach-in must be a deliberate edit to the recorded baseline in
`_surface_baseline.py`, where a reviewer sees it.

## What it cannot see

- It records *counts*, not names, for reach-ins. A rename inside a package that
  keeps the counts equal passes. Names are not recorded because the two recorded
  reach-ins are already tracked precisely by `test_boundary_law.py`, which names
  the exact modules; duplicating that here would give one concern two owners.
- It says nothing about *semantic* belonging: a package can add a public module
  that no consumer uses and this will only see growth, not the absence of a reason.
- It does not grade whether a consumer *should* have imported something. `06`
  decided ordinary package imports are not a defect, and this guard does not
  reopen that.

## Why `__all__` is not required everywhere

Three packages declare no surface: `cli`, `orchestration` (the LangGraph engine),
and `studio` (the composition root). They are reached by submodule 35 times in
total. Forcing a root `__all__` on `orchestration` would make importing it eagerly
load the graph and `langgraph` — `test_bare_package_roots.py` measures that
directly. Instead each must declare a *reason*, in this file, and the reason is
checked: a package with no `__all__` and no declared reason fails.
"""

from __future__ import annotations

import importlib
import types

from tests.unit.architecture._surface_baseline import (
    ARTIFACT_NAMES,
    BARE_ROOT_REASONS,
    SURFACE_BASELINE,
)
from tests.unit.architecture._surface_scan import (
    declared_surface,
    packages,
    public_module_names,
    reachable_public_names,
)


def test_every_package_declares_a_surface_or_a_reason() -> None:
    """A package must either declare `__all__` or say why it does not.

    This is the "make sure we have public interfaces" half. It does not demand an
    `__all__` from a package that must stay bare — it demands that the absence be
    a stated decision rather than an omission.
    """
    undeclared = [
        package
        for package in packages()
        if declared_surface(package) is None and package not in BARE_ROOT_REASONS
    ]
    assert not undeclared, (
        f"{undeclared} declare no __all__ and no reason. Either declare a surface, "
        f"or add the package to BARE_ROOT_REASONS in "
        f"tests/unit/architecture/_surface_baseline.py explaining why it must not."
    )


def test_declared_reasons_are_still_needed() -> None:
    """A bare root that gains an `__all__` should leave the reason list.

    The inverse of the check above: a stale exemption would let a package skip the
    surface discipline after it stopped needing to.
    """
    stale = [package for package in BARE_ROOT_REASONS if declared_surface(package) is not None]
    assert not stale, (
        f"{stale} now declare __all__ but are still listed in BARE_ROOT_REASONS. "
        "Remove them so the surface guard grades them."
    )


def test_no_package_leaks_an_undeclared_symbol_off_its_root() -> None:
    """A public name on the package root must be declared, or be an import artifact.

    This is the part of "nothing outside the interface is accessible" that holds
    at the root. It passes today with zero findings — it is here so that a new
    re-export that skips `__all__` fails loudly instead of quietly widening the
    surface. Import artifacts (`typing.Any`, `from __future__ import annotations`)
    are excluded by name because they are not the package's own API.
    """
    leaks: dict[str, list[str]] = {}
    for package in packages():
        declared = declared_surface(package)
        if declared is None:
            continue
        module = importlib.import_module(f"film_pipeline.{package}")
        public = {
            name
            for name in dir(module)
            if not name.startswith("_") and not isinstance(getattr(module, name), types.ModuleType)
        }
        extra = sorted(public - declared - ARTIFACT_NAMES)
        if extra:
            leaks[package] = extra

    assert not leaks, (
        f"public names reachable off a package root without being declared: {leaks}. "
        "Add them to __all__, or stop re-exporting them."
    )


def test_module_count_has_not_grown() -> None:
    """Adding a module to a package widens what consumers can import from it."""
    actual = {package: len(public_module_names(package)) for package in packages()}
    grown = {
        package: (SURFACE_BASELINE[package].modules, count)
        for package, count in actual.items()
        if package in SURFACE_BASELINE and count > SURFACE_BASELINE[package].modules
    }
    assert not grown, (
        f"public module count grew (baseline -> actual): {grown}. If the new module "
        "is meant to be importable by other packages, raise the baseline in "
        "_surface_baseline.py; if not, prefix it with an underscore."
    )


def test_exported_name_count_has_not_grown() -> None:
    """Adding an exported name is a public-API change, so it must be deliberate."""
    grown: dict[str, tuple[int, int]] = {}
    for package in packages():
        declared = declared_surface(package)
        if declared is None:
            continue
        baseline = SURFACE_BASELINE.get(package)
        if baseline is None or baseline.names is None:
            # `baseline.names is None` means the baseline recorded this package as
            # bare, but it now declares `__all__`. That transition is caught by
            # `test_declared_reasons_are_still_needed`, which owns it; comparing
            # counts here would be a type error and a duplicate report.
            continue
        if len(declared) > baseline.names:
            grown[package] = (baseline.names, len(declared))
    assert not grown, (
        f"declared surface grew (baseline -> actual): {grown}. A widening of __all__ "
        "is a public-interface change: raise the baseline deliberately, in the same "
        "commit that adds the name."
    )


def test_undeclared_public_module_count_has_not_grown() -> None:
    """A package with no `__all__` still has a surface: its public modules."""
    grown: dict[str, tuple[int, int]] = {}
    for package in BARE_ROOT_REASONS:
        baseline = SURFACE_BASELINE.get(package)
        if baseline is None:
            continue
        actual = len(public_module_names(package))
        if actual > baseline.modules:
            grown[package] = (baseline.modules, actual)
    assert not grown, (
        f"a bare package root grew new public modules (baseline -> actual): {grown}. "
        f"It has no __all__, so its public modules are its interface by default. "
        f"Prefix new modules with an underscore, or record the growth."
    )


def test_the_guard_has_something_to_check() -> None:
    """Guard the guard: an empty sweep would pass while proving nothing."""
    assert len(packages()) >= 15, "package discovery found too few packages"
    assert len(SURFACE_BASELINE) >= 15, "the baseline covers too few packages"
    assert len(BARE_ROOT_REASONS) >= 3, "the bare-root reasons went missing"
    assert reachable_public_names("schemas"), "no names reachable on a known package"
