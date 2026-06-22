# Phase 8 — Agent Output Quality: Chain-of-Thought & Advanced Sampling

**Goal:** Close the remaining quality gap after Phase 0 quick wins (profile routing + quality instructions).
Add chain-of-thought prompting, `frequency_penalty`, and per-agent temperature tuning.

**Prerequisite:** Phase 0 (quick wins) — profile routing must be done first. Phase 6 (scoped context) — agents
must receive structured data before chain-of-thought can be effective.

---

## Current State (After Phase 0)

- Creative agents routed to `creative_writer` (temp 0.7, max_tokens 8192)
- Templates have `quality_instructions` telling the model to be thorough
- But: agents still jump directly to JSON output without reasoning
- But: no `frequency_penalty` — dialogue and descriptions repeat phrases
- But: templates not restructured for step-by-step thinking

---

## Target State

- Creative templates guide step-by-step reasoning before JSON output
- `ModelAdapter` supports `frequency_penalty` to reduce repetition
- `top_p` sampling added for creative profiles
- Agent `execute()` methods handle chain-of-thought output (text before JSON)

---

## Files to Modify

| File | Change |
|------|--------|
| `agents/model_adapter.py` | Add `frequency_penalty`, `top_p` parameters |
| `agents/model_routing/__init__.py` | Add `frequency_penalty`, `top_p` to profiles |
| `agents/prompt_templates/defaults.py` | Restructure 5 creative templates for chain-of-thought |
| `agents/runner.py` | Pass new params to model adapter |

---

## Step-by-Step

### Step 1: Add `frequency_penalty` and `top_p` to ModelAdapter

**File:** `src/film_pipeline/agents/model_adapter.py:55-68`

```python
def _request(
    self,
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    top_p: float = 0.95,              # NEW
    frequency_penalty: float = 0.0,   # NEW
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
    }
    # ... rest unchanged

def chat(
    self,
    prompt: str,
    *,
    model: str,
    system: str = "",
    max_tokens: int = 4096,
    temperature: float = 0.7,
    top_p: float = 0.95,              # NEW
    frequency_penalty: float = 0.0,   # NEW
) -> str:
    response = self._request(
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
    )
    # ... rest unchanged
```

Same additions propagate through `chat_json()` and `chat_multimodal()`.

### Step 2: Add `frequency_penalty` to Creative Profiles

**File:** `src/film_pipeline/agents/model_routing/__init__.py`

```python
_DEFAULT_PROFILES = {
    "creative_writer": {
        "primary": "deepseek/deepseek-chat",
        "fallback": "google/gemini-3-flash-preview",
        "max_tokens": 8192,
        "temperature": 0.7,
        "top_p": 0.95,              # NEW
        "frequency_penalty": 0.15,   # NEW — reduces repetition
    },
    "visual_reasoner": {
        "primary": "google/gemini-3-flash-preview",
        "fallback": "deepseek/deepseek-chat",
        "max_tokens": 4096,
        "temperature": 0.4,
        "top_p": 0.9,
        "frequency_penalty": 0.1,
    },
    # Validator profiles: frequency_penalty=0 (deterministic output)
    "strict_validator": {
        # ... unchanged, frequency_penalty=0 default
    },
}
```

### Step 3: Resolve New Params in Router

**File:** `src/film_pipeline/agents/model_routing/__init__.py:resolve_model_params`

```python
def resolve_model_params(self, profile_name: str) -> tuple[str, int, float, float, float]:
    """Resolve: (model_id, max_tokens, temperature, top_p, frequency_penalty)."""
    profile = self.profiles.get(profile_name)
    if profile is None:
        raise ModelResolutionError(...)

    model_id = str(profile["primary"])
    max_tokens = int(str(profile.get("max_tokens", 4096)))
    temperature = float(str(profile.get("temperature", 0.7)))
    top_p = float(str(profile.get("top_p", 0.95)))
    frequency_penalty = float(str(profile.get("frequency_penalty", 0.0)))

    return model_id, max_tokens, temperature, top_p, frequency_penalty
```

### Step 4: Restructure Creative Templates for Chain-of-Thought

**File:** `src/film_pipeline/agents/prompt_templates/defaults.py`

