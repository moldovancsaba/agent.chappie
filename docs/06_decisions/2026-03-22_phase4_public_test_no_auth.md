# Decision: Phase 4 public test MVP ships without auth

Date:

- 2026-03-22

## Context

The first implementation-bearing MVP should validate the accepted job, result, and feedback contracts quickly. Auth would add significant implementation drag before the core workflow is proven in a public test surface.

## Decision

For Phase 4:

- the first app version is a public test app
- auth integration is explicitly deferred
- there is no OIDC, OAuth, JWT verification, session middleware, or SSO wiring in this phase
- the app uses anonymous demo identifiers instead of authenticated users

## Rules

- the app remains thin and contract-driven
- the lack of auth must not change the core contracts unnecessarily
- the app must use demo-safe content only
- sensitive client data must not be used in the public test flow

## Consequences

- implementation friction drops materially for the first release
- the MVP should be treated as a workflow-validation surface, not a secure product launch
- a later auth phase can add authenticated ownership and access control without breaking the current contract layer
