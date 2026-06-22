# Phase 7: Rollout — Remaining 6 Validators

## Goal

Roll out LLM validation to the remaining 6 validators, one at a time. Each validator follows the same pattern established by the pilot (Phase 6).

## Rollout Order

Ordered by risk (lowest risk first, multimodal last):

| # | Validator | Profile | Risk | Why this order |
|---|-----------|---------|------|----------------|
| 1 | `script_structure` | `text_validator` | Low | Pilot — proven in Phase 6 |
| 2 | `dialogue_voice` | `text_validator` | Low | Text-only, similar to script_structure |
| 3 | `prompt_readiness` | `text_validator` | Low | Text-only, straightforward rubric |
| 4 | `assembly` | `text_validator` | Medium | Rule-based core + LLM qualitative layer |
| 5 | `delivery_completeness` | `text_validator` | Low | Mostly rule-based, LLM adds sanity check |
| 6 | `reference_usability` | `multimodal_reviewer` | High | First multimodal — tests Gemini integration |
| 7 | `scene_continuity` | `multimodal_reviewer` | High | Multimodal with multiple images per call |

## Pattern for Each Rollout

For each validator, the changes are mechanical:

### Step A: Rename `validate()` → `_validate_rules()`

```python
# Before
def validate(self, artifact, context=None) -> dict[str, Any]:
    # ... rule-based logic ...

# After
def _validate_rules(self, artifact, context=None) -> dict[str, Any]:
    # ... existing rule-based logic (unchanged) ...
```

### Step B: Set `llm_enabled` flag

```python
class DialogueVoiceValidator(BaseValidator):
    llm_enabled = True  # ← or False initially, flip after testing
```

### Step C: Update `extract_issues()` to map suggestion fields

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

### Step D: Register prompt template

Add the template to `load_validator_templates()` in `defaults.py`.

### Step E: Write tests

Following the pilot pattern:
- `test_llm_path_produces_score_and_issues` — with fake adapter
- `test_llm_fallback_to_rules_on_error` — graceful degradation
- `test_stub_still_works_when_disabled` — backward compat
- `test_extract_issues_maps_suggestion` — field mapping
- `test_stub_vs_llm_comparison` — LLM catches what stub misses

### Step F: Verify, then flip `llm_enabled = True`

Run tests in mock mode, then real mode. Verify real LLM output quality manually.

---

## Validator 2: `dialogue_voice`

### Current stub limitations
- Detects "all characters sound the same" only by line length
- Detects exposition only by phrase matching ("as you know")
- Detects generic dialogue only by phrase matching ("I'm fine", "let's go")
- Can't evaluate subtext, voice differentiation, or character truth

### LLM differentiator
The LLM actually reads each character's lines and compares voice patterns — word choice, rhythm, emotional register. It can detect that two characters use the same vocabulary and sentence structure even if line lengths differ. It can flag exposition that's organic but still excessive. It can identify when characters say what they mean (no subtext) vs. when there's meaning beneath the words.

### Rollout steps
1. Rename `validate()` → `_validate_rules()`
2. `llm_enabled = False` (start disabled)
3. Update `extract_issues()` for suggestion fields
4. Register `_dialogue_voice_validator()` template
5. Write tests per pilot pattern
6. Run mock mode tests → green
7. Run real mode test manually → verify output quality
8. **Check**: does LLM catch voice similarity that stub misses?
9. Flip `llm_enabled = True`

### Special consideration
DialogueVoiceValidator needs **CharacterDossiers** injected into prompt context. The `_build_validation_prompt()` method in `BaseValidator` currently only has the artifact. The `context` parameter carries additional data. The `_run_script_validators()` function must pass character dossiers via context:

```python
# In _run_script_validators()
context = {
    "character_dossiers": _load_character_dossiers(state),
}
instance.validate(artifact, context=context)
```

---

## Validator 3: `prompt_readiness`

### Current stub limitations
- Checks RCTCO fields exist (r, c1 present)
- Checks artifact_refs non-empty
- Checks prompt length < 8000 chars
- Keyword-matches ambiguous phrases
- Checks output schema ref is non-empty

