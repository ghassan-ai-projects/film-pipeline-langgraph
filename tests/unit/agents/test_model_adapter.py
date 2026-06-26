"""Tests for model adapter — OpenRouter calls with mock HTTP."""

from __future__ import annotations

import json
import urllib.error
from email.message import Message
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock

import pytest

from film_pipeline.agents.model_adapter import ModelAdapter, _accepts_timeout_kw, _open_with_timeout


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
        result = adapter.chat("Say hello", model="test-model")
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
        adapter.chat("Do something", model="test-model", system="You are helpful.")
        body = json.loads(captured[0])
        messages: list[dict[str, str]] = body["messages"]
        assert messages[0] == {"role": "system", "content": "You are helpful."}
        assert messages[1] == {"role": "user", "content": "Do something"}

    def test_chat_passes_configured_request_timeout(self) -> None:
        opener = _make_opener(
            {
                "choices": [{"message": {"content": "ok"}}],
            }
        )
        adapter = ModelAdapter(
            http_opener=opener,
            api_key="test-key",
            request_timeout_seconds=12.5,
        )
        adapter.chat("Do something", model="test-model")
        assert opener.open.call_args.kwargs["timeout"] == 12.5

    def test_chat_keeps_single_argument_test_opener_compatible(self) -> None:
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
        adapter = ModelAdapter(
            http_opener=opener,
            api_key="test-key",
            request_timeout_seconds=12.5,
        )
        assert adapter.chat("Do something", model="test-model") == "ok"
        assert len(captured) == 1

    def test_chat_json_direct_parse(self) -> None:
        opener = _make_opener(
            {
                "choices": [{"message": {"content": '{"score": 95, "status": "pass"}'}}],
            }
        )
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        result = adapter.chat_json("Rate this", model="test-model")
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
        result = adapter.chat_json("Give me JSON", model="test-model")
        assert result == {"x": 1}

    def test_chat_json_from_plain_fence(self) -> None:
        opener = _make_opener(
            {
                "choices": [{"message": {"content": '```\n{"a": "b"}\n```'}}],
            }
        )
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        result = adapter.chat_json("Give me JSON", model="test-model")
        assert result == {"a": "b"}

    def test_chat_json_invalid_raises(self) -> None:
        opener = _make_opener(
            {
                "choices": [{"message": {"content": "Not JSON at all."}}],
            }
        )
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        with pytest.raises(ValueError, match="not valid JSON"):
            adapter.chat_json("Give me JSON", model="test-model")

    def test_chat_no_choices_raises(self) -> None:
        opener = _make_opener({"choices": []})
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        with pytest.raises(RuntimeError, match="returned no choices"):
            adapter.chat("Hello", model="test-model")

    def test_http_error_raises(self) -> None:
        opener = MagicMock()
        opener.open.side_effect = OSError("Connection refused")
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")
        with pytest.raises(RuntimeError, match="OpenRouter chat completions failed"):
            adapter.chat("Hello", model="test-model")

    def test_no_api_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no key is configured, _api_key() raises RuntimeError."""
        import film_pipeline.agents.model_adapter as ma

        monkeypatch.setattr(ma, "lookup", lambda _provider_id: None)
        adapter = ModelAdapter(api_key=None)
        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY is not set"):
            adapter.chat("Hello", model="test-model")

    def test_chat_json_extracts_json_from_surrounding_prose(self) -> None:
        opener = _make_opener(
            {
                "choices": [
                    {"message": {"content": 'analysis first\n{"status": "pass"}\ntrailing text'}}
                ],
            }
        )
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")

        assert adapter.chat_json("Give me JSON", model="test-model") == {"status": "pass"}

    def test_chat_json_rejects_array_response_after_bracket_strategy(self) -> None:
        opener = _make_opener(
            {
                "choices": [{"message": {"content": "Here are values:\n[1, 2, 3]"}}],
            }
        )
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")

        with pytest.raises(ValueError, match="not valid JSON"):
            adapter.chat_json("Give me JSON", model="test-model")

    def test_chat_multimodal_without_images_uses_text_chat(self) -> None:
        opener = _make_opener({"choices": [{"message": {"content": "text only"}}]})
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")

        assert adapter.chat_multimodal("Describe", model="openai/test", images_b64=None) == (
            "text only"
        )

    def test_chat_multimodal_drops_images_for_non_google_model(self) -> None:
        opener = _make_opener({"choices": [{"message": {"content": "fallback"}}]})
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")

        assert adapter.chat_multimodal("Describe", model="openai/test", images_b64=["abc"]) == (
            "fallback"
        )

    def test_chat_multimodal_calls_gemini_with_inline_images(self) -> None:
        captured: list[dict[str, Any]] = []

        def _capture(req: Any, *, timeout: float | None = None) -> Any:
            captured.append({"url": req.full_url, "data": json.loads(req.data), "timeout": timeout})
            return BytesIO(
                json.dumps(
                    {"candidates": [{"content": {"parts": [{"text": "gemini response"}]}}]}
                ).encode()
            )

        opener = MagicMock()
        opener.open = _capture
        adapter = ModelAdapter(
            http_opener=opener,
            api_key="openrouter",
            gemini_api_key="gemini-key",
            request_timeout_seconds=9,
        )

        result = adapter.chat_multimodal(
            "Describe",
            model="google/gemini-test",
            images_b64=["abc"],
            mime_type="image/jpeg",
            max_tokens=123,
            temperature=0.4,
        )

        assert result == "gemini response"
        assert "gemini-test:generateContent?key=gemini-key" in captured[0]["url"]
        assert captured[0]["timeout"] == 9
        body = captured[0]["data"]
        assert body["contents"][0]["parts"] == [
            {"text": "Describe"},
            {"inline_data": {"mime_type": "image/jpeg", "data": "abc"}},
        ]
        assert body["generationConfig"] == {"temperature": 0.4, "maxOutputTokens": 123}

    def test_gemini_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import film_pipeline.agents.model_adapter as ma

        monkeypatch.setattr(ma, "lookup", lambda _provider_id: None)
        adapter = ModelAdapter(api_key="openrouter", gemini_api_key=None)

        with pytest.raises(RuntimeError, match="GOOGLE_API_KEY is not set"):
            adapter.chat_multimodal("Describe", model="google/gemini-test", images_b64=["abc"])

    def test_gemini_no_candidates_and_no_parts_raise(self) -> None:
        no_candidates = ModelAdapter(
            http_opener=_make_gemini_opener({"candidates": []}),
            api_key="openrouter",
            gemini_api_key="gemini",
        )
        no_parts = ModelAdapter(
            http_opener=_make_gemini_opener({"candidates": [{"content": {"parts": []}}]}),
            api_key="openrouter",
            gemini_api_key="gemini",
        )

        with pytest.raises(RuntimeError, match="Gemini returned no candidates"):
            no_candidates.chat_multimodal("Describe", model="google/gemini", images_b64=["abc"])
        with pytest.raises(RuntimeError, match="Gemini returned no content parts"):
            no_parts.chat_multimodal("Describe", model="google/gemini", images_b64=["abc"])

    def test_openrouter_http_error_redacts_response_body(self) -> None:
        opener = MagicMock()
        opener.open.side_effect = urllib.error.HTTPError(
            "https://example.test",
            401,
            "Unauthorized",
            hdrs=Message(),
            fp=BytesIO(b'{"error":"bad secret sk-test"}'),
        )
        adapter = ModelAdapter(http_opener=opener, api_key="test-key")

        with pytest.raises(RuntimeError, match="HTTP 401"):
            adapter.chat("Hello", model="test-model")

    def test_gemini_http_error_is_wrapped(self) -> None:
        opener = MagicMock()
        opener.open.side_effect = urllib.error.HTTPError(
            "https://example.test",
            500,
            "Server Error",
            hdrs=Message(),
            fp=BytesIO(b'{"error":"down"}'),
        )
        adapter = ModelAdapter(
            http_opener=opener,
            api_key="openrouter",
            gemini_api_key="gemini",
        )

        with pytest.raises(RuntimeError, match="Gemini generateContent failed: HTTP 500"):
            adapter.chat_multimodal("Describe", model="google/gemini", images_b64=["abc"])


def _make_gemini_opener(response_body: dict[str, Any]) -> MagicMock:
    opener = MagicMock()
    opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(
        response_body
    ).encode()
    return opener


def test_open_with_timeout_uses_timeout_when_supported() -> None:
    calls: list[float | None] = []

    def opener(_req: Any, *, timeout: float | None = None) -> str:
        calls.append(timeout)
        return "ok"

    assert _open_with_timeout(opener, MagicMock(), 3.5) == "ok"
    assert calls == [3.5]


def test_open_with_timeout_skips_timeout_when_disabled_or_unsupported() -> None:
    calls: list[str] = []

    def opener(_req: Any) -> str:
        calls.append("called")
        return "ok"

    assert _open_with_timeout(opener, MagicMock(), None) == "ok"
    assert _open_with_timeout(opener, MagicMock(), 3.5) == "ok"
    assert calls == ["called", "called"]


def test_accepts_timeout_kw_handles_var_kwargs_and_rejects_plain_builtins() -> None:
    def accepts_kwargs(_req: Any, **_kwargs: Any) -> str:
        return "ok"

    assert _accepts_timeout_kw(accepts_kwargs) is True
    assert _accepts_timeout_kw(len) is False
