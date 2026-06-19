# 01 Runtime And Graph

---

## Goal

Make the runtime and graph the true execution engine of the product.

The runtime must own:

- durable project state
- phase progression
- approval and revision semantics
- checkpoint creation
- rollback coordination
- audit and resume

The graph must own:

- real phase execution entry points
- human pause/resume semantics
- deterministic routing between phases
- dynamic branching when work is blocked or parallelizable

---

## Final Product Result

When this phase is complete:

- creating a project creates durable state and a valid working root
- submitting an idea starts real phase execution
- approving a phase resumes execution cleanly into the next phase
- revision requests re-enter the correct repair path
- graph pauses use explicit interrupt semantics, not recursion failure handling
- state can be reloaded and resumed without corruption

---

## Required Implementation

### Runtime

- replace ad hoc dict state with one canonical runtime state model
- persist state after every mutating operation
- create checkpoints automatically at required approval and expensive-operation gates
- record audit events for every runtime mutation
- track current phase, pending actions, blockers, approvals, checkpoint refs, validation refs, and artifact refs

### Graph

- replace GraphRecursionError control flow with explicit pause/resume behavior
- route from current project state, not only from graph entry defaults
- implement real revision, repair, and rollback edges
- support blocked-path plus available-path routing where architecture requires it

---

## Concrete Tests

### Unit Tests

- runtime state initialization
- phase approval transition
- revision transition
- checkpoint creation on approval
- rollback request state preparation
- graph route from current phase
- interrupt/pause state
- resume after approval

### Integration Tests

- `create project -> submit idea -> approve -> next phase`
- revision request keeps the project recoverable
- checkpoint metadata is created with phase and git refs
- restart runtime from persisted state and continue
- blocked path does not destroy independent available work

### Final Acceptance Tests

- a project can advance from intake to script through persisted runtime behavior
- no test in the supported path relies on catching recursion errors as normal control flow

---

## Acceptance Criteria

This area is done only when all of the following are true:

- runtime state is durable, reloadable, and authoritative
- approval transitions are real runtime operations, not flag flips only
- graph pause/resume uses explicit semantics
- revision and repair paths are executable and test-covered
- checkpoint creation is automatic at required gates
- audit records explain all graph-visible runtime mutations