### LLM differentiator
The LLM evaluates prompt *quality* — not just field presence. It can tell the difference between "You are an artist" (too vague) and "You are a cinematographer specializing in natural-light landscape photography" (specific). It evaluates whether constraints are testable ("character must wear the blue cloak" vs "make it look good"). It checks if context is complete for the task.

### Rollout steps
Same pattern as dialogue_voice. No special considerations.

---

## Validator 4: `assembly`

### Current stub (KEEP)
- Rule-based checks: clip order, transition validity, duplicate IDs, missing assets, audio plan, color plan

### LLM addition (qualitative layer)
The LLM provides a qualitative review of narrative flow, transition appropriateness, pacing, and emotional arc. The stub's rule-based checks handle the concrete validation (clip existence, transition validity). The LLM adds what the stub can't: does the edit *feel* right?

### Scoring model
```python
def extract_score(self, raw: dict[str, Any]) -> float:
    rule_score = self._rule_based_score(raw)  # existing logic
    llm_score = raw.get("score", 100)  # from LLM response
    # Weight: 60% rules, 40% LLM qualitative
    return rule_score * 0.6 + llm_score * 0.4
```

### Rollout steps
Same pattern. The `extract_score()` method changes to weighted blend.

---

## Validator 5: `delivery_completeness`

### Current stub (KEEP)
- Rule-based checks: required files exist, subtitles, stills, validation/cost/credits refs

### LLM addition (qualitative layer)
The LLM does a production readiness sanity check: reasonable file sizes, correct formats, naming conventions, no temp files. This is a lightweight sanity check, not a heavy evaluation.

### Scoring model
```python
def extract_score(self, raw: dict[str, Any]) -> float:
    rule_score = self._rule_based_score(raw)
    llm_score = raw.get("score", 100)
    return rule_score * 0.7 + llm_score * 0.3  # 70% rules, 30% LLM
```

### Rollout steps
Same pattern.

---

## Validator 6: `reference_usability` (FIRST MULTIMODAL)

### Current stub limitations
- Checks `quality_score < 60` (a number, not actual image quality)
- Checks `moderation_risk == "high"` (a flag, not actual content moderation)
- Checks `subject_type` validity
- Keyword-matches notes for lighting/style issues

### LLM differentiator
The LLM actually **looks at the image**. It compares the image against the character/environment description. It evaluates image quality (resolution, composition, lighting). It does real content moderation. It checks art style consistency.

### Multimodal considerations
- Uses `chat_multimodal()` with `model="google/gemini-3-flash-preview"`
- Image is extracted from artifact via `_extract_images()`
- The `_extract_images()` method looks for `"images"`, `"asset_data"`, or `"data"` keys in the artifact
- For reference_usability, images are typically in `artifact["entries"][n]["asset_data"]`

### Custom `_extract_images()` override
```python
class ReferenceUsabilityValidator(BaseValidator):
    def _extract_images(self, artifact: dict[str, Any]) -> list[str]:
        """Extract reference images from entries."""
        entries = artifact.get("entries", [])
        images = []
        for entry in entries:
            asset = entry.get("asset_data") or entry.get("image_b64") or entry.get("data")
            if asset:
                images.append(str(asset))
        return images
```

### Rollout steps
Same pattern + custom `_extract_images()`.

### Special consideration
Gemini multimodal call costs more than text-only. Each reference image is one API call. A film with 20 references = 20 Gemini calls. Acceptable for now; revisit if cost becomes an issue.

---

## Validator 7: `scene_continuity` (MULTIPLE IMAGES PER CALL)

### Current stub limitations
- Tracks character state from dict metadata (not visual)
- Compares prop sets, lighting, wardrobe as strings
- None of this involves looking at actual frames

### LLM differentiator
The LLM looks at **consecutive frames** and compares them visually. Same character should look the same. Props should be present. Lighting should be consistent. Wardrobe shouldn't change. Spatial relationships should make sense.

### Multimodal considerations
- Uses `chat_multimodal()` with **multiple images per call** (consecutive frames)
- The prompt says "You are viewing N consecutive frames from the same scene"
- Each call compares 2-5 consecutive frames

