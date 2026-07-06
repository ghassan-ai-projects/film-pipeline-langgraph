"""Shared quality-instruction blocks used by the creator templates."""

from __future__ import annotations

_QUALITY_DIRECTIVE = (
    "QUALITY REQUIREMENTS:\n"
    "- Be thorough and detailed where detail serves the work; be ruthless where it "
    "does not. Depth means specificity, not word count — never pad to hit a length.\n"
    "- Use vivid, sensory, cinematic language with concrete, filmable choices.\n"
    "- Make specific creative decisions. Never vague, generic, or placeholder text.\n"
    "- Review your output for internal consistency before finalizing.\n"
    "- Every field in the output schema must be populated with real content — "
    "no empty strings, no placeholders, no 'TBD'."
)

_SCREENWRITER_QUALITY = (
    "QUALITY REQUIREMENTS:\n"
    "- Be thorough and detailed where detail serves the story; be ruthless where it "
    "does not. Length is never the goal — necessity is.\n"
    "- Write in vivid, sensory, cinematic language: concrete images the camera can "
    "actually capture, not abstractions.\n"
    "- Make specific creative choices. Never generic, never placeholder text.\n"
    "- Prefer a precise 12-word logline to a padded 40-word one.\n"
    "- Before finalizing, reread each character's dialogue with the names hidden and "
    "confirm you could still tell them apart. If you cannot, rewrite until you can."
)
