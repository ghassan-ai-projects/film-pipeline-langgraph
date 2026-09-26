"""One definition of "this issue blocks", and one place that decides it.

`AGENTS.md`: "One policy reimplemented at N sites is the real defect." The rule
"an issue whose severity is `blocking` blocks phase advancement" was re-derived
at **19 sites across 16 files** as a bare `issue.get("severity") == "blocking"`,
and they had already diverged: most guarded a malformed record with
`isinstance(issue, dict)` and one did not, so an issue list containing `None` or
a string raised `AttributeError` on that path — a live MCP handler — while every
other reader skipped it.

The owner is `filmspec`, which already declares `IssueSeverity` and is the
package the other vocabulary rules live in:

    is_blocking_issue(issue) -> bool
    blocking_issues(issues)  -> list[dict]

Those are now called from `cli`, `governance`, `mcp`, `operations`,
`orchestration`, `studio` and `validation`.

**Out of scope, deliberately:** three remaining sites compare
`severity == "blocking"` on objects that are *not* issues — config conflicts
(`mcp/tools/projects.py`), a generated conflict list (`operations/operator.py`),
and failure-decision records (`orchestration/orchestrator_state.py`). Those are
different records that happen to share a field name; routing them through the
issue predicate would be wrong, and this guard does not ask for it.

Also out of scope: the ~25 *producer* sites that write `{"severity": "blocking"}`
into a new issue. Building a record is not deciding whether one blocks.
"""

from __future__ import annotations

import ast
import pathlib

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src" / "film_pipeline"

# Files whose `severity == "blocking"` comparison is about a DIFFERENT record
# type, so the issue predicate would be the wrong function to call. Listed so the
# sweep is honest about what it exempts and why.
_NON_ISSUE_READERS = {
    "mcp/tools/projects.py",  # config conflicts, not issues
    "operations/operator.py",  # a generated conflict list (a second, narrower site)
    "orchestration/orchestrator_state.py",  # failure-decision records
    # Typed attribute reads, not dict reads: these compare `record.severity` on a
    # schema object, while the predicate takes a mapping from persisted state.
    "config/resolver.py",  # ConfigConflict.severity
    "validation/base.py",  # ValidationIssue.severity
    "orchestration/nodes/qc.py",  # a validation finding object
}


def _raw_issue_severity_readers() -> dict[str, list[int]]:
    """Find `... severity ... == "blocking"` comparisons outside the owner."""
    found: dict[str, list[int]] = {}
    for path in _SRC.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        relative = str(path.relative_to(_SRC))
        if relative == "filmspec/__init__.py" or relative in _NON_ISSUE_READERS:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Compare):
                continue
            text = ast.unparse(node)
            if "blocking" in text and "severity" in text:
                found.setdefault(relative, []).append(node.lineno)
    return found


def test_issue_severity_is_decided_in_one_place() -> None:
    """No module outside the owner may re-derive the issue-severity rule."""
    offenders = _raw_issue_severity_readers()

    assert not offenders, (
        "these re-derive the issue-severity rule instead of calling "
        f"filmspec.is_blocking_issue / blocking_issues: {offenders}. The rule had "
        "19 sites and they had already diverged on malformed input."
    )


def test_the_owner_declares_both_predicates() -> None:
    """The owner must actually expose them, or the routing above is a fiction."""
    source = (_SRC / "filmspec" / "__init__.py").read_text()
    tree = ast.parse(source)
    names = {
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for expected in ("is_blocking_issue", "blocking_issues"):
        assert expected in names, f"filmspec no longer defines {expected}"
        assert f'"{expected}"' in source, f"{expected} is not declared in __all__"


def test_the_predicate_tolerates_malformed_records() -> None:
    """The divergence that prompted this: a non-mapping must not raise.

    Issue lists are persisted state, so crash recovery must not depend on every
    entry being well-formed — and one of the 19 original sites did raise.
    """
    from film_pipeline.filmspec import blocking_issues, is_blocking_issue

    malformed_inputs: tuple[object, ...] = (None, "a-string", 42, [], {"no_severity": True})
    for malformed in malformed_inputs:
        assert is_blocking_issue(malformed) is False, malformed

    assert blocking_issues(None) == []
    assert len(blocking_issues([None, "x", {"severity": "blocking"}])) == 1
