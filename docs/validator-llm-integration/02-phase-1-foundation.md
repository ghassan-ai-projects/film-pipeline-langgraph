# Phase 1: Foundation — De-Hardcoding + Schema + Routing

## Goal

Eliminate every hardcoded model ID string in the codebase, add the schema fields validators need for actionable feedback, and establish the model routing profiles validators will use.

## 1. De-Hardcoding Audit (complete — 30 strings across 12 files)

### To fix

| # | File | Current | Replace With |
|---|------|---------|-------------|
| 1 | `validation/validators/__init__.py` | 15× `models=["gemini-flash"]` or `["gpt-5-mini"]` | `model_profile="text_validator"` or `"multimodal_reviewer"` |
| 2 | `validation/impl/scene_continuity.py:26` | `models=["gemini-flash"]` | `model_profile="multimodal_reviewer"` |
| 3 | `validation/impl/reference_usability.py:25` | `models=["gemini-flash"]` | `model_profile="multimodal_reviewer"` |
| 4 | `validation/impl/script_structure.py:25` | `models=["gemini-flash"]` | `model_profile="text_validator"` |
| 5 | `validation/impl/dialogue_voice.py:25` | `models=["gpt-5-mini"]` | `model_profile="text_validator"` |
| 6 | `validation/impl/prompt_readiness.py:25` | `models=["gemini-flash"]` | `model_profile="text_validator"` |
| 7 | `validation/impl/assembly.py:25` | `models=["gemini-flash"]` | `model_profile="text_validator"` |
| 8 | `validation/impl/delivery_completeness.py:34` | `models=["gemini-flash"]` | `model_profile="text_validator"` |
| 9 | `mcp/tools/__init__.py` | 5× `model="google/gemini-3-flash-preview"` | `ModelRouter.resolve("creative_writer")` |
| 10 | `generation/frame_reviewer.py` | `model: str = "gemini-3-flash-preview"` | Inject via caller using `ModelRouter.resolve("visual_reasoner")` |
| 11 | `generation/sheet_reviewer.py` | `model: str = "gemini-3-flash-preview"` | Inject via caller using `ModelRouter.resolve("visual_reasoner")` |
| 12 | `graph/services.py:358` | `"model_id": "openrouter/gemini-flash-1.1"` | `ModelRouter.resolve("cheap_draft")` |

### NOT to fix (provider-specific API model IDs)

| File | Hardcoded | Why kept |
|------|----------|---------|
| `providers/seedance_openrouter.py` | `"imagen-4.0-fast-generate-001"` | Provider API model ID, not a user-facing selection |
| `providers/imagen4_gemini.py` | `"imagen-4.0-fast-generate-001"` | Same reason |

## 2. Schema Changes

### 2a. `ValidationIssue` — Add actionable feedback fields

**File:** `src/film_pipeline/schemas/validation.py`

```python
class ValidationIssue(SchemaBase):
    code: str
    message: str
    severity: str = Field(description="'info' | 'warning' | 'blocking'.")
    suggestion: str = ""           # NEW: exactly what to do to fix it
    affected_entity: str = ""      # NEW: which character/prop/scene
    affected_field: str = ""       # NEW: which field to modify
    affected_shot: str = ""        # NEW: which shot/entry ID
```

All existing code creating `ValidationIssue(code=..., message=..., severity=...)` continues to work because new fields default to `""`.

### 2b. `ValidatorRegistryEntry` — Replace `models` with `model_profile`

**File:** `src/film_pipeline/schemas/registries/validator_registry.py`

```python
class ValidatorRegistryEntry(SchemaBase):
    validator_id: str
    scope: ValidationScope
    modalities: list[ValidationModality] = Field(default_factory=list)
    input_schema: str = ""
    output_schema: str = "validation-report:v1"
    model_profile: str = ""                                 # NEW: resolved via ModelRouter
    thresholds: ValidatorThresholds = Field(default_factory=ValidatorThresholds)
    blocking_conditions: list[str] = Field(default_factory=list)
    warning_conditions: list[str] = Field(default_factory=list)
    enabled: bool = True

    # REMOVED: models: list[str] = Field(default_factory=list)
```

**Migration:** Every `models=["gemini-flash"]` becomes `model_profile="text_validator"` (or `"multimodal_reviewer"` for multimodal validators). The `models` field is removed — no dual-field transition period.

## 3. ModelRouter New Profiles

**File:** `src/film_pipeline/agents/model_routing/__init__.py`

Add two profiles to `_DEFAULT_PROFILES`:

```python
"multimodal_reviewer": {
    "primary": "google/gemini-3-flash-preview",  # supports image+text
    "fallback": "deepseek/deepseek-chat",         # text-only fallback
    "max_tokens": 4096,
    "temperature": 0.2,
},
"text_validator": {
    "primary": "deepseek/deepseek-chat",
    "fallback": "google/gemini-3-flash-preview",
    "max_tokens": 4096,
    "temperature": 0.1,
},
```

**Profile assignments:**

| Validator | Profile |
|-----------|---------|
| scene_continuity | `multimodal_reviewer` |
| reference_usability | `multimodal_reviewer` |
| script_structure | `text_validator` |
| dialogue_voice | `text_validator` |
| prompt_readiness | `text_validator` |
| assembly | `text_validator` |
| delivery_completeness | `text_validator` |
| All other MVP validators (logline, treatment, character-dossier, etc.) | `text_validator` or `multimodal_reviewer` depending on modality |

## 4. Update MVP_VALIDATORS Entries

**File:** `src/film_pipeline/validation/validators/__init__.py`

Every entry changes `models=[...]` → `model_profile="..."`:

