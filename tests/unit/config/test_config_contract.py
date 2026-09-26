"""Config contract [Flx-F9]: every profile leaf and env-override path is read.

A path counts as READ when an AST scan over ``src/film_pipeline`` finds every
segment of the path occurring as a string literal somewhere in production code
(subscript chains like ``config["generation"]["default_mode"]``, ``.get()``
chains like ``resolved_config.get("model_profiles", {})``, or kwargs to
schema/model constructors). Reads that flow through framework indirection can
be pinned explicitly via ``READERS`` annotations below so they never depend on
scanner luck.

Paths that are deliberately NOT read yet live in ``KNOWN_DEAD_GROUPS`` with a
recorded reason and a citation into
``documentation/reviews/hardcoded-values-inventory.md`` (narrative audit; this
test pins current paths because that document's citations have drifted before).
Removing a KNOWN_DEAD row without wiring a real reader fails this test — the
point is that dead config may only disappear deliberately.

Known scanner idiom (documented per review amendment): dynamic key construction
(e.g. ``config[dynamic_key]``) is invisible to the scan; such paths MUST get a
READERS annotation instead of being left to pass by luck.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import yaml

from film_pipeline.config.runtime_overrides import ENV_OVERRIDE_MAP

_SRC_DIR = Path(__file__).resolve().parents[3] / "src" / "film_pipeline"
_PROFILES_DIR = Path(__file__).resolve().parents[3] / "profiles"
_REPO_DIR = _PROFILES_DIR.parent

_INVENTORY = "documentation/reviews/hardcoded-values-inventory.md"

# Each group: (prefix paths, reason, citation). A leaf is exempt when it starts
# with any of the group's prefix paths.
type _KnownDeadGroup = tuple[tuple[tuple[str, ...], ...], str, str]

KNOWN_DEAD_GROUPS: tuple[_KnownDeadGroup, ...] = (
    (
        (("camera_default",), ("story_structure",), ("dialogue_weight",), ("visual_style",)),
        "Film-type creative-overlay corpus: profiles advertise intent that no code reads yet.",
        f"{_INVENTORY} §A; wire-or-delete deferred to WS-F/C-6",
    ),
    (
        (
            ("profile", "id"),
            ("profile", "name"),
            ("profile", "description"),
            ("profile", "version"),
            ("phases",),
            ("models", "default"),
            ("limits", "max_scenes"),
            ("studio", "skip_visual_dev"),
            ("generation", "search_api"),
        ),
        "Legacy/profile and environment knobs are declared but not consumed by the current "
        "runtime.",
        f"{_INVENTORY} §A re-check; Phase 02 config-contract review",
    ),
    (
        (
            ("review", "strategy"),
            ("review", "min_reviewers"),
            ("review", "escalation_on_disagreement"),
            ("review", "approval_gates"),
        ),
        "Multi-model review panel machinery not implemented; single-reviewer "
        "flow is authoritative today.",
        f"{_INVENTORY}; roadmap review-package work",
    ),
    (
        (
            ("budget", "per_phase_cap_usd"),
            ("budget", "max_auto_approved_cost_usd"),
            ("budget", "human_approval_above_usd"),
            ("budget", "auto_approve_up_to"),
            ("budget", "per_clip_limit"),
            ("generation", "require_spend_approval"),
        ),
        "Budget-gate knobs awaiting spend tracking (actual_cost_usd is never "
        "written — O-F9); gates cannot fire until costs are recorded.",
        f"{_INVENTORY}; O-F9",
    ),
    (
        (
            ("generation", "re_anchor_every_n_clips"),
            ("generation", "re_anchor_on_scene_boundary"),
            ("generation", "re_anchor_on_drift_warning"),
            ("generation", "allow_parallel_independent_tests"),
            ("generation", "require_last_frame_chaining"),
            ("generation", "max_clips"),
            ("generation", "max_duration_seconds"),
            ("generation", "default_mode"),
            ("generation", "duration_seconds"),
            ("generation", "resolution"),
        ),
        "Generation-loop policy knobs declared but unread by the generation "
        "loop (confirmed 2026-08 re-check).",
        f"{_INVENTORY} §C re-check",
    ),
    (
        (
            ("delivery", "modes"),
            ("delivery", "include_subtitles"),
            ("delivery", "include_audio_stems"),
        ),
        "Delivery-format options ahead of the post/delivery feature work.",
        f"{_INVENTORY}",
    ),
    (
        (
            ("validators", "strictness"),
            ("validators", "multi_review"),
            ("validators", "review_models"),
            ("validation", "thresholds"),
        ),
        "Validator configuration is not fed from resolved config; per-entry "
        "ValidatorThresholds literals in validation/thresholds.py are the "
        "authority. Wiring deferred to C-6 (the base.studio.yaml thresholds "
        "block was deleted on this basis).",
        f"{_INVENTORY} §C re-check; C-6",
    ),
    (
        (
            ("providers", "fallback_allowed"),
            ("providers", "max_duration_seconds"),
            ("checkpoints", "backend"),
        ),
        "Provider-fallback policy and checkpoint-backend selection pending "
        "provider/checkpoint phase work.",
        f"{_INVENTORY}",
    ),
)

# Paths read through mechanisms the path scan cannot see. These are exact
# annotations: profile maps and list-shaped sections are represented by their
# container path, while dynamic profile names and keys are not guessed. Each
# value names the production consumer that provides the evidence for the row.
READERS: dict[tuple[str, ...], tuple[str, str]] = {
    # The profile name and setting names are dynamic, so the scanner can only
    # prove this container-level reader. _model_overrides_for passes each
    # selected profile through to the router at runtime.
    ("model_profiles",): (
        "src/film_pipeline/orchestration/nodes/_context.py",
        "_model_overrides_for",
    ),
    ("model_profiles", "creative_writer", "primary"): (
        "src/film_pipeline/orchestration/nodes/_context.py",
        "_model_overrides_for",
    ),
    ("model_profiles", "creative_writer", "max_tokens"): (
        "src/film_pipeline/orchestration/nodes/_context.py",
        "_model_overrides_for",
    ),
    ("model_profiles", "creative_writer", "temperature"): (
        "src/film_pipeline/orchestration/nodes/_context.py",
        "_model_overrides_for",
    ),
    ("model_profiles", "strict_validator", "primary"): (
        "src/film_pipeline/orchestration/nodes/_context.py",
        "_model_overrides_for",
    ),
    ("model_profiles", "strict_validator", "max_tokens"): (
        "src/film_pipeline/orchestration/nodes/_context.py",
        "_model_overrides_for",
    ),
    ("providers", "image"): (
        "src/film_pipeline/config/profile_resolver.py",
        "provider_specs_from_raw",
    ),
    ("models", "available"): (
        "src/film_pipeline/mcp/tools/helpers.py",
        "_collect_profile_models",
    ),
    ("budget", "project_cap_usd"): (
        "src/film_pipeline/orchestration/nodes/_context.py",
        "_inject_config_context",
    ),
    ("budget", "max_total_usd"): (
        "src/film_pipeline/orchestration/nodes/_context.py",
        "_inject_config_context",
    ),
    ("context", "max_chars_per_artifact"): (
        "src/film_pipeline/orchestration/nodes/_context.py",
        "_artifact_context_max_chars",
    ),
}

_CONFIG_ROOTS = frozenset(
    {
        "budget",
        "config",
        "resolved_config",
        "context_config",
        "providers",
        "resolved",
        "studio",
        "generation",
        "limits",
        "models",
    }
)


def _literal_string(node: ast.AST) -> str | None:
    """Return a string literal value, if *node* is one."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _access_path(node: ast.AST) -> tuple[str, ...]:
    """Return a literal-key access path for subscript/get chains."""
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Subscript):
        key = _literal_string(node.slice)
        parent = _access_path(node.value)
        return (*parent, key) if key is not None else ()
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr != "get" or not node.args:
            return ()
        key = _literal_string(node.args[0])
        parent = _access_path(node.func.value)
        return (*parent, key) if key is not None else ()
    return ()


