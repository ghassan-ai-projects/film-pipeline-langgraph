# Validation Comparison — ODR vs. FPL

## What Each System Validates

### ODR: Output Quality Evaluation (Post-Hoc)
- **When**: After the report is generated, by a separate evaluation harness
- **What**: The final report's quality against 6 axes
- **How**: LLM-as-judge (GPT-4.1) with structured Pydantic scoring
- **Where**: In tests/ — a separate evaluation system, not in the graph

### FPL: Structural Gatekeeping (In-Line)
- **When**: Within each phase node and at approval gates
- **What**: Artifact structure, completeness, format correctness
- **How**: Rule-based checks + optional LLM validation fallback
- **Where**: In validation/impl/ — integrated into graph nodes

## Detailed Comparison

### 1. Scoring Model

| Aspect | ODR | FPL |
|--------|-----|-----|
| **Scoring method** | LLM-as-judge: GPT-4.1 evaluates output | Rule-based: heuristics on structural properties |
| **Score type** | 1-5 with detailed reasoning per axis | 0-100 computed from issue counts |
| **Judgment source** | Separate model from the generation model | Same system, different validator instance |
| **Reasoning** | Every score includes specific examples | Issues have messages, no examples |
| **Bias risk** | Low (different model, different prompt) | Low (rule-based, no LLM self-review) |

**ODR approach**: `eval_model.with_structured_output(OverallQualityScore).invoke([...])` — a separate GPT-4.1 call with a dedicated evaluation prompt that produces a Pydantic model with 6 sub-scores and justifications.

**FPL approach**: `score = 100.0; score -= blocking_count * 25.0; score -= warning_count * 10.0` — arithmetic on pre-defined penalties.

### 2. Evaluation Axes

#### ODR: 6 Quality Axes
1. **Research Depth** — thoroughness, coverage, background context
2. **Source Quality** — authority, diversity, citation quality
3. **Analytical Rigor** — sophistication, critical evaluation, nuance
4. **Practical Value** — clarity, specificity, actionability
5. **Balance & Objectivity** — multiple perspectives, limitations, bias avoidance
6. **Writing Quality** — clarity, terminology, consistency, engagement

Each axis has a dedicated Pydantic model and prompt. Each score includes reasoning with specific examples.

#### FPL: 8 Structural Validators
1. **Script Structure** — scene count, intent mapping, conflict presence, dialogue density
2. **Dialogue Voice** — character voice differentiation, exposition load, generic phrases
3. **Scene Continuity** — character state tracking, prop tracking, lighting, wardrobe
4. **Reference Usability** — resolution, moderation risk, subject type, generation status
5. **Prompt Readiness** — RCTCO completeness, artifact refs, prompt length, constraints
6. **Assembly** — clip ordering, transition validity, missing assets
7. **Delivery Completeness** — output format, file existence
8. **Consensus Builder** — multi-validator agreement synthesis

Each is rule-based with heuristics (keyword matching, ratio checks, count thresholds).

### 3. What ODR Has That FPL Doesn't

#### a) Separate evaluation model
ODR uses a *different* model for evaluation (`gpt-4.1`) than for generation. This prevents the "mark your own homework" problem. FPL's LLM validation would use the same model family.

#### b) Groundedness verification
```python
class GroundednessClaim(BaseModel):
    claim: str
    grounded: bool

# Extract every claim from the report
# Verify each claim against the source context
# Score = grounded_claims / total_claims
```

This doesn't exist in FPL. No validator checks if the generated script actually reflects the treatment and constitution.

#### c) Completeness evaluation
```python
# Compare report against research brief + user question
# "Does the report answer all points?"
COMPLETENESS_PROMPT = """Identify any points not covered by the report.
Compare against the research brief and user question."""
```

FPL's validators check structural completeness (scene count, intent refs) but not *content* completeness (does the script tell the full story?).

#### d) Correctness against reference
```python
# Compare report against a known-correct answer
def eval_correctness(inputs, outputs, reference_outputs):
    answer = reference_outputs["answer"]
    # Score 1-5 on how well report mirrors the authority answer
```

FPL has no reference answers to compare against.

#### e) Benchmark dataset
ODR uses `"Deep Research Bench"` — a LangSmith dataset of inputs with known outputs. Every evaluation run is reproducible and comparable.

FPL has no evaluation dataset.

### 4. What FPL Has That ODR Doesn't

#### a) Multi-validator consensus
FPL's `ConsensusBuilder` aggregates multiple validator reports and computes agreement levels, shared findings, and disagreements. ODR evaluates one report at a time with a single model.

#### b) Validator registry with scoping
```python
ValidatorRegistry:
    - lookup_by_scope(ValidationScope.SCENE)
    - lookup_by_modality(ValidationModality.TEXT)
    - enabled_only()
```

ODR's evaluators are standalone functions, no registry.

