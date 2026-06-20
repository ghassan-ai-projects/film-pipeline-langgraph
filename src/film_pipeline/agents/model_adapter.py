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

    def __init__(self, http_opener: Any = None, api_key: str | None = None) -> None:
        self._http_opener = http_opener
        self._configured_api_key = api_key

    def _api_key(self) -> str:
        key = self._configured_api_key or lookup("seedance-openrouter")
        if not key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Set it in the environment or in a local .env file."
            )
        return key

    def _request(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
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
        )
        choices: list[dict[str, Any]] = response.get("choices", [])
        if not choices:
            raise RuntimeError("OpenRouter returned no choices.")
        msg: dict[str, Any] = choices[0].get("message", {})
        return str(msg.get("content", ""))

    def chat_json(
        self,
        prompt: str,
        *,
        model: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Send a prompt, expect a JSON response, parse and return it.

        ``model`` is REQUIRED — no hardcoded default.
        """
        text = self.chat(
            prompt,
            model=model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        ).strip()

        # Try direct JSON parse first
        try:
            return dict(json.loads(text))
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown fences
        for fence in ("```json", "```"):
            if fence in text:
                block = text.split(fence, 1)[1]
                if "```" in block:
                    block = block.split("```", 1)[0]
                try:
                    result: Any = json.loads(block.strip())
                    return dict(result)
                except json.JSONDecodeError:
                    continue

        raise ValueError(f"Model response is not valid JSON. Response preview: {text[:200]}")
