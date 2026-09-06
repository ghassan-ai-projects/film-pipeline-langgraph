"""Shared test helpers for provider transport boundaries."""

from __future__ import annotations

import json
from io import BytesIO
from unittest import mock


def _mock_opener(response_body: dict[str, object], code: int = 200) -> mock.Mock:
    """Build a mock urllib opener that returns a canned JSON response."""

    def _open(_req: object) -> BytesIO:
        if code >= 400:
            raise OSError(f"HTTP {code}")
        return BytesIO(json.dumps(response_body).encode())

    opener = mock.Mock()
    opener.open = _open
    return opener
