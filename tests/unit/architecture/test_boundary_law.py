"""The dependency boundaries this repository actually enforces.

## Why this file is not the target-architecture layer law

`docs/modular-architecture/03-target-architecture.md` declares a per-package
**Allowed outbound** set, and an earlier version of this guard graded every
import against it — freezing 73 edges as debt to burn down. That was wrong, and
the document itself says so in its own header:

    Review status (2026-09-25): superseded proposal. The independent review in
    06 does not adopt the 20-module catalog or its dependency law as an
    implementation mandate.

`06-independent-review-and-decision.md` section 4 is explicit about what to
enforce:

    This is an ownership map, not a prohibition on ordinary package imports.
    Tighten a dependency only when it removes a proven cycle or unsafe reach-in.

So this file enforces the boundaries the project has actually adopted, and
records the superseded law as an observation rather than a target:

1. **No cross-package private reach-in.** Importing another package's
   underscore-prefixed module is the one import shape `06` names as worth
   tightening ("or unsafe reach-in"), and it is a real encapsulation break, not
   a diagram preference. Guarded and ratcheted.
2. **The port's mirrored privates stay in the port.** `operations/ports.py`
   deliberately mirrors two `StudioRuntime` private method names so the port can
   describe the surface it adapts; nothing else may call them.
3. **No writes to another package's private module attributes.** The same
   encapsulation break as a private import, from the writing side, and invisible
   to a guard that reads import statements. Guarded and ratcheted.
4. **A recorded census of imports the superseded law would forbid.** Reported,
   never failing — so the number stays measurable if that decision is revisited,
   and so nobody mistakes its absence for a clean bill of health.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src" / "film_pipeline"

# Cross-package reach-ins into private modules, frozen 2026-09-26.
# `06` section 4 endorses tightening these ("unsafe reach-in"). Lower a count
# when you remove one; delete the row at zero. Never raise one.
KNOWN_PRIVATE_REACH_INS: dict[tuple[str, str], int] = {
    # `_persistence` — investigated 2026-09-26 and kept, with a reason tighter than
    # "not urgent". `mcp/server.py` needs the configured runtime root to place its
    # log file before any runtime exists. The function it calls has since been
    # reshaped (`configured_runtime_root` -> `Path | None`, plus
    # `runtime_root_from_config`), which removed a duplicated env read, but the
    # import still names a private module. Moving the resolver to a public module is
    # a real option; it is left here because the reach-in is one call site at
    # process start and no defect follows from it.
    ("mcp", "studio._persistence"): 1,
    # `_operator_runtime` — the profile-provider composition root. The row is
    # legitimate; the reason it used to give here named `OperatorService`,
    # `StudioRuntimeProvider` and a provider composition that have all been deleted.
    # What `mcp` actually imports is `register_profile_providers`, which selects and
    # builds the adapters a profile stack names — composition-root policy that
    # `operations` cannot supply without importing `studio` (the mutual dependency
    # `operations/ports.py` exists to prevent). The `mcp`-side callers were
    # collapsed into `mcp/tools/helpers.py`, so this is one module-level crossing.
    ("mcp", "studio._operator_runtime"): 1,
    # The `studio -> orchestration._repair_loop` row is gone: graph execution moved
    # into `orchestration/execution.py` (doc 02 slice 3), so the phase-node table is
    # now read from inside its own package and `studio` no longer names it at all.
}

# Private *symbols* imported across a package boundary. A narrower concern than a
# private module: these are individual underscore-prefixed functions or values,
# not whole modules, so the encapsulation break is real but smaller. Tracked
# separately rather than folded into the row above, because conflating the two
# would let a genuine module-level reach-in hide inside a symbol count.
#
# All of these were invisible until the detector was widened to read imported names
# and not just module paths — see the docstring on `_measure_private_reach_ins`.
KNOWN_PRIVATE_SYMBOL_IMPORTS: dict[tuple[str, str], int] = {
    # `agents` re-exports these two from `providers.http_transport` under the
    # historical alias form, deliberately, so old import paths keep working.
    # Retiring the aliases is a separate, consumer-visible change.
    ("agents", "providers._accepts_timeout_kw"): 1,
    ("agents", "providers._open_with_timeout"): 1,
    # `studio` reaches orchestration internals: the services context variable it
    # sets and resets around graph runs, and the validator runner. These are the
    # composition root driving the graph, which is its job, but it does so
    # through private names rather than a declared seam.
    #
    # Three rows were here: the phase-node table (moved to a private *module*
    # reach-in by `resolved_phase_node`), `_SERVICES_CTX` and `_run_validators`.
    # All three are gone with doc 02 slice 3 — `_graph_exec` was 3 of the 5
    # cross-package private reach-ins in the tree precisely because it needed
    # orchestration's internals to execute the graph, and it now lives in
    # `orchestration/execution.py` where they are not reach-ins at all.
}

# Assignments to another package's private module attributes, frozen 2026-09-27.
# **Empty on purpose.** `cli/driver.setup_runtime` installed its runtime by
# writing `studio.runtime._RUNTIME` and `_RUNTIME_MODE_OVERRIDE`; it now calls the
# owner's public `install_runtime`. If a new write appears, add a public API to
# the owner rather than recording it here — this table exists so an unavoidable
# case is visible, not so ordinary ones can be frozen.
KNOWN_PRIVATE_ATTRIBUTE_WRITES: dict[tuple[str, str], int] = {}

# The private spellings of the runtime's persist/audit methods. `studio` owns
# them and uses these internally; every other package must call the public names
# (`persist_project_state`, `record_audit`), which `RuntimePort` declares.
#
# Only the private spellings are counted. Counting the public ones would flag
# legitimate operator-surface calls and force a table that grows whenever someone
# does the right thing.
_PORT_MIRRORED_PRIVATES = {"_persist_project_state", "_record_audit"}

# Call sites of the runtime's persist/audit methods outside the package that owns
# them, frozen 2026-09-26 and **cleared to zero** on 2026-09-26.
#
# History, because an empty table needs to say why it is empty: `operations/`
# and six `mcp/tools/*` modules used to call `rt._persist_project_state` and
# `rt._record_audit` — private names — while `operations/ports.py` mirrored those
# spellings so the port could describe them. That is a port bypassed by its own
# intended callers. `StudioRuntime` now exposes `persist_project_state` and
# `record_audit` as the public surface (keeping the underscore names as
# in-package aliases, where 24 internal call sites still use them), the port
# declares the public names, and all 8 external call sites were redirected.
#
# If a future change reintroduces an external private call, the count must be
# recorded here rather than silently allowed.
KNOWN_MIRRORED_PRIVATE_CALLS: dict[str, int] = {}


def _film_pipeline_imports(tree: ast.Module) -> list[str]:
    """Every ``film_pipeline...`` module path this file imports."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("film_pipeline"):
                found.append(node.module)
        elif isinstance(node, ast.Import):
            found.extend(a.name for a in node.names if a.name.startswith("film_pipeline"))
    return found


