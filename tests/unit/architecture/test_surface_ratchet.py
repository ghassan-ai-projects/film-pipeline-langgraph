"""The public-surface ratchet: a package's reachable surface may not grow silently.

## What this enforces, and why it is a ratchet rather than a rule

The user's request was "make sure we have public interfaces for the modules, and
nothing outside those interfaces is accessible, enforced by tool or script."

Measured reality, which shapes what is honest to enforce:

- **The package roots are already closed.** Across the 33 packages that declare
  `__all__`, there are **zero** public names reachable off the root beyond the
  declared ones and the recorded import artifacts — checked, not assumed. Every
  declared name resolves. So "nothing outside the interface is reachable *at the
  root*" already holds.
- **Submodule paths are the real surface.** 530 cross-package imports go through
  a submodule (`from film_pipeline.schemas.base import FilmPhase`) against 84
  through a package root. For a 36-module package, the submodules *are* the API; a
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

Four packages declare no surface: `cli`, `orchestration` (the LangGraph engine),
`orchestration.subgraphs` (whose `__init__` is a docstring), and `studio` (the
composition root). They are reached by submodule in 25 cross-package import statements.
Forcing a root `__all__` on `orchestration` would make importing it eagerly
load the graph and `langgraph` — `test_bare_package_roots.py` measures that
directly. Instead each must declare a *reason*, in this file, and the reason is
checked: a package with no `__all__` and no declared reason fails. A bare root's
surface is then graded by its public module count *and* by `BARE_ROOT_SYMBOLS`,
which records the public symbols reachable on the root itself.
"""

from __future__ import annotations

import importlib
import types

