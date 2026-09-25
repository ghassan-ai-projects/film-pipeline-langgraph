"""The LLM response unwrapping rule has one owner.

The frame reviewer and the contact-sheet reviewer both ask a model for JSON and
both had their own copy of the markdown-fence unwrap. These tests pin the shared
rule and, importantly, that both reviewers reach it — a future edit to one
copy is what the duplication allowed.
"""

from __future__ import annotations

from film_pipeline.generation.review_parsing import strip_markdown_fences


class TestStripMarkdownFences:
    def test_unwraps_a_json_fence(self) -> None:
        assert strip_markdown_fences('```json\n{"a": 1}\n```') == '{"a": 1}'

    def test_unwraps_an_unlabelled_fence(self) -> None:
        assert strip_markdown_fences('```\n{"a": 1}\n```') == '{"a": 1}'

    def test_leaves_plain_json_untouched(self) -> None:
        assert strip_markdown_fences('{"a": 1}') == '{"a": 1}'

    def test_strips_surrounding_whitespace(self) -> None:
        assert strip_markdown_fences('  \n {"a": 1} \n ') == '{"a": 1}'

    def test_handles_a_fence_without_a_closing_marker(self) -> None:
        assert strip_markdown_fences('```json\n{"a": 1}') == '{"a": 1}'

    def test_empty_input_is_empty(self) -> None:
        assert strip_markdown_fences("") == ""


def test_both_reviewers_use_the_shared_unwrapper() -> None:
    """Neither reviewer may go back to carrying its own copy."""
    import film_pipeline.generation.frame_reviewer as frame_reviewer
    import film_pipeline.generation.sheet_reviewer as sheet_reviewer

    assert frame_reviewer.__dict__["strip_markdown_fences"] is strip_markdown_fences
    assert sheet_reviewer.__dict__["strip_markdown_fences"] is strip_markdown_fences
    assert "_strip_markdown_fences" not in vars(frame_reviewer)
    assert "_strip_code_fence" not in vars(sheet_reviewer)