**Before (screenwriter):**
```python
core_task=(
    "Create a StoryBible and Script from the treatment and scene intents. "
    "Write a complete logline, premise, scene-by-scene breakdown, "
    "dialogue, action lines, and setup-payoff mapping."
)
```

**After (screenwriter — chain-of-thought):**
```python
core_task=(
    "Create a StoryBible and Script from the treatment and scene intents.\n\n"
    "Think through each step before writing. Work in this order:\n\n"
    "STEP 1 — LOGLINE & PREMISE: What is the single-sentence hook? "
    "What is the dramatic question?\n\n"
    "STEP 2 — ACT STRUCTURE: Map the three-act structure from the treatment. "
    "Identify the inciting incident, midpoint, climax, resolution.\n\n"
    "STEP 3 — SCENE BREAKDOWN: For each scene, determine:\n"
    "  - Dramatic function (what does this scene accomplish?)\n"
    "  - Emotional shift (from what, to what?)\n"
    "  - Conflict (what opposing forces meet?)\n"
    "  - Outcome (what changes by scene end?)\n\n"
    "STEP 4 — DIALOGUE: Write dialogue that serves character and plot. "
    "Every line must reveal character, advance plot, or build tension.\n\n"
    "STEP 5 — SETUP-PAYOFF: Identify pairs — if something is introduced "
    "in one scene, where does it pay off?\n\n"
    "STEP 6 — REVIEW: Count your scenes. Verify every scene has a heading, "
    "action lines, and dialogue where appropriate. Check internal consistency.\n\n"
    "After completing all steps, output the complete JSON."
)
```

Same pattern for: constitution, treatment, visual_dev, shot_bible.

### Step 5: Update `chat_json` to Handle Chain-of-Thought Output

**File:** `src/film_pipeline/agents/model_adapter.py:chat_json`

The `chat_json` method already has 4 extraction strategies that handle text before JSON.
Chain-of-thought output naturally produces: reasoning text → ` ```json ... ``` ` → JSON.
The existing extraction strategies already handle this. No code change needed.

**Verify:** Run a creative agent with chain-of-thought prompting against a real model.
Confirm `chat_json` successfully extracts JSON from the CoT output.

---

## Test Cases

```python
def test_chat_json_extracts_cot_output():
    """chat_json handles chain-of-thought text before JSON."""
    response = (
        "Let me think about this step by step...\n"
        "The theme should be about hope.\n"
        "```json\n"
        '{"constitution": {"theme": "Hope against despair"}}\n'
        "```"
    )
    adapter = ModelAdapter(http_opener=mock_opener_returning(response))
    result = adapter.chat_json(prompt="...", model="test-model")
    assert result["constitution"]["theme"] == "Hope against despair"

def test_frequency_penalty_passed_to_api():
    """frequency_penalty parameter is included in API request body."""
    adapter = ModelAdapter(http_opener=capture_opener())
    adapter.chat("test", model="test-model", frequency_penalty=0.15)
    # Verify request body includes "frequency_penalty": 0.15

def test_creative_profile_has_frequency_penalty():
    """creative_writer profile includes frequency_penalty > 0."""
    router = ModelRouter()
    _, _, _, _, fp = router.resolve_model_params("creative_writer")
    assert fp > 0.0

def test_validator_profile_has_zero_frequency_penalty():
    """strict_validator profile keeps frequency_penalty=0 for determinism."""
    router = ModelRouter()
    _, _, _, _, fp = router.resolve_model_params("strict_validator")
    assert fp == 0.0
```

---

## Acceptance Criteria

- [ ] `ModelAdapter._request()` accepts `top_p` and `frequency_penalty`
- [ ] `ModelRouter.resolve_model_params()` returns 5-tuple
- [ ] `creative_writer` profile has `frequency_penalty: 0.15, top_p: 0.95`
- [ ] `strict_validator` profile has `frequency_penalty: 0.0`
- [ ] 5 creative templates restructured with numbered steps / chain-of-thought
- [ ] `chat_json` successfully extracts JSON from CoT output (existing strategies, verified)
- [ ] `make ci-check` green
- [ ] Manual E2E: creative agent output shows improved detail and variety

**Estimated implementation time:** 1-2 hours
**Prerequisite:** Phase 0 (profile routing) + Phase 6 (scoped context)
