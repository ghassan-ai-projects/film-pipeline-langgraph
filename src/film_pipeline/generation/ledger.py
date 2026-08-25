"""Generation ledger — CRUD and lifecycle state transitions.

Owns the `GenerationLedger` artifact: creates, reads, and mutates rows.
The ledger is persisted via `ArtifactStore` as a standard artifact of the
generation phase. No provider calls happen here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.schemas._base import (
    ArtifactStatus,
    ArtifactType,
    FilmPhase,
    GenerationMode,
    GenerationStatus,
)
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.schemas.generation import (
    GenerationLedger,
    GenerationLedgerRow,
)

LEDGER_ARTIFACT_ID = "generation_ledger"


class GenerationLedgerManager:
    """Create and mutate the generation ledger for a project.

    The ledger is a persisted `GenerationLedger` artifact. Every row
    represents one generation request with full lifecycle state.
    """

    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    # ── create / load ────────────────────────────────────────────────────

    def create(self, project_id: str) -> GenerationLedger:
        """Create a new empty ledger for *project_id*."""
        ledger = GenerationLedger(project_id=project_id, rows=[])
        self._persist(ledger)
        return ledger

    def load(self, project_id: str) -> GenerationLedger:
        """Load the ledger for *project_id*, or create if missing."""
        try:
            data = self._store.load(project_id, FilmPhase.GENERATION, LEDGER_ARTIFACT_ID, 1)
            return GenerationLedger.model_validate(data)
        except FileNotFoundError:
            return self.create(project_id)

    # ── plan ─────────────────────────────────────────────────────────────

    def plan_batch(
        self,
        project_id: str,
        shot_ids: list[str],
        provider: str,
        model: str,
        prompt_ref: str = "",
        reference_refs: list[str] | None = None,
        mode: GenerationMode = GenerationMode.TEST,
    ) -> GenerationLedger:
        """Add a row per shot to the ledger with status PREPARED.

        Idempotent: skips any shot that already has a row.
        """
        ledger = self.load(project_id)
        existing = {r.shot_id for r in ledger.rows}

        for sid in shot_ids:
            if sid in existing:
                continue
            req_id = f"gen-req:{project_id}:{sid}:{uuid4().hex[:8]}"
            gen_id = f"gen:{project_id}:{sid}:{uuid4().hex[:8]}"
            row = GenerationLedgerRow(
                generation_request_id=req_id,
                generation_id=gen_id,
                project_id=project_id,
                shot_id=sid,
                mode=mode,
                provider=provider,
                model=model,
                prompt_ref=prompt_ref,
                reference_refs=reference_refs or [],
                status=GenerationStatus.PREPARED,
                next_action="submit",
            )
            ledger.rows.append(row)

        self._persist(ledger)
        return ledger

    # ── approve spend ────────────────────────────────────────────────────

    def approve_spend(self, project_id: str, max_cost_usd: float = -1.0) -> GenerationLedger:
        """Mark PREPARED rows as SUBMITTED and record submit time.

        This is a local state transition only. It does not call any provider.

        Skips rows already SUBMITTED (duplicate-submit prevention).
        If *max_cost_usd* is set (>= 0), rejects if estimated cost exceeds budget.
        """
        ledger = self.load(project_id)
        new_rows, submitted_count = _submit_prepared_rows(ledger.rows)
        _raise_if_over_budget(new_rows, max_cost_usd, submitted_count)
        ledger = ledger.model_copy(update={"rows": new_rows})
        self._persist(ledger)
        return ledger

    def estimate_total_cost(self, project_id: str) -> float:
        """Sum estimated_cost_usd for all non-terminal rows."""
        ledger = self.load(project_id)
        terminal = {
            GenerationStatus.COMPLETED,
            GenerationStatus.FAILED,
            GenerationStatus.CANCELLED,
            GenerationStatus.TIMED_OUT,
        }
        return sum(r.estimated_cost_usd for r in ledger.rows if r.status not in terminal)

    # ── promote ──────────────────────────────────────────────────────────

    def promote_to_production(
        self,
        project_id: str,
        *,
        shot_ids: list[str] | None = None,
    ) -> tuple[int, list[str]]:
        """Transition COMPLETED TEST rows to PRODUCTION mode.

        Only rows with mode=TEST and status=COMPLETED are eligible.
        Returns (promoted_count, promoted_generation_ids).

        If *shot_ids* is provided, only promotes those specific shots.
        """
        ledger = self.load(project_id)
        promoted: list[str] = []
        new_rows: list[GenerationLedgerRow] = []

        for row in ledger.rows:
            eligible = (
                row.mode == GenerationMode.TEST
                and row.status == GenerationStatus.COMPLETED
                and (shot_ids is None or row.shot_id in shot_ids)
            )
            if eligible:
                promoted.append(row.generation_id)
                new_rows.append(
                    row.model_copy(
                        update={
                            "mode": GenerationMode.PRODUCTION,
                            "next_action": "stop",
                        }
                    )
                )
            else:
                new_rows.append(row)

        if promoted:
            ledger = ledger.model_copy(update={"rows": new_rows})
            self._persist(ledger)

        return len(promoted), promoted

    # ── query ────────────────────────────────────────────────────────────

    def list_rows(
        self,
        project_id: str,
        status: GenerationStatus | None = None,
    ) -> list[GenerationLedgerRow]:
        """List ledger rows, optionally filtered by status."""
        ledger = self.load(project_id)
        if status is None:
            return list(ledger.rows)
        return [r for r in ledger.rows if r.status == status]

    def get_row(self, project_id: str, generation_id: str) -> GenerationLedgerRow | None:
        """Look up a single row by generation_id."""
        ledger = self.load(project_id)
        for row in ledger.rows:
            if row.generation_id == generation_id:
                return row
        return None

    def update_row(
        self,
        project_id: str,
        generation_id: str,
        **updates: object,
    ) -> GenerationLedgerRow | None:
        """Update a single row's fields and persist. Returns the updated row."""
        ledger = self.load(project_id)
        new_rows: list[GenerationLedgerRow] = []
        found: GenerationLedgerRow | None = None
        for row in ledger.rows:
            if row.generation_id == generation_id:
                row = row.model_copy(update=updates)
                found = row
            new_rows.append(row)
        if found is not None:
            ledger = ledger.model_copy(update={"rows": new_rows})
            self._persist(ledger)
        return found

    # ── helpers ──────────────────────────────────────────────────────────

    def _persist(self, ledger: GenerationLedger) -> None:
        meta = ArtifactMetadata(
            artifact_id=LEDGER_ARTIFACT_ID,
            artifact_type=ArtifactType.GENERATION_LEDGER,
            project_id=ledger.project_id,
            phase=FilmPhase.GENERATION,
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="generation-ledger-manager",
            created_at=datetime.now(UTC),
        )
        self._store.save(ledger, meta)


