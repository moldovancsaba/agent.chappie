# Decision: Vercel app with Mac mini private worker boundary

Date:

- 2026-03-22

## Context

The product direction needs a public web surface and a sovereign local worker without making the Mac mini the public edge.

## Decision

Use this production boundary:

- Vercel app/API as the public layer
- durable database/job layer between app and worker
- Agent.Chappie on the Mac mini as a private worker

## Alternatives considered

- expose the Mac mini directly as the main public API
- use the Mac mini as the synchronous website dependency

## Consequences

- the public product can scale independently of the Mac mini
- the governed triad remains private and local-first
- direct tunnel exposure can remain optional admin access only
