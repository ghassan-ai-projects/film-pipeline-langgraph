"""Tests for artifact manifest read/write."""

from __future__ import annotations

import tempfile
from pathlib import Path

from film_pipeline.artifacts.manifest import (
    AssetEntry,
    AssetManifest,
    read_manifest,
    write_manifest,
)


class TestAssetEntry:
    def test_create(self) -> None:
        entry = AssetEntry(
            asset_id="asset:clip:S001:v1",
            path="output/S001.mp4",
            kind="generated_clip",
            scene_id="SC_001",
            shot_id="S001",
        )
        assert entry.asset_id == "asset:clip:S001:v1"
        assert entry.kind == "generated_clip"
        assert entry.scene_id == "SC_001"
        assert entry.shot_id == "S001"
        assert entry.active is True


class TestAssetManifest:
    def test_add_and_get(self) -> None:
        manifest = AssetManifest(project_id="p1")
        entry = AssetEntry(
            asset_id="asset:clip:S001:v1",
            path="output/S001.mp4",
            kind="generated_clip",
            shot_id="S001",
        )
        manifest.add(entry)
        assert len(manifest.entries) == 1

    def test_active_take(self) -> None:
        manifest = AssetManifest(project_id="p1")
        active = AssetEntry(
            asset_id="a1", path="p", kind="generated_clip", shot_id="S001", active=True
        )
        inactive = AssetEntry(
            asset_id="a2", path="p", kind="generated_clip", shot_id="S001", active=False
        )
        manifest.add(active)
        manifest.add(inactive)

        found = manifest.active_take("S001")
        assert found is not None
        assert found.asset_id == "a1"

    def test_active_take_none(self) -> None:
        manifest = AssetManifest(project_id="p1")
        assert manifest.active_take("nonexistent") is None

    def test_list_by_kind(self) -> None:
        manifest = AssetManifest(project_id="p1")
        manifest.add(AssetEntry(asset_id="a1", path="p", kind="generated_clip"))
        manifest.add(AssetEntry(asset_id="a2", path="p", kind="last_frame"))
        manifest.add(AssetEntry(asset_id="a3", path="p", kind="generated_clip"))
        clips = manifest.list_by_kind("generated_clip")
        assert len(clips) == 2

    def test_list_by_scene_and_shot(self) -> None:
        manifest = AssetManifest(project_id="p1")
        manifest.add(
            AssetEntry(
                asset_id="a1",
                path="p",
                kind="generated_clip",
                scene_id="SC_001",
                shot_id="shot_001",
            )
        )
        manifest.add(
            AssetEntry(
                asset_id="a2",
                path="p",
                kind="generated_clip",
                scene_id="SC_002",
                shot_id="shot_002",
            )
        )

        assert [entry.asset_id for entry in manifest.list_by_scene("SC_001")] == ["a1"]
        assert [entry.asset_id for entry in manifest.list_by_shot("shot_002")] == ["a2"]


class TestManifestIO:
    def test_write_and_read(self) -> None:
        manifest = AssetManifest(project_id="test_project")
        manifest.add(AssetEntry(asset_id="a1", path="p1", kind="generated_clip"))
        manifest.add(AssetEntry(asset_id="a2", path="p2", kind="last_frame"))

        with tempfile.TemporaryDirectory() as tmpdir:
            write_manifest(manifest, root=Path(tmpdir))
            loaded = read_manifest("test_project", root=Path(tmpdir))
            assert loaded is not None
            assert loaded.project_id == "test_project"
            assert len(loaded.entries) == 2

    def test_read_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = read_manifest("nonexistent", root=Path(tmpdir))
            assert result is None
