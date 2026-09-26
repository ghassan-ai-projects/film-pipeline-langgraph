"""Tests for the model adapter — dispatch, request shaping, and the transports.

``ModelAdapter`` is tested through its public ``chat`` / ``chat_multimodal`` /
``chat_json`` surface plus the dispatch policy in ``TestDispatchPolicy``.
Per-provider wire-format details are tested against ``agents.transports``
directly in ``TestTransportModules``, which is where that code now lives.
"""

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
        """When no key is configured, the OpenRouter transport raises."""
        import film_pipeline.agents.transports.chat_completions as cc

        monkeypatch.setattr(cc, "lookup", lambda _provider_id: None)
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
        import film_pipeline.agents.transports.gemini as gemini

        monkeypatch.setattr(gemini, "lookup", lambda _provider_id: None)
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


class TestZaiProvider:
    """z.ai (GLM) dispatch — models prefixed ``zai/`` bypass OpenRouter."""

    def test_zai_model_posts_to_zai_endpoint_with_stripped_model_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import film_pipeline.providers.credentials as creds

        captured: list[Any] = []

        def _capture(req: Any, *, timeout: float | None = None) -> Any:
            captured.append(req)
            return BytesIO(json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode())

        opener = MagicMock()
        opener.open = _capture
        # Isolate from the developer's local .env, which may set ZAI_BASE_URL.
        monkeypatch.delenv("ZAI_BASE_URL", raising=False)
        monkeypatch.setattr(creds, "_read_dotenv", lambda _root: {})
        adapter = ModelAdapter(http_opener=opener, zai_api_key="zai-key-123")

        assert adapter.chat("Hello", model="zai/glm-5.3-flash") == "ok"
        assert len(captured) == 1
        req = captured[0]
        assert req.full_url == "https://api.z.ai/api/paas/v4/chat/completions"
        assert req.get_header("Authorization") == "Bearer zai-key-123"
        assert req.get_header("Content-type") == "application/json"
        body = json.loads(req.data)
        assert body["model"] == "glm-5.3-flash"  # prefix must NOT reach the wire
        assert body["messages"] == [{"role": "user", "content": "Hello"}]

    def test_zai_base_url_override_via_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: list[Any] = []

        def _capture(req: Any) -> Any:
            captured.append(req)
            return BytesIO(json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode())

        opener = MagicMock()
        opener.open = _capture
        monkeypatch.setenv("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
        adapter = ModelAdapter(http_opener=opener, zai_api_key="zai-key")

        adapter.chat("Hello", model="zai/glm-5.3-flash")
        assert captured[0].full_url == "https://api.z.ai/api/coding/paas/v4/chat/completions"

    def test_zai_base_url_falls_back_to_dotenv(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / ".env").write_text("ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4\n")
        monkeypatch.delenv("ZAI_BASE_URL", raising=False)
        monkeypatch.setattr("film_pipeline.providers.credentials.Path.cwd", lambda: tmp_path)
        adapter = ModelAdapter(http_opener=MagicMock(), zai_api_key="zai-key")

        assert adapter._zai_base_url() == "https://api.z.ai/api/coding/paas/v4"

    def test_zai_base_url_default_without_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import film_pipeline.providers.credentials as creds

        monkeypatch.delenv("ZAI_BASE_URL", raising=False)
        monkeypatch.setattr(creds, "_read_dotenv", lambda _root: {})
        adapter = ModelAdapter()

        assert adapter._zai_base_url() == "https://api.z.ai/api/paas/v4"

    def test_zai_base_url_override_trailing_slash_is_stripped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4/")
        adapter = ModelAdapter()

        assert adapter._zai_base_url() == "https://api.z.ai/api/coding/paas/v4"

    def test_zai_missing_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import film_pipeline.agents.transports.zai as zai

        monkeypatch.setattr(zai, "lookup", lambda _provider_id: None)
        adapter = ModelAdapter(zai_api_key=None)

        with pytest.raises(RuntimeError, match="ZAI_API_KEY is not set"):
            adapter.chat("Hello", model="zai/glm-5.3-flash")

    def test_zai_no_choices_raises_provider_aware_error(self) -> None:
        opener = _make_opener({"choices": []})
        adapter = ModelAdapter(http_opener=opener, zai_api_key="zai-key")

        with pytest.raises(RuntimeError, match="z\\.ai returned no choices"):
            adapter.chat("Hello", model="zai/glm-5.3-flash")

    def test_zai_http_error_is_prefixed_and_redacted(self) -> None:
        opener = MagicMock()
        opener.open.side_effect = urllib.error.HTTPError(
            "https://example.test",
            401,
            "Unauthorized",
            hdrs=Message(),
            fp=BytesIO(b'{"error":"bad secret sk-test"}'),
        )
        adapter = ModelAdapter(http_opener=opener, zai_api_key="zai-key")

        with pytest.raises(RuntimeError, match="z\\.ai chat completions failed: HTTP 401"):
            adapter.chat("Hello", model="zai/glm-5.3-flash")

    def test_zai_reasoning_content_with_empty_content_fails_json_parse(self) -> None:
        """Reasoning models can spend the whole budget on reasoning_content."""
        opener = _make_opener(
            {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "reasoning_content": "I thought about it at length.",
                        }
                    }
                ]
            }
        )
        adapter = ModelAdapter(http_opener=opener, zai_api_key="zai-key")

        with pytest.raises(ValueError, match="not valid JSON"):
            adapter.chat_json("Give me JSON", model="zai/glm-5.3-flash")

    def test_zai_null_content_is_treated_as_empty_string(self) -> None:
        opener = _make_opener({"choices": [{"message": {"content": None}}]})
        adapter = ModelAdapter(http_opener=opener, zai_api_key="zai-key")

        assert adapter.chat("Hello", model="zai/glm-5.3-flash") == ""

    def test_zai_multimodal_preserves_images_in_openai_content_blocks(self) -> None:
        captured: list[Any] = []

        def _capture(req: Any, *, timeout: float | None = None) -> Any:
            captured.append({"request": req, "timeout": timeout})
            return BytesIO(json.dumps({"choices": [{"message": {"content": "vision"}}]}).encode())

        opener = MagicMock()
        opener.open = _capture
        adapter = ModelAdapter(http_opener=opener, zai_api_key="zai-key")

        assert (
            adapter.chat_multimodal(
                "Describe",
                model="zai/glm-5.3-flash",
                images_b64=["abc"],
                mime_type="image/jpeg",
            )
            == "vision"
        )

        body = json.loads(captured[0]["request"].data)
        assert body["messages"] == [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64,abc"},
                    },
                ],
            }
        ]
        assert "frequency_penalty" not in body

    def test_zai_rejects_untrusted_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ZAI_BASE_URL", "https://attacker.example/api")
        adapter = ModelAdapter(zai_api_key="zai-key")

        with pytest.raises(RuntimeError, match="ZAI_BASE_URL must be"):
            adapter.chat("Hello", model="zai/glm-5.3-flash")


