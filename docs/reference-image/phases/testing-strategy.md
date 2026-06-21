# Testing Strategy — Reference Image Pipeline

**Status:** Not started
**Depends on:** Phase 2 (structured prompts), Phase 7 (compositor)
**Covers:** Prompt correctness, composite layout, end-to-end validation with real provider

---

## Two Test Layers

| Layer | Provider | When | What it proves |
|-------|----------|------|----------------|
| Unit + CI | Mock (returns solid-color PNG) | Every `make ci-check` | Prompt assembly is correct, composite builds, retry logic works, validation parses |
| E2E manual | Real Imagen 4 | Operator runs manually before locking references | Actual image quality, identity consistency across real frames, Gemini review on real images |

---

## Layer 1 — CI Tests (Mock Provider)

### Strategy

The mock provider returns a 1024×1024 solid gray PNG with the prompt text burned into it as an overlay. This lets us verify the pipeline end-to-end without spending money or waiting for API calls.

```python
class MockImageProvider:
    def build_payload(self, prompt, **kwargs):
        return {"prompt": prompt, "seed": kwargs.get("seed")}

    def submit(self, payload, shot_id):
        return ProviderJob(job_id=f"mock-{shot_id}", status="submitted")

    def poll(self, job):
        return ProviderJob(job_id=job.job_id, status="completed")

    def download(self, job, output_dir):
        # Create a synthetic PNG with the prompt text visible
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (1024, 1024), (128, 128, 128))
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), f"MOCK IMAGE\njob: {job.job_id}", fill="white")
        path = Path(output_dir) / f"{job.job_id}.png"
        img.save(path)
        return str(path)
```

The key assertion is on the **prompt text** passed to `build_payload`, not the image pixels.

### Test: Structured Prompt Construction

```
Test: Character prompt assembled from CharacterBible + FilmConstitution
  Given:
    CharacterBible(identity_block="Mediterranean features, short dark hair, brown eyes,
                   scar across left eyebrow, 1.78m, medium build")
    entry = {subject_type: "character", frame_role: "front-face", expression: "neutral"}
    FilmConstitution(visual_language="painterly natural light",
                     camera_philosophy="observational, intimate close-up")

  When:  prompt = build_structured_prompt(entry, bible, constitution)

  Then:
    assert "Mediterranean features" in prompt
    assert "scar across left eyebrow" in prompt
    assert "Front face, looking directly at camera" in prompt
    assert "Neutral expression" in prompt
    assert "painterly natural light" in prompt
    assert "observational" in prompt
    assert "intimate close-up" in prompt
    assert "Same person as in all other frames" in prompt
    assert "No text. No logos. No 2D animation" in prompt
    assert "Photorealistic only" in prompt
```

### Test: Environment Prompt Assembled Without EnvironmentBible

```
Test: Environment prompt falls back to FilmConstitution + script
  Given:
    No CharacterBible / EnvironmentBible exists
    entry = {subject_type: "environment", frame_role: "wide-establishing",
             lighting: "cool night"}
    FilmConstitution(
      visual_language="converted warehouse, exposed brick, 6m ceilings, frosted windows",
      tone="melancholic, painterly",
      camera_philosophy="observational, static wide"
    )
    Script contains scene: "INT. MODERN STUDIO - NIGHT"

  When:  prompt = build_structured_prompt(entry, None, constitution)

  Then:
    assert "converted warehouse" in prompt
    assert "exposed brick" in prompt
    assert "Wide establishing shot" in prompt
    assert "Cool night" in prompt
    assert "melancholic" in prompt
    assert "Same location across all angles" in prompt
    assert "No characters visible" in prompt
```

### Test: Frame-Role Tuning

```
Test: Each frame_role produces correct block text
  Table-driven:
    ("front-face")          → "Front face, looking directly at camera"
    ("3-4-left")            → "Three-quarter angle facing left"
    ("profile-right")       → "Right profile. Clean silhouette"
    ("full-body")           → "Full body standing. Entire figure"
    ("expression-frustrated") → "Frustrated expression. Furrowed brow"
    ("wide-establishing")   → "Wide establishing shot showing the full space"
    ("lighting-cool-night") → "Same wide establishing composition. Cool night lighting"
    ("detail-texture")      → "Extreme close-up of a surface texture"
```

