# Phase 13 — Real Provider Adapter

**Depends on:** Phase 10 (Mock Provider), Phase 12 (E2E Mock Mini-Film passes)
**Blocks:** Phase 15 (Production Hardening)
**Human Gate:** Yes — real provider spend requires approval

---

## Goal

Implement real video provider adapters following the same `BaseProviderAdapter` contract proven by the mock provider. Start with Seedance 2.0 (via OpenRouter) as the primary provider, then add Veo 3.1 Fast as fallback. Every safety mechanism — idempotent submission, generation ledger, provider health tracking, failure handling, cost controls — must work with real providers.

No paid generation until E2E mock baseline passes.

---

## Deliverables

### Files to Create

#### Real Provider Adapters (`src/film_pipeline/providers/adapters/`)

- [ ] `seedance_openrouter.py` — Seedance 2.0 via OpenRouter
- [ ] `veo_fast.py` — Veo 3.1 Fast
- [   ] `veo_lite.py` — Veo 3.1 Lite (optional, later)
- [   ] `__init__.py`

#### Provider Credentials (`src/film_pipeline/providers/credentials.py`)

- [ ] Credential lookup (environment variables, per-provider)
- [   ] Credential health check
- [ ] Safe error redaction (no secrets in logs or artifacts)
- [   ] `__init__.py` (already exists from Phase 10)

#### Provider-Specific Tests

- [ ] `tests/integration/providers/test_seedance_adapter.py` — adapter contract compliance (mocked HTTP)
- [   ] `tests/integration/providers/test_veo_adapter.py` — adapter contract compliance (mocked HTTP)
- [   ] `tests/integration/providers/test_credential_management.py` — credential lookup and redaction

---

## Task Checklist

### Seedance 2.0 Adapter

- [ ] Implement `SeedanceOpenRouterProvider(BaseProviderAdapter)`:
  - [   ] `build_payload(prompt_package, references, config)` — construct OpenRouter API payload
  - [   ] `submit(payload)` — POST to OpenRouter, return job_id
  - [   ] `poll(job_id)` — GET job status from OpenRouter
  - [   ] `download(job_id)` — download output video from URL
  - [   ] `extract_metadata(asset)` — extract duration, resolution, codec
  - [   ] `estimate_cost(duration, model)` — $0.18/second for Seedance 2.0
  - [   ] `cancel(job_id)` — cancel if OpenRouter supports it
- [   ] Register provider in `ProviderRegistry`:
  - [   ] `provider_id: "seedance-openrouter"`
  - [   ] `models: ["bytedance/seedance-2.0"]`
  - [   ] `capabilities: {text_to_video: true, image_to_video: true, return_last_frame: true, max_duration_seconds: 15, aspect_ratios: ["16:9", "9:16"], supports_audio: false}`
  - [   ] `cost_profile: {unit: "second", estimated_rate: 0.18}`
  - [   ] `failure_modes: ["timeout", "quota", "moderation", "download_failure"]`
- [   ] Implement polling config:
  - [   ] `initial_delay_seconds: 20`
  - [   ] `poll_interval_seconds: 30`
  - [   ] `max_wait_seconds: 1800`
  - [   ] `backoff_multiplier: 1.2`

### Veo 3.1 Fast Adapter

- [ ] Implement `VeoFastProvider(BaseProviderAdapter)`:
  - [   ] Full adapter contract implementation
  - [   ] Different API endpoint and payload format
  - [   ] Different cost profile
- [   ] Register in `ProviderRegistry` with capabilities and cost

### Credential Management

- [ ] Implement credential lookup:
  - [   ] `OPENROUTER_API_KEY` for Seedance
  - [   ] `GOOGLE_API_KEY` for Veo
  - [   ] Per-provider credential health check
- [   ] Implement safe error redaction:
  - [   ] Never log API keys
  - [   ] Never include keys in artifacts or audit log
  - [   ] Redact keys from error messages

### Cost Controls

- [ ] Implement budget enforcement:
  - [   ] Check budget before submit
  - [   ] Block if estimated cost exceeds remaining budget
  - [   ] Require human approval for spend above threshold
- [   ] Implement spend tracking:
  - [   ] Record actual cost in generation ledger
  - [   ] Update budget state after each generation
  - [   ] Alert when approaching budget cap

### Integration Testing

- [ ] Write adapter contract compliance tests (mocked HTTP responses)
- [   ] Test idempotent submission with real adapter
- [   ] Test polling and download with mocked responses
- [   ] Test failure handling: timeout, quota, auth, moderation
- [   ] Test provider health tracking with real adapter
- [   ] Run `make ci-check`

---

## Acceptance Criteria

- [   ] Seedance adapter implements full `BaseProviderAdapter` contract
- [   ] Veo adapter implements full `BaseProviderAdapter` contract
- [   ] Both adapters pass contract compliance tests (mocked HTTP)
- [   ] Idempotent submission works (no duplicate jobs)
- [   ] Polling config is respected (initial delay, interval, max wait)
- [   ] Cost estimation is accurate ($0.18/s for Seedance)
- [   ] Budget enforcement blocks over-spend
- [   ] Human approval required for spend above threshold
- [   ] Credentials are never logged or stored in artifacts
- [   ] Provider health tracking works with real adapters
- [   ] Failure handling agent correctly classifies real provider errors
- [   ] All tests pass
- [   ] `make ci-check` passes

---

## Definition of Ready for Real Generation

Before any real API call:

- [   ] E2E mock baseline (Scenarios 1, 4, 5, 6) passes
- [   ] Credential management implemented
- [   ] Budget enforcement implemented
- [   ] Idempotent submission verified
- [   ] Failure handling verified
- [   ] Audit trail explains every provider action
- [   ] 1-second test clip approved before full generation

---

## Provider Chain

```
Seedance 2.0 ($0.18/s) → Veo 3.1 Fast → Veo 3.1 Lite
```

Fallback only with human approval. No automatic provider switch unless profile explicitly allows it.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Real API costs | 1-second test clips first; budget caps; human approval for production |
| API changes | Abstract behind adapter; pin API version; test with mocked HTTP |
| Credential leakage | Redaction layer; no secrets in logs; `.env` in `.gitignore` |
| Rate limiting | Polling config respects provider limits; exponential backoff |
