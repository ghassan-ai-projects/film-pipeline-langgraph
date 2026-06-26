"""Tests for prompt template quality instructions."""

from __future__ import annotations

from film_pipeline.agents.prompt_templates.defaults import (
    _constitution_creator,
    _development_creator,
    _screenwriter,
    _shot_bible_creator,
    _visual_development_creator,
)
from film_pipeline.agents.prompt_templates.registry import PromptTemplate


class TestQualityInstructions:
    def test_creative_templates_have_quality_instructions(self) -> None:
        """All 5 creative templates must include quality_instructions."""
        creative = [
            _constitution_creator(),
            _development_creator(),
            _screenwriter(),
            _visual_development_creator(),
            _shot_bible_creator(),
        ]
        for tpl in creative:
            assert "thorough and detailed" in tpl.quality_instructions.lower(), (
                f"{tpl.template_id} missing quality_instructions"
            )

    def test_quality_instructions_appears_in_rendered_output(self) -> None:
        """render() must append quality_instructions when present."""
        tpl = _screenwriter()
        rendered = tpl.render(idea="test film idea")
        assert "QUALITY REQUIREMENTS" in rendered

    def test_render_includes_current_date_context(self) -> None:
        """render() injects temporal context and allows deterministic override."""
        tpl = _screenwriter()
        rendered = tpl.render(idea="test film idea", current_date="2026-06-24")
        assert "# Runtime Context\nCurrent date: 2026-06-24" in rendered

    def test_empty_quality_instructions_not_rendered(self) -> None:
        """render() must NOT append quality section when field is empty."""
        tpl = PromptTemplate(
            template_id="test",
            agent_id="test",
            version=1,
            role="R",
            core_task="T",
            context_template="C",
            constraints="X",
            output_format="O",
            output_schema_ref="test",
            quality_instructions="",
        )
        rendered = tpl.render()
        assert "QUALITY REQUIREMENTS" not in rendered
