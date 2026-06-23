"""Formatting helpers for the terminal console."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass


def title(text: str) -> str:
    """Render a section title."""
    return f"\n{text}\n{'=' * len(text)}"


def table(rows: Iterable[Mapping[str, object]], columns: list[str]) -> str:
    """Render a compact ASCII table."""
    row_list = list(rows)
    widths = {
        column: max([len(column), *(len(_cell(row.get(column, ""))) for row in row_list)])
        for column in columns
    }
    header = "  ".join(column.ljust(widths[column]) for column in columns)
    divider = "  ".join("-" * widths[column] for column in columns)
    body = [
        "  ".join(_cell(row.get(column, "")).ljust(widths[column]) for column in columns)
        for row in row_list
    ]
    return "\n".join([header, divider, *body]) if body else "\n".join([header, divider])


def pretty(value: object) -> str:
    """Render nested data for inspection."""
    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    return json.dumps(value, indent=2, sort_keys=True, default=str)


def _cell(value: object) -> str:
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value)
