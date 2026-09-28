"""Every function-level ``film_pipeline`` import must justify itself.

## The finding

`docs/modularity-improvements/05-import-hygiene.md` measured the tree and found that
**96% of function-level imports protect no cycle**: of 287 function-level internal
imports, 275 could be moved to module level without creating one. The imports were
there because someone put them there, and nothing could tell the difference between
one that was load-bearing and one that was habit.

That matters because a lazy import *hides an edge from the dependency graph* — the
package census, the acyclicity check and Enola all read the module level, so an
import that could be eager but is not makes the graph a quieter, less true picture
than the code actually is.

## What this guard enforces

A function-level `film_pipeline` import is allowed in exactly two cases:

1. **It is cycle-required** — the target can already reach the source through eager
   edges, so hoisting would close a cycle. Computed with `measure.py`'s own
   algorithm, imported here rather than reimplemented: a guard that disagrees with
   the measurement it grades is worse than no guard.
2. **It carries a `# lazy:` comment on the same line or the line above** — an
   explicit, reviewable reason. `# lazy: defers langgraph` and
   `# lazy: cycle via orchestration` are both acceptable; a bare suppression is not,
   because the whole point is that the reason is written down.

## The ratchet

`HOISTABLE_CEILING` is the number of function-level imports that are *neither*
cycle-required *nor* annotated. It may only fall. When a package's hoist lands, lower
it in the same commit.

This is deliberately a count of the *unexplained* imports rather than all of them:
the 275 hoistable ones are work in progress, and a guard that failed on all of them
could not be committed until the migration finished.
"""

from __future__ import annotations

import re
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

#: Function-level internal imports that are neither cycle-required nor carry a
#: `# lazy:` reason. Lowered package by package as doc 05's hoist lands.
HOISTABLE_CEILING = 266

#: A reason, not a suppression: `# lazy: <why>` on the import's line or the one above.
_LAZY_REASON = re.compile(r"#\s*lazy:\s*\S+")


def _has_reason(path: Path, lineno: int) -> bool:
    """True when the import at `lineno` carries a `# lazy:` reason nearby.

    The reason may sit on the import's own line, or in the contiguous comment block
    directly above it. The block is scanned rather than a fixed number of lines
    because a real reason needs a sentence or two — `subtitle_agent.py` explains a
    shadowing hazard in three lines, and a two-line window would have rejected it
    for being *too well* explained.

    Scanning stops at the first non-comment, non-blank line, so a reason cannot be
    inherited from an unrelated comment further up the function.
    """
    lines = path.read_text().split("\n")
    index = lineno - 1
    if 0 <= index < len(lines) and _LAZY_REASON.search(lines[index]):
        return True
    index -= 1
    while index >= 0:
        stripped = lines[index].strip()
        if stripped.startswith("#"):
            if _LAZY_REASON.search(lines[index]):
                return True
            index -= 1
            continue
        break
    return False


def _module_paths() -> dict[str, Path]:
    root = Path(__file__).resolve().parents[3] / "src" / "film_pipeline"
    return {
        "film_pipeline."
        + ".".join(p.relative_to(root).with_suffix("").parts).replace(".__init__", ""): p
        for p in root.rglob("*.py")
        if "__pycache__" not in p.parts
    }


def _unexplained_lazy_imports() -> list[tuple[str, str, int]]:
    """Function-level internal imports with neither a cycle nor a stated reason."""
    eager, lazy = collect_imports()
    paths = _module_paths()
    out: list[tuple[str, str, int]] = []
    for source, target, lineno in lazy:
        if reaches(eager, target, source):
            continue  # cycle-required: hoisting it would close a cycle
        path = paths.get(source)
        if path is not None and _has_reason(path, lineno):
            continue  # an explicit reason on the import
        out.append((source, target, lineno))
    return out


def test_the_hoistable_count_has_not_grown() -> None:
    """The number of unexplained lazy imports may only fall."""
    unexplained = _unexplained_lazy_imports()
    assert len(unexplained) <= HOISTABLE_CEILING, (
        f"{len(unexplained)} function-level imports are neither cycle-required nor "
        f"carry a '# lazy: <reason>' comment, up from the recorded ceiling of "
        f"{HOISTABLE_CEILING}. Hoist the import, or state why it is lazy. By package: "
        + _by_package(unexplained)
    )


def test_every_lazy_reason_is_a_reason() -> None:
    """A `# lazy:` must say *what* it defers, not just that it is lazy.

    Cheap to satisfy badly — `# lazy: needed` would pass a naive check and tells the
    next reader nothing. Requiring three characters after the colon is a low bar on
    purpose; the guard's job is to force the sentence to exist, not to grade it.
    """
    offenders: list[str] = []
    for path in _module_paths().values():
        for lineno, line in enumerate(path.read_text().split("\n"), start=1):
            match = re.search(r"#\s*lazy:?\s*(.*)$", line)
            if match and len(match.group(1).strip()) < 3:
                offenders.append(f"{path.name}:{lineno}")
    assert not offenders, (
        f"these carry a bare '# lazy' with no stated reason: {offenders}. Say what it "
        "defers — '# lazy: defers langgraph' or '# lazy: cycle via storage'."
    )


def test_the_guard_has_something_to_check() -> None:
    """Guard the guard: a broken collector would report zero and pass.

    The threshold *falls* as the migration proceeds, which is the point: it exists to
    catch a collector that reads nothing, not to assert the migration is unfinished.
    It has moved 200 → 150 → 100 as `mcp`, `orchestration` and the small packages were
    hoisted, each time because the real total dropped to meet it. Lowering it is not
    lowering a finding — `HOISTABLE_CEILING` is the number that measures the work, and
    that one only ever goes down when imports are actually hoisted.
    """
    eager, lazy = collect_imports()
    assert len(lazy) > 100, (
        f"only {len(lazy)} function-level internal imports found; the collector is "
        "probably not reading the tree, which would make the ceiling vacuous."
    )
    assert len(eager) > 100, f"only {len(eager)} modules in the eager graph"


def _by_package(edges: list[tuple[str, str, int]]) -> str:
    import collections

    counts = collections.Counter(package_of(source) for source, _, _ in edges)
    return ", ".join(f"{pkg}={n}" for pkg, n in counts.most_common())
