"""Terminal operator console.

Run with:

```
python -m film_pipeline.tui.app
```
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from film_pipeline.app.services.errors import ServiceError
from film_pipeline.app.services.models import ProjectCreateRequest
from film_pipeline.tui.formatting import pretty, table, title
from film_pipeline.tui.gateway import StudioGateway
from film_pipeline.tui.gateways import InProcessStudioGateway


class OperatorConsole:
    """Keyboard-first terminal shell for the film pipeline."""

    def __init__(
        self,
        gateway: StudioGateway | None = None,
        *,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
    ) -> None:
        self.gateway = gateway or InProcessStudioGateway()
        self._input = input_func
        self._output = output_func
        self._active_project_id = ""

    def run(self) -> int:
        """Run the interactive console loop."""
        self._output(title("LangGraph Film Studio"))
        self._output("Operator console. Choose an action number, or q to quit.")
        while True:
            self._output(self._menu())
            choice = self._input("> ").strip().lower()
            if choice in {"q", "quit", "exit"}:
                return 0
            self._dispatch(choice)

    def create_project_from_values(
        self,
        *,
        project_id: str,
        title_text: str,
        slug: str,
        idea: str,
        runtime_mode: str = "mock",
        workflow_mode: str = "manual",
    ) -> None:
        """Create a project from explicit values.

        This method supports both the interactive flow and unit tests.
        """
        request = ProjectCreateRequest(
            project_id=project_id,
            title=title_text,
            slug=slug,
            idea=idea,
            runtime_mode=runtime_mode,
            workflow_mode=workflow_mode,
        )
        result = self.gateway.create_project(request)
        self._active_project_id = result.project_id
        self._output(f"Created project {result.project_id}; phase={result.current_phase or 'none'}")

    def _dispatch(self, choice: str) -> None:
        try:
            actions: dict[str, Callable[[], None]] = {
                "1": self._create_project_interactive,
                "2": self._select_project_interactive,
                "3": self._show_dashboard,
                "4": self._show_review,
                "5": self._approve_phase,
                "6": self._request_revision_interactive,
                "7": self._show_validation,
                "8": self._list_artifacts,
                "9": self._inspect_artifact_interactive,
                "10": self._list_checkpoints,
                "11": self._list_providers,
                "12": self._show_audit,
                "13": self._submit_idea_interactive,
            }
            action = actions.get(choice)
            if action is None:
                self._output("Unknown action.")
                return
            action()
        except (ServiceError, ValueError, FileNotFoundError) as exc:
            self._output(f"Error: {exc}")

    def _menu(self) -> str:
        active = self._active_project_id or "none"
        return "\n".join(
            [
                "",
                f"Active project: {active}",
                "1. New project from idea",
                "2. Select project",
                "3. Dashboard",
                "4. Review workspace",
                "5. Approve phase",
                "6. Request revision",
                "7. Validation",
                "8. List artifacts",
                "9. Inspect artifact",
                "10. Checkpoints",
                "11. Providers",
                "12. Audit",
                "13. Submit idea to active project",
                "q. Quit",
            ]
        )

    def _create_project_interactive(self) -> None:
        self._output(title("New Project"))
        project_id = self._input("project id: ").strip()
        title_text = self._input("title: ").strip()
        slug = self._input("slug [project id]: ").strip()
        runtime_mode = self._input("runtime mode [mock]: ").strip() or "mock"
        workflow_mode = self._input("workflow mode [manual]: ").strip() or "manual"
        idea = self._input("idea: ").strip()
        self.create_project_from_values(
            project_id=project_id,
            title_text=title_text,
            slug=slug,
            idea=idea,
            runtime_mode=runtime_mode,
            workflow_mode=workflow_mode,
        )
        self._show_dashboard()

    def _select_project_interactive(self) -> None:
        projects = self.gateway.list_projects()
        self._output(title("Projects"))
        self._output(
            table(
                [project.__dict__ for project in projects],
                ["project_id", "title", "current_phase", "status", "awaiting_review"],
            )
        )
        project_id = self._input("project id: ").strip()
        dashboard = self.gateway.set_active_project(project_id)
        self._active_project_id = dashboard.project_id
        self._output(f"Selected {dashboard.project_id}.")

    def _show_dashboard(self) -> None:
        dashboard = self.gateway.get_dashboard(self._project_ref())
        self._active_project_id = dashboard.project_id
        self._output(title("Dashboard"))
        self._output(
            table(
                [
                    {
                        "project": dashboard.project_id,
                        "phase": dashboard.current_phase,
                        "status": dashboard.status,
                        "runtime": dashboard.runtime_mode,
                        "workflow": dashboard.workflow_mode,
                        "next_action": dashboard.next_action,
                    }
                ],
                ["project", "phase", "status", "runtime", "workflow", "next_action"],
            )
        )
        if dashboard.route_reason:
            self._output(f"\nRoute reason: {dashboard.route_reason}")
        self._output(
            f"Artifacts: {dashboard.artifact_count}  "
            f"Checkpoints: {dashboard.checkpoint_count}  "
            f"Issues: {dashboard.issue_count}"
        )
        if dashboard.blocked_actions:
            self._output("\nBlocked actions:")
            self._output(pretty(dashboard.blocked_actions))

    def _show_review(self) -> None:
        review = self.gateway.get_review_workspace(self._project_ref())
        self._output(title("Review"))
        self._output(f"Phase: {review.phase or 'none'}")
        self._output(f"Recommendation: {review.recommendation}")
        self._output("\nArtifacts:")
        self._output(
            table(
                review.candidate_artifacts,
                ["artifact_id", "artifact_type", "phase", "version", "status"],
            )
        )
        if review.open_issues:
            self._output("\nOpen blocking issues:")
            for issue in review.open_issues:
                self._output(f"- {issue}")

    def _approve_phase(self) -> None:
        dashboard = self.gateway.get_dashboard(self._project_ref())
        if not self._confirm(
            f"Approve phase '{dashboard.current_phase}' for project '{dashboard.project_id}'?"
        ):
            self._output("Approval cancelled.")
            return
        result = self.gateway.approve_phase(self._project_ref())
        self._active_project_id = result.project_id
        self._output(f"{result.message} Current phase: {result.current_phase}")

    def _request_revision_interactive(self) -> None:
        note = self._input("revision note: ").strip()
        if not self._confirm("Submit revision request?"):
            self._output("Revision request cancelled.")
            return
        result = self.gateway.request_revision(note, self._project_ref())
        self._active_project_id = result.project_id
        self._output(f"{result.message} Current phase: {result.current_phase}")

    def _submit_idea_interactive(self) -> None:
        idea = self._input("idea: ").strip()
        project_id = self._project_ref()
        if project_id is None:
            self._output("Error: select or create a project first.")
            return
        result = self.gateway.submit_idea(project_id, idea)
        self._active_project_id = result.project_id
        self._output(f"{result.message} Current phase: {result.current_phase}")

    def _show_validation(self) -> None:
        workspace = self.gateway.get_validation_workspace(self._project_ref())
        self._output(title("Validation"))
        self._output(
            table(
                [
                    {
                        "project": workspace.project_id,
                        "phase": workspace.phase or "none",
                        "source": workspace.source,
                        "reports": len(workspace.reports),
                        "blocking": len(workspace.blocking_issues),
                        "non_blocking": len(workspace.non_blocking_issues),
                    }
                ],
                ["project", "phase", "source", "reports", "blocking", "non_blocking"],
            )
        )
        if workspace.reports:
            self._output("\nReports:")
            self._output(pretty(workspace.reports))
        if workspace.blocking_issues:
            self._output("\nBlocking issues:")
            self._output(pretty(workspace.blocking_issues))
        if workspace.non_blocking_issues:
            self._output("\nWarnings and info:")
            self._output(pretty(workspace.non_blocking_issues))

    def _list_artifacts(self) -> None:
        artifacts = self.gateway.list_artifacts(self._project_ref())
        self._output(title("Artifacts"))
        self._output(
            table(artifacts, ["artifact_id", "artifact_type", "phase", "version", "status"])
        )

    def _inspect_artifact_interactive(self) -> None:
        artifact_id = self._input("artifact id: ").strip()
        phase = self._input("phase: ").strip()
        version_raw = self._input("version [1]: ").strip() or "1"
        artifact = self.gateway.inspect_artifact(
            artifact_id,
            phase,
            int(version_raw),
            self._project_ref(),
        )
        self._output(title(f"Artifact {artifact.artifact_id}"))
        self._output(pretty(artifact.body))

    def _list_checkpoints(self) -> None:
        checkpoints = self.gateway.list_checkpoints(self._project_ref())
        self._output(title("Checkpoints"))
        self._output(table(checkpoints, ["checkpoint_id", "phase", "reason", "created_at"]))

    def _list_providers(self) -> None:
        providers = self.gateway.list_provider_status()
        self._output(title("Providers"))
        if not providers:
            self._output("No provider health records.")
            return
        self._output(table(providers, ["provider_id", "status", "reason"]))

    def _show_audit(self) -> None:
        events = self.gateway.get_audit_feed(self._project_ref(), limit=20)
        self._output(title("Audit"))
        self._output(
            table(
                [event.__dict__ for event in events],
                ["timestamp", "actor", "action", "target", "summary"],
            )
        )

    def _project_ref(self) -> str | None:
        return self._active_project_id or None

    def _confirm(self, prompt: str) -> bool:
        answer = self._input(f"{prompt} [y/N] ").strip().lower()
        return answer in {"y", "yes"}


def main(argv: list[str] | None = None) -> int:
    """Entry point for the TUI."""
    parser = argparse.ArgumentParser(description="Run the film pipeline terminal UI.")
    parser.add_argument("--create", action="store_true", help="Start in the project creation flow.")
    args = parser.parse_args(argv)
    console = OperatorConsole()
    if args.create:
        console._create_project_interactive()
    return console.run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
