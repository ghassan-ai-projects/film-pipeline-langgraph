# Phase 0 — Quick Wins: Model Profile Routing + Quality Instructions

**Goal:** Fix the two highest-ROI agent output quality issues with zero architectural risk.
These changes touch only prompt templates and one function call in `_run_agent()` — no graph changes.

---

## 0.1 Route Creative Agents to Creative Profiles

### Problem
Every agent currently runs at `temperature: 0.2, max_tokens: 4096` via `operations_triage`.
The `creative_writer` profile (temp 0.7, max_tokens 8192) exists in `model_routing/__init__.py`
but is never used because `_run_agent()` doesn't pass `model_profile=` to `run_from_template()`.

### Files to Modify

| File | Change |
|------|--------|
| `src/film_pipeline/graph/nodes.py:180` | Add `model_profile=` argument to `run_from_template()` call |
| `src/film_pipeline/graph/nodes.py:24-30` | Add `_AGENT_PROFILE_MAP` dict |
| `tests/unit/graph/test_services.py` | Verify profile routing (or new test file) |

### Step-by-Step

**Step 1:** Add agent-to-profile mapping in `nodes.py`, near the top of `_run_agent()`:

```python
# After existing imports, before _run_agent definition (~line 24)

_AGENT_PROFILE_MAP: dict[str, str] = {
    # Creative agents → creative profiles
    "film-constitution-agent": "creative_writer",
    "treatment-agent": "creative_writer",
    "screenwriter-agent": "creative_writer",
    "shot-design-agent": "creative_writer",
    "visual-dev-agent": "creative_writer",
    "reference-strategy-planner": "visual_reasoner",
    # Analytical agents → strict/operational profiles
    "structure-extractor-agent": "strict_validator",
    "intake-classifier-agent": "operations_triage",
    "provider-planning-agent": "operations_triage",
    "clip-validator": "strict_validator",
    "failure-handling-agent": "operations_triage",
}
```

**Step 2:** Modify the `run_from_template()` call (~line 180):

```python
# Current:
model_output, template_id, model_profile = services.prompt_runner.run_from_template(
    template, kb, task, context_vars=context_vars
)

# Target:
resolved_profile = _AGENT_PROFILE_MAP.get(resolved_agent_id, "operations_triage")
model_output, template_id, _ = services.prompt_runner.run_from_template(
    template, kb, task,
    context_vars=context_vars,
    model_profile=resolved_profile,
)
```

**Step 3:** Update the `_record_handoff` call to capture the actual profile used:

```python
# Current (~line 196):
_record_handoff(state, resolved_agent_id, phase, task, route_result, result,
    template_id=template_id, model_profile=model_profile)

# Target:
_record_handoff(state, resolved_agent_id, phase, task, route_result, result,
    template_id=template_id, model_profile=resolved_profile)
```

### Test Cases

```python
# tests/unit/graph/test_agent_profile_routing.py

def test_screenwriter_uses_creative_writer_profile():
    """Verify screenwriter-agent routes to creative_writer (temp 0.7)."""
    assert _AGENT_PROFILE_MAP["screenwriter-agent"] == "creative_writer"

def test_validator_uses_strict_profile():
    """Verify clip-validator routes to strict_validator (temp 0.1)."""
    assert _AGENT_PROFILE_MAP["clip-validator"] == "strict_validator"

def test_unknown_agent_falls_back_to_operations_triage():
    """Verify unrecognized agents get the default profile."""
    assert _AGENT_PROFILE_MAP.get("nonexistent-agent", "operations_triage") == "operations_triage"

def test_all_registered_agents_have_profile_entries():
    """Verify every agent in MVP_AGENTS has a profile map entry."""
    from film_pipeline.agents.mvp import MVP_AGENTS
    from film_pipeline.graph.nodes import _AGENT_PROFILE_MAP
    for agent in MVP_AGENTS:
        assert agent.agent_id in _AGENT_PROFILE_MAP, f"Missing profile for {agent.agent_id}"
```

### Acceptance Criteria
- [ ] `_AGENT_PROFILE_MAP` covers all registered MVP agents
- [ ] Creative agents (screenwriter, constitution, treatment, shot_design, visual_dev) map to `creative_writer` or `visual_reasoner`
- [ ] Validator agents map to `strict_validator`
- [ ] `run_from_template()` receives correct `model_profile=` argument
- [ ] `make ci-check` passes
- [ ] Mock-mode behavior unchanged (mock responses bypass the router)

