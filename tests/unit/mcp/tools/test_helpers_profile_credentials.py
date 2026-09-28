"""The profile-credential check `mcp` owns.

It used to be `OperatorService.missing_profile_credentials`, then briefly a
composition-root helper. It is neither: it composes
`config.profile_resolver.provider_specs` (which providers the profile selects)
with `providers.credentials` (which of their keys are unset), and `mcp` may import
both. Keeping it in `mcp/tools/helpers.py` means `mcp` reaches the composition
root exactly once — for the adapter factory, which genuinely needs the concrete
provider classes — instead of twice.

See `docs/modularity-improvements/03-one-use-case-layer.md`.
"""

from __future__ import annotations

import pytest

from film_pipeline.mcp.tools.helpers import missing_profile_credentials
from film_pipeline.providers.credentials import MissingProviderCredential


def test_missing_profile_credentials_uses_resolved_provider_specs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A profile selecting an unconfigured provider reports its env var."""
    monkeypatch.setattr("film_pipeline.providers.credentials.is_configured", lambda _: False)

    missing = missing_profile_credentials(
        {},
        {
            "providers": {
                "video": [{"provider_id": "seedance-openrouter", "models": []}],
            }
        },
    )

    assert missing == [MissingProviderCredential("seedance-openrouter", "OPENROUTER_API_KEY")]


def test_missing_profile_credentials_is_empty_when_the_key_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("film_pipeline.providers.credentials.is_configured", lambda _: True)

    missing = missing_profile_credentials(
        {},
        {"providers": {"video": [{"provider_id": "seedance-openrouter", "models": []}]}},
    )

    assert missing == []
