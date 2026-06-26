# Context Management & Long Output — The Two-Sided Problem

## The Problem

Film pipeline agents face two opposing constraints:

1. **Input overflow**: The script (50+ scenes), shot matrix (100+ shots), character bibles, and visual references all need to fit in the LLM's context window. With multiple artifacts feeding each phase, context explodes.

2. **Output truncation**: A screenplay is long. A shot matrix is long. Models have output token limits (8K for DeepSeek, 8K for Gemini Flash, 100K for GPT-4.1). Asking for "the complete script" can hit output limits.

ODR faces the same problem with both input (web pages are huge) and output (reports can be long). They solve it with a compression pipeline.

## How ODR Solves Input Overflow

### Layer 1: Truncation

```python
# Configurable truncation limit
max_char_to_include = configurable.max_content_length  # default 50000
result['raw_content'][:max_char_to_include]  # simple character truncation
```

Every piece of content gets a hard character cap. The limit is configurable per profile.

### Layer 2: Deduplication

```python
unique_results = {}
for response in search_results:
    for result in response['results']:
        url = result['url']
        if url not in unique_results:
            unique_results[url] = result
```

Same content doesn't get injected twice. In FPL terms: don't load both `script` and `story_bible` if the story bible is embedded in the script.

### Layer 3: Summarization

```python
# Truncate → summarize with dedicated model → inject summary, not raw content
summarization_model = init_chat_model(
    model=configurable.summarization_model,  # gpt-4.1-mini (cheaper)
    max_tokens=configurable.summarization_model_max_tokens  # 8192
).with_structured_output(Summary)

class Summary(BaseModel):
    summary: str
    key_excerpts: str
```

Raw web pages (50K chars) get compressed to structured summaries (2-3 paragraphs + key excerpts). A cheaper model does the compression so the expensive research model gets clean input.

### Layer 4: Parallel Compression

```python
summarization_tasks = [
    summarize_webpage(model, result['raw_content'][:max_char_to_include])
    for result in unique_results.values()
]
summaries = await asyncio.gather(*summarization_tasks)
```

All summaries happen in parallel with timeouts (60s each). If one fails, the original content is returned as fallback.

### Layer 5: Research Compression

After a researcher finishes gathering information, a *compression node* runs:

```python
compress_research_system_prompt = """Your job is to clean up the findings,
but preserve ALL relevant statements and information verbatim. Don't rewrite it,
don't summarize it, don't paraphrase it."""

# The model cleans redundant tool outputs while preserving facts
response = await synthesizer_model.ainvoke([
    SystemMessage(content=compression_prompt),
    *researcher_messages,
    HumanMessage(content="Clean up these findings. DO NOT summarize.")
])
```

This is smart compression — not summarization. It removes redundancy (duplicate tool results, repeated text), formats consistently, but preserves every fact verbatim. The output is cleaner but not shorter in content — just shorter in token waste.

## How ODR Solves Output Truncation

### 1. High Token Limits

```python
research_model_max_tokens: int = 10000       # Room for long outputs
final_report_model_max_tokens: int = 10000   # Final report can be long
compression_model_max_tokens: int = 8192     # Compression summary
summarization_model_max_tokens: int = 8192   # Search result summaries
```

ODR configures `max_tokens` per model role. Research model gets 10000. Final report gets 10000. Summarization gets 8192. This means the model is told "you have 10K tokens to work with, use them."

### 2. Token Limit Detection with Adaptive Retry

```python
def is_token_limit_exceeded(exception, model_name=None) -> bool:
    # Provider-specific detection
    # OpenAI: context_length_exceeded
    # Anthropic: prompt is too long
    # Gemini: ResourceExhausted

def handle_token_limit_exceeded(state, config):
    current_retry += 1
    if current_retry == 1:
        model_token_limit = get_model_token_limit(model_name)
        findings_token_limit = model_token_limit * 4  # 4 chars ≈ 1 token
    else:
        findings_token_limit = int(findings_token_limit * 0.9)  # Reduce 10% per retry
    findings = findings[:findings_token_limit]  # Truncate input, not output
```

When token limit is exceeded, ODR doesn't reduce the output — it reduces the *input*. The model still gets its full output budget.

### 3. Progressive Content Removal

```python
def remove_up_to_last_ai_message(messages):
    """Truncate message history by removing up to the last AI message."""
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            return messages[:i]  # Drop everything from last AI message onward
```