def _access_paths_in_src() -> frozenset[tuple[str, ...]]:
    paths: set[tuple[str, ...]] = set()
    for path in _SRC_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Subscript, ast.Call)):
                access_path = _access_path(node)
                if access_path:
                    paths.add(access_path)
    return frozenset(paths)


def _path_is_read(path: tuple[str, ...], access_paths: frozenset[tuple[str, ...]]) -> bool:
    """Return whether a path has a concrete or explicitly annotated reader."""
    if any(
        candidate[0] in _CONFIG_ROOTS and candidate[-len(path) :] == path
        for candidate in access_paths
    ):
        return True
    return any(path[: len(reader)] == reader for reader in READERS)


def test_path_scanner_does_not_accept_unrelated_prefixes() -> None:
    access_paths = frozenset({("unrelated", "custom", "key")})
    assert not _path_is_read(("custom", "key"), access_paths)
    assert not _path_is_read(("custom",), access_paths)
    assert not _path_is_read(("visual_style",), access_paths)


def _yaml_leaves(path: Path) -> set[tuple[str, ...]]:
    data = yaml.safe_load(path.read_text())
    leaves: set[tuple[str, ...]] = set()

    def walk(node: object, prefix: tuple[str, ...]) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, (*prefix, str(key)))
        else:
            leaves.add(prefix)

    if isinstance(data, dict):
        walk(data, ())
    return leaves


def _known_dead_reason(path: tuple[str, ...]) -> str | None:
    for prefixes, reason, _citation in KNOWN_DEAD_GROUPS:
        if any(path[: len(p)] == p for p in prefixes):
            return reason
    return None


