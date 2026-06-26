"""Tests for config loading, merging, validation, and resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.config.loader import ProfileLoader, ProfileSource
from film_pipeline.config.merger import ProfileMerger
from film_pipeline.config.resolver import ConfigResolver, ResolvedConfig
from film_pipeline.config.runtime_overrides import apply_runtime_overrides
from film_pipeline.config.validator import ConfigValidator

# --- Loader tests --------------------------------------------------------


def test_load_base_studio_profile() -> None:
    loader = ProfileLoader(profiles_dir=Path("profiles"))
    src = loader.load("base.studio")
    assert src.raw["review"]["strategy"] == "multi_model_panel"
    assert len(src.raw["phases"]) == 11


def test_load_narrative_type() -> None:
    loader = ProfileLoader(profiles_dir=Path("profiles"))
    src = loader.load("film-type.narrative")
    assert src.raw["film_type"] == "narrative"
    assert src.raw["dialogue_weight"] == "medium"


def test_load_visual_poetry_type() -> None:
    loader = ProfileLoader(profiles_dir=Path("profiles"))
    src = loader.load("film-type.visual_poetry")
    assert src.raw["film_type"] == "visual_poetry"
    assert src.raw["dialogue_weight"] == "none"


def test_load_experimental_type() -> None:
    loader = ProfileLoader(profiles_dir=Path("profiles"))
    src = loader.load("film-type.experimental")
    assert src.raw["film_type"] == "experimental"


def test_load_quality_festival() -> None:
    loader = ProfileLoader(profiles_dir=Path("profiles"))
    src = loader.load("quality.festival")
    assert src.raw["validation"]["thresholds"]["pass"] == 90


def test_load_provider_free() -> None:
    loader = ProfileLoader(profiles_dir=Path("profiles"))
    src = loader.load("provider.free_or_low_cost")
    assert src.raw["providers"]["fallback_allowed"] is False


def test_load_strict_continuity() -> None:
    loader = ProfileLoader(profiles_dir=Path("profiles"))
    src = loader.load("review.strict_continuity")
    assert src.raw["generation"]["re_anchor_every_n_clips"] == 3


def test_loader_missing_raises() -> None:
    loader = ProfileLoader(profiles_dir=Path("profiles"))
    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent")


def test_loader_all_names() -> None:
    loader = ProfileLoader(profiles_dir=Path("profiles"))
    names = loader.all_names()
    assert "base.studio" in names
    assert "quality.festival" in names


def test_load_without_yaml_suffix() -> None:
    loader = ProfileLoader(profiles_dir=Path("profiles"))
    src = loader.load("base.studio")
    assert src.name == "base.studio"


# --- Merger tests --------------------------------------------------------


def test_merge_scalar_override() -> None:
    m = ProfileMerger()
    s1 = ProfileSource(name="a", path=Path("a.yaml"), raw={"x": 1, "y": 2})
    s2 = ProfileSource(name="b", path=Path("b.yaml"), raw={"y": 99})
    merged = m.merge([s1, s2])
    assert merged == {"x": 1, "y": 99}


def test_merge_list_replace() -> None:
    m = ProfileMerger()
    s1 = ProfileSource(name="a", path=Path("a.yaml"), raw={"items": [1, 2]})
    s2 = ProfileSource(name="b", path=Path("b.yaml"), raw={"items": [3]})
    merged = m.merge([s1, s2])
    assert merged["items"] == [3]


def test_merge_deep_nested() -> None:
    m = ProfileMerger()
    s1 = ProfileSource(name="a", path=Path("a.yaml"), raw={"a": {"b": 1, "c": 2}})
    s2 = ProfileSource(name="b", path=Path("b.yaml"), raw={"a": {"b": 99}})
    merged = m.merge([s1, s2])
    assert merged == {"a": {"b": 99, "c": 2}}


def test_merge_empty_sources() -> None:
    m = ProfileMerger()
    assert m.merge([]) == {}


def test_merge_later_wins() -> None:
    m = ProfileMerger()
    s1 = ProfileSource(name="a", path=Path("a.yaml"), raw={"film_type": "narrative"})
    s2 = ProfileSource(name="b", path=Path("b.yaml"), raw={"film_type": "visual_poetry"})
    s3 = ProfileSource(name="c", path=Path("c.yaml"), raw={"film_type": "experimental"})
    merged = m.merge([s1, s2, s3])
    assert merged["film_type"] == "experimental"


# --- Runtime override tests ---------------------------------------------


def test_apply_runtime_overrides_does_not_mutate_input() -> None:
    cfg = {"quality_profile": "studio", "studio": {"require_human_approval": True}}

    overridden = apply_runtime_overrides(
        cfg,
        environ={
            "FILM_PIPELINE_QUALITY": "draft",
            "FILM_PIPELINE_APPROVAL_MODE": "false",
        },
    )

    assert cfg == {"quality_profile": "studio", "studio": {"require_human_approval": True}}
    assert overridden["quality_profile"] == "draft"
    assert overridden["studio"]["require_human_approval"] is False


def test_apply_runtime_overrides_coerces_nested_values() -> None:
    overridden = apply_runtime_overrides(
        {},
        environ={
            "FILM_PIPELINE_MAX_SCENES": "12",
            "FILM_PIPELINE_SKIP_VISUAL_DEV": "yes",
            "FILM_PIPELINE_MAX_CONTEXT_CHARS": "8000",
            "FILM_PIPELINE_MODEL_OVERRIDE": "custom/model",
        },
    )

    assert overridden["limits"]["max_scenes"] == 12
    assert overridden["studio"]["skip_visual_dev"] is True
    assert overridden["context"]["max_chars_per_artifact"] == 8000
    assert overridden["models"]["creative_writer"]["primary"] == "custom/model"


# --- Validator tests -----------------------------------------------------


def test_validator_no_conflicts_on_valid_config() -> None:
    v = ConfigValidator()
    cfg = {
        "quality_profile": "studio",
        "providers": {"order": ["seedance-openrouter"]},
        "budget": {"project_cap_usd": 50},
        "generation": {"expected_shot_count": 8},
        "film_type": "narrative",
        "writing_style": "",
    }
    conflicts = v.validate(cfg)
    assert conflicts == []


def test_validator_detects_festival_free_conflict() -> None:
    v = ConfigValidator()
    cfg = {
        "quality_profile": "festival",
        "providers": {"order": ["mock-video-provider"]},
    }
    conflicts = v.validate(cfg)
    assert len(conflicts) == 1
    assert conflicts[0].code == "festival_free_conflict"
    assert conflicts[0].severity == "blocking"


def test_validator_detects_poetry_dialogue_conflict() -> None:
    v = ConfigValidator()
    cfg = {
        "film_type": "visual_poetry",
        "writing_style": "dialogue-heavy",
    }
    conflicts = v.validate(cfg)
    assert len(conflicts) == 1
    assert conflicts[0].code == "poetry_dialogue_conflict"


def test_validator_detects_budget_shot_mismatch() -> None:
    v = ConfigValidator()
    cfg = {"budget": {"project_cap_usd": 5}, "generation": {"expected_shot_count": 30}}
    conflicts = v.validate(cfg)
    assert len(conflicts) == 1
    assert conflicts[0].code == "budget_shot_mismatch"


# --- Resolver tests ------------------------------------------------------


def test_resolver_no_conflicts_happy_path() -> None:
    r = ConfigResolver(loader=ProfileLoader(profiles_dir=Path("profiles")))
    result = r.resolve(
        [
            "base.studio",
            "film-type.narrative",
            "quality.studio",
            "provider.seedance_primary",
        ]
    )
    assert isinstance(result, ResolvedConfig)
    assert result.is_blocked is False
    assert result.conflicts == []
    assert result.raw["film_type"] == "narrative"
    assert result.raw["quality_profile"] == "studio"
    # review strategy comes from last profile that touches it
    assert result.raw["review"]["strategy"] == "multi_model_panel"


def test_resolver_applies_runtime_overrides_last(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FILM_PIPELINE_QUALITY", "draft")
    monkeypatch.setenv("FILM_PIPELINE_APPROVAL_MODE", "false")
    r = ConfigResolver(loader=ProfileLoader(profiles_dir=Path("profiles")))

    result = r.resolve(
        [
            "base.studio",
            "film-type.narrative",
            "quality.studio",
            "provider.seedance_primary",
        ]
    )

    assert result.raw["quality_profile"] == "draft"
    assert result.raw["studio"]["require_human_approval"] is False


def test_resolver_detects_festival_free_conflict() -> None:
    from film_pipeline.config.loader import ProfileSource

    r = ConfigResolver(loader=ProfileLoader(profiles_dir=Path("profiles")))
    sources = r.loader.load_many(["base.studio", "film-type.visual_poetry", "quality.festival"])
    sources.append(
        ProfileSource(
            name="test_override",
            path=Path("test.yaml"),
            raw={"providers": {"order": ["mock-video-provider"]}},
        )
    )
    raw = r.merger.merge(sources)
    conflicts = r.validator.validate(raw)
    assert any(c.code == "festival_free_conflict" for c in conflicts)


def test_resolver_visual_poetry_ok_without_dialogue_flag() -> None:
    r = ConfigResolver(loader=ProfileLoader(profiles_dir=Path("profiles")))
    result = r.resolve(
        [
            "base.studio",
            "film-type.visual_poetry",
            "quality.studio",
            "provider.seedance_primary",
        ]
    )
    # visual_poetry profile has no writing_style → no dialogue conflict
    assert not any(c.code == "poetry_dialogue_conflict" for c in result.conflicts)


def test_resolver_sources_tracked() -> None:
    r = ConfigResolver(loader=ProfileLoader(profiles_dir=Path("profiles")))
    result = r.resolve(["base.studio", "film-type.narrative"])
    names = {s.name for s in result.sources}
    assert "base.studio" in names
    assert "film-type.narrative" in names


def test_resolver_provider_profile_layers_last() -> None:
    r = ConfigResolver(loader=ProfileLoader(profiles_dir=Path("profiles")))
    result = r.resolve(
        [
            "base.studio",
            "film-type.narrative",
            "quality.studio",
            "provider.seedance_primary",
        ]
    )
    assert result.raw["providers"]["max_duration_seconds"] == 15


def test_resolver_strict_continuity_layers() -> None:
    r = ConfigResolver(loader=ProfileLoader(profiles_dir=Path("profiles")))
    result = r.resolve(
        [
            "base.studio",
            "film-type.narrative",
            "quality.studio",
            "provider.seedance_primary",
            "review.strict_continuity",
        ]
    )
    assert result.raw["generation"]["re_anchor_every_n_clips"] == 3
