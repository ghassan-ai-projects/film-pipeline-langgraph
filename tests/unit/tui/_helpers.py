"""Shared test helpers for TUI unit tests."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any


def _run[ResultT](async_fn: Coroutine[Any, Any, ResultT]) -> ResultT:
    """Run an async test body in a fresh event loop."""
    return asyncio.run(async_fn)
