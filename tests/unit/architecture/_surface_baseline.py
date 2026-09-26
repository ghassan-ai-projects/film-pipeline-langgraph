"""The recorded public surface of every package, and why three declare none.

## How to read this

`SURFACE_BASELINE` is a ratchet, not a target. It records what each package
exposes today so that a *widening* is a deliberate edit a reviewer sees, rather
than something that slips in. Growth is not forbidden — it is required to be
recorded in the same commit that causes it.

- `names` — the size of the package's declared `__all__`, or `None` when the
  package declares none.
- `modules` — the count of public (non-underscore) modules under the package.
  This is the surface of a package with no `__all__`, since its modules are what
  consumers import from.

Numbers were measured with `tests/unit/architecture/_surface_scan.py`, which
resolves surfaces from imported modules rather than by parsing AST. That matters:
an AST literal parser read `mcp/tools`'s computed `__all__` as `None`, silently
skipping 77 declared names.

## Why three packages declare no `__all__`

`BARE_ROOT_REASONS` is checked by the guard: a package with no `__all__` and no
entry here fails, so the absence is a stated decision rather than an oversight.
Each reason is falsifiable — `test_bare_package_roots.py` measures the property
each one claims (no eager submodule load, no `langgraph` on the import path).

Adding `__all__` to any of these is not forbidden, but it is not free: for
`orchestration` it would eagerly load the graph. The sanctioned path if one ever
needs to export is a module-level `__getattr__`, which keeps the import lazy.
"""

from __future__ import annotations

from typing import NamedTuple


class Surface(NamedTuple):
    """A package's recorded surface: declared names and public modules."""

    names: int | None
    modules: int


#: package -> (declared `__all__` size or None, public module count).
SURFACE_BASELINE: dict[str, Surface] = {
    "agents": Surface(5, 28),
    "checkpoints": Surface(8, 6),
    "cli": Surface(None, 4),
    "config": Surface(15, 6),
    "constraints": Surface(4, 1),
    "devharness": Surface(4, 5),
    "filmspec": Surface(22, 0),
    "generation": Surface(18, 15),
    "governance": Surface(12, 11),
    "kb": Surface(4, 6),
    "mcp": Surface(14, 37),
    "operations": Surface(23, 5),
    "orchestration": Surface(None, 14),
    "post": Surface(13, 6),
    "projects": Surface(10, 2),
    "providers": Surface(18, 13),
    "schemas": Surface(107, 36),
    "storage": Surface(38, 12),
    "studio": Surface(None, 9),
    "validation": Surface(7, 11),
}

#: Package roots that deliberately declare no `__all__`, with the reason.
BARE_ROOT_REASONS: dict[str, str] = {
    "cli": (
        "A command-line entry package: consumers invoke console commands, not "
        "symbols from its root. It is imported by nothing in src/, so a root "
        "surface would exist only to be declared."
    ),
    "orchestration": (
        "The LangGraph execution engine. A root `__all__` naming its submodules "
        "would make `import film_pipeline.orchestration` eagerly load the graph "
        "and pull in `langgraph` — measured by `test_bare_package_roots.py`. 25 "
        "cross-package imports reach its submodules directly, so a facade would "
        "also have to re-export the engine it exists to keep lazy."
    ),
    "studio": (
        "The composition root: it wires other packages together and owns no "
        "vocabulary of its own. `__version__` is the only root binding, and it is "
        "not part of any consumer's contract. 10 cross-package imports reach its "
        "submodules directly."
    ),
}

#: Public names that appear on a package root only because the package imported
#: them for its own use (`from __future__ import annotations`, `typing.Any`,
#: `enum.StrEnum`, ...). These are not the package's API, so the guard excludes
#: them by name rather than forcing them into `__all__`.
ARTIFACT_NAMES: frozenset[str] = frozenset(
    {
        "ABC",
        "Any",
        "Callable",
        "Enum",
        "Field",
        "Iterable",
        "Mapping",
        "Protocol",
        "Sequence",
        "StrEnum",
        "TYPE_CHECKING",
        "UTC",
        "annotations",
        "datetime",
        "re",
        "cast",
    }
)
