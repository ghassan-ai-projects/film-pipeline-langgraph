"""Shared parsing helpers for LLM reviewer responses.

Both the frame reviewer and the contact-sheet reviewer ask a model for JSON and
must tolerate the model wrapping that JSON in a markdown code fence. The unwrap
rule is one rule, so it lives here rather than in each reviewer.
"""

from __future__ import annotations

_FENCE = "```"


def strip_markdown_fences(text: str) -> str:
    """Remove a wrapping markdown code fence from ``text``, if present.

    Returns the inner text with surrounding whitespace removed. Text that does
    not start with a fence is returned stripped but otherwise unchanged.
    """
    stripped = text.strip()
    if stripped.startswith(_FENCE):
        stripped = stripped.split("\n", 1)[-1]
        if stripped.endswith(_FENCE):
            stripped = stripped[: -len(_FENCE)]
    return stripped.strip()
