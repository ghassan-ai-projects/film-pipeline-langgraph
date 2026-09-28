"""The no-requests issue codes and the text-only request shape have one owner.

Three modules used to declare the same two issue codes independently, and two
of them built the text-only generation request row by hand. The codes are raised
by the generation-planning gate and then recognised by the graph-resume path,
the operator service, and the MCP text-only policy; the request rows are built
on both the operator and MCP paths and must carry the same ids and fields.
These tests pin the shared owner and the property that actually matters: a
recogniser and a producer that move together.
"""

from __future__ import annotations

from film_pipeline.filmspec import STALE_GENERATION_REQUEST_CODES
from film_pipeline.generation.text_only import (
    text_only_generation_request,
    text_only_generation_requests,
)


class TestStaleGenerationRequestCodes:
    def test_owner_declares_both_codes(self) -> None:
        assert (
            frozenset({"empty_generation_requests", "no_generation_requests"})
            == STALE_GENERATION_REQUEST_CODES
        )

    def test_recognises_codes_the_planning_gate_raises(self) -> None:
        """Every code the gate emits must be removable by the shared helper."""
        from film_pipeline.governance.gates.planning_gates import (
            validate_dispatch_readiness,
        )
        from film_pipeline.orchestration.state_schema import remove_issues_by_code

        issues = validate_dispatch_readiness({}, None)
        assert issues, "expected the no-requests gate to raise an issue"
        state = {"issues": list(issues)}
        remove_issues_by_code(state, STALE_GENERATION_REQUEST_CODES)
        assert state["issues"] == []

    def test_empty_request_list_is_also_removable(self) -> None:
        from film_pipeline.governance.gates.planning_gates import (
            validate_dispatch_readiness,
        )
        from film_pipeline.orchestration.state_schema import remove_issues_by_code

        state = {"issues": list(validate_dispatch_readiness({}, []))}
        remove_issues_by_code(state, STALE_GENERATION_REQUEST_CODES)
        assert state["issues"] == []

    def test_unrelated_issue_codes_survive(self) -> None:
        from film_pipeline.orchestration.state_schema import remove_issues_by_code

        state = {"issues": [{"code": "matrix_incomplete"}]}
        remove_issues_by_code(state, STALE_GENERATION_REQUEST_CODES)
        assert state["issues"] == [{"code": "matrix_incomplete"}]


class TestTextOnlyRequestBuilder:
    def test_shot_row_carries_shot_id_in_payload(self) -> None:
        row = text_only_generation_request("p1", "S001", "veo", "veo-3")
        assert row["generation_request_id"] == "text-only-p1-S001"
        assert row["generation_id"] == "text-only-p1-S001"
        assert row["mode"] == "text_only"
        assert row["status"] == "completed"
        assert row["prompt_payload"] == {"text_only": True, "shot_id": "S001"}

    def test_fallback_row_omits_shot_id_from_payload(self) -> None:
        row = text_only_generation_request("p1", "all", "veo", "veo-3")
        assert row["shot_id"] == "all"
        assert row["prompt_payload"] == {"text_only": True}

    def test_one_request_per_usable_row(self) -> None:
        requests = text_only_generation_requests(
            "p1",
            [{"shot_id": "S001"}, {"scene_id": "SC02"}, {"shot_id": "S003"}],
            "veo",
            "veo-3",
        )
        assert [request["shot_id"] for request in requests] == ["S001", "SC02", "S003"]

    def test_rows_without_identity_are_skipped(self) -> None:
        requests = text_only_generation_requests("p1", [{"shot_id": "  "}], "veo", "veo-3")
        assert [request["shot_id"] for request in requests] == ["all"]

    def test_empty_rows_fall_back_to_a_single_row(self) -> None:
        requests = text_only_generation_requests("p1", [], "veo", "veo-3")
        assert len(requests) == 1
        assert requests[0]["shot_id"] == "all"

    def test_the_text_only_path_uses_the_shared_vocabulary(self) -> None:
        """The surviving text-only path applies the shared code set.

        This replaced `test_both_generation_paths_share_the_vocabulary`, which
        compared the MCP path against `operations._generation_ops
        ._strip_stale_request_issues`. That second implementation is deleted
        (`docs/modularity-improvements/03-one-use-case-layer.md`), so the
        comparison has nothing to compare — the property worth asserting now is
        that the one remaining path goes through the shared owner.
        """
        from film_pipeline.mcp.tools.generation._text_only import (
            _apply_text_only_state,
        )

        rows = [{"shot_id": "S001"}]
        expected = text_only_generation_requests("p1", rows, "veo", "veo-3")

        state: dict[str, object] = {"issues": [{"code": "no_generation_requests"}]}
        _apply_text_only_state(state, expected)
        assert state["generation_requests"] == expected
        assert state["issues"] == []

    def test_module_exposes_one_code_set(self) -> None:
        """No consumer module may re-declare the codes for itself.

        The `operations._generation_ops` half of this check is gone with that
        module; `studio._resume` is the remaining consumer that could plausibly
        re-declare them.
        """
        import film_pipeline.orchestration.resume as resume

        assert resume.__dict__["_STALE_REQUEST_CODES"] is STALE_GENERATION_REQUEST_CODES
