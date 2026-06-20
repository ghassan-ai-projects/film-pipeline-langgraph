# OpenClaw MCP Operator Guide

This guide covers the OpenClaw production MCP path — real models, real providers,
profile-aware project setup. It is **not** the mock-first demo path.

For the mock demo path, use the [manual 4-minute mock short](../documentation/manual-4min-mock-short.md).

---

## Two Modes

| Mode | Path | Purpose | Mock allowed? |
|------|------|---------|---------------|
| **mock** | `make run-mcp` | Local development, CI, demos | Yes |
| **real** | OpenClaw via MCP with `runtime_mode: "real"` | Production operator use | No |

OpenClaw should always operate in **real** mode. The runtime guard in
`create_film_project` enforces this — passing `runtime_mode: "real"` with
mock provider/model ids is rejected before project creation.

---

## Before Starting

### Required environment variables

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

Without this, real model calls will fail. `list_profiles` and `inspect_profile`
work read-only regardless.

### Verify profiles exist

```bash
ls profiles/*.yaml
```

You should see at minimum:
- `base.studio.yaml` — studio defaults
- `provider.seedance_primary.yaml` — real provider stack (Seedance via OpenRouter)
- `provider.free_or_low_cost.yaml` — cost-conscious alternative
- `quality.studio.yaml` — model routing preferences for studio quality
- `quality.draft.yaml` — draft-quality model routing
- `quality.festival.yaml` — festival-quality model routing
- `film-type.narrative.yaml` — narrative film conventions
- `film-type.visual_poetry.yaml` — visual poetry conventions
- `film-type.experimental.yaml` — experimental film conventions
- `review.strict_continuity.yaml` — strict continuity review
- `local-real-provider.yaml` — local development with real provider
- `mock-demo.yaml` — mock mode (rejected in real mode)

---

## Workflow

### 1. Discover available profiles

```
MCP: list_profiles
```

Returns every profile in `profiles/` with id, name, description, and `studio_mode`.

Example response:
```json
{
  "ok": true,
  "profiles": [
    {
      "id": "seedance_primary",
      "name": "Seedance Primary",
      "description": "Primary video generation via Seedance 2.0 on OpenRouter.",
      "studio_mode": "production",
      "file": "profiles/provider.seedance_primary.yaml"
    },
    {
      "id": "mock-demo",
      "name": "Mock Demo",
      "description": "Safe profile for testing with zero-cost mock provider.",
      "studio_mode": "mock",
      "file": "profiles/mock-demo.yaml"
    }
  ],
  "total": 12
}
```

### 2. Inspect a profile

```
MCP: inspect_profile { "profile_id": "seedance_primary" }
```

Returns the full YAML raw. Use this to verify provider ids, model ids, budget caps,
and validator strictness before creating a project.

### 3. Create a real-mode project

```
MCP: create_film_project {
  "project_id":         "my-film-001",
  "title":              "After the Fall",
  "slug":               "after-the-fall",
  "runtime_mode":       "real",
  "provider_profile":   "seedance_primary",
  "quality_profile":    "studio",
  "film_type_profile":  "narrative",
  "review_profile":     "strict_continuity"
}
```

**Real-mode guards:**
- Any profile referencing a `mock-*` provider or model id is rejected
- `runtime_mode` must be `"mock"` or `"real"` — anything else returns an error

If the call succeeds, the project is locked into real mode. The resolved profile
stack is persisted in project state and visible via `get_runtime_mode`.

### 4. Verify the mode

```
MCP: get_runtime_mode
```

Returns:
```json
{
  "ok": true,
  "runtime_mode": "real",
  "profile_stack": {
    "provider_profile": "seedance_primary",
    "quality_profile": "studio",
    "film_type_profile": "narrative",
    "review_profile": "strict_continuity"
  }
}
```

### 5. Proceed with the normal workflow

```
MCP: submit_idea    { "idea": "A survivor discovers..." }
MCP: approve_phase
MCP: approve_phase  (after each phase)
MCP: request_revision { "note": "Tone needs to be darker." }
```

The existing MCP workflow is unchanged. Profile resolution happens once at project
creation time and is stored in state.

---

## Detecting Accidental Mock Mode

If `get_runtime_mode` returns `"mock"`, OpenClaw is NOT in production mode.
Do not proceed with a project that expects real execution.

Check:
1. Was `runtime_mode: "real"` passed to `create_film_project`?
2. Did any profile reference a `mock-*` id that caused rejection at creation time?

**To retroactively verify a project:** call `inspect_profile` on the profiles
referenced in `get_runtime_mode`'s `profile_stack`. If any return `studio_mode: "mock"`,
the project was created with mock infrastructure.

---

## Current Limitations (first slice)

This is the **first slice** of the real-mode MCP path. The following is still in progress:

| Capability | Status |
|-----------|--------|
| Profile-aware project creation with real-mode guards | ✅ Done |
| Profile discovery and inspection via MCP | ✅ Done |
| Real-mode enforcement (mock rejection at project creation) | ✅ Done |
| Real model adapter execution (live LLM calls) | Not yet — `GraphServices.for_real_runtime()` planned |
| Real provider registration from resolved config | Not yet — providers not auto-registered at startup |
| Real-mode bootstrap (credential validation at startup) | Not yet |
| Audit evidence proving live model usage | Not yet |

The gap between "project is marked real" and "runtime actually calls real models"
is tracked in [real-model-only-mcp-plan.md](./mcp-openclaw/real-model-only-mcp-plan.md).
The remaining phases are scoped and ordered in that document.
