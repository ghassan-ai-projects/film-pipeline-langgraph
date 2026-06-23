# Risks, Open Questions, And Acceptance

## Key Risks

### 1. Backend duplication risk

If the TUI or MCP adapters own separate business rules, behavior will diverge.

Mitigation:

- extract shared application services
- keep adapters thin
- expose missing public state through MCP instead of duplicating logic in UI code

### 1a. Service-layer overreach risk

If the new service layer becomes a vague abstraction bucket, it will add complexity without
clarity.

Mitigation:

- organize by use case, not by generic helper categories
- extract only proven operator-critical workflows first
- keep service interfaces typed and narrow

### 2. Polling cost and stale state

A TUI with many panels can become chatty and inconsistent.

Mitigation:

- cache view models
- refresh by visible panel
- add bulk summary APIs where needed

### 3. Review-package readability

If review packages are verbose or inconsistent, the TUI will still feel hard to use.

Mitigation:

- treat review package quality as a product issue, not just a UI issue
- standardize summaries, issue severity, and recommendation fields

### 4. Terminal rendering limits

Long scripts and dense artifact metadata can become unpleasant in narrow terminals.

Mitigation:

- support wide-terminal expectation in docs
- design for split panes with wrap toggles
- let users pop into full-reader screens

### 5. Real-mode safety

A weak confirmation model could create accidental spend or irreversible operator mistakes.

Mitigation:

- strong runtime mode visibility
- explicit confirmations
- human-readable cost and invalidation previews

## Open Questions

### 1. Should the TUI start the MCP server or attach to an already-running one?

Recommendation:

- support both
- start-local is the default for simplicity
- attach mode is useful for advanced debugging

### 2. Should review notes support markdown?

Recommendation:

- yes for storage and readability
- keep plain text fully supported

### 3. Should artifact editing happen in the TUI?

Recommendation:

- not in V1
- inspection and decision support first
- if editing is added later, keep it tightly scoped to note fields and safe metadata

### 4. Should the TUI support multiple simultaneous server connections?

Recommendation:

- no for V1
- one local studio per TUI process keeps complexity low

### 5. Do we need a chat pane?

Recommendation:

- no by default
- the product need is operator decision support, not another chat surface

## Acceptance Criteria For The Architecture

- the TUI clearly preserves MCP as the product boundary
- shared application services exist below MCP and TUI
- the UI model maps to the real pipeline and human gate flow
- review, blocker, provider, and rollback workflows are first-class
- the recommended implementation is incremental and low-risk
- extension strategy exists without speculative over-abstraction

## Acceptance Criteria For The Product

- the operator can find the next required action quickly
- the operator can review a phase without raw JSON being the main experience
- the operator can distinguish approved vs candidate state
- the operator can understand why an action is blocked
- the operator can inspect rollback impact before committing
- the operator can see whether the system is in mock or real mode at all times

## Final Recommendation

Build the TUI.

But build it as an operator console over shared application services, with MCP preserved as
the public control surface.

That is the highest-leverage path:

- it improves usability immediately
- it respects the current architecture
- it keeps logic centralized below both surfaces
- it scales with the rest of the studio