def _source_files() -> list[Path]:
    return [p for p in _SRC.rglob("*.py") if "__pycache__" not in p.parts]


def _measure_private_imports() -> tuple[dict[tuple[str, str], int], dict[tuple[str, str], int]]:
    """Count cross-package imports of private MODULES and of private SYMBOLS.

    Three syntactic forms count, and each earlier version saw fewer:

        from film_pipeline.storage._layout import read_json   # private module
        from film_pipeline.storage import _layout             # private symbol
        import film_pipeline.storage._layout as secret        # bare Import
        from . import _layout                                 # relative

    Widening it to read imported names exposed five real reach-ins it had been
    blind to. Widening it to `ast.Import` (doc 10 B2) exposed none: the tree has
    no bare-import reach-in, so this is a capability the guard lacked, not a
    defect the tree had. The four forms are covered by
    `test_the_reach_in_detector_sees_every_import_form`.

    A relative import (``from . import _layout``) is resolved against the file's
    own package, so it counts when it leaves the package — a form the earlier
    versions skipped entirely by requiring an absolute ``film_pipeline.`` prefix.

    They are returned separately because the severities differ: importing another
    package's whole private module is a larger encapsulation break than importing
    one private function from it.
    """
    modules: dict[tuple[str, str], int] = {}
    symbols: dict[tuple[str, str], int] = {}

    for path in _source_files():
        parts = path.relative_to(_SRC).parts
        source = parts[0] if len(parts) > 1 else None
        if source is None:
            continue
        own_package = ".".join(parts[:-1])

        for module, names in _imported_modules(ast.parse(path.read_text()), own_package):
            if not module.startswith("film_pipeline."):
                continue
            segments = module.split(".")
            owner = segments[1]
            if owner == source:
                continue
            if len(segments) >= 3 and segments[-1].startswith("_"):
                key = (source, f"{owner}.{segments[-1]}")
                modules[key] = modules.get(key, 0) + 1
            for name in names:
                if name.startswith("_"):
                    key = (source, f"{owner}.{name}")
                    symbols[key] = symbols.get(key, 0) + 1

    return modules, symbols


