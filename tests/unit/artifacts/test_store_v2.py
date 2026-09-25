"""P2 engine tests: golden layout, envelopes, schema versions, derived index."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel

from film_pipeline.artifacts.envelope import SchemaTooNewError, payload_checksum

if TYPE_CHECKING:
    from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.artifacts.registry import (
    MIGRATIONS,
    REGISTRY,
    register_migration,
)
from film_pipeline.devharness.storage import make_store
from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef
from film_pipeline.schemas.film_constitution import FilmConstitution
from film_pipeline.schemas.script import Script, ScriptScene


def _meta(**kw: object) -> ArtifactMetadata:
    defaults = {
        "artifact_id": "film_constitution",
        "artifact_type": ArtifactType.FILM_CONSTITUTION,
        "project_id": "p1",
        "phase": FilmPhase.CONSTITUTION,
        "version": 1,
        "created_by": "constitution-agent",
        "created_at": datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC),
    }
    defaults.update({k: v for k, v in kw.items() if v is not None})
    return ArtifactMetadata(**defaults)  # type: ignore[arg-type]


def _constitution() -> FilmConstitution:
    return FilmConstitution(
        project_id="p1",
        theme="connection",
        tone="quiet",
        visual_language="natural light",
        emotional_promise="wonder",
        camera_philosophy="observe first",
        quality_bar="feature-grade",
    )


class TestGoldenLayout:
    def test_on_disk_tree_is_pinned(self, tmp_path: Path) -> None:
        root = tmp_path / "store"
        store = make_store(root)
        meta = _meta()
        ref = store.save(_constitution(), meta)
        expected = {
            "p1/artifacts/01-vision/film_constitution/meta.json",
            "p1/artifacts/01-vision/film_constitution/current.md",
            "p1/artifacts/01-vision/film_constitution/versions/v001.json",
            "p1/index/artifacts.json",
            "p1/README.md",
            "p1/.storage.lock",
            "storage.json",
        }
        actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
        assert actual == expected
        assert ref.to_string() == "artifact:constitution:film_constitution:v1"

    def test_json_files_are_deterministic_and_sorted(self, tmp_path: Path) -> None:
        store_a = make_store(tmp_path / "a")
        store_b = make_store(tmp_path / "b")
        meta = _meta()
        store_a.save(_constitution(), meta)
        store_b.save(_constitution(), meta)
        file_a = tmp_path / "a/p1/artifacts/01-vision/film_constitution/versions/v001.json"
        file_b = tmp_path / "b/p1/artifacts/01-vision/film_constitution/versions/v001.json"
        assert file_a.read_bytes() == file_b.read_bytes()
        text = file_a.read_text()
        assert text.endswith("}\n")
        keys = list(json.loads(text).keys())
        assert keys == sorted(keys)

    def test_new_versions_append_and_current_pointer_moves(self, tmp_path: Path) -> None:
        root = tmp_path / "store"
        store = make_store(root)
        base_meta = _meta(
            artifact_id="script",
            artifact_type=ArtifactType.SCRIPT,
            phase=FilmPhase.SCRIPT,
        )
        store.save(Script(project_id="p1", title="T", scenes=[]), base_meta)
        script_v2 = Script(
            project_id="p1",
            title="T",
            scenes=[ScriptScene(scene_id="SC_001", scene_heading="INT. ROOM")],
        )
        store.save(script_v2, base_meta)
        versions_dir = root / "p1/artifacts/03-script/script/versions"
        assert sorted(p.name for p in versions_dir.glob("*.json")) == [
            "v001.json",
            "v002.json",
        ]
        meta_file = json.loads((root / "p1/artifacts/03-script/script/meta.json").read_text())
        assert meta_file["current_version"] == 2
        assert store.load("p1", FilmPhase.SCRIPT, "script", 2)["scenes"]
        assert store.load("p1", FilmPhase.SCRIPT, "script", 1)["scenes"] == []


class TestEnvelope:
    def test_envelope_carries_full_metadata_set(self, tmp_path: Path) -> None:
        store = make_store(tmp_path / "store")
        meta = _meta(kb_context_ref="kbctx:p1:x", change_summary="first cut")
        store.save(_constitution(), meta)
        envelope = store.load_envelope("p1", FilmPhase.CONSTITUTION, "film_constitution", 1)
        assert envelope.kind == "film.studio/film-constitution"
        assert envelope.artifact_type == ArtifactType.FILM_CONSTITUTION
        assert envelope.project_id == "p1"
        assert envelope.phase == FilmPhase.CONSTITUTION
        assert envelope.created_by == "constitution-agent"
        assert envelope.kb_context_ref == "kbctx:p1:x"
        assert envelope.change_summary == "first cut"
        assert envelope.checksum.startswith("sha256:")
        assert envelope.prompt_template_version is None
        assert envelope.model_profile is None

    def test_load_metadata_reflects_envelope_provenance(self, tmp_path: Path) -> None:
        store = make_store(tmp_path / "store")
        meta = _meta(built_from={"treatment": "artifact:script:treatment:v1"})
        store.save(_constitution(), meta)
        record = store.load_metadata("p1", "constitution", "film_constitution", 1)
        assert record.built_from["treatment"] == "artifact:script:treatment:v1"
        assert record.version == 1
        assert record.status == ArtifactStatus.CANDIDATE

    def test_rejects_newer_schema_version(self, tmp_path: Path) -> None:
        root = tmp_path / "store"
        store = make_store(root)
        store.save(_constitution(), _meta())
        version_file = root / "p1/artifacts/01-vision/film_constitution/versions/v001.json"
        raw = json.loads(version_file.read_text())
        raw["schema_version"] = 99
        version_file.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")
        with pytest.raises(SchemaTooNewError, match="schema_version 99"):
            store.load_envelope("p1", FilmPhase.CONSTITUTION, "film_constitution", 1)


class TestMigrations:
    def test_payload_migrates_through_registered_chain(self, tmp_path: Path) -> None:
        root = tmp_path / "store"
        store = make_store(root)
        meta = _meta(
            artifact_id="logline",
            artifact_type=ArtifactType.LOGLINE,
            phase=FilmPhase.DEVELOPMENT,
        )
        store.save(_DictPayload(text="hello"), meta)
        version_file = root / "p1/artifacts/02-development/logline/versions/v001.json"
        raw = json.loads(version_file.read_text())
        kind = raw["kind"]
        assert kind == "film.studio/logline"
        # Simulate an older writer: downgrade the stored payload to v0 semantics.
        raw["schema_version"] = 0
        raw["payload"] = {"text_v0": raw["payload"]["text"]}
        raw["checksum"] = payload_checksum(dict(raw["payload"]))
        version_file.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")

        saved_migrations = dict(MIGRATIONS)
        register_migration(kind, 0, lambda payload: {"text": payload["text_v0"]})
        try:
            envelope = store.load_envelope("p1", FilmPhase.DEVELOPMENT, "logline", 1)
            assert envelope.payload == {"text": "hello"}
            assert envelope.schema_version == REGISTRY.spec_for("logline").schema_version
        finally:
            MIGRATIONS.clear()
            MIGRATIONS.update(saved_migrations)

    def test_missing_migration_is_actionable(self) -> None:
        from film_pipeline.artifacts.registry import migrate_payload

        with pytest.raises(KeyError, match="No migration registered"):
            migrate_payload("film.studio/logline", {}, 7, 8)


class _DictPayload(BaseModel):
    """Minimal payload model with one field."""

    text: str


class TestDerivedIndex:
    def test_index_reflects_saved_artifacts(self, tmp_path: Path) -> None:
        root = tmp_path / "store"
        store = make_store(root)
        store.save(_constitution(), _meta())
        index = json.loads((root / "p1/index/artifacts.json").read_text())
        assert index["schema_version"] == 1
        assert index["artifacts"] == [
            {
                "artifact_id": "film_constitution",
                "artifact_type": "film_constitution",
                "phase": "constitution",
                "current_version": 1,
                "status": "candidate",
                "created_at": "2026-09-24T12:00:00Z",
                "updated_at": index["artifacts"][0]["updated_at"],
            }
        ]


class TestLegacyReadonly:
    def test_mutable_kind_uses_revision_counted_single_file(self, tmp_path: Path) -> None:
        from film_pipeline.generation.ledger import GenerationLedgerManager

        root = tmp_path / "store"
        store = make_store(root)
        manager = GenerationLedgerManager(store)
        manager.plan_batch("p1", ["S001"], "profile", "model")
        manager.plan_batch("p1", ["S002"], "profile", "model")
        artifact_dir = root / "p1/artifacts/07-generated-assets/generation_ledger"
        assert not (artifact_dir / "versions").exists()
        ledger_file = artifact_dir / "generation_ledger.json"
        assert ledger_file.exists()
        envelope = json.loads(ledger_file.read_text())
        # create (r1) + first plan_batch persist (r2) + second (r3)
        assert envelope["revision"] == 3
        rows = manager.list_rows("p1")
        assert {row.shot_id for row in rows} == {"S001", "S002"}


def test_save_rejects_mutable_kinds(tmp_path: Path) -> None:
    """Mutable kinds must go through save_mutable — never the version path."""
    from film_pipeline.schemas.generation import GenerationLedger

    store = make_store(tmp_path / "store")
    meta = _meta(
        artifact_id="generation_ledger",
        artifact_type=ArtifactType.GENERATION_LEDGER,
        phase=FilmPhase.GENERATION,
    )
    with pytest.raises(ValueError, match="mutable kind"):
        store.save(GenerationLedger(project_id="p1", rows=[]), meta)


def test_meta_json_is_the_only_mutable_file(tmp_path: Path) -> None:
    root = tmp_path / "store"
    store = make_store(root)
    meta = _meta()
    store.save(_constitution(), meta)
    version_file = root / "p1/artifacts/01-vision/film_constitution/versions/v001.json"
    before = version_file.read_bytes()
    store.approve("p1", "constitution", "film_constitution", 1, approval_ref="a-1")
    after = version_file.read_bytes()
    assert before == after
    meta_file = json.loads(
        (root / "p1/artifacts/01-vision/film_constitution/meta.json").read_text()
    )
    assert meta_file["status"] == ArtifactStatus.APPROVED.value
    assert meta_file["approval_ref"] == "a-1"


class TestRegistryRoundTrip:
    def test_every_registered_exact_kind_saves_and_loads(self, tmp_path: Path) -> None:
        """One save/load round-trip per registered exact kind (plan D4)."""
        from pydantic import BaseModel

        class _MinimalPayload(BaseModel):
            note: str = "round-trip"

        store = make_store(tmp_path / "store")
        phase = FilmPhase.INTAKE
        for artifact_id in REGISTRY.known_ids():
            if artifact_id == "graph_state":
                continue  # its payload is validated against CheckpointState in P3
            if REGISTRY.spec_for(artifact_id).mutable:
                continue  # mutable kinds round-trip through save_mutable elsewhere
            meta = _meta(
                artifact_id=artifact_id,
                artifact_type=ArtifactType.PROJECT_CONFIG,
                project_id="p1",
                phase=phase,
            )
            store.save(_MinimalPayload(), meta)
            body = store.load("p1", phase, artifact_id, 1)
            assert body == {"note": "round-trip"}, artifact_id
            envelope = store.load_envelope("p1", phase, artifact_id, 1)
            assert envelope.kind == f"film.studio/{artifact_id.replace('_', '-')}"

    def test_one_id_per_registered_prefix_saves_and_loads(self, tmp_path: Path) -> None:
        from pydantic import BaseModel

        class _MinimalPayload(BaseModel):
            note: str = "prefix"

        store = make_store(tmp_path / "store")
        prefix_samples = {
            "matrix_patch_generation": "generation",
            "repair_feedback_script": "script",
            "profile_change_proposal__profile_change_abc123": "intake",
            "profile_change_approval__profile_approval_abc123": "intake",
            "invalidation_report_deadbeef": "intake",
            "rollback_record_deadbeef": "intake",
            "checkpoint_deadbeef": "intake",
        }
        for artifact_id, phase_value in prefix_samples.items():
            meta = _meta(
                artifact_id=artifact_id,
                artifact_type=ArtifactType.PROJECT_CONFIG,
                project_id="p1",
                phase=FilmPhase(phase_value),
            )
            store.save(_MinimalPayload(), meta)
            assert store.load("p1", FilmPhase(phase_value), artifact_id, 1)

    def test_parents_round_trip_into_the_envelope(self, tmp_path: Path) -> None:
        store = make_store(tmp_path / "store")
        meta = _meta(
            parents=[ArtifactRef(artifact_id="treatment", version=1, phase="script")],
            reviewed_by=["operator-1"],
            validation_refs=["validation:abc"],
            approval_ref="approval:x",
            built_from={"treatment": "artifact:script:treatment:v1"},
        )
        store.save(_constitution(), meta)
        envelope = store.load_envelope("p1", FilmPhase.CONSTITUTION, "film_constitution", 1)
        assert envelope.parents == [ArtifactRef(artifact_id="treatment", version=1, phase="script")]
        assert envelope.reviewed_by == ["operator-1"]
        assert envelope.validation_refs == ["validation:abc"]
        assert envelope.approval_ref == "approval:x"
        assert envelope.built_from == {"treatment": "artifact:script:treatment:v1"}
        assert envelope.version == 1
        assert envelope.artifact_id == "film_constitution"
        assert envelope.created_at == datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC)

    def test_tampered_payload_fails_integrity_check(self, tmp_path: Path) -> None:
        from film_pipeline.artifacts.envelope import ChecksumMismatchError

        root = tmp_path / "store"
        store = make_store(root)
        store.save(_constitution(), _meta())
        version_file = root / "p1/artifacts/01-vision/film_constitution/versions/v001.json"
        raw = json.loads(version_file.read_text())
        raw["payload"]["theme"] = "tampered"
        version_file.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")
        with pytest.raises(ChecksumMismatchError, match="integrity check"):
            store.load("p1", FilmPhase.CONSTITUTION, "film_constitution", 1)

    def test_load_metadata_for_historical_version_uses_that_envelope(self, tmp_path: Path) -> None:
        from film_pipeline.schemas.script import Script

        store = make_store(tmp_path / "store")
        base = _meta(
            artifact_id="script",
            artifact_type=ArtifactType.SCRIPT,
            phase=FilmPhase.SCRIPT,
        )
        meta_v1 = base.model_copy(update={"created_by": "writer-v1"})
        store.save(Script(project_id="p1", title="T", scenes=[]), meta_v1)
        meta_v2 = base.model_copy(update={"created_by": "writer-v2"})
        store.save(
            Script(project_id="p1", title="T", scenes=[]),
            meta_v2,
        )
        historical = store.load_metadata("p1", "script", "script", 1)
        assert historical.created_by == "writer-v1"
        assert historical.status == ArtifactStatus.SUPERSEDED
        current = store.load_metadata("p1", "script", "script", 2)
        assert current.created_by == "writer-v2"
        assert current.status == ArtifactStatus.CANDIDATE


class TestLoadRef:
    def test_phase_bearing_ref_loads_directly(self, tmp_path: Path) -> None:
        root = tmp_path / "store"
        store = make_store(root)
        store.save(_constitution(), _meta())
        body = store.load_ref("p1", "artifact:constitution:film_constitution:v1")
        assert body["theme"] == "connection"

    def test_unknown_ref_names_the_ref_in_the_error(self, tmp_path: Path) -> None:
        store = make_store(tmp_path / "store")
        with pytest.raises(FileNotFoundError, match="artifact:qc:mystery:v2"):
            store.load_ref("p1", "artifact:qc:mystery:v2")


class TestListOrdering:
    def test_phase_order_then_id_then_version_desc(self, tmp_path: Path) -> None:
        from film_pipeline.schemas.script import Script

        root = tmp_path / "store"
        store = make_store(root)
        script_meta = _meta(
            artifact_id="script",
            artifact_type=ArtifactType.SCRIPT,
            phase=FilmPhase.SCRIPT,
        )
        store.save(Script(project_id="p1", title="T", scenes=[]), script_meta)
        store.save(Script(project_id="p1", title="T", scenes=[]), script_meta)
        store.save(
            _constitution(),
            _meta(),  # constitution phase precedes script
        )
        store.save(
            Script(project_id="p1", title="T", scenes=[]),
            _meta(
                artifact_id="dialogue_pass",
                artifact_type=ArtifactType.DIALOGUE_PASS,
                phase=FilmPhase.SCRIPT,
            ),
        )
        listed = store.list_artifacts("p1")
        # One row per artifact (current version), ids ascending within a phase.
        assert [(m.phase.value, m.artifact_id, m.version) for m in listed] == [
            ("constitution", "film_constitution", 1),
            ("script", "dialogue_pass", 1),
            ("script", "script", 2),
        ]


class TestNonFinitePayloads:
    """A stored artifact must always be readable by the store that wrote it.

    Non-finite floats serialize as bare ``Infinity``/``NaN`` (not legal JSON),
    and a reader normalizes them, so the recomputed checksum would differ and
    the artifact would fail its own integrity check forever. These tests pin
    that such a write fails loudly instead of poisoning storage.
    """

    @pytest.mark.parametrize("bad", [float("inf"), float("-inf"), float("nan")])
    def test_save_rejects_non_finite_payload(self, tmp_path: Path, bad: float) -> None:
        from film_pipeline.artifacts.serialization import NonFiniteNumberError
        from film_pipeline.schemas.budget import BudgetState

        store = make_store(tmp_path / "store")
        budget = BudgetState(project_id="p1", per_phase_caps_usd={"script": bad})
        with pytest.raises(NonFiniteNumberError):
            store.save(
                budget, _meta(artifact_id="budget_state", artifact_type=ArtifactType.BUDGET_STATE)
            )

    def test_rejected_write_leaves_no_artifact_behind(self, tmp_path: Path) -> None:
        """A failed save must not leave a half-written, unreadable version."""
        from film_pipeline.artifacts.serialization import NonFiniteNumberError
        from film_pipeline.schemas.budget import BudgetState

        root = tmp_path / "store"
        store = make_store(root)
        with pytest.raises(NonFiniteNumberError):
            store.save(
                BudgetState(project_id="p1", per_phase_caps_usd={"script": float("inf")}),
                _meta(artifact_id="budget_state", artifact_type=ArtifactType.BUDGET_STATE),
            )
        assert store.list_artifacts("p1") == []

    def test_finite_payload_round_trips(self, tmp_path: Path) -> None:
        """The guard must not reject ordinary finite floats."""
        from film_pipeline.schemas.budget import BudgetState

        store = make_store(tmp_path / "store")
        ref = store.save(
            BudgetState(project_id="p1", per_phase_caps_usd={"script": 12.5}),
            _meta(artifact_id="budget_state", artifact_type=ArtifactType.BUDGET_STATE),
        )
        assert store.load_ref("p1", ref)["per_phase_caps_usd"] == {"script": 12.5}

    def test_dump_json_rejects_nested_non_finite(self) -> None:
        """The guard is recursive, so nesting cannot smuggle a bad float in."""
        from film_pipeline.artifacts.serialization import NonFiniteNumberError, dump_json

        with pytest.raises(NonFiniteNumberError):
            dump_json({"a": [{"b": float("nan")}]})

    def test_checksum_rejects_non_finite(self) -> None:
        from film_pipeline.artifacts.envelope import payload_checksum
        from film_pipeline.artifacts.serialization import NonFiniteNumberError

        with pytest.raises(NonFiniteNumberError):
            payload_checksum({"x": float("inf")})


class TestRendererRegistryOwnership:
    """The registry is the single map from kind to storage contract (plan D4/D9).

    The renderer table used to live in ``store.py`` keyed by a re-derived slug,
    duplicating registry knowledge and allowing the two to drift. These tests
    pin that the registry owns the mapping.
    """

    def test_registry_owns_renderer_lookup(self) -> None:
        from film_pipeline.artifacts.registry import REGISTRY
        from film_pipeline.artifacts.rendering import render_script

        spec = REGISTRY.spec_for("script")
        assert spec.renderer is render_script
        assert REGISTRY.renderer_for(spec.kind) is render_script

    def test_every_kind_is_looked_up_by_its_registry_key(self) -> None:
        """Each kind resolves through its own key, with no slug re-derivation."""
        from film_pipeline.artifacts.registry import REGISTRY

        for artifact_id in REGISTRY.known_ids():
            spec = REGISTRY.spec_for(artifact_id)
            assert REGISTRY.renderer_for(spec.kind) is spec.renderer

    def test_unregistered_renderer_key_falls_back(self) -> None:
        from film_pipeline.artifacts.registry import REGISTRY

        assert REGISTRY.renderer_for("film.studio/not-a-kind") is None


class TestStatusMachineIntegrity:
    """Only approve()/supersede() may move a version out of "current".

    A version being written becomes the current version, so accepting
    ``SUPERSEDED`` at save time would make the status field unable to
    distinguish a live current version from a historical one.
    """

    def test_save_rejects_superseded_status(self, tmp_path: Path) -> None:
        store = make_store(tmp_path / "store")
        with pytest.raises(ValueError, match="superseded"):
            store.save(_constitution(), _meta(status=ArtifactStatus.SUPERSEDED))

    def test_save_still_honors_pre_approved_status(self, tmp_path: Path) -> None:
        """Pre-approved writes (config snapshots) must keep working."""
        store = make_store(tmp_path / "store")
        store.save(_constitution(), _meta(status=ArtifactStatus.APPROVED))
        listed = store.list_artifacts("p1")
        assert [m.status for m in listed] == [ArtifactStatus.APPROVED]

    def test_approve_then_supersede_moves_status(self, tmp_path: Path) -> None:
        """The real transition path still works after the save-time guard."""
        store = make_store(tmp_path / "store")
        store.save(_constitution(), _meta())
        store.approve("p1", FilmPhase.CONSTITUTION.value, "film_constitution", 1)
        assert store.list_artifacts("p1")[0].status is ArtifactStatus.APPROVED
        store.supersede("p1", FilmPhase.CONSTITUTION.value, "film_constitution", 1)
        assert store.list_artifacts("p1")[0].status is ArtifactStatus.SUPERSEDED


class TestMutableRefRevisions:
    """A ref must identify what it names (plan D5).

    Mutable kinds keep one revision-counted file, so an older ref cannot be
    satisfied. It must fail loudly rather than silently returning the current
    content, which would answer a question the caller did not ask.
    """

    def _ledger_store(self, tmp_path: Path) -> tuple[ArtifactStore, ArtifactMetadata]:
        from film_pipeline.schemas.generation import GenerationLedger

        store = make_store(tmp_path / "store")
        meta = _meta(
            artifact_id="generation_ledger",
            artifact_type=ArtifactType.GENERATION_LEDGER,
            phase=FilmPhase.GEN_PLANNING,
        )
        store.save_mutable(GenerationLedger(project_id="p1"), meta)
        store.save_mutable(GenerationLedger(project_id="p1"), meta)
        return store, meta

    def test_current_revision_resolves(self, tmp_path: Path) -> None:
        store, _ = self._ledger_store(tmp_path)
        assert (
            store.load_ref("p1", "artifact:gen_planning:generation_ledger:v2")["project_id"] == "p1"
        )

    def test_stale_revision_raises_instead_of_substituting(self, tmp_path: Path) -> None:
        from film_pipeline.artifacts.envelope import MutableRevisionMismatchError

        store, _ = self._ledger_store(tmp_path)
        with pytest.raises(MutableRevisionMismatchError, match="revision 2"):
            store.load_ref("p1", "artifact:gen_planning:generation_ledger:v1")

    def test_load_envelope_agrees_with_load_ref(self, tmp_path: Path) -> None:
        """The two public read paths must not disagree about a mutable ref."""
        from film_pipeline.artifacts.envelope import MutableRevisionMismatchError

        store, _ = self._ledger_store(tmp_path)
        current = store.load_envelope("p1", FilmPhase.GEN_PLANNING, "generation_ledger", 2)
        assert current.version == 2
        with pytest.raises(MutableRevisionMismatchError):
            store.load_envelope("p1", FilmPhase.GEN_PLANNING, "generation_ledger", 1)


class TestAtomicDurability:
    """D6: every storage write is atomic and durable.

    The write helper must fsync the file contents AND the parent directory,
    otherwise a crash can lose the rename even though the bytes were flushed.
    """

    def test_atomic_write_fsyncs_file_and_parent_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import os

        from film_pipeline.artifacts import serialization

        synced: list[int] = []
        real_fsync = os.fsync

        def spy_fsync(fd: int) -> None:
            synced.append(fd)
            real_fsync(fd)

        monkeypatch.setattr(os, "fsync", spy_fsync)

        target = tmp_path / "nested" / "file.json"
        serialization.write_json_atomic(target, {"a": 1})
        assert target.exists()
        # One fsync for the temp file, one for the containing directory.
        assert len(synced) == 2

    def test_atomic_write_leaves_no_temp_files(self, tmp_path: Path) -> None:
        from film_pipeline.artifacts.serialization import write_json_atomic

        target = tmp_path / "out" / "file.json"
        write_json_atomic(target, {"a": 1})
        assert [p.name for p in target.parent.iterdir()] == ["file.json"]

    def test_manifest_write_is_atomic(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The asset manifest must not be written with a bare write_text."""
        from film_pipeline.artifacts import manifest as manifest_mod
        from film_pipeline.artifacts.manifest import AssetManifest, write_manifest

        calls: list[str] = []
        # Patch the name as ``manifest`` bound it, so the spy sees the call.
        real: Callable[[Path, object], None] = manifest_mod.write_json_atomic  # type: ignore[attr-defined]

        def spy(path: Path, obj: object) -> None:
            calls.append(str(path))
            real(path, obj)

        monkeypatch.setattr(manifest_mod, "write_json_atomic", spy)
        write_manifest(AssetManifest(project_id="p1"), tmp_path)
        assert calls and calls[0].endswith("asset-manifest.json")