from tests.unit.architecture._surface_baseline import (
    ARTIFACT_NAMES,
    BARE_ROOT_REASONS,
    BARE_ROOT_SYMBOLS,
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
    """Adding a module to a package widens what consumers can import from it.

    Only *growth* fails. A shrink is not a widening, and the earlier `!=` form
    reported one as if it were — deleting a module (as
    `docs/modularity-improvements/03` did to four of them) failed this guard with
    "count grew". A count that moves down is the ratchet working, so it is
    re-measured into the baseline deliberately, not treated as a regression.
    """
    actual = {package: len(public_module_names(package)) for package in packages()}
    grown = {
        package: (SURFACE_BASELINE[package].modules, count)
        for package, count in actual.items()
        if package in SURFACE_BASELINE and count > SURFACE_BASELINE[package].modules
    }
    shrank = {
        package: (SURFACE_BASELINE[package].modules, count)
        for package, count in actual.items()
        if package in SURFACE_BASELINE and count < SURFACE_BASELINE[package].modules
    }
    assert not grown, (
        f"public module count grew (baseline -> actual): {grown}. If the new module "
        "is meant to be importable by other packages, raise the baseline in "
        "_surface_baseline.py; if not, prefix it with an underscore."
    )
    _assert_shrunk_rows_are_recorded(shrank, what="public modules")


def test_exported_name_count_has_not_grown() -> None:
    """Adding an exported name is a public-API change, so it must be deliberate."""
    grown: dict[str, tuple[int, int]] = {}
    shrank: dict[str, tuple[int, int]] = {}
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
        elif len(declared) < baseline.names:
            shrank[package] = (baseline.names, len(declared))
    assert not grown, (
        f"declared surface grew (baseline -> actual): {grown}. A widening of __all__ "
        "is a public-interface change: raise the baseline deliberately, in the same "
        "commit that adds the name."
    )
    _assert_shrunk_rows_are_recorded(shrank, what="declared names")


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


def test_bare_package_roots_gain_no_public_symbols() -> None:
    """A bare root's *symbols* are a surface too, and the module count cannot see them.

    `test_undeclared_public_module_count_has_not_grown` grades only how many
    public modules a bare package has, so a public function or class added to
    `studio/__init__.py` left that count untouched and was graded by nothing:
    `test_no_package_leaks_an_undeclared_symbol_off_its_root` `continue`s on a
    package with no `__all__`. An adversarial review demonstrated the escape by
    appending a public function to `studio/__init__.py` and watching every guard
    pass. This closes it with set equality against `BARE_ROOT_SYMBOLS`, so the
    first symbol is a recorded edit in either direction.
    """
    drift: dict[str, tuple[list[str], list[str]]] = {}
    for package, recorded in BARE_ROOT_SYMBOLS.items():
        actual = reachable_public_names(package) - ARTIFACT_NAMES
        added = sorted(actual - recorded)
        removed = sorted(recorded - actual)
        if added or removed:
            drift[package] = (added, removed)
    assert not drift, (
        f"a bare package root's public symbols changed (package -> (added, removed)): "
        f"{drift}. These roots declare no __all__, so a reachable public symbol is "
        "API by default. Import it under a different name, move it to a submodule, "
        "or record it in BARE_ROOT_SYMBOLS in tests/unit/architecture/_surface_baseline.py."
    )


def _assert_shrunk_rows_are_recorded(shrank: dict[str, tuple[int, int]], *, what: str) -> None:
    """A shrink must be recorded in the baseline, not left as silent drift.

    Growth is the ratchet's job; shrinkage is not a regression, so it does not
    fail. But leaving the baseline above the real number would let that much
    growth back in unnoticed — the same defect `test_recorded_reach_ins_are_not_stale`
    guards against for reach-ins. So this fails until the row is lowered, and the
    message names the exact edit.

    This is what makes the count guards a *ratchet* rather than a "has not changed"
    check: every move, in either direction, is a deliberate edit to the baseline.
    """
    assert not shrank, (
        f"{what} shrank (baseline -> actual): {shrank}. That is the ratchet working, "
        "not a regression — but the baseline must be lowered to match, or the "
        "slack lets that much growth return silently. Edit SURFACE_BASELINE in "
        "tests/unit/architecture/_surface_baseline.py."
    )


def test_the_guard_has_something_to_check() -> None:
    """Guard the guard, and close the escape hatch an absent baseline row opens.

    The count guards look a package up in `SURFACE_BASELINE` and `continue` when
    it is missing, so a **newly added package would be graded by nothing**. An
    adversarial review demonstrated exactly that: a package with a 500-name
    `__all__` and 30 public modules passed all seven guards. The size assertions
    below would not have caught it either (`len(...) >= 15` still held), so the
    set equality is the load-bearing part, not the lengths.
    """
    discovered = set(packages())
    recorded = set(SURFACE_BASELINE)
    ungraded = sorted(discovered - recorded)
    assert not ungraded, (
        f"{ungraded} exist under src/film_pipeline but are absent from SURFACE_BASELINE, "
        "so no count guard grades them. Add a row for each — a package nobody records "
        "is a package nobody checks."
    )
    stale = sorted(recorded - discovered)
    assert not stale, f"SURFACE_BASELINE records {stale}, which no longer exist. Remove the rows."
    assert set(BARE_ROOT_REASONS) <= recorded, (
        "BARE_ROOT_REASONS names a package with no SURFACE_BASELINE row, so its "
        "module count is never checked."
    )
    # A `names=None` row is what `test_exported_name_count_has_not_grown` reads as
    # "this package is bare, skip the name comparison". A row like that on a
    # package that is *not* in BARE_ROOT_REASONS is therefore ungraded for names
    # even after it starts declaring `__all__` — `test_declared_reasons_are_still_needed`
    # only inspects BARE_ROOT_REASONS and never sees it. Exactly the packages with
    # a `None` row may be the ones exempted, and each must carry a reason.
    bare_rows = {package for package, surface in SURFACE_BASELINE.items() if surface.names is None}
    assert bare_rows == set(BARE_ROOT_REASONS), (
        "the packages with a `names=None` baseline row and BARE_ROOT_REASONS must be "
        f"the same set; rows only: {sorted(bare_rows - set(BARE_ROOT_REASONS))}, "
        f"reasons only: {sorted(set(BARE_ROOT_REASONS) - bare_rows)}. A `names=None` "
        "row outside BARE_ROOT_REASONS exempts that package's declared surface from "
        "the name guard with no stated reason."
    )
    assert set(BARE_ROOT_SYMBOLS) == set(BARE_ROOT_REASONS), (
        "BARE_ROOT_SYMBOLS must cover exactly the bare roots in BARE_ROOT_REASONS, "
        f"so every exempted root has its symbol surface graded: "
        f"{sorted(set(BARE_ROOT_REASONS) ^ set(BARE_ROOT_SYMBOLS))} differ."
    )
    assert len(discovered) >= 15, "package discovery found too few packages"
    assert reachable_public_names("schemas"), "no names reachable on a known package"


DECLARED_PRIVATE_EXPORTS: dict[str, int] = {
    "agents.prompt_templates.defaults": 22,
    "mcp.tools.bibles": 1,
    "mcp.tools.generation": 2,
    "orchestration.nodes": 26,
}


def _declared_private_exports() -> dict[str, int]:
    """Count underscore-prefixed names each package declares in its `__all__`."""
    counted: dict[str, int] = {}
    for package in packages():
        declared = declared_surface(package)
        if declared is None:
            continue
        private = [name for name in declared if name.startswith("_")]
        if private:
            counted[package] = len(private)
    return counted


def test_declared_private_exports_do_not_grow() -> None:
    """A package may publish internal names, but not more of them silently.

    Doc 10 B5: 51 underscore-prefixed names are declared exportable across four
    package roots, which is why an earlier draft of that finding called the
    surface dishonest. Measured since: **none of the 51 has a consumer outside its
    own package**, and 36 have no importer at all — 17 of the 22
    `prompt_templates.defaults` agent names, 17 of the 26 `orchestration.nodes`
    graph helpers, and both `mcp.tools.generation` helpers.

    So the honest reading is narrower than "the interfaces lie": these are
    intra-package names that a grouped `__init__` publishes for its own callers,
    with a leading underscore that keeps them out of the *documented* surface. The
    measurement is what was missing, and it is recorded here so the next one is a
    deliberate edit rather than drift.
    """
    actual = _declared_private_exports()
    grew = {
        package: (DECLARED_PRIVATE_EXPORTS.get(package, 0), count)
        for package, count in actual.items()
        if count > DECLARED_PRIVATE_EXPORTS.get(package, 0)
    }
    assert not grew, (
        f"declared private exports grew (recorded -> actual): {grew}. Publishing "
        "another underscore name is allowed if it has a consumer — say which one "
        "in the commit message — otherwise drop the underscore or the export."
    )

    shrank = {
        package: (recorded, actual.get(package, 0))
        for package, recorded in DECLARED_PRIVATE_EXPORTS.items()
        if actual.get(package, 0) < recorded
    }
    assert not shrank, (
        f"declared private exports shrank (recorded -> actual): {shrank}. That is "
        "the ratchet working; lower the recorded value so the slack cannot return."
    )
