"""The production-root guard actually detects a write.

`conftest._production_roots_untouched` protects the user's real storage roots
by snapshotting them before the session and asserting nothing changed after.
A guard that silently stops detecting is worse than no guard, so this verifies
the detection by exercising the snapshot/compare logic against a temporary
tree — the same code path, isolated from any real root.

An earlier version of this file wrote a canary file *into* `.film-pipeline-run`
and relied on the session guard to fail. That passed only on a machine where
the file already existed from a previous run: the before/after snapshots then
matched and the guard stayed quiet. On a fresh checkout the write was a genuine
addition, so the guard tripped — and reported the violation against whichever
four tests happened to be finishing at session teardown rather than against the
cause. It was also self-defeating: a canary that permanently pollutes a watched
root makes the guard it tests unfalsifiable on every later run.
"""

from __future__ import annotations

from pathlib import Path

from tests.conftest import _snapshot_tree

_GUARD_SOURCE = Path(__file__).resolve().parents[1] / "conftest.py"


def _diff(before: dict[str, int] | None, after: dict[str, int] | None) -> list[str]:
    """Mirror the comparison the session guard performs."""
    if after == before:
        return []
    old = before or {}
    new = after or {}
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    resized = sorted(key for key in set(old) & set(new) if old[key] != new[key])
    return [f"added={added} removed={removed} resized={resized}"]


class TestGuardDetectsChanges:
    def test_an_added_file_is_a_violation(self, tmp_path: Path) -> None:
        root = tmp_path / "watched"
        root.mkdir()
        before = _snapshot_tree(root)
        (root / "CANARY.txt").write_text("canary")
        assert _diff(before, _snapshot_tree(root)) != []

    def test_an_added_directory_is_a_violation(self, tmp_path: Path) -> None:
        """Directory creation alone counts: size 0 is still a change."""
        root = tmp_path / "watched"
        root.mkdir()
        before = _snapshot_tree(root)
        (root / "new-dir").mkdir()
        assert _diff(before, _snapshot_tree(root)) != []

    def test_a_resized_file_is_a_violation(self, tmp_path: Path) -> None:
        root = tmp_path / "watched"
        root.mkdir()
        target = root / "existing.txt"
        target.write_text("one")
        before = _snapshot_tree(root)
        target.write_text("one and more")
        assert _diff(before, _snapshot_tree(root)) != []

    def test_a_removed_file_is_a_violation(self, tmp_path: Path) -> None:
        root = tmp_path / "watched"
        root.mkdir()
        target = root / "existing.txt"
        target.write_text("one")
        before = _snapshot_tree(root)
        target.unlink()
        assert _diff(before, _snapshot_tree(root)) != []


class TestGuardStaysQuiet:
    def test_an_untouched_tree_is_not_a_violation(self, tmp_path: Path) -> None:
        root = tmp_path / "watched"
        root.mkdir()
        (root / "existing.txt").write_text("one")
        before = _snapshot_tree(root)
        assert _diff(before, _snapshot_tree(root)) == []

    def test_an_absent_root_is_not_a_violation(self, tmp_path: Path) -> None:
        """A root that never existed cannot have been written to."""
        assert _diff(_snapshot_tree(tmp_path / "absent"), _snapshot_tree(tmp_path / "absent")) == []

    def test_log_appends_are_ignored(self, tmp_path: Path) -> None:
        """A live server may legitimately append to its own logs."""
        root = tmp_path / "watched"
        logs = root / "logs"
        logs.mkdir(parents=True)
        log = logs / "server.log"
        log.write_text("start\n")
        before = _snapshot_tree(root)
        log.write_text("start\nmore\n")
        assert _diff(before, _snapshot_tree(root)) == []


def test_the_session_guard_still_uses_this_logic() -> None:
    """If the guard stops comparing snapshots, this canary proves nothing."""
    source = _GUARD_SOURCE.read_text(encoding="utf-8")
    assert "def _production_roots_untouched" in source
    assert "_snapshot_tree(path)" in source
    assert "Test run touched production storage roots" in source
