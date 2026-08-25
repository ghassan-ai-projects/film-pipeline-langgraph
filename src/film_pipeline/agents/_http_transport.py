"""HTTP transport for model adapters — POST JSON and normalize failures.

Owns the network boundary so ``model_adapter`` can read as request shaping
and key resolution only: build the request, honor the injected test opener,
and turn transport errors into specific RuntimeErrors without leaking
response-body secrets.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from inspect import Parameter, signature
from typing import Any

from film_pipeline.providers.credentials import redact


def post_json(
    url: str,
    payload_bytes: bytes,
    *,
    http_opener: Any,
    timeout_seconds: float | None,
    headers: dict[str, str],
    error_prefix: str,
    redact_body: bool,
) -> dict[str, Any]:
    """POST ``payload_bytes`` to ``url`` and return the parsed JSON response.

    Transport failures raise ``RuntimeError`` prefixed with ``error_prefix``.
    HTTP error bodies are truncated to 200 chars and secret-redacted when
    ``redact_body`` is set.
    """
    req = urllib.request.Request(url, data=payload_bytes, headers=headers, method="POST")
    opener: Any = http_opener or urllib.request.build_opener()
    try:
        with _open_with_timeout(opener.open, req, timeout_seconds) as resp:
            raw: Any = json.loads(resp.read())
            return dict(raw)
    except (urllib.error.HTTPError, OSError) as e:
        detail = str(e)
        if isinstance(e, urllib.error.HTTPError):
            body_text = e.read().decode(errors="replace")
            body_detail = redact(body_text)[:200] if redact_body else body_text[:200]
            detail = f"HTTP {e.code}: {body_detail}"
        raise RuntimeError(f"{error_prefix}: {detail}") from e


def _open_with_timeout(
    open_fn: Callable[..., Any],
    req: urllib.request.Request,
    timeout_seconds: float | None,
) -> Any:
    """Call opener.open with a timeout when the injected opener supports it."""
    if timeout_seconds is None or not _accepts_timeout_kw(open_fn):
        return open_fn(req)
    return open_fn(req, timeout=timeout_seconds)


def _accepts_timeout_kw(open_fn: Callable[..., Any]) -> bool:
    """Return whether a callable can accept a ``timeout=`` keyword."""
    try:
        params = signature(open_fn).parameters
    except (TypeError, ValueError):
        return True
    return any(param.kind == Parameter.VAR_KEYWORD for param in params.values()) or any(
        name == "timeout" for name in params
    )
