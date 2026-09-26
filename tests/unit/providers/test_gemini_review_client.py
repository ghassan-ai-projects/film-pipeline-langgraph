"""Tests for the Gemini review client.

The client moved from `generation` to `providers` because it talks to a concrete
provider API and resolves that provider's credentials. It also gained transport
error normalization while moving: the previous implementation called
`urllib` directly, so an HTTP failure surfaced a raw `urllib` error whose
message can contain the request URL — and that URL carries the API key.
"""

from __future__ import annotations

import json
import urllib.error
from typing import Any

import pytest

from film_pipeline.providers.gemini_review_client import (
    GEMINI_API_BASE,
    call_gemini,
)


class _BodyHTTPError(urllib.error.HTTPError):
    """An ``HTTPError`` whose body is supplied eagerly.

    Subclassing rather than patching ``read`` keeps the override type-correct;
    the stdlib attribute is typed read-only.
    """

    def __init__(self, url: str, code: int, body: bytes) -> None:
        super().__init__(url, code, "err", {}, None)  # type: ignore[arg-type]
        self._body = body

    def read(self, _n: int = -1) -> bytes:
        return self._body


def _http_error(url: str, code: int, body: bytes) -> urllib.error.HTTPError:
    """Build an HTTPError whose ``read()`` returns ``body``."""
    return _BodyHTTPError(url, code, body)


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class _Opener:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.requests: list[Any] = []

    def open(self, req: Any, **kwargs: Any) -> Any:
        self.requests.append(req)
        if self._error is not None:
            raise self._error
        return self._response


class TestCallGemini:
    def test_returns_the_parsed_response(self) -> None:
        opener = _Opener(_Response({"candidates": [{"content": "ok"}]}))
        result = call_gemini("prompt", "aGk=", "gemini-2.0", http_opener=opener, api_key="k")
        assert result == {"candidates": [{"content": "ok"}]}

    def test_posts_to_the_generate_content_endpoint(self) -> None:
        opener = _Opener(_Response({}))
        call_gemini("prompt", "aGk=", "gemini-2.0", http_opener=opener, api_key="k")
        url = opener.requests[0].full_url
        assert url.startswith(f"{GEMINI_API_BASE}/gemini-2.0:generateContent")

    def test_sends_the_prompt_and_inline_png(self) -> None:
        opener = _Opener(_Response({}))
        call_gemini("describe this", "aGk=", "gemini-2.0", http_opener=opener, api_key="k")
        body = json.loads(opener.requests[0].data.decode("utf-8"))
        parts = body["contents"][0]["parts"]
        assert parts[0] == {"text": "describe this"}
        assert parts[1]["inline_data"] == {"mime_type": "image/png", "data": "aGk="}

    def test_missing_credential_raises_actionable_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Isolated from the ambient environment: no real key may leak in."""
        monkeypatch.setattr(
            "film_pipeline.providers.gemini_review_client.lookup", lambda _provider: None
        )
        with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
            call_gemini("p", "aGk=", "gemini-2.0", http_opener=_Opener(_Response({})), api_key="")

    def test_explicit_key_is_used_without_consulting_the_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "film_pipeline.providers.gemini_review_client.lookup",
            lambda _provider: pytest.fail("lookup must not be called when api_key is given"),
        )
        opener = _Opener(_Response({"ok": True}))
        assert call_gemini("p", "aGk=", "m", http_opener=opener, api_key="explicit") == {"ok": True}


class TestTransportFailures:
    def test_os_error_becomes_a_prefixed_runtime_error(self) -> None:
        opener = _Opener(error=OSError("connection reset"))
        with pytest.raises(RuntimeError, match="Gemini review call failed"):
            call_gemini("p", "aGk=", "m", http_opener=opener, api_key="k")

    def test_http_error_reports_the_status_code(self) -> None:
        opener = _Opener(error=_http_error("https://example.invalid", 429, b"rate limited"))
        with pytest.raises(RuntimeError, match="HTTP 429"):
            call_gemini("p", "aGk=", "m", http_opener=opener, api_key="k")

    def test_api_key_is_redacted_from_the_error(self) -> None:
        """The request URL carries the key, so it must not reach the message."""
        secret = "SUPER-SECRET-KEY-12345"
        opener = _Opener(
            error=_http_error(
                f"{GEMINI_API_BASE}/m:generateContent?key={secret}",
                403,
                f"denied for key={secret}".encode(),
            )
        )
        with pytest.raises(RuntimeError) as excinfo:
            call_gemini("p", "aGk=", "m", http_opener=opener, api_key=secret)
        assert secret not in str(excinfo.value)

    def test_error_body_is_truncated(self) -> None:
        opener = _Opener(error=_http_error("https://example.invalid", 500, b"x" * 5000))
        with pytest.raises(RuntimeError) as excinfo:
            call_gemini("p", "aGk=", "m", http_opener=opener, api_key="k")
        assert len(str(excinfo.value)) < 400
