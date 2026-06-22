# Phase 3: Multimodal Adapter — `chat_multimodal()` in ModelAdapter

## Goal

Extend `ModelAdapter` with a `chat_multimodal()` method for Gemini image+text calls. Reuse the existing `_call_gemini` pattern from `frame_reviewer.py` and `sheet_reviewer.py` but with constructor-injected HTTP opener for testability — same as the existing `_request()` method.

## Current State

- `ModelAdapter.chat()` — text-only OpenRouter call, constructor-injected opener
- `ModelAdapter.chat_json()` — text-only OpenRouter with JSON parsing
- `_call_gemini()` — standalone function in `frame_reviewer.py` (duplicated in `sheet_reviewer.py`), no constructor injection

## Target

```python
class ModelAdapter:
    def chat_multimodal(
        self,
        prompt: str,
        *,
        model: str,                      # "google/gemini-3-flash-preview"
        images_b64: list[str] | None = None,
        mime_type: str = "image/png",
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> str:
        """Send prompt + images to Gemini, return text response.

        When images_b64 is empty or None: falls back to chat() via OpenRouter.
        When model starts with "google/": uses Gemini generateContent API.
        Otherwise: uses OpenRouter with text-only (images dropped).
        """
```

## Design

### API choice: Gemini generateContent vs OpenRouter multimodal

OpenRouter *can* do multimodal with some models, but:
- The provider chain is unreliable for image+text
- Gemini's native API is simpler and well-tested (already used in `_call_gemini`)
- The two validators that need multimodal (`scene_continuity`, `reference_usability`) already plan to use `google/gemini-3-flash-preview`

**Decision:** Use Gemini native API for `google/*` models, OpenRouter text-only fallback for everything else.

### Reusing the existing `_call_gemini` pattern

The `_call_gemini` function in `frame_reviewer.py` and `sheet_reviewer.py` is duplicated. After this phase:
- `ModelAdapter.chat_multimodal()` becomes the canonical implementation
- `_call_gemini` functions are refactored to call `ModelAdapter.chat_multimodal()`

### Credential lookup

The existing `_call_gemini` uses `lookup("gemini-imagen-4")`. The adapter already has `_api_key()` using `lookup("seedance-openrouter")`. For Gemini, we need a separate credential path:

```python
def _gemini_api_key(self) -> str:
    key = self._configured_api_key or lookup("gemini-imagen-4")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is not set.")
    return key
```

The adapter constructor already accepts `api_key`. For multimodal calls, the caller can pass the Gemini key, or the adapter falls back to `lookup("gemini-imagen-4")`.

### Constructor injection for testability

Same pattern as `_request()`:

```python
def __init__(self, http_opener=None, api_key=None, gemini_api_key=None):
    self._http_opener = http_opener
    self._configured_api_key = api_key
    self._configured_gemini_api_key = gemini_api_key
```

Tests can inject a mock opener that simulates Gemini API responses.

### Fallback chain

```
ModelRouter.resolve("multimodal_reviewer") → "google/gemini-3-flash-preview"
  ↓
chat_multimodal(prompt, model="google/gemini-3-flash-preview", images_b64=[...])
  ↓
model starts with "google/" → Gemini generateContent API
  ↓ success
returns text response
  ↓ failure (quota, auth, network)
ModelRouter.resolve("multimodal_reviewer", prefer_cheap=True) → "deepseek/deepseek-chat"
  ↓
chat_multimodal(prompt, model="deepseek/deepseek-chat", images_b64=[...])
  ↓
model does NOT start with "google/" → OpenRouter text-only (images dropped, warning logged)
```

The caller is responsible for fallback. The adapter doesn't auto-retry with a different model — that's the router's job.

## Implementation

### File: `src/film_pipeline/agents/model_adapter.py`

```python
def __init__(
    self,
    http_opener: Any = None,
    api_key: str | None = None,
    gemini_api_key: str | None = None,
) -> None:
    self._http_opener = http_opener
    self._configured_api_key = api_key
    self._configured_gemini_api_key = gemini_api_key

def _gemini_api_key(self) -> str:
    key = self._configured_gemini_api_key or lookup("gemini-imagen-4")
    if not key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Set it in the environment or .env file."
        )
    return key

def chat_multimodal(
    self,
    prompt: str,
    *,
    model: str,
    images_b64: list[str] | None = None,
    mime_type: str = "image/png",
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> str:
    """Send prompt + images to a multimodal model.

    When model starts with 'google/', uses Gemini's generateContent API
    with inline image data. Otherwise falls back to text-only chat()
    (images are logged as dropped but the call proceeds).

    Args:
        prompt: The text prompt.
        model: Full model ID (e.g. "google/gemini-3-flash-preview").
        images_b64: Base64-encoded images (no data URI prefix).
        mime_type: Image MIME type for Gemini API.
        max_tokens: Max output tokens.
        temperature: Generation temperature.

    Returns:
        Model's text response.
    """
    if not images_b64:
        # No images — use text-only path
        return self.chat(
            prompt, model=model, max_tokens=max_tokens, temperature=temperature
        )

    if model.startswith("google/"):
        return self._call_gemini_api(
            prompt=prompt,
            model=model,
            images_b64=images_b64,
            mime_type=mime_type,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    # Non-Google model with images — text-only fallback
    import logging
    logging.warning(
        f"chat_multimodal: dropping {len(images_b64)} images for non-Google model '{model}'"
    )
    return self.chat(
        prompt, model=model, max_tokens=max_tokens, temperature=temperature
    )

def _call_gemini_api(
    self,
    prompt: str,
    model: str,
    images_b64: list[str],
    mime_type: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call Gemini's generateContent API with text + inline images."""
    key = self._gemini_api_key()
    # Strip "google/" prefix for Gemini API
    gemini_model = model.removeprefix("google/")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{gemini_model}:generateContent?key={key}"
    )

    parts: list[dict[str, Any]] = [{"text": prompt}]
    for img in images_b64:
        parts.append({"inline_data": {"mime_type": mime_type, "data": img}})

    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )

    opener = self._http_opener or urllib.request.build_opener()
    try:
        with opener.open(req) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, OSError) as e:
        detail = str(e)
        if isinstance(e, urllib.error.HTTPError):
            body_text = e.read().decode(errors="replace")
            detail = f"HTTP {e.code}: {body_text[:200]}"
        raise RuntimeError(f"Gemini generateContent failed: {detail}") from e

    # Extract text from Gemini response
    candidates = raw.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")
    parts_out = candidates[0].get("content", {}).get("parts", [])
    if not parts_out:
        raise RuntimeError("Gemini returned no content parts.")
    return str(parts_out[0].get("text", ""))
```

