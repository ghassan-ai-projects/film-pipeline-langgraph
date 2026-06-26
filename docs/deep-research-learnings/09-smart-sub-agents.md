# Making Sub-Agents Smarter — Tool-Driven Specialists

## The Core Problem

FPL's agents are *good parsers* but *bad agents*. They:
- Fill a template with context
- Call the LLM once
- Parse the JSON output into Pydantic models
- Return the result

But they can't:
- Self-revise when output is weak
- Ask for missing context during writing
- Search for references or conventions
- Validate their own work before returning
- Signal when they're stuck and need help

ODR's agents do all five of these through tools. The fix is simple: **keep the agents, give them tools.**

## The Pattern: Tool-Bound Specialist

Each specialist agent gets a curated set of tools relevant to its domain:

```python
class SpecialistAgent(BaseAgent):
    """Agent with domain-specific tools for self-improvement."""

    tools: list  # Domain-specific tools
    max_revision_rounds: int = 3

    def execute(self, model_output: dict) -> dict:
        # Parse model output into Pydantic model
        ...

    def run(self, state, kb_context, task, model_output):
        """Full lifecycle with optional self-revision via tools."""
        result = self.execute(model_output)

        # NEW: self-revision loop
        if hasattr(self, 'tools') and self.tools:
            for round_num in range(self.max_revision_rounds):
                self_assessment = self._assess_quality(result, state)
                if self_assessment["satisfied"]:
                    break
                # Run revision with feedback from self-assessment
                revision_output = self._revise(result, self_assessment["feedback"], state)
                result = self.execute(revision_output)

        if not self.validate(result):
            raise ValueError(f"Agent '{self.contract.agent_id}' produced invalid output.")
        return result
```

## Concrete Agent Tools

### ScreenwriterAgent Tools

```python
screenwriter_tools = [
    check_scene_continuity,      # "Does scene 3 follow from scene 2?"
    diagnose_dialogue_voice,     # "Is Mara's voice consistent across scenes?"
    find_pacing_issue,           # "Is act 2 dragging?"
    revise_scene,                # "Rewrite scene 5 with this feedback"
    propose_alternative_beat,    # "Try a different dramatic beat for scene 7"
    signal_draft_complete,       # "I'm satisfied with this script"
]
```

**Self-revision loop**: After writing, the screenwriter calls `check_scene_continuity` on every scene pair. If scene 3 feels disconnected from scene 2, it calls `revise_scene` with the specific gap. It loops until all continuity checks pass or max rounds exhausted.

### ConstitutionAgent Tools

```python
constitution_tools = [
    validate_theme_coherence,     # "Does this theme hold across all character truths?"
    stress_test_emotional_promise,# "Will audiences actually feel this?"
    check_visual_language_consistency, # "Do camera philosophy and visual language align?"
    search_film_theory,           # Optional: research film theory references
    signal_constitution_complete,
]
```

**Self-revision loop**: After defining the constitution, calls `validate_theme_coherence` to verify every character truth supports the theme. If not, revises.

### ShotBibleAgent Tools

```python
shot_bible_tools = [
    validate_shot_scene_mapping,   # "Does every shot map to a real scene?"
    check_coverage_completeness,   # "Are all coverage angles covered?"
    estimate_shot_feasibility,     # "Can this 15-second steadicam shot actually work?"
    balance_duration_pacing,       # "Is the pacing right for target runtime?"
    adjust_camera_for_emotion,     # "Change camera profile for emotional beat"
    signal_shot_bible_complete,
]
```

**Self-revision loop**: After building the shot matrix, calls `validate_shot_scene_mapping` to ensure every shot references a valid scene. If a shot references `scene_id: "sc_999"` that doesn't exist, it fixes it.

### OrchestratorAgent Tools (already recommended in 04)

```python
orchestrator_tools = [
    creative_reflection,     # Mandatory: pause and assess
    approve_phase,           # Decision: advance
    request_revision,        # Decision: revise with specific feedback
    escalate_to_human,       # Decision: stuck, need human
]
```

## How It Changes the Execution Flow

### Before (Current)
```
Phase starts → agent runs ONCE → returns JSON → orchestrator reviews → approve/revise
                                                              ↓
                                                   If revise: run agent FRESH
                                                   (loses all context, starts over)
```

### After (With Tools)
```
Phase starts → agent runs with tools:
    Draft 1 → self-checks → "scene 3 pacing is off"
    Draft 2 → revises scene 3 → self-checks → "all scenes consistent"
    Draft 3 → signals complete → returns final output

Orchestrator reviews final output (which has been self-improved)
    → Approve: already high quality
    → Revise: specific issue the agent couldn't fix itself
        → Agent runs revision with orchestrator feedback + tool access
```

**Key difference**: The agent self-improves before the orchestrator sees it. The orchestrator only sees output that the agent is already confident about.

## Implementation: What Changes in Code

### Step 1: Add Tools Module

```python
# agents/tools/screenwriter_tools.py
from langchain_core.tools import tool

@tool
def check_scene_continuity(
    scene_a_id: str,
    scene_a_summary: str,
    scene_b_id: str,
    scene_b_summary: str,
) -> str:
    """Check if scene B naturally follows scene A in narrative flow."""
    # This is a lightweight check — uses the same LLM instance
    # but with a focused, structured prompt
    return f"Continuity check {scene_a_id} → {scene_b_id}: {'PASS' if passes else 'ISSUE: ' + issue}"

@tool
def revise_scene(
    scene_id: str,
    issue: str,
    constraints: str,
) -> str:
    """Revise a specific scene based on identified issues."""
    # Generates a revised version of the scene with the fix
    ...
```

