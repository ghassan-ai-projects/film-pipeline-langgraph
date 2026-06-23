# Providers Page

## Purpose

Support provider health and generation operations.

## Primary Users

- studio_operator

## Why This Page Exists

Operational degradation needs a dedicated page.

## Main Sections

### 1. Provider List

Show:

- provider id
- status
- capability family
- active job count

### 2. Provider Detail

Show:

- latest failures
- health reason
- safe-to-continue flag
- related generation state

### 3. Recovery Actions

Actions:

- refresh health
- inspect jobs
- resolve block
- jump to affected assets or review

## Key Actions

- inspect degraded providers
- understand generation blockers
- choose next operational step

## Required Data

- provider status list
- provider health detail
- generation overview

## Cross-Links

- `Dashboard`
- `Assets`
- `Review`

## V1 Priority

Medium priority.
