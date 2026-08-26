"""Structured prompt construction — block-based assembly from domain data.

Assembles image-generation prompts from locked blocks (character bibles,
film constitution, entry metadata) instead of LLM-hallucinated freeform text.

Supports both character and environment prompt structures.
"""

from __future__ import annotations

from typing import Any

# ── Global negatives ─────────────────────────────────────────────────────

_GLOBAL_NEGATIVES = (
    "No text. No logos. No 2D animation. No cartoon. No anime. No illustrated style. "
    "Photorealistic only. No other characters visible. No watermarks. No grain."
)

_ENV_NEGATIVES_ADDITION = " No characters visible. No people."

# ── Frame-role → block text mappings ─────────────────────────────────────

_CHARACTER_FRAME_ROLE_TEXT: dict[str, str] = {
    "front-face": "Front face, looking at camera. Face centered, well-lit, dominant in frame.",
    "3-4-left": "Three-quarter angle facing left. Face clearly visible, features recognizable.",
    "3-4-right": "Three-quarter angle facing right. Face clearly visible, features recognizable.",
    "profile-right": "Right profile. Clean silhouette, ear and jawline clearly visible.",
    "profile-left": "Left profile. Clean silhouette, ear and jawline clearly visible.",
    "full-body": "Full body standing. Entire figure from head to feet visible. Neutral stance.",
    "expression-neutral": "Neutral expression. Relaxed face, mouth closed, eyes open naturally.",
    "expression-frustrated": "Frustrated expression. Furrowed brow, tightened jaw, mouth tension.",
    "expression-tired": "Tired expression. Drooped eyelids, relaxed mouth, subtle exhaustion.",
    "expression-peaceful": "Peaceful expression. Soft eyes, slight smile, calm demeanor.",
    "detail-eyes": "Extreme close-up of eyes. Sharp focus on iris and lashes. Both eyes visible.",
    "detail-hands": "Close-up of hands. Fingers clearly visible, natural resting position.",
    "wardrobe-baseline": "Full body showing default costume. Clean, unworn state.",
}

_ENVIRONMENT_FRAME_ROLE_TEXT: dict[str, str] = {
    "wide-establishing": (
        "Wide establishing shot showing the full space. Dominant in composition. "
        "This is the canonical view that all other angles must be consistent with."
    ),
    "alt-angle-desk": (
        "Alternate angle from desk perspective. Same room, same geometry, "
        "different viewpoint confirming spatial layout."
    ),
    "alt-angle-corner": (
        "Alternate angle from opposite corner. Same room, same furniture placement, "
        "different viewpoint."
    ),
    "alt-angle-entrance": (
        "View from the entrance. Same room geometry, confirms entryway and spatial flow."
    ),
    "lighting-cool-night": (
        "Same wide establishing composition. Cool night lighting: blue ambient through "
        "windows, warm tungsten practicals, deep shadows in corners."
    ),
    "lighting-golden-afternoon": (
        "Same wide establishing composition. Golden afternoon light: warm sun through "
        "windows, long shadows, dust motes visible in light beams."
    ),
    "lighting-overcast-morning": (
        "Same wide establishing composition. Overcast morning: soft diffuse light, "
        "no sharp shadows, muted colors."
    ),
    "detail-texture": (
        "Extreme close-up of a surface texture. Sharp focus on material detail — "
        "paint splatter, wood grain, brick texture, fabric weave."
    ),
    "detail-prop": (
        "Close-up of a key prop in situ. Object clearly visible in context, "
        "material and condition readable."
    ),
    "color-palette": (
        "Flat color swatches arranged as a horizontal strip. 3-5 dominant colors "
        "from the environment. Include hex codes below each swatch."
    ),
}

# ── Public API ────────────────────────────────────────────────────────────


def build_structured_prompt(
    entry: dict[str, Any],
    character_bible: dict[str, Any] | None = None,
    constitution: dict[str, Any] | None = None,
    *,
    identity_state: dict[str, Any] | None = None,
) -> str:
    """Assemble a structured generation prompt from domain data blocks.

    Detects the entry's ``subject_type`` and assembles the correct block
    sequence (character or environment). Falls back gracefully when optional
    sources are absent.
    """
    subject_type = str(entry.get("subject_type", "character")).strip().lower()

    if subject_type == "character":
        return _build_character_prompt(entry, character_bible, constitution, identity_state)
    if subject_type == "environment":
        return _build_environment_prompt(entry, constitution)
    return _build_generic_prompt(entry, constitution)


