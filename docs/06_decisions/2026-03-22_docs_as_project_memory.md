# Decision: Repository docs as project memory

Date:

- 2026-03-22

## Context

Project direction, constraints, and decisions were being tracked in chat context rather than a repository-native source of truth.

## Decision

Create and maintain a repository documentation layer under `docs/` for:

- vision
- architecture
- stack
- roadmap
- operational model
- constraints
- decisions
- runbooks
- handoffs

## Alternatives considered

- rely on chat history
- maintain loose notes outside the repository

## Consequences

- project state becomes transferable and auditable
- future development must keep docs and code in sync
