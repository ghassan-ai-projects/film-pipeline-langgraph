# 07 — Agent Output Quality: Why Chat Beats Nodes

**Date:** 2026-06-22
**Question:** With the same prompts and models, chat interfaces produce detailed answers but agents/LLM nodes produce dry, short output. Why? How to fix?

**Context:** Builds on the user's analysis in `07-enritchment.md` (4 causes: system prompt contamination, max_tokens, chat history, temperature). This document verifies each against our actual code and finds additional issues.

---

## 1. Your 4 Points — Verified Against Our Code

### 1.1 System Prompt / Chat Wrapper Contamination — ✅ CONFIRMED, CRITICAL

**What chat interfaces do:** Wrap your prompt in a hidden system prompt like *"You are a helpful assistant. Be detailed. Use markdown formatting. Explain your reasoning step-by-step. Provide thorough answers. Anticipate follow-up questions."*

**What our agents get:** A one-line role string from the prompt template.

Evidence from our templates:

```python
# constitution-creator-v2 (defaults.py:194-195)
role="You are the constitution-agent (Constitution Creator). "
     "Your role is to define the creative constitution of a film project. "
     "This document governs every downstream creative decision."

# screenwriter-v1 (defaults.py:305-306)
role="You are the screenwriter-agent (Screenwriter). "
     "Your role is to write the full screenplay from the treatment."
```

These are **functional identity statements**, not quality directives. They tell the model WHO it is, not HOW to think. A chat wrapper adds 200-500 tokens of quality instructions. Our agents get 15-30 tokens of identity.

**What's missing from every role:**
- "Be thorough and detailed. Never summarize or be brief unless asked."
- "Explain your creative reasoning before outputting."
- "Use rich, evocative language appropriate for creative writing."
- "If you're uncertain about a detail, make a specific, defensible choice rather than being vague."
- "Produce complete, production-ready output — not sketches or outlines."

### 1.2 max_tokens — ⚠️ PARTIALLY CONFIRMED, BUT NOT THE MAIN ISSUE

**The user's analysis:** SDKs default to 256–512 tokens. Our code doesn't have this problem — we default to 4096 and `creative_writer` gets 8192.

```python
# model_routing/__init__.py:14-20
"creative_writer": {
    "primary": "deepseek/deepseek-chat",
    "fallback": "google/gemini-3-flash-preview",
    "max_tokens": 8192,
    "temperature": 0.7,
},
```

**But here's the twist:** The `creative_writer` profile IS defined, but it's **never used**. All agents default to `operations_triage`:

```python
# runner.py:142 — run_from_template() signature
def run_from_template(self, template, _kb_context, task, *,
    model_profile: str = "operations_triage",  # ← ALL agents use this
    context_vars=None,
) -> tuple[dict[str, Any], str, str]:
```

**Evidence from `_run_agent()` in `nodes.py:180`:**
```python
model_output, template_id, model_profile = services.prompt_runner.run_from_template(
    template, kb, task, context_vars=context_vars
    # ← NO model_profile= argument passed!
    # Falls through to default: "operations_triage"
)
```

**Result:** The screenwriter (creative) gets `temperature: 0.2, max_tokens: 4096`. The constitution creator gets `temperature: 0.2, max_tokens: 4096`. The shot bible creator gets `temperature: 0.2, max_tokens: 4096`.

This is the **single biggest quality issue in the codebase.** Every creative agent runs at near-zero temperature and moderate token limits.

### 1.3 Chat History Context — ✅ CONFIRMED, MAJOR

**What chat interfaces do:** Accumulate the full conversation — user messages, assistant responses, follow-ups — and feed the entire history back to the model on every turn. The model builds on its own previous thinking.

**What our agents get:** Isolated one-shot prompts. Every `_run_agent()` call is a fresh context with no memory of what the agent produced before or what other agents have done.

```python
# nodes.py:24 — every agent call starts from scratch
def _run_agent(state, agent_id, phase, task, *, task_type="create"):
    # Builds context_vars from state
    # Calls model
    # Returns result
    # NOTHING persists between calls
```

**Why this matters for quality:** In chat, if you ask "write a film treatment" and the response is short, you say "make it more detailed" and the model has the full context of its first attempt. In our pipeline, the repair loop reconstructs context from scratch — the agent doesn't see its previous attempt, only the repair feedback string.

### 1.4 Temperature — ✅ CONFIRMED, CRITICAL