def _imported_modules(tree: ast.Module, own_package: str) -> list[tuple[str, list[str]]]:
    """Every ``(module, imported_names)`` pair one file imports.

    ``ast.Import`` names the module in the alias and imports no name from it;
    ``ast.ImportFrom`` names the module in ``node.module`` — or, for
    ``from . import x``, in the aliases. A relative import is resolved against
    *own_package*, so ``from . import _layout`` inside ``storage`` is
    ``film_pipeline.storage`` importing ``_layout``.
    """
    found: list[tuple[str, list[str]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, []) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                owner = own_package.split(".")
                if node.level > 1:
                    owner = owner[: -(node.level - 1)]
                base = ".".join([*owner, base]) if base else ".".join(owner)
            found.append((base, [alias.name for alias in node.names]))
    return found


def _measure_private_reach_ins() -> dict[tuple[str, str], int]:
    """Private-module reach-ins only (the narrower, older measurement)."""
    return _measure_private_imports()[0]


def _measure_private_symbol_imports() -> dict[tuple[str, str], int]:
    """Private-symbol reach-ins only."""
    return _measure_private_imports()[1]


# --- 1. No cross-package private reach-in ------------------------------------


def test_no_new_private_reach_in() -> None:
    """A package must not import another package's private module."""
    actual = _measure_private_reach_ins()
    new = sorted(set(actual) - set(KNOWN_PRIVATE_REACH_INS))

    assert not new, (
        "these packages import another package's PRIVATE module, and they are "
        f"not recorded: {new}. Import a public module, or add a row to "
        "KNOWN_PRIVATE_REACH_INS with a reason."
    )


def test_known_private_reach_ins_have_not_grown() -> None:
    actual = _measure_private_reach_ins()
    grown = {
        pair: (KNOWN_PRIVATE_REACH_INS[pair], actual[pair])
        for pair in sorted(KNOWN_PRIVATE_REACH_INS)
        if actual.get(pair, 0) > KNOWN_PRIVATE_REACH_INS[pair]
    }
    assert not grown, f"private reach-ins grew (recorded -> actual): {grown}."


def test_recorded_reach_ins_are_not_stale() -> None:
    """A baseline left too high lets that many new reach-ins back in unnoticed."""
    actual = _measure_private_reach_ins()
    stale = {
        pair: (recorded, actual.get(pair, 0))
        for pair, recorded in sorted(KNOWN_PRIVATE_REACH_INS.items())
        if actual.get(pair, 0) < recorded
    }
    assert not stale, f"private reach-ins improved (recorded -> actual): {stale}. Tighten the row."


@pytest.mark.parametrize("pair", sorted(KNOWN_PRIVATE_REACH_INS), ids=lambda p: f"{p[0]}->{p[1]}")
def test_recorded_reach_in_still_exists(pair: tuple[str, str]) -> None:
    assert _measure_private_reach_ins().get(pair, 0) > 0, (
        f"{pair[0]} -> {pair[1]} no longer reaches in; delete its row."
    )


def test_no_new_private_symbol_import() -> None:
    """Private *symbols* imported across a package boundary, tracked separately.

    Kept distinct from the module baseline above: importing another package's
    whole private module is a larger encapsulation break than importing one
    private function from it, and folding them together would let the former hide
    inside the latter's count.
    """
    actual = _measure_private_symbol_imports()
    new = sorted(set(actual) - set(KNOWN_PRIVATE_SYMBOL_IMPORTS))

    assert not new, (
        "these import a PRIVATE symbol from another package: "
        f"{new}. Import a public name, or record it in "
        "KNOWN_PRIVATE_SYMBOL_IMPORTS with a reason."
    )


def test_recorded_private_symbol_imports_have_not_grown() -> None:
    actual = _measure_private_symbol_imports()
    grown = {
        pair: (KNOWN_PRIVATE_SYMBOL_IMPORTS[pair], actual[pair])
        for pair in sorted(KNOWN_PRIVATE_SYMBOL_IMPORTS)
        if actual.get(pair, 0) > KNOWN_PRIVATE_SYMBOL_IMPORTS[pair]
    }
    assert not grown, f"private symbol imports grew (recorded -> actual): {grown}."


def test_recorded_private_symbol_imports_are_not_stale() -> None:
    actual = _measure_private_symbol_imports()
    stale = {
        pair: (recorded, actual.get(pair, 0))
        for pair, recorded in sorted(KNOWN_PRIVATE_SYMBOL_IMPORTS.items())
        if actual.get(pair, 0) < recorded
    }
    assert not stale, (
        f"private symbol imports improved (recorded -> actual): {stale}. Tighten the rows."
    )


def test_the_detector_sees_the_name_form_of_a_reach_in() -> None:
    """Guard the guard: the name form was invisible to an earlier version.

    That version inspected only module paths, so it required three dotted
    segments and could not see `from film_pipeline.<pkg> import _private` at all.
    A probe injecting exactly that shape into a temp tree was not reported. Both
    forms must stay visible.
    """
    name_form = ast.parse("from film_pipeline.storage import _layout")
    hits = [
        alias.name
        for node in ast.walk(name_form)
        if isinstance(node, ast.ImportFrom) and node.module == "film_pipeline.storage"
        for alias in node.names
        if alias.name.startswith("_")
    ]
    assert hits == ["_layout"], (
        "the name form `from film_pipeline.<pkg> import _private` must be visible "
        "to the detector, not only the dotted-path form"
    )


def test_the_reach_in_detector_sees_every_import_form() -> None:
    """Guard the guard: every import spelling that reaches a private module.

    Doc 10 B2 found this detector read only `ast.ImportFrom`, so
    `import film_pipeline.studio._persistence as secret` — a real encapsulation
    break, and the form a developer reaches for when they want a short handle —
    produced no finding. This exercises the detector through the same helper it
    uses in production, over synthetic sources, because the current tree has no
    live instance of the newly covered forms to observe.

    The dynamic forms are listed as *not* covered. That is a stated limit, not an
    oversight: `importlib.import_module("film_pipeline.x._y")` is a runtime string
    and reading it statically would mean evaluating expressions. If one ever
    appears, the guard has to be extended deliberately rather than assumed.
    """
    cases: dict[str, tuple[tuple[str, str], bool]] = {
        "from film_pipeline.storage._layout import read_json": (("storage", "_layout"), True),
        "from film_pipeline.storage import _layout": (("storage", "_layout"), True),
        "import film_pipeline.storage._layout": (("storage", "_layout"), True),
        "import film_pipeline.storage._layout as secret": (("storage", "_layout"), True),
        "from film_pipeline.storage import read_json": (("storage", "read_json"), False),
        "import film_pipeline.storage.manifest as m": (("storage", "manifest"), False),
        "from film_pipeline import storage": (("storage", "storage"), False),
    }
    for source, (expected, should_hit) in cases.items():
        modules, symbols = _measure_private_imports_in(ast.parse(source), "mcp")
        found = {**modules, **symbols}
        key = ("mcp", f"{expected[0]}.{expected[1]}")
        assert (key in found) is should_hit, (
            f"{source!r}: expected {'a finding' if should_hit else 'no finding'} "
            f"for {key}, got {found}"
        )

    # Relative imports resolve against the file's own package, so a relative form
    # that stays inside the package is not a reach-in, and one that leaves it is.
    inside, _ = _measure_private_imports_in(ast.parse("from . import _layout"), "storage")
    assert inside == {}, "a relative import inside the package is not a reach-in"

    # A relative import is resolved against the file's own package. `from .
    # import _layout` inside `storage.sub` names `storage.sub._layout`, which is
    # private to `storage.sub` and therefore not a *cross-package* reach-in: the
    # guard must not report a package reaching into itself.
    self_relative, _ = _measure_private_imports_in(
        ast.parse("from . import _layout"), "storage.sub"
    )
    assert self_relative == {}, "a package reaching into itself is not a reach-in"

    # Leaving the package is what makes it one. `from .. import _layout` inside
    # `storage.sub` names `storage._layout` from package `storage.sub`, so the
    # owner (`storage`) is not the importer's package root (`storage`) — the key
    # is built from the source package's first segment, and `storage` equal
    # `storage` means this is still inside the package. The interesting case is a
    # *different* top-level package, which the absolute cases above already cover.
    foreign, _ = _measure_private_imports_in(ast.parse("import film_pipeline.studio._x"), "mcp")
    assert foreign == {("mcp", "studio._x"): 1}, "a bare private-module import counts"

    dynamic = ast.parse("import importlib\nimportlib.import_module('film_pipeline.studio._p')\n")
    assert _measure_private_imports_in(dynamic, "mcp") == ({}, {}), (
        "dynamic imports are a stated limit of this detector; if this starts "
        "failing, the limit changed and the docstring must say so"
    )


def _measure_private_imports_in(
    tree: ast.Module, source: str
) -> tuple[dict[tuple[str, str], int], dict[tuple[str, str], int]]:
    """Run the reach-in detector's own resolution over one synthetic module.

    Same helpers as `_measure_private_imports` (`_imported_modules`), so this
    cannot drift from production: the only thing the test substitutes is the file
    it reads.
    """
    modules: dict[tuple[str, str], int] = {}
    symbols: dict[tuple[str, str], int] = {}
    for module, names in _imported_modules(tree, source):
        if not module.startswith("film_pipeline."):
            continue
        segments = module.split(".")
        if len(segments) < 2:
            continue
        owner = segments[1]
        if owner == source:
            continue
        if len(segments) >= 3 and segments[-1].startswith("_"):
            modules[(source, f"{owner}.{segments[-1]}")] = 1
        for name in names:
            if name.startswith("_"):
                symbols[(source, f"{owner}.{name}")] = 1
    return modules, symbols


# --- 2. The port's mirrored privates stay in the port -----------------------


def _measure_mirrored_private_calls() -> dict[str, int]:
    """Count external calls to the runtime persist/audit methods, by caller file."""
    counts: dict[str, int] = {}
    for path in _source_files():
        parts = path.relative_to(_SRC).parts
        if len(parts) > 1 and parts[0] == "studio":
            continue
        relative = str(path.relative_to(_SRC))
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in _PORT_MIRRORED_PRIVATES
            ):
                counts[relative] = counts.get(relative, 0) + 1
    return counts