### Refactoring `_call_gemini` in frame_reviewer.py / sheet_reviewer.py

After `chat_multimodal()` is implemented, the standalone `_call_gemini` functions can redirect:

```python
# Before (in frame_reviewer.py)
response = _call_gemini(prompt, image_b64, model, http_opener, api_key)

# After
adapter = ModelAdapter(http_opener=http_opener, gemini_api_key=api_key)
text = adapter.chat_multimodal(
    prompt,
    model=f"google/{model}",  # add google/ prefix
    images_b64=[image_b64],
)
response = json.loads(text)
```

This refactoring is done in Phase 7 (rollout), not here, to keep scope small.

## Tests

### File: `tests/unit/agents/test_model_adapter_multimodal.py`

```python
class FakeGeminiOpener:
    """Simulates Gemini generateContent API responses."""
    def __init__(self, response_text: str, status: int = 200):
        self.response_text = response_text
        self.status = status

    def open(self, req):
        if self.status != 200:
            raise urllib.error.HTTPError(
                req.full_url, self.status, "Error", {}, None
            )
        return FakeResponse(json.dumps({
            "candidates": [{
                "content": {"parts": [{"text": self.response_text}]}
            }]
        }).encode())


def test_chat_multimodal_gemini_with_images():
    """Gemini path with images returns text from generateContent API."""
    adapter = ModelAdapter(
        http_opener=FakeGeminiOpener('{"score": 85}'),
        gemini_api_key="test-key",
    )
    result = adapter.chat_multimodal(
        "Evaluate this image",
        model="google/gemini-3-flash-preview",
        images_b64=["aW1hZ2VkYXRh"],  # "imagedata" in base64
    )
    assert "score" in result


def test_chat_multimodal_no_images_falls_back_to_chat():
    """Empty images → text-only chat path."""
    adapter = ModelAdapter(http_opener=FakeOpenRouterOpener("hello"))
    result = adapter.chat_multimodal(
        "Hello",
        model="deepseek/deepseek-chat",
        images_b64=None,
    )
    assert result == "hello"


def test_chat_multimodal_non_google_drops_images():
    """Non-Google model with images → text-only fallback."""
    adapter = ModelAdapter(http_opener=FakeOpenRouterOpener("text only"))
    result = adapter.chat_multimodal(
        "Evaluate",
        model="deepseek/deepseek-chat",
        images_b64=["aW1hZ2VkYXRh"],
    )
    assert result == "text only"


def test_chat_multimodal_gemini_error_raises():
    """Gemini HTTP error → RuntimeError."""
    adapter = ModelAdapter(
        http_opener=FakeGeminiOpener("", status=429),
        gemini_api_key="test-key",
    )
    with pytest.raises(RuntimeError, match="Gemini generateContent failed"):
        adapter.chat_multimodal(
            "Evaluate",
            model="google/gemini-3-flash-preview",
            images_b64=["aW1hZ2VkYXRh"],
        )


def test_chat_multimodal_multiple_images():
    """Multiple images are all sent to Gemini."""
    adapter = ModelAdapter(
        http_opener=FakeGeminiOpener('{"score": 90}'),
        gemini_api_key="test-key",
    )
    result = adapter.chat_multimodal(
        "Compare these two frames",
        model="google/gemini-3-flash-preview",
        images_b64=["aW1hZ2Ux", "aW1hZ2Uy"],
    )
    assert "score" in result
```

## Verification Checklist

- [ ] `make ci-check` passes
- [ ] `chat_multimodal()` with `images_b64=["..."]` + `model="google/..."` → calls Gemini API
- [ ] `chat_multimodal()` with `images_b64=None` → calls `chat()` text-only
- [ ] `chat_multimodal()` with `images_b64=["..."]` + `model="deepseek/..."` → calls `chat()` text-only with warning
- [ ] Gemini HTTP error → raises `RuntimeError` with details
- [ ] Multiple images → all sent in `parts` array
- [ ] Constructor injection works for both `http_opener` and `gemini_api_key`
- [ ] Test coverage ≥ 90% on new code

## Risks

| Risk | Mitigation |
|------|-----------|
| Gemini API key not set | Clear error message telling user to set `GOOGLE_API_KEY` |
| Gemini API rate limiting | Caller implements retry (not adapter's job) |
| Image too large for Gemini | Error surfaced as RuntimeError; caller can downscale before retry |
| `_call_gemini` duplication | Marked for refactor in Phase 7 |
