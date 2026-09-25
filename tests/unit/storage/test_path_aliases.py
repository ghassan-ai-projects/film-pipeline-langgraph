"""Artifact path imports remain aliases of the storage owner."""

from film_pipeline.artifacts import paths as legacy_paths
from film_pipeline.storage import paths


def test_artifact_path_aliases_keep_identity() -> None:
    assert legacy_paths.PHASE_DIR_MAP is paths.PHASE_DIR_MAP
    assert legacy_paths.project_dir is paths.project_dir
    assert legacy_paths.phase_dir is paths.phase_dir
    assert legacy_paths.media_scene_dir is paths.media_scene_dir
