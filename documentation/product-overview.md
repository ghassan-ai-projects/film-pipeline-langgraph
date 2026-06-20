# Product Overview

`film-pipeline-langgraph` is an MCP-first film studio runtime for taking a film idea through structured pre-production and generation preparation.

## Supported Product Boundary

The supported path today is:

`idea -> approved artifacts -> generation planning -> generation bookkeeping -> QC evidence -> validated handoff state`

What is real inside the repository:

- MCP tools drive the workflow
- runtime state, approvals, checkpoints, and audit are persisted
- critical-path agents run through dedicated prompt templates
- artifact lineage is stored and inspectable
- validation changes runtime behavior
- generation planning, spend approval, status, cancel, resume, and promotion are behavior-tested

What is intentionally out of scope right now:

- final editorial assembly
- audio post
- color grading
- delivery packaging

Those downstream steps are expected to happen in an external finishing tool such as DaVinci Resolve.

## Core Runtime Path

1. Create project
2. Submit idea
3. Approve through intake, constitution, development, script, visual development, shot bible, and generation planning
4. Plan generation batches and approve spend
5. Move into generation/QC control states without requiring paid video execution
6. Inspect artifacts, validation, checkpoints, routing, and audit evidence

## Best Starting Points

- Operator setup: [getting-started.md](./getting-started.md)
- Codebase map: [repository-structure.md](./repository-structure.md)
- Maintainer onboarding: [onboarding.md](./onboarding.md)
- Reproducible manual walkthrough: [manual-4min-mock-short.md](./manual-4min-mock-short.md)
