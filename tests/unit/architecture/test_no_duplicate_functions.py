"""No module-level function body may be defined identically in two modules.

`AGENTS.md`: "One policy reimplemented at N sites is the real defect." A body
appearing verbatim in two files is that defect in its purest form — two authors
for one rule, with nothing forcing them to agree and no test able to notice when
they drift apart.

Three existed when this guard was written, all now consolidated:

- `_collect_updates` in `orchestration/nodes/qc.py` and `visual.py` — the
  node-boundary update rule (which refs and issues cross, which keys carry),
  19 lines, byte-identical. Moved to `nodes/_shared.py`, which already owned its
  `_is_new_ref`/`_is_new_issue` prerequisites.
- `missing_profile_credentials` in `studio/_provider_profiles.py` and
  `studio/_operator_runtime.py`. The former module turned out to be dead in
  production — nothing in `src/` imported it, only a test did — so it was
  deleted and the test retargeted at the live implementation.
- `_is_text_only_policy` in `operations/_generation_ops.py` and
  `mcp/tools/generation/_text_only.py`, with the `"text_only"` literal in three
  places. The vocabulary owner is `filmspec`, so `TEXT_ONLY_POLICY` and
  `is_text_only_policy` live there now.

Scope: **module-level** functions only, and only exact body matches. Methods are
excluded because same-shaped methods on different classes are usually a real
contract (two adapters implementing one port), not duplication. Near-duplicates
are out of scope: they need judgement, not a string comparison.
"""

from __future__ import annotations

import ast
import hashlib
import pathlib
from collections import defaultdict

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src" / "film_pipeline"


def _body_fingerprint(source: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Hash everything after the name, so same-body/different-name still groups."""
    segment = ast.get_source_segment(source, node)
    assert segment is not None
    return hashlib.sha256(segment.split("(", 1)[1].encode()).hexdigest()


def _duplicate_function_bodies() -> dict[str, list[str]]:
    copies: dict[str, list[str]] = defaultdict(list)
    for path in _SRC.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        source = path.read_text()
        for node in ast.parse(source).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                copies[_body_fingerprint(source, node)].append(
                    f"{path.relative_to(_SRC)}::{node.name}"
                )
    return {
        fingerprint: sites
        for fingerprint, sites in copies.items()
        if len({site.split("::")[0] for site in sites}) > 1
    }


def test_no_function_body_is_defined_in_two_modules() -> None:
    duplicates = _duplicate_function_bodies()

    assert not duplicates, (
        "these module-level functions have byte-identical bodies in two files, "
        "which means one rule with two authors and no test tying them together: "
        f"{sorted(duplicates.values())}. Keep one definition in the module that "
        "owns the rule and delete the other."
    )


def test_the_sweep_finds_functions_to_compare() -> None:
    """Guard the guard: a sweep that parses nothing would pass vacuously."""
    count = 0
    for path in _SRC.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        count += sum(
            1
            for node in ast.parse(path.read_text()).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
    assert count > 100, f"only found {count} module-level functions; the sweep is broken"
