# Phase 4: BaseValidator LLM Lifecycle

## Goal

Add `_validate_llm()` to `BaseValidator` — the shared LLM call lifecycle that all validators use. Add `set_services()` for dependency injection. Add `llm_enabled` mode flag. Keep existing stub logic intact.

## Current State

```python
class BaseValidator(ABC):
    entry: ValidatorRegistryEntry

    @abstractmethod
    def validate(self, artifact, context=None) -> dict[str, Any]: ...
    @abstractmethod
    def extract_score(self, raw) -> float: ...
    @abstractmethod
    def extract_issues(self, raw) -> list[ValidationIssue]: ...

    def run(self, artifact, artifact_refs=None, context=None) -> ValidationReport:
        raw = self.validate(artifact, context)
        score = self.extract_score(raw)
        issues = self.extract_issues(raw)
        # ... build ValidationReport ...
```

Each validator implements `validate()` with rule-based logic. The `run()` method orchestrates: validate → score → issues → report.

## Target

```python
class BaseValidator(ABC):
    entry: ValidatorRegistryEntry
    llm_enabled: bool = False           # NEW: opt-in per validator
    _adapter: ModelAdapter | None = None # NEW: injected via set_services()
    _router: ModelRouter | None = None   # NEW: injected via set_services()
    _template_registry: PromptTemplateRegistry | None = None  # NEW

    def set_services(
        self,
        adapter: ModelAdapter,
        router: ModelRouter,
        template_registry: PromptTemplateRegistry,
    ) -> None: ...

    def validate(self, artifact, context=None) -> dict[str, Any]:
        """Dispatch to stub or LLM path based on llm_enabled."""
        if self.llm_enabled and self._adapter is not None:
            return self._validate_llm(artifact, context)
        return self._validate_rules(artifact, context)

    @abstractmethod
    def _validate_rules(self, artifact, context=None) -> dict[str, Any]:
        """Existing rule-based validation (renamed from validate)."""
        ...

    def _validate_llm(self, artifact, context=None) -> dict[str, Any]:
        """Shared LLM validation lifecycle."""
        # 1. Load prompt template
        # 2. Resolve model
        # 3. Build prompt with artifact + context
        # 4. Call LLM
        # 5. Parse response
        ...

    @abstractmethod
    def extract_score(self, raw) -> float: ...    # unchanged
    @abstractmethod
    def extract_issues(self, raw) -> list[ValidationIssue]: ...  # updated
```

## Key Design Decisions

### Decision 1: `validate()` dispatches, subclasses implement `_validate_rules()`

This means:
- Existing validators rename their `validate()` → `_validate_rules()` (mechanical change)
- `BaseValidator.validate()` becomes the dispatcher
- `_validate_llm()` is implemented once in BaseValidator, not per subclass

**Rejected alternative:** Per-subclass `_validate_llm()`. This would mean 7 copies of the same prompt→LLM→parse flow. Centralizing in `BaseValidator` keeps it DRY.

### Decision 2: `set_services()` injects dependencies, not constructor

This means:
- Validators can be constructed without services (existing `ValidatorCls()` patterns still work)
- Services are injected after construction, before first `validate()` call
- If services aren't set and `llm_enabled=True`, `validate()` falls back to rules + warning

**Rejected alternative:** Constructor injection. Would require updating all 15+ instantiation sites across tests and graph nodes.

### Decision 3: `llm_enabled` is a simple boolean, not env-var controlled

This means:
- Each validator class defaults to `llm_enabled=False`
- The rollout flips it per validator when ready
- No env var (e.g., `VALIDATOR_LLM_MODE`) — that's a global switch that makes incremental rollout impossible

**Rejected alternative:** Env var `VALIDATOR_LLM_MODE=real`. This is a global toggle — can't enable one validator at a time.

## Implementation

