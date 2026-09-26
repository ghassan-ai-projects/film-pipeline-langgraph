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
3. **A recorded census of imports the superseded law would forbid.** Reported,
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
    # `_persistence` and `_operator_runtime` are the composition root's private
    # modules. `mcp` reaches them for root resolution and for building an
    # OperatorService. Both should route through a public seam; neither is
    # urgent, and `06` says not to invent an abstraction without a current need.
    ("mcp", "studio._persistence"): 1,
    ("mcp", "studio._operator_runtime"): 1,
}

# `operations/ports.py` mirrors these two names on purpose so `RuntimePort` can
# describe the runtime surface it adapts. That file declares the debt.
_PORT_MIRRORED_PRIVATES = {"_persist_project_state", "_record_audit"}

# Call sites of those mirrored privates outside the package that owns them,
# frozen 2026-09-26. `06` section 4 endorses tightening reach-ins; these are the
# remaining ones. Remove them by routing through a public seam, then lower the
# count. Never raise it.
KNOWN_MIRRORED_PRIVATE_CALLS: dict[str, int] = {
    # `operations/_generation_ops.py` and six `mcp/tools/*` modules persist
    # project state and write audit records by calling the runtime's private
    # methods directly. `operations/ports.py` mirrors the names so the port can
    # declare them; the callers should go through that port instead.
    "operations/_generation_ops.py": 1,
    "mcp/tools/_profile_change.py": 2,
    "mcp/tools/generation/_text_only.py": 1,
    "mcp/tools/helpers.py": 1,
    "mcp/tools/projects.py": 1,
    "mcp/tools/reference_generation/tool.py": 1,
    "mcp/tools/validation.py": 1,
}


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


def _measure_private_reach_ins() -> dict[tuple[str, str], int]:
    """Count imports of another package's underscore-prefixed module."""
    counts: dict[tuple[str, str], int] = {}
    for path in _source_files():
        parts = path.relative_to(_SRC).parts
        source = parts[0] if len(parts) > 1 else None
        if source is None:
            continue
        for module in _film_pipeline_imports(ast.parse(path.read_text())):
            segments = module.split(".")
            if len(segments) < 3:
                continue
            destination, leaf = segments[1], segments[-1]
            if destination == source or not leaf.startswith("_"):
                continue
            key = (source, f"{destination}.{leaf}")
            counts[key] = counts.get(key, 0) + 1
    return counts


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


# --- 2. The port's mirrored privates stay in the port -----------------------


def _measure_mirrored_private_calls() -> dict[str, int]:
    """Count calls to the port's mirrored runtime privates, by caller file."""
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
