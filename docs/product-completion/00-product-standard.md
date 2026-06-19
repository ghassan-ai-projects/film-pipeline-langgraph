# 00 Product Standard

---

## Hard Definition Of Done

The project is done only when all of the following are true:

- idea to delivery is possible on the supported path through MCP
- no critical-path MCP tool returns stub output
- no core graph phase is label-only
- core agents produce schema-valid artifacts through the prompt framework
- dynamic agent routing chooses and executes real agents by capability and state
- validators produce real findings and can block downstream work
- approvals, checkpoints, rollback, and audit are real runtime behaviors
- generation is idempotent and recoverable
- review cut and delivery package are real outputs, not plans only
- all required E2E scenarios pass
- an operator can install, run, inspect, recover, and release the system from the docs

If any of the above is false, the project is not done.

The only tolerated non-real external behavior is costly video generation itself. Even there, the
surrounding runtime behavior must be real and behavior-tested:

- planning
- spend approval
- job submission bookkeeping
- polling/resume
- duplicate-prevention
- provider block handling
- artifact ingestion

---

## Non-Negotiable Rules

- A phase is not done if it only mutates `current_phase`, `approved`, or gate flags.
- An agent is not done if it only returns canned dicts or mock shells in production flow.
- A prompt framework is not done if prompts are generic and not adopted by real core agents.
- Dynamic routing is not done if the orchestrator does not actually select agents based on capability, state, and policy.
- Validation is not done if reports are stored but runtime behavior does not change.
- MCP is not done if operators need hidden internal APIs or direct runtime mutation.
- Checkpointing is not done if rollback cannot restore meaningful project state.
- Documentation is not done if it claims behavior that is not validated by tests.
- The only acceptable mock/stub at product-completion time is paid video creation execution itself; all surrounding behavior must be tested and proven.

---

## Mandatory Evidence

Each major capability must have all of the following:

- implementation files
- unit tests
- integration tests where boundaries matter
- at least one E2E scenario proving operator-visible behavior
- documentation that matches real commands and tool names

Claims without behavior tests do not count as evidence.

---

## Product Acceptance Gate

The product cannot be called release-ready until:

- all critical-path docs in this folder are satisfied
- all critical-path MCP tools are non-stubbed
- mock-mode end-to-end baseline passes
- the real-provider path is gated behind completed mock acceptance