def test_no_new_mirrored_private_call_site() -> None:
    """Only the owner package and the recorded debt may call these privates."""
    actual = _measure_mirrored_private_calls()
    new = sorted(set(actual) - set(KNOWN_MIRRORED_PRIVATE_CALLS))

    assert not new, (
        "these modules call a runtime private from outside the package that owns "
        f"it, and they are not recorded: {new}. `operations/ports.py` mirrors "
        "`_persist_project_state` and `_record_audit` so the port can declare "
        "them; use a public seam, or record the debt with a reason."
    )


def test_mirrored_private_call_debt_has_not_grown() -> None:
    actual = _measure_mirrored_private_calls()
    grown = {
        name: (KNOWN_MIRRORED_PRIVATE_CALLS[name], actual[name])
        for name in sorted(KNOWN_MIRRORED_PRIVATE_CALLS)
        if actual.get(name, 0) > KNOWN_MIRRORED_PRIVATE_CALLS[name]
    }
    assert not grown, f"mirrored-private call debt grew (recorded -> actual): {grown}."


def test_recorded_mirrored_private_calls_are_not_stale() -> None:
    actual = _measure_mirrored_private_calls()
    stale = {
        name: (recorded, actual.get(name, 0))
        for name, recorded in sorted(KNOWN_MIRRORED_PRIVATE_CALLS.items())
        if actual.get(name, 0) < recorded
    }
    assert not stale, (
        f"mirrored-private call debt improved (recorded -> actual): {stale}. Tighten the rows."
    )


