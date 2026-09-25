"""The budget cap policy has one owner.

`audit/12` recorded the cap being derived in four shapes, eight gate sites of
which only one could actually refuse, and a `SpendRecord` with zero writers.
These tests pin the single reader, the single refusal path, and the spend
record, so a later gate cannot quietly grow its own cap.
"""

from __future__ import annotations

import pytest

from film_pipeline.budget import (
    UNLIMITED,
    BudgetExceeded,
    BudgetLedger,
    authorize_spend,
    budget_cap_prompt_value,
    cap_for,
    record_spend,
)


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


class TestBudgetCapPromptValue:
    def test_formats_a_configured_cap(self) -> None:
        assert budget_cap_prompt_value({"budget_cap_usd": 100.0}) == "$100.00"

    def test_unconfigured_cap_reads_unlimited(self) -> None:
        assert budget_cap_prompt_value(None) == "unlimited"
        assert budget_cap_prompt_value({}) == "unlimited"


class TestAuthorizeSpend:
    def test_permits_spend_within_the_cap(self) -> None:
        authorize_spend("p1", 10.0, cap_usd=100.0, spent_usd=0.0)

    def test_permits_spend_exactly_up_to_the_cap(self) -> None:
        """The boundary is inclusive: spending the cap exactly is allowed."""
        authorize_spend("p1", 100.0, cap_usd=100.0, spent_usd=0.0)

    def test_refuses_spend_past_the_cap(self) -> None:
        with pytest.raises(BudgetExceeded):
            authorize_spend("p1", 100.01, cap_usd=100.0, spent_usd=0.0)

    def test_accounts_for_spend_already_recorded(self) -> None:
        with pytest.raises(BudgetExceeded):
            authorize_spend("p1", 60.0, cap_usd=100.0, spent_usd=50.0)

    def test_unlimited_cap_never_refuses(self) -> None:
        authorize_spend("p1", 1e9, cap_usd=UNLIMITED)

    def test_zero_cap_refuses_any_spend(self) -> None:
        with pytest.raises(BudgetExceeded):
            authorize_spend("p1", 0.01, cap_usd=0.0)

    def test_refusal_carries_the_numbers_that_produced_it(self) -> None:
        with pytest.raises(BudgetExceeded) as excinfo:
            authorize_spend("p1", 70.0, cap_usd=100.0, spent_usd=50.0)
        error = excinfo.value
        assert error.project_id == "p1"
        assert error.requested_usd == 70.0
        assert error.cap_usd == 100.0
        assert error.spent_usd == 50.0
        assert error.remaining_usd == 50.0
        assert "$50.00" in str(error)


class TestBudgetLedger:
    def test_spend_is_derived_from_records(self) -> None:
        ledger = BudgetLedger(project_id="p1", cap_usd=100.0)
        ledger.record("generation", 10.0, "batch-1")
        ledger.record("generation", 15.0, "batch-2")
        assert ledger.spent_usd == 25.0
        assert ledger.remaining_usd == 75.0

    def test_records_are_attributable(self) -> None:
        ledger = BudgetLedger(project_id="p1", cap_usd=100.0)
        entry = ledger.record("generation", 10.0, "batch-1")
        assert entry.project_id == "p1"
        assert entry.generation_id == "batch-1"
        assert entry.amount_usd == 10.0

    def test_record_ids_are_unique(self) -> None:
        ledger = BudgetLedger(project_id="p1", cap_usd=100.0)
        ids = {ledger.record("generation", 1.0, f"b{i}").spend_id for i in range(3)}
        assert len(ids) == 3

    def test_negative_spend_is_rejected(self) -> None:
        ledger = BudgetLedger(project_id="p1", cap_usd=100.0)
        with pytest.raises(ValueError, match="non-negative"):
            ledger.record("generation", -1.0, "batch-1")

    def test_authorize_uses_recorded_spend(self) -> None:
        ledger = BudgetLedger(project_id="p1", cap_usd=100.0)
        ledger.record("generation", 90.0, "batch-1")
        with pytest.raises(BudgetExceeded):
            ledger.authorize(20.0)
        ledger.authorize(10.0)

    def test_remaining_never_goes_negative(self) -> None:
        ledger = BudgetLedger(project_id="p1", cap_usd=10.0)
        ledger.record("generation", 25.0, "batch-1")
        assert ledger.remaining_usd == 0.0

    def test_projects_onto_the_persisted_state_shape(self) -> None:
        ledger = BudgetLedger(project_id="p1", cap_usd=100.0)
        ledger.record("generation", 30.0, "batch-1")
        state = ledger.to_state()
        assert state.project_id == "p1"
        assert state.cap_usd == 100.0
        assert state.spent_usd == 30.0
        assert state.remaining_usd == 70.0

    def test_record_spend_helper_delegates_to_the_ledger(self) -> None:
        ledger = BudgetLedger(project_id="p1", cap_usd=100.0)
        entry = record_spend(ledger, "generation", 5.0, "batch-1")
        assert entry.amount_usd == 5.0
        assert ledger.spent_usd == 5.0


def test_budget_module_does_not_import_config_or_generation() -> None:
    """The spec forbids `budget -> config`; the cap is read, not re-derived."""
    import ast
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3] / "src" / "film_pipeline" / "budget" / "__init__.py"
    )
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    forbidden = {
        m for m in imported if m.startswith(("film_pipeline.config", "film_pipeline.generation"))
    }
    assert forbidden == set(), f"budget imports a forbidden module: {sorted(forbidden)}"