# ── Character prompt ──────────────────────────────────────────────────────


def _build_character_prompt(
    entry: dict[str, Any],
    character_bible: dict[str, Any] | None,
    constitution: dict[str, Any] | None,
    identity_state: dict[str, Any] | None,
) -> str:
    blocks: list[str] = []

    # CHAR_DESC
    char_desc = _resolve_char_desc(entry, character_bible, constitution)
    if char_desc:
        blocks.append(char_desc)

    # FRAME_ROLE
    role_text = _frame_role_text(entry, _CHARACTER_FRAME_ROLE_TEXT)
    if role_text:
        blocks.append(role_text)

    # EXPRESSION
    expression = str(entry.get("expression", "")).strip().lower()
    if expression and expression != "neutral":
        blocks.append(_expression_text(expression))

    # LIGHTING
    lighting = _resolve_lighting(entry, constitution)
    if lighting:
        blocks.append(lighting)

    # CAMERA
    camera = _resolve_camera(constitution)
    if camera:
        blocks.append(camera)

    # ID_REINFORCE
    id_reinforce = _resolve_id_reinforce(identity_state)
    if id_reinforce:
        blocks.append(id_reinforce)

    # GLOBAL_NEGATIVES
    blocks.append(_GLOBAL_NEGATIVES)

    return " ".join(blocks)


# ── Environment prompt ────────────────────────────────────────────────────


def _build_environment_prompt(
    entry: dict[str, Any],
    constitution: dict[str, Any] | None,
) -> str:
    blocks: list[str] = []

    # ENV_BASE
    env_base = _resolve_env_base(entry, constitution)
    if env_base:
        blocks.append(env_base)

    # ANGLE
    angle_text = _frame_role_text(entry, _ENVIRONMENT_FRAME_ROLE_TEXT)
    if angle_text:
        blocks.append(angle_text)

    # LIGHTING
    lighting = _resolve_lighting(entry, constitution)
    if lighting:
        blocks.append(lighting)

    # MOOD
    mood = _resolve_mood(constitution)
    if mood:
        blocks.append(mood)

    # CAMERA
    camera = _resolve_camera(constitution)
    if camera:
        blocks.append(camera)

    # ENV_REINFORCE
    blocks.append(
        "Same location across all angles. Consistent geometry, same furniture placement, "
        "same architectural details. No characters visible."
    )

    # GLOBAL_NEGATIVES + env addition
    blocks.append(_GLOBAL_NEGATIVES + _ENV_NEGATIVES_ADDITION)

    return " ".join(blocks)


# ── Generic fallback ──────────────────────────────────────────────────────


def _build_generic_prompt(
    entry: dict[str, Any],
    constitution: dict[str, Any] | None,
) -> str:
    """Fallback for non-character, non-environment entries (props, style, scale, camera)."""
    blocks: list[str] = []

    subject_type = str(entry.get("subject_type", "subject"))
    subject_id = str(entry.get("subject_id", "subject"))
    asset_type = str(entry.get("asset_type", "reference_sheet")).replace("_", " ")
    prompt_text = str(entry.get("prompt_text", "")).strip()

    if prompt_text:
        blocks.append(prompt_text)
    else:
        blocks.append(
            f"Create a production-ready {asset_type} for the {subject_type} '{subject_id}'."
        )

    lighting = _resolve_lighting(entry, constitution)
    if lighting:
        blocks.append(lighting)

    camera = _resolve_camera(constitution)
    if camera:
        blocks.append(camera)

    blocks.append("Photorealistic.")
    blocks.append(_GLOBAL_NEGATIVES)

    return " ".join(blocks)


# ── Resolvers (fallback chains) ───────────────────────────────────────────


