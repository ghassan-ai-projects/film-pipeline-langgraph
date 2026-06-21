"""Integration test: MCP-driven reference image generation."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.mcp.tools import (
    generate_reference_images,
    get_validation_report,
    inspect_reference,
)
from film_pipeline.providers.factory import build_provider_adapter


@pytest.mark.integration
class TestReferenceGenerationMCP:
    def test_generate_reference_images_updates_visual_dev_artifact(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("ref-mcp", "Reference MCP")
        rt.set_active("ref-mcp")

        state = rt._run_phase_node(rt.get_active() or {}, "intake")
        state = rt._run_phase_node(state, "constitution")
        state = rt._run_phase_node(state, "development")
        state = rt._run_phase_node(state, "script")
        state = rt._run_phase_node(state, "visual_dev")
        rt.projects["ref-mcp"] = state

        rt.register_provider(
            "mock-image-provider",
            build_provider_adapter(
                "mock-image-provider",
                provider_type="image",
                models=["mock-fast"],
            ),
        )
        rt.set_provider_health("mock-image-provider", "healthy")

        import film_pipeline.mcp.tools as mcp_tools

        monkeypatch.setattr(mcp_tools, "get_runtime", lambda: rt)
        result = asyncio.run(generate_reference_images({}))
        assert result["ok"] is True
        assert cast(int, result["generated"]) >= 1

        inspect_result = asyncio.run(inspect_reference({"reference_id": "ref_001"}))
        assert inspect_result["ok"] is True
        reference = cast(dict[str, object], inspect_result["reference"])
        assert reference["provider"] == "mock-image-provider"
        # Status may be 'validated', 'generated', or 'needs_regeneration'
        # depending on Gemini availability in the test environment
        assert reference["generation_status"] in ("validated", "generated", "needs_regeneration")
        asset_path = Path(rt.project_roots["ref-mcp"]) / cast(str, reference["asset_path"])
        assert asset_path.exists()

        validation_result = asyncio.run(get_validation_report({}))
        assert validation_result["ok"] is True
        assert validation_result["phase"] == "visual_dev"
        assert validation_result["source"] == "live"
        assert len(cast(list[object], validation_result["reports"])) >= 1
