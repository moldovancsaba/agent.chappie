# Agent.Chappie Operational Model

## Current runtime modes

### Dry-run

- deterministic local stub
- fully validated in this repository
- used for repeatable control-plane verification

### Live-run

- uses Ollama transport through `http://127.0.0.1:11434/api/generate`
- validated on the host with `llama3:latest`
- still not reproducible inside the restricted sandbox because of loopback limits

## Task lifecycle

1. receive request
2. persist request trace
3. generate `StructuredTaskObject`
4. validate `StructuredTaskObject`
5. collect retrieval evidence
6. generate `ExecutionPlan`
7. validate `ExecutionPlan`
8. generate `DecisionRecord`
9. validate `DecisionRecord`
10. route with confidence thresholds
11. produce outcome or error outcome
12. persist all trace artifacts

## Failure handling

Current failure behavior:

- if any stage raises an exception, outcome is recorded with `status=error`
- placeholder artifact files are written for unproduced triad artifacts
- request and outcome traces always persist

## Retry logic

- no automatic retry loop is implemented yet
- retries are manual at this phase

## Freeze detection

- watchdog checks heartbeat age against a bounded stale threshold
- stale detection is implemented in `scripts/watchdog_agent.py`
- stale recovery is performed by a persistent watchdog launchd job

## Boot behavior

- manual CLI invocation is validated
- runtime and watchdog launchd plists exist for service-style boot on the host
- install/bootstrap behavior is the current reboot-equivalent startup proof in this repository

## Restart behavior

- `launchd` restarts the runtime when it exits unexpectedly because `KeepAlive=true`
- watchdog can request restart through `launchctl kickstart -k`
- restart storm protection is bounded by count and rolling window

## Heartbeat behavior

- runtime loop writes `runtime_status/heartbeat.json`
- heartbeat records pid, mode, last heartbeat, and last probe status

## Current service truth

- runtime foundation is implemented
- service supervision behavior is documented
- launchd service is evidenced as running on the host
- watchdog service is evidenced as running on the host
- crash recovery is evidenced on the host
- watchdog restart path is evidenced on the host
