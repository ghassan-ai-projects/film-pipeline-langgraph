"""Base Textual app shell: CSS, bindings, compose, and table plumbing."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Header, Input, Static, TabbedContent, TabPane

from film_pipeline.app.services.models import ArtifactDetail
from film_pipeline.tui.app_base import AppCockpitBase
from film_pipeline.tui.formatting import pretty
from film_pipeline.tui.gateway import StudioGateway
from film_pipeline.tui.gateways import default_gateway
from film_pipeline.tui.view_models import (
    CockpitSnapshot,
    MatrixImpact,
    ReaderView,
    TargetSelection,
)


class AppShell(AppCockpitBase):
    """Bloomberg-style terminal cockpit shell: layout, CSS, and table helpers."""

    CSS = """
    Screen {
        background: #06080a;
        color: #d8dee9;
    }

    #shell {
        height: 1fr;
    }

    #project_rail {
        width: 28;
        border: solid #2e3440;
        padding: 0 1;
    }

    #workspace {
        width: 1fr;
        border: solid #3b4252;
    }

    #context_drawer {
        width: 34;
        border: solid #2e3440;
        padding: 0 1;
    }

    #dashboard_top {
        height: 7;
    }

    #dashboard_summary {
        width: 1fr;
    }

    #attention_panel {
        width: 1fr;
    }

    #dashboard_ops {
        height: 1fr;
    }

    #dashboard_kpi_table {
        width: 35%;
    }

    #dashboard_action_table {
        width: 65%;
    }

    #asset_ops {
        height: 13;
    }

    #asset_table {
        width: 45%;
    }

    #asset_action_table {
        width: 55%;
    }

    #reader_ops {
        height: 1fr;
    }

    #reader_index_table {
        width: 35%;
    }

    #reader_body_stack {
        width: 65%;
    }

    #reader_body {
        height: 1fr;
    }

    .panel {
        border: solid #3b4252;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    .headline {
        color: #88c0d0;
        text-style: bold;
    }

    .danger {
        color: #bf616a;
    }

    .warn {
        color: #ebcb8b;
    }

    .ok {
        color: #a3be8c;
    }

    DataTable {
        height: 1fr;
    }

    #comment_input {
        height: 3;
    }

    #review_main {
        height: 1fr;
    }

    #review_reading {
        width: 60%;
        border: solid #3b4252;
        padding: 0 1;
    }

    #review_side {
        width: 40%;
    }

    #review_side #review_checklist_table {
        height: 8;
    }

    #review_side #comment_thread_table {
        height: 8;
    }

    #generation_buttons {
        height: 3;
    }

    #generation_buttons Button {
        margin: 0 1 0 0;
    }

    #generation_summary {
        height: 5;
    }

    #generation_detail {
        height: 12;
    }

    #command_palette {
        dock: bottom;
        display: none;
    }

    #command_palette.open {
        display: block;
    }
    """

    BINDINGS: ClassVar = [
        # Number keys switch workspaces; letters are actions. (In Textual a
        # comma inside one Binding means alternative keys, not a chord, so
        # tab navigation must not reuse action letters.)
        Binding("1", "open_tab('dashboard')", "Dash", show=False),
        Binding("2", "open_tab('review')", "Review", show=False),
        Binding("3", "open_tab('generate')", "Generate", show=False),
        Binding("4", "open_tab('scenes')", "Scenes", show=False),
        Binding("5", "open_tab('assets')", "Assets", show=False),
        Binding("6", "open_tab('matrix')", "Matrix", show=False),
        Binding("7", "open_tab('guide')", "Guide", show=False),
        Binding("8", "open_tab('validation')", "Validation", show=False),
        Binding("9", "open_tab('ops')", "Ops", show=False),
        Binding("n", "new_project", "New"),
        Binding("i", "revise_idea", "Idea"),
        Binding("a", "approve_phase", "Approve"),
        Binding("y", "confirm_approval", "Confirm"),
        Binding("r", "request_revision", "Revise"),
        Binding("G", "run_generation", "Generate"),
        Binding("V", "run_validation", "Validate"),
        Binding("c", "add_comment", "Comment"),
        Binding("/", "toggle_command_palette", "Command"),
        Binding("f5", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        gateway: StudioGateway | None = None,
        *,
        start_create: bool = False,
    ) -> None:
        super().__init__()
        self.gateway = gateway or default_gateway()
        self.start_create = start_create
        self.active_project_id = ""
        self.snapshot: CockpitSnapshot | None = None
        self.selected_artifact: ArtifactDetail | None = None
        self.reader: ReaderView | None = None
        self.selected_target: TargetSelection | None = None
        self.matrix_filter = ""
        self.project_filter = "production"
        self._matrix_pivot = "status"
        self.matrix_impact: MatrixImpact | None = None
        self.pending_confirmation = ""
        self.busy_label = ""
        self._table_rows: dict[str, list[dict[str, object]]] = {}

    def compose(self) -> ComposeResult:
        """Compose the persistent cockpit shell."""
        yield Header(show_clock=True)
        with Horizontal(id="shell"):
            with Vertical(id="project_rail"):
                yield Static("Projects", classes="headline")
                yield Static("", id="project_filter", classes="panel")
                yield DataTable(id="project_table")
                yield Button("New Project", id="new_project", variant="primary")
                yield Button("Revise Idea", id="revise_idea_button")
                yield Button("Refresh", id="refresh_button")
            with Vertical(id="workspace"):
                yield Static("", id="status_bar", classes="panel")
                with TabbedContent(initial="dashboard", id="tabs"):
                    with TabPane("Dashboard", id="dashboard"):
                        with Horizontal(id="dashboard_top"):
                            yield Static("", id="dashboard_summary", classes="panel")
                            yield Static("", id="attention_panel", classes="panel")
                        with Horizontal(id="dashboard_ops"):
                            yield DataTable(id="dashboard_kpi_table")
                            yield DataTable(id="dashboard_action_table")
                        yield Static("Pipeline", classes="headline")
                        yield DataTable(id="graph_table")
                        yield Static("", id="graph_phase_detail", classes="panel")
                    with TabPane("Review", id="review"):
                        yield Static("", id="review_summary", classes="panel")
                        with Horizontal(id="review_main"):
                            with VerticalScroll(id="review_reading"):
                                yield Static("", id="review_reading_body")
                            with Vertical(id="review_side"):
                                yield DataTable(id="review_checklist_table")
                                yield DataTable(id="review_issue_table")
                                yield Static("Comment Threads", classes="headline")
                                yield DataTable(id="comment_thread_table")
                        yield Input(
                            placeholder="Comment on selected scene/artifact/issue, then press r",
                            id="comment_input",
                        )
                        with Horizontal():
                            yield Button("Add Comment", id="comment_button", variant="primary")
                            yield Button("Approve Phase", id="approve_button", variant="success")
                            yield Button(
                                "Confirm Approval",
                                id="confirm_approve_button",
                                variant="success",
                            )
                            yield Button(
                                "Request Revision",
                                id="revision_button",
                                variant="warning",
                            )
                    with TabPane("Generate", id="generate"):
                        yield Static("", id="generation_summary", classes="panel")
                        with Horizontal(id="generation_buttons"):
                            yield Button("Run Generation", id="gen_run_button", variant="primary")
                            yield Button("Plan Shots", id="gen_plan_button")
                            yield Button("Approve Spend", id="gen_spend_button")
                            yield Button("Start Batch", id="gen_start_button")
                            yield Button("Poll Status", id="gen_poll_button")
                        yield DataTable(id="generation_table")
                        yield Static("", id="generation_detail", classes="panel")
                    with TabPane("Scenes", id="scenes"):
                        yield Static("", id="scene_summary", classes="panel")
                        yield DataTable(id="scene_table")
                        yield Static("", id="scene_reader", classes="panel")
                    with TabPane("Assets", id="assets"):
                        with Horizontal(id="asset_ops"):
                            yield DataTable(id="asset_table")
                            yield DataTable(id="asset_action_table")
                        yield Static("", id="reader_title", classes="panel")
                        with Horizontal(id="reader_ops"):
                            yield DataTable(id="reader_index_table")
                            with Vertical(id="reader_body_stack"):
                                yield Static("", id="reader_outline", classes="panel")
                                yield Static("", id="reader_body", classes="panel")
                                yield Static("", id="reader_metadata", classes="panel")
                        yield DataTable(id="reader_link_table")
                        yield Static("", id="reader_links", classes="panel")
                    with TabPane("Matrix", id="matrix"):
                        yield Static("Smart Matrix", classes="headline")
                        yield Static("", id="matrix_summary", classes="panel")
                        yield DataTable(id="matrix_pivot_table")
                        yield DataTable(id="matrix_table")
                    with TabPane("Guide", id="guide"):
                        yield Static("1 Minute Movie Guide", classes="headline")
                        yield Static("", id="guide_summary", classes="panel")
                        yield DataTable(id="guide_table")
                        yield Static("", id="guide_detail", classes="panel")
                    with TabPane("Validation", id="validation"):
                        yield Static("", id="validation_summary", classes="panel")
                        yield Static("", id="validation_intelligence", classes="panel")
                        yield Button(
                            "Run Validation",
                            id="run_validation_button",
                            variant="primary",
                        )
                        yield DataTable(id="validation_group_table")
                        yield DataTable(id="validation_fix_table")
                        yield DataTable(id="validation_table")
                    with TabPane("Ops", id="ops"):
                        yield Static("Providers", classes="headline")
                        yield DataTable(id="provider_table")
                        yield Static("Checkpoint Timeline", classes="headline")
                        yield DataTable(id="checkpoint_table")
                        yield Static("Recent Audit Events", classes="headline")
                        yield DataTable(id="audit_table")
            with VerticalScroll(id="context_drawer"):
                yield Static("Context", classes="headline")
                yield Static("", id="context_panel")
                yield Static("", id="command_options", classes="panel")
                yield Static("", id="command_validation", classes="panel")
                yield Static("Command Suggestions", classes="headline")
                yield DataTable(id="command_suggestion_table")
                yield Static("Command Help", classes="headline")
                yield DataTable(id="command_help_table")
        yield Input(
            placeholder="Command palette: try 'open review', 'show blocked', 'artifact <id>'",
            id="command_palette",
        )
        yield Footer()

    def _initialize_tables(self) -> None:
        for selector in (
            "#project_table",
            "#dashboard_kpi_table",
            "#dashboard_action_table",
            "#graph_table",
            "#generation_table",
            "#matrix_table",
            "#matrix_pivot_table",
            "#review_checklist_table",
            "#review_issue_table",
            "#scene_table",
            "#asset_table",
            "#asset_action_table",
            "#guide_table",
            "#reader_index_table",
            "#reader_link_table",
            "#validation_table",
            "#validation_group_table",
            "#validation_fix_table",
            "#checkpoint_table",
            "#provider_table",
            "#audit_table",
            "#comment_thread_table",
            "#command_suggestion_table",
            "#command_help_table",
        ):
            table = self.query_one(selector, DataTable)
            table.cursor_type = "row"
            table.zebra_stripes = True

    def _set_table(
        self,
        selector: str,
        columns: list[str],
        rows: Iterable[Mapping[str, object]],
    ) -> None:
        table = self.query_one(selector, DataTable)
        table.clear(columns=True)
        table.add_columns(*columns)
        row_list = [dict(row) for row in rows]
        self._table_rows[selector.removeprefix("#")] = row_list
        for row in row_list:
            table.add_row(*[self._cell(row.get(column, "")) for column in columns])

    def _update_context(self, text: str) -> None:
        self.query_one("#context_panel", Static).update(text)

    @staticmethod
    def _cell(value: object) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        if isinstance(value, dict):
            return pretty(value)
        return str(value)


def _asset_line(asset: dict[str, object]) -> str:
    return (
        f"- {asset.get('asset_id', '')} | "
        f"{asset.get('kind', '')} | "
        f"shot={asset.get('shot_id', '') or 'none'} | "
        f"take={asset.get('take', '')} | "
        f"active={asset.get('active', '')} | "
        f"{asset.get('path', '')}"
    )
