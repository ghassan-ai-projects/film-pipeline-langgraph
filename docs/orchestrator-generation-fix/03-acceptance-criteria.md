# Acceptance Criteria

## Goal

The pipeline should be able to take an authored 4-minute film blueprint and produce a generation-ready plan without losing structure, runtime, or execution-critical metadata.

## Functional Criteria

- The orchestrator stores the approved film execution brief after script approval.
- The shot-bible phase preserves authored movement structure unless a human explicitly approves a deviation.
- The shot-bible output includes enough shot rows to satisfy the approved movement plan.
- The summed shot durations match the approved runtime within a defined tolerance.
- Every shot row contains non-empty generation-critical fields.
- Generation planning produces real clip counts and non-placeholder cost estimates.
- Provider dispatch only starts from executable requests.

## Camino-Specific Expected Outcome

For the current Camino-style film:

- the orchestrator recognizes a 240-second target runtime
- the orchestrator recognizes a `5 + 5 + 5 + 4` authored shot pattern
- the resulting plan preserves the barren -> green -> split -> yellow-rose progression
- every shot is tied to concrete subject, environment, and camera intent
- generation planning reports the actual number of planned clips
- paid-provider estimates are greater than zero unless mock mode is active

## Validation Criteria

- A failing shot-count mismatch blocks advancement out of shot-bible.
- A failing runtime mismatch blocks advancement out of shot-bible or planning.
- A missing prompt or reference package blocks provider dispatch.
- A symbolic `prompt_ref` without a resolved payload is treated as not ready.

## Non-Goals

- letting downstream phases infer missing structure from vague upstream artifacts
- silently accepting under-produced shot matrices
- relying on provider submission code to repair planning defects

## Done

This effort is done when the orchestrator prevents the known failure mode by design, not by lucky prompt behavior.
