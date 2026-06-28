"""Textual operator cockpit for the film pipeline.

Run with:

```
python -m film_pipeline.tui.app
```
"""

from __future__ import annotations

import argparse
import sys

from film_pipeline.tui.app_actions import AppActionsMixin
from film_pipeline.tui.app_commands import AppCommandsMixin
from film_pipeline.tui.app_render import AppRenderMixin
from film_pipeline.tui.app_shell import AppShell


class FilmCockpitApp(AppActionsMixin, AppCommandsMixin, AppRenderMixin, AppShell):
    """Bloomberg-style terminal cockpit for film pipeline operations."""


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Textual TUI."""
    parser = argparse.ArgumentParser(description="Run the film pipeline Textual cockpit.")
    parser.add_argument("--create", action="store_true", help="Open the create-project command.")
    args = parser.parse_args(argv)
    FilmCockpitApp(start_create=args.create).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
