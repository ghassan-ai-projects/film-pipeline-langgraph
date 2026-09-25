"""Issue removal has one implementation, shared with the reducer.

`merge_issues` owns the rule that issues can be removed by code, via a
``{"__remove_codes__": [...]}`` sentinel. It is a *reducer*, so it only applies
when LangGraph merges a node update — callers outside the graph write state
directly and cannot use it. Three of them had each reimplemented the same list
comprehension:

- `studio/_resume.py` (stale generation-request blockers)
- `mcp/tools/generation/_text_only.py` (same codes, text-only policy)
- `operations/_generation_ops.py` (same codes again)

`remove_issues_by_code` applies the reducer's own semantics to a plain mapping.
These tests pin the behaviour and the equivalence with the replaced code.
"""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.orchestration.state_schema import (
    merge_issues,
    remove_issues_by_code,
)


def _issue(code: str, message: str = "m") -> dict[str, Any]:
    return {"code": code, "message": message, "severity": "blocking"}


class TestRemoveIssuesByCode:
    def test_removes_matching_issues(self) -> None:
        state: dict[str, Any] = {"issues": [_issue("a"), _issue("b")]}
        remove_issues_by_code(state, {"a"})
        assert state["issues"] == [_issue("b")]

    def test_removes_every_matching_code(self) -> None:
        state: dict[str, Any] = {"issues": [_issue("a"), _issue("b"), _issue("c")]}
        remove_issues_by_code(state, {"a", "b"})
        assert state["issues"] == [_issue("c")]

    def test_unmatched_issues_survive_untouched(self) -> None:
        original = [_issue("keep", "important")]
        state: dict[str, Any] = {"issues": list(original)}
        remove_issues_by_code(state, {"gone"})
        assert state["issues"] == original

    def test_empty_code_set_is_a_noop(self) -> None:
        original = [_issue("a")]
        state: dict[str, Any] = {"issues": list(original)}
        remove_issues_by_code(state, set())
        assert state["issues"] == original

    def test_missing_key_is_tolerated(self) -> None:
        state: dict[str, Any] = {}
        remove_issues_by_code(state, {"a"})
        assert "issues" not in state

    def test_non_list_issues_is_left_alone(self) -> None:
        state: dict[str, Any] = {"issues": "not-a-list"}
        remove_issues_by_code(state, {"a"})
        assert state["issues"] == "not-a-list"

    def test_non_mapping_entries_survive(self) -> None:
        """The replaced comprehensions kept non-dict entries; so does this."""
        state: dict[str, Any] = {"issues": [_issue("a"), "loose-entry"]}
        remove_issues_by_code(state, {"a"})
        assert state["issues"] == ["loose-entry"]

    @pytest.mark.parametrize("code", ["empty_generation_requests", "no_generation_requests"])
    def test_matches_the_stale_generation_request_vocabulary(self, code: str) -> None:
        from film_pipeline.filmspec import STALE_GENERATION_REQUEST_CODES

        state: dict[str, Any] = {"issues": [_issue(code), _issue("other")]}
        remove_issues_by_code(state, STALE_GENERATION_REQUEST_CODES)
        assert state["issues"] == [_issue("other")]


class TestAgreesWithTheReducer:
    def test_same_result_as_applying_the_sentinel(self) -> None:
        """The helper must not drift from the rule it delegates to."""
        issues = [_issue("a"), _issue("b"), _issue("c")]
        via_helper: dict[str, Any] = {"issues": list(issues)}
        remove_issues_by_code(via_helper, {"a", "c"})
        via_reducer = merge_issues(issues, [{"__remove_codes__": ["a", "c"]}])
        assert via_helper["issues"] == via_reducer

    def test_reducer_semantics_still_remove_and_keep(self) -> None:
        merged = merge_issues([_issue("a"), _issue("b")], [{"__remove_codes__": ["a"]}])
        assert merged == [_issue("b")]