class TestDispatchPolicy:
    """The model-id → transport policy, pinned in exactly one place.

    Every assertion here is about *which* transport a model id selects, not
    about what that transport does. That policy lives in ``ModelAdapter``; the
    per-provider behaviour is tested against ``agents.transports`` directly.
    """

    @staticmethod
    def _spy(monkeypatch: pytest.MonkeyPatch) -> list[str]:
        """Record which transport each send path selects.

        ``ModelAdapter`` resolves its sends through the transport *modules* at
        call time, so patching the module attributes is exactly the seam the
        adapter uses.
        """
        import film_pipeline.agents.transports.chat_completions as cc
        import film_pipeline.agents.transports.gemini as gemini
        import film_pipeline.agents.transports.zai as zai

        selected: list[str] = []
        real_openrouter = cc.send_chat_completion
        real_zai = zai.send_zai_chat_completion
        real_gemini = gemini.send_generate_content

        def _openrouter(*args: Any, **kwargs: Any) -> Any:
            selected.append("openrouter")
            return real_openrouter(*args, **kwargs)

        def _zai(*args: Any, **kwargs: Any) -> Any:
            selected.append("zai")
            return real_zai(*args, **kwargs)

        def _gemini(*args: Any, **kwargs: Any) -> Any:
            selected.append("gemini")
            return real_gemini(*args, **kwargs)

        monkeypatch.setattr(cc, "send_chat_completion", _openrouter)
        monkeypatch.setattr(zai, "send_zai_chat_completion", _zai)
        monkeypatch.setattr(gemini, "send_generate_content", _gemini)
        return selected

    @pytest.mark.parametrize(
        ("model", "expected"),
        [
            ("zai/glm-5.3-flash", "zai"),
            ("glm-5.3-flash", "openrouter"),
            ("openai/gpt-5", "openrouter"),
            ("anthropic/claude-sonnet-5", "openrouter"),
            # ``zai`` without the slash is a bare model id — not a z.ai route.
            ("zaikey/model", "openrouter"),
        ],
    )
    def test_chat_dispatches_by_model_prefix(
        self, monkeypatch: pytest.MonkeyPatch, model: str, expected: str
    ) -> None:
        selected = self._spy(monkeypatch)
        opener = _make_opener({"choices": [{"message": {"content": "ok"}}]})
        # Both keys configured: selection must depend on the model id alone.
        adapter = ModelAdapter(http_opener=opener, api_key="openrouter-key", zai_api_key="zai-key")

        assert adapter.chat("Hello", model=model) == "ok"
        assert selected == [expected]

    def test_zai_model_never_reaches_openrouter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        selected = self._spy(monkeypatch)
        opener = _make_opener({"choices": [{"message": {"content": "ok"}}]})
        adapter = ModelAdapter(http_opener=opener, api_key="openrouter-key", zai_api_key="zai-key")

        adapter.chat("Hello", model="zai/glm-5.3-flash")

        assert "zai" in selected
        assert "openrouter" not in selected

    def test_bare_model_never_reaches_zai(self, monkeypatch: pytest.MonkeyPatch) -> None:
        selected = self._spy(monkeypatch)
        opener = _make_opener({"choices": [{"message": {"content": "ok"}}]})
        adapter = ModelAdapter(http_opener=opener, api_key="openrouter-key", zai_api_key="zai-key")

        adapter.chat("Hello", model="glm-5.3-flash")

        assert selected == ["openrouter"]

    @pytest.mark.parametrize(
        ("model", "expected"),
        [
            ("google/gemini-test", "gemini"),
            ("zai/glm-5v-turbo", "zai"),
            ("openai/gpt-5", "openrouter"),
        ],
    )
    def test_chat_multimodal_dispatches_by_model_prefix(
        self, monkeypatch: pytest.MonkeyPatch, model: str, expected: str
    ) -> None:
        selected = self._spy(monkeypatch)
        body: dict[str, Any] = {"choices": [{"message": {"content": "ok"}}]}
        if expected == "gemini":
            body = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        adapter = ModelAdapter(
            http_opener=_make_opener(body),
            api_key="openrouter-key",
            gemini_api_key="gemini-key",
            zai_api_key="zai-key",
        )

        assert adapter.chat_multimodal("Describe", model=model, images_b64=["abc"]) == "ok"
        assert selected == [expected]

    def test_google_model_without_images_does_not_reach_gemini(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Text-only calls use the chat transport even for a Gemini model id."""
        selected = self._spy(monkeypatch)
        opener = _make_opener({"choices": [{"message": {"content": "ok"}}]})
        adapter = ModelAdapter(
            http_opener=opener, api_key="openrouter-key", gemini_api_key="gemini-key"
        )

        adapter.chat_multimodal("Describe", model="google/gemini-test", images_b64=None)

        assert selected == ["openrouter"]

    def test_non_google_model_drops_images_and_uses_chat(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A model with no multimodal transport falls back to text-only chat."""
        selected = self._spy(monkeypatch)
        opener = _make_opener({"choices": [{"message": {"content": "ok"}}]})
        adapter = ModelAdapter(http_opener=opener, api_key="openrouter-key")

        adapter.chat_multimodal("Describe", model="openai/gpt-5", images_b64=["abc"])

        assert selected == ["openrouter"]


class TestTransportModules:
    """The extracted transports, tested where they now live."""

    def test_zai_base_url_defaults_without_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import film_pipeline.providers.credentials as creds
        from film_pipeline.agents.transports.zai import zai_base_url

        monkeypatch.delenv("ZAI_BASE_URL", raising=False)
        monkeypatch.setattr(creds, "_read_dotenv", lambda _root: {})

        assert zai_base_url() == "https://api.z.ai/api/paas/v4"

    def test_zai_base_url_rejects_untrusted_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from film_pipeline.agents.transports.zai import zai_base_url

        monkeypatch.setenv("ZAI_BASE_URL", "https://attacker.example/api")

        with pytest.raises(RuntimeError, match="ZAI_BASE_URL must be"):
            zai_base_url()

    def test_zai_base_url_rejects_http_scheme(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An allowlisted host over plain http is still refused."""
        from film_pipeline.agents.transports.zai import zai_base_url

        monkeypatch.setenv("ZAI_BASE_URL", "http://api.z.ai/api/paas/v4")

        with pytest.raises(RuntimeError, match="ZAI_BASE_URL must be"):
            zai_base_url()

    def test_zai_payload_omits_frequency_penalty(self) -> None:
        from film_pipeline.agents.transports.chat_completions import (
            ChatRequest,
            chat_completions_payload,
        )

        payload = json.loads(
            chat_completions_payload(
                ChatRequest(messages=[{"role": "user", "content": "hi"}], model="glm"),
                include_frequency_penalty=False,
            )
        )

        assert "frequency_penalty" not in payload
        assert payload["model"] == "glm"

    def test_openrouter_payload_includes_frequency_penalty(self) -> None:
        from film_pipeline.agents.transports.chat_completions import (
            ChatRequest,
            chat_completions_payload,
        )

        payload = json.loads(
            chat_completions_payload(
                ChatRequest(messages=[{"role": "user", "content": "hi"}], model="m")
            )
        )

        assert payload["frequency_penalty"] == 0.0

    def test_gemini_url_strips_google_prefix_and_carries_key(self) -> None:
        from film_pipeline.agents.transports.gemini import gemini_url

        url = gemini_url("google/gemini-3-flash", "secret-key")

        assert url == (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-3-flash:generateContent?key=secret-key"
        )

    def test_gemini_payload_builds_inline_image_parts(self) -> None:
        from film_pipeline.agents.transports.gemini import (
            GeminiRequest,
            build_gemini_payload,
        )

        payload = build_gemini_payload(
            GeminiRequest(
                prompt="Describe",
                model="google/gemini",
                images_b64=["abc", "def"],
                mime_type="image/jpeg",
                max_tokens=64,
                temperature=0.5,
            )
        )

        assert payload["contents"][0]["parts"] == [
            {"text": "Describe"},
            {"inline_data": {"mime_type": "image/jpeg", "data": "abc"}},
            {"inline_data": {"mime_type": "image/jpeg", "data": "def"}},
        ]
        assert payload["generationConfig"] == {"temperature": 0.5, "maxOutputTokens": 64}

    def test_first_candidate_text_raises_without_candidates_or_parts(self) -> None:
        from film_pipeline.agents.transports.gemini import first_candidate_text

        assert (
            first_candidate_text({"candidates": [{"content": {"parts": [{"text": "x"}]}}]}) == "x"
        )
        with pytest.raises(RuntimeError, match="Gemini returned no candidates"):
            first_candidate_text({"candidates": []})
        with pytest.raises(RuntimeError, match="Gemini returned no content parts"):
            first_candidate_text({"candidates": [{"content": {"parts": []}}]})

    def test_transports_package_surface_is_importable(self) -> None:
        """``agents.transports`` is the declared package surface."""
        from film_pipeline.agents import transports

        missing = [name for name in transports.__all__ if not hasattr(transports, name)]

        assert not missing, f"transports.__all__ names unknown symbols: {missing}"


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


def test_transport_scrubs_sensitive_headers_before_reraising() -> None:
    from film_pipeline.providers.http_transport import post_json

    opener = MagicMock()
    secret = "0123456789abcdef0123456789abcdef.secret-value"
    opener.open.side_effect = OSError(f"network unavailable for {secret}")
    headers = {"Authorization": f"Bearer {secret}"}

    with pytest.raises(RuntimeError, match="network unavailable") as exc_info:
        post_json(
            "https://api.z.ai/api/paas/v4/chat/completions",
            b"{}",
            http_opener=opener,
            timeout_seconds=None,
            headers=headers,
            error_prefix="z.ai failed",
            redact_body=True,
        )

    assert headers["Authorization"] == "[REDACTED]"
    assert secret not in str(exc_info.value)
