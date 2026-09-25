"""Artifact store — the canonical registry for all typed artifacts (layout v2).

On-disk layout per artifact (``<root>/<project>/artifacts/<NN-phase>/<id>/``):

- ``meta.json``     — artifact-level current pointer + status (the only mutable file)
- ``current.md``    — generated human-readable view of the current version
- ``versions/vNNN.json`` — immutable envelopes: provenance + payload + checksum

A derived ``<root>/<project>/index/artifacts.json`` is regenerated on every
write. See ``documentation/storage-upgrade-plan.md``.

Mutable kinds (generation ledger) are the exception to versioning: they live
as a single revision-counted ``<id>.json`` written through
:meth:`save_mutable`; every immutable kind is append-only under ``versions/``.
"""

from __future__ import annotations

import fcntl
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from film_pipeline.artifacts import paths
from film_pipeline.artifacts.envelope import (
    ArtifactCurrentMeta,
    ArtifactEnvelope,
    ArtifactIndex,
    ArtifactIndexEntry,
    ChecksumMismatchError,
    MutableRevisionMismatchError,
    SchemaTooNewError,
    payload_checksum,
)
from film_pipeline.artifacts.registry import (
    REGISTRY,
    KindNotRegisteredError,
    KindSpec,
    Renderer,
    migrate_payload,
    validate_artifact_id,
)
from film_pipeline.artifacts.serialization import atomic_write_text, dump_json
from film_pipeline.artifacts.storage import ensure_storage_root
from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef

_logger = logging.getLogger(__name__)


