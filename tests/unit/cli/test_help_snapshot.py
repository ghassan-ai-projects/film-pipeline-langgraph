"""Golden snapshot for ``film-pipeline-run --help``.

Pins the help output byte-for-byte, including option-registration order
(argparse emits usage/options in registration order — e.g. ``--confirm-real``
must stay after ``--constraints-file``, see run.py).
"""

from __future__ import annotations

import pytest

from film_pipeline.cli.run import _build_parser

# Generated from the current parser at a fixed width (COLUMNS=100). Do not
# reformat by hand — regenerate via:
#   COLUMNS=100 uv run python -c \
#     "from film_pipeline.cli.run import _build_parser; \
#      print(repr(_build_parser().format_help()))"
_GOLDEN_HELP = """usage: film-pipeline-run [-h] [--project-id PROJECT_ID] [--title TITLE]
                         [--runtime-mode {mock,real}] [--target-phase TARGET_PHASE]
                         [--target-runtime-seconds TARGET_RUNTIME_SECONDS]
                         [--target-scene-count TARGET_SCENE_COUNT]
                         [--provider-profile PROVIDER_PROFILE] [--quality-profile QUALITY_PROFILE]
                         [--film-type-profile FILM_TYPE_PROFILE] [--runtime-root RUNTIME_ROOT]
                         [--constraints-file CONSTRAINTS_FILE] [--confirm-real]
                         file

Run the full film pipeline from an idea file with no human gates.

positional arguments:
  file                  Idea file to run. Supported formats: .md, .pdf, .txt.

options:
  -h, --help            show this help message and exit
  --project-id PROJECT_ID
                        Project id. Defaults to the file stem.
  --title TITLE         Film title. Defaults to the project id.
  --runtime-mode {mock,real}
                        Execution mode. Mock is fast and zero-cost (default). Real uses configured
                        providers.
  --target-phase TARGET_PHASE
                        Phase to run through before stopping. Default: shot_bible.
  --target-runtime-seconds TARGET_RUNTIME_SECONDS
                        Target runtime in seconds. Defaults to the value in the idea text or 180.
  --target-scene-count TARGET_SCENE_COUNT
                        Target scene count. Defaults to the value in the idea text.
  --provider-profile PROVIDER_PROFILE
                        Provider profile for real mode. Default: provider.seedance_primary.
  --quality-profile QUALITY_PROFILE
                        Quality profile. Default: quality.studio.
  --film-type-profile FILM_TYPE_PROFILE
                        Film-type profile. Default: film-type.narrative.
  --runtime-root RUNTIME_ROOT
                        Directory for runtime state and artifacts. Default: <storage
                        root>/../runs/default (see FILM_PIPELINE_STORAGE_ROOT).
  --constraints-file CONSTRAINTS_FILE
                        Optional JSON/YAML file with explicit project constraints.
  --confirm-real        Confirm that real-mode provider spend is acceptable. May also be set via
                        FILM_PIPELINE_CONFIRM_REAL=1.
"""


def test_cli_help_matches_golden_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pin the wrap width so argparse's terminal-size probe cannot vary the
    # output between hosts/CI runners.
    monkeypatch.setenv("COLUMNS", "100")
    assert _build_parser().format_help() == _GOLDEN_HELP
