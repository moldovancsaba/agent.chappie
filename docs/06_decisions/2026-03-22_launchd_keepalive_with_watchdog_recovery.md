# Decision: launchd KeepAlive with watchdog stale recovery

Date:

- 2026-03-22

## Context

Agent.Chappie now has a host-live runtime service and a watchdog, but unattended operation needs an explicit supervision split between crash restart and stale-state recovery.

## Decision

Use this supervision model:

- `launchd` with `KeepAlive=true` for crash and unexpected exit recovery
- watchdog as a separate persistent launchd job for stale heartbeat and freeze-style recovery
- bounded restart budget enforced by watchdog to avoid restart storms

## Alternatives considered

- `KeepAlive=false` with watchdog as the sole restart authority
- `KeepAlive=true` without a separate stale-state watchdog

## Consequences

- crash recovery is delegated to launchd directly
- stale recovery remains explicit and inspectable
- unattended runtime behavior becomes easier to reason about and prove