def test_env_override_paths_are_read() -> None:
    """All seven env override targets reach code that consumes them."""
    access_paths = _access_paths_in_src()
    for env_var, path in ENV_OVERRIDE_MAP.items():
        assert _path_is_read(path, access_paths) or _known_dead_reason(path) is not None, (
            f"{env_var} writes {'/'.join(path)} but nothing reads it"
        )


def test_profile_leaves_are_read_or_known_dead() -> None:
    access_paths = _access_paths_in_src()
    offenders: list[str] = []
    for yaml_file in sorted(_PROFILES_DIR.glob("*.yaml")):
        for path in sorted(_yaml_leaves(yaml_file)):
            if _known_dead_reason(path) is not None:
                continue
            if not _path_is_read(path, access_paths):
                offenders.append(f"{yaml_file.name}: {'/'.join(path)}")
    assert not offenders, "unread, unexempted config leaves:\n" + "\n".join(offenders)


def test_named_flx_f9_failures_stay_deliberate() -> None:
    """The three originally-named dead items may only pass via explicit rows."""
    for path in (
        ("generation", "re_anchor_every_n_clips"),
        ("validation", "thresholds"),
    ):
        assert _known_dead_reason(path) is not None, (
            f"{'/'.join(path)} lost its KNOWN_DEAD exemption without a reader"
        )


def test_known_dead_rows_cite_evidence() -> None:
    for _prefixes, reason, citation in KNOWN_DEAD_GROUPS:
        assert reason.strip(), "empty reason"
        assert citation.startswith("documentation/"), citation
        for reference in citation.split(";"):
            reference = reference.strip()
            if not reference.startswith("documentation/"):
                continue
            cited_file, _, locator = reference.partition(" ")
            evidence_file = _REPO_DIR / cited_file
            assert evidence_file.exists(), citation
            section = re.search(r"§([A-Z])", locator)
            if section:
                letter = section.group(1)
                assert re.search(rf"^## {letter}[.: ]", evidence_file.read_text(), re.MULTILINE)


def test_reader_annotations_name_real_consumers() -> None:
    for _path, (source, function) in READERS.items():
        source_text = (_REPO_DIR / source).read_text()
        tree = ast.parse(source_text)
        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function
        ]
        assert functions, f"missing reader {function}: {source}"
        function_source = ast.get_source_segment(source_text, functions[0]) or ""
        assert "get(" in function_source or "[" in function_source, (
            f"reader annotation {function} has no config access: {source}"
        )


def test_annotated_reader_paths_are_exercised() -> None:
    """Annotations must prove runtime extraction, not just name a function."""
    from film_pipeline.config.profile_resolver import provider_specs_from_raw
    from film_pipeline.mcp.tools.helpers import _collect_profile_models
    from film_pipeline.orchestration.nodes._context import (
        _artifact_context_max_chars,
        _inject_config_context,
        _model_overrides_for,
    )

    state = {
        "resolved_config": {
            "model_profiles": {
                "creative_writer": {
                    "primary": "override/model",
                    "max_tokens": 123,
                    "temperature": 0.2,
                },
                "strict_validator": {"primary": "strict/model", "max_tokens": 456},
            },
            "budget": {"project_cap_usd": 7, "max_total_usd": 8},
            "context": {"max_chars_per_artifact": 321},
        }
    }
    assert _model_overrides_for(state, "creative_writer") == {
        "primary": "override/model",
        "max_tokens": 123,
        "temperature": 0.2,
    }
    assert _model_overrides_for(state, "strict_validator") == {
        "primary": "strict/model",
        "max_tokens": 456,
    }
    observed_paths: set[tuple[str, ...]] = {
        ("model_profiles",),
        ("model_profiles", "creative_writer", "primary"),
        ("model_profiles", "creative_writer", "max_tokens"),
        ("model_profiles", "creative_writer", "temperature"),
        ("model_profiles", "strict_validator", "primary"),
        ("model_profiles", "strict_validator", "max_tokens"),
    }
    context: dict[str, str] = {}
    _inject_config_context(state, context)
    assert context["budget_cap"] == "7"
    observed_paths.update({("budget", "project_cap_usd")})
    context = {}
    _inject_config_context(
        {"resolved_config": {"budget": {"max_total_usd": 8}}},
        context,
    )
    assert context["budget_cap"] == "8"
    observed_paths.add(("budget", "max_total_usd"))
    assert _artifact_context_max_chars(state) == 321
    observed_paths.add(("context", "max_chars_per_artifact"))
    assert provider_specs_from_raw({"image": [{"provider_id": "mock-image-provider"}]})
    observed_paths.add(("providers", "image"))
    assert "mock-model" in _collect_profile_models({"quality_profile": "mock-demo"})
    observed_paths.add(("models", "available"))
    assert observed_paths == set(READERS)
