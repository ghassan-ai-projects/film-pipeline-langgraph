"""Provider credential management.

Credentials come from environment variables, never from code or config.
Every read is redacted: keys are never logged, stored in artifacts, or
included in error messages.

Provider → env var mapping:
- Seedance 2.0: ``OPENROUTER_API_KEY``
- Veo 3.1 Fast: ``GOOGLE_API_KEY``
"""

from __future__ import annotations

import os
import re

REDACTION_RE = re.compile(r"(sk-|key-|AIza)[a-zA-Z0-9_\-]{8,}")


def lookup(provider_id: str) -> str | None:
    """Look up the API key for a provider from environment variables.

    Returns None if the key is not set.
    """
    env_var = _env_var_for(provider_id)
    if not env_var:
        return None
    return os.environ.get(env_var)


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
    }
    return mapping.get(provider_id)
