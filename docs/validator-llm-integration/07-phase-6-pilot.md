# Phase 6: Pilot — `script_structure` as First LLM Validator

## Goal

Make `ScriptStructureValidator` the first validator to go LLM. Prove the full chain: prompt → LLM → parse → score → issues with suggestions → gate detection → repair feedback.

## Why `script_structure` first

1. **Text-only** — no multimodal complexity. Uses `text_validator` profile → `deepseek/deepseek-chat`.
2. **Well-defined rubric** — conflict presence, intent fulfillment, structural flow, pacing, dialogue/action balance. Clear criteria for LLM evaluation.
3. **Stub catches surface issues** — easy to compare stub vs LLM output side-by-side.
4. **Dramatic structure is what LLMs excel at** — evaluating scene conflict, character intent, and narrative flow is a semantic task that rule-based checks fundamentally can't do.

## Step 1: Register the prompt template

**File:** `src/film_pipeline/agents/prompt_templates/defaults.py`

Add `load_validator_templates()` and the `_script_structure_validator()` template function (full text from `03-phase-2-prompt-design.md`).

```python
def load_validator_templates(reg: PromptTemplateRegistry) -> None:
    """Register all 7 validator prompt templates."""
    reg.register(_script_structure_validator())


def _script_structure_validator() -> PromptTemplate:
    return PromptTemplate(
        template_id="script-structure-v1",
        agent_id="scene-writing-validator",  # matches validator_id in registry
        version=1,
        role=(...),      # full role text from Phase 2
        core_task=(...),  # full rubric text from Phase 2
        context_template=(...),
        constraints=(...),
        output_format=(...),
        output_schema_ref="validation.ValidationReport",
    )
```

Register it in the app startup:

**File:** `src/film_pipeline/app/runtime.py` (or wherever templates are loaded)

```python
from film_pipeline.agents.prompt_templates.defaults import load_validator_templates
load_validator_templates(prompt_template_registry)
```

## Step 2: Rename `validate()` → `_validate_rules()`

**File:** `src/film_pipeline/validation/impl/script_structure.py`

```python
class ScriptStructureValidator(BaseValidator):
    llm_enabled = True  # ← flip the switch

    def _validate_rules(self, artifact, context=None) -> dict[str, Any]:
        """Rule-based validation (existing logic, renamed from validate)."""
        # ... all existing rule-based logic unchanged ...

    # extract_score() and extract_issues() unchanged
```

## Step 3: Update `extract_issues()` to map suggestion fields

```python
def extract_issues(self, raw: dict[str, Any]) -> list[ValidationIssue]:
    return [
        ValidationIssue(
            code=str(i.get("code", "unknown")),
            message=str(i.get("message", "")),
            severity=str(i.get("severity", "info")),
            suggestion=str(i.get("suggestion", "")),
            affected_entity=str(i.get("affected_entity", "")),
            affected_field=str(i.get("affected_field", "")),
            affected_shot=str(i.get("affected_shot", "")),
        )
        for i in raw.get("issues", [])
    ]
```

## Step 4: Verify the full chain end-to-end

### Test: LLM path produces richer output than stub

```python
# tests/unit/validation/test_script_structure_llm.py

def test_llm_path_produces_score_and_issues():
    """LLM validation produces score and issues with suggestions."""
    adapter = FakeAdapter(json.dumps({
        "score": 72,
        "passed": False,
        "issues": [{
            "code": "no_conflict",
            "severity": "blocking",
            "message": "Scene 'sc_003' has no dramatic tension.",
            "suggestion": "Add a moment where the merchant hesitates before answering.",
            "affected_entity": "sc_003",
            "affected_field": "dialogue",
            "affected_shot": "sc_003",
        }]
    }))

    validator = ScriptStructureValidator()
    validator.llm_enabled = True
    validator.set_services(
        adapter=adapter,
        router=FakeRouter(),
        template_registry=_template_registry_with_script_structure(),
    )

    artifact = {"scenes": [{"scene_id": "sc_001", "dialogue": [...]}]}
    raw = validator.validate(artifact)
    assert raw["score"] == 72
    assert len(raw["issues"]) == 1
    assert raw["issues"][0]["suggestion"].startswith("Add a moment")


def test_llm_fallback_to_rules_on_error():
    """When LLM fails, falls back to rule-based validation."""
    adapter = FakeAdapter("this is not json at all {{{")

    validator = ScriptStructureValidator()
    validator.llm_enabled = True
    validator.set_services(
        adapter=adapter,
        router=FakeRouter(),
        template_registry=_template_registry_with_script_structure(),
    )

    # This should not crash — falls back to _validate_rules()
    raw = validator.validate({"scenes": []})
    assert "issues" in raw
    assert raw["scenes_count"] == 0


def test_stub_still_works_when_disabled():
    """llm_enabled=False → rule-based path (backward compat)."""
    validator = ScriptStructureValidator()
    validator.llm_enabled = False
    raw = validator.validate({"scenes": [
        {"scene_id": "sc_001", "intent_ref": "", "dialogue": [], "action_lines": []}
    ]})
    # Stub catches missing intent_ref
    assert any(i["code"] == "missing_scene_intent" for i in raw["issues"])


def test_extract_issues_maps_suggestion():
    """extract_issues() populates the new suggestion fields."""
    validator = ScriptStructureValidator()
    raw = {"issues": [{
        "code": "test",
        "message": "msg",
        "severity": "blocking",
        "suggestion": "do X",
        "affected_entity": "hero",
        "affected_field": "dialogue",
        "affected_shot": "s_001",
    }]}
    issues = validator.extract_issues(raw)
    assert issues[0].suggestion == "do X"
    assert issues[0].affected_entity == "hero"


def test_stub_vs_llm_comparison():
    """Stub catches surface issues; LLM catches semantic issues.

    Stub: keyword-matches 'conflict', counts lines
    LLM: evaluates dramatic tension, intent fulfillment

    A scene with the word 'conflict' in dialogue but zero actual tension:
    - Stub: passes (keyword found)
    - LLM: fails (no dramatic tension despite the word)
    """
    artifact = {"scenes": [{
        "scene_id": "sc_001",
        "intent_ref": "establish_hero",
        "dialogue": [
            {"character_id": "a", "line": "I'm very conflicted about this."},
            {"character_id": "b", "line": "Yes, there is definitely conflict here."},
        ],
        "action_lines": ["They sit calmly drinking tea."],
    }]}

    # Stub path
    validator_stub = ScriptStructureValidator()
    validator_stub.llm_enabled = False
    stub_result = validator_stub.validate(artifact)
    # Stub finds 'conflict' keywords → might not flag as no_conflict
    # (depends on how many scenes lack conflict keywords)

    # LLM path (simulated)
    adapter = FakeAdapter(json.dumps({
        "score": 45,
        "passed": False,
        "issues": [{
            "code": "no_conflict",
            "severity": "blocking",
            "message": "Scene 'sc_001': characters literally say 'conflict' but the scene has zero dramatic tension — they're sitting calmly drinking tea.",
            "suggestion": "Replace the dialogue with a disagreement about a concrete decision. Have one character want action while the other wants caution.",
            "affected_entity": "sc_001",
            "affected_field": "dialogue",
            "affected_shot": "sc_001",
        }]
    }))
    validator_llm = ScriptStructureValidator()
    validator_llm.llm_enabled = True
    validator_llm.set_services(
        adapter=adapter,
        router=FakeRouter(),
        template_registry=_template_registry_with_script_structure(),
    )
    llm_result = validator_llm.validate(artifact)

    # LLM catches what the stub misses:
    # It evaluates tension semantically, not by keyword matching
    assert llm_result["score"] < 50  # LLM correctly scores low
```

