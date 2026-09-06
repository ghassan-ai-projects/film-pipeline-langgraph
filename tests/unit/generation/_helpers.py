"""Shared helpers for generation unit tests."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import Mock


def _mock_opener(response_body: dict[str, Any]) -> Mock:
    """Return a mock HTTP opener that returns *response_body* as JSON."""
    response = Mock()
    response.read.return_value = json.dumps(response_body).encode("utf-8")
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)

    opener = Mock()
    opener.open.return_value = response
    return opener
