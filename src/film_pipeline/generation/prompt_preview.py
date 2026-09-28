"""Preview the exact prompt each shot will send to its provider.

This is a `generation` use case, not an operator-surface one: it reads the shot
matrix through `GenerationExecutor`, resolves each row's prompt, and reports the
provider/model that will be used. `operations._generation_ops` carried it (and
five sibling methods) because a now-removed TUI needed an in-process service; the
only remaining caller is the `preview_generation_prompts` MCP tool, which passes a
runtime.

Available as soon as the shot matrix exists, so the operator can read and validate
prompts during `gen_planning` review — before any spend.

The runtime is taken as a narrow structural type rather than through
`operations.ports.RuntimePort`: this is `generation`'s use case, and importing
`operations` for the protocol would add a `generation -> operations` edge for a
type that names two members. `StudioRuntime` satisfies it as-is.

See `docs/modularity-improvements/03-one-use-case-layer.md`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from film_pipeline.generation.executor import GenerationExecutor


@runtime_checkable
class PromptPreviewRuntime(Protocol):
    """The runtime capabilities this use case needs, and no more."""

    @property
    def services(self) -> Any:
        """The wired services bundle, whose `artifact_store` we read."""
        ...

    @property
    def provider_adapters(self) -> Mapping[str, Any]:
        """Registered provider adapters, keyed by provider id."""
        ...

    def default_video_provider(self) -> tuple[str, str]:
        """Return the `(provider_id, model)` a generation batch would dispatch to."""
        ...


class GenerationNotConfiguredError(RuntimeError):
    """Raised when the runtime has no artifact store to plan against."""


def preview_generation_prompts(
    runtime: PromptPreviewRuntime,
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return the resolved prompt for every shot row in ``state``'s project.

    ``state`` is passed in rather than looked up: resolving "which project" is the
    caller's job, and the MCP handler has already had its project resolved by
    dispatch. Re-deriving it here would be the second source of truth doc 01
    removes.
    """
    services = runtime.services
    if services is None:
        raise GenerationNotConfiguredError("artifact store is not configured.")
    executor = GenerationExecutor(services.artifact_store, runtime.provider_adapters)
    provider, model = runtime.default_video_provider()

    project_id = str(state["project_id"])
    previews: list[dict[str, Any]] = []
    for row in executor.load_shot_rows(project_id):
        shot_id = str(row.get("shot_id", "") or "")
        if not shot_id:
            continue
        previews.append(
            {
                "shot_id": shot_id,
                "scene_id": str(row.get("scene_id", "")),
                "provider": provider,
                "model": model,
                "duration_seconds": row.get("duration_seconds", 5),
                "prompt": executor.resolve_prompt(project_id, shot_id, row),
            }
        )
    return previews


__all__ = ["GenerationNotConfiguredError", "PromptPreviewRuntime", "preview_generation_prompts"]