#### c) Blocking vs. warning classification
FPL issues can be `blocking` (halts pipeline) or `warning` (pass with notes). ODR's scores are continuous; there's no blocking concept.

#### d) Threshold configuration
```python
ValidatorThresholds(pass_at=85, review_at=75, block_below=75)
```
Each validator has configurable thresholds. ODR uses raw 1-5 scores.

#### e) Matrix patches from validation
FPL's validators produce `MatrixRowUpdate` patches that feed back into the shot matrix. ODR has no such feedback loop.

### 5. The Core Gap: FPL Validates Structure, Not Quality

This is the fundamental difference:

- **ODR asks**: "Is this report *good*?" (quality, depth, correctness, groundedness)
- **FPL asks**: "Is this artifact *valid*?" (structure, completeness, format)

FPL can tell you:
- The script has 3 scenes ✓
- Every scene has an intent_ref ✓
- No scene has >15 dialogue lines ✓
- Conflict keywords appear in 60% of scenes ✓

FPL cannot tell you:
- The script is emotionally compelling ❌
- The dialogue sounds natural ❌
- The scenes flow with proper dramatic tension ❌
- The characters feel distinct and real ❌
- The story matches the constitution's emotional promise ❌

## The Fix: Add Quality Evaluation Layer

FPL should keep its structural validators AND add quality evaluation.

### New Layer: Quality Evaluators (LLM-as-Judge)

```python
# validation/quality/ (new package)

from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model

# ── Quality axes for film artifacts ──

class ScriptQualityScore(BaseModel):
    """Evaluate script quality on creative dimensions."""
    dramatic_tension: int = Field(description="1-5: How well does dramatic tension build?")
    character_voice: int = Field(description="1-5: Are character voices distinct and consistent?")
    dialogue_naturalness: int = Field(description="1-5: Does dialogue sound natural, not expositional?")
    scene_pacing: int = Field(description="1-5: Is pacing appropriate for each scene's function?")
    emotional_impact: int = Field(description="1-5: Will audiences feel the intended emotions?")
    reasoning: str = Field(description="Detailed reasoning with specific scene examples.")


class ConstitutionQualityScore(BaseModel):
    """Evaluate constitution quality."""
    thematic_clarity: int = Field(description="1-5: Is the theme clearly defined and compelling?")
    visual_language_specificity: int = Field(description="1-5: Is visual language concrete, not vague?")
    emotional_promise_feasibility: int = Field(description="1-5: Can this promise be delivered?")
    coherence: int = Field(description="1-5: Do all elements support each other?")
    reasoning: str


class ShotMatrixQualityScore(BaseModel):
    """Evaluate shot matrix quality."""
    coverage_completeness: int = Field(description="1-5: Are all scenes properly covered?")
    creative_shot_design: int = Field(description="1-5: Are shots creatively designed, not just functional?")
    continuity_flow: int = Field(description="1-5: Do shots flow naturally between scenes?")
    duration_realism: int = Field(description="1-5: Are shot durations feasible?")
    reasoning: str


# ── Evaluator classes ──

class ScriptQualityEvaluator:
    """LLM-as-judge for script quality."""

    EVAL_MODEL = "google/gemini-3-flash-preview"  # Cheaper than creative model

    async def evaluate(
        self,
        script: dict[str, Any],
        constitution: dict[str, Any] | None = None,
        treatment: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate script quality against the constitution and treatment."""
        model = init_chat_model(
            model=self.EVAL_MODEL,
            max_tokens=4096,
        ).with_structured_output(ScriptQualityScore)

        context = self._build_context(script, constitution, treatment)

        try:
            result = await asyncio.wait_for(
                model.ainvoke([HumanMessage(content=(
                    SCRIPT_QUALITY_PROMPT.format(**context, date=get_today_str())
                ))]),
                timeout=45.0,
            )
        except asyncio.TimeoutError:
            return {"status": "eval_timeout", "score": 0}

        overall = (
            result.dramatic_tension +
            result.character_voice +
            result.dialogue_naturalness +
            result.scene_pacing +
            result.emotional_impact
        ) / 25.0  # Normalize 0-1 from 5 axes × 5 max each

        return {
            "overall_score": overall,
            "axes": {
                "dramatic_tension": result.dramatic_tension,
                "character_voice": result.character_voice,
                "dialogue_naturalness": result.dialogue_naturalness,
                "scene_pacing": result.scene_pacing,
                "emotional_impact": result.emotional_impact,
            },
            "reasoning": result.reasoning,
        }
```

### Quality Evaluation Prompts