class TestTypedArtifactIndex:
    """The derived index is a persisted boundary, so it validates both ways."""

    def test_index_rows_round_trip_through_the_model(self, tmp_path: Path) -> None:
        import json as _json

        from film_pipeline.artifacts.envelope import ArtifactIndex

        root = tmp_path / "store"
        store = make_store(root)
        store.save(_constitution(), _meta())

        raw = _json.loads((root / "p1" / "index" / "artifacts.json").read_text())
        index = ArtifactIndex.model_validate(raw)
        assert index.schema_version == 1
        assert [e.artifact_id for e in index.artifacts] == ["film_constitution"]
        entry = index.artifacts[0]
        assert entry.current_version == 1
        assert entry.status is ArtifactStatus.CANDIDATE
        assert entry.phase is FilmPhase.CONSTITUTION

    def test_index_stays_in_sync_with_list_artifacts(self, tmp_path: Path) -> None:
        """The derived cache must not drift from the authoritative read path."""
        import json as _json

        root = tmp_path / "store"
        store = make_store(root)
        store.save(_constitution(), _meta())
        store.save(
            Script(project_id="p1", title="T", scenes=[]),
            _meta(
                artifact_id="script",
                artifact_type=ArtifactType.SCRIPT,
                phase=FilmPhase.SCRIPT,
            ),
        )

        raw = _json.loads((root / "p1" / "index" / "artifacts.json").read_text())
        indexed = [(r["artifact_id"], r["current_version"]) for r in raw["artifacts"]]
        listed = [(m.artifact_id, m.version) for m in store.list_artifacts("p1")]
        assert indexed == listed
