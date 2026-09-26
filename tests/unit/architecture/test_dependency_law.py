"""The declared module dependency law, made checkable.

`docs/modular-architecture/03-target-architecture.md` declares, per package, an
**Allowed outbound** set — for `mcp` it says "`filmspec`, `schemas`, `projects`,
`governance`, `validation`, `operations`. **Nothing else.**" Until now that law
was documentation only: nothing failed when an import crossed it, and 73 edges
have accumulated across 12 package pairs while `enola check` reported PASS,
because Enola grades *cycles*, not declared layers.

This guard makes the law executable. It reads the allowed-outbound sets straight
out of the architecture document — so the document stays the single source of
truth and cannot drift from the check — and grades every import under
`src/film_pipeline/` against them.

## How it handles existing debt

Twelve pairs already violate the law. Failing on all 73 today would mean either
a big-bang refactor or a permanently red gate, and this program has learned that
both are worse than a recorded baseline. So the violations are frozen by
**pair and count**:

- a violation of a pair not in the baseline fails immediately (new edge type);
- an increase in an existing pair fails (the debt got worse);
- a decrease passes and prints a reminder to lower the baseline (the debt got
  better, which is the only direction this file should ever move).

That makes every existing violation a visible, individually claimable target
rather than invisible debt, and it makes the *next* one impossible.

This mirrors the repo's existing precedent for recorded debt — the Enola
baseline and the `xfail` markers both work this way.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src" / "film_pipeline"
_ARCHITECTURE_DOC = _REPO_ROOT / "docs" / "modular-architecture" / "03-target-architecture.md"

# Recorded violations of the declared law, frozen at 2026-09-26 (45ba45f) and
# tightened as edges are removed. Keyed by (source, forbidden destination) ->
# edge count. Lower a number when you remove edges; delete the row at zero.
# Never raise one.
#
# Paid down so far: mcp->studio 10 -> 7, by routing the four `operator_service`
# imports through `mcp.tools.helpers.operator_service` instead of importing the
# composition root's private `_operator_runtime` module directly.
KNOWN_DEPENDENCY_LAW_DEBT: dict[tuple[str, str], int] = {
    ("mcp", "agents"): 3,
    ("mcp", "budget"): 1,
    ("mcp", "checkpoints"): 2,
    ("mcp", "config"): 6,
    ("mcp", "generation"): 23,
    ("mcp", "kb"): 5,
    ("mcp", "orchestration"): 8,
    ("mcp", "post"): 2,
    ("mcp", "providers"): 6,
    ("mcp", "storage"): 6,
    ("mcp", "studio"): 7,
    ("schemas", "orchestration"): 1,
}

_SECTION = re.compile(r"### 3\.\d+ `(\w+)`[^\n]*\n(.*?)(?=\n### |\Z)", re.S)
_OUTBOUND = re.compile(r"\*\*Allowed outbound\.\*\*\s*(.+?)(?:\n\n|\n- )", re.S)


def _parse_allowed_outbound() -> dict[str, set[str] | None]:
    """Read the declared outbound sets from the architecture document.

    ``None`` means "every module" (the composition roots, which may import
    anything); an empty set means the package may import nothing.
    """
    law: dict[str, set[str] | None] = {}
    text = _ARCHITECTURE_DOC.read_text()
    for match in _SECTION.finditer(text):
        package, body = match.group(1), match.group(2)
        outbound = _OUTBOUND.search(body)
        if outbound is None:
            continue
        raw = " ".join(outbound.group(1).split())
        if raw.startswith("**none**"):
            law[package] = set()
        elif raw.startswith("every module"):
            law[package] = None
        else:
            law[package] = set(re.findall(r"`(\w+)`", raw))
    return law


def _imported_packages(tree: ast.Module, source_package: str) -> list[str]:
    """Every ``film_pipeline.<pkg>`` this module imports, excluding itself."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("film_pipeline."):
                parts = node.module.split(".")
                if len(parts) > 1 and parts[1] != source_package:
                    found.append(parts[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("film_pipeline."):
                    parts = alias.name.split(".")
                    if len(parts) > 1 and parts[1] != source_package:
                        found.append(parts[1])
    return found


def _measure_violations() -> dict[tuple[str, str], int]:
    """Count edges that cross the declared law, by package pair."""
    law = _parse_allowed_outbound()
    counts: dict[tuple[str, str], int] = {}
    for path in _SRC.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(_SRC).parts
        source = relative[0] if len(relative) > 1 else None
        if source is None or source not in law:
            continue
        allowed = law[source]
        if allowed is None:
            continue
        tree = ast.parse(path.read_text())
        for destination in _imported_packages(tree, source):
            if destination in allowed:
                continue
            key = (source, destination)
            counts[key] = counts.get(key, 0) + 1
    return counts


def test_the_law_is_parsed_from_the_architecture_document() -> None:
    """Guard the guard: an unparsed law would silently check nothing."""
    law = _parse_allowed_outbound()
    assert len(law) >= 15, f"only parsed {len(law)} packages; the document format changed"

    # `mcp` is the package the law is strictest about, and the one this guard
    # exists for. Pin its declared set so a doc edit cannot quietly widen it.
    assert law["mcp"] == {
        "filmspec",
        "schemas",
        "projects",
        "governance",
        "validation",
        "operations",
    }, f"mcp's allowed outbound changed in the architecture document: {law['mcp']}"

    # The composition roots legitimately may import anything.
    assert law["studio"] is None
    assert law["orchestration"] is not None


def test_no_new_dependency_law_violation() -> None:
    """A pair that does not appear in the baseline must not appear at all."""
    actual = _measure_violations()
    new_pairs = sorted(set(actual) - set(KNOWN_DEPENDENCY_LAW_DEBT))

    assert not new_pairs, (
        "these packages now import something the architecture law forbids, and "
        f"they are not recorded as known debt: {new_pairs}. Either route the "
        "import through an allowed owner, or add a row to "
        "KNOWN_DEPENDENCY_LAW_DEBT with a reason."
    )


def test_known_dependency_law_debt_has_not_grown() -> None:
    """Existing debt may shrink; it may never grow."""
    actual = _measure_violations()
    grown = {
        pair: (KNOWN_DEPENDENCY_LAW_DEBT[pair], actual[pair])
        for pair in sorted(KNOWN_DEPENDENCY_LAW_DEBT)
        if actual.get(pair, 0) > KNOWN_DEPENDENCY_LAW_DEBT[pair]
    }

    assert not grown, (
        "dependency-law debt grew (recorded -> actual): "
        f"{grown}. Removing an edge is the point; adding one is not allowed."
    )


def test_recorded_debt_does_not_understate_reality() -> None:
    """A stale baseline that is too high hides edges that came back.

    If a pair's recorded count is higher than reality, the surplus lets that
    many new edges slip through unnoticed, so the baseline must be tightened.
    """
    actual = _measure_violations()
    stale = {
        pair: (recorded, actual.get(pair, 0))
        for pair, recorded in sorted(KNOWN_DEPENDENCY_LAW_DEBT.items())
        if actual.get(pair, 0) < recorded
    }

    assert not stale, (
        "dependency-law debt improved (recorded -> actual): "
        f"{stale}. Lower the number, or delete the row at zero, so the "
        "surplus cannot hide a future regression."
    )


@pytest.mark.parametrize("pair", sorted(KNOWN_DEPENDENCY_LAW_DEBT), ids=lambda p: f"{p[0]}->{p[1]}")
def test_recorded_debt_still_exists(pair: tuple[str, str]) -> None:
    """A row for a pair that no longer violates anything is stale bookkeeping."""
    actual = _measure_violations()
    assert actual.get(pair, 0) > 0, (
        f"{pair[0]} -> {pair[1]} no longer violates the law; delete its "
        "KNOWN_DEPENDENCY_LAW_DEBT row so the baseline means what it says."
    )
