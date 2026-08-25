"""Generation batch executor — plan, spend approval, dispatch, and delivery.

Owns the operational half of the generation phase: turning the approved
shot matrix into ledger rows, submitting them to provider adapters, polling
jobs to completion, downloading outputs into the project's asset tree, and
recording every delivered file in the project asset manifest.

Both the operator service (TUI) and MCP tools drive generation through this
executor so the two surfaces stay behaviorally identical.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from film_pipeline.artifacts.manifest import (
    AssetEntry,
    AssetManifest,
    read_manifest,
    write_manifest,
)
from film_pipeline.artifacts.paths import generated_asset_dir
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.generation.ledger import GenerationLedgerManager
from film_pipeline.schemas._base import FilmPhase, GenerationMode, GenerationStatus

_TERMINAL_STATUSES = {
    GenerationStatus.COMPLETED,
    GenerationStatus.FAILED,
    GenerationStatus.CANCELLED,
    GenerationStatus.TIMED_OUT,
}


@dataclass
class GenerationStepResult:
    """Outcome of one executor step across a batch of ledger rows."""

    processed: int = 0
    completed: int = 0
    failed: int = 0
    running: int = 0
    details: list[dict[str, str]] = field(default_factory=list)

    @property
    def done(self) -> bool:
        """True when no rows remain in a non-terminal, in-flight status."""
        return self.running == 0


class GenerationExecutor:
    """Drive generation ledger rows from planning through delivered assets."""

    def __init__(self, store: ArtifactStore, providers: Mapping[str, Any]) -> None:
        self._store = store
        self._providers = providers
        self._ledger = GenerationLedgerManager(store)

    # ── shot matrix access ────────────────────────────────────────────────

    def load_shot_rows(self, project_id: str) -> list[dict[str, Any]]:
        """Return shot rows from the latest shot matrix artifact.

        Supports both the current ``shot_matrix`` artifact (``rows`` key) and
        the legacy ``shot_bible`` artifact (``shots``/``scenes`` keys).
        """
        for artifact_id, keys in (
            ("shot_matrix", ("rows",)),
            ("shot_bible", ("shots", "scenes")),
        ):
            data = self._load_latest(project_id, FilmPhase.SHOT_BIBLE, artifact_id)
            if not isinstance(data, dict):
                continue
            for key in keys:
                rows = data.get(key)
                if isinstance(rows, list) and rows:
                    return [row for row in rows if isinstance(row, dict)]
        return []

    def shot_ids(self, project_id: str) -> list[str]:
        """Return shot ids from the latest shot matrix, in matrix order."""
        ids: list[str] = []
        for row in self.load_shot_rows(project_id):
            shot_id = str(row.get("shot_id", "") or row.get("scene_id", "")).strip()
            if shot_id:
                ids.append(shot_id)
        return ids

    # ── batch lifecycle ───────────────────────────────────────────────────

    def plan(
        self,
        project_id: str,
        *,
        provider: str,
        model: str,
        mode: GenerationMode = GenerationMode.TEST,
        shot_ids: list[str] | None = None,
        prompt_ref: str = "",
    ) -> GenerationStepResult:
        """Add PREPARED ledger rows for the requested (or all matrix) shots."""
        targets = [sid for sid in (shot_ids or self.shot_ids(project_id)) if sid]
        if not targets:
            raise ValueError(
                "No shots to plan. The shot matrix has no rows — approve shot_bible first."
            )
        ledger = self._ledger.plan_batch(
            project_id=project_id,
            shot_ids=targets,
            provider=provider,
            model=model,
            prompt_ref=prompt_ref,
            mode=mode,
        )
        planned = [row for row in ledger.rows if row.shot_id in set(targets)]
        result = GenerationStepResult(processed=len(planned))
        result.details = [
            {"shot_id": row.shot_id, "generation_id": row.generation_id, "status": row.status.value}
            for row in planned
        ]
        return result

    def approve_spend(self, project_id: str, max_cost_usd: float = -1.0) -> GenerationStepResult:
        """Approve spend for PREPARED rows (PREPARED -> SUBMITTED)."""
        ledger = self._ledger.approve_spend(project_id, max_cost_usd=max_cost_usd)
        submitted = [row for row in ledger.rows if row.status == GenerationStatus.SUBMITTED]
        return GenerationStepResult(processed=len(submitted), running=len(submitted))

    def start(self, project_id: str) -> GenerationStepResult:
        """Submit SUBMITTED rows to their provider adapters (-> RUNNING)."""
        rows = self._ledger.list_rows(project_id, status=GenerationStatus.SUBMITTED)
        result = GenerationStepResult()
        shot_rows = self._shot_rows_by_id(project_id)
        for row in rows:
            result.processed += 1
            if row.provider_job_id:
                result.running += 1
                continue
            self._dispatch_row(project_id, row, shot_rows.get(row.shot_id, {}), result)
        return result

    def _dispatch_row(
        self,
        project_id: str,
        row: Any,
        shot_row: dict[str, Any],
        result: GenerationStepResult,
    ) -> None:
        """Submit one SUBMITTED row to its provider adapter (-> RUNNING or FAILED)."""
        adapter = self._providers.get(row.provider)
        if adapter is None:
            self._fail_row(
                project_id,
                row.generation_id,
                code="unknown_provider",
                reason=f"Provider '{row.provider}' is not registered.",
            )
            result.failed += 1
            result.details.append(
                {"shot_id": row.shot_id, "error": f"provider '{row.provider}' not registered"}
            )
            return
        prompt = self.resolve_prompt(project_id, row.shot_id, shot_row, row.prompt_ref)
        duration = float(shot_row.get("duration_seconds", 5) or 5)
        try:
            payload = adapter.build_payload(
                prompt=prompt,
                references=row.reference_refs or None,
                duration=duration,
            )
            job = adapter.submit(payload, row.shot_id)
        except Exception as exc:
            self._fail_row(
                project_id,
                row.generation_id,
                code="submit_failed",
                reason=str(exc)[:200],
            )
            result.failed += 1
            result.details.append({"shot_id": row.shot_id, "error": str(exc)[:200]})
            return
        self._ledger.update_row(
            project_id,
            row.generation_id,
            provider_job_id=job.job_id,
            status=GenerationStatus.RUNNING,
            submitted_at=datetime.now(UTC),
            next_action="poll",
        )
        result.running += 1
        result.details.append({"shot_id": row.shot_id, "provider_job_id": job.job_id})

    def poll_once(self, project_id: str) -> GenerationStepResult:
        """Poll RUNNING rows once; download and record completed outputs."""
        rows = self._ledger.list_rows(project_id, status=GenerationStatus.RUNNING)
        result = GenerationStepResult()
        for row in rows:
            result.processed += 1
            self._poll_row(project_id, row, result)
        return result

    def _poll_row(self, project_id: str, row: Any, result: GenerationStepResult) -> None:
        """Poll one RUNNING row and route by the provider job outcome."""
        from film_pipeline.providers.base import ProviderJob

        adapter = self._providers.get(row.provider)
        if adapter is None or not row.provider_job_id:
            self._fail_row(
                project_id,
                row.generation_id,
                code="unknown_provider",
                reason=f"Provider '{row.provider}' is not registered.",
            )
            result.failed += 1
            return
        job = ProviderJob(
            job_id=row.provider_job_id,
            shot_id=row.shot_id,
            provider_id=row.provider,
            model=row.model,
            status="submitted",
            polls=row.poll_count,
        )
        try:
            job = adapter.poll(job)
        except Exception as exc:
            self._fail_row(project_id, row.generation_id, code="poll_failed", reason=str(exc)[:200])
            result.failed += 1
            result.details.append({"shot_id": row.shot_id, "error": str(exc)[:200]})
            return
        if job.status == "completed":
            self._complete_row(project_id, row, adapter, job, result)
        elif job.status == "failed":
            self._fail_row(
                project_id,
                row.generation_id,
                code=str(job.metadata.get("error", "generation_failed")),
                reason="Provider reported the job as failed.",
            )
            result.failed += 1
        else:
            self._ledger.update_row(
                project_id,
                row.generation_id,
                poll_count=row.poll_count + 1,
                last_polled_at=datetime.now(UTC),
            )
            result.running += 1

    def _complete_row(
        self,
        project_id: str,
        row: Any,
        adapter: Any,
        job: Any,
        result: GenerationStepResult,
    ) -> None:
        """Deliver a completed job's outputs and mark its ledger row COMPLETED."""
        try:
            output_paths = self._deliver(project_id, row, adapter, job)
        except Exception as exc:
            self._fail_row(
                project_id,
                row.generation_id,
                code="download_failed",
                reason=str(exc)[:200],
            )
            result.failed += 1
            result.details.append({"shot_id": row.shot_id, "error": str(exc)[:200]})
            return
        self._ledger.update_row(
            project_id,
            row.generation_id,
            status=GenerationStatus.COMPLETED,
            poll_count=row.poll_count + 1,
            last_polled_at=datetime.now(UTC),
            output_refs=output_paths,
            next_action="validate",
        )
        result.completed += 1
        result.details.append(
            {"shot_id": row.shot_id, "output": output_paths[0] if output_paths else ""}
        )

    def has_ledger(self, project_id: str) -> bool:
        """True when a generation ledger artifact exists for the project.

        Read paths must check this first: the ledger manager's ``load``
        persists a new empty ledger artifact when none exists, which would
        turn every status refresh into an artifact write.
        """
        return (
            self._store.next_version(project_id, FilmPhase.GENERATION.value, "generation_ledger")
            > 1
        )

    def status_rows(self, project_id: str) -> list[dict[str, Any]]:
        """Summarize all ledger rows for operator display."""
        if not self.has_ledger(project_id):
            return []
        return [
            {
                "shot_id": row.shot_id,
                "generation_id": row.generation_id,
                "provider": row.provider,
                "model": row.model,
                "mode": row.mode.value,
                "status": row.status.value,
                "polls": row.poll_count,
                "cost_usd": row.estimated_cost_usd,
                "output": row.output_refs[0] if row.output_refs else "",
                "error": row.blocking_reason or "",
            }
            for row in self._ledger.list_rows(project_id)
        ]

    def estimated_cost(self, project_id: str) -> float:
        """Total estimated cost across the ledger."""
        if not self.has_ledger(project_id):
            return 0.0
        return self._ledger.estimate_total_cost(project_id)

    def dispatchable_requests(self, project_id: str) -> list[dict[str, Any]]:
        """Build graph-state generation requests from current ledger rows.

        The generation phase gate requires ``generation_requests`` in project
        state; this mirrors the ledger so approvals can pass the gate.
        """
        if not self.has_ledger(project_id):
            return []
        requests: list[dict[str, Any]] = []
        for row in self._ledger.list_rows(project_id):
            if row.status in {GenerationStatus.CANCELLED}:
                continue
            requests.append(
                {
                    "generation_request_id": row.generation_request_id,
                    "generation_id": row.generation_id,
                    "project_id": row.project_id,
                    "shot_id": row.shot_id,
                    "mode": row.mode.value,
                    "provider": row.provider,
                    "model": row.model,
                    "prompt_ref": row.prompt_ref,
                    "prompt_payload": {"prompt_ref": row.prompt_ref, "shot_id": row.shot_id},
                    "reference_refs": list(row.reference_refs),
                    "status": row.status.value,
                }
            )
        return requests

    # ── prompt resolution ─────────────────────────────────────────────────

    def resolve_prompt(
        self,
        project_id: str,
        shot_id: str,
        shot_row: dict[str, Any],
        prompt_ref: str = "",
    ) -> str:
        """Resolve the best prompt text for a shot.

        Prefers a rendered prompt from the gen_planning prompt artifact when
        ``prompt_ref`` names one, then a structured prompt from the shot
        matrix row, then a plain fallback so submission never blocks.
        """
        rendered = self._rendered_prompt(project_id, shot_id, prompt_ref)
        if rendered:
            return rendered
        if shot_row:
            structured = self._structured_prompt(project_id, shot_row)
            if structured:
                return structured
        return f"Cinematic shot {shot_id} for project {project_id}."

    def _rendered_prompt(self, project_id: str, shot_id: str, prompt_ref: str) -> str:
        if not prompt_ref:
            return ""
        artifact_id = prompt_ref.split(":")[1] if ":" in prompt_ref else prompt_ref
        for phase in (FilmPhase.GEN_PLANNING, FilmPhase.SHOT_BIBLE):
            data = self._load_latest(project_id, phase, artifact_id)
            if not isinstance(data, dict):
                continue
            for entry in data.get("entries", []) or []:
                if isinstance(entry, dict) and str(entry.get("shot_id", "")) == shot_id:
                    return str(entry.get("rendered_prompt", "") or "")
        return ""

    def _structured_prompt(self, project_id: str, shot_row: dict[str, Any]) -> str:
        from film_pipeline.generation.prompt_builder import build_structured_prompt

        characters = shot_row.get("characters") or []
        environment = str(shot_row.get("environment", "") or "")
        subject_type = "environment" if not characters else "character"
        entry: dict[str, Any] = {
            "subject_type": subject_type,
            "subject_id": environment if not characters else str(characters[0]),
            "frame_role": str(shot_row.get("camera_profile", "") or ""),
            "prompt_text": str(shot_row.get("story_function", "") or ""),
            "lighting": str(shot_row.get("lighting_state", "") or ""),
            "notes": str(shot_row.get("environment_state", "") or ""),
        }
        character_bible = (
            self._load_latest(project_id, FilmPhase.VISUAL_DEV, "character_bible")
            if characters
            else None
        )
        constitution = self._load_latest(project_id, FilmPhase.CONSTITUTION, "film_constitution")
        return build_structured_prompt(
            entry,
            character_bible=character_bible if isinstance(character_bible, dict) else None,
            constitution=constitution if isinstance(constitution, dict) else None,
        )

    # ── internals ─────────────────────────────────────────────────────────

    def _shot_rows_by_id(self, project_id: str) -> dict[str, dict[str, Any]]:
        """Index current shot-matrix rows by shot id for O(1) lookup."""
        return {str(row.get("shot_id", "")): row for row in self.load_shot_rows(project_id)}

    def _deliver(
        self,
        project_id: str,
        row: Any,
        adapter: Any,
        job: Any,
    ) -> list[str]:
        """Download a completed job into the project asset tree + manifest."""
        output_dir = self._output_dir(project_id, row)
        output_dir.mkdir(parents=True, exist_ok=True)
        primary = adapter.download(job, str(output_dir))
        produced = sorted(
            path
            for path in output_dir.iterdir()
            if path.is_file() and not path.name.endswith("_metadata.json")
        )
        self._record_assets(project_id, row, produced)
        return [primary, *[str(path) for path in produced if str(path) != primary]]

    def _output_dir(self, project_id: str, row: Any) -> Path:
        """Target directory for a row's generated assets, keyed by scene id."""
        shot_row = self._shot_rows_by_id(project_id).get(row.shot_id, {})
        scene_id = str(shot_row.get("scene_id", "") or "unassigned")
        return generated_asset_dir(project_id, scene_id, row.shot_id, root=self._root())

    def _record_assets(self, project_id: str, row: Any, produced: list[Path]) -> None:
        """Record every produced file in the asset manifest under the next take."""
        shot_row = self._shot_rows_by_id(project_id).get(row.shot_id, {})
        scene_id = str(shot_row.get("scene_id", "") or "unassigned")
        take = self._next_take(project_id, row.shot_id)
        manifest = read_manifest(project_id, root=self._root()) or AssetManifest(
            project_id=project_id
        )
        for path in produced:
            kind = _asset_kind(path)
            manifest.add(
                AssetEntry(
                    asset_id=f"{row.shot_id}:{kind}:take{take}",
                    path=str(path),
                    kind=kind,
                    scene_id="" if scene_id == "unassigned" else scene_id,
                    shot_id=row.shot_id,
                    take=take,
                    active=True,
                )
            )
        write_manifest(manifest, root=self._root())

    def _next_take(self, project_id: str, shot_id: str) -> int:
        manifest = read_manifest(project_id, root=self._root())
        if manifest is None:
            return 1
        takes = [entry.take for entry in manifest.entries if entry.shot_id == shot_id]
        return max(takes, default=0) + 1

    def _fail_row(self, project_id: str, generation_id: str, *, code: str, reason: str) -> None:
        self._ledger.update_row(
            project_id,
            generation_id,
            status=GenerationStatus.FAILED,
            error_code=code,
            blocking_reason=reason,
            next_action="wait_human",
        )

    def _load_latest(
        self, project_id: str, phase: FilmPhase, artifact_id: str
    ) -> dict[str, Any] | None:
        latest = self._store.next_version(project_id, phase.value, artifact_id) - 1
        if latest < 1:
            return None
        try:
            return self._store.load(project_id, phase, artifact_id, latest)
        except (FileNotFoundError, ValueError):
            return None

    def _root(self) -> Path:
        root = getattr(self._store, "_root", None)
        return root if isinstance(root, Path) else Path("projects")


def _asset_kind(path: Path) -> str:
    name = path.name.lower()
    if name.endswith("_last.png"):
        return "last_frame"
    if name.endswith("_mid.png"):
        return "mid_frame"
    if path.suffix.lower() in {".mp4", ".mov", ".webm"}:
        return "generated_clip"
    if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        return "reference_sheet"
    if path.suffix.lower() in {".wav", ".mp3"}:
        return "audio_stem"
    return "generated_clip"
