"""Console entry point: ``film-pipeline-run <file>``."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from film_pipeline.artifacts.storage import default_run_root
from film_pipeline.cli.driver import HeadlessDriverError, HeadlessRunSpec, run_headless
from film_pipeline.cli.io import SUPPORTED_EXTENSIONS, read_constraints_file


@dataclass(frozen=True)
class RunRequest:
    """Read-only field bindings describing one headless pipeline run."""

    file_path: Path
    project_id: str
    title: str
    slug: str
    runtime_mode: str
    runtime_root: Path
    profile_stack: list[str]
    target_phase: str
    target_runtime_seconds: int | None
    target_scene_count: int | None
    constraints: dict[str, Any] | None = None


def _add_positional_and_identity_args(parser: argparse.ArgumentParser) -> None:
    """Register the idea-file positional and project identity options."""
    parser.add_argument(
        "file",
        type=Path,
        help=f"Idea file to run. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
    )
    parser.add_argument(
        "--project-id",
        default="",
        help="Project id. Defaults to the file stem.",
    )
    parser.add_argument(
        "--title",
        default="",
        help="Film title. Defaults to the project id.",
    )


def _add_execution_mode_args(parser: argparse.ArgumentParser) -> None:
    """Register the mock/real execution mode option."""
    parser.add_argument(
        "--runtime-mode",
        choices=["mock", "real"],
        default="mock",
        help=(
            "Execution mode. Mock is fast and zero-cost (default). Real uses configured providers."
        ),
    )


def _add_target_args(parser: argparse.ArgumentParser) -> None:
    """Register the run-target phase and metric options."""
    parser.add_argument(
        "--target-phase",
        default="shot_bible",
        help="Phase to run through before stopping. Default: shot_bible.",
    )
    parser.add_argument(
        "--target-runtime-seconds",
        type=int,
        default=0,
        help="Target runtime in seconds. Defaults to the value in the idea text or 180.",
    )
    parser.add_argument(
        "--target-scene-count",
        type=int,
        default=0,
        help="Target scene count. Defaults to the value in the idea text.",
    )


def _add_profile_args(parser: argparse.ArgumentParser) -> None:
    """Register the profile-stack selection options."""
    parser.add_argument(
        "--provider-profile",
        default="provider.seedance_primary",
        help="Provider profile for real mode. Default: provider.seedance_primary.",
    )
    parser.add_argument(
        "--quality-profile",
        default="quality.studio",
        help="Quality profile. Default: quality.studio.",
    )
    parser.add_argument(
        "--film-type-profile",
        default="film-type.narrative",
        help="Film-type profile. Default: film-type.narrative.",
    )


def _add_runtime_path_args(parser: argparse.ArgumentParser) -> None:
    """Register runtime state paths and the real-mode spend confirmation."""
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=None,
        help=(
            "Directory for runtime state and artifacts. "
            "Default: <storage root>/../runs/default (see FILM_PIPELINE_STORAGE_ROOT)."
        ),
    )
    parser.add_argument(
        "--constraints-file",
        type=Path,
        default=None,
        help="Optional JSON/YAML file with explicit project constraints.",
    )
    # Kept here instead of _add_execution_mode_args: argparse emits help/usage in
    # registration order, so relocating --confirm-real would alter printed help.
    parser.add_argument(
        "--confirm-real",
        action="store_true",
        help=(
            "Confirm that real-mode provider spend is acceptable. "
            "May also be set via FILM_PIPELINE_CONFIRM_REAL=1."
        ),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="film-pipeline-run",
        description="Run the full film pipeline from an idea file with no human gates.",
    )
    for add_flag_group in (
        _add_positional_and_identity_args,
        _add_execution_mode_args,
        _add_target_args,
        _add_profile_args,
        _add_runtime_path_args,
    ):
        add_flag_group(parser)
    return parser


def _real_mode_confirmed(args: argparse.Namespace) -> bool:
    """Return True when the user has confirmed real-mode provider spend."""
    if args.confirm_real:
        return True
    return os.getenv("FILM_PIPELINE_CONFIRM_REAL", "").lower() in {"1", "true", "yes"}


def _profile_stack(args: argparse.Namespace) -> list[str]:
    """Return the profile stack in the order expected by create_film_project."""
    if args.runtime_mode == "real":
        if not _real_mode_confirmed(args):
            raise HeadlessDriverError(
                "Real mode requires --confirm-real or FILM_PIPELINE_CONFIRM_REAL=1 "
                "to acknowledge provider spend."
            )
        return [
            args.provider_profile,
            args.quality_profile,
            args.film_type_profile,
        ]
    # Mock mode uses the same creative profiles without a real provider.
    return [
        args.quality_profile,
        args.film_type_profile,
    ]


def _build_run_request(args_ns: argparse.Namespace, profile_stack: list[str]) -> RunRequest:
    """Map parsed CLI arguments deterministically onto a run request."""
    file_path: Path = args_ns.file
    project_id: str = args_ns.project_id or file_path.stem
    title: str = args_ns.title or project_id
    slug: str = project_id.lower().replace(" ", "-")
    constraints: dict[str, Any] | None = None
    if args_ns.constraints_file is not None:
        constraints = read_constraints_file(args_ns.constraints_file)
    return RunRequest(
        file_path=file_path,
        project_id=project_id,
        title=title,
        slug=slug,
        runtime_mode=args_ns.runtime_mode,
        runtime_root=args_ns.runtime_root or default_run_root(),
        profile_stack=profile_stack,
        target_phase=args_ns.target_phase,
        target_runtime_seconds=args_ns.target_runtime_seconds or None,
        target_scene_count=args_ns.target_scene_count or None,
        constraints=constraints,
    )


def _fail(message: str, code: int) -> int:
    """Print an error message verbatim to stderr and return the exit code."""
    print(message, file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    """Run the headless pipeline and print a summary."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        stack = _profile_stack(args)
    except HeadlessDriverError as exc:
        return _fail(f"Error: {exc}", 2)

    request = _build_run_request(args, stack)

    from film_pipeline.app.logging_setup import configure_logging

    # The headless runner persists state under the explicit request root, so
    # retain INFO+ logs there as well as the WARNING-capped stderr stream.
    configure_logging(
        request.runtime_root,
        persist_enabled=not bool(os.getenv("FILM_PIPELINE_NO_PERSIST")),
    )

    try:
        final_state = _run_headless_pipeline(request)
    except (HeadlessDriverError, FileNotFoundError) as exc:
        return _fail(f"Error: {exc}", 1)

    _print_summary(final_state, request.project_id)
    return 0