**The user's analysis:** Chat interfaces use 0.7–0.9. API defaults use 0.0–0.2.

**Our reality is worse than described:**

| Profile | Temperature | Used By |
|---------|------------|---------|
| `creative_writer` | 0.7 | **No one** — defined but unreachable |
| `cheap_draft` | 0.8 | **No one** — defined but unreachable |
| `operations_triage` | **0.2** | **Every agent** — the default |
| `strict_validator` | 0.1 | Validators (via `validation/base.py:139`) |
| `schema_enforcer` | 0.0 | **No one** |

```python
# model_routing/__init__.py:48-55
"operations_triage": {
    "primary": "google/gemini-3-flash-preview",
    "fallback": "deepseek/deepseek-chat",
    "max_tokens": 4096,
    "temperature": 0.2,     # ← THIS is what the screenwriter gets
},
```

**Impact at temperature 0.2:**
- The model selects the most probable token at every step — no creative deviation
- Output is deterministic, clinical, brief
- Characters feel flat, dialogue is generic, descriptions are formulaic
- Exactly the "dry, 3-sentence summary" the user described

**The fix is trivial — route creative agents to creative profiles:**

```python
# In _run_agent(), select profile based on agent role
_PROFILE_BY_AGENT = {
    "screenwriter-agent": "creative_writer",
    "film-constitution-agent": "creative_writer",
    "treatment-agent": "creative_writer",
    "shot-design-agent": "creative_writer",
    "visual-dev-agent": "creative_writer",
    "structure-extractor-agent": "strict_validator",
    "clip-validator": "strict_validator",
    "provider-planning-agent": "operations_triage",
    # ...
}

model_profile = _PROFILE_BY_AGENT.get(resolved_agent_id, "operations_triage")
```

---

## 2. Additional Issues Specific to Our Codebase

Beyond the 4 points from your analysis, these are equally damaging:

### 2.5 Forced JSON Output with `chat_json()` — Kills Creative Thinking

Every critical-path agent call goes through `chat_json()`:

```python
# runner.py:124-132
model_id, max_tokens, temperature = self.model_router.resolve_model_params(model_profile)
return self.model_adapter.chat_json(
    prompt.rendered,
    model=model_id,
    system=prompt.role,
    max_tokens=max_tokens,
    temperature=temperature,
)
```

`chat_json()` defaults to `temperature=0.3` — but the router's resolved `temperature` **overrides** this. So the actual temperature comes from the profile.

**However**, `chat_json()` has 4 extraction strategies:

```python
# model_adapter.py:231-290
def chat_json(self, prompt, *, model, system="", max_tokens=4096, temperature=0.3):
    text = self.chat(prompt, ...).strip()
    # Strategy 1: Direct JSON parse
    # Strategy 2: Extract from markdown fences
    # Strategy 3: Find outermost brace pair
    # Strategy 4: Find outermost bracket pair
```

This is **correct and robust** — but the model is told "Respond with valid JSON" in every output format. This means:
- The model allocates cognitive capacity to JSON syntax compliance instead of creative quality
- No room for "thinking out loud" before producing JSON
- The model can't use chain-of-thought (which dramatically improves quality on complex tasks)

**Evidence from templates:**

```python
# Every output_format ends with:
output_format=(
    "Respond with valid JSON matching the X schema:\n"
    "{\n"
    '  "shot_matrix": {\n'
    # ... rigid JSON template
)
```

### 2.6 Dedicated Template Rendering Bypasses Quality Instruction Sections

`run_from_template()` takes the template's `rendered_text` and builds a `RCTCOPrompt`:

```python
# runner.py:167-179
def run_from_template(self, template, ...):
    rendered_text = template.render(**(context_vars or {}))

    prompt = RCTCOPrompt(
        role=template.role,
        core_task=task,
        context=rendered_text,       # ← THE ENTIRE TEMPLATE becomes "context"
        constraints=template.constraints,
        output_format=template.output_format,
    )
    prompt.rendered = rendered_text  # ← OVERWRITTEN to just the rendered text
```

So the model receives `prompt.rendered` which is the raw template with context variables substituted. The role, core_task, constraints, and output_format from the template are embedded in the rendered text. But the `RCTCOPrompt.__post_init__` formatting that adds `# Role`, `# Core Task` headers is **never used** for dedicated templates — it's only used for generic RCTCO via `run()`.