### Test: Global Negatives Always Appended

```
Test: Every prompt ends with global negatives block
  Given: Any entry (character, environment, prop, style)
  When:  prompt = build_structured_prompt(entry, ...)
  Then:
    assert "No text. No logos. No 2D animation" in prompt
    assert "No cartoon. No anime. No illustrated style" in prompt
    assert "Photorealistic only" in prompt
    assert "No watermarks. No grain" in prompt
```

### Test: Environment Negatives Include "No Characters"

```
Test: Environment prompts forbid characters
  Given: entry = {subject_type: "environment", ...}
  When:  prompt = build_structured_prompt(entry, ...)
  Then:
    assert "No characters visible" in prompt
    assert "No people" in prompt
```

### Test: Character Prompts Do NOT Include "No Characters"

```
Test: Character prompts allow the character to be visible
  Given: entry = {subject_type: "character", ...}
  When:  prompt = build_structured_prompt(entry, ...)
  Then:
    assert "No characters visible" not in prompt  # character IS the subject
    assert "No other characters visible" in prompt  # but no extras
```

### Test: Identity Reinforcement

```
Test: Subsequent frame prompts include ID_REINFORCE
  Given: anchor_path exists, identity_state = {i2i_active: False}
         entry.frame_role = "3-4-left"
  When:  prompt = build_structured_prompt(entry, ..., identity_state=identity_state)
  Then:
    assert "Same person as in all other frames" in prompt
    assert "Consistent facial features" in prompt
```

### Test: I2I Fallback Strengthens ID_REINFORCE

```
Test: When I2I is active, ID_REINFORCE is stronger
  Given: identity_state = {i2i_active: True, anchor_frame_path: Path("anchor.png")}
  When:  prompt = build_structured_prompt(entry, ..., identity_state=identity_state)
  Then:
    assert "Same person as the anchor frame" in prompt
    assert "Identical facial structure" in prompt
    assert "No variation in identity" in prompt
```

### Test: Composite Builder

```
Test: Character identity sheet built from frames
  Given:
    frames = [
      {"role": "front-face", "path": fixture("gray-640.png")},
      {"role": "3-4-left", "path": fixture("gray-320.png")},
      {"role": "full-body", "path": fixture("gray-720.png")},
      {"role": "expression-neutral", "path": fixture("gray-320.png")},
    ]

  When:  sheet_path = build_character_identity_sheet("CHAR_001", "Leo", frames)

  Then:
    assert sheet_path.exists()
    img = Image.open(sheet_path)
    assert img.size == (2048, 2048)
    assert img.mode == "RGB"
```

### Test: Composite Builder — Missing Frame

```
Test: Missing frame renders placeholder, doesn't crash
  Given: frames = [{"role": "front-face", "path": fixture("gray-640.png")}]
         (3-4-left, profile, full-body, expressions all missing)

  When:  sheet_path = build_character_identity_sheet("CHAR_001", "Leo", frames)

  Then:
    assert sheet_path.exists()  # sheet builds successfully
    # placeholder tiles show the role name in gray
```

### Test: Retry Loop

```
Test: Retry terminates after max 2 retries
  Given: Mock provider, Gemini mock always returns score=20 (fail)
         entry with frame_role="front-face"

  When:  generate_with_retry(entry, max_retries=2)

  Then:
    assert entry["retry_count"] == 3  # initial + 2 retries
    assert entry["generation_status"] == "needs_regeneration"
    assert entry["best_score"] == 20.0  # best of all attempts
```

### Test: Delta Regeneration

```
Test: Only failing tiles regenerated
  Given: Composite validation returns failing_tiles=["profile-right"]
         3 frames exist for character Leo

  When:  regenerate_failing_tiles(review, entries, project_root)

  Then:
    assert profile-right was regenerated
    assert front-face was NOT regenerated
    assert full-body was NOT regenerated
```