On token limit, ODR removes the most recent AI response and its associated tool calls from the history. This frees context for the model to produce a fresh response.

### 4. Structured Output for Controlled Size

```python
class Summary(BaseModel):
    summary: str          # Model fills this, but it's not unbounded
    key_excerpts: str     # Same — structured, bounded by schema

model.with_structured_output(Summary).invoke(prompt)
```

`with_structured_output()` tells the model to produce a specific JSON structure. The model can write long strings inside fields, but the structure itself prevents runaway outputs.

## The FPL Solution

### Part A: Input Context Budget

Introduce a **context budget** system. Every artifact that gets injected into a prompt costs "budget". The total budget equals the model's context window minus output budget minus prompt overhead.

```python
# agents/context_budget.py

from dataclasses import dataclass, field
from typing import Any
import json

# Token limits for FPL models (update with actual values)
MODEL_CONTEXT_LIMITS = {
    "deepseek/deepseek-chat": 65536,
    "google/gemini-3-flash-preview": 1048576,
    "deepseek/deepseek-v4-flash": 131072,
}

MODEL_OUTPUT_LIMITS = {
    "deepseek/deepseek-chat": 8192,
    "google/gemini-3-flash-preview": 8192,
    "deepseek/deepseek-v4-flash": 16384,
}

@dataclass
class ContextBudget:
    """Manages how much context each artifact can consume in a prompt."""

    model_id: str
    output_tokens_needed: int = 8192  # Budget for the model's output
    system_prompt_overhead: int = 500  # Fixed overhead
    safety_margin: float = 0.9  # 90% of context window

    @property
    def total_tokens(self) -> int:
        return int(
            MODEL_CONTEXT_LIMITS.get(self.model_id, 65536) * self.safety_margin
        )

    @property
    def available_for_input(self) -> int:
        """Tokens available for KB context + task + template."""
        return self.total_tokens - self.output_tokens_needed - self.system_prompt_overhead

    def allocate(self, num_artifacts: int, template_tokens: int = 1000) -> int:
        """Tokens per artifact after accounting for template and task."""
        available = self.available_for_input - template_tokens
        return max(1000, available // max(num_artifacts, 1))
```

### Part B: Artifact Compression Pipeline

ODR has a 3-step pipeline: truncate → deduplicate → summarize. FPL needs the same:

```python
# kb/compression.py

import asyncio
import json
import logging
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

_logger = logging.getLogger(__name__)

class ArtifactDigest(BaseModel):
    """Compressed artifact for context injection."""
    artifact_id: str
    artifact_type: str
    essential_summary: str = Field(description="1-2 paragraph summary of the artifact")
    key_facts: list[str] = Field(description="3-10 critical facts that downstream agents need")
    character_ids: list[str] = Field(default_factory=list)
    location_ids: list[str] = Field(default_factory=list)
    scene_ids: list[str] = Field(default_factory=list)
    structural_data: dict = Field(default_factory=dict)  # counts, durations, etc.


async def compress_artifact(
    artifact_data: dict[str, Any],
    artifact_id: str,
    artifact_type: str,
    max_chars: int = 8000,
    *,
    summarization_model: str = "google/gemini-3-flash-preview",
    timeout_seconds: float = 30.0,
) -> str:
    """Compress an artifact for context injection.

    Strategy depends on artifact size:
    - < max_chars: return as-is
    - max_chars to 4x max_chars: truncate to max_chars
    - > 4x max_chars: summarize with dedicated model

    If summarization fails or times out, falls back to truncation.
    """
    content_str = json.dumps(artifact_data, indent=2, ensure_ascii=False)

    if len(content_str) <= max_chars:
        return content_str

    if len(content_str) <= max_chars * 4:
        # Moderate overflow: just truncate with marker
        return (
            f"{content_str[:max_chars]}\n\n"
            f"[Truncated: {len(content_str) - max_chars} additional characters]"
        )

    # Large artifact: summarize
    try:
        model = init_chat_model(
            model=summarization_model,
            max_tokens=4096,
        ).with_structured_output(ArtifactDigest)

        digest = await asyncio.wait_for(
            model.ainvoke([HumanMessage(content=(
                f"Compress this film artifact ({artifact_type}: {artifact_id}) "
                f"for a downstream agent that needs to understand it:\n\n"
                f"{content_str[:content_str_limit]}"
            ))]),
            timeout=timeout_seconds,
        )

        return (
            f"[COMPRESSED: {artifact_type}:{artifact_id} "
            f"({len(content_str)} → ~{len(digest.essential_summary)} chars)]\n\n"
            f"Summary: {digest.essential_summary}\n\n"
            f"Key Facts:\n" + "\n".join(f"- {f}" for f in digest.key_facts) + "\n\n"
            f"Characters: {', '.join(digest.character_ids) or 'none'}\n"
            f"Locations: {', '.join(digest.location_ids) or 'none'}\n"
        )
    except asyncio.TimeoutError:
        _logger.warning("Artifact compression timed out, falling back to truncation")
        return f"{content_str[:max_chars]}\n\n[TRUNCATED after timeout]"
    except Exception as e:
        _logger.warning(f"Artifact compression failed: {e}, falling back to truncation")
        return f"{content_str[:max_chars]}\n\n[TRUNCATED after error]"
```

