"""Budget cap policy: resolve the project cap, authorize spend, record spend.

This module owns the *policy* around spend — what the cap gates, what refusal
means, and the durable record of what was spent. It deliberately does not
estimate provider costs (`providers.pricing` owns the number), own generation
ledger rows (`generation`), route the graph (it returns a verdict and the
caller reacts), or hold the phase decision (`governance`).

The cap's *value* has exactly one declared owner: the `budget_cap_usd` field on
the project profile (`schemas/project.py`), produced once at project creation
from the resolved profile. This module reads it and caches nothing.

Measured correction to `03` §3.11: that section places the field on
`ProjectRecord`. At this revision `ProjectRecord` declares no such field — it
sets `extra="allow"`, so a cap can survive round-tripping without being part of
its typed contract — while `ProjectProfile.budget_cap_usd` is the real declared
owner. :func:`cap_for` therefore accepts either shape, reading the declared
field first and falling back to the extra key, so both the typed profile and a
persisted record resolve to the same value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from film_pipeline.schemas.budget import BudgetState, SpendRecord

#: Sentinel meaning "no cap configured", so callers compare against a number
#: rather than branching on ``None`` at every gate.
__all__ = [
    "UNLIMITED",
    "BudgetExceeded",
    "BudgetLedger",
    "authorize_spend",
    "budget_cap_prompt_value",
    "cap_for",
    "record_spend",
]

UNLIMITED: float = float("inf")


class BudgetExceeded(Exception):
    """Raised when a spend request would exceed the project's cap.

    Carries the numbers that produced the refusal so a caller can build an
    actionable operator message without re-deriving them.
    """

    def __init__(
        self, project_id: str, requested_usd: float, cap_usd: float, spent_usd: float
    ) -> None:
        self.project_id = project_id
        self.requested_usd = requested_usd
        self.cap_usd = cap_usd
        self.spent_usd = spent_usd
        self.remaining_usd = max(0.0, cap_usd - spent_usd)
        super().__init__(
            f"Spend of ${requested_usd:.2f} for project '{project_id}' exceeds the "
            f"remaining budget of ${self.remaining_usd:.2f} "
            f"(cap ${cap_usd:.2f}, already spent ${spent_usd:.2f})."
        )


@dataclass
class BudgetLedger:
    """In-memory spend ledger for one project.

    Holds the durable budget document's contents. Persistence goes through
    `storage`; this type only enforces the invariant that spend never decreases
    and that every recorded line has a source.
    """

    project_id: str
    cap_usd: float = 0.0
    records: list[SpendRecord] = field(default_factory=list)

    @property
    def spent_usd(self) -> float:
        """Total recorded spend, derived from the records rather than stored."""
        return sum(record.amount_usd for record in self.records)

    @property
    def remaining_usd(self) -> float:
        """Remaining allowance, floored at zero."""
        return max(0.0, self.cap_usd - self.spent_usd)

    def record(self, phase: str, amount_usd: float, source: str) -> SpendRecord:
        """Append one spend line and return it.

        ``source`` names what produced the charge (a batch id, a provider job)
        so a ledger line is always attributable.
        """
        if amount_usd < 0:
            raise ValueError(f"amount_usd must be non-negative, got {amount_usd!r}.")
        entry = SpendRecord(
            spend_id=f"spend:{self.project_id}:{len(self.records) + 1}",
            project_id=self.project_id,
            generation_id=source,
            provider=phase,
            amount_usd=amount_usd,
            mode="recorded",
            created_at=datetime.now(UTC),
        )
        self.records.append(entry)
        return entry

    def authorize(self, requested_usd: float) -> None:
        """Raise :class:`BudgetExceeded` unless the request fits the cap."""
        if self.cap_usd >= UNLIMITED:
            return
        if self.spent_usd + requested_usd > self.cap_usd:
            raise BudgetExceeded(self.project_id, requested_usd, self.cap_usd, self.spent_usd)

    def to_state(self) -> BudgetState:
        """Project this ledger onto the persisted :class:`BudgetState` shape."""
        return BudgetState(
            project_id=self.project_id,
            cap_usd=self.cap_usd,
            spent_usd=self.spent_usd,
        )


def cap_for(source: object | None) -> float:
    """Return the cap declared by ``source``, or :data:`UNLIMITED` if none is.

    This is the single reader of the cap value. ``source`` is a project profile,
    a persisted project record, or any mapping carrying the field — the declared
    `budget_cap_usd` attribute and the ``extra="allow"`` key both resolve to the
    same number.

    A source without a cap, or no source at all, is unlimited rather than zero,
    so an unconfigured project is never silently blocked. A non-numeric or
    negative value is treated as unconfigured rather than crashing a gate.
    """
    if source is None:
        return UNLIMITED
    raw: Any
    if isinstance(source, dict):
        raw = source.get("budget_cap_usd")
    else:
        raw = getattr(source, "budget_cap_usd", None)
    if raw is None:
        return UNLIMITED
    try:
        cap = float(raw)
    except (TypeError, ValueError):
        return UNLIMITED
    if cap < 0:
        return UNLIMITED
    return cap


def authorize_spend(
    project_id: str,
    requested_usd: float,
    cap_usd: float,
    spent_usd: float = 0.0,
) -> None:
    """Refuse a spend request that would exceed ``cap_usd``.

    The one refusal path: every gate that declines generation for cost reasons
    routes through here, so they cannot diverge.
    """
    if cap_usd >= UNLIMITED:
        return
    if spent_usd + requested_usd > cap_usd:
        raise BudgetExceeded(project_id, requested_usd, cap_usd, spent_usd)


def record_spend(
    ledger: BudgetLedger,
    phase: str,
    usd: float,
    source: str,
) -> SpendRecord:
    """Record actual spend against a project's ledger."""
    return ledger.record(phase, usd, source)


def budget_cap_prompt_value(source: object | None) -> str:
    """The ``budget_cap`` prompt variable, derived once from the cap.

    F-BUD-04 recorded this value being derived in two places while the prompt
    read a key nobody wrote. The formatting lives here so producers and the
    prompt template cannot disagree.
    """
    cap = cap_for(source)
    if cap >= UNLIMITED:
        return "unlimited"
    return f"${cap:.2f}"
