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

from film_pipeline.filmspec import (
    STALE_GENERATION_REQUEST_CODES,
    is_stale_generation_request_issue,
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
        """Every code the gate emits must be recognised as stale here."""
        from film_pipeline.governance.validators.planning_gates import (
            validate_dispatch_readiness,
        )

        issues = validate_dispatch_readiness({}, None)
        assert issues, "expected the no-requests gate to raise an issue"
        for issue in issues:
            assert is_stale_generation_request_issue(issue)

    def test_empty_request_list_is_also_recognised(self) -> None:
        from film_pipeline.governance.validators.planning_gates import (
            validate_dispatch_readiness,
        )

        for issue in validate_dispatch_readiness({}, []):
            assert is_stale_generation_request_issue(issue)

    def test_ignores_unrelated_issue_codes(self) -> None:
        assert not is_stale_generation_request_issue({"code": "matrix_incomplete"})

    def test_ignores_non_mapping_issues(self) -> None:
        assert not is_stale_generation_request_issue("not-an-issue")
        assert not is_stale_generation_request_issue(None)


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

    def test_both_generation_paths_share_the_vocabulary(self) -> None:
        """The operator path and the MCP path must produce identical rows."""
        from film_pipeline.mcp.tools.generation._text_only import (
            _apply_text_only_state,
        )
        from film_pipeline.operations._generation_ops import (
            _strip_stale_request_issues as operator_strip,
        )

        rows = [{"shot_id": "S001"}]
        expected = text_only_generation_requests("p1", rows, "veo", "veo-3")

        operator_state = {"issues": [{"code": "no_generation_requests"}]}
        operator_strip(operator_state)
        assert operator_state["issues"] == []

        mcp_state: dict[str, object] = {"issues": [{"code": "no_generation_requests"}]}
        _apply_text_only_state(mcp_state, expected)
        assert mcp_state["generation_requests"] == expected
        assert mcp_state["issues"] == []

    def test_module_exposes_one_code_set(self) -> None:
        """No consumer module may re-declare the codes for itself."""
        import film_pipeline.operations._generation_ops as generation_ops
        import film_pipeline.studio._resume as resume

        assert resume.__dict__["_STALE_REQUEST_CODES"] is STALE_GENERATION_REQUEST_CODES
        assert "_STALE_REQUEST_CODES" not in vars(generation_ops)
