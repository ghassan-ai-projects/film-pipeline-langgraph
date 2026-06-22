# Phase 5: Graph Wiring — Pass Services Through Validator Dispatch

## Goal

Pass `GraphServices` (ModelAdapter, ModelRouter, PromptTemplateRegistry) through the validator dispatch chain so validators can access them. Update `repair_phase_node` to include `suggestion` in feedback strings.

## Current State

```python
# In nodes.py
def _run_validators(state):
    services = _get_services(state)
    # ... collect artifacts ...
    _run_script_validators(artifact_data, issues, state)  # no services passed

def _run_script_validators(artifact_data, issues, state):
    for vcls in (ScriptStructureValidator, DialogueVoiceValidator):
        instance = vcls()           # fresh instance, no services
        report = instance.run(artifact)  # runs rule-based only
```

Validators are constructed with `vcls()` — no dependency injection. They can never access `ModelAdapter` or `ModelRouter`.

## Target

```python
def _run_validators(state):
    services = _get_services(state)
    if services is None:
        return
    # ... collect artifacts ...
    _run_script_validators(artifact_data, issues, state, services)

def _run_script_validators(artifact_data, issues, state, services):
    for vcls in (ScriptStructureValidator, DialogueVoiceValidator):
        instance = vcls()
        instance.set_services(
            adapter=services.model_adapter,
            router=services.model_router,
            template_registry=services.prompt_runner.template_registry,
        )
        report = instance.run(artifact)
```

## Changes

### 1. Pass `services` through all `_run_*_validators()` functions

**File:** `src/film_pipeline/graph/nodes.py`

Every `_run_*_validators()` function signature changes:

```python
# Before
def _run_script_validators(artifact_data, issues, state):
def _run_reference_validators(artifact_data, issues, state):
def _run_prompt_validators(artifact_data, issues, state):
def _run_continuity_validators(artifact_data, issues, state):
def _run_assembly_validators(artifact_data, issues, state):
def _run_delivery_validators(artifact_data, issues, state):

# After
def _run_script_validators(artifact_data, issues, state, services):
def _run_reference_validators(artifact_data, issues, state, services):
def _run_prompt_validators(artifact_data, issues, state, services):
def _run_continuity_validators(artifact_data, issues, state, services):
def _run_assembly_validators(artifact_data, issues, state, services):
def _run_delivery_validators(artifact_data, issues, state, services):
```

Each function injects services into validator instances:

```python
def _run_script_validators(artifact_data, issues, state, services):
    from film_pipeline.validation.impl.dialogue_voice import DialogueVoiceValidator
    from film_pipeline.validation.impl.script_structure import ScriptStructureValidator

    raw = next(iter(artifact_data.values()), {})
    artifact = raw if isinstance(raw, dict) else {}
    for vcls in (ScriptStructureValidator, DialogueVoiceValidator):
        try:
            instance = vcls()
            instance.set_services(
                adapter=services.model_adapter,
                router=services.model_router,
                template_registry=services.prompt_runner.template_registry,
                prompt_runner=services.prompt_runner,
            )
            report = instance.run(artifact)
        except Exception:
            continue
        _append_validator_report(report, issues, state)
```

### 2. Add `model_adapter` and `model_router` to `GraphServices`

**File:** `src/film_pipeline/graph/services.py`

These may already exist on `GraphServices`. If not, add them:

```python
@dataclass
class GraphServices:
    artifact_store: ArtifactStore
    agent_registry: AgentRegistry
    prompt_runner: PromptRunner
    model_adapter: ModelAdapter          # Ensure this exists
    model_router: ModelRouter            # Ensure this exists
    validator_registry: ValidatorRegistry
```

### 3. Update `repair_phase_node` to include `suggestion` in feedback

**File:** `src/film_pipeline/graph/nodes.py`

