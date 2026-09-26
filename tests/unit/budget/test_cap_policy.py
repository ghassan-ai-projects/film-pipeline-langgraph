"""The budget cap reader has one owner.

`audit/12` recorded the cap being derived in four shapes, eight gate sites of
which only one could actually refuse, and a `SpendRecord` with zero writers.

What remains after the dead-surface deletion (see `budget/__init__.py`): the
single cap reader. The enforcement surface these tests used to pin —
`authorize_spend`, `record_spend`, `BudgetLedger`, `BudgetExceeded`,
`budget_cap_prompt_value` — had **zero production callers** and was deleted. The
refusal that *does* work is `generation.ledger.approve_spend`, which raises before
persisting and is covered in `tests/unit/generation/test_ledger.py`.

These tests are kept because `cap_for` is live: it is the generation planner's
only cap read, and the "unconfigured means unlimited, not zero" rule it pins is
the difference between a project that runs and one that silently refuses.
"""

from __future__ import annotations

import pytest

from film_pipeline.budget import UNLIMITED, cap_for


class TestCapFor:
    def test_reads_a_declared_attribute(self) -> None:
        class _Profile:
            budget_cap_usd = 250.0

        assert cap_for(_Profile()) == 250.0

    def test_reads_a_mapping_key(self) -> None:
        assert cap_for({"budget_cap_usd": 75.0}) == 75.0

    def test_absent_cap_is_unlimited_not_zero(self) -> None:
        """An unconfigured project must not be silently blocked."""
        assert cap_for({}) is UNLIMITED
        assert cap_for(None) is UNLIMITED

        class _NoCap:
            pass

        assert cap_for(_NoCap()) is UNLIMITED

    def test_explicit_none_is_unlimited(self) -> None:
        assert cap_for({"budget_cap_usd": None}) is UNLIMITED

    @pytest.mark.parametrize("bad", ["abc", object(), -1.0, -0.01])
    def test_unusable_values_are_unlimited_rather_than_fatal(self, bad: object) -> None:
        """A malformed cap must not crash a gate; it degrades to unlimited."""
        assert cap_for({"budget_cap_usd": bad}) is UNLIMITED

    def test_zero_is_a_real_cap(self) -> None:
        """Zero means 'spend nothing', which is distinct from unconfigured."""
        assert cap_for({"budget_cap_usd": 0.0}) == 0.0


def test_the_module_has_no_enforcement_surface_left() -> None:
    """The deleted symbols must not come back without a caller.

    They were removed because every one had zero production callers, while
    `authorize_spend`'s own docstring claimed to be the single refusal path. If a
    future change genuinely needs a gate here, it should be justified by a call
    site — this test is a speed bump, not a prohibition.
    """
    import film_pipeline.budget as budget_module

    removed = {
        "authorize_spend",
        "record_spend",
        "budget_cap_prompt_value",
        "BudgetLedger",
        "BudgetExceeded",
    }
    resurrected = sorted(name for name in removed if hasattr(budget_module, name))

    assert not resurrected, (
        f"budget reintroduced {resurrected}. Each was deleted for having zero "
        "production callers; if one is genuinely needed now, add it with a caller "
        "and remove it from this list."
    )
    assert budget_module.__all__ == ["UNLIMITED", "cap_for"]