```python
# Before
ValidatorRegistryEntry(
    validator_id="scene-writing-validator",
    ...
    models=["gemini-flash", "gpt-5-mini"],
    ...
)

# After
ValidatorRegistryEntry(
    validator_id="scene-writing-validator",
    ...
    model_profile="text_validator",
    ...
)
```

The 8 validators with `modalities` containing `IMAGE` or `VIDEO` get `model_profile="multimodal_reviewer"`. All text-only validators get `model_profile="text_validator"`.

## 5. Update Validator Impl `__init__` Methods

**Files:** `src/film_pipeline/validation/impl/*.py` (7 files)

Each validator's `__init__` creates a `ValidatorRegistryEntry` with `models=[...]`. Change to `model_profile="..."`.

```python
# Before (in scene_continuity.py)
entry = ValidatorRegistryEntry(
    validator_id="scene-continuity-validator",
    ...
    models=["gemini-flash"],
    ...
)

# After
entry = ValidatorRegistryEntry(
    validator_id="scene-continuity-validator",
    ...
    model_profile="multimodal_reviewer",
    ...
)
```

## 6. De-Hardcode MCP Tools

**File:** `src/film_pipeline/mcp/tools/__init__.py`

The 5 tools that hardcode model IDs need to resolve through the router. This requires the MCP tools to have access to a `ModelRouter` instance.

```python
# Before
tool_params = {
    "model": "google/gemini-3-flash-preview",
    ...
}

# After
from film_pipeline.agents.model_routing import ModelRouter
router = ModelRouter()  # or injected
tool_params = {
    "model": router.resolve("creative_writer"),
    ...
}
```

The router can be accessed through `StudioRuntime` → `GraphServices` → `ModelRouter`, or instantiated directly (defaults are good enough for MCP tools).

## 7. De-Hardcode Frame/Sheet Reviewers

**Files:** `src/film_pipeline/generation/frame_reviewer.py`, `src/film_pipeline/generation/sheet_reviewer.py`

Change from default parameter to required parameter:

```python
# Before
class FrameReviewer:
    def __init__(self, model: str = "gemini-3-flash-preview"):
        self.model = model

# After
class FrameReviewer:
    def __init__(self, model: str):  # required — caller resolves via router
        self.model = model
```

Callers update:

```python
# Before
reviewer = FrameReviewer()

# After
from film_pipeline.agents.model_routing import ModelRouter
router = ModelRouter()
reviewer = FrameReviewer(model=router.resolve("visual_reasoner"))
```

## 8. De-Hardcode services.py

**File:** `src/film_pipeline/graph/services.py` (line ~358)

```python
# Before
"model_id": "openrouter/gemini-flash-1.1",

# After
"model_id": self._router.resolve("cheap_draft"),
```

## 9. Tests

### 9a. Model router profile tests

```python
# tests/unit/agents/model_routing/test_routing.py
def test_multimodal_reviewer_profile():
    router = ModelRouter()
    assert "gemini" in router.resolve("multimodal_reviewer").lower()

def test_text_validator_profile():
    router = ModelRouter()
    assert "deepseek" in router.resolve("text_validator").lower()

def test_multimodal_fallback_is_text_only():
    router = ModelRouter()
    fallback = router.resolve("multimodal_reviewer", prefer_cheap=True)
    assert "deepseek" in fallback.lower()
```

### 9b. Schema migration tests

```python
# tests/unit/validation/test_schema_migration.py
def test_validation_issue_defaults():
    issue = ValidationIssue(code="test", message="msg")
    assert issue.suggestion == ""
    assert issue.affected_entity == ""
    assert issue.affected_field == ""
    assert issue.affected_shot == ""

def test_validator_registry_entry_no_models_field():
    entry = ValidatorRegistryEntry(
        validator_id="test",
        scope=ValidationScope.ARTIFACT,
        model_profile="text_validator",
    )
    assert entry.model_profile == "text_validator"
    # assert that 'models' attribute does not exist
    with pytest.raises(AttributeError):
        _ = entry.models
```

### 9c. Verify zero hardcoded model strings

```python
# tests/unit/validation/test_no_hardcoded_models.py
def test_no_hardcoded_model_strings_in_validators():
    """Grep for model ID strings in validator code."""
    # This is a manual verification step, not a unit test per se.
    # Run: rg '"gemini' src/film_pipeline/validation/  # should return 0 results
    # Run: rg '"gpt-' src/film_pipeline/validation/     # should return 0 results
```

## 10. Verification Checklist

- [ ] `make ci-check` passes (ruff format + lint + mypy strict + tests)
- [ ] `rg '"gemini' src/film_pipeline/validation/` returns 0 results
- [ ] `rg '"gpt-' src/film_pipeline/validation/` returns 0 results
- [ ] `rg 'models=\[' src/film_pipeline/validation/` returns 0 results
- [ ] All 7 validators construct without errors
- [ ] `MVP_VALIDATORS` entries all have `model_profile` set
- [ ] `ModelRouter.resolve("text_validator")` works
- [ ] `ModelRouter.resolve("multimodal_reviewer")` works
- [ ] Existing tests pass unchanged (backward compat)

## Risks

| Risk | Mitigation |
|------|-----------|
| Removing `models` field breaks external code that reads it | `models` was never referenced outside `ValidatorRegistryEntry.__init__`. It was a dead field carrying stale data. |
| MCP tools can't access ModelRouter | MCP tools run inside `StudioRuntime` which has `GraphServices`. Access through the runtime. |
| FrameReviewer/SheetReviewer break without default | Search for all instantiation sites. Update each to pass model via router. |

## Dependencies

- Phase 2 (prompt design) depends on this phase being complete — templates use `model_profile`
- Phase 4 (BaseValidator LLM) depends on schema changes being in place
- All subsequent phases depend on model routing profiles existing