This is fine structurally (the template has its own formatting), but it means the role text is whatever the template defines — and templates only define identity, not quality instructions.

### 2.7 No Chain-of-Thought Prompting

Compare:

**What we send:**
```
You are the screenwriter-agent. Write the full screenplay.
Respond with valid JSON: { "script": { "scenes": [...] } }
```

**What chat interfaces effectively send:**
```
You are a creative screenwriter. Think step by step:
1. First, understand the treatment and constitution
2. Plan the three-act structure
3. For each scene, determine the dramatic function
4. Write dialogue that serves character and plot
5. Review for consistency and completeness
Be thorough. Use vivid language. Every scene must have a clear purpose.
Respond with valid JSON.
```

The difference is **structural thinking instructions** — telling the model HOW to arrive at the answer, not just WHAT to output. Research shows chain-of-thought prompting improves quality by 20-40% on complex creative tasks.

### 2.8 Mock Responses Train Agents on Minimal Data

In mock mode, every agent gets the same canned responses from `_default_mock_responses()`:

```python
# services.py:275-355 — a 100-shot matrix mock is 2 rows
"shot_matrix": {
    "rows": [
        {"shot_id": "shot_0001", ...},  # only 2 rows!
        {"shot_id": "shot_0002", ...},
    ],
}
```

Agents are tested and their parsing logic is built against **minimal 2-row mock data**. When they encounter real 100-shot matrices, the parsing code hasn't been exercised at scale. This doesn't directly affect LLM output quality but means the agent `execute()` methods may silently drop data or mishandle edge cases that only appear with realistic input sizes.

---

## 3. The Fix — Concrete Changes

### Fix 1 (P0): Route Creative Agents to Creative Profiles

```python
# New: graph/nodes.py — add profile routing before agent execution
_AGENT_PROFILE_MAP: dict[str, str] = {
    "intake-classifier-agent": "operations_triage",
    "film-constitution-agent": "creative_writer",
    "treatment-agent": "creative_writer",
    "screenwriter-agent": "creative_writer",
    "structure-extractor-agent": "strict_validator",
    "shot-design-agent": "creative_writer",
    "reference-strategy-planner": "visual_reasoner",
    "visual-dev-agent": "creative_writer",
    "provider-planning-agent": "operations_triage",
    "clip-validator": "strict_validator",
    "failure-handling-agent": "operations_triage",
}

# In _run_agent(), after resolving the agent:
model_profile = _AGENT_PROFILE_MAP.get(resolved_agent_id, "operations_triage")
model_output, template_id, _ = services.prompt_runner.run_from_template(
    template, kb, task, context_vars=context_vars, model_profile=model_profile
)
```

**Impact:** Creative agents go from temperature 0.2 → 0.7, max_tokens 4096 → 8192. Validators stay at 0.1 for consistency.

### Fix 2 (P0): Add Quality Instructions to Prompt Templates

Add a `quality_instructions` field to every template:

```python
# New field on PromptTemplate
quality_instructions: str = (
    "QUALITY STANDARDS:\n"
    "- Be thorough and detailed. Never summarize unless explicitly asked.\n"
    "- For creative writing: use vivid, sensory language. Make specific choices.\n"
    "- If uncertain, make a concrete, defensible decision rather than being vague.\n"
    "- Produce complete output — not sketches, outlines, or placeholders.\n"
    "- Review your output for internal consistency before finalizing."
)
```

Or, simpler: add it to the `role` field of creative templates:

```python
role=(
    "You are the screenwriter-agent (Screenwriter). "
    "Your role is to write the full screenplay from the treatment.\n\n"
    "QUALITY REQUIREMENTS:\n"
    "- Be thorough and detailed — every scene needs complete dialogue and action.\n"
    "- Use vivid, cinematic language. You are writing for production, not summary.\n"
    "- Make specific creative choices. Never be vague or generic.\n"
    "- Review for dramatic consistency: setups must have payoffs, characters must arc."
)
```

### Fix 3 (P1): Add Chain-of-Thought to Complex Agents

For agents doing complex creative work (screenwriter, shot designer, constitution), restructure the prompt to encourage reasoning before output:

```python
core_task=(
    "Create a FilmConstitution from the project idea. "
    "Think through each section before writing:\n\n"
    "STEP 1 — Theme: What is the single most important idea this film explores?\n"
    "STEP 2 — Tone: Given the theme, what emotional register serves it best?\n"
    "STEP 3 — Visual Language: What visual approach reinforces the theme and tone?\n"
    "STEP 4 — Character Truths: For each named character, what is their unchanging core?\n"
    "STEP 5 — Taboos: What creative choices would betray the film's identity?\n\n"
    "After you have thought through each step, produce the complete JSON output."
)
```

This mirrors the chat experience where the model "thinks" before answering. The JSON extraction (4 strategies in `chat_json()`) already handles models that output reasoning before JSON — we just need to tell the model to do so.

### Fix 4 (P1): Accumulate Agent History in State

For repair/revision loops, preserve the agent's previous output so it can build on it:

```python
# In repair_phase_node, instead of just injecting feedback:
state["_previous_agent_output"] = previous_output  # the full previous attempt
state["_repair_feedback"] = {
    "round": round_num,
    "previous_output_summary": summarize_previous(previous_output),
    "specific_issues": [...],
    "what_was_good": [...],  # preserve what worked
}
```

The agent now has context: "Your previous attempt had 12 shots (need 20). The 12 you wrote are good — keep them and add 8 more in act_1." This mirrors chat's iterative refinement.

### Fix 5 (P2): Per-Agent Temperature Calibration

Current profiles are too coarse. Add finer-grained control:

```python
_DEFAULT_PROFILES = {
    "creative_writer": {
        "max_tokens": 8192,
        "temperature": 0.8,     # was 0.7 — screenwriting needs more creativity
    },
    "creative_writer_json": {   # NEW: creative work with structured output
        "max_tokens": 8192,
        "temperature": 0.6,     # slightly cooler for JSON compliance
    },
    "visual_reasoner": {
        "max_tokens": 4096,
        "temperature": 0.4,     # was 0.3 — needs some creativity for visual descriptions
    },
    # ...
}
```

### Fix 6 (P2): Add `top_p` and `frequency_penalty` to ModelAdapter

Chat interfaces use additional sampling parameters:

```python
def _request(self, messages, model, max_tokens=4096, temperature=0.7,
             top_p=0.95, frequency_penalty=0.1):
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,                          # NEW
        "frequency_penalty": frequency_penalty,   # NEW — reduces repetition
    }
```

`frequency_penalty` is especially important for creative agents — it prevents the model from repeating the same phrases, making dialogue and descriptions more varied and natural.

---

## 4. Summary — Root Cause Hierarchy

| Rank | Cause | Impact | Fix Difficulty |
|------|-------|--------|---------------|
| **#1** | All agents use `operations_triage` (temp 0.2) | Creative quality destroyed | Trivial — add profile map |
| **#2** | Role fields lack quality instructions | Model doesn't know to be detailed | Easy — add to templates |
| **#3** | No chain-of-thought prompting | Model jumps to output without reasoning | Easy — restructure core_task |
| **#4** | No chat history accumulation | Agents can't build on previous attempts | Medium — add to state |
| **#5** | max_tokens at 4096 for creative work | Long scripts get truncated | Trivial — use creative_writer (8192) |
| **#6** | No frequency_penalty | Dialogue and descriptions get repetitive | Easy — add to adapter |
| **#7** | JSON-output pressure (temp 0.3 default in chat_json) | Model prioritizes syntax over quality | Handled by profile routing (fix #1) |

**The single-line fix that would have the biggest impact:**

```python
# In _run_agent(), change one line:
model_profile = _AGENT_PROFILE_MAP.get(resolved_agent_id, "operations_triage")
```

This routes the screenwriter from temperature 0.2 → 0.7 and doubles its token budget. Combined with adding quality instructions to the role fields (fix #2), these two changes would close most of the quality gap between chat and agent output.

### Files Referenced

| File | Lines | Role |
|------|-------|------|
| `agents/model_routing/__init__.py` | 137 | 8 profiles — creative_writer exists but unused |
| `agents/runner.py` | 217 | run_from_template defaults to operations_triage |
| `graph/nodes.py:24-218` | ~195 | _run_agent() — never passes model_profile |
| `agents/model_adapter.py` | 294 | chat_json with 4 extraction strategies, temp 0.3 default |
| `agents/prompt_templates/defaults.py` | 1079 | All templates — roles are identity-only, no quality instructions |
| `agents/base.py` | 59 | BaseAgent lifecycle — no profile awareness |