def _submit_prepared_rows(
    rows: list[GenerationLedgerRow],
) -> tuple[list[GenerationLedgerRow], int]:
    """Return copies of *rows* with PREPARED ones moved to SUBMITTED, and how many moved.

    Rows in any other status (including already-SUBMITTED ones) pass through unchanged,
    which is what makes duplicate submission impossible.
    """
    now = datetime.now(UTC)
    new_rows: list[GenerationLedgerRow] = []
    submitted_count = 0

    for row in rows:
        if row.status == GenerationStatus.PREPARED:
            submitted_count += 1
            row = row.model_copy(
                update={
                    "status": GenerationStatus.SUBMITTED,
                    "submitted_at": now,
                    "next_action": "poll",
                }
            )
        new_rows.append(row)

    return new_rows, submitted_count


def _raise_if_over_budget(
    rows: list[GenerationLedgerRow],
    max_cost_usd: float,
    submitted_count: int,
) -> None:
    """Reject the batch when estimated cost of SUBMITTED rows exceeds *max_cost_usd*.

    A negative *max_cost_usd* means "no limit". Raises instead of persisting, so a
    rejection leaves the stored ledger untouched.
    """
    if max_cost_usd < 0:
        return
    total_cost = sum(r.estimated_cost_usd for r in rows if r.status == GenerationStatus.SUBMITTED)
    if total_cost > max_cost_usd:
        raise ValueError(
            f"Total estimated cost ${total_cost:.2f} exceeds budget ${max_cost_usd:.2f}. "
            f"({submitted_count} new request(s) would be submitted). "
            "Reduce batch or increase max_cost_usd."
        )