# --- 3. The superseded law, recorded rather than enforced -------------------


def _superseded_law_census() -> int:
    """Count imports `03`'s superseded Allowed-outbound law would forbid."""
    document = (
        _REPO_ROOT / "docs" / "modular-architecture" / "03-target-architecture.md"
    ).read_text()

    law: dict[str, set[str] | None] = {}
    for match in re.finditer(r"### 3\.\d+ `(\w+)`[^\n]*\n(.*?)(?=\n### |\Z)", document, re.S):
        package, body = match.group(1), match.group(2)
        outbound = re.search(r"\*\*Allowed outbound\.\*\*\s*(.+?)(?:\n\n|\n- )", body, re.S)
        if outbound is None:
            continue
        raw = " ".join(outbound.group(1).split())
        law[package] = (
            set()
            if raw.startswith("**none**")
            else (None if raw.startswith("every module") else set(re.findall(r"`(\w+)`", raw)))
        )
    assert len(law) >= 15, f"parsed only {len(law)} packages; the document format changed"

    census = 0
    for path in _source_files():
        parts = path.relative_to(_SRC).parts
        source = parts[0] if len(parts) > 1 else None
        if source not in law:
            continue
        allowed = law[source]
        if allowed is None:
            continue
        for module in _film_pipeline_imports(ast.parse(path.read_text())):
            segments = module.split(".")
            if len(segments) > 1 and segments[1] != source and segments[1] not in allowed:
                census += 1
    return census


