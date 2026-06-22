# Root Cause Analysis

## Problem Statement

The current flow can complete phases without crashing, yet still fail the actual production goal:

- fewer shots than the authored film blueprint
- shorter runtime than the target film runtime
- generic shot matrix rows with empty operational fields
- zero-cost planning and blocked generation dispatch

This is not one bug. It is a control failure across multiple phases.

## Evidence

From the Camino source movie brief:

- the film is structured as 4 movements
- Movements 1, 2, and 3 each use 5 shots
- Movement 4 uses 4 shots
- the film ends with a held final chord over black
- the intended runtime is about 4 minutes

From the current pipeline behavior:

- the shot bible can return only 13 shots
- the runtime can collapse to about 93 seconds
- `prompt_ref`, character refs, environment refs, and camera refs can be empty
- generation cost can remain `$0.0`
- provider dispatch can be blocked before usable clip requests exist

## 5 Whys

### 1. Why does the film end up with too few shots?

Because the shot bible output is accepted even when it does not preserve the authored movement-to-shot structure.

### 2. Why is that output accepted?

Because the orchestrator treats the shot bible as a pass-through artifact producer, not as a contract enforcer.

### 3. Why does runtime collapse?

Because there is no phase-level invariant that checks authored runtime against summed shot durations before generation planning proceeds.

### 4. Why are shot rows operationally weak?

Because the flow does not require each shot row to resolve the minimum production fields needed for planning and provider execution.

### 5. Why does generation planning fail to produce real cost and dispatchable requests?

Because downstream planning is allowed to consume incomplete shot rows and symbolic prompt fields instead of fully resolved generation inputs.

## Root Cause

The orchestrator is not currently enforcing film-level invariants between:

- authored narrative structure
- shot decomposition
- prompt readiness
- generation planning
- provider dispatch readiness

Agents create artifacts. The orchestrator must decide whether those artifacts are sufficient to continue.

## Required Invariants

Before leaving shot design:

- every authored movement has the required shot count or an explicit approved override
- total shot duration matches the target runtime within tolerance
- every row has non-empty generation-critical references

Before leaving generation planning:

- every shot has a provider, model, duration, estimated cost, and usable prompt payload
- the batch estimate reflects real clips, not placeholder counts

Before provider dispatch:

- every request is executable without guessing missing fields at submit time
