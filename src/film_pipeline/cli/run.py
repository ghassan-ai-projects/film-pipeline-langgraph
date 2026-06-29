"""Console entry point: ``film-pipeline-run <file>``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from film_pipeline.cli.driver import HeadlessDriverError, run_headless
from film_pipeline.cli.io import SUPPORTED_EXTENSIONS


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="film-pipeline-run",
        description="Run the full film pipeline from an idea file with no human gates.",
    )
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
    parser.add_argument(
        "--runtime-mode",
        choices=["mock", "real"],
        default="mock",
        help=(
            "Execution mode. Mock is fast and zero-cost (default). Real uses configured providers."
        ),
    )
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
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path(".film-pipeline-run"),
        help="Directory for runtime state and artifacts. Default: .film-pipeline-run.",
    )
    parser.add_argument(
        "--confirm-real",
        action="store_true",
        help="Confirm that real-mode provider spend is acceptable.",
    )
    return parser


def _profile_stack(args: argparse.Namespace) -> list[str]:
    """Return the profile stack in the order expected by create_film_project."""
    if args.runtime_mode == "real":
        if not args.confirm_real:
            raise HeadlessDriverError(
                "Real mode requires --confirm-real to acknowledge provider spend."
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


def main(argv: list[str] | None = None) -> int:
    """Run the headless pipeline and print a summary."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    file_path: Path = args.file
    project_id: str = args.project_id or file_path.stem
    title: str = args.title or project_id
    slug: str = project_id.lower().replace(" ", "-")

    try:
        stack = _profile_stack(args)
    except HeadlessDriverError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    target_runtime_seconds: int | None = args.target_runtime_seconds or None
    target_scene_count: int | None = args.target_scene_count or None

    try:
        final_state = _run(
            file_path=file_path,
            project_id=project_id,
            title=title,
            slug=slug,
            runtime_mode=args.runtime_mode,
            runtime_root=args.runtime_root,
            profile_stack=stack,
            target_phase=args.target_phase,
            target_runtime_seconds=target_runtime_seconds,
            target_scene_count=target_scene_count,
        )
    except HeadlessDriverError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_summary(final_state, project_id)
    return 0


def _run(
    file_path: Path,
    project_id: str,
    title: str,
    slug: str,
    runtime_mode: str,
    runtime_root: Path,
    profile_stack: list[str],
    target_phase: str,
    target_runtime_seconds: int | None,
    target_scene_count: int | None,
) -> dict[str, Any]:
    """Synchronous wrapper around the async headless driver."""
    import asyncio

    return asyncio.run(
        run_headless(
            file_path=file_path,
            project_id=project_id,
            title=title,
            slug=slug,
            runtime_mode=runtime_mode,
            runtime_root=runtime_root,
            profile_stack=profile_stack,
            target_phase=target_phase,
            target_runtime_seconds=target_runtime_seconds,
            target_scene_count=target_scene_count,
        )
    )


def _print_summary(state: dict[str, Any], project_id: str) -> None:
    print(f"Project: {project_id}")
    print(f"Current phase: {state.get('current_phase', 'unknown')}")
    print(f"Approved: {state.get('approved', False)}")
    raw_refs = state.get("artifact_refs", [])
    seen: set[str] = set()
    artifact_refs: list[str] = []
    for ref in raw_refs:
        ref_str = str(ref)
        if ref_str not in seen:
            seen.add(ref_str)
            artifact_refs.append(ref_str)
    print(f"Artifacts produced: {len(artifact_refs)}")
    for ref in artifact_refs:
        print(f"  - {ref}")
    issues = state.get("issues", [])
    blockers = [i for i in issues if isinstance(i, dict) and i.get("severity") == "blocking"]
    if blockers:
        print(f"Blockers: {len(blockers)}")
        for b in blockers:
            print(f"  - {b.get('code', 'unknown')}: {b.get('message', '')}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