### Step 2: Extend BaseAgent with Tool Support

```python
# agents/base.py
class BaseAgent(ABC):
    contract: AgentRegistration
    tools: list = []  # NEW: domain-specific tools
    max_self_revision_rounds: int = 3  # NEW

    def run(self, state, kb_context, task, model_output):
        """Full lifecycle: prepare → execute → [self-revise] → validate."""
        _inputs = self.prepare(state, kb_context, task)
        result = self.execute(model_output)

        # NEW: self-revision loop
        for round_num in range(self.max_self_revision_rounds):
            assessment = self.assess_quality(result, state, kb_context)
            if assessment.get("satisfied", True):
                break
            revision_model_output = self.invoke_revision(
                result, assessment["feedback"], state, kb_context
            )
            if revision_model_output is None:
                break  # Can't revise — accept current
            result = self.execute(revision_model_output)

        if not self.validate(result):
            raise ValueError(f"Agent '{self.contract.agent_id}' produced invalid output.")
        return result

    def assess_quality(self, result, state, kb_context) -> dict:
        """Self-assess output quality. Override to add domain checks."""
        return {"satisfied": True}  # Default: no self-assessment

    def invoke_revision(self, result, feedback, state, kb_context) -> dict | None:
        """Invoke LLM to revise based on feedback. Override to use tools."""
        return None  # Default: no self-revision
```

### Step 3: Add Self-Assessment to ScreenwriterAgent

```python
class ScreenwriterAgent(BaseAgent):
    max_self_revision_rounds = 3

    def assess_quality(self, result, state, kb_context):
        """Self-assess the script before returning."""
        script = result["script"]
        issues = []

        # Check 1: Scene continuity
        for i in range(len(script.scenes) - 1):
            current = script.scenes[i]
            next_scene = script.scenes[i + 1]
            continuity = check_scene_continuity(
                current.scene_id,
                str(current.scene_heading),
                next_scene.scene_id,
                str(next_scene.scene_heading)
            )
            if "ISSUE" in continuity:
                issues.append(continuity)

        # Check 2: Dialogue consistency
        characters = set()
        for scene in script.scenes:
            for dialogue in scene.dialogue:
                characters.add(dialogue.character_id)

        for char_id in characters:
            char_scenes = [
                s for s in script.scenes
                if any(d.character_id == char_id for d in s.dialogue)
            ]
            if len(char_scenes) > 1:
                # Check voice consistency across scenes
                voice_check = diagnose_dialogue_voice(char_id, char_scenes)
                if "ISSUE" in voice_check:
                    issues.append(voice_check)

        if not issues:
            return {"satisfied": True}

        return {
            "satisfied": False,
            "feedback": "\n".join(issues),
            "issue_count": len(issues),
        }

    def invoke_revision(self, result, feedback, state, kb_context):
        """Revise the script with specific feedback."""
        # This calls the LLM again but with:
        # 1. The current script as context
        # 2. The specific issues to fix
        # 3. A "revise, don't regenerate" instruction
        revision_prompt = self._build_revision_prompt(result, feedback, state)
        return self._call_model(revision_prompt)  # Uses PromptRunner
```

### Step 4: Give the Orchestrator Visibility Into the Process

```python
# The handoff record now includes self-revision metadata
handoff = {
    "agent_id": "screenwriter-agent",
    "phase": "script",
    "self_revision_rounds": 2,  # NEW
    "self_assessment_issues": [  # NEW
        "scene_003 → scene_004: emotional shift too abrupt",
        "mara: dialogue voice inconsistent between sc_001 and sc_005"
    ],
    "quality_score": 4,  # NEW: agent's own quality assessment
    ...
}
```

## What This Solves (Without Removing Agents)

| Problem | Before | After |
|---------|--------|-------|
| Weak first draft reaches orchestrator | Yes | No — 3 rounds of self-revision first |
| Agent can't fix specific issues | Regenerates everything | Tool-driven targeted revision |
| Revision feedback is vague | "Improve the script" | "Fix scene 3 pacing, it's too slow" |
| Orchestrator wastes time on obvious issues | Reviews draft 1 | Reviews polished draft 3 |
| No quality signal from agents | Just produce output | Self-scored with issue list |
| Agent output is a black box | Just JSON | JSON + revision history + issues |

## Phased Rollout

### Phase 1: Give ScreenwriterAgent self-revision (highest impact)
The screenwriter produces the most complex output (StoryBible + Script). Self-revision here catches continuity, dialogue, and pacing issues before they propagate to shot_bible.

### Phase 2: Give ShotBibleAgent self-revision
The shot matrix has many cross-references (scene_id, environment_id, character_id). Self-revision validates these before gen_planning.

### Phase 3: Give OrchestratorAgent tool-calling
Instead of raw JSON decisions, the orchestrator uses `creative_reflection`, `approve_phase`, `request_revision` tools.

### Phase 4: Add tools to remaining agents
ConstitutionAgent, DevelopmentAgent, VisualDevAgent, GenPlannerAgent get domain-specific self-revision.

## Cost Impact

Self-revision adds LLM calls. Mitigation:
1. **Cheap model for self-assessment**: Use gemini-flash or deepseek (not the primary creative model) for assessment calls
2. **Early exit**: Agent stops revising as soon as self-assessment passes
3. **Configurable max rounds**: Default 3, override to 0 for draft mode
4. **Parallel assessment**: Check all scenes in parallel using `asyncio.gather`