def _run_headless_pipeline(request: RunRequest) -> dict[str, Any]:
    """Synchronous wrapper around the async headless driver."""
    import asyncio

    return asyncio.run(
        run_headless(
            HeadlessRunSpec(
                file_path=request.file_path,
                project_id=request.project_id,
                title=request.title,
                slug=request.slug,
                runtime_mode=request.runtime_mode,
                runtime_root=request.runtime_root,
                profile_stack=request.profile_stack,
                target_phase=request.target_phase,
                target_runtime_seconds=request.target_runtime_seconds,
                target_scene_count=request.target_scene_count,
                constraints=request.constraints,
            )
        )
    )


def _print_summary(state: dict[str, Any], project_id: str) -> None:
    print(f"Project: {project_id}")
    print(f"Current phase: {state.get('current_phase', 'unknown')}")
    print(f"Approved: {state.get('approved', False)}")
    artifact_refs = _unique_strs(state.get("artifact_refs", []))
    print(f"Artifacts produced: {len(artifact_refs)}")
    for ref in artifact_refs:
        print(f"  - {ref}")
    issues = state.get("issues", [])
    blockers = _blocking_issues(issues)
    if blockers:
        print(f"Blockers: {len(blockers)}")
        for blocker in blockers:
            print(f"  - {blocker.get('code', 'unknown')}: {blocker.get('message', '')}")


def _blocking_issues(issues: Iterable[Any]) -> list[dict[str, Any]]:
    """Return well-formed issues whose severity blocks delivery."""
    return [
        issue for issue in issues if isinstance(issue, dict) and issue.get("severity") == "blocking"
    ]


def _unique_strs(values: Iterable[Any]) -> list[str]:
    """Return str(value) per entry, keeping first-seen order without duplicates."""
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        value_str = str(value)
        if value_str not in seen:
            seen.add(value_str)
            unique.append(value_str)
    return unique


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
