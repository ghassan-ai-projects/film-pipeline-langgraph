"""Project gallery / home screen for the film studio TUI."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from film_pipeline.app.services.models import ProjectListItem
from film_pipeline.tui.widgets.project_form import ProjectForm


class ProjectGalleryScreen(Screen[None]):
    """First screen: list projects and create new ones."""

    CSS = """
    #home_container {
        align: center middle;
        padding: 2 4;
    }

    #home_header {
        height: auto;
        content-align: center middle;
        text-align: center;
    }

    #home_title {
        text-style: bold;
        color: #88c0d0;
        text-align: center;
        width: 100%;
    }

    #home_subtitle {
        color: #6b7480;
        text-align: center;
        width: 100%;
    }

    #home_actions {
        height: auto;
        align: center middle;
        margin: 1 0;
    }

    #home_actions Button {
        margin: 0 1;
    }

    #project_table {
        height: 1fr;
        border: solid #3b4252;
    }

    #project_filter {
        height: auto;
        margin: 1 0 0 0;
    }

    #empty_state {
        text-align: center;
        color: #6b7480;
        height: 1fr;
        content-align: center middle;
    }
    """

    BINDINGS: ClassVar = []

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._projects: list[ProjectListItem] = []
        self._filter = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="home_container"):
            yield Static("LANGGRAPH FILM STUDIO", id="home_title")
            yield Static("Pick a project or start a new film.", id="home_subtitle")
            with Horizontal(id="home_actions"):
                yield Button("New Project", id="new_project", variant="primary")
                yield Button("Refresh", id="refresh")
            yield Input(placeholder="Filter projects...", id="project_filter")
            yield DataTable(id="project_table")
            yield Static("No projects yet. Click New Project to create one.", id="empty_state")
        yield Static("", id="status_footer")
        yield Input(
            placeholder="Command palette: try 'next', 'approve', 'validate', 'project <id>'",
            id="command_palette",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#project_table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        self._refresh_view()
        from film_pipeline.tui.app import FilmStudioApp

        if isinstance(self.app, FilmStudioApp):
            self.app.action_refresh()

    def update_state(self, app_state: object) -> None:
        """Refresh the project list from the parent app state."""
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        if state is None or state.snapshot is None:
            self._projects = []
        else:
            self._projects = list(state.snapshot.projects)
        self._refresh_view()

    def _visible_projects(self) -> list[ProjectListItem]:
        """Projects matching the current filter, in display order."""
        if not self._filter:
            return list(self._projects)
        needle = self._filter.lower()
        return [
            project
            for project in self._projects
            if needle in project.project_id.lower() or needle in project.title.lower()
        ]

    def _refresh_view(self) -> None:
        table = self.query_one("#project_table", DataTable)
        table.clear(columns=True)
        visible = self._visible_projects()
        empty = self.query_one("#empty_state", Static)
        if not visible:
            empty.styles.display = "block"
            table.styles.display = "none"
        else:
            empty.styles.display = "none"
            table.styles.display = "block"
            table.add_columns("Project", "Phase", "Status", "Mode")
            for project in visible:
                kind = project.project_kind or "production"
                table.add_row(
                    f"{project.title} ({project.project_id})",
                    project.current_phase or "—",
                    project.status,
                    kind,
                )

    def action_new_project(self) -> None:
        """Open the new project modal form."""
        self.app.push_screen(ProjectForm(), self._on_project_form_result)

    def _on_project_form_result(self, request: object) -> None:
        from film_pipeline.app.services.models import ProjectCreateRequest
        from film_pipeline.tui.app import FilmStudioApp

        if not isinstance(request, ProjectCreateRequest):
            return
        if isinstance(self.app, FilmStudioApp):
            self.app.create_project(request)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new_project":
            self.action_new_project()
        elif event.button.id == "refresh" and hasattr(self.app, "action_refresh"):
            self.app.action_refresh()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "project_filter":
            self._filter = event.value
            self._refresh_view()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "project_table":
            return
        visible = self._visible_projects()
        if event.cursor_row < 0 or event.cursor_row >= len(visible):
            return
        project = visible[event.cursor_row]
        from film_pipeline.tui.app import FilmStudioApp

        if isinstance(self.app, FilmStudioApp):
            self.app.open_project(project.project_id)
