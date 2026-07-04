"""Command palette suggestion, validation, and help builders."""

from __future__ import annotations

from film_pipeline.app.services.models import (
    DashboardSummary,
    ProjectListItem,
    ValidationWorkspace,
)
from film_pipeline.tui.view_models.builders_reader import build_validation_fix_suggestions
from film_pipeline.tui.view_models.helpers import (
    _all_issues,
    _dedupe_command_rows,
    _first_command,
    _first_prefix_match,
    _is_placeholder,
    _is_scene_id,
    _matching_suggestion,
    _preview_values,
    _scene_ids_from_summary,
    _validate_known_value,
)
from film_pipeline.tui.view_models.models import CommandOptions, CommandValidation


def build_command_suggestions(
    *,
    dashboard: DashboardSummary | None,
    validation: ValidationWorkspace | None,
    artifacts: list[dict[str, object]],
    matrix_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Generate command rows that are valid for the current cockpit snapshot."""
    rows: list[dict[str, object]] = [
        {
            "command": "open review",
            "scope": "navigation",
            "reason": "inspect approval workspace",
        },
        {
            "command": "matrix blocking",
            "scope": "matrix",
            "reason": "filter production matrix to blockers",
        },
        {
            "command": "open guide",
            "scope": "guide",
            "reason": "walk through the 1 minute mock film path",
        },
        {
            "command": "projects production",
            "scope": "projects",
            "reason": "hide test projects and focus on real projects",
        },
        {
            "command": "projects test",
            "scope": "projects",
            "reason": "show test and demo projects separately",
        },
    ]
    if dashboard is not None:
        rows.append(
            {
                "command": f"phase {dashboard.current_phase}",
                "scope": "pipeline",
                "reason": "inspect current phase",
            }
        )
        if dashboard.current_phase == "generation":
            rows.insert(
                0,
                {
                    "command": "gen run",
                    "scope": "generation",
                    "reason": "plan, approve, and generate every shot",
                },
            )
        if "approve_phase" in dashboard.eligible_actions:
            rows.append(
                {
                    "command": "approve",
                    "scope": "review",
                    "reason": "preview approval consequence and require confirmation",
                }
            )
            rows.append(
                {
                    "command": "confirm approve",
                    "scope": "review",
                    "reason": "commit pending phase approval after preview",
                }
            )
        if "request_revision" in dashboard.eligible_actions:
            rows.append(
                {
                    "command": "revise <note>",
                    "scope": "review",
                    "reason": "request changes for the selected target",
                }
            )
        if dashboard.stalled_phase:
            rows.append(
                {
                    "command": "show blocked",
                    "scope": "escalation",
                    "reason": "inspect stalled phase before operator intervention",
                }
            )
        rows.append(
            {
                "command": f"project {dashboard.project_id}",
                "scope": "projects",
                "reason": "open the active project from the project rail",
            }
        )
    for suggestion in build_validation_fix_suggestions(validation)[:5]:
        rows.append(
            {
                "command": suggestion.command,
                "scope": "validation",
                "reason": suggestion.rationale,
            }
        )
    for artifact in artifacts[:5]:
        artifact_id = str(artifact.get("artifact_id", ""))
        if artifact_id:
            rows.append(
                {
                    "command": f"artifact {artifact_id}",
                    "scope": "reader",
                    "reason": f"open {artifact_id}",
                }
            )
    for row in matrix_rows:
        target = str(row.get("target", ""))
        if _is_scene_id(target):
            rows.append(
                {
                    "command": f"scene {target}",
                    "scope": "reader",
                    "reason": str(row.get("validation", "open scene")),
                }
            )
    return _dedupe_command_rows(rows)


def build_command_help_rows(options: CommandOptions) -> list[dict[str, object]]:
    """Build operator-facing command reference rows with live selectable values."""
    return [
        {
            "command": "open <page>",
            "values": "dashboard, review, generate, scenes, assets, matrix, guide, validation, ops",
            "purpose": "jump between cockpit workspaces",
        },
        {
            "command": "gen <step>",
            "values": "run, plan, spend, start, poll, status",
            "purpose": "drive the generation batch (run does all steps)",
        },
        {
            "command": "project <project_id>",
            "values": _preview_values(options.project_ids),
            "purpose": "open or switch the active project",
        },
        {
            "command": "projects <production|test|all>",
            "values": _preview_values(options.project_kinds),
            "purpose": "filter the project rail by production or test lane",
        },
        {
            "command": "artifact <artifact_id>",
            "values": _preview_values(options.artifact_ids),
            "purpose": "open a readable artifact with linked issues and comments",
        },
        {
            "command": "asset review <artifact_id>",
            "values": _preview_values(options.artifact_ids),
            "purpose": "store a review request on an artifact",
        },
        {
            "command": "asset change <artifact_id> | <note>",
            "values": _preview_values(options.artifact_ids),
            "purpose": "request a targeted artifact change",
        },
        {
            "command": "asset extend <artifact_id> | <note>",
            "values": _preview_values(options.artifact_ids),
            "purpose": "request extension, variants, or more detail for an artifact",
        },
        {
            "command": "scene <scene_id>",
            "values": _preview_values(options.scene_ids),
            "purpose": "open a scene reader and make it the active comment target",
        },
        {
            "command": "phase <phase>",
            "values": _preview_values(options.phases),
            "purpose": "drill into graph position and phase blockers",
        },
        {
            "command": "validator <validator_id>",
            "values": _preview_values(options.validator_ids),
            "purpose": "filter validation issues by validator",
        },
        {
            "command": "matrix <query>",
            "values": "blocking, warning, candidate, status:<value>, phase:<value>",
            "purpose": "filter the smart matrix across scenes, artifacts, and issues",
        },
        {
            "command": "matrix pivot <field>",
            "values": "status, phase, kind, validation",
            "purpose": "regroup the matrix by the selected operating dimension",
        },
        {
            "command": "fix <target>",
            "values": _preview_values([*options.scene_ids, *options.artifact_ids]),
            "purpose": "prefill a targeted revision note from validation intelligence",
        },
        {
            "command": "comment <target> | <note>",
            "values": "target plus note",
            "purpose": "store a durable operator annotation on a scene, artifact, or phase",
        },
        {
            "command": "draft <target> | <note>",
            "values": "target plus note",
            "purpose": "prefill a targeted revision note without submitting it",
        },
        {
            "command": "confirm approve",
            "values": "after running approve",
            "purpose": "commit the pending phase approval after consequence preview",
        },
        {
            "command": "create <project_id> | <title> | <idea>",
            "values": "three required fields",
            "purpose": "create a new film project with default runtime settings",
        },
    ]


def filter_command_suggestions(
    rows: list[dict[str, object]],
    prefix: str,
) -> list[dict[str, object]]:
    """Filter command suggestions using a forgiving prefix/search query."""
    query = prefix.strip().lower()
    if not query:
        return rows
    matches = [
        row
        for row in rows
        if query
        in " ".join(str(row.get(key, "")).lower() for key in ("command", "scope", "reason"))
    ]
    if matches or " " not in query:
        return matches
    head = query.split(maxsplit=1)[0]
    return [
        row
        for row in rows
        if str(row.get("command", "")).lower().startswith(head)
        or str(row.get("scope", "")).lower() == head
    ]


def build_command_validation(
    command: str,
    options: CommandOptions,
    suggestions: list[dict[str, object]],
) -> CommandValidation:
    """Validate a command palette value against live selectable IDs."""
    value = command.strip()
    normalized = value.lower()
    if not value:
        return CommandValidation(
            status="incomplete",
            message="Start typing a command or select a row from suggestions.",
            completion=_first_command(suggestions),
        )

    suggestion_match = _matching_suggestion(value, suggestions)
    if suggestion_match is not None and "<" not in suggestion_match:
        return CommandValidation(status="ready", message=f"Ready: {suggestion_match}")

    tab_aliases = {
        "dashboard",
        "open dashboard",
        "review",
        "open review",
        "generate",
        "open generate",
        "gen run",
        "gen plan",
        "gen spend",
        "gen start",
        "gen poll",
        "gen status",
        "matrix",
        "open matrix",
        "validation",
        "providers",
        "assets",
        "artifacts",
        "guide",
        "open guide",
        "scenes",
        "checkpoints",
        "audit",
        "ops",
        "open ops",
        "next",
        "approve",
        "confirm approve",
        "show blocked",
    }
    if normalized in tab_aliases:
        return CommandValidation(status="ready", message=f"Ready: {value}")
    if any(candidate.startswith(normalized) for candidate in tab_aliases):
        completion = next(
            candidate for candidate in sorted(tab_aliases) if candidate.startswith(normalized)
        )
        return CommandValidation(
            status="incomplete",
            message=f"Partial command. Complete to: {completion}",
            completion=completion,
        )

    if normalized == "create":
        template = "create <project_id> | <title> | <idea>"
        return CommandValidation(
            status="incomplete",
            message="Create requires project_id, title, and idea separated by |.",
            completion=template,
        )
    if normalized.startswith("create "):
        parts = [part.strip() for part in value.removeprefix("create ").split("|")]
        if len(parts) == 3 and all(parts) and not any(_is_placeholder(part) for part in parts):
            return CommandValidation(status="ready", message="Ready: create project")
        return CommandValidation(
            status="incomplete",
            message="Create needs exactly three non-empty fields separated by |.",
            completion="create <project_id> | <title> | <idea>",
        )

    if normalized == "asset":
        return CommandValidation(
            status="incomplete",
            message="asset requires review, change, or extend.",
            completion="asset review <artifact_id>",
        )
    if normalized.startswith("asset review"):
        artifact_id = value.removeprefix("asset review").strip()
        if not artifact_id:
            return CommandValidation(
                status="incomplete",
                message=f"asset review requires one of: {_preview_values(options.artifact_ids)}.",
                completion=f"asset review {options.artifact_ids[0]}"
                if options.artifact_ids
                else "",
            )
        return _validate_known_value("asset review", artifact_id, options.artifact_ids)
    if normalized.startswith(("asset change", "asset extend")):
        verb = "asset change" if normalized.startswith("asset change") else "asset extend"
        payload = value.removeprefix(verb).strip()
        parts = [part.strip() for part in payload.split("|", maxsplit=1)]
        if len(parts) != 2 or not all(parts) or any(_is_placeholder(part) for part in parts):
            return CommandValidation(
                status="incomplete",
                message=f"{verb} needs '<artifact_id> | <note>'.",
                completion=f"{verb} <artifact_id> | <note>",
            )
        artifact_id = parts[0]
        if artifact_id not in options.artifact_ids:
            known = _preview_values(options.artifact_ids)
            return CommandValidation(
                status="unknown",
                message=f"Unknown artifact '{artifact_id}'. Known: {known}.",
            )
        return CommandValidation(status="ready", message=f"Ready: {verb}")

    target_commands = {
        "artifact": options.artifact_ids,
        "scene": options.scene_ids,
        "project": options.project_ids,
        "projects": options.project_kinds,
        "phase": options.phases,
        "validator": options.validator_ids,
    }
    for verb, valid_values in target_commands.items():
        if normalized == verb:
            return CommandValidation(
                status="incomplete",
                message=f"{verb} requires one of: {_preview_values(valid_values)}.",
                completion=f"{verb} {valid_values[0]}" if valid_values else "",
            )
        if normalized.startswith(f"{verb} "):
            target = value.split(maxsplit=1)[1].strip()
            return _validate_known_value(verb, target, valid_values)

    if normalized == "matrix":
        return CommandValidation(
            status="incomplete",
            message="Matrix requires a query or pivot field.",
            completion="matrix blocking",
        )
    if normalized.startswith("matrix pivot"):
        field_value = value.removeprefix("matrix pivot").strip()
        valid_pivots = ["status", "phase", "kind", "validation"]
        if not field_value:
            return CommandValidation(
                status="incomplete",
                message=f"matrix pivot requires one of: {_preview_values(valid_pivots)}.",
                completion="matrix pivot status",
            )
        return _validate_known_value("matrix pivot", field_value, valid_pivots)
    if normalized.startswith("matrix "):
        return CommandValidation(status="ready", message=f"Ready: filter {value}")

    pipe_commands = {"comment", "draft"}
    for verb in pipe_commands:
        if normalized == verb:
            return CommandValidation(
                status="incomplete",
                message=f"{verb} requires '<target> | <note>'.",
                completion=f"{verb} <target> | <note>",
            )
        if normalized.startswith(f"{verb} "):
            payload = value.split(maxsplit=1)[1]
            parts = [part.strip() for part in payload.split("|")]
            if len(parts) == 2 and all(parts) and not any(_is_placeholder(part) for part in parts):
                return CommandValidation(status="ready", message=f"Ready: {verb}")
            return CommandValidation(
                status="incomplete",
                message=f"{verb} needs a target and note separated by |.",
                completion=f"{verb} <target> | <note>",
            )

    argument_commands = (
        "review issue",
        "thread",
        "reader",
        "link",
        "fix",
        "open",
        "dashboard",
        "validation",
        "revise",
    )
    for verb in argument_commands:
        if normalized == verb:
            return CommandValidation(
                status="incomplete",
                message=f"{verb} needs an argument.",
            )
        if normalized.startswith(f"{verb} "):
            return CommandValidation(status="ready", message=f"Ready: {verb}")

    completion = _first_prefix_match(value, suggestions)
    if completion:
        return CommandValidation(
            status="incomplete",
            message=f"Unknown partial command. Closest match: {completion}",
            completion=completion,
        )
    return CommandValidation(
        status="unknown",
        message=f"Unknown command '{value}'. Select a suggestion or type 'commands'.",
    )


def complete_command_prefix(
    command: str,
    suggestions: list[dict[str, object]],
) -> str:
    """Return the first concrete suggestion matching a command prefix."""
    return _first_prefix_match(command, suggestions)


def build_command_options(
    *,
    projects: list[ProjectListItem],
    dashboard: DashboardSummary | None,
    validation: ValidationWorkspace | None,
    artifacts: list[dict[str, object]],
    providers: list[dict[str, object]],
) -> CommandOptions:
    """Collect selectable IDs from the current project state."""
    project_ids = sorted({project.project_id for project in projects})
    phases = sorted(
        {
            phase
            for phase in [
                *(str(artifact.get("phase", "")) for artifact in artifacts),
                dashboard.current_phase if dashboard else "",
                validation.phase if validation else "",
            ]
            if phase
        }
    )
    artifact_ids = sorted(
        {
            str(artifact.get("artifact_id", ""))
            for artifact in artifacts
            if str(artifact.get("artifact_id", ""))
        }
    )
    validator_ids = sorted(
        {
            str(report.get("validator_id", issue.get("validator_id", "")))
            for report in (validation.reports if validation else [])
            for issue in [report]
            if str(report.get("validator_id", issue.get("validator_id", "")))
        }
        | {
            str(issue.get("validator_id", ""))
            for issue in _all_issues(validation)
            if str(issue.get("validator_id", ""))
        }
    )
    scene_ids = sorted(
        {
            value
            for issue in _all_issues(validation)
            for value in [
                str(issue.get("scene_id", "")),
                str(issue.get("affected_entity", "")),
                str(issue.get("target", "")),
            ]
            if _is_scene_id(value)
        }
        | {scene_id for artifact in artifacts for scene_id in _scene_ids_from_summary(artifact)}
    )
    provider_ids = sorted(
        {
            str(provider.get("provider_id", ""))
            for provider in providers
            if str(provider.get("provider_id", ""))
        }
    )
    return CommandOptions(
        project_ids=project_ids,
        phases=phases,
        artifact_ids=artifact_ids,
        scene_ids=scene_ids,
        validator_ids=validator_ids,
        provider_ids=provider_ids,
    )
