# Dashboard Page

## Purpose

Provide the best summary of project state and the clearest path to the next important action.

## Primary Users

- studio_operator
- film_creator

## Why This Page Exists

The dashboard is the control center.

It answers:

- where the project is
- what is blocked
- what needs human attention
- what the system wants to do next
- what scope the user should drill into next

## Main Sections

### 1. Project Summary Card

Show:

- project title
- current phase
- runtime mode
- workflow mode
- current status
- last updated time

### 2. Orchestrator Summary Card

Show:

- next action
- route reason
- active review cycle
- pending revisions
- candidate vs approved summary

### 3. Action Board

Show:

- eligible actions
- blocked actions
- reasons for blocked actions

### 4. Risk Board

Show:

- blocking issues count
- provider warnings
- budget/spend warnings
- structural warnings

### 5. Latest Work

Show:

- latest artifacts
- latest checkpoints
- latest audit entries

## Key Actions

- open review package
- open structure page
- open scenes page
- open assets page
- open validation page
- approve phase
- request revision
- change workflow mode

## Required Data

- project summary
- orchestrator summary
- workflow mode summary
- blocker summary
- next-actions summary
- latest artifacts summary
- latest audit summary
- provider health summary

## Refresh Behavior

- periodic refresh
- immediate refresh after mutations
- partial refresh acceptable for secondary widgets

## Cross-Links

- `Review`
- `Structure`
- `Scenes`
- `Assets`
- `Validation`
- `Providers`
- `Checkpoints`

## V1 Priority

Highest priority page.