def test_superseded_layer_law_is_recorded_not_enforced() -> None:
    """Record the superseded law's census, and assert it is still superseded.

    This is an OBSERVATION, not a gate. `06` section 4 declined to adopt the
    law, so failing on these imports would enforce a rejected proposal — and
    `06` says plainly that ordinary package imports are not prohibited.

    The assertion that matters is the header check: if someone re-adopts the law,
    this file must be re-scoped rather than left silently enforcing a stale
    reading in either direction.
    """
    document = (
        _REPO_ROOT / "docs" / "modular-architecture" / "03-target-architecture.md"
    ).read_text()
    assert "superseded proposal" in document[:600], (
        "03's superseded-proposal header is gone. If the layer law was re-adopted, "
        "re-scope this file deliberately instead of inheriting a stale reading."
    )

    census = _superseded_law_census()
    print(f"\n[recorded, not enforced] imports the superseded layer law would forbid: {census}")


# --- 4. No writes to another package's private attributes -------------------


def _measure_private_attribute_writes() -> dict[tuple[str, str], int]:
    """Count writes to another package's ``_``-prefixed module attributes.

    The reach-in guards above count private *imports*: reading another package's
    private name. This counts the write shape, which is the same encapsulation
    break from the other direction and was invisible to every guard here:

        import film_pipeline.studio.runtime as rt_mod
        rt_mod._RUNTIME = rt            # another package's private global
        rt_mod._RUNTIME_MODE_OVERRIDE = mode

    That is what the headless CLI did to install its runtime
    (`docs/modularity-improvements/01`). No import of a private *name* appears —
    the module is public and the attribute is spelled literally — so a guard
    reading import statements cannot see it.

    Scope: assignments and augmented assignments where the target is
    ``<something>._<name>`` and the module part is a bare name (a module handle),
    not ``self`` or a local object. `self._x = y` and `obj._x = y` are ordinary
    encapsulation *within* a class and are not the concern; a module-level
    ``alias._x = y`` is.

    Doc 10 B2 found the handle table was built **only** from `ast.Import`, so

        from film_pipeline.studio import runtime as rt_mod
        rt_mod._RUNTIME = object()

    produced no finding — the same break, spelled with the import form this
    file's other detector reads. Handles now come from `_module_handles`, which
    covers both forms.
    """
    counts: dict[tuple[str, str], int] = {}

    for path in _source_files():
        parts = path.relative_to(_SRC).parts
        source = parts[0] if len(parts) > 1 else None
        if source is None:
            continue

        tree = ast.parse(path.read_text())
        aliases = _module_handles(tree)

        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
            for target in targets:
                if not isinstance(target, ast.Attribute) or not target.attr.startswith("_"):
                    continue
                if not isinstance(target.value, ast.Name):
                    continue  # `self._x` / `obj._x` — in-class, not cross-package
                owner = aliases.get(target.value.id)
                if owner is None or owner == source:
                    continue
                key = (source, f"{owner}.{target.attr}")
                counts[key] = counts.get(key, 0) + 1

    return counts


