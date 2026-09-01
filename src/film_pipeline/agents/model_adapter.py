"""Model adapter — calls an LLM via OpenRouter or z.ai for agent execution.

Same pattern as ``SeedanceOpenRouterProvider``: constructor-injected HTTP opener
so tests can mock the network without any test-only dependency.

Model selection is ALWAYS explicit: no hardcoded defaults. Callers must resolve
the model through the routing layer before invoking this adapter. Models are
dispatched by id prefix: ``zai/`` goes to z.ai's OpenAI-compatible endpoint
(``ZAI_API_KEY``), ``google/`` multimodal calls go to Gemini's generateContent
API (``GOOGLE_API_KEY``), everything else goes to OpenRouter
(``OPENROUTER_API_KEY``).

Transport concerns live in ``_http_transport`` and model-text JSON recovery in
``_json_extraction``; this module stays with request shaping, key resolution,
and provider payload/response mapping.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from typing import Any

# Historical import paths kept stable for callers and tests (explicit alias
# form so mypy strict's no_implicit_reexport passes them through).
from film_pipeline.agents._http_transport import (
    _accepts_timeout_kw as _accepts_timeout_kw,
)
from film_pipeline.agents._http_transport import (
    _open_with_timeout as _open_with_timeout,
)
from film_pipeline.agents._http_transport import post_json
from film_pipeline.agents._json_extraction import extract_json_object
from film_pipeline.providers.adapters.seedance_openrouter import OPENROUTER_API
from film_pipeline.providers.credentials import env_or_dotenv, lookup

ZAI_MODEL_PREFIX = "zai/"
ZAI_API_BASE = "https://api.z.ai/api/paas/v4"


@dataclass(frozen=True)
class _GeminiRequest:
    """Parameters for a single Gemini generateContent call."""

    prompt: str
    model: str
    images_b64: list[str]
    mime_type: str
    max_tokens: int
    temperature: float


@dataclass(frozen=True)
class _ChatRequest:
    """Request-shaping parameters for an OpenRouter chat-completion call."""

    messages: list[dict[str, str]]
    model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.95
    frequency_penalty: float = 0.0


class ModelAdapter:
    """Call a chat model through OpenRouter or z.ai (prefix-routed).

    Testable: pass ``_http_opener`` to inject a mock HTTP handler.
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
        key = self._configured_api_key or lookup("seedance-openrouter")
        if not key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Set it in the environment or in a local .env file."
            )
        return key

    def _gemini_api_key(self) -> str:
        key = self._configured_gemini_api_key or lookup("gemini-imagen-4")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY is not set. Set it in the environment or .env file.")
        return key

    def _zai_api_key(self) -> str:
        key = self._configured_zai_api_key or lookup("zai")
        if not key:
            raise RuntimeError(
                "ZAI_API_KEY is not set. Set it in the environment or in a local .env file."
            )
        return key

    def _zai_base_url(self) -> str:
        """Resolve the z.ai API base URL.

        ``ZAI_BASE_URL`` (environment or local ``.env``) overrides the default.
        Coding-plan keys only work against the coding endpoint:
        ``https://api.z.ai/api/coding/paas/v4`` — against the standard endpoint
        they fail with error 1113 (insufficient balance).
        """
        return env_or_dotenv("ZAI_BASE_URL") or ZAI_API_BASE

    def _request(self, request: _ChatRequest) -> dict[str, Any]:
        """Post a chat-completion request to the model's provider endpoint.

        Models prefixed ``zai/`` go to z.ai (OpenAI-compatible chat
        completions); everything else goes to OpenRouter. ``request.model``
        is REQUIRED — no hardcoded default. The caller must resolve the model
        through config/routing before invoking.
        """
        if request.model.startswith(ZAI_MODEL_PREFIX):
            return self._zai_request(request)
        return post_json(
            f"{OPENROUTER_API}/chat/completions",
            _chat_completions_payload(request),
            http_opener=self._http_opener,
            timeout_seconds=self.request_timeout_seconds,
            headers={
                "Authorization": f"Bearer {self._api_key()}",
                "Content-Type": "application/json",
            },
            error_prefix="OpenRouter chat completions failed",
            redact_body=True,
        )

    def _zai_request(self, request: _ChatRequest) -> dict[str, Any]:
        """Post a chat-completion request to z.ai, stripping the ``zai/`` prefix."""
        wire_request = replace(request, model=request.model.removeprefix(ZAI_MODEL_PREFIX))
        return post_json(
            f"{self._zai_base_url()}/chat/completions",
            _chat_completions_payload(wire_request),
            http_opener=self._http_opener,
            timeout_seconds=self.request_timeout_seconds,
            headers={
                "Authorization": f"Bearer {self._zai_api_key()}",
                "Content-Type": "application/json",
            },
            error_prefix="z.ai chat completions failed",
            redact_body=True,
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
        messages: list[dict[str, str]] = []
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
        choices: list[dict[str, Any]] = response.get("choices", [])
        if not choices:
            provider = "z.ai" if model.startswith(ZAI_MODEL_PREFIX) else "OpenRouter"
            raise RuntimeError(f"{provider} returned no choices.")
        msg: dict[str, Any] = choices[0].get("message", {})
        # ``or ""`` guards content: null — some providers send it when the
        # whole completion budget went to reasoning_content.
        return str(msg.get("content") or "")

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
        with inline image data. Otherwise falls back to text-only chat()
        (images are dropped with a warning).

        Args:
            prompt: The text prompt.
            model: Full model ID (e.g. "google/gemini-3-flash-preview").
            images_b64: Base64-encoded images (no data URI prefix).
            mime_type: Image MIME type for Gemini API.
            max_tokens: Max output tokens.
            temperature: Generation temperature.

        Returns:
            Model's text response.
        """
        if not images_b64:
            return self.chat(prompt, model=model, max_tokens=max_tokens, temperature=temperature)

        if model.startswith("google/"):
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

        _warn_dropped_images(len(images_b64), model)
        return self.chat(prompt, model=model, max_tokens=max_tokens, temperature=temperature)

    def _call_gemini_api(self, request: _GeminiRequest) -> str:
        """Call Gemini's generateContent API with text + inline images."""
        response = post_json(
            self._gemini_url(request.model),
            json.dumps(_build_gemini_payload(request)).encode("utf-8"),
            http_opener=self._http_opener,
            timeout_seconds=self.request_timeout_seconds,
            headers={"Content-Type": "application/json"},
            error_prefix="Gemini generateContent failed",
            redact_body=False,
        )
        return _first_candidate_text(response)

    def _gemini_url(self, model: str) -> str:
        """Build the generateContent endpoint URL after resolving the API key."""
        key = self._gemini_api_key()
        gemini_model = model.removeprefix("google/")
        return (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{gemini_model}:generateContent?key={key}"
        )

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


def _chat_completions_payload(request: _ChatRequest) -> bytes:
    """Build the OpenAI-compatible chat body shared by OpenRouter and z.ai."""
    body: dict[str, Any] = {
        "model": request.model,
        "messages": request.messages,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "top_p": request.top_p,
        "frequency_penalty": request.frequency_penalty,
    }
    return json.dumps(body).encode()


def _build_gemini_payload(request: _GeminiRequest) -> dict[str, Any]:
    parts: list[dict[str, Any]] = [{"text": request.prompt}]
    for img in request.images_b64:
        parts.append({"inline_data": {"mime_type": request.mime_type, "data": img}})
    return {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_tokens,
        },
    }


def _first_candidate_text(response: dict[str, Any]) -> str:
    candidates: list[dict[str, Any]] = response.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")
    parts_out: list[dict[str, Any]] = candidates[0].get("content", {}).get("parts", [])
    if not parts_out:
        raise RuntimeError("Gemini returned no content parts.")
    return str(parts_out[0].get("text", ""))


def _warn_dropped_images(count: int, model: str) -> None:
    logging.warning(
        "chat_multimodal: dropping %d images for non-Google model '%s'",
        count,
        model,
    )