Currently `repair_phase_node` builds feedback like:
```
REPAIR ROUND 2: Your previous output was REJECTED.
Issues to fix:
[character_state_mismatch] Character 'hero' state changed...
```

Add the suggestion field:

```python
def _build_repair_feedback(issues: list[dict[str, Any]]) -> str:
    """Build a feedback string from validation issues, including suggestions."""
    lines = ["Your previous output was REJECTED. Issues to fix:\n"]
    for i, issue in enumerate(issues, 1):
        code = issue.get("code", "unknown")
        message = issue.get("message", "")
        suggestion = issue.get("suggestion", "")
        lines.append(f"{i}. [{code}] {message}")
        if suggestion:
            lines.append(f"   SUGGESTION: {suggestion}")
            # Also include affected entity/field for routing
            entity = issue.get("affected_entity", "")
            field = issue.get("affected_field", "")
            shot = issue.get("affected_shot", "")
            if entity or field or shot:
                details = []
                if entity:
                    details.append(f"entity={entity}")
                if field:
                    details.append(f"field={field}")
                if shot:
                    details.append(f"shot={shot}")
                lines.append(f"   AFFECTS: {', '.join(details)}")
    return "\n".join(lines)
```

The `repair_phase_node` already has a pattern for building `_repair_feedback`. Update it to use `_build_repair_feedback()` with the full issue dicts (not just extracting code+message).

## Tests

### File: `tests/unit/graph/test_validator_wiring.py`

```python
def test_validator_receives_services():
    """Validator.set_services() is called during _run_script_validators."""
    ...

def test_repair_feedback_includes_suggestion():
    """_build_repair_feedback() includes suggestion, affected_entity, etc."""
    issues = [{
        "code": "test_code",
        "message": "something wrong",
        "suggestion": "fix it this way",
        "affected_entity": "hero",
        "affected_field": "dialogue",
        "affected_shot": "s_001",
    }]
    feedback = _build_repair_feedback(issues)
    assert "SUGGESTION: fix it this way" in feedback
    assert "entity=hero" in feedback
    assert "field=dialogue" in feedback
    assert "shot=s_001" in feedback


def test_repair_feedback_without_suggestion():
    """Issues without suggestion still produce usable feedback."""
    issues = [{
        "code": "test_code",
        "message": "something wrong",
    }]
    feedback = _build_repair_feedback(issues)
    assert "[test_code] something wrong" in feedback
    assert "SUGGESTION:" not in feedback


def test_repair_feedback_multiple_issues():
    """Multiple issues are all included."""
    issues = [
        {"code": "c1", "message": "msg1", "suggestion": "fix1"},
        {"code": "c2", "message": "msg2", "suggestion": "fix2"},
    ]
    feedback = _build_repair_feedback(issues)
    assert "1. [c1] msg1" in feedback
    assert "2. [c2] msg2" in feedback
    assert "SUGGESTION: fix1" in feedback
    assert "SUGGESTION: fix2" in feedback
```

## Verification Checklist

- [ ] All `_run_*_validators()` accept `services` parameter
- [ ] Every validator gets `set_services()` called before `run()`
- [ ] `GraphServices` has `model_adapter` and `model_router` attributes
- [ ] `repair_phase_node` includes `suggestion` in feedback strings
- [ ] Feedback includes `affected_entity`, `affected_field`, `affected_shot`
- [ ] Existing tests pass with new function signatures
- [ ] `make ci-check` passes

## Risks

| Risk | Mitigation |
|------|-----------|
| `_run_*_validators()` functions also called from QC synthesis | QC synthesis doesn't call these — it calls `_run_validators()` which is the entry point. Only the signature of `_run_validators()` calls change. |
| `GraphServices` might not have `model_adapter`/`model_router` yet | Check during implementation. If missing, add them as constructor params. |
| Repair feedback with suggestions could be very long | Truncate suggestions at 200 chars. The full suggestion is in the ValidationIssue stored in state. |
