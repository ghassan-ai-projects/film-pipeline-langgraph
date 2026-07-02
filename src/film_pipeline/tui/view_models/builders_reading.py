"""Phase reading builders — the substance behind an approval decision.

The review workspace must let the operator actually read what they are
approving: the screenplay, the shot matrix, the prompts that will be sent
to generation models, the reference descriptions, the cost estimate. These
builders turn the current phase's candidate artifacts into readable,
plain-text sections for the Review tab's reading pane.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_SKIP_KEYS = {"schema_version", "project_id"}


@dataclass(frozen=True)
class ReadingSection:
    """One readable section of the phase reading pane."""

    artifact_id: str
    heading: str
    body: str


@dataclass(frozen=True)
class PhaseReading:
    """Everything the operator should read before approving a phase."""

    phase: str
    headline: str
    sections: list[ReadingSection] = field(default_factory=list)

    def as_text(self) -> str:
        """Render the full reading as one plain-text document."""
        lines: list[str] = [self.headline, ""]
        for section in self.sections:
            lines.append(f"━━ {section.heading} " + "━" * max(4, 56 - len(section.heading)))
            lines.append("")
            lines.append(section.body.rstrip())
            lines.append("")
        return "\n".join(lines).rstrip()


def build_phase_reading(
    phase: str,
    artifact_bodies: dict[str, dict[str, Any]],
    *,
    prompts: list[dict[str, Any]] | None = None,
) -> PhaseReading:
    """Build the readable review material for a phase.

    ``artifact_bodies`` maps artifact_id -> loaded body for the phase's
    candidate artifacts. ``prompts`` carries per-shot generation prompt
    previews (used for gen_planning and generation).
    """
    sections: list[ReadingSection] = []
    handled: set[str] = set()

    def add(artifact_id: str, heading: str, body: str) -> None:
        if body.strip():
            sections.append(ReadingSection(artifact_id=artifact_id, heading=heading, body=body))
        handled.add(artifact_id)

    profile = artifact_bodies.get("project_profile")
    if profile is not None:
        add("project_profile", "Project Profile", _read_profile(profile))
    constraints = artifact_bodies.get("project_constraints")
    if constraints is not None:
        add("project_constraints", "User Constraints", _read_generic(constraints))
    scope = artifact_bodies.get("scope_contract")
    if scope is not None:
        add("scope_contract", "Scope Contract", _read_generic(scope))
    constitution = artifact_bodies.get("film_constitution")
    if constitution is not None:
        add("film_constitution", "Film Constitution", _read_constitution(constitution))
    treatment = artifact_bodies.get("treatment")
    if treatment is not None:
        add("treatment", "Treatment", _read_treatment(treatment))
    scene_list = artifact_bodies.get("scene_list")
    if scene_list is not None:
        add("scene_list", "Scene List", _read_scene_list(scene_list))
    script = artifact_bodies.get("script")
    if script is not None:
        add("script", "Screenplay", _read_script(script))
    story_bible = artifact_bodies.get("story_bible")
    if story_bible is not None:
        add("story_bible", "Story Bible", _read_generic(story_bible))
    reference_index = artifact_bodies.get("reference_index")
    if reference_index is not None:
        add("reference_index", "Reference Images (prompts)", _read_reference_index(reference_index))
    shot_matrix = artifact_bodies.get("shot_matrix")
    if shot_matrix is not None:
        add("shot_matrix", "Shot Matrix", _read_shot_matrix(shot_matrix))
    cost_estimate = artifact_bodies.get("cost_estimate")
    if cost_estimate is not None:
        add("cost_estimate", "Cost Estimate", _read_generic(cost_estimate))
    if prompts:
        sections.append(
            ReadingSection(
                artifact_id="generation_prompts",
                heading="Generation Prompts (exactly what the model will receive)",
                body=_read_prompts(prompts),
            )
        )
    ledger = artifact_bodies.get("generation_ledger")
    if ledger is not None:
        add("generation_ledger", "Generation Ledger", _read_ledger(ledger))
    assembly = artifact_bodies.get("assembly_manifest")
    if assembly is not None:
        add("assembly_manifest", "Assembly Manifest", _read_generic(assembly))
    delivery = artifact_bodies.get("delivery_manifest")
    if delivery is not None:
        add("delivery_manifest", "Delivery Manifest", _read_generic(delivery))

    # Any phase artifact not covered above still gets a readable fallback so
    # nothing is invisible at review time.
    for artifact_id, body in artifact_bodies.items():
        if artifact_id in handled or artifact_id == "graph_state":
            continue
        add(artifact_id, artifact_id.replace("_", " ").title(), _read_generic(body))

    return PhaseReading(
        phase=phase,
        headline=_headline_for_phase(phase, sections),
        sections=sections,
    )


def _headline_for_phase(phase: str, sections: list[ReadingSection]) -> str:
    if not sections:
        return "Nothing to read yet — this phase has not produced artifacts."
    focus = {
        "intake": "Check the profile matches your idea before approving.",
        "constitution": "This is the film's creative contract — read it fully.",
        "development": "Read the treatment and every scene's dramatic function.",
        "script": "Read the screenplay. This is what gets shot.",
        "visual_dev": "These prompts define every reference image.",
        "shot_bible": "Every row becomes one generated clip — check durations and coverage.",
        "gen_planning": "Review prompts and cost before authorizing generation.",
        "generation": "Verify prompts and delivered outputs per shot.",
        "qc": "Read the validation findings before signing off.",
        "post": "Check the assembly order and transitions.",
        "delivery": "Final check: everything the package ships with.",
    }.get(phase, "Read the phase output before approving.")
    return f"READ BEFORE APPROVING — {focus}"


# ── per-artifact formatters ────────────────────────────────────────────


def _read_profile(body: dict[str, Any]) -> str:
    identity = body.get("identity", {}) if isinstance(body.get("identity"), dict) else {}
    lines = [
        f"Title:          {identity.get('title', '')}",
        f"Film type:      {body.get('film_type', '')}",
        f"Target runtime: {body.get('target_runtime_seconds', '?')}s",
        f"Aspect ratio:   {body.get('aspect_ratio', '')}",
        f"Delivery:       {', '.join(str(m) for m in body.get('delivery_modes', []) or [])}",
    ]
    budget = body.get("budget_cap_usd")
    lines.append(f"Budget cap:     {'none' if budget in (None, '') else f'${budget}'}")
    return "\n".join(lines)


def _read_constitution(body: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in (
        "theme",
        "tone",
        "emotional_promise",
        "visual_language",
        "camera_philosophy",
        "quality_bar",
    ):
        value = body.get(key)
        if value:
            lines.append(f"{key.replace('_', ' ').title()}:")
            lines.append(f"  {value}")
    truths = body.get("character_truths")
    if isinstance(truths, list) and truths:
        lines.append("Character Truths:")
        for truth in truths:
            if isinstance(truth, dict):
                lock = " (locked)" if truth.get("must_not_change") else ""
                character = truth.get("character_id", "?")
                lines.append(f"  • {character}: {truth.get('truth', '')}{lock}")
    return "\n".join(lines)


def _read_treatment(body: dict[str, Any]) -> str:
    lines: list[str] = []
    text = body.get("text")
    if text:
        lines.append(str(text))
    themes = body.get("themes")
    if isinstance(themes, list) and themes:
        lines.append("")
        lines.append(f"Themes: {', '.join(str(theme) for theme in themes)}")
    act_map = body.get("act_map")
    if isinstance(act_map, dict):
        lines.append("")
        for key, value in act_map.items():
            if key in _SKIP_KEYS or not value:
                continue
            lines.append(f"{key.replace('_', ' ').title()}: {value}")
    return "\n".join(lines)


def _read_scene_list(body: dict[str, Any]) -> str:
    scenes = body.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return _read_generic(body)
    blocks: list[str] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        lines = [f"[{scene.get('scene_id', '?')}]"]
        for key in ("dramatic_function", "emotional_shift", "conflict", "outcome"):
            value = scene.get(key)
            if value:
                lines.append(f"  {key.replace('_', ' ')}: {value}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _read_script(body: dict[str, Any]) -> str:
    scenes = body.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return _read_generic(body)
    blocks: list[str] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        lines = [str(scene.get("scene_heading", scene.get("scene_id", "SCENE")))]
        scene_id = scene.get("scene_id")
        if scene_id:
            lines.append(f"  ({scene_id})")
        lines.append("")
        for action in scene.get("action_lines", []) or []:
            lines.append(f"  {action}")
        for dialogue in scene.get("dialogue", []) or []:
            if not isinstance(dialogue, dict):
                continue
            character = str(dialogue.get("character_id", "")).upper()
            direction = str(dialogue.get("direction", "") or "")
            lines.append("")
            lines.append(f"            {character}" + (f" ({direction})" if direction else ""))
            lines.append(f"        {dialogue.get('line', '')}")
        blocks.append("\n".join(lines))
    total = body.get("total_scenes", len(scenes))
    footer = f"\n\n— {total} scene(s), {body.get('total_dialogue_lines', '?')} dialogue line(s)"
    return "\n\n\n".join(blocks) + footer


def _read_reference_index(body: dict[str, Any]) -> str:
    entries = body.get("entries")
    if not isinstance(entries, list) or not entries:
        return _read_generic(body)
    blocks: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        lines = [
            f"[{entry.get('reference_id', '?')}] "
            f"{entry.get('subject_type', '')}: {entry.get('subject_id', '')} "
            f"({entry.get('asset_type', '')})"
        ]
        prompt = entry.get("prompt_text")
        if prompt:
            lines.append(f"  prompt: {prompt}")
        for key in ("tier", "quality_score", "generation_status", "moderation_risk"):
            value = entry.get(key)
            if value not in (None, "", [], 0):
                lines.append(f"  {key.replace('_', ' ')}: {value}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _read_shot_matrix(body: dict[str, Any]) -> str:
    rows = body.get("rows")
    if not isinstance(rows, list) or not rows:
        return _read_generic(body)
    blocks: list[str] = []
    total_seconds = 0.0
    for row in rows:
        if not isinstance(row, dict):
            continue
        duration = float(row.get("duration_seconds", 0) or 0)
        total_seconds += duration
        characters = ", ".join(str(c) for c in row.get("characters", []) or []) or "none"
        lines = [
            f"[{row.get('shot_id', '?')}]  scene {row.get('scene_id', '?')}  ·  "
            f"{duration:g}s  ·  {row.get('priority', 'standard')} priority",
            f"  story:      {row.get('story_function', '')}",
            f"  camera:     {row.get('camera_profile', '')}"
            + (f" ({row.get('lighting_state')})" if row.get("lighting_state") else ""),
            f"  characters: {characters}",
            f"  where:      {row.get('environment', '')}"
            + (f" / {row.get('environment_state')}" if row.get("environment_state") else ""),
        ]
        chaining = row.get("chaining")
        if isinstance(chaining, dict) and chaining.get("input_frame_ref"):
            lines.append(f"  chained from: {chaining.get('input_frame_ref')}")
        blocks.append("\n".join(lines))
    header = f"{len(blocks)} shot(s), {total_seconds:g}s planned total\n"
    return header + "\n\n".join(blocks)


def _read_prompts(prompts: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for item in prompts:
        header = (
            f"[{item.get('shot_id', '?')}]  {item.get('provider', '')} / "
            f"{item.get('model', '')}  ·  {item.get('duration_seconds', '?')}s"
        )
        prompt = str(item.get("prompt", "")).strip()
        blocks.append(f"{header}\n{_indent(prompt)}")
    return "\n\n".join(blocks) if blocks else "No prompts available yet."


def _read_ledger(body: dict[str, Any]) -> str:
    rows = body.get("rows")
    if not isinstance(rows, list) or not rows:
        return _read_generic(body)
    lines: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "?"))
        line = f"[{row.get('shot_id', '?')}]  {status}"
        outputs = row.get("output_refs") or []
        if outputs:
            line += f"  →  {outputs[0]}"
        reason = row.get("blocking_reason")
        if reason:
            line += f"  ({reason})"
        lines.append(line)
    return "\n".join(lines)


def _read_generic(body: dict[str, Any], indent: int = 0) -> str:
    """Readable fallback for any artifact: nested key/value lines."""
    lines: list[str] = []
    pad = "  " * indent
    for key, value in body.items():
        if key in _SKIP_KEYS or key.startswith("_"):
            continue
        label = key.replace("_", " ")
        if isinstance(value, dict):
            lines.append(f"{pad}{label}:")
            nested = _read_generic(value, indent + 1)
            if nested:
                lines.append(nested)
        elif isinstance(value, list):
            if not value:
                continue
            lines.append(f"{pad}{label}:")
            for item in value:
                if isinstance(item, dict):
                    nested = _read_generic(item, indent + 1)
                    if nested:
                        lines.append(nested)
                        lines.append("")
                else:
                    lines.append(f"{pad}  • {item}")
            while lines and lines[-1] == "":
                lines.pop()
        elif value not in (None, ""):
            lines.append(f"{pad}{label}: {value}")
    return "\n".join(lines)


def _indent(text: str, prefix: str = "  ") -> str:
    return "\n".join(f"{prefix}{line}" for line in text.splitlines())