def _module_handles(tree: ast.Module) -> dict[str, str]:
    """Map each local module handle to the ``film_pipeline`` package it names.

    Both import spellings bind a handle, and each was the other's blind spot at
    some point in this file's history:

        import film_pipeline.studio.runtime as rt_mod       # handle -> "studio"
        from film_pipeline.studio import runtime as rt_mod  # handle -> "studio"

    The second form is the one that hid a write from the earlier detector, so
    both are read whenever the name is aliased (``as``), which is what makes the
    import's target unambiguous; the name is a module handle either way.

    A **bare** name from a dotted `from` import is not recorded, because it is
    ambiguous from syntax alone:

        from film_pipeline.studio import runtime      # a module handle
        from film_pipeline.studio.runtime import install_runtime   # a function

    Only the first can be written to as a module, and no resolution available to
    this detector can tell them apart without importing the target — which a
    static guard must not do. That case is not silently ignored:
    `test_the_write_detector_sees_every_shape_it_was_written_for` asserts the
    limit, so a future author who wants it covered has to resolve it deliberately.

    A handle is only recorded for an absolute ``film_pipeline`` target: a relative
    import resolves against the file's own package and cannot name a *foreign*
    package's private global.
    """
    handles: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                segments = alias.name.split(".")
                if alias.name.startswith("film_pipeline.") and len(segments) >= 2:
                    handles[alias.asname or segments[0]] = segments[1]
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module or not node.module.startswith("film_pipeline."):
                continue
            segments = node.module.split(".")
            if len(segments) < 2:
                continue
            for alias in node.names:
                if alias.name != "*" and alias.asname:
                    handles[alias.asname] = segments[1]
    return handles


def test_no_writes_to_another_packages_private_globals() -> None:
    """A package must not assign another package's private module attributes.

    `cli` used to install its runtime by writing `studio.runtime._RUNTIME` and
    `_RUNTIME_MODE_OVERRIDE`. `studio.runtime.install_runtime` is the public
    replacement; the row table below is empty because the last writer is gone.
    """
    actual = _measure_private_attribute_writes()
    new = sorted(set(actual) - set(KNOWN_PRIVATE_ATTRIBUTE_WRITES))

    assert not new, (
        "these modules assign a private attribute on ANOTHER package's module: "
        f"{new}. Add a public API to the owner (a setter/installer function) and "
        "call that, or record the row in KNOWN_PRIVATE_ATTRIBUTE_WRITES with a "
        "reason if it is genuinely irreducible."
    )


def test_recorded_private_attribute_writes_are_not_stale() -> None:
    actual = _measure_private_attribute_writes()
    stale = {
        pair: (recorded, actual.get(pair, 0))
        for pair, recorded in sorted(KNOWN_PRIVATE_ATTRIBUTE_WRITES.items())
        if actual.get(pair, 0) < recorded
    }
    assert not stale, (
        f"private attribute writes improved (recorded -> actual): {stale}. Tighten the rows."
    )


def test_the_write_detector_sees_every_shape_it_was_written_for() -> None:
    """Guard the guard: the exact shapes the CLI used, in both import spellings.

    Without this, a detector that silently matched nothing would report a clean
    tree forever — the failure mode AGENTS.md names for a guard that "reports
    clean while measuring nothing". The second case is doc 10 B2: the same write
    spelled with `from ... import ... as`, which the earlier handle table did not
    read, so it reported the tree clean while missing the break entirely.
    """
    cases = {
        "import ... as": (
            "import film_pipeline.studio.runtime as rt_mod\nrt_mod._RUNTIME = object()\n"
        ),
        "from ... import ... as": (
            "from film_pipeline.studio import runtime as rt_mod\n"
            "rt_mod._RUNTIME_MODE_OVERRIDE = 'mock'\n"
        ),
        "augmented": "import film_pipeline.studio.runtime as rt_mod\nrt_mod._RUNTIME += 1\n",
        "annotated": (
            "import film_pipeline.studio.runtime as rt_mod\nrt_mod._RUNTIME: object = None\n"
        ),
        # A bare `from ... import x` name is ambiguous from syntax alone (module
        # handle vs function), so it is a stated limit rather than a finding:
        # `_module_handles` records only aliased forms. Asserted, not assumed.
        "from ... import bare name (stated limit)": (
            "from film_pipeline.studio.runtime import install_runtime\n"
            "install_runtime._RUNTIME = object()\n"
        ),
    }
    for name, source in cases.items():
        tree = ast.parse(source)
        aliases = _module_handles(tree)
        hits = [
            (aliases[target.value.id], target.attr)
            for node in ast.walk(tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
            if isinstance(target, ast.Attribute)
            and target.attr.startswith("_")
            and isinstance(target.value, ast.Name)
            and target.value.id in aliases
        ]
        if "stated limit" in name:
            assert hits == [], f"{name}: a function handle is not a module handle: {hits}"
        else:
            assert hits == [("studio", hits[0][1])], f"{name}: not detected: {hits}"
