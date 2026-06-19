# Phase 16 — Productization & Release Readiness

**Depends on:** Phases 13 (Real Provider Adapter), 14 (Post-Production Assembly), 15 (Production Hardening)
**Blocks:** Nothing (final phase)
**Human Gate:** Yes — release and production enablement require approval

---

## Goal

Turn the system from an implementation-complete codebase into a working product that another operator can install, configure, run, observe, demo, and release safely.

This phase closes the gap between "the architecture works" and "the studio is actually usable." The focus is packaging, startup ergonomics, operator workflow, demoability, release safety, and final product acceptance.

---

## Deliverables

### Files to Create / Modify

#### Product Runtime

- [ ] `src/film_pipeline/mcp/server.py` — production MCP server entrypoint with startup, shutdown, and health hooks
- [ ] `src/film_pipeline/app/bootstrap.py` — environment/bootstrap validation for startup
- [ ] `src/film_pipeline/app/health.py` — readiness and dependency health checks
- [ ] `src/film_pipeline/app/smoke.py` — product smoke-test runner
- [ ] `src/film_pipeline/app/version.py` — runtime version/build metadata

#### Packaging / Scripts

- [ ] `Makefile` — add product-level commands (`make run-mcp`, `make smoke`, `make demo-project`, `make release-check`)
- [ ] `pyproject.toml` — package entrypoints and optional dependency groups
- [ ] `scripts/run_local_mcp.py` — local launch helper
- [ ] `scripts/create_demo_project.py` — creates sample working project
- [ ] `scripts/release_check.py` — consolidated release validation

#### Example Assets / Profiles

- [ ] `profiles/mock-demo.yaml` — safe demo profile
- [ ] `profiles/local-real-provider.yaml` — real-provider local profile
- [ ] `examples/demo-project/` — sample project inputs and expected outputs
- [ ] `tests/smoke/test_product_bootstrap.py` — bootstrap and startup smoke test
- [ ] `tests/smoke/test_demo_project_flow.py` — demo-project smoke flow

#### Documentation

- [ ] `README.md` — quickstart, install, run, smoke, demo, release links
- [ ] `docs/operations-guide.md` — operator workflow from project creation to delivery
- [ ] `docs/runbook-first-film.md` — first real film runbook
- [ ] `docs/release-process.md` — release checklist, tagging, rollback, hotfix flow
- [ ] `docs/demo-guide.md` — how to demo the product safely
- [ ] `docs/acceptance-checklist.md` — final consolidated product acceptance checklist

---

## Task Checklist

### Runtime Packaging

- [ ] Provide a stable MCP server entrypoint:
  - [ ] Starts from one documented command
  - [ ] Validates environment before serving requests
  - [ ] Reports version, profile, and dependency health
  - [ ] Fails fast on missing required configuration
- [ ] Define runtime dependency groups:
  - [ ] core dev/test dependencies
  - [ ] post-production/media dependencies
  - [ ] real-provider dependencies

### Bootstrap And Health

- [ ] Implement bootstrap validation:
  - [ ] verify writable artifact directories
  - [ ] verify configured profiles resolve correctly
  - [ ] verify ffmpeg/tooling availability if enabled
  - [ ] verify credentials only when the selected profile requires them
- [ ] Implement health checks:
  - [ ] readiness for MCP server
  - [ ] provider credential health
  - [ ] artifact store health
  - [ ] checkpoint store health
  - [ ] knowledge-base availability

### Operator Workflow

- [ ] Define the default operator journey:
  - [ ] bootstrap environment
  - [ ] create project
  - [ ] submit idea
  - [ ] progress through approvals
  - [ ] run generation
  - [ ] inspect blockers and audit trail
  - [ ] assemble review cut
  - [ ] export delivery package
- [ ] Ensure docs and scripts match the actual MCP tool names and commands
- [ ] Provide a demo project that exercises the happy path with minimal setup

### Smoke Tests

- [ ] Add product smoke tests:
  - [ ] fresh checkout bootstrap
  - [ ] MCP server startup
  - [ ] health endpoint / health tool response
  - [ ] demo project creation
  - [ ] happy-path mock flow
  - [ ] delivery package export
- [ ] Add a release-check command that runs:
  - [ ] lint/type/test gates
  - [ ] smoke tests
  - [ ] docs link/reference sanity checks
  - [ ] required example/profile presence checks

### Demo And Release Readiness

- [ ] Create a safe demo mode:
  - [ ] mock-only profile
  - [ ] deterministic example project
  - [ ] bounded runtime and artifact size
- [ ] Define release process:
  - [ ] versioning convention
  - [ ] release checklist
  - [ ] rollback procedure
  - [ ] hotfix path
  - [ ] known limitations section

### Final Acceptance Consolidation

- [ ] Copy the top-level ship checklist into `docs/acceptance-checklist.md`
- [ ] Link each checklist section to the owning phase docs
- [ ] Record pass/fail evidence locations for each final acceptance item
- [ ] Require explicit approval before calling the product release-ready

---

## Acceptance Criteria

- [ ] A new operator can install and run the MCP server from documentation alone
- [ ] `make run-mcp` (or equivalent documented command) starts the product successfully
- [ ] Startup fails with actionable messages when required config is missing
- [ ] Health checks correctly report readiness and dependency failures
- [ ] Demo project can be created and run in mock mode end to end
- [ ] Release-check command validates code, smoke tests, and required docs/assets
- [ ] Example profiles cover both mock-demo and local real-provider usage
- [ ] The final acceptance checklist exists as its own document and is traceable to phase evidence
- [ ] Release and rollback procedures are documented and usable
- [ ] Another operator could reasonably reproduce the first successful film run without tribal knowledge

---

## Risks

| Risk | Mitigation |
|------|------------|
| Product docs drift from implementation | Make smoke and release-check commands validate documented commands and files |
| Packaging complexity hides runtime issues | Keep one blessed startup path and one blessed demo path |
| "Works on my machine" bootstrap failures | Fresh-checkout smoke tests and bootstrap validation |
| Final acceptance becomes subjective | Use a separate acceptance checklist with evidence links and explicit approval |
