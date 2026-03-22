# Contract: Scheduler Policy v1

## Purpose

Defines the minimal scheduler behavior needed for clean future multi-app support without implementing the scheduler yet.

## Policy

- serial execution by default
- one heavy job at a time
- queued work grouped by app and project identity
- bounded concurrency
- no app may bypass scheduler ordering

## State model

- `queued`
- `running`
- `complete`
- `failed`
- `blocked`

## Ordering principles

- higher `priority_class` jobs should be considered before lower priority jobs
- heavy jobs should not run concurrently in v1
- light jobs may be considered for future concurrency, but not in this phase
- per-app and per-project identity must prevent one app from starving all others

## Non-goals in v1

- no quota engine
- no cooldown engine
- no dynamic fairness algorithm
- no implementation in code yet

## Boundary rule

Scheduler policy belongs to the scheduler layer. App clients can request work and declare identity and priority hints, but they do not decide execution ordering.
