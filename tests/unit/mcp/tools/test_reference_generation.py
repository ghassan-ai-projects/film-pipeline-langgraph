"""Unit tests for film_pipeline.mcp.tools.reference_generation.generate_reference_images.

These tests exercise the main async tool end-to-end with heavy mocking for
provider calls, frame heuristics, frame review, compositing, and sidecar
writing. The goal is to cover retry loops, heuristic failures, review paths,
composite generation, delta regeneration, and index-file writing without real
image generation.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from unittest import mock

import pytest
from pydantic import Field

from film_pipeline.mcp.tools.reference_generation import generate_reference_images
from film_pipeline.orchestration.services import GraphServices
from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase, SchemaBase
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.schemas.reference import ReferenceIndex, ReferenceIndexEntry
from film_pipeline.studio.mock_responses import default_mock_responses
from film_pipeline.studio.runtime import StudioRuntime


@dataclass
class _FakeHeuristicResult:
    passed: bool
    failures: list[str] = field(default_factory=list)


@dataclass
class _FakeReviewResult:
    passed: bool
    total: float
    scores: dict[str, object] = field(default_factory=dict)
    actionable_feedback: str = ""


def _save_reference_index(rt: StudioRuntime, entries: list[dict[str, object]]) -> None:
    """Persist a reference_index artifact for the active project."""
    assert rt.services is not None
    store = rt.services.artifact_store
    meta = ArtifactMetadata(
        artifact_id="reference_index",
        artifact_type=ArtifactType.REFERENCE_INDEX,
        project_id=str(rt.active_project_id),
        phase=FilmPhase.VISUAL_DEV,
        version=1,
        status=ArtifactStatus.CANDIDATE,
        parents=[],
        created_by="test",
        created_at=datetime.now(UTC),
    )
    typed_entries: list[ReferenceIndexEntry] = []
    for raw in entries:
        data = dict(raw)
        data.setdefault("asset_path", "")
        data.setdefault("asset_type", "")
        data.setdefault("subject_type", "")
        data.setdefault("subject_id", "")
        data.setdefault("quality_score", 0.0)
        typed_entries.append(ReferenceIndexEntry.model_validate(data))
    store.save(
        ReferenceIndex(
            project_id=str(rt.active_project_id),
            entries=typed_entries,
        ),
        meta,
    )


def _build_fake_provider(tmp_path: Path) -> mock.MagicMock:
    """Build a heavily-mocked image provider."""
    provider = mock.MagicMock()
    provider.entry.provider_id = "mock-image-provider"
    provider.entry.provider_type = "image"
    provider.build_payload.return_value = {"prompt": "fake-prompt"}

    _call_count = 0

    def _download(job: object, output_dir: str) -> str:
        nonlocal _call_count
        _call_count += 1
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"download-{_call_count}.png"
        path.write_bytes(b"fake-png")
        return str(path)

    provider.download.side_effect = _download
    provider.submit.return_value = mock.MagicMock(status="submitted")
    provider.poll.return_value = mock.MagicMock(status="completed")
    provider.extract_metadata.return_value = {"mime_type": "image/png"}
    return provider


@pytest.fixture
def rt(tmp_path: Path) -> Generator[StudioRuntime, None, None]:
    """Runtime with an active project and a fake image provider."""
    services = GraphServices.for_mock_runtime(
        artifacts_root=str(tmp_path / "artifacts"), mock_responses=default_mock_responses()
    )
    runtime = StudioRuntime(runtime_root=tmp_path / "runtime")
    runtime.services = services
    runtime.create_project("ref-gen-test", "Ref Gen Test")
    runtime.set_active("ref-gen-test")
    runtime.register_provider("mock-image-provider", _build_fake_provider(tmp_path))
    runtime.set_provider_health("mock-image-provider", "healthy")
    with mock.patch("film_pipeline.mcp.tools.get_runtime", return_value=runtime):
        yield runtime


@pytest.fixture
def mocks() -> Generator[dict[str, mock.MagicMock], None, None]:
    """Patch all external generation/compositing/review helpers."""
    patch_targets = {
        "prompt_builder": "film_pipeline.generation.prompt_builder.build_structured_prompt",
        "heuristics": "film_pipeline.generation.frame_heuristics.run_heuristic_checks",
        "should_review": "film_pipeline.generation.frame_reviewer.should_review_frame",
        "review_frame": "film_pipeline.generation.frame_reviewer.review_frame",
        "write_sidecar": "film_pipeline.generation.frame_sidecar.write_frame_sidecar",
        "character_sheet": "film_pipeline.generation.compositor.build_character_identity_sheet",
        "environment_board": "film_pipeline.generation.compositor.build_environment_board",
        "expression_sheet": "film_pipeline.generation.compositor.build_expression_sheet",
        "scale_sheet": "film_pipeline.generation.compositor.build_scale_sheet",
        "style_board": "film_pipeline.generation.compositor.build_style_board",
        "review_composite": "film_pipeline.generation.sheet_reviewer.review_composite_sheet",
    }
    contexts: dict[str, Any] = {}
    for key, target in patch_targets.items():
        contexts[key] = mock.patch(target)
    started = {key: ctx.start() for key, ctx in contexts.items()}

    # Defaults: pass heuristics, skip review, echo prompt text.
    started["prompt_builder"].side_effect = lambda entry, **_: str(
        entry.get("prompt_text", "prompt")
    )
    started["heuristics"].return_value = _FakeHeuristicResult(passed=True)
    started["should_review"].return_value = False
    started["review_frame"].return_value = _FakeReviewResult(passed=True, total=38.0)

    try:
        yield started
    finally:
        for ctx in contexts.values():
            ctx.stop()


def _make_entry(
    reference_id: str,
    subject_type: str = "character",
    subject_id: str = "leo",
    frame_role: str = "front-face",
    prompt_text: str = "prompt",
    tier: str = "fast",
    **extra: object,
) -> dict[str, object]:
    return {
        "reference_id": reference_id,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "frame_role": frame_role,
        "asset_type": "character_frame",
        "prompt_text": prompt_text,
        "tier": tier,
        **extra,
    }


# ---------------------------------------------------------------------------
# Error / early-return paths
# ---------------------------------------------------------------------------


def test_no_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    from film_pipeline.studio.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is False
    assert "No active project" in str(result.get("error", ""))


def test_missing_reference_index(rt: StudioRuntime) -> None:
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is False
    assert "Reference index not yet generated" in str(result.get("error", ""))


def test_empty_entries(rt: StudioRuntime) -> None:
    _save_reference_index(rt, [])
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is False
    assert "no entries" in str(result.get("error", "")).lower()


def test_no_image_provider(rt: StudioRuntime, monkeypatch: pytest.MonkeyPatch) -> None:
    _save_reference_index(rt, [_make_entry("ref:leo:front")])
    rt.provider_adapters.clear()
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is False
    assert "No image provider" in str(result.get("error", ""))


def test_project_root_not_found(rt: StudioRuntime, monkeypatch: pytest.MonkeyPatch) -> None:
    _save_reference_index(rt, [_make_entry("ref:leo:front")])
    rt.project_roots.clear()
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is False
    assert "Project root" in str(result.get("error", ""))


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_success_single_entry(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    _save_reference_index(rt, [_make_entry("ref:leo:front", frame_role="front-face")])
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 1
    assert result["failed"] == 0


def test_success_review_passed(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    mocks["should_review"].return_value = True
    mocks["review_frame"].return_value = _FakeReviewResult(
        passed=True,
        total=38.0,
        scores={"subject": {"score": 9}},
        actionable_feedback="",
    )
    _save_reference_index(rt, [_make_entry("ref:leo:front", frame_role="front-face")])
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 1


def test_requested_ids_filter(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    _save_reference_index(
        rt,
        [
            _make_entry("ref:leo:front", frame_role="front-face"),
            _make_entry("ref:leo:side", frame_role="side-profile"),
        ],
    )
    result = asyncio.run(generate_reference_images({"reference_ids": ["ref:leo:side"]}))
    assert result["ok"] is True
    assert result["generated"] == 1
    results = cast(list[dict[str, object]], result.get("results", []))
    assert any(str(r.get("reference_id")) == "ref:leo:side" for r in results)


def test_force_regeneration(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    project_root = rt.project_roots[str(rt.active_project_id)]
    existing = project_root / "references" / "characters" / "leo" / "master-frames"
    existing.mkdir(parents=True, exist_ok=True)
    (existing / "ref-leo-front.png").write_bytes(b"existing")
    _save_reference_index(
        rt,
        [
            _make_entry(
                "ref:leo:front",
                frame_role="front-face",
                asset_path="references/characters/leo/master-frames/ref-leo-front.png",
            )
        ],
    )
    result = asyncio.run(generate_reference_images({"force": True}))
    assert result["ok"] is True
    assert result["generated"] == 1


def test_asset_path_missing_file_generates(
    rt: StudioRuntime, mocks: dict[str, mock.MagicMock]
) -> None:
    """Asset path is set but the file does not exist, so generation runs."""
    _save_reference_index(
        rt,
        [
            _make_entry(
                "ref:leo:front",
                frame_role="front-face",
                asset_path="references/characters/leo/master-frames/missing.png",
            )
        ],
    )
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 1


def test_empty_reference_id_filtered(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    _save_reference_index(
        rt,
        [
            _make_entry("ref:leo:front", frame_role="front-face"),
            {"reference_id": "", "subject_type": "character", "subject_id": "leo"},
        ],
    )
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 1


# ---------------------------------------------------------------------------
# Retry / failure paths
# ---------------------------------------------------------------------------


def test_generation_fails_all_retries(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    provider = rt.provider_adapters["mock-image-provider"]
    provider.submit.side_effect = RuntimeError("provider down")
    _save_reference_index(rt, [_make_entry("ref:leo:front", frame_role="front-face")])
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["failed"] == 1
    assert result["generated"] == 0


def test_retry_then_succeed(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    """First attempt fails generation; second attempt succeeds."""
    provider = rt.provider_adapters["mock-image-provider"]
    calls: list[int] = []

    def _submit(payload: dict[str, object], shot_id: str) -> object:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("transient")
        return mock.MagicMock(status="submitted")

    provider.submit.side_effect = _submit
    _save_reference_index(rt, [_make_entry("ref:leo:front", frame_role="front-face")])
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 1
    assert result["failed"] == 0


def test_heuristic_fails_all_retries(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    mocks["heuristics"].return_value = _FakeHeuristicResult(
        passed=False, failures=["resolution_too_low"]
    )
    _save_reference_index(rt, [_make_entry("ref:leo:front", frame_role="front-face")])
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["failed"] == 1
    assert result["generated"] == 0


def test_review_failed_then_passed(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    """First review fails with feedback; retry passes."""
    mocks["should_review"].return_value = True
    attempts: list[int] = []

    def _review(*_args: object, **_kwargs: object) -> _FakeReviewResult:
        attempts.append(1)
        if len(attempts) == 1:
            return _FakeReviewResult(
                passed=False,
                total=20.0,
                scores={"subject": {"score": 6}},
                actionable_feedback="Face obscured.",
            )
        return _FakeReviewResult(
            passed=True,
            total=36.0,
            scores={"subject": {"score": 9}},
            actionable_feedback="",
        )

    mocks["review_frame"].side_effect = _review
    _save_reference_index(rt, [_make_entry("ref:leo:side", frame_role="side-profile")])
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 1


def test_review_failed_all_retries(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    mocks["should_review"].return_value = True
    mocks["review_frame"].return_value = _FakeReviewResult(
        passed=False,
        total=18.0,
        scores={"subject": {"score": 4}},
        actionable_feedback="Face missing.",
    )
    _save_reference_index(rt, [_make_entry("ref:leo:side", frame_role="side-profile")])
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 1  # accepted as needs_regeneration
    assert result["failed"] == 0


def test_review_skipped(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    mocks["should_review"].return_value = False
    _save_reference_index(rt, [_make_entry("ref:leo:front", frame_role="front-face")])
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 1


# ---------------------------------------------------------------------------
# Identity / tier / delta-regeneration paths
# ---------------------------------------------------------------------------


def test_standard_tier_uses_seed_and_identity_state(
    rt: StudioRuntime, mocks: dict[str, mock.MagicMock]
) -> None:
    """Standard tier should set seed and propagate identity state."""
    _save_reference_index(
        rt,
        [
            _make_entry("ref:leo:front", frame_role="front-face", tier="standard"),
            _make_entry("ref:leo:side", frame_role="side-profile", tier="standard"),
        ],
    )
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 2
    provider = rt.provider_adapters["mock-image-provider"]
    kwargs = [call.kwargs for call in provider.build_payload.call_args_list]
    # The second call should include the seed set on the first anchor.
    assert any("seed" in k for k in kwargs)


def test_delta_regeneration_strengthens_i2i(
    rt: StudioRuntime, mocks: dict[str, mock.MagicMock]
) -> None:
    """Failed subject score on non-anchor activates i2i state."""
    mocks["should_review"].return_value = True
    mocks["review_frame"].return_value = _FakeReviewResult(
        passed=False,
        total=20.0,
        scores={"subject": {"score": 5}},
        actionable_feedback="Subject drift.",
    )
    _save_reference_index(
        rt,
        [
            _make_entry("ref:leo:front", frame_role="front-face"),
            _make_entry("ref:leo:side", frame_role="side-profile"),
        ],
    )
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True


def test_anchor_frame_tracks_path(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    _save_reference_index(
        rt,
        [
            _make_entry("ref:leo:front", frame_role="front-face", tier="standard"),
        ],
    )
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 1


def test_delta_regeneration_reduces_i2i_strength(
    rt: StudioRuntime, mocks: dict[str, mock.MagicMock]
) -> None:
    """Second failed subject review for a group reduces i2i_strength to 0.3."""
    mocks["should_review"].return_value = True

    def _review(*_args: object, **_kwargs: object) -> _FakeReviewResult:
        return _FakeReviewResult(
            passed=False,
            total=20.0,
            scores={"subject": {"score": 5}},
            actionable_feedback="Subject drift.",
        )

    mocks["review_frame"].side_effect = _review
    _save_reference_index(
        rt,
        [
            _make_entry("ref:leo:side", frame_role="side-profile"),
            _make_entry("ref:leo:3-4", frame_role="3-4-left"),
        ],
    )
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True


def test_sidecar_exception_is_non_blocking(
    rt: StudioRuntime, mocks: dict[str, mock.MagicMock]
) -> None:
    mocks["write_sidecar"].side_effect = RuntimeError("sidecar boom")
    _save_reference_index(rt, [_make_entry("ref:leo:front", frame_role="front-face")])
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 1


# ---------------------------------------------------------------------------
# Composite sheets / sidecar / index files
# ---------------------------------------------------------------------------


def test_composite_sheets_called_for_character_and_environment(
    rt: StudioRuntime, mocks: dict[str, mock.MagicMock]
) -> None:
    assert rt.services is not None
    store = rt.services.artifact_store
    env_meta = ArtifactMetadata(
        artifact_id="environment_bible",
        artifact_type=ArtifactType.ENVIRONMENT_BIBLE,
        project_id=str(rt.active_project_id),
        phase=FilmPhase.VISUAL_DEV,
        version=1,
        status=ArtifactStatus.CANDIDATE,
        parents=[],
        created_by="test",
        created_at=datetime.now(UTC),
    )

    class _EnvironmentBible(SchemaBase):
        environment_id: str
        color_palette: list[str] = Field(default_factory=list)

    store.save(_EnvironmentBible(environment_id="studio", color_palette=["#000000"]), env_meta)
    _save_reference_index(
        rt,
        [
            _make_entry(
                "ref:leo:front",
                subject_type="character",
                subject_id="leo",
                frame_role="front-face",
            ),
            _make_entry(
                "ref:studio:wide",
                subject_type="environment",
                subject_id="studio",
                frame_role="wide-establishing",
            ),
        ],
    )
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    mocks["character_sheet"].assert_called_once()
    mocks["environment_board"].assert_called_once()


def test_optional_sheets_called(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    _save_reference_index(
        rt,
        [
            _make_entry(
                "ref:leo:front",
                subject_type="character",
                subject_id="leo",
                frame_role="front-face",
            ),
        ],
    )
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    mocks["expression_sheet"].assert_called_once()


def test_composite_exceptions_are_non_blocking(
    rt: StudioRuntime, mocks: dict[str, mock.MagicMock]
) -> None:
    mocks["character_sheet"].side_effect = RuntimeError("sheet boom")
    mocks["environment_board"].side_effect = RuntimeError("board boom")
    mocks["expression_sheet"].side_effect = RuntimeError("expression boom")
    mocks["scale_sheet"].side_effect = RuntimeError("scale boom")
    mocks["style_board"].side_effect = RuntimeError("style boom")
    mocks["review_composite"].side_effect = RuntimeError("review boom")
    _save_reference_index(
        rt,
        [
            _make_entry(
                "ref:leo:front",
                subject_type="character",
                subject_id="leo",
                frame_role="front-face",
            ),
            _make_entry(
                "ref:studio:wide",
                subject_type="environment",
                subject_id="studio",
                frame_role="wide-establishing",
            ),
        ],
    )
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 2


def test_sidecar_written(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    _save_reference_index(rt, [_make_entry("ref:leo:front", frame_role="front-face")])
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    mocks["write_sidecar"].assert_called_once()


def test_index_files_written(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    _save_reference_index(rt, [_make_entry("ref:leo:front", frame_role="front-face")])
    asyncio.run(generate_reference_images({}))
    project_root = rt.project_roots[str(rt.active_project_id)]
    idx_dir = project_root / "references" / "index"
    assert (idx_dir / "reference-index.json").exists()
    data = json.loads((idx_dir / "reference-index.json").read_text())
    assert len(data["entries"]) == 1


def test_no_entries_needed_generation(rt: StudioRuntime, mocks: dict[str, mock.MagicMock]) -> None:
    project_root = rt.project_roots[str(rt.active_project_id)]
    existing = project_root / "references" / "characters" / "leo" / "master-frames"
    existing.mkdir(parents=True, exist_ok=True)
    (existing / "ref-leo-front.png").write_bytes(b"existing")
    _save_reference_index(
        rt,
        [
            _make_entry(
                "ref:leo:front",
                frame_role="front-face",
                asset_path="references/characters/leo/master-frames/ref-leo-front.png",
            )
        ],
    )
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 0
    assert result["skipped"] == 1


# ---------------------------------------------------------------------------
# Character bible preload
# ---------------------------------------------------------------------------


def test_character_bible_preloaded_when_available(
    rt: StudioRuntime, mocks: dict[str, mock.MagicMock]
) -> None:
    assert rt.services is not None
    store = rt.services.artifact_store
    meta = ArtifactMetadata(
        artifact_id="character_bible",
        artifact_type=ArtifactType.CHARACTER_BIBLE,
        project_id=str(rt.active_project_id),
        phase=FilmPhase.VISUAL_DEV,
        version=1,
        status=ArtifactStatus.CANDIDATE,
        parents=[],
        created_by="test",
        created_at=datetime.now(UTC),
    )

    class _CharacterBible(SchemaBase):
        character_id: str
        identity_block: dict[str, object] = Field(default_factory=dict)

    store.save(_CharacterBible(character_id="leo", identity_block={}), meta)

    _save_reference_index(
        rt,
        [
            _make_entry(
                "ref:leo:front",
                subject_type="character",
                subject_id="leo",
                frame_role="front-face",
            ),
            _make_entry(
                "ref:mia:front",
                subject_type="character",
                subject_id="mia",
                frame_role="front-face",
            ),
        ],
    )
    result = asyncio.run(generate_reference_images({}))
    assert result["ok"] is True
    assert result["generated"] == 2
