"""Model adapter — calls an LLM via OpenRouter, z.ai, or Gemini for agent execution.

Same pattern as ``SeedanceOpenRouterProvider``: constructor-injected HTTP opener
so tests can mock the network without any test-only dependency.

Model selection is ALWAYS explicit: no hardcoded defaults. Callers must resolve
the model through the routing layer before invoking this adapter. Models are
dispatched by id prefix: ``zai/`` goes to z.ai's OpenAI-compatible endpoint
(``ZAI_API_KEY``), ``google/`` multimodal calls go to Gemini's generateContent
API (``GOOGLE_API_KEY``), everything else goes to OpenRouter
(``OPENROUTER_API_KEY``).

This module owns dispatch and request shaping only. Per-provider wire formats
live in ``agents.transports``; the network boundary lives in
``providers.http_transport``. Model-text JSON recovery lives in
``_json_extraction``.
"""

from __future__ import annotations

from typing import Any

from film_pipeline.agents._json_extraction import extract_json_object
from film_pipeline.agents.transports import chat_completions, gemini, zai
from film_pipeline.agents.transports.chat_completions import (
    ChatRequest as _ChatRequest,
)
from film_pipeline.agents.transports.gemini import GeminiRequest as _GeminiRequest
from film_pipeline.agents.transports.zai import ZAI_MODEL_PREFIX

# Historical import paths kept stable for callers and tests (explicit alias
# form so mypy strict's no_implicit_reexport passes them through).
from film_pipeline.providers.http_transport import (
    _accepts_timeout_kw as _accepts_timeout_kw,
)
from film_pipeline.providers.http_transport import (
    _open_with_timeout as _open_with_timeout,
)
from film_pipeline.providers.http_transport import post_json as post_json

_ZAI_MODEL_PREFIX = ZAI_MODEL_PREFIX
_GEMINI_MODEL_PREFIX = "google/"


def _warn_dropped_images(count: int, model: str) -> None:
    import logging

    logging.warning(
        "chat_multimodal: dropping %d images for non-Google model '%s'",
        count,
        model,
    )