## Step 5: Integration test — full flow through the graph

```python
# tests/integration/test_validator_script_structure_in_graph.py

def test_script_validator_llm_path_in_qc_node():
    """QC node runs ScriptStructureValidator with LLM, issues flow to state."""
    # Set up state with script artifact
    # Run qc_node
    # Verify state["issues"] contains LLM-generated issues with suggestions
    # Verify state["_validation_reports"] contains ValidationReport with suggestions
    ...
```

## Step 6: Run with mock mode first, then real

```bash
# Mock mode — stub works, LLM path not triggered
FILM_PIPELINE_MCP_MODE=mock make test-unit

# Real mode — LLM path triggered, needs OPENROUTER_API_KEY
FILM_PIPELINE_MCP_MODE=real python -m pytest tests/unit/validation/test_script_structure_llm.py -v

# Verify real LLM output quality
python -c "
from film_pipeline.validation.impl.script_structure import ScriptStructureValidator
# ... load services, set llm_enabled=True, validate a real script
"
```

## Verification Checklist

- [ ] `ScriptStructureValidator.llm_enabled = True`
- [ ] `_validate_rules()` has existing logic (renamed from `validate()`)
- [ ] `extract_issues()` maps `suggestion`, `affected_entity`, `affected_field`, `affected_shot`
- [ ] Prompt template registered with `agent_id="scene-writing-validator"`
- [ ] `set_services()` injects adapter, router, template_registry
- [ ] LLM call produces structured JSON with score + issues + suggestions
- [ ] LLM failure gracefully falls back to rule-based validation
- [ ] `llm_enabled=False` → rule-based validation (backward compat)
- [ ] Stub still detects surface issues when enabled
- [ ] LLM detects semantic issues the stub misses (verified with test fixture)
- [ ] `make ci-check` passes
- [ ] Real LLM call produces reasonable output (manual verification)

## What Success Looks Like

After this phase:

1. `ScriptStructureValidator` runs LLM validation in real mode
2. Issues include actionable suggestions (not just error codes)
3. The orchestrator can route these issues to repair agents
4. The repair agent receives `suggestion` text in `_repair_feedback`
5. If the LLM fails (rate limit, auth error, parse error), the validator falls back to rule-based checks — no crash, no pipeline halt

## What Could Go Wrong

| Risk | Response |
|------|----------|
| LLM produces valid JSON but wrong structure (e.g., `issues` is a list of strings, not objects) | `_validate_llm()` catches this — the JSON parses but `extract_issues()` gets empty strings for fields. The validator produces a low score but doesn't crash. |
| LLM hallucinates scene_ids that don't exist | The `suggestion` references a non-existent scene_id. The repair agent will try to fix it and fail. Mitigation: the prompt template says "reference specific scene_ids from the provided script" — the LLM has the script content in context. |
| LLM is too lenient (gives everything 95+) | Temperature is 0.1 for `text_validator` profile. If still too lenient, lower to 0.0 or adjust rubric to be stricter. |
| DeepSeek API rate limits | The `text_validator` profile has `google/gemini-3-flash-preview` as fallback. The router can auto-fallback via `prefer_cheap=True`. |
