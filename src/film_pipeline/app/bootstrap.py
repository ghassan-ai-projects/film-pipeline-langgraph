"""Bootstrap validation — fails fast if the environment is misconfigured."""

from __future__ import annotations

from pathlib import Path


def validate_environment() -> list[str]:
    """Check required directories and configuration exist.

    Returns a list of actionable error messages. Empty list = ready.
    """
    issues: list[str] = []

    # Check profile directory
    profiles_dir = Path("profiles")
    if not profiles_dir.is_dir():
        issues.append("profiles/ directory not found. Create it with at least one profile YAML.")

    # Check KB manifest
    kb_manifest = Path("film-knowledge-base/manifest.yaml")
    if not kb_manifest.exists():
        issues.append(
            "film-knowledge-base/manifest.yaml not found. "
            "The KB manifest is required for context packets."
        )

    # Check writable artifacts directory
    artifacts_dir = Path("artifacts")
    if artifacts_dir.exists() and not artifacts_dir.is_dir():
        issues.append("artifacts exists but is not a directory.")
    if artifacts_dir.exists():
        try:
            test = artifacts_dir / ".write_test"
            test.touch()
            test.unlink()
        except OSError:
            issues.append("Cannot write to artifacts/ directory.")

    return issues


def bootstrap_ok() -> bool:
    """Return True if the environment passes bootstrap checks."""
    return len(validate_environment()) == 0