### Part C: Scoped Context Builder

Replace the current `_inject_artifact_context` which loads ALL artifacts with a scoped builder that respects the budget:

```python
# graph/context_packets.py — enhance existing PHASE_BUILDERS

async def build_scoped_context(
    state: dict[str, Any],
    services: GraphServices,
    phase: str,
    model_id: str,
) -> str:
    """Build scoped context that fits within the model's context budget."""
    budget = ContextBudget(model_id=model_id)

    # Determine which artifacts this phase needs (not ALL artifacts)
    required = get_required_artifacts_for_phase(phase)

    # Calculate budget per artifact
    tokens_per_artifact = budget.allocate(len(required))
    chars_per_artifact = tokens_per_artifact * 3  # ~3 chars per token

    # Load and compress in parallel
    async def load_and_compress(aid: str, atype: str) -> str | None:
        try:
            ref = state.get(f"{aid}_ref", "")
            if not ref:
                return None
            data = services.artifact_store.load(project_id, phase, aid, version)
            return await compress_artifact(
                data, aid, atype, max_chars=chars_per_artifact,
            )
        except Exception:
            return None

    tasks = [load_and_compress(aid, atype) for aid, atype in required]
    compressed = await asyncio.gather(*tasks)

    # Assemble: priority-ordered, compressed artifacts
    sections = []
    for (aid, atype), content in zip(required, compressed):
        if content:
            sections.append(f"## {atype}: {aid}\n{content}")

    return "\n\n".join(sections)


def get_required_artifacts_for_phase(phase: str) -> list[tuple[str, str]]:
    """Which artifacts does this phase actually need? Not all of them."""
    return {
        "intake": [],  # No upstream artifacts
        "constitution": [
            ("project_profile", "profile"),
        ],
        "development": [
            ("film_constitution", "constitution"),
        ],
        "script": [
            ("film_constitution", "constitution"),
            ("treatment", "treatment"),
            ("scene_list", "scene_list"),
        ],
        "visual_dev": [
            ("film_constitution", "constitution"),
            ("script", "script"),
            ("story_bible", "story_bible"),
        ],
        "shot_bible": [
            ("film_constitution", "constitution"),
            ("script", "script"),
            ("story_bible", "story_bible"),
            ("reference_index", "reference_index"),
        ],
        "gen_planning": [
            ("shot_matrix", "shot_matrix"),
            ("execution_brief", "execution_brief"),
        ],
        "generation": [
            ("shot_matrix", "shot_matrix"),
            ("provider_plan", "provider_plan"),
        ],
        "qc": [
            ("film_constitution", "constitution"),
            ("script", "script"),
            ("shot_matrix", "shot_matrix"),
            ("generation_ledger", "generation"),
        ],
        "post": [
            ("script", "script"),
            ("generation_ledger", "generation"),
            ("consensus_report", "consensus_report"),
        ],
        "delivery": [
            ("assembly_manifest", "assembly"),
            ("consensus_report", "consensus_report"),
        ],
    }.get(phase, [])
```

### Part D: Token Limit Detection + Adaptive Retry

Add to FPL's `PromptRunner` (currently just retries on ValueError):

