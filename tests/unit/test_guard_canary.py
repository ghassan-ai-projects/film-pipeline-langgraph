"""Canary: write into a watched production root; the session guard MUST fail."""

from pathlib import Path


def test_canary_writes_production_root() -> None:
    target = Path(".film-pipeline-run") / "GUARD_CANARY_SHOULD_TRIP.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("canary")