class ModelAdapter:
    """Call a chat model through OpenRouter, z.ai, or Gemini (prefix-routed).

    Testable: pass ``_http_opener`` to inject a mock HTTP handler.

    This class is dispatch plus request shaping: it decides which transport a
    model id targets, builds that transport's value object, and normalizes the
    text response. Each provider's wire format lives in ``agents.transports``.
    """

    def __init__(
        self,
        http_opener: Any = None,
        api_key: str | None = None,
        gemini_api_key: str | None = None,
        zai_api_key: str | None = None,
        request_timeout_seconds: float | None = 120.0,
    ) -> None:
        self._http_opener = http_opener
        self._configured_api_key = api_key
        self._configured_gemini_api_key = gemini_api_key
        self._configured_zai_api_key = zai_api_key
        self.request_timeout_seconds = request_timeout_seconds

    def _api_key(self) -> str:
        return chat_completions.openrouter_api_key(self._configured_api_key)

    def _gemini_api_key(self) -> str:
        return gemini.gemini_api_key(self._configured_gemini_api_key)

    def _zai_api_key(self) -> str:
        return zai.zai_api_key(self._configured_zai_api_key)

    def _zai_base_url(self) -> str:
        """Resolve the z.ai API base URL (see ``transports.zai.zai_base_url``)."""
        return zai.zai_base_url()

    def _request(self, request: _ChatRequest) -> dict[str, Any]:
        """Post a chat-completion request to the model's provider endpoint.

        Models prefixed ``zai/`` go to z.ai (OpenAI-compatible chat
        completions); everything else goes to OpenRouter. ``request.model``
        is REQUIRED — no hardcoded default. The caller must resolve the model
        through config/routing before invoking.
        """
        if _is_zai_model(request.model):
            return self._zai_request(request)
        return chat_completions.send_chat_completion(
            request,
            http_opener=self._http_opener,
            timeout_seconds=self.request_timeout_seconds,
            api_key=self._api_key(),
        )

    def _zai_request(self, request: _ChatRequest) -> dict[str, Any]:
        """Post a chat-completion request to z.ai, stripping the ``zai/`` prefix."""
        return zai.send_zai_chat_completion(
            request,
            http_opener=self._http_opener,
            timeout_seconds=self.request_timeout_seconds,
            api_key=self._zai_api_key(),
        )

    def chat(
        self,
        prompt: str,
        *,
        model: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.95,
        frequency_penalty: float = 0.0,
    ) -> str:
        """Send a prompt and return the model's text response.

        ``model`` is REQUIRED — no hardcoded default.
        """
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self._request(
            _ChatRequest(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
            )
        )
        return _first_message_content(response, provider=_provider_label(model))

    def chat_multimodal(
        self,
        prompt: str,
        *,
        model: str,
        images_b64: list[str] | None = None,
        mime_type: str = "image/png",
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> str:
        """Send prompt + images to a multimodal model.

        When model starts with 'google/', uses Gemini's generateContent API
        with inline image data. z.ai models use the OpenAI-compatible
        ``image_url`` content block format. Other models fall back to
        text-only chat() because their adapter contract is text-only.

        Args:
            prompt: The text prompt.
            model: Full model ID (e.g. "google/gemini-3-flash-preview" or
                "zai/glm-5v-turbo").
            images_b64: Base64-encoded images (no data URI prefix).
            mime_type: Image MIME type for Gemini API.
            max_tokens: Max output tokens.
            temperature: Generation temperature.

        Returns:
            Model's text response.
        """
        if not images_b64:
            return self.chat(prompt, model=model, max_tokens=max_tokens, temperature=temperature)

        if _is_gemini_model(model):
            return self._call_gemini_api(
                _GeminiRequest(
                    prompt=prompt,
                    model=model,
                    images_b64=images_b64,
                    mime_type=mime_type,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            )

        if _is_zai_model(model):
            content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
            content.extend(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                }
                for image_b64 in images_b64
            )
            response = self._request(
                _ChatRequest(
                    messages=[{"role": "user", "content": content}],
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            )
            return _first_message_content(response, provider=_provider_label(model))

        _warn_dropped_images(len(images_b64), model)
        return self.chat(prompt, model=model, max_tokens=max_tokens, temperature=temperature)

    def _call_gemini_api(self, request: _GeminiRequest) -> str:
        """Call Gemini's generateContent API with text + inline images."""
        return gemini.send_generate_content(
            request,
            http_opener=self._http_opener,
            timeout_seconds=self.request_timeout_seconds,
            api_key=self._gemini_api_key(),
        )

    def _gemini_url(self, model: str) -> str:
        """Build the generateContent endpoint URL after resolving the API key."""
        return gemini.gemini_url(model, self._gemini_api_key())

    def chat_json(
        self,
        prompt: str,
        *,
        model: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        top_p: float = 0.95,
        frequency_penalty: float = 0.0,
    ) -> dict[str, Any]:
        """Send a prompt, expect a JSON response, parse and return it.

        ``model`` is REQUIRED — no hardcoded default.

        Robustly handles markdown-fenced JSON, leading/trailing prose,
        and extremely long responses from Gemini-style streaming.
        """
        text = self.chat(
            prompt,
            model=model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
        ).strip()

        extracted = extract_json_object(text)
        if extracted is None:
            raise ValueError(
                f"Model response is not valid JSON after 4 extraction strategies. "
                f"Response length: {len(text)} chars. "
                f"Preview: {text[:300]}"
            )
        return extracted


def _is_zai_model(model: str) -> bool:
    """Whether ``model`` targets the z.ai OpenAI-compatible endpoint."""
    return model.startswith(_ZAI_MODEL_PREFIX)


def _is_gemini_model(model: str) -> bool:
    """Whether ``model`` targets Gemini's generateContent API."""
    return model.startswith(_GEMINI_MODEL_PREFIX)


def _provider_label(model: str) -> str:
    """Human-readable provider name for error messages."""
    return "z.ai" if _is_zai_model(model) else "OpenRouter"


def _first_message_content(response: dict[str, Any], *, provider: str) -> str:
    """Return the first choice's text content, or raise for the provider."""
    choices: list[dict[str, Any]] = response.get("choices", [])
    if not choices:
        raise RuntimeError(f"{provider} returned no choices.")
    msg: dict[str, Any] = choices[0].get("message", {})
    # ``or ""`` guards content: null — some providers send it when the
    # whole completion budget went to reasoning_content.
    return str(msg.get("content") or "")
