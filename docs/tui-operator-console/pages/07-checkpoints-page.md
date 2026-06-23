# Checkpoints Page

## Purpose

Support compare, rollback, and recovery workflows.

## Primary Users

- studio_operator
- film_creator

## Why This Page Exists

Recovery is a core trust feature.

## Main Sections

### 1. Checkpoint Timeline

Show:

- checkpoint id
- phase
- reason
- timestamp

### 2. Selected Checkpoint Detail

Show:

- artifact versions
- approvals
- related audit

### 3. Invalidation Preview

Show:

- what will revert
- what will invalidate
- what requires regeneration

### 4. Actions

Actions:

- compare versions
- preview rollback
- execute rollback

## Key Actions

- inspect history
- compare baseline changes
- rollback safely

## Required Data

- checkpoint list
- checkpoint detail
- invalidation preview
- version comparison

## Cross-Links

- `Dashboard`
- `Review`
- `Structure`
- `Scenes`
- `Assets`

## V1 Priority

Medium-high priority.
