# Runbook: watchdog recovery

## Persistent watchdog

The watchdog is installed as:

- `~/Library/LaunchAgents/com.agentchappie.watchdog.plist`
- `RunAtLoad=true`
- `StartInterval=30`

## Healthy check

```bash
python3 /Users/chappie/Projects/Agent.Chappie/scripts/watchdog_agent.py --status-dir /Users/chappie/Projects/Agent.Chappie/runtime_status --stale-seconds 60 --check-only
```

## Force stale check for debugging

```bash
python3 /Users/chappie/Projects/Agent.Chappie/scripts/watchdog_agent.py --status-dir /Users/chappie/Projects/Agent.Chappie/runtime_status --stale-seconds 0 --check-only
```

## Recovery behavior

- if heartbeat is stale and restart budget remains, watchdog:
  kills the pid from the heartbeat payload when present
  calls `launchctl kickstart -k gui/<uid>/com.agentchappie.runtime`
- if the runtime exits unexpectedly, launchd restarts it because `KeepAlive=true`
- if restart budget is exhausted, watchdog logs `restart_blocked`

## Files

- heartbeat: `runtime_status/heartbeat.json`
- watchdog state: `runtime_status/watchdog_state.json`
- watchdog log: `runtime_status/watchdog_log.jsonl`

## Restart storm protection

- watchdog allows 3 restarts per 300 seconds
- further stale recoveries in that window are blocked and logged
