"""Budget cap policy — the single reader of a project's spend cap.

This module owns the *policy* around the cap: what value a project's cap
resolves to, and the rule that an unconfigured project is never silently
blocked. It deliberately does not estimate provider costs (`providers.pricing`
owns the number), own generation ledger rows (`generation`), route the graph (it
returns a value and the caller decides), or hold the phase decision
(`governance`).

## What this module no longer owns, and why

It previously declared an enforcement surface — ``authorize_spend``,
``record_spend``, ``BudgetLedger``, ``BudgetExceeded``, ``budget_cap_prompt_value``
— and every one of those had **zero production callers**. Measured before
deletion: the only symbol in the module reached from ``src/`` was :func:`cap_for`
(one caller, the generation planner). ``authorize_spend``'s own docstring claimed
"every gate that declines generation for cost reasons routes through here"; the
grep said otherwise.

The spend refusals that *do* work live where the spend happens and are untouched:
``generation.ledger.approve_spend`` raises before persisting when a batch exceeds
its ceiling, and ``orchestration.nodes._generation_batch_planning`` turns that
refusal into a blocking issue. This module was a second, unused copy of that
policy.

## The cap's value

The declared owner is the ``budget_cap_usd`` field on the project profile
(``schemas/project.py``), produced once at project creation from the resolved
profile. :func:`cap_for` reads it and caches nothing.

The previous docstring also claimed `ProjectRecord` sets ``extra="allow"`` so a
cap could survive round-tripping. That is **false at this revision**: the record
is ``ConfigDict(extra="forbid", frozen=True)`` and declares no cost field, so an
extra key is rejected rather than preserved. The stale claim is recorded here
because `03` §3.11 repeats it.
"""

from __future__ import annotations

from typing import Any

#: Sentinel meaning "no cap configured", so callers compare against a number
#: rather than branching on ``None`` at every gate.
__all__ = ["UNLIMITED", "cap_for"]

UNLIMITED: float = float("inf")


def cap_for(source: object | None) -> float:
    """Return the cap declared by ``source``, or :data:`UNLIMITED` if none is.

    This is the single reader of the cap value. ``source`` is a project profile,
    a persisted project record, or any mapping carrying the field.

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
