"""The four-strategy JSON recovery chain, including shapes that used to crash.

`extract_json_object` backs `ModelAdapter.chat_json`, so every agent that
requests structured output depends on it. It had **no direct test** before this
file, which is how a real bug survived: `dict(result)` raises `ValueError` — not
`JSONDecodeError` and not `TypeError` — when the parsed JSON is an array
(`[{"a": 1}]`), and none of the four strategies caught it.

The consequence was not a graceful `None`. The exception escaped the strategy and
aborted the whole chain, so `chat_json` surfaced
`ValueError: dictionary update sequence element #0 has length 1; 2 is required`
instead of its intended actionable "not valid JSON after 4 extraction strategies"
message. An array is a normal shape for a model to return.
"""

from __future__ import annotations

import pytest

from film_pipeline.agents._json_extraction import extract_json_object


class TestRecoverableShapes:
    """Every shape the chain is meant to recover."""

    def test_direct_object(self) -> None:
        assert extract_json_object('{"a": 1}') == {"a": 1}

    def test_object_with_surrounding_prose(self) -> None:
        assert extract_json_object('Here you go: {"b": 2} — done.') == {"b": 2}

    def test_fenced_json_block(self) -> None:
        text = 'Sure:\n```json\n{"c": 3}\n```\n'
        assert extract_json_object(text) == {"c": 3}

    def test_fenced_block_without_language_tag(self) -> None:
        assert extract_json_object('```\n{"d": 4}\n```') == {"d": 4}

    def test_nested_object(self) -> None:
        assert extract_json_object('x {"o": {"i": 1}} y') == {"o": {"i": 1}}


class TestArrayShapesDoNotCrash:
    """The regression: `dict()` on a parsed array raises ValueError.

    These cases previously raised out of `extract_json_object` entirely. A
    single-element array of objects is now recovered (the bracketed strategy can
    legitimately unwrap it); other arrays degrade to `None` so the caller reports
    its own actionable error.
    """

    def test_single_element_object_array_is_unwrapped(self) -> None:
        assert extract_json_object('[{"e": 5}]') == {"e": 5}

    @pytest.mark.parametrize(
        "text",
        ['["a", "b"]', "[1, 2, 3]", "[[1], [2]]", "[null]"],
        ids=repr,
    )
    def test_other_arrays_return_none_instead_of_raising(self, text: str) -> None:
        assert extract_json_object(text) is None

    def test_empty_array_degrades_to_an_empty_mapping(self) -> None:
        """`dict([])` legitimately succeeds, so this is an empty dict, not None.

        Asserted explicitly because the distinction is easy to get wrong in a
        test written from the shape rather than from the behaviour.
        """
        assert extract_json_object("[]") == {}

    @pytest.mark.parametrize("text", ["42", "true", '"just a string"', "null"], ids=repr)
    def test_json_scalars_return_none(self, text: str) -> None:
        """Also not mappings, and also previously a ValueError from dict()."""
        assert extract_json_object(text) is None


class TestUnrecoverableShapes:
    def test_plain_prose_returns_none(self) -> None:
        assert extract_json_object("no json at all here") is None

    def test_empty_string_returns_none(self) -> None:
        assert extract_json_object("") is None

    def test_unbalanced_braces_return_none(self) -> None:
        assert extract_json_object('{"a": 1') is None


def test_chat_json_reports_the_actionable_error_for_an_array() -> None:
    """End to end through the public path the bug was observed on."""
    from film_pipeline.agents.model_adapter import ModelAdapter

    class _ArrayResponder(ModelAdapter):
        def __init__(self) -> None:
            super().__init__()

        def chat(self, prompt: str, **kwargs: object) -> str:
            return "[1, 2, 3]"

    with pytest.raises(ValueError, match="not valid JSON"):
        _ArrayResponder().chat_json("prompt", model="some/model")
