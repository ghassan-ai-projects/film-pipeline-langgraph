"""One condition, one message.

"Which project am I acting on?" was checked at 45 call sites with three
different wordings and five different emptiness tests:

    if not active            x15   (falsy: rejects {} )
    if state is None         x11
    if project_id is None    x10
    if active is None        x7
    if resolved is None      x2

`if not active` and `if active is None` disagree on an empty dict, so the same
condition produced different answers depending on which site you hit. The
response is now built in one place.
"""

from __future__ import annotations

from film_pipeline.mcp.tools.helpers import (
    NO_ACTIVE_PROJECT,
    _no_active_project,
)


class TestNoActiveProject:
    def test_response_shape(self) -> None:
        assert _no_active_project() == {"ok": False, "error": NO_ACTIVE_PROJECT}

    def test_message_is_the_single_definition(self) -> None:
        assert _no_active_project()["error"] == NO_ACTIVE_PROJECT

    def test_response_is_an_error(self) -> None:
        assert _no_active_project()["ok"] is False


#: The one file allowed to phrase this condition differently, and why:
#: `explain_agent_routing` returns **success** with a message, because "no
#: active project" is a valid empty answer for session-scoped routing data —
#: it is not a failure. Everywhere else the condition is an error.
_ALLOWED = {"helpers.py", "audit.py"}


def test_no_module_builds_the_error_message_inline() -> None:
    """The wording must not be re-derived anywhere in the tool tree."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[4] / "src" / "film_pipeline" / "mcp" / "tools"
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "No active project" in text and path.name not in _ALLOWED:
            offenders.append(str(path.relative_to(root)))
    assert offenders == [], f"inline 'No active project' message: {offenders}"


def test_helpers_is_the_only_definition() -> None:
    from pathlib import Path

    helpers = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "film_pipeline"
        / "mcp"
        / "tools"
        / "helpers.py"
    )
    text = helpers.read_text(encoding="utf-8")
    assert text.count('NO_ACTIVE_PROJECT = "No active project."') == 1