def _resolve_char_desc(
    entry: dict[str, Any],
    character_bible: dict[str, Any] | None,
    constitution: dict[str, Any] | None,
) -> str:
    # 1. CharacterBible.identity_block
    if character_bible:
        visual_id = character_bible.get("visual_identity", {})
        if isinstance(visual_id, dict):
            identity_block = str(visual_id.get("identity_block", "")).strip()
            if identity_block:
                return identity_block

    # 2. FilmConstitution.character_truths
    if constitution:
        subject_id = str(entry.get("subject_id", ""))
        truths = constitution.get("character_truths", [])
        for truth in truths:
            if isinstance(truth, dict) and truth.get("character_id") == subject_id:
                return str(truth.get("truth", ""))

    # 3. Entry prompt_text (LLM-generated)
    prompt_text = str(entry.get("prompt_text", "")).strip()
    if prompt_text:
        return prompt_text

    # 4. Last resort: subject_id as label
    return str(entry.get("subject_id", "subject"))


def _resolve_env_base(
    entry: dict[str, Any],
    constitution: dict[str, Any] | None,
) -> str:
    # 1. Constitution visual_language
    if constitution:
        vis_lang = str(constitution.get("visual_language", "")).strip()
        if vis_lang:
            return vis_lang

    # 2. Entry prompt_text (LLM-generated from script)
    prompt_text = str(entry.get("prompt_text", "")).strip()
    if prompt_text:
        return prompt_text

    # 3. Entry notes
    notes = str(entry.get("notes", "")).strip()
    if notes:
        return notes

    return str(entry.get("subject_id", "environment"))


def _resolve_lighting(
    entry: dict[str, Any],
    constitution: dict[str, Any] | None,
) -> str:
    # 1. Entry lighting field
    lighting = str(entry.get("lighting", "")).strip()
    if lighting:
        return lighting

    # 2. Constitution visual_language (may contain lighting cues)
    if constitution:
        vis_lang = str(constitution.get("visual_language", "")).strip()
        if vis_lang and any(
            kw in vis_lang.lower() for kw in ("light", "golden", "cool", "warm", "night", "day")
        ):
            return vis_lang

    return ""


def _resolve_camera(constitution: dict[str, Any] | None) -> str:
    if constitution:
        cam = str(constitution.get("camera_philosophy", "")).strip()
        if cam:
            return cam
    return ""


def _resolve_mood(constitution: dict[str, Any] | None) -> str:
    if constitution:
        tone = str(constitution.get("tone", "")).strip()
        if tone:
            return tone
    return ""


def _resolve_id_reinforce(identity_state: dict[str, Any] | None) -> str:
    if identity_state and identity_state.get("i2i_active"):
        return (
            "Same person as the anchor frame. Identical facial structure, identical features. "
            "Same age, same bone structure, same skin texture. No variation in identity."
        )
    return (
        "Same person as in all other frames. Consistent facial features. "
        "Same age, same bone structure."
    )


def _frame_role_text(entry: dict[str, Any], role_texts: dict[str, str]) -> str:
    """Frame-role block: mapped phrasing when known, title-cased role otherwise."""
    frame_role = str(entry.get("frame_role", "")).strip().lower()
    if not frame_role:
        return ""
    return role_texts.get(frame_role) or (frame_role.replace("-", " ").title() + ".")


def _expression_text(expression: str) -> str:
    mapping = {
        "neutral": "Neutral expression. Relaxed face, mouth closed, eyes open naturally.",
        "frustrated": "Frustrated expression. Furrowed brow, tightened jaw, mouth tension.",
        "tired": "Tired expression. Slightly drooped eyelids, relaxed mouth, subtle exhaustion.",
        "peaceful": "Peaceful expression. Soft eyes, slight relaxed smile, calm demeanor.",
        "angry": "Angry expression. Tightened jaw, flared nostrils, intense eyes.",
        "sad": "Sad expression. Downward mouth, soft eyes, slightly furrowed brow.",
        "surprised": "Surprised expression. Raised eyebrows, slightly open mouth, wide eyes.",
        "fearful": "Fearful expression. Wide eyes, slightly parted lips, tension in brow.",
    }
    return mapping.get(expression, f"{expression.title()} expression.")
