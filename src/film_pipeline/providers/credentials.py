"""Provider credential management.

Credentials come from environment variables, never from code or config.
Every read is redacted: keys are never logged, stored in artifacts, or
included in error messages.

Provider → env var mapping:
- Seedance 2.0: ``OPENROUTER_API_KEY``
- Veo 3.1 Fast: ``GOOGLE_API_KEY``
- Imagen 4: ``GOOGLE_API_KEY``
- z.ai (GLM chat models): ``ZAI_API_KEY``
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# z.ai keys use an ``id.secret`` shape rather than a provider-specific prefix.
# Keep this deliberately conservative so ordinary dotted prose is not masked.
REDACTION_RE = re.compile(
    r"(?:sk-|key-|AIza)[a-zA-Z0-9_\-]{8,}|[a-fA-F0-9]{24,}\.[A-Za-z0-9_\-]{8,}"
)
ENV_FILE_NAME = ".env"


def lookup(provider_id: str) -> str | None:
    """Look up the API key for a provider from environment variables.

    Environment variables take precedence. If not present, fall back to a
    local ``.env`` file in the current working directory.
    """
    env_var = _env_var_for(provider_id)
    if not env_var:
        return None
    return env_or_dotenv(env_var)


def env_or_dotenv(env_var: str) -> str | None:
    """Resolve an environment variable, falling back to the local ``.env`` file.

    The environment wins over ``.env``. Used for credentials and for
    non-secret provider settings such as ``ZAI_BASE_URL``.
    """
    env_value = os.environ.get(env_var)
    if env_value and env_value.strip():
        return env_value.strip()
    dotenv_value = _read_dotenv(Path.cwd()).get(env_var)
    if dotenv_value and dotenv_value.strip():
        return dotenv_value.strip()
    return None


def is_configured(provider_id: str) -> bool:
    """Check whether a provider has credentials configured."""
    return lookup(provider_id) is not None


def redact(text: str) -> str:
    """Redact API keys from a string. Safe to call on any text."""
    return REDACTION_RE.sub("[REDACTED]", text)


def _env_var_for(provider_id: str) -> str | None:
    """Map provider_id to environment variable name."""
    mapping: dict[str, str] = {
        "seedance-openrouter": "OPENROUTER_API_KEY",
        "veo-fast": "GOOGLE_API_KEY",
        "veo-lite": "GOOGLE_API_KEY",
        "veo-3.1-fast": "GOOGLE_API_KEY",
        "gemini-imagen-4": "GOOGLE_API_KEY",
        "imagen-4": "GOOGLE_API_KEY",
        "zai": "ZAI_API_KEY",
    }
    return mapping.get(provider_id)


def _read_dotenv(path: Path) -> dict[str, str]:
    """Read simple KEY=VALUE pairs from a local ``.env`` file."""
    env_path = path / ENV_FILE_NAME
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed_key = key.strip()
        parsed_value = value.strip().strip("\"'")
        if parsed_key:
            values[parsed_key] = parsed_value
    return values