class ArtifactStore:
    """Persist and retrieve typed artifacts with metadata and versioning."""

    def __init__(self, root: Path) -> None:
        self._root = ensure_storage_root(root)

    @property
    def root(self) -> Path:
        """The storage root this store reads and writes."""
        return self._root

    # --- Paths -------------------------------------------------------------

    def _project_dir(self, project_id: str) -> Path:
        return self._root / project_id

    def _artifacts_base(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "artifacts"

    def _artifact_dir(self, project_id: str, phase: str, artifact_id: str) -> Path:
        return (
            self._artifacts_base(project_id) / paths.PHASE_DIR_MAP.get(phase, phase) / artifact_id
        )

    def _versions_dir(self, project_id: str, phase: str, artifact_id: str) -> Path:
        return self._artifact_dir(project_id, phase, artifact_id) / "versions"

    def _version_path(self, project_id: str, phase: str, artifact_id: str, version: int) -> Path:
        return self._versions_dir(project_id, phase, artifact_id) / f"v{version:03}.json"

    def _meta_path(self, project_id: str, phase: str, artifact_id: str) -> Path:
        return self._artifact_dir(project_id, phase, artifact_id) / "meta.json"

    def _index_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "index" / "artifacts.json"

    @contextmanager
    def _project_lock(self, project_id: str) -> Iterator[None]:
        """Serialize mutating operations per project (single-writer guard).

        The lock file lives inside the project directory so it travels with
        the data; ``flock`` releases it automatically if a process dies.
        Readers never take the lock.
        """
        lock_path = self._project_dir(project_id) / ".storage.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    # --- Write path ---------------------------------------------------------

    def save(self, artifact: BaseModel, meta: ArtifactMetadata) -> ArtifactRef:
        """Store a new version of an artifact and return its canonical ref.

        The store owns version numbering for immutable kinds (``meta.version``
        is advisory). The registry's ``mutable`` kinds (generation ledger) go
        through :meth:`save_mutable` instead — their single revision-counted
        file is the only copy.
        """
        validate_artifact_id(meta.artifact_id)
        if meta.status is ArtifactStatus.SUPERSEDED:
            raise ValueError(
                f"Cannot save {meta.artifact_id} with status 'superseded': the "
                "version being written becomes the current version, and only "
                "approve()/supersede() move a version out of current. Pass "
                "'candidate' or 'approved'."
            )
        spec = REGISTRY.spec_for(meta.artifact_id)
        if spec.mutable:
            raise ValueError(
                f"{meta.artifact_id} is a mutable kind; persist it with "
                "save_mutable() so its revision-counted file stays the only copy."
            )
        with self._project_lock(meta.project_id):
            return self._save_locked(artifact, meta, spec)

    def _save_locked(
        self, artifact: BaseModel, meta: ArtifactMetadata, spec: KindSpec
    ) -> ArtifactRef:
        phase = meta.phase.value
        version = self.next_version(meta.project_id, phase, meta.artifact_id)
        now = datetime.now(UTC)
        payload = artifact.model_dump(mode="json")
        envelope = ArtifactEnvelope(
            kind=spec.kind,
            schema_version=spec.schema_version,
            artifact_id=meta.artifact_id,
            artifact_type=meta.artifact_type,
            project_id=meta.project_id,
            phase=meta.phase,
            version=version,
            created_at=meta.created_at,
            created_by=meta.created_by,
            reviewed_by=meta.reviewed_by,
            validation_refs=meta.validation_refs,
            approval_ref=meta.approval_ref,
            kb_context_ref=meta.kb_context_ref,
            parents=meta.parents,
            built_from=meta.built_from,
            prompt_template_version=None,
            model_profile=None,
            change_summary=meta.change_summary,
            checksum=payload_checksum(payload),
            payload=payload,
        )
        current_meta = ArtifactCurrentMeta(
            artifact_id=meta.artifact_id,
            artifact_type=meta.artifact_type,
            project_id=meta.project_id,
            phase=meta.phase,
            current_version=version,
            # Callers may pre-approve a written artifact (e.g. profile-change
            # config snapshots); the store never invents a higher status.
            # SUPERSEDED is refused earlier in save(): a version being written
            # as current cannot be superseded by definition, and allowing it
            # would make status unable to distinguish current from historical.
            status=meta.status,
            created_at=meta.created_at,
            updated_at=now,
            created_by=meta.created_by,
            reviewed_by=meta.reviewed_by,
            validation_refs=meta.validation_refs,
            approval_ref=meta.approval_ref,
            kb_context_ref=meta.kb_context_ref,
            checksum=envelope.checksum,
        )

        version_path = self._version_path(meta.project_id, phase, meta.artifact_id, version)
        meta_path = self._meta_path(meta.project_id, phase, meta.artifact_id)
        atomic_write_text(version_path, dump_json(envelope.model_dump(mode="json")))
        atomic_write_text(meta_path, dump_json(current_meta.model_dump(mode="json")))
        atomic_write_text(
            meta_path.parent / "current.md",
            _render_markdown(spec.kind, meta, payload),
        )
        self._write_index(meta.project_id)
        self._safe_write_readme(meta.project_id)
        return ArtifactRef(artifact_id=meta.artifact_id, version=version, phase=meta.phase.value)

    # --- Mutable kinds (single revision-counted file) ------------------------

    def _mutable_path(self, project_id: str, phase: str, artifact_id: str) -> Path:
        return self._artifact_dir(project_id, phase, artifact_id) / f"{artifact_id}.json"

    def save_mutable(
        self,
        artifact: BaseModel,
        meta: ArtifactMetadata,
        *,
        change_summary: str = "",
    ) -> ArtifactRef:
        """Persist a mutable kind as its single revision-counted file.

        Each write bumps the envelope's ``revision``; the file replaces
        atomically. The returned ref's ``version`` is the new revision.
        """
        validate_artifact_id(meta.artifact_id)
        spec = REGISTRY.spec_for(meta.artifact_id)
        if not spec.mutable:
            raise ValueError(f"{meta.artifact_id} is not a mutable kind; use save() to version it.")
        with self._project_lock(meta.project_id):
            return self._save_mutable_locked(artifact, meta, spec, change_summary)

    def _save_mutable_locked(
        self,
        artifact: BaseModel,
        meta: ArtifactMetadata,
        spec: KindSpec,
        change_summary: str,
    ) -> ArtifactRef:
        phase = meta.phase.value
        path = self._mutable_path(meta.project_id, phase, meta.artifact_id)
        revision = 1
        if path.exists():
            # Corrupt previous files must fail loudly: the revision chain is
            # the ledger's audit trail.
            previous = _read_envelope(path)
            revision = (previous.revision or 1) + 1
        now = datetime.now(UTC)
        payload = artifact.model_dump(mode="json")
        envelope = ArtifactEnvelope(
            kind=spec.kind,
            schema_version=spec.schema_version,
            artifact_id=meta.artifact_id,
            artifact_type=meta.artifact_type,
            project_id=meta.project_id,
            phase=meta.phase,
            version=revision,
            created_at=meta.created_at,
            created_by=meta.created_by,
            kb_context_ref=meta.kb_context_ref,
            parents=meta.parents,
            built_from=meta.built_from,
            change_summary=change_summary,
            checksum=payload_checksum(payload),
            payload=payload,
            revision=revision,
        )
        atomic_write_text(path, dump_json(envelope.model_dump(mode="json")))
        self._write_mutable_meta(meta, revision, now, envelope.checksum)
        self._write_index(meta.project_id)
        self._safe_write_readme(meta.project_id)
        return ArtifactRef(artifact_id=meta.artifact_id, version=revision, phase=meta.phase.value)

    def _write_mutable_meta(
        self,
        meta: ArtifactMetadata,
        revision: int,
        now: datetime,
        checksum: str,
    ) -> None:
        meta_path = self._meta_path(meta.project_id, meta.phase.value, meta.artifact_id)
        existing = _read_meta_file(meta_path)
        first_created = (
            datetime.fromisoformat(str(existing["created_at"]))
            if existing and existing.get("created_at")
            else meta.created_at
        )
        current_meta = ArtifactCurrentMeta(
            artifact_id=meta.artifact_id,
            artifact_type=meta.artifact_type,
            project_id=meta.project_id,
            phase=meta.phase,
            current_version=revision,
            status=ArtifactStatus.CANDIDATE,
            created_at=first_created,
            updated_at=now,
            created_by=meta.created_by,
            checksum=checksum,
        )
        atomic_write_text(meta_path, dump_json(current_meta.model_dump(mode="json")))

    def load_mutable(self, project_id: str, phase: FilmPhase, artifact_id: str) -> dict[str, Any]:
        """Load a mutable kind's payload (its single revision-counted file)."""
        path = self._mutable_path(project_id, phase.value, artifact_id)
        if not path.exists():
            raise FileNotFoundError(f"Mutable artifact not found: {path}")
        return _read_envelope(path).payload

    def load_mutable_envelope(
        self, project_id: str, phase: FilmPhase, artifact_id: str
    ) -> ArtifactEnvelope:
        """Load a mutable kind's full envelope (includes its revision)."""
        path = self._mutable_path(project_id, phase.value, artifact_id)
        if not path.exists():
            raise FileNotFoundError(f"Mutable artifact not found: {path}")
        return _read_envelope(path)

    def mutable_exists(self, project_id: str, phase: FilmPhase, artifact_id: str) -> bool:
        """Whether the mutable kind's single file exists."""
        return self._mutable_path(project_id, phase, artifact_id).exists()

    # --- Ref resolution -------------------------------------------------------

    def load_ref(self, project_id: str, ref: str | ArtifactRef) -> dict[str, Any]:
        """Resolve an artifact ref to its payload.

        Phase-bearing refs load directly from their phase. A mutable kind has
        exactly one revision-counted file, so only a ref naming its CURRENT
        revision resolves; a stale ref raises instead of silently returning
        newer content, keeping the ``v<N>`` grammar honest.
        """
        parsed = ref if isinstance(ref, ArtifactRef) else ArtifactRef.from_string(ref)
        try:
            return self.load(
                project_id, FilmPhase(parsed.phase), parsed.artifact_id, parsed.version
            )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Artifact ref '{parsed.to_string()}' not found in project '{project_id}'."
            ) from None

    def _safe_write_readme(self, project_id: str) -> None:
        """Best-effort README regeneration: a corrupt sibling record must
        never fail the artifact write that triggered it."""
        try:
            self._write_project_readme(project_id)
        except (OSError, ValueError, KeyError) as exc:
            _logger.warning("Could not regenerate README for %s: %s", project_id, exc)

    def _write_project_readme(self, project_id: str) -> None:
        """Regenerate the generated project README (phase, artifact links)."""
        record = _read_meta_file(self._project_dir(project_id) / "project.json")
        phase = str((record or {}).get("current_phase", "")) or "intake"
        title = str((record or {}).get("title", "")) or project_id
        lines = [
            f"# {title}",
            "",
            f"Project `{project_id}` — current phase: **{phase}**.",
            "",
            "## Artifacts (current versions)",
            "",
        ]
        artifacts = self.list_artifacts(project_id)
        if artifacts:
            for meta in artifacts:
                phase_dirname = paths.PHASE_DIR_MAP.get(meta.phase.value, meta.phase.value)
                view = (
                    self._project_dir(project_id)
                    / "artifacts"
                    / phase_dirname
                    / meta.artifact_id
                    / "current.md"
                )
                if view.exists():
                    link = f"artifacts/{phase_dirname}/{meta.artifact_id}/current.md"
                    lines.append(
                        f"- [{meta.artifact_id}]({link}) — {meta.phase.value}, "
                        f"v{meta.version}, {meta.status.value}"
                    )
                else:
                    lines.append(
                        f"- {meta.artifact_id} — {meta.phase.value}, "
                        f"v{meta.version}, {meta.status.value}"
                    )
        else:
            lines.append("_No artifacts yet._")
        deliverables = self._project_dir(project_id) / "deliverables"
        if deliverables.is_dir() and any(deliverables.glob("*.md")):
            lines += ["", "## Deliverables", "", "- See [deliverables/](deliverables/README.md)."]
        atomic_write_text(
            self._project_dir(project_id) / "README.md",
            "".join(f"{line}\n" for line in lines),
        )

    def _record_deliverable(self, project_id: str, phase: str, artifact_id: str) -> None:
        """Copy the approved artifact's human view into ``deliverables/``."""
        source = self._artifact_dir(project_id, phase, artifact_id) / "current.md"
        if not source.exists():
            return
        deliverables = self._project_dir(project_id) / "deliverables"
        deliverables.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            deliverables / f"{phase}-{artifact_id}.md",
            source.read_text(encoding="utf-8"),
        )
        lines = ["# Deliverables", "", "Approved artifacts, one file per approval:", ""]
        for entry in sorted(deliverables.glob("*.md")):
            if entry.name != "README.md":
                lines.append(f"- [{entry.stem}]({entry.name})")
        atomic_write_text(deliverables / "README.md", "".join(f"{line}\n" for line in lines))

    def _write_index(self, project_id: str) -> None:
        """Regenerate the derived artifact index for one project."""
        entries: list[ArtifactIndexEntry] = []
        base = self._artifacts_base(project_id)
        if base.is_dir():
            for meta_file in sorted(base.glob("*/*/meta.json")):
                meta = _read_meta_file(meta_file)
                if meta is None:
                    continue
                entries.append(ArtifactIndexEntry.model_validate(meta))
        index = ArtifactIndex(artifacts=entries)
        atomic_write_text(self._index_path(project_id), dump_json(index.model_dump(mode="json")))

    # --- Read path ----------------------------------------------------------

    def load(
        self, project_id: str, phase: FilmPhase, artifact_id: str, version: int
    ) -> dict[str, Any]:
        """Load an artifact body (payload) as a raw dict.

        A mutable kind has one revision-counted file, so only the ref naming its
        CURRENT revision resolves; requesting a superseded revision raises
        rather than silently returning newer content (the ref grammar promises
        ``v<N>`` identifies what was asked for).
        """
        if self._safe_spec(artifact_id).mutable:
            envelope = self.load_mutable_envelope(project_id, phase, artifact_id)
            if envelope.version != version:
                raise MutableRevisionMismatchError(
                    artifact_id, requested=version, current=envelope.version
                )
            return envelope.payload
        path = self._version_path(project_id, phase.value, artifact_id, version)
        if not path.exists():
            raise FileNotFoundError(f"Artifact version not found: {path}")
        return self._read_checked_envelope(path, artifact_id).payload

    def load_envelope(
        self, project_id: str, phase: FilmPhase, artifact_id: str, version: int
    ) -> ArtifactEnvelope:
        """Load one artifact version envelope, schema-checked and migrated.

        Mutable kinds have no ``versions/`` tree, so they route to their single
        revision-counted file; a stale revision raises rather than reporting a
        bare missing file.
        """
        if self._safe_spec(artifact_id).mutable:
            envelope = self.load_mutable_envelope(project_id, phase, artifact_id)
            if envelope.version != version:
                raise MutableRevisionMismatchError(
                    artifact_id, requested=version, current=envelope.version
                )
            return envelope
        path = self._version_path(project_id, phase.value, artifact_id, version)
        if not path.exists():
            raise FileNotFoundError(f"Artifact version not found: {path}")
        return self._read_checked_envelope(path, artifact_id)

    def _read_checked_envelope(self, path: Path, artifact_id: str) -> ArtifactEnvelope:
        """Read, integrity-check, and schema-check one envelope."""
        envelope = _read_envelope(path)
        spec = self._safe_spec(artifact_id)
        if envelope.schema_version > spec.schema_version:
            raise SchemaTooNewError(
                envelope.kind, envelope.schema_version, spec.schema_version, str(path)
            )
        if envelope.schema_version < spec.schema_version:
            migrated = migrate_payload(
                envelope.kind,
                envelope.payload,
                envelope.schema_version,
                spec.schema_version,
            )
            return envelope.model_copy(
                update={"payload": migrated, "schema_version": spec.schema_version}
            )
        return envelope

    def list_artifacts(
        self, project_id: str, phase: FilmPhase | None = None
    ) -> list[ArtifactMetadata]:
        """List artifact metadata for a project, optionally filtered by phase.

        Defined ordering: pipeline phase order, then artifact id, then
        current version descending.
        """
        results: list[ArtifactMetadata] = []
        base = self._artifacts_base(project_id)
        if base.is_dir():
            pattern = (
                "*/*/meta.json"
                if phase is None
                else f"{paths.PHASE_DIR_MAP.get(phase.value, phase.value)}/*/meta.json"
            )
            for meta_path in sorted(base.glob(pattern)):
                meta = _read_meta_file(meta_path)
                if meta is not None:
                    results.append(_meta_record_to_metadata(meta))
        phase_order = {name: index for index, name in enumerate(paths.PHASE_DIR_MAP)}
        return sorted(
            results,
            key=lambda r: (
                phase_order.get(r.phase.value, len(phase_order)),
                r.artifact_id,
                -r.version,
            ),
        )

    def next_version(self, project_id: str, phase: str, artifact_id: str) -> int:
        """Next version number for an artifact: max(existing) + 1."""
        existing = _scan_versions(self._versions_dir(project_id, phase, artifact_id))
        return max(existing) + 1 if existing else 1

    def latest_version(self, project_id: str, phase: str, artifact_id: str) -> int:
        """Version number of the current version (0 when the artifact is absent)."""
        meta = _read_meta_file(self._meta_path(project_id, phase, artifact_id))
        return int(meta["current_version"]) if meta is not None else 0

    def load_metadata(
        self, project_id: str, phase: str, artifact_id: str, version: int
    ) -> ArtifactMetadata:
        """Metadata for one version; non-current versions report SUPERSEDED.

        Immutable per-version fields (provenance, lineage) come from that
        version's envelope; mutable artifact-level fields (status, review
        refs) come from ``meta.json``.
        """
        meta = _read_meta_file(self._meta_path(project_id, phase, artifact_id))
        if meta is None:
            raise FileNotFoundError(
                f"Artifact metadata not found: {self._meta_path(project_id, phase, artifact_id)}"
            )
        current_version = int(meta["current_version"])
        mutable_fields = {
            "approval_ref": meta.get("approval_ref"),
            "kb_context_ref": meta.get("kb_context_ref"),
            "reviewed_by": list(meta.get("reviewed_by", [])),
            "validation_refs": list(meta.get("validation_refs", [])),
        }
        if version != current_version:
            version_path = self._version_path(project_id, phase, artifact_id, version)
            if not version_path.exists():
                raise FileNotFoundError(f"Artifact version not found: {version_path}")
            record = _envelope_to_metadata(_read_envelope(version_path), ArtifactStatus.SUPERSEDED)
            return record.model_copy(update=mutable_fields)
        envelope_path = self._version_path(project_id, phase, artifact_id, current_version)
        if envelope_path.exists():
            record = _envelope_to_metadata(
                _read_envelope(envelope_path), ArtifactStatus(str(meta["status"]))
            )
            return record.model_copy(update=mutable_fields)
        return _meta_record_to_metadata(meta)

    # --- Status transitions --------------------------------------------------

    def approve(
        self,
        project_id: str,
        phase: str,
        artifact_id: str,
        version: int,
        approval_ref: str | None = None,
    ) -> ArtifactMetadata:
        """Transition the artifact (at its current version) from CANDIDATE to APPROVED."""
        return self._transition_status(
            project_id,
            phase,
            artifact_id,
            version,
            expected_status=ArtifactStatus.CANDIDATE,
            next_status=ArtifactStatus.APPROVED,
            action="approve",
            approval_ref=approval_ref,
        )

    def supersede(
        self, project_id: str, phase: str, artifact_id: str, version: int
    ) -> ArtifactMetadata:
        """Transition the artifact (at its current version) from APPROVED to SUPERSEDED."""
        return self._transition_status(
            project_id,
            phase,
            artifact_id,
            version,
            expected_status=ArtifactStatus.APPROVED,
            next_status=ArtifactStatus.SUPERSEDED,
            action="supersede",
            approval_ref=None,
        )

    def _transition_status(
        self,
        project_id: str,
        phase: str,
        artifact_id: str,
        version: int,
        expected_status: ArtifactStatus,
        next_status: ArtifactStatus,
        action: str,
        approval_ref: str | None,
    ) -> ArtifactMetadata:
        with self._project_lock(project_id):
            return self._transition_status_locked(
                project_id,
                phase,
                artifact_id,
                version,
                expected_status,
                next_status,
                action,
                approval_ref,
            )

    def _transition_status_locked(
        self,
        project_id: str,
        phase: str,
        artifact_id: str,
        version: int,
        expected_status: ArtifactStatus,
        next_status: ArtifactStatus,
        action: str,
        approval_ref: str | None,
    ) -> ArtifactMetadata:
        meta_path = self._meta_path(project_id, phase, artifact_id)
        raw = _read_meta_file(meta_path)
        if raw is None:
            raise ValueError(f"Cannot {action} {artifact_id}: artifact not found at {meta_path}")
        current_version = int(raw["current_version"])
        if version != current_version:
            raise ValueError(
                f"Cannot {action} {artifact_id} v{version}: only the current version "
                f"v{current_version} can be transitioned."
            )
        status = ArtifactStatus(str(raw["status"]))
        if status != expected_status:
            raise ValueError(
                f"Cannot {action} {artifact_id}: status is {status.value}, "
                f"expected {expected_status.value}"
            )
        updates: dict[str, Any] = {
            "status": next_status.value,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if approval_ref is not None:
            updates["approval_ref"] = approval_ref
        raw.update(updates)
        atomic_write_text(meta_path, dump_json(raw))
        self._write_index(project_id)
        if next_status == ArtifactStatus.APPROVED:
            self._record_deliverable(project_id, phase, artifact_id)
        self._safe_write_readme(project_id)
        return _meta_record_to_metadata(raw)

    def _safe_spec(self, artifact_id: str) -> KindSpec:
        try:
            return REGISTRY.spec_for(artifact_id)
        except KindNotRegisteredError:
            return KindSpec(artifact_id=artifact_id, kind=f"film.studio/{artifact_id}")


# --- Module helpers -----------------------------------------------------------


def _scan_versions(versions_dir: Path) -> list[int]:
    if not versions_dir.is_dir():
        return []
    versions: list[int] = []
    for path in versions_dir.glob("v*.json"):
        try:
            versions.append(int(path.stem.removeprefix("v")))
        except ValueError:
            continue
    return versions


def _read_envelope(path: Path) -> ArtifactEnvelope:
    """Parse one envelope file: integrity-check the checksum, warn on unknown keys."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    envelope = ArtifactEnvelope.model_validate(raw)
    if envelope.checksum and envelope.checksum != payload_checksum(envelope.payload):
        raise ChecksumMismatchError(
            f"Artifact {path} failed its integrity check: stored "
            f"{envelope.checksum} != computed {payload_checksum(envelope.payload)}. "
            "The file was modified outside film-pipeline or is corrupt; restore it "
            "from a checkpoint or backup."
        )
    unknown = set(raw) - set(ArtifactEnvelope.model_fields)
    if unknown:
        _logger.warning(
            "Artifact %s carries unknown envelope fields %s (written by a newer "
            "build?); they are preserved on disk but not interpreted.",
            path,
            sorted(unknown),
        )
    return envelope


def _read_meta_file(meta_path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _envelope_to_metadata(envelope: ArtifactEnvelope, status: ArtifactStatus) -> ArtifactMetadata:
    """Build the public ``ArtifactMetadata`` view from a version envelope.

    Status is artifact-level (from ``meta.json``); envelopes are immutable.
    """
    return ArtifactMetadata(
        artifact_id=envelope.artifact_id,
        artifact_type=envelope.artifact_type,
        project_id=envelope.project_id,
        phase=envelope.phase,
        version=envelope.version,
        status=status,
        parents=envelope.parents,
        created_by=envelope.created_by,
        reviewed_by=envelope.reviewed_by,
        validation_refs=envelope.validation_refs,
        approval_ref=envelope.approval_ref,
        kb_context_ref=envelope.kb_context_ref,
        created_at=envelope.created_at,
        built_from=envelope.built_from,
        change_summary=envelope.change_summary,
    )


def _meta_record_to_metadata(raw: dict[str, Any]) -> ArtifactMetadata:
    """Build the public ``ArtifactMetadata`` view from a ``meta.json`` record."""
    return ArtifactMetadata(
        artifact_id=str(raw["artifact_id"]),
        artifact_type=ArtifactType(str(raw["artifact_type"])),
        project_id=str(raw["project_id"]),
        phase=FilmPhase(str(raw["phase"])),
        version=int(raw["current_version"]),
        status=ArtifactStatus(str(raw["status"])),
        parents=[],
        created_by=str(raw.get("created_by", "")),
        reviewed_by=list(raw.get("reviewed_by", [])),
        validation_refs=list(raw.get("validation_refs", [])),
        approval_ref=raw.get("approval_ref"),
        kb_context_ref=raw.get("kb_context_ref"),
        created_at=datetime.fromisoformat(str(raw["created_at"])),
        built_from={},
        change_summary="",
    )


def _render_markdown(kind: str, meta: ArtifactMetadata, payload: dict[str, Any]) -> str:
    title = f"# {meta.artifact_id}\n\n"
    details = [
        f"- phase: {meta.phase.value}",
        f"- type: {meta.artifact_type.value}",
        f"- version: {meta.version}",
        f"- status: {meta.status.value}",
    ]
    # The registry owns which renderer a kind uses (plan D4/D9), so there is no
    # second table here to drift out of sync with the kind slugs.
    renderer = _renderer_for(kind)
    body = renderer(payload) if renderer is not None else _markdown_body(payload)
    detail_text = "\n".join(details)
    return f"{title}{detail_text}\n\n{body}\n"


def _renderer_for(kind: str) -> Renderer | None:
    """Renderer registered for ``kind``, or ``None`` for the generic fallback."""
    return REGISTRY.renderer_for(kind)


def _markdown_body(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("text"), str):
        return str(payload["text"])
    if isinstance(payload.get("treatment"), dict) and isinstance(
        payload["treatment"].get("text"), str
    ):
        return str(payload["treatment"]["text"])
    scenes = _scene_rows(payload)
    if scenes:
        return "\n\n".join(_scene_markdown(scene) for scene in scenes)
    return "\n".join(f"- {key}: {_markdown_value(value)}" for key, value in payload.items())


def _scene_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    scene_list = payload.get("scene_list")
    nested = scene_list.get("scenes", []) if isinstance(scene_list, dict) else []
    rows: list[dict[str, Any]] = []
    for container in (payload.get("scenes"), payload.get("rows"), nested):
        if isinstance(container, list):
            rows.extend(row for row in container if isinstance(row, dict))
    return rows


def _scene_markdown(scene: dict[str, Any]) -> str:
    heading = str(scene.get("scene_heading", scene.get("scene_id", "Scene")))
    lines = [f"## {heading}"]
    for key in (
        "scene_id",
        "dramatic_function",
        "story_function",
        "conflict",
        "outcome",
        "environment",
        "viewpoint",
        "camera_profile",
        "camera_movement",
        "movement",
    ):
        if scene.get(key):
            lines.append(f"- {key}: {scene[key]}")
    for action in scene.get("action_lines", []):
        lines.append(str(action))
    for dialogue in scene.get("dialogue", []):
        if isinstance(dialogue, dict):
            character = str(dialogue.get("character_id", "")).upper()
            direction = str(dialogue.get("direction", ""))
            line = str(dialogue.get("line", ""))
            lines.append(f"{character} {f'({direction}) ' if direction else ''}{line}".strip())
    for key in ("characters", "asset_refs", "reference_refs", "validation_refs"):
        if scene.get(key):
            lines.append(f"- {key}: {_markdown_value(scene[key])}")
    return "\n".join(lines)


def _markdown_value(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return f"{len(value)} field(s)"
    return str(value)
