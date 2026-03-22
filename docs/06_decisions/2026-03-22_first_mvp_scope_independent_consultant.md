# Decision: First MVP scope is independent consultant follow-up

Date:

- 2026-03-22

## Context

Phase 3 requires one domain, one user type, and one recommendation loop only. The scope must be narrow enough to preserve the clean core/scheduler/app boundary and avoid multi-domain drift.

## Decision

The first MVP scope is:

- domain: client project follow-up task recommendation
- user type: independent consultant managing one client project
- loop: upload project context, receive recommended follow-up tasks, submit done/edited/declined feedback

## Rules

- the scope remains contract-level only in this phase
- the core remains app-agnostic
- the MVP language stays capability-oriented rather than page-oriented
- no second domain or user type is introduced in this phase

## Alternatives considered

- a broader multi-role productivity assistant
- a general team task engine without a single user type
- multiple domains in parallel

## Consequences

- the first app contract can stay concrete without hardcoding product logic into the core
- the next worked example can be tied to a real user and real problem
- expansion pressure remains intentionally constrained
