# Phase 6 — Provider Tier Routing

**Status:** Not started
**Depends on:** Nothing
**Blocks:** Phase 2 (prompt builder needs tier to set quality params)

---

## Goal

Route entries to different provider configs based on a `tier` field.

## Why

The legacy spec uses 3 tiers for cost/quality differentiation:

| Tier | Cost/Image | Use |
|------|-----------|-----|
| Fast | $0.02 | Bulk — environments, expressions, body shots |
| Standard | $0.05 | Critical anchors — hero face, key poses |
| Ultra | $0.10 | Detail insets — eyes, hands, textures |

## Implementation

- Add `tier: Literal["fast", "standard", "ultra"] = "fast"` to `ReferenceIndexEntry`
- Update `VisualDevAgent` prompt template to let the model assign tiers
- In `generate_reference_images`, select provider parameters based on tier:
  - Fast: standard quality, lower resolution
  - Standard: high quality + seed
  - Ultra: max quality + seed + higher resolution

## Files

| File | Action |
|------|--------|
| `schemas/reference.py` | Add `tier` field |
| `agents/impl/visual_dev_agent.py` | Parse `tier` from model output |
| `agents/prompt_templates/defaults.py` | Update visual-dev template to include tier assignment |
| `mcp/tools/__init__.py` | Read tier, adjust provider call parameters |

## Effort

~40 lines across 4 files.

## Tests

| Type | What |
|------|------|
| Unit | Tier → provider parameter mapping (fast/standard/ultra) |