```python
# agents/runner.py — enhance call_model()

def call_model(self, prompt, *, model_profile, agent_id=None):
    model_id, max_tokens, temperature, top_p, freq_penalty = (
        self.model_router.resolve_model_params(model_profile)
    )

    # Track context reduction across attempts
    original_prompt = prompt.rendered

    for attempt in range(3):
        try:
            return self.model_adapter.chat_json(
                prompt.rendered,
                model=model_id,
                system=prompt.role,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=freq_penalty,
            )
        except Exception as e:
            from film_pipeline.providers.failure_classifier import is_token_limit_exceeded

            if is_token_limit_exceeded(e, model_id):
                if attempt == 2:
                    _logger.error(
                        f"Token limit exceeded 3 times for {model_profile}. "
                        f"Model: {model_id}. Returning error."
                    )
                    return {
                        "status": "token_limit_exceeded",
                        "error": "exhausted_retries",
                        "model": model_id,
                        "profile": model_profile,
                    }

                # Reduce context progressively
                reduction = 0.7 - (attempt * 0.2)  # 70% → 50% → 30%
                prompt.rendered = _compress_context(original_prompt, factor=reduction)
                _logger.warning(
                    f"Token limit exceeded for {model_profile}. "
                    f"Reducing context to {reduction*100:.0f}% (attempt {attempt+1}/3)"
                )
                continue

            # ... existing ValueError retry logic ...
```

### Part E: Output Token Configuration

Explicitly set `max_tokens` per agent profile so the model knows it can write long outputs:

```python
# In ModelRouter profiles:
"creative_writer": {
    "primary": "deepseek/deepseek-chat",
    "max_tokens": 16384,      # UP from 8192 — room for long scripts
    "temperature": 0.7,
},
"shot_designer": {
    "primary": "deepseek/deepseek-chat",
    "max_tokens": 16384,      # Shot matrix can be long
    "temperature": 0.3,
},
"operations_triage": {
    "primary": "google/gemini-3-flash-preview",
    "max_tokens": 4096,       # Small operations answers
    "temperature": 0.2,
},
```

### Part F: Output Stitching for Very Long Content

When an agent needs to produce more than a single call's `max_tokens`, use the ODR approach of multi-call output assembly:

```python
async def generate_large_artifact(
    agent_id: str,
    task: str,
    context: str,
    model_id: str,
    max_tokens_per_call: int = 8192,
    max_calls: int = 5,
) -> dict[str, Any]:
    """Generate a large artifact that may exceed single-call output limits.

    Strategy: Generate in sections, stitch together.
    """
    # Step 1: Generate the plan/structure
    plan = await call_model(
        f"Plan the structure for: {task}\nContext: {context}",
        max_tokens=2048,
    )

    # Step 2: Generate each section
    sections = []
    for section in plan["sections"]:
        section_result = await call_model(
            f"Write section '{section['name']}' for: {task}\n"
            f"Previous sections: {_summarize_sections(sections)}\n"
            f"Context: {context}",
            max_tokens=max_tokens_per_call,
        )
        sections.append(section_result)

    # Step 3: Assemble
    return _assemble_sections(plan, sections)
```

This is the ODR pattern: the supervisor plans section structure, then parallel researchers write each section, then the final writer assembles.

## Configuration

Add to config profiles:

```yaml
# profiles/base.studio.yaml
context:
  max_chars_per_artifact: 8000
  max_total_context_tokens: 50000
  summarization_model: "google/gemini-3-flash-preview"
  summarization_timeout_seconds: 30
  compression_model: "google/gemini-3-flash-preview"
  safety_margin: 0.85  # Use 85% of context window

output:
  default_max_tokens: 8192
  creative_max_tokens: 16384
  allow_multipass_large_artifacts: true
  max_passes: 5
```

## Summary

| Problem | ODR Solution | FPL Implementation |
|---------|-------------|-------------------|
| Too much input | Truncation + dedup + summarization + parallel compression | ContextBudget + compress_artifact() + scoped context builder |
| Token limit exceeded | Detect provider → truncate input 10% → retry 3x | is_token_limit_exceeded() + progressive context reduction |
| Output too short | High max_tokens per profile (10K+) | Raise creative profiles to 16384 |
| Very long output | Multi-call generation with planning | generate_large_artifact() with section-based assembly |
| Timeout on compression | asyncio.wait_for(60s) → return original | Same pattern, 30s default |
| Deduplication | URL-based dedup of search results | Artifact-level dedup in context builder (same artifact_id skips reload) |