### Custom `_extract_images()` override
```python
class SceneContinuityValidator(BaseValidator):
    def _extract_images(self, artifact: dict[str, Any]) -> list[str]:
        """Extract consecutive frame images from shots."""
        shots = artifact.get("shots", artifact.get("scenes", []))
        images = []
        for shot in shots:
            # Each shot may have frames or clip data
            frames = shot.get("frames", [])
            for frame in frames:
                b64 = frame.get("data") or frame.get("image_b64")
                if b64:
                    images.append(str(b64))
        return images
```

### Batch processing
Not every shot needs continuity checking. Only consecutive shots within the same scene. The validator receives a batch of 2-5 frames at a time:

```python
def _validate_rules(self, artifact, context=None) -> dict[str, Any]:
    # Existing logic checks ALL shots at once
    ...

# For LLM path, process in batches of 5 consecutive frames
# Each batch is one LLM call comparing those frames
```

The `_validate_llm()` method handles this — it calls the LLM once per batch. The `run()` method aggregates scores across batches.

### Rollout steps
Same pattern + custom `_extract_images()` + batch processing.

### Special consideration
Scene continuity is the most expensive validator: N batches × multi-image Gemini calls. A 20-shot film with 4 frames per shot = 80 frames, batched by 5 = 16 Gemini calls. Acceptable for initial rollout. Can optimize by only checking shots flagged by the rule-based validator.

---

## After All 7 Are Rolled Out

### Verification: Integration test

```python
# tests/integration/test_all_validators_llm.py

def test_all_seven_validators_produce_suggestions():
    """Every validator produces issues with suggestions when LLM enabled."""
    ...

def test_mixed_stub_and_llm_validators():
    """Some validators LLM, some stub — both work together."""
    ...

def test_end_to_end_repair_feedback_includes_suggestions():
    """Full flow: validate → gate detects → repair builds feedback with suggestions."""
    ...
```

### Verification: Real mode smoke test

```bash
# Set up a real project with real artifacts
# Run the full pipeline with llm_enabled=True for all 7 validators
# Verify:
# - No crashes
# - Issues include suggestions
# - Suggestions are actionable (not "fix the problem")
# - Repair agents can use suggestions
```

### Verification: Cost baseline

| Validator | Calls per 20-shot film | Cost per call (est.) | Total |
|-----------|----------------------|---------------------|-------|
| script_structure | 1 | $0.001 | $0.001 |
| dialogue_voice | 1 | $0.002 | $0.002 |
| prompt_readiness | 1 | $0.001 | $0.001 |
| assembly | 1 | $0.001 | $0.001 |
| delivery_completeness | 1 | $0.001 | $0.001 |
| reference_usability | N references (est. 10) | $0.003 | $0.03 |
| scene_continuity | N batches (est. 16) | $0.005 | $0.08 |
| **Total** | | | **~$0.12** |

Actual costs will vary by model pricing. This is an estimate for planning.

## Per-Validator Checklist

For each of the 6 validators:

- [ ] `validate()` renamed to `_validate_rules()`
- [ ] `llm_enabled` flag set (initially `False`, flipped after testing)
- [ ] `extract_issues()` maps suggestion/affected_entity/affected_field/affected_shot
- [ ] Prompt template registered with matching `agent_id`
- [ ] Custom `_extract_images()` if multimodal
- [ ] Tests: LLM path, fallback, backward compat, suggestion mapping, stub vs LLM comparison
- [ ] Mock mode tests pass
- [ ] Real mode test with real LLM output (manual verification)
- [ ] `make ci-check` passes after each validator
- [ ] `llm_enabled = True` after verification

## Risks

| Risk | Mitigation |
|------|-----------|
| Rolling out all 7 at once breaks everything | One at a time, verify each before next |
| Gemini multimodal costs spike | Baseline costs estimated at ~$0.12 per 20-shot film. Monitor and throttle if needed. |
| Real LLM output quality varies by model | The `text_validator` profile has `temperature: 0.1` for consistency. If still inconsistent, fall back to rule-based. |
| Suggestions are vague ("improve the dialogue") | Prompt templates explicitly require specific suggestions with examples. If LLM still produces vague output, increase temperature or switch model. |
| `extract_issues()` breaks on unexpected LLM output format | Each validator's `extract_issues()` uses `.get()` with defaults — safe against missing fields. |
