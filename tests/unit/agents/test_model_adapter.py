"""Tests for model adapter — OpenRouter calls with mock HTTP."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock

import pytest

from film_pipeline.agents.model_adapter import ModelAdapter


def _make_opener(response_body: dict[str, Any]) -> MagicMock:
    opener = MagicMock()
    resp_bytes = json.dumps(response_body).encode()
    opener.open.return_value.__enter__.return_value.read.return_value = resp_bytes
    return opener


class TestModelAdapter:
    def test_chat_returns_content(self) -> None:
        opener = _make_opener(
            {
                "choices": [{"message": {"content": "Hello, world!"}}],
            }
        )
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        result = adapter.chat("Say hello")
        assert result == "Hello, world!"

    def test_chat_with_system_prompt(self) -> None:
        captured: list[bytes] = []

        def _capture(req: Any) -> Any:
            captured.append(req.data)
            return BytesIO(
                json.dumps(
                    {
                        "choices": [{"message": {"content": "ok"}}],
                    }
                ).encode()
            )

        opener = MagicMock()
        opener.open = _capture
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        adapter.chat("Do something", system="You are helpful.")
        body = json.loads(captured[0])
        messages: list[dict[str, str]] = body["messages"]
        assert messages[0] == {"role": "system", "content": "You are helpful."}
        assert messages[1] == {"role": "user", "content": "Do something"}

    def test_chat_json_direct_parse(self) -> None:
        opener = _make_opener(
            {
                "choices": [{"message": {"content": '{"score": 95, "status": "pass"}'}}],
            }
        )
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        result = adapter.chat_json("Rate this")
        assert result == {"score": 95, "status": "pass"}

    def test_chat_json_from_markdown_fence(self) -> None:
        opener = _make_opener(
            {
                "choices": [
                    {"message": {"content": 'Sure, here you go:\n\n```json\n{"x": 1}\n```'}}
                ],
            }
        )
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        result = adapter.chat_json("Give me JSON")
        assert result == {"x": 1}

    def test_chat_json_from_plain_fence(self) -> None:
        opener = _make_opener(
            {
                "choices": [{"message": {"content": '```\n{"a": "b"}\n```'}}],
            }
        )
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        result = adapter.chat_json("Give me JSON")
        assert result == {"a": "b"}

    def test_chat_json_invalid_raises(self) -> None:
        opener = _make_opener(
            {
                "choices": [{"message": {"content": "Not JSON at all."}}],
            }
        )
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        with pytest.raises(ValueError, match="not valid JSON"):
            adapter.chat_json("Give me JSON")

    def test_chat_no_choices_raises(self) -> None:
        opener = _make_opener({"choices": []})
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        with pytest.raises(RuntimeError, match="returned no choices"):
            adapter.chat("Hello")

    def test_http_error_raises(self) -> None:
        opener = MagicMock()
        opener.open.side_effect = OSError("Connection refused")
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        with pytest.raises(RuntimeError, match="OpenRouter chat completions failed"):
            adapter.chat("Hello")
