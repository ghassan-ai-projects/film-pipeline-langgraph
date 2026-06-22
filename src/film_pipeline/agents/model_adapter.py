"""Model adapter — calls an LLM via OpenRouter for agent execution.

Same pattern as ``SeedanceOpenRouterProvider``: constructor-injected HTTP opener
so tests can mock the network without any test-only dependency.

Model selection is ALWAYS explicit: no hardcoded defaults. Callers must resolve
the model through the routing layer before invoking this adapter.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from film_pipeline.providers.adapters.seedance_openrouter import OPENROUTER_API
from film_pipeline.providers.credentials import lookup, redact


class ModelAdapter:
    """Call a chat model through OpenRouter.

    Testable: pass ``_http_opener`` to inject a mock HTTP handler.
    """

    def __init__(
        self,
        http_opener: Any = None,
        api_key: str | None = None,
        gemini_api_key: str | None = None,
    ) -> None:
        self._http_opener = http_opener
        self._configured_api_key = api_key
        self._configured_gemini_api_key = gemini_api_key

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

    def _request(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.95,
        frequency_penalty: float = 0.0,
    ) -> dict[str, Any]:
        """Post a chat-completion request to OpenRouter and return parsed JSON.

        ``model`` is REQUIRED — no hardcoded default. The caller must resolve
        the model through config/routing before invoking.
        """
        url = f"{OPENROUTER_API}/chat/completions"
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
        }
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self._api_key()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        opener: Any = self._http_opener or urllib.request.build_opener()
        try:
            with opener.open(req) as resp:
                raw: Any = json.loads(resp.read())
                return dict(raw)
        except (urllib.error.HTTPError, OSError) as e:
            detail = str(e)
            if isinstance(e, urllib.error.HTTPError):
                body_text = e.read().decode(errors="replace")
                detail = f"HTTP {e.code}: {redact(body_text)[:200]}"
            raise RuntimeError(f"OpenRouter chat completions failed: {detail}") from e

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
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
        )
        choices: list[dict[str, Any]] = response.get("choices", [])
        if not choices:
            raise RuntimeError("OpenRouter returned no choices.")
        msg: dict[str, Any] = choices[0].get("message", {})
        return str(msg.get("content", ""))

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
                prompt=prompt,
                model=model,
                images_b64=images_b64,
                mime_type=mime_type,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        import logging

        logging.warning(
            "chat_multimodal: dropping %d images for non-Google model '%s'",
            len(images_b64),
            model,
        )
        return self.chat(prompt, model=model, max_tokens=max_tokens, temperature=temperature)

    def _call_gemini_api(
        self,
        prompt: str,
        model: str,
        images_b64: list[str],
        mime_type: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Call Gemini's generateContent API with text + inline images."""
        key = self._gemini_api_key()
        gemini_model = model.removeprefix("google/")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{gemini_model}:generateContent?key={key}"
        )

        parts: list[dict[str, Any]] = [{"text": prompt}]
        for img in images_b64:
            parts.append({"inline_data": {"mime_type": mime_type, "data": img}})

        body = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )

        opener: Any = self._http_opener or urllib.request.build_opener()
        try:
            with opener.open(req) as resp:
                raw: Any = json.loads(resp.read().decode("utf-8"))
                response: dict[str, Any] = dict(raw)
        except (urllib.error.HTTPError, OSError) as e:
            detail = str(e)
            if isinstance(e, urllib.error.HTTPError):
                body_text = e.read().decode(errors="replace")
                detail = f"HTTP {e.code}: {body_text[:200]}"
            raise RuntimeError(f"Gemini generateContent failed: {detail}") from e

        candidates: list[dict[str, Any]] = response.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")
        parts_out: list[dict[str, Any]] = candidates[0].get("content", {}).get("parts", [])
        if not parts_out:
            raise RuntimeError("Gemini returned no content parts.")
        return str(parts_out[0].get("text", ""))

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

        # Strategy 1: Direct JSON parse
        try:
            return dict(json.loads(text))
        except json.JSONDecodeError:
            pass

        # Strategy 2: extract from markdown fences (most common with Gemini)
        for fence_start in ("```json", "```JSON", "```"):
            if fence_start not in text:
                continue
            # Find the LAST opening fence and FIRST closing fence after it
            # (Gemini sometimes has multiple code blocks)
            last_open = text.rfind(fence_start)
            block = text[last_open + len(fence_start) :]
            close_idx = block.find("```")
            if close_idx != -1:
                block = block[:close_idx]
            candidate = block.strip()
            if not candidate:
                continue
            # Handle Gemini injecting trailing content right after closing ````
            try:
                result: Any = json.loads(candidate)
                return dict(result)
            except json.JSONDecodeError:
                pass

        # Strategy 3: Find the outermost brace pair anywhere in text
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            candidate = text[brace_start : brace_end + 1]
            try:
                result = json.loads(candidate)
                return dict(result)
            except json.JSONDecodeError:
                pass

        # Strategy 4: Find outermost bracket pair (for array responses)
        bracket_start = text.find("[")
        bracket_end = text.rfind("]")
        if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
            candidate = text[bracket_start : bracket_end + 1]
            try:
                result = json.loads(candidate)
                return dict(result)
            except (json.JSONDecodeError, TypeError):
                pass

        raise ValueError(
            f"Model response is not valid JSON after 4 extraction strategies. "
            f"Response length: {len(text)} chars. "
            f"Preview: {text[:300]}"
        )
