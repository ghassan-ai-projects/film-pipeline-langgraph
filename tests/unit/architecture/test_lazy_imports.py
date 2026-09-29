"""Function-level ``film_pipeline`` imports are counted and may not grow.

## Why this exists

`docs/modularity-improvements/05-import-hygiene.md` measured the tree and found that
**96% of function-level imports protect no cycle**: of 287 function-level internal
imports, 275 could be moved to module level without creating one. They were there
because someone put them there, and nothing could tell a load-bearing import from a
habit.

It matters because a function-level import *hides an edge from the dependency graph*.
The package census, the acyclicity check and Enola all read the module level, so an
import that could be eager but is not makes the graph a quieter, less true picture
than the code actually is.

## What this guard enforces

Two counts, computed by `measure.py`'s own algorithm — imported here rather than
reimplemented, because a guard that disagrees with the measurement it grades is worse
than no guard — and ratcheted so they may only fall:

- `LAZY_EDGE_CEILING` — every function-level internal import.
- `HOISTABLE_EDGE_CEILING` — those that are **not** cycle-required, i.e. the ones that
  hide an edge with no structural reason to.

The 11 cycle-required edges are the floor: hoisting one closes a cycle, which
`ImportError` proves.

## Why there is no per-import comment any more

This guard used to require every function-level import to carry a `# lazy: <reason>`
comment, and the migration was recorded through those comments. The reasons were
mostly the same two sentences repeated at 29 call sites ("tests patch X at its source
module"), and a comment is a claim that rots: the hoist in `5cc0170` left two of them
asserting a circular import that no longer existed, and two earlier rounds of this
program lost time to written claims that the tree no longer supported.

The reasons now live once, in `AGENTS.md` under *"Function-level imports are
deliberate"*, and the guard counts instead of annotating. This is **stricter** than
what it replaced: the annotation regime allowed a new function-level import as long as
it carried a comment, whereas these ceilings do not move without an edit here.
"""

from __future__ import annotations

import sys
from pathlib import Path

# `measure.py` lives with the review that produced these numbers. Importing it keeps
# this guard and the measurement provably in step; reimplementing the reachability
# walk here would let the two drift, and the drift would be invisible.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "docs" / "modularity-improvements"))

from measure import (  # type: ignore[import-not-found]
    collect_imports,
    package_of,
    reaches,
)

#: Function-level internal imports (edges), across 36 statements. Down from 287 at the
#: branch base `2450616`: the doc 05 hoist took `storage`, `governance`, `cli`,
#: `studio`, `generation`, `post`, `orchestration` and `mcp` to module level.
LAZY_EDGE_CEILING = 42

#: Of those, the ones that are *not* cycle-required: 11 of the 42 are, so 31 remain.
#: These are deliberate — a test patching a name at its source module, an import that
#: would shadow a same-named class, or a module whose import has a side effect. See
#: `AGENTS.md`. Lower this by hoisting, never by editing the number to match a
#: regression.
HOISTABLE_EDGE_CEILING = 31


def _partition() -> tuple[
    dict[str, set[str]], list[tuple[str, str, int]], list[tuple[str, str, int]]
]:
    """Return (eager graph, cycle-required, not-cycle-required) function-level imports."""
    eager, lazy = collect_imports()
    required = [(s, t, n) for s, t, n in lazy if reaches(eager, t, s)]
    hoistable = [(s, t, n) for s, t, n in lazy if (s, t, n) not in required]
    return eager, required, hoistable


def test_the_lazy_import_count_has_not_grown() -> None:
    """Every function-level internal import, ratcheted."""
    _, required, hoistable = _partition()
    total = len(required) + len(hoistable)
    assert total <= LAZY_EDGE_CEILING, (
        f"{total} function-level internal imports, up from the recorded ceiling of "
        f"{LAZY_EDGE_CEILING}. Hoist the import to module level, or — if it genuinely "
        f"cannot be hoisted — lower the ceiling deliberately and say why in the commit "
        f"message. {len(hoistable)} of them are not cycle-required. By package: "
        + _by_package(hoistable)
    )


def test_the_hoistable_count_has_not_grown() -> None:
    """The imports that hide an edge with no structural reason, ratcheted.

    This is the number that measures the work. It may fall and never rise; a value
    below the ceiling is progress, and the ceiling should be lowered to meet it.
    """
    _, _, hoistable = _partition()
    assert len(hoistable) <= HOISTABLE_EDGE_CEILING, (
        f"{len(hoistable)} function-level imports are not cycle-required, up from the "
        f"recorded ceiling of {HOISTABLE_EDGE_CEILING}. By package: " + _by_package(hoistable)
    )


def test_the_cycle_required_floor_is_real() -> None:
    """Guard the guard: cycle-requiredness must be computed, not assumed.

    If `reaches` returned False always, `HOISTABLE_EDGE_CEILING` would swallow all 42
    edges and the ratchet would stop measuring anything. The floor is 11 edges, each
    of which raises `ImportError` when hoisted.
    """
    _, required, hoistable = _partition()
    assert len(required) >= 10, (
        f"only {len(required)} function-level imports look cycle-required; the "
        "reachability walk is probably not reading the graph."
    )
    assert not set(required) & set(hoistable), "the partition overlaps"


def test_the_guard_has_something_to_check() -> None:
    """Guard the guard: a broken collector would report zero and pass.

    The ceilings above are only meaningful if `collect_imports` actually reads the
    tree — a collector that returned nothing would make both trivially satisfiable.
    """
    eager, lazy = collect_imports()
    assert len(lazy) > 30, (
        f"only {len(lazy)} function-level internal imports found; the collector is "
        "probably not reading the tree, which would make the ceilings vacuous."
    )
    assert len(eager) > 100, f"only {len(eager)} modules in the eager graph"


def _by_package(edges: list[tuple[str, str, int]]) -> str:
    import collections

    counts = collections.Counter(package_of(source) for source, _, _ in edges)
    return ", ".join(f"{pkg}={n}" for pkg, n in counts.most_common())
