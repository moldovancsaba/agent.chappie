# Decision: Governed triad control plane

Date:

- 2026-03-22

## Context

The initial scaffold used a single-loop agent pattern. The project direction requires explicit governance, artifact separation, and auditable control flow.

## Decision

Adopt a governed triad-shaped control plane:

- `StructuredTaskObject`
- `ExecutionPlan`
- `DecisionRecord`
- explicit confidence router
- immutable on-disk trace persistence

## Alternatives considered

- keep a single generic loop
- move directly to broader multi-agent orchestration

## Consequences

- architecture becomes more explicit and inspectable
- dry-run verification becomes stronger
- live-run transport still remains a separate validation problem