---

## Layer 2 — Manual E2E Test (Real Imagen 4)

### File

`tests/e2e/test_reference_image_real.py`

Marked with `@pytest.mark.e2e_real` and `@pytest.mark.skipif(not os.getenv("RUN_REAL_E2E"))` so it never runs in CI.

### How to Run

```bash
RUN_REAL_E2E=1 pytest tests/e2e/test_reference_image_real.py -v -s
```

Requires `GEMINI_API_KEY` set in environment.

### What It Tests

```
Test: Generate Leo character identity sheet with real Imagen 4

  1. Create a test project with a known FilmConstitution + CharacterBible
     (use a simple test character: "John, tall man with red hair and glasses")

  2. Create 4 ReferenceIndexEntry entries for John:
     - front-face, expression=neutral
     - 3-4-left
     - full-body
     - expression-neutral

  3. Call generate_reference_images() with force=True

  4. Assert:
     - 4 images generated (no failures from provider)
     - Each image passes auto-heuristics (file exists, ≥512×512, not corrupt)
     - Composite sheet built at references/characters/john/identity-sheet.png
     - Composite sheet is 2048×2048

  5. Manual inspection:
     - Open identity-sheet.png
     - Verify all tiles show the same person (red hair, glasses)
     - Verify front face is 2× larger than other tiles
     - Verify labels are in margins, not on tiles

  6. (Optional) Run Gemini per-frame review on front-face:
     - Call review_frame() with the real image
     - Assert subject score ≥ 7/10 (person is visible)
     - Assert prompt_match score ≥ 5/10 (red hair, glasses visible)

  Total cost estimate: 4 × $0.02 = $0.08 (fast tier)
```

### Test Data (Bundled in Repo)

```python
# tests/e2e/fixtures/test_character_bible.json
{
    "character_id": "john",
    "project_id": "e2e-test",
    "visual_identity": {
        "character_id": "john",
        "name": "John Test",
        "role": "protagonist",
        "age": "mid-30s",
        "physical_description": "Tall man with bright red hair, round wire-rimmed glasses, friendly smile",
        "identity_block": "A tall man in his mid-30s with bright red hair, round wire-rimmed glasses, a friendly smile, and a slightly crooked nose. Fair skin with freckles across the bridge of his nose. Casual button-down shirt, relaxed posture. 1.85m tall."
    }
}
```

### What We Cannot Automate (Manual Inspection Required)

- "Does the generated person look like the same person across tiles?" — human judgment
- "Is the expression correct?" — Gemini can approximate this, human can verify
- "Is the composite layout visually correct?" — human judgment
- "Would this stabilize generation across 60+ shots?" — only proven in production

---

## CI Pipeline Integration

```makefile
# Makefile additions

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-e2e-mock:
	pytest tests/e2e/ -v -m "not e2e_real"

test-e2e-real:  # MANUAL ONLY — requires GEMINI_API_KEY
	RUN_REAL_E2E=1 pytest tests/e2e/test_reference_image_real.py -v -s

ci-check: format-check lint typecheck test-unit test-integration test-e2e-mock build
```

The real E2E test is never in the CI path. It's a manual operator tool for validating before locking references.

---

## Test File Layout

```
tests/
├── unit/
│   └── generation/
│       ├── test_prompt_builder.py          ← Phase 2: all prompt assertions
│       ├── test_frame_heuristics.py        ← Phase 1
│       ├── test_frame_reviewer.py          ← Phase 3 (mock Gemini)
│       ├── test_compositor.py              ← Phase 7 (Pillow output assertions)
│       ├── test_sheet_reviewer.py          ← Phase 8 (mock Gemini)
│       └── test_delta_regenerator.py       ← Phase 9
├── integration/
│   └── test_reference_image_pipeline.py    ← Full flow with mock provider
└── e2e/
    ├── fixtures/
    │   └── test_character_bible.json
    └── test_reference_image_real.py        ← Real Imagen 4, manual only
```
