# Decision: Layered platform boundary for Agent.Chappie

Date:

- 2026-03-22

## Context

Agent.Chappie now has an operationally trustworthy local runtime. The next risk is architectural drift: future MVP apps could push app-specific logic into the sovereign core unless the boundary is made explicit before product work begins.

## Decision

Agent.Chappie is the sovereign core/platform and is documented as three layers:

- Core Layer
- Scheduler Layer
- App Layer

The ownership split is:

- the core owns governed execution, triad artifacts, routing, traces, runtime supervision, and execution policy
- the scheduler owns execution ordering, queueing, priority, capacity policy, and app isolation
- apps live at the app layer and use explicit contracts for jobs, results, and feedback

## Rules

- app logic must not pollute core logic
- apps are clients of Agent.Chappie, not modifications of Agent.Chappie
- scheduler policy must not be embedded in app clients
- future MVPs must integrate through contracts instead of direct orchestration changes

## Alternatives considered

- build the first app directly against the core without a boundary pass
- let the first MVP define the job shape implicitly in product code
- place scheduling behavior inside app clients

## Consequences

- the core remains reusable across multiple future apps
- scheduler responsibilities can evolve without changing the app contract shape
- product work can stay thin and app-specific without corrupting the runtime foundation
