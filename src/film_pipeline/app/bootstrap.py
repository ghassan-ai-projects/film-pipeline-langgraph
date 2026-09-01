"""Bootstrap validation — fails fast if the environment is misconfigured."""

from __future__ import annotations

import os
from pathlib import Path

from film_pipeline.kb.paths import kb_manifest_path
from film_pipeline.providers import credentials


def validate_environment() -> list[str]:
    """Check required directories and configuration exist.

    Returns a list of actionable error messages. Empty list = ready.
    """
    return [
        *_missing_profiles_dir_issues(),
        *_missing_kb_manifest_issues(),
        *_unusable_artifacts_dir_issues(),
        *_missing_real_mode_credentials_issues(),
    ]


def bootstrap_ok() -> bool:
    """Return True if the environment passes bootstrap checks."""
    return len(validate_environment()) == 0


def _missing_profiles_dir_issues() -> list[str]:
    """Report absence of the profiles directory."""
    if Path("profiles").is_dir():
        return []
    return ["profiles/ directory not found. Create it with at least one profile YAML."]


def _missing_kb_manifest_issues() -> list[str]:
    """Report absence of the KB manifest."""
    if kb_manifest_path().exists():
        return []
    return [
        "film-knowledge-base/index/kb-manifest.yaml not found. "
        "The KB manifest is required for context packets."
    ]


def _unusable_artifacts_dir_issues() -> list[str]:
    """Report an artifacts path that exists but cannot hold written artifacts."""
    artifacts_dir = Path("artifacts")
    if not artifacts_dir.exists():
        return []
    issues: list[str] = []
    if not artifacts_dir.is_dir():
        issues.append("artifacts exists but is not a directory.")
    try:
        probe = artifacts_dir / ".write_test"
        probe.touch()
        probe.unlink()
    except OSError:
        issues.append("Cannot write to artifacts/ directory.")
    return issues


def _missing_real_mode_credentials_issues() -> list[str]:
    """Report a real-mode configuration missing required provider keys.

    Chat agents default to z.ai's ``zai/glm-5.3-flash`` primary, so real mode
    needs ``ZAI_API_KEY`` in addition to OpenRouter. The z.ai check goes
    through the same env-then-.env resolution the adapter uses at call time.
    """
    mcp_mode = os.getenv("FILM_PIPELINE_MCP_MODE", "mock").strip().lower()
    if mcp_mode != "real":
        return []
    issues: list[str] = []
    if not credentials.is_configured("seedance-openrouter"):
        issues.append("OPENROUTER_API_KEY is required when FILM_PIPELINE_MCP_MODE=real.")
    if not credentials.is_configured("zai"):
        issues.append(
            "ZAI_API_KEY is required when FILM_PIPELINE_MCP_MODE=real "
            "because the default chat models use z.ai GLM."
        )
    return issues
