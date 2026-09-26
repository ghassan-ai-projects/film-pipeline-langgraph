"""The provider identity catalogue — the contract that replaced the pricing table.

`providers/catalog.py` exists because the deleted pricing table was accidentally
also serving as the unknown-provider guard: its own comment said the mock rows
were there "so planning never treats an unknown provider as free". Removing cost
therefore had to preserve *identity*, and these tests pin that identity so it
cannot quietly drift the way the table did.

The load-bearing claim is in `KNOWN_PROVIDER_IDS`'s comment: every id listed is
one the system can build an adapter for. If that ever stops being true, the
predicate overstates what it knows and planning can accept a provider that cannot
run — exactly the failure the original guard was there to prevent.
"""

from __future__ import annotations

import pytest

from film_pipeline.providers.catalog import (
    KNOWN_PROVIDER_IDS,
    PROVIDER_IDS_BY_MODE,
    is_known_provider,
    supported_provider_ids,
)
from film_pipeline.studio._provider_factory import build_provider_adapter


def test_every_known_id_is_buildable() -> None:
    """`is_known_provider` must not accept an id the factory cannot build.

    This is the guard's whole purpose: "known" has to mean "usable". A typo is
    rejected trivially; the interesting case is an id that is *listed* but has no
    adapter behind it.
    """
    for provider_id in sorted(KNOWN_PROVIDER_IDS):
        adapter = build_provider_adapter(provider_id)
        assert adapter is not None, f"{provider_id} is known but not buildable"
        assert adapter.entry.provider_id == provider_id


@pytest.mark.parametrize(
    "typo",
    ["", "veo-fastt", "seedance", "VEO-FAST", "imagen-4 ", "veo-3.1", "unknown-provider"],
)
def test_typos_and_near_misses_are_rejected(typo: str) -> None:
    """Near misses must not pass: an id is real or it is not."""
    assert is_known_provider(typo) is False


def test_match_is_exact_not_prefix_or_case_folded() -> None:
    """A real id is accepted; case and whitespace variants are not."""
    assert is_known_provider("veo-fast") is True
    assert is_known_provider(" veo-fast") is False
    assert is_known_provider("veo-fast ") is False


def test_every_mode_seeds_only_known_ids() -> None:
    """A mode must never seed an id the catalogue does not know.

    The reverse does not hold and is not asserted: the alias ids
    (`veo-3.1-fast`, `imagen-4`) are buildable identities that no mode seeds,
    because seeding uses one canonical id per real provider.
    """
    for mode, ids in PROVIDER_IDS_BY_MODE.items():
        for provider_id in ids:
            assert is_known_provider(provider_id) is True, f"{mode} seeds unknown id {provider_id}"


def test_supported_provider_ids_falls_back_to_mock() -> None:
    """An unrecognised mode yields the mock set rather than an empty one.

    Returns-the-default is the deliberate behaviour: a typo'd mode must not be
    able to make every provider unknown and silently block planning.
    """
    assert supported_provider_ids("mock") == PROVIDER_IDS_BY_MODE["mock"]
    assert supported_provider_ids("no-such-mode") == PROVIDER_IDS_BY_MODE["mock"]


def test_real_and_mock_modes_do_not_overlap() -> None:
    """A real-mode runtime must not advertise mock providers as reachable."""
    real = set(supported_provider_ids("real"))
    mock = set(supported_provider_ids("mock"))
    assert not (real & mock), f"modes share provider ids: {sorted(real & mock)}"
