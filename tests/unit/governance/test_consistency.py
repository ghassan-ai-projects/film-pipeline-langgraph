"""Direct tests for the artifact staleness checks.

The consistency node is covered end-to-end elsewhere, but its defensive
branches are not: a malformed ref, a missing artifact, and a store that cannot
answer all return silently rather than raising. That silence is the point of
the module — a consistency check must never break the phase it is inspecting —
so each branch is pinned here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from film_pipeline.governance.consistency import (
    _staleness_warnings,
    check_staleness,
)


class _FakeStore:
    """Minimal store surface used by ``check_staleness``."""

    def __init__(self, metadata: Any = None, error: Exception | None = None) -> None:
        self._metadata = metadata
        self._error = error
        self.calls: list[tuple[str, str, str, object]] = []

    def load_metadata(self, project_id: str, phase: str, artifact_id: str, version: str) -> Any:
        self.calls.append((project_id, phase, artifact_id, version))
        if self._error is not None:
            raise self._error
        return self._metadata


class TestStalenessWarnings:
    def test_no_built_from_yields_no_warnings(self) -> None:
        assert _staleness_warnings("a", "ref", {}, {}) == []

    def test_matching_ref_is_not_stale(self) -> None:
        warnings = _staleness_warnings(
            "manifest",
            "artifact:post:manifest:v1",
            {"script": "artifact:script:s:v1"},
            {"script": "artifact:script:s:v1"},
        )
        assert warnings == []

    def test_dependency_without_approval_is_ignored(self) -> None:
        """An unapproved dependency has no current version to compare against."""
        warnings = _staleness_warnings(
            "manifest",
            "artifact:post:manifest:v1",
            {"script": "artifact:script:s:v1"},
            {},
        )
        assert warnings == []

    def test_divergent_ref_is_reported_with_both_versions(self) -> None:
        warnings = _staleness_warnings(
            "manifest",
            "artifact:post:manifest:v1",
            {"script": "artifact:script:s:v1"},
            {"script": "artifact:script:s:v2"},
        )
        assert len(warnings) == 1
        warning = warnings[0]
        assert warning["severity"] == "stale"
        assert warning["built_with_version"] == "artifact:script:s:v1"
        assert warning["current_version"] == "artifact:script:s:v2"
        assert "script" in warning["message"]


class TestCheckStalenessDefensiveBranches:
    def test_malformed_ref_returns_no_warnings(self) -> None:
        """A ref the schema cannot parse is skipped, not raised."""
        store = _FakeStore()
        assert check_staleness("not-a-valid-ref", {"project_id": "p1"}, store) == []
        assert store.calls == [], "the store must not be consulted for a bad ref"

    def test_missing_artifact_returns_no_warnings(self) -> None:
        store = _FakeStore(error=FileNotFoundError("gone"))
        assert check_staleness("artifact:script:S001:v1", {"project_id": "p1"}, store) == []

    def test_store_value_error_returns_no_warnings(self) -> None:
        store = _FakeStore(error=ValueError("bad metadata"))
        assert check_staleness("artifact:script:S001:v1", {"project_id": "p1"}, store) == []

    def test_absent_metadata_returns_no_warnings(self) -> None:
        store = _FakeStore(metadata=None)
        assert check_staleness("artifact:script:S001:v1", {"project_id": "p1"}, store) == []

    def test_metadata_without_built_from_is_tolerated(self) -> None:
        class _Meta:
            def __init__(self) -> None:
                self.built_from: dict[str, str] | None = None

        store = _FakeStore(metadata=_Meta())
        assert check_staleness("artifact:script:S001:v1", {"project_id": "p1"}, store) == []

    def test_project_id_is_taken_from_state(self) -> None:
        class _Meta:
            def __init__(self) -> None:
                self.built_from: dict[str, str] = {}

        store = _FakeStore(metadata=_Meta())
        check_staleness("artifact:script:S001:v1", {"project_id": "proj-9"}, store)
        # ``ArtifactRef.from_string`` parses the version to an int.
        assert store.calls == [("proj-9", "script", "S001", 1)]

    def test_empty_project_id_is_passed_through(self, tmp_path: Path) -> None:
        """A state without a project id still resolves without raising."""
        store = _FakeStore(error=FileNotFoundError("gone"))
        assert check_staleness("artifact:script:S001:v1", {}, store) == []
        assert store.calls[0][0] == ""
