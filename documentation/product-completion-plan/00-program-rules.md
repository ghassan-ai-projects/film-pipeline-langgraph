# Phase 00 - Program Rules And Acceptance Control

Depends on: none
Blocks: all later phases

---

## Goal

Create a hard execution frame so the remaining work is judged by product behavior, not by structure, good intentions, or partial wiring.

---

## Scope

- align completion work to the product standard
- define evidence requirements per claim
- define which stubs are forbidden
- define mandatory validation commands per phase
- define documentation truthfulness rules

---

## Deliverables

- `documentation/product-completion-plan/acceptance-manifest.yaml`
- `documentation/product-completion-plan/acceptance-checklist.md`
- `documentation/product-completion-plan/status-tracker.md`
- references from this folder back to `documentation/product-completion/`

---

## Required Decisions

- product claims must be tied to test files or commands
- acceptance must record both current state and final required state
- only costly video rendering may remain externally mocked
- all non-video workflows must be behavior-tested
- secrets must be loaded from environment or local `.env`, and never echoed back in logs or docs

---

## Mandatory Validation

- `UV_CACHE_DIR=.uv-cache uv run --python 3.12 --group dev pytest -q`
- `UV_CACHE_DIR=.uv-cache uv run --python 3.12 --group dev ruff check .`
- `UV_CACHE_DIR=.uv-cache uv run --python 3.12 --group dev mypy src tests`
- `UV_CACHE_DIR=.uv-cache make product-gate`

For product-complete status, `make ci-check` must pass.

---

## Acceptance Criteria

- [x] completion language is hard and test-backed
- [x] global checklist exists and is traceable to phases
- [x] allowed stub policy is explicit
- [x] required validation commands are explicit
- [x] documentation claims require evidence references

---

## Exit Condition

✅ This phase is done — the plan cannot silently drift into "soft done" language.

## Implementation Notes

- `make ci-check` now includes `product-gate` as a mandatory step
- `product_gate.py` loads both manifests (standard + plan)
- Plan manifest keys (`allowed_stub_behaviors`, `required_e2e_scenarios`) mapped during load
- `src/film_pipeline/mcp/tools/__init__.py` excluded from coverage (tracked by product-gate stub detection)
- Pre-existing lint/mypy issues in `test_generation_mcp.py` and `test_app_ops.py` fixed
