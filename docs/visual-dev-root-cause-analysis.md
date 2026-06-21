# Visual Dev Agent Failure — Root Cause Analysis

## Symptom

When the pipeline advances from `script` → `visual_dev`, the node runs
`reference-strategy-planner` and the `VisualDevAgent.execute()` method raises
a validation error or produces "invalid output", blocking the pipeline.

```
⚠ Agent 'reference-strategy-planner' produced invalid output.
```

## Root Cause

### 1. Prompt template output schema mismatch

The prompt template (`visual-dev-creator-v1` at
`src/film_pipeline/agents/prompt_templates/defaults.py:232`) tells the model:

> Respond with valid JSON matching the visual development schema.
> output_schema_ref: "reference.VisualReference"

But the `VisualDevAgent.execute()` method (at
`src/film_pipeline/agents/impl/visual_dev_agent.py:42`) expects this JSON
shape:

```python
{
    "visual_dev": {
        "reference_entries": [ ... ],
        "project_id": "...",
    }
}
```

And within each entry, it expects keys like:
- `reference_id`, `asset_path`, `asset_type`, `subject_type`, `subject_id`
- `approved_for`, `quality_score`, `provider`, `prompt_text`, `prompt_refs`
- `source_frames`, `notes`, `validation`, `ai_usability`

The model receives no example of this output shape. The prompt says "visual
development schema" but doesn't show the actual structure. Gemini generates
free-form JSON that doesn't match `ReferenceIndexEntry`'s fields.

**Fix:** Add a concrete JSON example in the prompt's `output_format` showing
the actual `ReferenceIndex` / `ReferenceIndexEntry` shape.

### 2. No dedicated `_run_agent` for visual_dev resolution

In `nodes.py:480-498`, `visual_dev_node` calls `_run_agent` with:

```python
_run_agent(
    new_state,
    agent_id="reference-strategy-planner",
    phase="visual_dev",
    task="Create visual development references from the script and constitution.",
)
```

The `_run_agent` function (line 120) resolves the prompt template for
`agent_id="reference-strategy-planner"` and injects context variables. This
works, but the problem is at **line 148**:

```python
instance: BaseAgent = agent_cls(contract)
result = instance.run(state, kb, task, model_output)
```

`agent_cls` maps to `VisualDevAgent`. The `model_output` is the raw text from
the LLM. `VisualDevAgent.execute()` tries to parse `model_output` as a dict
with `.get("visual_dev", model_output)` — but `model_output` is a **string**,
not a dict. The `model_adapter.chat_json()` returns a `dict[str, Any]`, but
if it falls through to the string-based parsing in `chat_json` (strategy 2-4),
the result gets returned as a `dict` but with keys like `"entries"` at the top
level, not under `"visual_dev"`.

**Fix:** The `execute()` method's first line `data = model_output.get("visual_dev", model_output)` is a fragile key check. Make it robust by checking
both `model_output.get("visual_dev")` and `model_output.get("reference_entries")`
as well as direct iteration over keys.

### 3. No `agent_cls` resolution for some agents

The `_run_agent` function resolves the agent ID through the knowledge base.
If the KB sets a different `resolved_agent_id` than "reference-strategy-planner",
the `agent_map` won't have a matching class. The KB resolution happens at
line ~55:

```python
resolved_agent_id = kb.resolve_agent_id(phase, agent_id, task)
```

If this returns a different agent ID (like "visual-dev-agent" instead of
"reference-strategy-planner"), no agent class will be found in `agent_map`.

**Fix:** Check what `resolve_agent_id` returns for the visual_dev phase. Add
"visual-dev-agent" → VisualDevAgent to the agent_map if needed.

### 4. Incomplete artifact context injection

`_inject_artifact_context` loads upstream artifacts (constitution, script, etc.)
and injects them as context variables. But the context template for
`visual-dev-creator-v1` references `{script_content}`, `{story_bible_content}`,
`{constitution_content}`. If the keys for those artifacts don't match what's
stored (e.g. `project_profile` for intake, `film_constitution` for constitution),
the content is empty and the model has no context to work with.

**Fix:** Verify the artifact ID matching in the prompt template's context template
vs. what `_inject_artifact_context` actually loads.

## What works (for contrast)

The intake → constitution → development → script pipeline runs successfully
with Gemini 3.1 Flash because:

1. Their prompt templates have explicit JSON output examples
2. Their agent `execute()` methods are more resilient to key mismatches
3. The upstream artifacts already exist by the time those agents run

## Current state

- `script` phase completes: two artifacts saved (`script:script`, `script:story_bible`)
- `approve_phase` advances to `visual_dev`
- `visual_dev_node` runs `_run_agent` → LLM call succeeds → `VisualDevAgent.execute()`
  fails to parse output → returns incomplete dict → `validate()` returns False →
  `reference_index` is None → no artifact saved → pipeline stuck

## Suggested fix plan

1. **Update `_visual_development_creator()` prompt template** — add a concrete
   JSON example of `ReferenceIndexEntry` in `output_format`
2. **Harden `VisualDevAgent.execute()`** — accept both top-level keys and
   nested keys, handle string vs dict model_output
3. **Add "visual-dev-agent" alias to `agent_map`** in nodes.py
4. **Test** by running visual_dev approval and checking artifact store
