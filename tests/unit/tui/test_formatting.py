"""Tests for terminal formatting helpers used by the TUI."""

from __future__ import annotations

import json
from dataclasses import dataclass

from film_pipeline.tui.formatting import pretty, table, title


@dataclass(frozen=True)
class Example:
    name: str
    count: int


def test_title_underlines_text() -> None:
    assert title("Dashboard") == "\nDashboard\n========="


def test_table_renders_headers_rows_and_complex_cells() -> None:
    rendered = table(
        [
            {"name": "alpha", "tags": ["ready", "review"], "meta": {"b": 2, "a": 1}},
            {"name": "beta", "tags": (), "meta": {}},
        ],
        ["name", "tags", "meta"],
    )

    lines = rendered.splitlines()
    assert lines[0].startswith("name")
    assert lines[1].startswith("-----")
    assert "ready, review" in rendered
    assert json.dumps({"a": 1, "b": 2}, sort_keys=True) in rendered


def test_table_renders_empty_body_with_header_and_divider() -> None:
    rendered = table([], ["project", "phase"])

    assert rendered.splitlines() == ["project  phase", "-------  -----"]


def test_pretty_serializes_dataclasses_and_unknown_objects() -> None:
    assert pretty(Example(name="scene", count=2)) == '{\n  "count": 2,\n  "name": "scene"\n}'
    assert pretty({"value": object()}).startswith('{\n  "value": "<object object at ')
