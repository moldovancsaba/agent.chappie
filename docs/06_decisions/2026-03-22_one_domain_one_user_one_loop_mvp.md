# Decision: One-domain, one-user-type, one-loop MVP scope

Date:

- 2026-03-22

## Context

The product initiative needs a narrow initial scope so the worker, app boundary, and feedback loop can be validated without broad multi-domain expansion.

## Decision

Scope the first MVP to:

- one domain
- one user type
- one recommendation loop

The recommendation loop is:

1. user provides context or upload
2. Agent.Chappie recommends tasks
3. user marks done, edited, or declined
4. feedback is stored
5. future recommendations improve

## Alternatives considered

- launch broad multi-domain support immediately
- add many user roles before the first loop is stable

## Consequences

- product complexity stays bounded
- feedback quality is easier to evaluate
- roadmap stays aligned with the current worker maturity