---

## 0.2 Add Quality Instructions to Creative Templates

### Problem
Role fields are identity-only (~15 tokens): "You are the screenwriter-agent (Screenwriter)."
Chat interfaces wrap prompts in 200+ tokens of quality instructions. Templates need explicit
quality directives so the model knows to be thorough, detailed, and production-ready.

### Files to Modify

| File | Change |
|------|--------|
| `src/film_pipeline/agents/prompt_templates/defaults.py` | Add `quality_instructions` field to `PromptTemplate`, populate for creative agents |
| `src/film_pipeline/agents/prompt_templates/registry.py` | If `PromptTemplate` schema lives here, add field |
| `src/film_pipeline/agents/runner.py` | Render `quality_instructions` in `run_from_template()` |

### Step-by-Step

**Step 1:** Check where `PromptTemplate` is defined. It may be in `runner.py` or a separate schema.

```bash
rg "class PromptTemplate" src/film_pipeline/
```

**Step 2:** Add `quality_instructions` field:

```python
class PromptTemplate(SchemaBase):
    template_id: str
    agent_id: str
    version: int
    role: str
    core_task: str
    context_template: str
    constraints: str
    output_format: str
    output_schema_ref: str = ""
    quality_instructions: str = ""  # NEW — rendered before output_format
```

**Step 3:** Define a base quality instruction string:

```python
_QUALITY_BASE = (
    "QUALITY REQUIREMENTS:\n"
    "- Be thorough and detailed. Never summarize or be brief unless explicitly asked.\n"
    "- Use vivid, sensory, cinematic language appropriate for creative production work.\n"
    "- Make specific, concrete creative choices. Never be vague or generic.\n"
    "- Review your output for internal consistency before finalizing.\n"
    "- Every field in the output schema must be populated — no empty strings or placeholders.\n"
)
```

**Step 4:** Add `quality_instructions=_QUALITY_BASE` to creative templates (5 agents):

- `_film_constitution()` → add `quality_instructions=_QUALITY_BASE`
- `_development_creator()` → add `quality_instructions=_QUALITY_BASE`
- `_screenwriter()` → add `quality_instructions=_QUALITY_BASE`
- `_visual_dev_creator()` → add `quality_instructions=_QUALITY_BASE`
- `_shot_bible_creator()` → add `quality_instructions=_QUALITY_BASE`

**Step 5:** Render `quality_instructions` in `run_from_template()`:

```python
# In runner.py, run_from_template():
rendered_text = template.render(**(context_vars or {}))
if template.quality_instructions:
    rendered_text = f"{rendered_text}\n\n{template.quality_instructions}"
```

### Test Cases

```python
def test_creative_template_has_quality_instructions():
    """Screenwriter template must include quality instructions."""
    template = _screenwriter()
    assert "thorough and detailed" in template.quality_instructions.lower()

def test_validator_template_lacks_quality_instructions():
    """Validators don't need creative quality instructions."""
    template = _structure_extractor()  # or whichever validator template exists
    assert template.quality_instructions == ""

def test_quality_instructions_rendered_in_output():
    """run_from_template() includes quality_instructions in rendered text."""
    template = _screenwriter()
    rendered = template.render(idea="test", **default_context_vars())
    assert "QUALITY REQUIREMENTS" in rendered
```

### Acceptance Criteria
- [ ] `PromptTemplate` has `quality_instructions: str` field with empty default
- [ ] 5 creative templates have populated `quality_instructions`
- [ ] `run_from_template()` renders quality instructions after context
- [ ] Existing template rendering behavior unchanged for non-creative agents
- [ ] `make ci-check` passes

---

## Phase 0 Completion Checklist

- [ ] `_AGENT_PROFILE_MAP` defined with all MVP agents
- [ ] `run_from_template()` receives correct `model_profile=` per agent
- [ ] `PromptTemplate.quality_instructions` field exists
- [ ] 5 creative templates have quality instructions
- [ ] `run_from_template()` renders quality instructions
- [ ] All new tests pass
- [ ] `make ci-check` green
- [ ] Mock-mode behavior unchanged

**Estimated implementation time:** 30-45 minutes
**Risk:** Zero — no graph/runtime changes
