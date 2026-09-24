"""Storage migration: pre-upgrade layouts → the v2 project layout.

Pure, unit-testable core shared by the ``storage_migrate`` MCP tool and the
command-line entry point (``python -m film_pipeline.artifacts.migration``).

Flow (plan D8): detect legacy project roots → ``--dry-run`` plan → copy
(never move) each project into the target storage root with a per-file
sha256 ledger → verify (re-hash + layout invariants) → quarantine each
source directory as ``<name>.migrated-<timestamp>`` (never hard-delete) →
idempotent re-runs short-circuit via the migration ledger and the target's
``storage.json`` marker.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from film_pipeline.artifacts.paths import PHASE_DIR_MAP
from film_pipeline.artifacts.serialization import atomic_write_text, dump_json, write_json_atomic
from film_pipeline.artifacts.storage import (
    MARKER_FILENAME,
    ensure_storage_root,
    read_marker,
)
from film_pipeline.schemas.runtime_state import ProjectRecord

_logger = logging.getLogger(__name__)

MIGRATION_LOG_FILENAME = "migration-log.jsonl"

# Migrated colon-bearing directory ids map to sanitized names (P2 rename).
_COLON_ID_DIR_PATTERN = re.compile(r"^(?P<prefix>[a-z_]+):(?P<suffix>.+)$")


#: Directory name → phase value (inverse of the write-side map).
_DIR_TO_PHASE: dict[str, str] = {d: p for p, d in PHASE_DIR_MAP.items()}

#: Source-relative files the conversion step intentionally rewrites; the
#: byte-for-byte verification skips them (their conversions are asserted
#: structurally instead).
_CONVERTED_FILES = frozenset(
    {
        ".gitignore",
        "project-state.json",
        "artifacts/07-generated-assets/generation_ledger/versions/v001.json",
    }
)


def _relayout_path(rel: str) -> str:
    """Source-relative path → post-re-layout path (artifacts/ inserted)."""
    parts = Path(rel).parts
    if parts and parts[0] in set(PHASE_DIR_MAP.values()) | {"intake"}:
        return Path("artifacts").joinpath(*parts).as_posix()
    return rel


def _is_converted(rel: str) -> bool:
    """Whether a source-relative path is intentionally rewritten in the copy."""
    if rel in _CONVERTED_FILES:
        return True
    parts = Path(rel).parts
    if any(":" in part for part in parts):
        return True  # colon-id rename
    # Legacy artifact layout: <phase>/<artifact>/... is re-layouted into
    # artifacts/<phase>/<artifact>/ envelopes, so source paths no longer
    # exist byte-for-byte.
    if (
        len(parts) >= 3
        and parts[0] in set(PHASE_DIR_MAP.values()) | {"intake"}
        and parts[-1] in {"current.json", "current.meta.json"}
    ):
        return True
    # Version bodies/sidecars under a legacy artifact dir are folded into
    # envelopes (same reason as above).
    return (
        len(parts) >= 4
        and parts[0] in set(PHASE_DIR_MAP.values()) | {"intake"}
        and "versions" in parts
    )


class MigrationError(RuntimeError):
    """Raised when a migration step fails; the source is never touched."""


class ConfirmationRequired(MigrationError):
    """Raised when migrate() is called without confirmed=True."""


@dataclass(frozen=True)
class LegacyProject:
    """One detected pre-upgrade project."""

    project_id: str
    source_dir: Path
    kind: str  # "artifact-tree" | "runtime-state"


@dataclass(frozen=True)
class ProjectPlan:
    project_id: str
    source_dir: Path
    target_dir: Path
    file_count: int
    total_bytes: int
    skip_reason: str = ""


@dataclass(frozen=True)
class MigrationPlan:
    source_roots: list[Path]
    target_root: Path
    projects: list[ProjectPlan] = field(default_factory=list)


@dataclass
class MigrationResult:
    target_root: Path
    migrated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    quarantined: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    files_copied: int = 0
    verified: bool = False


# --- Detection -----------------------------------------------------------------


def looks_like_legacy_project(project_dir: Path) -> bool:
    """Heuristic for pre-upgrade project directories (legacy layouts only)."""
    if (project_dir / "project.json").exists():
        return False  # already v2-era record; not a migration source
    if any(project_dir.glob("artifacts/*/*/meta.json")):
        return False  # already carries v2 artifacts
    if (project_dir / "project-state.json").is_file():
        return True  # runtime-state-only project (no artifacts at all)
    if any(project_dir.rglob("current.meta.json")):
        return True
    return bool(any(project_dir.rglob("*.v*.json")))


def discover_legacy_projects(source_root: Path) -> list[LegacyProject]:
    """Find legacy project directories directly under ``source_root``."""
    found: list[LegacyProject] = []
    if not source_root.is_dir():
        return found
    for child in sorted(source_root.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or "migrated-" in child.name:
            continue
        if looks_like_legacy_project(child):
            kind = "runtime-state" if (child / "project-state.json").is_file() else "artifact-tree"
            found.append(LegacyProject(project_id=child.name, source_dir=child, kind=kind))
    return found


# --- Planning ------------------------------------------------------------------


def _tree_stats(root: Path) -> tuple[int, int]:
    count = 0
    total = 0
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            count += 1
            total += path.stat().st_size
    return count, total


def plan_migration(source_roots: list[Path], target_root: Path) -> MigrationPlan:
    """Build the dry-run plan: what would move where, and what would be skipped."""
    target_root = Path(target_root)
    projects: list[ProjectPlan] = []
    for source_root in source_roots:
        for legacy in discover_legacy_projects(source_root):
            target_dir = target_root / legacy.project_id
            skip = ""
            if target_dir.exists() and read_marker(target_root) is not None:
                already = (
                    _ledger_contains(target_root, legacy.project_id)
                    or (target_dir / "project.json").exists()
                )
                if already:
                    skip = "already migrated"
            file_count, total_bytes = _tree_stats(legacy.source_dir)
            projects.append(
                ProjectPlan(
                    project_id=legacy.project_id,
                    source_dir=legacy.source_dir,
                    target_dir=target_dir,
                    file_count=file_count,
                    total_bytes=total_bytes,
                    skip_reason=skip,
                )
            )
    return MigrationPlan(
        source_roots=[Path(root) for root in source_roots],
        target_root=target_root,
        projects=projects,
    )


# --- Conversion helpers ---------------------------------------------------------


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _migrated_dir_name(name: str) -> str:
    """Map legacy (possibly colon-bearing) artifact directory names to v2 ids."""
    if ":" not in name:
        return name
    from film_pipeline.artifacts.registry import sanitize_artifact_id

    prefix, _, rest = name.partition(":")
    return f"{sanitize_artifact_id(prefix)}__{sanitize_artifact_id(rest)}"


def _convert_runtime_state(project_dir: Path) -> None:
    """Upgrade ``project-state.json`` to the typed ``project.json`` record."""
    legacy = project_dir / "project-state.json"
    record_path = project_dir / "project.json"
    if not legacy.exists() or record_path.exists():
        return
    try:
        raw = json.loads(legacy.read_text(encoding="utf-8"))
        record = ProjectRecord.model_validate(raw)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _logger.warning("Could not convert %s: %s", legacy, exc)
        return
    data = record.model_dump(mode="json")
    dead = _mark_dead_path_refs(data)
    if dead:
        data["migrated_dead_refs"] = dead
        _logger.warning("Normalized %d unresolvable path-shaped refs in %s", len(dead), legacy)
    write_json_atomic(record_path, data)


def _mark_dead_path_refs(data: dict[str, Any]) -> dict[str, str]:
    """Blank out unresolvable path-shaped ``*_ref`` values (plan D8).

    The pre-rewrite store returned filesystem paths from ``save()`` and some
    of those leaked into state as ``*_ref`` values. Canonical refs start with
    ``artifact:``; anything else that looks like a path cannot be resolved
    against the new layout, so it is blanked and its original recorded under
    ``migrated_dead_refs`` for the operator.
    """
    dead: dict[str, str] = {}
    for key, value in list(data.items()):
        if (
            key.endswith("_ref")
            and isinstance(value, str)
            and value
            and not value.startswith("artifact:")
            and ("/" in value or "\\" in value or value.endswith(".json"))
        ):
            dead[key] = value
            data[key] = ""
    return dead


def _convert_versioned_ledger(project_dir: Path) -> None:
    """Move a P2-era rewritten ``versions/v001.json`` ledger to the mutable file."""
    for base in (
        project_dir / "artifacts" / PHASE_DIR_MAP["generation"],
        project_dir / PHASE_DIR_MAP["generation"],  # legacy layout: no artifacts/ parent
    ):
        ledger_dir = base / "generation_ledger"
        version_file = ledger_dir / "versions" / "v001.json"
        mutable_file = ledger_dir / "generation_ledger.json"
        if not version_file.exists():
            continue
        if mutable_file.exists():
            return
        try:
            raw = json.loads(version_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _logger.warning("Could not convert legacy ledger %s: %s", version_file, exc)
            return
        raw.setdefault("revision", 1)
        write_json_atomic(mutable_file, raw)
        return


def _upgrade_gitignore(project_dir: Path) -> None:
    gitignore = project_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("media/\n")
        return
    text = gitignore.read_text(encoding="utf-8")
    if "media/" not in text.splitlines():
        atomic_write_text(gitignore, "media/\n" + text)


def _relayout_artifacts(project_dir: Path) -> None:
    """Move legacy phase dirs under ``artifacts/`` and convert to envelopes."""
    artifacts_root = project_dir / "artifacts"
    phase_names = set(PHASE_DIR_MAP.values()) | {"intake"}
    for phase_dir in sorted(project_dir.iterdir()):
        if not phase_dir.is_dir() or phase_dir.name not in phase_names:
            continue
        artifacts_root.mkdir(exist_ok=True)
        phase_dir.rename(artifacts_root / phase_dir.name)

    if not artifacts_root.is_dir():
        return
    for artifact_dir in sorted(artifacts_root.glob("*/*")):
        if artifact_dir.is_dir() and (artifact_dir / "current.json").exists():
            _convert_artifact_dir(artifact_dir)


def _convert_artifact_dir(artifact_dir: Path) -> None:
    """Convert one legacy artifact directory (current.json + sidecars) to v2."""
    from film_pipeline.schemas.artifact import ArtifactMetadata

    versions_dir = artifact_dir / "versions"
    if not versions_dir.is_dir():
        versions_dir.mkdir(parents=True)
        versions_dir = artifact_dir / "versions"

    current_body_path = artifact_dir / "current.json"
    if not current_body_path.exists():
        return  # versions-only dir: kept as data, flagged by storage_verify
    project_dir = artifact_dir.parents[2]
    phase_name = artifact_dir.parents[0].name
    current_meta_path = artifact_dir / "current.meta.json"
    payload = json.loads(current_body_path.read_text(encoding="utf-8"))
    if current_meta_path.exists():
        legacy_meta = ArtifactMetadata.model_validate_json(
            current_meta_path.read_text(encoding="utf-8")
        )
    else:
        # No sidecar: synthesize minimal metadata from the directory layout
        # so the artifact still becomes a first-class v2 envelope. The kind
        # is unknowable from the dir alone, so the payload is typed as an
        # intake analysis (the generic payload shape).
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import (
            ArtifactStatus,
            ArtifactType,
            FilmPhase,
        )

        phase = _DIR_TO_PHASE.get(phase_name)
        if phase is None:
            _logger.warning(
                "Skipping %s: directory %s does not map to a known phase.",
                artifact_dir,
                phase_name,
            )
            return
        legacy_meta = ArtifactMetadata(
            artifact_id=artifact_dir.name,
            artifact_type=ArtifactType.INTAKE_ANALYSIS,
            project_id=project_dir.name,
            phase=FilmPhase(phase),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            created_by="storage-migration",
            created_at=datetime.now(UTC),
        )
    kind = f"film.studio/{legacy_meta.artifact_id.replace('_', '-')}"
    spec_version = _safe_schema_version(legacy_meta.artifact_id)

    # Re-materialize every historical version as an envelope.
    for version_file in sorted(versions_dir.glob("v*.json")):
        if _is_envelope(version_file):
            continue
        if version_file.name.endswith(".meta.json"):
            continue  # legacy sidecar; folded into its envelope
        version = int(version_file.stem.removeprefix("v"))
        sidecar = versions_dir / f"{version_file.stem}.meta.json"
        body = json.loads(version_file.read_text(encoding="utf-8"))
        version_meta = legacy_meta
        if sidecar.exists():
            try:
                version_meta = ArtifactMetadata.model_validate_json(
                    sidecar.read_text(encoding="utf-8")
                )
            except ValueError:
                _logger.warning(
                    "Version sidecar %s is malformed; falling back to the "
                    "artifact's current metadata for v%03d provenance.",
                    sidecar,
                    version,
                )
        envelope = _legacy_envelope(body, version_meta, version, kind, spec_version)
        atomic_write_text(version_file, dump_json(envelope))

    envelope = _legacy_envelope(payload, legacy_meta, legacy_meta.version, kind, spec_version)
    atomic_write_text(versions_dir / f"v{legacy_meta.version:03}.json", dump_json(envelope))

    meta_file = artifact_dir / "meta.json"
    if not meta_file.exists():
        from datetime import UTC, datetime

        write_json_atomic(
            meta_file,
            {
                "schema_version": 1,
                "artifact_id": legacy_meta.artifact_id,
                "artifact_type": str(legacy_meta.artifact_type.value),
                "project_id": legacy_meta.project_id,
                "phase": str(legacy_meta.phase.value),
                "current_version": legacy_meta.version,
                "status": str(legacy_meta.status.value),
                "created_at": legacy_meta.created_at.isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "created_by": legacy_meta.created_by,
                "checksum": envelope["checksum"],
            },
        )
    current_md = artifact_dir / "current.md"
    if not current_md.exists():
        from film_pipeline.artifacts.store import _render_markdown

        atomic_write_text(current_md, _render_markdown(kind, legacy_meta, payload))
    # Legacy current body + sidecar are superseded by meta.json + envelopes.
    current_body_path.unlink()
    current_meta_path.unlink(missing_ok=True)


def _is_envelope(path: Path) -> bool:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(raw, dict) and "kind" in raw and "payload" in raw


def _safe_schema_version(artifact_id: str) -> int:
    from film_pipeline.artifacts.registry import REGISTRY, KindNotRegisteredError

    try:
        return REGISTRY.spec_for(artifact_id).schema_version
    except KindNotRegisteredError:
        return 1


def _legacy_envelope(
    payload: dict[str, Any], meta: Any, version: int, kind: str, schema_version: int
) -> dict[str, Any]:
    from film_pipeline.artifacts.envelope import payload_checksum

    return {
        "kind": kind,
        "schema_version": schema_version,
        "artifact_id": meta.artifact_id,
        "artifact_type": str(meta.artifact_type.value),
        "project_id": meta.project_id,
        "phase": str(meta.phase.value),
        "version": version,
        "created_at": meta.created_at.isoformat(),
        "created_by": meta.created_by,
        "reviewed_by": meta.reviewed_by,
        "validation_refs": meta.validation_refs,
        "approval_ref": meta.approval_ref,
        "kb_context_ref": meta.kb_context_ref,
        "parents": [parent.model_dump(mode="json") for parent in meta.parents],
        "built_from": meta.built_from,
        "change_summary": meta.change_summary,
        "checksum": payload_checksum(payload),
        "payload": payload,
    }


def _convert_project(project_dir: Path) -> None:
    """In-place conversions on the COPY inside the new root."""
    _relayout_artifacts(project_dir)
    _convert_versioned_ledger(project_dir)
    _convert_runtime_state(project_dir)
    _upgrade_gitignore(project_dir)
    # Colon-bearing artifact directory names → sanitized v2 ids (both the
    # legacy root shape and the v2 artifacts/ shape).
    for phase_dir in list(project_dir.glob("*")) + list(project_dir.glob("artifacts/*")):
        if not phase_dir.is_dir():
            continue
        for child in sorted(phase_dir.iterdir()):
            new_name = _migrated_dir_name(child.name)
            if new_name != child.name:
                child.rename(child.parent / new_name)


# --- Core migration --------------------------------------------------------------


def _ledger_path(target_root: Path) -> Path:
    return target_root.parent / MIGRATION_LOG_FILENAME


def _ledger_contains(target_root: Path, project_id: str) -> bool:
    log_path = _ledger_path(target_root)
    if not log_path.exists():
        return False
    for line in log_path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("project_id") == project_id and entry.get("event") == "migrated":
            return True
    return False


def _append_ledger(target_root: Path, entry: dict[str, Any]) -> None:
    log_path = _ledger_path(target_root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
        handle.flush()


def migrate(
    source_roots: list[Path],
    target_root: Path,
    *,
    confirmed: bool = False,
    dry_run: bool = False,
) -> MigrationResult:
    """Copy legacy projects into ``target_root``; quarantine the sources.

    Copy-based: sources are renamed to ``<name>.migrated-<timestamp>`` only
    after verification, so rollback is moving them back. Per-project
    isolation: one failing project is recorded in ``result.failed`` and the
    remaining projects still migrate. Raises
    :class:`ConfirmationRequired` when ``confirmed`` is False.
    """
    if not confirmed:
        raise ConfirmationRequired(
            "Storage migration requires confirmation. Re-run with confirmed=True."
        )
    target_root = Path(target_root)
    ensure_storage_root(target_root)
    plan = plan_migration(source_roots, target_root)
    result = MigrationResult(target_root=target_root)

    for project in plan.projects:
        if project.skip_reason:
            result.skipped.append(project.project_id)
            continue
        if dry_run:
            result.skipped.append(f"{project.project_id} (dry-run)")
            continue
        try:
            _migrate_project(project, result)
        except MigrationError as exc:
            result.failed.append(f"{project.project_id}: {exc}")

    result.verified = not result.failed
    return result


def _migrate_project(project: ProjectPlan, result: MigrationResult) -> None:
    """Copy, convert, verify, ledger, and quarantine one project."""
    target_root = result.target_root

    # A target dir with no ledger entry and no typed record is a stale
    # remnant of an interrupted earlier run — replace it.
    if project.target_dir.exists() and not (project.target_dir / "project.json").exists():
        shutil.rmtree(project.target_dir)
    shutil.copytree(project.source_dir, project.target_dir, dirs_exist_ok=True)
    try:
        _convert_project(project.target_dir)
    except Exception as exc:
        shutil.rmtree(project.target_dir, ignore_errors=True)
        raise MigrationError(f"Conversion failed for {project.project_id}: {exc}") from exc
    ensure_storage_root(target_root)

    # Verify: re-hash every copied non-git file against the source at its
    # post-re-layout location, excluding files the conversion step
    # intentionally rewrites.
    source_files = {
        p.relative_to(project.source_dir).as_posix()
        for p in project.source_dir.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }
    for rel in sorted(source_files):
        if _is_converted(rel):
            continue
        source_file = project.source_dir / rel
        target_file = project.target_dir / _relayout_path(rel)
        if not target_file.exists():
            raise MigrationError(f"Verification failed for {project.project_id}: missing {rel}")
        if _sha256(source_file) != _sha256(target_file):
            raise MigrationError(
                f"Verification failed for {project.project_id}: hash mismatch {rel}"
            )
    for converted in _CONVERTED_FILES:
        if (project.source_dir / converted).exists() and not (
            project.target_dir / _relayout_path(converted)
        ).exists():
            raise MigrationError(
                f"Verification failed for {project.project_id}: "
                f"converted file vanished: {converted}"
            )
    result.files_copied += len(source_files)
    result.migrated.append(project.project_id)
    _append_ledger(
        target_root,
        {
            "event": "migrated",
            "project_id": project.project_id,
            "source": str(project.source_dir),
            "target": str(project.target_dir),
            "files": len(source_files),
            "at": datetime.now(UTC).isoformat(),
        },
    )

    # Quarantine the source (rename in place — recoverable, never deleted).
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    quarantine = project.source_dir.parent / f"{project.source_dir.name}.migrated-{timestamp}"
    project.source_dir.rename(quarantine)
    result.quarantined.append(quarantine.name)
    _append_ledger(
        target_root,
        {
            "event": "quarantined",
            "project_id": project.project_id,
            "quarantined_as": quarantine.name,
            "at": datetime.now(UTC).isoformat(),
        },
    )


def storage_verify(root: Path) -> dict[str, Any]:
    """Verify structural invariants of a storage root; return a summary.

    Raises :class:`MigrationError` on the first violated invariant.
    """
    if read_marker(root) is None:
        raise MigrationError(f"{root} has no {MARKER_FILENAME} marker; not a storage root.")
    projects = 0
    artifacts = 0
    for project_dir in sorted(root.iterdir()):
        if not project_dir.is_dir() or project_dir.name.startswith("."):
            continue
        if not (
            (project_dir / "project.json").is_file()
            or (project_dir / "artifacts").is_dir()
            or (project_dir / "state").is_dir()
        ):
            continue  # not a project directory
        projects += 1
        artifacts_base = project_dir / "artifacts"
        if artifacts_base.is_dir():
            remnants = sorted(artifacts_base.glob("*/*/current.json")) + sorted(
                artifacts_base.glob("*/*/current.meta.json")
            )
            if remnants:
                raise MigrationError(f"Legacy artifact remnants survived migration: {remnants[0]}")
            for meta_file in artifacts_base.glob("*/*/meta.json"):
                artifacts += 1
                try:
                    raw = json.loads(meta_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise MigrationError(f"Unreadable meta at {meta_file}: {exc}") from exc
                for required in ("artifact_id", "phase", "current_version", "status"):
                    if required not in raw:
                        raise MigrationError(f"meta at {meta_file} is missing '{required}'.")
    return {"root": str(root), "projects": projects, "artifacts": artifacts, "ok": True}


if __name__ == "__main__":  # pragma: no cover
    from film_pipeline.artifacts.migration_cli import main

    raise SystemExit(main())