```python
SCRIPT_QUALITY_PROMPT = """You are an expert screenplay evaluator. Assess this film script against creative quality dimensions.

**Film Constitution (what the film promises):**
Theme: {theme}
Tone: {tone}
Emotional Promise: {emotional_promise}
Visual Language: {visual_language}

**Treatment Summary:**
{treatment_summary}

**Script (scenes {total_scenes}):**
{script_snippet}

Evaluate on 5 dimensions (1-5 each):
1. **Dramatic Tension**: Does tension build effectively through the scenes? Are stakes clear and escalating?
2. **Character Voice**: Are character voices distinct? Can you tell who's speaking without names?
3. **Dialogue Naturalness**: Does dialogue sound like real people, not exposition delivery?
4. **Scene Pacing**: Is each scene's duration/density appropriate for its dramatic function?
5. **Emotional Impact**: Will audiences feel what the scene intends? Does it match the emotional promise?

For each dimension, provide specific scene examples. If a dimension scores low, explain exactly what's wrong.

Today is {date}
"""
```

### Integration: Quality Evaluation in the Graph

Quality evaluation runs AFTER structural validation, BEFORE the orchestrator reviews:

```python
# In graph/nodes.py — enhance each phase node

def script_node(state):
    # ... existing structural validation ...

    # NEW: Quality evaluation (if enabled in config)
    quality_config = state.get("resolved_config", {}).get("quality", {})
    if quality_config.get("evaluate_quality", True):
        quality_result = await _evaluate_script_quality(state, services)
        state.setdefault("quality_reports", []).append(quality_result)

    # Orchestrator now sees: structural issues + quality scores
    ...


# Orchestrator review includes quality data
def _build_phase_context(state):
    ctx = _build_structural_context(state)  # Existing

    # NEW: Include quality evaluation if available
    quality_reports = state.get("quality_reports", [])
    if quality_reports:
        latest = quality_reports[-1]
        ctx["quality_overall"] = f"{latest['overall_score']:.2f}"
        ctx["quality_detail"] = json.dumps(latest.get("axes", {}), indent=2)
        ctx["quality_reasoning"] = latest.get("reasoning", "")

    return ctx
```

### Evaluation Dataset

Create a benchmark dataset for reproducible quality testing:

```python
# evaluation/benchmark.py

FILM_EVAL_DATASET = [
    {
        "name": "short_narrative_test",
        "input": {"idea": "A robot discovers it has feelings."},
        "expected": {
            "constitution": {"theme": "identity", "tone": "contemplative"},
            "script_min_scenes": 3,
            "script_max_scenes": 8,
            "dialogue_quality_threshold": 0.7,
            "pacing_threshold": 0.6,
        }
    },
    {
        "name": "complex_ensemble_test",
        "input": {"idea": "Three strangers trapped in an elevator must confront their shared past."},
        "expected": {
            "character_voice_differentiation": 0.8,  # Three distinct voices required
            "dramatic_tension_build": 0.7,
            "dialogue_naturalness": 0.75,
        }
    },
    # ... more test cases ...
]

async def run_benchmark(graph, dataset):
    """Run the pipeline on each test case and evaluate quality."""
    results = []
    for case in dataset:
        result = await graph.ainvoke({"messages": [{"role": "user", "content": case["input"]["idea"]}]})
        quality = await evaluate_quality(result, case["expected"])
        results.append({"case": case["name"], "passed": quality["passed"], "scores": quality["scores"]})
    return results
```

## Summary: What to Build

| Layer | Current State | Add |
|-------|--------------|-----|
| **Structural Validation** | ✅ Complete (8 validators) | Keep as-is, enhance keyword detection |
| **Quality Evaluation** | ❌ Missing | Add LLM-as-judge for script, constitution, shot matrix |
| **Groundedness** | ❌ Missing | Verify script claims against treatment and constitution |
| **Completeness** | ⚠️ Structure only | Add content completeness (does the script tell the full story?) |
| **Benchmark Dataset** | ❌ Missing | Curate 5-10 test cases with expected quality scores |
| **Multi-Validator Consensus** | ✅ Complete | Wire quality scores into existing ConsensusBuilder |
| **Feedback Loop** | ⚠️ Issues only | Add quality scores to orchestrator context and MCP surface |

## Cost Impact

Quality evaluation adds LLM calls. Mitigation:
- Use **cheapest capable model** for evaluation (gemini-flash, not the creative model)
- Run quality evaluation **only when human approval is required** (skip in draft mode)
- **Parallel evaluation**: all quality axes in one call (single prompt, multi-score output)
- **Configurable**: disable quality eval via `profiles/quality.none.yaml`

## Key Distinction

ODR's validation says "is this good?" — FPL's validation says "is this valid?".
Both matter. FPL needs both. The structural validators (rule-based, fast, deterministic) catch format errors. The quality evaluators (LLM-as-judge, slower, subjective) catch creative weakness. Together they give the orchestrator a complete picture:

```
Orchestrator Review Package:
├── Structural: scene_count=8, missing_intents=0, dense_dialogue=2 ✅
├── Quality: overall=0.72, dramatic_tension=3/5, dialogue=4/5 ⚠️
├── Issues: [dialogue_dense: scenes sc_003, sc_007]
└── Recommendation: PASS_WITH_NOTES (fix dialogue density, acceptable quality)
```