### File: `src/film_pipeline/validation/base.py`

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from film_pipeline.schemas._base import ValidationStatus
from film_pipeline.schemas.registries.validator_registry import ValidatorRegistryEntry
from film_pipeline.schemas.validation import ValidationIssue, ValidationReport
from film_pipeline.validation.thresholds import score_to_status


class BaseValidator(ABC):
    """Standard validator lifecycle.

    Subclasses implement _validate_rules() for rule-based checks.
    When llm_enabled=True and services are injected, validate()
    dispatches to _validate_llm() which uses the shared LLM infrastructure
    (ModelRouter, PromptTemplateRegistry, ModelAdapter).
    """

    entry: ValidatorRegistryEntry
    llm_enabled: bool = False

    def __init__(self, entry: ValidatorRegistryEntry) -> None:
        self.entry = entry
        self._adapter: Any = None
        self._router: Any = None
        self._template_registry: Any = None
        self._prompt_runner: Any = None

    # ── Service injection ──────────────────────────────────────────

    def set_services(
        self,
        *,
        adapter: Any = None,
        router: Any = None,
        template_registry: Any = None,
        prompt_runner: Any = None,
    ) -> None:
        """Inject runtime services for LLM validation.

        Args:
            adapter: ModelAdapter instance (required for LLM calls).
            router: ModelRouter instance (required for model resolution).
            template_registry: PromptTemplateRegistry (required for prompt loading).
            prompt_runner: PromptRunner instance (optional, for RCTCO assembly).
        """
        if adapter is not None:
            self._adapter = adapter
        if router is not None:
            self._router = router
        if template_registry is not None:
            self._template_registry = template_registry
        if prompt_runner is not None:
            self._prompt_runner = prompt_runner

    def _has_llm_services(self) -> bool:
        return (
            self._adapter is not None
            and self._router is not None
            and self._template_registry is not None
        )

    # ── Public API ──────────────────────────────────────────────────

    def validate(
        self,
        artifact: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run validation, dispatching to LLM or rules based on configuration."""
        if self.llm_enabled and self._has_llm_services():
            try:
                return self._validate_llm(artifact, context)
            except Exception:
                # Fall back to rules on LLM failure
                import logging
                logging.warning(
                    f"Validator '{self.entry.validator_id}': LLM validation failed, "
                    "falling back to rule-based check."
                )
        return self._validate_rules(artifact, context)

    @abstractmethod
    def _validate_rules(
        self,
        artifact: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Rule-based validation (existing logic)."""
        ...

    # ── LLM validation lifecycle ────────────────────────────────────

    def _validate_llm(
        self,
        artifact: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Shared LLM validation: prompt → model → parse.

        1. Load the prompt template for this validator
        2. Resolve the model via ModelRouter
        3. Build the prompt with artifact content injected
        4. Call the LLM (multimodal or text)
        5. Parse the response into score + issues
        """
        # 1. Load template
        template = self._template_registry.get(
            agent_id=self.entry.validator_id
        )
        if template is None:
            raise RuntimeError(
                f"No prompt template found for validator "
                f"'{self.entry.validator_id}'"
            )

        # 2. Resolve model
        profile = self.entry.model_profile
        if not profile:
            raise RuntimeError(
                f"Validator '{self.entry.validator_id}' has no model_profile set."
            )
        model = self._router.resolve(profile)

        # 3. Build prompt
        ctx = (context or {}) | {"artifact": artifact}
        prompt = self._build_validation_prompt(template, ctx)

        # 4. Call LLM
        is_multimodal = self._needs_multimodal()
        images = self._extract_images(artifact) if is_multimodal else None

        if is_multimodal and images:
            text = self._adapter.chat_multimodal(
                prompt,
                model=model,
                images_b64=images,
                max_tokens=int(template.output_config.get("max_tokens", 4096)),
                temperature=float(template.output_config.get("temperature", 0.2)),
            )
        else:
            text = self._adapter.chat(
                prompt,
                model=model,
                system=template.role,
                max_tokens=int(template.output_config.get("max_tokens", 4096)),
                temperature=float(template.output_config.get("temperature", 0.2)),
            )

        # 5. Parse response
        return self._parse_validation_response(text, template)

    def _build_validation_prompt(
        self,
        template: Any,
        context: dict[str, Any],
    ) -> str:
        """Build the validation prompt from template + context."""
        # Use the PromptRunner if available (supports RCTCO assembly)
        if self._prompt_runner is not None:
            return self._prompt_runner.build(
                template=template,
                context=context,
            )
        # Fallback: simple string formatting
        return template.context_template.format_map(
            _SafeDict(context)
        )

    def _needs_multimodal(self) -> bool:
        """Check if this validator needs multimodal (image+text) input."""
        from film_pipeline.schemas._base import ValidationModality
        return (
            ValidationModality.IMAGE in self.entry.modalities
            or ValidationModality.VIDEO in self.entry.modalities
        )

    def _extract_images(self, artifact: dict[str, Any]) -> list[str]:
        """Extract base64-encoded images from the artifact.

        Override in subclasses for artifact-specific extraction.
        Default: looks for 'images', 'frames', or 'asset_data' keys.
        """
        # Try common keys for image data
        for key in ("images", "frames", "asset_data", "clips"):
            value = artifact.get(key)
            if isinstance(value, list) and value:
                # Each entry might be a b64 string or a dict with b64 data
                images: list[str] = []
                for item in value:
                    if isinstance(item, str):
                        images.append(item)
                    elif isinstance(item, dict):
                        b64 = item.get("data") or item.get("b64") or item.get("image_b64")
                        if b64:
                            images.append(str(b64))
                if images:
                    return images
        return []

    def _parse_validation_response(
        self,
        text: str,
        template: Any,
    ) -> dict[str, Any]:
        """Parse LLM response into the expected raw dict format.

        Handles: direct JSON, markdown-fenced JSON, and partial JSON.
        """
        import json

        text = text.strip()

        # Strategy 1: Direct JSON
        try:
            return dict(json.loads(text))
        except json.JSONDecodeError:
            pass

        # Strategy 2: Markdown fence
        for fence in ("```json", "```JSON", "```"):
            if fence in text:
                idx = text.rfind(fence)
                block = text[idx + len(fence):]
                close = block.find("```")
                if close != -1:
                    block = block[:close]
                try:
                    return dict(json.loads(block.strip()))
                except json.JSONDecodeError:
                    pass

        # Strategy 3: Brace pair
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            try:
                return dict(json.loads(text[brace_start:brace_end + 1]))
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"Validator '{self.entry.validator_id}' LLM response is not valid JSON. "
            f"Preview: {text[:300]}"
        )

    # ── Abstract methods (unchanged) ────────────────────────────────

    @abstractmethod
    def extract_score(self, raw: dict[str, Any]) -> float: ...

    @abstractmethod
    def extract_issues(self, raw: dict[str, Any]) -> list[ValidationIssue]: ...

    # ── Full lifecycle ──────────────────────────────────────────────

    def run(
        self,
        artifact: dict[str, Any],
        artifact_refs: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ValidationReport:
        """Full lifecycle: validate → score → classify → report."""
        raw = self.validate(artifact, context)
        score = self.extract_score(raw)
        issues = self.extract_issues(raw)

        blocking = [i for i in issues if i.severity == "blocking"]
        warnings = [i for i in issues if i.severity != "blocking"]
        status = score_to_status(score, self.entry.thresholds)

        return ValidationReport(
            validation_id=f"validation:{self.entry.validator_id}:{uuid4().hex[:8]}",
            validator_id=self.entry.validator_id,
            scope=self.entry.scope,
            modalities=list(self.entry.modalities),
            artifact_refs=artifact_refs or [],
            score=score,
            status=status,
            blocking_issues=blocking,
            warnings=warnings,
            recommended_actions=_recommended_actions(status, blocking),
            requires_human_review=status
            in (ValidationStatus.NEEDS_REVISION, ValidationStatus.BLOCKED),
        )


class _SafeDict(dict):
    """Dict that returns the missing key as the value for missing keys.

    Used as a fallback formatter when PromptRunner is not available.
    """
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
```

## Subclass Migration (example: ScriptStructureValidator)

### Before
```python
class ScriptStructureValidator(BaseValidator):
    def validate(self, artifact, context=None) -> dict[str, Any]:
        # ... rule-based logic ...
```

### After
```python
class ScriptStructureValidator(BaseValidator):
    llm_enabled = False  # explicit default

    def _validate_rules(self, artifact, context=None) -> dict[str, Any]:
        # ... existing rule-based logic (unchanged, just renamed) ...
```

The `extract_issues()` method is updated to map `suggestion`, `affected_entity`, `affected_field`, `affected_shot` from the LLM response:

```python
def extract_issues(self, raw: dict[str, Any]) -> list[ValidationIssue]:
    return [
        ValidationIssue(
            code=str(i.get("code", "unknown")),
            message=str(i.get("message", "")),
            severity=str(i.get("severity", "info")),
            suggestion=str(i.get("suggestion", "")),           # NEW
            affected_entity=str(i.get("affected_entity", "")), # NEW
            affected_field=str(i.get("affected_field", "")),   # NEW
            affected_shot=str(i.get("affected_shot", "")),     # NEW
        )
        for i in raw.get("issues", [])
    ]
```

## Tests

### File: `tests/unit/validation/test_base_validator_llm.py`

```python
class FakeAdapter:
    """Returns pre-configured responses without network calls."""
    def __init__(self, response: str):
        self.response = response
        self.last_prompt = ""
        self.last_model = ""

    def chat(self, prompt, *, model, system="", max_tokens=4096, temperature=0.7):
        self.last_prompt = prompt
        self.last_model = model
        return self.response

    def chat_multimodal(self, prompt, *, model, images_b64=None, **kwargs):
        self.last_prompt = prompt
        self.last_model = model
        return self.response


class FakeRouter:
    def resolve(self, profile_name, prefer_cheap=False):
        return f"test-model-for-{profile_name}"


class FakeTemplateRegistry:
    def __init__(self):
        self.templates = {}

    def get(self, agent_id):
        return self.templates.get(agent_id)

    def register(self, template):
        self.templates[template.agent_id] = template


class TestValidator(BaseValidator):
    """Minimal validator for testing the LLM lifecycle."""
    llm_enabled = True

    def _validate_rules(self, artifact, context=None):
        return {"issues": [], "score": 100}

    def extract_score(self, raw):
        return float(raw.get("score", 0))

    def extract_issues(self, raw):
        return [
            ValidationIssue(
                code=str(i.get("code", "")),
                message=str(i.get("message", "")),
                severity=str(i.get("severity", "info")),
                suggestion=str(i.get("suggestion", "")),
                affected_entity=str(i.get("affected_entity", "")),
                affected_field=str(i.get("affected_field", "")),
                affected_shot=str(i.get("affected_shot", "")),
            )
            for i in raw.get("issues", [])
        ]


def test_validate_dispatches_to_llm_when_enabled():
    """llm_enabled=True + services → _validate_llm() called."""
    adapter = FakeAdapter('{"score": 85, "issues": []}')
    validator = TestValidator(ValidatorRegistryEntry(
        validator_id="test-validator",
        scope=ValidationScope.ARTIFACT,
        model_profile="text_validator",
    ))
    validator.set_services(
        adapter=adapter,
        router=FakeRouter(),
        template_registry=_make_template_registry(),
    )
    result = validator.validate({"test": "data"})
    assert result["score"] == 85


def test_validate_falls_back_to_rules_when_disabled():
    """llm_enabled=False → _validate_rules() called."""
    validator = TestValidator(ValidatorRegistryEntry(
        validator_id="test-validator",
        scope=ValidationScope.ARTIFACT,
        model_profile="text_validator",
    ))
    validator.llm_enabled = False
    result = validator.validate({"test": "data"})
    assert result["score"] == 100  # from _validate_rules


def test_validate_falls_back_to_rules_on_llm_error():
    """LLM call raises → falls back to rules gracefully."""
    adapter = FakeAdapter("not json")
    validator = TestValidator(ValidatorRegistryEntry(
        validator_id="test-validator",
        scope=ValidationScope.ARTIFACT,
        model_profile="text_validator",
    ))
    validator.set_services(
        adapter=adapter,
        router=FakeRouter(),
        template_registry=_make_template_registry(),
    )
    # The LLM path will try to parse "not json" and fail → fall back
    # (FakeAdapter returns a non-JSON string, _parse_validation_response raises)
    # Actually we want to test the try/except in validate() —
    # _validate_llm raises ValueError → caught → falls back
    # Let's use a spy instead
    ...


def test_extract_issues_maps_suggestion_fields():
    """extract_issues() populates suggestion, affected_entity, etc."""
    raw = {
        "issues": [{
            "code": "test_code",
            "message": "test message",
            "severity": "blocking",
            "suggestion": "do this fix",
            "affected_entity": "hero",
            "affected_field": "dialogue",
            "affected_shot": "s_001",
        }]
    }
    validator = TestValidator(ValidatorRegistryEntry(
        validator_id="test-validator",
        scope=ValidationScope.ARTIFACT,
        model_profile="text_validator",
    ))
    issues = validator.extract_issues(raw)
    assert len(issues) == 1
    assert issues[0].suggestion == "do this fix"
    assert issues[0].affected_entity == "hero"
    assert issues[0].affected_field == "dialogue"
    assert issues[0].affected_shot == "s_001"


def test_set_services_partial_injection():
    """set_services() with partial args only updates provided ones."""
    validator = TestValidator(ValidatorRegistryEntry(
        validator_id="test-validator",
        scope=ValidationScope.ARTIFACT,
        model_profile="text_validator",
    ))
    assert not validator._has_llm_services()
    validator.set_services(adapter=FakeAdapter(""))
    assert not validator._has_llm_services()  # still missing router + templates
    validator.set_services(router=FakeRouter(), template_registry=_make_template_registry())
    assert validator._has_llm_services()


def _make_template_registry():
    reg = FakeTemplateRegistry()
    reg.register(PromptTemplate(
        template_id="test-v1",
        agent_id="test-validator",
        version=1,
        role="You are a test validator.",
        core_task="Return a score.",
        context_template="Artifact: {artifact}",
        constraints="",
        output_format='{"score": 0, "issues": []}',
        output_schema_ref="validation.ValidationReport",
    ))
    return reg
```

## Verification Checklist

- [ ] All 7 validators rename `validate()` → `_validate_rules()` (mechanical, no logic change)
- [ ] `validate()` dispatches correctly: LLM path when enabled, rules when not
- [ ] LLM failure → graceful fallback to rules
- [ ] `set_services()` partial injection works (can call multiple times)
- [ ] `_needs_multimodal()` returns True for validators with IMAGE/VIDEO modality
- [ ] `_extract_images()` finds images in common artifact structures
- [ ] `extract_issues()` maps suggestion/affected_entity/affected_field/affected_shot
- [ ] All existing tests pass unchanged (backward compat)
- [ ] `make ci-check` passes

## Risks

| Risk | Mitigation |
|------|-----------|
| Renaming `validate()` → `_validate_rules()` is a breaking change for subclass-override callers | Nobody calls `validate()` directly on subclasses — always through `run()` or the `BaseValidator` instance. The rename is internal. |
| `_SafeDict` fallback formatter is too simple for complex templates | Only used when `PromptRunner` isn't available. In production, `PromptRunner` is always injected. |
| LLM failure fallback could silently pass broken artifacts | Warning is logged. The orchestrator will see the rule-based score and can trigger repair if below threshold. |
