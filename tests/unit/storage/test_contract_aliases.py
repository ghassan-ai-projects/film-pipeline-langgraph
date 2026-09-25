"""Artifact registry keeps the same identity rules after ownership moves."""

from film_pipeline.artifacts import registry
from film_pipeline.storage import contract


def test_artifact_id_rules_are_storage_contract_aliases() -> None:
    assert registry.ARTIFACT_ID_PATTERN is contract.ARTIFACT_ID_PATTERN
    assert registry.validate_artifact_id is contract.validate_artifact_id
    assert registry.sanitize_artifact_id is contract.sanitize_artifact_id
    assert registry.KindSpec is contract.KindSpec
